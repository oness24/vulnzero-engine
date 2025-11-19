# Database Optimization Guide

**Last Updated:** 2025-11-19
**Version:** 1.0.0

## Overview

This guide covers database optimization strategies, query patterns, and performance best practices for VulnZero.

---

## Table of Contents

- [Indexes](#indexes)
- [Query Optimization](#query-optimization)
- [Bulk Operations](#bulk-operations)
- [N+1 Query Prevention](#n1-query-prevention)
- [Connection Pooling](#connection-pooling)
- [Performance Monitoring](#performance-monitoring)
- [Best Practices](#best-practices)

---

## Indexes

### Existing Indexes

Our models have comprehensive indexing on frequently queried fields:

**Vulnerabilities:**
```python
# Single column indexes
- cve_id (non-unique, allows multiple assets with same CVE)
- severity
- priority_score
- status
- discovered_at
- remediated_at
- affected_package
- scanner_source

# Composite indexes
- (status, severity) - For filtering by both
- (status, priority_score) - For prioritized queues
- (discovered_at, status) - For time-based queries
- (cve_id, scanner_source) - For scanner correlation
```

**Assets:**
```python
# Single column indexes
- asset_id (unique)
- type
- status
- hostname
- ip_address
- os_type
- cloud_provider
- environment
- is_public_facing
- last_scanned

# Composite indexes
- (type, status) - For asset inventory
- (environment, criticality) - For risk assessment
- (os_type, os_version) - For patch compatibility
- (is_public_facing, environment) - For security audits
```

**Patches:**
```python
# Single column indexes
- vulnerability_id (foreign key)
- patch_type
- status
- confidence_score
- test_status

# Composite indexes
- (vulnerability_id, status) - For patch tracking
- (patch_type, status) - For patch inventory
- (confidence_score, status) - For quality filtering
- (test_status, status) - For test results
```

### When to Add Indexes

**Do add indexes when:**
- Column appears in WHERE clauses frequently
- Column used in ORDER BY
- Column used in JOINs
- Column used in GROUP BY
- Query is slow and EXPLAIN shows sequential scan

**Don't add indexes when:**
- Table is very small (< 1000 rows)
- Column has low cardinality (few distinct values like boolean)
- Write-heavy table (indexes slow down INSERT/UPDATE)
- Index would be larger than the table

### Index Types

**B-Tree (Default):**
```sql
CREATE INDEX ix_vuln_priority ON vulnerabilities(priority_score);
```
Good for: Equality, range queries, sorting

**Partial Index:**
```sql
CREATE INDEX ix_active_vulns ON vulnerabilities(status) 
WHERE status IN ('new', 'analyzing', 'patch_generated');
```
Good for: Filtering frequently queried subset

**Composite Index:**
```sql
CREATE INDEX ix_vuln_status_severity ON vulnerabilities(status, severity);
```
Good for: Queries filtering on multiple columns

---

## Query Optimization

### Use QueryOptimizer Helper

Instead of raw SQLAlchemy queries, use the optimized helper:

**Before:**
```python
vulnerabilities = (
    db.query(Vulnerability)
    .filter(Vulnerability.status == "new")
    .filter(Vulnerability.severity == "critical")
    .order_by(Vulnerability.priority_score.desc())
    .limit(10)
    .all()
)
```

**After:**
```python
from shared.database import QueryOptimizer

optimizer = QueryOptimizer(Vulnerability, db)
vulnerabilities = (
    optimizer
    .filter_by(status="new", severity="critical")
    .order_by("priority_score", desc=True)
    .limit(10)
    .all()
)
```

### Efficient Pagination

**Bad (loads all records):**
```python
all_vulns = db.query(Vulnerability).all()
page = all_vulns[offset:offset+limit]  # Memory intensive!
```

**Good (uses LIMIT/OFFSET):**
```python
optimizer = QueryOptimizer(Vulnerability, db)
vulns, total = optimizer.paginate(page=2, page_size=20).all(), optimizer.count()
```

### Date Range Queries

**Use indexed BETWEEN:**
```python
from datetime import datetime, timedelta

cutoff = datetime.utcnow() - timedelta(days=7)

optimizer = QueryOptimizer(Vulnerability, db)
recent = optimizer.filter_date_range("discovered_at", start_date=cutoff).all()
```

### IN Queries

**Efficient for small sets:**
```python
statuses = ["new", "analyzing", "patch_generated"]
optimizer.filter_in("status", statuses).all()
```

---

## Bulk Operations

### Bulk Insert

**Bad (N separate INSERT statements):**
```python
for record in records:
    db.add(Vulnerability(**record))
    db.commit()  # Very slow!
```

**Good (batched inserts):**
```python
from shared.database import BulkQueryHelper

BulkQueryHelper.bulk_insert(
    session=db,
    model=Vulnerability,
    records=records,
    batch_size=500
)
db.commit()
```

### Bulk Update

```python
updates = [
    {"id": 1, "status": "remediated"},
    {"id": 2, "status": "remediated"},
    # ... many more
]

BulkQueryHelper.bulk_update(
    session=db,
    model=Vulnerability,
    updates=updates,
    batch_size=500
)
db.commit()
```

---

## N+1 Query Prevention

### The Problem

**Bad (N+1 queries):**
```python
vulnerabilities = db.query(Vulnerability).filter(...).all()  # 1 query

for vuln in vulnerabilities:  # N queries!
    for patch in vuln.patches:  # Loads patches one at a time
        print(patch.title)
```
This executes 1 + N queries where N = number of vulnerabilities.

### The Solution

**Good (2 queries total):**
```python
from shared.database import QueryOptimizer

optimizer = QueryOptimizer(Vulnerability, db)
vulnerabilities = (
    optimizer
    .filter_by(status="new")
    .eager_load("patches")  # Loads all patches in one query
    .all()
)

for vuln in vulnerabilities:  # No additional queries
    for patch in vuln.patches:
        print(patch.title)
```

### Eager Loading Strategies

**joinedload** - Single query with JOIN (use for one-to-one, small collections):
```python
from sqlalchemy.orm import joinedload

db.query(Vulnerability).options(joinedload(Vulnerability.patches)).all()
```

**selectinload** - Separate query with IN (use for large collections):
```python
from sqlalchemy.orm import selectinload

db.query(Vulnerability).options(selectinload(Vulnerability.patches)).all()
```

QueryOptimizer automatically chooses the right strategy!

---

## Connection Pooling

### Configuration

See `.env.production`:
```bash
DATABASE_POOL_SIZE=20          # Number of persistent connections
DATABASE_MAX_OVERFLOW=10       # Additional connections when pool full
DATABASE_POOL_TIMEOUT=30       # Seconds to wait for connection
DATABASE_POOL_RECYCLE=3600     # Recycle connections after 1 hour
```

### Best Practices

1. **Set appropriate pool size:**
   - Production: `pool_size = (2 * CPU_cores) + disk_drives`
   - Example: 4 cores + 1 SSD = pool_size of 10-20

2. **Monitor pool usage:**
   ```python
   from shared.config.database import engine
   
   pool = engine.pool
   print(f"Pool size: {pool.size()}")
   print(f"Checked out: {pool.checkedout()}")
   print(f"Overflow: {pool.overflow()}")
   ```

3. **Avoid connection leaks:**
   - Always use context managers
   - Close sessions in finally blocks
   - Use dependency injection in FastAPI

---

## Performance Monitoring

### Query Execution Plans

Use EXPLAIN to identify slow queries:

```python
from shared.database import explain_query
from sqlalchemy import select

query = select(Vulnerability).where(Vulnerability.status == "new")
plan = explain_query(db, query)
print(plan)
```

Look for:
- **Seq Scan** - Bad! Needs index
- **Index Scan** - Good!
- **Bitmap Heap Scan** - Good for multiple conditions
- **Cost** - Lower is better

### Slow Query Logging

Enable PostgreSQL slow query log:

```sql
-- In postgresql.conf
log_min_duration_statement = 1000  # Log queries > 1 second
```

### Prometheus Metrics

Monitor database performance:

```python
from shared.monitoring import (
    db_query_duration_seconds,
    db_slow_queries_total,
    db_pool_checked_out
)

# Track query duration
with MetricsContext(db_query_duration_seconds, {"operation": "select", "table": "vulns"}):
    results = db.query(Vulnerability).all()

# Check pool usage
db_pool_checked_out.set(engine.pool.checkedout())
```

---

## Best Practices

### 1. SELECT Only What You Need

**Bad:**
```python
vulns = db.query(Vulnerability).all()  # Loads ALL columns
```

**Good:**
```python
vulns = db.query(
    Vulnerability.id,
    Vulnerability.cve_id,
    Vulnerability.severity
).all()  # Loads only needed columns
```

### 2. Use Limit for Large Result Sets

**Always limit:**
```python
vulns = db.query(Vulnerability).order_by(Vulnerability.id.desc()).limit(100).all()
```

### 3. Avoid OR Conditions

**Slow (can't use indexes efficiently):**
```python
vulns = db.query(Vulnerability).filter(
    or_(
        Vulnerability.severity == "critical",
        Vulnerability.priority_score > 90
    )
).all()
```

**Faster (two separate indexed queries):**
```python
critical = db.query(Vulnerability).filter_by(severity="critical").all()
high_priority = db.query(Vulnerability).filter(Vulnerability.priority_score > 90).all()
results = list(set(critical + high_priority))
```

### 4. Use Exists for Existence Checks

**Bad (loads all data):**
```python
if len(db.query(Vulnerability).filter_by(cve_id="CVE-2024-1234").all()) > 0:
    ...
```

**Good (efficient check):**
```python
from shared.database import QueryOptimizer

optimizer = QueryOptimizer(Vulnerability, db)
if optimizer.filter_by(cve_id="CVE-2024-1234").exists():
    ...
```

### 5. Batch Database Operations

**Bad:**
```python
for vuln_id in vuln_ids:
    vuln = db.query(Vulnerability).get(vuln_id)  # N queries
```

**Good:**
```python
from shared.database import BulkQueryHelper

vulns = BulkQueryHelper.batch_fetch(db, Vulnerability, vuln_ids, batch_size=500)
```

### 6. Cache Frequently Accessed Data

Use Redis for:
- Reference data (CVE details, package versions)
- Computed values (risk scores, statistics)
- Query results that don't change often

See caching guide for details.

---

## Common Query Patterns

### Get Critical Vulnerabilities

```python
from shared.database import QueryPatterns

critical_vulns = QueryPatterns.get_by_status_with_priority(
    session=db,
    model=Vulnerability,
    status_values=["new", "analyzing"],
    min_priority=80.0,
    limit=50
)
```

### Get Recent Records

```python
recent_patches = QueryPatterns.get_recent_records(
    session=db,
    model=Patch,
    hours=24,
    limit=100
)
```

### Paginated Results with Count

```python
query = select(Vulnerability).where(Vulnerability.status == "new")

items, total = QueryPatterns.get_paginated_with_count(
    session=db,
    query=query,
    page=1,
    page_size=20
)
```

### Text Search

```python
results = QueryPatterns.search_by_text(
    session=db,
    model=Vulnerability,
    search_fields=["cve_id", "title", "description"],
    search_term="privilege escalation",
    limit=50
)
```

---

## Troubleshooting

### Query is Slow

1. Check EXPLAIN plan:
   ```python
   plan = explain_query(db, query)
   ```

2. Look for missing indexes:
   - Sequential scans on large tables
   - High cost values

3. Add index:
   ```python
   # In model
   Index("ix_custom", "column1", "column2")
   ```

4. Re-run EXPLAIN to verify improvement

### Connection Pool Exhausted

**Error:** "QueuePool limit of size X overflow X reached"

**Solutions:**
1. Increase pool size:
   ```python
   DATABASE_POOL_SIZE=30
   DATABASE_MAX_OVERFLOW=20
   ```

2. Find connection leaks:
   ```python
   print(f"Checked out: {engine.pool.checkedout()}")
   # Should be 0 when idle
   ```

3. Ensure sessions are closed:
   ```python
   try:
       result = db.query(...).all()
   finally:
       db.close()
   ```

### High Database CPU

1. Enable slow query log
2. Identify expensive queries
3. Add indexes or optimize queries
4. Consider read replicas for read-heavy workloads

---

## Database Maintenance

### Vacuum

PostgreSQL requires periodic vacuuming:

```sql
-- Auto-vacuum is enabled by default, but can manually run:
VACUUM ANALYZE vulnerabilities;
```

### Reindex

Rebuild indexes periodically:

```sql
REINDEX TABLE vulnerabilities;
```

### Statistics

Update query planner statistics:

```sql
ANALYZE vulnerabilities;
```

### Disk Space

Monitor table and index sizes:

```sql
SELECT
    relname AS table_name,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

---

## Further Reading

- [PostgreSQL Performance Tuning](https://www.postgresql.org/docs/current/performance-tips.html)
- [SQLAlchemy ORM Tutorial](https://docs.sqlalchemy.org/en/20/orm/tutorial.html)
- [Understanding EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html)
- [Index Types](https://www.postgresql.org/docs/current/indexes-types.html)

---

**Maintained by:** VulnZero DevOps Team
**Questions?** See database team in Slack #vulnzero-database
