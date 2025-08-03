"""Tests for user registration and API key generation."""

import sqlite3
from fastapi.testclient import TestClient

from api.app import app
from api import users


def test_login_returns_new_api_key(tmp_path):
    users.DB_PATH = tmp_path / "users.db"
    users.VECTOR_DB_PATH = tmp_path / "vectors"
    users.init_db()

    client = TestClient(app)

    # Register user
    resp = client.post(
        "/user/register", json={"username": "alice", "password": "secret"}
    )
    assert resp.status_code == 200

    # Login should return a new key
    resp = client.post(
        "/user/login", json={"username": "alice", "password": "secret"}
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


def test_create_api_key_generates_unique_keys(tmp_path):
    users.DB_PATH = tmp_path / "users.db"
    users.VECTOR_DB_PATH = tmp_path / "vectors"
    users.init_db()

    client = TestClient(app)
    client.post("/user/register", json={"username": "bob", "password": "pass"})

    resp1 = client.post(
        "/user/create-api-key", json={"username": "bob", "password": "pass"}
    )
    resp2 = client.post(
        "/user/create-api-key", json={"username": "bob", "password": "pass"}
    )

    key1 = resp1.json()["api_key"]
    key2 = resp2.json()["api_key"]
    assert key1 != key2

    conn = sqlite3.connect(users.DB_PATH)
    cur = conn.execute("SELECT COUNT(*) FROM api_keys")
    count = cur.fetchone()[0]
    conn.close()
    assert count == 2

