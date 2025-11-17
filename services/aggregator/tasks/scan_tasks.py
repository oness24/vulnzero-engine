"""
Celery Tasks for Vulnerability Scanning

Periodic and on-demand vulnerability scanning tasks.
"""

from celery import shared_task
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import asyncio

from services.aggregator.tasks.celery_app import celery_app
from services.aggregator.scanners.wazuh_scanner import WazuhScanner
from services.aggregator.scanners.qualys_scanner import QualysScanner
from services.aggregator.scanners.tenable_scanner import TenableScanner
from services.aggregator.scanners.csv_scanner import CSVScanner
from services.aggregator.processors.normalizer import VulnerabilityNormalizer
from services.aggregator.processors.deduplicator import VulnerabilityDeduplicator
from shared.config.database import SessionLocal
from shared.models import Vulnerability, Asset, AuditLog, RemediationJob
from shared.models.audit_log import AuditAction, AuditResourceType
from shared.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(name="services.aggregator.tasks.scan_tasks.scan_wazuh")
def scan_wazuh():
    """Scan vulnerabilities from Wazuh"""
    return asyncio.run(_scan_wazuh_async())


async def _scan_wazuh_async():
    """Async implementation of Wazuh scan"""
    logger.info("Starting Wazuh vulnerability scan")

    config = {
        "api_url": settings.wazuh_api_url,
        "username": settings.wazuh_username,
        "password": settings.wazuh_password,
    }

    try:
        async with WazuhScanner(config) as scanner:
            # Perform scan
            scan_result = await scanner.scan()

            # Process results
            if scan_result.success:
                count = await _process_scan_results(scan_result)
                logger.info(f"Wazuh scan completed: {count} vulnerabilities processed")
                return {"success": True, "count": count, "scanner": "wazuh"}
            else:
                logger.error(f"Wazuh scan failed: {scan_result.errors}")
                return {"success": False, "errors": scan_result.errors}

    except Exception as e:
        logger.error(f"Wazuh scan error: {e}")
        return {"success": False, "error": str(e)}


@celery_app.task(name="services.aggregator.tasks.scan_tasks.scan_qualys")
def scan_qualys():
    """Scan vulnerabilities from Qualys"""
    return asyncio.run(_scan_qualys_async())


async def _scan_qualys_async():
    """Async implementation of Qualys scan"""
    logger.info("Starting Qualys vulnerability scan")

    config = {
        "api_url": settings.qualys_api_url,
        "username": settings.qualys_username,
        "password": settings.qualys_password,
    }

    try:
        async with QualysScanner(config) as scanner:
            scan_result = await scanner.scan()

            if scan_result.success:
                count = await _process_scan_results(scan_result)
                logger.info(f"Qualys scan completed: {count} vulnerabilities processed")
                return {"success": True, "count": count, "scanner": "qualys"}
            else:
                logger.error(f"Qualys scan failed: {scan_result.errors}")
                return {"success": False, "errors": scan_result.errors}

    except Exception as e:
        logger.error(f"Qualys scan error: {e}")
        return {"success": False, "error": str(e)}


@celery_app.task(name="services.aggregator.tasks.scan_tasks.scan_tenable")
def scan_tenable():
    """Scan vulnerabilities from Tenable.io"""
    return asyncio.run(_scan_tenable_async())


async def _scan_tenable_async():
    """Async implementation of Tenable scan"""
    logger.info("Starting Tenable vulnerability scan")

    config = {
        "access_key": settings.tenable_access_key,
        "secret_key": settings.tenable_secret_key,
    }

    try:
        async with TenableScanner(config) as scanner:
            scan_result = await scanner.scan()

            if scan_result.success:
                count = await _process_scan_results(scan_result)
                logger.info(f"Tenable scan completed: {count} vulnerabilities processed")
                return {"success": True, "count": count, "scanner": "tenable"}
            else:
                logger.error(f"Tenable scan failed: {scan_result.errors}")
                return {"success": False, "errors": scan_result.errors}

    except Exception as e:
        logger.error(f"Tenable scan error: {e}")
        return {"success": False, "error": str(e)}


@celery_app.task(name="services.aggregator.tasks.scan_tasks.import_csv")
def import_csv(file_path: str, file_type: str = "csv", mapping: dict = None):
    """Import vulnerabilities from CSV/JSON file"""
    return asyncio.run(_import_csv_async(file_path, file_type, mapping))


