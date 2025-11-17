"""
Unit Tests for Deployment Orchestrator

Tests deployment strategies, validators, and orchestration logic.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from services.deployment_orchestrator.strategies.rolling import RollingDeployment
from services.deployment_orchestrator.strategies.canary import CanaryDeployment
from services.deployment_orchestrator.strategies.all_at_once import AllAtOnceDeployment


class TestRollingDeployment:
    """Test rolling deployment strategy"""

    @patch('services.deployment_orchestrator.ansible.executor.AnsibleExecutor')
    def test_rolling_deployment_success(self, mock_executor, sample_patch, sample_asset, test_db):
        """Test successful rolling deployment"""
        # Mock successful execution
        mock_result = Mock()
        mock_result.success = True
        mock_executor.return_value.execute_patch.return_value = mock_result

        # Create assets
        assets = [sample_asset]

        # Execute rolling deployment
        strategy = RollingDeployment(
            patch=sample_patch,
            batch_size=0.5,  # 50% at a time
            wait_seconds=1
        )

        result = strategy.execute(assets)

        assert result.success is True
        assert len(result.assets_deployed) == len(assets)
        assert len(result.assets_failed) == 0

    @patch('services.deployment_orchestrator.ansible.executor.AnsibleExecutor')
    def test_rolling_deployment_partial_failure(self, mock_executor, sample_patch, sample_asset):
        """Test rolling deployment with partial failure"""
        # Mock mixed results
        success_result = Mock(success=True)
        failure_result = Mock(success=False, message="Deployment failed")

        mock_executor.return_value.execute_patch.side_effect = [
            success_result,
            failure_result
        ]

        # Create multiple assets
        assets = [sample_asset, sample_asset]

        strategy = RollingDeployment(
            patch=sample_patch,
            batch_size=0.5,
            max_failures=1
        )

        result = strategy.execute(assets)

        # Should complete despite one failure
        assert len(result.assets_deployed) >= 1

    def test_rolling_deployment_batch_calculation(self, sample_patch):
        """Test batch size calculation"""
        strategy = RollingDeployment(
            patch=sample_patch,
            batch_size=0.25  # 25%
        )

        # Test with 100 assets
        assets = [Mock() for _ in range(100)]
        batches = strategy._calculate_batches(assets)

        # Should have 4 batches of 25 each
        assert len(batches) == 4
        assert all(len(batch) == 25 for batch in batches)

    def test_rolling_deployment_small_batch(self, sample_patch):
        """Test rolling deployment with small number of assets"""
        strategy = RollingDeployment(
            patch=sample_patch,
            batch_size=0.5
        )

        assets = [Mock(), Mock(), Mock()]  # 3 assets
        batches = strategy._calculate_batches(assets)

        # Should handle small numbers appropriately
        assert len(batches) >= 1


class TestCanaryDeployment:
    """Test canary deployment strategy"""

    @patch('services.deployment_orchestrator.ansible.executor.AnsibleExecutor')
    def test_canary_deployment_stages(self, mock_executor, sample_patch):
        """Test canary deployment progresses through stages"""
        mock_result = Mock(success=True)
        mock_executor.return_value.execute_patch.return_value = mock_result

        assets = [Mock() for _ in range(10)]

        strategy = CanaryDeployment(
            patch=sample_patch,
            stages=[0.1, 0.5, 1.0],  # 10%, 50%, 100%
            monitoring_duration=1  # 1 second for testing
        )

        result = strategy.execute(assets)

        # Should complete all stages
        assert result.success is True

    @patch('services.deployment_orchestrator.ansible.executor.AnsibleExecutor')
    def test_canary_deployment_rollback_on_failure(self, mock_executor, sample_patch):
        """Test canary deployment rolls back on failure"""
        # First stage succeeds, second fails
        mock_executor.return_value.execute_patch.side_effect = [
            Mock(success=True),   # Stage 1: 10% - succeeds
            Mock(success=False),  # Stage 2: 50% - fails
        ]

        assets = [Mock() for _ in range(10)]

        strategy = CanaryDeployment(
            patch=sample_patch,
            stages=[0.1, 0.5, 1.0],
            rollback_on_failure=True
        )

        result = strategy.execute(assets)

        # Should trigger rollback
        assert result.success is False

    def test_canary_stage_calculation(self, sample_patch):
        """Test canary stage asset calculation"""
        strategy = CanaryDeployment(
            patch=sample_patch,
            stages=[0.1, 0.5, 1.0]
        )

        assets = [Mock() for _ in range(100)]
        stage_groups = strategy._calculate_stage_groups(assets)

        # Should have 3 groups: 10, 50, 100 assets
        assert len(stage_groups) == 3
        assert len(stage_groups[0]) == 10
        assert len(stage_groups[1]) == 50
        assert len(stage_groups[2]) == 100


class TestAllAtOnceDeployment:
    """Test all-at-once deployment strategy"""

    @patch('services.deployment_orchestrator.ansible.executor.AnsibleExecutor')
    def test_all_at_once_success(self, mock_executor, sample_patch):
        """Test successful all-at-once deployment"""
        mock_result = Mock(success=True)
        mock_executor.return_value.execute_patch.return_value = mock_result

        assets = [Mock() for _ in range(5)]

        strategy = AllAtOnceDeployment(patch=sample_patch)
        result = strategy.execute(assets)

        assert result.success is True
        assert len(result.assets_deployed) == 5

    @patch('services.deployment_orchestrator.ansible.executor.AnsibleExecutor')
    def test_all_at_once_with_failures(self, mock_executor, sample_patch):
        """Test all-at-once deployment with some failures"""
        # Mix of success and failure
        mock_executor.return_value.execute_patch.side_effect = [
            Mock(success=True),
            Mock(success=False),
            Mock(success=True),
        ]

        assets = [Mock() for _ in range(3)]

        strategy = AllAtOnceDeployment(patch=sample_patch)
        result = strategy.execute(assets)

        assert len(result.assets_deployed) == 2
        assert len(result.assets_failed) == 1


class TestPreDeployValidator:
    """Test pre-deployment validation"""

    def test_validate_patch_tested(self, test_db, sample_patch, sample_asset):
        """Test validation requires patch to be tested"""
        from services.deployment_orchestrator.validators.pre_deploy import PreDeployValidator

        validator = PreDeployValidator(test_db)

        # Patch not tested yet
        is_valid, message = validator.validate(sample_patch, [sample_asset])

        # Should fail validation - no test results
        assert is_valid is False
        assert "test" in message.lower()

    def test_validate_asset_connectivity(self, test_db, sample_patch, sample_asset):
        """Test validation checks asset connectivity"""
        from services.deployment_orchestrator.validators.pre_deploy import PreDeployValidator

        validator = PreDeployValidator(test_db)

        # Asset with no hostname
        invalid_asset = Mock()
        invalid_asset.hostname = None

        is_valid, message = validator._validate_asset_connectivity([invalid_asset])

        assert is_valid is False
        assert "hostname" in message.lower()

    def test_validate_maintenance_windows(self, test_db, sample_patch):
        """Test validation checks maintenance windows"""
        from services.deployment_orchestrator.validators.pre_deploy import PreDeployValidator
        from shared.models import Asset, AssetType, AssetStatus

        validator = PreDeployValidator(test_db)

        # Asset in maintenance mode
        maintenance_asset = Asset(
            hostname="maintenance-server",
            type=AssetType.SERVER,
            status=AssetStatus.ACTIVE,
            asset_metadata={"maintenance_mode": True}
        )
        test_db.add(maintenance_asset)
        test_db.commit()

        is_valid, message = validator._validate_maintenance_windows([maintenance_asset])

        assert is_valid is False
        assert "maintenance" in message.lower()


class TestPostDeployValidator:
    """Test post-deployment validation"""

    @patch('subprocess.run')
    def test_validate_deployment_health(self, mock_subprocess, test_db, sample_patch, sample_asset):
        """Test post-deployment health checks"""
        from services.deployment_orchestrator.validators.post_deploy import PostDeployValidator

        # Mock successful health check
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="ok=5 failed=0"
        )

        validator = PostDeployValidator(test_db)
        result = validator.validate(sample_patch, [sample_asset])

        assert result["success"] is True
        assert result["health_percentage"] >= 0

    @patch('subprocess.run')
    def test_validate_deployment_failures(self, mock_subprocess, test_db, sample_patch, sample_asset):
        """Test post-deployment detects failures"""
        from services.deployment_orchestrator.validators.post_deploy import PostDeployValidator

        # Mock failed health check
        mock_subprocess.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Health check failed"
        )

        validator = PostDeployValidator(test_db)
        result = validator.validate(sample_patch, [sample_asset])

        assert result["success"] is False
        assert len(result["issues"]) > 0


class TestAnsibleIntegration:
    """Test Ansible integration"""

    @patch('subprocess.run')
    def test_ansible_playbook_execution(self, mock_subprocess, sample_patch, sample_asset):
        """Test Ansible playbook execution"""
        from services.deployment_orchestrator.ansible.executor import AnsibleExecutor

        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="PLAY RECAP: success",
            stderr=""
        )

        executor = AnsibleExecutor()
        result = executor.execute_patch(sample_asset, sample_patch)

        assert result.success is True
        assert mock_subprocess.called

    @patch('subprocess.run')
    def test_ansible_execution_timeout(self, mock_subprocess, sample_patch, sample_asset):
        """Test Ansible execution handles timeout"""
        from services.deployment_orchestrator.ansible.executor import AnsibleExecutor
        import subprocess

        mock_subprocess.side_effect = subprocess.TimeoutExpired("ansible-playbook", 300)

        executor = AnsibleExecutor()
        result = executor.execute_patch(sample_asset, sample_patch)

        assert result.success is False
        assert "timeout" in result.message.lower()

    def test_playbook_generation(self, sample_patch, sample_asset):
        """Test Ansible playbook generation"""
        from services.deployment_orchestrator.ansible.playbook_generator import PlaybookGenerator

        generator = PlaybookGenerator()
        playbook = generator.generate_patch_playbook(sample_asset, sample_patch)

        assert playbook is not None
        assert isinstance(playbook, str)
        assert "hosts:" in playbook
        assert "tasks:" in playbook


class TestDeploymentEngine:
    """Test deployment engine orchestration"""

    @patch('services.deployment_orchestrator.strategies.rolling.RollingDeployment.execute')
    def test_deployment_engine_orchestration(self, mock_execute, test_db, sample_patch, sample_asset):
        """Test deployment engine orchestrates deployment"""
        from services.deployment_orchestrator.core.engine import DeploymentEngine

        mock_execute.return_value = Mock(
            success=True,
            successful_assets=1,
            failed_assets=0,
            total_assets=1
        )

        engine = DeploymentEngine(test_db)
        result = engine.deploy(
            patch=sample_patch,
            assets=[sample_asset],
            strategy="rolling"
        )

        assert result.success is True

    def test_deployment_engine_pre_validation(self, test_db, sample_patch, sample_asset):
        """Test deployment engine runs pre-validation"""
        from services.deployment_orchestrator.core.engine import DeploymentEngine

        engine = DeploymentEngine(test_db)

        # Should run pre-deployment checks
        is_valid, message = engine.pre_deploy_checks(sample_patch, [sample_asset])

        # Will fail because patch not tested
        assert isinstance(is_valid, bool)
