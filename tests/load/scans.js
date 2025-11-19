/**
 * k6 Load Test - Vulnerability Scan Endpoint
 *
 * Tests the /api/v1/vulnerabilities/scan endpoint performance
 * Respects rate limiting (5 requests per hour per IP)
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const scanFailureRate = new Rate('scan_failures');
const scanDuration = new Trend('scan_duration');
const scanCount = new Counter('scans_triggered');
const rateLimitHits = new Counter('rate_limit_hits');
const vulnerabilityCount = new Counter('vulnerabilities_found');

// Test configuration
export const options = {
  scenarios: {
    // Low-rate scanning (respecting 5/hour rate limit)
    compliant_scanning: {
      executor: 'constant-arrival-rate',
      rate: 4,  // 4 scans per hour (under the 5/hour limit)
      timeUnit: '1h',
      duration: '5m',
      preAllocatedVUs: 2,
      maxVUs: 5,
      tags: { scenario: 'compliant' },
    },
    // Test rate limiting behavior
    rate_limit_test: {
      executor: 'constant-vus',
      vus: 1,
      duration: '30s',
      startTime: '6m',
      tags: { scenario: 'rate_limit_test' },
    },
  },

  thresholds: {
    'http_req_duration{endpoint:scan}': ['p(95)<3000', 'p(99)<10000'],
    'http_req_duration{endpoint:vulnerabilities_list}': ['p(95)<500'],
    'scan_failures{!rate_limited}': ['rate<0.05'],  // Exclude rate limit failures
  },
};

// Environment configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_TOKEN = __ENV.API_TOKEN || '';
const SCANNER_TYPE = __ENV.SCANNER_TYPE || 'wazuh';  // wazuh, qualys, tenable

export function setup() {
  console.log(`🚀 Starting vulnerability scan load test against ${BASE_URL}`);

  // Authenticate to get token
  let token = API_TOKEN;

  if (!token) {
    console.log('⚠️  No API_TOKEN provided, attempting authentication...');

    const authPayload = JSON.stringify({
      email: __ENV.TEST_EMAIL || 'test@example.com',
      password: __ENV.TEST_PASSWORD || 'TestPassword123!',
    });

    const authResponse = http.post(
      `${BASE_URL}/api/v1/auth/login`,
      authPayload,
      {
        headers: { 'Content-Type': 'application/json' },
      }
    );

    if (authResponse.status === 200) {
      const authData = JSON.parse(authResponse.body);
      token = authData.access_token;
      console.log('✅ Authentication successful');
    } else {
      console.error('❌ Authentication failed');
      throw new Error('Cannot authenticate');
    }
  }

  // Fetch available assets
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };

  const assetsResponse = http.get(`${BASE_URL}/api/v1/assets`, { headers });

  let assets = [];

  if (assetsResponse.status === 200) {
    assets = JSON.parse(assetsResponse.body);
    console.log(`✅ Found ${assets.length} assets`);
  }

  if (assets.length === 0) {
    console.warn('⚠️  No assets available for scanning');
  }

  return {
    baseUrl: BASE_URL,
    token: token,
    assets: assets,
    scanner: SCANNER_TYPE,
  };
}

export default function(data) {
  const headers = {
    'Authorization': `Bearer ${data.token}`,
    'Content-Type': 'application/json',
  };

  if (data.assets.length === 0) {
    console.warn('⚠️  Skipping scan - no assets available');
    sleep(10);
    return;
  }

  group('Vulnerability Scanning Workflow', () => {
    // Step 1: List existing vulnerabilities
    const listResponse = http.get(
      `${data.baseUrl}/api/v1/vulnerabilities?limit=20`,
      {
        headers: headers,
        tags: { endpoint: 'vulnerabilities_list' },
      }
    );

    check(listResponse, {
      'list status is 200': (r) => r.status === 200,
      'list has results': (r) => {
        try {
          const body = JSON.parse(r.body);
          const vulns = Array.isArray(body) ? body : (body.items || []);

          // Count vulnerabilities
          vulnerabilityCount.add(vulns.length);

          return Array.isArray(vulns);
        } catch (e) {
          return false;
        }
      },
      'list response time < 500ms': (r) => r.timings.duration < 500,
    });

    // Step 2: Trigger new scan
    const asset = data.assets[Math.floor(Math.random() * data.assets.length)];

    const scanPayload = JSON.stringify({
      asset_ids: [asset.id],
      scanner: data.scanner,
      scan_type: 'full',
    });

    const startTime = Date.now();
    const scanResponse = http.post(
      `${data.baseUrl}/api/v1/vulnerabilities/scan`,
      scanPayload,
      {
        headers: headers,
        tags: { endpoint: 'scan' },
      }
    );
    const duration = Date.now() - startTime;

    scanCount.add(1);
    scanDuration.add(duration);

    // Check if rate limited
    if (scanResponse.status === 429) {
      rateLimitHits.add(1);
      console.log('⚠️  Rate limit hit (expected for rate_limit_test scenario)');

      check(scanResponse, {
        'rate limit status is 429': (r) => r.status === 429,
        'rate limit has retry-after header': (r) =>
          r.headers['Retry-After'] !== undefined ||
          r.headers['retry-after'] !== undefined,
      });

      return; // Skip further checks for rate-limited requests
    }

    // Validate successful scan trigger
    const scanSuccess = check(scanResponse, {
      'scan status is 200/201/202': (r) =>
        r.status === 200 || r.status === 201 || r.status === 202,
      'scan has task_id': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.task_id !== undefined || body.id !== undefined;
        } catch (e) {
          return false;
        }
      },
      'scan response time < 3s': (r) => r.timings.duration < 3000,
    });

    if (!scanSuccess) {
      scanFailureRate.add(1, { rate_limited: false });
      console.error(`❌ Scan failed: ${scanResponse.status} - ${scanResponse.body}`);
      return;
    } else {
      scanFailureRate.add(0, { rate_limited: false });
    }

    // Extract task ID
    let taskId = null;
    try {
      const scanBody = JSON.parse(scanResponse.body);
      taskId = scanBody.task_id;
    } catch (e) {
      console.warn('⚠️  Could not extract task_id from scan response');
    }

    // Step 3: Check task status (if available)
    if (taskId) {
      sleep(2); // Brief delay before checking

      const statusResponse = http.get(
        `${data.baseUrl}/api/v1/tasks/${taskId}`,
        {
          headers: headers,
          tags: { endpoint: 'task_status' },
        }
      );

      check(statusResponse, {
        'task status is 200': (r) => r.status === 200,
        'task has state': (r) => {
          try {
            const body = JSON.parse(r.body);
            return body.state !== undefined;
          } catch (e) {
            return false;
          }
        },
      });

      // Log task state
      try {
        const statusBody = JSON.parse(statusResponse.body);
        console.log(`ℹ️  Scan task ${taskId} state: ${statusBody.state}`);
      } catch (e) {
        // Ignore parsing errors
      }
    }

    // Step 4: Get vulnerability details (for existing vulnerabilities)
    if (listResponse.status === 200) {
      try {
        const listBody = JSON.parse(listResponse.body);
        const vulns = Array.isArray(listBody) ? listBody : (listBody.items || []);

        if (vulns.length > 0) {
          const vuln = vulns[0];
          const detailResponse = http.get(
            `${data.baseUrl}/api/v1/vulnerabilities/${vuln.id}`,
            {
              headers: headers,
              tags: { endpoint: 'vulnerability_detail' },
            }
          );

          check(detailResponse, {
            'detail status is 200': (r) => r.status === 200,
            'detail has full data': (r) => {
              try {
                const body = JSON.parse(r.body);
                return body.id !== undefined && body.severity !== undefined;
              } catch (e) {
                return false;
              }
            },
          });
        }
      } catch (e) {
        console.warn('⚠️  Could not fetch vulnerability details');
      }
    }
  });

  // Realistic delay between scan operations
  // Longer delay to respect rate limits
  sleep(10 + Math.random() * 5); // 10-15 seconds
}

export function teardown(data) {
  console.log('🏁 Vulnerability scan load test completed');
  console.log(`   Scans triggered: ${scanCount.value}`);
  console.log(`   Rate limit hits: ${rateLimitHits.value}`);
  console.log(`   Vulnerabilities found: ${vulnerabilityCount.value}`);
}