async def _import_csv_async(file_path: str, file_type: str, mapping: dict):
    """Async implementation of CSV import"""
    logger.info(f"Starting CSV/JSON import from {file_path}")

    config = {
        "file_path": file_path,
        "file_type": file_type,
        "mapping": mapping or {},
    }

    try:
        async with CSVScanner(config) as scanner:
            scan_result = await scanner.scan()

            if scan_result.success:
                count = await _process_scan_results(scan_result)
                logger.info(f"CSV/JSON import completed: {count} vulnerabilities processed")
                return {"success": True, "count": count, "scanner": "csv"}
            else:
                logger.error(f"CSV/JSON import failed: {scan_result.errors}")
                return {"success": False, "errors": scan_result.errors}

    except Exception as e:
        logger.error(f"CSV/JSON import error: {e}")
        return {"success": False, "error": str(e)}


async def _process_scan_results(scan_result) -> int:
    """
    Process scan results: normalize, deduplicate, and store in database.

    Returns:
        Number of vulnerabilities processed
    """
    db = SessionLocal()
    try:
        # Normalize vulnerabilities
        normalizer = VulnerabilityNormalizer()
        normalized_vulns = []

        for raw_vuln in scan_result.vulnerabilities:
            normalized = normalizer.normalize(raw_vuln)
            if normalized:
                normalized_vulns.append(normalized)

        logger.info(f"Normalized {len(normalized_vulns)} vulnerabilities")

        # Deduplicate
        deduplicator = VulnerabilityDeduplicator()
        deduplicated_vulns = deduplicator.deduplicate(normalized_vulns)

        logger.info(f"Deduplicated to {len(deduplicated_vulns)} unique vulnerabilities")

        # Store in database
        stored_count = 0
        for vuln in deduplicated_vulns:
            # Check if vulnerability already exists
            existing = db.query(Vulnerability).filter(
                Vulnerability.cve_id == vuln.cve_id,
                Vulnerability.asset_id == vuln.asset_identifier
            ).first()

            if existing:
                # Update existing vulnerability
                existing.updated_at = datetime.utcnow()
                # Update severity if higher
                if vuln.severity != existing.severity:
                    existing.severity = vuln.severity
                stored_count += 1
            else:
                # Create new vulnerability
                # First, find or create asset
                asset = await _find_or_create_asset(db, vuln.asset_identifier)

                new_vuln = Vulnerability(
                    cve_id=vuln.cve_id,
                    title=vuln.title,
                    description=vuln.description,
                    severity=vuln.severity,
                    cvss_score=vuln.cvss_score,
                    asset_id=asset.id if asset else None,
                    status="new",
                    discovered_at=vuln.discovered_at,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(new_vuln)
                stored_count += 1

        db.commit()
        logger.info(f"Stored {stored_count} vulnerabilities in database")

        # Create audit log
        audit_log = AuditLog(
            action=AuditAction.VULNERABILITY_DETECTED,
            timestamp=datetime.utcnow(),
            actor_type="system",
            actor_id="aggregator",
            actor_name="Vulnerability Aggregator",
            resource_type=AuditResourceType.SCAN,
            resource_id=scan_result.scan_id,
            description=f"Scan completed: {stored_count} vulnerabilities processed",
            success=1,
            severity="info",
        )
        db.add(audit_log)
        db.commit()

        return stored_count

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing scan results: {e}")
        raise
    finally:
        db.close()


async def _find_or_create_asset(db: Session, asset_identifier: str):
    """Find or create asset by identifier"""
    if not asset_identifier:
        return None

    # Try to find existing asset
    asset = db.query(Asset).filter(
        Asset.asset_id == asset_identifier
    ).first()

    if not asset:
        # Try by hostname or IP
        asset = db.query(Asset).filter(
            (Asset.hostname == asset_identifier) |
            (Asset.ip_address == asset_identifier)
        ).first()

    # Create if not found
    if not asset:
        asset = Asset(
            asset_id=asset_identifier,
            name=f"Auto-discovered: {asset_identifier}",
            type="server",  # Default type
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(asset)
        db.flush()  # Get ID

    return asset
