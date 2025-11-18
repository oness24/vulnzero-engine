# VulnZero AI Patch Generator Service

The AI Patch Generator Service uses Large Language Models (LLMs) to automatically generate context-aware remediation scripts for security vulnerabilities.

## Features

### LLM Integration
- **OpenAI GPT-4**: High-quality patch generation with GPT-4/GPT-3.5-turbo
- **Anthropic Claude**: Alternative LLM provider (Claude 3 Opus/Sonnet/Haiku)
- **Unified Interface**: Seamless switching between providers
- **Automatic Retry**: Exponential backoff on rate limits and failures

### Vulnerability Analysis
- **Patch Type Detection**: Automatically determines if vulnerability needs package update, config change, workaround, or kernel patch
- **Package Manager Detection**: Supports apt (Debian/Ubuntu), yum (RHEL/CentOS), dnf (Fedora), zypper (SUSE)
- **Confidence Scoring**: Calculates confidence based on available CVE data
- **Complexity Assessment**: Classifies patches as low/medium/high complexity
- **Reboot Detection**: Identifies if patch requires system reboot

### Patch Generation
- **Context-Aware Scripts**: Generates bash scripts tailored to specific vulnerabilities
- **Multiple Patch Types**:
  * Package Updates: Safe package manager commands with version locking
  * Configuration Changes: Backup, modify, and validate config files
  * Workarounds: Temporary mitigations until patches available
  * Kernel Patches: Kernel update procedures with fallback
- **Error Handling**: All scripts include `set -e`, `set -u`, error checking
- **Rollback Scripts**: Automatic generation of rollback procedures
- **Production-Ready**: Scripts designed for production environments

### Safety Validation
- **Dangerous Command Detection**: Blocks destructive commands (rm -rf /, dd, mkfs)
- **Suspicious Pattern Detection**: Flags risky patterns (curl | bash, chmod 777)
- **Syntax Checking**: Basic bash syntax validation
- **Safety Scoring**: Rates patch safety (0-1 scale)
- **Quality Checks**: Verifies error handling, logging, backups

## Architecture

```
services/patch-generator/
├── llm/                    # LLM integrations
│   ├── base.py            # Base LLM interface
│   ├── openai_client.py   # OpenAI GPT integration
│   ├── anthropic_client.py # Anthropic Claude integration
│   └── factory.py         # LLM client factory
├── analyzers/              # Vulnerability analysis
│   └── vulnerability_analyzer.py
├── generators/             # Patch generation
│   └── patch_generator.py # Main patch generator
├── validators/             # Safety validation
│   └── patch_validator.py
└── tasks/                  # Celery tasks
    ├── celery_app.py
    └── generation_tasks.py
```

## Configuration

Environment variables required:

```bash
# OpenAI (if using OpenAI provider)
OPENAI_API_KEY=sk-...

# Anthropic (if using Anthropic provider)
ANTHROPIC_API_KEY=sk-ant-...

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Usage

### Generate Patch for Vulnerability

```python
import asyncio
from services.patch_generator.analyzers.vulnerability_analyzer import VulnerabilityAnalyzer
from services.patch_generator.generators.patch_generator import AIPatchGenerator
from services.patch_generator.validators.patch_validator import validate_patch
from shared.models import Vulnerability

async def generate_patch(vulnerability: Vulnerability):
    # Analyze vulnerability
    analyzer = VulnerabilityAnalyzer()
    analysis = await analyzer.analyze(vulnerability)

    print(f"Patch Type: {analysis.patch_type.value}")
    print(f"Confidence: {analysis.confidence:.2f}")

    # Generate patch using OpenAI
    async with AIPatchGenerator(llm_provider="openai") as generator:
        result = await generator.generate_patch(vulnerability, analysis)

    print(f"Generated patch ({result.tokens_used} tokens)")
    print(f"Confidence Score: {result.confidence_score:.2f}")

    # Validate patch
    validation = validate_patch(result.patch_content)

    if validation.is_valid:
        print("✅ Patch is safe to deploy")
    else:
        print("❌ Patch has issues:")
        for error in validation.errors:
            print(f"  - {error}")

    return result

# Run
vuln = get_vulnerability_from_db()
result = asyncio.run(generate_patch(vuln))
```

### Using Celery Tasks

```python
from services.patch_generator.tasks.generation_tasks import generate_patch_for_vulnerability

# Trigger patch generation (async task)
task = generate_patch_for_vulnerability.delay(
    vulnerability_id=123,
    llm_provider="openai"
)

# Check result
result = task.get(timeout=300)
print(result)
# {
#   'success': True,
#   'patch_id': 456,
#   'confidence_score': 0.85,
#   'is_valid': True,
#   ...
# }
```

### LLM Provider Selection

```python
# Use OpenAI GPT-4
generator = AIPatchGenerator(
    llm_provider="openai",
    llm_model="gpt-4"
)

# Use Anthropic Claude
generator = AIPatchGenerator(
    llm_provider="anthropic",
    llm_model="claude-3-sonnet-20240229"
)

