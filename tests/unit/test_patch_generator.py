"""Unit tests for patch generator."""
import pytest

from vulnzero.services.patch_generator.prompts import get_package_update_prompt
from vulnzero.services.patch_generator.templates import TemplateLibrary
from vulnzero.services.patch_generator.validator import PatchValidator


@pytest.mark.unit
def test_get_package_update_prompt():
    """Test prompt generation for package updates."""
    context = {
        "cve_id": "CVE-2024-0001",
        "description": "Test vulnerability",
        "package_name": "test-package",
        "vulnerable_version": "1.0.0",
        "fixed_version": "1.0.1",
        "os_type": "ubuntu",
        "os_version": "22.04",
        "package_manager": "apt",
    }

    prompt = get_package_update_prompt(context)

    assert "CVE-2024-0001" in prompt
    assert "test-package" in prompt
    assert "ubuntu" in prompt
    assert "apt" in prompt
    assert "bash" in prompt.lower()


@pytest.mark.unit
def test_template_library_get_template():
    """Test template library template retrieval."""
    library = TemplateLibrary()

    # Ubuntu should get apt template
    template = library.get_template("ubuntu", "package_update")
    assert template is not None
    assert "apt" in template.template.lower()

    # RHEL should get yum template
    template = library.get_template("rhel", "package_update")
    assert template is not None
    assert "yum" in template.template.lower()


@pytest.mark.unit
def test_template_render():
    """Test template rendering."""
    library = TemplateLibrary()

    context = {
        "cve_id": "CVE-2024-0001",
        "package_name": "openssl",
        "fixed_version": "1.1.1w",
        "timestamp": "2024-01-01T00:00:00",
    }

    script = library.render_template("apt_package_update", context)

    assert script is not None
    assert "CVE-2024-0001" in script
    assert "openssl" in script
    assert "1.1.1w" in script
    assert "#!/bin/bash" in script


@pytest.mark.unit
def test_validator_syntax_check_valid():
    """Test validator with valid bash script."""
    validator = PatchValidator()

    valid_script = """#!/bin/bash
set -e
echo "Hello World"
exit 0
"""

    is_valid, error = validator.validate_syntax(valid_script)
    assert is_valid
    assert error is None


@pytest.mark.unit
def test_validator_syntax_check_invalid():
    """Test validator with invalid bash script."""
    validator = PatchValidator()

    invalid_script = """#!/bin/bash
if [ "test"
echo "Missing fi"
"""

    is_valid, error = validator.validate_syntax(invalid_script)
    assert not is_valid
    assert error is not None


@pytest.mark.unit
def test_validator_detect_dangerous_commands():
    """Test dangerous command detection."""
    validator = PatchValidator()

    dangerous_script = """#!/bin/bash
rm -rf /
dd if=/dev/zero of=/dev/sda
"""

    issues = validator.detect_dangerous_commands(dangerous_script)
    assert len(issues) > 0
    assert any("rm -rf" in issue.description for issue in issues)


@pytest.mark.unit
def test_validator_validate_safe_script():
    """Test validation of safe script."""
    validator = PatchValidator()

    safe_script = """#!/bin/bash
set -e

apt-get update
apt-get install -y package-name

exit 0
"""

    result = validator.validate(safe_script)

    assert result.syntax_valid
    assert len(result.dangerous_commands) == 0
    assert result.safety_score > 0.5


@pytest.mark.unit
def test_validator_calculate_safety_score():
    """Test safety score calculation."""
    validator = PatchValidator()

    from vulnzero.services.patch_generator.validator import ValidationIssue

    # No issues should give high score
    issues = []
    dangerous = []
    score = validator.calculate_safety_score(issues, dangerous)
    assert score == 1.0

    # Dangerous commands should give 0
    issues = []
    dangerous = ["rm -rf /"]
    score = validator.calculate_safety_score(issues, dangerous)
    assert score == 0.0

    # Medium issues should reduce score
    issues = [ValidationIssue(severity="medium", description="Test issue")]
    dangerous = []
    score = validator.calculate_safety_score(issues, dangerous)
    assert 0.0 < score < 1.0
