"""Corpus permission checking and authorization utilities."""

import sqlite3
from typing import Optional

from fastapi import HTTPException, status

from api.corpus_db import _get_conn


def check_corpus_permission(
    corpus_id: int,
    user_id: int,
    required_permission: str = "read"
) -> bool:
    """Check if user has required permission for corpus.

    Permission hierarchy: owner > admin > write > read

    Args:
        corpus_id: Corpus ID
        user_id: User ID
        required_permission: Required permission level ("read", "write", "admin", "owner")

    Returns:
        bool: True if user has permission

    Raises:
        HTTPException: 404 if corpus not found
        HTTPException: 403 if permission denied
    """
    conn = _get_conn()

    # Check if corpus exists and get its metadata
    cur = conn.execute(
        "SELECT owner_id, is_public, is_approved FROM corpuses WHERE id = ?",
        (corpus_id,)
    )
    row = cur.fetchone()

    if not row:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Corpus {corpus_id} not found"
        )

    owner_id, is_public, is_approved = row

    # Owner has all permissions
    if owner_id == user_id:
        conn.close()
        return True

    # Check if corpus requires approval
    if not is_approved and required_permission != "owner":
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Corpus not yet approved by admin"
        )

    # Public approved corpuses allow read access to all
    if is_public and is_approved and required_permission == "read":
        conn.close()
        return True

    # Check explicit permissions in corpus_permissions table
    cur = conn.execute(
        """
        SELECT permission_type FROM corpus_permissions
        WHERE corpus_id = ? AND user_id = ?
        """,
        (corpus_id, user_id)
    )
    perm_row = cur.fetchone()
    conn.close()

    if not perm_row:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No access to corpus {corpus_id}"
        )

    user_perm = perm_row[0]

    # Permission hierarchy check
    hierarchy = {"read": 1, "write": 2, "admin": 3, "owner": 4}
    user_level = hierarchy.get(user_perm, 0)
    required_level = hierarchy.get(required_permission, 0)

    if user_level >= required_level:
        return True

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Insufficient permission for corpus {corpus_id}. "
               f"Required: {required_permission}, has: {user_perm}"
    )


def get_user_corpus_permission(corpus_id: int, user_id: int) -> Optional[str]:
    """Get user's permission level for a corpus.

    Args:
        corpus_id: Corpus ID
        user_id: User ID

    Returns:
        str: Permission level ("owner", "admin", "write", "read") or None if no access
    """
    conn = _get_conn()

    # Check if user is owner
    cur = conn.execute(
        "SELECT owner_id FROM corpuses WHERE id = ?",
        (corpus_id,)
    )
    row = cur.fetchone()

    if row and row[0] == user_id:
        conn.close()
        return "owner"

    # Check explicit permission
    cur = conn.execute(
        "SELECT permission_type FROM corpus_permissions WHERE corpus_id = ? AND user_id = ?",
        (corpus_id, user_id)
    )
    perm_row = cur.fetchone()
    conn.close()

    return perm_row[0] if perm_row else None


def check_user_owns_corpus(corpus_id: int, user_id: int) -> bool:
    """Check if user is the owner of a corpus.

    Args:
        corpus_id: Corpus ID
        user_id: User ID

    Returns:
        bool: True if user owns the corpus

    Raises:
        HTTPException: 404 if corpus not found
        HTTPException: 403 if user is not owner
    """
    conn = _get_conn()

    cur = conn.execute(
        "SELECT owner_id FROM corpuses WHERE id = ?",
        (corpus_id,)
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Corpus {corpus_id} not found"
        )

    if row[0] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the corpus owner can perform this action"
        )

    return True
