"""Admin authentication and authorization utilities."""

from fastapi import Depends, HTTPException, status

from api.auth import get_current_user
from config import ADMIN_USERS


def is_admin(username: str) -> bool:
    """Check if a user is an admin.

    Args:
        username: Username to check

    Returns:
        bool: True if user is in ADMIN_USERS list
    """
    return username in ADMIN_USERS


def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency to require admin user.

    This is a FastAPI dependency that can be used in endpoint signatures
    to ensure only admin users can access the endpoint.

    Args:
        current_user: Authenticated user from get_current_user dependency

    Returns:
        dict: User dict if user is admin

    Raises:
        HTTPException: 403 if user is not an admin

    Example:
        @router.get("/admin/stats")
        async def get_stats(admin_user: dict = Depends(get_admin_user)):
            # Only admins can access this
            pass
    """
    if not is_admin(current_user["username"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
