"""User management and API key generation utilities."""

import hashlib
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from passlib.context import CryptContext
from pydantic import BaseModel

from config import (
    API_KEY_TTL_DAYS,
    AUTH_RATE_LIMIT,
    PASSWORD_MIN_LENGTH,
    REQUIRE_COMPLEX_PASSWORD,
    USER_DB_PATH,
    VECTOR_DB_PATH,
)

from .rate_limiting import limiter
from .validation import validate_username

# Database location for user accounts and API keys
DB_PATH = USER_DB_PATH
API_KEY_TTL_SECONDS = API_KEY_TTL_DAYS * 24 * 60 * 60

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    # Note: bcrypt 4.x+ raises errors for passwords > 72 bytes
    # We handle truncation manually in _hash_password() and _verify_password()
)


def _get_conn():
    return sqlite3.connect(DB_PATH)


def _current_timestamp() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _ensure_api_key_schema(conn: sqlite3.Connection) -> None:
    """Add missing columns for API key metadata."""
    cur = conn.execute("PRAGMA table_info(api_keys)")
    columns = {row[1] for row in cur.fetchall()}
    if "created_at" not in columns:
        conn.execute("ALTER TABLE api_keys ADD COLUMN created_at INTEGER")
    if "expires_at" not in columns:
        conn.execute("ALTER TABLE api_keys ADD COLUMN expires_at INTEGER")
    conn.execute(
        "UPDATE api_keys SET created_at = COALESCE(created_at, strftime('%s','now'))"
    )
    conn.execute(
        "UPDATE api_keys SET expires_at = COALESCE(expires_at, created_at + ?)",
        (API_KEY_TTL_SECONDS,),
    )


def _purge_expired_api_keys(conn: sqlite3.Connection) -> None:
    conn.execute(
        "DELETE FROM api_keys WHERE expires_at IS NOT NULL AND expires_at < ?",
        (_current_timestamp(),),
    )


def _ensure_cognito_schema(conn: sqlite3.Connection) -> None:
    """Add cognito_sub and email columns if they don't exist."""
    cur = conn.execute("PRAGMA table_info(users)")
    columns = {row[1] for row in cur.fetchall()}
    if "cognito_sub" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN cognito_sub TEXT")
    if "email" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
    # Create unique index for cognito_sub (SQLite allows this on existing columns)
    try:
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_cognito_sub ON users(cognito_sub) WHERE cognito_sub IS NOT NULL")
    except sqlite3.OperationalError:
        # Index might already exist from init_db
        pass


