# Patch Generator Guide

The VulnZero Patch Generator is an AI-powered service that automatically generates remediation scripts for security vulnerabilities.

## Features

- **AI-Powered Generation**: Uses OpenAI GPT-4 or Anthropic Claude to generate context-aware patches
- **Multi-Stage Validation**: Validates syntax, detects dangerous commands, and scores safety
- **CVE Data Integration**: Automatically fetches vulnerability details from NVD
- **Template Library**: Pre-defined templates for common vulnerability patterns (cost optimization)
- **Confidence Scoring**: Calculates confidence scores based on validation results
- **Rollback Scripts**: Automatically generates rollback procedures

## Quick Start

### 1. Set Up API Key

The patch generator requires an LLM API key:

```bash
# Option A: OpenAI (Recommended)
export OPENAI_API_KEY="sk-your-openai-key-here"

# Option B: Anthropic
export ANTHROPIC_API_KEY="sk-ant-your-anthropic-key-here"
```

### 2. Generate Your First Patch

```bash
# Generate a patch for a CVE
vulnzero generate-patch CVE-2023-4911

# Specify target OS
vulnzero generate-patch CVE-2023-4911 --os-type ubuntu --os-version 22.04

# Save to file
vulnzero generate-patch CVE-2023-4911 -o patch.sh
```

### 3. Review the Output

The CLI will display:
- CVE information (severity, CVSS score, description)
- Validation results (safety score, issues found)
- Confidence score
- The generated bash script
- Recommendations

## Using in Python Code

```python
from vulnzero.services.patch_generator import PatchGenerator
from vulnzero.shared.models import Vulnerability

# Create vulnerability object
vuln = Vulnerability(
    cve_id="CVE-2023-4911",
    title="Buffer overflow in glibc",
    description="...",
    severity="high",
    package_name="glibc",
    vulnerable_version="2.35",
    fixed_version="2.35-0ubuntu3.6"
)

# Generate patch
generator = PatchGenerator()
result = generator.generate_patch(
    vulnerability=vuln,
    os_type="ubuntu",
    os_version="22.04"
)

if result.success:
    print(f"Generated patch with {result.patch.confidence_score:.2%} confidence")
    print(result.patch.patch_content)
else:
    print(f"Failed: {result.error_message}")
```

## Architecture

### Components

1. **LLM Client (`llm_client.py`)**
   - Abstraction layer for OpenAI and Anthropic APIs
   - Handles API calls with retry logic
   - Model selection based on configuration

2. **Prompt Templates (`prompts.py`)**
   - Pre-defined prompts for different patch types
   - Package updates, config changes, workarounds
   - Structured to produce safe, production-ready scripts

3. **Validator (`validator.py`)**
   - Syntax validation (bash -n)
   - Shellcheck integration
   - Dangerous command detection
   - Safety scoring algorithm

4. **CVE Fetcher (`cve_fetcher.py`)**
   - NVD API integration
   - CVE data parsing
   - Package information extraction

5. **Template Library (`templates.py`)**
   - Pre-defined scripts for common scenarios
   - Reduces LLM API costs
   - Instant generation for known patterns

6. **Generator (`generator.py`)**
   - Main orchestration service
   - Combines all components
   - Confidence scoring
   - Result packaging

## Safety Features

### Multi-Stage Validation

Every generated patch goes through:

1. **Syntax Validation**: Checks bash syntax with `bash -n`
2. **Shellcheck**: Runs shellcheck for best practices
3. **Dangerous Command Detection**: Regex patterns for risky commands
4. **Safety Scoring**: Algorithm to calculate overall safety (0-100%)

### Forbidden Commands

These commands will cause validation to fail:

- `rm -rf /` (recursive delete on root)
- `dd if=` (disk operations)
- `mkfs` (filesystem creation)
- `fdisk` (disk partitioning)
- `chmod 777` (overly permissive)
- `curl | bash` (piping to shell)

### Suspicious Patterns

These generate warnings:

- `rm -rf` (recursive delete)
- `sed -i` (in-place editing)
- `>/etc/` (writing to /etc)
- `systemctl disable` (disabling services)
- `iptables FLUSH` (flushing firewall)

## Confidence Scoring

Confidence scores are calculated based on:

- **Validation Safety Score (40%)**: Result from safety checks
- **Syntax Validity (20%)**: Whether script has valid syntax
- **CVE Severity (15%)**: Well-known CVEs have more tested patterns
- **Script Complexity (15%)**: Simpler scripts are more confident
- **No Dangerous Commands (10%)**: Absence of forbidden patterns

Example scores:
- **90-100%**: Safe to deploy with standard review
- **70-89%**: Review carefully before deployment
- **50-69%**: Requires security team review
- **<50%**: Do not deploy, needs manual patch creation

## Cost Optimization

### Using Templates

For common package updates, templates are used instead of LLM calls:

