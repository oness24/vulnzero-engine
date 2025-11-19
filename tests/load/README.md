# k6 Load Testing Suite

Comprehensive performance testing for the VulnZero API using [k6](https://k6.io/).

## 📋 Test Files

### `auth.js` - Authentication Load Test
Tests login endpoint performance with multiple load patterns:
- **Baseline**: 10 concurrent users for 2 minutes
- **Spike**: Sudden increase to 100 users
- **Stress**: Gradual ramp-up to 200 users

**SLA**: 95% of requests under 500ms, 99% under 1s

### `deployments.js` - Deployment Endpoint Test
Simulates realistic deployment workloads:
- **Normal Operations**: 5-10 concurrent users
- **Peak Hours**: 20 concurrent users

Tests the full deployment workflow:
1. Trigger deployment
2. Check task status
3. List deployments

**SLA**: 95% under 2s for deployments, 95% under 200ms for task status

### `scans.js` - Vulnerability Scan Test
Tests scan endpoint with rate limiting respect:
- **Compliant Scanning**: 4 scans/hour (under 5/hour limit)
- **Rate Limit Test**: Validates rate limiting behavior

**SLA**: 95% under 3s, graceful handling of rate limits

### `comprehensive.js` - Full System Test
Simulates real user behavior for 30 minutes:
- **Normal Users**: 10-30 concurrent users with realistic actions
- **Monitoring Agents**: 5 continuous polling users

User actions:
- 30% trigger deployments
- 10% trigger scans
- 60% browse/monitor

**SLA**: 95% under 1s overall, per-endpoint SLAs enforced

## 🚀 Prerequisites

### Install k6

**macOS**:
```bash
brew install k6
```

**Linux** (Debian/Ubuntu):
```bash
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
  --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | \
  sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

**Windows** (using Chocolatey):
```powershell
choco install k6
```

**Docker**:
```bash
docker pull grafana/k6:latest
```

### Prepare Test Environment

1. **Start API Gateway**:
   ```bash
   docker-compose up api-gateway postgres redis
   ```

2. **Create Test Data**:
   ```bash
   # Create test user
   python scripts/create_test_user.py

   # Add sample assets and patches
   python scripts/seed_test_data.py
   ```

3. **Verify API is Running**:
   ```bash
   curl http://localhost:8000/api/v1/system/health
   ```

## 🎯 Running Tests

### Quick Start

```bash
# Test authentication performance
k6 run tests/load/auth.js

# Test deployment workflow
k6 run tests/load/deployments.js

# Test vulnerability scanning
k6 run tests/load/scans.js

# Run comprehensive system test
k6 run tests/load/comprehensive.js
```

### With Environment Variables

```bash
# Customize base URL
k6 run --env BASE_URL=http://localhost:8000 tests/load/auth.js

# Use existing API token (skip authentication)
k6 run --env API_TOKEN=your_token_here tests/load/deployments.js

# Specify test credentials
k6 run \
  --env TEST_EMAIL=admin@example.com \
  --env TEST_PASSWORD=SecurePassword123! \
  tests/load/comprehensive.js

# Choose scanner type
k6 run --env SCANNER_TYPE=qualys tests/load/scans.js
```

### Using Docker

```bash
# Run test in container
docker run --rm -v $(pwd):/tests grafana/k6:latest run /tests/tests/load/auth.js

# With environment variables
docker run --rm \
  -v $(pwd):/tests \
  -e BASE_URL=http://host.docker.internal:8000 \
  grafana/k6:latest run /tests/tests/load/auth.js
```

## 📊 Output Formats

### Console Output (Default)
Real-time metrics displayed in terminal:
```
✓ status is 200
✓ has access token
✓ response time < 500ms

checks.........................: 100.00% ✓ 1500  ✗ 0
http_req_duration..............: avg=245ms min=120ms med=230ms max=980ms p(95)=380ms p(99)=650ms
```

### HTML Report
```bash
# Generate HTML report
k6 run --out json=results.json tests/load/auth.js

# Convert to HTML (requires k6-reporter)
k6-reporter results.json --output report.html
```

### InfluxDB + Grafana
```bash
# Send metrics to InfluxDB
k6 run --out influxdb=http://localhost:8086/k6 tests/load/comprehensive.js

# View in Grafana at http://localhost:3000
```

### Cloud (k6 Cloud)
```bash
# Upload results to k6 Cloud
k6 cloud tests/load/comprehensive.js

# Get shareable URL with detailed analysis
```

## 🔧 Configuration Options

### Adjusting Load Levels

Edit the `options` object in test files:

```javascript
export const options = {
  scenarios: {
    my_scenario: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 20 },   // Ramp to 20 users
        { duration: '5m', target: 20 },   // Stay at 20
        { duration: '1m', target: 0 },    // Ramp down
      ],
    },
  },
  thresholds: {
    'http_req_duration': ['p(95)<500'],  // 95% under 500ms
    'http_req_failed': ['rate<0.01'],    // <1% failure rate
  },
};
```

### Available Executors

- **constant-vus**: Fixed number of users
  ```javascript
  { executor: 'constant-vus', vus: 10, duration: '5m' }
  ```

- **ramping-vus**: Gradually increase/decrease users
  ```javascript
  {
    executor: 'ramping-vus',
    stages: [
      { duration: '2m', target: 50 },
      { duration: '5m', target: 50 },
    ]
  }
  ```

- **constant-arrival-rate**: Fixed request rate
  ```javascript
  {
    executor: 'constant-arrival-rate',
    rate: 100,           // 100 requests
    timeUnit: '1s',      // per second
    duration: '10m',
  }
  ```

## 📈 Interpreting Results

### Key Metrics

| Metric | Description | Good Target |
|--------|-------------|-------------|
| `http_req_duration` | Request latency | p95 < 500ms |
| `http_req_failed` | Failed request rate | < 1% |
| `http_reqs` | Requests per second | Depends on capacity |
| `vus` | Virtual users active | As configured |
| `iterations` | Completed test cycles | - |

### Percentiles (p95, p99)

- **p95**: 95% of requests faster than this
- **p99**: 99% of requests faster than this
- Focus on p95/p99, not average (hides tail latency)

### Checks vs Thresholds

- **Checks**: Validate response correctness (doesn't fail test)
- **Thresholds**: Pass/fail criteria (fails test if not met)

```javascript
// Check (validation only)
check(response, {
  'status is 200': (r) => r.status === 200,
});

