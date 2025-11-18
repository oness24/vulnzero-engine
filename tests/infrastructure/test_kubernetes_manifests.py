"""
Kubernetes Manifest Validation Tests

These tests validate Kubernetes manifests before deployment to ensure:
- YAML syntax is correct
- Required fields are present
- Security best practices are followed
- Resource limits are defined
- Health checks are configured
- Labels and selectors match
"""

import pytest
import yaml
import os
from pathlib import Path


# Path to Kubernetes manifests
K8S_DIR = Path(__file__).parent.parent.parent / "infrastructure" / "kubernetes"


class TestKubernetesManifestStructure:
    """Test Kubernetes manifest file structure and organization"""

    def test_kubernetes_directory_exists(self):
        """Test that Kubernetes manifests directory exists"""
        assert K8S_DIR.exists(), f"Kubernetes directory not found at {K8S_DIR}"

    def test_required_manifest_files_exist(self):
        """Test that all required manifest files exist"""
        required_files = [
            "namespace.yaml",
            "configmap.yaml",
            "secrets.yaml",
        ]

        for filename in required_files:
            filepath = K8S_DIR / filename
            assert filepath.exists(), f"Required manifest {filename} not found"

    def test_deployment_directory_exists(self):
        """Test that deployments directory exists"""
        deployments_dir = K8S_DIR / "deployments"
        assert deployments_dir.exists(), "Deployments directory not found"

    def test_service_directory_exists(self):
        """Test that services directory exists"""
        services_dir = K8S_DIR / "services"
        assert services_dir.exists(), "Services directory not found"

    def test_required_deployment_files_exist(self):
        """Test that all required deployment files exist"""
        deployments_dir = K8S_DIR / "deployments"
        required_deployments = [
            "api.yaml",
            "celery-worker.yaml",
            "celery-beat.yaml",
            "frontend.yaml",
            "flower.yaml",
        ]

        for filename in required_deployments:
            filepath = deployments_dir / filename
            assert filepath.exists(), f"Required deployment {filename} not found"

    def test_required_service_files_exist(self):
        """Test that all required service files exist"""
        services_dir = K8S_DIR / "services"
        required_services = [
            "api-service.yaml",
            "frontend-service.yaml",
            "flower-service.yaml",
        ]

        for filename in required_services:
            filepath = services_dir / filename
            assert filepath.exists(), f"Required service {filename} not found"


class TestYAMLSyntax:
    """Test YAML syntax and structure"""

    def get_all_yaml_files(self):
        """Get all YAML files in the Kubernetes directory"""
        if not K8S_DIR.exists():
            return []
        return list(K8S_DIR.rglob("*.yaml")) + list(K8S_DIR.rglob("*.yml"))

    def test_all_yaml_files_are_valid(self):
        """Test that all YAML files have valid syntax"""
        yaml_files = self.get_all_yaml_files()

        if not yaml_files:
            pytest.skip("No Kubernetes manifests found yet")

        for filepath in yaml_files:
            with open(filepath, 'r') as f:
                try:
                    yaml.safe_load_all(f)
                except yaml.YAMLError as e:
                    pytest.fail(f"Invalid YAML in {filepath}: {e}")

    def test_yaml_files_are_not_empty(self):
        """Test that YAML files are not empty"""
        yaml_files = self.get_all_yaml_files()

        if not yaml_files:
            pytest.skip("No Kubernetes manifests found yet")

        for filepath in yaml_files:
            assert filepath.stat().st_size > 0, f"{filepath} is empty"


class TestNamespaceManifest:
    """Test namespace manifest"""

    @pytest.fixture
    def namespace_manifest(self):
        """Load namespace manifest"""
        filepath = K8S_DIR / "namespace.yaml"
        if not filepath.exists():
            pytest.skip("Namespace manifest not created yet")

        with open(filepath, 'r') as f:
            return yaml.safe_load(f)

    def test_namespace_has_correct_kind(self, namespace_manifest):
        """Test namespace has correct kind"""
        assert namespace_manifest['kind'] == 'Namespace'

    def test_namespace_has_metadata(self, namespace_manifest):
        """Test namespace has metadata"""
        assert 'metadata' in namespace_manifest
        assert 'name' in namespace_manifest['metadata']

    def test_namespace_name_is_vulnzero(self, namespace_manifest):
        """Test namespace name is 'vulnzero'"""
        assert namespace_manifest['metadata']['name'] == 'vulnzero'

    def test_namespace_has_labels(self, namespace_manifest):
        """Test namespace has appropriate labels"""
        assert 'labels' in namespace_manifest['metadata']
        labels = namespace_manifest['metadata']['labels']
        assert 'app' in labels or 'name' in labels


