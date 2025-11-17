"""
Celery Tasks for Priority Calculation

Tasks for calculating and updating vulnerability priority scores.
"""

from celery import shared_task
from datetime import datetime
import logging

from services.aggregator.tasks.celery_app import celery_app
from services.aggregator.ml.priority_scorer import PriorityScorer
from services.aggregator.processors.normalizer import NormalizedVulnerability
from shared.config.database import SessionLocal
from shared.models import Vulnerability, Asset
from shared.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(name="services.aggregator.tasks.priority_tasks.recalculate_all_priorities")
def recalculate_all_priorities():
    """Recalculate priority scores for all active vulnerabilities"""
    logger.info("Starting priority recalculation for all vulnerabilities")

    db = SessionLocal()
    try:
        # Get all active vulnerabilities (not remediated)
        vulnerabilities = db.query(Vulnerability).filter(
            Vulnerability.status != "remediated"
        ).all()

        if not vulnerabilities:
            logger.info("No active vulnerabilities to prioritize")
            return {"success": True, "count": 0}

        logger.info(f"Recalculating priorities for {len(vulnerabilities)} vulnerabilities")

        scorer = PriorityScorer()
        updated_count = 0

        for vuln in vulnerabilities:
            try:
                # Get asset criticality
                asset_criticality = 3  # Default medium
                if vuln.asset_id:
                    asset = db.query(Asset).filter(Asset.id == vuln.asset_id).first()
                    if asset and asset.criticality:
                        asset_criticality = asset.criticality

                # Convert to normalized format for scoring
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

                # Prepare enrichment data
                enrichment_data = {
                    "cvss_score": vuln.cvss_score,
                    "epss_score": vuln.epss_score,
                    "exploit_available": vuln.exploit_available,
                }

                # Calculate priority
                priority_score = scorer.calculate_priority(
                    normalized,
                    enrichment_data,
                    asset_criticality
                )

                # Update vulnerability
                vuln.priority_score = int(priority_score)
                vuln.updated_at = datetime.utcnow()
                updated_count += 1

            except Exception as e:
                logger.error(f"Error calculating priority for vulnerability {vuln.id}: {e}")
                continue

        db.commit()
        logger.info(f"Updated priorities for {updated_count} vulnerabilities")

        return {"success": True, "count": updated_count}

    except Exception as e:
        db.rollback()
        logger.error(f"Priority recalculation error: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="services.aggregator.tasks.priority_tasks.calculate_vulnerability_priority")
def calculate_vulnerability_priority(vulnerability_id: int):
    """Calculate priority score for a specific vulnerability"""
    logger.info(f"Calculating priority for vulnerability {vulnerability_id}")

    db = SessionLocal()
    try:
        vuln = db.query(Vulnerability).filter(Vulnerability.id == vulnerability_id).first()

        if not vuln:
            return {"success": False, "error": "Vulnerability not found"}

        # Get asset criticality
        asset_criticality = 3
        if vuln.asset_id:
            asset = db.query(Asset).filter(Asset.id == vuln.asset_id).first()
            if asset and asset.criticality:
                asset_criticality = asset.criticality

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

        # Prepare enrichment data
        enrichment_data = {
            "cvss_score": vuln.cvss_score,
            "epss_score": vuln.epss_score,
            "exploit_available": vuln.exploit_available,
        }

        # Calculate priority
        scorer = PriorityScorer()
        priority_score = scorer.calculate_priority(
            normalized,
            enrichment_data,
            asset_criticality
        )

        # Get explanation
        explanation = scorer.get_priority_explanation(
            normalized,
            enrichment_data,
            asset_criticality
        )

        # Update vulnerability
        vuln.priority_score = int(priority_score)
        vuln.updated_at = datetime.utcnow()

        db.commit()
        logger.info(f"Updated priority for vulnerability {vulnerability_id}: {priority_score}")

        return {
            "success": True,
            "priority_score": priority_score,
            "explanation": explanation
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error calculating priority for vulnerability {vulnerability_id}: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()
