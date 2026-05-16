from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DownloadUpdatePayload(BaseModel):
    action: Literal["download_update"] = "download_update"
    version: str = "latest"
    force: bool = False


class ServiceControlPayload(BaseModel):
    action: Literal["service_control"] = "service_control"
    command: Literal["start", "stop", "restart"]


class ProgressPayload(BaseModel):
    action: Literal["progress"] = "progress"
    download_id: str


class CancelPayload(BaseModel):
    action: Literal["cancel"] = "cancel"
    download_id: str


class CollectionManagementPayload(BaseModel):
    action: Literal["collection_management"] = "collection_management"
    operation: Literal["create", "delete", "list", "get"]
    collection_name: str
    config: dict[str, Any] | None = None


class DataManagementPayload(BaseModel):
    action: Literal["data_management"] = "data_management"
    operation: Literal["add", "delete", "update"]
    collection_name: str
    id: str | None = None
    vector: list[float] | None = None
    payload: dict[str, Any] | None = None


class VectorSearchPayload(BaseModel):
    action: Literal["vector_search"] = "vector_search"
    query_vector: list[float]
    top_k: int = 5
    collection_name: str


class EmbedSigmaRefPayload(BaseModel):
    action: Literal["embed_sigmaref"] = "embed_sigmaref"
    registry_path: str = "data/documents/sigmaref"
    collection_name: str = "sigma_doc"


class QdrantActionRequest(BaseModel):
    action: Literal[
        "download_update",
        "service_control",
        "collection_management",
        "data_management",
        "vector_search",
        "progress",
        "cancel",
        "embed_sigmaref",
    ]
    payload: (
        DownloadUpdatePayload
        | ServiceControlPayload
        | ProgressPayload
        | CancelPayload
        | CollectionManagementPayload
        | DataManagementPayload
        | VectorSearchPayload
        | EmbedSigmaRefPayload
    ) = Field(..., discriminator="action")


class QdrantActionResponse(BaseModel):
    status: Literal["success", "error"]
    action: str
    data: Any | None = None
    message: str | None = None
    error_code: str | None = None
    details: dict[str, Any] | None = None
