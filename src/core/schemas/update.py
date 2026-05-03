"""Pydantic schemas for update management."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UpdateApplyRequest(BaseModel):
    """Request model for applying an update."""

    service: str = Field(..., description="Service to update (llama.cpp, qdrant)")
    version: str = Field(..., description="Version to apply")


class UpdateApplyResponse(BaseModel):
    """Response model for update application."""

    status: str = Field(..., description="Update status (success, failed)")
    service: str = Field(..., description="Service updated")
    version: str = Field(..., description="New version applied")
    backup_id: str | None = Field(None, description="Backup ID created")
    previous_version: str | None = Field(None, description="Previous version")
    health_check: str | None = Field(None, description="Health check result")
    error: str | None = Field(None, description="Error message if failed")
    rollback: str | None = Field(None, description="Rollback performed")


class UpdateRollbackRequest(BaseModel):
    """Request model for rollback."""

    service: str = Field(..., description="Service to rollback (llama.cpp, qdrant)")


class UpdateRollbackResponse(BaseModel):
    """Response model for rollback."""

    status: str = Field(..., description="Rollback status (success, failed)")
    service: str = Field(..., description="Service rolled back")
    version: str | None = Field(None, description="Version restored to")
    backup_id: str | None = Field(None, description="Backup ID used")
    health_check: str | None = Field(None, description="Health check result")
    error: str | None = Field(None, description="Error message if failed")


class BackupInfo(BaseModel):
    """Information about a backup."""

    backup_id: str = Field(..., description="Backup identifier")
    service: str = Field(..., description="Service backed up")
    version: str = Field(..., description="Version backed up")
    created: datetime = Field(..., description="Backup creation time")
    size_bytes: int | None = Field(None, description="Backup size in bytes")


class ServiceVersionInfo(BaseModel):
    """Version information for a service."""

    current_version: str = Field(..., description="Current installed version")
    last_updated: datetime | None = Field(None, description="Last update time")


class UpdateStatus(BaseModel):
    """Status response for update system."""

    llama_cpp: ServiceVersionInfo = Field(..., description="llama.cpp version info")
    qdrant: ServiceVersionInfo = Field(..., description="Qdrant version info")
    available_backups: list[BackupInfo] = Field(
        default_factory=list, description="Available backups"
    )


def create_apply_response(
    status: str,
    service: str,
    version: str,
    backup_id: str | None = None,
    previous_version: str | None = None,
    health_check: str | None = None,
    error: str | None = None,
    rollback: str | None = None,
) -> dict[str, Any]:
    """Create an update apply response dict.

    Args:
        status: Update status
        service: Service name
        version: Version applied
        backup_id: Backup ID
        previous_version: Previous version
        health_check: Health check result
        error: Error message
        rollback: Rollback performed

    Returns:
        Response dictionary
    """
    result: dict[str, Any] = {
        "status": status,
        "service": service,
        "version": version,
    }
    if backup_id is not None:
        result["backup_id"] = backup_id
    if previous_version is not None:
        result["previous_version"] = previous_version
    if health_check is not None:
        result["health_check"] = health_check
    if error is not None:
        result["error"] = error
    if rollback is not None:
        result["rollback"] = rollback

    return result


def create_rollback_response(
    status: str,
    service: str,
    version: str | None = None,
    backup_id: str | None = None,
    health_check: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Create an update rollback response dict.

    Args:
        status: Rollback status
        service: Service name
        version: Version restored
        backup_id: Backup ID used
        health_check: Health check result
        error: Error message

    Returns:
        Response dictionary
    """
    result: dict[str, Any] = {
        "status": status,
        "service": service,
    }
    if version is not None:
        result["version"] = version
    if backup_id is not None:
        result["backup_id"] = backup_id
    if health_check is not None:
        result["health_check"] = health_check
    if error is not None:
        result["error"] = error

    return result
