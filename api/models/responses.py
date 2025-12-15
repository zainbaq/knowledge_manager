"""Pydantic response models for API endpoints."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response format with optional MCP error code."""

    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="MCP error code for retry logic")

    class Config:
        json_schema_extra = {
            "examples": [
                {"detail": "Invalid API key", "error_code": "auth.invalid_api_key"},
                {"detail": "Collection not found", "error_code": "resource.collection_not_found"},
            ]
        }


class AuthResponse(BaseModel):
    """Response for login/register/create-api-key endpoints."""

    api_key: str = Field(..., description="API key for authentication")

    class Config:
        json_schema_extra = {
            "examples": [
                {"api_key": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"}
            ]
        }


class UploadResponse(BaseModel):
    """Response for create-index and update-index endpoints."""

    message: str = Field(..., description="Success message")
    indexed_chunks: int = Field(
        ..., description="Number of chunks indexed", ge=0
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "message": "Created index and ingested 42 chunks into 'research'",
                    "indexed_chunks": 42,
                }
            ]
        }


class CollectionMetadata(BaseModel):
    """Metadata for a single collection."""

    name: str = Field(..., description="Collection name")
    files: List[str] = Field(..., description="List of source files")
    num_chunks: int = Field(..., description="Total number of chunks", ge=0)

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "name": "research_papers",
                    "files": ["paper1.pdf", "paper2.pdf"],
                    "num_chunks": 150,
                }
            ]
        }


class ListCollectionsResponse(BaseModel):
    """Response for list-indexes endpoint."""

    collections: List[CollectionMetadata]

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "collections": [
                        {
                            "name": "research_papers",
                            "files": ["paper1.pdf", "paper2.pdf"],
                            "num_chunks": 150,
                        },
                        {
                            "name": "documentation",
                            "files": ["readme.md"],
                            "num_chunks": 25,
                        },
                    ]
                }
            ]
        }


class QueryResponse(BaseModel):
    """Response for query endpoint."""

    context: str = Field(..., description="Compiled context from query results")
    raw_results: dict = Field(..., description="Raw ChromaDB query results")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "context": "Machine learning is a subset of AI...\n\nDeep learning uses neural networks...",
                    "raw_results": {
                        "ids": [["id1", "id2"]],
                        "documents": [["doc1 text", "doc2 text"]],
                        "metadatas": [[{"source": "paper1.pdf"}, {"source": "paper2.pdf"}]],
                        "distances": [[0.123, 0.456]],
                    },
                }
            ]
        }


class DeleteResponse(BaseModel):
    """Response for delete-index endpoint."""

    message: str = Field(..., description="Confirmation message")

    class Config:
        json_schema_extra = {
            "examples": [
                {"message": "Collection 'research_papers' deleted successfully"}
            ]
        }


class StatusResponse(BaseModel):
    """Response for status endpoint."""

    status: str = Field(..., description="API status", pattern="^ok$")

    class Config:
        json_schema_extra = {"examples": [{"status": "ok"}]}
