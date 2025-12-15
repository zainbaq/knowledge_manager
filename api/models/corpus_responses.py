"""Pydantic response models for corpus management."""

from typing import List, Optional

from pydantic import BaseModel, Field


class CorpusMetadata(BaseModel):
    """Metadata for a single corpus."""

    id: int = Field(..., description="Corpus ID", ge=1)
    name: str = Field(..., description="Corpus identifier")
    display_name: str = Field(..., description="Human-readable corpus name")
    description: Optional[str] = Field(None, description="Corpus description")
    category: Optional[str] = Field(None, description="Corpus category")
    version: int = Field(..., description="Current version number", ge=1)
    is_public: bool = Field(..., description="Whether corpus is public")
    is_approved: bool = Field(..., description="Whether corpus is approved")
    owner_username: str = Field(..., description="Username of corpus owner")
    created_at: int = Field(..., description="Creation timestamp (Unix epoch)")
    updated_at: int = Field(..., description="Last update timestamp (Unix epoch)")
    chunk_count: int = Field(default=0, description="Number of chunks", ge=0)
    file_count: int = Field(default=0, description="Number of files", ge=0)

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "id": 1,
                    "name": "legal_corpus_2024",
                    "display_name": "Legal Documents 2024",
                    "description": "Collection of legal documents and case law from 2024",
                    "category": "legal",
                    "version": 2,
                    "is_public": True,
                    "is_approved": True,
                    "owner_username": "alice",
                    "created_at": 1704067200,
                    "updated_at": 1704153600,
                    "chunk_count": 1500,
                    "file_count": 45,
                }
            ]
        }


class CorpusPermission(BaseModel):
    """Corpus permission details."""

    username: str = Field(..., description="Username with permission")
    permission_type: str = Field(..., description="Permission level (owner/admin/write/read)")
    granted_at: int = Field(..., description="Permission grant timestamp (Unix epoch)")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "username": "bob",
                    "permission_type": "read",
                    "granted_at": 1704067200,
                }
            ]
        }


class CorpusVersionInfo(BaseModel):
    """Corpus version information."""

    version: int = Field(..., description="Version number", ge=1)
    description: Optional[str] = Field(None, description="Version description")
    created_by: str = Field(..., description="Username of creator")
    created_at: int = Field(..., description="Creation timestamp (Unix epoch)")
    chunk_count: int = Field(default=0, description="Chunk count at version", ge=0)
    file_count: int = Field(default=0, description="File count at version", ge=0)

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "version": 2,
                    "description": "Added Q1 2024 legal documents",
                    "created_by": "alice",
                    "created_at": 1704153600,
                    "chunk_count": 1500,
                    "file_count": 45,
                }
            ]
        }


class SubscriptionInfo(BaseModel):
    """Subscription details."""

    user_id: int = Field(..., description="User ID", ge=1)
    corpus_id: int = Field(..., description="Corpus ID", ge=1)
    status: str = Field(..., description="Subscription status (active/expired/cancelled)")
    tier: Optional[str] = Field(None, description="Subscription tier (free/basic/premium)")
    started_at: int = Field(..., description="Start timestamp (Unix epoch)")
    expires_at: Optional[int] = Field(None, description="Expiry timestamp (Unix epoch, None for lifetime)")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "user_id": 2,
                    "corpus_id": 1,
                    "status": "active",
                    "tier": "premium",
                    "started_at": 1704067200,
                    "expires_at": 1735689600,
                }
            ]
        }


class ListCorpusesResponse(BaseModel):
    """Response for listing accessible corpuses."""

    corpuses: List[CorpusMetadata]

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "corpuses": [
                        {
                            "id": 1,
                            "name": "legal_corpus_2024",
                            "display_name": "Legal Documents 2024",
                            "description": "Collection of legal documents",
                            "category": "legal",
                            "version": 2,
                            "is_public": True,
                            "is_approved": True,
                            "owner_username": "alice",
                            "created_at": 1704067200,
                            "updated_at": 1704153600,
                            "chunk_count": 1500,
                            "file_count": 45,
                        }
                    ]
                }
            ]
        }


class CorpusDetailResponse(BaseModel):
    """Detailed corpus information including permissions and versions."""

    corpus: CorpusMetadata
    permissions: List[CorpusPermission]
    versions: List[CorpusVersionInfo]
    user_permission: Optional[str] = Field(
        None,
        description="Current user's permission level (owner/admin/write/read)",
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "corpus": {
                        "id": 1,
                        "name": "legal_corpus_2024",
                        "display_name": "Legal Documents 2024",
                        "description": "Collection of legal documents",
                        "category": "legal",
                        "version": 2,
                        "is_public": True,
                        "is_approved": True,
                        "owner_username": "alice",
                        "created_at": 1704067200,
                        "updated_at": 1704153600,
                        "chunk_count": 1500,
                        "file_count": 45,
                    },
                    "permissions": [
                        {
                            "username": "bob",
                            "permission_type": "read",
                            "granted_at": 1704067200,
                        }
                    ],
                    "versions": [
                        {
                            "version": 2,
                            "description": "Added Q1 2024 documents",
                            "created_by": "alice",
                            "created_at": 1704153600,
                            "chunk_count": 1500,
                            "file_count": 45,
                        }
                    ],
                    "user_permission": "owner",
                }
            ]
        }


class CreateCorpusResponse(BaseModel):
    """Response after creating a corpus."""

    message: str = Field(..., description="Success message")
    corpus_id: int = Field(..., description="Created corpus ID", ge=1)
    corpus_name: str = Field(..., description="Created corpus name")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "message": "Corpus 'Legal Documents 2024' created successfully. Awaiting admin approval.",
                    "corpus_id": 1,
                    "corpus_name": "legal_corpus_2024",
                }
            ]
        }


class PermissionGrantedResponse(BaseModel):
    """Response after granting permission."""

    message: str = Field(..., description="Success message")
    username: str = Field(..., description="Username permission was granted to")
    permission_type: str = Field(..., description="Permission level granted")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "message": "Granted read permission to bob",
                    "username": "bob",
                    "permission_type": "read",
                }
            ]
        }


class SubscriptionResponse(BaseModel):
    """Response after subscription action."""

    message: str = Field(..., description="Success message")
    subscription: SubscriptionInfo

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "message": "Successfully subscribed to corpus",
                    "subscription": {
                        "user_id": 2,
                        "corpus_id": 1,
                        "status": "active",
                        "tier": "free",
                        "started_at": 1704067200,
                        "expires_at": None,
                    },
                }
            ]
        }


class UsageStatsResponse(BaseModel):
    """Response for usage statistics."""

    total_actions: int = Field(default=0, description="Total number of actions", ge=0)
    total_queries: int = Field(default=0, description="Total number of queries", ge=0)
    last_access: Optional[int] = Field(None, description="Last access timestamp (Unix epoch)")
    unique_users: Optional[int] = Field(None, description="Unique users (corpus stats only)", ge=0)

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "total_actions": 150,
                    "total_queries": 120,
                    "last_access": 1704153600,
                    "unique_users": 15,
                }
            ]
        }