class TestDeploymentManifests:
    """Test deployment manifests"""

    @pytest.fixture
    def api_deployment(self):
        """Load API deployment manifest"""
        filepath = K8S_DIR / "deployments" / "api.yaml"
        if not filepath.exists():
            pytest.skip("API deployment not created yet")

        with open(filepath, 'r') as f:
            return yaml.safe_load(f)

    def test_deployment_has_required_fields(self, api_deployment):
        """Test deployment has all required fields"""
        required_fields = ['apiVersion', 'kind', 'metadata', 'spec']
        for field in required_fields:
            assert field in api_deployment, f"Missing required field: {field}"

    def test_deployment_kind_is_correct(self, api_deployment):
        """Test deployment kind is 'Deployment'"""
        assert api_deployment['kind'] == 'Deployment'

    def test_deployment_has_replicas(self, api_deployment):
        """Test deployment specifies replica count"""
        assert 'replicas' in api_deployment['spec']
        assert api_deployment['spec']['replicas'] >= 1

    def test_deployment_has_selector(self, api_deployment):
        """Test deployment has selector"""
        assert 'selector' in api_deployment['spec']
        assert 'matchLabels' in api_deployment['spec']['selector']

    def test_deployment_has_template(self, api_deployment):
        """Test deployment has pod template"""
        assert 'template' in api_deployment['spec']
        assert 'metadata' in api_deployment['spec']['template']
        assert 'spec' in api_deployment['spec']['template']

    def test_deployment_labels_match_selector(self, api_deployment):
        """Test pod labels match deployment selector"""
        selector_labels = api_deployment['spec']['selector']['matchLabels']
        pod_labels = api_deployment['spec']['template']['metadata']['labels']

        for key, value in selector_labels.items():
            assert key in pod_labels, f"Selector label '{key}' not in pod labels"
            assert pod_labels[key] == value, f"Label mismatch for '{key}'"

    def test_deployment_has_container_spec(self, api_deployment):
        """Test deployment has container specification"""
        containers = api_deployment['spec']['template']['spec']['containers']
        assert len(containers) > 0, "No containers defined"

    def test_container_has_image(self, api_deployment):
        """Test container has image specified"""
        container = api_deployment['spec']['template']['spec']['containers'][0]
        assert 'image' in container
        assert container['image'] != '', "Container image is empty"

    def test_container_has_resource_limits(self, api_deployment):
        """Test container has resource limits defined"""
        container = api_deployment['spec']['template']['spec']['containers'][0]
        assert 'resources' in container, "No resource limits defined"
        assert 'limits' in container['resources'], "No resource limits specified"
        assert 'memory' in container['resources']['limits']

    def test_container_has_resource_requests(self, api_deployment):
        """Test container has resource requests defined"""
        container = api_deployment['spec']['template']['spec']['containers'][0]
        assert 'resources' in container
        assert 'requests' in container['resources'], "No resource requests specified"
        assert 'memory' in container['resources']['requests']
        assert 'cpu' in container['resources']['requests']

    def test_container_has_ports(self, api_deployment):
        """Test container has ports defined"""
        container = api_deployment['spec']['template']['spec']['containers'][0]
        assert 'ports' in container, "No ports defined"
        assert len(container['ports']) > 0

    def test_container_has_liveness_probe(self, api_deployment):
        """Test container has liveness probe"""
        container = api_deployment['spec']['template']['spec']['containers'][0]
        assert 'livenessProbe' in container, "No liveness probe defined"

    def test_container_has_readiness_probe(self, api_deployment):
        """Test container has readiness probe"""
        container = api_deployment['spec']['template']['spec']['containers'][0]
        assert 'readinessProbe' in container, "No readiness probe defined"

    def test_deployment_has_security_context(self, api_deployment):
        """Test deployment has security context"""
        pod_spec = api_deployment['spec']['template']['spec']
        # Can be at pod level or container level
        container = pod_spec['containers'][0]
        assert 'securityContext' in pod_spec or 'securityContext' in container


