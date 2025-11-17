"""Initial schema - Create all VulnZero database tables

Revision ID: 001_initial
Revises:
Create Date: 2024-11-17 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all VulnZero database tables"""

    # ========================================================================
    # Create ENUM types
    # ========================================================================
    vulnerability_status = postgresql.ENUM(
        'new', 'analyzing', 'patch_generated', 'testing', 'pending_approval',
        'approved', 'deploying', 'deployed', 'remediated', 'failed', 'ignored',
        name='vulnerabilitystatus'
    )
    vulnerability_status.create(op.get_bind())

    vulnerability_severity = postgresql.ENUM(
        'critical', 'high', 'medium', 'low', 'info',
        name='vulnerabilityseverity'
    )
    vulnerability_severity.create(op.get_bind())

    asset_type = postgresql.ENUM(
        'server', 'container', 'cloud', 'network_device', 'database', 'application', 'other',
        name='assettype'
    )
    asset_type.create(op.get_bind())

    asset_status = postgresql.ENUM(
        'active', 'inactive', 'maintenance', 'decommissioned',
        name='assetstatus'
    )
    asset_status.create(op.get_bind())

    patch_type = postgresql.ENUM(
        'package_update', 'config_change', 'script_execution', 'workaround', 'manual',
        name='patchtype'
    )
    patch_type.create(op.get_bind())

    patch_status = postgresql.ENUM(
        'generated', 'validated', 'testing', 'test_passed', 'test_failed',
        'approved', 'rejected', 'deployed', 'failed', 'rolled_back',
        name='patchstatus'
    )
    patch_status.create(op.get_bind())

    deployment_status = postgresql.ENUM(
        'pending', 'scheduled', 'pre_check_running', 'pre_check_passed', 'pre_check_failed',
        'deploying', 'success', 'failed', 'rolling_back', 'rolled_back', 'cancelled',
        name='deploymentstatus'
    )
    deployment_status.create(op.get_bind())

    deployment_strategy = postgresql.ENUM(
        'blue_green', 'canary', 'rolling', 'all_at_once',
        name='deploymentstrategy'
    )
    deployment_strategy.create(op.get_bind())

    audit_action = postgresql.ENUM(
        'vulnerability_discovered', 'vulnerability_updated', 'vulnerability_remediated', 'vulnerability_ignored',
        'patch_generated', 'patch_validated', 'patch_tested', 'patch_approved', 'patch_rejected',
        'deployment_scheduled', 'deployment_started', 'deployment_completed', 'deployment_failed',
        'deployment_rolled_back', 'deployment_cancelled',
        'asset_registered', 'asset_updated', 'asset_scanned', 'asset_decommissioned',
        'user_login', 'user_logout', 'user_created', 'user_updated', 'user_deleted',
        'config_changed', 'scanner_configured', 'settings_updated',
        'permission_granted', 'permission_revoked', 'access_denied', 'auth_failed',
        'system_started', 'system_stopped', 'backup_created', 'restore_performed',
        name='auditaction'
    )
    audit_action.create(op.get_bind())

    audit_resource_type = postgresql.ENUM(
        'vulnerability', 'asset', 'patch', 'deployment', 'user', 'scanner',
        'configuration', 'system', 'remediation_job',
        name='auditresourcetype'
    )
    audit_resource_type.create(op.get_bind())

    job_type = postgresql.ENUM(
        'vulnerability_scan', 'vulnerability_enrichment', 'priority_calculation',
        'patch_generation', 'patch_validation', 'digital_twin_test', 'deployment',
        'post_deployment_monitoring', 'rollback', 'asset_discovery',
        'report_generation', 'data_cleanup', 'ml_model_training',
        name='jobtype'
    )
    job_type.create(op.get_bind())

    job_status = postgresql.ENUM(
        'pending', 'queued', 'running', 'success', 'failed', 'cancelled', 'retrying', 'timeout',
        name='jobstatus'
    )
    job_status.create(op.get_bind())

    job_priority = postgresql.ENUM(
        'critical', 'high', 'normal', 'low',
        name='jobpriority'
    )
    job_priority.create(op.get_bind())

    # ========================================================================
    # Create vulnerabilities table
    # ========================================================================
    op.create_table(
        'vulnerabilities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('cve_id', sa.String(length=50), nullable=False, comment='CVE identifier'),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('severity', vulnerability_severity, nullable=False),
        sa.Column('cvss_score', sa.Float(), nullable=True),
        sa.Column('cvss_vector', sa.String(length=200), nullable=True),
        sa.Column('epss_score', sa.Float(), nullable=True),
        sa.Column('priority_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('status', vulnerability_status, nullable=False, server_default='new'),
        sa.Column('discovered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('remediated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('affected_package', sa.String(length=200), nullable=True),
        sa.Column('affected_version', sa.String(length=100), nullable=True),
        sa.Column('fixed_version', sa.String(length=100), nullable=True),
        sa.Column('scanner_source', sa.String(length=100), nullable=False),
        sa.Column('scanner_id', sa.String(length=200), nullable=True),
        sa.Column('raw_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('exploit_available', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('exploit_urls', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('references', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('cwe_ids', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('business_criticality', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('public_exposure', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('assigned_to', sa.String(length=200), nullable=True),
        sa.Column('approved_by', sa.String(length=200), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('cvss_score >= 0.0 AND cvss_score <= 10.0', name='check_cvss_range'),
        sa.CheckConstraint('epss_score >= 0.0 AND epss_score <= 1.0', name='check_epss_range'),
        sa.CheckConstraint('priority_score >= 0.0 AND priority_score <= 100.0', name='check_priority_range'),
        sa.CheckConstraint('business_criticality >= 1 AND business_criticality <= 10', name='check_criticality_range'),
        comment='Stores detected vulnerabilities from various scanners with enrichment data'
    )

    # Create indexes for vulnerabilities
    op.create_index('ix_vulnerabilities_id', 'vulnerabilities', ['id'])
    op.create_index('ix_vulnerabilities_cve_id', 'vulnerabilities', ['cve_id'])
    op.create_index('ix_vulnerabilities_severity', 'vulnerabilities', ['severity'])
    op.create_index('ix_vulnerabilities_status', 'vulnerabilities', ['status'])
    op.create_index('ix_vulnerabilities_priority_score', 'vulnerabilities', ['priority_score'])
    op.create_index('ix_vulnerabilities_discovered_at', 'vulnerabilities', ['discovered_at'])
    op.create_index('ix_vulnerabilities_remediated_at', 'vulnerabilities', ['remediated_at'])
    op.create_index('ix_vulnerabilities_affected_package', 'vulnerabilities', ['affected_package'])
    op.create_index('ix_vulnerabilities_scanner_source', 'vulnerabilities', ['scanner_source'])
    op.create_index('ix_vuln_status_severity', 'vulnerabilities', ['status', 'severity'])
    op.create_index('ix_vuln_status_priority', 'vulnerabilities', ['status', 'priority_score'])
    op.create_index('ix_vuln_discovered_status', 'vulnerabilities', ['discovered_at', 'status'])
    op.create_index('ix_vuln_cve_scanner', 'vulnerabilities', ['cve_id', 'scanner_source'])

    # ========================================================================
    # Create assets table
    # ========================================================================
    op.create_table(
        'assets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('asset_id', sa.String(length=200), nullable=False, unique=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('type', asset_type, nullable=False),
        sa.Column('status', asset_status, nullable=False, server_default='active'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('hostname', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('mac_address', sa.String(length=17), nullable=True),
        sa.Column('os_type', sa.String(length=100), nullable=True),
        sa.Column('os_name', sa.String(length=100), nullable=True),
        sa.Column('os_version', sa.String(length=100), nullable=True),
        sa.Column('kernel_version', sa.String(length=100), nullable=True),
        sa.Column('architecture', sa.String(length=50), nullable=True),
        sa.Column('cloud_provider', sa.String(length=50), nullable=True),
        sa.Column('cloud_region', sa.String(length=50), nullable=True),
        sa.Column('cloud_instance_id', sa.String(length=200), nullable=True),
        sa.Column('container_image', sa.String(length=500), nullable=True),
        sa.Column('container_id', sa.String(length=100), nullable=True),
        sa.Column('location', sa.String(length=200), nullable=True),
        sa.Column('environment', sa.String(length=50), nullable=True),
        sa.Column('business_unit', sa.String(length=200), nullable=True),
        sa.Column('owner', sa.String(length=200), nullable=True),
        sa.Column('cost_center', sa.String(length=100), nullable=True),
        sa.Column('criticality', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('is_public_facing', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('compliance_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_scanned', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scan_frequency', sa.Integer(), nullable=False, server_default='6'),
        sa.Column('vulnerability_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('critical_vuln_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('high_vuln_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ssh_port', sa.Integer(), nullable=True),
        sa.Column('ssh_user', sa.String(length=100), nullable=True),
        sa.Column('ansible_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('installed_packages', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('running_services', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('criticality >= 1 AND criticality <= 10', name='check_asset_criticality_range'),
        sa.CheckConstraint('scan_frequency > 0', name='check_scan_frequency_positive'),
        sa.CheckConstraint('vulnerability_count >= 0', name='check_vuln_count_non_negative'),
        comment='Stores infrastructure assets (servers, containers, cloud resources)'
    )

    # Create indexes for assets
    op.create_index('ix_assets_id', 'assets', ['id'])
    op.create_index('ix_assets_asset_id', 'assets', ['asset_id'], unique=True)
    op.create_index('ix_assets_type', 'assets', ['type'])
    op.create_index('ix_assets_status', 'assets', ['status'])
    op.create_index('ix_assets_hostname', 'assets', ['hostname'])
    op.create_index('ix_assets_ip_address', 'assets', ['ip_address'])
    op.create_index('ix_assets_os_type', 'assets', ['os_type'])
    op.create_index('ix_assets_cloud_provider', 'assets', ['cloud_provider'])
    op.create_index('ix_assets_environment', 'assets', ['environment'])
    op.create_index('ix_assets_is_public_facing', 'assets', ['is_public_facing'])
    op.create_index('ix_assets_last_scanned', 'assets', ['last_scanned'])
    op.create_index('ix_asset_type_status', 'assets', ['type', 'status'])
    op.create_index('ix_asset_env_criticality', 'assets', ['environment', 'criticality'])
    op.create_index('ix_asset_os_type_version', 'assets', ['os_type', 'os_version'])
    op.create_index('ix_asset_public_facing_env', 'assets', ['is_public_facing', 'environment'])

    # ========================================================================
    # Create patches table
    # ========================================================================
    op.create_table(
        'patches',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('vulnerability_id', sa.Integer(), nullable=False),
        sa.Column('patch_type', patch_type, nullable=False),
        sa.Column('status', patch_status, nullable=False, server_default='generated'),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('patch_content', sa.Text(), nullable=False),
        sa.Column('patch_language', sa.String(length=50), nullable=False, server_default='bash'),
        sa.Column('rollback_script', sa.Text(), nullable=True),
        sa.Column('llm_provider', sa.String(length=50), nullable=False),
        sa.Column('llm_model', sa.String(length=100), nullable=False),
        sa.Column('llm_prompt', sa.Text(), nullable=True),
        sa.Column('llm_response', sa.Text(), nullable=True),
        sa.Column('generation_time_seconds', sa.Float(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('validation_passed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('validation_errors', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('safety_checks', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('test_status', sa.String(length=50), nullable=True),
        sa.Column('test_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('test_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('test_duration_seconds', sa.Float(), nullable=True),
        sa.Column('test_results', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('test_logs', sa.Text(), nullable=True),
        sa.Column('deployment_method', sa.String(length=50), nullable=True),
        sa.Column('deployment_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failure_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rollback_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('requires_approval', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('approved_by', sa.String(length=200), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_by', sa.String(length=200), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_template', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('template_category', sa.String(length=100), nullable=True),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['vulnerability_id'], ['vulnerabilities.id'], ondelete='CASCADE'),
        sa.CheckConstraint('confidence_score >= 0.0 AND confidence_score <= 100.0', name='check_patch_confidence_range'),
        sa.CheckConstraint('version >= 1', name='check_patch_version_positive'),
        sa.CheckConstraint('deployment_count >= 0', name='check_deployment_count_non_negative'),
        sa.CheckConstraint('success_count >= 0', name='check_success_count_non_negative'),
        sa.CheckConstraint('failure_count >= 0', name='check_failure_count_non_negative'),
        comment='Stores AI-generated patches for vulnerability remediation'
    )

    # Create indexes for patches
    op.create_index('ix_patches_id', 'patches', ['id'])
    op.create_index('ix_patches_vulnerability_id', 'patches', ['vulnerability_id'])
    op.create_index('ix_patches_patch_type', 'patches', ['patch_type'])
    op.create_index('ix_patches_status', 'patches', ['status'])
    op.create_index('ix_patches_confidence_score', 'patches', ['confidence_score'])
    op.create_index('ix_patches_test_status', 'patches', ['test_status'])
    op.create_index('ix_patch_vuln_status', 'patches', ['vulnerability_id', 'status'])
    op.create_index('ix_patch_type_status', 'patches', ['patch_type', 'status'])
    op.create_index('ix_patch_confidence_status', 'patches', ['confidence_score', 'status'])

    # ========================================================================
    # Create deployments table
    # ========================================================================
    op.create_table(
        'deployments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('patch_id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('deployment_id', sa.String(length=100), nullable=False, unique=True),
        sa.Column('status', deployment_status, nullable=False, server_default='pending'),
        sa.Column('strategy', deployment_strategy, nullable=False, server_default='all_at_once'),
        sa.Column('deployment_method', sa.String(length=100), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('pre_check_passed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('pre_check_results', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('pre_check_errors', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('execution_logs', sa.Text(), nullable=True),
        sa.Column('exit_code', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('post_validation_passed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('post_validation_results', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('baseline_metrics', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('post_deployment_metrics', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('anomalies_detected', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('monitoring_duration_seconds', sa.Integer(), nullable=False, server_default='900'),
        sa.Column('rollback_needed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('rollback_reason', sa.String(length=500), nullable=True),
        sa.Column('rollback_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rollback_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rollback_logs', sa.Text(), nullable=True),
        sa.Column('rollback_success', sa.Boolean(), nullable=True),
        sa.Column('canary_percentage', sa.Integer(), nullable=True),
        sa.Column('canary_phase', sa.Integer(), nullable=True),
        sa.Column('canary_wait_time', sa.Integer(), nullable=True),
        sa.Column('requires_approval', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('approved_by', sa.String(length=200), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('executed_by', sa.String(length=200), nullable=False, server_default='system'),
        sa.Column('cancelled_by', sa.String(length=200), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('backup_created', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('backup_location', sa.String(length=500), nullable=True),
        sa.Column('backup_size_bytes', sa.Integer(), nullable=True),
        sa.Column('notifications_sent', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('parent_deployment_id', sa.Integer(), nullable=True),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['patch_id'], ['patches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_deployment_id'], ['deployments.id'], ondelete='SET NULL'),
        sa.CheckConstraint('retry_count >= 0', name='check_retry_count_non_negative'),
        sa.CheckConstraint('duration_seconds >= 0', name='check_duration_non_negative'),
        sa.CheckConstraint(
            'canary_percentage IS NULL OR (canary_percentage >= 0 AND canary_percentage <= 100)',
            name='check_canary_percentage_range'
        ),
        comment='Stores deployment history and tracking information'
    )

    # Create indexes for deployments
    op.create_index('ix_deployments_id', 'deployments', ['id'])
    op.create_index('ix_deployments_deployment_id', 'deployments', ['deployment_id'], unique=True)
    op.create_index('ix_deployments_patch_id', 'deployments', ['patch_id'])
    op.create_index('ix_deployments_asset_id', 'deployments', ['asset_id'])
    op.create_index('ix_deployments_status', 'deployments', ['status'])
    op.create_index('ix_deployments_scheduled_at', 'deployments', ['scheduled_at'])
    op.create_index('ix_deployments_started_at', 'deployments', ['started_at'])
    op.create_index('ix_deployments_completed_at', 'deployments', ['completed_at'])
    op.create_index('ix_deployment_patch_status', 'deployments', ['patch_id', 'status'])
    op.create_index('ix_deployment_asset_status', 'deployments', ['asset_id', 'status'])
    op.create_index('ix_deployment_status_started', 'deployments', ['status', 'started_at'])
    op.create_index('ix_deployment_strategy_status', 'deployments', ['strategy', 'status'])

    # ========================================================================
    # Create audit_logs table
    # ========================================================================
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('action', audit_action, nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actor_type', sa.String(length=50), nullable=False),
        sa.Column('actor_id', sa.String(length=200), nullable=False),
        sa.Column('actor_name', sa.String(length=200), nullable=True),
        sa.Column('actor_ip', sa.String(length=45), nullable=True),
        sa.Column('actor_user_agent', sa.String(length=500), nullable=True),
        sa.Column('resource_type', audit_resource_type, nullable=False),
        sa.Column('resource_id', sa.String(length=200), nullable=False),
        sa.Column('resource_name', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('success', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('changes', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('request_id', sa.String(length=100), nullable=True),
        sa.Column('request_method', sa.String(length=10), nullable=True),
        sa.Column('request_path', sa.String(length=1000), nullable=True),
        sa.Column('request_params', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='info'),
        sa.Column('requires_attention', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('compliance_relevant', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('retention_period_days', sa.Integer(), nullable=False, server_default='2555'),
        sa.PrimaryKeyConstraint('id'),
        comment='Immutable audit trail for all system actions'
    )

    # Create indexes for audit_logs
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('ix_audit_logs_actor_type', 'audit_logs', ['actor_type'])
    op.create_index('ix_audit_logs_actor_id', 'audit_logs', ['actor_id'])
    op.create_index('ix_audit_logs_actor_ip', 'audit_logs', ['actor_ip'])
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'])
    op.create_index('ix_audit_logs_resource_id', 'audit_logs', ['resource_id'])
    op.create_index('ix_audit_logs_success', 'audit_logs', ['success'])
    op.create_index('ix_audit_logs_severity', 'audit_logs', ['severity'])
    op.create_index('ix_audit_logs_requires_attention', 'audit_logs', ['requires_attention'])
    op.create_index('ix_audit_logs_compliance_relevant', 'audit_logs', ['compliance_relevant'])
    op.create_index('ix_audit_timestamp_action', 'audit_logs', ['timestamp', 'action'])
    op.create_index('ix_audit_actor_timestamp', 'audit_logs', ['actor_id', 'timestamp'])
    op.create_index('ix_audit_resource_timestamp', 'audit_logs', ['resource_type', 'resource_id', 'timestamp'])
    op.create_index('ix_audit_action_success', 'audit_logs', ['action', 'success'])
    op.create_index('ix_audit_severity_timestamp', 'audit_logs', ['severity', 'timestamp'])
    op.create_index('ix_audit_request_id', 'audit_logs', ['request_id'])

    # ========================================================================
    # Create remediation_jobs table
    # ========================================================================
    op.create_table(
        'remediation_jobs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('job_id', sa.String(length=100), nullable=False, unique=True),
        sa.Column('job_type', job_type, nullable=False),
        sa.Column('job_name', sa.String(length=200), nullable=False),
        sa.Column('status', job_status, nullable=False, server_default='pending'),
        sa.Column('priority', job_priority, nullable=False, server_default='normal'),
        sa.Column('priority_score', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('created_at_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('queued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='3600'),
        sa.Column('progress_percent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('progress_message', sa.String(length=500), nullable=True),
        sa.Column('steps_total', sa.Integer(), nullable=True),
        sa.Column('steps_completed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('worker_id', sa.String(length=200), nullable=True),
        sa.Column('worker_hostname', sa.String(length=200), nullable=True),
        sa.Column('queue_name', sa.String(length=100), nullable=False, server_default='default'),
        sa.Column('input_params', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('result', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_traceback', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('retry_delay_seconds', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('last_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('parent_job_id', sa.String(length=100), nullable=True),
        sa.Column('depends_on', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('vulnerability_id', sa.Integer(), nullable=True),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('patch_id', sa.Integer(), nullable=True),
        sa.Column('deployment_id', sa.Integer(), nullable=True),
        sa.Column('cpu_time_seconds', sa.Float(), nullable=True),
        sa.Column('memory_peak_mb', sa.Integer(), nullable=True),
        sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_periodic', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('cron_expression', sa.String(length=100), nullable=True),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('logs', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('notify_on_completion', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notification_sent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notification_channels', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('progress_percent >= 0 AND progress_percent <= 100', name='check_progress_range'),
        sa.CheckConstraint('priority_score >= 0 AND priority_score <= 9', name='check_priority_range'),
        sa.CheckConstraint('retry_count >= 0', name='check_retry_count_non_negative'),
        sa.CheckConstraint('max_retries >= 0', name='check_max_retries_non_negative'),
        sa.CheckConstraint('steps_completed >= 0', name='check_steps_completed_non_negative'),
        comment='Tracks async remediation jobs processed by Celery workers'
    )

    # Create indexes for remediation_jobs
    op.create_index('ix_remediation_jobs_id', 'remediation_jobs', ['id'])
    op.create_index('ix_remediation_jobs_job_id', 'remediation_jobs', ['job_id'], unique=True)
    op.create_index('ix_remediation_jobs_job_type', 'remediation_jobs', ['job_type'])
    op.create_index('ix_remediation_jobs_status', 'remediation_jobs', ['status'])
    op.create_index('ix_remediation_jobs_priority', 'remediation_jobs', ['priority'])
    op.create_index('ix_remediation_jobs_created_at_timestamp', 'remediation_jobs', ['created_at_timestamp'])
    op.create_index('ix_remediation_jobs_started_at', 'remediation_jobs', ['started_at'])
    op.create_index('ix_remediation_jobs_completed_at', 'remediation_jobs', ['completed_at'])
    op.create_index('ix_remediation_jobs_worker_id', 'remediation_jobs', ['worker_id'])
    op.create_index('ix_remediation_jobs_parent_job_id', 'remediation_jobs', ['parent_job_id'])
    op.create_index('ix_remediation_jobs_vulnerability_id', 'remediation_jobs', ['vulnerability_id'])
    op.create_index('ix_remediation_jobs_asset_id', 'remediation_jobs', ['asset_id'])
    op.create_index('ix_remediation_jobs_patch_id', 'remediation_jobs', ['patch_id'])
    op.create_index('ix_remediation_jobs_deployment_id', 'remediation_jobs', ['deployment_id'])
    op.create_index('ix_remediation_jobs_scheduled_for', 'remediation_jobs', ['scheduled_for'])
    op.create_index('ix_job_status_priority', 'remediation_jobs', ['status', 'priority_score'])
    op.create_index('ix_job_type_status', 'remediation_jobs', ['job_type', 'status'])
    op.create_index('ix_job_created_status', 'remediation_jobs', ['created_at_timestamp', 'status'])
    op.create_index('ix_job_worker_status', 'remediation_jobs', ['worker_id', 'status'])
    op.create_index('ix_job_scheduled', 'remediation_jobs', ['scheduled_for', 'status'])
    op.create_index('ix_job_queue_status', 'remediation_jobs', ['queue_name', 'status'])


def downgrade() -> None:
    """Drop all VulnZero database tables"""

    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('remediation_jobs')
    op.drop_table('audit_logs')
    op.drop_table('deployments')
    op.drop_table('patches')
    op.drop_table('assets')
    op.drop_table('vulnerabilities')

    # Drop ENUM types
    sa.Enum(name='jobpriority').drop(op.get_bind())
    sa.Enum(name='jobstatus').drop(op.get_bind())
    sa.Enum(name='jobtype').drop(op.get_bind())
    sa.Enum(name='auditresourcetype').drop(op.get_bind())
    sa.Enum(name='auditaction').drop(op.get_bind())
    sa.Enum(name='deploymentstrategy').drop(op.get_bind())
    sa.Enum(name='deploymentstatus').drop(op.get_bind())
    sa.Enum(name='patchstatus').drop(op.get_bind())
    sa.Enum(name='patchtype').drop(op.get_bind())
    sa.Enum(name='assetstatus').drop(op.get_bind())
    sa.Enum(name='assettype').drop(op.get_bind())
    sa.Enum(name='vulnerabilityseverity').drop(op.get_bind())
    sa.Enum(name='vulnerabilitystatus').drop(op.get_bind())
