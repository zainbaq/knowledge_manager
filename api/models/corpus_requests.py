"""Pydantic request models for corpus management."""

from typing import Optional

from pydantic import BaseModel, Field


class CreateCorpusRequest(BaseModel):
    """Request model for creating a new corpus."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Unique corpus identifier (letters, numbers, hyphens, underscores)",
        examples=["legal_corpus_2024"],
    )
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Human-readable corpus name",
        examples=["Legal Documents 2024"],
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Corpus description",
        examples=["Collection of legal documents and case law from 2024"],
    )
    category: Optional[str] = Field(
        None,
        max_length=64,
        description="Corpus category",
        examples=["legal", "medical", "research"],
    )
    is_public: bool = Field(
        default=False,
        description="Whether corpus is publicly accessible (requires admin approval)",
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "name": "legal_corpus_2024",
                    "display_name": "Legal Documents 2024",
                    "description": "Collection of legal documents and case law from 2024",
                    "category": "legal",
                    "is_public": True,
                }
            ]
        }


class UpdateCorpusRequest(BaseModel):
    """Request model for updating corpus metadata."""

    display_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=128,
        description="Updated display name",
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Updated description",
    )
    category: Optional[str] = Field(
        None,
        max_length=64,
        description="Updated category",
    )
    is_public: Optional[bool] = Field(
        None,
        description="Updated public visibility",
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "display_name": "Legal Documents 2024 - Updated",
                    "description": "Updated collection with Q1 2024 additions",
                    "category": "legal",
                }
            ]
        }


class GrantPermissionRequest(BaseModel):
    """Request model for granting corpus access to a user."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=32,
        description="Username to grant access to",
        examples=["alice"],
    )
    permission_type: str = Field(
        ...,
        pattern=r"^(read|write|admin)$",
        description="Permission level: read, write, or admin",
        examples=["read"],
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "username": "alice",
                    "permission_type": "read",
                }
            ]
        }


class CreateSubscriptionRequest(BaseModel):
    """Request model for subscribing to a corpus."""

    tier: str = Field(
        default="free",
        pattern=r"^(free|basic|premium)$",
        description="Subscription tier",
        examples=["free"],
    )
    duration_days: Optional[int] = Field(
        None,
        ge=1,
        le=3650,
        description="Subscription duration in days (None for lifetime access)",
        examples=[365],
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "tier": "free",
                },
                {
                    "tier": "premium",
                    "duration_days": 365,
                },
            ]
        }


class CorpusQueryRequest(BaseModel):
    """Request model for querying a specific corpus."""

    query: str = Field(
        ...,
        min_length=1,
        description="Search query text",
        examples=["What are the key legal precedents?"],
    )
    n_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of results to return",
        examples=[5],
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "query": "What are the key legal precedents?",
                    "n_results": 5,
                }
            ]
        }


class CreateVersionRequest(BaseModel):
    """Request model for creating a new corpus version."""

    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Version description",
        examples=["Added Q1 2024 legal documents"],
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "description": "Added Q1 2024 legal documents",
                }
            ]
        }
