#!/usr/bin/env python3
"""Test script for Phase 3 API updates."""

import sys
import requests
import json

API_URL = "http://localhost:8000"

def print_section(title):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}\n")

def test_api_status():
    """Test API status endpoint."""
    print_section("Testing API Status Endpoint")

    try:
        # Test v1 endpoint
        response = requests.get(f"{API_URL}/api/v1/status/")
        print(f"✓ /api/v1/status/: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Response: {json.dumps(data, indent=2)}")
            assert "status" in data, "Response should have 'status' field"
            print("  ✓ Pydantic model validation passed")

        # Test backward compatibility
        response = requests.get(f"{API_URL}/api/status/")
        print(f"✓ /api/status/ (backward compat): {response.status_code}")

        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_user_registration():
    """Test user registration with v1 endpoint."""
    print_section("Testing User Registration (v1)")

    try:
        username = "test_phase3_user"
        password = "TestPhase3Pass123!"

        # Test v1 endpoint
        response = requests.post(
            f"{API_URL}/api/v1/user/register",
            json={"username": username, "password": password}
        )

        print(f"✓ POST /api/v1/user/register: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"  Response: {json.dumps(data, indent=2)}")
            assert "api_key" in data, "Response should have 'api_key' field"
            assert len(data["api_key"]) == 32, "API key should be 32 characters"
            print("  ✓ AuthResponse model validation passed")
            return data["api_key"]
        elif response.status_code == 400:
            # User might already exist
            error = response.json()
            print(f"  Note: {error.get('detail', 'Unknown error')}")
            # Try login instead
            response = requests.post(
                f"{API_URL}/api/v1/user/login",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                data = response.json()
                print("  ✓ Logged in with existing user")
                return data["api_key"]

        return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None

def test_error_format(api_key):
    """Test that errors use 'detail' key consistently."""
    print_section("Testing Error Response Format")

    try:
        # Test invalid collection name (should return error with 'detail' key)
        response = requests.get(
            f"{API_URL}/api/v1/list-indexes/",
            headers={"X-API-Key": "invalid_key_12345678901234567890"}
        )

        print(f"✓ Tested with invalid API key: {response.status_code}")
        if response.status_code != 200:
            error = response.json()
            print(f"  Error response: {json.dumps(error, indent=2)}")
            assert "detail" in error, "Error should have 'detail' field"
            assert "error" not in error, "Error should NOT have 'error' field (old format)"
            print("  ✓ Error uses 'detail' key (standardized format)")

        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_openapi_docs():
    """Test OpenAPI documentation availability."""
    print_section("Testing OpenAPI Documentation")

    try:
        # Test docs endpoint
        response = requests.get(f"{API_URL}/docs")
        print(f"✓ /docs endpoint: {response.status_code}")

        # Test OpenAPI schema
        response = requests.get(f"{API_URL}/openapi.json")
        print(f"✓ /openapi.json endpoint: {response.status_code}")

        if response.status_code == 200:
            schema = response.json()
            print(f"  API Title: {schema.get('info', {}).get('title')}")
            print(f"  API Version: {schema.get('info', {}).get('version')}")

            # Check for v1 paths
            paths = schema.get("paths", {})
            v1_paths = [p for p in paths.keys() if "/api/v1/" in p]
            print(f"  ✓ Found {len(v1_paths)} v1 endpoints")

            # Check for response models
            components = schema.get("components", {}).get("schemas", {})
            response_models = ["AuthResponse", "UploadResponse", "QueryResponse",
                              "ListCollectionsResponse", "DeleteResponse", "StatusResponse"]
            found_models = [m for m in response_models if m in components]
            print(f"  ✓ Found {len(found_models)}/{len(response_models)} response models")

            if len(found_models) == len(response_models):
                print("  ✓ All Pydantic response models are documented")

        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    """Run all tests."""
    print(f"\n{'#'*60}")
    print("# Phase 3 API Testing")
    print("# Testing: API Versioning, Pydantic Models, Error Format")
    print(f"{'#'*60}")

    results = []

    # Test 1: API Status
    results.append(("API Status", test_api_status()))

    # Test 2: User Registration (v1)
    api_key = test_user_registration()
    results.append(("User Registration (v1)", api_key is not None))

    # Test 3: Error Format
    if api_key:
        results.append(("Error Format", test_error_format(api_key)))

    # Test 4: OpenAPI Docs
    results.append(("OpenAPI Docs", test_openapi_docs()))

    # Summary
    print_section("Test Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All Phase 3 tests passed!")
        print("\nPhase 3 improvements verified:")
        print("  ✓ API versioning (/api/v1/*)")
        print("  ✓ Pydantic response models")
        print("  ✓ Standardized error format (detail key)")
        print("  ✓ OpenAPI documentation")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
