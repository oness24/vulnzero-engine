"""
Custom assertion helpers for testing

Provides reusable assertion functions for common validation scenarios
"""

from typing import Dict, Any, Optional, List
from shared.models.models import (
    Vulnerability,
    Patch,
    Deployment,
    Asset,
    VulnerabilitySeverity,
    PatchStatus,
    DeploymentStatus,
)


def assert_vulnerability_valid(vulnerability: Vulnerability):
    """
    Assert vulnerability object is valid

    Args:
        vulnerability: Vulnerability to validate
    """
    assert vulnerability is not None, "Vulnerability cannot be None"
    assert vulnerability.id is not None, "Vulnerability must have an ID"
    assert vulnerability.cve_id, "Vulnerability must have a CVE ID"
    assert vulnerability.title, "Vulnerability must have a title"
    assert vulnerability.description, "Vulnerability must have a description"
    assert vulnerability.severity in [s.value for s in VulnerabilitySeverity], \
        f"Invalid severity: {vulnerability.severity}"
    assert 0 <= vulnerability.cvss_score <= 10, \
        f"CVSS score must be between 0 and 10, got {vulnerability.cvss_score}"
    assert isinstance(vulnerability.affected_systems, list), \
        "Affected systems must be a list"
    assert len(vulnerability.affected_systems) > 0, \
        "Vulnerability must have at least one affected system"


def assert_patch_valid(patch: Patch):
    """
    Assert patch object is valid

    Args:
        patch: Patch to validate
    """
    assert patch is not None, "Patch cannot be None"
    assert patch.id is not None, "Patch must have an ID"
    assert patch.vulnerability_id is not None, "Patch must be linked to a vulnerability"
    assert patch.patch_script, "Patch must have a patch script"
    assert patch.rollback_script, "Patch must have a rollback script"
    assert patch.status in [s.value for s in PatchStatus], \
        f"Invalid patch status: {patch.status}"

    if patch.confidence_score is not None:
        assert 0 <= patch.confidence_score <= 1, \
            f"Confidence score must be between 0 and 1, got {patch.confidence_score}"


def assert_deployment_valid(deployment: Deployment):
    """
    Assert deployment object is valid

    Args:
        deployment: Deployment to validate
    """
    assert deployment is not None, "Deployment cannot be None"
    assert deployment.id is not None, "Deployment must have an ID"
    assert deployment.patch_id is not None, "Deployment must be linked to a patch"
    assert deployment.strategy in ["rolling", "blue_green", "canary"], \
        f"Invalid deployment strategy: {deployment.strategy}"
    assert deployment.status in [s.value for s in DeploymentStatus], \
        f"Invalid deployment status: {deployment.status}"

    if deployment.started_at and deployment.completed_at:
        assert deployment.completed_at >= deployment.started_at, \
            "Completion time must be after start time"


def assert_asset_valid(asset: Asset):
    """
    Assert asset object is valid

    Args:
        asset: Asset to validate
    """
    assert asset is not None, "Asset cannot be None"
    assert asset.id is not None, "Asset must have an ID"
    assert asset.name, "Asset must have a name"
    assert asset.ip_address, "Asset must have an IP address"
    assert asset.os_version, "Asset must have an OS version"


def assert_api_response_success(response: Dict[str, Any]):
    """
    Assert API response indicates success

    Args:
        response: API response dictionary
    """
    assert "status" in response, "Response must have a status"
    assert response["status"] == "success", f"Expected success, got {response.get('status')}"


def assert_api_response_error(response: Dict[str, Any], expected_message: Optional[str] = None):
    """
    Assert API response indicates error

    Args:
        response: API response dictionary
        expected_message: Optional expected error message substring
    """
    assert "status" in response, "Response must have a status"
    assert response["status"] == "error", f"Expected error, got {response.get('status')}"

    if expected_message:
        assert "message" in response, "Error response must have a message"
        assert expected_message.lower() in response["message"].lower(), \
            f"Expected message containing '{expected_message}', got '{response.get('message')}'"


def assert_test_results_valid(test_results: Dict[str, Any]):
    """
    Assert test results are valid

    Args:
        test_results: Test results dictionary
    """
    assert test_results is not None, "Test results cannot be None"
    assert "smoke_tests" in test_results, "Test results must include smoke tests"

    for test_type in ["smoke_tests", "security_tests", "performance_tests"]:
        if test_type in test_results:
            assert "passed" in test_results[test_type], \
                f"{test_type} must have 'passed' count"
            assert "failed" in test_results[test_type], \
                f"{test_type} must have 'failed' count"
            assert isinstance(test_results[test_type]["passed"], int), \
                f"{test_type} passed count must be an integer"
            assert isinstance(test_results[test_type]["failed"], int), \
                f"{test_type} failed count must be an integer"


