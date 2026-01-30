#!/usr/bin/env python3
"""
External Connectivity Test Suite for Knowledge Manager API

Tests the deployed API at knowledge-manager.promethean-labs.co to verify
all endpoints are working correctly from an external client perspective.

Usage:
    Standalone:  python tests/test_external_connectivity.py
    With URL:    python tests/test_external_connectivity.py --url https://your-api.com
    With pytest: pytest tests/test_external_connectivity.py -v
    With env:    TEST_API_URL="https://your-api.com" pytest tests/test_external_connectivity.py -v
"""

import argparse
import io
import os
import sys
import uuid
from typing import Optional

import requests

# Configuration
DEFAULT_URL = "https://knowledge-manager.promethean-labs.co"
TEST_PASSWORD = "SecureTestPass123!"

# Sample document content for testing
SAMPLE_DOCUMENT_CONTENT = """
Knowledge Management Systems Overview

A knowledge management system (KMS) is a technology solution that helps organizations
capture, store, and share knowledge across their workforce. These systems are designed
to improve efficiency, foster innovation, and preserve institutional knowledge.

Key Components of Knowledge Management:
1. Knowledge Capture - Collecting information from various sources
2. Knowledge Storage - Organizing and storing information in accessible formats
3. Knowledge Retrieval - Finding and accessing relevant information quickly
4. Knowledge Sharing - Distributing knowledge to those who need it

Vector databases play a crucial role in modern knowledge management by enabling
semantic search capabilities. Unlike traditional keyword-based search, semantic
search understands the meaning and context of queries, providing more relevant results.

Benefits of vector-based knowledge management:
- Improved search accuracy through semantic understanding
- Ability to find related concepts even without exact keyword matches
- Support for multi-modal content including text, images, and documents
- Scalable architecture for large knowledge bases

This document serves as a test file for the Knowledge Manager API external
connectivity tests. It contains enough content to generate multiple chunks
when processed by the ingestion pipeline.
"""


class TestState:
    """Shared state across tests."""
    api_key: Optional[str] = None
    username: Optional[str] = None
    collection_name: Optional[str] = None
    base_url: str = DEFAULT_URL


# Initialize test state
state = TestState()


def get_base_url() -> str:
    """Get the base URL from environment or state."""
    return os.environ.get("TEST_API_URL", state.base_url)


def print_result(test_name: str, success: bool, message: str = "", details: str = ""):
    """Print test result with color coding."""
    if success:
        status = "\033[92mPASS\033[0m"  # Green
    else:
        status = "\033[91mFAIL\033[0m"  # Red

    print(f"[{status}] {test_name}")
    if message:
        print(f"       {message}")
    if details:
        print(f"       Details: {details}")


def test_health_check() -> bool:
    """Test 1: Health check endpoint (unauthenticated)."""
    url = f"{get_base_url()}/api/v1/status/"

    try:
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok":
                print_result("Health Check", True, "API is reachable and healthy")
                return True
            else:
                print_result("Health Check", False, f"Unexpected response: {data}")
                return False
        else:
            print_result("Health Check", False, f"Status code: {response.status_code}", response.text[:200])
            return False
    except requests.exceptions.RequestException as e:
        print_result("Health Check", False, f"Connection error: {e}")
        return False


def test_register_user() -> bool:
    """Test 2: Register a new user."""
    url = f"{get_base_url()}/api/v1/user/register"

    # Generate unique username
    state.username = f"test_user_{uuid.uuid4().hex[:8]}"

    payload = {
        "username": state.username,
        "password": TEST_PASSWORD
    }

    try:
        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            data = response.json()
            if "api_key" in data:
                state.api_key = data["api_key"]
                print_result("Register User", True, f"Created user: {state.username}")
                return True
            else:
                print_result("Register User", False, "No API key in response", str(data))
                return False
        else:
            print_result("Register User", False, f"Status code: {response.status_code}", response.text[:200])
            return False
    except requests.exceptions.RequestException as e:
        print_result("Register User", False, f"Connection error: {e}")
        return False


