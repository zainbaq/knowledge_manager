"""Admin endpoints for corpus approval and usage monitoring."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.admin_auth import get_admin_user
from api.corpus_db import _current_timestamp, _get_conn
from api.models.corpus_responses import CorpusMetadata
from api.rate_limiting import limiter
from api.usage_tracking import get_corpus_usage_stats, get_user_usage_stats
from config import MANAGEMENT_RATE_LIMIT
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/corpuses/pending", response_model=List[CorpusMetadata])
@limiter.limit(MANAGEMENT_RATE_LIMIT)
async def list_pending_corpuses(
    request: Request,
    admin_user: dict = Depends(get_admin_user),
):
    """List all corpuses awaiting approval.

    Only returns public corpuses that are not yet approved. Admins can use this
    to review and approve corpuses for public access.

    Args:
        admin_user: Authenticated admin user

    Returns:
        List[CorpusMetadata]: List of pending corpuses

    Raises:
        HTTPException: 403 if user is not admin
    """
    conn = _get_conn()

    try:
        cur = conn.execute(
            """
            SELECT
                c.id, c.name, c.display_name, c.description, c.category,
                c.version, c.is_public, c.is_approved, c.created_at, c.updated_at,
                u.username
            FROM corpuses c
            JOIN users u ON c.owner_id = u.id
            WHERE c.is_public = 1 AND c.is_approved = 0
            ORDER BY c.created_at ASC
            """
        )

        pending_corpuses = []
        for row in cur.fetchall():
            # Get chunk and file count (not stored in corpuses table)
            # For now, default to 0 - could query ChromaDB if needed
            pending_corpuses.append(
                CorpusMetadata(
                    id=row[0],
                    name=row[1],
                    display_name=row[2],
                    description=row[3],
                    category=row[4],
                    version=row[5],
                    is_public=bool(row[6]),
                    is_approved=bool(row[7]),
                    created_at=row[8],
                    updated_at=row[9],
                    owner_username=row[10],
                    chunk_count=0,  # Could fetch from ChromaDB if needed
                    file_count=0,   # Could fetch from ChromaDB if needed
                )
            )

        logger.info(
            f"Admin {admin_user['username']} listed {len(pending_corpuses)} pending corpuses"
        )

        return pending_corpuses

    except Exception as e:
        logger.error(f"Error listing pending corpuses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing pending corpuses: {str(e)}",
        )
    finally:
        conn.close()


@router.post("/corpuses/{corpus_id}/approve")
@limiter.limit(MANAGEMENT_RATE_LIMIT)
async def approve_corpus(
    request: Request,
    corpus_id: int,
    admin_user: dict = Depends(get_admin_user),
):
    """Approve a corpus for public access.

    Sets is_approved=True, making the corpus accessible to users based on
    its permission settings.

    Args:
        corpus_id: Corpus ID to approve
        admin_user: Authenticated admin user

    Returns:
        dict: Success message with corpus details

    Raises:
        HTTPException: 403 if user is not admin
        HTTPException: 404 if corpus not found
    """
    conn = _get_conn()

    try:
        # Check if corpus exists
        cur = conn.execute(
            "SELECT name, is_approved FROM corpuses WHERE id = ?",
            (corpus_id,)
        )
        row = cur.fetchone()

        if not row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Corpus {corpus_id} not found"
            )

        corpus_name, is_approved = row

        if is_approved:
            conn.close()
            return {
                "message": f"Corpus '{corpus_name}' (ID: {corpus_id}) is already approved",
                "corpus_id": corpus_id,
                "corpus_name": corpus_name,
            }

        # Approve the corpus
        conn.execute(
            "UPDATE corpuses SET is_approved = 1, updated_at = ? WHERE id = ?",
            (_current_timestamp(), corpus_id)
        )
        conn.commit()

        logger.info(
            f"Admin {admin_user['username']} approved corpus {corpus_id} ('{corpus_name}')"
        )

        return {
            "message": f"Corpus '{corpus_name}' (ID: {corpus_id}) approved successfully",
            "corpus_id": corpus_id,
            "corpus_name": corpus_name,
        }

    except HTTPException:
        conn.close()
        raise
    except Exception as e:
        conn.close()
        logger.error(f"Error approving corpus {corpus_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error approving corpus: {str(e)}",
        )
    finally:
        conn.close()


@router.post("/corpuses/{corpus_id}/reject")
@limiter.limit(MANAGEMENT_RATE_LIMIT)
async def reject_corpus(
    request: Request,
    corpus_id: int,
    admin_user: dict = Depends(get_admin_user),
):
    """Reject/unapprove a corpus.

    Sets is_approved=False, preventing public access to the corpus.

    Args:
        corpus_id: Corpus ID to reject
        admin_user: Authenticated admin user

    Returns:
        dict: Success message with corpus details

    Raises:
        HTTPException: 403 if user is not admin
        HTTPException: 404 if corpus not found
    """
    conn = _get_conn()

    try:
        # Check if corpus exists
        cur = conn.execute(
            "SELECT name, is_approved FROM corpuses WHERE id = ?",
            (corpus_id,)
        )
        row = cur.fetchone()

        if not row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Corpus {corpus_id} not found"
            )

        corpus_name, is_approved = row

        if not is_approved:
            conn.close()
            return {
                "message": f"Corpus '{corpus_name}' (ID: {corpus_id}) is already unapproved",
                "corpus_id": corpus_id,
                "corpus_name": corpus_name,
            }

        # Reject the corpus
        conn.execute(
            "UPDATE corpuses SET is_approved = 0, updated_at = ? WHERE id = ?",
            (_current_timestamp(), corpus_id)
        )
        conn.commit()

        logger.info(
            f"Admin {admin_user['username']} rejected corpus {corpus_id} ('{corpus_name}')"
        )

        return {
            "message": f"Corpus '{corpus_name}' (ID: {corpus_id}) rejected successfully",
            "corpus_id": corpus_id,
            "corpus_name": corpus_name,
        }

    except HTTPException:
        conn.close()
        raise
    except Exception as e:
        conn.close()
        logger.error(f"Error rejecting corpus {corpus_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rejecting corpus: {str(e)}",
        )
    finally:
        conn.close()


@router.get("/usage/corpus/{corpus_id}")
@limiter.limit(MANAGEMENT_RATE_LIMIT)
async def get_corpus_usage(
    request: Request,
    corpus_id: int,
    admin_user: dict = Depends(get_admin_user),
):
    """Get usage statistics for a corpus.

    Returns aggregated usage data including unique users, total actions,
    total queries, and last access time.

    Args:
        corpus_id: Corpus ID
        admin_user: Authenticated admin user

    Returns:
        dict: Usage statistics with keys:
            - corpus_id: Corpus ID
            - unique_users: Number of unique users
            - total_actions: Total number of actions
            - total_queries: Total number of queries
            - last_access: Timestamp of last access (or None)

    Raises:
        HTTPException: 403 if user is not admin
        HTTPException: 404 if corpus not found
    """
    conn = _get_conn()

    try:
        # Verify corpus exists
        cur = conn.execute("SELECT name FROM corpuses WHERE id = ?", (corpus_id,))
        row = cur.fetchone()

        if not row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Corpus {corpus_id} not found"
            )

        corpus_name = row[0]
        conn.close()

        # Get usage stats from usage_tracking module
        stats = get_corpus_usage_stats(corpus_id)

        logger.debug(
            f"Admin {admin_user['username']} retrieved usage stats for corpus {corpus_id}"
        )

        return {
            "corpus_id": corpus_id,
            "corpus_name": corpus_name,
            **stats,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting corpus usage stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting usage stats: {str(e)}",
        )


@router.get("/usage/user/{user_id}")
@limiter.limit(MANAGEMENT_RATE_LIMIT)
async def get_user_usage(
    request: Request,
    user_id: int,
    admin_user: dict = Depends(get_admin_user),
):
    """Get usage statistics for a user across all corpuses.

    Returns aggregated usage data for the specified user.

    Args:
        user_id: User ID
        admin_user: Authenticated admin user

    Returns:
        dict: Usage statistics with keys:
            - user_id: User ID
            - username: Username
            - total_actions: Total number of actions
            - total_queries: Total number of queries
            - last_access: Timestamp of last access (or None)

    Raises:
        HTTPException: 403 if user is not admin
        HTTPException: 404 if user not found
    """
    conn = _get_conn()

    try:
        # Verify user exists
        cur = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()

        if not row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        username = row[0]
        conn.close()

        # Get usage stats from usage_tracking module
        stats = get_user_usage_stats(user_id)

        logger.debug(
            f"Admin {admin_user['username']} retrieved usage stats for user {user_id}"
        )

        return {
            "user_id": user_id,
            "username": username,
            **stats,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user usage stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting usage stats: {str(e)}",
        )
