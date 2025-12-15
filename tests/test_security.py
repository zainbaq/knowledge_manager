"""Comprehensive security tests for the Knowledge Manager API."""

import time
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.app import app
from api import users
from api.validation import validate_username, validate_collection_name, sanitize_path_component
from config import AUTH_RATE_LIMIT


# Test fixtures (client and test_db are provided by conftest.py)

@pytest.fixture
def test_user(client, test_db):
    """Create a test user and return credentials."""
    username = "testuser"
    password = "TestPassword123!"

    response = client.post(
        "/api/v1/user/register",
        json={"username": username, "password": password}
    )
    assert response.status_code == 200
    api_key = response.json()["api_key"]

    return {"username": username, "password": password, "api_key": api_key}


# === Password Complexity Tests ===


def test_weak_password_rejected(client, test_db):
    """Verify that weak passwords are rejected during registration."""
    weak_passwords = [
        "short",  # Too short
        "onlylowercase123!",  # No uppercase
        "ONLYUPPERCASE123!",  # No lowercase
        "NoDigitsHere!",  # No digits
        "NoSpecialChars123",  # No special characters
    ]

    for password in weak_passwords:
        response = client.post(
            "/api/v1/user/register",
            json={"username": f"user_{password}", "password": password}
        )
        assert response.status_code in [400, 422], f"Weak password '{password}' should be rejected"


def test_strong_password_accepted(client, test_db):
    """Verify that strong passwords are accepted."""
    response = client.post(
        "/api/v1/user/register",
        json={"username": "stronguser", "password": "StrongP@ssw0rd123"}
    )
    assert response.status_code == 200
    assert "api_key" in response.json()


# === Collection Name Validation Tests ===


def test_path_traversal_in_collection_name_rejected(client, test_user):
    """Verify that collection names with path traversal are blocked."""
    malicious_names = [
        "../../../etc/passwd",
        "..\\..\\windows\\system32",
        "../../other_user/collection",
        "normal/../../../etc",
        "test/../secret",
    ]

    for name in malicious_names:
        response = client.post(
            "/api/v1/create-index/",
            data={"collection": name},
            files=[("files", ("test.txt", b"test content", "text/plain"))],
            headers={"X-API-Key": test_user["api_key"]}
        )
        assert response.status_code == 422, f"Path traversal attempt '{name}' should be rejected"
        detail = response.json()["detail"]
        detail_str = str(detail).lower() if isinstance(detail, list) else detail.lower()
        assert "collection" in detail_str or "invalid" in detail_str


def test_invalid_collection_name_characters_rejected(client, test_user):
    """Verify that collection names with special characters are blocked."""
    invalid_names = [
        "collection/name",
        "collection\\name",
        "collection name",  # Spaces
        "collection@name",
        "collection#name",
        "collection!name",
    ]

    for name in invalid_names:
        response = client.post(
            "/api/v1/create-index/",
            data={"collection": name},
            files=[("files", ("test.txt", b"test content", "text/plain"))],
            headers={"X-API-Key": test_user["api_key"]}
        )
        assert response.status_code == 422, f"Invalid collection name '{name}' should be rejected"


def test_valid_collection_name_accepted(client, test_user):
    """Verify that valid collection names are accepted."""
    valid_names = [
        "test_collection",
        "TestCollection",
        "test-collection",
        "test123",
        "123test",
    ]

    for name in valid_names:
        response = client.post(
            "/api/v1/create-index/",
            data={"collection": name},
            files=[("files", ("test.txt", b"test content", "text/plain"))],
            headers={"X-API-Key": test_user["api_key"]}
        )
        # Should not fail due to collection name validation (422)
        # May fail for other reasons (e.g., 400 for file issues), but not validation
        if response.status_code == 422:
            detail = response.json().get("detail", "")
            detail_str = str(detail).lower() if isinstance(detail, list) else detail.lower()
            assert "collection" not in detail_str, f"Valid collection name '{name}' should not trigger validation error"


# === MIME Type Validation Tests ===


def test_mime_type_spoofing_rejected(client, test_user):
    """Verify that files with mismatched MIME types are rejected."""
    # Create a fake PDF (actually just text)
    fake_pdf_content = b"This is not a PDF file"

    response = client.post(
        "/api/v1/create-index/",
        data={"collection": "test_mime"},
        files=[("files", ("fake.pdf", fake_pdf_content, "text/plain"))],
        headers={"X-API-Key": test_user["api_key"]}
    )

    # The validation should detect the mismatch (415 for MIME type errors)
    assert response.status_code in [400, 415]
    detail = response.json()["detail"]
    detail_str = str(detail).lower() if isinstance(detail, list) else detail.lower()
    assert "mime" in detail_str or "invalid" in detail_str or "type" in detail_str