def test_login_user() -> bool:
    """Test 3: Login with the registered user."""
    if not state.username:
        print_result("Login User", False, "Skipped - no user registered")
        return False

    url = f"{get_base_url()}/api/v1/user/login"

    payload = {
        "username": state.username,
        "password": TEST_PASSWORD
    }

    try:
        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            data = response.json()
            if "api_key" in data:
                # Update API key (login returns a new one)
                state.api_key = data["api_key"]
                print_result("Login User", True, "Successfully logged in")
                return True
            else:
                print_result("Login User", False, "No API key in response", str(data))
                return False
        else:
            print_result("Login User", False, f"Status code: {response.status_code}", response.text[:200])
            return False
    except requests.exceptions.RequestException as e:
        print_result("Login User", False, f"Connection error: {e}")
        return False


def test_create_index() -> bool:
    """Test 4: Create an index by uploading a document."""
    if not state.api_key:
        print_result("Create Index", False, "Skipped - no API key available")
        return False

    url = f"{get_base_url()}/api/v1/create-index/"

    # Generate unique collection name
    state.collection_name = f"test_collection_{uuid.uuid4().hex[:8]}"

    headers = {
        "X-API-Key": state.api_key
    }

    # Create an in-memory file
    file_content = SAMPLE_DOCUMENT_CONTENT.encode("utf-8")
    files = {
        "files": ("test_document.txt", io.BytesIO(file_content), "text/plain")
    }
    data = {
        "collection": state.collection_name
    }

    try:
        response = requests.post(url, headers=headers, files=files, data=data, timeout=60)

        if response.status_code == 200:
            resp_data = response.json()
            indexed_chunks = resp_data.get("indexed_chunks", 0)
            print_result("Create Index", True,
                        f"Collection: {state.collection_name}",
                        f"Indexed {indexed_chunks} chunks")
            return True
        else:
            print_result("Create Index", False, f"Status code: {response.status_code}", response.text[:200])
            return False
    except requests.exceptions.RequestException as e:
        print_result("Create Index", False, f"Connection error: {e}")
        return False


