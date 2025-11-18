"""
Celery tasks for vulnerability aggregation
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
import structlog

from shared.celery_app import app
from shared.models.database import AsyncSessionLocal
from shared.models.models import Vulnerability, Asset
from shared.config import settings
from sqlalchemy import select

from services.aggregator.scanners import WazuhAdapter, MockAdapter
from services.aggregator.normalizer import VulnerabilityNormalizer, DataDeduplicator
from services.aggregator.enrichment import CVEEnricher
from services.aggregator.prioritizer import VulnerabilityPrioritizer

logger = structlog.get_logger()


@app.task(name="services.aggregator.tasks.scan_all_sources", bind=True)
def scan_all_sources(self) -> Dict[str, Any]:
    """
    Scan all configured vulnerability sources

    This is the main task that orchestrates the scanning process.
    Scheduled to run periodically via Celery Beat.

    Returns:
        Dictionary with scan results
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_scan_all_sources_async())


async def _scan_all_sources_async() -> Dict[str, Any]:
    """Async implementation of scan_all_sources"""
    logger.info("starting_vulnerability_scan")

    results = {
        "started_at": datetime.utcnow().isoformat(),
        "sources": {},
        "total_vulnerabilities": 0,
        "new_vulnerabilities": 0,
        "updated_vulnerabilities": 0,
    }

    # Configure scanners
    scanners = []

    # Use mock scanner in development/testing
    if settings.mock_scanner_apis:
        scanners.append(MockAdapter({"num_vulnerabilities": 20}))
    else:
        # Add real scanners
        if settings.wazuh_api_url:
            scanners.append(WazuhAdapter({
                "api_url": settings.wazuh_api_url,
                "username": settings.wazuh_api_user,
                "password": settings.wazuh_api_password,
                "verify_ssl": settings.wazuh_verify_ssl,
            }))

    # Scan each source
    all_raw_vulnerabilities = []

    for scanner in scanners:
        try:
            source_name = scanner.scanner_name
            logger.info("scanning_source", source=source_name)

            # Fetch vulnerabilities
            raw_vulns = await scanner.fetch_vulnerabilities(
                since=datetime.utcnow() - timedelta(days=30),
            )

            all_raw_vulnerabilities.extend(raw_vulns)

            results["sources"][source_name] = {
                "status": "success",
                "vulnerabilities_found": len(raw_vulns),
            }

        except Exception as e:
            logger.error("scanner_failed", scanner=scanner.scanner_name, error=str(e))
            results["sources"][scanner.scanner_name] = {
                "status": "failed",
                "error": str(e),
            }

    # Deduplicate vulnerabilities
    deduplicator = DataDeduplicator()
    deduplicated_vulns = deduplicator.deduplicate_vulnerabilities(all_raw_vulnerabilities)

    results["total_vulnerabilities"] = len(deduplicated_vulns)

    # Process and store vulnerabilities
    async with AsyncSessionLocal() as session:
        normalizer = VulnerabilityNormalizer()
        prioritizer = VulnerabilityPrioritizer()

        async with CVEEnricher(nvd_api_key=settings.nvd_api_key) as enricher:
            for raw_vuln in deduplicated_vulns:
                try:
                    # Enrich with CVE data
                    enriched_data = None
                    if raw_vuln.cve_id:
                        enriched_data = await enricher.enrich_vulnerability(raw_vuln.cve_id)

                    # Normalize to database model
                    vulnerability = normalizer.normalize_vulnerability(raw_vuln, enriched_data)

                    # Check if vulnerability already exists
                    query = select(Vulnerability).where(
                        Vulnerability.cve_id == vulnerability.cve_id
                    )
                    result = await session.execute(query)
                    existing = result.scalar_one_or_none()

                    if existing:
                        # Update existing vulnerability
                        existing.cvss_score = vulnerability.cvss_score or existing.cvss_score
                        existing.epss_score = vulnerability.epss_score or existing.epss_score
                        existing.exploit_available = vulnerability.exploit_available
                        existing.nvd_data = vulnerability.nvd_data or existing.nvd_data
                        results["updated_vulnerabilities"] += 1
                        vuln_to_prioritize = existing
                    else:
                        # Add new vulnerability
                        session.add(vulnerability)
                        results["new_vulnerabilities"] += 1
                        vuln_to_prioritize = vulnerability

                    # Calculate priority score
                    priority_score = prioritizer.calculate_priority_score(vuln_to_prioritize)
                    vuln_to_prioritize.priority_score = priority_score

                except Exception as e:
                    logger.error(
                        "vulnerability_processing_failed",
                        cve_id=raw_vuln.cve_id,
                        error=str(e),
                    )
                    continue

        await session.commit()

    results["completed_at"] = datetime.utcnow().isoformat()
    logger.info("vulnerability_scan_completed", results=results)

    return results


