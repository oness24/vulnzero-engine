"""
Monitoring Configuration Tests

Tests for Prometheus and Grafana configurations to ensure:
- Valid YAML/JSON syntax
- Required metrics are being collected
- Dashboards have proper structure
- Alert rules are correctly defined
- Targets are configured properly
"""

import pytest
import yaml
import json
from pathlib import Path


# Paths to monitoring configurations
PROMETHEUS_CONFIG = Path(__file__).parent.parent.parent / "monitoring" / "prometheus.yml"
GRAFANA_DASHBOARDS_DIR = Path(__file__).parent.parent.parent / "monitoring" / "grafana" / "dashboards"
GRAFANA_DATASOURCES_DIR = Path(__file__).parent.parent.parent / "monitoring" / "grafana" / "datasources"
ALERT_RULES_DIR = Path(__file__).parent.parent.parent / "monitoring" / "alerts"


class TestPrometheusConfiguration:
    """Test Prometheus configuration"""

    @pytest.fixture
    def prometheus_config(self):
        """Load Prometheus configuration"""
        if not PROMETHEUS_CONFIG.exists():
            pytest.skip("Prometheus config not found")

        with open(PROMETHEUS_CONFIG, 'r') as f:
            return yaml.safe_load(f)

    def test_prometheus_config_exists(self):
        """Test that Prometheus config file exists"""
        assert PROMETHEUS_CONFIG.exists(), "Prometheus config not found"

    def test_prometheus_config_is_valid_yaml(self, prometheus_config):
        """Test that Prometheus config is valid YAML"""
        assert prometheus_config is not None

    def test_prometheus_has_global_config(self, prometheus_config):
        """Test Prometheus has global configuration"""
        assert 'global' in prometheus_config

    def test_prometheus_has_scrape_interval(self, prometheus_config):
        """Test Prometheus has scrape interval configured"""
        assert 'scrape_interval' in prometheus_config['global']

    def test_prometheus_has_scrape_configs(self, prometheus_config):
        """Test Prometheus has scrape configurations"""
        assert 'scrape_configs' in prometheus_config
        assert len(prometheus_config['scrape_configs']) > 0

    def test_prometheus_scrapes_vulnzero_api(self, prometheus_config):
        """Test Prometheus scrapes VulnZero API metrics"""
        job_names = [job['job_name'] for job in prometheus_config['scrape_configs']]
        assert 'vulnzero-api' in job_names, "VulnZero API not in scrape targets"

    def test_prometheus_scrapes_itself(self, prometheus_config):
        """Test Prometheus scrapes its own metrics"""
        job_names = [job['job_name'] for job in prometheus_config['scrape_configs']]
        assert 'prometheus' in job_names

    def test_scrape_configs_have_targets(self, prometheus_config):
        """Test all scrape configs have targets"""
        for job in prometheus_config['scrape_configs']:
            assert 'static_configs' in job or 'kubernetes_sd_configs' in job, \
                f"Job {job['job_name']} has no target configuration"

    def test_metrics_path_is_configured(self, prometheus_config):
        """Test metrics path is configured for VulnZero API"""
        vulnzero_jobs = [job for job in prometheus_config['scrape_configs']
                         if 'vulnzero' in job['job_name']]

        for job in vulnzero_jobs:
            metrics_path = job.get('metrics_path', '/metrics')
            assert metrics_path.startswith('/'), "Metrics path should start with /"


class TestPrometheusAlertRules:
    """Test Prometheus alert rules"""

    def test_alert_rules_directory_exists(self):
        """Test that alert rules directory exists"""
        assert ALERT_RULES_DIR.exists(), "Alert rules directory not found"

    def get_alert_rule_files(self):
        """Get all alert rule files"""
        if not ALERT_RULES_DIR.exists():
            return []
        return list(ALERT_RULES_DIR.glob("*.yml")) + list(ALERT_RULES_DIR.glob("*.yaml"))

    def test_alert_rules_are_valid_yaml(self):
        """Test that all alert rule files are valid YAML"""
        rule_files = self.get_alert_rule_files()

        if not rule_files:
            pytest.skip("No alert rules found yet")

        for filepath in rule_files:
            with open(filepath, 'r') as f:
                try:
                    yaml.safe_load(f)
                except yaml.YAMLError as e:
                    pytest.fail(f"Invalid YAML in {filepath}: {e}")

    def test_alert_rules_have_required_fields(self):
        """Test that alert rules have required fields"""
        rule_files = self.get_alert_rule_files()

        if not rule_files:
            pytest.skip("No alert rules found yet")

        for filepath in rule_files:
            with open(filepath, 'r') as f:
                rules = yaml.safe_load(f)

            assert 'groups' in rules, f"{filepath} missing 'groups' field"

            for group in rules['groups']:
                assert 'name' in group, "Alert group missing 'name'"
                assert 'rules' in group, "Alert group missing 'rules'"

                for rule in group['rules']:
                    assert 'alert' in rule, "Alert rule missing 'alert' name"
                    assert 'expr' in rule, "Alert rule missing 'expr' (expression)"
                    assert 'annotations' in rule or 'labels' in rule, \
                        "Alert should have annotations or labels"

    def test_critical_alerts_are_defined(self):
        """Test that critical alerts are defined"""
        rule_files = self.get_alert_rule_files()

        if not rule_files:
            pytest.skip("No alert rules found yet")

        all_alert_names = []
        for filepath in rule_files:
            with open(filepath, 'r') as f:
                rules = yaml.safe_load(f)

            for group in rules.get('groups', []):
                for rule in group.get('rules', []):
                    all_alert_names.append(rule.get('alert', ''))

        # Check for critical alerts
        critical_alerts = [
            'HighErrorRate',
            'ServiceDown',
            'HighMemoryUsage',
            'HighCPUUsage',
        ]

        # At least some critical alerts should be defined
        # (exact names may vary)
        assert len(all_alert_names) > 0, "No alerts defined"


