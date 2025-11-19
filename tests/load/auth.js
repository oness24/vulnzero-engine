/**
 * k6 Load Test - Authentication Endpoint
 *
 * Tests the /api/v1/auth/login endpoint performance
 * Measures authentication latency and throughput
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const authFailureRate = new Rate('auth_failures');
const authDuration = new Trend('auth_duration');
const authAttempts = new Counter('auth_attempts');

// Test configuration
export const options = {
  // Scenarios define different load patterns
  scenarios: {
    // Baseline: Constant low load
    baseline: {
      executor: 'constant-vus',
      vus: 10,
      duration: '2m',
      tags: { scenario: 'baseline' },
    },
    // Spike: Sudden traffic increase
    spike: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 100 },  // Ramp up quickly
        { duration: '1m', target: 100 },   // Stay high
        { duration: '30s', target: 0 },    // Ramp down
      ],
      startTime: '3m',
      tags: { scenario: 'spike' },
    },
    // Stress: Gradual increase to breaking point
    stress: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 50 },
        { duration: '3m', target: 100 },
        { duration: '2m', target: 150 },
        { duration: '3m', target: 200 },
        { duration: '2m', target: 0 },
      ],
      startTime: '6m',
      tags: { scenario: 'stress' },
    },
  },

  // Thresholds define pass/fail criteria
  thresholds: {
    'http_req_duration': ['p(95)<500', 'p(99)<1000'],  // 95% under 500ms, 99% under 1s
    'http_req_failed': ['rate<0.01'],  // Less than 1% failure rate
    'auth_failures': ['rate<0.01'],    // Less than 1% auth failures
    'auth_duration': ['p(95)<400'],    // Auth should be fast
  },
};

// Environment variables
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const TEST_EMAIL = __ENV.TEST_EMAIL || 'test@example.com';
const TEST_PASSWORD = __ENV.TEST_PASSWORD || 'TestPassword123!';

export function setup() {
  console.log(`🚀 Starting authentication load test against ${BASE_URL}`);

  // Verify API is reachable
  const healthCheck = http.get(`${BASE_URL}/api/v1/system/health`);

  if (healthCheck.status !== 200) {
    console.error('❌ API health check failed. Is the API running?');
    throw new Error('API not available');
  }

  console.log('✅ API health check passed');
  return { baseUrl: BASE_URL, email: TEST_EMAIL, password: TEST_PASSWORD };
}

export default function(data) {
  // Prepare login request
  const payload = JSON.stringify({
    email: data.email,
    password: data.password,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
    tags: {
      endpoint: 'auth_login',
    },
  };

  // Send login request
  const startTime = Date.now();
  const response = http.post(
    `${data.baseUrl}/api/v1/auth/login`,
    payload,
    params
  );
  const duration = Date.now() - startTime;

  // Record metrics
  authAttempts.add(1);
  authDuration.add(duration);

  // Validate response
  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'has access token': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.access_token !== undefined;
      } catch (e) {
        return false;
      }
    },
    'response time < 500ms': (r) => r.timings.duration < 500,
    'response time < 1000ms': (r) => r.timings.duration < 1000,
  });

  if (!success) {
    authFailureRate.add(1);
    console.error(`❌ Auth failed: ${response.status} - ${response.body}`);
  } else {
    authFailureRate.add(0);
  }

  // Realistic user delay between requests
  sleep(1);
}

export function teardown(data) {
  console.log('🏁 Authentication load test completed');
  console.log(`   Total requests: ${authAttempts.value}`);
}
