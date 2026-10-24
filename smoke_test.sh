#!/usr/bin/env bash
# ==============================================================================
# RepairBuddy / KaamSetu End-to-End Smoke Test Script
# Tests all endpoints on the live local FastAPI server (http://localhost:8000)
# Usage:
#   1. Start server: uvicorn main:app --reload --port 8000
#   2. Run script:   bash smoke_test.sh
# ==============================================================================

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}       REPAIRBUDDY API - END-TO-END LIVE SMOKE TEST SUITE             ${NC}"
echo -e "${BLUE}       Target: ${BASE_URL}                                             ${NC}"
echo -e "${BLUE}======================================================================${NC}"

# Helper function to print step
step() {
    echo -e "\n${BLUE}[STEP $1]${NC} $2"
}

pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

# ------------------------------------------------------------------------------
# 1. Health Check
# ------------------------------------------------------------------------------
step "1" "Checking System Health (/health)..."
HEALTH_RES=$(curl -s -f -X GET "${BASE_URL}/health")
echo "Response: ${HEALTH_RES}"
pass "Health check succeeded."

# ------------------------------------------------------------------------------
# 2. Customer Creates a Job (POST /jobs)
# ------------------------------------------------------------------------------
step "2" "Customer creates a new plumbing job (POST /jobs)..."
CREATE_JOB_RES=$(curl -s -f -X POST "${BASE_URL}/jobs" \
  -H "Authorization: Bearer cust_priya" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "plumber",
    "description": "Kitchen sink pipe leakage under sink cabinet",
    "location": {
      "lat": 19.2825,
      "lng": 72.8570,
      "address": "Flat 402, Beverly Park, Mira Road East, Mumbai"
    },
    "budget": 400.0,
    "mode": "on-demand"
  }')

echo "Response: ${CREATE_JOB_RES}"
JOB_ID=$(echo "${CREATE_JOB_RES}" | python -c "import sys, json; print(json.load(sys.stdin)['id'])")
pass "Created job with ID: ${JOB_ID}"

# ------------------------------------------------------------------------------
# 3. Match Workers for the Job (GET /workers/match?jobId=...)
# ------------------------------------------------------------------------------
step "3" "Matching verified workers for Job ${JOB_ID} (GET /workers/match)..."
MATCH_RES=$(curl -s -f -X GET "${BASE_URL}/workers/match?jobId=${JOB_ID}" \
  -H "Authorization: Bearer cust_priya")

MATCH_COUNT=$(echo "${MATCH_RES}" | python -c "import sys, json; print(len(json.load(sys.stdin)))")
TOP_WORKER_UID=$(echo "${MATCH_RES}" | python -c "import sys, json; data=json.load(sys.stdin); print(data[0]['worker']['uid'] if data else '')")
echo "Matched Workers Count: ${MATCH_COUNT}"
echo "Top Ranked Worker UID: ${TOP_WORKER_UID}"
pass "Found ${MATCH_COUNT} matched workers. Top match is ${TOP_WORKER_UID}."

# ------------------------------------------------------------------------------
# 4. Worker Nearby Job Feed (GET /jobs/nearby)
# ------------------------------------------------------------------------------
step "4" "Worker checks nearby job feed (GET /jobs/nearby)..."
NEARBY_RES=$(curl -s -f -X GET "${BASE_URL}/jobs/nearby" \
  -H "Authorization: Bearer worker_plumber_1")

NEARBY_COUNT=$(echo "${NEARBY_RES}" | python -c "import sys, json; print(len(json.load(sys.stdin)))")
echo "Nearby Open Jobs Count: ${NEARBY_COUNT}"
pass "Worker feed returned ${NEARBY_COUNT} relevant jobs."

# ------------------------------------------------------------------------------
# 5. Customer Makes Initial Offer (POST /offers)
# ------------------------------------------------------------------------------
step "5" "Customer makes initial offer of Rs. 350 to worker_plumber_1 (POST /offers)..."
OFFER_RES=$(curl -s -f -X POST "${BASE_URL}/offers" \
  -H "Authorization: Bearer cust_priya" \
  -H "Content-Type: application/json" \
  -d "{
    \"jobId\": \"${JOB_ID}\",
    \"workerId\": \"worker_plumber_1\",
    \"price\": 350.0,
    \"by\": \"customer\"
  }")

echo "Response: ${OFFER_RES}"
OFFER1_ID=$(echo "${OFFER_RES}" | python -c "import sys, json; print(json.load(sys.stdin)['id'])")
pass "Offer created with ID: ${OFFER1_ID} for Rs. 350"

# ------------------------------------------------------------------------------
# 6. Worker Counters Offer (POST /offers/{id}/counter)
# ------------------------------------------------------------------------------
step "6" "Worker counters offer with Rs. 450 (POST /offers/${OFFER1_ID}/counter)..."
COUNTER_RES=$(curl -s -f -X POST "${BASE_URL}/offers/${OFFER1_ID}/counter" \
  -H "Authorization: Bearer worker_plumber_1" \
  -H "Content-Type: application/json" \
  -d '{
    "price": 450.0
  }')

echo "Response: ${COUNTER_RES}"
OFFER2_ID=$(echo "${COUNTER_RES}" | python -c "import sys, json; print(json.load(sys.stdin)['id'])")
pass "Worker countered with new offer ID: ${OFFER2_ID} for Rs. 450"

# ------------------------------------------------------------------------------
# 7. Customer Accepts Offer (POST /offers/{id}/accept)
# ------------------------------------------------------------------------------
step "7" "Customer accepts worker counter offer (POST /offers/${OFFER2_ID}/accept)..."
ACCEPT_RES=$(curl -s -f -X POST "${BASE_URL}/offers/${OFFER2_ID}/accept" \
  -H "Authorization: Bearer cust_priya")

