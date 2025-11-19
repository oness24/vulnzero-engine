# OWASP ZAP Security Scanning Configuration

This directory contains configuration files for OWASP ZAP security scanning.

## 📋 Configuration Files

### `zap-baseline.conf`
Baseline scan configuration for CI/CD pipelines:
- **Speed**: Fast (passive scanning only)
- **Coverage**: Basic security checks
- **Use Case**: Pull request validation, daily builds
- **Duration**: ~5-10 minutes
- **Impact**: No load on application

### `zap-api-scan.conf`
Comprehensive API security scan:
- **Speed**: Slow (active attacks)
- **Coverage**: OWASP API Security Top 10
- **Use Case**: Weekly security audits, pre-release testing
- **Duration**: ~30-60 minutes
- **Impact**: High load on application

## 🚀 Usage

### Local Testing

#### Baseline Scan (Fast)
```bash
# Start your API gateway locally
docker-compose up api-gateway

# Run ZAP baseline scan
docker run --rm -v $(pwd)/.zap:/zap/wrk:rw \
  -t ghcr.io/zaproxy/zaproxy:stable \
  zap-baseline.py \
  -t http://host.docker.internal:8000 \
  -c zap-baseline.conf \
  -r zap-baseline-report.html \
  -J zap-baseline-report.json
```

#### API Scan (Comprehensive)
```bash
# Start your API gateway locally
docker-compose up api-gateway

# Export OpenAPI spec
curl http://localhost:8000/openapi.json > .zap/openapi.json

# Run ZAP API scan
docker run --rm -v $(pwd)/.zap:/zap/wrk:rw \
  -t ghcr.io/zaproxy/zaproxy:stable \
  zap-api-scan.py \
  -t http://host.docker.internal:8000/openapi.json \
  -f openapi \
  -c zap-api-scan.conf \
  -r zap-api-report.html \
  -J zap-api-report.json
```

### CI/CD Integration

The security scanning workflow runs automatically:
- **Baseline Scan**: On every pull request
- **API Scan**: Weekly on Monday at 2 AM UTC
- **Manual Trigger**: Via GitHub Actions UI

See `.github/workflows/security.yml` for configuration.

## 📊 Alert Levels

### FAIL (Critical)
Vulnerabilities that will fail the build:
- SQL Injection
- Command Injection
- XSS (Reflected & Persistent)
- Path Traversal
- Authentication Bypass
- IDOR vulnerabilities
- CORS misconfiguration

### WARN (Important)
Issues logged as warnings:
- Missing CSRF tokens
- Cookie security flags
- Information disclosure
- Rate limiting issues
- Debug mode enabled

### IGNORE (Handled)
Alerts ignored because we handle them via middleware:
- Security headers (X-Frame-Options, CSP, HSTS)
- We set these in `services/api_gateway/middleware/security_headers.py`

## 🔧 Customization

### Adding New Rules

Edit `zap-baseline.conf` or `zap-api-scan.conf`:

```
# Format: <alert_id>	<action>
40012	FAIL  # XSS Reflected

# Add comment explaining why
10020	IGNORE  # X-Frame-Options (set via middleware)
```

### Excluding Endpoints

Add to configuration file:

```
# Exclude specific paths
/api/v1/internal/debug	OUTOFSCOPE
/api/v1/test/*	OUTOFSCOPE
```

## 📈 Interpreting Results

### HTML Report
- Open `zap-baseline-report.html` or `zap-api-report.html` in browser
- View alerts grouped by risk level
- Each alert includes:
  - Description of vulnerability
  - Affected URLs
  - Recommendations for fixing
  - CWE/WASC references

### JSON Report
Machine-readable format for integration:
```json
{
  "site": [
    {
      "alerts": [
        {
          "name": "SQL Injection",
          "riskcode": "3",
          "riskdesc": "High",
          "desc": "SQL injection may be possible...",
          "solution": "Do not trust client side input...",
          "instances": [...]
        }
      ]
    }
  ]
}
```

## 🛠️ Troubleshooting

### False Positives

If ZAP reports a false positive:

1. **Verify it's actually false**: Test the endpoint manually
2. **Add to ignore list**: Add alert ID to configuration with IGNORE
3. **Document why**: Add comment explaining the exception
4. **Report upstream**: File issue with OWASP ZAP if bug in scanner

### Scan Takes Too Long

For API scans that timeout:

1. Reduce attack strength in configuration
2. Exclude non-critical endpoints
3. Split into multiple scans
4. Increase timeout in workflow file

### Authentication Required

To scan authenticated endpoints:

1. Create ZAP authentication script
2. Add authentication context to configuration
3. Use session management in ZAP
4. See [ZAP Authentication Guide](https://www.zaproxy.org/docs/authentication/)

## 🔒 Security Considerations

### API Keys & Secrets

**NEVER** commit:
- API keys in configuration files
- Session tokens
- Passwords or credentials

Use environment variables or GitHub Secrets for sensitive data.

### Production Scanning

**DO NOT** run active scans (API scan) against production:
- Can cause service disruption
- May trigger rate limits
- Could create test data in production
- Use staging environment instead

### Rate Limiting

Active scans generate high request volume:
- Exclude from rate limiting in test environment
- Or increase rate limits for security scanner IP
- Monitor resource usage during scans

## 📚 Resources

- [OWASP ZAP Documentation](https://www.zaproxy.org/docs/)
- [OWASP API Security Top 10](https://owasp.org/API-Security/editions/2023/en/0x00-header/)
- [ZAP Alert IDs Reference](https://www.zaproxy.org/docs/alerts/)
- [ZAP Automation Framework](https://www.zaproxy.org/docs/automate/automation-framework/)

## 🎯 Next Steps

After setting up ZAP scanning:

1. **Run baseline scan locally** - Verify configuration works
2. **Fix any HIGH/CRITICAL alerts** - Address security issues
3. **Review WARN alerts** - Decide which to fix or ignore
4. **Enable CI/CD integration** - Automate scanning on PRs
5. **Schedule weekly API scans** - Comprehensive security audits
6. **Monitor trends** - Track security posture over time

## 📞 Support

For questions about ZAP configuration:
1. Check OWASP ZAP documentation
2. Review ZAP GitHub issues
3. Consult security team
4. Update this documentation with findings
