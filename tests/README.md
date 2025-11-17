# Tests

Test suite for VulnZero.

## Structure

- **unit/**: Unit tests for individual functions/classes
- **integration/**: Integration tests for service interactions
- **e2e/**: End-to-end tests for complete workflows

## Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
pytest tests/unit/test_vulnerability_aggregator.py

# Run in parallel
make test-fast
```

## Writing Tests

See [CONTRIBUTING.md](../CONTRIBUTING.md) for testing guidelines.