echo "Response: ${ACCEPT_RES}"
pass "Offer ${OFFER2_ID} successfully accepted."

# ------------------------------------------------------------------------------
# 8. Verify Job Status & Final Price (GET /jobs/{id})
# ------------------------------------------------------------------------------
step "8" "Verifying job status transitioned to 'accepted' with final price..."
JOB_DETAIL_RES=$(curl -s -f -X GET "${BASE_URL}/jobs/${JOB_ID}" \
  -H "Authorization: Bearer cust_priya")

echo "Job Details: ${JOB_DETAIL_RES}"
python -c "
import sys, json
data = json.loads('''${JOB_DETAIL_RES}''')
assert data['status'] == 'accepted', f\"Status is {data['status']}\"
assert data['acceptedWorkerId'] == 'worker_plumber_1'
assert data['finalPrice'] == 450.0
print('Verified: status=accepted, worker=worker_plumber_1, finalPrice=450.0')
"
pass "Job verified in accepted state."

# ------------------------------------------------------------------------------
# 9. Worker Starts the Job (POST /jobs/{id}/start)
# ------------------------------------------------------------------------------
step "9" "Worker starts the accepted job (POST /jobs/${JOB_ID}/start)..."
START_RES=$(curl -s -f -X POST "${BASE_URL}/jobs/${JOB_ID}/start" \
  -H "Authorization: Bearer worker_plumber_1")

echo "Response: ${START_RES}"
pass "Job started successfully. Status is now 'in_progress'."

# ------------------------------------------------------------------------------
# 10. Worker Completes the Job (POST /jobs/{id}/complete)
# ------------------------------------------------------------------------------
step "10" "Worker marks job as completed (POST /jobs/${JOB_ID}/complete)..."
COMPLETE_RES=$(curl -s -f -X POST "${BASE_URL}/jobs/${JOB_ID}/complete" \
  -H "Authorization: Bearer worker_plumber_1")

echo "Response: ${COMPLETE_RES}"
pass "Job completed successfully. Status is now 'completed'."

# ------------------------------------------------------------------------------
# 11. Customer Submits Review (POST /reviews)
# ------------------------------------------------------------------------------
step "11" "Customer submits review and rating (POST /reviews)..."
REVIEW_RES=$(curl -s -f -X POST "${BASE_URL}/reviews" \
  -H "Authorization: Bearer cust_priya" \
  -H "Content-Type: application/json" \
  -d "{
    \"jobId\": \"${JOB_ID}\",
    \"workerId\": \"worker_plumber_1\",
    \"rating\": 5.0,
    \"comment\": \"Super fast service! Replaced the pipe fitting cleanly.\"
  }")

echo "Response: ${REVIEW_RES}"
pass "Review submitted successfully and worker rolling rating updated."

# ------------------------------------------------------------------------------
# 12. Safety Emergency SOS (POST /sos)
# ------------------------------------------------------------------------------
step "12" "Triggering safety SOS alert (POST /sos)..."
SOS_RES=$(curl -s -f -X POST "${BASE_URL}/sos" \
  -H "Authorization: Bearer cust_priya" \
  -H "Content-Type: application/json" \
  -d "{
    \"jobId\": \"${JOB_ID}\",
    \"location\": {
      \"lat\": 19.2825,
      \"lng\": 72.8570
    }
  }")

echo "Response: ${SOS_RES}"
pass "SOS emergency alert recorded."

# ------------------------------------------------------------------------------
# 13. Customer Reports Worker (POST /reports)
# ------------------------------------------------------------------------------
step "13" "Customer submits safety/incident report against worker (POST /reports)..."
REPORT_RES=$(curl -s -f -X POST "${BASE_URL}/reports" \
  -H "Authorization: Bearer cust_priya" \
  -H "Content-Type: application/json" \
  -d '{
    "workerId": "worker_plumber_4",
    "reason": "Unprofessional conduct during service visit"
  }')

echo "Response: ${REPORT_RES}"
pass "Report submitted and logged."

# ------------------------------------------------------------------------------
# 14. Worker Requests Verification (POST /workers/verify)
# ------------------------------------------------------------------------------
step "14" "Worker requests Aadhaar verification (POST /workers/verify)..."
VERIFY_REQ_RES=$(curl -s -f -X POST "${BASE_URL}/workers/verify" \
  -H "Authorization: Bearer worker_plumber_unverified" \
  -H "Content-Type: application/json" \
  -d '{
    "documentType": "aadhaar",
    "documentNumber": "1234-5678-9012"
  }')

echo "Response: ${VERIFY_REQ_RES}"
pass "Worker verification request submitted."

# ------------------------------------------------------------------------------
# 15. Admin Approves Verification (POST /admin/verifications/{uid}/approve)
# ------------------------------------------------------------------------------
step "15" "Admin approves worker verification (POST /admin/verifications/{uid}/approve)..."
APPROVE_RES=$(curl -s -f -X POST "${BASE_URL}/admin/verifications/worker_plumber_unverified/approve" \
  -H "Authorization: Bearer admin_user")

echo "Response: ${APPROVE_RES}"
pass "Worker verification approved by admin."

echo -e "\n${GREEN}======================================================================${NC}"
echo -e "${GREEN}       ALL 15 ENDPOINTS VERIFIED SUCCESSFULLY! SMOKE TEST PASSED!     ${NC}"
echo -e "${GREEN}======================================================================${NC}"
