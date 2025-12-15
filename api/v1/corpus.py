"""Corpus management endpoints for API v1."""

import sqlite3
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.auth import get_current_user
from api.corpus_auth import check_corpus_permission, get_user_corpus_permission
from api.corpus_db import _current_timestamp, _get_conn
from api.models.corpus_requests import (
    CorpusQueryRequest,
    CreateCorpusRequest,
    CreateSubscriptionRequest,
    CreateVersionRequest,
    GrantPermissionRequest,
    UpdateCorpusRequest,
)
from api.models.corpus_responses import (
    CorpusDetailResponse,
    CorpusMetadata,
    CorpusPermission,
    CorpusVersionInfo,
    CreateCorpusResponse,
    ListCorpusesResponse,
    PermissionGrantedResponse,
    SubscriptionInfo,
    SubscriptionResponse,
)
from api.models.responses import QueryResponse
from api.usage_tracking import log_corpus_usage
from api.rate_limiting import limiter
from api.validation import validate_collection_name, validate_username
from config import MANAGEMENT_RATE_LIMIT, QUERY_RATE_LIMIT
from logging_config import get_logger
from vector_store.vector_index import (
    compile_context,
    get_corpus_db_path,
    get_or_create_collection,
    query_index,
)

logger = get_logger(__name__)

router = APIRouter()


