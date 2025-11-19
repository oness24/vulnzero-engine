# VulnZero Engine - Implementation Plan for Audit Findings

**Created**: 2025-11-19
**Based On**: Comprehensive Audit Report
**Target Completion**: 2-3 weeks
**Overall Goal**: Achieve 95%+ production readiness

---

## 📋 Executive Summary

This plan addresses **7 identified issues** from the comprehensive audit, organized into 4 implementation phases. The work is prioritized by risk level and business impact.

### Issues Summary:
- **🔴 Critical**: 0 (all resolved in previous session)
- **🟠 High Priority**: 2 issues (must fix before production)
- **🟡 Medium Priority**: 3 issues (should fix soon)
- **🔵 Low Priority**: 2 issues (quality improvements)

### Estimated Timeline:
- **Phase 1 (Critical Path)**: 5-7 days
- **Phase 2 (High Priority)**: 3-4 days
- **Phase 3 (Quality Improvements)**: 2-3 days
- **Phase 4 (Testing & Validation)**: 2-3 days
- **Total**: 12-17 working days

---

## 🎯 Phase 1: Critical Path Items (Days 1-7)

### TASK 1.1: Implement Actual Rollback Execution
**Priority**: 🔴 **CRITICAL**
**Risk**: High - System reports false rollback success
**Effort**: 2-3 days
**Dependencies**: None
**Assignee**: Backend Engineer + DevOps

#### Current State:
```python
# services/deployment_orchestrator/strategies/canary.py:293
rollback_logs.append({
    "status": "rolled_back",  # ⚠️ Lies - nothing was rolled back!
    "message": f"Patch rolled back on {asset.name}",
})
```

#### Implementation Steps:

**Step 1.1.1**: Design rollback command storage (0.5 days)
- Add `rollback_commands` field to `Patch` model
- Store inverse commands when patch is generated
- Migration: `alembic revision -m "add_rollback_commands"`

**Step 1.1.2**: Implement connection to target assets (0.5 days)
- Reuse `ConnectionManager` from deployment engine
- Add rollback-specific connection handling
- Files to modify:
  - `services/deployment_engine/connection_manager.py`

**Step 1.1.3**: Implement rollback command execution (1 day)
- Execute stored rollback commands via SSH/Ansible
- Add command verification
- Handle partial rollback failures
- Files to create/modify:
  - `services/deployment_orchestrator/strategies/canary.py` (lines 286-314)
  - `services/deployment_engine/executor.py` (add `rollback_patch()` method)

**Step 1.1.4**: Add rollback verification (0.5 days)
- Check service health after rollback
- Verify package versions reverted
- Compare against pre-deployment snapshot
- Files to modify:
  - `services/deployment_orchestrator/validators/post_deploy.py`

**Step 1.1.5**: Update logging and error handling (0.5 days)
- Change from placeholder to real execution logs
- Add failure recovery logic
- Emit metrics for monitoring

#### Implementation Example:

