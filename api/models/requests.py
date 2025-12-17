"""Pydantic request models for API endpoints."""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class QueryRequest(BaseModel):
    """Request model for querying collections."""

    query: str = Field(
        ...,
        description="Search query text",
        min_length=1,
        examples=["What is machine learning?"],
    )
    collection: Optional[str] = Field(
        None,
        description="Single collection to query",
        examples=["research_papers"],
    )
    collections: Optional[List[str]] = Field(
        None,
        description="Multiple collections to query",
        examples=[["research_papers", "documentation"]],
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "query": "What is machine learning?",
                    "collection": "research_papers",
                },
                {
                    "query": "API documentation",
                    "collections": ["docs", "tutorials"],
                },
            ]
        }


class UserCredentials(BaseModel):
    """Request model for user login/register."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern="^[a-zA-Z0-9_-]+$",
        description="Username (alphanumeric, underscore, hyphen)",
        examples=["john_doe"],
    )
    password: str = Field(
        ...,
        min_length=8,
        description="Password (minimum 8 characters)",
        examples=["SecurePassword123!"],
    )

    @field_validator("password")
    @classmethod
    def truncate_password(cls, v: str) -> str:
        """Truncate password to 72 bytes for bcrypt compatibility."""
        encoded = v.encode("utf-8")
        if len(encoded) > 72:
            return encoded[:72].decode("utf-8", errors="ignore")
        return v

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "username": "john_doe",
                    "password": "SecurePassword123!",
                }
            ]
        }