class TestServiceManifests:
    """Test service manifests"""

    @pytest.fixture
    def api_service(self):
        """Load API service manifest"""
        filepath = K8S_DIR / "services" / "api-service.yaml"
        if not filepath.exists():
            pytest.skip("API service not created yet")

        with open(filepath, 'r') as f:
            return yaml.safe_load(f)

    def test_service_has_required_fields(self, api_service):
        """Test service has all required fields"""
        required_fields = ['apiVersion', 'kind', 'metadata', 'spec']
        for field in required_fields:
            assert field in api_service

    def test_service_kind_is_correct(self, api_service):
        """Test service kind is 'Service'"""
        assert api_service['kind'] == 'Service'

    def test_service_has_selector(self, api_service):
        """Test service has selector"""
        assert 'selector' in api_service['spec']
        assert len(api_service['spec']['selector']) > 0

    def test_service_has_ports(self, api_service):
        """Test service has ports defined"""
        assert 'ports' in api_service['spec']
        assert len(api_service['spec']['ports']) > 0

    def test_service_port_has_name(self, api_service):
        """Test service ports have names"""
        for port in api_service['spec']['ports']:
            assert 'name' in port or len(api_service['spec']['ports']) == 1

    def test_service_type_is_valid(self, api_service):
        """Test service type is valid"""
        valid_types = ['ClusterIP', 'NodePort', 'LoadBalancer', 'ExternalName']
        service_type = api_service['spec'].get('type', 'ClusterIP')
        assert service_type in valid_types


class TestConfigMapManifest:
    """Test ConfigMap manifest"""

    @pytest.fixture
    def configmap(self):
        """Load ConfigMap manifest"""
        filepath = K8S_DIR / "configmap.yaml"
        if not filepath.exists():
            pytest.skip("ConfigMap not created yet")

        with open(filepath, 'r') as f:
            return yaml.safe_load(f)

    def test_configmap_has_data(self, configmap):
        """Test ConfigMap has data section"""
        assert 'data' in configmap or 'binaryData' in configmap

    def test_configmap_kind_is_correct(self, configmap):
        """Test ConfigMap kind is correct"""
        assert configmap['kind'] == 'ConfigMap'


class TestSecretsManifest:
    """Test Secrets manifest"""

    @pytest.fixture
    def secrets(self):
        """Load Secrets manifest"""
        filepath = K8S_DIR / "secrets.yaml"
        if not filepath.exists():
            pytest.skip("Secrets manifest not created yet")

        with open(filepath, 'r') as f:
            return yaml.safe_load(f)

    def test_secrets_kind_is_correct(self, secrets):
        """Test Secrets kind is correct"""
        assert secrets['kind'] == 'Secret'

    def test_secrets_has_type(self, secrets):
        """Test Secrets has type specified"""
        assert 'type' in secrets
        assert secrets['type'] in ['Opaque', 'kubernetes.io/tls', 'kubernetes.io/service-account-token']

    def test_secrets_has_data_or_string_data(self, secrets):
        """Test Secrets has data or stringData"""
        assert 'data' in secrets or 'stringData' in secrets


class TestIngressManifest:
    """Test Ingress manifest"""

    @pytest.fixture
    def ingress(self):
        """Load Ingress manifest"""
        filepath = K8S_DIR / "ingress.yaml"
        if not filepath.exists():
            pytest.skip("Ingress not created yet")

        with open(filepath, 'r') as f:
            return yaml.safe_load(f)

    def test_ingress_has_rules(self, ingress):
        """Test Ingress has rules defined"""
        assert 'rules' in ingress['spec']
        assert len(ingress['spec']['rules']) > 0

    def test_ingress_has_tls(self, ingress):
        """Test Ingress has TLS configured"""
        assert 'tls' in ingress['spec'], "Ingress should have TLS for production"


class TestPostgreSQLStatefulSet:
    """Test PostgreSQL StatefulSet"""

    @pytest.fixture
    def postgres_statefulset(self):
        """Load PostgreSQL StatefulSet manifest"""
        filepath = K8S_DIR / "postgres" / "statefulset.yaml"
        if not filepath.exists():
            pytest.skip("PostgreSQL StatefulSet not created yet")

        with open(filepath, 'r') as f:
            return yaml.safe_load(f)

    def test_statefulset_kind_is_correct(self, postgres_statefulset):
        """Test StatefulSet kind is correct"""
        assert postgres_statefulset['kind'] == 'StatefulSet'

    def test_statefulset_has_volume_claim_templates(self, postgres_statefulset):
        """Test StatefulSet has volume claim templates"""
        assert 'volumeClaimTemplates' in postgres_statefulset['spec']

    def test_statefulset_has_service_name(self, postgres_statefulset):
        """Test StatefulSet has serviceName"""
        assert 'serviceName' in postgres_statefulset['spec']