```python
# services/deployment_orchestrator/strategies/canary.py

def _execute_rollback(self, deployed_asset_ids: List[int], all_assets: List[Asset]) -> List[Dict]:
    """Execute actual rollback for deployed assets."""
    rollback_logs = []
    asset_map = {asset.id: asset for asset in all_assets}

    self.logger.info(f"🔄 Starting REAL rollback for {len(deployed_asset_ids)} assets")

    # Get the patch to access rollback commands
    patch = self.db.query(Patch).filter_by(id=self.patch.id).first()
    if not patch or not patch.rollback_commands:
        self.logger.error("No rollback commands available for this patch")
        return [{
            "status": "error",
            "message": "Rollback commands not found in patch metadata"
        }]

    for asset_id in deployed_asset_ids:
        asset = asset_map.get(asset_id)
        if not asset:
            rollback_logs.append({
                "asset_id": asset_id,
                "status": "error",
                "message": f"Asset {asset_id} not found for rollback",
                "timestamp": datetime.utcnow().isoformat()
            })
            continue

        try:
            self.logger.info(f"Connecting to {asset.name} for rollback")

            # Use ConnectionManager to connect to asset
            with ConnectionManager() as conn_mgr:
                connection = conn_mgr.connect(
                    hostname=asset.hostname,
                    username=asset.ssh_username,
                    key_file=asset.ssh_key_path
                )

                # Execute rollback commands
                rollback_result = connection.execute_commands(
                    commands=patch.rollback_commands,
                    timeout=300
                )

                if rollback_result.success:
                    # Verify rollback succeeded
                    verification = self._verify_rollback(connection, asset, patch)

                    if verification.success:
                        rollback_logs.append({
                            "asset_id": asset_id,
                            "asset_name": asset.name,
                            "status": "rolled_back",
                            "message": f"Successfully rolled back patch on {asset.name}",
                            "commands_executed": len(patch.rollback_commands),
                            "verification": "passed",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        self.logger.info(f"✅ Rollback verified for {asset.name}")
                    else:
                        raise Exception(f"Rollback verification failed: {verification.error}")
                else:
                    raise Exception(f"Rollback commands failed: {rollback_result.error}")

        except Exception as e:
            self.logger.error(f"❌ Rollback failed for {asset.name}: {e}")
            rollback_logs.append({
                "asset_id": asset_id,
                "asset_name": asset.name if asset else "unknown",
                "status": "rollback_failed",
                "message": f"Rollback execution failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            })

    return rollback_logs

def _verify_rollback(self, connection, asset: Asset, patch: Patch) -> VerificationResult:
    """Verify that rollback actually succeeded."""
    try:
        # Check service is running
        if patch.service_name:
            result = connection.execute(f"systemctl is-active {patch.service_name}")
            if result.return_code != 0:
                return VerificationResult(
                    success=False,
                    error=f"Service {patch.service_name} not running after rollback"
                )

        # Check package version if applicable
        if patch.package_name and patch.previous_version:
            result = connection.execute(f"dpkg -l | grep {patch.package_name}")
            if patch.previous_version not in result.stdout:
                return VerificationResult(
                    success=False,
                    error=f"Package version not reverted to {patch.previous_version}"
                )

        return VerificationResult(success=True)

    except Exception as e:
        return VerificationResult(success=False, error=str(e))
```

#### Database Migration:

```python
# alembic/versions/20251119_add_rollback_commands.py

def upgrade():
    op.add_column('patches',
        sa.Column('rollback_commands', sa.JSON, nullable=True)
    )
    op.add_column('patches',
        sa.Column('previous_version', sa.String(100), nullable=True)
    )
    op.add_column('patches',
        sa.Column('service_name', sa.String(100), nullable=True)
    )

def downgrade():
    op.drop_column('patches', 'rollback_commands')
    op.drop_column('patches', 'previous_version')
    op.drop_column('patches', 'service_name')
```

#### Testing Strategy:
1. Unit tests for `_execute_rollback()` with mocked connections
2. Integration tests with actual Docker containers
3. End-to-end test: deploy → fail → verify rollback
4. Test partial rollback failures

#### Acceptance Criteria:
- ✅ Rollback commands are executed on target assets
- ✅ Service health verified after rollback
- ✅ Logs accurately reflect rollback status
- ✅ Partial failures handled gracefully
- ✅ Metrics emitted for monitoring

---

### TASK 1.2: Add Integration Tests for Celery Tasks
**Priority**: 🔴 **CRITICAL**
**Risk**: High - No automated verification of core functionality
**Effort**: 3-4 days
**Dependencies**: None
**Assignee**: QA Engineer + Backend Engineer

#### Current State:
- ✅ Unit tests exist for individual components
- ❌ No integration tests for Celery task execution
- ❌ No verification that API → Celery → Database flow works

#### Implementation Steps:

**Step 1.2.1**: Set up Celery test infrastructure (1 day)
- Configure test Celery worker with in-memory broker
- Create test fixtures for database + Celery
- Add Docker Compose for integration test environment

**Step 1.2.2**: Write deployment task integration tests (1 day)
- Test: API endpoint triggers Celery task
- Test: Task creates deployment record
- Test: Task updates deployment status
- Test: Task handles failures gracefully

**Step 1.2.3**: Write vulnerability scan task integration tests (1 day)
- Test: Scan endpoint triggers scanner tasks
- Test: Scan results saved to database
- Test: Multiple scanners can run in parallel
- Test: Scan failures are logged

**Step 1.2.4**: Add rollback integration tests (0.5 days)
- Test: Failed deployment triggers automatic rollback
- Test: Manual rollback endpoint works
- Test: Rollback updates deployment status

**Step 1.2.5**: Add CI/CD integration (0.5 days)
- Update GitHub Actions workflow
- Run integration tests on every PR
- Add test coverage reporting

