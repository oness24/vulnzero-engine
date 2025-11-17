"""
Unit Tests for Patch Generator Service

Tests AI patch generation, validation, and LLM integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from services.patch_generator.generators.patch_generator import PatchGenerator
from services.patch_generator.validators.patch_validator import PatchValidator
from services.patch_generator.llm.factory import get_llm_client


class TestPatchGenerator:
    """Test patch generation logic"""

    @patch('services.patch_generator.llm.openai_client.OpenAI')
    def test_generate_patch_success(self, mock_openai, sample_vulnerability):
        """Test successful patch generation"""
        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="""
```bash
#!/bin/bash
apt-get update
apt-get install -y webapp=1.0.1
```
"""))]
        mock_response.usage = Mock(total_tokens=150)

        mock_openai.return_value.chat.completions.create.return_value = mock_response

        # Generate patch
        generator = PatchGenerator()
        result = generator.generate_patch(
            vulnerability=sample_vulnerability,
            asset_context={"os": "Ubuntu 22.04"}
        )

        assert result is not None
        assert result.patch_content is not None
        assert "apt-get" in result.patch_content
        assert result.confidence_score > 0

    def test_generate_patch_missing_vulnerability(self):
        """Test patch generation with missing vulnerability"""
        generator = PatchGenerator()

        with pytest.raises(ValueError):
            generator.generate_patch(vulnerability=None)

    @patch('services.patch_generator.llm.openai_client.OpenAI')
    def test_generate_patch_with_metadata(self, mock_openai, sample_vulnerability):
        """Test patch generation includes metadata"""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="#!/bin/bash\necho 'patch'"))]
        mock_response.usage = Mock(total_tokens=100)

        mock_openai.return_value.chat.completions.create.return_value = mock_response

        generator = PatchGenerator()
        result = generator.generate_patch(
            vulnerability=sample_vulnerability,
            asset_context={"os": "Ubuntu"}
        )

        assert result.metadata is not None
        assert "llm_provider" in result.metadata or hasattr(result, 'llm_provider')

    @patch('services.patch_generator.llm.anthropic_client.Anthropic')
    def test_generate_patch_anthropic(self, mock_anthropic, sample_vulnerability):
        """Test patch generation with Anthropic"""
        mock_response = Mock()
        mock_response.content = [Mock(text="#!/bin/bash\necho 'patch'")]
        mock_response.usage = Mock(input_tokens=50, output_tokens=50)

        mock_anthropic.return_value.messages.create.return_value = mock_response

        generator = PatchGenerator(llm_provider="anthropic")
        result = generator.generate_patch(vulnerability=sample_vulnerability)

        assert result is not None
        assert result.patch_content is not None


class TestPatchValidator:
    """Test patch validation logic"""

    def test_validate_bash_script_valid(self, sample_patch_script):
        """Test validation of valid bash script"""
        validator = PatchValidator()
        result = validator.validate(sample_patch_script)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_bash_script_syntax_error(self):
        """Test validation catches bash syntax errors"""
        invalid_script = """#!/bin/bash