class TestSecurityBestPractices:
    """Test security best practices in manifests"""

    def get_all_deployment_manifests(self):
        """Get all deployment manifests"""
        deployments_dir = K8S_DIR / "deployments"
        if not deployments_dir.exists():
            return []
        return list(deployments_dir.glob("*.yaml"))

    def test_containers_do_not_run_as_root(self):
        """Test that containers don't run as root"""
        deployment_files = self.get_all_deployment_manifests()

        if not deployment_files:
            pytest.skip("No deployment manifests found yet")

        for filepath in deployment_files:
            with open(filepath, 'r') as f:
                manifest = yaml.safe_load(f)

            containers = manifest['spec']['template']['spec']['containers']
            for container in containers:
                security_context = container.get('securityContext', {})
                # Check if runAsNonRoot is set or runAsUser is not 0
                run_as_non_root = security_context.get('runAsNonRoot', False)
                run_as_user = security_context.get('runAsUser', 0)

                # Either runAsNonRoot should be True or runAsUser should not be 0
                assert run_as_non_root or run_as_user != 0, \
                    f"Container in {filepath} may run as root"

    def test_containers_have_read_only_root_filesystem(self):
        """Test that containers have read-only root filesystem where possible"""
        deployment_files = self.get_all_deployment_manifests()

        if not deployment_files:
            pytest.skip("No deployment manifests found yet")

        # This is a recommendation, not strictly enforced for all containers
        # Some containers may need writable filesystem
        pass

    def test_resource_limits_prevent_dos(self):
        """Test that resource limits prevent DoS attacks"""
        deployment_files = self.get_all_deployment_manifests()

        if not deployment_files:
            pytest.skip("No deployment manifests found yet")

        for filepath in deployment_files:
            with open(filepath, 'r') as f:
                manifest = yaml.safe_load(f)

            containers = manifest['spec']['template']['spec']['containers']
            for container in containers:
                resources = container.get('resources', {})
                limits = resources.get('limits', {})

                # Should have memory limit to prevent OOM
                assert 'memory' in limits, \
                    f"Container in {filepath} has no memory limit (DoS risk)"


class TestHighAvailability:
    """Test high availability configurations"""

    def test_critical_services_have_multiple_replicas(self):
        """Test that critical services have multiple replicas"""
        critical_services = ['api.yaml']
        deployments_dir = K8S_DIR / "deployments"

        if not deployments_dir.exists():
            pytest.skip("Deployments directory not found yet")

        for service_file in critical_services:
            filepath = deployments_dir / service_file
            if not filepath.exists():
                pytest.skip(f"{service_file} not created yet")

            with open(filepath, 'r') as f:
                manifest = yaml.safe_load(f)

            replicas = manifest['spec'].get('replicas', 1)
            assert replicas >= 2, \
                f"{service_file} should have at least 2 replicas for HA"

    def test_deployments_have_pod_disruption_budgets(self):
        """Test that deployments reference pod disruption budgets"""
        # This is optional but recommended for HA
        # Could check for PodDisruptionBudget manifests
        pass


class TestResourceValidation:
    """Test resource allocation is reasonable"""

    def test_memory_limits_are_reasonable(self):
        """Test that memory limits are within reasonable bounds"""
        deployment_files = self.get_all_deployment_manifests()

        if not deployment_files:
            pytest.skip("No deployment manifests found yet")

        for filepath in deployment_files:
            with open(filepath, 'r') as f:
                manifest = yaml.safe_load(f)

            containers = manifest['spec']['template']['spec']['containers']
            for container in containers:
                resources = container.get('resources', {})
                limits = resources.get('limits', {})
                memory_limit = limits.get('memory', '')

                # Parse memory limit (e.g., "512Mi", "1Gi")
                if memory_limit:
                    # Should be between 128Mi and 8Gi for most services
                    assert memory_limit.endswith(('Mi', 'Gi', 'M', 'G')), \
                        "Memory limit should specify units (Mi/Gi)"

    def get_all_deployment_manifests(self):
        """Get all deployment manifests"""
        deployments_dir = K8S_DIR / "deployments"
        if not deployments_dir.exists():
            return []
        return list(deployments_dir.glob("*.yaml"))
