"""
Integration Tests for End-to-End Workflows

Tests complete workflows across multiple services.
"""

import pytest
from unittest.mock import patch, Mock


@pytest.mark.integration
class TestVulnerabilityToPatchWorkflow:
    """Test complete workflow from vulnerability to patch"""

    @pytest.mark.skip(reason="Full integration - requires all services")
    @patch('services.patch_generator.llm.openai_client.OpenAI')
    def test_create_vulnerability_generate_patch(self, mock_openai, test_db, api_client):
        """Test creating vulnerability and generating patch"""
        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="#!/bin/bash\necho 'patch'"))]
        mock_response.usage = Mock(total_tokens=100)
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        # 1. Create vulnerability via API
        vuln_response = api_client.post(
            "/api/v1/vulnerabilities",
            json={
                "cve_id": "CVE-2024-INT-001",
                "title": "Integration Test Vulnerability",
                "description": "Test description",
                "severity": "high",
                "cvss_score": 8.5,
                "affected_package": "test-pkg"
            }
        )

        assert vuln_response.status_code in [200, 201]
        vuln_id = vuln_response.json().get("id")

        # 2. Generate patch for vulnerability
        patch_response = api_client.post(
            f"/api/v1/patches/generate?vulnerability_id={vuln_id}"
        )

        assert patch_response.status_code in [200, 202]
        # Should return task ID for async generation
        assert "task_id" in patch_response.json()


@pytest.mark.integration
class TestPatchToDeploymentWorkflow:
    """Test workflow from patch generation to deployment"""

    @pytest.mark.skip(reason="Full integration - requires all services")
    @patch('services.digital_twin.core.container.ContainerManager')
    @patch('services.deployment_orchestrator.ansible.executor.AnsibleExecutor')
    def test_patch_test_deploy_workflow(
        self,
        mock_ansible,
        mock_container,
        test_db,
        sample_vulnerability,
        sample_patch,
        sample_asset
    ):
        """Test complete patch testing and deployment workflow"""
        # Mock successful execution
        mock_ansible.return_value.execute_patch.return_value = Mock(success=True)

        # 1. Test patch in digital twin
        from services.digital_twin.core.twin import DigitalTwin

        twin = DigitalTwin(os_image="ubuntu:22.04")
        test_result = twin.execute_patch(sample_patch.patch_content)

        assert test_result is not None

        # 2. If test passes, deploy to production
        if test_result:
            from services.deployment_orchestrator.core.engine import DeploymentEngine

            engine = DeploymentEngine(test_db)
            deployment_result = engine.deploy(
                patch=sample_patch,
                assets=[sample_asset],
                strategy="all-at-once"
            )

            assert deployment_result.success is True


@pytest.mark.integration
class TestMonitoringAndRollbackWorkflow:
    """Test monitoring and automatic rollback workflow"""

    @pytest.mark.skip(reason="Full integration - requires monitoring")
    @patch('psutil.cpu_percent')
    def test_deployment_monitoring_rollback(self, mock_cpu, test_db, sample_deployment):
        """Test monitoring deployment and triggering rollback"""
        from services.monitoring.collectors.metrics_collector import MetricsCollector
        from services.monitoring.detectors.anomaly_detector import AnomalyDetector
        from services.monitoring.rollback.rollback_engine import RollbackEngine

        # Simulate high CPU (anomaly)
        mock_cpu.return_value = 99.0

        # 1. Collect metrics
        collector = MetricsCollector(test_db)
        metrics = collector.collect_system_metrics(asset_id=1)

        # 2. Detect anomalies
        detector = AnomalyDetector()
        anomalies = detector.detect(metrics)

        assert len(anomalies) > 0

        # 3. Evaluate rollback
        engine = RollbackEngine(test_db)
        decision = engine.evaluate_rollback(sample_deployment.id, anomalies)

        if decision.should_rollback:
            # Would trigger rollback in production
            assert decision.confidence > 0


@pytest.mark.integration
class TestAPIWorkflows:
    """Test API workflows"""

    @pytest.mark.skip(reason="Requires authentication implementation")
    def test_api_authentication_flow(self, api_client):
        """Test login and authenticated request flow"""
        # 1. Login
        login_response = api_client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@test.com",
                "password": "Admin123!"
            }
        )

        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # 2. Use token for authenticated request
        headers = {"Authorization": f"Bearer {token}"}
        vuln_response = api_client.get(
            "/api/v1/vulnerabilities",
            headers=headers
        )

        assert vuln_response.status_code == 200

    def test_crud_workflow(self, test_db):
        """Test basic CRUD operations"""
        from shared.models import Vulnerability, VulnerabilityStatus

        # Create
        vuln = Vulnerability(
            cve_id="CVE-2024-CRUD",
            title="CRUD Test",
            severity="medium",
            cvss_score=5.5,
            scanner_source="test"
        )
        test_db.add(vuln)
        test_db.commit()
        test_db.refresh(vuln)

        assert vuln.id is not None

        # Read
        retrieved = test_db.query(Vulnerability).filter_by(id=vuln.id).first()
        assert retrieved.cve_id == "CVE-2024-CRUD"

        # Update
        retrieved.status = VulnerabilityStatus.PATCHED
        test_db.commit()

        updated = test_db.query(Vulnerability).filter_by(id=vuln.id).first()
        assert updated.status == VulnerabilityStatus.PATCHED

        # Delete
        test_db.delete(updated)
        test_db.commit()

        deleted = test_db.query(Vulnerability).filter_by(id=vuln.id).first()
        assert deleted is None
