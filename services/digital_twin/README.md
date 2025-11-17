# VulnZero Digital Twin Testing Engine

The Digital Twin Testing Engine provides isolated Docker environments for safe patch testing before production deployment. It creates containerized replicas of production assets to validate patches without risk.

## Features

### 1. **Environment Provisioning**
- Spin up Docker containers matching production assets
- Support for multiple Linux distributions:
  - Ubuntu 20.04, 22.04, 24.04
  - RHEL 8, 9 (Rocky Linux)
  - Amazon Linux 2
  - Debian 11, 12
- Isolated test networks
- Resource limits (CPU: 2 cores, Memory: 4GB)

### 2. **Patch Testing**
- Execute patches in isolated environments
- Monitor execution (stdout, stderr, exit codes)
- Capture system state before/after patching
- Timeout handling (10 minutes default)
- Automatic rollback capability

### 3. **Health Checks**
- **Port checks**: Verify services are listening
- **Service checks**: systemd service status validation
- **HTTP checks**: Endpoint response testing
- **Process checks**: Verify critical processes running
- **Package checks**: Validate package installation
- **Log checks**: Scan for errors in logs

### 4. **Test Result Analysis**
- Pass/Fail determination with confidence scoring
- Detailed issue and warning identification
- Comprehensive test reports
- System state comparison
- Performance metrics

### 5. **Cleanup & Management**
- Automatic container lifecycle management
- Old container cleanup (24h default)
- Resource tracking and monitoring
- Container inventory management

## Architecture

```
services/digital-twin/
├── core/                   # Core components
│   ├── container.py        # Docker container management
│   └── twin.py             # Digital twin orchestrator
├── executors/              # Execution engines
│   └── patch_executor.py   # Patch execution logic
├── validators/             # Validation & testing
│   ├── health_checks.py    # Health check implementations
│   └── test_suite.py       # Customizable test suites
├── analyzers/              # Result analysis
│   └── result_analyzer.py  # Test result analysis & reporting
└── tasks/                  # Async tasks
    ├── celery_app.py       # Celery configuration
    └── testing_tasks.py    # Celery testing tasks
```

## Usage

### Basic Usage

```python
from services.digital_twin.core.twin import DigitalTwin
from shared.models import Asset, Patch

# Get asset and patch
asset = db.query(Asset).filter(Asset.id == asset_id).first()
patch = db.query(Patch).filter(Patch.id == patch_id).first()

# Create digital twin
twin = DigitalTwin(asset=asset, patch=patch)

# Provision environment
if twin.provision():
    # Execute patch
    result = twin.execute_patch()
    
    # Run health checks
    health = twin.run_health_checks()
    
    # Cleanup
    twin.cleanup()
```

### Context Manager Usage

```python
from services.digital_twin.core.twin import DigitalTwin

# Automatic provision and cleanup
with DigitalTwin(asset=asset, patch=patch) as twin:
    # Execute patch
    exec_result = twin.execute_patch()
    
    # Run health checks
    health_result = twin.run_health_checks()
    
    # Results available
    if exec_result.success and health_result["overall_passed"]:
        print("✅ Patch test PASSED")
    else:
        print("❌ Patch test FAILED")
```

### Using Celery Tasks

```python
from services.digital_twin.tasks.testing_tasks import test_patch_in_digital_twin

# Trigger async testing
task = test_patch_in_digital_twin.delay(
    patch_id=123,
    asset_id=456
)

# Get result
result = task.get(timeout=1800)  # 30 min timeout
print(f"Test status: {result['status']}")
print(f"Confidence: {result['confidence_score']}%")
```

### Custom Test Suites

```python
from services.digital_twin.validators.test_suite import TestSuite
from services.digital_twin.validators.health_checks import HealthCheckResult

# Create custom test suite
suite = TestSuite(asset_type="web_server")

# Add custom test
def check_custom_service(container):
    result = container.exec_run("systemctl is-active my-service")
    return HealthCheckResult(
        name="custom_service_check",
        passed=(result.exit_code == 0),
        message="Custom service is running"
    )

suite.add_test(check_custom_service, "custom_service")

# Execute suite
results = suite.execute(container)
```

## Configuration

### Environment Variables

```bash
# Celery (for async tasks)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Docker (uses local Docker daemon by default)
DOCKER_HOST=unix:///var/run/docker.sock
```

### Resource Limits

Default container limits (configurable):
- **CPU**: 2 cores
- **Memory**: 4GB
- **Timeout**: 10 minutes for patch execution
- **Container TTL**: 24 hours (auto-cleanup)

