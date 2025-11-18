"""
VulnZero - Database Seed Script
Populates the database with sample data for development and testing
"""

import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session
from shared.config.database import SessionLocal, init_db
from shared.models import (
    Vulnerability,
    Asset,
    Patch,
    Deployment,
    AuditLog,
    RemediationJob,
)
from shared.models.vulnerability import VulnerabilityStatus, VulnerabilitySeverity
from shared.models.asset import AssetType, AssetStatus
from shared.models.patch import PatchType, PatchStatus
from shared.models.deployment import DeploymentStatus, DeploymentStrategy
from shared.models.audit_log import AuditAction, AuditResourceType
from shared.models.remediation_job import JobType, JobStatus, JobPriority


def seed_assets(db: Session) -> list[Asset]:
    """Create sample assets"""
    print("Creating sample assets...")

    assets = [
        Asset(
            asset_id=f"asset-{uuid.uuid4().hex[:8]}",
            name="Production Web Server 1",
            type=AssetType.SERVER,
            status=AssetStatus.ACTIVE,
            hostname="web-prod-01.vulnzero.local",
            ip_address="10.0.1.10",
            os_type="linux",
            os_name="Ubuntu",
            os_version="22.04",
            environment="production",
            criticality=9,
            is_public_facing=True,
            vulnerability_count=5,
            critical_vuln_count=1,
            high_vuln_count=2,
            last_scanned=datetime.utcnow() - timedelta(hours=2),
        ),
        Asset(
            asset_id=f"asset-{uuid.uuid4().hex[:8]}",
            name="Production Database Server",
            type=AssetType.DATABASE,
            status=AssetStatus.ACTIVE,
            hostname="db-prod-01.vulnzero.local",
            ip_address="10.0.2.10",
            os_type="linux",
            os_name="RHEL",
            os_version="9.1",
            environment="production",
            criticality=10,
            is_public_facing=False,
            vulnerability_count=3,
            critical_vuln_count=1,
            high_vuln_count=1,
            last_scanned=datetime.utcnow() - timedelta(hours=1),
        ),
        Asset(
            asset_id=f"asset-{uuid.uuid4().hex[:8]}",
            name="Staging Application Server",
            type=AssetType.SERVER,
            status=AssetStatus.ACTIVE,
            hostname="app-staging-01.vulnzero.local",
            ip_address="10.0.3.10",
            os_type="linux",
            os_name="Ubuntu",
            os_version="22.04",
            environment="staging",
            criticality=5,
            is_public_facing=True,
            vulnerability_count=8,
            critical_vuln_count=0,
            high_vuln_count=3,
            last_scanned=datetime.utcnow() - timedelta(hours=6),
        ),
        Asset(
            asset_id=f"asset-{uuid.uuid4().hex[:8]}",
            name="Development Container",
            type=AssetType.CONTAINER,
            status=AssetStatus.ACTIVE,
            hostname="dev-container-01",
            ip_address="172.17.0.2",
            container_image="node:18-alpine",
            container_id=uuid.uuid4().hex[:12],
            environment="development",
            criticality=3,
            is_public_facing=False,
            vulnerability_count=2,
            last_scanned=datetime.utcnow() - timedelta(days=1),
        ),
        Asset(
            asset_id=f"asset-{uuid.uuid4().hex[:8]}",
            name="AWS EC2 Instance",
            type=AssetType.CLOUD,
            status=AssetStatus.ACTIVE,
            hostname="aws-prod-web-02",
            ip_address="10.10.1.100",
            cloud_provider="AWS",
            cloud_region="us-east-1",
            cloud_instance_id="i-" + uuid.uuid4().hex[:17],
            os_type="linux",
            os_name="Amazon Linux",
            os_version="2",
            environment="production",
            criticality=8,
            is_public_facing=True,
            vulnerability_count=4,
            critical_vuln_count=1,
            high_vuln_count=1,
            last_scanned=datetime.utcnow() - timedelta(hours=4),
        ),
    ]

    db.add_all(assets)
    db.commit()
    print(f"✓ Created {len(assets)} assets")
    return assets


