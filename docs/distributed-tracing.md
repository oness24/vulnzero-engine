# Distributed Tracing with OpenTelemetry

**Last Updated:** 2025-11-19
**Version:** 1.0.0

## Overview

VulnZero uses OpenTelemetry for distributed tracing across microservices, enabling end-to-end visibility of requests, performance analysis, and debugging of complex workflows.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Instrumentation](#instrumentation)
- [Manual Tracing](#manual-tracing)
- [Viewing Traces](#viewing-traces)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Starting Jaeger

```bash
# Start all services including Jaeger
docker-compose up -d

# Verify Jaeger is running
docker-compose ps jaeger

# Access Jaeger UI
open http://localhost:16686
```

### Basic Instrumentation

```python
from shared.tracing import setup_tracing, instrument_fastapi
from fastapi import FastAPI

# Create app
app = FastAPI()

# Setup tracing
tracer = setup_tracing(
    service_name="api-gateway",
    jaeger_host="jaeger",
    jaeger_port=6831,
)

# Instrument FastAPI (automatic tracing)
instrument_fastapi(app)

# Now all HTTP requests are automatically traced!
```

---

## Architecture

### Components

```
┌──────────────┐
│ API Gateway  │──┐
└──────────────┘  │
                  │
┌──────────────┐  │    ┌──────────────┐
│ Scanner Svc  │──┼───▶│   Jaeger     │──▶ Jaeger UI
└──────────────┘  │    │   Collector  │    (localhost:16686)
                  │    └──────────────┘
┌──────────────┐  │
│ Patch Engine │──┘
└──────────────┘
```

**Flow:**
1. Service generates spans during request processing
2. Spans sent to Jaeger agent (UDP 6831)
3. Jaeger collector stores spans
4. View traces in Jaeger UI

### Trace Structure

```
Trace (end-to-end request)
  │
  ├─ Span: HTTP GET /api/v1/vulnerabilities
  │   │
  │   ├─ Span: db.SELECT vulnerabilities
  │   │
  │   ├─ Span: cache.get vuln:list
  │   │
  │   └─ Span: external.nvd-api.get_cve
  │
  └─ Span: event.publish vulnerability.detected
```

**Key concepts:**
- **Trace**: Complete journey of a request across services
- **Span**: Unit of work within a trace (function, query, API call)
- **Context**: Propagated between services to link spans
- **Attributes**: Key-value metadata attached to spans

---

## Instrumentation

### Automatic Instrumentation

OpenTelemetry provides automatic instrumentation for common frameworks:

**FastAPI:**
```python
from shared.tracing import setup_tracing, instrument_fastapi

app = FastAPI()
setup_tracing("api-gateway")
instrument_fastapi(app)

# All HTTP endpoints automatically traced
@app.get("/vulnerabilities")
async def list_vulns():
    return []
```

**SQLAlchemy:**
```python
from shared.tracing import instrument_sqlalchemy
from shared.config.database import engine

# Instrument database
instrument_sqlalchemy(engine)

# All queries automatically traced
results = db.query(Vulnerability).all()
```

**Redis:**
```python
from shared.tracing import instrument_redis

# Instrument Redis
instrument_redis()

# All cache operations automatically traced
await cache_manager.get("key")
```

**HTTP Clients:**
```python
from shared.tracing import instrument_http_clients

# Instrument requests and httpx
instrument_http_clients()

# All HTTP calls automatically traced
response = requests.get("https://api.example.com")
response = await httpx.get("https://api.example.com")
```

### Full Service Setup

```python
# services/api_gateway/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

from shared.tracing import (
    setup_tracing,
    instrument_fastapi,
    instrument_sqlalchemy,
    instrument_redis,
    instrument_http_clients,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    tracer = setup_tracing(
        service_name="api-gateway",
        jaeger_host="jaeger",
        jaeger_port=6831,
    )

    # Instrument frameworks
    instrument_fastapi(app)

    from shared.config.database import engine
    instrument_sqlalchemy(engine)

    instrument_redis()
    instrument_http_clients()

    yield

    # Shutdown (OpenTelemetry handles cleanup)

app = FastAPI(lifespan=lifespan)
```

---

## Manual Tracing

### Function Decorator

```python
from shared.tracing import trace_function

@trace_function(span_name="process_vulnerability")
async def process_vulnerability(vuln_id: int):
    """Function automatically traced"""
    # Do work
    return result

# With custom attributes
@trace_function(
    span_name="analyze_code",
    attributes={"component": "analyzer"}
)
async def analyze_code(code: str):
    # Span includes component=analyzer attribute
    return analysis
```

### Context Managers

**Database Queries:**
```python
from shared.tracing import trace_database_query

with trace_database_query("SELECT", "vulnerabilities"):
    vulns = db.query(Vulnerability).filter_by(status="new").all()
```

**External API Calls:**
```python
from shared.tracing import trace_external_call

with trace_external_call("nvd-api", "get_cve"):
    response = requests.get(f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}")
```

**Event Publishing:**
```python
from shared.tracing import trace_event_publish

with trace_event_publish("vulnerability.detected"):
    await event_bus.publish(event)
```

**Event Consumption:**
```python
from shared.tracing import trace_event_consume

@event_bus.subscribe(EventType.VULNERABILITY_DETECTED)
async def handle_vulnerability(event):
    with trace_event_consume("vulnerability.detected", "handle_vulnerability"):
        # Process event
        pass
```

### Manual Span Creation

```python
from shared.tracing import get_tracer

tracer = get_tracer()

with tracer.start_as_current_span("custom_operation") as span:
    # Add attributes
    span.set_attribute("vulnerability.id", vuln_id)
    span.set_attribute("severity", "critical")

    # Add events
    span.add_event("processing_started")

    # Do work
    result = process_data()

    span.add_event("processing_completed", {
        "items_processed": len(result)
    })

    return result
```

### Adding Attributes and Events

```python
from shared.tracing import add_span_attributes, add_span_event

# Inside a traced function
def process_vulnerabilities(vulns):
    # Add attributes to current span
    add_span_attributes(
        vuln_count=len(vulns),
        has_critical=any(v.severity == "critical" for v in vulns),
    )

    for vuln in vulns:
        # Add event
        add_span_event("processing_vulnerability", {
            "vuln_id": vuln.id,
            "cve_id": vuln.cve_id,
        })

        process_single(vuln)
```

---

## Viewing Traces

### Jaeger UI

Access Jaeger UI at: **http://localhost:16686**

**Main Features:**

1. **Search Traces**
   - Filter by service, operation, tags
   - Search by trace ID
   - Time range selection

2. **Trace View**
   - Timeline visualization
   - Span details
   - Service dependencies
   - Performance bottlenecks

3. **Service Dependencies**
   - Visual service map
   - Request flow
   - Service health

4. **Compare Traces**
   - Compare performance
   - Identify regressions
   - A/B testing analysis

### Finding Traces

**By Service:**
```
Service: api-gateway
Operation: GET /api/v1/vulnerabilities
Lookback: Last 1 hour
Limit: 20
```

**By Trace ID:**
```
# Get trace ID from logs or response headers
# Example: 5f5c7c5c9b8e4b3a9d5e6f7a8b9c0d1e

Search by Trace ID: 5f5c7c5c9b8e4b3a9d5e6f7a8b9c0d1e
```

**By Tags:**
```
Tags:
  http.status_code=500
  error=true
  vulnerability.severity=critical
```

### Understanding Traces

**Span Timeline:**
```
|────── GET /api/v1/vulnerabilities (200ms) ──────|
  |─ db.SELECT vulnerabilities (50ms) ─|
  |─ cache.get (5ms) ─|
    |─ external.nvd-api (100ms) ─|
      |─ event.publish (10ms) ─|
```

**Span Details:**
- **Duration**: Time spent in span
- **Attributes**: Metadata (method, status, query, etc.)
- **Events**: Timestamped log points
- **Tags**: Searchable labels

---

## Best Practices

### 1. Name Spans Descriptively

**Bad:**
```python
with tracer.start_as_current_span("process"):
    do_work()
```

**Good:**
```python
with tracer.start_as_current_span("vulnerability.analysis.priority_scoring"):
    calculate_priority_score()
```

### 2. Add Meaningful Attributes

**Bad:**
```python
span.set_attribute("data", str(data))  # Too vague
```

**Good:**
```python
span.set_attribute("vulnerability.id", vuln_id)
span.set_attribute("vulnerability.severity", severity)
span.set_attribute("vulnerability.cve_id", cve_id)
span.set_attribute("processing.batch_size", len(batch))
```

### 3. Use Events for Important Moments

```python
with tracer.start_as_current_span("patch_deployment") as span:
    span.add_event("deployment_started")

    deploy_patch()

    span.add_event("health_check_initiated")
    if not health_check_passed():
        span.add_event("rollback_triggered")
        rollback()

    span.add_event("deployment_completed")
```

### 4. Propagate Context Across Services

```python
# Service A: API Gateway
import httpx
from opentelemetry import trace

# Context automatically propagated in HTTP headers
async with httpx.AsyncClient() as client:
    # OpenTelemetry adds trace headers automatically
    response = await client.post(
        "http://patch-engine:8001/generate",
        json=data
    )

# Service B: Patch Engine
# FastAPI instrumentation automatically extracts trace context
@app.post("/generate")
async def generate_patch(data: dict):
    # This span is linked to the parent trace from API Gateway
    return result
```

### 5. Don't Over-Instrument

**Bad (too granular):**
```python
with tracer.start_as_current_span("validate_field_1"):
    validate(field1)
with tracer.start_as_current_span("validate_field_2"):
    validate(field2)
# ... 100 more spans
```

**Good (appropriate granularity):**
```python
with tracer.start_as_current_span("validate_vulnerability_data"):
    validate_all_fields(data)
```

### 6. Handle Errors Properly

```python
from opentelemetry.trace import Status, StatusCode

with tracer.start_as_current_span("process_vulnerability") as span:
    try:
        result = process(vuln_id)
        span.set_status(Status(StatusCode.OK))
        return result
    except Exception as e:
        span.set_status(Status(StatusCode.ERROR))
        span.record_exception(e)
        raise
```

---

## Troubleshooting

### Traces Not Appearing

**Problem:** No traces show up in Jaeger UI.

**Solutions:**

1. **Check Jaeger is running:**
   ```bash
   docker-compose ps jaeger
   curl http://localhost:16686
   ```

2. **Verify tracing setup:**
   ```python
   # Check logs for initialization message
   # Should see: "✓ Distributed tracing initialized for api-gateway"
   ```

3. **Check network connectivity:**
   ```bash
   # From service container
   docker-compose exec api ping jaeger
   telnet jaeger 6831
   ```

4. **Enable console exporter for debugging:**
   ```python
   setup_tracing(
       service_name="api-gateway",
       enable_console=True  # Prints spans to console
   )
   ```

### Performance Impact

**Problem:** Tracing adds latency to requests.

**Solutions:**

1. **Use sampling:**
   ```python
   from opentelemetry.sdk.trace import sampling

   # Sample 10% of requests
   tracer_provider = TracerProvider(
       resource=resource,
       sampler=sampling.TraceIdRatioBased(0.1)
   )
   ```

2. **Batch span export:**
   ```python
   # Already configured in setup_tracing()
   BatchSpanProcessor(exporter, max_export_batch_size=512)
   ```

3. **Reduce span granularity** - Don't trace every function

### Missing Context Propagation

**Problem:** Spans not linked across services.

**Solutions:**

1. **Use instrumented HTTP clients:**
   ```python
   # Good: Auto-propagates context
   instrument_http_clients()
   response = requests.get(url)

   # Bad: Manual propagation needed
   response = urllib.request.urlopen(url)
   ```

2. **Manual context propagation:**
   ```python
   from opentelemetry.propagate import inject, extract

   # Sender
   headers = {}
   inject(headers)
   requests.post(url, headers=headers)

   # Receiver
   context = extract(request.headers)
   with tracer.start_as_current_span("operation", context=context):
       process()
   ```

---

## Integration Examples

### Complete API Service

```python
# services/api_gateway/main.py
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import logging

from shared.tracing import (
    setup_tracing,
    instrument_fastapi,
    instrument_sqlalchemy,
    instrument_redis,
    instrument_http_clients,
    trace_function,
    add_span_attributes,
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup tracing on startup
    tracer = setup_tracing(
        service_name="api-gateway",
        jaeger_host="jaeger",
        jaeger_port=6831,
    )

    # Instrument frameworks
    instrument_fastapi(app)

    from shared.config.database import engine
    instrument_sqlalchemy(engine)

    instrument_redis()
    instrument_http_clients()

    logger.info("Tracing initialized")

    yield

app = FastAPI(lifespan=lifespan)

# Endpoints are automatically traced
@app.get("/api/v1/vulnerabilities")
@trace_function(span_name="list_vulnerabilities")
async def list_vulnerabilities(request: Request):
    # Add custom attributes
    add_span_attributes(
        endpoint="list_vulnerabilities",
        user_agent=request.headers.get("user-agent"),
    )

    # Database query (automatically traced)
    vulns = db.query(Vulnerability).all()

    return {"vulnerabilities": [v.to_dict() for v in vulns]}
```

---

## Further Reading

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Distributed Tracing Best Practices](https://opentelemetry.io/docs/concepts/signals/traces/)

---

**Maintained by:** VulnZero DevOps Team
**Questions?** See #vulnzero-tracing in Slack