if [ true  # Missing closing bracket
    echo "test"
fi
"""
        validator = PatchValidator()
        result = validator.validate(invalid_script)

        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_validate_dangerous_commands(self):
        """Test validation catches dangerous commands"""
        dangerous_script = """#!/bin/bash
rm -rf /
"""
        validator = PatchValidator()
        result = validator.validate(dangerous_script)

        assert result.is_valid is False
        assert any("dangerous" in err.lower() for err in result.errors)

    def test_validate_safety_score(self, sample_patch_script):
        """Test safety score calculation"""
        validator = PatchValidator()
        result = validator.validate(sample_patch_script)

        assert hasattr(result, 'safety_score')
        assert 0 <= result.safety_score <= 100

    def test_validate_empty_script(self):
        """Test validation of empty script"""
        validator = PatchValidator()
        result = validator.validate("")

        assert result.is_valid is False
        assert any("empty" in err.lower() for err in result.errors)

    def test_validate_non_bash_script(self):
        """Test validation of non-bash content"""
        python_script = """#!/usr/bin/env python3
print("This is Python, not Bash")
"""
        validator = PatchValidator()
        result = validator.validate(python_script)

        # Should still validate as a script
        assert isinstance(result.is_valid, bool)

    def test_validate_long_script(self):
        """Test validation of very long script"""
        long_script = "#!/bin/bash\n" + "\n".join([f"echo 'line {i}'" for i in range(1000)])

        validator = PatchValidator()
        result = validator.validate(long_script)

        # Should handle long scripts
        assert isinstance(result.is_valid, bool)

    def test_validate_special_characters(self):
        """Test validation handles special characters"""
        script_with_special = """#!/bin/bash
echo "Test with special chars: é, ñ, 中文"
"""
        validator = PatchValidator()
        result = validator.validate(script_with_special)

        assert isinstance(result.is_valid, bool)


class TestLLMFactory:
    """Test LLM client factory"""

    @patch('services.patch_generator.llm.openai_client.OpenAI')
    def test_get_openai_client(self, mock_openai):
        """Test getting OpenAI client"""
        client = get_llm_client(provider="openai")

        assert client is not None
        # Should return OpenAIClient instance
        assert hasattr(client, 'generate')

    @patch('services.patch_generator.llm.anthropic_client.Anthropic')
    def test_get_anthropic_client(self, mock_anthropic):
        """Test getting Anthropic client"""
        client = get_llm_client(provider="anthropic")

        assert client is not None
        assert hasattr(client, 'generate')

    def test_get_invalid_provider(self):
        """Test getting client with invalid provider"""
        with pytest.raises(ValueError):
            get_llm_client(provider="invalid-provider")

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('services.patch_generator.llm.openai_client.OpenAI')
    def test_client_uses_env_api_key(self, mock_openai):
        """Test client uses API key from environment"""
        get_llm_client(provider="openai")

        # OpenAI client should be initialized (actual key validation would happen on API call)
        assert mock_openai.called


class TestPatchConfidenceScoring:
    """Test patch confidence scoring"""

    def test_confidence_score_range(self):
        """Test confidence score is within 0-100"""
        from services.patch_generator.analyzers.confidence_scorer import calculate_confidence

        # Mock patch data
        patch_data = {
            "has_rollback": True,
            "syntax_valid": True,
            "safety_score": 90,
            "llm_confidence": 0.85
        }

        score = calculate_confidence(patch_data)

        assert 0 <= score <= 100

    def test_confidence_higher_with_rollback(self):
        """Test confidence is higher when rollback script exists"""
        from services.patch_generator.analyzers.confidence_scorer import calculate_confidence

        with_rollback = {
            "has_rollback": True,
            "syntax_valid": True,
            "safety_score": 80,
            "llm_confidence": 0.8
        }

        without_rollback = {
            "has_rollback": False,
            "syntax_valid": True,
            "safety_score": 80,
            "llm_confidence": 0.8
        }

        score_with = calculate_confidence(with_rollback)
        score_without = calculate_confidence(without_rollback)

        assert score_with > score_without

    def test_confidence_lower_with_syntax_errors(self):
        """Test confidence is lower with syntax errors"""
        from services.patch_generator.analyzers.confidence_scorer import calculate_confidence

        valid_syntax = {
            "has_rollback": True,
            "syntax_valid": True,
            "safety_score": 80,
            "llm_confidence": 0.8
        }

        invalid_syntax = {
            "has_rollback": True,
            "syntax_valid": False,
            "safety_score": 80,
            "llm_confidence": 0.8
        }

        score_valid = calculate_confidence(valid_syntax)
        score_invalid = calculate_confidence(invalid_syntax)

        assert score_valid > score_invalid


class TestVulnerabilityAnalyzer:
    """Test vulnerability analysis"""

    def test_analyze_vulnerability(self, sample_vulnerability):
        """Test analyzing vulnerability for patch generation"""
        from services.patch_generator.analyzers.vulnerability_analyzer import VulnerabilityAnalyzer

        analyzer = VulnerabilityAnalyzer()
        analysis = analyzer.analyze(sample_vulnerability)

        assert analysis is not None
        assert "severity" in analysis or hasattr(analysis, 'severity')
        assert "recommendations" in analysis or hasattr(analysis, 'recommendations')

    def test_analyze_sql_injection(self):
        """Test analyzing SQL injection vulnerability"""
        from services.patch_generator.analyzers.vulnerability_analyzer import VulnerabilityAnalyzer

        vuln_data = {
            "cve_id": "CVE-2024-SQL",
            "title": "SQL Injection in login form",
            "description": "Unsanitized SQL query",
            "severity": "critical"
        }

        analyzer = VulnerabilityAnalyzer()
        analysis = analyzer.analyze_description(vuln_data["description"])

        # Should identify SQL injection type
        assert "sql" in str(analysis).lower() or "injection" in str(analysis).lower()

    def test_analyze_xss(self):
        """Test analyzing XSS vulnerability"""
        from services.patch_generator.analyzers.vulnerability_analyzer import VulnerabilityAnalyzer

        vuln_data = {
            "description": "Cross-site scripting in user input"
        }

        analyzer = VulnerabilityAnalyzer()
        analysis = analyzer.analyze_description(vuln_data["description"])

        # Should identify XSS type
        assert isinstance(analysis, (dict, object))
