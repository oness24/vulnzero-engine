"""Unit tests for CVE fetcher."""
import pytest

from vulnzero.services.patch_generator.cve_fetcher import CVEFetcher


@pytest.mark.unit
def test_get_package_manager_for_os():
    """Test package manager detection for different OS types."""
    fetcher = CVEFetcher()

    assert fetcher.get_package_manager_for_os("ubuntu") == "apt"
    assert fetcher.get_package_manager_for_os("debian") == "apt"
    assert fetcher.get_package_manager_for_os("rhel") == "yum"
    assert fetcher.get_package_manager_for_os("centos") == "yum"
    assert fetcher.get_package_manager_for_os("fedora") == "dnf"
    assert fetcher.get_package_manager_for_os("rocky") == "dnf"
    assert fetcher.get_package_manager_for_os("suse") == "zypper"


@pytest.mark.unit
def test_cve_fetcher_context_manager():
    """Test CVE fetcher as context manager."""
    with CVEFetcher() as fetcher:
        assert fetcher is not None
        assert fetcher.client is not None
