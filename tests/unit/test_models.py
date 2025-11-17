"""Unit tests for database models."""
import pytest

from vulnzero.shared.models import Asset, Vulnerability


@pytest.mark.unit
def test_create_vulnerability(db_session, sample_vulnerability_data):
    """Test creating a vulnerability."""
    vuln = Vulnerability(**sample_vulnerability_data)
    db_session.add(vuln)
    db_session.commit()

    assert vuln.id is not None
    assert vuln.cve_id == "CVE-2024-0001"
    assert vuln.severity == "high"
    assert vuln.cvss_score == 8.5


@pytest.mark.unit
def test_create_asset(db_session, sample_asset_data):
    """Test creating an asset."""
    asset = Asset(**sample_asset_data)
    db_session.add(asset)
    db_session.commit()

    assert asset.id is not None
    assert asset.hostname == "test-server-01"
    assert asset.os_type == "ubuntu"


@pytest.mark.unit
def test_vulnerability_unique_cve(db_session, sample_vulnerability_data):
    """Test that CVE IDs must be unique."""
    vuln1 = Vulnerability(**sample_vulnerability_data)
    db_session.add(vuln1)
    db_session.commit()

    # Try to create another with same CVE ID
    vuln2 = Vulnerability(**sample_vulnerability_data)
    db_session.add(vuln2)

    with pytest.raises(Exception):  # Should raise IntegrityError
        db_session.commit()
