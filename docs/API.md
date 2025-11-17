# VulnZero REST API Documentation

The VulnZero REST API provides programmatic access to vulnerability management and patch generation capabilities.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All API endpoints (except health checks) require authentication using an API key.

### Methods

**Option 1: Authorization Header (Recommended)**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/v1/vulnerabilities
```

**Option 2: X-API-Key Header**
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  http://localhost:8000/api/v1/vulnerabilities
```

### Configuration

Set your API keys in `.env`:
```bash
API_KEYS=["key1", "key2", "key3"]
```

### Development Mode

In development, authentication is disabled by default. To enable:
```bash
REQUIRE_AUTH_IN_DEV=true
```

## Rate Limiting

- **Default**: 60 requests per minute per IP address
- **Response**: HTTP 429 with `Retry-After` header when exceeded

## Interactive Documentation

VulnZero provides interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

---

## Endpoints

### Health Checks

#### GET /health
Basic health check endpoint (no authentication required).

**Response:**
```json
{
  "status": "healthy",
  "service": "VulnZero API Gateway",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

#### GET /health/database
Check database connectivity.

**Response:**
```json
{
  "status": "healthy",
  "component": "database",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

#### GET /health/ready
Kubernetes readiness probe.

#### GET /health/live
Kubernetes liveness probe.

---

### Vulnerabilities

#### GET /api/v1/vulnerabilities
List all vulnerabilities with filtering and pagination.

**Query Parameters:**
- `severity` (optional): Filter by severity (critical, high, medium, low)
- `status` (optional): Filter by status (new, patch_generated, approved, deployed, etc.)
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20, max: 100)

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:8000/api/v1/vulnerabilities?severity=critical&page=1&page_size=10"
```

**Response:**
```json
{
  "vulnerabilities": [
    {
      "id": 1,
      "cve_id": "CVE-2023-4911",
      "title": "Buffer overflow in glibc",
      "description": "A buffer overflow vulnerability...",
      "severity": "high",
      "cvss_score": 7.8,
      "cvss_vector": "CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H",
      "status": "patch_generated",
      "package_name": "glibc",
      "vulnerable_version": "2.35",
      "fixed_version": "2.35-0ubuntu3.6",
      "priority_score": 85.5,
      "patch_count": 2,
      "discovered_at": "2024-01-10T08:00:00.000Z",
      "created_at": "2024-01-10T08:00:00.000Z",
      "updated_at": "2024-01-12T14:30:00.000Z"
    }
  ],
  "total": 145,
  "page": 1,
  "page_size": 10
}
```

#### GET /api/v1/vulnerabilities/{vulnerability_id}
Get detailed information about a specific vulnerability.

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/v1/vulnerabilities/1
```

**Response:** Same as single vulnerability object above.

#### GET /api/v1/vulnerabilities/cve/{cve_id}
Get vulnerability by CVE ID.

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/v1/vulnerabilities/cve/CVE-2023-4911
```

#### POST /api/v1/vulnerabilities
Create or update a vulnerability.

**Request Body:**
```json
{
  "cve_id": "CVE-2024-1234",
  "title": "Example Vulnerability",
  "description": "Detailed description...",
  "severity": "high",
  "cvss_score": 8.1,
  "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
  "package_name": "nginx",
  "vulnerable_version": "1.20.0",
  "fixed_version": "1.20.2"
}
```

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"cve_id":"CVE-2024-1234","title":"Example","severity":"high"}' \
  http://localhost:8000/api/v1/vulnerabilities
```

**Response:** HTTP 201 with created vulnerability object.

#### GET /api/v1/vulnerabilities/stats
Get vulnerability statistics.

**Response:**
```json
{
  "total_vulnerabilities": 145,
  "by_severity": {
    "critical": 12,
    "high": 45,
    "medium": 67,
    "low": 21
  },
  "by_status": {
    "new": 34,
    "patch_generated": 56,
    "approved": 32,
    "deployed": 18,
    "resolved": 5
  },
  "average_cvss": 6.7,
  "critical_count": 12,
  "high_count": 45,
  "medium_count": 67,
  "low_count": 21
}
```

---

### Patches

#### GET /api/v1/patches
List all patches with filtering and pagination.

**Query Parameters:**
- `status` (optional): Filter by status (generated, approved, rejected, etc.)
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20, max: 100)

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:8000/api/v1/patches?status=pending&page=1"
```

**Response:**
```json
{
  "patches": [
    {
      "id": 1,
      "patch_id": "PATCH-2024-001",
      "vulnerability_id": 1,
      "cve_id": "CVE-2023-4911",
      "status": "generated",
      "confidence_score": 0.87,
      "llm_model": "gpt-4",
      "approved_by": null,
      "approved_at": null,
      "rejection_reason": null,
      "test_status": null,
      "created_at": "2024-01-12T10:00:00.000Z",
      "updated_at": "2024-01-12T10:00:00.000Z"
    }
  ],
  "total": 89,
  "page": 1,
  "page_size": 20
}
```

#### GET /api/v1/patches/{patch_id}
Get detailed patch information including content and rollback script.

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/v1/patches/PATCH-2024-001
```

