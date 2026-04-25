"""Details panel component."""

from __future__ import annotations

import logging
from typing import Any

import gradio as gr

logger = logging.getLogger(__name__)


class DetailsPanel:
    """Details panel component for showing rule details."""

    def __init__(self) -> None:
        """Initialize the details panel."""
        self.component = gr.Markdown(value="Select a result to view details")

    def get_component(self) -> gr.Component:
        """Get the component."""
        return self.component

    @staticmethod
    def format_details(result: dict[str, Any]) -> str:
        """Format result details for display.

        Args:
            result: Search result with metadata

        Returns:
            Formatted Markdown
        """
        metadata = result.get("metadata", {})
        text = result.get("text", "")
        title = metadata.get("title", "Untitled Rule")
        description = metadata.get("description", "")
        severity = metadata.get("severity", "unknown")
        platform = metadata.get("platform", "")
        tactic = metadata.get("tactic", "")
        citation = result.get("citation", "")
        score = result.get("score", 0)

        details = f"""# {title}

**Description:** {description}

**Severity:** {severity.upper()}
**Platform:** {platform}
**Tactic:** {tactic}

---

**Source:** {citation}

**Similarity Score:** {score:.2f}

---

### Rule Content

```
{text}
```

---

*Select another result to view its details*
"""
        return details

    @staticmethod
    def format_empty_state(query: str | None = None) -> str:
        """Format empty state message.

        Args:
            query: Original search query

        Returns:
            Empty state message
        """
        if query:
            return f"**Aucune règle trouvée pour '{query}'**\n\nEssayez de:\n- Reformuler votre requête\n- Utiliser des mots-clés différents\n- Réduire les critères de recherche"
        return "**No results yet**\n\nEnter a search query to find Sigma rules"
