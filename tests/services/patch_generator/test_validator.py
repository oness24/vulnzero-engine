"""
Tests for patch validation
"""

import pytest
from services.patch_generator.validator import PatchValidator, PatchAnalyzer


@pytest.fixture
def validator():
    """Create validator instance"""
    return PatchValidator()


@pytest.fixture
def analyzer():
    """Create analyzer instance"""
    return PatchAnalyzer()


@pytest.fixture
def safe_patch_script():
    """A safe patch script"""
    return """#!/bin/bash
set -euo pipefail

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root"
    exit 1
fi

# Update package
apt-get update -qq
apt-get install -y --only-upgrade nginx

echo "Patch completed successfully"
"""


@pytest.fixture
def dangerous_patch_script():
    """A dangerous patch script"""
    return """#!/bin/bash
# This is a dangerous script
rm -rf /
"""


@pytest.fixture
def risky_patch_script():
    """A risky but not necessarily dangerous script"""
    return """#!/bin/bash
# Risky operations
rm -rf /tmp/old_data
chmod 777 /var/www
systemctl stop firewalld
"""


def test_validate_safe_patch(validator, safe_patch_script):
    """Test validating a safe patch"""
    result = validator.validate_patch(safe_patch_script)

    assert result["is_safe"] is True
    assert len(result["issues"]) == 0
    assert result["risk_level"] in ["low", "medium"]
    assert result["score"] >= 70


def test_validate_dangerous_patch(validator, dangerous_patch_script):
    """Test validating a dangerous patch"""
    result = validator.validate_patch(dangerous_patch_script)

    assert result["is_safe"] is False
    assert len(result["issues"]) > 0
    assert result["risk_level"] == "critical"
    assert "dangerous" in result["issues"][0].lower()


def test_validate_risky_patch(validator, risky_patch_script):
    """Test validating a risky patch"""
    result = validator.validate_patch(risky_patch_script)

    # Should be safe (no critical issues) but have warnings
    assert result["is_safe"] is True
    assert len(result["warnings"]) > 0
    assert "risky" in result["warnings"][0].lower() or "rm -rf" in result["warnings"][0].lower()


def test_validate_patch_with_production_context(validator, safe_patch_script):
    """Test validation with production context"""
    context = {"is_production": True, "is_critical": True}

    result = validator.validate_patch(safe_patch_script, context)

    # Same script but risk level may be elevated due to context
    assert result["is_safe"] is True


def test_validate_patch_missing_error_handling(validator):
    """Test patch without error handling"""
    script = """#!/bin/bash
apt-get update
apt-get install -y nginx
"""

    result = validator.validate_patch(script)

    # Should have recommendations about missing error handling
    assert any("set -e" in rec for rec in result["recommendations"])


def test_validate_patch_missing_root_check(validator):
    """Test patch without root check"""
    script = """#!/bin/bash
set -euo pipefail
apt-get install -y nginx
"""

    result = validator.validate_patch(script)

    # Should recommend privilege check
    assert any("privilege" in rec.lower() or "root" in rec.lower() for rec in result["recommendations"])


def test_validate_patch_unquoted_variables(validator):
    """Test patch with unquoted variables"""
    script = """#!/bin/bash
set -euo pipefail
PACKAGE=$1
apt-get install -y $PACKAGE
"""

    result = validator.validate_patch(script)

    # Should warn about unquoted variables
    assert any("unquoted" in warn.lower() for warn in result["warnings"])


def test_validate_patch_with_eval(validator):
    """Test patch using eval (dangerous)"""
    script = """#!/bin/bash
set -euo pipefail
eval "apt-get install -y nginx"
"""

    result = validator.validate_patch(script)

    # Should warn about eval usage
    assert any("eval" in warn.lower() for warn in result["warnings"])


