"""
Backup Manager

Creates backups before patch deployment to enable reliable rollbacks.
Supports file backups, package snapshots, and system state capture.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from shared.models import Asset, Patch
from services.deployment_engine.connection_manager import SSHConnectionManager

logger = logging.getLogger(__name__)


class BackupType(str, Enum):
    """Types of backups"""
    FILES = "files"  # Backup affected files
    PACKAGES = "packages"  # Snapshot package versions
    SYSTEM_STATE = "system_state"  # Full system state
    CONFIGURATION = "configuration"  # Config files only


class BackupResult:
    """Result of backup operation"""
    def __init__(
        self,
        success: bool,
        backup_id: str,
        backup_path: str,
        backup_type: BackupType,
        size_bytes: int = 0,
        files_count: int = 0,
        message: str = "",
        duration_seconds: float = 0
    ):
        self.success = success
        self.backup_id = backup_id
        self.backup_path = backup_path
        self.backup_type = backup_type
        self.size_bytes = size_bytes
        self.files_count = files_count
        self.message = message
        self.duration_seconds = duration_seconds
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "backup_id": self.backup_id,
            "backup_path": self.backup_path,
            "backup_type": self.backup_type.value,
            "size_bytes": self.size_bytes,
            "size_mb": round(self.size_bytes / 1024 / 1024, 2),
            "files_count": self.files_count,
            "message": self.message,
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp.isoformat()
        }


class BackupManager:
    """
    Manages pre-deployment backups.

    Creates backups before patch deployment to enable safe rollbacks.
    Supports intelligent backup based on patch type.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.backup_base_dir = "/var/vulnzero/backups"

    def create_backup(
        self,
        asset: Asset,
        patch: Patch,
        backup_type: Optional[BackupType] = None
    ) -> BackupResult:
        """
        Create pre-deployment backup.

        Args:
            asset: Asset to backup
            patch: Patch being deployed (used to determine what to backup)
            backup_type: Override automatic backup type detection

        Returns:
            BackupResult with backup details
        """
        start_time = datetime.utcnow()
        backup_id = f"patch_{patch.id}_{asset.id}_{int(start_time.timestamp())}"

        self.logger.info(
            f"Creating backup for asset {asset.name} "
            f"before patch {patch.id} deployment"
        )

        try:
            # Determine backup type
            if not backup_type:
                backup_type = self._determine_backup_type(patch)

            self.logger.info(f"Using backup type: {backup_type.value}")

            # Execute appropriate backup strategy
            if backup_type == BackupType.FILES:
                result = self._backup_files(asset, patch, backup_id)
            elif backup_type == BackupType.PACKAGES:
                result = self._backup_packages(asset, patch, backup_id)
            elif backup_type == BackupType.CONFIGURATION:
                result = self._backup_configuration(asset, patch, backup_id)
            elif backup_type == BackupType.SYSTEM_STATE:
                result = self._backup_system_state(asset, patch, backup_id)
            else:
                result = BackupResult(
                    success=False,
                    backup_id=backup_id,
                    backup_path="",
                    backup_type=backup_type,
                    message=f"Unknown backup type: {backup_type}"
                )

            duration = (datetime.utcnow() - start_time).total_seconds()
            result.duration_seconds = duration

            if result.success:
                self.logger.info(
                    f"✅ Backup created: {result.backup_id} "
                    f"({result.size_bytes / 1024 / 1024:.2f} MB, "
                    f"{result.files_count} files) in {duration:.2f}s"
                )
            else:
                self.logger.error(
                    f"❌ Backup failed: {result.message}"
                )

            return result

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.logger.exception(f"Backup exception: {e}")
            return BackupResult(
                success=False,
                backup_id=backup_id,
                backup_path="",
                backup_type=backup_type or BackupType.FILES,
                message=f"Exception: {str(e)}",
                duration_seconds=duration
            )

    def _determine_backup_type(self, patch: Patch) -> BackupType:
        """Determine appropriate backup type based on patch content"""
        content = patch.patch_content or ""
        content_lower = content.lower()

        # Package installations/upgrades
        if any(pkg in content_lower for pkg in ['apt install', 'yum install', 'dnf install', 'pip install']):
            return BackupType.PACKAGES

        # Config file changes
        if any(cfg in content_lower for cfg in ['/etc/', 'nginx.conf', 'apache', '.conf', 'config']):
            return BackupType.CONFIGURATION

        # System-level changes
        if any(sys in content_lower for sys in ['systemctl', 'service ', 'kernel', 'grub']):
            return BackupType.SYSTEM_STATE

        # Default to file backup
        return BackupType.FILES

    def _backup_files(
        self,
        asset: Asset,
        patch: Patch,
        backup_id: str
    ) -> BackupResult:
        """Backup specific files that will be modified"""
        self.logger.info(f"Creating file backup for {asset.name}")

        conn_manager = SSHConnectionManager()

        try:
            # Connect
            connected = conn_manager.connect({
                "hostname": asset.hostname or asset.ip_address,
                "username": asset.ssh_username or "root",
                "key_filename": asset.ssh_key_path
            })

            if not connected:
                return BackupResult(
                    success=False,
                    backup_id=backup_id,
                    backup_path="",
                    backup_type=BackupType.FILES,
                    message="Failed to connect to asset"
                )

            # Detect files to backup from patch content
            files_to_backup = self._extract_file_paths(patch.patch_content)

            if not files_to_backup:
                # If no specific files detected, backup common config directories
                files_to_backup = ["/etc/"]

            backup_path = f"{self.backup_base_dir}/{backup_id}"

            # Create backup directory
            create_dir_result = conn_manager.execute_command(
                f"sudo mkdir -p {backup_path}",
                sudo=True
            )

            if not create_dir_result.get("success"):
                return BackupResult(
                    success=False,
                    backup_id=backup_id,
                    backup_path=backup_path,
                    backup_type=BackupType.FILES,
                    message=f"Failed to create backup directory: {create_dir_result.get('error')}"
                )

            # Backup each file/directory
            backup_commands = []
            for file_path in files_to_backup:
                # Use rsync or cp with archive mode to preserve permissions
                backup_commands.append(
                    f"sudo rsync -a {file_path} {backup_path}/ 2>/dev/null || "
                    f"sudo cp -rp {file_path} {backup_path}/ 2>/dev/null || true"
                )

            # Execute all backup commands
            backup_script = " && ".join(backup_commands)
            backup_result = conn_manager.execute_command(
                backup_script,
                sudo=True,
                timeout=600
            )

            # Get backup size and file count
            size_result = conn_manager.execute_command(
                f"sudo du -sb {backup_path} | cut -f1"
            )
            size_bytes = int(size_result.get("stdout", "0").strip() or 0)

            count_result = conn_manager.execute_command(
                f"sudo find {backup_path} -type f | wc -l"
            )
            files_count = int(count_result.get("stdout", "0").strip() or 0)

            # Create backup metadata file
            metadata = f"""# Backup Metadata
BACKUP_ID={backup_id}
PATCH_ID={patch.id}
ASSET_ID={asset.id}
ASSET_NAME={asset.name}
BACKUP_TYPE=files
TIMESTAMP={datetime.utcnow().isoformat()}
FILES_BACKED_UP={','.join(files_to_backup)}
SIZE_BYTES={size_bytes}
FILES_COUNT={files_count}
"""
            conn_manager.execute_command(
                f"echo '{metadata}' | sudo tee {backup_path}/BACKUP_METADATA.txt > /dev/null"
            )

            conn_manager.disconnect()

            return BackupResult(
                success=True,
                backup_id=backup_id,
                backup_path=backup_path,
                backup_type=BackupType.FILES,
                size_bytes=size_bytes,
                files_count=files_count,
                message=f"Backed up {files_count} files from {len(files_to_backup)} locations"
            )

        except Exception as e:
            conn_manager.disconnect()
            return BackupResult(
                success=False,
                backup_id=backup_id,
                backup_path="",
                backup_type=BackupType.FILES,
                message=f"Exception: {str(e)}"
            )

    def _backup_packages(
        self,
        asset: Asset,
        patch: Patch,
        backup_id: str
    ) -> BackupResult:
        """Create package version snapshot"""
        self.logger.info(f"Creating package snapshot for {asset.name}")

        conn_manager = SSHConnectionManager()

        try:
            connected = conn_manager.connect({
                "hostname": asset.hostname or asset.ip_address,
                "username": asset.ssh_username or "root",
                "key_filename": asset.ssh_key_path
            })

            if not connected:
                return BackupResult(
                    success=False,
                    backup_id=backup_id,
                    backup_path="",
                    backup_type=BackupType.PACKAGES,
                    message="Failed to connect"
                )

            backup_path = f"{self.backup_base_dir}/{backup_id}"

            # Create backup directory
            conn_manager.execute_command(f"sudo mkdir -p {backup_path}", sudo=True)

            # Detect package manager and create snapshot
            pkg_manager_result = conn_manager.execute_command(
                "which apt dpkg rpm yum dnf 2>/dev/null | head -1"
            )
            pkg_manager = pkg_manager_result.get("stdout", "").strip().split("/")[-1]

            snapshot_file = f"{backup_path}/packages_snapshot.txt"

            if pkg_manager in ["apt", "dpkg"]:
                # Debian/Ubuntu: dpkg package list
                snapshot_cmd = f"sudo dpkg -l > {snapshot_file}"
            elif pkg_manager in ["rpm", "yum", "dnf"]:
                # RedHat/CentOS: rpm package list
                snapshot_cmd = f"sudo rpm -qa --qf '%{{NAME}}-%{{VERSION}}-%{{RELEASE}}.%{{ARCH}}\\n' > {snapshot_file}"
            else:
                return BackupResult(
                    success=False,
                    backup_id=backup_id,
                    backup_path=backup_path,
                    backup_type=BackupType.PACKAGES,
                    message=f"Unsupported package manager: {pkg_manager}"
                )

            # Create package snapshot
            result = conn_manager.execute_command(snapshot_cmd, sudo=True)

            # Get package count
            count_result = conn_manager.execute_command(f"wc -l < {snapshot_file}")
            package_count = int(count_result.get("stdout", "0").strip() or 0)

            # Get file size
            size_result = conn_manager.execute_command(f"stat -f%z {snapshot_file} 2>/dev/null || stat -c%s {snapshot_file}")
            size_bytes = int(size_result.get("stdout", "0").strip() or 0)

            conn_manager.disconnect()

            return BackupResult(
                success=result.get("success", False),
                backup_id=backup_id,
                backup_path=backup_path,
                backup_type=BackupType.PACKAGES,
                size_bytes=size_bytes,
                files_count=package_count,
                message=f"Snapshot of {package_count} packages using {pkg_manager}"
            )

        except Exception as e:
            conn_manager.disconnect()
            return BackupResult(
                success=False,
                backup_id=backup_id,
                backup_path="",
                backup_type=BackupType.PACKAGES,
                message=f"Exception: {str(e)}"
            )

    def _backup_configuration(
        self,
        asset: Asset,
        patch: Patch,
        backup_id: str
    ) -> BackupResult:
        """Backup system configuration files"""
        self.logger.info(f"Creating configuration backup for {asset.name}")

        # Use file backup but focus on /etc directory
        config_dirs = [
            "/etc",
            "/usr/local/etc",
            "/opt/*/conf",
            "/opt/*/config"
        ]

        # Temporarily modify patch content to focus on config dirs
        original_content = patch.patch_content
        patch.patch_content = "\n".join(config_dirs)

        result = self._backup_files(asset, patch, backup_id)
        result.backup_type = BackupType.CONFIGURATION

        # Restore original content
        patch.patch_content = original_content

        return result

    def _backup_system_state(
        self,
        asset: Asset,
        patch: Patch,
        backup_id: str
    ) -> BackupResult:
        """Create comprehensive system state backup"""
        self.logger.info(f"Creating system state backup for {asset.name}")

        # Combine packages and critical configs
        package_result = self._backup_packages(asset, patch, f"{backup_id}_packages")
        config_result = self._backup_configuration(asset, patch, f"{backup_id}_config")

        # Return combined result
        total_size = package_result.size_bytes + config_result.size_bytes
        total_files = package_result.files_count + config_result.files_count

        success = package_result.success and config_result.success

        return BackupResult(
            success=success,
            backup_id=backup_id,
            backup_path=f"{self.backup_base_dir}/{backup_id}",
            backup_type=BackupType.SYSTEM_STATE,
            size_bytes=total_size,
            files_count=total_files,
            message=f"System state: packages + configuration ({total_files} items)"
        )

    def _extract_file_paths(self, patch_content: str) -> List[str]:
        """Extract file paths from patch content"""
        import re

        paths = set()
        lines = patch_content.split('\n')

        for line in lines:
            # Look for common file path patterns
            # /etc/something, /usr/local/something, etc.
            matches = re.findall(r'(/etc/[^\s]+|/usr/[^\s]+|/opt/[^\s]+|/var/[^\s]+)', line)
            for match in matches:
                # Clean up quotes and other chars
                clean_path = match.strip('"\'();,')
                if clean_path:
                    paths.add(clean_path)

        return list(paths)
