"""
Tests for LLM client
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.patch_generator.llm_client import (
    OpenAIClient,
    AnthropicClient,
    get_llm_client,
)


@pytest.fixture
def mock_vulnerability():
    """Mock vulnerability data"""
    return {
        "cve_id": "CVE-2024-1234",
        "title": "Test Vulnerability",
        "description": "Test vulnerability description",
        "severity": "HIGH",
        "cvss_score": 8.5,
        "affected_package": "nginx",
        "current_version": "1.18.0-0",
        "fixed_version": "1.18.0-1",
    }


@pytest.fixture
def mock_system_context():
    """Mock system context"""
    return {
        "os_type": "ubuntu",
        "os_version": "22.04",
        "package_manager": "apt",
        "asset_criticality": 7.0,
        "is_production": True,
    }


@pytest.fixture
def mock_llm_response():
    """Mock LLM response"""
    return """```json
{
  "patch_script": "#!/bin/bash\\nset -euo pipefail\\napt-get update\\napt-get install -y nginx",
  "rollback_script": "#!/bin/bash\\nset -euo pipefail\\napt-get install -y --allow-downgrades nginx=1.18.0-0",
  "validation_script": "#!/bin/bash\\ndpkg -l nginx",
  "confidence_score": 85,
  "estimated_duration_minutes": 5,
  "requires_restart": false,
  "risk_assessment": "low",
  "prerequisites": ["root access", "apt package manager"],
  "affected_services": ["nginx"],
  "notes": "Standard package update"
}
```"""


@pytest.mark.asyncio
async def test_openai_generate_patch(mock_vulnerability, mock_system_context, mock_llm_response):
    """Test OpenAI patch generation"""
    client = OpenAIClient(api_key="test-key", model="gpt-4")

    with patch.object(client, "client") as mock_client:
        # Mock the API response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = mock_llm_response

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Generate patch
        result = await client.generate_patch(mock_vulnerability, mock_system_context)

        # Verify result structure
        assert "patch_script" in result
        assert "rollback_script" in result
        assert "confidence_score" in result
        assert result["confidence_score"] == 85

        # Verify API was called
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["model"] == "gpt-4"
        assert call_args["temperature"] == 0.3


@pytest.mark.asyncio
async def test_openai_validate_patch():
    """Test OpenAI patch validation"""
    client = OpenAIClient(api_key="test-key", model="gpt-4")

    patch_script = "#!/bin/bash\\napt-get install -y nginx"
    context = {"os_type": "ubuntu", "package_manager": "apt"}

    validation_response = """```json
{
  "is_safe": true,
  "risk_level": "low",
  "issues": [],
  "recommendations": ["Add version check"]
}
```"""

    with patch.object(client, "client") as mock_client:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = validation_response

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await client.validate_patch(patch_script, context)

        assert result["is_safe"] is True
        assert result["risk_level"] == "low"
        assert isinstance(result["issues"], list)


@pytest.mark.asyncio
async def test_anthropic_generate_patch(mock_vulnerability, mock_system_context, mock_llm_response):
    """Test Anthropic patch generation"""
    client = AnthropicClient(api_key="test-key", model="claude-3-opus-20240229")

    with patch.object(client, "client") as mock_client:
        # Mock the API response
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = mock_llm_response

        mock_client.messages.create = AsyncMock(return_value=mock_response)

        # Generate patch
        result = await client.generate_patch(mock_vulnerability, mock_system_context)

        # Verify result
        assert "patch_script" in result
        assert "rollback_script" in result
        assert result["confidence_score"] == 85

        # Verify API was called
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args[1]
        assert call_args["model"] == "claude-3-opus-20240229"
        assert call_args["temperature"] == 0.3


@pytest.mark.asyncio
async def test_openai_no_api_key():
    """Test OpenAI client without API key"""
    client = OpenAIClient(api_key=None)
    client.client = None

    with pytest.raises(ValueError, match="OpenAI API key not configured"):
        await client.generate_patch({}, {})


@pytest.mark.asyncio
async def test_anthropic_no_api_key():
    """Test Anthropic client without API key"""
    client = AnthropicClient(api_key=None)
    client.client = None

    with pytest.raises(ValueError, match="Anthropic API key not configured"):
        await client.generate_patch({}, {})


def test_parse_llm_response_with_json():
    """Test parsing LLM response with valid JSON"""
    client = OpenAIClient(api_key="test-key")

    response = """Here's the patch:
```json
{
  "patch_script": "#!/bin/bash",
  "rollback_script": "#!/bin/bash",
  "confidence_score": 90
}
```"""

    result = client._parse_llm_response(response)

    assert result["patch_script"] == "#!/bin/bash"
    assert result["confidence_score"] == 90


def test_parse_llm_response_without_markdown():
    """Test parsing LLM response without markdown"""
    client = OpenAIClient(api_key="test-key")

    response = """{"patch_script": "#!/bin/bash", "confidence_score": 85}"""

    result = client._parse_llm_response(response)

    assert result["patch_script"] == "#!/bin/bash"
    assert result["confidence_score"] == 85


def test_parse_llm_response_fallback():
    """Test parsing LLM response with no JSON (fallback)"""
    client = OpenAIClient(api_key="test-key")

    response = "This is just plain text with no JSON"

    result = client._parse_llm_response(response)

    # Should return fallback structure
    assert result["patch_script"] == response
    assert result["confidence_score"] == 50
    assert "Failed to parse" in result["notes"]


def test_build_patch_prompt(mock_vulnerability, mock_system_context):
    """Test building patch generation prompt"""
    client = OpenAIClient(api_key="test-key")

    prompt = client._build_patch_prompt(mock_vulnerability, mock_system_context)

    # Should include key information
    assert "CVE-2024-1234" in prompt
    assert "nginx" in prompt
    assert "ubuntu" in prompt
    assert "apt" in prompt
    assert "JSON" in prompt  # Should request JSON format


@patch("services.patch_generator.llm_client.settings")
def test_get_llm_client_openai(mock_settings):
    """Test getting OpenAI client"""
    mock_settings.llm_provider = "openai"
    mock_settings.openai_api_key = "test-key"

    client = get_llm_client()
    assert isinstance(client, OpenAIClient)


@patch("services.patch_generator.llm_client.settings")
def test_get_llm_client_anthropic(mock_settings):
    """Test getting Anthropic client"""
    mock_settings.llm_provider = "anthropic"
    mock_settings.anthropic_api_key = "test-key"

    client = get_llm_client()
    assert isinstance(client, AnthropicClient)


@patch("services.patch_generator.llm_client.settings")
def test_get_llm_client_invalid(mock_settings):
    """Test getting client with invalid provider"""
    mock_settings.llm_provider = "invalid"

    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        get_llm_client()


def test_parse_validation_response():
    """Test parsing validation response"""
    client = OpenAIClient(api_key="test-key")

    response = """```json
{
  "is_safe": true,
  "risk_level": "low",
  "issues": ["Issue 1"],
  "recommendations": ["Rec 1"]
}
```"""

    result = client._parse_validation_response(response)

    assert result["is_safe"] is True
    assert result["risk_level"] == "low"
    assert len(result["issues"]) == 1
    assert len(result["recommendations"]) == 1


def test_parse_validation_response_fallback():
    """Test parsing validation response with fallback"""
    client = OpenAIClient(api_key="test-key")

    response = "No JSON here"

    result = client._parse_validation_response(response)

    # Should return default safe response
    assert result["is_safe"] is True
    assert result["risk_level"] == "medium"
    assert isinstance(result["issues"], list)
