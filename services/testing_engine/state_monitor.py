"""
System state monitoring for tracking changes during patch testing
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from docker.models.containers import Container
import json
import structlog

from services.testing_engine.container_manager import ContainerManager

logger = structlog.get_logger()


class SystemStateMonitor:
    """
    Captures and compares system state before/after patch application
    """

    def __init__(self, container_manager: ContainerManager):
        self.container_manager = container_manager

    def capture_state(
        self,
        container: Container,
        packages: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Capture current system state

        Args:
            container: Docker container
            packages: Optional list of specific packages to check

        Returns:
            Dictionary with system state
        """
        logger.info("capturing_system_state", container_id=container.id)

        state = {
            "timestamp": datetime.utcnow().isoformat(),
            "packages": self._capture_package_state(container, packages),
            "services": self._capture_service_state(container),
            "files": self._capture_file_state(container),
            "network": self._capture_network_state(container),
            "processes": self._capture_process_state(container),
            "system_info": self._capture_system_info(container),
        }

        logger.info("system_state_captured", container_id=container.id)
        return state

    def _capture_package_state(
        self,
        container: Container,
        packages: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """Capture installed package versions"""
        package_state = {}

        # Detect package manager
        pkg_manager = self._detect_package_manager(container)

        if pkg_manager == "apt":
            if packages:
                for pkg in packages:
                    result = self.container_manager.execute_command(
                        container,
                        f"dpkg-query -W -f='${{Version}}' {pkg} 2>/dev/null || echo 'not-installed'",
                    )
                    if result["success"]:
                        package_state[pkg] = result["stdout"].strip()
            else:
                # Get all installed packages
                result = self.container_manager.execute_command(
                    container,
                    "dpkg-query -W -f='${Package}=${Version}\n'",
                )
                if result["success"]:
                    for line in result["stdout"].strip().split('\n'):
                        if '=' in line:
                            pkg, version = line.split('=', 1)
                            package_state[pkg] = version

        elif pkg_manager in ["yum", "dnf"]:
            if packages:
                for pkg in packages:
                    result = self.container_manager.execute_command(
                        container,
                        f"rpm -q --queryformat '%{{VERSION}}-%{{RELEASE}}' {pkg} 2>/dev/null || echo 'not-installed'",
                    )
                    if result["success"]:
                        package_state[pkg] = result["stdout"].strip()
            else:
                result = self.container_manager.execute_command(
                    container,
                    "rpm -qa --queryformat '%{NAME}=%{VERSION}-%{RELEASE}\n'",
                )
                if result["success"]:
                    for line in result["stdout"].strip().split('\n'):
                        if '=' in line:
                            pkg, version = line.split('=', 1)
                            package_state[pkg] = version

        elif pkg_manager == "zypper":
            if packages:
                for pkg in packages:
                    result = self.container_manager.execute_command(
                        container,
                        f"rpm -q --queryformat '%{{VERSION}}-%{{RELEASE}}' {pkg} 2>/dev/null || echo 'not-installed'",
                    )
                    if result["success"]:
                        package_state[pkg] = result["stdout"].strip()

        return package_state

    def _capture_service_state(self, container: Container) -> Dict[str, str]:
        """Capture running services state"""
        services = {}

        # Try systemctl first
        result = self.container_manager.execute_command(
            container,
            "systemctl list-units --type=service --state=running --no-pager --no-legend 2>/dev/null || echo ''",
        )

        if result["success"] and result["stdout"].strip():
            for line in result["stdout"].strip().split('\n'):
                parts = line.split()
                if parts:
                    service_name = parts[0].replace('.service', '')
                    services[service_name] = "running"
        else:
            # Fallback to service command
            result = self.container_manager.execute_command(
                container,
                "service --status-all 2>/dev/null || echo ''",
            )
            if result["success"]:
                for line in result["stdout"].strip().split('\n'):
                    if '[+]' in line or '[ + ]' in line:
                        parts = line.split()
                        if len(parts) > 3:
                            services[parts[-1]] = "running"

        return services

    def _capture_file_state(self, container: Container) -> Dict[str, Any]:
        """Capture important file states"""
        files_to_check = [
            "/etc/passwd",
            "/etc/group",
            "/etc/hosts",
            "/etc/resolv.conf",
        ]

        file_state = {}

        for filepath in files_to_check:
            result = self.container_manager.execute_command(
                container,
                f"stat -c '%s %Y' {filepath} 2>/dev/null || echo 'not-found'",
            )

            if result["success"] and result["stdout"].strip() != "not-found":
                parts = result["stdout"].strip().split()
                if len(parts) == 2:
                    file_state[filepath] = {
                        "size": parts[0],
                        "mtime": parts[1],
                    }

        return file_state

    def _capture_network_state(self, container: Container) -> Dict[str, Any]:
        """Capture network configuration"""
        network_state = {}

        # Get network interfaces
        result = self.container_manager.execute_command(
            container,
            "ip -o addr show 2>/dev/null || echo ''",
        )

        if result["success"] and result["stdout"].strip():
            interfaces = {}
            for line in result["stdout"].strip().split('\n'):
                parts = line.split()
                if len(parts) >= 4:
                    iface = parts[1]
                    if iface not in interfaces:
                        interfaces[iface] = []
                    if len(parts) >= 4:
                        interfaces[iface].append(parts[3])

            network_state["interfaces"] = interfaces

        # Get listening ports
        result = self.container_manager.execute_command(
            container,
            "ss -tuln 2>/dev/null | grep LISTEN || netstat -tuln 2>/dev/null | grep LISTEN || echo ''",
        )

        if result["success"] and result["stdout"].strip():
            listening_ports = []
            for line in result["stdout"].strip().split('\n'):
                if 'LISTEN' in line:
                    listening_ports.append(line.strip())

            network_state["listening_ports"] = listening_ports

        return network_state

    def _capture_process_state(self, container: Container) -> List[str]:
        """Capture running processes"""
        result = self.container_manager.execute_command(
            container,
            "ps aux --no-headers 2>/dev/null || ps aux 2>/dev/null || echo ''",
        )

        if result["success"] and result["stdout"].strip():
            return [line.strip() for line in result["stdout"].strip().split('\n')[:50]]  # Limit to 50

        return []

    def _capture_system_info(self, container: Container) -> Dict[str, str]:
        """Capture system information"""
        info = {}

        # OS information
        result = self.container_manager.execute_command(
            container,
            "cat /etc/os-release 2>/dev/null || echo ''",
        )

        if result["success"] and result["stdout"].strip():
            for line in result["stdout"].strip().split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    info[key] = value.strip('"')

        # Kernel version
        result = self.container_manager.execute_command(
            container,
            "uname -r 2>/dev/null || echo ''",
        )
        if result["success"]:
            info["kernel"] = result["stdout"].strip()

        # Memory info
        result = self.container_manager.execute_command(
            container,
            "free -m 2>/dev/null | grep Mem || echo ''",
        )
        if result["success"] and result["stdout"].strip():
            parts = result["stdout"].strip().split()
            if len(parts) >= 2:
                info["memory_total_mb"] = parts[1]

        return info

    def _detect_package_manager(self, container: Container) -> str:
        """Detect which package manager is available"""
        # Check for apt
        result = self.container_manager.execute_command(
            container,
            "command -v apt-get >/dev/null 2>&1 && echo 'apt' || echo ''",
        )
        if result["success"] and result["stdout"].strip() == "apt":
            return "apt"

        # Check for dnf
        result = self.container_manager.execute_command(
            container,
            "command -v dnf >/dev/null 2>&1 && echo 'dnf' || echo ''",
        )
        if result["success"] and result["stdout"].strip() == "dnf":
            return "dnf"

        # Check for yum
        result = self.container_manager.execute_command(
            container,
            "command -v yum >/dev/null 2>&1 && echo 'yum' || echo ''",
        )
        if result["success"] and result["stdout"].strip() == "yum":
            return "yum"

        # Check for zypper
        result = self.container_manager.execute_command(
            container,
            "command -v zypper >/dev/null 2>&1 && echo 'zypper' || echo ''",
        )
        if result["success"] and result["stdout"].strip() == "zypper":
            return "zypper"

        return "unknown"

    def compare_states(
        self,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Compare two system states and identify changes

        Args:
            before_state: State before patch
            after_state: State after patch

        Returns:
            Dictionary with differences
        """
        logger.info("comparing_system_states")

        differences = {
            "packages_changed": self._compare_packages(
                before_state.get("packages", {}),
                after_state.get("packages", {}),
            ),
            "services_changed": self._compare_services(
                before_state.get("services", {}),
                after_state.get("services", {}),
            ),
            "files_changed": self._compare_files(
                before_state.get("files", {}),
                after_state.get("files", {}),
            ),
            "network_changed": self._compare_network(
                before_state.get("network", {}),
                after_state.get("network", {}),
            ),
            "has_changes": False,
        }

        # Determine if there are any changes
        differences["has_changes"] = any([
            differences["packages_changed"]["added"],
            differences["packages_changed"]["removed"],
            differences["packages_changed"]["updated"],
            differences["services_changed"]["started"],
            differences["services_changed"]["stopped"],
            differences["files_changed"]["modified"],
        ])

        logger.info(
            "state_comparison_complete",
            has_changes=differences["has_changes"],
            packages_updated=len(differences["packages_changed"]["updated"]),
        )

        return differences

    def _compare_packages(
        self,
        before: Dict[str, str],
        after: Dict[str, str],
    ) -> Dict[str, List[Dict[str, str]]]:
        """Compare package states"""
        added = []
        removed = []
        updated = []

        # Find added packages
        for pkg, version in after.items():
            if pkg not in before:
                added.append({"package": pkg, "version": version})

        # Find removed and updated packages
        for pkg, before_version in before.items():
            if pkg not in after:
                removed.append({"package": pkg, "version": before_version})
            elif after[pkg] != before_version:
                updated.append({
                    "package": pkg,
                    "before_version": before_version,
                    "after_version": after[pkg],
                })

        return {
            "added": added,
            "removed": removed,
            "updated": updated,
        }

    def _compare_services(
        self,
        before: Dict[str, str],
        after: Dict[str, str],
    ) -> Dict[str, List[str]]:
        """Compare service states"""
        started = []
        stopped = []

        # Find started services
        for service in after:
            if service not in before:
                started.append(service)

        # Find stopped services
        for service in before:
            if service not in after:
                stopped.append(service)

        return {
            "started": started,
            "stopped": stopped,
        }

    def _compare_files(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any],
    ) -> Dict[str, List[str]]:
        """Compare file states"""
        modified = []

        for filepath, before_info in before.items():
            if filepath in after:
                after_info = after[filepath]
                if before_info != after_info:
                    modified.append(filepath)

        return {"modified": modified}

    def _compare_network(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any],
    ) -> Dict[str, bool]:
        """Compare network states"""
        interfaces_changed = before.get("interfaces") != after.get("interfaces")
        ports_changed = before.get("listening_ports") != after.get("listening_ports")

        return {
            "interfaces_changed": interfaces_changed,
            "ports_changed": ports_changed,
        }

    def generate_state_report(
        self,
        state: Dict[str, Any],
        differences: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a human-readable state report

        Args:
            state: System state
            differences: Optional state differences

        Returns:
            Formatted report string
        """
        report_lines = [
            "=" * 60,
            "SYSTEM STATE REPORT",
            "=" * 60,
            f"Timestamp: {state.get('timestamp', 'N/A')}",
            "",
        ]

        # System info
        if "system_info" in state:
            report_lines.append("System Information:")
            for key, value in state["system_info"].items():
                report_lines.append(f"  {key}: {value}")
            report_lines.append("")

        # Packages
        if "packages" in state:
            report_lines.append(f"Installed Packages: {len(state['packages'])}")
            report_lines.append("")

        # Services
        if "services" in state:
            report_lines.append(f"Running Services: {len(state['services'])}")
            for service in list(state["services"].keys())[:10]:  # Top 10
                report_lines.append(f"  - {service}")
            report_lines.append("")

        # Differences if provided
        if differences:
            report_lines.append("=" * 60)
            report_lines.append("CHANGES DETECTED")
            report_lines.append("=" * 60)

            pkg_changes = differences.get("packages_changed", {})
            if pkg_changes.get("updated"):
                report_lines.append("Updated Packages:")
                for pkg in pkg_changes["updated"]:
                    report_lines.append(
                        f"  {pkg['package']}: {pkg['before_version']} -> {pkg['after_version']}"
                    )
                report_lines.append("")

            if pkg_changes.get("added"):
                report_lines.append("Added Packages:")
                for pkg in pkg_changes["added"]:
                    report_lines.append(f"  {pkg['package']} ({pkg['version']})")
                report_lines.append("")

            svc_changes = differences.get("services_changed", {})
            if svc_changes.get("started"):
                report_lines.append("Started Services:")
                for svc in svc_changes["started"]:
                    report_lines.append(f"  - {svc}")
                report_lines.append("")

            if svc_changes.get("stopped"):
                report_lines.append("Stopped Services:")
                for svc in svc_changes["stopped"]:
                    report_lines.append(f"  - {svc}")
                report_lines.append("")

        report_lines.append("=" * 60)

        return "\n".join(report_lines)
