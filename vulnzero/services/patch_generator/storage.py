"""Patch storage service for database operations."""
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from vulnzero.shared.models import (
    AuditAction,
    AuditLog,
    Patch,
    PatchStatus,
    Vulnerability,
    VulnerabilityStatus,
)


class PatchStorageService:
    """Service for storing and retrieving patches from database."""

    def __init__(self, db: Session):
        """
        Initialize storage service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def save_patch(self, patch: Patch, vulnerability: Vulnerability) -> Patch:
        """
        Save a patch to the database.

        Args:
            patch: Patch object to save
            vulnerability: Associated vulnerability

        Returns:
            Saved patch with ID
        """
        # Ensure vulnerability is in database
        if not vulnerability.id:
            self.db.add(vulnerability)
            self.db.flush()

        # Set vulnerability_id
        patch.vulnerability_id = vulnerability.id

        # Add patch to database
        self.db.add(patch)
        self.db.commit()
        self.db.refresh(patch)

        # Update vulnerability status
        vulnerability.status = VulnerabilityStatus.PATCH_GENERATED
        self.db.commit()

        # Create audit log
        self._create_audit_log(
            action=AuditAction.PATCH_GENERATED,
            resource_id=str(patch.id),
            description=f"Patch generated for {vulnerability.cve_id}",
            details={
                "patch_id": patch.patch_id,
                "cve_id": vulnerability.cve_id,
                "confidence_score": patch.confidence_score,
                "llm_model": patch.llm_model,
            },
        )

        return patch

    def get_patch_by_id(self, patch_id: str) -> Optional[Patch]:
        """
        Get patch by patch_id.

        Args:
            patch_id: Patch identifier

        Returns:
            Patch if found, None otherwise
        """
        return self.db.query(Patch).filter(Patch.patch_id == patch_id).first()

    def get_patches_for_vulnerability(self, vulnerability_id: int) -> List[Patch]:
        """
        Get all patches for a vulnerability.

        Args:
            vulnerability_id: Vulnerability ID

        Returns:
            List of patches
        """
        return (
            self.db.query(Patch)
            .filter(Patch.vulnerability_id == vulnerability_id)
            .order_by(Patch.created_at.desc())
            .all()
        )

    def get_patches_by_status(self, status: PatchStatus, limit: int = 100) -> List[Patch]:
        """
        Get patches by status.

        Args:
            status: Patch status
            limit: Maximum number of patches to return

        Returns:
            List of patches
        """
        return (
            self.db.query(Patch)
            .filter(Patch.status == status)
            .order_by(Patch.created_at.desc())
            .limit(limit)
            .all()
        )

    def approve_patch(self, patch_id: str, approver: str, notes: Optional[str] = None) -> Patch:
        """
        Approve a patch for deployment.

        Args:
            patch_id: Patch identifier
            approver: Who approved the patch
            notes: Optional approval notes

        Returns:
            Updated patch
        """
        patch = self.get_patch_by_id(patch_id)
        if not patch:
            raise ValueError(f"Patch {patch_id} not found")

        patch.status = PatchStatus.APPROVED
        patch.approved_by = approver
        patch.approved_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(patch)

        # Create audit log
        self._create_audit_log(
            action=AuditAction.PATCH_APPROVED,
            resource_id=str(patch.id),
            description=f"Patch {patch_id} approved by {approver}",
            details={"patch_id": patch_id, "approver": approver, "notes": notes},
        )

        return patch

    def reject_patch(self, patch_id: str, rejector: str, reason: str) -> Patch:
        """
        Reject a patch.

        Args:
            patch_id: Patch identifier
            rejector: Who rejected the patch
            reason: Rejection reason

        Returns:
            Updated patch
        """
        patch = self.get_patch_by_id(patch_id)
        if not patch:
            raise ValueError(f"Patch {patch_id} not found")

        patch.status = PatchStatus.REJECTED
        patch.rejection_reason = reason

        self.db.commit()
        self.db.refresh(patch)

        # Create audit log
        self._create_audit_log(
            action=AuditAction.PATCH_REJECTED,
            resource_id=str(patch.id),
            description=f"Patch {patch_id} rejected by {rejector}",
            details={"patch_id": patch_id, "rejector": rejector, "reason": reason},
        )

        return patch

    def update_patch_test_status(self, patch_id: str, test_status: str, test_report: dict) -> Patch:
        """
        Update patch test status.

        Args:
            patch_id: Patch identifier
            test_status: Test status (passed/failed)
            test_report: Test results

        Returns:
            Updated patch
        """
        patch = self.get_patch_by_id(patch_id)
        if not patch:
            raise ValueError(f"Patch {patch_id} not found")

        patch.test_status = test_status
        patch.test_report = str(test_report)
        patch.test_completed_at = datetime.utcnow()

        if test_status == "passed":
            patch.status = PatchStatus.TEST_PASSED
        else:
            patch.status = PatchStatus.TEST_FAILED

        self.db.commit()
        self.db.refresh(patch)

        return patch

    def get_vulnerability_by_cve(self, cve_id: str) -> Optional[Vulnerability]:
        """
        Get vulnerability by CVE ID.

        Args:
            cve_id: CVE identifier

        Returns:
            Vulnerability if found, None otherwise
        """
        return self.db.query(Vulnerability).filter(Vulnerability.cve_id == cve_id).first()

    def create_or_update_vulnerability(self, cve_data: dict) -> Vulnerability:
        """
        Create or update vulnerability from CVE data.

        Args:
            cve_data: Dictionary with CVE information

        Returns:
            Vulnerability object
        """
        # Check if vulnerability already exists
        vuln = self.get_vulnerability_by_cve(cve_data["cve_id"])

        if vuln:
            # Update existing
            vuln.description = cve_data.get("description", vuln.description)
            vuln.severity = cve_data.get("severity", vuln.severity)
            vuln.cvss_score = cve_data.get("cvss_score", vuln.cvss_score)
            vuln.cvss_vector = cve_data.get("cvss_vector", vuln.cvss_vector)
        else:
            # Create new
            vuln = Vulnerability(
                cve_id=cve_data["cve_id"],
                title=cve_data.get("title", f"Vulnerability {cve_data['cve_id']}"),
                description=cve_data.get("description", ""),
                severity=cve_data.get("severity", "unknown"),
                cvss_score=cve_data.get("cvss_score"),
                cvss_vector=cve_data.get("cvss_vector"),
                package_name=cve_data.get("package_name"),
                vulnerable_version=cve_data.get("vulnerable_version"),
                fixed_version=cve_data.get("fixed_version"),
                status=VulnerabilityStatus.NEW,
            )
            self.db.add(vuln)

        self.db.commit()
        self.db.refresh(vuln)

        return vuln

    def get_recent_patches(self, limit: int = 20) -> List[Patch]:
        """
        Get most recent patches.

        Args:
            limit: Maximum number of patches

        Returns:
            List of patches
        """
        return self.db.query(Patch).order_by(Patch.created_at.desc()).limit(limit).all()

    def get_statistics(self) -> dict:
        """
        Get patch statistics.

        Returns:
            Dictionary with statistics
        """
        total_patches = self.db.query(Patch).count()
        approved = self.db.query(Patch).filter(Patch.status == PatchStatus.APPROVED).count()
        rejected = self.db.query(Patch).filter(Patch.status == PatchStatus.REJECTED).count()
        pending = (
            self.db.query(Patch)
            .filter(Patch.status.in_([PatchStatus.GENERATED, PatchStatus.VALIDATING]))
            .count()
        )

        avg_confidence = self.db.query(Patch).with_entities(
            self.db.func.avg(Patch.confidence_score)
        ).scalar()

        return {
            "total_patches": total_patches,
            "approved": approved,
            "rejected": rejected,
            "pending_review": pending,
            "average_confidence": float(avg_confidence or 0.0),
            "approval_rate": approved / total_patches if total_patches > 0 else 0.0,
        }

    def _create_audit_log(
        self,
        action: AuditAction,
        resource_id: str,
        description: str,
        details: Optional[dict] = None,
    ) -> AuditLog:
        """Create audit log entry."""
        log = AuditLog(
            actor_type="system",
            actor_id="patch_generator",
            action=action,
            resource_type="patch",
            resource_id=resource_id,
            description=description,
            details=str(details) if details else None,
            success=True,
        )
        self.db.add(log)
        self.db.commit()
        return log
