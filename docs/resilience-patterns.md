# Resilience Patterns Guide

**Last Updated:** 2025-11-19
**Version:** 1.0.0

## Overview

VulnZero implements comprehensive resilience patterns to handle failures gracefully, prevent cascading failures, and ensure system stability under adverse conditions.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Circuit Breaker](#circuit-breaker)
- [Retry with Backoff](#retry-with-backoff)
- [Timeout](#timeout)
- [Bulkhead](#bulkhead)
- [Combining Patterns](#combining-patterns)
- [Best Practices](#best-practices)
- [Monitoring](#monitoring)

---

## Quick Start

### Circuit Breaker

Prevents cascading failures by stopping requests to failing services:

```python
from shared.resilience import circuit_breaker
import httpx

@circuit_breaker(
    name="nvd-api",
    failure_threshold=5,
    recovery_timeout=60
)
async def fetch_cve_data(cve_id: str):
    response = await httpx.get(f"https://nvd.nist.gov/...")
    return response.json()

# After 5 failures, circuit opens for 60 seconds
```

### Retry with Exponential Backoff

Automatically retry failed operations:

```python
from shared.resilience import retry_with_backoff

@retry_with_backoff(
    max_retries=3,
    base_delay=1.0,
    exceptions=(httpx.HTTPError,)
)
async def fetch_data():
    response = await httpx.get("https://api.example.com")
    return response.json()

# Retries: 1s, 2s, 4s delays
```

### Timeout

Prevent operations from running indefinitely:

```python
from shared.resilience import with_timeout

@with_timeout(30.0)
async def fetch_large_dataset():
    data = await slow_api_call()
    return data

# Raises TimeoutError after 30 seconds
```

### Bulkhead

Limit concurrent operations:

```python
from shared.resilience import get_bulkhead

bulkhead = get_bulkhead("api-calls", max_concurrent=10)

async def make_api_call(url):
    async with bulkhead:
        # Only 10 concurrent calls allowed
        response = await httpx.get(url)
        return response.json()
```

---

## Circuit Breaker

### Concept

Circuit breaker prevents cascading failures by stopping requests to a failing service and giving it time to recover.

**States:**
- **CLOSED**: Normal operation, all requests pass through
- **OPEN**: Too many failures, all requests rejected immediately
- **HALF_OPEN**: Testing recovery, limited requests allowed

```
┌─────────┐          5 failures          ┌──────┐
│ CLOSED  │─────────────────────────────▶│ OPEN │
└─────────┘                               └──────┘
     ▲                                       │
     │                                       │
     │         1 success                     │ 60s timeout
     │                                       │
     │         ┌─────────────┐               │
     └─────────│ HALF_OPEN   │◀──────────────┘
               └─────────────┘
```

### Usage

**Basic:**
```python
from shared.resilience import CircuitBreaker
import requests

cb = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=requests.RequestException,
    name="external-api"
)

# Context manager
with cb:
    response = requests.get("https://api.example.com")
```

**Decorator:**
```python
from shared.resilience import circuit_breaker

@circuit_breaker(
    name="nvd-api",
    failure_threshold=3,
    recovery_timeout=30,
    expected_exception=httpx.HTTPError
)
async def fetch_cve_details(cve_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"
        )
        response.raise_for_status()
        return response.json()

# Circuit automatically tracks failures
try:
    data = await fetch_cve_details("CVE-2024-1234")
except CircuitBreakerError:
    # Circuit is open, service unavailable
    logger.error("NVD API circuit breaker is OPEN")
```

**Manual Control:**
```python
from shared.resilience import get_circuit_breaker

cb = get_circuit_breaker("my-service")

# Check state
if cb.is_open:
    print("Circuit is OPEN, using fallback")
    return cached_data

# Manual reset
cb.reset()
```

### Configuration

```python
CircuitBreaker(
    failure_threshold=5,      # Open after 5 failures
    recovery_timeout=60,      # Wait 60s before trying again
    expected_exception=Exception,  # What counts as failure
    name="my-circuit"         # For logging/monitoring
)
```

---

## Retry with Backoff

### Concept

Automatically retry failed operations with increasing delays between attempts.

**Strategies:**
- **Exponential**: 2^n * base_delay (1s, 2s, 4s, 8s, ...)
- **Linear**: n * base_delay (1s, 2s, 3s, 4s, ...)
- **Constant**: base_delay (1s, 1s, 1s, 1s, ...)

### Usage

**Basic:**
```python
from shared.resilience import retry_with_backoff, RetryStrategy

@retry_with_backoff(
    max_retries=5,
    base_delay=2.0,
    max_delay=60.0,
    strategy=RetryStrategy.EXPONENTIAL
)
async def fetch_data_from_api():
    response = await httpx.get("https://api.example.com/data")
    response.raise_for_status()
    return response.json()
```

**With Specific Exceptions:**
```python
import httpx

@retry_with_backoff(
    max_retries=3,
    base_delay=1.0,
    exceptions=(httpx.HTTPError, httpx.TimeoutException)
)
async def fetch_with_timeout():
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get("https://api.example.com")
        return response.json()
```

**With Retry Callback:**
```python
def on_retry_callback(attempt: int, delay: float, exception: Exception):
    logger.warning(
        f"Retry attempt {attempt + 1}, waiting {delay:.2f}s. Error: {exception}"
    )
    # Could send metrics, update dashboard, etc.

@retry_with_backoff(
    max_retries=5,
    base_delay=1.0,
    on_retry=on_retry_callback
)
async def critical_operation():
    # Operation with retry tracking
    pass
```

### Pre-configured Decorators

For common scenarios:

```python
from shared.resilience import (
    retry_api_call,
    retry_database_operation,
    retry_network_call,
)

# API calls: 3 retries, exponential (1s, 2s, 4s)
@retry_api_call
async def fetch_from_api():
    pass

# Database operations: 2 retries, linear (2s, 4s)
@retry_database_operation
async def save_to_database():
    pass

# Network calls: 5 retries, exponential, max 30s
@retry_network_call
async def download_file():
    pass
```

---

## Timeout

### Concept

Prevent operations from running indefinitely by enforcing time limits.

### Usage

**Basic:**
```python
from shared.resilience import with_timeout

@with_timeout(30.0)
async def fetch_large_dataset():
    # Will raise TimeoutError if takes > 30 seconds
    data = await slow_api_call()
    return data

try:
    result = await fetch_large_dataset()
except TimeoutError:
    logger.error("Operation timed out")
    result = fallback_data
```

**Multiple Timeouts:**
```python
# Overall operation timeout: 60s
@with_timeout(60.0)
async def complex_operation():
    # Individual step timeout: 20s
    @with_timeout(20.0)
    async def step1():
        return await api_call_1()

    @with_timeout(20.0)
    async def step2():
        return await api_call_2()

    result1 = await step1()
    result2 = await step2()
    return combine(result1, result2)
```

---

## Bulkhead

### Concept

Isolate resources and limit concurrent operations to prevent resource exhaustion and cascading failures.

```
┌──────────────────────┐
│  Bulkhead (max=10)   │
│                      │
│  [█][█][█][█][█]     │  5 operations running
│  [ ][ ][ ][ ][ ]     │  5 slots available
└──────────────────────┘
        │
        ▼
   More requests wait in queue
```

### Usage

**Basic:**
```python
from shared.resilience import Bulkhead

bulkhead = Bulkhead(
    max_concurrent=10,
    max_wait_time=5.0,
    name="api-calls"
)

async def make_api_call(url: str):
    async with bulkhead:
        # Only 10 concurrent calls allowed
        # If all slots full, wait up to 5 seconds
        response = await httpx.get(url)
        return response.json()

# Process many URLs concurrently, but controlled
urls = [f"https://api.example.com/item/{i}" for i in range(100)]
results = await asyncio.gather(*[make_api_call(url) for url in urls])
```

**Get or Create:**
```python
from shared.resilience import get_bulkhead

# Get shared bulkhead (creates if doesn't exist)
bulkhead = get_bulkhead(
    name="nvd-api-calls",
    max_concurrent=5,
    max_wait_time=10.0
)

async def fetch_cve(cve_id: str):
    async with bulkhead:
        return await httpx.get(f"https://nvd.nist.gov/...")
```

**Check Capacity:**
```python
bulkhead = get_bulkhead("my-bulkhead", max_concurrent=10)

print(f"Current: {bulkhead.current_count}")
print(f"Available: {bulkhead.available_slots}")

if bulkhead.available_slots > 0:
    async with bulkhead:
        await do_work()
else:
    logger.warning("Bulkhead at capacity")
```

---

## Combining Patterns

### Circuit Breaker + Retry

```python
from shared.resilience import circuit_breaker, retry_with_backoff
import httpx

@circuit_breaker(name="external-api", failure_threshold=10, recovery_timeout=120)
@retry_with_backoff(max_retries=3, base_delay=1.0)
async def fetch_external_data(url: str):
    response = await httpx.get(url)
    response.raise_for_status()
    return response.json()

# Retries up to 3 times
# If 10 total failures, circuit opens for 120 seconds
```

### Timeout + Retry

```python
from shared.resilience import with_timeout, retry_with_backoff

@retry_with_backoff(max_retries=5, base_delay=2.0)
@with_timeout(30.0)
async def fetch_with_timeout_and_retry():
    # Each attempt times out after 30s
    # Retries up to 5 times
    response = await httpx.get("https://slow-api.example.com")
    return response.json()
```

### Circuit Breaker + Bulkhead + Retry + Timeout

```python
from shared.resilience import (
    circuit_breaker,
    get_bulkhead,
    retry_with_backoff,
    with_timeout,
)

bulkhead = get_bulkhead("nvd-api", max_concurrent=5)

@circuit_breaker(name="nvd-api", failure_threshold=10, recovery_timeout=60)
@retry_with_backoff(max_retries=3, base_delay=1.0)
@with_timeout(30.0)
async def fetch_cve_comprehensive(cve_id: str):
    async with bulkhead:  # Limit concurrency
        # Timeout per attempt: 30s
        # Retry: 3 times
        # Circuit breaker: Opens after 10 failures
        response = await httpx.get(
            f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"
        )
        response.raise_for_status()
        return response.json()
```

---

## Best Practices

### 1. Choose Appropriate Failure Thresholds

```python
# Too low: Circuit trips on transient errors
CircuitBreaker(failure_threshold=2)  # Too sensitive

# Too high: Takes too long to detect failures
CircuitBreaker(failure_threshold=100)  # Not responsive

# Good: Balance between responsiveness and stability
CircuitBreaker(failure_threshold=5-10)  # Reasonable
```

### 2. Set Realistic Timeouts

```python
# Too short: Fails on normal slow responses
@with_timeout(1.0)  # Too aggressive for external API

# Too long: Doesn't prevent hanging
@with_timeout(300.0)  # 5 minutes is too long

# Good: Based on p99 latency + buffer
@with_timeout(30.0)  # Reasonable for most APIs
```

### 3. Use Appropriate Retry Counts

```python
# Too many: Wastes resources on permanent failures
@retry_with_backoff(max_retries=20)  # Too many

# Too few: Gives up on transient errors
@retry_with_backoff(max_retries=1)  # Not resilient enough

# Good: 3-5 retries for most cases
@retry_with_backoff(max_retries=3-5)  # Balanced
```

### 4. Only Retry Transient Errors

```python
# Bad: Retry everything
@retry_with_backoff(exceptions=(Exception,))

# Good: Retry specific transient errors
@retry_with_backoff(exceptions=(
    httpx.TimeoutException,
    httpx.ConnectError,
    # Don't retry 4xx errors (client errors)
))
```

### 5. Add Jitter to Prevent Thundering Herd

```python
# Jitter is enabled by default in retry_with_backoff
# This prevents all clients from retrying at the same time

@retry_with_backoff(max_retries=5, base_delay=1.0)
# Actual delays will be: 1.0-1.25s, 2.0-2.5s, 4.0-5.0s, etc.
```

---

## Monitoring

### Metrics to Track

**Circuit Breaker:**
```python
# Track circuit breaker state changes
from shared.monitoring import circuit_breaker_state_changes

circuit_breaker_state_changes.labels(
    circuit_name="nvd-api",
    state="OPEN"
).inc()
```

**Retry:**
```python
# Track retry attempts
from shared.monitoring import retry_attempts_total

retry_attempts_total.labels(
    function="fetch_cve_data",
    attempt=3
).inc()
```

**Timeouts:**
```python
# Track timeout occurrences
from shared.monitoring import timeouts_total

timeouts_total.labels(
    function="fetch_large_dataset"
).inc()
```

### Logging

All resilience patterns automatically log important events:

```python
# Circuit breaker
[WARNING] Circuit breaker 'nvd-api' OPENED after 5 failures
[INFO] Circuit breaker 'nvd-api' transitioning to HALF_OPEN
[INFO] Circuit breaker 'nvd-api' recovered, transitioning to CLOSED

# Retry
[WARNING] Function fetch_data failed (attempt 1/4), retrying in 1.2s. Error: ...
[INFO] Function fetch_data succeeded after 2 retries

# Timeout
[ERROR] Function fetch_large_dataset timed out after 30.0s

# Bulkhead
[INFO] Bulkhead 'api-calls' initialized (max_concurrent=10, max_wait=5.0s)
```

---

## Troubleshooting

### Circuit Breaker Always Open

**Problem:** Circuit breaker constantly open, blocking requests.

**Solutions:**
1. Increase `failure_threshold`
2. Increase `recovery_timeout`
3. Check if downstream service is actually down
4. Review what exceptions count as failures

### Retries Not Helping

**Problem:** Still getting failures despite retries.

**Solutions:**
1. Check if errors are permanent (don't retry 4xx errors)
2. Increase `max_retries`
3. Increase delays between retries
4. Add circuit breaker to stop retrying failed service

### Operations Timing Out

**Problem:** Legitimate operations timing out.

**Solutions:**
1. Increase timeout duration
2. Optimize slow operations
3. Use streaming for large responses
4. Check network connectivity

### Bulkhead Rejecting Requests

**Problem:** Bulkhead at capacity, rejecting requests.

**Solutions:**
1. Increase `max_concurrent`
2. Reduce operation duration
3. Add more worker instances
4. Increase `max_wait_time`

---

## Further Reading

- [Martin Fowler: Circuit Breaker](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Release It!: Design Patterns for Production](https://pragprog.com/titles/mnee2/release-it-second-edition/)
- [AWS Well-Architected: Reliability](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)

---

**Maintained by:** VulnZero Architecture Team
**Questions?** See #vulnzero-resilience in Slack
