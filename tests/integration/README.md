# Integration Tests

**Status:** Planned - See [Testing Roadmap](../../docs/TESTING_ROADMAP.md)

## Overview

Integration tests will verify end-to-end workflows and service-to-service communication.
This directory is reserved for future integration tests.

## Planned Test Coverage

### Phase 1: Database Integration (Priority: High)
- Vulnerability → Patch → Deployment relationships
- Audit log creation and tracking
- Transaction rollback scenarios

### Phase 2: Service Component Integration (Priority: Medium)
- Metrics collection and storage
- Anomaly detection with real data
- Deployment strategies (with mocked infrastructure)

### Phase 3: End-to-End Workflows (Priority: Low)
- Complete remediation pipeline
- Multi-asset deployments
- Automatic rollback scenarios

## Current Status

- ✅ Unit tests: 55/55 passing, 64% coverage
- ⏳ Integration tests: Planned
- ⏳ E2E tests: Planned

See the [Testing Roadmap](../../docs/TESTING_ROADMAP.md) for timeline and implementation details.

## Running Tests

When integration tests are implemented:

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific integration test module
pytest tests/integration/test_database_workflows.py -v

# Run integration tests with coverage
pytest tests/integration/ --cov=services --cov=shared --cov-report=html
```

## Contributing

When adding integration tests:
1. Follow the patterns in `tests/unit/`
2. Use real database (not mocked)
3. Mock external services (LLMs, Docker, Ansible)
4. Keep tests independent and idempotent
5. See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines
