"""
Tests for patch generator Celery tasks
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.patch_generator.tasks import (
    _generate_patch_async,
    _generate_patches_for_vulnerability_async,
    _auto_generate_patches_async,
)
from shared.models.models import (
    Vulnerability,
    Asset,
    Patch,
    VulnerabilitySeverity,
    AssetType,
    PatchStatus,
)


@pytest.mark.asyncio
async def test_generate_patch_task(db_session, sample_vulnerability):
    """Test generate_patch task"""
    with patch("services.patch_generator.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.patch_generator.tasks.PatchGenerator") as MockGenerator:
            mock_gen_instance = AsyncMock()
            mock_gen_instance.generate_patch.return_value = {
                "patch_script": "#!/bin/bash",
                "rollback_script": "#!/bin/bash",
                "validation_script": "",
                "confidence_score": 85,
                "risk_assessment": "low",
                "estimated_duration_minutes": 5,
                "requires_restart": False,
                "affected_services": [],
                "prerequisites": [],
                "validation_result": {"is_safe": True, "risk_level": "low"},
                "analysis": {"requires_restart": False},
                "generation_method": "llm",
                "notes": "",
            }
            MockGenerator.return_value = mock_gen_instance

            result = await _generate_patch_async(sample_vulnerability.id, None, True)

            assert result["status"] == "success"
            assert "patch_id" in result
            assert result["confidence_score"] == 85


@pytest.mark.asyncio
async def test_generate_patch_task_not_found(db_session):
    """Test generate_patch task with non-existent vulnerability"""
    with patch("services.patch_generator.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        result = await _generate_patch_async(99999, None, True)

        assert result["status"] == "error"
        assert "not found" in result["message"].lower()


@pytest.mark.asyncio
async def test_generate_patch_task_with_asset(db_session, sample_vulnerability, sample_asset):
    """Test generate_patch task with specific asset"""
    with patch("services.patch_generator.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.patch_generator.tasks.PatchGenerator") as MockGenerator:
            mock_gen_instance = AsyncMock()
            mock_gen_instance.generate_patch.return_value = {
                "patch_script": "#!/bin/bash",
                "rollback_script": "#!/bin/bash",
                "validation_script": "",
                "confidence_score": 90,
                "risk_assessment": "low",
                "estimated_duration_minutes": 5,
                "requires_restart": False,
                "affected_services": [],
                "prerequisites": [],
                "validation_result": {"is_safe": True, "risk_level": "low"},
                "analysis": {},
                "generation_method": "llm",
                "notes": "",
            }
            MockGenerator.return_value = mock_gen_instance

            result = await _generate_patch_async(
                sample_vulnerability.id,
                sample_asset.id,
                True,
            )

            assert result["status"] == "success"


@pytest.mark.asyncio
async def test_generate_patches_for_vulnerability(
    db_session,
    sample_vulnerability,
    sample_asset,
):
    """Test generating patches for all affected assets"""
    # Create asset-vulnerability relationship
    from shared.models.models import AssetVulnerability

    asset_vuln = AssetVulnerability(
        asset_id=sample_asset.id,
        vulnerability_id=sample_vulnerability.id,
    )
    db_session.add(asset_vuln)
    await db_session.commit()

    with patch("services.patch_generator.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.patch_generator.tasks.PatchGenerator") as MockGenerator:
            mock_gen_instance = AsyncMock()
            mock_gen_instance.generate_patch.return_value = {
                "patch_script": "#!/bin/bash",
                "rollback_script": "#!/bin/bash",
                "validation_script": "",
                "confidence_score": 85,
                "risk_assessment": "low",
                "estimated_duration_minutes": 5,
                "requires_restart": False,
                "affected_services": [],
                "prerequisites": [],
                "validation_result": {"is_safe": True, "risk_level": "low"},
                "analysis": {},
                "generation_method": "llm",
            }
            MockGenerator.return_value = mock_gen_instance

            result = await _generate_patches_for_vulnerability_async(
                sample_vulnerability.id,
                True,
            )

            assert result["status"] == "success"
            assert result["total_assets"] >= 1
            assert result["successful_patches"] >= 1


@pytest.mark.asyncio
async def test_auto_generate_patches(db_session, multiple_vulnerabilities):
    """Test auto-generating patches for high-priority vulnerabilities"""
    with patch("services.patch_generator.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.patch_generator.tasks.PatchGenerator") as MockGenerator:
            mock_gen_instance = AsyncMock()
            mock_gen_instance.generate_patch.return_value = {
                "patch_script": "#!/bin/bash",
                "rollback_script": "#!/bin/bash",
                "validation_script": "",
                "confidence_score": 85,
                "risk_assessment": "low",
                "estimated_duration_minutes": 5,
                "requires_restart": False,
                "affected_services": [],
                "prerequisites": [],
                "validation_result": {"is_safe": True, "risk_level": "low"},
                "analysis": {},
                "generation_method": "llm",
            }
            MockGenerator.return_value = mock_gen_instance

            result = await _auto_generate_patches_async(min_priority=70.0)

            assert result["status"] == "success"
            assert result["total_vulnerabilities"] >= 0


@pytest.mark.asyncio
async def test_generate_patch_auto_approval(db_session, sample_vulnerability):
    """Test that high-confidence patches are auto-approved"""
    with patch("services.patch_generator.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.patch_generator.tasks.PatchGenerator") as MockGenerator:
            mock_gen_instance = AsyncMock()
            # High confidence, safe patch
            mock_gen_instance.generate_patch.return_value = {
                "patch_script": "#!/bin/bash",
                "rollback_script": "#!/bin/bash",
                "validation_script": "",
                "confidence_score": 90,  # High confidence
                "risk_assessment": "low",
                "estimated_duration_minutes": 5,
                "requires_restart": False,
                "affected_services": [],
                "prerequisites": [],
                "validation_result": {"is_safe": True, "risk_level": "low"},
                "analysis": {},
                "generation_method": "llm",
                "notes": "",
            }
            MockGenerator.return_value = mock_gen_instance

            result = await _generate_patch_async(sample_vulnerability.id, None, True)

            assert result["status"] == "success"
            assert result["patch_status"] == "approved"


@pytest.mark.asyncio
async def test_generate_patch_pending_review(db_session, sample_vulnerability):
    """Test that medium-confidence patches require review"""
    with patch("services.patch_generator.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.patch_generator.tasks.PatchGenerator") as MockGenerator:
            mock_gen_instance = AsyncMock()
            # Medium confidence
            mock_gen_instance.generate_patch.return_value = {
                "patch_script": "#!/bin/bash",
                "rollback_script": "#!/bin/bash",
                "validation_script": "",
                "confidence_score": 70,  # Medium confidence
                "risk_assessment": "medium",
                "estimated_duration_minutes": 5,
                "requires_restart": False,
                "affected_services": [],
                "prerequisites": [],
                "validation_result": {"is_safe": True, "risk_level": "medium"},
                "analysis": {},
                "generation_method": "llm",
                "notes": "",
            }
            MockGenerator.return_value = mock_gen_instance

            result = await _generate_patch_async(sample_vulnerability.id, None, True)

            assert result["status"] == "success"
            assert result["patch_status"] == "pending_review"


@pytest.mark.asyncio
async def test_generate_patch_rejected(db_session, sample_vulnerability):
    """Test that low-confidence or unsafe patches are rejected"""
    with patch("services.patch_generator.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.patch_generator.tasks.PatchGenerator") as MockGenerator:
            mock_gen_instance = AsyncMock()
            # Low confidence or unsafe
            mock_gen_instance.generate_patch.return_value = {
                "patch_script": "#!/bin/bash",
                "rollback_script": "#!/bin/bash",
                "validation_script": "",
                "confidence_score": 40,  # Low confidence
                "risk_assessment": "high",
                "estimated_duration_minutes": 5,
                "requires_restart": False,
                "affected_services": [],
                "prerequisites": [],
                "validation_result": {"is_safe": False, "risk_level": "high"},
                "analysis": {},
                "generation_method": "llm",
                "notes": "",
            }
            MockGenerator.return_value = mock_gen_instance

            result = await _generate_patch_async(sample_vulnerability.id, None, True)

            assert result["status"] == "success"
            assert result["patch_status"] == "rejected"


@pytest.mark.asyncio
async def test_generate_patch_error_handling(db_session, sample_vulnerability):
    """Test error handling in patch generation"""
    with patch("services.patch_generator.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.patch_generator.tasks.PatchGenerator") as MockGenerator:
            mock_gen_instance = AsyncMock()
            mock_gen_instance.generate_patch.side_effect = Exception("Test error")
            MockGenerator.return_value = mock_gen_instance

            result = await _generate_patch_async(sample_vulnerability.id, None, True)

            assert result["status"] == "error"
            assert "error" in result["message"].lower() or "test error" in result["message"].lower()