# Auto-detect from environment
from services.patch_generator.llm.factory import get_llm_client
client = get_llm_client("openai")  # Uses OPENAI_API_KEY env var
```

## Patch Types

### Package Update

Generated for vulnerabilities fixable via package manager:

```bash
#!/bin/bash
set -euo pipefail

# Backup package state
dpkg --get-selections > /tmp/package-backup-$(date +%Y%m%d-%H%M%S).txt

# Update package
apt-get update
apt-get install --only-upgrade openssl=1.1.1f-1ubuntu2.20

# Verify installation
dpkg -s openssl | grep Version
```

### Configuration Change

Generated for config-based vulnerabilities:

```bash
#!/bin/bash
set -euo pipefail

CONFIG_FILE="/etc/ssh/sshd_config"
BACKUP_FILE="${CONFIG_FILE}.backup-$(date +%Y%m%d-%H%M%S)"

# Backup original
cp "$CONFIG_FILE" "$BACKUP_FILE"

# Modify configuration
sed -i 's/^PermitRootLogin yes/PermitRootLogin no/' "$CONFIG_FILE"

# Validate syntax
sshd -t

# Restart service
systemctl restart sshd
```

### Workaround

Temporary mitigations:

```bash
#!/bin/bash
set -euo pipefail

# Temporary workaround for CVE-XXXX-XXXXX
# TODO: Replace with proper patch when available

# Disable vulnerable service
systemctl stop vulnerable-service
systemctl disable vulnerable-service

# Log workaround status
echo "$(date): Workaround applied for CVE-XXXX-XXXXX" >> /var/log/vulnzero-workarounds.log
```

## Safety Features

### Dangerous Command Blocking

The validator automatically blocks:
- `rm -rf /` - Recursive root deletion
- `dd if=` - Direct disk writes
- `mkfs.*` - Filesystem formatting
- `fdisk` - Partition manipulation

### Suspicious Pattern Detection

Warns about:
- `curl ... | bash` - Piping to bash
- `chmod 777` - Overly permissive permissions
- `eval $(...)` - Dynamic code execution

### Quality Requirements

All patches must include:
- Shebang (`#!/bin/bash`)
- Error handling (`set -e`, `set -u`)
- Backups before modifications
- Logging/output for monitoring
- Validation after changes

## Celery Tasks

### On-Demand Patch Generation

```python
# Generate patch for specific vulnerability
generate_patch_for_vulnerability.delay(vulnerability_id=123)
```

### Scheduled Batch Generation

```python
# Generate patches for all critical vulnerabilities (scheduled daily)
generate_patches_for_critical_vulnerabilities.delay()
```

## Supported Operating Systems

- **Debian/Ubuntu**: apt package manager
- **RHEL/CentOS**: yum/dnf package managers
- **Fedora**: dnf package manager
- **SUSE/SLES**: zypper package manager

## LLM Model Recommendations

### OpenAI

- **gpt-4**: Highest quality, best for complex patches
- **gpt-4-turbo-preview**: Fast, cost-effective
- **gpt-3.5-turbo**: Budget option for simple patches

### Anthropic

- **claude-3-opus**: Highest capability
- **claude-3-sonnet**: Balanced quality/cost (recommended)
- **claude-3-haiku**: Fast, economical

## Limitations

- **MVP Focus**: Linux OS vulnerabilities only
- **Package Managers**: Limited to apt, yum, dnf, zypper
- **Validation**: Basic syntax checking (not full execution testing)
- **LLM Dependencies**: Requires internet access for API calls
- **Cost**: LLM API usage incurs costs (typically $0.01-0.10 per patch)

## Future Enhancements

- [ ] Windows patch support (PowerShell scripts)
- [ ] Advanced syntax validation (shellcheck integration)
- [ ] Patch testing in sandboxed environments
- [ ] Multi-language support (Python, Ansible, Terraform)
- [ ] Fine-tuned models for specific vulnerability types
- [ ] Cost optimization (caching, model selection)
- [ ] Human-in-the-loop approval workflows

## Monitoring

Key metrics to track:
- Patch generation success rate
- Average confidence scores
- Validation pass rate
- LLM token usage and costs
- Generation latency

## Troubleshooting

### LLM Rate Limits

```python
# Automatic retry with exponential backoff
result = await client.generate_with_retry(messages, max_retries=5)
```

### Low Confidence Scores

- Check CVE data completeness
- Verify package information available
- Consider manual review for complex vulnerabilities

### Validation Failures

- Review validation errors
- Check for dangerous commands
- Manually inspect generated scripts
- Adjust LLM prompts if needed

## Security Considerations

- **Code Review**: Always review AI-generated patches before deployment
- **Testing**: Test in staging environment first
- **Rollback**: Ensure rollback scripts are available
- **Monitoring**: Monitor systems after patch deployment
- **Audit Trail**: All patch generations are logged

## Contributing

When adding new features:
1. Update LLM prompts in `patch_generator.py`
2. Add validation rules in `patch_validator.py`
3. Update tests
4. Document in README
