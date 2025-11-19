/**
 * k6 Comprehensive Load Test - Full System
 *
 * Tests all critical endpoints together to simulate real-world usage
 * Combines authentication, deployments, scans, and monitoring
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter, Gauge } from 'k6/metrics';
import { randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

// Custom metrics
const requestFailureRate = new Rate('request_failures');
const apiLatency = new Trend('api_latency');
const activeUsers = new Gauge('active_users');
const totalRequests = new Counter('total_requests');

// Endpoint-specific metrics
const authRequests = new Counter('auth_requests');
const deploymentRequests = new Counter('deployment_requests');
const scanRequests = new Counter('scan_requests');
const taskStatusRequests = new Counter('task_status_requests');
const assetRequests = new Counter('asset_requests');
const patchRequests = new Counter('patch_requests');

// Test configuration
export const options = {
  scenarios: {
    // Realistic user behavior
    normal_users: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 10 },    // Morning ramp-up
        { duration: '10m', target: 20 },   // Business hours
        { duration: '5m', target: 30 },    // Peak activity
        { duration: '10m', target: 20 },   // Afternoon
        { duration: '2m', target: 0 },     // Evening ramp-down
      ],
      tags: { scenario: 'normal' },
    },
    // Automated monitoring/polling
    monitoring_agents: {
      executor: 'constant-vus',
      vus: 5,
      duration: '30m',
      tags: { scenario: 'monitoring' },
    },
  },

  thresholds: {
    // Overall system health
    'http_req_duration': ['p(95)<1000', 'p(99)<3000'],
    'http_req_failed': ['rate<0.05'],
    'request_failures': ['rate<0.05'],

    // Endpoint-specific SLAs
    'http_req_duration{endpoint:auth}': ['p(95)<400'],
    'http_req_duration{endpoint:assets}': ['p(95)<500'],
    'http_req_duration{endpoint:patches}': ['p(95)<500'],
    'http_req_duration{endpoint:deployments}': ['p(95)<2000'],
    'http_req_duration{endpoint:scans}': ['p(95)<3000'],
    'http_req_duration{endpoint:task_status}': ['p(95)<200'],
    'http_req_duration{endpoint:health}': ['p(95)<100'],
  },
};

// Environment configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const TEST_EMAIL = __ENV.TEST_EMAIL || 'test@example.com';
const TEST_PASSWORD = __ENV.TEST_PASSWORD || 'TestPassword123!';

export function setup() {
  console.log(`🚀 Starting comprehensive load test against ${BASE_URL}`);
  console.log(`📊 Simulating realistic user behavior for 30 minutes`);

  // Health check
  const healthCheck = http.get(`${BASE_URL}/api/v1/system/health`);

  if (healthCheck.status !== 200) {
    console.error('❌ API health check failed');
    throw new Error('API not available');
  }

  console.log('✅ API is healthy and ready for load testing');

  return {
    baseUrl: BASE_URL,
    email: TEST_EMAIL,
    password: TEST_PASSWORD,
  };
}

/**
 * Authenticate user and get JWT token
 */
function authenticate(data) {
  const payload = JSON.stringify({
    email: data.email,
    password: data.password,
  });

  const response = http.post(
    `${data.baseUrl}/api/v1/auth/login`,
    payload,
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { endpoint: 'auth' },
    }
  );

  authRequests.add(1);
  totalRequests.add(1);

  const success = check(response, {
    'auth successful': (r) => r.status === 200,
    'has token': (r) => {
      try {
        return JSON.parse(r.body).access_token !== undefined;
      } catch (e) {
        return false;
      }
    },
  });

  if (!success) {
    requestFailureRate.add(1);
    return null;
  }

  requestFailureRate.add(0);

  try {
    return JSON.parse(response.body).access_token;
  } catch (e) {
    return null;
  }
}

/**
 * Browse assets
 */
function browseAssets(data, token) {
  const response = http.get(
    `${data.baseUrl}/api/v1/assets?limit=20`,
    {
      headers: { 'Authorization': `Bearer ${token}` },
      tags: { endpoint: 'assets' },
    }
  );

  assetRequests.add(1);
  totalRequests.add(1);

  const success = check(response, {
    'assets retrieved': (r) => r.status === 200,
  });

  requestFailureRate.add(success ? 0 : 1);

  try {
    return JSON.parse(response.body);
  } catch (e) {
    return [];
  }
}

/**
 * Browse patches
 */
function browsePatches(data, token) {
  const response = http.get(
    `${data.baseUrl}/api/v1/patches?status=approved&limit=20`,
    {
      headers: { 'Authorization': `Bearer ${token}` },
      tags: { endpoint: 'patches' },
    }
  );

  patchRequests.add(1);
  totalRequests.add(1);

  const success = check(response, {
    'patches retrieved': (r) => r.status === 200,
  });

  requestFailureRate.add(success ? 0 : 1);

  try {
    return JSON.parse(response.body);
  } catch (e) {
    return [];
  }
}

