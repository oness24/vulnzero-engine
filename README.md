# VulnZero: Autonomous Vulnerability Remediation Platform

**Zero-Touch Vulnerability Remediation. Zero Days of Exposure.**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## 🚀 Overview

VulnZero is the world's first fully autonomous vulnerability remediation platform that detects, patches, tests, deploys, and validates fixes across your entire infrastructure without human intervention.

### Key Features

- **🔍 Automated Detection**: Integrates with Wazuh, Qualys, Tenable, and other vulnerability scanners
- **🤖 AI-Powered Patch Generation**: Uses GPT-4/Claude to generate context-aware remediation scripts
- **🧪 Digital Twin Testing**: Tests patches in isolated sandbox environments before production deployment
- **⚡ Zero-Downtime Deployment**: Blue-green and canary deployment strategies
- **📊 Real-Time Monitoring**: Automatic rollback on anomaly detection
- **🎯 ML-Based Prioritization**: Intelligently prioritizes vulnerabilities based on risk scoring

### Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Vulnerability │────▶│   AI Patch       │────▶│  Digital Twin   │
│   Aggregator    │     │   Generator      │     │  Testing Engine │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                           │
                                                           ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Monitoring &  │◀────│   Deployment     │◀────│   Test Results  │
│   Rollback      │     │   Orchestrator   │     │   Validation    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

---

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

---

## 🔧 Prerequisites

- **Python**: 3.11 or higher
- **Docker**: 24.0+ and Docker Compose
- **PostgreSQL**: 15+ (or use Docker Compose)
- **Redis**: 7+ (or use Docker Compose)
- **Node.js**: 18+ (for web dashboard)
- **API Keys**: OpenAI or Anthropic API key for AI patch generation

---

## ⚡ Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/oness24/vulnzero-engine.git
cd vulnzero-engine
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration (API keys, database credentials, etc.)
```

3. **Start with Docker Compose** (Recommended for development)
```bash
make docker-up
```

4. **Access the dashboard**
```
Web Dashboard: http://localhost:3000
API Documentation: http://localhost:8000/docs
Grafana Monitoring: http://localhost:3001
```

---

## 💻 Installation

### Local Development Setup

1. **Create and activate virtual environment**
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Install pre-commit hooks**
```bash
pre-commit install
```

4. **Set up the database**
```bash
make db-migrate
make db-seed  # Optional: Load sample data
```

5. **Start the services**
```bash
# Terminal 1: API Gateway
make run-api

# Terminal 2: Celery Workers
make run-workers

# Terminal 3: Web Dashboard
make run-web
```

---

## ⚙️ Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure the following:

```bash
# Database
DATABASE_URL=postgresql://vulnzero:password@localhost:5432/vulnzero

# Redis
REDIS_URL=redis://localhost:6379/0

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Scanner Integration
WAZUH_API_URL=https://wazuh.example.com
WAZUH_API_USERNAME=admin
WAZUH_API_PASSWORD=secret

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001
```

### Scanner Configuration

Configure your vulnerability scanners in the dashboard under **Settings → Scanners** or via API:

```bash
curl -X POST http://localhost:8000/api/v1/scanners \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Wazuh Production",
    "type": "wazuh",
    "url": "https://wazuh.example.com",
    "credentials": {...}
  }'
```

---

## 🛠️ Development

### Project Structure

```
vulnzero-engine/
├── services/               # Microservices
│   ├── aggregator/        # Vulnerability ingestion
│   ├── patch-generator/   # AI-powered patch creation
│   ├── testing-engine/    # Digital twin testing
│   ├── deployment-engine/ # Deployment orchestration
│   ├── monitoring/        # Post-deployment monitoring
│   └── api-gateway/       # Main API gateway
├── shared/                # Shared code
│   ├── models/           # Data models (Pydantic)
│   ├── utils/            # Utilities
│   └── config/           # Configuration
├── web/                  # React dashboard
├── infrastructure/       # Terraform/K8s configs
├── tests/               # Test suites
├── docs/                # Documentation
└── scripts/             # Utility scripts
```

### Common Commands

```bash
# Development
make setup          # Initial setup
make run            # Run all services locally
make test           # Run all tests
make lint           # Run linters (black, flake8, mypy)
make format         # Format code with black

