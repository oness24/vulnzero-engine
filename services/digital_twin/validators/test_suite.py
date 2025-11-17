"""
Test Suite

Customizable test suite for patch validation.
"""

import logging
from typing import List, Callable, Dict, Any
import docker

from services.digital_twin.validators.health_checks import HealthCheckResult

logger = logging.getLogger(__name__)


class TestSuite:
    """
    Customizable test suite for digital twin testing.
    """

    def __init__(self, asset_type: str = "generic"):
        """
        Initialize test suite.

        Args:
            asset_type: Type of asset (web_server, database, application, etc.)
        """
        self.asset_type = asset_type
        self.tests = []
        self.logger = logging.getLogger(__name__)

        # Load default tests for asset type
        self._load_default_tests()

    def add_test(self, test_func: Callable, name: str):
        """
        Add custom test function.

        Args:
            test_func: Test function that takes container and returns HealthCheckResult
            name: Test name
        """
        self.tests.append({"name": name, "func": test_func})
        self.logger.info(f"Added test: {name}")

    def execute(self, container: docker.models.containers.Container) -> Dict[str, Any]:
        """
        Execute all tests in the suite.

        Args:
            container: Docker container to test

        Returns:
            Test report dictionary
        """
        self.logger.info(f"Executing test suite for {self.asset_type}")
        
        results = []
        for test in self.tests:
            try:
                result = test["func"](container)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Test {test['name']} failed with exception: {e}")
                results.append(HealthCheckResult(
                    name=test["name"],
                    passed=False,
                    message=f"Test exception: {e}"
                ))

        # Calculate summary
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        
        return {
            "asset_type": self.asset_type,
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "all_passed": passed == total,
            "results": [r.to_dict() for r in results],
        }

    def _load_default_tests(self):
        """Load default tests based on asset type"""
        if self.asset_type == "web_server":
            self._load_web_server_tests()
        elif self.asset_type == "database":
            self._load_database_tests()
        else:
            self._load_generic_tests()

    def _load_generic_tests(self):
        """Load generic system tests"""
        from services.digital_twin.validators.health_checks import (
            check_process_running,
            check_service_running,
        )

        self.add_test(
            lambda c: check_process_running(c, "systemd"),
            "systemd_running"
        )
        self.add_test(
            lambda c: check_service_running(c, "cron"),
            "cron_service"
        )

    def _load_web_server_tests(self):
        """Load web server specific tests"""
        self._load_generic_tests()
        
        from services.digital_twin.validators.health_checks import (
            check_service_running,
            check_port_listening,
            check_http_endpoint,
        )

        self.add_test(
            lambda c: check_service_running(c, "nginx"),
            "nginx_service"
        )
        self.add_test(
            lambda c: check_port_listening(c, 80),
            "http_port"
        )
        self.add_test(
            lambda c: check_http_endpoint(c, "http://localhost"),
            "http_response"
        )

    def _load_database_tests(self):
        """Load database specific tests"""
        self._load_generic_tests()
        
        from services.digital_twin.validators.health_checks import (
            check_process_running,
            check_port_listening,
        )

        self.add_test(
            lambda c: check_process_running(c, "mysqld"),
            "mysql_process"
        )
        self.add_test(
            lambda c: check_port_listening(c, 3306),
            "mysql_port"
        )
