# VulnZero Quick Start Guide

Get VulnZero up and running in 5 minutes!

## 🚀 Fast Track

```bash
# 1. Clone and enter directory
git clone https://github.com/oness24/vulnzero-engine.git
cd vulnzero-engine

# 2. Copy environment configuration
cp .env.example .env

# 3. Edit .env and add your OpenAI or Anthropic API key
# OPENAI_API_KEY=sk-your-key-here
# OR
# ANTHROPIC_API_KEY=sk-ant-your-key-here

# 4. Set up Python environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
make install-dev

# 5. Start infrastructure (Docker)
docker-compose up -d postgres redis

# 6. Initialize database
make db-upgrade

# 7. Try the CLI
vulnzero --help
vulnzero init
vulnzero stats
```

## ✅ Verify Installation

```bash
# Run tests to ensure everything works
make test-unit

# Check code quality
make format
```

## 🎯 Next Steps

### Option A: Explore with CLI

```bash
# Register a test asset
vulnzero register-asset test-server --os-type ubuntu --os-version 22.04

# List vulnerabilities (none yet)
vulnzero list-vulns

# Check system health
vulnzero check-health
```

### Option B: Start Development

```bash
# Start API server (in one terminal)
make run-api
# Visit http://localhost:8000/docs for API documentation

# Start Celery worker (in another terminal)
make run-celery
```

### Option C: Use Full Docker Stack

```bash
# Start everything with Docker Compose
make docker-up

# API: http://localhost:8000
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3001 (admin/admin)
```

## 📚 What You Just Set Up

- ✅ **PostgreSQL database** for storing vulnerabilities, patches, assets
- ✅ **Redis** for caching and task queue
- ✅ **Alembic** for database migrations
- ✅ **CLI tool** for interacting with VulnZero
- ✅ **Pre-commit hooks** for code quality
- ✅ **Testing framework** with pytest

## 🔑 Required: Get API Keys

VulnZero needs an LLM API key to generate patches:

### OpenAI (Recommended)
1. Sign up at https://platform.openai.com/
2. Create API key
3. Add to `.env`: `OPENAI_API_KEY=sk-...`

### Anthropic (Alternative)
1. Sign up at https://console.anthropic.com/
2. Create API key
3. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`

## 🐛 Troubleshooting

**"Command not found: vulnzero"**
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall in development mode
pip install -e .
```

**Database connection error**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# If not, start it
docker-compose up -d postgres
```

**Import errors**
```bash
# Reinstall dependencies
pip install -r requirements-dev.txt
pip install -e .
```

## 📖 Learn More

- **Full development guide**: See `docs/DEVELOPMENT.md`
- **Implementation plan**: See `claude.md`
- **Improvements**: See `IMPROVEMENTS.md`
- **Architecture**: See `README.md`

## 💡 Development Workflow

```bash
# Make changes to code...

# Format code
make format

# Run tests
make test

# Run all quality checks
make quality

# Commit (pre-commit hooks run automatically)
git add .
git commit -m "Your message"
```

## 🎓 What's Next?

Now that your environment is set up, here's the recommended path:

1. **Week 1-2**: Read through the codebase
   - Explore `vulnzero/shared/models/` (database models)
   - Check out `vulnzero/cli.py` (CLI commands)
   - Review tests in `tests/unit/`

2. **Week 3-4**: Implement Patch Generator
   - Create `vulnzero/services/patch_generator/`
   - Integrate OpenAI/Anthropic API
   - Generate first patch for a real CVE

3. **Week 5-8**: Build MVP
   - Simple web UI
   - Basic API endpoints
   - Manual testing workflow

See `IMPROVEMENTS.md` for detailed implementation roadmap!

---

**Ready to build the future of vulnerability remediation? Let's go! 🚀**

Questions? Open an issue: https://github.com/oness24/vulnzero-engine/issues