## API Integration

### Trigger Testing from API

```python
# In API endpoint
from services.digital_twin.tasks.testing_tasks import test_patch_in_digital_twin

@router.post("/patches/{patch_id}/test")
async def test_patch(
    patch_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("operator"))
):
    """Trigger digital twin testing for a patch"""
    
    # Verify patch and asset exist
    patch = db.query(Patch).filter(Patch.id == patch_id).first()
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    
    if not patch or not asset:
        raise HTTPException(status_code=404, detail="Patch or Asset not found")
    
    # Trigger async testing
    task = test_patch_in_digital_twin.delay(patch_id=patch_id, asset_id=asset_id)
    
    return {
        "message": "Testing started",
        "task_id": task.id,
        "patch_id": patch_id,
        "asset_id": asset_id
    }
```

## Health Check Types

### Port Checks
```python
check_port_listening(container, 80)   # HTTP
check_port_listening(container, 443)  # HTTPS
check_port_listening(container, 22)   # SSH
check_port_listening(container, 3306) # MySQL
```

### Service Checks
```python
check_service_running(container, "nginx")
check_service_running(container, "mysql")
check_service_running(container, "ssh")
```

### HTTP Checks
```python
check_http_endpoint(container, "http://localhost")
check_http_endpoint(container, "http://localhost/health")
```

### Process Checks
```python
check_process_running(container, "nginx")
check_process_running(container, "mysqld")
```

### Package Checks
```python
check_package_installed(container, "nginx")
check_package_installed(container, "openssl")
```

## Test Result Structure

```python
{
    "patch_id": 123,
    "asset_id": 456,
    "test_id": "twin-456-123-20250117120000",
    "status": "passed",  # passed, failed, error
    "overall_passed": True,
    "confidence_score": 85.5,
    "duration_seconds": 45.2,
    
    "patch_execution": {
        "exit_code": 0,
        "success": True,
        "stdout": "...",
        "stderr": "",
        "duration_seconds": 12.5
    },
    
    "health_checks": {
        "overall_passed": True,
        "success_rate": 90.0,
        "total_checks": 10,
        "passed_checks": 9,
        "failed_checks": 1,
        "results": [...]
    },
    
    "issues": [],
    "warnings": ["Patch execution produced stderr output"],
    
    "container_logs": "...",
    "system_state_before": {...},
    "system_state_after": {...}
}
```

## Troubleshooting

### Docker Connection Issues

```bash
# Check Docker daemon is running
sudo systemctl status docker

# Test Docker connection
docker ps

# Check permissions
sudo usermod -aG docker $USER
```

### Container Provisioning Failures

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check available images
from services.digital_twin.core.container import ContainerManager
manager = ContainerManager()
print(manager.IMAGES)
```

### Cleanup Stuck Containers

```python
from services.digital_twin.tasks.testing_tasks import cleanup_old_twins

# Force cleanup all containers
cleanup_old_twins.delay(max_age_hours=0)
```

## Performance Considerations

- **Parallel Testing**: Multiple patches can be tested simultaneously
- **Resource Limits**: Prevents system overload (2 CPU, 4GB RAM per container)
- **Automatic Cleanup**: Removes old containers to free resources
- **Worker Limits**: Celery workers restart after 20 tasks to prevent memory leaks

## Security

- **Network Isolation**: Containers run in isolated networks
- **No Host Access**: Containers cannot access host filesystem
- **Resource Limits**: CPU and memory limits prevent DoS
- **Auto-Cleanup**: Containers automatically removed after testing
- **Audit Logging**: All test actions logged for compliance

## Monitoring

Key metrics to track:
- Test success rate
- Average test duration
- Container resource usage
- Health check pass rates
- Active container count

## Future Enhancements

- [ ] Support for Windows containers (PowerShell patches)
- [ ] Kubernetes pod-based testing
- [ ] Performance regression testing
- [ ] Screenshot capability for web services
- [ ] Database state comparison
- [ ] Network traffic monitoring
- [ ] Security scanning during testing

## Dependencies

All dependencies already in requirements.txt:
- `docker==6.1.3` (line 55)
- `python-docker==6.1.3` (line 56)
- `celery==5.3.4` (line 25)
- `redis==5.0.1` (line 24)
- `pydantic==2.5.0` (line 9)

## Examples

See `/examples/digital_twin_examples.py` for complete working examples.

## Support

For issues or questions:
- Check logs: Container logs captured in test results
- Enable debug logging: `logging.basicConfig(level=logging.DEBUG)`
- Review Docker logs: `docker logs <container_name>`