// Threshold (enforces SLA)
thresholds: {
  'http_req_duration': ['p(95)<500'],  // FAILS test if exceeded
}
```

## 🐛 Troubleshooting

### Test Fails with Connection Errors

**Problem**: `connection refused` or `timeout`

**Solution**:
1. Verify API is running: `curl http://localhost:8000/api/v1/system/health`
2. Check BASE_URL: `--env BASE_URL=http://localhost:8000`
3. Use `host.docker.internal` if running in Docker

### Authentication Failures

**Problem**: 401 Unauthorized errors

**Solution**:
1. Create test user: `python scripts/create_test_user.py`
2. Verify credentials: `--env TEST_EMAIL=user@example.com`
3. Check token expiration (default 24 hours)

### Rate Limiting Errors (429)

**Problem**: Too many 429 responses in scan test

**Solution**: This is expected! The scan endpoint is rate-limited to 5/hour. The test validates this behavior.

### High Failure Rate

**Problem**: `http_req_failed` > 5%

**Solution**:
1. Check API logs for errors
2. Verify database/Redis are running
3. Reduce load (lower VU count)
4. Check resource limits (CPU, memory)

### Slow Response Times

**Problem**: p95 latency exceeds thresholds

**Solution**:
1. Check database query performance
2. Review API logs for slow endpoints
3. Monitor CPU/memory usage
4. Consider increasing resources
5. Profile hot code paths

## 📚 Best Practices

### Load Testing Strategy

1. **Start Small**: Begin with auth.js to verify setup
2. **Increase Gradually**: Move to deployments.js
3. **Full System**: Run comprehensive.js
4. **Monitor Resources**: Watch CPU, memory, database
5. **Iterate**: Optimize and re-test

### Test Data Management

- Use **isolated test database** (not production!)
- Create **sufficient test data** (100+ assets, patches)
- **Clean up** after tests to avoid bloat
- Use **realistic data sizes** (mimic production)

### Performance Targets

Set SLAs based on user expectations:

| Operation | Target Latency | Priority |
|-----------|----------------|----------|
| Authentication | p95 < 400ms | High |
| List Assets | p95 < 500ms | High |
| Deploy Patch | p95 < 2s | Medium |
| Scan Trigger | p95 < 3s | Medium |
| Task Status | p95 < 200ms | High |

### Continuous Testing

Integrate into CI/CD:

```yaml
# .github/workflows/performance.yml
- name: Run k6 Performance Tests
  run: |
    k6 run --quiet tests/load/auth.js
    k6 run --quiet tests/load/deployments.js
```

Run weekly comprehensive tests:
```bash
# Cron job
0 2 * * 1 k6 run tests/load/comprehensive.js --out json=results.json
```

## 🔗 Resources

- [k6 Documentation](https://k6.io/docs/)
- [k6 Examples](https://k6.io/docs/examples/)
- [k6 Cloud](https://k6.io/cloud/)
- [Grafana k6 GitHub](https://github.com/grafana/k6)

## 🎯 Next Steps

After running load tests:

1. **Analyze Results**: Review metrics and identify bottlenecks
2. **Optimize Code**: Address slow endpoints
3. **Re-test**: Verify improvements
4. **Set Baselines**: Document acceptable performance ranges
5. **Monitor Production**: Compare production metrics to test results
6. **Alert on Degradation**: Set up monitoring for performance regression

## 📞 Support

For questions about load testing:
1. Check k6 documentation
2. Review test script comments
3. Analyze k6 output carefully
4. Consult with performance team
