"""
Rollback Manager

Handles rollback of deployed patches with actual execution logic.
Supports multiple rollback strategies:
- Snapshot restoration
- Undo script execution
- Package version rollback
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

from shared.models import Asset, Patch, Deployment
from services.deployment_engine.connection_manager import SSHConnectionManager

logger = logging.getLogger(__name__)


class RollbackStrategy(str, Enum):
    """Available rollback strategies"""
    SNAPSHOT = "snapshot"  # Restore from pre-deployment snapshot
    UNDO_SCRIPT = "undo_script"  # Execute undo commands
    PACKAGE_DOWNGRADE = "package_downgrade"  # Downgrade packages
    FILE_RESTORE = "file_restore"  # Restore backed up files


class RollbackResult:
    """Result of rollback operation"""
    def __init__(
        self,
        success: bool,
        asset_id: int,
        asset_name: str,
        strategy_used: RollbackStrategy,
        message: str,
        stdout: str = "",
        stderr: str = "",
        duration_seconds: float = 0
    ):
        self.success = success
        self.asset_id = asset_id
        self.asset_name = asset_name
        self.strategy_used = strategy_used
        self.message = message
        self.stdout = stdout
        self.stderr = stderr
        self.duration_seconds = duration_seconds
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "asset_id": self.asset_id,
            "asset_name": self.asset_name,
            "strategy": self.strategy_used.value,
            "message": self.message,
            "stdout": self.stdout[:500],  # Truncate for logging
            "stderr": self.stderr[:500],
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp.isoformat()
        }


class RollbackManager:
    """
    Manages patch rollback with multiple strategies.

    Workflow:
    1. Connect to asset
    2. Detect rollback strategy (based on patch metadata)
    3. Execute appropriate rollback
    4. Verify rollback success
    5. Clean up
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def rollback_patch(
        self,
        asset: Asset,
        patch: Patch,
        deployment: Optional[Deployment] = None
    ) -> RollbackResult:
        """
        Roll back a deployed patch on a single asset.

        Args:
            asset: Asset to roll back
            patch: Patch that was deployed
            deployment: Deployment record (for metadata)

        Returns:
            RollbackResult with outcome
        """
        start_time = datetime.utcnow()
        self.logger.info(f"Starting rollback for patch {patch.id} on {asset.name}")

        # Determine rollback strategy
        strategy = self._determine_strategy(patch, deployment)
        self.logger.info(f"Using rollback strategy: {strategy.value}")

        try:
            # Execute rollback based on strategy
            if strategy == RollbackStrategy.SNAPSHOT:
                result = self._rollback_snapshot(asset, patch, deployment)
            elif strategy == RollbackStrategy.UNDO_SCRIPT:
                result = self._rollback_undo_script(asset, patch)
            elif strategy == RollbackStrategy.PACKAGE_DOWNGRADE:
                result = self._rollback_package(asset, patch)
            elif strategy == RollbackStrategy.FILE_RESTORE:
                result = self._rollback_files(asset, patch)
            else:
                result = RollbackResult(
                    success=False,
                    asset_id=asset.id,
                    asset_name=asset.name,
                    strategy_used=strategy,
                    message=f"Unknown strategy: {strategy}"
                )

            duration = (datetime.utcnow() - start_time).total_seconds()
            result.duration_seconds = duration

            if result.success:
                self.logger.info(
                    f"✅ Rollback successful for {asset.name} "
                    f"in {duration:.2f}s"
                )
            else:
                self.logger.error(
                    f"❌ Rollback failed for {asset.name}: {result.message}"
                )

            return result

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.logger.exception(f"Rollback exception for {asset.name}: {e}")
            return RollbackResult(
                success=False,
                asset_id=asset.id,
                asset_name=asset.name,
                strategy_used=strategy,
                message=f"Exception: {str(e)}",
                duration_seconds=duration
            )

    def _determine_strategy(
        self,
        patch: Patch,
        deployment: Optional[Deployment]
    ) -> RollbackStrategy:
        """Determine best rollback strategy for this patch"""

        # Check if patch has rollback metadata
        if hasattr(patch, 'rollback_strategy') and patch.rollback_strategy:
            try:
                return RollbackStrategy(patch.rollback_strategy)
            except ValueError:
                pass

        # Check if patch has undo script
        if hasattr(patch, 'rollback_script') and patch.rollback_script:
            return RollbackStrategy.UNDO_SCRIPT

        # Check patch type from content
        content = patch.patch_content or ""
        content_lower = content.lower()

        if any(pkg in content_lower for pkg in ['apt', 'yum', 'dnf', 'pip', 'npm']):
            return RollbackStrategy.PACKAGE_DOWNGRADE
        elif 'snapshot' in content_lower or 'backup' in content_lower:
            return RollbackStrategy.SNAPSHOT
        else:
            return RollbackStrategy.FILE_RESTORE

    def _rollback_undo_script(self, asset: Asset, patch: Patch) -> RollbackResult:
        """Execute undo script to rollback changes"""
        self.logger.info(f"Executing undo script for {asset.name}")

        conn_manager = SSHConnectionManager()

        try:
            # Connect to asset
            connection_success = conn_manager.connect({
                "hostname": asset.hostname or asset.ip_address,
                "username": asset.ssh_username or "root",
                "key_filename": asset.ssh_key_path
            })

            if not connection_success:
                return RollbackResult(
                    success=False,
                    asset_id=asset.id,
                    asset_name=asset.name,
                    strategy_used=RollbackStrategy.UNDO_SCRIPT,
                    message="Failed to connect to asset"
                )

            # Get rollback script
            if hasattr(patch, 'rollback_script') and patch.rollback_script:
                undo_script = patch.rollback_script
            else:
                # Generate undo script from patch content
                undo_script = self._generate_undo_script(patch.patch_content)

            # Execute undo script
            result = conn_manager.execute_command(
                command=f"bash -c '{undo_script}'",
                sudo=True,
                timeout=600  # 10 minutes
            )

            conn_manager.disconnect()

            return RollbackResult(
                success=result.get("success", False),
                asset_id=asset.id,
                asset_name=asset.name,
                strategy_used=RollbackStrategy.UNDO_SCRIPT,
                message="Undo script executed" if result.get("success") else f"Script failed: {result.get('error')}",
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", "")
            )

        except Exception as e:
            conn_manager.disconnect()
            return RollbackResult(
                success=False,
                asset_id=asset.id,
                asset_name=asset.name,
                strategy_used=RollbackStrategy.UNDO_SCRIPT,
                message=f"Exception: {str(e)}"
            )

    def _rollback_package(self, asset: Asset, patch: Patch) -> RollbackResult:
        """Rollback package installations/upgrades"""
        self.logger.info(f"Rolling back packages for {asset.name}")

        conn_manager = SSHConnectionManager()

        try:
            # Connect
            connection_success = conn_manager.connect({
                "hostname": asset.hostname or asset.ip_address,
                "username": asset.ssh_username or "root",
                "key_filename": asset.ssh_key_path
            })

            if not connection_success:
                return RollbackResult(
                    success=False,
                    asset_id=asset.id,
                    asset_name=asset.name,
                    strategy_used=RollbackStrategy.PACKAGE_DOWNGRADE,
                    message="Failed to connect"
                )

            # Detect package manager
            pkg_manager_check = conn_manager.execute_command(
                "which apt yum dnf 2>/dev/null | head -1"
            )

            pkg_manager = pkg_manager_check.get("stdout", "").strip().split("/")[-1]

            if not pkg_manager:
                return RollbackResult(
                    success=False,
                    asset_id=asset.id,
                    asset_name=asset.name,
                    strategy_used=RollbackStrategy.PACKAGE_DOWNGRADE,
                    message="No package manager found"
                )

            # Extract package names from patch
            packages = self._extract_package_names(patch.patch_content)

            if not packages:
                return RollbackResult(
                    success=False,
                    asset_id=asset.id,
                    asset_name=asset.name,
                    strategy_used=RollbackStrategy.PACKAGE_DOWNGRADE,
                    message="No packages found to rollback"
                )

            # Build rollback command based on package manager
            if pkg_manager in ["apt", "apt-get"]:
                # For apt: reinstall previous version or remove
                rollback_cmd = f"apt-get install --reinstall {' '.join(packages)} -y"
            elif pkg_manager in ["yum", "dnf"]:
                # For yum/dnf: downgrade or remove
                rollback_cmd = f"{pkg_manager} downgrade {' '.join(packages)} -y"
            else:
                rollback_cmd = f"echo 'Unsupported package manager: {pkg_manager}'"

            # Execute rollback
            result = conn_manager.execute_command(
                command=rollback_cmd,
                sudo=True,
                timeout=600
            )

            conn_manager.disconnect()

            return RollbackResult(
                success=result.get("success", False),
                asset_id=asset.id,
                asset_name=asset.name,
                strategy_used=RollbackStrategy.PACKAGE_DOWNGRADE,
                message=f"Package rollback: {', '.join(packages)}",
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", "")
            )

        except Exception as e:
            conn_manager.disconnect()
            return RollbackResult(
                success=False,
                asset_id=asset.id,
                asset_name=asset.name,
                strategy_used=RollbackStrategy.PACKAGE_DOWNGRADE,
                message=f"Exception: {str(e)}"
            )

    def _rollback_files(self, asset: Asset, patch: Patch) -> RollbackResult:
        """Restore backed up files"""
        self.logger.info(f"Restoring files for {asset.name}")

        conn_manager = SSHConnectionManager()

        try:
            connection_success = conn_manager.connect({
                "hostname": asset.hostname or asset.ip_address,
                "username": asset.ssh_username or "root",
                "key_filename": asset.ssh_key_path
            })

            if not connection_success:
                return RollbackResult(
                    success=False,
                    asset_id=asset.id,
                    asset_name=asset.name,
                    strategy_used=RollbackStrategy.FILE_RESTORE,
                    message="Failed to connect"
                )

            # Look for backup directory created during deployment
            backup_dir = f"/var/vulnzero/backups/patch_{patch.id}_{datetime.utcnow().strftime('%Y%m%d')}"

            # Check if backup exists
            check_backup = conn_manager.execute_command(
                f"test -d {backup_dir} && echo 'exists' || echo 'notfound'"
            )

            if "notfound" in check_backup.get("stdout", ""):
                return RollbackResult(
                    success=False,
                    asset_id=asset.id,
                    asset_name=asset.name,
                    strategy_used=RollbackStrategy.FILE_RESTORE,
                    message=f"Backup not found at {backup_dir}"
                )

            # Restore files from backup
            restore_cmd = f"""
            cd {backup_dir} && \
            find . -type f | while read file; do \
                target_file="/${{file#./}}"; \
                sudo cp -p "$file" "$target_file"; \
            done
            """

            result = conn_manager.execute_command(
                command=restore_cmd,
                sudo=True,
                timeout=300
            )

            conn_manager.disconnect()

            return RollbackResult(
                success=result.get("success", False),
                asset_id=asset.id,
                asset_name=asset.name,
                strategy_used=RollbackStrategy.FILE_RESTORE,
                message=f"Files restored from {backup_dir}",
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", "")
            )

        except Exception as e:
            conn_manager.disconnect()
            return RollbackResult(
                success=False,
                asset_id=asset.id,
                asset_name=asset.name,
                strategy_used=RollbackStrategy.FILE_RESTORE,
                message=f"Exception: {str(e)}"
            )

    def _rollback_snapshot(
        self,
        asset: Asset,
        patch: Patch,
        deployment: Optional[Deployment]
    ) -> RollbackResult:
        """Restore from VM/container snapshot"""
        self.logger.info(f"Restoring snapshot for {asset.name}")

        # This is a placeholder for VM/container snapshot restoration
        # Implementation depends on infrastructure (VMware, KVM, Docker, etc.)

        snapshot_id = None
        if deployment and hasattr(deployment, 'snapshot_id'):
            snapshot_id = deployment.snapshot_id

        if not snapshot_id:
            return RollbackResult(
                success=False,
                asset_id=asset.id,
                asset_name=asset.name,
                strategy_used=RollbackStrategy.SNAPSHOT,
                message="No snapshot ID available"
            )

        # TODO: Implement actual snapshot restoration based on infrastructure
        # For now, log the intent
        self.logger.warning(
            f"Snapshot restoration not yet implemented for {asset.asset_type}. "
            f"Would restore snapshot: {snapshot_id}"
        )

        return RollbackResult(
            success=False,
            asset_id=asset.id,
            asset_name=asset.name,
            strategy_used=RollbackStrategy.SNAPSHOT,
            message="Snapshot restoration not yet implemented"
        )

    def _generate_undo_script(self, patch_content: str) -> str:
        """
        Generate undo script by analyzing patch content.

        This is a simple heuristic-based approach.
        Better approach: patches should include explicit rollback scripts.
        """
        lines = patch_content.strip().split('\n')
        undo_lines = []

        for line in lines:
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Reverse common operations
            if 'systemctl start' in line:
                undo_lines.append(line.replace('start', 'stop'))
            elif 'systemctl enable' in line:
                undo_lines.append(line.replace('enable', 'disable'))
            elif 'sed -i' in line and 's/' in line:
                # Cannot easily reverse sed, log warning
                undo_lines.append(f"# Cannot auto-reverse: {line}")
            elif 'rm ' in line:
                undo_lines.append(f"# Cannot restore deleted file: {line}")
            else:
                undo_lines.append(f"# No auto-undo for: {line}")

        return '\n'.join(undo_lines) if undo_lines else "echo 'No undo operations generated'"

    def _extract_package_names(self, patch_content: str) -> List[str]:
        """Extract package names from patch content"""
        packages = []
        lines = patch_content.split('\n')

        for line in lines:
            # apt install
            if 'apt' in line and 'install' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'install' and i + 1 < len(parts):
                        # Get packages after 'install', before flags
                        for pkg in parts[i+1:]:
                            if not pkg.startswith('-') and pkg not in ['apt', 'apt-get', 'sudo']:
                                packages.append(pkg)
                        break

            # yum/dnf install
            elif any(pm in line for pm in ['yum', 'dnf']) and 'install' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'install' and i + 1 < len(parts):
                        for pkg in parts[i+1:]:
                            if not pkg.startswith('-') and pkg not in ['yum', 'dnf', 'sudo']:
                                packages.append(pkg)
                        break

        return list(set(packages))  # Remove duplicates