/**
 * Trigger deployment
 */
function triggerDeployment(data, token, patch, asset) {
  const payload = JSON.stringify({
    patch_id: patch.id,
    asset_ids: [asset.id],
    strategy: 'canary',
    parameters: {
      canary_percentage: 10,
      monitoring_duration_seconds: 60,
    },
  });

  const response = http.post(
    `${data.baseUrl}/api/v1/deployments`,
    payload,
    {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      tags: { endpoint: 'deployments' },
    }
  );

  deploymentRequests.add(1);
  totalRequests.add(1);

  const success = check(response, {
    'deployment triggered': (r) =>
      r.status === 200 || r.status === 201 || r.status === 202,
  });

  requestFailureRate.add(success ? 0 : 1);

  try {
    return JSON.parse(response.body);
  } catch (e) {
    return null;
  }
}

/**
 * Check task status
 */
function checkTaskStatus(data, token, taskId) {
  if (!taskId) return null;

  const response = http.get(
    `${data.baseUrl}/api/v1/tasks/${taskId}`,
    {
      headers: { 'Authorization': `Bearer ${token}` },
      tags: { endpoint: 'task_status' },
    }
  );

  taskStatusRequests.add(1);
  totalRequests.add(1);

  const success = check(response, {
    'task status retrieved': (r) => r.status === 200,
  });

  requestFailureRate.add(success ? 0 : 1);

  try {
    return JSON.parse(response.body);
  } catch (e) {
    return null;
  }
}

/**
 * Main user scenario
 */
export default function(data) {
  // Track active users
  activeUsers.add(1);

  group('User Session', () => {
    // Step 1: Authenticate
    const token = authenticate(data);

    if (!token) {
      console.error('❌ Authentication failed, skipping session');
      activeUsers.add(-1);
      return;
    }

    sleep(randomIntBetween(1, 3)); // Think time

    // Step 2: Browse assets and patches
    const assets = browseAssets(data, token);
    sleep(randomIntBetween(1, 2));

    const patches = browsePatches(data, token);
    sleep(randomIntBetween(1, 2));

    // Determine user action based on probability
    const action = Math.random();

    if (action < 0.3 && patches.length > 0 && assets.length > 0) {
      // 30% chance: Trigger deployment
      const patch = patches[Math.floor(Math.random() * patches.length)];
      const asset = assets[Math.floor(Math.random() * assets.length)];

      const deployment = triggerDeployment(data, token, patch, asset);
      sleep(randomIntBetween(2, 4));

      // Check deployment task status
      if (deployment && deployment.task_id) {
        checkTaskStatus(data, token, deployment.task_id);
        sleep(randomIntBetween(5, 10));

        // Check again after some time
        checkTaskStatus(data, token, deployment.task_id);
      }

    } else if (action < 0.4 && assets.length > 0) {
      // 10% chance: Trigger vulnerability scan
      // Note: Rate limited to 5/hour, so many will fail
      const asset = assets[Math.floor(Math.random() * assets.length)];

      const scanPayload = JSON.stringify({
        asset_ids: [asset.id],
        scanner: 'wazuh',
        scan_type: 'full',
      });

      const scanResponse = http.post(
        `${data.baseUrl}/api/v1/vulnerabilities/scan`,
        scanPayload,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          tags: { endpoint: 'scans' },
        }
      );

      scanRequests.add(1);
      totalRequests.add(1);

      if (scanResponse.status === 429) {
        // Rate limited (expected)
        console.log('ℹ️  Scan rate limited (expected)');
      } else {
        check(scanResponse, {
          'scan triggered': (r) =>
            r.status === 200 || r.status === 201 || r.status === 202,
        });
      }

      sleep(randomIntBetween(3, 6));

    } else {
      // 60% chance: Just browsing/monitoring
      sleep(randomIntBetween(2, 5));

      // Refresh assets view
      browseAssets(data, token);
      sleep(randomIntBetween(2, 4));
    }
  });

  activeUsers.add(-1);

  // Session complete, user leaves
  sleep(randomIntBetween(5, 15));
}

export function teardown(data) {
  console.log('🏁 Comprehensive load test completed');
  console.log(`📊 Total requests: ${totalRequests.value}`);
  console.log(`   - Auth: ${authRequests.value}`);
  console.log(`   - Assets: ${assetRequests.value}`);
  console.log(`   - Patches: ${patchRequests.value}`);
  console.log(`   - Deployments: ${deploymentRequests.value}`);
  console.log(`   - Scans: ${scanRequests.value}`);
  console.log(`   - Task Status: ${taskStatusRequests.value}`);
}