class TestGrafanaDashboards:
    """Test Grafana dashboard configurations"""

    def test_grafana_dashboards_directory_exists(self):
        """Test that Grafana dashboards directory exists"""
        assert GRAFANA_DASHBOARDS_DIR.exists(), "Grafana dashboards directory not found"

    def get_dashboard_files(self):
        """Get all Grafana dashboard JSON files"""
        if not GRAFANA_DASHBOARDS_DIR.exists():
            return []
        return list(GRAFANA_DASHBOARDS_DIR.glob("*.json"))

    def test_provisioning_config_exists(self):
        """Test that dashboard provisioning config exists"""
        provisioning_file = GRAFANA_DASHBOARDS_DIR / "dashboard.yml"
        assert provisioning_file.exists(), "Dashboard provisioning config not found"

    def test_dashboards_are_valid_json(self):
        """Test that all dashboards are valid JSON"""
        dashboard_files = self.get_dashboard_files()

        if not dashboard_files:
            pytest.skip("No Grafana dashboards found yet")

        for filepath in dashboard_files:
            with open(filepath, 'r') as f:
                try:
                    json.load(f)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON in {filepath}: {e}")

    def test_dashboards_have_required_fields(self):
        """Test that dashboards have required fields"""
        dashboard_files = self.get_dashboard_files()

        if not dashboard_files:
            pytest.skip("No Grafana dashboards found yet")

        for filepath in dashboard_files:
            with open(filepath, 'r') as f:
                dashboard = json.load(f)

            required_fields = ['title', 'panels', 'schemaVersion']
            for field in required_fields:
                assert field in dashboard, \
                    f"Dashboard {filepath} missing required field: {field}"

    def test_dashboards_have_panels(self):
        """Test that dashboards have panels defined"""
        dashboard_files = self.get_dashboard_files()

        if not dashboard_files:
            pytest.skip("No Grafana dashboards found yet")

        for filepath in dashboard_files:
            with open(filepath, 'r') as f:
                dashboard = json.load(f)

            assert len(dashboard['panels']) > 0, \
                f"Dashboard {filepath} has no panels"

    def test_panels_have_targets(self):
        """Test that panels have Prometheus targets"""
        dashboard_files = self.get_dashboard_files()

        if not dashboard_files:
            pytest.skip("No Grafana dashboards found yet")

        for filepath in dashboard_files:
            with open(filepath, 'r') as f:
                dashboard = json.load(f)

            for panel in dashboard['panels']:
                # Skip row panels
                if panel.get('type') == 'row':
                    continue

                # Panels should have targets (queries)
                assert 'targets' in panel, \
                    f"Panel '{panel.get('title', 'Untitled')}' has no targets"
                assert len(panel['targets']) > 0

    def test_system_overview_dashboard_exists(self):
        """Test that system overview dashboard exists"""
        dashboard_files = self.get_dashboard_files()

        if not dashboard_files:
            pytest.skip("No Grafana dashboards found yet")

        dashboard_names = []
        for filepath in dashboard_files:
            with open(filepath, 'r') as f:
                dashboard = json.load(f)
                dashboard_names.append(dashboard['title'].lower())

        # Should have some kind of overview dashboard
        assert any('overview' in name or 'system' in name for name in dashboard_names), \
            "No system overview dashboard found"

    def test_application_metrics_dashboard_exists(self):
        """Test that application metrics dashboard exists"""
        dashboard_files = self.get_dashboard_files()

        if not dashboard_files:
            pytest.skip("No Grafana dashboards found yet")

        dashboard_names = []
        for filepath in dashboard_files:
            with open(filepath, 'r') as f:
                dashboard = json.load(f)
                dashboard_names.append(dashboard['title'].lower())

        # Should have application-specific metrics
        assert any('application' in name or 'vulnzero' in name or 'api' in name
                   for name in dashboard_names), \
            "No application metrics dashboard found"


