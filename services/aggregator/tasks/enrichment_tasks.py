"""
Celery Tasks for Vulnerability Enrichment

Tasks for enriching vulnerabilities with external data (NVD, EPSS, Exploit-DB).
"""

from celery import shared_task
from datetime import datetime, timedelta
import logging
import asyncio

from services.aggregator.tasks.celery_app import celery_app
from services.aggregator.enrichment.enrichment_service import EnrichmentService
from services.aggregator.processors.normalizer import NormalizedVulnerability
from shared.config.database import SessionLocal
from shared.models import Vulnerability
from shared.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(name="services.aggregator.tasks.enrichment_tasks.enrich_new_vulnerabilities")
def enrich_new_vulnerabilities():
    """Enrich recently discovered vulnerabilities"""
    return asyncio.run(_enrich_new_vulnerabilities_async())


async def _enrich_new_vulnerabilities_async():
    """Async implementation of enrichment"""
    logger.info("Starting vulnerability enrichment")

    db = SessionLocal()
    try:
        # Get vulnerabilities discovered in last 7 days that haven't been enriched
        cutoff_date = datetime.utcnow() - timedelta(days=7)

        vulnerabilities = db.query(Vulnerability).filter(
            Vulnerability.discovered_at >= cutoff_date,
            Vulnerability.cve_id.like("CVE-%")  # Only CVEs
        ).limit(100).all()  # Limit to 100 per run to avoid API overload

        if not vulnerabilities:
            logger.info("No new vulnerabilities to enrich")
            return {"success": True, "count": 0}

        logger.info(f"Enriching {len(vulnerabilities)} vulnerabilities")

        # Convert to normalized format for enrichment
        normalized_vulns = []
        for vuln in vulnerabilities:
            normalized = NormalizedVulnerability(
                cve_id=vuln.cve_id,
                title=vuln.title,
                description=vuln.description,
                severity=vuln.severity,
                cvss_score=vuln.cvss_score,
                discovered_at=vuln.discovered_at,
                status=vuln.status,
                source_scanner="database",
            )
            normalized_vulns.append((vuln.id, normalized))

        # Enrich
        async with EnrichmentService(nvd_api_key=settings.nvd_api_key) as enrichment:
            enriched_count = 0

            for vuln_id, normalized_vuln in normalized_vulns:
                enrichment_data = await enrichment.enrich_vulnerability(normalized_vuln)

                if enrichment_data:
                    # Update vulnerability with enriched data
                    vuln = db.query(Vulnerability).filter(Vulnerability.id == vuln_id).first()
                    if vuln:
                        # Update CVSS if available
                        if enrichment_data.get("cvss_score") and not vuln.cvss_score:
                            vuln.cvss_score = enrichment_data["cvss_score"]

                        # Update EPSS
                        if enrichment_data.get("epss_score"):
                            vuln.epss_score = enrichment_data["epss_score"]

                        # Update exploit availability
                        vuln.exploit_available = enrichment_data.get("exploit_available", False)

                        vuln.updated_at = datetime.utcnow()
                        enriched_count += 1

            db.commit()
            logger.info(f"Enriched {enriched_count} vulnerabilities")

            return {"success": True, "count": enriched_count}

    except Exception as e:
        db.rollback()
        logger.error(f"Enrichment error: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="services.aggregator.tasks.enrichment_tasks.enrich_vulnerability")
def enrich_vulnerability(vulnerability_id: int):
    """Enrich a specific vulnerability"""
    return asyncio.run(_enrich_vulnerability_async(vulnerability_id))


async def _enrich_vulnerability_async(vulnerability_id: int):
    """Async implementation of single vulnerability enrichment"""
    logger.info(f"Enriching vulnerability {vulnerability_id}")

    db = SessionLocal()
    try:
        vuln = db.query(Vulnerability).filter(Vulnerability.id == vulnerability_id).first()

        if not vuln:
            return {"success": False, "error": "Vulnerability not found"}

        # Convert to normalized format
        normalized = NormalizedVulnerability(
            cve_id=vuln.cve_id,
            title=vuln.title,
            description=vuln.description,
            severity=vuln.severity,
            cvss_score=vuln.cvss_score,
            discovered_at=vuln.discovered_at,
            status=vuln.status,
            source_scanner="database",
        )

        # Enrich
        async with EnrichmentService(nvd_api_key=settings.nvd_api_key) as enrichment:
            enrichment_data = await enrichment.enrich_vulnerability(normalized)

            if enrichment_data:
                # Update vulnerability
                if enrichment_data.get("cvss_score"):
                    vuln.cvss_score = enrichment_data["cvss_score"]

                if enrichment_data.get("epss_score"):
                    vuln.epss_score = enrichment_data["epss_score"]

                vuln.exploit_available = enrichment_data.get("exploit_available", False)
                vuln.updated_at = datetime.utcnow()

                db.commit()
                logger.info(f"Enriched vulnerability {vulnerability_id}")

                return {"success": True, "enrichment_data": enrichment_data}
            else:
                return {"success": False, "error": "No enrichment data available"}

    except Exception as e:
        db.rollback()
        logger.error(f"Enrichment error for vulnerability {vulnerability_id}: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()
