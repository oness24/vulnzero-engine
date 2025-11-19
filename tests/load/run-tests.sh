#!/bin/bash
# k6 Load Testing Runner Script
# Runs all k6 performance tests with proper configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
TEST_EMAIL="${TEST_EMAIL:-test@example.com}"
TEST_PASSWORD="${TEST_PASSWORD:-TestPassword123!}"
OUTPUT_DIR="${OUTPUT_DIR:-./test-results}"

# Banner
echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║         k6 Load Testing Suite for VulnZero               ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if k6 is installed
if ! command -v k6 &> /dev/null; then
    echo -e "${RED}❌ k6 is not installed${NC}"
    echo "Install k6 from https://k6.io/docs/getting-started/installation/"
    exit 1
fi

echo -e "${GREEN}✅ k6 is installed ($(k6 version | head -1))${NC}"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Check if API is running
echo ""
echo -e "${YELLOW}🔍 Checking if API is available at ${BASE_URL}...${NC}"
if curl -s -f "${BASE_URL}/api/v1/system/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API is healthy${NC}"
else
    echo -e "${RED}❌ API is not responding at ${BASE_URL}${NC}"
    echo "Please start the API gateway:"
    echo "  docker-compose up api-gateway postgres redis"
    exit 1
fi

# Test selection
echo ""
echo "Select test to run:"
echo "  1) Authentication Load Test (fast, ~5 min)"
echo "  2) Deployment Load Test (medium, ~15 min)"
echo "  3) Vulnerability Scan Test (medium, ~10 min)"
echo "  4) Comprehensive System Test (slow, ~30 min)"
echo "  5) All Tests (very slow, ~60 min)"
echo "  6) Quick Smoke Test (very fast, ~2 min)"
echo ""
read -p "Enter choice [1-6]: " test_choice

# Test runner function
run_test() {
    local test_file=$1
    local test_name=$2
    local output_file="${OUTPUT_DIR}/$(basename ${test_file} .js)-$(date +%Y%m%d-%H%M%S).json"

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}🚀 Running: ${test_name}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Run k6 with environment variables
    if k6 run \
        --env BASE_URL="$BASE_URL" \
        --env TEST_EMAIL="$TEST_EMAIL" \
        --env TEST_PASSWORD="$TEST_PASSWORD" \
        --out json="$output_file" \
        "$test_file"; then
        echo ""
        echo -e "${GREEN}✅ ${test_name} PASSED${NC}"
        echo -e "${GREEN}📊 Results saved to: ${output_file}${NC}"
        return 0
    else
        echo ""
        echo -e "${RED}❌ ${test_name} FAILED${NC}"
        echo -e "${YELLOW}📊 Results saved to: ${output_file}${NC}"
        return 1
    fi
}

# Smoke test function (quick validation)
run_smoke_test() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}🔥 Running: Quick Smoke Test${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Quick smoke test with k6
    k6 run --env BASE_URL="$BASE_URL" - <<'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 5,
  duration: '30s',
  thresholds: {
    'http_req_duration': ['p(95)<1000'],
    'http_req_failed': ['rate<0.05'],
  },
};

export default function() {
  const baseUrl = __ENV.BASE_URL || 'http://localhost:8000';

  // Health check
  let res = http.get(`${baseUrl}/api/v1/system/health`);
  check(res, {
    'health check passed': (r) => r.status === 200,
  });

  sleep(1);
}
EOF

    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✅ Smoke test PASSED - System is ready for load testing${NC}"
        return 0
    else
        echo ""
        echo -e "${RED}❌ Smoke test FAILED - Check API health${NC}"
        return 1
    fi
}

# Execute based on choice
case $test_choice in
    1)
        run_test "tests/load/auth.js" "Authentication Load Test"
        ;;
    2)
        run_test "tests/load/deployments.js" "Deployment Load Test"
        ;;
    3)
        run_test "tests/load/scans.js" "Vulnerability Scan Test"
        ;;
    4)
        run_test "tests/load/comprehensive.js" "Comprehensive System Test"
        ;;
    5)
        echo -e "${YELLOW}⚠️  Running all tests will take approximately 60 minutes${NC}"
        read -p "Continue? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            failed_tests=0

            run_test "tests/load/auth.js" "Authentication Load Test" || ((failed_tests++))
            run_test "tests/load/deployments.js" "Deployment Load Test" || ((failed_tests++))
            run_test "tests/load/scans.js" "Vulnerability Scan Test" || ((failed_tests++))
            run_test "tests/load/comprehensive.js" "Comprehensive System Test" || ((failed_tests++))

            echo ""
            echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${BLUE}📊 Test Suite Summary${NC}"
            echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

            if [ $failed_tests -eq 0 ]; then
                echo -e "${GREEN}✅ All tests PASSED (4/4)${NC}"
            else
                echo -e "${RED}❌ ${failed_tests}/4 tests FAILED${NC}"
            fi

            echo -e "${BLUE}📁 Results directory: ${OUTPUT_DIR}${NC}"
        else
            echo "Test run cancelled"
            exit 0
        fi
        ;;
    6)
        run_smoke_test
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🏁 Load testing complete!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Next steps:"
echo "  1. Review test results in ${OUTPUT_DIR}"
echo "  2. Analyze performance metrics"
echo "  3. Identify and optimize bottlenecks"
echo "  4. Set up continuous performance monitoring"
echo ""
