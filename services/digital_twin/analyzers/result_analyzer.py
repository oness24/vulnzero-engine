"""
Test Result Analyzer

Analyzes test execution results and generates reports.
"""

import logging
from enum import Enum
from typing import Dict, Any, List
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TestStatus(str, Enum):
    """Test status enumeration"""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class TestResult(BaseModel):
    """Complete test result"""
    patch_id: int
    vulnerability_id: int
    asset_id: int
    test_id: str
    status: TestStatus
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    
    # Execution results
    patch_execution: Dict[str, Any]
    health_checks: Dict[str, Any]
    
    # Analysis
    overall_passed: bool
    confidence_score: float  # 0-100
    issues: List[str] = []
    warnings: List[str] = []
    
    # Artifacts
    container_logs: str = ""
    system_state_before: Dict[str, Any] = {}
    system_state_after: Dict[str, Any] = {}

    class Config:
        use_enum_values = True


class ResultAnalyzer:
    """
    Analyzes test results and generates actionable insights.
    """

    def __init__(self):
        """Initialize result analyzer"""
        self.logger = logging.getLogger(__name__)

    def analyze(
        self,
        patch_id: int,
        vulnerability_id: int,
        asset_id: int,
        test_id: str,
        patch_execution: Dict[str, Any],
        health_checks: Dict[str, Any],
        container_logs: str = "",
        state_before: Dict[str, Any] = None,
        state_after: Dict[str, Any] = None,
    ) -> TestResult:
        """
        Analyze test execution and generate result.

        Args:
            patch_id: Patch ID
            vulnerability_id: Vulnerability ID
            asset_id: Asset ID
            test_id: Test identifier
            patch_execution: Patch execution results
            health_checks: Health check results
            container_logs: Container logs
            state_before: System state before patch
            state_after: System state after patch

        Returns:
            TestResult with complete analysis
        """
        self.logger.info(f"Analyzing test results for {test_id}")

        # Determine overall status
        patch_success = patch_execution.get("success", False)
        health_pass = health_checks.get("overall_passed", False)
        
        if patch_success and health_pass:
            status = TestStatus.PASSED
        elif not patch_success:
            status = TestStatus.FAILED
        else:
            status = TestStatus.FAILED

        # Calculate confidence score
        confidence = self._calculate_confidence(
            patch_execution, health_checks, status
        )

        # Identify issues and warnings
        issues = self._identify_issues(patch_execution, health_checks)
        warnings = self._identify_warnings(patch_execution, health_checks)

        # Get timestamps
        started_at = datetime.fromisoformat(patch_execution.get("timestamp"))
        duration = patch_execution.get("duration_seconds", 0)
        completed_at = datetime.utcnow()

        return TestResult(
            patch_id=patch_id,
            vulnerability_id=vulnerability_id,
            asset_id=asset_id,
            test_id=test_id,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            patch_execution=patch_execution,
            health_checks=health_checks,
            overall_passed=(status == TestStatus.PASSED),
            confidence_score=confidence,
            issues=issues,
            warnings=warnings,
            container_logs=container_logs,
            system_state_before=state_before or {},
            system_state_after=state_after or {},
        )

    def _calculate_confidence(
        self,
        patch_execution: Dict[str, Any],
        health_checks: Dict[str, Any],
        status: TestStatus
    ) -> float:
        """Calculate confidence score (0-100)"""
        score = 0.0

        # Base score from status
        if status == TestStatus.PASSED:
            score += 50.0
        elif status == TestStatus.FAILED:
            score += 0.0

        # Patch execution quality
        if patch_execution.get("exit_code") == 0:
            score += 20.0
        
        if not patch_execution.get("stderr", "").strip():
            score += 10.0

        # Health check success rate
        success_rate = health_checks.get("success_rate", 0)
        score += (success_rate / 100) * 20.0

        return min(100.0, score)

    def _identify_issues(
        self,
        patch_execution: Dict[str, Any],
        health_checks: Dict[str, Any]
    ) -> List[str]:
        """Identify critical issues"""
        issues = []

        # Patch execution issues
        if not patch_execution.get("success"):
            issues.append(f"Patch execution failed with exit code {patch_execution.get('exit_code')}")
        
        if patch_execution.get("error_message"):
            issues.append(f"Execution error: {patch_execution.get('error_message')}")

        # Health check failures
        failed_checks = [
            r for r in health_checks.get("results", [])
            if not r.get("passed")
        ]
        for check in failed_checks:
            issues.append(f"Health check failed: {check.get('name')} - {check.get('message')}")

        return issues

    def _identify_warnings(
        self,
        patch_execution: Dict[str, Any],
        health_checks: Dict[str, Any]
    ) -> List[str]:
        """Identify warnings"""
        warnings = []

        # Check for stderr output
        stderr = patch_execution.get("stderr", "").strip()
        if stderr and len(stderr) > 0:
            warnings.append("Patch execution produced stderr output")

        # Check success rate
        success_rate = health_checks.get("success_rate", 0)
        if 50 <= success_rate < 70:
            warnings.append(f"Low health check success rate: {success_rate:.1f}%")

        return warnings

    def generate_report(self, result: TestResult) -> str:
        """
        Generate human-readable test report.

        Args:
            result: TestResult to report on

        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 80)
        report.append(f"DIGITAL TWIN TEST REPORT")
        report.append("=" * 80)
        report.append(f"Test ID: {result.test_id}")
        report.append(f"Status: {result.status.upper()}")
        report.append(f"Confidence: {result.confidence_score:.1f}%")
        report.append(f"Duration: {result.duration_seconds:.2f}s")
        report.append("")

        # Patch execution
        report.append("PATCH EXECUTION:")
        report.append(f"  Exit Code: {result.patch_execution.get('exit_code')}")
        report.append(f"  Success: {result.patch_execution.get('success')}")
        
        if result.patch_execution.get("stdout"):
            report.append("  Stdout:")
            for line in result.patch_execution.get("stdout", "").split("\n")[:10]:
                report.append(f"    {line}")

        report.append("")

        # Health checks
        report.append("HEALTH CHECKS:")
        report.append(f"  Overall: {'PASSED' if result.health_checks.get('overall_passed') else 'FAILED'}")
        report.append(f"  Success Rate: {result.health_checks.get('success_rate', 0):.1f}%")
        report.append(f"  Passed: {result.health_checks.get('passed_checks', 0)}/{result.health_checks.get('total_checks', 0)}")

        report.append("")

        # Issues
        if result.issues:
            report.append("ISSUES:")
            for issue in result.issues:
                report.append(f"  - {issue}")
            report.append("")

        # Warnings
        if result.warnings:
            report.append("WARNINGS:")
            for warning in result.warnings:
                report.append(f"  - {warning}")
            report.append("")

        report.append("=" * 80)

        return "\n".join(report)
