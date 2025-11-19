# Operator Guide: Task Status Tracking

**Version**: 1.0
**Last Updated**: 2025-11-19
**Audience**: Operations Team, DevOps, Support Engineers

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Task Status Endpoints](#task-status-endpoints)
4. [Common Workflows](#common-workflows)
5. [Monitoring & Troubleshooting](#monitoring--troubleshooting)
6. [Best Practices](#best-practices)
7. [FAQ](#faq)
8. [Reference](#reference)

---

## Overview

### What is Task Tracking?

VulnZero performs long-running operations (deployments, vulnerability scans) asynchronously using **Celery**. When you trigger these operations via the API, you receive a **task ID** that you can use to track progress and retrieve results.

### Why is This Important?

Before task tracking, operators had no way to:
- ✗ Check if a deployment completed
- ✗ Monitor scan progress
- ✗ Retrieve operation results
- ✗ Cancel stuck tasks
- ✗ Debug failed operations

With task tracking, you can:
- ✅ Check task status in real-time
- ✅ Monitor long-running operations
- ✅ Retrieve results when complete
- ✅ Cancel tasks if needed
- ✅ Debug failures with detailed error info

### Supported Operations

| Operation | Endpoint | Typical Duration | Task ID Location |
|-----------|----------|------------------|------------------|
| **Deploy Patch** | `POST /api/v1/deployments` | 5-30 minutes | `response.task_id` |
| **Vulnerability Scan** | `POST /api/v1/vulnerabilities/scan` | 10-60 minutes | `response.task_id` |
| **Patch Generation** | `POST /api/v1/patches/generate` | 2-10 minutes | `response.task_id` |

---

## Getting Started

### Prerequisites

1. **API Access**: You need valid API credentials
2. **Authentication Token**: JWT token from `/api/v1/auth/login`
3. **curl or API Client**: Examples use curl, but any HTTP client works

### Quick Start

```bash
# 1. Authenticate
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"operator@example.com","password":"YourPassword"}' \
  | jq -r '.access_token')

# 2. Trigger a deployment (returns task ID)
TASK_ID=$(curl -X POST http://localhost:8000/api/v1/deployments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patch_id": 123,
    "asset_ids": [456],
    "strategy": "canary"
  }' | jq -r '.task_id')

echo "Task ID: $TASK_ID"

# 3. Check task status
curl http://localhost:8000/api/v1/tasks/$TASK_ID \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## Task Status Endpoints

### 1. Get Task Status

**Endpoint**: `GET /api/v1/tasks/{task_id}`

Retrieve the current status and result of a task.

#### Request

```bash
curl http://localhost:8000/api/v1/tasks/{task_id} \
  -H "Authorization: Bearer $TOKEN"
```

#### Response (Task Pending)

```json
{
  "task_id": "abc-123-def-456",
  "state": "PENDING",
  "ready": false,
  "successful": null,
  "info": null
}
```

#### Response (Task Running)

```json
{
  "task_id": "abc-123-def-456",
  "state": "STARTED",
  "ready": false,
  "successful": null,
  "info": {
    "current": 3,
    "total": 10,
    "status": "Deploying to asset-prod-web-03"
  },
  "progress": {
    "percent": 30,
    "message": "Deploying to 3 of 10 assets"
  }
}
```

#### Response (Task Success)

```json
{
  "task_id": "abc-123-def-456",
  "state": "SUCCESS",
  "ready": true,
  "successful": true,
  "result": {
    "deployment_id": 789,
    "status": "deployed",
    "deployed_assets": [456, 457, 458],
    "deployment_time": "2025-11-19T10:30:00Z"
  },
  "completed_at": "2025-11-19T10:30:45Z"
}
```

#### Response (Task Failed)

```json
{
  "task_id": "abc-123-def-456",
  "state": "FAILURE",
  "ready": true,
  "successful": false,
  "error": "Failed to connect to asset: Connection timeout",
  "traceback": "Traceback (most recent call last):\n  File ...",
  "failed_at": "2025-11-19T10:25:30Z"
}
```

#### Task States

| State | Description | Next Action |
|-------|-------------|-------------|
| `PENDING` | Task queued, not started yet | Wait or check worker status |
| `STARTED` | Task is executing | Monitor progress |
| `SUCCESS` | Task completed successfully | Retrieve results |
| `FAILURE` | Task failed with error | Review error message |
| `RETRY` | Task failed, retrying | Wait for retry |
| `REVOKED` | Task was cancelled | No action needed |

---

### 2. Cancel Task

**Endpoint**: `DELETE /api/v1/tasks/{task_id}`

Cancel a running task (use with caution!).

#### Request

```bash
# Graceful cancellation
curl -X DELETE http://localhost:8000/api/v1/tasks/{task_id} \
  -H "Authorization: Bearer $TOKEN"

# Forced termination (if graceful fails)
curl -X DELETE "http://localhost:8000/api/v1/tasks/{task_id}?terminate=true" \
  -H "Authorization: Bearer $TOKEN"
```

#### Response (Success)

```json
{
  "task_id": "abc-123-def-456",
  "cancelled": true,
  "terminated": false,
  "message": "Task cancellation requested"
}
```

#### Response (Already Complete)

```json
{
  "task_id": "abc-123-def-456",
  "cancelled": false,
  "message": "Task already completed with state: SUCCESS"
}
```

#### When to Cancel Tasks

✅ **Safe to Cancel**:
- Scan tasks that are taking too long
- Deployments stuck in monitoring phase
- Tasks triggered by mistake

⚠️ **Use Caution**:
- Deployments in progress (may leave systems in inconsistent state)
- Tasks that have already modified infrastructure

❌ **Do Not Cancel**:
- Rollback operations (let them complete)
- Tasks that are cleaning up resources

---

### 3. List Recent Tasks

**Endpoint**: `GET /api/v1/tasks`

View all active, scheduled, and reserved tasks across all workers.

#### Request

```bash
curl "http://localhost:8000/api/v1/tasks?limit=20" \
  -H "Authorization: Bearer $TOKEN"
```

#### Response

```json
{
  "tasks": [
    {
      "task_id": "abc-123",
      "name": "services.deployment_orchestrator.tasks.deploy_patch",
      "state": "ACTIVE",
      "worker": "celery@worker1",
      "started_at": "2025-11-19T10:20:00Z"
    },
    {
      "task_id": "def-456",
      "name": "services.vulnerability_scanner.tasks.scan_asset",
      "state": "SCHEDULED",
      "worker": "celery@worker2",
      "eta": "2025-11-19T11:00:00Z"
    }
  ],
  "count": 2,
  "limit": 20
}
```

#### Use Cases

- **Dashboard**: Display all active operations
- **Debugging**: Find stuck or long-running tasks
- **Monitoring**: Track system workload
- **Planning**: See queued operations

---

## Common Workflows

### Workflow 1: Deploy Patch and Monitor

```bash
#!/bin/bash
# Complete deployment workflow with monitoring

TOKEN="your_jwt_token"
BASE_URL="http://localhost:8000"

# Step 1: Trigger deployment
echo "🚀 Triggering deployment..."
RESPONSE=$(curl -X POST "$BASE_URL/api/v1/deployments" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patch_id": 123,
    "asset_ids": [456, 457, 458],
    "strategy": "canary",
    "parameters": {
      "canary_percentage": 10,
      "monitoring_duration_seconds": 300
    }
  }')

TASK_ID=$(echo $RESPONSE | jq -r '.task_id')
echo "✅ Deployment started: Task ID = $TASK_ID"

# Step 2: Poll for completion
echo "⏳ Monitoring deployment progress..."
while true; do
  STATUS=$(curl -s "$BASE_URL/api/v1/tasks/$TASK_ID" \
    -H "Authorization: Bearer $TOKEN")

  STATE=$(echo $STATUS | jq -r '.state')
  READY=$(echo $STATUS | jq -r '.ready')

  echo "   Status: $STATE"

  # Check if complete
  if [ "$READY" = "true" ]; then
    SUCCESSFUL=$(echo $STATUS | jq -r '.successful')

    if [ "$SUCCESSFUL" = "true" ]; then
      echo "✅ Deployment completed successfully!"
      echo $STATUS | jq '.result'
      exit 0
    else
      echo "❌ Deployment failed!"
      echo $STATUS | jq '.error'
      exit 1
    fi
  fi

  # Show progress if available
  PROGRESS=$(echo $STATUS | jq -r '.progress.message // empty')
  if [ -n "$PROGRESS" ]; then
    echo "   Progress: $PROGRESS"
  fi

  # Wait before next check
  sleep 10
done
```

---

### Workflow 2: Trigger Scan and Wait

```bash
#!/bin/bash
# Scan workflow with automatic result retrieval

TOKEN="your_jwt_token"
BASE_URL="http://localhost:8000"

# Trigger scan
echo "🔍 Starting vulnerability scan..."
RESPONSE=$(curl -X POST "$BASE_URL/api/v1/vulnerabilities/scan" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_ids": [456],
    "scanner": "wazuh",
    "scan_type": "full"
  }')

TASK_ID=$(echo $RESPONSE | jq -r '.task_id')
echo "✅ Scan started: Task ID = $TASK_ID"

# Wait for completion (timeout after 1 hour)
echo "⏳ Waiting for scan to complete (max 1 hour)..."
TIMEOUT=3600
ELAPSED=0

while [ $ELAPSED -lt $TIMEOUT ]; do
  STATUS=$(curl -s "$BASE_URL/api/v1/tasks/$TASK_ID" \
    -H "Authorization: Bearer $TOKEN")

  READY=$(echo $STATUS | jq -r '.ready')

  if [ "$READY" = "true" ]; then
    SUCCESSFUL=$(echo $STATUS | jq -r '.successful')

    if [ "$SUCCESSFUL" = "true" ]; then
      echo "✅ Scan completed!"

      # Retrieve vulnerabilities
      echo "📊 Fetching scan results..."
      VULNS=$(curl -s "$BASE_URL/api/v1/vulnerabilities?asset_id=456&limit=100" \
        -H "Authorization: Bearer $TOKEN")

      CRITICAL=$(echo $VULNS | jq '[.[] | select(.severity=="CRITICAL")] | length')
      HIGH=$(echo $VULNS | jq '[.[] | select(.severity=="HIGH")] | length')
      MEDIUM=$(echo $VULNS | jq '[.[] | select(.severity=="MEDIUM")] | length')

      echo "   🔴 Critical: $CRITICAL"
      echo "   🟠 High: $HIGH"
      echo "   🟡 Medium: $MEDIUM"

      exit 0
    else
      echo "❌ Scan failed!"
      echo $STATUS | jq '.error'
      exit 1
    fi
  fi

  sleep 15
  ELAPSED=$((ELAPSED + 15))
  echo "   Elapsed: ${ELAPSED}s / ${TIMEOUT}s"
done

echo "⏰ Scan timeout after 1 hour"
exit 2
```

---

### Workflow 3: Cancel Stuck Task

```bash
#!/bin/bash
# Emergency task cancellation

TOKEN="your_jwt_token"
BASE_URL="http://localhost:8000"
TASK_ID="abc-123-def-456"

# Check current status
echo "🔍 Checking task status..."
STATUS=$(curl -s "$BASE_URL/api/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN")

STATE=$(echo $STATUS | jq -r '.state')
READY=$(echo $STATUS | jq -r '.ready')

echo "   Current state: $STATE"
echo "   Ready: $READY"

if [ "$READY" = "true" ]; then
  echo "⚠️  Task is already complete, no need to cancel"
  exit 0
fi

# Confirm cancellation
read -p "⚠️  Cancel task $TASK_ID? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Cancellation aborted"
  exit 0
fi

# Attempt graceful cancellation
echo "🛑 Requesting graceful cancellation..."
CANCEL_RESPONSE=$(curl -s -X DELETE "$BASE_URL/api/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN")

CANCELLED=$(echo $CANCEL_RESPONSE | jq -r '.cancelled')

if [ "$CANCELLED" = "true" ]; then
  echo "✅ Task cancelled successfully"
  exit 0
else
  echo "⚠️  Graceful cancellation failed"

  # Try forced termination
  read -p "❗ Force terminate? (y/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "💥 Forcing task termination..."
    curl -s -X DELETE "$BASE_URL/api/v1/tasks/$TASK_ID?terminate=true" \
      -H "Authorization: Bearer $TOKEN" | jq
    echo "⚠️  Task forcefully terminated - check for side effects"
  fi
fi
```

---

## Monitoring & Troubleshooting

### Dashboard Integration

Create a simple monitoring dashboard:

```bash
#!/bin/bash
# Simple task monitoring dashboard

TOKEN="your_jwt_token"
BASE_URL="http://localhost:8000"

while true; do
  clear
  echo "╔═══════════════════════════════════════════════════════════╗"
  echo "║         VulnZero Task Monitoring Dashboard               ║"
  echo "╚═══════════════════════════════════════════════════════════╝"
  echo ""
  echo "⏰ Last updated: $(date)"
  echo ""

  # Get all active tasks
  TASKS=$(curl -s "$BASE_URL/api/v1/tasks?limit=50" \
    -H "Authorization: Bearer $TOKEN")

  ACTIVE=$(echo $TASKS | jq '[.tasks[] | select(.state=="ACTIVE")] | length')
  SCHEDULED=$(echo $TASKS | jq '[.tasks[] | select(.state=="SCHEDULED")] | length')
  RESERVED=$(echo $TASKS | jq '[.tasks[] | select(.state=="RESERVED")] | length')

  echo "📊 Task Summary:"
  echo "   ▶️  Active:    $ACTIVE"
  echo "   ⏰ Scheduled: $SCHEDULED"
  echo "   📋 Reserved:  $RESERVED"
  echo ""

  # Show active tasks
  if [ "$ACTIVE" -gt 0 ]; then
    echo "🔄 Active Tasks:"
    echo $TASKS | jq -r '.tasks[] | select(.state=="ACTIVE") | "   • \(.task_id | .[0:12])... - \(.name | split(".") | .[-1]) - \(.worker)"'
  fi

  echo ""
  echo "Press Ctrl+C to exit"

  # Refresh every 10 seconds
  sleep 10
done
```

---

### Common Issues

#### Issue 1: Task Stuck in PENDING

**Symptoms**:
- Task status remains `PENDING` for extended period
- No progress updates

**Causes**:
- Celery workers not running
- Worker overloaded
- Task routing misconfiguration

**Troubleshooting**:

```bash
# Check if Celery workers are running
docker ps | grep celery

# Check worker logs
docker logs celery-worker-1

# Inspect Celery queues
celery -A services.deployment_orchestrator.celery inspect active_queues

# Check queue length
celery -A services.deployment_orchestrator.celery inspect stats
```

**Resolution**:
1. Start Celery workers: `docker-compose up -d celery-worker`
2. Increase worker concurrency: `CELERY_WORKER_CONCURRENCY=8`
3. Add more workers: `docker-compose scale celery-worker=3`

---

#### Issue 2: Task Fails Immediately

**Symptoms**:
- Task transitions to `FAILURE` within seconds
- Error message indicates configuration issue

**Common Errors**:

| Error Message | Cause | Fix |
|---------------|-------|-----|
| "Database connection failed" | DB unavailable | Check PostgreSQL service |
| "SSH connection timeout" | Asset unreachable | Verify network/credentials |
| "Permission denied" | Auth failure | Check user permissions |
| "Patch not found" | Invalid patch ID | Verify patch exists |

**Troubleshooting**:

```bash
# Get detailed error
curl "$BASE_URL/api/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.error, .traceback'

# Check worker logs for full stack trace
docker logs celery-worker-1 | grep -A 20 "Task.*failed"

# Verify resource availability
curl "$BASE_URL/api/v1/patches/123" -H "Authorization: Bearer $TOKEN"
curl "$BASE_URL/api/v1/assets/456" -H "Authorization: Bearer $TOKEN"
```

---

#### Issue 3: Cannot Retrieve Task Status (404)

**Symptoms**:
- `GET /api/v1/tasks/{task_id}` returns 404
- Task ID appears valid

**Causes**:
- Task expired from result backend
- Redis connection issue
- Task never actually started

**Troubleshooting**:

```bash
# Check Redis connectivity
docker exec redis redis-cli PING

# Check if task ID exists in Redis
docker exec redis redis-cli --scan --pattern "celery-task-meta-*"

# Verify result backend configuration
grep CELERY_RESULT_BACKEND services/deployment_orchestrator/celery.py
```

**Resolution**:
1. Increase result expiration: `CELERY_RESULT_EXPIRES=86400` (24 hours)
2. Restart Redis if connection failed
3. Check original response for correct task ID

---

## Best Practices

### 1. Polling Intervals

**Don't poll too frequently!**

| Operation Type | Recommended Interval |
|----------------|---------------------|
| Deployment (5-30 min) | Every 10-30 seconds |
| Scan (10-60 min) | Every 30-60 seconds |
| Patch Gen (2-10 min) | Every 10-15 seconds |
| Quick operations | Every 5-10 seconds |

**Why?**
- Reduces API load
- Prevents rate limiting
- More efficient resource usage

**Implementation**:

```python
import time

def wait_for_task(task_id, interval=10, timeout=3600):
    """Poll task with exponential backoff"""
    start_time = time.time()
    backoff = interval

    while time.time() - start_time < timeout:
        status = get_task_status(task_id)

        if status['ready']:
            return status

        time.sleep(backoff)

        # Exponential backoff (max 60s)
        backoff = min(backoff * 1.5, 60)

    raise TimeoutError(f"Task {task_id} did not complete in {timeout}s")
```

---

### 2. Timeout Management

Always set appropriate timeouts:

```python
# Good: Reasonable timeout
try:
    result = wait_for_task(task_id, timeout=1800)  # 30 minutes
except TimeoutError:
    print(f"Task {task_id} timed out - consider cancelling")
    cancel_task(task_id)

# Bad: Infinite wait
while True:
    status = get_task_status(task_id)
    if status['ready']:
        break
    time.sleep(10)  # Could wait forever!
```

---

### 3. Error Handling

Always handle failures gracefully:

```python
def deploy_with_error_handling(patch_id, asset_ids):
    # Trigger deployment
    response = trigger_deployment(patch_id, asset_ids)
    task_id = response['task_id']

    try:
        # Wait for completion
        result = wait_for_task(task_id, timeout=1800)

        if result['successful']:
            print(f"✅ Deployment successful: {result['result']}")
            return result['result']
        else:
            error = result.get('error', 'Unknown error')
            print(f"❌ Deployment failed: {error}")

            # Log failure for investigation
            log_deployment_failure(patch_id, asset_ids, error)

            # Trigger automatic rollback?
            if should_rollback(error):
                trigger_rollback(patch_id, asset_ids)

            raise DeploymentError(error)

    except TimeoutError:
        print(f"⏰ Deployment timed out after 30 minutes")

        # Check final status
        final_status = get_task_status(task_id)
        print(f"Final state: {final_status['state']}")

        # Cancel if still running
        if not final_status['ready']:
            cancel_task(task_id)

        raise
```

---

### 4. Logging and Auditing

Log all task operations for audit trail:

```python
import logging

logger = logging.getLogger(__name__)

def trigger_deployment_with_audit(patch_id, asset_ids, user_id):
    logger.info(
        f"User {user_id} triggering deployment: "
        f"patch={patch_id}, assets={asset_ids}"
    )

    response = trigger_deployment(patch_id, asset_ids)
    task_id = response['task_id']

    logger.info(f"Deployment task created: {task_id}")

    result = wait_for_task(task_id)

    if result['successful']:
        logger.info(
            f"Deployment {task_id} completed successfully: "
            f"{result['result']}"
        )
    else:
        logger.error(
            f"Deployment {task_id} failed: "
            f"{result.get('error')}"
        )

    return result
```

---

## FAQ

### Q: How long are task results stored?

**A**: By default, task results are stored in Redis for **24 hours** after completion. After that, you'll get a 404 when checking status.

**Configure retention**:
```python
# services/deployment_orchestrator/celery.py
CELERY_RESULT_EXPIRES = 86400  # 24 hours (default)
CELERY_RESULT_EXPIRES = 604800  # 7 days (recommended for audits)
```

---

### Q: Can I get notifications when tasks complete?

**A**: Not built-in yet, but you can implement webhooks:

```python
# Option 1: Poll and notify
def notify_on_completion(task_id, webhook_url):
    while True:
        status = get_task_status(task_id)
        if status['ready']:
            requests.post(webhook_url, json=status)
            break
        time.sleep(30)

# Option 2: Use Celery signals (requires custom code)
from celery.signals import task_success, task_failure

@task_success.connect
def task_success_handler(sender, result, **kwargs):
    notify_slack(f"Task {sender.request.id} completed: {result}")

@task_failure.connect
def task_failure_handler(sender, exception, **kwargs):
    notify_pagerduty(f"Task {sender.request.id} failed: {exception}")
```

---

### Q: What happens if I restart Celery workers?

**A**: Running tasks will be interrupted!

**Safe restart procedure**:

1. **Stop accepting new tasks**:
   ```bash
   # Send TERM signal (graceful shutdown)
   docker kill --signal=TERM celery-worker-1
   ```

2. **Wait for tasks to complete** (up to `CELERY_TASK_TIME_LIMIT`):
   ```bash
   # Check for active tasks
   celery -A services.deployment_orchestrator.celery inspect active
   ```

3. **Force stop if necessary** (after timeout):
   ```bash
   docker kill --signal=KILL celery-worker-1
   ```

4. **Restart workers**:
   ```bash
   docker-compose up -d celery-worker
   ```

**Interrupted tasks** will remain in `STARTED` state until they timeout or are revoked manually.

---

### Q: How many concurrent tasks can run?

**A**: Depends on worker configuration:

```bash
# Check current concurrency
celery -A services.deployment_orchestrator.celery inspect stats

# Output:
# celery@worker1: {
#   "pool": {
#     "max-concurrency": 4,  # Max parallel tasks
#     "processes": [1234, 1235, 1236, 1237]
#   }
# }
```

**Adjust concurrency**:
```bash
# In docker-compose.yml
celery-worker:
  command: celery -A services.deployment_orchestrator.celery worker --concurrency=8

# Or environment variable
environment:
  CELERY_WORKER_CONCURRENCY: 8
```

**Recommendation**: Set concurrency to **CPU cores × 2** for I/O-bound tasks (deployments, scans).

---

## Reference

### API Endpoints Quick Reference

| Method | Endpoint | Purpose | Auth Required |
|--------|----------|---------|---------------|
| `GET` | `/api/v1/tasks/{task_id}` | Get task status | ✅ Yes |
| `DELETE` | `/api/v1/tasks/{task_id}` | Cancel task | ✅ Yes |
| `GET` | `/api/v1/tasks` | List recent tasks | ✅ Yes |

### Task States Reference

| State | Terminal? | Meaning |
|-------|-----------|---------|
| `PENDING` | No | Waiting to start |
| `STARTED` | No | Currently executing |
| `SUCCESS` | Yes | Completed successfully |
| `FAILURE` | Yes | Failed with error |
| `RETRY` | No | Retrying after failure |
| `REVOKED` | Yes | Cancelled |

### Response Fields Reference

| Field | Type | Present When | Description |
|-------|------|--------------|-------------|
| `task_id` | string | Always | Unique task identifier |
| `state` | string | Always | Current task state |
| `ready` | boolean | Always | True if terminal state |
| `successful` | boolean | When ready | True if SUCCESS |
| `result` | object | When successful | Task return value |
| `error` | string | When failed | Error message |
| `traceback` | string | When failed | Full stack trace |
| `info` | object | When running | Progress information |
| `progress` | object | When available | Progress details |
| `completed_at` | string | When successful | ISO timestamp |
| `failed_at` | string | When failed | ISO timestamp |

---

## Training Checklist

Use this checklist to verify operator proficiency:

- [ ] Can authenticate and obtain JWT token
- [ ] Can trigger a deployment and retrieve task ID
- [ ] Can check task status using curl
- [ ] Can interpret task states (PENDING, STARTED, SUCCESS, FAILURE)
- [ ] Can monitor a long-running task until completion
- [ ] Can retrieve task results after completion
- [ ] Can cancel a running task
- [ ] Can list all active tasks
- [ ] Understands when it's safe to cancel tasks
- [ ] Can troubleshoot stuck tasks
- [ ] Can write a monitoring script
- [ ] Knows task result retention period (24 hours)
- [ ] Understands polling best practices
- [ ] Can handle task timeouts appropriately
- [ ] Can escalate issues when needed

---

## Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **Celery Documentation**: https://docs.celeryq.dev/
- **Redis Documentation**: https://redis.io/documentation
- **Internal Runbooks**: `/docs/runbooks/`
- **Support Channel**: #vulnzero-ops on Slack

---

**Document Version**: 1.0
**Last Review**: 2025-11-19
**Next Review**: 2025-12-19
**Maintainer**: DevOps Team