```python
from vulnzero.services.patch_generator.templates import template_library

# Check if template exists
if template_library.has_template(cve_id, os_type):
    # Use template (free, instant)
    script = template_library.render_template("apt_package_update", context)
else:
    # Fall back to LLM generation
    script = llm_client.generate(prompt)
```

### Model Selection

Choose models based on complexity:

```bash
# Simple package update: Use GPT-3.5-turbo ($0.002/call)
export OPENAI_MODEL="gpt-3.5-turbo"

# Complex custom patches: Use GPT-4 ($0.03/call)
export OPENAI_MODEL="gpt-4"
```

**Estimated Costs**:
- With templates: ~$0.01 per 10 patches
- Without templates: ~$0.30 per 10 patches (GPT-4)

## Examples

### Example 1: Simple Package Update

```bash
$ vulnzero generate-patch CVE-2023-32681

CVE Information
CVE ID: CVE-2023-32681
Severity: MEDIUM
CVSS Score: 6.5
Description: Requests library vulnerability...

✓ Validation Results:
  Safety Score: 95.00%
  Syntax Valid: ✓
  Issues Found: 1
  Confidence: 87.50%

Generated Patch:
#!/bin/bash
set -euo pipefail

PACKAGE_NAME="python3-requests"
apt-get update
apt-get install -y --only-upgrade $PACKAGE_NAME
...
```

### Example 2: Using in Code

```python
from vulnzero.services.patch_generator import PatchGenerator, get_llm_client
from vulnzero.shared.models import Vulnerability

# Custom LLM configuration
llm_client = get_llm_client(provider="anthropic")

generator = PatchGenerator(llm_client=llm_client)

vuln = Vulnerability(
    cve_id="CVE-2024-1234",
    title="Example vulnerability",
    severity="critical",
    package_name="nginx",
    vulnerable_version="1.20.0",
    fixed_version="1.20.2"
)

result = generator.generate_patch(vuln, os_type="ubuntu", os_version="22.04")

if result.success and result.validation_result.is_valid:
    # Save to file
    with open(f"patch_{vuln.cve_id}.sh", "w") as f:
        f.write(result.patch.patch_content)

    # Save rollback script
    with open(f"rollback_{vuln.cve_id}.sh", "w") as f:
        f.write(result.patch.rollback_script)

    print(f"Confidence: {result.patch.confidence_score:.2%}")
```

## Best Practices

### 1. Always Review Generated Patches

**Never deploy AI-generated code to production without human review**, even with high confidence scores.

### 2. Test in Staging First

```bash
# Generate patch
vulnzero generate-patch CVE-2024-1234 -o patch.sh

# Test in isolated environment
docker run -it ubuntu:22.04 bash < patch.sh
```

### 3. Use Version Control

```bash
# Save patches to git
mkdir -p patches/
vulnzero generate-patch CVE-2024-1234 -o patches/CVE-2024-1234.sh
git add patches/
git commit -m "Add patch for CVE-2024-1234"
```

### 4. Monitor Validation Scores

Track validation scores over time to improve prompt templates:

```python
# Save validation metrics
metrics = {
    "cve_id": result.cve_data.cve_id,
    "safety_score": result.validation_result.safety_score,
    "confidence": result.patch.confidence_score,
    "issues_count": len(result.validation_result.issues),
}
```

### 5. Implement Approval Workflows

For production deployments:

```python
if result.patch.confidence_score >= 0.9:
    # High confidence: Standard review
    send_for_review(result.patch, reviewers=["security-team"])
elif result.patch.confidence_score >= 0.7:
    # Medium confidence: Thorough review
    send_for_review(result.patch, reviewers=["security-team", "senior-devops"])
else:
    # Low confidence: Reject or manual creation
    reject_patch(result.patch)
```

## Troubleshooting

### "OpenAI API key not provided"

```bash
# Set environment variable
export OPENAI_API_KEY="sk-your-key"

# Or in .env file
echo "OPENAI_API_KEY=sk-your-key" >> .env
```

### "CVE data not found"

Some CVEs may not be in the NVD database yet. Try:

```python
# Manual CVE data
vuln = Vulnerability(
    cve_id="CVE-NEW-2024",
    package_name="manual-package",
    vulnerable_version="1.0.0",
    fixed_version="1.0.1",
    description="Manual description"
)
```

### "Validation failed: dangerous commands"

The patch contains forbidden commands. Options:

1. Review the LLM response - may be hallucinating
2. Adjust prompts to be more explicit about safety
3. Create manual patch for this case

### High API Costs

To reduce costs:

1. Use template library for common patterns
2. Switch to GPT-3.5-turbo for simple updates
3. Cache patches for identical CVE+OS combinations
4. Batch process multiple CVEs

## Next Steps

- [Development Guide](DEVELOPMENT.md) - Set up development environment
- [API Documentation](api/README.md) - REST API reference
- [Contributing](../CONTRIBUTING.md) - How to contribute

---

**Remember**: VulnZero patch generation is a tool to assist security teams, not replace them. Always review, test, and validate patches before production deployment.
