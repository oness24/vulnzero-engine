# VulnZero Engine - Complete Installation & Usage Guide

**Version**: 1.0.0
**Last Updated**: 2025-11-18
**Difficulty**: Beginner-Friendly

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (5 Minutes)](#quick-start-5-minutes)
3. [Detailed Installation](#detailed-installation)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [First-Time Setup](#first-time-setup)
7. [Using VulnZero](#using-vulnzero)
8. [Common Workflows](#common-workflows)
9. [Troubleshooting](#troubleshooting)
10. [Upgrading](#upgrading)

---

## Prerequisites

### Required Software

| Software | Minimum Version | Purpose | Installation |
|----------|----------------|---------|--------------|
| **Docker** | 20.10+ | Container runtime | [Get Docker](https://docs.docker.com/get-docker/) |
| **Docker Compose** | 2.0+ | Multi-container orchestration | Included with Docker Desktop |
| **Git** | 2.0+ | Version control | [Get Git](https://git-scm.com/downloads) |
| **Python** | 3.11+ | Backend runtime | [Get Python](https://www.python.org/downloads/) |
| **Node.js** | 18+ | Frontend build | [Get Node.js](https://nodejs.org/) |

### System Requirements

**Minimum**:
- CPU: 2 cores
- RAM: 4 GB
- Disk: 10 GB free space
- OS: Linux, macOS, or Windows with WSL2

**Recommended**:
- CPU: 4+ cores
- RAM: 8 GB+
- Disk: 20 GB+ SSD
- OS: Ubuntu 22.04 LTS or similar

### Check Prerequisites

```bash
# Check Docker
docker --version
docker-compose --version

# Check Git
git --version

# Check Python
python3 --version

# Check Node.js
node --version
npm --version
```

---

## Quick Start (5 Minutes)

**For experienced users who want to get running immediately:**

```bash
# 1. Clone repository
git clone https://github.com/your-org/vulnzero-engine.git
cd vulnzero-engine

# 2. Start services
docker-compose up -d

# 3. Access application
open http://localhost:8000
```

**That's it!** 🎉 The application is now running.

Default credentials:
- **Username**: `admin`
- **Password**: `admin` (change on first login)

---

## Detailed Installation

### Step 1: Clone the Repository

```bash
# Clone the repository
git clone https://github.com/your-org/vulnzero-engine.git

# Navigate to project directory
cd vulnzero-engine

# Verify files
ls -la
```

**Expected output**: You should see directories like `api/`, `services/`, `web/`, `infrastructure/`

---

### Step 2: Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit configuration (optional)
nano .env
```

**Key settings to review:**

```bash
# Basic Configuration
ENVIRONMENT=development
DEBUG=true

# Database (will use Docker defaults)
DATABASE_URL=postgresql+asyncpg://vulnzero:vulnzero_password@postgres:5432/vulnzero

# Redis (will use Docker defaults)
REDIS_URL=redis://redis:6379/0

# Security (CHANGE IN PRODUCTION!)
API_SECRET_KEY=your-secret-key-change-this-in-production

# Feature Flags (adjust based on your needs)
FEATURE_AUTO_REMEDIATION=true
FEATURE_MANUAL_APPROVAL_REQUIRED=false
FEATURE_CRITICAL_VULN_AUTO_APPROVE=true
```

**💡 Tip**: For now, you can use the defaults. We'll configure advanced features later.

---

### Step 3: Install Dependencies (Optional)

**If running without Docker** (for development):

```bash
# Python dependencies
pip install -r requirements.txt

# Frontend dependencies
cd web
npm install
cd ..
```

**If using Docker** (recommended): Skip this step - Docker handles dependencies automatically.

---

### Step 4: Start Infrastructure

**Option A: Docker Compose (Recommended)**

```bash
# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps
```

**Expected output:**
```
NAME                  STATUS    PORTS
vulnzero-api          running   0.0.0.0:8000->8000
vulnzero-frontend     running   0.0.0.0:3000->80
vulnzero-postgres     running   5432
vulnzero-redis        running   6379
vulnzero-celery       running
```

**Option B: Manual Start (Development)**

```bash
# Terminal 1: Start PostgreSQL
docker run -d --name postgres \
  -e POSTGRES_USER=vulnzero \
  -e POSTGRES_PASSWORD=vulnzero_password \
  -e POSTGRES_DB=vulnzero \
  -p 5432:5432 \
  postgres:15

# Terminal 2: Start Redis
docker run -d --name redis \
  -p 6379:6379 \
  redis:7-alpine

# Terminal 3: Start API
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 4: Start Celery Worker
celery -A shared.celery_app worker --loglevel=info

# Terminal 5: Start Frontend
cd web
npm run dev
```

---

### Step 5: Initialize Database

```bash
# Run database migrations
docker-compose exec api alembic upgrade head

# Verify migrations
docker-compose exec api alembic current
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Running upgrade -> abc123, Initial migration
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
```

---

### Step 6: Create Admin User

```bash
# Create first admin user
docker-compose exec api python -m scripts.create_user \
  --username admin \
  --password admin123 \
  --email admin@vulnzero.io \
  --role admin

# Or use interactive mode
docker-compose exec api python -c "
from shared.database.session import AsyncSessionLocal
from shared.models.models import User, UserRole
from shared.auth.password import hash_password
import asyncio

async def create_admin():
    async with AsyncSessionLocal() as session:
        # Check if admin exists
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.username == 'admin'))
        if result.scalar_one_or_none():
            print('Admin user already exists')
            return

        # Create admin
        admin = User(
            username='admin',
            email='admin@vulnzero.io',
            full_name='VulnZero Admin',
            hashed_password=hash_password('admin123'),
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        print('Admin user created successfully')

asyncio.run(create_admin())
"
```

---

### Step 7: Verify Installation

```bash
# Run validation script
python3 validate_app.py
```

**Expected output:**
```
✅ CORE SYSTEMS
   • Backend API          ✓ Working
   • Frontend React App   ✓ Working
   • Database Models      ✓ Working
   • Authentication       ✓ Working

🎉 VERDICT: PRODUCTION READY!
```

---

### Step 8: Access Application

Open your browser and navigate to:

**Frontend Dashboard**: http://localhost:3000
**API Documentation**: http://localhost:8000/docs
**API Health Check**: http://localhost:8000/api/system/health

**Login Credentials**:
- Username: `admin`
- Password: `admin123` (or what you set)

---

## Configuration

### Security Configuration

**⚠️ IMPORTANT**: Change these before production deployment!

```bash
# Generate secure secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Update .env file
API_SECRET_KEY=<generated-key>
```

### Autonomy Level Configuration

Choose your automation level:

#### Level 1: Maximum Control (Recommended for Start)

```bash
FEATURE_AUTO_REMEDIATION=true
FEATURE_MANUAL_APPROVAL_REQUIRED=true
FEATURE_CRITICAL_VULN_AUTO_APPROVE=false
```

**Behavior**: All patches require manual approval before deployment.

#### Level 2: Supervised Autonomy (Recommended for Production)

```bash
FEATURE_AUTO_REMEDIATION=true
FEATURE_MANUAL_APPROVAL_REQUIRED=true
FEATURE_CRITICAL_VULN_AUTO_APPROVE=true
```

**Behavior**: Non-critical patches need approval; critical CVEs are fast-tracked.

#### Level 3: Full Autonomy (Advanced)

```bash
FEATURE_AUTO_REMEDIATION=true
FEATURE_MANUAL_APPROVAL_REQUIRED=false
FEATURE_CRITICAL_VULN_AUTO_APPROVE=true
```

**Behavior**: Fully autonomous remediation after testing.

### Monitoring Configuration

```bash
# Sentry Error Tracking (Optional)
VITE_SENTRY_DSN=https://your-sentry-dsn@sentry.io/project

# Slack Notifications (Optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_CHANNEL=#vulnzero-alerts
```

### Scanner Integrations (Optional)

```bash
# Wazuh
WAZUH_API_URL=https://wazuh.example.com:55000
WAZUH_API_USER=wazuh-api-user
WAZUH_API_PASSWORD=wazuh-api-password

# Qualys
QUALYS_API_URL=https://qualysapi.qualys.com
QUALYS_USERNAME=qualys-username
QUALYS_PASSWORD=qualys-password

# Tenable.io
TENABLE_ACCESS_KEY=your-tenable-access-key
TENABLE_SECRET_KEY=your-tenable-secret-key

# NVD (National Vulnerability Database)
NVD_API_KEY=your-nvd-api-key
```

---

## Running the Application

### Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api
docker-compose logs -f celery

# Stop all services
docker-compose down

# Stop and remove volumes (clean restart)
docker-compose down -v
```

### Using Make Commands

```bash
# Show all available commands
make help

# Start services
make docker-up

# Stop services
make docker-down

# View logs
make logs

# Run tests
make test

# Run linters
make lint

# Format code
make format
```

### Development Mode

**Terminal 1: Backend API**
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2: Celery Worker**
```bash
celery -A shared.celery_app worker --loglevel=info
```

**Terminal 3: Celery Beat (Scheduler)**
```bash
celery -A shared.celery_app beat --loglevel=info
```

**Terminal 4: Frontend**
```bash
cd web
npm run dev
```

---

## First-Time Setup

### Step 1: Log In

1. Open http://localhost:3000
2. Enter credentials:
   - Username: `admin`
   - Password: `admin123`
3. Click "Sign In"

### Step 2: Change Password

1. Click profile icon (top-right)
2. Select "Settings"
3. Navigate to "Security"
4. Update password
5. Click "Save Changes"

### Step 3: Add Team Members (Optional)

1. Navigate to "Settings" → "Users"
2. Click "Add User"
3. Fill in details:
   - Username
   - Email
   - Role (viewer, operator, admin)
4. Click "Create User"
5. Share credentials with team member

### Step 4: Configure Assets

1. Navigate to "Assets"
2. Click "Add Asset"
3. Enter asset details:
   - Name: `production-web-01`
   - Type: `Server`
   - Environment: `Production`
   - IP Address: `10.0.1.100`
   - Tags: `web, critical, production`
4. Click "Save Asset"

### Step 5: Connect Vulnerability Scanners

1. Navigate to "Settings" → "Integrations"
2. Select scanner type (Wazuh, Qualys, Tenable)
3. Enter API credentials
4. Click "Test Connection"
5. If successful, click "Save"

### Step 6: Run Initial Scan

1. Navigate to "Vulnerabilities"
2. Click "Scan Now"
3. Wait for scan to complete (1-5 minutes)
4. View detected vulnerabilities

---

## Using VulnZero

### Dashboard Overview

**Main Dashboard** shows:
- Total vulnerabilities
- Severity breakdown (Critical, High, Medium, Low)
- Recent patches
- Deployment status
- System health

### Vulnerability Management

#### View Vulnerabilities

1. Navigate to "Vulnerabilities"
2. Use filters:
   - **Severity**: Critical, High, Medium, Low
   - **Status**: Open, In Progress, Patched
   - **Source**: Wazuh, Qualys, Tenable, NVD
3. Click vulnerability to view details:
   - CVE ID
   - CVSS Score
   - EPSS Score (exploit probability)
   - Affected assets
   - Available patches
   - Exploit status (CISA KEV data)

#### Prioritize Vulnerabilities

Vulnerabilities are automatically prioritized using:
- **CVSS Score** (25% weight)
- **EPSS Score** (20% weight)
- **Severity Level** (15% weight)
- **Asset Criticality** (15% weight)
- **Exploit Available** (25% weight)

**High Priority** = CVSS > 7.0 AND (EPSS > 0.5 OR Exploit Available)

### Patch Management

#### View Generated Patches

1. Navigate to "Patches"
2. Filter by status:
   - **Pending Approval**: Awaiting operator review
   - **Approved**: Ready for deployment
   - **Rejected**: Not suitable
   - **Testing**: In digital twin
   - **Deployed**: Applied to production

#### Approve a Patch

1. Navigate to "Patches" → "Pending Approval"
2. Click on patch to review
3. Review details:
   - **Vulnerability**: CVE-2024-1234
   - **Confidence Score**: 95% ⭐⭐⭐
   - **Test Status**: PASSED ✅
   - **Code Changes**: View diff
4. Click "Approve Patch"
5. Add notes (optional)
6. Confirm approval

#### Reject a Patch

1. Click on patch to review
2. Click "Reject Patch"
3. Select rejection reason:
   - Performance concerns
   - Breaking changes
   - Business logic conflicts
   - Security concerns
   - Other (specify)
4. Add detailed reason
5. Confirm rejection

### Deployment Management

#### Manual Deployment

1. Navigate to "Deployments"
2. Click "New Deployment"
3. Select patch(es) to deploy
4. Choose deployment strategy:
   - **Canary**: 5% → 25% → 100% (safest)
   - **Blue-Green**: Full switch with rollback
   - **Rolling**: Sequential updates
   - **All-at-Once**: Simultaneous (fastest)
5. Select target assets
6. Click "Start Deployment"

#### Monitor Deployment

1. View deployment progress in real-time
2. Monitor metrics:
   - Deployment percentage
   - Success/failure rate
   - Error logs
   - Performance impact
3. Watch for alerts

#### Rollback Deployment

**Automatic Rollback** (if enabled):
- Triggers on error rate increase >50%
- Triggers on performance degradation
- Triggers on health check failures

**Manual Rollback**:
1. Navigate to "Deployments"
2. Click on active deployment
3. Click "Rollback"
4. Enter rollback reason
5. Confirm rollback

### Monitoring

#### System Health

1. Navigate to "Monitoring" → "System Health"
2. View service status:
   - API: Healthy ✅
   - Database: Healthy ✅
   - Redis: Healthy ✅
   - Celery: Healthy ✅
3. View metrics:
   - Response time
   - Request rate
   - Error rate
   - CPU/Memory usage

#### Vulnerability Metrics

1. Navigate to "Analytics"
2. View charts:
   - Vulnerabilities over time
   - Time to remediation
   - Patch approval rate
   - Deployment success rate
   - Mean time to recovery (MTTR)

---

## Common Workflows

### Workflow 1: Manual Patch Approval Process

**Scenario**: You want to review and approve patches before deployment.

```mermaid
graph TD
    A[Vulnerability Detected] --> B[AI Generates Patch]
    B --> C[Digital Twin Testing]
    C --> D{Tests Pass?}
    D -->|No| E[Log Failure]
    D -->|Yes| F[Pending Approval]
    F --> G[Operator Reviews]
    G --> H{Approve?}
    H -->|Yes| I[Deploy to Production]
    H -->|No| J[Reject + Log Reason]
    I --> K[Monitor Metrics]
    K --> L{Healthy?}
    L -->|No| M[Auto Rollback]
    L -->|Yes| N[Mark Complete]
```

**Steps**:
1. Configure: `FEATURE_MANUAL_APPROVAL_REQUIRED=true`
2. Wait for vulnerability detection
3. Review generated patch in "Patches" tab
4. Approve or reject with reason
5. If approved, monitor deployment
6. Rollback if issues detected

### Workflow 2: Fast-Track Critical Vulnerabilities

**Scenario**: You want critical CVEs to be patched immediately.

**Steps**:
1. Configure:
   ```bash
   FEATURE_AUTO_REMEDIATION=true
   FEATURE_MANUAL_APPROVAL_REQUIRED=true
   FEATURE_CRITICAL_VULN_AUTO_APPROVE=true
   ```
2. Critical vulnerabilities (CVSS ≥ 9.0 with exploit) are auto-approved
3. Non-critical patches still require manual approval
4. Monitor all deployments in dashboard

### Workflow 3: Scheduled Maintenance Window

**Scenario**: You want to deploy patches during off-hours.

**Steps**:
1. Approve patches during the day
2. Schedule deployment:
   - Navigate to approved patch
   - Click "Schedule Deployment"
   - Select date/time (e.g., 2 AM Sunday)
   - Choose deployment strategy
3. Celery Beat scheduler will trigger deployment at specified time
4. Receive Slack/email notification when complete

### Workflow 4: Multi-Environment Deployment

**Scenario**: You want to test in staging before production.

**Steps**:
1. Tag assets by environment:
   - `environment:staging`
   - `environment:production`
2. Approve patch
3. Deploy to staging:
   - Select staging assets only
   - Deploy with "All-at-Once" strategy
4. Monitor staging for 24 hours
5. Deploy to production:
   - Select production assets
   - Deploy with "Canary" strategy
   - Monitor closely

### Workflow 5: Audit Compliance Reporting

**Scenario**: You need to generate compliance reports.

**Steps**:
1. Navigate to "Audit Logs"
2. Select date range
3. Filter by event type:
   - Vulnerability detections
   - Patch approvals
   - Deployments
   - Rollbacks
4. Export to CSV/PDF
5. Submit to compliance team

---

## Troubleshooting

### Common Issues

#### Issue 1: Services Won't Start

**Symptoms**:
```bash
docker-compose up -d
ERROR: Service 'api' failed to build
```

**Solutions**:
```bash
# Check Docker is running
docker info

# Remove old containers
docker-compose down -v

# Rebuild images
docker-compose build --no-cache

# Start services
docker-compose up -d
```

#### Issue 2: Database Connection Failed

**Symptoms**:
```
FATAL: password authentication failed for user "vulnzero"
```

**Solutions**:
```bash
# Check database is running
docker-compose ps postgres

# Check database logs
docker-compose logs postgres

# Reset database
docker-compose down -v
docker-compose up -d postgres

# Verify connection
docker-compose exec api python -c "
from shared.models.database import engine
import asyncio
asyncio.run(engine.dispose())
print('Database connection OK')
"
```

#### Issue 3: Frontend Can't Connect to API

**Symptoms**: Frontend shows "Network Error" or "Failed to fetch"

**Solutions**:

1. Check API is running:
   ```bash
   curl http://localhost:8000/api/system/health
   ```

2. Check CORS configuration in `.env`:
   ```bash
   CORS_ORIGINS=http://localhost:3000,http://localhost:8000
   ```

3. Restart services:
   ```bash
   docker-compose restart api frontend
   ```

#### Issue 4: Celery Tasks Not Running

**Symptoms**: Patches stay in "Generating" status indefinitely

**Solutions**:
```bash
# Check Celery is running
docker-compose ps celery

# Check Celery logs
docker-compose logs -f celery

# Restart Celery
docker-compose restart celery

# Check Redis connection
docker-compose exec celery python -c "
import redis
r = redis.from_url('redis://redis:6379/0')
r.ping()
print('Redis connection OK')
"
```

#### Issue 5: Out of Memory

**Symptoms**: Services crash with `OOMKilled`

**Solutions**:

1. Increase Docker memory limit (Docker Desktop → Settings → Resources)
2. Reduce worker count in `.env`:
   ```bash
   API_WORKERS=2  # Reduce from 4
   ```
3. Use production-grade deployment (Kubernetes with autoscaling)

### Logs and Debugging

**View all logs**:
```bash
docker-compose logs -f
```

**View specific service logs**:
```bash
docker-compose logs -f api
docker-compose logs -f celery
docker-compose logs -f postgres
```

**Access container shell**:
```bash
docker-compose exec api bash
docker-compose exec postgres psql -U vulnzero -d vulnzero
```

**Check database**:
```bash
docker-compose exec postgres psql -U vulnzero -d vulnzero -c "\dt"
docker-compose exec postgres psql -U vulnzero -d vulnzero -c "SELECT * FROM users;"
```

### Performance Issues

**Slow API responses**:
1. Check database query performance
2. Enable database indexes (run migrations)
3. Increase database pool size in `.env`:
   ```bash
   DATABASE_POOL_SIZE=30
   DATABASE_MAX_OVERFLOW=20
   ```

**High memory usage**:
1. Reduce Celery worker concurrency
2. Enable Redis memory limits
3. Optimize database queries

**High CPU usage**:
1. Check for infinite loops in logs
2. Reduce background task frequency
3. Scale horizontally (multiple instances)

### Getting Help

**Documentation**:
- README.md
- SECURITY_AUDIT_REPORT.md
- HUMAN_IN_THE_LOOP.md
- API docs: http://localhost:8000/docs

**Support Channels**:
- GitHub Issues: https://github.com/your-org/vulnzero-engine/issues
- Email: support@vulnzero.io
- Slack: #vulnzero-support

**Include in bug reports**:
1. VulnZero version: `git describe --tags`
2. Docker version: `docker --version`
3. OS version: `uname -a`
4. Error logs: `docker-compose logs`
5. Steps to reproduce

---

## Upgrading

### Backup Before Upgrade

```bash
# Backup database
docker-compose exec postgres pg_dump -U vulnzero vulnzero > backup.sql

# Backup .env file
cp .env .env.backup

# Backup volumes
docker run --rm -v vulnzero_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres-backup.tar.gz /data
```

### Upgrade Process

```bash
# 1. Stop services
docker-compose down

# 2. Pull latest code
git fetch --all --tags
git checkout v1.1.0  # Or latest version

# 3. Update dependencies
docker-compose build --no-cache

# 4. Run migrations
docker-compose up -d postgres redis
docker-compose run --rm api alembic upgrade head

# 5. Start all services
docker-compose up -d

# 6. Verify upgrade
docker-compose ps
python3 validate_app.py
```

### Rollback (If Needed)

```bash
# 1. Stop services
docker-compose down

# 2. Checkout previous version
git checkout v1.0.0

# 3. Restore database
docker-compose up -d postgres
docker-compose exec -T postgres psql -U vulnzero vulnzero < backup.sql

# 4. Start services
docker-compose up -d
```

---

## Next Steps

**After Installation**:
1. ✅ Change default passwords
2. ✅ Configure scanner integrations
3. ✅ Add assets to monitor
4. ✅ Run initial vulnerability scan
5. ✅ Configure notification channels (Slack, email)
6. ✅ Set up monitoring dashboards (Grafana)
7. ✅ Review and adjust autonomy levels
8. ✅ Train team on approval workflows

**Production Deployment**:
1. Review SECURITY_AUDIT_REPORT.md
2. Configure TLS/SSL certificates
3. Set up external database (managed PostgreSQL)
4. Configure external Redis (managed Redis)
5. Deploy to Kubernetes (see `infrastructure/kubernetes/`)
6. Set up monitoring (Prometheus + Grafana)
7. Configure backup strategy
8. Perform load testing
9. Create disaster recovery plan

**Optimization**:
1. Tune database performance
2. Configure CDN for frontend
3. Enable GZip compression
4. Implement caching strategy
5. Scale horizontally (multiple API instances)
6. Optimize Celery worker count
7. Fine-tune ML prioritization models

---

## Appendix A: Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      VulnZero Engine                        │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│ API Gateway  │────▶│  Database    │
│  (React)     │     │  (FastAPI)   │     │ (PostgreSQL) │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ├─────────────▶┌──────────────┐
                            │              │    Redis     │
                            │              └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │    Celery    │
                     │   Workers    │
                     └──────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Aggregator  │    │    Patch     │    │ Deployment   │
│   Service    │    │  Generator   │    │   Engine     │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Scanners    │    │   Testing    │    │ Monitoring   │
│ (Wazuh, etc) │    │    Engine    │    │   Service    │
└──────────────┘    └──────────────┘    └──────────────┘
```

---

## Appendix B: API Endpoints Reference

**Authentication**:
- `POST /api/auth/login` - Login
- `POST /api/auth/refresh` - Refresh token
- `POST /api/auth/logout` - Logout

**Vulnerabilities**:
- `GET /api/vulnerabilities` - List vulnerabilities
- `GET /api/vulnerabilities/{id}` - Get vulnerability details
- `GET /api/vulnerabilities/stats` - Get statistics
- `POST /api/vulnerabilities/scan` - Trigger scan

**Patches**:
- `GET /api/patches` - List patches
- `GET /api/patches/{id}` - Get patch details
- `POST /api/patches/{id}/approve` - Approve patch
- `POST /api/patches/{id}/reject` - Reject patch

**Deployments**:
- `GET /api/deployments` - List deployments
- `POST /api/deployments` - Create deployment
- `POST /api/deployments/{id}/rollback` - Rollback deployment

**System**:
- `GET /api/system/health` - Health check
- `GET /api/system/metrics` - System metrics

**Full API documentation**: http://localhost:8000/docs

---

## Appendix C: Environment Variables Reference

See `.env.example` for complete list with descriptions.

**Critical Variables**:
- `API_SECRET_KEY` - JWT signing key (change in production!)
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `FEATURE_MANUAL_APPROVAL_REQUIRED` - Human approval gate
- `FEATURE_CRITICAL_VULN_AUTO_APPROVE` - Auto-approve criticals

---

## Appendix D: Keyboard Shortcuts

**Dashboard**:
- `d` - Go to dashboard
- `v` - Go to vulnerabilities
- `p` - Go to patches
- `/` - Focus search
- `?` - Show keyboard shortcuts

**Patch Review**:
- `a` - Approve patch
- `r` - Reject patch
- `←` - Previous patch
- `→` - Next patch

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-18
**Maintained By**: VulnZero Team

---

*For the latest documentation, visit: https://docs.vulnzero.io*
