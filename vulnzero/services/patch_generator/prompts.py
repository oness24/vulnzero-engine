"""Prompt templates for patch generation."""
from typing import Dict, Any


def get_package_update_prompt(context: Dict[str, Any]) -> str:
    """
    Generate prompt for package update patches.

    Args:
        context: Dictionary with vulnerability context containing:
            - cve_id: CVE identifier
            - description: Vulnerability description
            - package_name: Affected package name
            - vulnerable_version: Current vulnerable version
            - fixed_version: Version with fix
            - os_type: Operating system (ubuntu, rhel, etc.)
            - os_version: OS version (22.04, 8, etc.)
            - package_manager: Package manager (apt, yum, dnf)

    Returns:
        Formatted prompt string
    """
    return f"""You are a Linux system administrator tasked with creating a remediation script for a security vulnerability.

VULNERABILITY DETAILS:
- CVE ID: {context.get('cve_id', 'Unknown')}
- Description: {context.get('description', 'No description available')}
- Affected Package: {context.get('package_name', 'unknown')} version {context.get('vulnerable_version', 'unknown')}
- Fixed Version: {context.get('fixed_version', 'latest')}

TARGET SYSTEM:
- Operating System: {context.get('os_type', 'ubuntu')} {context.get('os_version', '22.04')}
- Package Manager: {context.get('package_manager', 'apt')}

REQUIREMENTS:
1. Create a production-ready bash script that safely updates the vulnerable package
2. Include pre-flight checks:
   - Verify current package version
   - Check if update is needed
   - Verify package manager is available
3. Create backup of package state before making changes
4. Update the package to the fixed version using the appropriate package manager
5. Handle service restarts gracefully if required (minimize downtime)
6. Include post-update verification:
   - Confirm package updated successfully
   - Verify service is running (if applicable)
7. Comprehensive error handling with clear error messages
8. Log all actions to /var/log/vulnzero/remediation.log
9. Make the script idempotent (safe to run multiple times)
10. Use exit codes: 0 (success), 1 (failure), 2 (already patched)

SAFETY CONSTRAINTS:
- DO NOT use destructive commands like `rm -rf /`
- DO NOT disable security features
- DO NOT make permanent system-wide changes beyond package updates
- Include rollback information in comments
- Add safety checks before critical operations

OUTPUT FORMAT:
Provide ONLY the bash script, with clear comments explaining each step.
Start with a shebang (#!/bin/bash) and end with an appropriate exit code.
Do not include any explanation before or after the script."""

    return prompt


def get_config_change_prompt(context: Dict[str, Any]) -> str:
    """
    Generate prompt for configuration change patches.

    Args:
        context: Dictionary with vulnerability context

    Returns:
        Formatted prompt string
    """
    return f"""You are a Linux system administrator creating a configuration remediation script.

VULNERABILITY DETAILS:
- CVE ID: {context.get('cve_id', 'Unknown')}
- Description: {context.get('description', 'No description available')}
- Affected Service: {context.get('service_name', 'unknown')}
- Configuration File: {context.get('config_file', '/etc/service/config')}

TARGET SYSTEM:
- Operating System: {context.get('os_type', 'ubuntu')} {context.get('os_version', '22.04')}

REQUIREMENTS:
1. Create a bash script that safely modifies the configuration to fix the vulnerability
2. Backup the original configuration file before making changes
3. Validate the new configuration before applying
4. Restart the service gracefully if needed
5. Verify the service starts successfully after changes
6. Include rollback instructions in comments
7. Make the script idempotent

SAFETY CONSTRAINTS:
- Create backup of original config before changes
- Validate configuration syntax before applying
- DO NOT make irreversible changes
- Include detailed logging

OUTPUT FORMAT:
Provide ONLY the bash script with clear comments.
Start with #!/bin/bash and use appropriate exit codes."""


def get_workaround_prompt(context: Dict[str, Any]) -> str:
    """
    Generate prompt for workaround patches (when no fix is available).

    Args:
        context: Dictionary with vulnerability context

    Returns:
        Formatted prompt string
    """
    return f"""You are a Linux system administrator creating a workaround for a vulnerability.

VULNERABILITY DETAILS:
- CVE ID: {context.get('cve_id', 'Unknown')}
- Description: {context.get('description', 'No description available')}
- Affected Component: {context.get('component', 'unknown')}
- Workaround Strategy: {context.get('workaround_type', 'mitigation')}

TARGET SYSTEM:
- Operating System: {context.get('os_type', 'ubuntu')} {context.get('os_version', '22.04')}

REQUIREMENTS:
1. Create a bash script that implements a workaround to mitigate the vulnerability
2. The workaround should reduce risk without breaking functionality
3. Document the limitations of this workaround
4. Make changes reversible
5. Include monitoring recommendations
6. Log all actions

SAFETY CONSTRAINTS:
- Minimize impact on system functionality
- Make changes reversible
- Document side effects

OUTPUT FORMAT:
Provide ONLY the bash script with detailed comments explaining the workaround."""


def get_rollback_prompt(patch_content: str, context: Dict[str, Any]) -> str:
    """
    Generate prompt for rollback script creation.

    Args:
        patch_content: The original patch script
        context: Dictionary with context

    Returns:
        Formatted prompt string
    """
    return f"""You are a Linux system administrator creating a rollback script.

ORIGINAL PATCH:
```bash
{patch_content}
```

TASK:
Create a rollback script that safely reverses the changes made by the above patch.

REQUIREMENTS:
1. Restore the system to its pre-patch state
2. Use backups created by the original patch
3. Verify rollback was successful
4. Handle cases where rollback may not be possible
5. Clear error messages if rollback fails

OUTPUT FORMAT:
Provide ONLY the rollback bash script with clear comments."""


def get_validation_prompt(script: str) -> str:
    """
    Generate prompt for script validation and safety analysis.

    Args:
        script: The bash script to validate

    Returns:
        Formatted prompt string for validation
    """
    return f"""You are a security expert reviewing a bash script for safety issues.

SCRIPT TO REVIEW:
```bash
{script}
```

ANALYSIS REQUIRED:
1. Identify any potentially dangerous commands (rm -rf, dd, mkfs, etc.)
2. Check for proper error handling
3. Verify idempotency
4. Check for hardcoded credentials or sensitive data
5. Assess overall safety on a scale of 0-100

OUTPUT FORMAT:
Provide a JSON response with the following structure:
{{
    "safe": true/false,
    "safety_score": 0-100,
    "issues_found": [
        {{"severity": "critical/high/medium/low", "description": "issue description"}}
    ],
    "recommendations": ["recommendation 1", "recommendation 2"],
    "dangerous_commands": ["command1", "command2"]
}}

Respond with ONLY the JSON, no additional text."""
