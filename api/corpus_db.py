"""Corpus database management and operations."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from config import USER_DB_PATH

# Share database with users
DB_PATH = USER_DB_PATH


def _get_conn():
    """Get database connection."""
    return sqlite3.connect(DB_PATH)


def _current_timestamp() -> int:
    """Get current UTC timestamp."""
    return int(datetime.now(timezone.utc).timestamp())


def init_corpus_tables():
    """Create corpus-related tables if they don't exist."""
    # Ensure the database directory exists
    db_dir = Path(DB_PATH).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    conn = _get_conn()
    cur = conn.cursor()

    # Create corpuses table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS corpuses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            is_public BOOLEAN NOT NULL DEFAULT 0,
            is_approved BOOLEAN NOT NULL DEFAULT 0,
            owner_id INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            FOREIGN KEY(owner_id) REFERENCES users(id)
        )
        """
    )

    # Create corpus_permissions table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS corpus_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            corpus_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            permission_type TEXT NOT NULL,
            granted_by INTEGER NOT NULL,
            granted_at INTEGER NOT NULL,
            FOREIGN KEY(corpus_id) REFERENCES corpuses(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(granted_by) REFERENCES users(id),
            UNIQUE(corpus_id, user_id)
        )
        """
    )

    # Create subscriptions table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            corpus_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            tier TEXT,
            started_at INTEGER NOT NULL,
            expires_at INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(corpus_id) REFERENCES corpuses(id) ON DELETE CASCADE,
            UNIQUE(user_id, corpus_id)
        )
        """
    )

    # Create usage_logs table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            corpus_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            query_count INTEGER DEFAULT 0,
            timestamp INTEGER NOT NULL,
            metadata TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(corpus_id) REFERENCES corpuses(id) ON DELETE CASCADE
        )
        """
    )

    # Create corpus_versions table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS corpus_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            corpus_id INTEGER NOT NULL,
            version INTEGER NOT NULL,
            description TEXT,
            created_by INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            chunk_count INTEGER DEFAULT 0,
            file_count INTEGER DEFAULT 0,
            FOREIGN KEY(corpus_id) REFERENCES corpuses(id) ON DELETE CASCADE,
            FOREIGN KEY(created_by) REFERENCES users(id),
            UNIQUE(corpus_id, version)
        )
        """
    )

    # Create indexes for better query performance
    cur.execute("CREATE INDEX IF NOT EXISTS idx_corpuses_owner_id ON corpuses(owner_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_corpuses_category ON corpuses(category)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_corpuses_is_approved ON corpuses(is_approved)")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_corpus_permissions_corpus_id ON corpus_permissions(corpus_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_corpus_permissions_user_id ON corpus_permissions(user_id)")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_corpus_id ON subscriptions(corpus_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status)")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON usage_logs(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_usage_logs_corpus_id ON usage_logs(corpus_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_usage_logs_timestamp ON usage_logs(timestamp)")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_corpus_versions_corpus_id ON corpus_versions(corpus_id)")

    conn.commit()
    conn.close()


# Initialize tables on import
init_corpus_tables()
