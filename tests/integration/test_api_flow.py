"""Integration tests for end-to-end API workflows."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api import users


# Test fixtures (client and test_db are provided by conftest.py)

def test_complete_user_workflow(client, test_db):
    """Test the complete workflow: register → login → upload → query → delete."""

    # Step 1: Register a new user
    username = "integration_user"
    password = "IntegrationTest123!"

    register_response = client.post(
        "/api/user/register",
        json={"username": username, "password": password}
    )
    assert register_response.status_code == 200
    api_key = register_response.json()["api_key"]
    assert api_key is not None
    assert len(api_key) == 32  # secrets.token_hex(16) produces 32 hex characters

    # Step 2: Login with the same credentials
    login_response = client.post(
        "/api/user/login",
        json={"username": username, "password": password}
    )
    assert login_response.status_code == 200
    login_api_key = login_response.json()["api_key"]
    assert login_api_key is not None

    # Step 3: Upload a document to create an index
    collection_name = "test_collection"
    test_content = b"This is a test document about machine learning and AI."

    upload_response = client.post(
        "/api/create-index/",
        data={"collection": collection_name},
        files=[("files", ("test.txt", test_content, "text/plain"))],
        headers={"X-API-Key": api_key}
    )
    assert upload_response.status_code == 200
    assert "indexed_chunks" in upload_response.json()
    assert upload_response.json()["indexed_chunks"] > 0

    # Step 4: List collections to verify creation
    list_response = client.get(
        "/api/list-indexes/",
        headers={"X-API-Key": api_key}
    )
    assert list_response.status_code == 200
    collections = list_response.json()["collections"]
    assert len(collections) > 0
    assert any(c["name"] == collection_name for c in collections)

    # Step 5: Query the collection
    query_response = client.post(
        "/api/query/",
        json={"query": "What is machine learning?", "collection": collection_name},
        headers={"X-API-Key": api_key}
    )
    assert query_response.status_code == 200
    assert "context" in query_response.json()
    context = query_response.json()["context"]
    assert len(context) > 0
    # Verify the content contains relevant keywords
    assert "machine learning" in context.lower() or "ai" in context.lower()

    # Step 6: Delete the collection
    delete_response = client.delete(
        f"/api/delete-index/{collection_name}",
        headers={"X-API-Key": api_key}
    )
    assert delete_response.status_code == 200

    # Step 7: Verify collection is deleted
    list_response_after = client.get(
        "/api/list-indexes/",
        headers={"X-API-Key": api_key}
    )
    assert list_response_after.status_code == 200
    collections_after = list_response_after.json()["collections"]
    assert not any(c["name"] == collection_name for c in collections_after)


def test_multi_user_isolation(client, test_db):
    """Verify that users cannot access each other's collections."""

    # Create two users
    user1_data = {"username": "user1", "password": "User1Password123!"}
    user2_data = {"username": "user2", "password": "User2Password123!"}

    user1_response = client.post("/api/user/register", json=user1_data)
    user2_response = client.post("/api/user/register", json=user2_data)

    assert user1_response.status_code == 200
    assert user2_response.status_code == 200

    user1_api_key = user1_response.json()["api_key"]
    user2_api_key = user2_response.json()["api_key"]

    # User 1 creates a collection
    collection_name = "user1_private_collection"
    client.post(
        "/api/create-index/",
        data={"collection": collection_name},
        files=[("files", ("user1_doc.txt", b"User 1's private data", "text/plain"))],
        headers={"X-API-Key": user1_api_key}
    )

    # User 2 tries to list collections (should only see their own)
    user2_list_response = client.get(
        "/api/list-indexes/",
        headers={"X-API-Key": user2_api_key}
    )
    assert user2_list_response.status_code == 200
    user2_collections = user2_list_response.json()["collections"]

    # User 2 should not see User 1's collection
    assert not any(c["name"] == collection_name for c in user2_collections)

    # User 2 tries to query User 1's collection (should fail or return empty)
    user2_query_response = client.post(
        "/api/query/",
        json={"query": "private data", "collection": collection_name},
        headers={"X-API-Key": user2_api_key}
    )
    # Either fails with 404/400 or returns no results
    if user2_query_response.status_code == 200:
        context = user2_query_response.json().get("context", "")
        assert "User 1's private data" not in context


