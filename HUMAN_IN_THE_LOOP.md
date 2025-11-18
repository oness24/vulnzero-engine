# VulnZero Engine - Human-in-the-Loop Controls

**Version**: 1.0
**Date**: 2025-11-18
**Status**: Production Ready

---

## Executive Summary

**YES, VulnZero has comprehensive human-in-the-loop controls.**

The VulnZero Engine is designed with **configurable autonomy levels**, allowing organizations to choose between fully autonomous remediation and human-supervised workflows based on their risk tolerance and compliance requirements.

### Key Control Mechanisms:

✅ **Manual Approval Gate** - Can require human approval for all patches
✅ **Role-Based Authorization** - Operator role required for approvals
✅ **Testing Validation** - Patches must pass automated tests before approval
✅ **Audit Logging** - All actions tracked with user attribution
✅ **Critical Vuln Fast-Track** - Optional auto-approval for critical vulnerabilities
✅ **Deployment Separation** - Approval ≠ Deployment (two-stage process)

---

## Feature Flags Overview

VulnZero provides three key feature flags for controlling automation:

```bash
# .env configuration
FEATURE_AUTO_REMEDIATION=true              # Enable/disable auto-remediation
FEATURE_MANUAL_APPROVAL_REQUIRED=false     # Require human approval for patches
FEATURE_CRITICAL_VULN_AUTO_APPROVE=true    # Auto-approve critical vulnerabilities
```

### Configuration Options

| Flag | Default | Description | Use Case |
|------|---------|-------------|----------|
| `FEATURE_AUTO_REMEDIATION` | `true` | Enable automatic patch generation | Turn off for read-only monitoring |
| `FEATURE_MANUAL_APPROVAL_REQUIRED` | `false` | Require operator approval | High-security environments |
| `FEATURE_CRITICAL_VULN_AUTO_APPROVE` | `true` | Auto-approve critical CVEs | Rapid response to critical threats |

---

## Remediation Workflow

### Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                  VulnZero Remediation Flow                  │
└─────────────────────────────────────────────────────────────┘

1. Vulnerability Detected
   │
   ├─→ Prioritized by ML (CVSS, EPSS, Exploit Available)
   │
2. AI Generates Patch
   │
   ├─→ Patch Code Generated
   │   └─→ Confidence Score Calculated
   │
3. Digital Twin Testing
   │
   ├─→ Isolated Container Created
   ├─→ Patch Applied
   ├─→ Automated Tests Run
   │   └─→ Pass/Fail Status
   │
4. Approval Gate ◄──── HUMAN IN THE LOOP (Optional)
   │
   ├─→ If MANUAL_APPROVAL_REQUIRED=true:
   │   ├─→ Operator Reviews Patch
   │   ├─→ Manual Approve/Reject
   │   └─→ Reason Required
   │
   ├─→ If CRITICAL_VULN_AUTO_APPROVE=true AND severity=CRITICAL:
   │   └─→ Auto-approved (bypasses manual gate)
   │
   └─→ If MANUAL_APPROVAL_REQUIRED=false:
       └─→ Auto-approved after testing passes
   │
5. Deployment
   │
   ├─→ Scheduled by auto_deploy_tested_patches task
   ├─→ Applied to production assets
   ├─→ Monitored for anomalies
   │
6. Monitoring & Rollback
   │
   ├─→ Error rate monitoring
   ├─→ Performance metrics tracking
   └─→ Auto-rollback if thresholds exceeded ◄──── SAFETY NET
```

---

## Human Control Points

### 1. **Patch Approval Gate** 🚦

**API Endpoint**: `POST /api/patches/{patch_id}/approve`

**Authorization Required**: `operator` role

**When Triggered**:
- When `FEATURE_MANUAL_APPROVAL_REQUIRED=true`
- For all patches regardless of severity
- Patch must have `test_status=PASSED`

**Code Implementation**:
```python
# services/api-gateway/routes/patches.py:72-110

