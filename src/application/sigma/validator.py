"""Sigma rule YAML validation service."""

from __future__ import annotations

import logging
from typing import Any

import yaml

from src.core.sigma.models import SigmaRule
from src.shared.exceptions import ValidationError

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ["id", "description", "detection"]
DEPRECATED_FIELDS = ["level", "falsepositives"]  # Sigma v2 deprecated
MAX_FILE_SIZE = 1024 * 1024

_VALID_LEVELS = frozenset({"informational", "low", "medium", "high", "critical"})
_VALID_STATUSES = frozenset(
    {"experimental", "stable", "testing", "deprecated", "test", "unsupported"}
)


class SigmaValidator:
    """Validates Sigma rule YAML files."""

    def validate(self, content: bytes) -> SigmaRule:
        """Validate Sigma rule YAML content.

        Args:
            content: Raw YAML file content as bytes

        Returns:
            Parsed and validated SigmaRule

        Raises:
            ValidationError: If validation fails
        """
        if not content:
            raise ValidationError(field="file", message="Empty file provided")

        if len(content) > MAX_FILE_SIZE:
            raise ValidationError(
                "file",
                f"File too large. Maximum size is {MAX_FILE_SIZE // 1024}KB",
            )

        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValidationError(
                field="yaml_syntax",
                message=f"Invalid YAML syntax: {str(e)}",
            ) from None

        if not isinstance(data, dict):
            raise ValidationError(
                field="yaml_structure",
                message="YAML content must be a mapping (dictionary)",
            )

        # Normalize name/title duality — Sigma YAML uses "name" or "title"
        self._normalize_name_title(data)

        self._validate_required_fields(data)
        self._validate_field_types(data)
        self._validate_detection_section(data)
        self._check_deprecated_fields(data)
        self._validate_condition_syntax(data)
        self._validate_level(data)
        self._validate_status(data)

        return SigmaRule.from_dict(data)

    def _normalize_name_title(self, data: dict[str, Any]) -> None:
        """Normalize 'name' / 'title' duality.

        Sigma YAML can use either key. The model uses 'title'.
        """
        if "title" in data and "name" not in data:
            data["name"] = data["title"]
        elif "name" in data and "title" not in data:
            data["title"] = data["name"]

    def _validate_required_fields(self, data: dict[str, Any]) -> None:
        """Validate that all required Sigma fields are present."""
        # At least one of 'name' or 'title' is required
        has_name_field = "name" in data or "title" in data
        missing = [field for field in REQUIRED_FIELDS if field not in data]
        if not has_name_field:
            missing.append("name")
        if missing:
            raise ValidationError(
                field="required_fields",
                message=f"Missing required fields: {', '.join(missing)}",
            )

    def _validate_field_types(self, data: dict[str, Any]) -> None:
        """Validate field types."""
        if not isinstance(data.get("id"), str) or not data["id"].strip():
            raise ValidationError(field="id", message="Rule ID must be a non-empty string")

        name_val = data.get("name") or data.get("title", "")
        if not isinstance(name_val, str) or not name_val.strip():
            raise ValidationError(field="name", message="Rule name must be a non-empty string")

        if not isinstance(data.get("description"), str) or not data["description"].strip():
            raise ValidationError(
                field="description", message="Description must be a non-empty string"
            )

    def _validate_detection_section(self, data: dict[str, Any]) -> None:
        """Validate detection section structure."""
        detection = data.get("detection")
        if not isinstance(detection, dict):
            raise ValidationError(
                field="detection",
                message="Detection section must be a mapping",
            )

        if not detection:
            raise ValidationError(
                field="detection",
                message="Detection section cannot be empty",
            )

    def _check_deprecated_fields(self, data: dict[str, Any]) -> None:
        """Warn about deprecated Sigma fields."""
        for field in DEPRECATED_FIELDS:
            if field in data:
                logger.warning(f"Deprecated field '{field}' found in rule")

    def _validate_condition_syntax(self, data: dict[str, Any]) -> None:
        """Validate condition syntax if present."""
        condition = data.get("condition")
        if condition and isinstance(condition, str):
            detection_keys = set(data.get("detection", {}).keys())
            condition_words = set(condition.replace("(", " ").replace(")", " ").split())
            invalid_refs = (
                condition_words - detection_keys - {"and", "or", "not", "1", "of", "them"}
            )
            if invalid_refs and not condition.startswith("selection"):
                logger.warning(
                    f"Condition may reference non-existent detection keys: {invalid_refs}"
                )

    def _validate_level(self, data: dict[str, Any]) -> None:
        """Validate level field if present."""
        level = data.get("level")
        if level is not None and level not in _VALID_LEVELS:
            raise ValidationError(
                field="level",
                message=f"Invalid level '{level}'. "
                f"Must be one of: {', '.join(sorted(_VALID_LEVELS))}",
            )

    def _validate_status(self, data: dict[str, Any]) -> None:
        """Validate status field if present."""
        status = data.get("status")
        if status is not None and status not in _VALID_STATUSES:
            raise ValidationError(
                field="status",
                message=f"Invalid status '{status}'. "
                f"Must be one of: {', '.join(sorted(_VALID_STATUSES))}",
            )
