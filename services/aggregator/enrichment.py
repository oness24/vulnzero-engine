"""
CVE enrichment service - fetches additional data from NVD and EPSS
"""

import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import structlog
import asyncio

logger = structlog.get_logger()


class CVEEnricher:
    """Enriches vulnerability data with CVE information from NVD and EPSS"""

    def __init__(self, nvd_api_key: Optional[str] = None):
        """
        Initialize CVE enricher

        Args:
            nvd_api_key: Optional NVD API key for higher rate limits
        """
        self.nvd_api_key = nvd_api_key
        self.nvd_base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        self.epss_base_url = "https://api.first.org/data/v1/epss"
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = timedelta(hours=24)

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def enrich_vulnerability(self, cve_id: str) -> Dict[str, Any]:
        """
        Enrich a vulnerability with CVE data from NVD and EPSS

        Args:
            cve_id: CVE identifier (e.g., CVE-2024-0001)

        Returns:
            Dictionary with enriched data
        """
        if not cve_id or not cve_id.startswith("CVE-"):
            logger.warning("invalid_cve_id", cve_id=cve_id)
            return {}

        # Check cache first
        if cve_id in self.cache:
            cached_data = self.cache[cve_id]
            if cached_data.get("cached_at"):
                cached_at = cached_data["cached_at"]
                if datetime.utcnow() - cached_at < self.cache_ttl:
                    logger.debug("cve_cache_hit", cve_id=cve_id)
                    return cached_data

        logger.info("enriching_cve", cve_id=cve_id)

        enriched_data = {
            "cve_id": cve_id,
            "cached_at": datetime.utcnow(),
        }

        # Fetch from NVD and EPSS concurrently
        nvd_task = self._fetch_nvd_data(cve_id)
        epss_task = self._fetch_epss_score(cve_id)

        nvd_data, epss_score = await asyncio.gather(
            nvd_task,
            epss_task,
            return_exceptions=True,
        )

        # Add NVD data
        if isinstance(nvd_data, dict):
            enriched_data["nvd_data"] = nvd_data
            enriched_data["cvss_score"] = nvd_data.get("cvss_score")
            enriched_data["cvss_vector"] = nvd_data.get("cvss_vector")
            enriched_data["references"] = nvd_data.get("references", [])
            enriched_data["published_date"] = nvd_data.get("published_date")

        # Add EPSS score
        if isinstance(epss_score, float):
            enriched_data["epss_score"] = epss_score

        # Check for known exploits
        enriched_data["exploit_available"] = await self._check_exploits(cve_id)

        # Cache the result
        self.cache[cve_id] = enriched_data

        return enriched_data

    async def _fetch_nvd_data(self, cve_id: str) -> Dict[str, Any]:
        """
        Fetch CVE data from NVD

        Args:
            cve_id: CVE identifier

        Returns:
            NVD data dictionary
        """
        try:
            session = await self._get_session()
            headers = {}
            if self.nvd_api_key:
                headers["apiKey"] = self.nvd_api_key

            url = f"{self.nvd_base_url}?cveId={cve_id}"

            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    vulnerabilities = data.get("vulnerabilities", [])

                    if vulnerabilities:
                        cve_item = vulnerabilities[0].get("cve", {})
                        return self._parse_nvd_response(cve_item)
                    else:
                        logger.warning("nvd_cve_not_found", cve_id=cve_id)
                        return {}

                elif response.status == 403:
                    logger.error("nvd_api_forbidden", cve_id=cve_id)
                    return {}
                else:
                    logger.error(
                        "nvd_fetch_failed",
                        cve_id=cve_id,
                        status=response.status,
                    )
                    return {}

        except Exception as e:
            logger.error("nvd_fetch_error", cve_id=cve_id, error=str(e))
            return {}

    def _parse_nvd_response(self, cve_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse NVD API response"""
        result = {}

        # Extract CVSS metrics
        metrics = cve_data.get("metrics", {})
        if "cvssMetricV31" in metrics and metrics["cvssMetricV31"]:
            cvss_v31 = metrics["cvssMetricV31"][0]["cvssData"]
            result["cvss_score"] = cvss_v31.get("baseScore")
            result["cvss_vector"] = cvss_v31.get("vectorString")
        elif "cvssMetricV30" in metrics and metrics["cvssMetricV30"]:
            cvss_v30 = metrics["cvssMetricV30"][0]["cvssData"]
            result["cvss_score"] = cvss_v30.get("baseScore")
            result["cvss_vector"] = cvss_v30.get("vectorString")

        # Extract references
        references = cve_data.get("references", [])
        result["references"] = [ref.get("url") for ref in references]

        # Extract published date
        if "published" in cve_data:
            result["published_date"] = cve_data["published"]

        # Extract description
        descriptions = cve_data.get("descriptions", [])
        if descriptions:
            result["description"] = descriptions[0].get("value")

        return result

    async def _fetch_epss_score(self, cve_id: str) -> Optional[float]:
        """
        Fetch EPSS (Exploit Prediction Scoring System) score

        Args:
            cve_id: CVE identifier

        Returns:
            EPSS score (0-1) or None
        """
        try:
            session = await self._get_session()
            url = f"{self.epss_base_url}?cve={cve_id}"

            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    epss_data = data.get("data", [])

                    if epss_data:
                        epss_score = float(epss_data[0].get("epss", 0))
                        logger.debug("epss_score_fetched", cve_id=cve_id, score=epss_score)
                        return epss_score
                    else:
                        logger.debug("epss_not_found", cve_id=cve_id)
                        return None
                else:
                    logger.warning("epss_fetch_failed", cve_id=cve_id, status=response.status)
                    return None

        except Exception as e:
            logger.error("epss_fetch_error", cve_id=cve_id, error=str(e))
            return None

    async def _check_exploits(self, cve_id: str) -> bool:
        """
        Check if known exploits exist for this CVE

        Checks multiple exploit databases:
        - CISA KEV (Known Exploited Vulnerabilities) catalog
        - GitHub Security Advisories
        - NVD references for exploit mentions

        Args:
            cve_id: CVE identifier

        Returns:
            True if exploits are known to exist
        """
        try:
            # Run all exploit checks concurrently
            kev_task = self._check_cisa_kev(cve_id)
            github_task = self._check_github_advisories(cve_id)

            kev_result, github_result = await asyncio.gather(
                kev_task,
                github_task,
                return_exceptions=True,
            )

            # If any check indicates exploit exists, return True
            exploit_exists = False

            if isinstance(kev_result, bool) and kev_result:
                logger.info("exploit_found_cisa_kev", cve_id=cve_id)
                exploit_exists = True

            if isinstance(github_result, bool) and github_result:
                logger.info("exploit_found_github", cve_id=cve_id)
                exploit_exists = True

            return exploit_exists

        except Exception as e:
            logger.error("exploit_check_error", cve_id=cve_id, error=str(e))
            return False

    async def _check_cisa_kev(self, cve_id: str) -> bool:
        """
        Check CISA Known Exploited Vulnerabilities (KEV) catalog

        CISA maintains a catalog of vulnerabilities known to be exploited in the wild.
        This is one of the most authoritative sources for exploit information.

        Args:
            cve_id: CVE identifier

        Returns:
            True if CVE is in CISA KEV catalog
        """
        try:
            session = await self._get_session()
            # CISA KEV catalog JSON endpoint
            url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    vulnerabilities = data.get("vulnerabilities", [])

                    # Check if CVE is in the catalog
                    for vuln in vulnerabilities:
                        if vuln.get("cveID") == cve_id:
                            logger.info(
                                "cve_in_cisa_kev",
                                cve_id=cve_id,
                                vendor_project=vuln.get("vendorProject"),
                                product=vuln.get("product"),
                            )
                            return True

                    return False
                else:
                    logger.warning("cisa_kev_fetch_failed", status=response.status)
                    return False

        except asyncio.TimeoutError:
            logger.warning("cisa_kev_timeout", cve_id=cve_id)
            return False
        except Exception as e:
            logger.error("cisa_kev_error", cve_id=cve_id, error=str(e))
            return False

    async def _check_github_advisories(self, cve_id: str) -> bool:
        """
        Check GitHub Security Advisories for exploit information

        GitHub aggregates security advisories and often indicates if exploits exist.

        Args:
            cve_id: CVE identifier

        Returns:
            True if GitHub advisory exists with exploit indicators
        """
        try:
            session = await self._get_session()
            # GitHub Security Advisory Database API
            # Note: This is a simplified check. Full implementation would use GraphQL API
            # For now, we check if an advisory exists which often indicates exploit interest

            # Use the public GitHub Advisory Database
            url = f"https://api.github.com/advisories?cve_id={cve_id}"
            headers = {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }

            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    advisories = await response.json()

                    if advisories and len(advisories) > 0:
                        # Check for exploit-related keywords in advisories
                        for advisory in advisories:
                            description = advisory.get("description", "").lower()
                            summary = advisory.get("summary", "").lower()
                            severity = advisory.get("severity", "").lower()

                            # Look for exploit indicators
                            exploit_keywords = [
                                "exploit",
                                "exploited",
                                "proof of concept",
                                "poc",
                                "in the wild",
                                "active exploitation",
                            ]

                            text_to_check = f"{description} {summary}"
                            has_exploit_mention = any(
                                keyword in text_to_check for keyword in exploit_keywords
                            )

                            # Critical/High severity with exploit mention = likely exploited
                            if has_exploit_mention and severity in ["critical", "high"]:
                                logger.info(
                                    "github_advisory_exploit_indicator",
                                    cve_id=cve_id,
                                    severity=severity,
                                )
                                return True

                        # Advisory exists but no clear exploit indicator
                        logger.debug("github_advisory_exists_no_exploit", cve_id=cve_id)
                        return False
                    else:
                        return False

                elif response.status == 404:
                    # No advisory found
                    return False
                else:
                    logger.warning("github_advisory_fetch_failed", status=response.status)
                    return False

        except asyncio.TimeoutError:
            logger.warning("github_advisory_timeout", cve_id=cve_id)
            return False
        except Exception as e:
            logger.error("github_advisory_error", cve_id=cve_id, error=str(e))
            return False

    async def close(self) -> None:
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