def init_db():
    """Create tables for users and API keys if they don't already exist."""
    # Ensure the database directory exists
    db_dir = Path(DB_PATH).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            cognito_sub TEXT,
            email TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_hash TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            created_at INTEGER,
            expires_at INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    _ensure_api_key_schema(conn)
    _ensure_cognito_schema(conn)
    _purge_expired_api_keys(conn)

    # Create indexes for better query performance
    cur.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_expires_at ON api_keys(expires_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_cognito_sub ON users(cognito_sub)")

    conn.commit()
    conn.close()


# Ensure DB exists on import
init_db()

router = APIRouter()


class UserCredentials(BaseModel):
    username: str
    password: str


def _truncate_password(password: str, max_bytes: int = 72) -> str:
    """Truncate password to max_bytes while preserving UTF-8 validity."""
    encoded = password.encode('utf-8')
    if len(encoded) <= max_bytes:
        return password
    # Truncate and decode, ignoring incomplete multi-byte sequences at the end
    truncated = encoded[:max_bytes].decode('utf-8', errors='ignore')
    return truncated


def _hash_password(password: str) -> str:
    """Hash password with bcrypt, truncating to 72 bytes if necessary."""
    password = _truncate_password(password, 72)
    return pwd_context.hash(password)


def _verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash, truncating to 72 bytes if necessary."""
    password = _truncate_password(password, 72)
    try:
        return pwd_context.verify(password, password_hash)
    except ValueError as e:
        # Handle bcrypt errors gracefully
        if 'password cannot be longer than 72 bytes' in str(e):
            return False
        raise


def _hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def _validate_password_strength(password: str) -> None:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {PASSWORD_MIN_LENGTH} characters long",
        )

    # Bcrypt has a 72 byte limit - warn users if their password will be truncated
    password_bytes = len(password.encode('utf-8'))
    if password_bytes > 72:
        raise HTTPException(
            status_code=400,
            detail=f"Password too long ({password_bytes} bytes). Maximum is 72 bytes due to bcrypt limits.",
        )

    if REQUIRE_COMPLEX_PASSWORD:
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_symbol = any(not c.isalnum() for c in password)
        if not (has_lower and has_upper and has_digit and has_symbol):
            raise HTTPException(
                status_code=400,
                detail="Password must include upper and lower case letters, a digit, and a special character",
            )


def _create_api_key(conn: sqlite3.Connection, user_id: int) -> str:
    api_key = secrets.token_hex(16)
    timestamp = _current_timestamp()
    expires_at = timestamp + API_KEY_TTL_SECONDS
    conn.execute(
        "INSERT INTO api_keys (key_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (_hash_api_key(api_key), user_id, timestamp, expires_at),
    )
    conn.commit()
    return api_key


def register_user(username: str, password: str) -> str:
    """Register a new user and return an API key."""
    # SECURITY: Validate username BEFORE any database operations
    username = validate_username(username)
    _validate_password_strength(password)
    conn = _get_conn()
    user_id = None
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, _hash_password(password)),
        )
        user_id = cursor.lastrowid
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")

    # Create API key for the new user
    api_key = _create_api_key(conn, user_id)
    conn.close()

    # Create vector DB directory for the user with safe path construction
    from vector_store.vector_index import get_user_db_path
    user_path = Path(get_user_db_path(username))
    user_path.mkdir(parents=True, exist_ok=True)

    return api_key


def login_user(username: str, password: str) -> str:
    """Validate user credentials and return a new API key."""
    # SECURITY: Validate username format (but don't raise 422 for non-existent users)
    # This prevents timing attacks and information leakage
    try:
        username = validate_username(username)
    except HTTPException:
        # Invalid format - return generic error
        raise HTTPException(status_code=401, detail="Invalid credentials")

    conn = _get_conn()
    cur = conn.execute(
        "SELECT id, password_hash FROM users WHERE username=?", (username,)
    )
    row = cur.fetchone()
    if not row or not _verify_password(password, row[1]):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user_id = row[0]
    api_key = _create_api_key(conn, user_id)
    conn.close()
    return api_key


def create_api_key_for_user(username: str, password: str) -> str:
    """Generate a new API key for a user after verifying credentials."""
    # SECURITY: Validate username
    try:
        username = validate_username(username)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    conn = _get_conn()
    cur = conn.execute(
        "SELECT id, password_hash FROM users WHERE username=?", (username,)
    )
    row = cur.fetchone()
    if not row or not _verify_password(password, row[1]):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user_id = row[0]
    api_key = _create_api_key(conn, user_id)
    conn.close()
    return api_key


@router.post("/register")
@limiter.limit(AUTH_RATE_LIMIT)
def register(request: Request, user: UserCredentials):
    """Register a new user and create a vector DB directory for them."""
    api_key = register_user(user.username, user.password)
    return {"message": "User registered", "api_key": api_key}


@router.post("/login")
@limiter.limit(AUTH_RATE_LIMIT)
def login(request: Request, user: UserCredentials):
    """Validate user credentials and return a new API key."""
    api_key = login_user(user.username, user.password)
    return {"api_key": api_key}


@router.post("/create-api-key")
@limiter.limit(AUTH_RATE_LIMIT)
def create_api_key(request: Request, user: UserCredentials):
    """Generate a new API key for a user after verifying credentials."""
    api_key = create_api_key_for_user(user.username, user.password)
    return {"api_key": api_key}


def get_user_by_api_key(api_key: Optional[str]) -> Optional[dict]:
    """Return user details for a given API key or ``None`` if not found."""
    if not api_key:
        return None
    conn = _get_conn()
    cur = conn.execute(
        """
        SELECT api_keys.id, api_keys.expires_at, users.id, users.username
        FROM api_keys
        JOIN users ON api_keys.user_id = users.id
        WHERE api_keys.key_hash = ?
        """,
        (_hash_api_key(api_key),),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    api_key_id, expires_at, user_id, username = row
    if expires_at is not None and expires_at < _current_timestamp():
        conn.execute("DELETE FROM api_keys WHERE id = ?", (api_key_id,))
        conn.commit()
        conn.close()
        return None
    conn.close()
    # Use safe path construction
    from vector_store.vector_index import get_user_db_path
    user_path = Path(get_user_db_path(username))
    user_path.mkdir(parents=True, exist_ok=True)
    return {"id": user_id, "username": username, "db_path": str(user_path)}


def get_or_create_cognito_user(cognito_sub: str, username: str, email: str = "") -> dict:
    """
    Get or create a user from Cognito authentication.

    If a user with the cognito_sub exists, return their details (and update email if changed).
    Otherwise, create a new user linked to the Cognito account.

    Args:
        cognito_sub: The unique Cognito user identifier (sub claim)
        username: The Cognito username
        email: Optional email from Cognito

    Returns:
        dict with user_id, username, and db_path
    """
    from vector_store.vector_index import get_user_db_path

    conn = _get_conn()

    # First, try to find existing user by cognito_sub
    cur = conn.execute(
        "SELECT id, username, email FROM users WHERE cognito_sub = ?",
        (cognito_sub,),
    )
    row = cur.fetchone()

    if row:
        user_id, db_username, stored_email = row
        # Update email if it has changed (Cognito is source of truth)
        if email and email != stored_email:
            conn.execute(
                "UPDATE users SET email = ? WHERE id = ?",
                (email, user_id),
            )
            conn.commit()
        conn.close()
        user_path = Path(get_user_db_path(db_username))
        user_path.mkdir(parents=True, exist_ok=True)
        return {"id": user_id, "username": db_username, "db_path": str(user_path)}

    # User doesn't exist, create them
    # Generate a random password hash since Cognito handles authentication
    random_password = secrets.token_hex(32)
    password_hash = _hash_password(random_password)

    # Ensure username is unique by appending cognito_sub suffix if needed
    base_username = username
    unique_username = base_username
    suffix = 1

    while True:
        try:
            cursor = conn.execute(
                """
                INSERT INTO users (username, password_hash, cognito_sub, email)
                VALUES (?, ?, ?, ?)
                """,
                (unique_username, password_hash, cognito_sub, email),
            )
            user_id = cursor.lastrowid
            conn.commit()
            break
        except sqlite3.IntegrityError as e:
            if "username" in str(e).lower():
                # Username exists, try with suffix
                unique_username = f"{base_username}_{suffix}"
                suffix += 1
                if suffix > 100:  # Safety limit
                    conn.close()
                    raise HTTPException(
                        status_code=500,
                        detail="Could not create unique username for Cognito user"
                    )
            else:
                conn.close()
                raise

    conn.close()

    # Create vector DB directory for the user
    user_path = Path(get_user_db_path(unique_username))
    user_path.mkdir(parents=True, exist_ok=True)

    return {"id": user_id, "username": unique_username, "db_path": str(user_path)}
