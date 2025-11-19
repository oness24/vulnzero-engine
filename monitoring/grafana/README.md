# VulnZero Grafana Dashboards

This directory contains Grafana dashboards for monitoring VulnZero application metrics.

## Dashboards

### 1. System Overview (`system-overview.json`)

High-level system health and performance dashboard.

**Panels:**
- HTTP Requests per Second - Request rate by endpoint/method
- API Response Time - p95 and p50 latency
- Total Requests - Counter
- Error Rate % - 5xx errors as percentage
- Active Requests - Current in-flight requests
- DB Connection Pool - Database connections in use
- Celery Workers - Number of active workers
- Cache Hit Rate % - Redis cache effectiveness
- Database Query Duration - p95 query latency by operation
- Celery Task Duration - p95 task execution time

**Use Cases:**
- Quick system health check
- Performance at-a-glance
- Incident response
- Capacity planning

**Refresh:** 10 seconds

---

### 2. Business Metrics (`business-metrics.json`)

Business KPIs and vulnerability management metrics.

**Panels:**
- Active Vulnerabilities - Total unresolved vulnerabilities
- Critical Vulnerabilities - High-priority vulns requiring immediate attention
- Patches Generated (24h) - Patch generation rate
- Deployments (24h) - Successful deployments
- Vulnerabilities Detected per Hour - Detection rate by severity
- Vulnerabilities Remediated per Hour - Remediation rate by severity/method
- Time to Remediation - p95 time from detection to fix
- Patch Generation Duration - LLM API latency
- Deployment Success Rate - Deployment reliability
- LLM API Calls - AI service usage

**Use Cases:**
- Track vulnerability management effectiveness
- Monitor AI-powered patching performance
- Measure MTTR (Mean Time To Remediation)
- Validate business objectives

**Refresh:** 30 seconds

---

## Setup

### Option 1: Automatic Provisioning (Recommended)

Dashboards are automatically loaded when using Docker Compose:

```yaml
# docker-compose.yml (already configured)
grafana:
  volumes:
    - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
    - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources:ro
```

Dashboards will be available immediately after Grafana starts.

### Option 2: Manual Import

1. Open Grafana UI (http://localhost:3001)
2. Login (admin/admin by default)
3. Navigate to Dashboards → Import
4. Upload JSON file or paste JSON content
5. Select Prometheus datasource
6. Click Import

## Accessing Dashboards

**Production:**
- URL: `https://grafana.vulnzero.example.com`
- Credentials: See `.env.production` (GRAFANA_ADMIN_USER/PASSWORD)

**Staging:**
- URL: `http://localhost:3002` (or staging domain)
- Credentials: See `.env.staging`

**Local Development:**
- URL: `http://localhost:3001`
- Default: admin/admin (change on first login)

## Prometheus Datasource

Configure Prometheus datasource:

1. Navigate to Configuration → Data Sources
2. Add Prometheus datasource
3. URL: `http://prometheus:9090` (Docker internal)
4. Access: Server (default)
5. Save & Test

Or use automatic provisioning (see `datasources/prometheus.yml`).

## Customization

### Adding Panels

1. Edit dashboard JSON files
2. Or use Grafana UI:
   - Click "Add Panel"
   - Select visualization type
   - Write PromQL query
   - Configure display options
   - Save dashboard
   - Export JSON (for version control)

### Common PromQL Queries

**Request Rate:**
```promql
rate(vulnzero_http_requests_total[5m])
```

**Error Rate:**
```promql
sum(rate(vulnzero_http_requests_total{status_code=~"5.."}[5m])) 
/ sum(rate(vulnzero_http_requests_total[5m])) * 100
```

**p95 Latency:**
```promql
histogram_quantile(0.95, 
  rate(vulnzero_http_request_duration_seconds_bucket[5m]))
```

**Cache Hit Ratio:**
```promql
sum(rate(vulnzero_cache_hits_total[5m])) / 
(sum(rate(vulnzero_cache_hits_total[5m])) + 
 sum(rate(vulnzero_cache_misses_total[5m]))) * 100
```

## Alerts

Configure alerts in Grafana or Prometheus:

**Example Alert Rules:**

1. **High Error Rate**
   - Condition: Error rate > 5% for 5 minutes
   - Severity: Critical
   - Action: Page on-call

2. **Slow Response Time**
   - Condition: p95 latency > 1s for 10 minutes
   - Severity: Warning
   - Action: Slack notification

3. **Critical Vulnerabilities**
   - Condition: Critical vulnerabilities > 0
   - Severity: High
   - Action: Email + Slack

4. **Database Connection Pool Exhaustion**
   - Condition: Checked out connections > 18
   - Severity: Critical
   - Action: Auto-scale or alert

5. **Worker Outage**
   - Condition: Active workers < 1
   - Severity: Critical
   - Action: Restart workers + page on-call

## Troubleshooting

**Dashboard not loading:**
- Check Grafana logs: `docker-compose logs grafana`
- Verify JSON syntax: `cat dashboard.json | jq .`
- Check file permissions

**No data in panels:**
- Verify Prometheus is scraping metrics: `curl http://localhost:9090/targets`
- Check /metrics endpoint: `curl http://localhost:8000/api/v1/system/metrics`
- Verify time range in dashboard (top-right)

**Queries timing out:**
- Reduce time range
- Increase Prometheus query timeout
- Optimize PromQL queries
- Add indexes to Prometheus (if using long retention)

## Best Practices

1. **Consistent Labels:**
   - Use same label names across metrics
   - Follow naming convention: `vulnzero_<component>_<metric>_<unit>`

2. **Histograms for Latency:**
   - Use histograms (not gauges) for duration metrics
   - Enables p50, p95, p99 calculations
   - Better for percentile-based SLOs

3. **Counters for Rates:**
   - Use counters for cumulative values
   - Calculate rates with `rate()` or `irate()`

4. **Gauge for Current State:**
   - Use gauges for values that go up and down
   - Examples: active connections, queue length

5. **Dashboard Organization:**
   - Most critical metrics at top
   - Group related panels
   - Use consistent colors for severity
   - Add descriptions/tooltips

## Metrics Reference

See `/shared/monitoring/metrics.py` for complete list of available metrics.

**Categories:**
- HTTP: Request count, duration, errors
- Database: Queries, connections, latency
- Cache: Hits, misses, memory
- Business: Vulnerabilities, patches, deployments
- Celery: Tasks, workers, queues
- LLM: API calls, tokens, duration

## Further Reading

- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [Prometheus Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/best-practices-for-creating-dashboards/)
- [Alerting Guide](https://grafana.com/docs/grafana/latest/alerting/)

---

**Created:** 2025-11-19
**Version:** 1.0.0
**Maintainer:** VulnZero DevOps Team
