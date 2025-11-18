# Contributing to VulnZero

Thank you for your interest in contributing to VulnZero! This document provides guidelines and requirements for contributing to the project.

## 🧪 Testing Requirements

**All contributions must include tests.** We maintain a minimum of 60% code coverage across the codebase.

### Running Tests Locally

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-asyncio pytest-mock

# Run all tests
pytest tests/

# Run with coverage report
pytest tests/ --cov=shared --cov=services --cov-report=html --cov-report=term

# Run specific test modules
pytest tests/unit/models/test_database_models.py -v
pytest tests/unit/services/test_monitoring.py -v
pytest tests/unit/services/test_deployment_orchestrator.py -v
```

### Current Test Status

- ✅ **55/55 tests passing**
- ✅ **64% code coverage** (target: 60%)
- ✅ **Test execution time: ~8 seconds**

### Test Structure

```
tests/
├── unit/
│   ├── models/          # Database model tests
│   │   └── test_database_models.py
│   └── services/        # Service layer tests
│       ├── test_monitoring.py
│       └── test_deployment_orchestrator.py
└── conftest.py          # Shared test fixtures
```

## 📝 Writing Tests

### Test File Organization

1. **Location**: Place tests in `tests/unit/` mirroring the source structure
2. **Naming**: Test files must start with `test_`
3. **Classes**: Group related tests in classes starting with `Test`

### Example Test Structure

```python
"""
Unit Tests for MyFeature

Brief description of what's being tested.
"""

import pytest
from unittest.mock import Mock, patch

class TestMyFeature:
    """Test MyFeature functionality"""

    def test_feature_works(self, test_db):
        """Test that feature works correctly"""
        # Arrange
        feature = MyFeature()

        # Act
        result = feature.do_something()

        # Assert
        assert result is True

    @patch('module.external_dependency')
    def test_feature_with_mock(self, mock_external):
        """Test feature with mocked external dependency"""
        mock_external.return_value = "mocked"

        feature = MyFeature()
        result = feature.do_something()

        assert result == "expected"
```

### Available Fixtures (from conftest.py)

All tests have access to these shared fixtures:

- `test_db` - In-memory SQLite database with fresh schema
- `sample_vulnerability` - Pre-created Vulnerability instance
- `sample_asset` - Pre-created Asset instance
- `sample_patch` - Pre-created Patch instance
- `sample_deployment` - Pre-created Deployment instance
- `mock_openai` - Mocked OpenAI API client
- `mock_anthropic` - Mocked Anthropic API client
- `mock_docker` - Mocked Docker client

### Testing Best Practices

1. **Isolation**: Each test should be independent
2. **Fast**: Use mocks for external services (LLMs, Docker, databases)
3. **Clear**: Use descriptive test names that explain what's being tested
4. **Comprehensive**: Test both success and failure cases
5. **Realistic**: Use realistic test data

### Mocking External Services

```python
@patch('services.patch_generator.openai.OpenAI')
def test_ai_patch_generation(self, mock_openai):
    """Test AI patch generation with mocked OpenAI"""
    # Configure mock
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="patch content"))]
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    # Test your code
    generator = PatchGenerator()
    result = generator.generate_patch(vulnerability)

    assert result.patch_content == "patch content"
```

## 🔄 Pre-commit Hooks

We use pre-commit hooks to ensure code quality. Install them:

```bash
pip install pre-commit
pre-commit install
```

The hooks will automatically:
- Format code with Black
- Sort imports with isort
- Lint with Ruff
- Run security checks with Bandit
- Run the test suite

## 🚀 Continuous Integration

All pull requests trigger automated checks:

1. **Test Suite** - All 55 tests must pass
2. **Coverage** - Must maintain ≥60% coverage
3. **Code Quality** - Linting and formatting checks
4. **Security Scan** - Bandit security analysis

Pull requests cannot be merged until all checks pass.

## 📊 Coverage Requirements

### Module-Level Coverage Targets

| Module | Minimum Coverage |
|--------|------------------|
| `shared/models/` | 75% |
| `shared/config/` | 60% |
| `services/monitoring/` | 60% |
| `services/deployment_orchestrator/` | 60% |
| New modules | 60% |

### How to Check Coverage

```bash
# Generate HTML coverage report
pytest --cov=shared --cov=services --cov-report=html
open htmlcov/index.html

# Terminal coverage report
pytest --cov=shared --cov=services --cov-report=term-missing
```

## 🐛 Bug Fixes

When fixing a bug:

1. **Write a failing test** that reproduces the bug
2. **Fix the bug** in the source code
3. **Verify the test passes**
4. **Add regression test** if not already covered

Example:

```python
def test_bug_123_duplicate_deployments(self):
    """Test that deployments aren't duplicated (Bug #123)"""
    deployment = create_deployment()

    # This should not create a duplicate
    result = create_deployment_again()

    assert count_deployments() == 1
```

## 📦 Pull Request Checklist

Before submitting a PR, ensure:

- [ ] All tests pass locally (`pytest tests/`)
- [ ] Coverage is ≥60% (`pytest --cov-fail-under=60`)
- [ ] New features have tests
- [ ] Bug fixes have regression tests
- [ ] Code is formatted (`black .`)
- [ ] Imports are sorted (`isort .`)
- [ ] No linting errors (`ruff check .`)
- [ ] Documentation is updated (if applicable)

## 🔧 Development Setup

```bash
# Clone the repository
git clone https://github.com/oness24/vulnzero-engine.git
cd vulnzero-engine

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development tools

# Install pre-commit hooks
pre-commit install

# Run tests to verify setup
pytest tests/
```

## 📚 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [unittest.mock Guide](https://docs.python.org/3/library/unittest.mock.html)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)

## 💬 Questions?

If you have questions about testing or contributing:

1. Check existing tests in `tests/` for examples
2. Review the test fixtures in `tests/conftest.py`
3. Open a GitHub Discussion
4. Ask in pull request comments

---

**Thank you for helping make VulnZero better! 🚀**
