# VulnZero - Technical Debt & TODO Items

**Generated**: 2025-11-18
**Total Items**: 18
**Status**: Catalogued for GitHub Issues

---

## Overview

This document catalogs all TODO, FIXME, and technical debt items found in the VulnZero codebase. Each item should be converted to a GitHub issue for tracking.

---

## 🔴 HIGH PRIORITY (Production Blockers)

### 1. Error Tracking - Sentry Integration
**File**: `web/src/components/ErrorBoundary.jsx:40`
**TODO**: Log to error reporting service (e.g., Sentry)
**Priority**: HIGH
**Effort**: 2-3 hours
**Description**: Implement Sentry error tracking in React error boundary
**GitHub Issue**:
```markdown
Title: Implement Sentry error tracking in ErrorBoundary
Labels: enhancement, frontend, monitoring
Priority: High

## Description
Add Sentry SDK integration to log errors caught by React ErrorBoundary component.

## Acceptance Criteria
- [ ] Install @sentry/react package
- [ ] Configure Sentry DSN from environment variables
- [ ] Send errors to Sentry in ErrorBoundary.componentDidCatch
- [ ] Include user context and breadcrumbs
- [ ] Test error reporting in staging environment

## Files to Modify
- web/src/components/ErrorBoundary.jsx
- web/.env.example (add REACT_APP_SENTRY_DSN)
```

---

## 🟠 MEDIUM PRIORITY (Feature Completion)

### 2. Database Connection Pool Initialization
**File**: `services/api-gateway/main.py:50`
**TODO**: Initialize database connection pool
**Priority**: MEDIUM
**Effort**: 1 hour
**Status**: ⚠️ May already be implemented in api/main.py
**Action**: Verify and remove outdated TODO or implement if missing

### 3. Redis Connection Pool Initialization
**File**: `services/api-gateway/main.py:51`
**TODO**: Initialize Redis connection pool
**Priority**: MEDIUM
**Effort**: 1 hour
**Status**: ⚠️ May already be implemented
**Action**: Verify and remove outdated TODO

### 4. Background Tasks Startup
**File**: `services/api-gateway/main.py:52`
**TODO**: Start background tasks
**Priority**: MEDIUM
**Effort**: 2-3 hours
**Description**: Initialize Celery tasks and scheduled jobs on app startup
**GitHub Issue**:
```markdown
Title: Initialize background tasks on application startup
Labels: enhancement, backend, celery
Priority: Medium

## Description
Start Celery beat scheduler and background tasks when FastAPI application starts.

## Tasks
- [ ] Initialize Celery beat scheduler
- [ ] Register periodic tasks (vulnerability scanning, etc.)
- [ ] Add health check for Celery workers
- [ ] Document background task configuration

## Files to Modify
- api/main.py (startup event)
- shared/celery_app.py
```

### 5. Graceful Shutdown - Database Connections
**File**: `services/api-gateway/main.py:58`
**TODO**: Close database connections
**Priority**: MEDIUM
**Effort**: 30 minutes
**Description**: Properly close database connections on app shutdown

### 6. Graceful Shutdown - Redis Connections
**File**: `services/api-gateway/main.py:59`
**TODO**: Close Redis connections
**Priority**: MEDIUM
**Effort**: 30 minutes
**Description**: Properly close Redis connections on app shutdown

### 7. Calculate Average Time to Remediate
**File**: `services/api-gateway/routes/vulnerabilities.py:112`
**TODO**: Calculate from deployment data
**Priority**: MEDIUM
**Effort**: 2-3 hours
**Description**: Implement calculation of average remediation time from vulnerability detection to deployment
**GitHub Issue**:
```markdown
Title: Calculate average time to remediate vulnerabilities
Labels: enhancement, backend, metrics
Priority: Medium

## Description
Calculate and expose average time from vulnerability detection to successful patch deployment.

## Implementation
- Query vulnerabilities with status='deployed'
- Calculate time difference: deployment.completed_at - vulnerability.created_at
- Return average across all vulnerabilities
- Add filtering by severity, time period

## Acceptance Criteria
- [ ] Add database query to calculate avg remediation time
- [ ] Expose in GET /api/vulnerabilities/stats
- [ ] Add unit tests
- [ ] Document metric in API docs

## Files to Modify
- services/api-gateway/routes/vulnerabilities.py
- tests/api/test_vulnerabilities.py
```

### 8. Trigger Celery Task for Vulnerability Scanning
**File**: `services/api-gateway/routes/vulnerabilities.py:208`
**TODO**: Trigger Celery task for scanning
**Priority**: MEDIUM
**Effort**: 2 hours
**Description**: Integrate with Celery to start async vulnerability scan

### 9. Return Actual Celery Task ID
**File**: `services/api-gateway/routes/vulnerabilities.py:214`
**TODO**: Return actual Celery task ID
**Priority**: MEDIUM
**Effort**: 30 minutes
**Description**: Return real Celery task ID instead of mock value

### 10. Count Vulnerabilities by Severity per Asset
**File**: `services/api-gateway/routes/assets.py:61`
**TODO**: Count by severity
**Priority**: MEDIUM
**Effort**: 1-2 hours
**Description**: Add vulnerability count breakdown by severity for each asset
**GitHub Issue**:
```markdown
Title: Add vulnerability severity breakdown to asset stats
Labels: enhancement, backend, api
Priority: Medium

## Description
Expose vulnerability count per severity level (critical, high, medium, low) for each asset.

## Acceptance Criteria
- [ ] Add severity counts to GET /api/assets/{id}/stats
- [ ] Return format: {"critical": 5, "high": 10, "medium": 15, "low": 20}
- [ ] Add database query optimization (avoid N+1)
- [ ] Add unit tests
- [ ] Update API documentation

## Files to Modify
- services/api-gateway/routes/assets.py
- tests/api/test_assets.py
```

