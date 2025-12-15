#!/bin/bash
# curl examples for Knowledge Manager API
# Replace YOUR_API_KEY with your actual API key

API_KEY="YOUR_API_KEY"
BASE_URL="http://localhost:8000/api/v1"

echo "============================================"
echo "Knowledge Manager API - curl Examples"
echo "============================================"

# 1. Register a new user
echo -e "\n1. Register User"
curl -X POST "$BASE_URL/user/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "SecurePassword123!"}'

# 2. Login
echo -e "\n\n2. Login"
curl -X POST "$BASE_URL/user/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "SecurePassword123!"}'

# 3. Create API key
echo -e "\n\n3. Create API Key"
curl -X POST "$BASE_URL/user/create-api-key" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "SecurePassword123!"}'

# 4. Upload documents (create index)
echo -e "\n\n4. Upload Documents"
curl -X POST "$BASE_URL/create-index/" \
  -H "X-API-Key: $API_KEY" \
  -F "collection=test_collection" \
  -F "files=@document.pdf" \
  -F "files=@notes.txt"

# 5. Update existing index
echo -e "\n\n5. Update Index"
curl -X POST "$BASE_URL/update-index/" \
  -H "X-API-Key: $API_KEY" \
  -F "collection=test_collection" \
  -F "files=@additional_doc.txt"

# 6. Query a single collection
echo -e "\n\n6. Query Single Collection"
curl -X POST "$BASE_URL/query/" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the main topic?",
    "collection": "test_collection"
  }'

# 7. Query multiple collections
echo -e "\n\n7. Query Multiple Collections"
curl -X POST "$BASE_URL/query/" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "API documentation",
    "collections": ["test_collection", "docs"]
  }'

# 8. Query all collections (no collection specified)
echo -e "\n\n8. Query All Collections"
curl -X POST "$BASE_URL/query/" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "search across all"
  }'

# 9. List all collections
echo -e "\n\n9. List Collections"
curl -X GET "$BASE_URL/list-indexes/" \
  -H "X-API-Key: $API_KEY"

# 10. Delete a collection
echo -e "\n\n10. Delete Collection"
curl -X DELETE "$BASE_URL/delete-index/test_collection" \
  -H "X-API-Key: $API_KEY"

# 11. Check API status
echo -e "\n\n11. API Status"
curl -X GET "$BASE_URL/status/"

echo -e "\n\n============================================"
echo "Examples complete!"
echo "============================================"
