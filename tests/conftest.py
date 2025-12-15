"""Shared test configuration and fixtures for pytest."""

import sys
from pathlib import Path

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api import users
from vector_store.vector_index import clear_client_cache


@pytest.fixture(scope="session", autouse=True)
def disable_rate_limiting():
    """Disable rate limiting for all tests."""
    from api.rate_limiting import limiter
    # Disable rate limiting by setting enabled to False
    limiter.enabled = False
    yield
    # Re-enable after tests (optional)
    limiter.enabled = True


@pytest.fixture(scope="function", autouse=True)
def cleanup_client_cache():
    """Clear ChromaDB client cache before each test for isolation."""
    clear_client_cache()
    yield
    clear_client_cache()


@pytest.fixture(scope="session")
def client():
    """Create a test client for the API (session-scoped)."""
    return TestClient(app)


@pytest.fixture(scope="function")
def test_db(tmp_path, monkeypatch):
    """
    Create a temporary database for testing (function-scoped).
    This fixture is available to all tests.
    """
    db_path = tmp_path / "test_users.db"
    vector_path = tmp_path / "vectors"

    # Monkeypatch both database paths before any database operations
    monkeypatch.setattr(users, "DB_PATH", str(db_path))
    monkeypatch.setattr("config.VECTOR_DB_PATH", str(vector_path))

    # Initialize the database with the new path
    users.init_db()

    yield db_path
