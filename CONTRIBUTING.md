# Contributing to VulnZero

Thank you for your interest in contributing to VulnZero! We welcome contributions from the community.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)
- [Community](#community)

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to:

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/vulnzero-engine.git
   cd vulnzero-engine
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/oness24/vulnzero-engine.git
   ```
4. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- Docker 24+ and Docker Compose
- PostgreSQL 15+ (or use Docker)
- Redis 7+ (or use Docker)

### Local Environment Setup

1. **Install Python dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

2. **Install frontend dependencies**:
   ```bash
   cd web
   npm install
   cd ..
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your local configuration
   ```

4. **Start services with Docker Compose**:
   ```bash
   docker-compose up -d postgres redis
   ```

5. **Run database migrations**:
   ```bash
   make migrate
   ```

6. **Start the development server**:
   ```bash
   make dev
   ```

### Verify Installation

```bash
make test
```

All tests should pass before you start making changes.

## How to Contribute

### Reporting Bugs

Before creating a bug report:
- Check the [issue tracker](https://github.com/oness24/vulnzero-engine/issues) for existing reports
- Try to reproduce with the latest version

When creating a bug report, include:
- Clear, descriptive title
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Logs or error messages
- Screenshots if applicable

### Suggesting Features

Feature requests are welcome! Please:
- Check if the feature has already been suggested
- Clearly describe the feature and its use case
- Explain why this feature would be useful
- Consider implementation complexity

### Contributing Code

Good first issues are labeled with `good-first-issue` in the issue tracker.

**Areas where contributions are especially welcome:**
- Bug fixes
- Documentation improvements
- Test coverage improvements
- Scanner integrations (new vulnerability scanners)
- Deployment strategy implementations
- UI/UX enhancements
- Performance optimizations

## Coding Standards

### Python (Backend)

Follow [PEP 8](https://pep8.org/) style guide:

```python
# Good
def calculate_risk_score(vulnerability: Vulnerability) -> float:
    """
    Calculate risk score based on CVSS and EPSS.

    Args:
        vulnerability: Vulnerability object with CVSS and EPSS data

    Returns:
        Risk score between 0.0 and 100.0
    """
    cvss_weight = 0.7
    epss_weight = 0.3
    return (vulnerability.cvss_score * cvss_weight +
            vulnerability.epss_score * 100 * epss_weight)
```

**Requirements:**
- Type hints for all functions
- Docstrings for all public functions/classes (Google style)
- Maximum line length: 100 characters
- Use `black` for code formatting
- Use `isort` for import sorting
- Use `pylint` and `mypy` for linting

**Run formatters**:
```bash
make format
```

**Run linters**:
```bash
make lint
```

### TypeScript (Frontend)

Follow the [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript):

```typescript
// Good
interface VulnerabilityProps {
  vulnerability: Vulnerability;
  onApprove: (id: string) => void;
}

export const VulnerabilityCard: React.FC<VulnerabilityProps> = ({
  vulnerability,
  onApprove,
}) => {
  // Component implementation
};
```

**Requirements:**
- Use functional components with hooks
- PropTypes or TypeScript interfaces for all props
- ESLint configuration must pass
- Prettier for formatting

**Run formatters**:
```bash
cd web
npm run format
```

**Run linters**:
```bash
cd web
npm run lint
```

## Testing Guidelines

### Python Tests

We use `pytest` for Python testing:

```python
import pytest
from services.aggregator import VulnerabilityAggregator

def test_vulnerability_deduplication():
    """Test that duplicate vulnerabilities are properly merged."""
    aggregator = VulnerabilityAggregator()

    vuln1 = {"cve_id": "CVE-2024-1234", "source": "wazuh"}
    vuln2 = {"cve_id": "CVE-2024-1234", "source": "qualys"}

    result = aggregator.deduplicate([vuln1, vuln2])

    assert len(result) == 1
    assert result[0]["sources"] == ["wazuh", "qualys"]
```

**Test Requirements:**
- All new features must include tests
- Bug fixes must include regression tests
- Aim for >80% code coverage
- Tests should be fast (<1 second each)
- Use fixtures for common test data

**Run tests**:
```bash
make test
```

**Check coverage**:
```bash
make coverage
```

### Frontend Tests

We use Jest and React Testing Library:

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { VulnerabilityCard } from './VulnerabilityCard';

test('calls onApprove when approve button is clicked', () => {
  const onApprove = jest.fn();
  const vulnerability = { id: '123', cve_id: 'CVE-2024-1234' };

  render(<VulnerabilityCard vulnerability={vulnerability} onApprove={onApprove} />);

  fireEvent.click(screen.getByText('Approve'));

  expect(onApprove).toHaveBeenCalledWith('123');
});
```

**Run frontend tests**:
```bash
cd web
npm test
```

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(aggregator): add support for Tenable.io scanner

Implements Tenable.io API client for vulnerability ingestion.
Includes deduplication logic and data normalization.

Closes #123
```

```
fix(deployment): handle SSH connection timeouts gracefully

Previously, SSH timeouts would crash the deployment process.
Now we retry up to 3 times with exponential backoff.

Fixes #456
```

## Pull Request Process

### Before Submitting

1. **Update your branch** with latest upstream changes:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run the full test suite**:
   ```bash
   make test-all
   ```

3. **Check code quality**:
   ```bash
   make lint
   ```

4. **Update documentation** if needed

5. **Add tests** for new features

### Submitting PR

1. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request** on GitHub

3. **Fill out the PR template** completely

4. **Link related issues** (e.g., "Closes #123")

### PR Review Process

- At least one maintainer must approve
- All CI checks must pass
- Code coverage must not decrease
- Documentation must be updated
- No merge conflicts

**Typical review timeline**: 2-5 business days

### After PR is Merged

- Delete your feature branch
- Update your local main branch:
  ```bash
  git checkout main
  git pull upstream main
  ```

## Community

### Communication Channels

- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: General questions, ideas
- **Email**: For security issues (security@vulnzero.io)

### Getting Help

If you're stuck or have questions:
1. Check existing documentation
2. Search closed issues
3. Ask in GitHub Discussions
4. Tag maintainers in your PR (if urgent)

## Recognition

Contributors will be:
- Listed in AUTHORS file
- Credited in release notes
- Mentioned in our Hall of Fame (for significant contributions)

## License

By contributing to VulnZero, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to VulnZero!** 🚀

Together, we're making cybersecurity teams' lives dramatically better.