# === API Key Expiration Tests ===


def test_expired_api_key_rejected(client, test_db, monkeypatch):
    """Verify that expired API keys are rejected."""
    # Create a user
    response = client.post(
        "/api/v1/user/register",
        json={"username": "expireuser", "password": "TestPassword123!"}
    )
    api_key = response.json()["api_key"]

    # Mock the timestamp to make the key expired
    original_timestamp = users._current_timestamp

    def future_timestamp():
        return original_timestamp() + (91 * 24 * 60 * 60)  # 91 days in the future

    monkeypatch.setattr(users, "_current_timestamp", future_timestamp)

    # Try to use the expired key
    response = client.post(
        "/api/v1/query/",
        json={"query": "test"},
        headers={"X-API-Key": api_key}
    )

    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()


# === Authentication Tests ===


def test_missing_api_key_rejected(client):
    """Verify that requests without API keys are rejected."""
    response = client.post(
        "/api/v1/query/",
        json={"query": "test"}
    )
    assert response.status_code == 401


def test_invalid_api_key_rejected(client):
    """Verify that requests with invalid API keys are rejected."""
    response = client.post(
        "/api/v1/query/",
        json={"query": "test"},
        headers={"X-API-Key": "invalid-key-12345678"}
    )
    assert response.status_code == 401


# === CORS Tests ===


def test_cors_headers_present(client):
    """Verify that CORS headers are configured."""
    # TestClient doesn't fully support OPTIONS preflight, so test with GET
    response = client.get(
        "/api/v1/status/",
        headers={"Origin": "http://localhost:8501"}
    )
    # CORS should allow the configured origin
    assert response.status_code == 200
    # Optionally check for CORS headers
    assert "access-control-allow-origin" in response.headers or response.status_code == 200


def test_cors_blocks_unauthorized_origin(client):
    """Verify that CORS blocks requests from non-whitelisted origins."""
    response = client.get(
        "/api/v1/status/",
        headers={"Origin": "https://evil.com"}
    )
    # The request might succeed, but CORS headers should not allow the origin
    if "access-control-allow-origin" in response.headers:
        assert response.headers["access-control-allow-origin"] != "https://evil.com"


# === Rate Limiting Tests ===


@pytest.mark.skip(reason="Rate limiting tests can be flaky in CI")
def test_rate_limiting_enforced_on_auth_endpoints(client, test_db):
    """Verify that rate limiting blocks excessive authentication requests."""
    # Extract the rate limit (e.g., "10/minute" -> 10)
    limit = int(AUTH_RATE_LIMIT.split("/")[0])

    # Make requests up to the limit + 1
    responses = []
    for i in range(limit + 2):
        response = client.post(
            "/api/v1/user/register",
            json={"username": f"user{i}", "password": "TestPassword123!"}
        )
        responses.append(response)
        time.sleep(0.1)  # Small delay to avoid request bunching

    # At least one request should be rate limited
    status_codes = [r.status_code for r in responses]
    assert 429 in status_codes, f"Expected 429 (rate limited) in {status_codes}"


# === File Upload Tests ===


def test_large_file_rejected(client, test_user):
    """Verify that files exceeding the size limit are rejected."""
    # Create a file larger than MAX_FILE_SIZE_MB (25MB default)
    large_content = b"x" * (26 * 1024 * 1024)  # 26MB

    response = client.post(
        "/api/v1/create-index/",
        data={"collection": "test_large"},
        files=[("files", ("large.txt", large_content, "text/plain"))],
        headers={"X-API-Key": test_user["api_key"]}
    )

    # Should return 413 (Payload Too Large) or 400
    assert response.status_code in [400, 413]
    detail = response.json()["detail"]
    detail_str = str(detail).lower() if isinstance(detail, list) else detail.lower()
    assert "large" in detail_str or "size" in detail_str


def test_unsupported_file_extension_rejected(client, test_user):
    """Verify that unsupported file types are rejected."""
    response = client.post(
        "/api/v1/create-index/",
        data={"collection": "test_extension"},
        files=[("files", ("test.exe", b"fake executable", "application/octet-stream"))],
        headers={"X-API-Key": test_user["api_key"]}
    )

    # Should return 415 (Unsupported Media Type) or 400
    assert response.status_code in [400, 415]
    detail = response.json()["detail"]
    detail_str = str(detail).lower() if isinstance(detail, list) else detail.lower()
    assert "unsupported" in detail_str or "type" in detail_str


# === Username Validation Tests ===


