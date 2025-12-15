"""Input validation utilities for API endpoints."""

import re
from pathlib import Path
from fastapi import HTTPException
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY


def validate_username(username: str) -> str:
    """
    Validate and sanitize username to prevent path traversal attacks.

    Rules:
    - 3-32 characters
    - Only letters, numbers, hyphens, underscores
    - Must start with letter or number (not hyphen/underscore)
    - Cannot be reserved system names

    Args:
        username: Username to validate

    Returns:
        The validated username

    Raises:
        HTTPException: 422 if validation fails
    """
    if not username:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username cannot be empty"
        )

    if not 3 <= len(username) <= 32:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username must be 3-32 characters"
        )

    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$', username):
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username must start with letter/number and contain only letters, numbers, hyphens, underscores"
        )

    # Block reserved system names
    reserved = {'admin', 'root', 'system', 'api', 'test', 'user'}
    if username.lower() in reserved:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username is reserved"
        )

    return username


def validate_collection_name(name: str) -> str:
    """
    Validate collection name to prevent path traversal attacks.

    Rules:
    - 1-64 characters
    - Only letters, numbers, hyphens, underscores
    - Cannot be '.' or '..'

    Args:
        name: Collection name to validate

    Returns:
        The validated collection name

    Raises:
        HTTPException: 422 if validation fails
    """
    if not name:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Collection name cannot be empty"
        )

    # Block directory traversal special names
    if name in ('.', '..'):
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid collection name"
        )

    if not 1 <= len(name) <= 64:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Collection name must be 1-64 characters"
        )

    # Only allow alphanumeric characters, underscores, and hyphens
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Collection name must contain only letters, numbers, hyphens, underscores"
        )

    return name


def validate_filename(filename: str) -> str:
    """
    Validate and sanitize uploaded filenames.

    Args:
        filename: Original filename from upload

    Returns:
        Sanitized filename

    Raises:
        HTTPException: If validation fails
    """
    if not filename:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filename cannot be empty"
        )

    # Get the actual filename without any path components
    safe_filename = Path(filename).name

    if not safe_filename:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid filename"
        )

    # Check for null bytes and other dangerous characters
    if '\x00' in safe_filename:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filename contains invalid characters"
        )

    if len(safe_filename) > 255:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filename too long (max 255 characters)"
        )

    return safe_filename


def sanitize_path_component(component: str) -> str:
    """
    Remove any path traversal characters from a string.

    This is a defense-in-depth measure. Should be used AFTER validation.

    Args:
        component: String that will be used as a path component

    Returns:
        str: Sanitized string safe for use in file paths
    """
    # Remove any path separators and null bytes
    sanitized = component.replace('/', '').replace('\\', '').replace('\0', '')
    # Remove . and ..
    sanitized = sanitized.replace('..', '').replace('.', '')
    return sanitized