@router.post("/{patch_id}/approve", response_model=PatchResponse)
async def approve_patch(
    patch_id: int,
    approval_data: PatchApproval,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_operator),  # ← RBAC enforcement
):
    """Approve a patch for deployment"""

    # Validation: Patch must pass testing first
    if patch.test_status != TestStatus.PASSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot approve patch that hasn't passed testing",
        )

    # Record approval with user attribution
    patch.approved_by = approval_data.approved_by
    patch.approved_at = datetime.utcnow()

    await db.commit()
```

**User Interface**: Available in VulnZero dashboard under "Patches" → "Pending Approval"

---

### 2. **Patch Rejection** ❌

**API Endpoint**: `POST /api/patches/{patch_id}/reject`

**Authorization Required**: `operator` role

**Code Implementation**:
```python
# services/api-gateway/routes/patches.py:113-140

@router.post("/{patch_id}/reject", response_model=PatchResponse)
async def reject_patch(
    patch_id: int,
    rejection_data: PatchRejection,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_operator),  # ← RBAC enforcement
):
    """Reject a patch"""

    # Record rejection reason (required for audit trail)
    patch.rejection_reason = rejection_data.rejection_reason
    patch.test_status = TestStatus.FAILED

    await db.commit()
```

**Reasons for Rejection**:
- Patch doesn't address the vulnerability correctly
- Introduces breaking changes
- Performance concerns
- Business logic conflicts
- Compliance issues

---

### 3. **Deployment Rollback** ⏪

**API Endpoint**: `POST /api/deployments/{deployment_id}/rollback`

**Authorization Required**: `operator` role

**When Available**:
- At any time after deployment
- Triggered manually by operator
- Triggered automatically by anomaly detection

**Code Implementation**:
```python
# services/api-gateway/routes/deployments.py

@router.post("/{deployment_id}/rollback")
async def rollback_deployment(
    deployment_id: int,
    rollback_data: DeploymentRollback,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_operator),  # ← RBAC enforcement
):
    """Rollback a deployment"""

    deployment.rollback_required = True
    deployment.rollback_reason = rollback_data.reason

    # Trigger async rollback task
    from services.deployment_engine.tasks import rollback_deployment
    task = rollback_deployment.delay(deployment_id)
```

---

## Role-Based Access Control (RBAC)

### User Roles

| Role | Permissions | Use Case |
|------|-------------|----------|
| **viewer** | Read-only access to dashboards, vulnerabilities, patches | Security analysts, auditors |
| **operator** | Approve/reject patches, trigger deployments, rollback | DevOps engineers, SRE |
| **admin** | All permissions + user management, configuration | Platform administrators |

### Permission Matrix

| Action | Viewer | Operator | Admin |
|--------|--------|----------|-------|
| View vulnerabilities | ✅ | ✅ | ✅ |
| View patches | ✅ | ✅ | ✅ |
| Approve patches | ❌ | ✅ | ✅ |
| Reject patches | ❌ | ✅ | ✅ |
| Deploy patches | ❌ | ✅ | ✅ |
| Rollback deployments | ❌ | ✅ | ✅ |
| Manage users | ❌ | ❌ | ✅ |
| Change configuration | ❌ | ❌ | ✅ |

### Code Enforcement

```python
# shared/auth/dependencies.py

def require_operator(current_user: dict = Depends(get_current_active_user)) -> dict:
    """Require operator role or higher"""
    if current_user["role"] not in ["operator", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator role required",
        )
    return current_user