def seed_vulnerabilities(db: Session, assets: list[Asset]) -> list[Vulnerability]:
    """Create sample vulnerabilities"""
    print("Creating sample vulnerabilities...")

    vulnerabilities = [
        Vulnerability(
            cve_id="CVE-2024-1234",
            title="Critical Remote Code Execution in OpenSSL",
            description="A critical vulnerability allowing remote code execution through malformed SSL handshakes.",
            severity=VulnerabilitySeverity.CRITICAL,
            cvss_score=9.8,
            cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            epss_score=0.95,
            priority_score=95.0,
            status=VulnerabilityStatus.PATCH_GENERATED,
            discovered_at=datetime.utcnow() - timedelta(days=2),
            affected_package="openssl",
            affected_version="1.1.1k",
            fixed_version="1.1.1w",
            scanner_source="wazuh",
            scanner_id="WAZUH-2024-001",
            exploit_available=1,
            business_criticality=9,
            public_exposure=1,
        ),
        Vulnerability(
            cve_id="CVE-2024-5678",
            title="SQL Injection in PostgreSQL Extension",
            description="SQL injection vulnerability in postgresql contrib modules.",
            severity=VulnerabilitySeverity.HIGH,
            cvss_score=8.5,
            cvss_vector="CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H",
            epss_score=0.65,
            priority_score=82.0,
            status=VulnerabilityStatus.TESTING,
            discovered_at=datetime.utcnow() - timedelta(days=5),
            affected_package="postgresql-contrib",
            affected_version="14.5",
            fixed_version="14.11",
            scanner_source="qualys",
            scanner_id="QID-376942",
            exploit_available=0,
            business_criticality=10,
            public_exposure=0,
        ),
        Vulnerability(
            cve_id="CVE-2024-9012",
            title="Cross-Site Scripting (XSS) in Apache",
            description="Reflected XSS vulnerability in Apache HTTP Server mod_proxy module.",
            severity=VulnerabilitySeverity.MEDIUM,
            cvss_score=6.1,
            cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
            epss_score=0.15,
            priority_score=45.0,
            status=VulnerabilityStatus.NEW,
            discovered_at=datetime.utcnow() - timedelta(days=1),
            affected_package="apache2",
            affected_version="2.4.54",
            fixed_version="2.4.58",
            scanner_source="tenable",
            scanner_id="TNS-2024-001",
            exploit_available=0,
            business_criticality=7,
            public_exposure=1,
        ),
        Vulnerability(
            cve_id="CVE-2024-3456",
            title="Privilege Escalation in Sudo",
            description="Local privilege escalation vulnerability in sudo command.",
            severity=VulnerabilitySeverity.HIGH,
            cvss_score=7.8,
            cvss_vector="CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H",
            epss_score=0.42,
            priority_score=75.0,
            status=VulnerabilityStatus.DEPLOYING,
            discovered_at=datetime.utcnow() - timedelta(days=7),
            affected_package="sudo",
            affected_version="1.9.5",
            fixed_version="1.9.13",
            scanner_source="wazuh",
            scanner_id="WAZUH-2024-002",
            exploit_available=1,
            business_criticality=8,
            public_exposure=0,
        ),
        Vulnerability(
            cve_id="CVE-2024-7890",
            title="Denial of Service in Nginx",
            description="DoS vulnerability in nginx HTTP/2 implementation.",
            severity=VulnerabilitySeverity.MEDIUM,
            cvss_score=5.3,
            cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:L",
            epss_score=0.08,
            priority_score=35.0,
            status=VulnerabilityStatus.REMEDIATED,
            discovered_at=datetime.utcnow() - timedelta(days=14),
            remediated_at=datetime.utcnow() - timedelta(days=1),
            affected_package="nginx",
            affected_version="1.20.1",
            fixed_version="1.24.0",
            scanner_source="wazuh",
            scanner_id="WAZUH-2024-003",
            exploit_available=0,
            business_criticality=6,
            public_exposure=1,
        ),
    ]

    db.add_all(vulnerabilities)
    db.commit()
    print(f"✓ Created {len(vulnerabilities)} vulnerabilities")
    return vulnerabilities


