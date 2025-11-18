# VulnZero Performance Optimization Guide

**Last Updated**: 2025-11-18
**Status**: Production-ready

---

## Overview

This guide documents all performance optimizations implemented in VulnZero and provides guidelines for maintaining optimal performance.

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| API P95 Response Time | < 500ms | ✅ Optimized |
| API P99 Response Time | < 1000ms | ✅ Optimized |
| Health Check Response | < 50ms | ✅ Optimized |
| Database Query Time | < 100ms | ✅ Optimized |
| Concurrent Users | 100+ | ✅ Supported |
| Throughput | > 100 req/s | ✅ Achieved |
| Error Rate | < 1% | ✅ Maintained |

---

## 1. Response Compression

### Implementation

**File**: `api/main.py`

```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(
    GZipMiddleware,
    minimum_size=1000,  # Only compress responses > 1KB
    compresslevel=6,    # Balance between compression ratio and speed
)
```

### Benefits

- **Bandwidth Reduction**: 60-80% smaller payloads for JSON responses
- **Faster Transfer**: Reduced network transfer time
- **Cost Savings**: Lower bandwidth costs in production

### Configuration

- **minimum_size**: `1000 bytes` - Don't compress tiny responses (overhead > benefit)
- **compresslevel**: `6` - Good balance (1=fastest/least compression, 9=slowest/most compression)

---

## 2. Database Query Optimization

### Query Optimization Module

**File**: `shared/database/query_optimization.py`

Provides utilities for:
- Eager loading to prevent N+1 queries
- Batch operations
- Paginated queries
- Query performance monitoring

### Preventing N+1 Queries

**Bad (N+1 Query Problem)**:
```python
# Fetches vulnerabilities
vulnerabilities = await session.execute(select(Vulnerability))

# Then makes N additional queries for patches
for vuln in vulnerabilities:
    patches = vuln.patches  # Triggers separate query!
```

**Good (Eager Loading)**:
```python
from shared.database.query_optimization import QueryOptimizer

# Single query with JOIN
query = QueryOptimizer.with_relationships(
    Vulnerability,
    'patches',
    'asset_vulnerabilities'
)
result = await session.execute(query)
vulnerabilities = result.scalars().all()

# No additional queries needed
for vuln in vulnerabilities:
    patches = vuln.patches  # Already loaded!
```

### Batch Operations

```python
# Fetch multiple records efficiently
vulnerabilities = await QueryOptimizer.batch_get_by_ids(
    session,
    Vulnerability,
    ids=[1, 2, 3, ..., 1000],
    batch_size=100  # Processes in chunks
)
```

### Pagination

```python
# Efficient pagination
query = select(Vulnerability).where(Vulnerability.severity == "critical")
results, total_count = await QueryOptimizer.paginated_query(
    session,
    query,
    page=1,
    page_size=50
)
```

### Query Performance Monitoring

```python
from shared.database.query_optimization import monitor_query_performance

@monitor_query_performance(threshold_ms=100.0)
async def get_critical_vulnerabilities(session):
    # Logs warning if query takes > 100ms
    result = await session.execute(
        select(Vulnerability).where(Vulnerability.severity == "critical")
    )
    return result.scalars().all()
```

---

## 3. Horizontal Pod Autoscaling (HPA)

### API Autoscaling

**File**: `infrastructure/kubernetes/hpa/api-hpa.yaml`

**Configuration**:
- **Min Replicas**: 3 (High availability)
- **Max Replicas**: 10 (Cost control)
- **CPU Target**: 70% utilization
- **Memory Target**: 80% utilization
- **Custom Metric**: 100 req/s per pod

**Scaling Behavior**:
- **Scale Up**: Aggressive (double capacity in 30s)
- **Scale Down**: Conservative (wait 5 min, reduce 50% max)

### Celery Worker Autoscaling

**File**: `infrastructure/kubernetes/hpa/celery-worker-hpa.yaml`

**Configuration**:
- **Min Replicas**: 2
- **Max Replicas**: 20 (Handle burst workloads)
- **CPU Target**: 75% utilization
- **Queue Length**: 50 tasks per worker
- **Active Tasks**: 4 per worker

**Scaling Behavior**:
- **Scale Up**: Very aggressive (triple capacity in 30s)
- **Scale Down**: Very conservative (wait 10 min)

### Frontend Autoscaling

**File**: `infrastructure/kubernetes/hpa/frontend-hpa.yaml`

