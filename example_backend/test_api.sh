#!/bin/bash
# Test script for the voice library API

API_URL="http://localhost:8006"

echo "=== Testing Voice Library API ==="
echo ""

# Test 1: Health check
echo "1. Testing health check endpoint..."
curl -s "${API_URL}/" | jq .
echo ""

# Test 2: Start a scan (this should return immediately, not hang)
echo "2. Starting dataset scan..."
RESPONSE=$(curl -s -X POST "${API_URL}/api/voice-library/scan-libritts" \
    -H "Content-Type: application/json" \
    --data-raw '{"libritts_path": "/tmp"}')

echo "$RESPONSE" | jq .

# Extract task ID
TASK_ID=$(echo "$RESPONSE" | jq -r '.task_id')
echo ""
echo "Task ID: $TASK_ID"
echo ""

# Test 3: Check status
echo "3. Checking scan status..."
for i in {1..5}; do
    echo "  Check #$i:"
    curl -s "${API_URL}/api/voice-library/scan-status/${TASK_ID}" | jq .
    echo ""
    sleep 1
done

# Test 4: List all tasks
echo "4. Listing all tasks..."
curl -s "${API_URL}/api/voice-library/tasks" | jq .
echo ""

echo "=== Test Complete ==="
echo ""
echo "Key differences from the hanging version:"
echo "  ✓ POST request returns immediately with task_id"
echo "  ✓ Long-running scan happens in background"
echo "  ✓ Client can poll status endpoint for progress"
echo "  ✓ No timeouts or hanging connections"