def seed_patches(db: Session, vulnerabilities: list[Vulnerability]) -> list[Patch]:
    """Create sample patches"""
    print("Creating sample patches...")

    patches = [
        Patch(
            vulnerability_id=vulnerabilities[0].id,
            patch_type=PatchType.PACKAGE_UPDATE,
            status=PatchStatus.TEST_PASSED,
            title="Update OpenSSL to fix CVE-2024-1234",
            description="Automated patch to update OpenSSL package to patched version",
            patch_content="""#!/bin/bash
set -e

# VulnZero Auto-Generated Patch
# CVE: CVE-2024-1234
# Package: openssl
# Target Version: 1.1.1w

echo "Backing up current OpenSSL configuration..."
cp -r /etc/ssl /tmp/ssl_backup_$(date +%Y%m%d_%H%M%S)

echo "Updating OpenSSL package..."
apt-get update
apt-get install -y --only-upgrade openssl=1.1.1w-0ubuntu1

echo "Verifying installation..."
openssl version

echo "Patch applied successfully!"
exit 0
""",
            patch_language="bash",
            llm_provider="openai",
            llm_model="gpt-4",
            generation_time_seconds=5.2,
            confidence_score=92.5,
            validation_passed=True,
            test_status="passed",
            test_started_at=datetime.utcnow() - timedelta(hours=1),
            test_completed_at=datetime.utcnow() - timedelta(minutes=50),
            test_duration_seconds=185.3,
            deployment_method="ansible",
        ),
        Patch(
            vulnerability_id=vulnerabilities[1].id,
            patch_type=PatchType.PACKAGE_UPDATE,
            status=PatchStatus.TESTING,
            title="Upgrade PostgreSQL contrib modules",
            description="Update PostgreSQL contrib package to fix SQL injection",
            patch_content="""#!/bin/bash
set -e

echo "Stopping PostgreSQL service..."
systemctl stop postgresql

echo "Updating postgresql-contrib..."
dnf update -y postgresql-contrib

echo "Starting PostgreSQL service..."
systemctl start postgresql

echo "Verifying service..."
systemctl status postgresql

exit 0
""",
            patch_language="bash",
            llm_provider="anthropic",
            llm_model="claude-3-sonnet-20240229",
            generation_time_seconds=4.8,
            confidence_score=88.0,
            validation_passed=True,
            test_status="running",
            test_started_at=datetime.utcnow() - timedelta(minutes=5),
            deployment_method="ansible",
        ),
        Patch(
            vulnerability_id=vulnerabilities[3].id,
            patch_type=PatchType.PACKAGE_UPDATE,
            status=PatchStatus.DEPLOYED,
            title="Update sudo package",
            description="Patch sudo privilege escalation vulnerability",
            patch_content="""#!/bin/bash
set -e

echo "Updating sudo package..."
apt-get update
apt-get install -y --only-upgrade sudo

echo "Verifying sudo version..."
sudo --version

echo "Sudo updated successfully!"
exit 0
""",
            patch_language="bash",
            llm_provider="openai",
            llm_model="gpt-4",
            generation_time_seconds=3.5,
            confidence_score=95.0,
            validation_passed=True,
            test_status="passed",
            deployment_count=2,
            success_count=2,
            failure_count=0,
            approved_by="admin@vulnzero.com",
            approved_at=datetime.utcnow() - timedelta(hours=2),
        ),
    ]

    db.add_all(patches)
    db.commit()
    print(f"✓ Created {len(patches)} patches")
    return patches


def seed_deployments(
    db: Session, patches: list[Patch], assets: list[Asset]
) -> list[Deployment]:
    """Create sample deployments"""
    print("Creating sample deployments...")

    deployments = [
        Deployment(
            patch_id=patches[2].id,
            asset_id=assets[0].id,
            deployment_id=str(uuid.uuid4()),
            status=DeploymentStatus.SUCCESS,
            strategy=DeploymentStrategy.BLUE_GREEN,
            deployment_method="ansible",
            scheduled_at=datetime.utcnow() - timedelta(hours=3),
            started_at=datetime.utcnow() - timedelta(hours=2, minutes=55),
            completed_at=datetime.utcnow() - timedelta(hours=2, minutes=50),
            duration_seconds=300.5,
            pre_check_passed=True,
            post_validation_passed=True,
            executed_by="system",
        ),
        Deployment(
            patch_id=patches[2].id,
            asset_id=assets[1].id,
            deployment_id=str(uuid.uuid4()),
            status=DeploymentStatus.SUCCESS,
            strategy=DeploymentStrategy.ALL_AT_ONCE,
            deployment_method="ansible",
            scheduled_at=datetime.utcnow() - timedelta(hours=2, minutes=45),
            started_at=datetime.utcnow() - timedelta(hours=2, minutes=40),
            completed_at=datetime.utcnow() - timedelta(hours=2, minutes=35),
            duration_seconds=280.2,
            pre_check_passed=True,
            post_validation_passed=True,
            executed_by="system",
        ),
    ]

    db.add_all(deployments)
    db.commit()
    print(f"✓ Created {len(deployments)} deployments")
    return deployments


