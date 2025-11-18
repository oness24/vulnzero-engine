# VulnZero Deployment Orchestrator

Production-grade deployment engine with multiple deployment strategies, pre/post validation, Ansible integration, and automatic rollback.

## Overview

The Deployment Orchestrator manages the safe deployment of patches to production assets with:
- Multiple deployment strategies (blue-green, rolling, canary, all-at-once)
- Pre-deployment validation
- Ansible-based remote execution
- Post-deployment health checks
- Automatic rollback on failure
- Real-time monitoring and logging

## Features

### 1. **Deployment Strategies**

#### All-At-Once
- Deploys to all assets simultaneously
- Fastest deployment method
- Best for dev/test environments
- High risk for production

#### Rolling Update
- Gradual deployment in batches
- Configurable batch size (default: 20%)
- Wait time between batches
- Automatic stop on failure
- Zero downtime deployments

#### Canary Deployment
- Progressive rollout: 10% → 50% → 100%
- Monitoring between stages
- Automatic promotion on success
- Quick rollback if issues detected
- Ideal for critical production systems

#### Blue-Green Deployment
- Deploy to inactive environment ("green")
- Test green environment
- Switch traffic from blue to green
- Keep blue for instant rollback
- True zero-downtime deployments

### 2. **Pre-Deployment Checks**
- ✅ Patch test status validation (must pass digital twin testing)
- ✅ Asset connectivity checks (SSH/WinRM)
- ✅ Maintenance window validation
- ✅ Backup verification
- ✅ Dependency checks
- ✅ Resource availability

### 3. **Ansible Integration**
- Dynamic playbook generation
- Inventory management from database
- Vault support for secrets
- Real-time execution logs
- Idempotent operations
- Error handling and retries

### 4. **Post-Deployment Validation**
- Health checks on deployed assets
- Service availability verification
- Vulnerability re-scan
- Metrics comparison (before/after)
- Performance validation

### 5. **Rollback Mechanism**
- Automatic rollback on failure
- Manual rollback trigger
- Rollback script execution
- State restoration
- Notification system

### 6. **Deployment Scheduling**
- Maintenance window respect
- Rate limiting
- Priority queue (critical first)
- Batch grouping
- Concurrent deployment limits

## Architecture

```
services/deployment-orchestrator/
├── core/
│   ├── engine.py           # Main deployment orchestrator
│   └── scheduler.py        # Deployment scheduling
├── strategies/
│   ├── base.py             # Abstract base strategy
│   ├── all_at_once.py      # All-at-once deployment
│   ├── rolling.py          # Rolling update
│   ├── canary.py           # Canary deployment
│   └── blue_green.py       # Blue-green deployment
├── ansible/
│   ├── executor.py         # Ansible execution
│   ├── playbook_generator.py  # Dynamic playbook creation
│   └── inventory.py        # Inventory management
├── validators/
│   ├── pre_deploy.py       # Pre-deployment checks
│   └── post_deploy.py      # Post-deployment validation
└── tasks/
    ├── celery_app.py       # Celery configuration
    └── deployment_tasks.py # Async deployment tasks
```

## Usage

### Basic Deployment

```python
from services.deployment_orchestrator.core.engine import DeploymentEngine
from services.deployment_orchestrator.strategies.rolling import RollingDeployment

# Get assets and patch
assets = db.query(Asset).filter(Asset.vulnerability_id == vuln_id).all()
patch = db.query(Patch).filter(Patch.id == patch_id).first()

# Create deployment engine
engine = DeploymentEngine(patch=patch, assets=assets)

# Run pre-deployment checks
checks = engine.pre_deploy_checks()
if not checks.passed:
    print(f"Pre-deploy checks failed: {checks.errors}")
    return

# Deploy with rolling strategy
strategy = RollingDeployment(patch=patch, batch_size=0.2, wait_seconds=60)
result = engine.deploy(strategy=strategy)

if result.success:
    print(f"✅ Deployed to {len(result.assets_deployed)} assets")
else:
    print(f"❌ Deployment failed: {result.error_message}")
```

### Using Celery Tasks

```python
from services.deployment_orchestrator.tasks.deployment_tasks import deploy_patch

# Trigger async deployment
task = deploy_patch.delay(
    patch_id=123,
    asset_ids=[1, 2, 3],
    strategy="rolling",
    strategy_params={"batch_size": 0.2, "wait_seconds": 60}
)

# Monitor progress
result = task.get(timeout=3600)  # 1 hour timeout
```

### Canary Deployment Example

```python
from services.deployment_orchestrator.strategies.canary import CanaryDeployment

# Canary with monitoring
strategy = CanaryDeployment(
    patch=patch,
    stages=[0.1, 0.5, 1.0],  # 10%, 50%, 100%
    monitoring_duration=900,  # 15 minutes between stages
    auto_promote=True
)

result = engine.deploy(strategy=strategy)
```

### Manual Rollback

```python
# Rollback deployment
rollback_result = engine.rollback(deployment_id=456)

if rollback_result.success:
    print("✅ Rollback completed successfully")
```

## Configuration

### Environment Variables