### 11. Health Check - Redis Connection
**File**: `services/api-gateway/routes/system.py:35`
**TODO**: Check Redis
**Priority**: MEDIUM
**Effort**: 30 minutes
**Description**: Add Redis connectivity check to health endpoint

### 12. Health Check - Celery Workers
**File**: `services/api-gateway/routes/system.py:38`
**TODO**: Check Celery
**Priority**: MEDIUM
**Effort**: 1 hour
**Description**: Add Celery worker status check to health endpoint

### 13. System Stats - Average Remediation Time
**File**: `services/api-gateway/routes/system.py:92`
**TODO**: Calculate avg time to remediate
**Priority**: MEDIUM
**Effort**: 1 hour
**Description**: Duplicate of #7, calculate system-wide remediation time metric

### 14. Trigger Deployment Job
**File**: `services/api-gateway/routes/patches.py:106`
**TODO**: Trigger deployment job
**Priority**: MEDIUM
**Effort**: 2 hours
**Description**: Integrate with Celery to trigger async patch deployment

### 15. Trigger Rollback Job
**File**: `services/api-gateway/routes/deployments.py:127`
**TODO**: Trigger rollback job
**Priority**: MEDIUM
**Effort**: 2-3 hours
**Description**: Implement automated rollback via Celery task
**GitHub Issue**:
```markdown
Title: Implement automated patch rollback functionality
Labels: enhancement, backend, deployment
Priority: Medium

## Description
Add ability to automatically rollback failed deployments via Celery background task.

## Implementation
- Create Celery task: rollback_deployment(deployment_id)
- Execute rollback script on target asset
- Update deployment status to 'rolled_back'
- Log rollback operation in audit trail
- Send notification on rollback completion

## Acceptance Criteria
- [ ] Create rollback Celery task
- [ ] Integrate with deployment engine
- [ ] Add rollback endpoint: POST /api/deployments/{id}/rollback
- [ ] Add rollback status tracking
- [ ] Add unit and integration tests
- [ ] Update API documentation

## Files to Modify
- services/deployment_engine/rollback.py
- services/api-gateway/routes/deployments.py
- shared/celery_app.py
```

---

## 🟡 LOW PRIORITY (Future Enhancements)

### 16. User Authentication - Database Integration
**File**: `services/api-gateway/routes/auth.py:27`
**TODO**: Fetch user from database
**Priority**: LOW
**Effort**: 3-4 hours
**Description**: Currently uses mock users, integrate with real user database
**Note**: May already be implemented in api/routes/auth.py

### 17. JWT Token Validation - Database Check
**File**: `services/api-gateway/auth.py:135`
**TODO**: Fetch user from database
**Priority**: LOW
**Effort**: 2 hours
**Description**: Validate user exists in database when verifying JWT token

### 18. User Active Status Check
**File**: `services/api-gateway/auth.py:166`
**TODO**: Check if user is active in database
**Priority**: LOW
**Effort**: 1 hour
**Description**: Verify user account is active before allowing authentication

### 19. Exploit Database Integration
**File**: `services/aggregator/enrichment.py:222`
**TODO**: Implement actual exploit database checks
**Priority**: LOW
**Effort**: 4-6 hours
**Description**: Integrate with exploit databases (Exploit-DB, Metasploit, etc.)
**GitHub Issue**:
```markdown
Title: Integrate with exploit databases for enrichment
Labels: enhancement, backend, security
Priority: Low (Future)

## Description
Check if exploits exist for vulnerabilities by querying public exploit databases.

## Exploit Sources
- Exploit-DB (searchsploit API)
- Metasploit Framework
- Packet Storm Security
- GitHub Security Advisories

## Implementation
- [ ] Add exploit database API clients
- [ ] Query for CVE exploits during enrichment
- [ ] Cache exploit availability (24 hour TTL)
- [ ] Add exploit_available field to vulnerability model
- [ ] Update priority scoring based on exploit availability

## Files to Modify
- services/aggregator/enrichment.py
- shared/models/models.py (add exploit metadata)
```

---

## 📊 Summary by Priority

| Priority | Count | Estimated Effort |
|----------|-------|------------------|
| 🔴 High  | 1     | 2-3 hours        |
| 🟠 Medium| 14    | 20-25 hours      |
| 🟡 Low   | 4     | 11-17 hours      |
| **Total**| **19**| **33-45 hours**  |

---

## 📋 Action Items

### Immediate (This Week)
1. ✅ Implement Sentry error tracking
2. ✅ Add graceful shutdown handlers
3. ✅ Implement health checks (Redis, Celery)
4. ✅ Calculate average remediation time metric

### Short-term (Next 2 Weeks)
5. Integrate Celery task triggers for scanning
6. Implement deployment job triggering
7. Add vulnerability severity counts per asset
8. Implement rollback functionality

### Long-term (Future Sprints)
9. Real user database integration
10. Exploit database integration
11. Advanced analytics and metrics

---

## 🔄 Process

For each TODO item:
1. Create GitHub issue using templates above
2. Assign priority label
3. Assign to sprint/milestone
4. Implement and test
5. Remove TODO comment from code
6. Close issue with PR reference

---

## 📝 Notes

- Items marked "⚠️ May already be implemented" need verification
- Services in `services/api-gateway/` may be legacy code
- Check if functionality exists in `api/` directory before implementing
- Some TODOs may be obsolete due to recent refactoring

---

**Last Updated**: 2025-11-18
**Next Review**: Weekly during sprint planning