**Configuration**:
- **Min Replicas**: 2
- **Max Replicas**: 6
- **CPU Target**: 60% utilization
- **Memory Target**: 75% utilization

---

## 4. Database Indexes

### Recommended Indexes

All indexes are defined in Alembic migrations.

**Vulnerabilities Table**:
```sql
CREATE INDEX idx_vulnerabilities_cve_id ON vulnerabilities(cve_id);
CREATE INDEX idx_vulnerabilities_severity ON vulnerabilities(severity);
CREATE INDEX idx_vulnerabilities_status ON vulnerabilities(status);
CREATE INDEX idx_vulnerabilities_priority_score ON vulnerabilities(priority_score);
CREATE INDEX idx_vulnerabilities_created_at ON vulnerabilities(created_at);
CREATE INDEX idx_vulnerabilities_severity_status ON vulnerabilities(severity, status);
```

**Assets Table**:
```sql
CREATE INDEX idx_assets_asset_id ON assets(asset_id);
CREATE INDEX idx_assets_hostname ON assets(hostname);
CREATE INDEX idx_assets_ip_address ON assets(ip_address);
CREATE INDEX idx_assets_is_active ON assets(is_active);
```

**Patches Table**:
```sql
CREATE INDEX idx_patches_patch_id ON patches(patch_id);
CREATE INDEX idx_patches_vulnerability_id ON patches(vulnerability_id);
CREATE INDEX idx_patches_validation_passed ON patches(validation_passed);
```

### Index Recommendations

Use the query optimization module:

```python
from shared.database.query_optimization import get_index_recommendations

indexes = get_index_recommendations("vulnerabilities")
for column, description in indexes:
    print(f"{column}: {description}")
```

---

## 5. Load Testing

### Locust Configuration

**File**: `tests/performance/locustfile.py`

### Running Load Tests

**Local Testing**:
```bash
# Install locust
pip install locust

# Run with web UI
locust -f tests/performance/locustfile.py --host=http://localhost:8000

# Access UI at http://localhost:8089
# Configure: 100 users, spawn rate 10/s, duration 60s
```

**Headless Testing**:
```bash
locust -f tests/performance/locustfile.py \
       --host=http://localhost:8000 \
       --users 100 \
       --spawn-rate 10 \
       --run-time 60s \
       --headless \
       --csv=results/load_test
```

### Test Scenarios

**VulnZeroUser** (Regular users - 80% of traffic):
- List vulnerabilities (50%)
- Get vulnerability details (30%)
- List assets (20%)
- List patches (20%)
- Create vulnerability (10%)
- Update vulnerability (10%)

**AdminUser** (Admin users - 20% of traffic):
- Generate patches
- Deploy patches
- View audit logs

### Performance Assertions

Locust automatically validates:
- ✅ P95 response time < 500ms
- ✅ Failure rate < 1%

---

## 6. Caching Strategy

### Redis Configuration

**Connection Pool**:
```python
# Reuse connections for better performance
redis_client = Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    connection_pool_max_connections=50,
    decode_responses=True,
)
```

### Cache Patterns

**Cache Frequently Read Data**:
```python
# Cache vulnerability by CVE ID
cache_key = f"vulnerability:{cve_id}"
cached = await redis.get(cache_key)

if cached:
    return json.loads(cached)

# Fetch from database
vulnerability = await get_from_db(cve_id)

# Cache for 5 minutes
await redis.setex(cache_key, 300, json.dumps(vulnerability))
```

**Cache Invalidation**:
```python
# Invalidate when data changes
await redis.delete(f"vulnerability:{cve_id}")
```

---

## 7. Connection Pooling

### Database Connection Pool

**Configuration** (`shared/database/session.py`):
```python
engine = create_async_engine(
    database_url,
    pool_size=20,           # Keep 20 connections open
    max_overflow=10,        # Allow 10 additional connections
    pool_pre_ping=True,     # Test connections before use
    pool_recycle=3600,      # Recycle connections after 1 hour
    echo=False,             # Disable SQL logging in production
)
```

### Redis Connection Pool

**Configuration**:
```python
redis_pool = ConnectionPool(
    host=settings.redis_host,
    port=settings.redis_port,
    max_connections=50,
    decode_responses=True,
)
```

---

## 8. Performance Monitoring

### Prometheus Metrics

Metrics are automatically exposed at `/metrics`:

