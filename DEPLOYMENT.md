# VulnZero Production Deployment Guide

**Version:** 1.0.0
**Last Updated:** 2025-11-19
**Environment:** Production

## Table of Contents

- [Prerequisites](#prerequisites)
- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Environment Setup](#environment-setup)
- [Deployment Steps](#deployment-steps)
- [Post-Deployment Verification](#post-deployment-verification)
- [Rollback Procedures](#rollback-procedures)
- [Monitoring & Alerts](#monitoring--alerts)
- [Backup & Recovery](#backup--recovery)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum Hardware:**
- CPU: 4 cores (8 cores recommended)
- RAM: 16GB (32GB recommended)
- Disk: 100GB SSD (500GB recommended for production)
- Network: 1 Gbps

**Software:**
- Docker 24.0+ and Docker Compose 2.20+
- PostgreSQL 15+ (if external database)
- Redis 7+ (if external cache)
- Linux OS (Ubuntu 22.04 LTS or RHEL 8+)

### Access Requirements

- [ ] SSH access to production servers
- [ ] Docker Registry credentials
- [ ] Database admin credentials
- [ ] Cloud provider access (AWS/GCP/Azure)
- [ ] DNS management access
- [ ] SSL certificates ready

### External Services

- [ ] NVD API key obtained
- [ ] OpenAI/Anthropic API keys
- [ ] Wazuh instance configured (if using)
- [ ] SMTP server configured
- [ ] Sentry project created
- [ ] Slack webhook configured
- [ ] Backup storage (S3/GCS) configured

---

## Pre-Deployment Checklist

### Security

- [ ] All secrets generated using secure methods (`openssl rand -hex 32`)
- [ ] `.env.production` created from template and reviewed
- [ ] No secrets in git repository
- [ ] Firewall rules configured
- [ ] SSL/TLS certificates installed and valid
- [ ] CORS origins configured correctly
- [ ] Rate limiting enabled
- [ ] Security headers enabled (CSP, HSTS, etc.)

### Infrastructure

- [ ] DNS records configured
- [ ] Load balancer configured (if applicable)
- [ ] Database backups scheduled
- [ ] Monitoring alerts configured
- [ ] Log aggregation setup (if using)
- [ ] CDN configured (if applicable)
- [ ] Network security groups configured

### Application

- [ ] Database migrations tested in staging
- [ ] All tests passing (`make test`)
- [ ] Code linting passed (`make lint`)
- [ ] Security scan passed (`make security-check`)
- [ ] Docker images built and tagged
- [ ] Health check endpoints verified
- [ ] Performance benchmarks reviewed

### Documentation

- [ ] Runbook reviewed
- [ ] On-call rotation configured
- [ ] Incident response plan ready
- [ ] Rollback procedures tested
- [ ] Team notified of deployment

---

## Environment Setup

### 1. Server Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installations
docker --version
docker-compose --version

# Create application directory
sudo mkdir -p /opt/vulnzero
sudo chown $USER:$USER /opt/vulnzero
cd /opt/vulnzero
```

### 2. Clone Repository

```bash
# Clone from git (production branch)
git clone -b main https://github.com/your-org/vulnzero-engine.git .

# Or deploy from release tag
git clone --branch v1.0.0 https://github.com/your-org/vulnzero-engine.git .
```

### 3. Configure Environment

```bash
# Copy production environment template
cp .env.production.template .env.production

# Edit environment variables
nano .env.production
# OR use your organization's secrets management
# vault kv get -field=env secret/vulnzero/production > .env.production

# Secure the file
chmod 600 .env.production
```

### 4. Create Required Directories

```bash
# Create data directories
mkdir -p data/postgres data/redis data/prometheus data/grafana
mkdir -p logs backups/postgres uploads

# Set permissions
chmod 700 data/postgres
chmod 700 backups
```

### 5. Load Environment

```bash
# Load production environment
set -a
source .env.production
set +a
```

---

## Deployment Steps

### Step 1: Pre-Deployment Database Backup

```bash
# If migrating from existing installation
docker-compose exec postgres pg_dump -U ${DATABASE_USER} ${DATABASE_NAME} | gzip > backups/postgres/pre-deploy-$(date +%Y%m%d-%H%M%S).sql.gz

# Verify backup
ls -lh backups/postgres/
```

### Step 2: Pull/Build Docker Images

```bash
# Option A: Pull from registry
docker-compose -f docker-compose.prod.yml pull

# Option B: Build locally
docker-compose -f docker-compose.prod.yml build --no-cache
```

### Step 3: Database Migrations

```bash
# Start only database services
docker-compose -f docker-compose.prod.yml up -d postgres redis

# Wait for database to be ready
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U ${DATABASE_USER}

# Run migrations
docker-compose -f docker-compose.prod.yml run --rm api alembic upgrade head

# Verify migrations
docker-compose -f docker-compose.prod.yml run --rm api alembic current
```

### Step 4: Start Services

```bash
# Start all services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Verify all services are running
docker-compose -f docker-compose.prod.yml ps
```

### Step 5: Verify Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check Prometheus
curl http://localhost:9090/-/healthy

# Check Grafana
curl http://localhost:3001/api/health

# Expected response: All services should return healthy status
```

---

## Post-Deployment Verification

### Functional Tests

```bash
# Run smoke tests
docker-compose -f docker-compose.prod.yml run --rm api pytest tests/integration/ -m smoke

# Test API endpoints
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'

# Test vulnerability scanning
curl -X POST http://localhost:8000/api/vulnerabilities/scan \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"asset_id": "test-asset-1"}'
```

### Performance Verification

```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health

# Monitor resource usage
docker stats

# Check Celery workers
docker-compose -f docker-compose.prod.yml exec celery-worker celery -A shared.celery_app inspect active
```

### Security Verification

```bash
# Verify security headers
curl -I http://localhost:8000/

# Expected headers:
# - Content-Security-Policy
# - Strict-Transport-Security
# - X-Frame-Options: DENY
# - X-Content-Type-Options: nosniff

# Check no exposed secrets
docker-compose -f docker-compose.prod.yml config | grep -i "password\|secret\|key" | grep -v "CHANGE_ME"
# Should not show actual secrets
```

### Monitoring Setup Verification

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job, health}'

# Verify Grafana dashboards
# Navigate to http://localhost:3001
# Login with configured credentials
# Verify all dashboards loading
```

---

## Rollback Procedures

### Quick Rollback (< 5 minutes)

```bash
# Stop current deployment
docker-compose -f docker-compose.prod.yml down

# Restore previous images
docker-compose -f docker-compose.prod.yml -f docker-compose.rollback.yml up -d

# Rollback database migrations (if needed)
docker-compose -f docker-compose.prod.yml run --rm api alembic downgrade -1

# Verify services
docker-compose -f docker-compose.prod.yml ps
curl http://localhost:8000/health
```

### Full Rollback (Database + Application)

```bash
# 1. Stop all services
docker-compose -f docker-compose.prod.yml down

# 2. Restore database from backup
BACKUP_FILE="backups/postgres/pre-deploy-YYYYMMDD-HHMMSS.sql.gz"
docker-compose -f docker-compose.prod.yml up -d postgres
sleep 10

gunzip -c $BACKUP_FILE | docker-compose -f docker-compose.prod.yml exec -T postgres psql -U ${DATABASE_USER} -d ${DATABASE_NAME}

# 3. Start previous version
git checkout previous-release-tag
docker-compose -f docker-compose.prod.yml up -d

# 4. Verify
curl http://localhost:8000/health
```

---

## Monitoring & Alerts

### Key Metrics to Monitor

**Application Metrics:**
- API response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- Request throughput (req/sec)
- Active user sessions

**Infrastructure Metrics:**
- CPU usage (< 80%)
- Memory usage (< 85%)
- Disk usage (< 80%)
- Network throughput

**Database Metrics:**
- Connection pool usage
- Query response time
- Slow query count
- Replication lag (if applicable)

**Celery Metrics:**
- Task queue length
- Worker availability
- Task failure rate
- Average task execution time

### Alert Configuration

**Critical Alerts (PagerDuty/Phone):**
- API down (health check failing)
- Database connection failures
- Disk usage > 90%
- Error rate > 5%

**Warning Alerts (Slack/Email):**
- API response time > 1s (p95)
- Memory usage > 80%
- Celery queue length > 1000
- Failed background tasks > 10/min

### Grafana Dashboards

Access: `https://grafana.vulnzero.example.com`

**Key Dashboards:**
- System Overview
- API Performance
- Database Metrics
- Celery Workers
- Error Tracking

---

## Backup & Recovery

### Automated Backups

```bash
# Database backups run daily at 2 AM (configured in .env.production)
# BACKUP_SCHEDULE="0 2 * * *"

# Manual backup
docker-compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U ${DATABASE_USER} ${DATABASE_NAME} | \
  gzip > backups/postgres/manual-$(date +%Y%m%d-%H%M%S).sql.gz

# Verify backup
gunzip -c backups/postgres/manual-*.sql.gz | head -20
```

### S3 Backup Sync (if configured)

```bash
# Upload to S3
aws s3 sync backups/ s3://vulnzero-backups-prod/$(date +%Y%m%d)/ \
  --exclude "*" \
  --include "*.sql.gz"

# Download from S3
aws s3 sync s3://vulnzero-backups-prod/20251119/ backups/restored/
```

### Recovery Testing

```bash
# Test restore (in isolated environment)
# 1. Create test database
# 2. Restore backup
# 3. Run application
# 4. Verify functionality
# 5. Document recovery time
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs service-name

# Check resource constraints
docker stats

# Verify environment variables
docker-compose -f docker-compose.prod.yml config

# Check disk space
df -h
```

### Database Connection Issues

```bash
# Test database connectivity
docker-compose -f docker-compose.prod.yml exec postgres psql -U ${DATABASE_USER} -d ${DATABASE_NAME} -c "SELECT version();"

# Check connection pool
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U ${DATABASE_USER} -d ${DATABASE_NAME} -c \
  "SELECT count(*) FROM pg_stat_activity;"

# Restart database
docker-compose -f docker-compose.prod.yml restart postgres
```

### High Memory Usage

```bash
# Identify memory-hungry processes
docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Reduce worker concurrency
# Edit .env.production: CELERY_WORKER_CONCURRENCY=4
docker-compose -f docker-compose.prod.yml restart celery-worker
```

### Slow API Response Times

```bash
# Check database slow queries
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U ${DATABASE_USER} -d ${DATABASE_NAME} -c \
  "SELECT query, calls, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Check Redis connection
docker-compose -f docker-compose.prod.yml exec redis redis-cli -a ${REDIS_PASSWORD} ping

# Review application logs
docker-compose -f docker-compose.prod.yml logs api | grep -i "slow\|timeout"
```

### Celery Tasks Not Processing

```bash
# Check worker status
docker-compose -f docker-compose.prod.yml exec celery-worker \
  celery -A shared.celery_app inspect active

# Check queue length
docker-compose -f docker-compose.prod.yml exec redis redis-cli -a ${REDIS_PASSWORD} llen celery

# Restart workers
docker-compose -f docker-compose.prod.yml restart celery-worker celery-beat
```

---

## Support & Escalation

### On-Call Contacts

- **Primary:** ops-team@example.com
- **Secondary:** dev-team@example.com
- **PagerDuty:** https://example.pagerduty.com

### Documentation

- **Architecture:** `/docs/ARCHITECTURE.md`
- **API Docs:** `https://api.vulnzero.example.com/docs`
- **Runbooks:** `/docs/runbooks/`
- **Wiki:** `https://wiki.example.com/vulnzero`

### Incident Response

1. **Acknowledge** - Respond to alert within 5 minutes
2. **Assess** - Determine severity and impact
3. **Mitigate** - Apply immediate fix or rollback
4. **Communicate** - Update stakeholders
5. **Resolve** - Fix root cause
6. **Document** - Write postmortem

---

## Maintenance Windows

**Scheduled Maintenance:**
- Weekly: Sundays 02:00-04:00 UTC (minor updates)
- Monthly: First Sunday 02:00-06:00 UTC (major updates)
- Emergency: As needed with 1-hour notice

**Maintenance Procedure:**
1. Notify users 24 hours in advance
2. Create backup
3. Enable maintenance mode
4. Perform updates
5. Run verification tests
6. Disable maintenance mode
7. Monitor for 1 hour
8. Send completion notice

---

## Change Log

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-11-19 | Initial production deployment guide | DevOps Team |

---

## Appendix

### A. Environment Variables Reference

See `.env.production.template` for complete list.

### B. Port Reference

| Service | Port | Access |
|---------|------|--------|
| API Gateway | 8000 | Public |
| PostgreSQL | 5432 | Internal |
| Redis | 6379 | Internal |
| Prometheus | 9090 | Internal |
| Grafana | 3001 | Internal/VPN |
| Flower | 5555 | Internal/VPN |

### C. File Locations

| Purpose | Location |
|---------|----------|
| Application | `/opt/vulnzero` |
| Data | `/opt/vulnzero/data` |
| Logs | `/opt/vulnzero/logs` |
| Backups | `/opt/vulnzero/backups` |
| SSL Certs | `/etc/ssl/vulnzero` |

### D. Useful Commands

```bash
# View all logs
docker-compose -f docker-compose.prod.yml logs -f --tail=100

# Restart specific service
docker-compose -f docker-compose.prod.yml restart api

# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=4

# Execute command in container
docker-compose -f docker-compose.prod.yml exec api python -m scripts.maintenance

# Export metrics
curl http://localhost:8000/metrics > metrics.txt
```
