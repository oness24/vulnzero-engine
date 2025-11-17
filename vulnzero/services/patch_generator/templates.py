"""Template library for common vulnerability patterns."""
from typing import Dict, Optional


class PatchTemplate:
    """Base class for patch templates."""

    def __init__(self, name: str, description: str, template: str):
        """
        Initialize template.

        Args:
            name: Template name
            description: Template description
            template: Template string with placeholders
        """
        self.name = name
        self.description = description
        self.template = template

    def render(self, context: Dict) -> str:
        """
        Render template with context.

        Args:
            context: Dictionary with template variables

        Returns:
            Rendered patch script
        """
        return self.template.format(**context)


# Template for simple package updates (apt)
APT_PACKAGE_UPDATE_TEMPLATE = PatchTemplate(
    name="apt_package_update",
    description="Update a package using apt (Debian/Ubuntu)",
    template="""#!/bin/bash
#
# VulnZero Remediation Script
# CVE: {cve_id}
# Package: {package_name}
# Generated: {timestamp}
#

set -euo pipefail

# Configuration
PACKAGE_NAME="{package_name}"
TARGET_VERSION="{fixed_version}"
LOG_FILE="/var/log/vulnzero/remediation_{cve_id}.log"
BACKUP_DIR="/var/backups/vulnzero"

# Logging function
log() {{
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}}

log "Starting remediation for CVE {cve_id}"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

# Pre-flight checks
log "Running pre-flight checks..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log "ERROR: This script must be run as root"
    exit 1
fi

# Check if package is installed
if ! dpkg -l | grep -q "^ii  $PACKAGE_NAME "; then
    log "Package $PACKAGE_NAME is not installed, nothing to do"
    exit 2
fi

# Get current version
CURRENT_VERSION=$(dpkg-query -W -f='${{Version}}' "$PACKAGE_NAME" 2>/dev/null || echo "unknown")
log "Current version: $CURRENT_VERSION"

# Backup package selections
log "Backing up package selections..."
dpkg --get-selections > "$BACKUP_DIR/package-selections-$(date +%Y%m%d-%H%M%S).txt"

# Update package lists
log "Updating package lists..."
apt-get update -qq || {{
    log "ERROR: Failed to update package lists"
    exit 1
}}

# Perform the update
log "Updating $PACKAGE_NAME to $TARGET_VERSION..."
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    --only-upgrade \
    "$PACKAGE_NAME" >> "$LOG_FILE" 2>&1 || {{
    log "ERROR: Failed to update package"
    exit 1
}}

# Verify update
NEW_VERSION=$(dpkg-query -W -f='${{Version}}' "$PACKAGE_NAME" 2>/dev/null || echo "unknown")
log "New version: $NEW_VERSION"

if [ "$NEW_VERSION" = "$CURRENT_VERSION" ]; then
    log "WARNING: Version did not change"
fi

# Clean up
log "Cleaning up..."
apt-get clean

log "Remediation completed successfully"
exit 0
""",
)

# Template for simple package updates (yum/dnf)
YUM_PACKAGE_UPDATE_TEMPLATE = PatchTemplate(
    name="yum_package_update",
    description="Update a package using yum (RHEL/CentOS)",
    template="""#!/bin/bash
#
# VulnZero Remediation Script
# CVE: {cve_id}
# Package: {package_name}
# Generated: {timestamp}
#

set -euo pipefail

# Configuration
PACKAGE_NAME="{package_name}"
LOG_FILE="/var/log/vulnzero/remediation_{cve_id}.log"

# Logging function
log() {{
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}}

log "Starting remediation for CVE {cve_id}"

# Create log directory
mkdir -p "$(dirname "$LOG_FILE")"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log "ERROR: This script must be run as root"
    exit 1
fi

# Check if package is installed
if ! rpm -q "$PACKAGE_NAME" &>/dev/null; then
    log "Package $PACKAGE_NAME is not installed, nothing to do"
    exit 2
fi

# Get current version
CURRENT_VERSION=$(rpm -q "$PACKAGE_NAME" || echo "unknown")
log "Current version: $CURRENT_VERSION"

# Perform the update
log "Updating $PACKAGE_NAME..."
yum update -y "$PACKAGE_NAME" >> "$LOG_FILE" 2>&1 || {{
    log "ERROR: Failed to update package"
    exit 1
}}

# Verify update
NEW_VERSION=$(rpm -q "$PACKAGE_NAME" || echo "unknown")
log "New version: $NEW_VERSION"

log "Remediation completed successfully"
exit 0
""",
)


class TemplateLibrary:
    """Library of pre-defined patch templates."""

    def __init__(self):
        """Initialize template library."""
        self.templates: Dict[str, PatchTemplate] = {
            "apt_package_update": APT_PACKAGE_UPDATE_TEMPLATE,
            "yum_package_update": YUM_PACKAGE_UPDATE_TEMPLATE,
        }

    def get_template(
        self, os_type: str, patch_type: str = "package_update"
    ) -> Optional[PatchTemplate]:
        """
        Get appropriate template based on OS and patch type.

        Args:
            os_type: Operating system type
            patch_type: Type of patch

        Returns:
            PatchTemplate if found, None otherwise
        """
        # Map OS types to package managers
        if os_type.lower() in ["ubuntu", "debian"]:
            return self.templates.get("apt_package_update")
        elif os_type.lower() in ["rhel", "centos", "rocky", "almalinux", "amazon"]:
            return self.templates.get("yum_package_update")

        return None

    def has_template(self, cve_id: str, os_type: str) -> bool:
        """
        Check if a template exists for this CVE/OS combination.

        Args:
            cve_id: CVE identifier
            os_type: Operating system type

        Returns:
            True if template exists
        """
        # For now, we have templates for common package update scenarios
        # In the future, this could check a database of CVE-specific templates
        return self.get_template(os_type) is not None

    def render_template(self, template_name: str, context: Dict) -> Optional[str]:
        """
        Render a template with context.

        Args:
            template_name: Name of template
            context: Template context

        Returns:
            Rendered script or None
        """
        template = self.templates.get(template_name)
        if not template:
            return None

        # Add timestamp to context
        from datetime import datetime

        context.setdefault("timestamp", datetime.utcnow().isoformat())

        return template.render(context)


# Global template library instance
template_library = TemplateLibrary()
