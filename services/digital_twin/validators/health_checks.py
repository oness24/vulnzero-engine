"""
Health Check Validators

Validates system health after patch application.
"""

import logging
from typing import Dict, Any, List
import docker

logger = logging.getLogger(__name__)


class HealthCheckResult:
    """Result of a single health check"""
    def __init__(self, name: str, passed: bool, message: str, details: Dict[str, Any] = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
        }


def check_port_listening(container: docker.models.containers.Container, port: int) -> HealthCheckResult:
    """Check if a port is listening"""
    try:
        result = container.exec_run(f"ss -tuln | grep :{port}", demux=True)
        stdout, _ = result.output
        listening = result.exit_code == 0 and stdout

        return HealthCheckResult(
            name=f"port_{port}_listening",
            passed=bool(listening),
            message=f"Port {port} is {'listening' if listening else 'not listening'}",
            details={"port": port, "output": stdout.decode() if stdout else ""}
        )
    except Exception as e:
        return HealthCheckResult(
            name=f"port_{port}_listening",
            passed=False,
            message=f"Failed to check port: {e}",
        )


def check_service_running(container: docker.models.containers.Container, service_name: str) -> HealthCheckResult:
    """Check if a systemd service is running"""
    try:
        result = container.exec_run(f"systemctl is-active {service_name}", demux=True)
        stdout, _ = result.output
        running = result.exit_code == 0 and stdout and b"active" in stdout

        return HealthCheckResult(
            name=f"service_{service_name}_running",
            passed=bool(running),
            message=f"Service {service_name} is {'running' if running else 'not running'}",
            details={"service": service_name, "status": stdout.decode() if stdout else ""}
        )
    except Exception as e:
        return HealthCheckResult(
            name=f"service_{service_name}_running",
            passed=False,
            message=f"Failed to check service: {e}",
        )


def check_http_endpoint(container: docker.models.containers.Container, url: str) -> HealthCheckResult:
    """Check if HTTP endpoint responds"""
    try:
        # Install curl if not available
        container.exec_run("which curl || (apt-get update -qq && apt-get install -y curl)")
        
        result = container.exec_run(f"curl -f -s -o /dev/null -w '%{{http_code}}' {url}", demux=True)
        stdout, _ = result.output
        http_code = stdout.decode().strip() if stdout else "000"
        success = http_code.startswith("2")

        return HealthCheckResult(
            name=f"http_endpoint_{url}",
            passed=success,
            message=f"HTTP {url} returned {http_code}",
            details={"url": url, "http_code": http_code}
        )
    except Exception as e:
        return HealthCheckResult(
            name=f"http_endpoint_{url}",
            passed=False,
            message=f"Failed to check endpoint: {e}",
        )


def check_process_running(container: docker.models.containers.Container, process_name: str) -> HealthCheckResult:
    """Check if a process is running"""
    try:
        result = container.exec_run(f"pgrep -x {process_name}", demux=True)
        running = result.exit_code == 0

        return HealthCheckResult(
            name=f"process_{process_name}_running",
            passed=running,
            message=f"Process {process_name} is {'running' if running else 'not running'}",
            details={"process": process_name}
        )
    except Exception as e:
        return HealthCheckResult(
            name=f"process_{process_name}_running",
            passed=False,
            message=f"Failed to check process: {e}",
        )


def check_package_installed(container: docker.models.containers.Container, package_name: str) -> HealthCheckResult:
    """Check if a package is installed"""
    try:
        # Try dpkg first (Debian/Ubuntu)
        result = container.exec_run(f"dpkg -l {package_name}", demux=True)
        if result.exit_code == 0:
            installed = True
        else:
            # Try rpm (RHEL/CentOS)
            result = container.exec_run(f"rpm -q {package_name}", demux=True)
            installed = result.exit_code == 0

        return HealthCheckResult(
            name=f"package_{package_name}_installed",
            passed=installed,
            message=f"Package {package_name} is {'installed' if installed else 'not installed'}",
            details={"package": package_name}
        )
    except Exception as e:
        return HealthCheckResult(
            name=f"package_{package_name}_installed",
            passed=False,
            message=f"Failed to check package: {e}",
        )


def check_log_errors(container: docker.models.containers.Container, log_path: str) -> HealthCheckResult:
    """Check for errors in log file"""
    try:
        result = container.exec_run(f"grep -i error {log_path} | tail -10", demux=True)
        stdout, _ = result.output
        errors_found = result.exit_code == 0 and stdout

        return HealthCheckResult(
            name=f"log_errors_{log_path}",
            passed=not errors_found,
            message=f"{'Errors found' if errors_found else 'No errors'} in {log_path}",
            details={"log_path": log_path, "errors": stdout.decode() if stdout else ""}
        )
    except Exception as e:
        return HealthCheckResult(
            name=f"log_errors_{log_path}",
            passed=True,  # Assume OK if log doesn't exist
            message=f"Could not check log: {e}",
        )


def run_all_health_checks(container: docker.models.containers.Container, asset: Any) -> Dict[str, Any]:
    """
    Run all applicable health checks for an asset.

    Args:
        container: Docker container
        asset: Asset being tested

    Returns:
        Dictionary with health check results
    """
    results = []

    # Basic system checks
    results.append(check_process_running(container, "systemd"))
    
    # Common service checks (if applicable)
    common_services = ["ssh", "cron"]
    for service in common_services:
        results.append(check_service_running(container, service))

    # Check common ports
    common_ports = [22, 80, 443]
    for port in common_ports:
        results.append(check_port_listening(container, port))

    # Calculate overall status
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    success_rate = (passed / total * 100) if total > 0 else 0

    return {
        "overall_passed": success_rate >= 70,  # 70% threshold
        "success_rate": success_rate,
        "total_checks": total,
        "passed_checks": passed,
        "failed_checks": total - passed,
        "results": [r.to_dict() for r in results],
    }