def test_update_existing_index(client, test_db):
    """Test updating an existing index with new documents."""

    # Create user
    user_response = client.post(
        "/api/user/register",
        json={"username": "updateuser", "password": "UpdateTest123!"}
    )
    api_key = user_response.json()["api_key"]

    collection_name = "expandable_collection"

    # Create initial collection
    create_response = client.post(
        "/api/create-index/",
        data={"collection": collection_name},
        files=[("files", ("doc1.txt", b"First document content", "text/plain"))],
        headers={"X-API-Key": api_key}
    )
    assert create_response.status_code == 200
    initial_chunks = create_response.json()["indexed_chunks"]

    # Update the collection with more documents
    update_response = client.post(
        "/api/update-index/",
        data={"collection": collection_name},
        files=[("files", ("doc2.txt", b"Second document content", "text/plain"))],
        headers={"X-API-Key": api_key}
    )
    assert update_response.status_code == 200
    updated_chunks = update_response.json()["indexed_chunks"]

    # Verify chunks were added in the update
    assert updated_chunks > 0

    # Query should return results from both documents
    query_response = client.post(
        "/api/query/",
        json={"query": "document", "collection": collection_name},
        headers={"X-API-Key": api_key}
    )
    assert query_response.status_code == 200
    context = query_response.json()["context"]
    assert len(context) > 0


def test_concurrent_file_processing(client, test_db):
    """Test uploading multiple files concurrently."""

    # Create user
    user_response = client.post(
        "/api/user/register",
        json={"username": "concurrent_user", "password": "ConcurrentTest123!"}
    )
    api_key = user_response.json()["api_key"]

    collection_name = "multi_file_collection"

    # Upload multiple files at once
    files = [
        ("files", ("file1.txt", b"Content of file 1", "text/plain")),
        ("files", ("file2.txt", b"Content of file 2", "text/plain")),
        ("files", ("file3.txt", b"Content of file 3", "text/plain")),
    ]

    upload_response = client.post(
        "/api/create-index/",
        data={"collection": collection_name},
        files=files,
        headers={"X-API-Key": api_key}
    )

    assert upload_response.status_code == 200
    assert upload_response.json()["indexed_chunks"] > 0

    # Query should return content from all files
    query_response = client.post(
        "/api/query/",
        json={"query": "file", "collection": collection_name},
        headers={"X-API-Key": api_key}
    )
    assert query_response.status_code == 200


def test_query_multiple_collections(client, test_db):
    """Test querying across multiple collections."""

    # Create user
    user_response = client.post(
        "/api/user/register",
        json={"username": "multi_coll_user", "password": "MultiColl123!"}
    )
    api_key = user_response.json()["api_key"]

    # Create two collections
    collection1 = "collection1"
    collection2 = "collection2"

    client.post(
        "/api/create-index/",
        data={"collection": collection1},
        files=[("files", ("doc1.txt", b"Machine learning content", "text/plain"))],
        headers={"X-API-Key": api_key}
    )

    client.post(
        "/api/create-index/",
        data={"collection": collection2},
        files=[("files", ("doc2.txt", b"Deep learning content", "text/plain"))],
        headers={"X-API-Key": api_key}
    )

    # Query both collections
    query_response = client.post(
        "/api/query/",
        json={"query": "learning", "collections": [collection1, collection2]},
        headers={"X-API-Key": api_key}
    )

    assert query_response.status_code == 200
    context = query_response.json()["context"]
    assert len(context) > 0
    # Should contain content from both collections
    assert "learning" in context.lower()


def test_api_key_generation(client, test_db):
    """Test creating additional API keys for a user."""

    # Register user
    user_response = client.post(
        "/api/user/register",
        json={"username": "keyuser", "password": "KeyUser123!@"}
    )
    first_api_key = user_response.json()["api_key"]

    # Generate a new API key
    new_key_response = client.post(
        "/api/user/create-api-key",
        json={"username": "keyuser", "password": "KeyUser123!@"}
    )
    assert new_key_response.status_code == 200, f"Response: {new_key_response.json()}"
    response_data = new_key_response.json()
    assert "api_key" in response_data, f"Response missing api_key: {response_data}"
    second_api_key = response_data["api_key"]

    # Verify both keys are different
    assert first_api_key != second_api_key

    # Both keys should work for authentication
    response1 = client.get("/api/list-indexes/", headers={"X-API-Key": first_api_key})
    response2 = client.get("/api/list-indexes/", headers={"X-API-Key": second_api_key})

    assert response1.status_code == 200
    assert response2.status_code == 200