#### Implementation Example:

```python
# tests/integration/test_deployment_celery_tasks.py

import pytest
from celery import Celery
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.main import app
from services.deployment_orchestrator.tasks.deployment_tasks import deploy_patch
from shared.models import Deployment, Patch, Asset
from tests.conftest import test_db, celery_app, celery_worker


class TestDeploymentCeleryIntegration:
    """Integration tests for deployment Celery tasks."""

    @pytest.mark.integration
    def test_api_triggers_deployment_task(
        self,
        test_db: Session,
        celery_worker,
        authenticated_client: TestClient
    ):
        """Test that POST /deployments triggers Celery task."""
        # Arrange
        patch = create_test_patch(test_db, status="approved")
        asset = create_test_asset(test_db)

        # Act
        response = authenticated_client.post(
            "/api/v1/deployments",
            json={
                "patch_id": patch.id,
                "asset_id": asset.id,
                "strategy": "immediate"
            }
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "id" in data

        # Wait for Celery task to complete
        deployment = test_db.query(Deployment).filter_by(id=data["id"]).first()
        assert deployment is not None

        # Give Celery time to process
        import time
        time.sleep(2)

        test_db.refresh(deployment)
        assert deployment.status in ["in_progress", "completed"]

    @pytest.mark.integration
    def test_deployment_task_execution_flow(
        self,
        test_db: Session,
        celery_app: Celery,
        celery_worker
    ):
        """Test complete deployment task execution."""
        # Arrange
        patch = create_test_patch(test_db, status="approved")
        asset = create_test_asset(test_db)

        # Act
        result = deploy_patch.delay(
            patch_id=patch.id,
            asset_ids=[asset.id],
            strategy="immediate",
            user_id=1
        )

        # Wait for task
        task_result = result.get(timeout=10)

        # Assert
        assert task_result["success"] is True

        # Verify database updated
        deployment = test_db.query(Deployment).filter_by(
            patch_id=patch.id,
            asset_id=asset.id
        ).first()
        assert deployment is not None
        assert deployment.status == "completed"

    @pytest.mark.integration
    def test_failed_deployment_triggers_rollback(
        self,
        test_db: Session,
        celery_worker,
        monkeypatch
    ):
        """Test automatic rollback on deployment failure."""
        # Arrange
        patch = create_test_patch(test_db, status="approved")
        assets = [create_test_asset(test_db) for _ in range(5)]

        # Simulate deployment failure on 3rd asset
        def mock_deploy_failing(*args, **kwargs):
            if args[0].id == assets[2].id:
                raise Exception("Deployment failed")
            return {"success": True}

        monkeypatch.setattr(
            "services.deployment_engine.executor.Executor.deploy",
            mock_deploy_failing
        )

        # Act
        result = deploy_patch.delay(
            patch_id=patch.id,
            asset_ids=[a.id for a in assets],
            strategy="canary",
            strategy_params={"rollback_on_failure": True}
        )

        task_result = result.get(timeout=30)

        # Assert
        assert task_result["success"] is False
        assert "rolled_back" in task_result.get("status", "").lower()

        # Verify rollback was executed
        deployment = test_db.query(Deployment).filter_by(
            patch_id=patch.id
        ).first()
        assert deployment.status == "rolled_back"
        assert len(deployment.execution_logs) > 0

        # Check rollback logs
        rollback_logs = [
            log for log in deployment.execution_logs
            if log.get("action") == "automatic_rollback"
        ]
        assert len(rollback_logs) > 0


class TestVulnerabilityScanCeleryIntegration:
    """Integration tests for vulnerability scan tasks."""

    @pytest.mark.integration
    def test_scan_endpoint_triggers_tasks(
        self,
        authenticated_client: TestClient,
        celery_worker
    ):
        """Test POST /vulnerabilities/scan triggers Celery tasks."""
        # Act
        response = authenticated_client.post("/api/v1/vulnerabilities/scan")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert len(data["tasks"]) == 3  # wazuh, qualys, tenable

        # Verify all tasks have IDs
        for task_info in data["tasks"]:
            assert "task_id" in task_info
            assert "scanner" in task_info

    @pytest.mark.integration
    def test_scan_results_saved_to_database(
        self,
        test_db: Session,
        celery_worker,
        mock_wazuh_api
    ):
        """Test scan results are persisted to database."""
        # Arrange
        initial_count = test_db.query(Vulnerability).count()

        # Act
        from services.aggregator.tasks.scan_tasks import scan_wazuh
        result = scan_wazuh.delay()
        task_result = result.get(timeout=15)

        # Assert
        assert task_result["success"] is True
        assert task_result["count"] > 0

        # Verify database
        final_count = test_db.query(Vulnerability).count()
        assert final_count > initial_count
```

