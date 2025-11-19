# Event-Driven Architecture Guide

**Last Updated:** 2025-11-19
**Version:** 1.0.0

## Overview

VulnZero uses event-driven architecture to enable loose coupling between services, improve scalability, and provide real-time reactivity to system changes.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Event Types](#event-types)
- [Publishing Events](#publishing-events)
- [Subscribing to Events](#subscribing-to-events)
- [Event Schemas](#event-schemas)
- [Best Practices](#best-practices)
- [Patterns](#patterns)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Publishing an Event

```python
from shared.events import get_event_bus, create_vulnerability_detected_event

# Get event bus
event_bus = await get_event_bus()

# Create and publish event
event = create_vulnerability_detected_event(
    vulnerability_id=123,
    cve_id="CVE-2024-1234",
    severity="critical",
    asset_id=456,
    source_service="scanner-service",
)

await event_bus.publish(event)
```

### Subscribing to Events

```python
from shared.events import get_event_bus, EventType, VulnerabilityEvent

# Get event bus
event_bus = await get_event_bus()

# Register handler
@event_bus.subscribe(EventType.VULNERABILITY_DETECTED, VulnerabilityEvent)
async def handle_vulnerability(event: VulnerabilityEvent):
    print(f"New vulnerability: {event.cve_id} on asset {event.data['asset_id']}")
    # Perform analysis, send notifications, etc.

# Start consuming
await event_bus.start_consuming()
```

---

## Event Types

### Vulnerability Events

Events related to vulnerability lifecycle:

- **`VULNERABILITY_DETECTED`** - New vulnerability discovered by scanner
- **`VULNERABILITY_ANALYZED`** - Vulnerability has been analyzed (priority, impact)
- **`VULNERABILITY_PRIORITIZED`** - Priority score assigned
- **`VULNERABILITY_REMEDIATED`** - Vulnerability fixed
- **`VULNERABILITY_VERIFIED`** - Remediation verified by scanning

### Patch Events

Events related to patch lifecycle:

- **`PATCH_GENERATED`** - AI generated a patch
- **`PATCH_TESTED`** - Patch tested in digital twin
- **`PATCH_APPROVED`** - Patch approved for deployment
- **`PATCH_REJECTED`** - Patch rejected (failed tests)
- **`PATCH_DEPLOYED`** - Patch deployed to production

### Deployment Events

Events related to deployments:

- **`DEPLOYMENT_STARTED`** - Deployment initiated
- **`DEPLOYMENT_SUCCEEDED`** - Deployment completed successfully
- **`DEPLOYMENT_FAILED`** - Deployment failed
- **`DEPLOYMENT_ROLLED_BACK`** - Deployment rolled back

### Asset Events

Events related to asset lifecycle:

- **`ASSET_DISCOVERED`** - New asset discovered
- **`ASSET_UPDATED`** - Asset metadata updated
- **`ASSET_DECOMMISSIONED`** - Asset removed from monitoring
- **`ASSET_SCANNED`** - Asset scanned for vulnerabilities

### Scan Events

Events related to vulnerability scans:

- **`SCAN_STARTED`** - Vulnerability scan initiated
- **`SCAN_COMPLETED`** - Scan completed successfully
- **`SCAN_FAILED`** - Scan failed

---

## Publishing Events

### Using Event Factory Functions

```python
from shared.events import (
    create_vulnerability_detected_event,
    create_patch_generated_event,
    create_deployment_succeeded_event,
    get_event_bus,
)

event_bus = await get_event_bus()

# Vulnerability detected
vuln_event = create_vulnerability_detected_event(
    vulnerability_id=123,
    cve_id="CVE-2024-1234",
    severity="critical",
    asset_id=456,
)
await event_bus.publish(vuln_event)

# Patch generated
patch_event = create_patch_generated_event(
    patch_id=789,
    vulnerability_id=123,
    patch_type="code",
    confidence_score=0.95,
)
await event_bus.publish(patch_event)
```

### Creating Custom Events

```python
from shared.events import Event, EventType

# Create custom event
event = Event(
    event_type=EventType.VULNERABILITY_DETECTED,
    source_service="my-scanner",
    data={
        "vulnerability_id": 123,
        "cve_id": "CVE-2024-1234",
        "severity": "critical",
        "asset_id": 456,
        "scanner_source": "trivy",
    },
    correlation_id="scan-abc-123",  # Optional: correlate related events
    metadata={
        "scan_duration": 45.2,
        "packages_scanned": 234,
    },
)

await event_bus.publish(event)
```

### Correlation IDs

Use correlation IDs to track related events:

```python
import uuid

# Generate correlation ID for a workflow
correlation_id = str(uuid.uuid4())

# All events in this workflow share the correlation ID
scan_event = ScanEvent(
    event_type=EventType.SCAN_STARTED,
    source_service="scanner",
    correlation_id=correlation_id,
    data={"scan_id": "scan-123", "asset_id": 456},
)

vuln_event = VulnerabilityEvent(
    event_type=EventType.VULNERABILITY_DETECTED,
    source_service="scanner",
    correlation_id=correlation_id,  # Same ID!
    data={"vulnerability_id": 123, "cve_id": "CVE-2024-1234", "severity": "critical"},
)

# Publish both
await event_bus.publish(scan_event)
await event_bus.publish(vuln_event)
```

---

## Subscribing to Events

### Basic Subscription

```python
from shared.events import get_event_bus, EventType, VulnerabilityEvent

event_bus = await get_event_bus()

@event_bus.subscribe(EventType.VULNERABILITY_DETECTED, VulnerabilityEvent)
async def on_vulnerability_detected(event: VulnerabilityEvent):
    """Handle new vulnerabilities"""
    logger.info(f"New vulnerability: {event.cve_id}")

    # Send notification
    await send_notification(
        f"Critical vulnerability {event.cve_id} detected",
        severity=event.severity,
    )

    # Trigger analysis
    if event.severity == "critical":
        await trigger_immediate_analysis(event.vulnerability_id)

# Start consuming
await event_bus.start_consuming()
```

### Multiple Event Types

```python
@event_bus.subscribe(EventType.VULNERABILITY_DETECTED, VulnerabilityEvent)
async def handle_vuln_detected(event: VulnerabilityEvent):
    print(f"Detected: {event.cve_id}")

@event_bus.subscribe(EventType.VULNERABILITY_REMEDIATED, VulnerabilityEvent)
async def handle_vuln_remediated(event: VulnerabilityEvent):
    print(f"Remediated: {event.cve_id}")

@event_bus.subscribe(EventType.PATCH_GENERATED, PatchEvent)
async def handle_patch_generated(event: PatchEvent):
    print(f"Patch generated for vuln {event.vulnerability_id}")

# Start consuming (handles all registered event types)
await event_bus.start_consuming()
```

### Filtering Events

```python
@event_bus.subscribe(EventType.VULNERABILITY_DETECTED, VulnerabilityEvent)
async def handle_critical_vulnerabilities(event: VulnerabilityEvent):
    """Only process critical vulnerabilities"""
    if event.severity != "critical":
        return  # Ignore non-critical

    # Handle critical vulnerabilities
    await escalate_to_security_team(event)
```

### Error Handling

```python
@event_bus.subscribe(EventType.PATCH_DEPLOYED, PatchEvent)
async def handle_patch_deployment(event: PatchEvent):
    try:
        # Process deployment
        await verify_deployment(event.patch_id)

        # Publish success event
        success_event = DeploymentEvent(
            event_type=EventType.DEPLOYMENT_SUCCEEDED,
            source_service="deployment-verifier",
            correlation_id=event.correlation_id,
            data={
                "deployment_id": event.data["deployment_id"],
                "patch_id": event.patch_id,
            },
        )
        await event_bus.publish(success_event)

    except Exception as e:
        logger.error(f"Deployment verification failed: {e}")

        # Publish failure event
        failure_event = DeploymentEvent(
            event_type=EventType.DEPLOYMENT_FAILED,
            source_service="deployment-verifier",
            correlation_id=event.correlation_id,
            data={
                "deployment_id": event.data["deployment_id"],
                "patch_id": event.patch_id,
                "error": str(e),
            },
        )
        await event_bus.publish(failure_event)
```

---

## Event Schemas

### Base Event Schema

All events inherit from the base `Event` class:

```python
{
    "event_id": "550e8400-e29b-41d4-a716-446655440000",  # UUID
    "event_type": "vulnerability.detected",
    "timestamp": "2024-11-19T10:30:00Z",
    "source_service": "scanner-service",
    "data": {
        # Event-specific data
    },
    "correlation_id": "optional-correlation-id",  # Optional
    "metadata": {
        # Optional additional metadata
    }
}
```

### VulnerabilityEvent Schema

```python
{
    "event_id": "...",
    "event_type": "vulnerability.detected",
    "timestamp": "2024-11-19T10:30:00Z",
    "source_service": "scanner-service",
    "data": {
        "vulnerability_id": 123,
        "cve_id": "CVE-2024-1234",
        "severity": "critical",
        "asset_id": 456,
        "status": "new",
        "priority_score": 95.5
    }
}
```

### PatchEvent Schema

```python
{
    "event_id": "...",
    "event_type": "patch.generated",
    "timestamp": "2024-11-19T10:35:00Z",
    "source_service": "patch-engine",
    "data": {
        "patch_id": 789,
        "vulnerability_id": 123,
        "patch_type": "code",
        "status": "generated",
        "confidence_score": 0.95,
        "test_status": "pending"
    }
}
```

### DeploymentEvent Schema

```python
{
    "event_id": "...",
    "event_type": "deployment.succeeded",
    "timestamp": "2024-11-19T10:40:00Z",
    "source_service": "deployment-service",
    "data": {
        "deployment_id": 101,
        "patch_id": 789,
        "asset_id": 456,
        "deployment_method": "blue_green",
        "status": "success"
    }
}
```

---

## Best Practices

### 1. Keep Events Small

**Bad (large payload):**
```python
event.data = {
    "vulnerability_id": 123,
    "full_vulnerability_object": vuln.__dict__,  # Entire object!
    "full_asset_object": asset.__dict__,
    "related_patches": [p.__dict__ for p in patches],  # All related data!
}
```

**Good (minimal payload):**
```python
event.data = {
    "vulnerability_id": 123,
    "cve_id": "CVE-2024-1234",
    "severity": "critical",
    "asset_id": 456,
}
# Subscribers fetch additional data if needed
```

### 2. Use Correlation IDs

```python
# When starting a workflow, generate correlation ID
correlation_id = str(uuid.uuid4())

# Pass through all related events
scan_event.correlation_id = correlation_id
vuln_event.correlation_id = correlation_id
patch_event.correlation_id = correlation_id

# This allows tracing the entire workflow
```

### 3. Make Handlers Idempotent

```python
@event_bus.subscribe(EventType.PATCH_DEPLOYED, PatchEvent)
async def handle_patch_deployment(event: PatchEvent):
    """Idempotent handler - safe to call multiple times"""

    # Check if already processed
    if await is_already_processed(event.event_id):
        logger.info(f"Event {event.event_id} already processed, skipping")
        return

    # Process event
    await process_deployment(event.patch_id)

    # Mark as processed
    await mark_processed(event.event_id)
```

### 4. Handle Failures Gracefully

```python
@event_bus.subscribe(EventType.VULNERABILITY_DETECTED, VulnerabilityEvent)
async def handle_vulnerability(event: VulnerabilityEvent):
    try:
        await analyze_vulnerability(event.vulnerability_id)
    except Exception as e:
        logger.error(f"Failed to analyze vulnerability {event.vulnerability_id}: {e}")

        # Publish failure event or retry
        # But don't let exception propagate (message would be requeued)

        # Option 1: Dead letter queue
        await send_to_dlq(event)

        # Option 2: Retry with backoff
        await schedule_retry(event, delay=60)
```

### 5. Use Typed Events

```python
# Good: Use specific event classes
@event_bus.subscribe(EventType.VULNERABILITY_DETECTED, VulnerabilityEvent)
async def handle_vuln(event: VulnerabilityEvent):
    # IDE autocomplete works, type checking works
    vuln_id = event.vulnerability_id
    cve_id = event.cve_id

# Bad: Use generic Event class
@event_bus.subscribe(EventType.VULNERABILITY_DETECTED, Event)
async def handle_vuln(event: Event):
    # No autocomplete, prone to errors
    vuln_id = event.data["vulnerability_id"]  # Manual access
```

---

## Patterns

### Event Sourcing

Track all state changes as events:

```python
# Instead of just updating database
vuln.status = "analyzing"
db.commit()

# Emit event
event = VulnerabilityEvent(
    event_type=EventType.VULNERABILITY_ANALYZED,
    source_service="analysis-service",
    data={
        "vulnerability_id": vuln.id,
        "previous_status": "new",
        "new_status": "analyzing",
        "analysis_results": {...},
    },
)
await event_bus.publish(event)
```

### CQRS (Command Query Responsibility Segregation)

Separate write operations (commands) from read operations (queries):

```python
# Command: Create vulnerability
async def create_vulnerability(data):
    vuln = Vulnerability(**data)
    db.add(vuln)
    db.commit()

    # Emit event
    event = create_vulnerability_detected_event(...)
    await event_bus.publish(event)

# Query: Read from optimized read model
@event_bus.subscribe(EventType.VULNERABILITY_DETECTED, VulnerabilityEvent)
async def update_read_model(event: VulnerabilityEvent):
    """Update denormalized read-optimized view"""
    await cache_manager.set(
        f"vuln:{event.vulnerability_id}",
        event.data,
        ttl=3600,
    )
```

### Saga Pattern

Coordinate multi-step workflows:

```python
# Orchestrator for vulnerability remediation saga
@event_bus.subscribe(EventType.VULNERABILITY_DETECTED, VulnerabilityEvent)
async def remediation_saga(event: VulnerabilityEvent):
    """Coordinate vulnerability -> patch -> deploy -> verify"""

    correlation_id = event.correlation_id or str(uuid.uuid4())

    try:
        # Step 1: Analyze vulnerability
        await analyze_vulnerability(event.vulnerability_id)

        # Step 2: Generate patch
        patch_id = await generate_patch(event.vulnerability_id)

        # Step 3: Test patch
        test_passed = await test_patch(patch_id)

        if test_passed:
            # Step 4: Deploy patch
            await deploy_patch(patch_id, event.data["asset_id"])

            # Step 5: Verify remediation
            await verify_remediation(event.vulnerability_id)

    except Exception as e:
        # Compensating transactions (rollback)
        logger.error(f"Remediation saga failed: {e}")
        await rollback_remediation(event.vulnerability_id, correlation_id)
```

---

## Monitoring

### Prometheus Metrics

The event bus automatically tracks:

- **`vulnzero_events_published_total`** - Events published by type and service
- **`vulnzero_events_consumed_total`** - Events consumed by handler and status
- **`vulnzero_event_processing_duration_seconds`** - Event processing latency
- **`vulnzero_event_processing_errors_total`** - Event processing errors

### View Metrics

```bash
# In Grafana or Prometheus
# Events published per second
rate(vulnzero_events_published_total[5m])

# Event processing latency (p95)
histogram_quantile(0.95, rate(vulnzero_event_processing_duration_seconds_bucket[5m]))

# Error rate
sum(rate(vulnzero_event_processing_errors_total[5m])) / sum(rate(vulnzero_events_consumed_total[5m]))
```

### Logging

All events are automatically logged:

```
[INFO] Published event: vulnerability.detected (id=550e8400-e29b-41d4-a716-446655440000, routing_key=vulnerability.detected)
[INFO] Processed event vulnerability.detected with handle_vulnerability
```

---

## Troubleshooting

### Events Not Being Consumed

**Problem:** Published events but no handlers triggered.

**Solutions:**

1. Check if consumer is running:
   ```python
   await event_bus.start_consuming()  # Must be called!
   ```

2. Check if handler is registered:
   ```python
   # Ensure @event_bus.subscribe is called before start_consuming
   ```

3. Check RabbitMQ connection:
   ```bash
   docker-compose logs rabbitmq
   ```

### Duplicate Event Processing

**Problem:** Event handler called multiple times for same event.

**Solutions:**

1. Make handlers idempotent (check if already processed)
2. Use unique event IDs to track processing
3. Check for multiple consumers on same queue

### Event Processing Too Slow

**Problem:** Events piling up in queue.

**Solutions:**

1. Add more consumers:
   ```python
   # Run multiple instances of consumer service
   docker-compose scale vulnerability-scanner=3
   ```

2. Optimize handler performance:
   ```python
   # Use async operations
   # Cache frequently accessed data
   # Batch database operations
   ```

3. Increase prefetch count:
   ```python
   await channel.set_qos(prefetch_count=50)  # Default is 10
   ```

### RabbitMQ Connection Issues

**Problem:** Can't connect to RabbitMQ.

**Solutions:**

1. Check RabbitMQ is running:
   ```bash
   docker-compose ps rabbitmq
   ```

2. Check connection URL:
   ```bash
   echo $RABBITMQ_URL
   # Should be: amqp://guest:guest@rabbitmq:5672/
   ```

3. Check network connectivity:
   ```bash
   docker-compose exec api_gateway ping rabbitmq
   ```

---

## Integration Examples

### Scanner Service (Publisher)

```python
# services/vulnerability_scanner/scanner.py
from shared.events import get_event_bus, create_vulnerability_detected_event

async def scan_asset(asset_id: int):
    # Perform scan
    vulnerabilities = await perform_scan(asset_id)

    # Get event bus
    event_bus = await get_event_bus()

    # Publish event for each vulnerability
    for vuln in vulnerabilities:
        event = create_vulnerability_detected_event(
            vulnerability_id=vuln.id,
            cve_id=vuln.cve_id,
            severity=vuln.severity,
            asset_id=asset_id,
            source_service="vulnerability-scanner",
        )
        await event_bus.publish(event)
```

### Analysis Service (Subscriber)

```python
# services/vulnerability_analysis/analyzer.py
from shared.events import get_event_bus, EventType, VulnerabilityEvent

async def start_analysis_service():
    event_bus = await get_event_bus()

    @event_bus.subscribe(EventType.VULNERABILITY_DETECTED, VulnerabilityEvent)
    async def analyze_vulnerability(event: VulnerabilityEvent):
        logger.info(f"Analyzing vulnerability {event.vulnerability_id}")

        # Perform analysis
        priority = await calculate_priority(event.vulnerability_id)
        impact = await assess_impact(event.vulnerability_id)

        # Update database
        await update_vulnerability_analysis(
            event.vulnerability_id,
            priority=priority,
            impact=impact,
        )

        # Publish analyzed event
        analyzed_event = VulnerabilityEvent(
            event_type=EventType.VULNERABILITY_ANALYZED,
            source_service="analysis-service",
            correlation_id=event.correlation_id,
            data={
                "vulnerability_id": event.vulnerability_id,
                "priority_score": priority,
                "impact_score": impact,
            },
        )
        await event_bus.publish(analyzed_event)

    # Start consuming
    await event_bus.start_consuming()
```

---

## Further Reading

- [RabbitMQ Tutorials](https://www.rabbitmq.com/getstarted.html)
- [Event-Driven Architecture Patterns](https://martinfowler.com/articles/201701-event-driven.html)
- [Domain Events](https://martinfowler.com/eaaDev/DomainEvent.html)

---

**Maintained by:** VulnZero Architecture Team
**Questions?** See #vulnzero-architecture in Slack
