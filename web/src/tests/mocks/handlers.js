/**
 * Mock Service Worker handlers for API mocking
 *
 * Used for integration and E2E tests to mock API responses
 */

// Note: MSW setup would go here when needed
// For now, we'll use Vitest's vi.mock() for unit tests

export const mockVulnerabilities = [
  {
    id: 1,
    cve_id: 'CVE-2024-1234',
    title: 'Critical SQL Injection in Auth Module',
    description: 'SQL injection vulnerability allowing unauthorized access',
    severity: 'critical',
    cvss_score: 9.8,
    affected_packages: ['auth-module@1.2.3'],
    status: 'open',
    discovered_at: '2024-01-15T10:30:00Z',
    tags: ['sql-injection', 'authentication', 'high-priority'],
  },
  {
    id: 2,
    cve_id: 'CVE-2024-5678',
    title: 'XSS Vulnerability in User Profile',
    description: 'Cross-site scripting in user profile rendering',
    severity: 'high',
    cvss_score: 7.5,
    affected_packages: ['frontend@2.1.0'],
    status: 'open',
    discovered_at: '2024-01-16T14:20:00Z',
    tags: ['xss', 'frontend', 'user-input'],
  },
  {
    id: 3,
    cve_id: 'CVE-2024-9012',
    title: 'Outdated Dependency with Known Vulnerability',
    description: 'lodash version has prototype pollution vulnerability',
    severity: 'medium',
    cvss_score: 5.3,
    affected_packages: ['lodash@4.17.15'],
    status: 'patched',
    discovered_at: '2024-01-10T09:15:00Z',
    patched_at: '2024-01-17T11:00:00Z',
    tags: ['dependency', 'prototype-pollution'],
  },
]

export const mockPatches = [
  {
    id: 1,
    vulnerability_id: 1,
    patch_type: 'code',
    description: 'Parameterized queries to prevent SQL injection',
    patch_script: '#!/bin/bash\nnpm install secure-auth@2.0.0\n',
    rollback_script: '#!/bin/bash\nnpm install auth-module@1.2.3\n',
    validation_tests: ['test_auth_injection.py', 'test_auth_security.py'],
    status: 'pending_approval',
    created_at: '2024-01-15T11:00:00Z',
    ai_confidence: 0.95,
    estimated_risk: 'low',
  },
  {
    id: 2,
    vulnerability_id: 2,
    patch_type: 'code',
    description: 'DOMPurify implementation for XSS prevention',
    patch_script: '#!/bin/bash\nnpm install dompurify@3.0.0\n',
    rollback_script: '#!/bin/bash\nnpm uninstall dompurify\n',
    validation_tests: ['test_xss_prevention.py'],
    status: 'approved',
    created_at: '2024-01-16T15:00:00Z',
    approved_at: '2024-01-16T16:00:00Z',
    ai_confidence: 0.92,
    estimated_risk: 'low',
  },
]

export const mockDeployments = [
  {
    id: 1,
    patch_id: 2,
    strategy: 'canary',
    target_environment: 'production',
    status: 'in_progress',
    progress: 0.45,
    started_at: '2024-01-17T10:00:00Z',
    estimated_completion: '2024-01-17T10:30:00Z',
    rollback_plan: 'automated',
    health_checks: {
      cpu: 'healthy',
      memory: 'healthy',
      error_rate: 'healthy',
    },
  },
  {
    id: 2,
    patch_id: 1,
    strategy: 'blue-green',
    target_environment: 'staging',
    status: 'completed',
    progress: 1.0,
    started_at: '2024-01-16T14:00:00Z',
    completed_at: '2024-01-16T14:25:00Z',
    rollback_plan: 'automated',
    health_checks: {
      cpu: 'healthy',
      memory: 'healthy',
      error_rate: 'healthy',
    },
  },
]

export const mockMetrics = {
  vulnerabilities: {
    total: 156,
    by_severity: {
      critical: 12,
      high: 34,
      medium: 67,
      low: 43,
    },
    trend: {
      week: -8, // 8 fewer than last week
      month: +23, // 23 more than last month
    },
  },
  patches: {
    total: 142,
    success_rate: 0.94,
    average_generation_time: 45, // seconds
    by_status: {
      pending_approval: 8,
      approved: 15,
      deployed: 119,
    },
  },
  deployments: {
    total: 119,
    success_rate: 0.97,
    average_duration: 18.5, // minutes
    rollback_rate: 0.03,
    by_strategy: {
      rolling: 67,
      'blue-green': 38,
      canary: 14,
    },
  },
  system_health: {
    api_latency: 42, // ms
    cpu_usage: 0.58,
    memory_usage: 0.72,
    active_scans: 3,
    queue_size: 12,
  },
}

export const mockSystemHealth = {
  status: 'healthy',
  timestamp: '2024-01-17T12:00:00Z',
  checks: {
    database: 'ok',
    redis: 'ok',
    celery: 'ok',
    api: 'ok',
  },
  metrics: {
    api_response_time: 45,
    database_connections: 12,
    celery_workers: 4,
    queue_length: 8,
  },
}

export const mockAlerts = [
  {
    id: 1,
    type: 'deployment_failed',
    severity: 'high',
    title: 'Deployment Failed: Patch #42',
    message: 'Blue-green deployment failed due to health check failure',
    timestamp: '2024-01-17T11:30:00Z',
    acknowledged: false,
    deployment_id: 42,
  },
  {
    id: 2,
    type: 'critical_vulnerability',
    severity: 'critical',
    title: 'New Critical Vulnerability Detected',
    message: 'CVE-2024-9999: Remote code execution in core auth module',
    timestamp: '2024-01-17T09:15:00Z',
    acknowledged: true,
    acknowledged_at: '2024-01-17T09:20:00Z',
    vulnerability_id: 157,
  },
]

export const mockWebSocketEvents = {
  deployment_progress: {
    type: 'deployment_progress',
    data: {
      deployment_id: 1,
      progress: 0.65,
      status: 'in_progress',
      current_step: 'health_check',
      message: 'Running health checks on canary instances...',
    },
  },
  vulnerability_detected: {
    type: 'vulnerability_detected',
    data: {
      vulnerability_id: 158,
      cve_id: 'CVE-2024-1111',
      severity: 'high',
      title: 'New vulnerability detected in dependency',
    },
  },
  patch_generated: {
    type: 'patch_generated',
    data: {
      patch_id: 143,
      vulnerability_id: 158,
      confidence: 0.89,
      status: 'pending_review',
    },
  },
}

// API response helpers
export const createMockResponse = (data, status = 200) => ({
  status,
  data,
  headers: {
    'content-type': 'application/json',
  },
})

export const createMockError = (message, status = 500) => ({
  status,
  data: {
    error: 'InternalServerError',
    message,
    timestamp: new Date().toISOString(),
  },
})

// Pagination helpers
export const createPaginatedResponse = (items, page = 1, pageSize = 20) => ({
  items: items.slice((page - 1) * pageSize, page * pageSize),
  pagination: {
    page,
    page_size: pageSize,
    total_items: items.length,
    total_pages: Math.ceil(items.length / pageSize),
    has_next: page < Math.ceil(items.length / pageSize),
    has_previous: page > 1,
  },
})
