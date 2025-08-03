"""User management and API key generation utilities."""

import sqlite3
import hashlib
import secrets
from pathlib import Path

from passlib.context import CryptContext
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import BASE_DIR, VECTOR_DB_PATH

# Database location for user accounts and API keys
DB_PATH = Path(BASE_DIR) / "users.db"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create tables for users and API keys if they don't already exist."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_hash TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    conn.commit()
    conn.close()


# Ensure DB exists on import
init_db()

router = APIRouter()


class UserCredentials(BaseModel):
    username: str
    password: str


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def _hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


@router.post("/register")
def register(user: UserCredentials):
    """Register a new user and create a vector DB directory for them."""
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (user.username, _hash_password(user.password)),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")
    conn.close()

    # Ensure user-specific vector DB directory exists
    user_path = Path(VECTOR_DB_PATH) / user.username
    user_path.mkdir(parents=True, exist_ok=True)

    return {"message": "User registered"}


@router.post("/login")
def login(user: UserCredentials):
    """Validate user credentials and return a new API key."""
    conn = _get_conn()
    cur = conn.execute(
        "SELECT id, password_hash FROM users WHERE username=?", (user.username,)
    )
    row = cur.fetchone()
    if not row or not _verify_password(user.password, row[1]):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user_id = row[0]
    api_key = secrets.token_hex(16)
    conn.execute(
        "INSERT INTO api_keys (key_hash, user_id) VALUES (?, ?)",
        (_hash_api_key(api_key), user_id),
    )
    conn.commit()
    conn.close()
    return {"api_key": api_key}


@router.post("/create-api-key")
def create_api_key(user: UserCredentials):
    """Generate a new API key for a user after verifying credentials."""
    conn = _get_conn()
    cur = conn.execute(
        "SELECT id, password_hash FROM users WHERE username=?", (user.username,)
    )
    row = cur.fetchone()
    if not row or not _verify_password(user.password, row[1]):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user_id = row[0]
    api_key = secrets.token_hex(16)
    conn.execute(
        "INSERT INTO api_keys (key_hash, user_id) VALUES (?, ?)",
        (_hash_api_key(api_key), user_id),
    )
    conn.commit()
    conn.close()
    return {"api_key": api_key}


def get_user_by_api_key(api_key: str) -> dict | None:
    """Return user details for a given API key or ``None`` if not found."""
    conn = _get_conn()
    cur = conn.execute(
        """
        SELECT users.id, users.username
        FROM api_keys
        JOIN users ON api_keys.user_id = users.id
        WHERE api_keys.key_hash = ?
        """,
        (_hash_api_key(api_key),),
    )
    row = cur.fetchone()
    conn.close()
    if row:
        user_id, username = row
        user_path = Path(VECTOR_DB_PATH) / username
        user_path.mkdir(parents=True, exist_ok=True)
        return {"id": user_id, "username": username, "db_path": str(user_path)}
    return None
