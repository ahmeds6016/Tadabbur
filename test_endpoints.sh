#!/bin/bash

# Test backend endpoints for query history and saved searches
BACKEND_URL="https://tafsir-backend-612616741510.us-central1.run.app"

echo "Testing Backend Endpoints..."
echo "=============================="

# Test 1: Query History GET (will fail without auth, but shows if endpoint exists)
echo -e "\n1. Testing GET /query-history"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" "${BACKEND_URL}/query-history"

# Test 2: Saved Searches GET
echo -e "\n2. Testing GET /saved-searches"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" "${BACKEND_URL}/saved-searches"

# Test 3: Annotations GET
echo -e "\n3. Testing GET /annotations/user"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" "${BACKEND_URL}/annotations/user"

# Test 4: Check if endpoints return 401 (auth required) or 404 (not found)
echo -e "\n4. Detailed query-history test:"
curl -s "${BACKEND_URL}/query-history" | head -n 5

echo -e "\n\nExpected: All should return 401 Unauthorized (means endpoint exists but needs auth)"
echo "If 404 Not Found → Endpoint doesn't exist (routing issue)"
echo "If 500 Internal Server Error → Backend code error"
