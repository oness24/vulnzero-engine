# VulnZero Vulnerability Aggregator Service

The Vulnerability Aggregator Service is responsible for ingesting, normalizing, enriching, and prioritizing vulnerabilities from multiple scanner sources.

## Features

### Scanner Integration
- **Wazuh**: Fetch vulnerabilities from Wazuh API
- **Qualys**: Integrate with Qualys vulnerability management
- **Tenable.io**: Import from Tenable cloud platform
- **CSV/JSON**: Generic import for any scanner data

### Data Processing
- **Normalization**: Convert scanner-specific formats to unified schema
- **Deduplication**: Merge duplicate vulnerabilities from multiple sources
- **Enrichment**: Add data from NVD, EPSS, and Exploit-DB
- **Prioritization**: ML-based scoring (0-100) for remediation order

### Scheduled Scanning
- Periodic vulnerability scans (configurable, default: every 6 hours)
- Daily enrichment of new vulnerabilities
- Daily priority recalculation

## Architecture

```
services/aggregator/
├── scanners/           # Scanner integrations
│   ├── base.py        # Base scanner interface
│   ├── wazuh_scanner.py
│   ├── qualys_scanner.py
│   ├── tenable_scanner.py
│   └── csv_scanner.py
├── processors/         # Data processing
│   ├── normalizer.py  # Format normalization
│   └── deduplicator.py # Duplicate detection
├── enrichment/         # External data sources
│   ├── nvd_client.py  # NVD API client
│   ├── epss_client.py # EPSS scores
│   ├── exploit_db_client.py # Exploit availability
│   └── enrichment_service.py # Orchestrator
├── ml/                 # Machine learning
│   └── priority_scorer.py # Priority calculation
└── tasks/              # Celery tasks
    ├── celery_app.py  # Celery configuration
    ├── scan_tasks.py  # Scanner tasks
    ├── enrichment_tasks.py
    └── priority_tasks.py
```

## Configuration

Environment variables required:

```bash
# Wazuh
WAZUH_API_URL=https://wazuh.example.com:55000
WAZUH_USERNAME=api_user
WAZUH_PASSWORD=api_password

# Qualys
QUALYS_API_URL=https://qualysapi.qualys.com
QUALYS_USERNAME=your_username
QUALYS_PASSWORD=your_password

# Tenable
TENABLE_ACCESS_KEY=your_access_key
TENABLE_SECRET_KEY=your_secret_key

# NVD (optional, for higher rate limits)
NVD_API_KEY=your_nvd_api_key

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Usage

### Running Celery Worker

```bash
# Start worker
celery -A services.aggregator.tasks.celery_app worker --loglevel=info

# Start beat scheduler (for periodic tasks)
celery -A services.aggregator.tasks.celery_app beat --loglevel=info
```

### Manual Scanner Execution

```python
import asyncio
from services.aggregator.scanners.wazuh_scanner import WazuhScanner

async def scan_wazuh():
    config = {
        "api_url": "https://wazuh.example.com:55000",
        "username": "api_user",
        "password": "api_password",
    }

    async with WazuhScanner(config) as scanner:
        result = await scanner.scan()
        print(f"Found {result.vulnerabilities_found} vulnerabilities")

asyncio.run(scan_wazuh())
```

### Enriching Vulnerabilities

```python
from services.aggregator.enrichment.enrichment_service import EnrichmentService
from services.aggregator.processors.normalizer import NormalizedVulnerability

async def enrich_cve():
    vuln = NormalizedVulnerability(
        cve_id="CVE-2023-12345",
        title="Example Vulnerability",
        severity="high",
        cvss_score=8.5,
        discovered_at=datetime.utcnow(),
        status="new",
        source_scanner="wazuh",
    )

    async with EnrichmentService() as enrichment:
        enrichment_data = await enrichment.enrich_vulnerability(vuln)
        print(f"EPSS Score: {enrichment_data.get('epss_score')}")
        print(f"Exploit Available: {enrichment_data.get('exploit_available')}")

asyncio.run(enrich_cve())
```

### Priority Scoring

```python
from services.aggregator.ml.priority_scorer import PriorityScorer

scorer = PriorityScorer()

# Calculate priority
priority = scorer.calculate_priority(
    vulnerability=normalized_vuln,
    enrichment_data=enrichment_data,
    asset_criticality=5  # 1-5 scale
)

print(f"Priority Score: {priority}/100")

# Get detailed explanation
explanation = scorer.get_priority_explanation(
    vulnerability=normalized_vuln,
    enrichment_data=enrichment_data,
    asset_criticality=5
)
print(explanation)
```

## Celery Tasks

### Scanner Tasks

- `scan_wazuh`: Scan vulnerabilities from Wazuh (scheduled every 6 hours)
- `scan_qualys`: Scan from Qualys (scheduled every 6 hours, offset +15min)
- `scan_tenable`: Scan from Tenable (scheduled every 6 hours, offset +30min)
- `import_csv`: Import from CSV/JSON file (on-demand)

### Enrichment Tasks

- `enrich_new_vulnerabilities`: Enrich recently discovered CVEs (daily at 2 AM UTC)
- `enrich_vulnerability`: Enrich specific vulnerability (on-demand)

### Priority Tasks

- `recalculate_all_priorities`: Recalculate all vulnerability priorities (daily at 3 AM UTC)
- `calculate_vulnerability_priority`: Calculate priority for specific vulnerability (on-demand)

## Priority Scoring Algorithm

The priority score (0-100) is calculated using weighted factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| CVSS Score | 25% | Base severity (0-10 scale) |
| EPSS Score | 25% | Exploit probability (0-1 scale) |
| Exploit Availability | 20% | Public exploits available |
| Asset Criticality | 15% | Importance of affected asset (1-5) |
| Vulnerability Age | 10% | Time since discovery |
| Patch Availability | 5% | Is a patch available? |

**Bonuses:**
- CISA KEV: +20% if in Known Exploited Vulnerabilities catalog

## Data Flow

```
Scanner APIs → Raw Vulnerability Data
      ↓
Normalization → Unified VulnZero Schema
      ↓
Deduplication → Merge from Multiple Sources
      ↓
Enrichment → NVD + EPSS + Exploit-DB
      ↓
Prioritization → ML-Based Score (0-100)
      ↓
Database Storage → PostgreSQL
```

## Testing

```bash
# Unit tests
pytest services/aggregator/tests/ -v

# Integration tests
pytest services/aggregator/tests/integration/ -v

# Test scanner connection
python -m services.aggregator.scanners.wazuh_scanner
```

## Rate Limiting

- **NVD API**: 5 req/30s (no key), 50 req/30s (with key)
- **EPSS API**: No official limit, be respectful
- **Scanners**: Implement exponential backoff on 429 errors

## Error Handling

All scanners implement:
- Automatic retry on transient errors
- Rate limit detection and backoff
- Comprehensive error logging
- Graceful degradation (partial results)

## Monitoring

Key metrics to monitor:
- Scanner success/failure rates
- Vulnerabilities discovered per scan
- Enrichment success rates
- Priority score distribution
- Processing latency

## Future Enhancements

- [ ] Train actual XGBoost model for priority scoring
- [ ] Add more scanner integrations (Nessus, OpenVAS)
- [ ] Real-time scanning via webhooks
- [ ] Custom prioritization rules per tenant
- [ ] Machine learning model retraining pipeline