#### Test Fixtures:

```python
# tests/conftest.py (additions)

@pytest.fixture(scope="session")
def celery_config():
    """Celery configuration for testing."""
    return {
        "broker_url": "memory://",
        "result_backend": "cache+memory://",
        "task_always_eager": False,  # Run tasks asynchronously
        "task_eager_propagates": True,
    }

@pytest.fixture(scope="session")
def celery_worker_parameters():
    """Parameters for Celery worker."""
    return {
        "queues": ["default", "deployments", "scans"],
        "pool": "solo",  # Single-threaded for testing
    }

@pytest.fixture
def celery_app(celery_config):
    """Celery app for testing."""
    from services.deployment_orchestrator.tasks.celery_app import celery_app
    celery_app.config_from_object(celery_config)
    return celery_app
```

#### CI/CD Integration:

```yaml
# .github/workflows/tests.yml (additions)

integration-tests:
  runs-on: ubuntu-latest
  services:
    postgres:
      image: postgres:15
      env:
        POSTGRES_PASSWORD: testpass
      options: >-
        --health-cmd pg_isready
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5

    redis:
      image: redis:7-alpine
      options: >-
        --health-cmd "redis-cli ping"
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5

  steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -e ".[dev]"
        pip install pytest-celery

    - name: Run integration tests
      env:
        DATABASE_URL: postgresql://postgres:testpass@localhost:5432/testdb
        REDIS_URL: redis://localhost:6379/0
      run: |
        pytest tests/integration/ -v --cov=services --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

#### Acceptance Criteria:
- ✅ Integration tests run in CI/CD
- ✅ All Celery tasks have integration test coverage
- ✅ Tests verify end-to-end API → Celery → Database flow
- ✅ Test coverage > 80% for Celery tasks
- ✅ Tests pass consistently (no flaky tests)

---

## 🎯 Phase 2: High-Priority Improvements (Days 8-11)

### TASK 2.1: Add Task Status Tracking Endpoint
**Priority**: 🟡 **MEDIUM**
**Risk**: Medium - Poor user experience
**Effort**: 1 day
**Dependencies**: None

#### Implementation:

```python
# services/api_gateway/api/v1/endpoints/tasks.py (NEW FILE)

from fastapi import APIRouter, HTTPException, Depends
from celery.result import AsyncResult
from services.api_gateway.core.security import get_current_user

router = APIRouter()

