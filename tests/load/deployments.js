/**
 * k6 Load Test - Deployment Endpoint
 *
 * Tests the /api/v1/deployments endpoint performance
 * Simulates realistic deployment workloads
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { SharedArray } from 'k6/data';

// Custom metrics
const deploymentFailureRate = new Rate('deployment_failures');
const deploymentDuration = new Trend('deployment_duration');
const deploymentCount = new Counter('deployments_triggered');
const taskStatusChecks = new Counter('task_status_checks');

// Test configuration
export const options = {
  scenarios: {
    // Realistic deployment workload
    normal_operations: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 5 },     // Gradual ramp-up
        { duration: '5m', target: 10 },    // Sustained load
        { duration: '1m', target: 0 },     // Ramp down
      ],
      tags: { scenario: 'normal' },
    },
    // Peak hours simulation
    peak_hours: {
      executor: 'constant-vus',
      vus: 20,
      duration: '3m',
      startTime: '8m',
      tags: { scenario: 'peak' },
    },
  },

  thresholds: {
    'http_req_duration{endpoint:deployments}': ['p(95)<2000', 'p(99)<5000'],
    'http_req_duration{endpoint:task_status}': ['p(95)<200', 'p(99)<500'],
    'http_req_failed': ['rate<0.05'],  // Less than 5% failure rate
    'deployment_failures': ['rate<0.05'],
    'deployment_duration': ['p(95)<3000'],
  },
};

// Environment configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_TOKEN = __ENV.API_TOKEN || '';

export function setup() {
  console.log(`🚀 Starting deployment load test against ${BASE_URL}`);

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

  // Fetch available patches and assets
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };

  const patchesResponse = http.get(`${BASE_URL}/api/v1/patches?status=approved`, { headers });
  const assetsResponse = http.get(`${BASE_URL}/api/v1/assets`, { headers });

  let patches = [];
  let assets = [];

  if (patchesResponse.status === 200) {
    patches = JSON.parse(patchesResponse.body);
    console.log(`✅ Found ${patches.length} approved patches`);
  }

  if (assetsResponse.status === 200) {
    assets = JSON.parse(assetsResponse.body);
    console.log(`✅ Found ${assets.length} assets`);
  }

  if (patches.length === 0 || assets.length === 0) {
    console.warn('⚠️  No patches or assets available for testing');
  }

  return {
    baseUrl: BASE_URL,
    token: token,
    patches: patches,
    assets: assets,
  };
}

export default function(data) {
  const headers = {
    'Authorization': `Bearer ${data.token}`,
    'Content-Type': 'application/json',
  };

  // Only attempt deployment if we have patches and assets
  if (data.patches.length === 0 || data.assets.length === 0) {
    console.warn('⚠️  Skipping deployment - no patches or assets available');
    sleep(5);
    return;
  }

  group('Deployment Workflow', () => {
    // Step 1: Trigger deployment
    const patch = data.patches[Math.floor(Math.random() * data.patches.length)];
    const asset = data.assets[Math.floor(Math.random() * data.assets.length)];

    const deploymentPayload = JSON.stringify({
      patch_id: patch.id,
      asset_ids: [asset.id],
      strategy: 'canary',
      parameters: {
        canary_percentage: 10,
        monitoring_duration_seconds: 60,
      },
    });

    const startTime = Date.now();
    const deployResponse = http.post(
      `${data.baseUrl}/api/v1/deployments`,
      deploymentPayload,
      {
        headers: headers,
        tags: { endpoint: 'deployments' },
      }
    );
    const duration = Date.now() - startTime;

    deploymentCount.add(1);
    deploymentDuration.add(duration);

    const deploySuccess = check(deployResponse, {
      'deployment status is 200/201/202': (r) =>
        r.status === 200 || r.status === 201 || r.status === 202,
      'deployment has id': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.id !== undefined;
        } catch (e) {
          return false;
        }
      },
      'deployment response time < 2s': (r) => r.timings.duration < 2000,
    });

    if (!deploySuccess) {
      deploymentFailureRate.add(1);
      console.error(`❌ Deployment failed: ${deployResponse.status}`);
      return;
    } else {
      deploymentFailureRate.add(0);
    }

    // Extract task ID for status checking
    let taskId = null;
    try {
      const deployBody = JSON.parse(deployResponse.body);
      taskId = deployBody.task_id;
    } catch (e) {
      console.warn('⚠️  Could not extract task_id from deployment response');
    }

    // Step 2: Check task status (if we have a task ID)
    if (taskId) {
      sleep(2); // Wait briefly before checking status

      const statusResponse = http.get(
        `${data.baseUrl}/api/v1/tasks/${taskId}`,
        {
          headers: headers,
          tags: { endpoint: 'task_status' },
        }
      );

      taskStatusChecks.add(1);

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
        'task status response time < 200ms': (r) => r.timings.duration < 200,
      });
    }

    // Step 3: List deployments
    const listResponse = http.get(
      `${data.baseUrl}/api/v1/deployments?limit=10`,
      {
        headers: headers,
        tags: { endpoint: 'list_deployments' },
      }
    );

    check(listResponse, {
      'list status is 200': (r) => r.status === 200,
      'list has results': (r) => {
        try {
          const body = JSON.parse(r.body);
          return Array.isArray(body) || Array.isArray(body.items);
        } catch (e) {
          return false;
        }
      },
    });
  });

  // Realistic delay between deployment operations
  sleep(3 + Math.random() * 2); // 3-5 seconds
}

export function teardown(data) {
  console.log('🏁 Deployment load test completed');
  console.log(`   Deployments triggered: ${deploymentCount.value}`);
  console.log(`   Task status checks: ${taskStatusChecks.value}`);
}
