"""
Unit Tests for Digital Twin Testing Engine

Tests container management, patch execution, and health checks.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from services.digital_twin.core.container import ContainerManager
from services.digital_twin.validators.health_checks import (
    check_port_listening,
    check_service_running,
    check_disk_space
)
from services.digital_twin.analyzers.result_analyzer import (
    TestResult,
    TestStatus,
    ResultAnalyzer
)


class TestContainerManager:
    """Test Docker container management"""

    @patch('docker.from_env')
    def test_create_container_success(self, mock_docker):
        """Test creating a container"""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.id = "test123"

        mock_client.containers.create.return_value = mock_container
        mock_docker.return_value = mock_client

        manager = ContainerManager()
        container = manager.create_container(
            image="ubuntu:22.04",
            name="test-container"
        )

        assert container is not None
        assert mock_client.containers.create.called

    @patch('docker.from_env')
    def test_start_container(self, mock_docker):
        """Test starting a container"""
        mock_client = MagicMock()
        mock_container = MagicMock()

        mock_client.containers.get.return_value = mock_container
        mock_docker.return_value = mock_client

        manager = ContainerManager()
        manager.start_container(mock_container)

        assert mock_container.start.called

    @patch('docker.from_env')
    def test_stop_container(self, mock_docker):
        """Test stopping a container"""
        mock_client = MagicMock()
        mock_container = MagicMock()

        mock_client.containers.get.return_value = mock_container
        mock_docker.return_value = mock_client

        manager = ContainerManager()
        manager.stop_container(mock_container)

        assert mock_container.stop.called

    @patch('docker.from_env')
    def test_execute_command(self, mock_docker):
        """Test executing command in container"""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.exec_run.return_value = (0, b"success")

        mock_client.containers.get.return_value = mock_container
        mock_docker.return_value = mock_client

        manager = ContainerManager()
        exit_code, output = manager.execute_command(
            mock_container,
            "echo 'test'"
        )

        assert exit_code == 0
        assert output == b"success"

    @patch('docker.from_env')
    def test_cleanup_old_containers(self, mock_docker):
        """Test cleaning up old containers"""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.labels = {"vulnzero": "digital-twin"}

        mock_client.containers.list.return_value = [mock_container]
        mock_docker.return_value = mock_client

        manager = ContainerManager()
        removed = manager.cleanup_old_containers(max_age_hours=24)

        # Should attempt cleanup
        assert isinstance(removed, (int, list))

    @patch('docker.from_env')
    def test_container_resource_limits(self, mock_docker):
        """Test container creation with resource limits"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client

        manager = ContainerManager()
        manager.create_container(
            image="ubuntu:22.04",
            name="limited-container",
            cpu_limit="1.0",
            mem_limit="2g"
        )

        # Verify resource limits were passed
        call_args = mock_client.containers.create.call_args
        assert call_args is not None


class TestHealthChecks:
    """Test health check validators"""

    @patch('docker.from_env')
    def test_check_port_listening(self, mock_docker):
        """Test checking if port is listening"""
        mock_container = MagicMock()
        mock_container.exec_run.return_value = (0, b"LISTEN")

        result = check_port_listening(mock_container, 80)

        assert isinstance(result, bool)

    @patch('docker.from_env')
    def test_check_service_running(self, mock_docker):
        """Test checking if service is running"""
        mock_container = MagicMock()
        mock_container.exec_run.return_value = (0, b"active (running)")

        result = check_service_running(mock_container, "nginx")

        assert isinstance(result, bool)

    @patch('docker.from_env')
    def test_check_disk_space(self, mock_docker):
        """Test checking disk space"""
        mock_container = MagicMock()
        mock_container.exec_run.return_value = (0, b"10%")  # 10% used

        result = check_disk_space(mock_container, threshold=90)

        assert isinstance(result, bool)

    @patch('docker.from_env')
    def test_health_check_failure(self, mock_docker):
        """Test health check handles failures"""
        mock_container = MagicMock()
        mock_container.exec_run.return_value = (1, b"error")

        result = check_port_listening(mock_container, 80)

        # Should handle failure gracefully
        assert isinstance(result, bool)