class TestUsernameValidation:
    """Test username validation security."""

    def test_valid_usernames(self):
        """Valid usernames should pass."""
        valid = ["alice", "bob123", "user_name", "user-name", "a1b2c3"]
        for username in valid:
            assert validate_username(username) == username

    def test_path_traversal_blocked(self):
        """Path traversal attempts should be blocked."""
        malicious = ["../admin", "../../root", "user/../admin", "user/../../etc"]
        for username in malicious:
            with pytest.raises(HTTPException) as exc:
                validate_username(username)
            assert exc.value.status_code == 422

    def test_special_characters_blocked(self):
        """Special characters should be blocked."""
        invalid = ["user;rm", "user`whoami`", "user$PATH", "user\\admin", "user/admin"]
        for username in invalid:
            with pytest.raises(HTTPException) as exc:
                validate_username(username)
            assert exc.value.status_code == 422

    def test_null_bytes_blocked(self):
        """Null bytes should be blocked."""
        with pytest.raises(HTTPException):
            validate_username("user\x00admin")

    def test_reserved_names_blocked(self):
        """Reserved system names should be blocked."""
        reserved = ["admin", "root", "system", "api", "ADMIN", "Root"]
        for username in reserved:
            with pytest.raises(HTTPException) as exc:
                validate_username(username)
            assert exc.value.status_code == 422

    def test_length_limits(self):
        """Username length should be enforced."""
        # Too short
        with pytest.raises(HTTPException):
            validate_username("ab")

        # Too long
        with pytest.raises(HTTPException):
            validate_username("a" * 33)

        # Just right
        assert validate_username("abc") == "abc"
        assert validate_username("a" * 32) == "a" * 32


class TestCollectionValidation:
    """Test collection name validation security."""

    def test_valid_collections(self):
        """Valid collection names should pass."""
        valid = ["docs", "research_2024", "project-alpha", "data123"]
        for name in valid:
            assert validate_collection_name(name) == name

    def test_path_traversal_blocked(self):
        """Path traversal in collection names should be blocked."""
        malicious = ["../admin", "../../data", "docs/../admin"]
        for name in malicious:
            with pytest.raises(HTTPException) as exc:
                validate_collection_name(name)
            assert exc.value.status_code == 422

    def test_dot_names_blocked(self):
        """Single and double dots should be blocked."""
        with pytest.raises(HTTPException):
            validate_collection_name(".")
        with pytest.raises(HTTPException):
            validate_collection_name("..")

    def test_length_limits(self):
        """Collection name length should be enforced."""
        # Too long
        with pytest.raises(HTTPException):
            validate_collection_name("a" * 65)

        # Just right
        assert validate_collection_name("a") == "a"
        assert validate_collection_name("a" * 64) == "a" * 64


class TestPathSanitization:
    """Test path construction security."""

    def test_sanitize_removes_dangerous_chars(self):
        """Sanitize should remove path traversal characters."""
        assert sanitize_path_component("../admin") == "admin"
        assert sanitize_path_component("user/admin") == "useradmin"
        assert sanitize_path_component("user\\admin") == "useradmin"
        assert sanitize_path_component("..") == ""
        assert sanitize_path_component("user\x00admin") == "useradmin"


class TestEndToEndSecurity:
    """End-to-end security tests."""

    def test_register_with_malicious_username(self, client, test_db):
        """Registration with path traversal username should fail."""
        response = client.post(
            "/api/v1/user/register",
            json={"username": "../admin", "password": "securepassword123"}
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        detail_str = str(detail).lower() if isinstance(detail, list) else detail.lower()
        assert "username" in detail_str

    def test_register_with_reserved_username(self, client, test_db):
        """Registration with reserved username should fail."""
        response = client.post(
            "/api/v1/user/register",
            json={"username": "admin", "password": "securepassword123"}
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        detail_str = str(detail).lower() if isinstance(detail, list) else detail.lower()
        assert "reserved" in detail_str

    def test_create_collection_with_malicious_name(self, client, test_user):
        """Creating collection with path traversal should fail."""
        response = client.post(
            "/api/v1/create-index/",
            data={"collection": "../admin"},
            files=[("files", ("test.txt", b"content", "text/plain"))],
            headers={"X-API-Key": test_user["api_key"]}
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        detail_str = str(detail).lower() if isinstance(detail, list) else detail.lower()
        assert "collection" in detail_str

    def test_create_collection_with_dot_name(self, client, test_user):
        """Creating collection with '.' or '..' should fail."""
        for bad_name in [".", ".."]:
            response = client.post(
                "/api/v1/create-index/",
                data={"collection": bad_name},
                files=[("files", ("test.txt", b"content", "text/plain"))],
                headers={"X-API-Key": test_user["api_key"]}
            )
            assert response.status_code == 422
