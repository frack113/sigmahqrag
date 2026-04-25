"""Sigma rule validator."""

from __future__ import annotations

import logging
import re

from src.documents.models import SigmaRule, ValidationError, ValidationResult

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = {"title", "detection", "condition"}
OPTIONAL_FIELDS = {
    "description",
    "author",
    "date",
    "modified",
    "references",
    "tags",
    "level",
    "falsepositives",
    "logsource",
    "status",
    "license",
}


def validate_sigma_rule(rule: SigmaRule) -> ValidationResult:
    """Validate a Sigma rule against specification.

    Args:
        rule: SigmaRule to validate

    Returns:
        ValidationResult with validation status and errors
    """
    errors: list[ValidationError] = []

    if not rule.title or not rule.title.strip():
        errors.append(
            ValidationError(field="title", message="Title cannot be empty")
        )

    if not rule.condition or not str(rule.condition).strip():
        errors.append(
            ValidationError(field="condition", message="Condition cannot be empty")
        )

    if not rule.detection or not isinstance(rule.detection, dict):
        errors.append(
            ValidationError(field="detection", message="Detection must be a non-empty dict")
        )

    if rule.level is not None:
        valid_levels = [
            "informational",
            "low",
            "medium",
            "high",
            "critical",
        ]
        if rule.level.lower() not in valid_levels:
            errors.append(
                ValidationError(
                    field="level",
                    message=f"Invalid level '{rule.level}'. Must be one of: {valid_levels}",
                )
            )

    if rule.status is not None:
        valid_statuses = ["experimental", "stable", "testing", "deprecated"]
        if rule.status.lower() not in valid_statuses:
            errors.append(
                ValidationError(
                    field="status",
                    message=f"Invalid status '{rule.status}'. Must be one of: {valid_statuses}",
                )
            )

    return ValidationResult(
        valid=len(errors) == 0,
        rule=rule,
        errors=errors,
    )


def validate_encoding(content: str) -> list[ValidationError]:
    """Validate file encoding.

    Args:
        content: File content as string

    Returns:
        List of encoding errors
    """
    errors: list[ValidationError] = []

    try:
        content.encode("utf-8")
    except UnicodeEncodeError:
        errors.append(
            ValidationError(
                field="encoding",
                message="File must be valid UTF-8",
            )
        )

    return errors


def validate_indentation(content: str) -> list[ValidationError]:
    """Validate YAML indentation (4 spaces).

    Args:
        content: File content as string

    Returns:
        List of indentation errors
    """
    errors: list[ValidationError] = []

    for line_no, line in enumerate(content.splitlines(), 1):
        if line.startswith(" ") and not line.startswith("    "):
            if not re.match(r"^(\t|    )+", line):
                errors.append(
                    ValidationError(
                        field="indentation",
                        message=f"Line {line_no}:Must use 4-space indentation",
                    )
                )

    return errors


def validate_keys_lowercase(content: str) -> list[ValidationError]:
    """Validate YAML keys are lowercase.

    Args:
        content: File content as string

    Returns:
        List of key case errors
    """
    errors: list[ValidationError] = []

    key_pattern = re.compile(r"^([a-zA-Z][a-zA-Z0-9_]*)\s*:", re.MULTILINE)
    for match in key_pattern.finditer(content):
        key = match.group(1)
        if key.lower() != key:
            errors.append(
                ValidationError(
                    field="keys",
                    message=f"Key '{key}' must be lowercase",
                )
            )

    return errors
