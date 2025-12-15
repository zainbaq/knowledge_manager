"""Tests for user registration and API key generation."""

import sqlite3
import pytest
from fastapi.testclient import TestClient

from api.app import app
from api import users
from config import VECTOR_DB_PATH


@pytest.fixture
def setup_test_db(tmp_path, monkeypatch):
    """Setup test database for each test."""
    db_path = tmp_path / "users.db"
    vector_path = tmp_path / "vectors"

    # Monkeypatch both database paths
    monkeypatch.setattr(users, "DB_PATH", str(db_path))
    monkeypatch.setattr("config.VECTOR_DB_PATH", str(vector_path))

    # Initialize the database
    users.init_db()

    yield db_path


def test_login_returns_new_api_key(setup_test_db):
    db_path = setup_test_db

    client = TestClient(app)

    # Register user
    resp = client.post(
        "/api/user/register",
        json={"username": "alice", "password": "Str0ngPass!23"},
    )
    assert resp.status_code == 200

    # Login should return a new key
    resp = client.post(
        "/api/user/login",
        json={"username": "alice", "password": "Str0ngPass!23"},
    )
    assert resp.status_code == 200
    api_key = resp.json()["api_key"]
    assert api_key

    # Stored key is hashed
    conn = sqlite3.connect(users.DB_PATH)
    cur = conn.execute("SELECT key_hash FROM api_keys")
    stored = cur.fetchone()[0]
    conn.close()
    assert stored != api_key

    # Lookup by API key works
    user = users.get_user_by_api_key(api_key)
    assert user["username"] == "alice"


def test_create_api_key_generates_unique_keys(setup_test_db):
    db_path = setup_test_db

    client = TestClient(app)
    password = "B3tterPass!42"
    client.post("/api/user/register", json={"username": "bob", "password": password})

    resp1 = client.post(
        "/api/user/create-api-key", json={"username": "bob", "password": password}
    )
    resp2 = client.post(
        "/api/user/create-api-key", json={"username": "bob", "password": password}
    )

    key1 = resp1.json()["api_key"]
    key2 = resp2.json()["api_key"]
    assert key1 != key2

    conn = sqlite3.connect(users.DB_PATH)
    cur = conn.execute("SELECT COUNT(*) FROM api_keys")
    count = cur.fetchone()[0]
    conn.close()
    # 3 keys: 1 from registration + 2 from create-api-key calls
    assert count == 3


def test_register_enforces_password_policy(setup_test_db):
    db_path = setup_test_db

    client = TestClient(app)
    resp = client.post(
        "/api/user/register", json={"username": "weak", "password": "short"}
    )
    assert resp.status_code == 400
    assert "Password" in resp.json()["detail"]


def test_expired_api_keys_are_rejected(setup_test_db):
    db_path = setup_test_db

    client = TestClient(app)
    password = "ValidPass!45"
    client.post("/api/user/register", json={"username": "carol", "password": password})
    resp = client.post(
        "/api/user/login", json={"username": "carol", "password": password}
    )
    api_key = resp.json()["api_key"]

    conn = sqlite3.connect(users.DB_PATH)
    expired = users._current_timestamp() - 10
    conn.execute("UPDATE api_keys SET expires_at=? WHERE 1=1", (expired,))
    conn.commit()
    conn.close()

    assert users.get_user_by_api_key(api_key) is None