# Docker
make docker-build   # Build Docker images
make docker-up      # Start all services
make docker-down    # Stop all services
make docker-logs    # View logs

# Database
make db-migrate     # Run migrations
make db-rollback    # Rollback last migration
make db-seed        # Seed database with test data
make db-reset       # Reset database (WARNING: deletes all data)

# Testing
make test-unit      # Run unit tests
make test-integration # Run integration tests
make test-e2e       # Run end-to-end tests
make coverage       # Generate coverage report
```

### Code Quality

This project follows strict code quality standards:

- **Black** for code formatting
- **Flake8** for linting
- **MyPy** for type checking
- **pytest** for testing (>80% coverage required)
- **pre-commit** hooks for automated checks

---

## 🧪 Testing

### Running Tests

```bash
# All tests
make test

# Specific test suite
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# With coverage
make coverage

# Watch mode (for development)
pytest-watch
```

### Test Structure

```
tests/
├── unit/               # Unit tests for individual functions
├── integration/        # Integration tests for services
├── e2e/               # End-to-end workflow tests
├── fixtures/          # Test fixtures and mock data
└── conftest.py        # Shared pytest configuration
```

---

## 🚀 Deployment

### Docker Compose (Development/Testing)

```bash
docker-compose up -d
```

### Kubernetes (Production)

```bash
# Apply Kubernetes manifests
kubectl apply -f infrastructure/k8s/

# Or use Helm
helm install vulnzero infrastructure/helm/vulnzero
```

### Terraform (AWS Infrastructure)

```bash
cd infrastructure/terraform/aws
terraform init
terraform plan
terraform apply
```

See [Deployment Guide](docs/guides/deployment.md) for detailed instructions.

---

## 📚 Documentation

- **[API Documentation](docs/api/README.md)**: Complete API reference
- **[Architecture Guide](docs/architecture/README.md)**: System architecture and design decisions
- **[Development Guide](docs/guides/development.md)**: Contributing and development workflow
- **[Deployment Guide](docs/guides/deployment.md)**: Production deployment instructions
- **[User Manual](docs/guides/user-manual.md)**: Using the VulnZero dashboard
- **[Troubleshooting](docs/guides/troubleshooting.md)**: Common issues and solutions

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`make test`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

---

## 📊 Key Metrics

VulnZero tracks the following metrics:

- **Remediation Success Rate**: Target >95%
- **Time to Remediation**: Target <24 hours
- **False Positive Rate**: Target <5%
- **System Uptime**: Target 99.9%

---

## 🔐 Security

VulnZero is built with security as the top priority:

- ✅ No hardcoded credentials (environment variables only)
- ✅ Secrets management (AWS Secrets Manager, HashiCorp Vault)
- ✅ Least-privilege access (IAM roles, RBAC)
- ✅ Comprehensive audit logging
- ✅ Encryption at rest and in transit (TLS 1.3+)
- ✅ Regular security audits and dependency scanning

To report a security vulnerability, please email security@vulnzero.com

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/), [React](https://react.dev/), [PostgreSQL](https://www.postgresql.org/)
- AI-powered by [OpenAI](https://openai.com/) and [Anthropic](https://www.anthropic.com/)
- Monitoring with [Prometheus](https://prometheus.io/) and [Grafana](https://grafana.com/)

---

## 📞 Contact

- **Website**: https://vulnzero.com
- **Email**: contact@vulnzero.com
- **Twitter**: [@vulnzero](https://twitter.com/vulnzero)
- **LinkedIn**: [VulnZero](https://linkedin.com/company/vulnzero)

---

**Built with ❤️ by cybersecurity professionals, for cybersecurity professionals.**