**Response:**
```json
{
  "id": 1,
  "patch_id": "PATCH-2024-001",
  "vulnerability_id": 1,
  "cve_id": "CVE-2023-4911",
  "status": "generated",
  "confidence_score": 0.87,
  "llm_model": "gpt-4",
  "patch_content": "#!/bin/bash\nset -euo pipefail\n...",
  "rollback_script": "#!/bin/bash\nset -euo pipefail\n...",
  "test_report": null,
  "validation_report": "{\"safety_score\": 0.95, \"issues\": []}",
  "created_at": "2024-01-12T10:00:00.000Z",
  "updated_at": "2024-01-12T10:00:00.000Z"
}
```

#### POST /api/v1/patches/{patch_id}/approve
Approve a patch for deployment.

**Request Body:**
```json
{
  "approver": "john.doe@example.com",
  "notes": "Reviewed and approved for production deployment"
}
```

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"approver":"john.doe@example.com","notes":"Approved"}' \
  http://localhost:8000/api/v1/patches/PATCH-2024-001/approve
```

**Response:** Updated patch object with `status: "approved"`.

#### POST /api/v1/patches/{patch_id}/reject
Reject a patch.

**Request Body:**
```json
{
  "rejector": "jane.smith@example.com",
  "reason": "Patch modifies critical system files without proper backup"
}
```

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"rejector":"jane.smith@example.com","reason":"Safety concerns"}' \
  http://localhost:8000/api/v1/patches/PATCH-2024-001/reject
```

**Response:** Updated patch object with `status: "rejected"`.

#### GET /api/v1/patches/stats
Get patch statistics.

**Response:**
```json
{
  "total_patches": 89,
  "approved": 45,
  "rejected": 12,
  "pending_review": 32,
  "average_confidence": 0.85,
  "approval_rate": 0.79
}
```

#### GET /api/v1/patches/vulnerability/{vulnerability_id}
Get all patches for a specific vulnerability.

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/v1/patches/vulnerability/1
```

**Response:** Array of patch objects.

---

## Error Responses

### 400 Bad Request
Invalid request parameters.
```json
{
  "detail": "Invalid status: invalid_status"
}
```

### 401 Unauthorized
Missing or invalid API key.
```json
{
  "detail": "Missing API key. Provide via Authorization header or X-API-Key header."
}
```

### 404 Not Found
Resource not found.
```json
{
  "detail": "Patch PATCH-2024-999 not found"
}
```

### 429 Too Many Requests
Rate limit exceeded.
```json
{
  "detail": "Rate limit exceeded. Please try again later."
}
```

**Headers:**
```
Retry-After: 60
```

### 500 Internal Server Error
Server error.
```json
{
  "detail": "Internal server error"
}
```

---

## Response Headers

All responses include these headers:

- `X-Process-Time`: Request processing time in seconds
- `Content-Type`: application/json

---

## Code Examples

### Python (requests)

```python
import requests

API_KEY = "your-api-key-here"
BASE_URL = "http://localhost:8000/api/v1"

headers = {"Authorization": f"Bearer {API_KEY}"}

# List critical vulnerabilities
response = requests.get(
    f"{BASE_URL}/vulnerabilities",
    headers=headers,
    params={"severity": "critical", "page_size": 10}
)
vulnerabilities = response.json()

# Approve a patch
response = requests.post(
    f"{BASE_URL}/patches/PATCH-2024-001/approve",
    headers=headers,
    json={
        "approver": "admin@example.com",
        "notes": "Reviewed and approved"
    }
)
approved_patch = response.json()
```

### JavaScript (fetch)

```javascript
const API_KEY = 'your-api-key-here';
const BASE_URL = 'http://localhost:8000/api/v1';

const headers = {
  'Authorization': `Bearer ${API_KEY}`,
  'Content-Type': 'application/json'
};

// Get vulnerability statistics
const statsResponse = await fetch(`${BASE_URL}/vulnerabilities/stats`, {
  headers
});
const stats = await statsResponse.json();

// Create vulnerability
const createResponse = await fetch(`${BASE_URL}/vulnerabilities`, {
  method: 'POST',
  headers,
  body: JSON.stringify({
    cve_id: 'CVE-2024-1234',
    title: 'Example Vulnerability',
    severity: 'high',
    cvss_score: 8.1
  })
});
const vulnerability = await createResponse.json();
```

### curl

```bash
# Get all high severity vulnerabilities
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:8000/api/v1/vulnerabilities?severity=high"

# Get patch details
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/v1/patches/PATCH-2024-001

# Approve patch
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"approver":"admin@example.com","notes":"Approved"}' \
  http://localhost:8000/api/v1/patches/PATCH-2024-001/approve
```

---

## Running the API Server

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
make db-migrate

# Start API server
uvicorn vulnzero.services.api_gateway.main:app --reload --host 0.0.0.0 --port 8000
```

### Production

```bash
# Using Docker Compose
docker-compose up -d api-gateway

# Or using gunicorn
gunicorn vulnzero.services.api_gateway.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

---

## WebSocket Support

*(Coming in future release)*

Real-time updates for patch generation progress, deployment status, and vulnerability alerts.

---

## Changelog

### v0.1.0 (Current)
- Initial REST API release
- Vulnerability CRUD operations
- Patch management endpoints
- API key authentication
- Rate limiting
- Health checks
- Statistics endpoints

---

## Support

- **Documentation**: https://docs.vulnzero.io
- **Issues**: https://github.com/oness24/vulnzero-engine/issues
- **API Status**: http://localhost:8000/api/v1/health