@router.post("/", response_model=CreateCorpusResponse)
@limiter.limit(MANAGEMENT_RATE_LIMIT)
async def create_corpus(
    request: Request,
    corpus_request: CreateCorpusRequest,
    current_user: dict = Depends(get_current_user),
) -> CreateCorpusResponse:
    """Create a new corpus.

    Only authenticated users can create corpuses.
    New corpuses require admin approval before being publicly accessible.
    """
    # Validate corpus name using same validation as collection names
    corpus_name = validate_collection_name(corpus_request.name)

    conn = _get_conn()
    timestamp = _current_timestamp()

    try:
        # Insert corpus
        cur = conn.execute(
            """
            INSERT INTO corpuses (
                name, display_name, description, category,
                version, is_public, is_approved, owner_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                corpus_name,
                corpus_request.display_name,
                corpus_request.description,
                corpus_request.category,
                1,  # Initial version
                corpus_request.is_public,
                False,  # Requires admin approval
                current_user["id"],
                timestamp,
                timestamp,
            ),
        )
        corpus_id = cur.lastrowid

        # Grant owner permission
        conn.execute(
            """
            INSERT INTO corpus_permissions (
                corpus_id, user_id, permission_type, granted_by, granted_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (corpus_id, current_user["id"], "owner", current_user["id"], timestamp),
        )

        # Create initial version record
        conn.execute(
            """
            INSERT INTO corpus_versions (
                corpus_id, version, description, created_by, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (corpus_id, 1, "Initial version", current_user["id"], timestamp),
        )

        conn.commit()

        # Create corpus directory
        corpus_path = get_corpus_db_path(corpus_id)
        Path(corpus_path).mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Created corpus {corpus_id} ({corpus_name}) by user {current_user['username']}"
        )

        approval_msg = (
            "Awaiting admin approval."
            if corpus_request.is_public
            else "Corpus created successfully."
        )

        return CreateCorpusResponse(
            message=f"Corpus '{corpus_request.display_name}' created successfully. {approval_msg}",
            corpus_id=corpus_id,
            corpus_name=corpus_name,
        )

    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Corpus name '{corpus_name}' already exists",
        )
    finally:
        conn.close()


@router.get("/", response_model=ListCorpusesResponse)
@limiter.limit(MANAGEMENT_RATE_LIMIT)
async def list_corpuses(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> ListCorpusesResponse:
    """List all corpuses accessible to the current user.

    Includes:
    - Public approved corpuses
    - Corpuses owned by user
    - Corpuses with explicit permissions
    """
    conn = _get_conn()

    # Get all corpuses where user has access
    cur = conn.execute(
        """
        SELECT DISTINCT c.id, c.name, c.display_name, c.description, c.category,
               c.version, c.is_public, c.is_approved, c.owner_id,
               c.created_at, c.updated_at, u.username as owner_username
        FROM corpuses c
        JOIN users u ON c.owner_id = u.id
        LEFT JOIN corpus_permissions cp ON c.id = cp.corpus_id
        WHERE
            c.owner_id = ?  -- User owns it
            OR (c.is_public = 1 AND c.is_approved = 1)  -- Public and approved
            OR cp.user_id = ?  -- Explicit permission
        ORDER BY c.updated_at DESC
        """,
        (current_user["id"], current_user["id"]),
    )

    corpuses = []
    for row in cur.fetchall():
        corpuses.append(
            CorpusMetadata(
                id=row[0],
                name=row[1],
                display_name=row[2],
                description=row[3],
                category=row[4],
                version=row[5],
                is_public=bool(row[6]),
                is_approved=bool(row[7]),
                owner_username=row[11],
                created_at=row[9],
                updated_at=row[10],
            )
        )

    conn.close()

    logger.info(f"Listed {len(corpuses)} corpuses for user {current_user['username']}")

    return ListCorpusesResponse(corpuses=corpuses)


@router.get("/{corpus_id}", response_model=CorpusDetailResponse)
@limiter.limit(MANAGEMENT_RATE_LIMIT)
async def get_corpus(
    request: Request,
    corpus_id: int,
    current_user: dict = Depends(get_current_user),
) -> CorpusDetailResponse:
    """Get detailed information about a corpus."""
    # Check read permission
    check_corpus_permission(corpus_id, current_user["id"], "read")

    conn = _get_conn()

    # Get corpus metadata
    cur = conn.execute(
        """
        SELECT c.id, c.name, c.display_name, c.description, c.category,
               c.version, c.is_public, c.is_approved, c.owner_id,
               c.created_at, c.updated_at, u.username as owner_username
        FROM corpuses c
        JOIN users u ON c.owner_id = u.id
        WHERE c.id = ?
        """,
        (corpus_id,),
    )
    row = cur.fetchone()

    if not row:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Corpus {corpus_id} not found",
        )

    corpus = CorpusMetadata(
        id=row[0],
        name=row[1],
        display_name=row[2],
        description=row[3],
        category=row[4],
        version=row[5],
        is_public=bool(row[6]),
        is_approved=bool(row[7]),
        owner_username=row[11],
        created_at=row[9],
        updated_at=row[10],
    )

    # Get permissions
    cur = conn.execute(
        """
        SELECT u.username, cp.permission_type, cp.granted_at
        FROM corpus_permissions cp
        JOIN users u ON cp.user_id = u.id
        WHERE cp.corpus_id = ?
        ORDER BY cp.granted_at DESC
        """,
        (corpus_id,),
    )
    permissions = [
        CorpusPermission(username=row[0], permission_type=row[1], granted_at=row[2])
        for row in cur.fetchall()
    ]

    # Get versions
    cur = conn.execute(
        """
        SELECT cv.version, cv.description, u.username, cv.created_at,
               cv.chunk_count, cv.file_count
        FROM corpus_versions cv
        JOIN users u ON cv.created_by = u.id
        WHERE cv.corpus_id = ?
        ORDER BY cv.version DESC
        """,
        (corpus_id,),
    )
    versions = [
        CorpusVersionInfo(
            version=row[0],
            description=row[1],
            created_by=row[2],
            created_at=row[3],
            chunk_count=row[4],
            file_count=row[5],
        )
        for row in cur.fetchall()
    ]

    conn.close()

    # Get user's permission level
    user_perm = get_user_corpus_permission(corpus_id, current_user["id"])

    logger.info(f"Retrieved corpus {corpus_id} details for user {current_user['username']}")

    return CorpusDetailResponse(
        corpus=corpus,
        permissions=permissions,
        versions=versions,
        user_permission=user_perm,
    )


@router.patch("/{corpus_id}", response_model=CorpusMetadata)
@limiter.limit(MANAGEMENT_RATE_LIMIT)
async def update_corpus(
    request: Request,
    corpus_id: int,
    update_request: UpdateCorpusRequest,
    current_user: dict = Depends(get_current_user),
) -> CorpusMetadata:
    """Update corpus metadata.

    Requires: owner or admin permission
    """
    # Check admin permission
    check_corpus_permission(corpus_id, current_user["id"], "admin")

    conn = _get_conn()

    # Build update query dynamically
    updates = []
    params = []

    if update_request.display_name is not None:
        updates.append("display_name = ?")
        params.append(update_request.display_name)

    if update_request.description is not None:
        updates.append("description = ?")
        params.append(update_request.description)

    if update_request.category is not None:
        updates.append("category = ?")
        params.append(update_request.category)

    if update_request.is_public is not None:
        updates.append("is_public = ?")
        params.append(update_request.is_public)

    updates.append("updated_at = ?")
    params.append(_current_timestamp())

    params.append(corpus_id)

    if updates:
        conn.execute(
            f"UPDATE corpuses SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        conn.commit()

    # Return updated corpus
    cur = conn.execute(
        """
        SELECT c.id, c.name, c.display_name, c.description, c.category,
               c.version, c.is_public, c.is_approved, c.owner_id,
               c.created_at, c.updated_at, u.username as owner_username
        FROM corpuses c
        JOIN users u ON c.owner_id = u.id
        WHERE c.id = ?
        """,
        (corpus_id,),
    )
    row = cur.fetchone()
    conn.close()

    logger.info(f"Updated corpus {corpus_id} by user {current_user['username']}")

    return CorpusMetadata(
        id=row[0],
        name=row[1],
        display_name=row[2],
        description=row[3],
        category=row[4],
        version=row[5],
        is_public=bool(row[6]),
        is_approved=bool(row[7]),
        owner_username=row[11],
        created_at=row[9],
        updated_at=row[10],
    )


@router.delete("/{corpus_id}")
@limiter.limit(MANAGEMENT_RATE_LIMIT)
async def delete_corpus(
    request: Request,
    corpus_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Delete a corpus.

    Requires: owner permission
    """
    # Check owner permission
    check_corpus_permission(corpus_id, current_user["id"], "owner")

    conn = _get_conn()

    # Delete corpus (cascades to permissions, subscriptions, etc.)
    conn.execute("DELETE FROM corpuses WHERE id = ?", (corpus_id,))
    conn.commit()
    conn.close()

    logger.info(f"Deleted corpus {corpus_id} by user {current_user['username']}")

    # Note: ChromaDB collections in corpus directory are NOT deleted automatically
    # This is intentional to prevent accidental data loss
    # Future enhancement: Add option to delete vector data as well

    return {"message": f"Corpus {corpus_id} deleted successfully"}


@router.post("/{corpus_id}/permissions", response_model=PermissionGrantedResponse)
@limiter.limit(MANAGEMENT_RATE_LIMIT)
async def grant_permission(
    request: Request,
    corpus_id: int,
    permission_request: GrantPermissionRequest,
    current_user: dict = Depends(get_current_user),
) -> PermissionGrantedResponse:
    """Grant permission to a user for a corpus.

    Requires: owner or admin permission
    """
    # Check admin permission
    check_corpus_permission(corpus_id, current_user["id"], "admin")

    # Validate username
    username = validate_username(permission_request.username)

    conn = _get_conn()

    # Get target user ID
    cur = conn.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_row = cur.fetchone()

    if not user_row:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found",
        )

    target_user_id = user_row[0]

    # Insert or update permission
    try:
        conn.execute(
            """
            INSERT INTO corpus_permissions (
                corpus_id, user_id, permission_type, granted_by, granted_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(corpus_id, user_id) DO UPDATE SET
                permission_type = excluded.permission_type,
                granted_by = excluded.granted_by,
                granted_at = excluded.granted_at
            """,
            (
                corpus_id,
                target_user_id,
                permission_request.permission_type,
                current_user["id"],
                _current_timestamp(),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    logger.info(
        f"Granted {permission_request.permission_type} permission on corpus {corpus_id} "
        f"to user {username} by {current_user['username']}"
    )

    return PermissionGrantedResponse(
        message=f"Granted {permission_request.permission_type} permission to {username}",
        username=username,
        permission_type=permission_request.permission_type,
    )


@router.delete("/{corpus_id}/permissions/{username}")
@limiter.limit(MANAGEMENT_RATE_LIMIT)
async def revoke_permission(
    request: Request,
    corpus_id: int,
    username: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Revoke a user's permission for a corpus.

    Requires: owner or admin permission
    """
    # Check admin permission
    check_corpus_permission(corpus_id, current_user["id"], "admin")

    # Validate username
    username = validate_username(username)

    conn = _get_conn()

    # Get target user ID
    cur = conn.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_row = cur.fetchone()

    if not user_row:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found",
        )

    target_user_id = user_row[0]

    # Cannot revoke owner permission
    cur = conn.execute("SELECT owner_id FROM corpuses WHERE id = ?", (corpus_id,))
    owner_row = cur.fetchone()

    if owner_row and owner_row[0] == target_user_id:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke owner permission",
        )

    # Delete permission
    conn.execute(
        "DELETE FROM corpus_permissions WHERE corpus_id = ? AND user_id = ?",
        (corpus_id, target_user_id),
    )
    conn.commit()
    conn.close()

    logger.info(
        f"Revoked permission on corpus {corpus_id} from user {username} "
        f"by {current_user['username']}"
    )

    return {"message": f"Revoked permission from {username}"}


@router.post("/{corpus_id}/subscribe", response_model=SubscriptionResponse)
@limiter.limit(MANAGEMENT_RATE_LIMIT)
async def subscribe_to_corpus(
    request: Request,
    corpus_id: int,
    subscription_request: CreateSubscriptionRequest,
    current_user: dict = Depends(get_current_user),
) -> SubscriptionResponse:
    """Subscribe to a corpus.

    Creates a subscription record and grants read permission.
    Corpus must be approved by admin to subscribe.
    """
    conn = _get_conn()

    # Check corpus exists and is approved
    cur = conn.execute(
        "SELECT id, is_approved, name FROM corpuses WHERE id = ?",
        (corpus_id,),
    )
    corpus_row = cur.fetchone()

    if not corpus_row:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Corpus {corpus_id} not found",
        )

    if not corpus_row[1]:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot subscribe to unapproved corpus. Please wait for admin approval.",
        )

    timestamp = _current_timestamp()
    expires_at = None

    if subscription_request.duration_days:
        expires_at = timestamp + (subscription_request.duration_days * 24 * 60 * 60)

    try:
        # Create or update subscription
        conn.execute(
            """
            INSERT INTO subscriptions (
                user_id, corpus_id, status, tier, started_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, corpus_id) DO UPDATE SET
                status = 'active',
                tier = excluded.tier,
                started_at = excluded.started_at,
                expires_at = excluded.expires_at
            """,
            (
                current_user["id"],
                corpus_id,
                "active",
                subscription_request.tier,
                timestamp,
                expires_at,
            ),
        )

        # Grant read permission if not already exists
        try:
            conn.execute(
                """
                INSERT INTO corpus_permissions (
                    corpus_id, user_id, permission_type, granted_by, granted_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(corpus_id, user_id) DO NOTHING
                """,
                (corpus_id, current_user["id"], "read", current_user["id"], timestamp),
            )
        except sqlite3.IntegrityError:
            pass  # Permission already exists

        conn.commit()

        logger.info(
            f"User {current_user['username']} subscribed to corpus {corpus_id} "
            f"(tier: {subscription_request.tier})"
        )

        subscription = SubscriptionInfo(
            user_id=current_user["id"],
            corpus_id=corpus_id,
            status="active",
            tier=subscription_request.tier,
            started_at=timestamp,
            expires_at=expires_at,
        )

        return SubscriptionResponse(
            message=f"Successfully subscribed to corpus '{corpus_row[2]}'",
            subscription=subscription,
        )

    finally:
        conn.close()


@router.delete("/{corpus_id}/subscribe")
@limiter.limit(MANAGEMENT_RATE_LIMIT)
async def unsubscribe_from_corpus(
    request: Request,
    corpus_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Unsubscribe from a corpus.

    Updates subscription status to 'cancelled'.
    Note: Does not automatically revoke read permission - admin must do that separately.
    """
    conn = _get_conn()

    # Check subscription exists
    cur = conn.execute(
        """
        SELECT id FROM subscriptions
        WHERE user_id = ? AND corpus_id = ? AND status = 'active'
        """,
        (current_user["id"], corpus_id),
    )

    if not cur.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active subscription found for corpus {corpus_id}",
        )

    # Update subscription status
    conn.execute(
        """
        UPDATE subscriptions
        SET status = 'cancelled'
        WHERE user_id = ? AND corpus_id = ?
        """,
        (current_user["id"], corpus_id),
    )

    conn.commit()
    conn.close()

    logger.info(f"User {current_user['username']} unsubscribed from corpus {corpus_id}")

    return {"message": "Successfully unsubscribed from corpus"}


@router.post("/{corpus_id}/query", response_model=QueryResponse)
@limiter.limit(QUERY_RATE_LIMIT)
async def query_corpus(
    request: Request,
    corpus_id: int,
    query_request: CorpusQueryRequest,
    current_user: dict = Depends(get_current_user),
) -> QueryResponse:
    """Query a specific corpus with semantic search.

    Requires: read permission
    Logs usage for billing and analytics.
    """
    # Check read permission (also verifies corpus is approved)
    check_corpus_permission(corpus_id, current_user["id"], "read")

    # Get corpus database path and name
    corpus_path = get_corpus_db_path(corpus_id)

    conn = _get_conn()
    cur = conn.execute("SELECT name FROM corpuses WHERE id = ?", (corpus_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Corpus {corpus_id} not found",
        )

    corpus_name = row[0]

    # Query the corpus using ChromaDB
    # Note: corpus_name is used as the collection name in ChromaDB
    try:
        results = query_index(
            corpus_name,
            query_request.query,
            corpus_path,
            n_results=query_request.n_results,
        )

        context = compile_context(results)

        # Log usage for billing and analytics
        log_corpus_usage(
            user_id=current_user["id"],
            corpus_id=corpus_id,
            action="query",
            query_count=1,
            metadata={"query_length": len(query_request.query)},
        )

        logger.info(
            f"User {current_user['username']} queried corpus {corpus_id} "
            f"(query length: {len(query_request.query)})"
        )

        return QueryResponse(context=context, raw_results=results)

    except Exception as e:
        logger.error(f"Error querying corpus {corpus_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error querying corpus: {str(e)}",
        )


@router.post("/{corpus_id}/versions", response_model=CorpusVersionInfo)
@limiter.limit(MANAGEMENT_RATE_LIMIT)
async def create_corpus_version(
    request: Request,
    corpus_id: int,
    version_request: CreateVersionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new version snapshot of a corpus.

    Requires admin permission. Increments version number and records current
    chunk count and file count as metadata.

    Args:
        corpus_id: Corpus ID
        version_request: Version creation details (description)
        current_user: Authenticated user

    Returns:
        CorpusVersionInfo: Created version details

    Raises:
        HTTPException: 403 if insufficient permissions
        HTTPException: 404 if corpus not found
        HTTPException: 500 if version creation fails
    """
    # Check admin permission (required to create versions)
    check_corpus_permission(corpus_id, current_user["id"], required_permission="admin")

    conn = _get_conn()

    try:
        # Get current corpus metadata
        cur = conn.execute(
            "SELECT name, version FROM corpuses WHERE id = ?",
            (corpus_id,)
        )
        row = cur.fetchone()

        if not row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Corpus {corpus_id} not found"
            )

        corpus_name, current_version = row
        new_version = current_version + 1

        # Get collection stats from ChromaDB
        chunk_count = 0
        file_count = 0

        try:
            corpus_path = get_corpus_db_path(corpus_id)
            collection = get_or_create_collection(name=corpus_name, db_path=corpus_path)
            docs = collection.get(include=["metadatas"])

            chunk_count = len(docs["ids"])

            # Count unique source files
            sources = [meta.get("source", "Unknown") for meta in docs["metadatas"]]
            file_count = len(set(sources))

        except Exception as e:
            logger.warning(f"Could not get collection stats for corpus {corpus_id}: {e}")
            # Continue with chunk_count=0, file_count=0

        # Insert version record
        conn.execute(
            """
            INSERT INTO corpus_versions (
                corpus_id, version, description, created_by, created_at,
                chunk_count, file_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                corpus_id,
                new_version,
                version_request.description,
                current_user["id"],
                _current_timestamp(),
                chunk_count,
                file_count,
            ),
        )

        # Update corpus version number
        conn.execute(
            "UPDATE corpuses SET version = ?, updated_at = ? WHERE id = ?",
            (new_version, _current_timestamp(), corpus_id),
        )

        conn.commit()

        logger.info(
            f"User {current_user['username']} created version {new_version} "
            f"for corpus {corpus_id} ({chunk_count} chunks, {file_count} files)"
        )

        return CorpusVersionInfo(
            corpus_id=corpus_id,
            version=new_version,
            description=version_request.description,
            created_by_username=current_user["username"],
            created_at=_current_timestamp(),
            chunk_count=chunk_count,
            file_count=file_count,
        )

    except HTTPException:
        conn.close()
        raise
    except Exception as e:
        conn.close()
        logger.error(f"Error creating corpus version: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating version: {str(e)}",
        )
    finally:
        conn.close()


@router.get("/{corpus_id}/versions", response_model=List[CorpusVersionInfo])
@limiter.limit(QUERY_RATE_LIMIT)
async def list_corpus_versions(
    request: Request,
    corpus_id: int,
    current_user: dict = Depends(get_current_user),
):
    """List all versions of a corpus in descending order.

    Requires read permission.

    Args:
        corpus_id: Corpus ID
        current_user: Authenticated user

    Returns:
        List[CorpusVersionInfo]: List of version records

    Raises:
        HTTPException: 403 if insufficient permissions
        HTTPException: 404 if corpus not found
    """
    # Check read permission
    check_corpus_permission(corpus_id, current_user["id"], required_permission="read")

    conn = _get_conn()

    try:
        cur = conn.execute(
            """
            SELECT
                cv.corpus_id, cv.version, cv.description, cv.created_at,
                cv.chunk_count, cv.file_count, u.username
            FROM corpus_versions cv
            JOIN users u ON cv.created_by = u.id
            WHERE cv.corpus_id = ?
            ORDER BY cv.version DESC
            """,
            (corpus_id,),
        )

        versions = []
        for row in cur.fetchall():
            versions.append(
                CorpusVersionInfo(
                    corpus_id=row[0],
                    version=row[1],
                    description=row[2],
                    created_at=row[3],
                    chunk_count=row[4],
                    file_count=row[5],
                    created_by_username=row[6],
                )
            )

        logger.debug(
            f"User {current_user['username']} listed {len(versions)} versions "
            f"for corpus {corpus_id}"
        )

        return versions

    except Exception as e:
        logger.error(f"Error listing corpus versions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing versions: {str(e)}",
        )
    finally:
        conn.close()
