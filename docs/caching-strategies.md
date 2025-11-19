# Redis Caching Strategies

**Last Updated:** 2025-11-19
**Version:** 1.0.0

## Overview

This guide covers Redis caching strategies, patterns, and best practices for optimal VulnZero performance.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Caching Decorator](#caching-decorator)
- [Cache Manager](#cache-manager)
- [Caching Patterns](#caching-patterns)
- [Cache Keys](#cache-keys)
- [TTL Strategy](#ttl-strategy)
- [Invalidation](#invalidation)
- [Best Practices](#best-practices)
- [Monitoring](#monitoring)

---

## Quick Start

### Using the Decorator

**Simplest approach for caching function results:**

```python
from shared.cache import cache
from datetime import timedelta

# Cache for 5 minutes (default is 300 seconds)
@cache(ttl=300, prefix="vuln")
async def get_vulnerability_details(vuln_id: int):
    # Expensive database query or API call
    vuln = await db.query(Vulnerability).get(vuln_id)
    return vuln.to_dict()

# Cache for 1 hour
@cache(ttl=timedelta(hours=1), prefix="stats")
async def get_vulnerability_stats():
    # Expensive aggregation query
    return {
        "total": count_vulnerabilities(),
        "critical": count_critical(),
        "by_severity": group_by_severity(),
    }
```

### Using Cache Manager

**For manual cache control:**

```python
from shared.cache import cache_manager

# Store in cache
await cache_manager.set("user:123", user_data, ttl=3600)

# Retrieve from cache
user_data = await cache_manager.get("user:123", default={})

# Delete from cache
await cache_manager.delete("user:123")

# Check existence
exists = await cache_manager.exists("user:123")
```

---

## Caching Decorator

### Basic Usage

```python
from shared.cache import cache

@cache(ttl=600, prefix="asset")
async def get_asset(asset_id: str):
    return await db.query(Asset).filter_by(asset_id=asset_id).first()
```

### Custom Key Builder

```python
def custom_key_builder(user_id: int, resource: str):
    return f"user:{user_id}:{resource}"

@cache(
    ttl=300,
    prefix="custom",
    key_builder=custom_key_builder
)
async def get_user_resource(user_id: int, resource: str):
    return fetch_resource(user_id, resource)
```

### How It Works

1. **Cache Hit:** Returns cached value immediately
2. **Cache Miss:** 
   - Executes function
   - Stores result in Redis
   - Returns result
3. **Cache Error:** Falls back to executing function

### Metrics Integration

The decorator automatically tracks:
- `cache_hits_total` - Successful cache retrievals
- `cache_misses_total` - Cache misses requiring function execution
- `cache_operation_duration_seconds` - Operation latency

---

## Cache Manager

### API Methods

**get(key, default=None)**
```python
# Get with default
value = await cache_manager.get("config:setting", default="default_value")
```

**set(key, value, ttl=None)**
```python
# Set with TTL
await cache_manager.set("session:abc123", session_data, ttl=1800)

# Set without expiration
await cache_manager.set("permanent:key", data)
```

**delete(*keys)**
```python
# Delete single key
await cache_manager.delete("user:123")

# Delete multiple keys
await cache_manager.delete("user:123", "user:124", "user:125")
```

**exists(key)**
```python
if await cache_manager.exists("config:initialized"):
    print("Already initialized")
```

**increment(key, amount=1)**
```python
# Rate limiting
count = await cache_manager.increment(f"rate_limit:{user_id}:{minute}", 1)
if count > 100:
    raise RateLimitExceeded()
```

**expire(key, ttl)**
```python
# Update expiration
await cache_manager.expire("session:abc123", ttl=3600)
```

**get_ttl(key)**
```python
# Check remaining time
ttl = await cache_manager.get_ttl("session:abc123")
if ttl < 300:  # Less than 5 minutes
    await refresh_session()
```

**invalidate_pattern(pattern)**
```python
# Clear all vulnerability caches
await cache_manager.invalidate_pattern("vuln:*")

# Clear user-specific caches
await cache_manager.invalidate_pattern(f"user:{user_id}:*")
```

---

## Caching Patterns

### 1. Cache-Aside (Lazy Loading)

**Most common pattern - data is loaded on demand.**

```python
async def get_vulnerability(vuln_id: int):
    # Try cache first
    cached = await cache_manager.get(f"vuln:{vuln_id}")
    if cached:
        return cached
    
    # Cache miss - fetch from database
    vuln = await db.query(Vulnerability).get(vuln_id)
    
    # Store in cache
    await cache_manager.set(f"vuln:{vuln_id}", vuln.to_dict(), ttl=600)
    
    return vuln.to_dict()
```

**Or use decorator (simpler):**

```python
@cache(ttl=600, prefix="vuln")
async def get_vulnerability(vuln_id: int):
    vuln = await db.query(Vulnerability).get(vuln_id)
    return vuln.to_dict()
```

### 2. Write-Through

**Cache is updated synchronously with database writes.**

```python
from shared.cache import CacheStrategies

async def update_vulnerability(vuln_id: int, data: dict):
    # Update database
    async def persist(data):
        vuln = await db.query(Vulnerability).get(vuln_id)
        vuln.update(data)
        await db.commit()
    
    # Write through to cache
    await CacheStrategies.write_through(
        cache_key=f"vuln:{vuln_id}",
        value=data,
        persist_function=persist,
        ttl=600
    )
```

### 3. Invalidate-on-Write

**Simpler alternative - just delete cache on write.**

```python
async def update_vulnerability(vuln_id: int, data: dict):
    # Update database
    vuln = await db.query(Vulnerability).get(vuln_id)
    vuln.update(data)
    await db.commit()
    
    # Invalidate cache
    await cache_manager.delete(f"vuln:{vuln_id}")
```

### 4. Refresh-Ahead

**Proactively refresh cache before expiration.**

```python
async def get_vulnerability_with_refresh(vuln_id: int):
    cache_key = f"vuln:{vuln_id}"
    
    # Get from cache
    vuln = await cache_manager.get(cache_key)
    
    # Check if nearing expiration
    ttl = await cache_manager.get_ttl(cache_key)
    if ttl > 0 and ttl < 60:  # Less than 1 minute
        # Refresh in background
        asyncio.create_task(refresh_vulnerability_cache(vuln_id))
    
    return vuln

async def refresh_vulnerability_cache(vuln_id: int):
    fresh_data = await fetch_vulnerability_from_db(vuln_id)
    await cache_manager.set(f"vuln:{vuln_id}", fresh_data, ttl=600)
```

---

## Cache Keys

### Key Naming Convention

Follow this pattern: `{prefix}:{identifier}:{sub-key}`

**Examples:**
```
vuln:123                    # Vulnerability by ID
vuln:CVE-2024-1234         # Vulnerability by CVE
asset:server-prod-01       # Asset by ID
patch:456                  # Patch by ID
user:789:sessions          # User's sessions
stats:vulnerabilities:24h  # Statistics
cve:CVE-2024-1234          # CVE details from NVD
```

### Pre-defined Key Generators

```python
from shared.cache import CacheStrategies

# For common entities
vuln_key = CacheStrategies.cache_key_for_vulnerability(123)
asset_key = CacheStrategies.cache_key_for_asset("server-01")
patch_key = CacheStrategies.cache_key_for_patch(456)

# For statistics
stats_key = CacheStrategies.cache_key_for_stats("vulnerabilities", "24h")

# For external data
cve_key = CacheStrategies.cache_key_for_cve_details("CVE-2024-1234")
```

### Custom Key Generation

```python
from shared.cache import generate_cache_key

# Automatic key from arguments
key = generate_cache_key("search", query="sql injection", page=1, limit=20)
# Result: "search:abc123def456" (MD5 hash of arguments)
```

---

## TTL Strategy

### Recommended TTLs

**Reference Data (rarely changes):**
```python
# CVE details from NVD
@cache(ttl=timedelta(days=7), prefix="cve")

# Package versions
@cache(ttl=timedelta(hours=24), prefix="package")
```

**Computed Data:**
```python
# Statistics and aggregations
@cache(ttl=timedelta(minutes=15), prefix="stats")

# Search results
@cache(ttl=timedelta(minutes=5), prefix="search")
```

**Session Data:**
```python
# User sessions
ttl=timedelta(hours=2)

# API rate limits
ttl=timedelta(minutes=1)
```

**Hot Data (frequently accessed):**
```python
# Active vulnerabilities
@cache(ttl=timedelta(minutes=10), prefix="vuln")

# User profiles
@cache(ttl=timedelta(minutes=30), prefix="user")
```

### Dynamic TTL

```python
async def get_vulnerability_cached(vuln_id: int):
    vuln = await fetch_vulnerability(vuln_id)
    
    # Cache longer if remediated
    if vuln.status == "remediated":
        ttl = 3600 * 24  # 24 hours
    else:
        ttl = 300  # 5 minutes
    
    await cache_manager.set(f"vuln:{vuln_id}", vuln, ttl=ttl)
    return vuln
```

---

## Invalidation

### Single Key Invalidation

```python
# After updating a vulnerability
await cache_manager.delete(f"vuln:{vuln_id}")
```

### Pattern-Based Invalidation

```python
# Clear all vulnerability caches
await cache_manager.invalidate_pattern("vuln:*")

# Clear specific user's caches
await cache_manager.invalidate_pattern(f"user:{user_id}:*")

# Clear statistics
await cache_manager.invalidate_pattern("stats:*")
```

### Cascading Invalidation

```python
async def invalidate_vulnerability_caches(vuln_id: int):
    """Invalidate vulnerability and related caches"""
    keys_to_delete = [
        f"vuln:{vuln_id}",
        f"vuln:patches:{vuln_id}",
        "stats:vulnerabilities:24h",
        "stats:vulnerabilities:7d",
    ]
    await cache_manager.delete(*keys_to_delete)
```

### Event-Based Invalidation

```python
# In your update function
async def update_vulnerability(vuln_id: int, data: dict):
    # Update database
    await db_update(vuln_id, data)
    
    # Trigger invalidation
    await invalidate_vulnerability_caches(vuln_id)
    
    # Publish event for other services
    await event_bus.publish("vulnerability.updated", {"id": vuln_id})
```

---

## Best Practices

### 1. Cache What's Expensive

**Good candidates:**
- Database aggregations/joins
- External API calls (NVD, scanner APIs)
- Complex computations
- Frequently accessed data

**Bad candidates:**
- Simple lookups by primary key (database is fast)
- Data that changes frequently
- User-specific data with low reuse

### 2. Set Appropriate TTLs

```python
# Too short - cache thrashing
@cache(ttl=10)  # Bad for stable data

# Too long - stale data
@cache(ttl=86400)  # Bad for changing data

# Just right
@cache(ttl=300)  # 5 minutes for dynamic data
@cache(ttl=3600)  # 1 hour for stable data
```

### 3. Handle Cache Failures Gracefully

```python
async def get_data(key: str):
    try:
        # Try cache
        data = await cache_manager.get(key)
        if data:
            return data
    except Exception as e:
        logger.warning(f"Cache error: {e}")
        # Fall through to database
    
    # Fetch from database
    data = await db_fetch(key)
    
    # Try to cache (but don't fail if it doesn't work)
    try:
        await cache_manager.set(key, data, ttl=300)
    except Exception:
        pass
    
    return data
```

### 4. Avoid Cache Stampede

**Problem:** Many requests hit cache miss simultaneously, overwhelming database.

**Solution: Use locking**

```python
import asyncio

locks = {}

async def get_with_lock(key: str):
    # Check cache
    data = await cache_manager.get(key)
    if data:
        return data
    
    # Acquire lock for this key
    if key not in locks:
        locks[key] = asyncio.Lock()
    
    async with locks[key]:
        # Double-check cache (another request may have filled it)
        data = await cache_manager.get(key)
        if data:
            return data
        
        # Fetch from database (only one request does this)
        data = await db_fetch(key)
        await cache_manager.set(key, data, ttl=300)
        
        return data
```

### 5. Monitor Cache Performance

```python
# Track cache hit rate
hit_rate = cache_hits / (cache_hits + cache_misses) * 100

# Aim for > 80% hit rate for frequently accessed data
# Aim for > 50% hit rate for general caching
```

---

## Monitoring

### Prometheus Metrics

View in Grafana:
- `cache_hits_total` - Total cache hits
- `cache_misses_total` - Total cache misses
- `cache_operation_duration_seconds` - Operation latency
- `cache_keys_total` - Number of keys in cache
- `cache_memory_bytes` - Memory usage

### Calculate Hit Rate

```promql
# Cache hit rate percentage
sum(rate(cache_hits_total[5m])) / 
(sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m]))) * 100
```

### Redis Memory Usage

```python
# Get memory info
client = await get_redis_client()
info = await client.info('memory')
print(f"Used memory: {info['used_memory_human']}")
print(f"Peak memory: {info['used_memory_peak_human']}")
```

### Key Statistics

```bash
# Via Redis CLI
redis-cli INFO stats
redis-cli DBSIZE
redis-cli MEMORY STATS
```

---

## Common Patterns

### Caching API Responses

```python
@cache(ttl=timedelta(hours=1), prefix="nvd_api")
async def get_cve_from_nvd(cve_id: str):
    """Cache expensive NVD API calls"""
    response = await httpx.get(f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}")
    return response.json()
```

### Caching Aggregations

```python
@cache(ttl=300, prefix="stats")
async def get_vulnerability_statistics():
    """Cache expensive database aggregations"""
    return {
        "total": await db.query(func.count(Vulnerability.id)).scalar(),
        "by_severity": await db.query(
            Vulnerability.severity,
            func.count(Vulnerability.id)
        ).group_by(Vulnerability.severity).all(),
        "critical_count": await db.query(func.count(Vulnerability.id))
            .filter(Vulnerability.severity == "critical").scalar(),
    }
```

### Rate Limiting with Cache

```python
async def check_rate_limit(user_id: int, limit: int = 100):
    """Simple rate limiting using Redis"""
    import time
    current_minute = int(time.time() / 60)
    key = f"rate_limit:{user_id}:{current_minute}"
    
    count = await cache_manager.increment(key, 1)
    
    # Set expiration on first request
    if count == 1:
        await cache_manager.expire(key, 60)
    
    if count > limit:
        raise RateLimitExceeded(f"Rate limit exceeded: {count}/{limit}")
    
    return count
```

### Session Management

```python
async def create_session(user_id: int, data: dict):
    """Store user session in Redis"""
    import uuid
    session_id = str(uuid.uuid4())
    
    await cache_manager.set(
        f"session:{session_id}",
        {"user_id": user_id, **data},
        ttl=7200  # 2 hours
    )
    
    return session_id

async def get_session(session_id: str):
    """Retrieve session"""
    return await cache_manager.get(f"session:{session_id}")

async def destroy_session(session_id: str):
    """Destroy session"""
    await cache_manager.delete(f"session:{session_id}")
```

---

## Troubleshooting

### Low Hit Rate

**Possible causes:**
1. TTL too short
2. Cache stampede
3. Unique queries (not cacheable)
4. Keys not matching (check key generation)

**Solutions:**
- Increase TTL for stable data
- Implement locking for stampede
- Don't cache unique queries
- Use consistent key generation

### Memory Issues

**Redis using too much memory:**

```python
# Check memory
info = await client.info('memory')
print(info['used_memory_human'])

# Clear all caches (careful!)
await client.flushdb()

# Or clear specific patterns
await cache_manager.invalidate_pattern("old_data:*")
```

**Configure maxmemory policy:**
```bash
# In redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru  # Evict least recently used
```

---

## Further Reading

- [Redis Documentation](https://redis.io/documentation)
- [Caching Strategies](https://redis.io/docs/manual/patterns/caching/)
- [Cache Stampede Solutions](https://redis.io/docs/manual/patterns/distributed-locks/)

---

**Maintained by:** VulnZero DevOps Team
**Questions?** See caching team in Slack #vulnzero-caching
