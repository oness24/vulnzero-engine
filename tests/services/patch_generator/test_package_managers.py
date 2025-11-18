"""
Tests for package manager adapters
"""

import pytest
from services.patch_generator.package_managers import (
    AptManager,
    YumManager,
    ZypperManager,
    get_package_manager,
)


def test_apt_manager_update_command():
    """Test APT update command generation"""
    manager = AptManager()

    # Without version
    cmd = manager.get_update_command("nginx")
    assert "apt-get install" in cmd
    assert "--only-upgrade" in cmd
    assert "nginx" in cmd

    # With version
    cmd = manager.get_update_command("nginx", "1.18.0-1")
    assert "nginx=1.18.0-1" in cmd


def test_apt_manager_install_command():
    """Test APT install command generation"""
    manager = AptManager()

    # Without version
    cmd = manager.get_install_command("nginx")
    assert "apt-get install -y nginx" in cmd

    # With version
    cmd = manager.get_install_command("nginx", "1.18.0-1")
    assert "nginx=1.18.0-1" in cmd


def test_apt_manager_version_check():
    """Test APT version check command"""
    manager = AptManager()

    cmd = manager.get_version_check_command("nginx")
    assert "dpkg-query" in cmd
    assert "nginx" in cmd


def test_apt_manager_rollback_command():
    """Test APT rollback command"""
    manager = AptManager()

    cmd = manager.get_rollback_command("nginx", "1.18.0-0")
    assert "apt-get install" in cmd
    assert "--allow-downgrades" in cmd
    assert "nginx=1.18.0-0" in cmd


def test_apt_manager_hold_commands():
    """Test APT hold/unhold commands"""
    manager = AptManager()

    hold = manager.get_package_hold_command("nginx")
    assert "apt-mark hold nginx" in hold

    unhold = manager.get_package_unhold_command("nginx")
    assert "apt-mark unhold nginx" in unhold


def test_apt_manager_build_patch_script():
    """Test APT patch script generation"""
    manager = AptManager()

    script = manager.build_patch_script("nginx", "1.18.0-1", pre_checks=True)

    # Should have shebang
    assert script.startswith("#!/bin/bash")

    # Should have error handling
    assert "set -euo pipefail" in script

    # Should have pre-flight checks
    assert "apt-get" in script
    assert "EUID" in script

    # Should update package lists
    assert "apt-get update" in script

    # Should install package
    assert "nginx" in script


def test_apt_manager_build_rollback_script():
    """Test APT rollback script generation"""
    manager = AptManager()

    script = manager.build_rollback_script("nginx", "1.18.0-0")

    assert script.startswith("#!/bin/bash")
    assert "set -euo pipefail" in script
    assert "nginx" in script
    assert "1.18.0-0" in script


def test_yum_manager_commands():
    """Test YUM/DNF manager commands"""
    manager = YumManager(use_dnf=True)

    # Update command
    cmd = manager.get_update_command("httpd")
    assert "dnf update -y httpd" in cmd

    # Install command
    cmd = manager.get_install_command("httpd", "2.4.48-1")
    assert "dnf install -y httpd-2.4.48-1" in cmd

    # Version check
    cmd = manager.get_version_check_command("httpd")
    assert "rpm -q" in cmd
    assert "httpd" in cmd

    # Rollback
    cmd = manager.get_rollback_command("httpd", "2.4.46-1")
    assert "dnf downgrade -y httpd-2.4.46-1" in cmd


def test_yum_manager_with_yum():
    """Test YUM manager using yum instead of dnf"""
    manager = YumManager(use_dnf=False)

    cmd = manager.get_update_command("httpd")
    assert "yum update -y httpd" in cmd


def test_yum_manager_build_patch_script():
    """Test YUM patch script generation"""
    manager = YumManager(use_dnf=True)

    script = manager.build_patch_script("httpd", "2.4.48-1")

    assert "#!/bin/bash" in script
    assert "set -euo pipefail" in script
    assert "dnf" in script
    assert "httpd" in script


def test_zypper_manager_commands():
    """Test Zypper manager commands"""
    manager = ZypperManager()

    # Update command
    cmd = manager.get_update_command("apache2")
    assert "zypper update -y apache2" in cmd

    # Install command
    cmd = manager.get_install_command("apache2", "2.4.48-1")
    assert "zypper install -y apache2=2.4.48-1" in cmd

    # Rollback
    cmd = manager.get_rollback_command("apache2", "2.4.46-1")
    assert "zypper install -y --oldpackage apache2=2.4.46-1" in cmd


def test_zypper_manager_build_patch_script():
    """Test Zypper patch script generation"""
    manager = ZypperManager()

    script = manager.build_patch_script("apache2")

    assert "#!/bin/bash" in script
    assert "zypper" in script
    assert "apache2" in script
    assert "zypper refresh" in script  # Should refresh repos


def test_get_package_manager_debian():
    """Test getting package manager for Debian/Ubuntu"""
    manager = get_package_manager("ubuntu")
    assert isinstance(manager, AptManager)

    manager = get_package_manager("debian")
    assert isinstance(manager, AptManager)


def test_get_package_manager_rhel():
    """Test getting package manager for RHEL/CentOS"""
    manager = get_package_manager("rhel")
    assert isinstance(manager, YumManager)
    assert manager.command == "dnf"

    manager = get_package_manager("rhel", "7.9")
    assert isinstance(manager, YumManager)
    assert manager.command == "yum"


def test_get_package_manager_fedora():
    """Test getting package manager for Fedora"""
    manager = get_package_manager("fedora")
    assert isinstance(manager, YumManager)
    assert manager.command == "dnf"


def test_get_package_manager_opensuse():
    """Test getting package manager for openSUSE"""
    manager = get_package_manager("opensuse")
    assert isinstance(manager, ZypperManager)

    manager = get_package_manager("sles")
    assert isinstance(manager, ZypperManager)


def test_get_package_manager_unknown():
    """Test getting package manager for unknown OS (defaults to APT)"""
    manager = get_package_manager("unknown-os")
    assert isinstance(manager, AptManager)


def test_patch_script_without_pre_checks():
    """Test generating patch script without pre-flight checks"""
    manager = AptManager()

    script = manager.build_patch_script("nginx", pre_checks=False)

    # Should not have EUID check
    assert "EUID" not in script

    # Should still have basic structure
    assert "#!/bin/bash" in script
    assert "nginx" in script