```bash
# Ansible
ANSIBLE_HOST_KEY_CHECKING=False
ANSIBLE_TIMEOUT=300

# Deployment
MAX_CONCURRENT_DEPLOYMENTS=5
DEFAULT_BATCH_SIZE=0.2
DEFAULT_WAIT_TIME=60

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Strategy Parameters

#### Rolling Update
```python
{
    "batch_size": 0.2,          # 20% of assets per batch
    "wait_seconds": 60,         # Wait between batches
    "max_failures": 2,          # Stop after N failures
    "continue_on_error": False  # Stop on first error
}
```

#### Canary
```python
{
    "stages": [0.1, 0.5, 1.0],      # Deployment stages
    "monitoring_duration": 900,      # Seconds to monitor
    "auto_promote": True,            # Auto-proceed if healthy
    "rollback_on_failure": True      # Auto-rollback on issues
}
```

## API Integration

Add to `services/api-gateway/api/v1/endpoints/deployments.py`:

```python
@router.post("/deploy")
async def deploy_patch(
    patch_id: int,
    asset_ids: List[int],
    strategy: str = "rolling",
    strategy_params: Dict[str, Any] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("operator"))
):
    """Deploy patch to production assets"""
    from services.deployment_orchestrator.tasks.deployment_tasks import deploy_patch
    
    task = deploy_patch.delay(
        patch_id=patch_id,
        asset_ids=asset_ids,
        strategy=strategy,
        strategy_params=strategy_params or {}
    )
    
    return {
        "message": "Deployment started",
        "task_id": task.id,
        "patch_id": patch_id,
        "assets": len(asset_ids),
        "strategy": strategy
    }
```

## Ansible Playbook Example

Generated playbook for package update:

```yaml
---
- name: Deploy patch for CVE-2024-12345
  hosts: affected_servers
  become: yes
  serial: "20%"  # Rolling deployment
  max_fail_percentage: 5
  
  tasks:
    - name: Backup package state
      shell: dpkg -l > /var/backups/vulnzero_{{ patch_id }}_{{ ansible_date_time.epoch }}.txt
      
    - name: Update package cache
      apt:
        update_cache: yes
        cache_valid_time: 3600
        
    - name: Install patch
      apt:
        name: "{{ package_name }}={{ fixed_version }}"
        state: present
        
    - name: Restart service
      systemd:
        name: "{{ service_name }}"
        state: restarted
        
    - name: Wait for service
      wait_for:
        port: "{{ service_port }}"
        timeout: 60
        
    - name: Verify service health
      uri:
        url: "http://localhost:{{ service_port }}/health"
        status_code: 200
      register: health_check
      retries: 3
      delay: 10
```

## Deployment Flow

```
1. API Request
   ↓
2. Pre-Deployment Checks
   ├─ Test status ✓
   ├─ Connectivity ✓
   ├─ Maintenance window ✓
   └─ Backups ✓
   ↓
3. Strategy Selection
   ↓
4. Ansible Playbook Generation
   ↓
5. Deployment Execution
   ├─ Batch 1 (20%)
   ├─ Monitor & Wait
   ├─ Batch 2 (20%)
   ├─ Monitor & Wait
   └─ Continue...
   ↓
6. Post-Deployment Validation
   ├─ Health checks
   ├─ Metrics comparison
   └─ Vulnerability scan
   ↓
7. Success/Rollback Decision
   ↓
8. Database Update & Audit Log
   ↓
9. Notification (Slack/Email)
```

## Monitoring & Alerts

### Metrics Tracked
- Deployment success rate
- Average deployment duration
- Assets deployed per hour
- Rollback frequency
- Strategy usage distribution

### Alerts
- Deployment failures
- Rollback triggered
- Extended deployment duration
- Asset connectivity issues
- Post-deployment health check failures

## Troubleshooting

### Deployment Hangs

```python
# Check active deployments
from services.deployment_orchestrator.core.engine import DeploymentEngine

active = DeploymentEngine.get_active_deployments()
print(f"Active: {len(active)}")

# Cancel stuck deployment
DeploymentEngine.cancel_deployment(deployment_id)
```

### Ansible Connection Issues

```bash
# Test connectivity
ansible -i inventory.ini all -m ping

# Check SSH access
ssh -i /path/to/key user@host

# Verify Ansible installation
ansible --version
```

### Rollback Failures

```python
# Manual rollback execution
from services.deployment_orchestrator.ansible.executor import AnsibleExecutor

executor = AnsibleExecutor()
result = executor.execute_rollback(asset, patch)
```

## Security Considerations

- **SSH Key Management**: Secure storage of deployment keys
- **Vault Integration**: Ansible Vault for secrets
- **Audit Logging**: All deployments logged
- **RBAC**: Role-based access (operator/admin only)
- **Idempotent**: Safe to retry deployments
- **Network Isolation**: Deployment network separation

## Performance

- **Concurrent Limit**: 5 deployments max (configurable)
- **Batch Size**: 20% default (rolling)
- **Wait Time**: 60 seconds between batches
- **Timeout**: 5 minutes per asset
- **Ansible Forks**: 10 parallel executions

## Dependencies

All in requirements.txt:
- `ansible==9.0.1` (line 61)
- `ansible-runner==2.3.4` (line 62)
- `ansible-core==2.16.0` (line 63)
- `celery==5.3.4` (line 25)
- `redis==5.0.1` (line 24)
- `paramiko==3.4.0` (line 163)
- `fabric==3.2.2` (line 164)

## Future Enhancements

- [ ] Kubernetes deployment support
- [ ] Terraform integration
- [ ] Multi-region deployments
- [ ] A/B testing integration
- [ ] Cost optimization algorithms
- [ ] ML-based deployment timing
- [ ] Automated rollback decisions

## Support

For detailed implementation, see individual module documentation:
- Strategies: `strategies/README.md`
- Ansible: `ansible/README.md`
- Validators: `validators/README.md`