**API Metrics**:
- `vulnzero_http_requests_total` - Total HTTP requests
- `vulnzero_request_duration_seconds` - Request duration histogram
- `vulnzero_http_requests_in_progress` - Active requests

**Database Metrics**:
- `vulnzero_db_connections_active` - Active database connections
- `vulnzero_db_query_duration_seconds` - Query duration

**Celery Metrics**:
- `celery_tasks_total` - Total tasks processed
- `celery_queue_length` - Current queue depth
- `celery_workers_active` - Active workers

### Grafana Dashboards

Performance dashboards available:
- **Application Metrics**: Request rates, response times, errors
- **Database Performance**: Query times, connection pool, cache hit ratio
- **Celery Monitoring**: Task rates, queue depth, worker status

---

## 9. Performance Testing

### Automated Tests

**File**: `tests/performance/test_api_performance.py`

Run performance tests:
```bash
pytest tests/performance/ -v
```

**Test Categories**:
- API response time tests (p95 < 500ms)
- Concurrent request handling (50 concurrent requests)
- Database query performance (N+1 prevention)
- Memory efficiency tests
- Cache effectiveness tests

---

## 10. Best Practices

### Backend Optimization

✅ **Always use eager loading for relationships**
```python
query = QueryOptimizer.with_relationships(Vulnerability, 'patches')
```

✅ **Paginate large result sets**
```python
results, total = await QueryOptimizer.paginated_query(session, query, page=1, page_size=50)
```

✅ **Use batch operations**
```python
await QueryOptimizer.batch_get_by_ids(session, Vulnerability, ids)
```

✅ **Monitor slow queries**
```python
@monitor_query_performance(threshold_ms=100.0)
async def my_query_function():
    ...
```

✅ **Cache frequently accessed data**
```python
await redis.setex(cache_key, ttl=300, value=data)
```

### Database Best Practices

✅ **Use database indexes** on frequently queried columns
✅ **Avoid SELECT *** - select only needed columns
✅ **Use LIMIT/OFFSET** for pagination
✅ **Batch INSERT/UPDATE** operations
✅ **Use connection pooling**

### API Best Practices

✅ **Enable response compression** (GZip)
✅ **Implement rate limiting** (already configured)
✅ **Use async endpoints** (FastAPI default)
✅ **Return 304 Not Modified** for cached responses
✅ **Implement field filtering** (e.g., ?fields=id,name)

---

## 11. Troubleshooting

### Slow API Responses

**Check**:
1. Grafana dashboard for P95/P99 response times
2. Slow query logs in application logs
3. Database connection pool exhaustion
4. High CPU/memory usage (scale up)

**Solutions**:
- Add database indexes
- Enable query caching
- Increase HPA max replicas
- Optimize N+1 queries

### High Memory Usage

**Check**:
1. Memory metrics in Grafana
2. Pod memory limits vs usage
3. Memory leaks in application logs

**Solutions**:
- Increase memory limits
- Scale horizontally instead of vertically
- Implement pagination
- Clear old cache entries

### Database Connection Exhaustion

**Symptoms**:
- `FATAL: remaining connection slots are reserved`
- High connection count in pg_stat_activity

**Solutions**:
- Increase `pool_size` in database config
- Increase PostgreSQL `max_connections`
- Check for connection leaks
- Use connection pooling (already enabled)

---

## 12. Production Checklist

✅ Response compression enabled (GZip)
✅ Database indexes created
✅ Connection pooling configured
✅ HPA configured for all services
✅ Query optimization implemented
✅ Performance monitoring enabled
✅ Load testing completed
✅ Slow query alerts configured
✅ Cache strategy implemented
✅ Rate limiting enabled

---

## 13. Performance Roadmap

### Completed ✅
- Response compression (GZip)
- Database query optimization
- Horizontal pod autoscaling
- Connection pooling
- Performance monitoring
- Load testing infrastructure

### Future Enhancements 🔜
- CDN integration for static assets
- Database read replicas
- Query result caching layer (Redis)
- GraphQL for flexible queries
- Edge caching with CloudFlare
- WebSocket connection pooling

---

## References

- [FastAPI Performance](https://fastapi.tiangolo.com/advanced/middleware/)
- [SQLAlchemy Performance Tips](https://docs.sqlalchemy.org/en/20/faq/performance.html)
- [Kubernetes HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Locust Documentation](https://docs.locust.io/)

---

**Last Updated**: 2025-11-18
**Maintained By**: VulnZero Team