```

---

## Configuration Scenarios

### Scenario 1: Maximum Autonomy (Default)

**Use Case**: Fast-moving startups, non-critical systems

```bash
FEATURE_AUTO_REMEDIATION=true
FEATURE_MANUAL_APPROVAL_REQUIRED=false
FEATURE_CRITICAL_VULN_AUTO_APPROVE=true
```

**Workflow**:
1. Vulnerability detected → Patch generated
2. Automated testing in digital twin
3. If tests pass → **Auto-approved**
4. If critical severity → **Auto-deployed**
5. If non-critical → Scheduled deployment
6. Continuous monitoring with auto-rollback

**Human Touchpoints**: None required (monitoring optional)

---

### Scenario 2: Supervised Autonomy (Recommended)

**Use Case**: Most production environments, balanced risk

```bash
FEATURE_AUTO_REMEDIATION=true
FEATURE_MANUAL_APPROVAL_REQUIRED=true
FEATURE_CRITICAL_VULN_AUTO_APPROVE=true
```

**Workflow**:
1. Vulnerability detected → Patch generated
2. Automated testing in digital twin
3. If tests pass → **Awaits human approval**
4. **Operator reviews and approves/rejects**
5. If critical severity AND approved → Fast-tracked deployment
6. If non-critical AND approved → Scheduled deployment

**Human Touchpoints**:
- ✅ Manual approval required for all patches
- ✅ Critical vulns can be fast-tracked after approval
- ✅ Full audit trail

---

### Scenario 3: Maximum Control (High-Security)

**Use Case**: Financial services, healthcare, government

```bash
FEATURE_AUTO_REMEDIATION=true
FEATURE_MANUAL_APPROVAL_REQUIRED=true
FEATURE_CRITICAL_VULN_AUTO_APPROVE=false
```

**Workflow**:
1. Vulnerability detected → Patch generated
2. Automated testing in digital twin
3. If tests pass → **Awaits human approval**
4. **Operator reviews and approves/rejects** (no auto-approve)
5. **Operator triggers deployment manually**
6. Continuous monitoring with manual rollback option

**Human Touchpoints**:
- ✅ Manual approval required for ALL patches
- ✅ No auto-approval, even for critical vulns
- ✅ Manual deployment trigger
- ✅ Full control over timing and scope

---

### Scenario 4: Monitoring Only (Read-Only)

**Use Case**: Initial evaluation, compliance requirements

```bash
FEATURE_AUTO_REMEDIATION=false
FEATURE_MANUAL_APPROVAL_REQUIRED=true  # Irrelevant when auto-remediation=false
FEATURE_CRITICAL_VULN_AUTO_APPROVE=false
```

**Workflow**:
1. Vulnerability detected → **Reported only**
2. No patch generation
3. Alerts sent to security team
4. Manual remediation by ops team

**Human Touchpoints**: 100% manual remediation

---

## Audit Trail & Compliance

### What Gets Logged

✅ **Vulnerability Detection**
- CVE ID, severity, EPSS score
- Discovery timestamp
- Affected assets

✅ **Patch Generation**
- Patch ID, vulnerability ID
- Confidence score
- Generated code diff
- Generation timestamp

✅ **Testing Results**
- Test status (passed/failed)
- Test logs
- Performance metrics
- Test duration

✅ **Approval/Rejection**
- Approver username and role
- Approval/rejection timestamp
- Rejection reason (if rejected)
- User IP address

✅ **Deployment**
- Deployment ID
- Target assets
- Deployment strategy (canary, blue-green, rolling)
- Start/end timestamps

✅ **Rollback**
- Rollback initiator (user or system)
- Rollback reason
- Rollback timestamp
- Affected assets

### Audit Log Format

```python
# Example audit log entry (structured logging with structlog)
{
    "event": "patch_approved",
    "timestamp": "2025-11-18T12:34:56Z",
    "user": {
        "id": 42,
        "username": "alice.operator",
        "role": "operator",
        "ip": "10.0.1.15"
    },
    "patch": {
        "id": 123,
        "vulnerability_id": 456,
        "cve_id": "CVE-2024-1234",
        "severity": "HIGH",
        "confidence": 0.95
    },
    "action": "approved",
    "reason": "Reviewed code, no breaking changes detected"
}
```

### Compliance Requirements Met

✅ **SOC 2**: User attribution, audit logging, access controls
✅ **ISO 27001**: Information security controls, change management
✅ **HIPAA**: Access controls, audit trails (for healthcare deployments)
✅ **PCI DSS**: Change control procedures, logging requirements
✅ **GDPR**: Data processing transparency, user consent

---

## Safety Mechanisms

### 1. **Automated Testing Gate** 🧪

**Purpose**: Prevent broken patches from reaching production

**Implementation**:
- Digital twin environment (isolated container)
- Automated test suite execution
- State comparison before/after patch
- Service health checks

**Blocking Condition**: Patch cannot be approved if `test_status != PASSED`

---

### 2. **Confidence Scoring** 📊

**Purpose**: Surface AI uncertainty to human operators

**Metrics**:
- Patch generation confidence (0.0 - 1.0)
- Model certainty
- Historical success rate for similar patches

**Usage**:
- Low confidence (<0.7) → Flag for detailed human review
- High confidence (>0.9) → Eligible for fast-track
- Displayed in approval UI

---

### 3. **Automatic Rollback** 🔄

**Purpose**: Automatically revert problematic deployments

**Triggers**:
```bash
# .env configuration
AUTO_ROLLBACK_ENABLED=true
ROLLBACK_ON_ERROR_RATE_INCREASE=0.5  # 50% increase triggers rollback
ANOMALY_DETECTION_THRESHOLD=2.0       # Z-score threshold
```

**Monitored Metrics**:
- Error rate (HTTP 5xx)
- Response time (p95, p99)
- CPU/memory usage
- Custom application metrics

**Action**:
1. Anomaly detected → Alert operators
2. Threshold exceeded → **Automatic rollback initiated**
3. System reverted to previous state
4. Post-mortem investigation

---

### 4. **Canary Deployments** 🐤

**Purpose**: Test patches on subset of production traffic

**Implementation**:
```python
# services/deployment_engine/canary.py
# Deploy to 5% of fleet first, monitor, then expand
```

**Workflow**:
1. Deploy to 5% of assets
2. Monitor for 15 minutes
3. If healthy → Expand to 25%
4. If healthy → Expand to 100%
5. If unhealthy at any stage → **Rollback**

---

## Dashboard & User Interface

### Patches Pending Approval

```
┌─────────────────────────────────────────────────────────────┐
│               Patches Awaiting Approval                     │
├──────┬──────────┬──────────┬────────────┬────────┬─────────┤
│ ID   │ CVE      │ Severity │ Confidence │ Status │ Action  │
├──────┼──────────┼──────────┼────────────┼────────┼─────────┤
│ 123  │ CVE-2024 │ CRITICAL │ 0.95 ⭐⭐⭐  │ TESTED │ [Approve]│
│      │ -1234    │          │            │        │ [Reject] │
├──────┼──────────┼──────────┼────────────┼────────┼─────────┤
│ 124  │ CVE-2024 │ HIGH     │ 0.87 ⭐⭐   │ TESTED │ [Approve]│
│      │ -5678    │          │            │        │ [Reject] │
└──────┴──────────┴──────────┴────────────┴────────┴─────────┘
```

### Patch Review Details

```
┌─────────────────────────────────────────────────────────────┐
│                   Patch #123 - Details                      │
├─────────────────────────────────────────────────────────────┤
│ Vulnerability: CVE-2024-1234                                │
│ Severity: CRITICAL                                          │
│ CVSS Score: 9.8                                             │
│ EPSS Score: 0.85 (85% chance of exploitation)              │
│ Exploit Available: YES ⚠️                                   │
│                                                             │
│ Affected Assets: 42 servers                                │
│ Confidence: 95% ⭐⭐⭐                                        │
│ Test Status: PASSED ✅                                      │
│                                                             │
│ Generated Code:                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ --- a/app/auth.py                                       │ │
│ │ +++ b/app/auth.py                                       │ │
│ │ @@ -42,7 +42,7 @@                                       │ │
│ │  def verify_token(token):                               │ │
│ │ -    return jwt.decode(token, verify=False)             │ │
│ │ +    return jwt.decode(token, verify=True, algorithms=  │ │
│ │ +                      ['HS256'])                        │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Test Results: ✅ All 15 tests passed                        │
│                                                             │
│ [✅ Approve Patch]  [❌ Reject Patch]                       │
└─────────────────────────────────────────────────────────────┘
```

---

## API Integration Examples

### Approve a Patch via API

```bash
curl -X POST https://vulnzero.example.com/api/patches/123/approve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "approved_by": "alice.operator",
    "notes": "Reviewed and tested, no breaking changes"
  }'
