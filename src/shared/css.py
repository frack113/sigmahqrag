"""
Shared CSS Styles for SigmaHQ RAG
Centralized styling across all application tabs.
"""

# GitHub Tab now uses Gradio native features (no custom CSS needed)
# Layout uses: gr.Column(variant="compact"), gr.Row(equal_height=False)

CSS_GITHUB = ""


def get_css() -> str:
    """Return centralized CSS styles."""
    return CSS_GITHUB