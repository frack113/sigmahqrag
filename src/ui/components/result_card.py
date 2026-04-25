"""Result card component."""

from __future__ import annotations

import logging
from typing import Any

import gradio as gr

logger = logging.getLogger(__name__)

SEVERITY_COLORS = {
    "critical": "#ef4444",
    "high": "#f97316",
    "medium": "#f59e0b",
    "low": "#22c55e",
    "informational": "#3b82f6",
}


class ResultCard:
    """Result card component with metadata display."""

    def __init__(self) -> None:
        """Initialize the result card."""
        self.component = gr.JSON(label="Result")

    def get_component(self) -> gr.Component:
        """Get the component."""
        return self.component

    @staticmethod
    def format_card(result: dict[str, Any]) -> str:
        """Format a search result as an HTML card.

        Args:
            result: Search result with metadata

        Returns:
            HTML formatted card
        """
        metadata = result.get("metadata", {})
        title = metadata.get("title", result.get("text", "")[:50])
        description = metadata.get("description", "")
        severity = metadata.get("severity", "informational").lower()
        platform = metadata.get("platform", "")
        tactic = metadata.get("tactic", "")
        citation = result.get("citation", "")
        score = result.get("score", 0)

        severity_color = SEVERITY_COLORS.get(severity, SEVERITY_COLORS["informational"])

        html = f"""<div style="
            background: #252525;
            border-left: 3px solid {severity_color};
            padding: 12px;
            margin: 8px 0;
            border-radius: 4px;
        ">
            <div style="font-weight: bold; color: #e5e5e5; margin-bottom: 4px;">
                {title}
            </div>
            <div style="color: #a3a3a3; font-size: 13px; margin-bottom: 8px;">
                {description}
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap; font-size: 12px;">
                {"<span style='background: " + severity_color + "; color: white; padding: 2px 6px; border-radius: 3px;'>" + severity.upper() + "</span>" if severity else ""}
                {"<span style='color: #a3a3a3;'>" + platform + "</span>" if platform else ""}
                {"<span style='color: #a3a3a3;'>" + tactic + "</span>" if tactic else ""}
            </div>
            <div style="font-size: 11px; color: #737373; margin-top: 4px;">
                {citation} • Score: {score:.2f}
            </div>
        </div>"""
        return html

    @staticmethod
    def get_severity_color(severity: str) -> str:
        """Get color for severity level."""
        return SEVERITY_COLORS.get(severity.lower(), SEVERITY_COLORS["informational"])