@router.get("/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the status of a Celery task.

    Returns:
    - state: PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED
    - result: Task result if completed
    - info: Additional task information
    """
    result = AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "state": result.state,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
    }

    if result.ready():
        if result.successful():
            response["result"] = result.result
        else:
            response["error"] = str(result.info)
    else:
        response["info"] = result.info

    return response
```

---

### TASK 2.2: Fix CORS Origin Hardcoding
**Priority**: 🟡 **MEDIUM**
**Risk**: Low - Security misconfiguration
**Effort**: 0.5 days

#### Implementation:

```python
# services/api_gateway/middleware/security_headers.py

from shared.config.settings import settings

class CORSSecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # Load from configuration
        self.allowed_origins = settings.cors_origins_list

    def _is_allowed_origin(self, origin: str) -> bool:
        """Check if origin is allowed (exact match)."""
        return origin in self.allowed_origins
```

---

### TASK 2.3: Add Rate Limiting to Expensive Endpoints
**Priority**: 🟡 **MEDIUM**
**Risk**: Medium - Cost/resource abuse
**Effort**: 0.5 days

#### Implementation:

```python
# services/api_gateway/api/v1/endpoints/vulnerabilities.py

from slowapi import Limiter
from fastapi import Request

limiter = Limiter(key_func=get_remote_address)

@router.post("/scan")
@limiter.limit("5/hour")  # Only 5 scans per hour per IP
async def trigger_scan(
    request: Request,
    scanner: Optional[str] = Query(None),
    current_user: dict = Depends(require_role("operator")),
):
    # ... existing implementation
```

---

## 🎯 Phase 3: Quality Improvements (Days 12-14)

### TASK 3.1: Tighten CSP Policy
**Priority**: 🔵 **LOW**
**Effort**: 1 day

#### Options:

**Option A: Use CSP Nonces** (Recommended)
```python
# Generate nonce per request
import secrets

@app.middleware("http")
async def add_csp_nonce(request: Request, call_next):
    nonce = secrets.token_urlsafe(16)
    request.state.csp_nonce = nonce
    response = await call_next(request)

    # Update CSP to use nonce instead of unsafe-inline
    response.headers["Content-Security-Policy"] = (
        f"default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}'; "
        f"style-src 'self' 'nonce-{nonce}'; "
        # ... rest of CSP
    )
    return response
```

**Option B: Separate Dev/Prod CSP**
```python
if settings.environment == "production":
    csp = STRICT_CSP  # No unsafe-inline/eval
else:
    csp = RELAXED_CSP  # Allows unsafe for development
```

---

### TASK 3.2: Standardize Error Response Format
**Priority**: 🔵 **LOW**
**Effort**: 0.5 days

Create consistent error schema across all endpoints.

---

### TASK 3.3: Add OpenAPI Documentation for Task Fields
**Priority**: 🔵 **LOW**
**Effort**: 0.5 days

Update Pydantic response models to include `task_id` field.

---

## 🎯 Phase 4: Testing & Validation (Days 15-17)

### TASK 4.1: End-to-End Testing
- Deploy to staging environment
- Run full vulnerability scan → patch → deploy → monitor workflow
- Test rollback scenarios
- Load testing with k6 or Locust

### TASK 4.2: Security Audit
- Run OWASP ZAP automated scan
- Manual penetration testing
- Review all security headers in production

### TASK 4.3: Performance Testing
- Load test Celery task queue
- Verify database query performance
- Check memory leaks in long-running tasks

---

## 📊 Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Production Readiness | 85% | 95% | Audit score |
| Test Coverage | 60% | 85% | pytest --cov |
| Integration Test Coverage | 0% | 80% | Celery task tests |
| Security Headers Score | B+ | A | securityheaders.com |
| Rollback Success Rate | 0% (placeholder) | 95% | Integration tests |
| API Response Time (p95) | Unknown | <500ms | Load testing |

---

## 🚀 Deployment Strategy

### Phase Rollout:
1. **Phase 1 → Staging**: Deploy after integration tests pass
2. **Phase 2 → Staging**: Deploy and monitor for 48 hours
3. **Phase 3 → Staging**: Final quality improvements
4. **All Phases → Production**: Deploy during maintenance window

### Rollback Plan:
- All changes behind feature flags where possible
- Database migrations are reversible
- Keep previous Docker images for quick rollback
- Monitor error rates for 24 hours post-deployment

---

## 📝 Documentation Updates Required

1. Update `README.md` with new task status endpoint
2. Update API documentation (OpenAPI schema)
3. Document rollback command format
4. Add integration testing guide
5. Update deployment runbook

---

## ✅ Definition of Done

For each task:
- [ ] Implementation completed and code reviewed
- [ ] Unit tests written and passing
- [ ] Integration tests written (where applicable)
- [ ] Documentation updated
- [ ] Deployed to staging and manually tested
- [ ] No new security vulnerabilities introduced
- [ ] Performance impact assessed
- [ ] Merged to main branch

---

## 👥 Team Assignments

| Role | Responsibilities | Tasks |
|------|-----------------|-------|
| **Backend Engineer** | Rollback implementation, API endpoints | 1.1, 2.1, 2.2, 2.3 |
| **QA Engineer** | Integration tests, end-to-end testing | 1.2, 4.1, 4.3 |
| **DevOps Engineer** | CI/CD, deployment, monitoring | 1.1.1, 1.2.5, Phase 4 |
| **Security Engineer** | CSP policy, security audit | 3.1, 4.2 |
| **Tech Lead** | Code review, architecture decisions | All |

---

## 🎯 Quick Start (Next Steps)

1. **Review this plan** with the team
2. **Assign tasks** to team members
3. **Create Jira/GitHub issues** for each task
4. **Set up project board** for tracking
5. **Schedule daily standups** during implementation
6. **Start with Phase 1, Task 1.1** (highest priority)

---

**Plan Created By**: Claude (Sonnet 4.5)
**Plan Date**: 2025-11-19
**Estimated Completion**: 2025-12-10
**Review Required**: Yes (before implementation)
