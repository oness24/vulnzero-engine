# VulnZero - Immediate Action Plan

**Created**: 2025-11-18
**Priority**: Address before production deployment

---

## 🚨 CRITICAL ACTIONS (Do NOW - 2-3 hours)

### 1. Security Audit: .env File Exposure

**Status**: 🔴 CRITICAL
**Time Estimate**: 30 minutes
**Priority**: P0 - Must do immediately

```bash
# Step 1: Check if .env was ever committed to git
git log --all --full-history --pretty=format:"%H %s" -- .env

# Step 2: If found, remove from git history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

# Step 3: Force push (coordinate with team first!)
git push origin --force --all

# Step 4: Verify .gitignore
echo ".env" >> .gitignore
git add .gitignore
git commit -m "security: Ensure .env is properly ignored"
```

**Action Items**:
- [ ] Check git history for .env file
- [ ] Remove from history if found
- [ ] Rotate ALL API keys:
  - [ ] OpenAI API key
  - [ ] Anthropic API key
  - [ ] Database password
  - [ ] Redis password
  - [ ] JWT secret key
  - [ ] Any other secrets in .env
- [ ] Update .env.example (remove real values)
- [ ] Verify .gitignore includes .env

---

### 2. CORS Configuration Hardening

**Status**: 🟠 HIGH
**Time Estimate**: 15 minutes
**Priority**: P1

**Current Issue**:
```python
# api/main.py:124
allow_origins=settings.cors_origins_list if settings.is_production else ["*"]
```

**Fix**:
```python
# Set specific origins even for development
CORS_ORIGINS_DEV = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list if settings.is_production else CORS_ORIGINS_DEV,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)
```

**Action Items**:
- [ ] Update api/main.py with specific CORS origins
- [ ] Test frontend still connects correctly
- [ ] Update .env.example with production CORS origins

---

### 3. Add Security Test Suite

**Status**: 🟠 HIGH
**Time Estimate**: 1-2 hours
**Priority**: P1

**Create**: `tests/security/test_sql_injection.py`

```python
import pytest
from sqlalchemy import select, text
from shared.models.models import Vulnerability

@pytest.mark.asyncio
async def test_sql_injection_prevention(db_session):
    """Test that SQLAlchemy ORM prevents SQL injection"""
    malicious_input = "1' OR '1'='1"

    # Should NOT return all records
    result = await db_session.execute(
        select(Vulnerability).where(Vulnerability.id == malicious_input)
    )
    vulns = result.scalars().all()
    assert len(vulns) == 0, "SQL injection protection failed"

@pytest.mark.asyncio
async def test_parameterized_queries(db_session):
    """Test that raw queries use proper parameterization"""
    user_input = "'; DROP TABLE vulnerabilities; --"

    # Should safely handle malicious input
    result = await db_session.execute(
        text("SELECT * FROM vulnerabilities WHERE cve_id = :cve_id"),
        {"cve_id": user_input}
    )
    # Should execute safely without SQL injection
    assert result is not None

@pytest.mark.asyncio
async def test_xss_prevention():
    """Test XSS prevention in API responses"""
    # Add tests for HTML escaping in responses
    pass
```

**Create**: `tests/security/test_authentication.py`

```python
import pytest
from fastapi.testclient import TestClient

def test_protected_routes_require_auth(client: TestClient):
    """Test that protected routes reject unauthenticated requests"""
    response = client.get("/api/vulnerabilities/")
    assert response.status_code == 401

def test_invalid_token_rejected(client: TestClient):
    """Test that invalid tokens are rejected"""
    response = client.get(
        "/api/vulnerabilities/",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401

def test_expired_token_rejected(client: TestClient):
    """Test that expired tokens are rejected"""
    # Create expired token
    # Test rejection
    pass
```

**Action Items**:
- [ ] Create tests/security/ directory
- [ ] Add SQL injection tests
- [ ] Add XSS prevention tests
- [ ] Add authentication tests
- [ ] Add CSRF tests
- [ ] Run security test suite
- [ ] Fix any failures

---

## 🟡 HIGH PRIORITY (This Week - 8-12 hours)

### 4. Clean Up Service Directory Duplication

**Status**: 🟠 HIGH
**Time Estimate**: 1 hour
**Priority**: P2

**Current Problem**:
```
services/
├── patch-generator/     # Kebab-case
├── patch_generator/     # Snake-case (duplicate)
├── deployment-engine/   # Duplicate
├── deployment_engine/   # Duplicate
└── testing-engine/      # Duplicate
    testing_engine/      # Duplicate
```