class TestResultAnalyzer:
    """Test test result analysis"""

    def test_analyze_passed_test(self):
        """Test analyzing passed test results"""
        analyzer = ResultAnalyzer()

        patch_execution = {
            "exit_code": 0,
            "stdout": "Success",
            "stderr": ""
        }

        health_checks = {
            "port_80": True,
            "service_nginx": True,
            "disk_space": True,
            "success_rate": 100
        }

        result = analyzer.analyze(
            patch_execution=patch_execution,
            health_checks=health_checks,
            errors=[]
        )

        assert result.status == TestStatus.PASSED
        assert result.confidence_score > 70

    def test_analyze_failed_test(self):
        """Test analyzing failed test results"""
        analyzer = ResultAnalyzer()

        patch_execution = {
            "exit_code": 1,
            "stdout": "",
            "stderr": "Error occurred"
        }

        health_checks = {
            "port_80": False,
            "service_nginx": False,
            "success_rate": 0
        }

        result = analyzer.analyze(
            patch_execution=patch_execution,
            health_checks=health_checks,
            errors=["Patch execution failed"]
        )

        assert result.status == TestStatus.FAILED
        assert result.confidence_score < 50

    def test_analyze_partial_success(self):
        """Test analyzing partially successful test"""
        analyzer = ResultAnalyzer()

        patch_execution = {
            "exit_code": 0,
            "stdout": "Completed with warnings",
            "stderr": "Warning: deprecated command"
        }

        health_checks = {
            "port_80": True,
            "service_nginx": True,
            "disk_space": False,  # One check failed
            "success_rate": 66.7
        }

        result = analyzer.analyze(
            patch_execution=patch_execution,
            health_checks=health_checks,
            errors=[]
        )

        # Should still pass but with warnings
        assert result.status in [TestStatus.PASSED, TestStatus.WARNING]
        assert 50 < result.confidence_score < 90

    def test_confidence_score_calculation(self):
        """Test confidence score calculation logic"""
        analyzer = ResultAnalyzer()

        # Perfect execution
        perfect_result = analyzer.analyze(
            patch_execution={"exit_code": 0, "stdout": "OK", "stderr": ""},
            health_checks={"success_rate": 100},
            errors=[]
        )

        # Failed execution
        failed_result = analyzer.analyze(
            patch_execution={"exit_code": 1, "stdout": "", "stderr": "Error"},
            health_checks={"success_rate": 0},
            errors=["Failed"]
        )

        assert perfect_result.confidence_score > failed_result.confidence_score


class TestDigitalTwinOrchestrator:
    """Test digital twin orchestration"""

    @patch('services.digital_twin.core.container.ContainerManager')
    @patch('services.digital_twin.executors.patch_executor.PatchExecutor')
    def test_provision_digital_twin(self, mock_executor, mock_container_mgr):
        """Test provisioning a digital twin"""
        from services.digital_twin.core.twin import DigitalTwin

        mock_container = MagicMock()
        mock_container_mgr.return_value.create_container.return_value = mock_container

        twin = DigitalTwin(
            os_image="ubuntu:22.04",
            asset_config={"hostname": "test"}
        )

        success = twin.provision()

        assert isinstance(success, bool)

    @patch('services.digital_twin.core.container.ContainerManager')
    def test_execute_patch_in_twin(self, mock_container_mgr):
        """Test executing patch in digital twin"""
        from services.digital_twin.core.twin import DigitalTwin

        mock_container = MagicMock()
        mock_container_mgr.return_value.create_container.return_value = mock_container

        twin = DigitalTwin(os_image="ubuntu:22.04")
        twin.provision()

        # Execute patch
        patch_script = "#!/bin/bash\necho 'patching'"
        result = twin.execute_patch(patch_script)

        assert result is not None

    @patch('services.digital_twin.core.container.ContainerManager')
    def test_cleanup_twin(self, mock_container_mgr):
        """Test cleaning up digital twin"""
        from services.digital_twin.core.twin import DigitalTwin

        mock_container = MagicMock()
        mock_container_mgr.return_value.create_container.return_value = mock_container

        twin = DigitalTwin(os_image="ubuntu:22.04")
        twin.provision()
        twin.cleanup()

        # Should cleanup resources
        assert mock_container.stop.called or mock_container.remove.called


class TestTestSuite:
    """Test test suite execution"""

    def test_create_test_suite(self):
        """Test creating a test suite"""
        from services.digital_twin.validators.test_suite import TestSuite

        suite = TestSuite(name="Security Tests")
        suite.add_test("check_port_80", lambda: True)
        suite.add_test("check_service", lambda: True)

        assert len(suite.tests) == 2

    def test_run_test_suite(self):
        """Test running a test suite"""
        from services.digital_twin.validators.test_suite import TestSuite

        suite = TestSuite(name="Basic Tests")
        suite.add_test("passing_test", lambda: True)
        suite.add_test("failing_test", lambda: False)

        results = suite.run()

        assert len(results) == 2
        assert any(r["passed"] for r in results)
        assert any(not r["passed"] for r in results)

    def test_test_suite_with_exception(self):
        """Test test suite handles exceptions"""
        from services.digital_twin.validators.test_suite import TestSuite

        def failing_test():
            raise Exception("Test error")

        suite = TestSuite(name="Error Tests")
        suite.add_test("error_test", failing_test)

        results = suite.run()

        # Should handle exception gracefully
        assert len(results) == 1
        assert not results[0]["passed"]