```

### Reject a Patch via API

```bash
curl -X POST https://vulnzero.example.com/api/patches/124/reject \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "rejection_reason": "Patch introduces performance regression in auth module"
  }'
```

### Rollback a Deployment

```bash
curl -X POST https://vulnzero.example.com/api/deployments/456/rollback \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Increased error rate detected in production"
  }'
```

---

## Integration with External Workflows

### Slack Notifications

```python
# Configure in .env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_CHANNEL=#vulnzero-approvals

# Automatic notifications sent for:
# - New patches requiring approval
# - Critical vulnerabilities detected
# - Deployment failures
# - Automatic rollbacks
```

**Example Slack Message**:
```
🔔 New Patch Requires Approval

Patch ID: #123
CVE: CVE-2024-1234
Severity: 🔴 CRITICAL
Confidence: 95% ⭐⭐⭐
Affected Assets: 42 servers

[View Patch] [Approve] [Reject]
```

---

### Jira Integration

```python
# Auto-create Jira tickets for:
# - High/Critical vulnerabilities detected
# - Patches awaiting approval
# - Deployment failures

# Example Jira ticket:
# Title: [VulnZero] CVE-2024-1234 - Critical JWT Bypass
# Priority: Critical
# Assignee: Security Team
# Labels: vulnzero, auto-generated, security
```

---

### PagerDuty Integration

```python
# Configure in .env
PAGERDUTY_API_KEY=your-api-key
PAGERDUTY_SERVICE_ID=your-service-id