@app.task(name="services.aggregator.tasks.enrich_vulnerability", bind=True)
def enrich_vulnerability(self, vulnerability_id: int) -> Dict[str, Any]:
    """
    Enrich a specific vulnerability with CVE data

    Args:
        vulnerability_id: ID of the vulnerability to enrich

    Returns:
        Enrichment results
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_enrich_vulnerability_async(vulnerability_id))


async def _enrich_vulnerability_async(vulnerability_id: int) -> Dict[str, Any]:
    """Async implementation of enrich_vulnerability"""
    logger.info("enriching_vulnerability", vulnerability_id=vulnerability_id)

    async with AsyncSessionLocal() as session:
        # Fetch vulnerability
        query = select(Vulnerability).where(Vulnerability.id == vulnerability_id)
        result = await session.execute(query)
        vulnerability = result.scalar_one_or_none()

        if not vulnerability:
            logger.error("vulnerability_not_found", vulnerability_id=vulnerability_id)
            return {"status": "error", "message": "Vulnerability not found"}

        # Enrich with CVE data
        async with CVEEnricher(nvd_api_key=settings.nvd_api_key) as enricher:
            enriched_data = await enricher.enrich_vulnerability(vulnerability.cve_id)

            # Update vulnerability with enriched data
            if enriched_data:
                vulnerability.cvss_score = enriched_data.get("cvss_score") or vulnerability.cvss_score
                vulnerability.cvss_vector = enriched_data.get("cvss_vector") or vulnerability.cvss_vector
                vulnerability.epss_score = enriched_data.get("epss_score")
                vulnerability.exploit_available = enriched_data.get("exploit_available", False)
                vulnerability.nvd_data = enriched_data.get("nvd_data")

        # Recalculate priority
        prioritizer = VulnerabilityPrioritizer()
        vulnerability.priority_score = prioritizer.calculate_priority_score(vulnerability)

        await session.commit()

    logger.info("vulnerability_enriched", vulnerability_id=vulnerability_id)

    return {
        "status": "success",
        "vulnerability_id": vulnerability_id,
        "priority_score": vulnerability.priority_score,
    }


@app.task(name="services.aggregator.tasks.calculate_priorities", bind=True)
def calculate_priorities(self) -> Dict[str, Any]:
    """
    Recalculate priority scores for all vulnerabilities

    This task can be run periodically to update priorities as new data becomes available.

    Returns:
        Results dictionary
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_calculate_priorities_async())


async def _calculate_priorities_async() -> Dict[str, Any]:
    """Async implementation of calculate_priorities"""
    logger.info("recalculating_priorities")

    async with AsyncSessionLocal() as session:
        # Fetch all active vulnerabilities
        query = select(Vulnerability).where(
            Vulnerability.status.in_(["new", "analyzing", "patch_generated"])
        )
        result = await session.execute(query)
        vulnerabilities = result.scalars().all()

        prioritizer = VulnerabilityPrioritizer()
        updated_count = 0

        for vuln in vulnerabilities:
            old_priority = vuln.priority_score
            new_priority = prioritizer.calculate_priority_score(vuln)

            if abs(old_priority - new_priority) > 0.1:  # Only update if changed significantly
                vuln.priority_score = new_priority
                updated_count += 1

        await session.commit()

    logger.info("priorities_recalculated", total=len(vulnerabilities), updated=updated_count)

    return {
        "status": "success",
        "total_vulnerabilities": len(vulnerabilities),
        "updated_priorities": updated_count,
    }