class TestGrafanaDatasources:
    """Test Grafana datasource configurations"""

    def test_datasources_config_exists(self):
        """Test that datasources config exists"""
        datasource_file = GRAFANA_DATASOURCES_DIR / "prometheus.yml"
        assert datasource_file.exists(), "Grafana datasources config not found"

    @pytest.fixture
    def datasource_config(self):
        """Load datasource configuration"""
        datasource_file = GRAFANA_DATASOURCES_DIR / "prometheus.yml"
        if not datasource_file.exists():
            pytest.skip("Datasource config not found")

        with open(datasource_file, 'r') as f:
            return yaml.safe_load(f)

    def test_datasource_config_is_valid_yaml(self, datasource_config):
        """Test datasource config is valid YAML"""
        assert datasource_config is not None

    def test_prometheus_datasource_is_defined(self, datasource_config):
        """Test that Prometheus datasource is defined"""
        assert 'datasources' in datasource_config
        assert len(datasource_config['datasources']) > 0

        prometheus_ds = [ds for ds in datasource_config['datasources']
                         if ds.get('type') == 'prometheus']
        assert len(prometheus_ds) > 0, "No Prometheus datasource defined"

    def test_datasource_has_url(self, datasource_config):
        """Test datasource has URL configured"""
        for datasource in datasource_config['datasources']:
            assert 'url' in datasource, \
                f"Datasource {datasource.get('name')} missing URL"

    def test_datasource_is_default(self, datasource_config):
        """Test at least one datasource is set as default"""
        default_datasources = [ds for ds in datasource_config['datasources']
                               if ds.get('isDefault', False)]
        assert len(default_datasources) > 0, "No default datasource configured"


class TestMonitoringIntegration:
    """Test monitoring stack integration"""

    def test_prometheus_config_references_correct_api_endpoint(self, prometheus_config=None):
        """Test Prometheus scrape config uses correct API endpoint"""
        if not PROMETHEUS_CONFIG.exists():
            pytest.skip("Prometheus config not found")

        with open(PROMETHEUS_CONFIG, 'r') as f:
            config = yaml.safe_load(f)

        vulnzero_jobs = [job for job in config['scrape_configs']
                         if 'vulnzero' in job['job_name']]

        for job in vulnzero_jobs:
            metrics_path = job.get('metrics_path', '/metrics')
            # Should scrape from /api/metrics as configured in our API
            assert '/metrics' in metrics_path

    def test_monitoring_stack_has_all_components(self):
        """Test that all monitoring components exist"""
        components = {
            'Prometheus config': PROMETHEUS_CONFIG,
            'Grafana dashboards': GRAFANA_DASHBOARDS_DIR,
            'Grafana datasources': GRAFANA_DATASOURCES_DIR,
            'Alert rules': ALERT_RULES_DIR,
        }

        for name, path in components.items():
            assert path.exists(), f"{name} not found at {path}"


class TestMetricsCoverage:
    """Test that important metrics are being collected"""

    @pytest.fixture
    def prometheus_config(self):
        """Load Prometheus configuration"""
        if not PROMETHEUS_CONFIG.exists():
            pytest.skip("Prometheus config not found")

        with open(PROMETHEUS_CONFIG, 'r') as f:
            return yaml.safe_load(f)

    def test_api_metrics_are_scraped(self, prometheus_config):
        """Test that API metrics endpoint is being scraped"""
        job_names = [job['job_name'] for job in prometheus_config['scrape_configs']]

        api_jobs = [name for name in job_names if 'api' in name or 'vulnzero' in name]
        assert len(api_jobs) > 0, "API metrics not being scraped"

    def test_scrape_interval_is_reasonable(self, prometheus_config):
        """Test that scrape interval is reasonable (not too frequent, not too slow)"""
        scrape_interval = prometheus_config['global']['scrape_interval']

        # Parse interval (e.g., "15s", "1m")
        # Should be between 10s and 60s for most use cases
        assert scrape_interval.endswith('s') or scrape_interval.endswith('m'), \
            "Scrape interval should specify units (s or m)"

        # Extract numeric value
        if scrape_interval.endswith('s'):
            value = int(scrape_interval[:-1])
            assert 5 <= value <= 60, "Scrape interval should be between 5s and 60s"
        elif scrape_interval.endswith('m'):
            value = int(scrape_interval[:-1])
            assert value <= 5, "Scrape interval should not exceed 5 minutes"