def test_list_indexes() -> bool:
    """Test 5: List indexes and verify the created collection exists."""
    if not state.api_key:
        print_result("List Indexes", False, "Skipped - no API key available")
        return False

    url = f"{get_base_url()}/api/v1/list-indexes/"

    headers = {
        "X-API-Key": state.api_key
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            data = response.json()
            collections = data.get("collections", [])
            collection_names = [c.get("name") for c in collections]

            if state.collection_name and state.collection_name in collection_names:
                # Find our collection details
                our_collection = next(c for c in collections if c.get("name") == state.collection_name)
                print_result("List Indexes", True,
                            f"Found {len(collections)} collection(s)",
                            f"Our collection has {our_collection.get('num_chunks', 0)} chunks")
                return True
            elif not state.collection_name:
                print_result("List Indexes", True, f"Found {len(collections)} collection(s)")
                return True
            else:
                print_result("List Indexes", False,
                            f"Collection '{state.collection_name}' not found",
                            f"Available: {collection_names}")
                return False
        else:
            print_result("List Indexes", False, f"Status code: {response.status_code}", response.text[:200])
            return False
    except requests.exceptions.RequestException as e:
        print_result("List Indexes", False, f"Connection error: {e}")
        return False


def test_query_index() -> bool:
    """Test 6: Query the created index."""
    if not state.api_key or not state.collection_name:
        print_result("Query Index", False, "Skipped - no API key or collection available")
        return False

    url = f"{get_base_url()}/api/v1/query/"

    headers = {
        "X-API-Key": state.api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "query": "What are the benefits of vector databases for knowledge management?",
        "collection": state.collection_name
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)

        if response.status_code == 200:
            data = response.json()
            context = data.get("context", "")
            raw_results = data.get("raw_results", {})

            # Check if we got meaningful results
            if context and len(context) > 50:
                num_results = len(raw_results.get("ids", [[]])[0]) if raw_results else 0
                print_result("Query Index", True,
                            f"Retrieved {num_results} result(s)",
                            f"Context preview: {context[:100]}...")
                return True
            else:
                print_result("Query Index", False, "Empty or minimal context returned", str(data)[:200])
                return False
        else:
            print_result("Query Index", False, f"Status code: {response.status_code}", response.text[:200])
            return False
    except requests.exceptions.RequestException as e:
        print_result("Query Index", False, f"Connection error: {e}")
        return False


def test_delete_index() -> bool:
    """Test 7: Delete the created index."""
    if not state.api_key or not state.collection_name:
        print_result("Delete Index", False, "Skipped - no API key or collection available")
        return False

    url = f"{get_base_url()}/api/v1/delete-index/{state.collection_name}"

    headers = {
        "X-API-Key": state.api_key
    }

    try:
        response = requests.delete(url, headers=headers, timeout=30)

        if response.status_code == 200:
            print_result("Delete Index", True, f"Deleted collection: {state.collection_name}")
            return True
        else:
            print_result("Delete Index", False, f"Status code: {response.status_code}", response.text[:200])
            return False
    except requests.exceptions.RequestException as e:
        print_result("Delete Index", False, f"Connection error: {e}")
        return False


def test_verify_deletion() -> bool:
    """Test 8: Verify the index was deleted."""
    if not state.api_key:
        print_result("Verify Deletion", False, "Skipped - no API key available")
        return False

    url = f"{get_base_url()}/api/v1/list-indexes/"

    headers = {
        "X-API-Key": state.api_key
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            data = response.json()
            collections = data.get("collections", [])
            collection_names = [c.get("name") for c in collections]

            if state.collection_name and state.collection_name not in collection_names:
                print_result("Verify Deletion", True, "Collection successfully removed")
                return True
            elif state.collection_name in collection_names:
                print_result("Verify Deletion", False, "Collection still exists after deletion")
                return False
            else:
                print_result("Verify Deletion", True, "No collections remaining")
                return True
        else:
            print_result("Verify Deletion", False, f"Status code: {response.status_code}", response.text[:200])
            return False
    except requests.exceptions.RequestException as e:
        print_result("Verify Deletion", False, f"Connection error: {e}")
        return False


def run_all_tests() -> bool:
    """Run all tests in sequence and return overall success."""
    print("\n" + "=" * 60)
    print("Knowledge Manager API - External Connectivity Tests")
    print(f"Target: {get_base_url()}")
    print("=" * 60 + "\n")

    tests = [
        ("Health Check", test_health_check),
        ("Register User", test_register_user),
        ("Login User", test_login_user),
        ("Create Index", test_create_index),
        ("List Indexes", test_list_indexes),
        ("Query Index", test_query_index),
        ("Delete Index", test_delete_index),
        ("Verify Deletion", test_verify_deletion),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_result(name, False, f"Unexpected error: {e}")
            results.append((name, False))
        print()  # Blank line between tests

    # Summary
    passed = sum(1 for _, r in results if r)
    total = len(results)

    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("\033[92mAll tests passed!\033[0m")
    else:
        print("\033[91mSome tests failed.\033[0m")
        failed_tests = [name for name, r in results if not r]
        print(f"Failed: {', '.join(failed_tests)}")

    print("=" * 60 + "\n")

    return passed == total


# Pytest-compatible test functions
class TestExternalConnectivity:
    """Pytest test class for external connectivity tests."""

    @classmethod
    def setup_class(cls):
        """Set up test state before running tests."""
        # Reset state
        state.api_key = None
        state.username = None
        state.collection_name = None

    def test_01_health_check(self):
        """Test health check endpoint."""
        assert test_health_check(), "Health check failed"

    def test_02_register_user(self):
        """Test user registration."""
        assert test_register_user(), "User registration failed"

    def test_03_login_user(self):
        """Test user login."""
        assert test_login_user(), "User login failed"

    def test_04_create_index(self):
        """Test index creation."""
        assert test_create_index(), "Index creation failed"

    def test_05_list_indexes(self):
        """Test listing indexes."""
        assert test_list_indexes(), "Listing indexes failed"

    def test_06_query_index(self):
        """Test querying index."""
        assert test_query_index(), "Querying index failed"

    def test_07_delete_index(self):
        """Test index deletion."""
        assert test_delete_index(), "Index deletion failed"

    def test_08_verify_deletion(self):
        """Test verifying index deletion."""
        assert test_verify_deletion(), "Verify deletion failed"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test external connectivity to Knowledge Manager API"
    )
    parser.add_argument(
        "--url",
        type=str,
        default=DEFAULT_URL,
        help=f"Base URL of the API (default: {DEFAULT_URL})"
    )

    args = parser.parse_args()

    # Set the base URL
    state.base_url = args.url

    # Run tests
    success = run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if success else 1)
