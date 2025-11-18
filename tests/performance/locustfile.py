"""
Locust load testing script for VulnZero API

Usage:
    # Run with web UI
    locust -f tests/performance/locustfile.py --host=http://localhost:8000

    # Run headless
    locust -f tests/performance/locustfile.py --host=http://localhost:8000 \
           --users 100 --spawn-rate 10 --run-time 60s --headless

Performance Targets:
- 95th percentile response time < 500ms
- Error rate < 1%
- Support 100+ concurrent users
- Throughput > 100 req/s
"""

from locust import HttpUser, task, between, events
import random
import json


class VulnZeroUser(HttpUser):
    """Simulated user interacting with VulnZero API"""

    # Wait 1-3 seconds between requests
    wait_time = between(1, 3)

    def on_start(self):
        """Called when a user starts - perform login"""
        self.token = None
        self.login()

    def login(self):
        """Authenticate and get JWT token"""
        response = self.client.post(
            "/api/auth/login",
            json={
                "username": "load_test_user",
                "password": "load_test_password"
            },
            catch_response=True
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            response.success()
        elif response.status_code == 404:
            # Auth endpoint might not exist yet
            response.success()
        else:
            response.failure(f"Login failed: {response.status_code}")

    def get_headers(self):
        """Get authorization headers"""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    @task(5)
    def list_vulnerabilities(self):
        """List vulnerabilities (most common operation - 50% of traffic)"""
        params = {
            "limit": random.choice([10, 20, 50]),
            "offset": random.choice([0, 10, 20]),
        }
        self.client.get(
            "/api/vulnerabilities/",
            params=params,
            headers=self.get_headers(),
            name="/api/vulnerabilities/ [LIST]"
        )

    @task(3)
    def get_vulnerability_details(self):
        """Get specific vulnerability details (30% of traffic)"""
        vuln_id = random.randint(1, 100)
        self.client.get(
            f"/api/vulnerabilities/{vuln_id}",
            headers=self.get_headers(),
            name="/api/vulnerabilities/[id] [GET]"
        )

    @task(2)
    def list_assets(self):
        """List assets (20% of traffic)"""
        self.client.get(
            "/api/assets/",
            headers=self.get_headers(),
            name="/api/assets/ [LIST]"
        )

    @task(2)
    def list_patches(self):
        """List patches (20% of traffic)"""
        self.client.get(
            "/api/patches/",
            headers=self.get_headers(),
            name="/api/patches/ [LIST]"
        )

    @task(2)
    def list_deployments(self):
        """List deployments (20% of traffic)"""
        self.client.get(
            "/api/deployments/",
            headers=self.get_headers(),
            name="/api/deployments/ [LIST]"
        )

    @task(1)
    def create_vulnerability(self):
        """Create new vulnerability (10% of traffic)"""
        payload = {
            "cve_id": f"CVE-2024-{random.randint(1000, 9999)}",
            "title": f"Test Vulnerability {random.randint(1, 1000)}",
            "description": "Load test vulnerability",
            "severity": random.choice(["critical", "high", "medium", "low"]),
            "cvss_score": round(random.uniform(0, 10), 1),
        }
        self.client.post(
            "/api/vulnerabilities/",
            json=payload,
            headers=self.get_headers(),
            name="/api/vulnerabilities/ [CREATE]"
        )

    @task(1)
    def update_vulnerability(self):
        """Update vulnerability (10% of traffic)"""
        vuln_id = random.randint(1, 100)
        payload = {
            "status": random.choice(["new", "in_progress", "patched", "deployed"]),
            "priority_score": random.uniform(0, 100),
        }
        self.client.patch(
            f"/api/vulnerabilities/{vuln_id}",
            json=payload,
            headers=self.get_headers(),
            name="/api/vulnerabilities/[id] [UPDATE]"
        )

    @task(1)
    def search_vulnerabilities(self):
        """Search vulnerabilities (10% of traffic)"""
        search_terms = ["sql injection", "xss", "authentication", "dos", "privilege escalation"]
        params = {
            "search": random.choice(search_terms),
            "severity": random.choice(["critical", "high", "medium", "low"]),
        }
        self.client.get(
            "/api/vulnerabilities/search",
            params=params,
            headers=self.get_headers(),
            name="/api/vulnerabilities/search [SEARCH]"
        )

    @task(10)
    def health_check(self):
        """Health check endpoint (should be very fast)"""
        self.client.get("/health", name="/health [HEALTH]")

    @task(1)
    def metrics_endpoint(self):
        """Metrics endpoint"""
        self.client.get("/metrics", name="/metrics [METRICS]")


class AdminUser(HttpUser):
    """Simulated admin user with heavier operations"""

    wait_time = between(2, 5)

    def on_start(self):
        """Login as admin"""
        self.token = None
        self.login_admin()

    def login_admin(self):
        """Admin login"""
        response = self.client.post(
            "/api/auth/login",
            json={
                "username": "admin",
                "password": "admin_password"
            },
            catch_response=True
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            response.success()
        elif response.status_code == 404:
            response.success()
        else:
            response.failure(f"Admin login failed: {response.status_code}")

    def get_headers(self):
        """Get authorization headers"""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    @task(3)
    def generate_patch(self):
        """Generate patch for vulnerability"""
        vuln_id = random.randint(1, 50)
        payload = {
            "vulnerability_id": vuln_id,
            "llm_provider": random.choice(["openai", "anthropic"]),
        }
        self.client.post(
            "/api/patches/generate",
            json=payload,
            headers=self.get_headers(),
            name="/api/patches/generate [ADMIN]"
        )

    @task(2)
    def deploy_patch(self):
        """Deploy patch"""
        patch_id = random.randint(1, 50)
        asset_id = random.randint(1, 20)
        payload = {
            "patch_id": patch_id,
            "asset_id": asset_id,
            "deployment_method": random.choice(["ansible", "terraform"]),
        }
        self.client.post(
            "/api/deployments/",
            json=payload,
            headers=self.get_headers(),
            name="/api/deployments/ [ADMIN]"
        )

    @task(1)
    def view_audit_logs(self):
        """View audit logs"""
        self.client.get(
            "/api/audit-logs/",
            headers=self.get_headers(),
            name="/api/audit-logs/ [ADMIN]"
        )


# Event handlers for custom metrics

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts"""
    print("=" * 60)
    print("VulnZero Load Test Starting")
    print(f"Target: {environment.host}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops - print summary"""
    print("\n" + "=" * 60)
    print("VulnZero Load Test Summary")
    print("=" * 60)

    stats = environment.stats
    print(f"Total requests: {stats.num_requests}")
    print(f"Total failures: {stats.num_failures}")
    print(f"Failure rate: {stats.total.fail_ratio:.2%}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Median response time: {stats.total.median_response_time:.2f}ms")
    print(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"99th percentile: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"Max response time: {stats.total.max_response_time:.2f}ms")
    print(f"Requests/sec: {stats.total.total_rps:.2f}")
    print("=" * 60)

    # Performance assertions
    p95 = stats.total.get_response_time_percentile(0.95)
    fail_rate = stats.total.fail_ratio

    if p95 > 500:
        print(f"⚠️  WARNING: P95 response time ({p95:.2f}ms) exceeds 500ms target")
    else:
        print(f"✅ PASS: P95 response time ({p95:.2f}ms) within target")

    if fail_rate > 0.01:
        print(f"⚠️  WARNING: Failure rate ({fail_rate:.2%}) exceeds 1% target")
    else:
        print(f"✅ PASS: Failure rate ({fail_rate:.2%}) within target")

    print("=" * 60)