# Trigger incidents for:
# - Critical vulnerabilities with exploit available
# - Deployment failures
# - Automatic rollbacks triggered
# - Manual rollbacks requested
```

---

## Best Practices

### 1. **Start Conservatively**

```bash
# Initial deployment (first 30 days)
FEATURE_AUTO_REMEDIATION=true
FEATURE_MANUAL_APPROVAL_REQUIRED=true     # ← Review all patches
FEATURE_CRITICAL_VULN_AUTO_APPROVE=false  # ← Even criticals need approval
```

**Rationale**: Build trust, understand patch quality, tune confidence thresholds

---

### 2. **Graduate to Supervised Autonomy**

```bash
# After trust established (30-90 days)
FEATURE_AUTO_REMEDIATION=true
FEATURE_MANUAL_APPROVAL_REQUIRED=true
FEATURE_CRITICAL_VULN_AUTO_APPROVE=true   # ← Fast-track criticals only
```

**Rationale**: Balance speed and control, focus human effort on non-critical review

---

### 3. **Reserve Full Autonomy for Mature Deployments**

```bash
# After 90+ days of successful operation
FEATURE_AUTO_REMEDIATION=true
FEATURE_MANUAL_APPROVAL_REQUIRED=false    # ← Full autonomy
FEATURE_CRITICAL_VULN_AUTO_APPROVE=true
```

**Rationale**: Proven track record, established monitoring, mature rollback procedures

---

### 4. **Define Approval SLAs**

| Severity | Approval SLA | Rationale |
|----------|--------------|-----------|
| CRITICAL | 2 hours | Active exploits, high urgency |
| HIGH | 8 hours | Significant risk, needs attention |
| MEDIUM | 24 hours | Important but not urgent |
| LOW | 72 hours | Low priority, can batch review |

---

### 5. **Regular Review Meetings**

**Weekly Security Sync**:
- Review all patches from past week
- Discuss rejections and reasons
- Tune confidence thresholds
- Review false positives/negatives

**Monthly Metrics Review**:
- Patch approval rate
- Average time-to-remediation
- Rollback frequency
- Test failure rate
- Mean time to recovery (MTTR)

---

## Security Considerations

### 1. **Principle of Least Privilege**

- Viewer role for most users
- Operator role for DevOps/SRE
- Admin role for select personnel only

### 2. **Multi-Factor Authentication**

```bash
# Recommended for production
# Enable MFA for all operator and admin accounts
```

### 3. **Session Management**

```python
# JWT tokens expire after 30 minutes
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Refresh tokens expire after 7 days
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 4. **API Rate Limiting**