**Action Items**:
- [ ] Standardize on snake_case naming
- [ ] Remove kebab-case directories
- [ ] Update all imports
- [ ] Test all services still work
- [ ] Update docker-compose.yml if needed
- [ ] Update CI/CD paths

---

### 5. Create Kubernetes Manifests

**Status**: 🟡 MEDIUM
**Time Estimate**: 6-8 hours
**Priority**: P2

**Create**: `infrastructure/kubernetes/`

Required files:
```
kubernetes/
├── namespace.yaml
├── configmap.yaml
├── secrets.yaml (template)
├── deployments/
│   ├── api.yaml
│   ├── celery-worker.yaml
│   ├── celery-beat.yaml
│   ├── frontend.yaml
│   └── flower.yaml
├── services/
│   ├── api-service.yaml
│   ├── frontend-service.yaml
│   └── flower-service.yaml
├── ingress.yaml
├── postgres/
│   ├── statefulset.yaml
│   ├── service.yaml
│   └── pvc.yaml
└── redis/
    ├── deployment.yaml
    ├── service.yaml
    └── pvc.yaml
```

**Action Items**:
- [ ] Create K8s namespace manifest
- [ ] Create deployment manifests for all services
- [ ] Create service manifests
- [ ] Create ingress with TLS
- [ ] Create persistent volume claims
- [ ] Create secrets template
- [ ] Create ConfigMap
- [ ] Test on local K8s (minikube/kind)
- [ ] Document deployment process

---

### 6. Add Grafana Dashboards

**Status**: 🟡 MEDIUM
**Time Estimate**: 3-4 hours
**Priority**: P2

**Create**: `monitoring/grafana/dashboards/vulnzero-overview.json`

Required dashboards:
1. **System Overview** - CPU, memory, disk, network
2. **Application Metrics** - Request rates, response times, error rates
3. **Vulnerability Metrics** - Detection rates, patch success, deployment stats
4. **Database Metrics** - Connection pool, query performance
5. **Celery Metrics** - Task queue depth, worker status

**Action Items**:
- [ ] Create system overview dashboard
- [ ] Create application metrics dashboard
- [ ] Create vulnerability tracking dashboard
- [ ] Create database performance dashboard
- [ ] Create Celery monitoring dashboard
- [ ] Test dashboards with real data
- [ ] Export dashboard JSON
- [ ] Add provisioning configuration

---

## 📋 RECOMMENDED WORKFLOW

### Day 1: Security (2-3 hours)
```bash
Morning:
1. Check git history for .env        (15 min)
2. Clean git history if needed       (15 min)
3. Rotate all API keys               (30 min)
4. Fix CORS configuration            (15 min)

Afternoon:
5. Create security test suite        (1-2 hours)
6. Run all security tests            (15 min)
7. Fix any failures                  (30 min)
```

### Day 2-3: Infrastructure Cleanup (8 hours)
```bash
Day 2:
1. Clean up service directories      (1 hour)
2. Test all services                 (30 min)
3. Start K8s manifest creation       (4 hours)

Day 3:
4. Complete K8s manifests            (3 hours)
5. Test K8s deployment locally       (2 hours)
```

### Day 4-5: Monitoring (6 hours)
```bash
Day 4:
1. Create Grafana dashboards         (4 hours)

Day 5:
2. Add Prometheus alert rules        (2 hours)
3. Test monitoring stack             (1 hour)
4. Document monitoring setup         (1 hour)
```

---

## ✅ Success Criteria

**After completing this action plan, you should have**:

- [✅] No secrets in git history
- [✅] All API keys rotated
- [✅] Hardened CORS configuration
- [✅] Comprehensive security test suite
- [✅] Clean service directory structure
- [✅] Production-ready K8s manifests
- [✅] Complete monitoring dashboards
- [✅] Alert rules for critical metrics
- [✅] Updated documentation

**Production Readiness Score**: Should increase from 60% to ~85%

---

## 🚀 Next Steps After This Plan

**Week 2:**
1. Performance testing and optimization
2. Load balancer configuration
3. Auto-scaling policies
4. Disaster recovery procedures

**Week 3:**
5. Staging environment deployment
6. Integration testing in staging
7. Security penetration testing
8. User acceptance testing

**Week 4:**
9. Final production checklist
10. Go-live preparation
11. Production deployment
12. Post-deployment monitoring

---

## 📞 Need Help?

If you encounter issues:
1. Check COMPREHENSIVE_REVIEW.md for detailed analysis
2. Review NEXT_STEPS.md for additional context
3. Consult claude.md for implementation details
4. Create GitHub issues for tracking

---

**Created**: 2025-11-18
**Last Updated**: 2025-11-18
**Estimated Total Time**: 15-20 hours over 1 week