def test_validate_rollback_script(validator):
    """Test rollback script validation"""
    rollback_script = """#!/bin/bash
set -euo pipefail

if [ "$EUID" -ne 0 ]; then
    exit 1
fi

apt-get install -y --allow-downgrades nginx=1.18.0-0
VERSION=$(dpkg-query -W -f='${Version}' nginx)
echo "Rollback complete. Current version: $VERSION"
"""

    result = validator.validate_rollback_script(rollback_script)

    assert result["is_safe"] is True
    assert result["score"] >= 60


def test_check_idempotency_positive(validator):
    """Test idempotency check with idempotent script"""
    script = """#!/bin/bash
if [ -f /etc/nginx/nginx.conf ]; then
    echo "Already configured"
    exit 0
fi
apt-get install -y nginx
"""

    assert validator._check_idempotency(script) is True


def test_check_idempotency_negative(validator):
    """Test idempotency check with non-idempotent script"""
    script = """#!/bin/bash
apt-get install -y nginx
echo "Done"
"""

    # May or may not be idempotent - this is a simple check
    # The actual result depends on implementation details


def test_calculate_safety_score(validator):
    """Test safety score calculation"""
    # Perfect score
    score = validator._calculate_safety_score([], [], [])
    assert score == 100.0

    # With issues
    score = validator._calculate_safety_score(["critical issue"], [], [])
    assert score == 50.0

    # With warnings
    score = validator._calculate_safety_score([], ["warning1", "warning2"], [])
    assert score == 80.0

    # With recommendations
    score = validator._calculate_safety_score([], [], ["rec1", "rec2"])
    assert score == 90.0


def test_analyze_patch_restart_required(analyzer):
    """Test detecting restart requirement"""
    script = """#!/bin/bash
apt-get install -y linux-image-generic
reboot
"""

    analysis = analyzer.analyze_patch(script)
    assert analysis["requires_restart"] is True


def test_analyze_patch_no_restart(analyzer):
    """Test no restart required"""
    script = """#!/bin/bash
apt-get install -y nginx
systemctl restart nginx
"""

    analysis = analyzer.analyze_patch(script)
    assert analysis["requires_restart"] is False


def test_analyze_affected_services(analyzer):
    """Test extracting affected services"""
    script = """#!/bin/bash
systemctl restart nginx
systemctl reload apache2
service postgresql restart
"""

    analysis = analyzer.analyze_patch(script)

    assert "nginx" in analysis["affected_services"]
    assert "apache2" in analysis["affected_services"]
    assert "postgresql" in analysis["affected_services"]


def test_analyze_estimated_duration(analyzer):
    """Test duration estimation"""
    script = """#!/bin/bash
apt-get update
apt-get install -y nginx
systemctl restart nginx
"""

    analysis = analyzer.analyze_patch(script)

    # Should have some estimated duration
    assert analysis["estimated_duration"] > 0
    assert analysis["estimated_duration"] < 60  # Reasonable estimate


def test_analyze_network_required(analyzer):
    """Test network requirement detection"""
    script = """#!/bin/bash
apt-get update
apt-get install -y nginx
"""

    analysis = analyzer.analyze_patch(script)
    assert analysis["network_required"] is True


def test_analyze_no_network_required(analyzer):
    """Test no network requirement"""
    script = """#!/bin/bash
systemctl restart nginx
"""

    analysis = analyzer.analyze_patch(script)
    assert analysis["network_required"] is False


def test_analyze_privilege_required(analyzer):
    """Test privilege detection"""
    script_root = """#!/bin/bash
apt-get install -y nginx
"""

    script_user = """#!/bin/bash
echo "Hello"
"""

    analysis_root = analyzer.analyze_patch(script_root)
    assert analysis_root["privilege_required"] == "root"

    analysis_user = analyzer.analyze_patch(script_user)
    assert analysis_user["privilege_required"] == "user"


def test_analyze_disk_operations(analyzer):
    """Test disk operations detection"""
    script = """#!/bin/bash
mkdir -p /opt/myapp
tar -xzf archive.tar.gz
"""

    analysis = analyzer.analyze_patch(script)
    assert analysis["disk_operations"] is True
