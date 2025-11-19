# API Versioning and Deprecation Strategy

**Last Updated:** 2025-11-19
**Version:** 1.0.0

## Overview

VulnZero uses URL-based semantic versioning to ensure API stability while allowing evolution. This guide covers versioning conventions, deprecation policies, and migration strategies.

---

## Table of Contents

- [Versioning Strategy](#versioning-strategy)
- [Version Format](#version-format)
- [Deprecation Policy](#deprecation-policy)
- [Creating Versioned Endpoints](#creating-versioned-endpoints)
- [Deprecating Endpoints](#deprecating-endpoints)
- [Client Integration](#client-integration)
- [Migration Guide](#migration-guide)
- [Best Practices](#best-practices)

---

## Versioning Strategy

### URL-Based Versioning

VulnZero uses URL path versioning as the primary method:

```
https://api.vulnzero.com/api/v1/vulnerabilities
https://api.vulnzero.com/api/v2/vulnerabilities
```

**Why URL versioning:**
- ✅ Clear and explicit
- ✅ Easy to understand and test
- ✅ Works with all HTTP clients
- ✅ Cacheable at CDN level
- ✅ API Gateway friendly

### Supported Versions

- **v1** (Current) - Initial stable release
- **v2** (Planned) - Future major version

Check current versions:
```bash
curl -I https://api.vulnzero.com/api/v1/health

# Response headers:
# X-API-Version: v1
# X-API-Supported-Versions: v1
# X-API-Latest-Version: v1
```

---

## Version Format

### Semantic Versioning

API versions follow semantic versioning principles:

**Major Version (v1, v2, v3)**
- Breaking changes
- Incompatible API changes
- Schema modifications
- Endpoint removals

**When to increment major version:**
- Removing endpoints
- Changing request/response schemas (breaking)
- Changing authentication methods
- Modifying core business logic

**When NOT to increment (backward compatible):**
- Adding new endpoints
- Adding optional fields to requests
- Adding new fields to responses
- Deprecating endpoints (with grace period)
- Bug fixes

---

## Deprecation Policy

### Deprecation Lifecycle

```
┌─────────────┐
│  Announced  │ Day 0: Deprecation announced
└──────┬──────┘
       │ (6+ months)
       ▼
┌─────────────┐
│  Deprecated │ Headers added, warnings logged
└──────┬──────┘
       │ (3+ months)
       ▼
┌─────────────┐
│   Sunset    │ Endpoint removed, returns 410 Gone
└─────────────┘
```

### Timeline

1. **Announcement (T+0)**
   - Deprecation notice in release notes
   - Email to API consumers
   - Documentation updated

2. **Deprecation Period (T+6 months minimum)**
   - Endpoint continues to work
   - `Deprecation: true` header added
   - `Sunset` header with removal date
   - Alternative endpoint suggested
   - Warnings logged

3. **Sunset (T+9 months minimum)**
   - Endpoint returns `410 Gone`
   - Error includes alternative endpoint
   - Removed in next major version

### Minimum Support Period

- **Major version**: 12 months after next version released
- **Deprecated endpoint**: 9 months after deprecation announced
- **Critical security issues**: May require faster deprecation

---

## Creating Versioned Endpoints

### Using VersionedAPIRouter

```python
from shared.api_versioning import VersionedAPIRouter, APIVersion

# Create versioned router
router = VersionedAPIRouter(
    version=APIVersion.V1,
    prefix="/vulnerabilities",
    tags=["vulnerabilities"]
)

# Endpoints automatically prefixed with /api/v1
@router.get("/")
async def list_vulnerabilities():
    """
    List vulnerabilities.

    Available at: /api/v1/vulnerabilities/
    """
    return {"vulnerabilities": []}

@router.get("/{vuln_id}")
async def get_vulnerability(vuln_id: int):
    """
    Get vulnerability details.

    Available at: /api/v1/vulnerabilities/{vuln_id}
    """
    return {"id": vuln_id}
```

### Multiple Versions

```python
# V1 router
v1_router = VersionedAPIRouter(
    version=APIVersion.V1,
    prefix="/vulnerabilities",
    tags=["vulnerabilities-v1"]
)

@v1_router.get("/")
async def list_vulnerabilities_v1():
    """Old response format"""
    return {
        "data": [],
        "count": 0
    }

# V2 router (future)
v2_router = VersionedAPIRouter(
    version=APIVersion.V2,
    prefix="/vulnerabilities",
    tags=["vulnerabilities-v2"]
)

@v2_router.get("/")
async def list_vulnerabilities_v2():
    """New response format with pagination"""
    return {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 20
    }

# Register both
app.include_router(v1_router)
app.include_router(v2_router)
```

---

## Deprecating Endpoints

### Mark as Deprecated

```python
from shared.api_versioning import deprecated
from datetime import date

@router.get("/old-endpoint")
@deprecated(
    sunset_date=date(2025, 12, 31),
    alternative="/api/v2/new-endpoint",
    reason="Moved to v2 with improved schema"
)
async def old_endpoint():
    """
    Old endpoint (deprecated).

    **Deprecated:** This endpoint is deprecated and will be removed on 2025-12-31.
    Use `/api/v2/new-endpoint` instead.
    """
    return {"message": "This endpoint is deprecated"}
```

### Response Headers

Deprecated endpoints automatically add these headers:

```http
HTTP/1.1 200 OK
Deprecation: true
Sunset: 2025-12-31
X-API-Deprecation-Info: This endpoint is deprecated. Use /api/v2/new-endpoint instead. Reason: Moved to v2 with improved schema. Sunset: 2025-12-31
```

### Enforce Sunset Date

```python
from shared.api_versioning import sunset
from datetime import date

@router.get("/removed-endpoint")
@sunset(date(2024, 1, 1))
async def removed_endpoint():
    """
    This endpoint was removed on 2024-01-01.

    Returns 410 Gone after sunset date.
    """
    return {"message": "This should never be seen"}
```

After sunset date:

```http
HTTP/1.1 410 Gone
Content-Type: application/json

{
    "error": "Endpoint has been sunset",
    "sunset_date": "2024-01-01",
    "message": "This endpoint was removed on 2024-01-01"
}
```

---

## Client Integration

### Making Requests

```python
import requests

# Option 1: URL path versioning (recommended)
response = requests.get("https://api.vulnzero.com/api/v1/vulnerabilities")

# Option 2: Accept header versioning
response = requests.get(
    "https://api.vulnzero.com/api/vulnerabilities",
    headers={"Accept": "application/vnd.vulnzero.v1+json"}
)

# Option 3: Custom header
response = requests.get(
    "https://api.vulnzero.com/api/vulnerabilities",
    headers={"X-API-Version": "v1"}
)
```

### Check for Deprecations

```python
response = requests.get("https://api.vulnzero.com/api/v1/some-endpoint")

# Check deprecation headers
if "Deprecation" in response.headers:
    print(f"⚠️ Warning: This endpoint is deprecated")
    print(f"Info: {response.headers.get('X-API-Deprecation-Info')}")

    sunset = response.headers.get("Sunset")
    if sunset:
        print(f"Sunset date: {sunset}")
```

### Get Deprecation List

```python
# Get list of all deprecated endpoints
response = requests.get("https://api.vulnzero.com/api/v1/system/deprecations")

deprecations = response.json()
print(f"Current version: {deprecations['current_version']}")
print(f"Deprecated endpoints: {len(deprecations['deprecated_endpoints'])}")

for endpoint in deprecations['deprecated_endpoints']:
    print(f"- {endpoint['endpoint']}")
    print(f"  Sunset: {endpoint['sunset_at']}")
    print(f"  Alternative: {endpoint['alternative']}")
```

---

## Migration Guide

### From v1 to v2 (Future)

When migrating between major versions:

**1. Review deprecations**
```bash
curl https://api.vulnzero.com/api/v1/system/deprecations
```

**2. Update client to use v2 endpoints**
```python
# Before (v1)
response = requests.get("https://api.vulnzero.com/api/v1/vulnerabilities")
data = response.json()["data"]  # Old format

# After (v2)
response = requests.get("https://api.vulnzero.com/api/v2/vulnerabilities")
data = response.json()["items"]  # New format
```

**3. Test with both versions**
```python
# Run integration tests against v2
# Keep v1 as fallback during transition
```

**4. Monitor deprecation warnings**
```python
# Log all deprecation headers
# Alert when using deprecated endpoints
```

**5. Switch to v2 before v1 sunset**
```python
# Complete migration before v1 is removed
```

---

## Best Practices

### 1. Always Specify Version

**Bad:**
```python
requests.get("https://api.vulnzero.com/vulnerabilities")  # Which version?
```

**Good:**
```python
requests.get("https://api.vulnzero.com/api/v1/vulnerabilities")  # Clear!
```

### 2. Never Break Backward Compatibility Within a Version

**Bad (breaking change in v1):**
```python
# Before
return {"vulnerabilities": [...]}

# After (BREAKING!)
return {"items": [...]}
```

**Good (backward compatible):**
```python
# Before
return {"vulnerabilities": [...]}

# After (new field added, old field remains)
return {
    "vulnerabilities": [...],  # Keep for compatibility
    "items": [...],  # New field
}
```

### 3. Add New Fields, Don't Remove

**Bad:**
```python
# Removing field breaks clients
return {
    "id": 123,
    # "cve_id": removed!  # BREAKING
    "severity": "high"
}
```

**Good:**
```python
# Add new fields, mark old as deprecated in docs
return {
    "id": 123,
    "cve_id": "CVE-2024-1234",  # Keep
    "cve_identifier": "CVE-2024-1234",  # New preferred field
    "severity": "high"
}
```

### 4. Announce Deprecations Early

- Announce 6+ months before sunset
- Provide migration guide
- Offer support during transition
- Monitor usage of deprecated endpoints

### 5. Version Your Schemas

```python
from pydantic import BaseModel

class VulnerabilityV1(BaseModel):
    """V1 schema"""
    id: int
    cve_id: str
    severity: str

class VulnerabilityV2(BaseModel):
    """V2 schema with additional fields"""
    id: int
    cve_identifier: str  # Renamed
    severity: str
    cvss_score: float  # New field
    affected_assets: List[int]  # New field
```

### 6. Document Breaking Changes

```markdown
## Breaking Changes in v2

### Changed Response Format
**Endpoint:** `GET /api/v2/vulnerabilities`

**Before (v1):**
```json
{
    "data": [...],
    "count": 10
}
```

**After (v2):**
```json
{
    "items": [...],
    "total": 10,
    "page": 1,
    "page_size": 20
}
```

**Migration:** Update client code to use `items` instead of `data`.
```

---

## Versioning Decision Tree

```
┌─────────────────────────────────┐
│  Making an API change?          │
└────────────┬────────────────────┘
             │
             ▼
    ┌────────────────┐
    │  Breaking      │
    │  change?       │
    └───┬────────┬───┘
        │        │
       YES       NO
        │        │
        ▼        ▼
  ┌──────────┐  ┌──────────┐
  │ New      │  │ Add to   │
  │ major    │  │ current  │
  │ version  │  │ version  │
  └──────────┘  └──────────┘
```

**Breaking changes:**
- Removing endpoints
- Removing fields from responses
- Changing field types
- Changing authentication
- Changing error codes
- Renaming fields (unless aliased)

**Non-breaking changes:**
- Adding endpoints
- Adding optional fields to requests
- Adding fields to responses
- Deprecating endpoints (with sunset)
- Bug fixes
- Performance improvements

---

## Monitoring

### Track API Version Usage

```python
# Prometheus metrics automatically track API version usage
# via URL path labels

# Query Grafana:
# API v1 requests
sum(rate(vulnzero_http_requests_total{endpoint=~"/api/v1/.*"}[5m]))

# API v2 requests
sum(rate(vulnzero_http_requests_total{endpoint=~"/api/v2/.*"}[5m]))

# Deprecated endpoint usage
sum(rate(vulnzero_http_requests_total{endpoint=~".*deprecated.*"}[5m]))
```

### Alert on Deprecated Endpoint Usage

```yaml
# Prometheus alert rule
groups:
  - name: api_deprecation
    rules:
      - alert: DeprecatedEndpointUsage
        expr: |
          sum(rate(vulnzero_http_requests_total{endpoint=~".*deprecated.*"}[5m])) > 10
        for: 1h
        annotations:
          summary: "Deprecated API endpoint still being used"
          description: "Deprecated endpoint receiving {{ $value }} req/s"
```

---

## FAQ

### Q: How do I know which version to use?

Check the response headers:
```http
X-API-Latest-Version: v1
X-API-Supported-Versions: v1
```

Use the latest version for new integrations.

### Q: Can I mix versions in one client?

Yes, but not recommended. Prefer using a single version across your application for consistency.

### Q: What happens if I don't specify a version?

The middleware will extract version from URL path. If not found, it defaults to the latest version. However, it's best practice to always be explicit.

### Q: How long is a version supported?

Minimum 12 months after the next major version is released. We aim for longer support when possible.

### Q: Can deprecated endpoints be un-deprecated?

Rarely. If an endpoint is deprecated and significant usage remains, we may extend the sunset date but won't un-deprecate.

---

## Further Reading

- [API Versioning Best Practices](https://www.troyhunt.com/your-api-versioning-is-wrong-which-is/)
- [RFC 8594 - Sunset Header](https://tools.ietf.org/html/rfc8594)
- [Deprecation HTTP Header](https://tools.ietf.org/id/draft-dalal-deprecation-header-03.html)

---

**Maintained by:** VulnZero API Team
**Questions?** See #vulnzero-api in Slack