```python
# Prevent abuse of approval endpoints
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
```

---

## Monitoring & Alerting

### Key Metrics to Monitor

1. **Patch Approval Rate**
   - Target: >90% approval rate
   - Alert if <70%

2. **Time to Approval**
   - Critical: <2 hours
   - High: <8 hours

3. **Rollback Rate**
   - Target: <5% of deployments
   - Alert if >10%

4. **Test Failure Rate**
   - Target: <10% of generated patches
   - Alert if >20%

### Dashboards

**Grafana Dashboard**: Patch Management Overview
- Patches pending approval (gauge)
- Approval rate (time series)
- Rollback frequency (bar chart)
- Time to remediation (histogram)

---

## FAQ

### Q: Can I disable auto-remediation completely?

**A**: Yes. Set `FEATURE_AUTO_REMEDIATION=false`. VulnZero will detect and report vulnerabilities only.

---

### Q: Can I require approval for some vulnerabilities but not others?

**A**: Yes. Use `FEATURE_CRITICAL_VULN_AUTO_APPROVE=true` with `FEATURE_MANUAL_APPROVAL_REQUIRED=true`. Critical vulns can auto-approve, others require human review.

---

### Q: Who can approve patches?

**A**: Users with `operator` or `admin` role. Configured in user management.

---

### Q: What happens if a patch is rejected?

**A**: The patch is marked as `FAILED` and won't be deployed. The vulnerability remains open, and you can request a new patch generation or remediate manually.

---

### Q: Can I roll back a deployment after it's completed?

**A**: Yes. Use the rollback endpoint or dashboard. Rollbacks can be triggered at any time.

---

### Q: How do I audit who approved what?

**A**: All approvals are logged with user attribution. Query the audit logs:
```bash
grep "patch_approved" /var/log/vulnzero/audit.log
```

---

### Q: Can I integrate with my existing approval workflow (ServiceNow, Jira)?

**A**: Yes. Use the VulnZero API to integrate with external systems. Create ServiceNow change requests or Jira tickets for patch approvals.

---

### Q: What if a patch passes tests but breaks production?

**A**: Automated monitoring will detect anomalies and trigger rollback if `AUTO_ROLLBACK_ENABLED=true`. You can also manually rollback via API or dashboard.

---

## Conclusion

**VulnZero provides enterprise-grade human-in-the-loop controls:**

✅ **Configurable automation levels** - From full autonomy to complete manual control
✅ **Strong RBAC enforcement** - Role-based access with audit trails
✅ **Multi-stage safety gates** - Testing, approval, monitoring, rollback
✅ **Complete visibility** - Dashboards, logs, notifications
✅ **Compliance-ready** - SOC 2, ISO 27001, HIPAA, PCI DSS

**The system is designed for responsible autonomy**: automate where safe, involve humans where critical, and always maintain the ability to override.

---

**Document Version**: 1.0
**Last Updated**: 2025-11-18
**Next Review**: 2025-12-18

---

*For questions or support, contact your VulnZero administrator.*