def assert_deployment_results_valid(results: Dict[str, Any]):
    """
    Assert deployment results are valid

    Args:
        results: Deployment results dictionary
    """
    assert results is not None, "Deployment results cannot be None"
    assert "total_assets" in results, "Results must include total_assets"
    assert "successful" in results, "Results must include successful count"
    assert "failed" in results, "Results must include failed count"

    total = results["total_assets"]
    successful = results["successful"]
    failed = results["failed"]

    assert total >= 0, "Total assets must be non-negative"
    assert successful >= 0, "Successful count must be non-negative"
    assert failed >= 0, "Failed count must be non-negative"
    assert successful + failed <= total, \
        "Sum of successful and failed cannot exceed total"


def assert_health_check_valid(health_check: Dict[str, Any]):
    """
    Assert health check results are valid

    Args:
        health_check: Health check results dictionary
    """
    assert health_check is not None, "Health check cannot be None"
    assert "healthy" in health_check, "Health check must have 'healthy' field"
    assert isinstance(health_check["healthy"], bool), \
        "Health check 'healthy' must be boolean"


def assert_metrics_valid(metrics: Dict[str, Any]):
    """
    Assert metrics are valid

    Args:
        metrics: Metrics dictionary
    """
    assert metrics is not None, "Metrics cannot be None"

    for metric_name in ["cpu_usage", "memory_usage", "disk_usage"]:
        if metric_name in metrics:
            value = metrics[metric_name]
            assert isinstance(value, (int, float)), \
                f"{metric_name} must be numeric"
            assert 0 <= value <= 100, \
                f"{metric_name} must be between 0 and 100, got {value}"


def assert_alert_valid(alert: Dict[str, Any]):
    """
    Assert alert is valid

    Args:
        alert: Alert dictionary
    """
    assert alert is not None, "Alert cannot be None"
    assert "id" in alert, "Alert must have an ID"
    assert "title" in alert, "Alert must have a title"
    assert "message" in alert, "Alert must have a message"
    assert "severity" in alert, "Alert must have a severity"
    assert alert["severity"] in ["info", "warning", "error", "critical"], \
        f"Invalid alert severity: {alert['severity']}"
    assert "acknowledged" in alert, "Alert must have acknowledged status"
    assert "resolved" in alert, "Alert must have resolved status"


def assert_pagination_valid(response: Dict[str, Any], expected_total: Optional[int] = None):
    """
    Assert paginated response is valid

    Args:
        response: Paginated response dictionary
        expected_total: Optional expected total count
    """
    assert "total" in response, "Paginated response must have total"
    assert "page" in response, "Paginated response must have page"
    assert "page_size" in response, "Paginated response must have page_size"

    assert response["page"] >= 1, "Page must be >= 1"
    assert response["page_size"] >= 1, "Page size must be >= 1"
    assert response["total"] >= 0, "Total must be >= 0"

    if expected_total is not None:
        assert response["total"] == expected_total, \
            f"Expected total {expected_total}, got {response['total']}"


def assert_analytics_valid(analytics: Dict[str, Any]):
    """
    Assert analytics data is valid

    Args:
        analytics: Analytics dictionary
    """
    assert analytics is not None, "Analytics cannot be None"
    assert "total_deployments" in analytics, "Analytics must have total_deployments"
    assert isinstance(analytics["total_deployments"], int), \
        "total_deployments must be an integer"

    if "success_rate" in analytics:
        rate = analytics["success_rate"]
        assert isinstance(rate, (int, float)), "success_rate must be numeric"
        assert 0 <= rate <= 100, f"success_rate must be 0-100, got {rate}"


def assert_no_sensitive_data(data: Dict[str, Any]):
    """
    Assert response doesn't contain sensitive data

    Args:
        data: Data to check
    """
    sensitive_keys = [
        "password", "secret", "token", "api_key", "private_key",
        "ssh_password", "ssh_key", "credentials"
    ]

    def check_dict(d: Dict[str, Any], path: str = ""):
        for key, value in d.items():
            current_path = f"{path}.{key}" if path else key

            # Check if key contains sensitive terms
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                assert value is None or value == "" or value == "***", \
                    f"Sensitive data exposed at {current_path}"

            # Recursively check nested dictionaries
            if isinstance(value, dict):
                check_dict(value, current_path)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        check_dict(item, f"{current_path}[{i}]")

    check_dict(data)
