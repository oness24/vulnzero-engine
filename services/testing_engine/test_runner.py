"""
Test runner for comprehensive patch validation
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from docker.models.containers import Container
from services.testing_engine.container_manager import ContainerManager
from services.testing_engine.executor import PatchExecutor

logger = structlog.get_logger()


class TestRunner:
    """
    Orchestrates comprehensive testing of patches
    """

    def __init__(self, container_manager: ContainerManager):
        self.container_manager = container_manager
        self.executor = PatchExecutor(container_manager)

    def run_comprehensive_tests(
        self,
        container: Container,
        patch_script: str,
        rollback_script: str,
        validation_script: Optional[str] = None,
        target_package: Optional[str] = None,
        custom_tests: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Run comprehensive test suite on a patch

        Args:
            container: Docker container
            patch_script: Patch script to test
            rollback_script: Rollback script
            validation_script: Optional validation script
            target_package: Target package being patched
            custom_tests: Optional list of custom tests

        Returns:
            Comprehensive test results
        """
        logger.info("starting_comprehensive_tests", container_id=container.id)

        results = {
            "started_at": datetime.utcnow().isoformat(),
            "container_id": container.id,
            "overall_success": False,
            "tests_passed": 0,
            "tests_failed": 0,
            "tests": {},
        }

        # Test 1: Basic patch execution
        logger.info("running_basic_patch_test")
        basic_test = self.executor.execute_patch(
            container,
            patch_script,
            validation_script=validation_script,
            capture_state=True,
        )
        results["tests"]["basic_execution"] = basic_test

        if basic_test["success"]:
            results["tests_passed"] += 1
        else:
            results["tests_failed"] += 1
            # If basic test fails, skip remaining tests
            logger.warning("basic_patch_test_failed_skipping_remaining")
            results["completed_at"] = datetime.utcnow().isoformat()
            return results

        # Test 2: Idempotency test
        logger.info("running_idempotency_test")
        idempotency_test = self.executor.verify_patch_idempotency(
            container,
            patch_script,
        )
        results["tests"]["idempotency"] = idempotency_test

        if idempotency_test["success"] and idempotency_test.get("is_idempotent", False):
            results["tests_passed"] += 1
        else:
            results["tests_failed"] += 1

        # Test 3: Rollback test
        if rollback_script:
            logger.info("running_rollback_test")
            rollback_test = self.executor.test_rollback(
                container,
                patch_script,
                rollback_script,
                target_package=target_package,
            )
            results["tests"]["rollback"] = rollback_test

            if rollback_test["success"]:
                results["tests_passed"] += 1
            else:
                results["tests_failed"] += 1

        # Test 4: Custom tests
        if custom_tests:
            logger.info("running_custom_tests", count=len(custom_tests))
            custom_results = []

            for test in custom_tests:
                test_result = self.executor.execute_custom_test(
                    container,
                    test["script"],
                    test.get("name", "custom_test"),
                )
                custom_results.append(test_result)

                if test_result["success"]:
                    results["tests_passed"] += 1
                else:
                    results["tests_failed"] += 1

            results["tests"]["custom_tests"] = custom_results

        # Overall success
        results["overall_success"] = results["tests_failed"] == 0
        results["completed_at"] = datetime.utcnow().isoformat()

        logger.info(
            "comprehensive_tests_complete",
            overall_success=results["overall_success"],
            passed=results["tests_passed"],
            failed=results["tests_failed"],
        )

        return results

    def run_smoke_tests(
        self,
        container: Container,
        services_to_check: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run smoke tests to verify system health

        Args:
            container: Docker container
            services_to_check: Optional list of services to verify

        Returns:
            Smoke test results
        """
        logger.info("running_smoke_tests", container_id=container.id)

        results = {
            "started_at": datetime.utcnow().isoformat(),
            "success": True,
            "tests": {},
        }

        # Test 1: Basic connectivity
        connectivity_test = self.container_manager.execute_command(
            container,
            "ping -c 1 8.8.8.8 2>/dev/null || echo 'no_network'",
        )
        results["tests"]["connectivity"] = {
            "success": "no_network" not in connectivity_test["stdout"],
        }

        # Test 2: Package manager health
        pkg_manager_test = self.container_manager.execute_command(
            container,
            "apt-get --version 2>/dev/null || yum --version 2>/dev/null || dnf --version 2>/dev/null || zypper --version 2>/dev/null",
        )
        results["tests"]["package_manager"] = {
            "success": pkg_manager_test["success"],
        }

        # Test 3: Disk space
        disk_test = self.container_manager.execute_command(
            container,
            "df -h / | tail -n 1 | awk '{print $5}' | sed 's/%//'",
        )
        if disk_test["success"]:
            try:
                usage = int(disk_test["stdout"].strip())
                results["tests"]["disk_space"] = {
                    "success": usage < 90,
                    "usage_percent": usage,
                }
            except:
                results["tests"]["disk_space"] = {"success": False}

        # Test 4: Service checks
        if services_to_check:
            service_results = {}
            for service in services_to_check:
                svc_test = self.container_manager.execute_command(
                    container,
                    f"systemctl is-active {service} 2>/dev/null || service {service} status 2>/dev/null",
                )
                service_results[service] = {"success": svc_test["success"]}

            results["tests"]["services"] = service_results

        # Overall success
        results["success"] = all(
            test.get("success", False)
            for test in results["tests"].values()
            if isinstance(test, dict)
        )

        results["completed_at"] = datetime.utcnow().isoformat()

        logger.info("smoke_tests_complete", success=results["success"])

        return results

    def run_security_tests(
        self,
        container: Container,
    ) -> Dict[str, Any]:
        """
        Run security-focused tests

        Args:
            container: Docker container

        Returns:
            Security test results
        """
        logger.info("running_security_tests", container_id=container.id)

        results = {
            "started_at": datetime.utcnow().isoformat(),
            "success": True,
            "tests": {},
        }

        # Test 1: No unauthorized users
        user_test = self.container_manager.execute_command(
            container,
            "getent passwd | awk -F: '$3 == 0 {print $1}' | grep -v '^root$' || echo 'ok'",
        )
        results["tests"]["no_extra_root_users"] = {
            "success": "ok" in user_test["stdout"],
        }

        # Test 2: No world-writable files in critical paths
        writable_test = self.container_manager.execute_command(
            container,
            "find /etc /usr/bin /usr/sbin -type f -perm -002 2>/dev/null | head -n 1 || echo 'ok'",
        )
        results["tests"]["no_world_writable_files"] = {
            "success": "ok" in writable_test["stdout"],
        }

        # Test 3: SSH configuration (if exists)
        ssh_test = self.container_manager.execute_command(
            container,
            "if [ -f /etc/ssh/sshd_config ]; then grep -i '^PermitRootLogin' /etc/ssh/sshd_config | grep -i 'no' && echo 'secure' || echo 'insecure'; else echo 'not_installed'; fi",
        )
        if "not_installed" not in ssh_test["stdout"]:
            results["tests"]["ssh_root_login_disabled"] = {
                "success": "secure" in ssh_test["stdout"],
            }

        # Test 4: Firewall rules (basic check)
        firewall_test = self.container_manager.execute_command(
            container,
            "iptables -L 2>/dev/null | grep -i 'chain' || echo 'no_iptables'",
        )
        results["tests"]["firewall_configured"] = {
            "success": "no_iptables" not in firewall_test["stdout"],
            "optional": True,  # Firewall may not be needed in container
        }

        # Overall success (ignore optional tests)
        results["success"] = all(
            test.get("success", False)
            for test in results["tests"].values()
            if isinstance(test, dict) and not test.get("optional", False)
        )

        results["completed_at"] = datetime.utcnow().isoformat()

        logger.info("security_tests_complete", success=results["success"])

        return results

    def run_performance_tests(
        self,
        container: Container,
        patch_script: str,
    ) -> Dict[str, Any]:
        """
        Run performance tests to measure patch impact

        Args:
            container: Docker container
            patch_script: Patch script

        Returns:
            Performance test results
        """
        logger.info("running_performance_tests", container_id=container.id)

        results = {
            "started_at": datetime.utcnow().isoformat(),
            "execution_time_seconds": 0,
            "memory_impact": {},
        }

        # Measure execution time
        start_time = datetime.utcnow()

        patch_result = self.executor.execute_patch(
            container,
            patch_script,
            capture_state=False,
        )

        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()

        results["execution_time_seconds"] = execution_time
        results["patch_success"] = patch_result["success"]

        # Check memory usage after patch
        mem_test = self.container_manager.execute_command(
            container,
            "free -m | grep Mem | awk '{print $3, $2}'",
        )

        if mem_test["success"]:
            parts = mem_test["stdout"].strip().split()
            if len(parts) == 2:
                results["memory_impact"] = {
                    "used_mb": int(parts[0]),
                    "total_mb": int(parts[1]),
                    "usage_percent": round((int(parts[0]) / int(parts[1])) * 100, 2),
                }

        results["completed_at"] = datetime.utcnow().isoformat()

        logger.info(
            "performance_tests_complete",
            execution_time=execution_time,
        )

        return results

    def generate_test_summary(self, test_results: Dict[str, Any]) -> str:
        """
        Generate a human-readable test summary

        Args:
            test_results: Test results dictionary

        Returns:
            Formatted summary string
        """
        summary_lines = [
            "=" * 70,
            "PATCH TEST SUMMARY",
            "=" * 70,
            f"Container: {test_results.get('container_id', 'N/A')}",
            f"Started: {test_results.get('started_at', 'N/A')}",
            f"Completed: {test_results.get('completed_at', 'N/A')}",
            "",
            f"Overall Status: {'PASSED' if test_results.get('overall_success') else 'FAILED'}",
            f"Tests Passed: {test_results.get('tests_passed', 0)}",
            f"Tests Failed: {test_results.get('tests_failed', 0)}",
            "",
            "=" * 70,
            "TEST RESULTS",
            "=" * 70,
        ]

        tests = test_results.get("tests", {})

        # Basic execution
        if "basic_execution" in tests:
            basic = tests["basic_execution"]
            status = "PASS" if basic.get("success") else "FAIL"
            summary_lines.append(f"[{status}] Basic Patch Execution")

            if basic.get("state_changes", {}).get("has_changes"):
                changes = basic["state_changes"]
                pkg_changes = changes.get("packages_changed", {})
                if pkg_changes.get("updated"):
                    summary_lines.append(f"      Updated {len(pkg_changes['updated'])} package(s)")

        # Idempotency
        if "idempotency" in tests:
            idemp = tests["idempotency"]
            status = "PASS" if idemp.get("is_idempotent") else "FAIL"
            summary_lines.append(f"[{status}] Idempotency Test")

        # Rollback
        if "rollback" in tests:
            rollback = tests["rollback"]
            status = "PASS" if rollback.get("success") else "FAIL"
            summary_lines.append(f"[{status}] Rollback Test")

        # Custom tests
        if "custom_tests" in tests:
            summary_lines.append("")
            summary_lines.append("Custom Tests:")
            for test in tests["custom_tests"]:
                status = "PASS" if test.get("success") else "FAIL"
                summary_lines.append(f"  [{status}] {test.get('test_name', 'Unknown')}")

        summary_lines.append("=" * 70)

        return "\n".join(summary_lines)
