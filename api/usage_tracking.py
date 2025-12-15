"""Usage tracking for billing and analytics."""

import json
import sqlite3
from typing import Optional

from api.corpus_db import _current_timestamp, _get_conn
from logging_config import get_logger

logger = get_logger(__name__)


def log_corpus_usage(
    user_id: int,
    corpus_id: int,
    action: str,
    query_count: int = 1,
    metadata: Optional[dict] = None
) -> None:
    """Log corpus usage for billing and analytics.

    Args:
        user_id: User ID
        corpus_id: Corpus ID
        action: Action type ("query", "upload", "update")
        query_count: Number of queries (default 1)
        metadata: Additional metadata as dict (will be stored as JSON)

    Note:
        This function is designed to never fail - errors are logged but not raised
        to avoid disrupting the main application flow.
    """
    conn = _get_conn()

    try:
        conn.execute(
            """
            INSERT INTO usage_logs (
                user_id, corpus_id, action, query_count, timestamp, metadata
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                corpus_id,
                action,
                query_count,
                _current_timestamp(),
                json.dumps(metadata) if metadata else None,
            ),
        )
        conn.commit()
        logger.debug(
            f"Logged usage: user={user_id}, corpus={corpus_id}, action={action}, count={query_count}"
        )
    except Exception as e:
        logger.error(f"Failed to log usage: {e}")
        # Don't raise - usage logging should never block main operations
    finally:
        conn.close()


def get_user_usage_stats(user_id: int, corpus_id: Optional[int] = None) -> dict:
    """Get usage statistics for a user.

    Args:
        user_id: User ID
        corpus_id: Optional corpus ID to filter by

    Returns:
        dict: Usage statistics with keys:
            - total_actions: Total number of logged actions
            - total_queries: Total number of queries
            - last_access: Timestamp of last access (or None)
    """
    conn = _get_conn()

    try:
        if corpus_id:
            cur = conn.execute(
                """
                SELECT
                    COUNT(*) as total_actions,
                    SUM(query_count) as total_queries,
                    MAX(timestamp) as last_access
                FROM usage_logs
                WHERE user_id = ? AND corpus_id = ?
                """,
                (user_id, corpus_id),
            )
        else:
            cur = conn.execute(
                """
                SELECT
                    COUNT(*) as total_actions,
                    SUM(query_count) as total_queries,
                    MAX(timestamp) as last_access
                FROM usage_logs
                WHERE user_id = ?
                """,
                (user_id,),
            )

        row = cur.fetchone()
        return {
            "total_actions": row[0] or 0,
            "total_queries": row[1] or 0,
            "last_access": row[2],
        }
    except Exception as e:
        logger.error(f"Failed to get user usage stats: {e}")
        return {
            "total_actions": 0,
            "total_queries": 0,
            "last_access": None,
        }
    finally:
        conn.close()


def get_corpus_usage_stats(corpus_id: int) -> dict:
    """Get usage statistics for a corpus.

    Args:
        corpus_id: Corpus ID

    Returns:
        dict: Usage statistics with keys:
            - unique_users: Number of unique users who accessed the corpus
            - total_actions: Total number of logged actions
            - total_queries: Total number of queries
            - last_access: Timestamp of last access (or None)
    """
    conn = _get_conn()

    try:
        cur = conn.execute(
            """
            SELECT
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(*) as total_actions,
                SUM(query_count) as total_queries,
                MAX(timestamp) as last_access
            FROM usage_logs
            WHERE corpus_id = ?
            """,
            (corpus_id,),
        )

        row = cur.fetchone()
        return {
            "unique_users": row[0] or 0,
            "total_actions": row[1] or 0,
            "total_queries": row[2] or 0,
            "last_access": row[3],
        }
    except Exception as e:
        logger.error(f"Failed to get corpus usage stats: {e}")
        return {
            "unique_users": 0,
            "total_actions": 0,
            "total_queries": 0,
            "last_access": None,
        }
    finally:
        conn.close()


def get_recent_usage_logs(
    user_id: Optional[int] = None,
    corpus_id: Optional[int] = None,
    limit: int = 100
) -> list[dict]:
    """Get recent usage logs with optional filtering.

    Args:
        user_id: Optional user ID to filter by
        corpus_id: Optional corpus ID to filter by
        limit: Maximum number of records to return (default 100)

    Returns:
        list[dict]: List of usage log entries
    """
    conn = _get_conn()

    try:
        query = """
            SELECT
                ul.id, ul.user_id, ul.corpus_id, ul.action,
                ul.query_count, ul.timestamp, ul.metadata,
                u.username, c.name as corpus_name
            FROM usage_logs ul
            JOIN users u ON ul.user_id = u.id
            JOIN corpuses c ON ul.corpus_id = c.id
            WHERE 1=1
        """
        params = []

        if user_id:
            query += " AND ul.user_id = ?"
            params.append(user_id)

        if corpus_id:
            query += " AND ul.corpus_id = ?"
            params.append(corpus_id)

        query += " ORDER BY ul.timestamp DESC LIMIT ?"
        params.append(limit)

        cur = conn.execute(query, params)

        logs = []
        for row in cur.fetchall():
            logs.append({
                "id": row[0],
                "user_id": row[1],
                "corpus_id": row[2],
                "action": row[3],
                "query_count": row[4],
                "timestamp": row[5],
                "metadata": json.loads(row[6]) if row[6] else None,
                "username": row[7],
                "corpus_name": row[8],
            })

        return logs
    except Exception as e:
        logger.error(f"Failed to get recent usage logs: {e}")
        return []
    finally:
        conn.close()
