"""Sigma rule YAML validation service."""

from __future__ import annotations

import logging
from typing import Any

import yaml

from src.shared.exceptions import ValidationError

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ["id", "name", "description", "detection"]
DEPRECATED_FIELDS = ["level", "falsepositives"]  # Sigma v2 deprecated
MAX_FILE_SIZE = 1024 * 1024


class SigmaValidator:
    """Validates Sigma rule YAML files."""

    def validate(self, content: bytes) -> dict[str, Any]:
        """Validate Sigma rule YAML content.

        Args:
            content: Raw YAML file content as bytes

        Returns:
            Parsed and validated rule dictionary

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
            rule_data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValidationError(
                field="yaml_syntax",
                message=f"Invalid YAML syntax: {str(e)}",
            ) from None

        if not isinstance(rule_data, dict):
            raise ValidationError(
                field="yaml_structure",
                message="YAML content must be a mapping (dictionary)",
            )

        self._validate_required_fields(rule_data)
        self._validate_field_types(rule_data)
        self._validate_detection_section(rule_data)
        self._check_deprecated_fields(rule_data)
        self._validate_condition_syntax(rule_data)
        return rule_data

    def _validate_required_fields(self, data: dict[str, Any]) -> None:
        """Validate that all required Sigma fields are present."""
        missing = [field for field in REQUIRED_FIELDS if field not in data]
        if missing:
            raise ValidationError(
                field="required_fields",
                message=f"Missing required fields: {', '.join(missing)}",
            )

    def _validate_field_types(self, data: dict[str, Any]) -> None:
        """Validate field types."""
        if not isinstance(data.get("id"), str) or not data["id"].strip():
            raise ValidationError(field="id", message="Rule ID must be a non-empty string")

        if not isinstance(data.get("name"), str) or not data["name"].strip():
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
            # Basic validation: condition should reference detection keys
            detection_keys = set(data.get("detection", {}).keys())
            condition_words = set(condition.replace("(", " ").replace(")", " ").split())
            # Check if condition references non-existent detection keys
            invalid_refs = (
                condition_words - detection_keys - {"and", "or", "not", "1", "of", "them"}
            )
            if invalid_refs and not condition.startswith("selection"):
                logger.warning(
                    f"Condition may reference non-existent detection keys: {invalid_refs}"
                )
