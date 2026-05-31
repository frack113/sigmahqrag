"""Sigma rule validator."""

from __future__ import annotations

import logging
from src.back.documents.models import SigmaRule, ValidationError, ValidationResult

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
        errors.append(ValidationError(field="title", message="Title cannot be empty"))

    if not rule.condition or not str(rule.condition).strip():
        errors.append(ValidationError(field="condition", message="Condition cannot be empty"))

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
        valid_statuses = ["experimental", "stable", "testing", "deprecated", "test", "unsupported"]
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