def seed_audit_logs(db: Session) -> list[AuditLog]:
    """Create sample audit logs"""
    print("Creating sample audit logs...")

    logs = [
        AuditLog(
            action=AuditAction.VULNERABILITY_DISCOVERED,
            timestamp=datetime.utcnow() - timedelta(days=2),
            actor_type="system",
            actor_id="scanner-wazuh-01",
            actor_name="Wazuh Scanner",
            resource_type=AuditResourceType.VULNERABILITY,
            resource_id="1",
            resource_name="CVE-2024-1234",
            description="Critical vulnerability discovered in OpenSSL",
            success=1,
            severity="critical",
            compliance_relevant=1,
        ),
        AuditLog(
            action=AuditAction.PATCH_GENERATED,
            timestamp=datetime.utcnow() - timedelta(hours=1),
            actor_type="system",
            actor_id="patch-generator-01",
            actor_name="AI Patch Generator",
            resource_type=AuditResourceType.PATCH,
            resource_id="1",
            resource_name="Update OpenSSL to fix CVE-2024-1234",
            description="AI-generated patch created successfully",
            success=1,
            severity="info",
        ),
        AuditLog(
            action=AuditAction.DEPLOYMENT_COMPLETED,
            timestamp=datetime.utcnow() - timedelta(hours=2, minutes=50),
            actor_type="system",
            actor_id="deployment-engine-01",
            actor_name="Deployment Engine",
            resource_type=AuditResourceType.DEPLOYMENT,
            resource_id="1",
            resource_name="Deploy sudo patch to web-prod-01",
            description="Deployment completed successfully",
            success=1,
            severity="info",
            compliance_relevant=1,
        ),
    ]

    db.add_all(logs)
    db.commit()
    print(f"✓ Created {len(logs)} audit logs")
    return logs


def seed_remediation_jobs(db: Session) -> list[RemediationJob]:
    """Create sample remediation jobs"""
    print("Creating sample remediation jobs...")

    jobs = [
        RemediationJob(
            job_id=str(uuid.uuid4()),
            job_type=JobType.VULNERABILITY_SCAN,
            job_name="Scheduled vulnerability scan",
            status=JobStatus.SUCCESS,
            priority=JobPriority.NORMAL,
            priority_score=5,
            created_at_timestamp=datetime.utcnow() - timedelta(hours=2),
            started_at=datetime.utcnow() - timedelta(hours=2, minutes=1),
            completed_at=datetime.utcnow() - timedelta(hours=1, minutes=45),
            duration_seconds=900.0,
            progress_percent=100,
            worker_id="celery-worker-01",
            queue_name="default",
        ),
        RemediationJob(
            job_id=str(uuid.uuid4()),
            job_type=JobType.PATCH_GENERATION,
            job_name="Generate patch for CVE-2024-1234",
            status=JobStatus.SUCCESS,
            priority=JobPriority.HIGH,
            priority_score=1,
            created_at_timestamp=datetime.utcnow() - timedelta(hours=1),
            started_at=datetime.utcnow() - timedelta(hours=1, minutes=5),
            completed_at=datetime.utcnow() - timedelta(minutes=55),
            duration_seconds=600.0,
            progress_percent=100,
            worker_id="celery-worker-02",
            queue_name="high-priority",
            vulnerability_id=1,
        ),
        RemediationJob(
            job_id=str(uuid.uuid4()),
            job_type=JobType.DIGITAL_TWIN_TEST,
            job_name="Test patch in digital twin",
            status=JobStatus.RUNNING,
            priority=JobPriority.NORMAL,
            priority_score=5,
            created_at_timestamp=datetime.utcnow() - timedelta(minutes=10),
            started_at=datetime.utcnow() - timedelta(minutes=5),
            progress_percent=65,
            progress_message="Running health checks...",
            worker_id="celery-worker-01",
            queue_name="testing",
            patch_id=2,
        ),
    ]

    db.add_all(jobs)
    db.commit()
    print(f"✓ Created {len(jobs)} remediation jobs")
    return jobs


def main():
    """Main seed function"""
    print("=" * 60)
    print("VulnZero Database Seed Script")
    print("=" * 60)
    print()

    # Initialize database schema
    print("Initializing database...")
    try:
        init_db()
        print("✓ Database initialized")
    except Exception as e:
        print(f"Note: {e}")

    # Create database session
    db = SessionLocal()

    try:
        # Seed data in order
        assets = seed_assets(db)
        vulnerabilities = seed_vulnerabilities(db, assets)
        patches = seed_patches(db, vulnerabilities)
        deployments = seed_deployments(db, patches, assets)
        audit_logs = seed_audit_logs(db)
        jobs = seed_remediation_jobs(db)

        print()
        print("=" * 60)
        print("✓ Database seeding completed successfully!")
        print("=" * 60)
        print()
        print("Summary:")
        print(f"  - Assets: {len(assets)}")
        print(f"  - Vulnerabilities: {len(vulnerabilities)}")
        print(f"  - Patches: {len(patches)}")
        print(f"  - Deployments: {len(deployments)}")
        print(f"  - Audit Logs: {len(audit_logs)}")
        print(f"  - Remediation Jobs: {len(jobs)}")
        print()

    except Exception as e:
        print(f"✗ Error seeding database: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
