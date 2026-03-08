"""
Markdown Renderer Component

Component for rendering markdown content with syntax highlighting and custom styling.
"""

import markdown
from nicegui import ui
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound


class MarkdownRenderer:
    """
    A component for rendering markdown content with syntax highlighting.

    Attributes:
        content: The markdown content to render
        theme: The syntax highlighting theme (default: 'monokai')
        show_line_numbers: Whether to show line numbers (default: False)
        max_width: Maximum width for the rendered content (default: None)
    """

    def __init__(
        self,
        content: str,
        theme: str = "monokai",
        show_line_numbers: bool = False,
        max_width: int | None = None,
    ):
        """
        Initialize the markdown renderer component.

        Args:
            content: The markdown content to render
            theme: The syntax highlighting theme name
            show_line_numbers: Whether to display line numbers
            max_width: Maximum width in pixels (None for unlimited)
        """
        self.content = content
        self.theme = theme
        self.show_line_numbers = show_line_numbers
        self.max_width = max_width
        self.renderer = None

    def render(self):
        """
        Render the markdown content with syntax highlighting.

        Returns:
            The rendered markdown element
        """
        # Create container
        container = ui.column().classes("w-full")

        with container:
            # Convert markdown to HTML
            html_content = self._convert_markdown()

            # Create styled HTML element
            self.renderer = ui.html(html_content).classes(
                "markdown-content prose max-w-none"
            )

            # Apply max width if specified
            if self.max_width:
                self.renderer.style(f"max-width: {self.max_width}px")

        return container

    def _convert_markdown(self) -> str:
        """
        Convert markdown to HTML with syntax highlighting.

        Returns:
            HTML string with syntax highlighting
        """
        # Convert markdown to HTML
        md = markdown.Markdown(
            extensions=[
                "fenced_code",
                "codehilite",
                "tables",
                "attr_list",
                "def_list",
                "footnotes",
                "md_in_html",
            ]
        )
        html = md.convert(self.content)

        # Add syntax highlighting for code blocks
        html = self._highlight_code_blocks(html)

        return html

    def _highlight_code_blocks(self, html: str) -> str:
        """
        Apply syntax highlighting to code blocks using Pygments.

        Args:
            html: HTML string with code blocks

        Returns:
            HTML string with syntax highlighting
        """
        # Find all code blocks
        import re

        # Pattern to match code blocks with language specification
        code_block_pattern = (
            r'<pre><code class="language-(\w+)">([\s\S]*?)</code></pre>'
        )

        def replace_code_block(match):
            language = match.group(1)
            code = match.group(2)

            try:
                # Get lexer for the language
                lexer = get_lexer_by_name(language, stripall=True)

                # Get formatter
                formatter = HtmlFormatter(
                    style=self.theme,
                    linenos=self.show_line_numbers,
                    noclasses=False,
                )

                # Highlight the code
                highlighted = highlight(code, lexer, formatter)

                return highlighted

            except ClassNotFound:
                # If language not found, return original code block
                return match.group(0)

        # Replace code blocks
        highlighted_html = re.sub(code_block_pattern, replace_code_block, html)

        return highlighted_html

    def update_content(self, new_content: str) -> None:
        """
        Update the content and re-render.

        Args:
            new_content: New markdown content
        """
        self.content = new_content
        if self.renderer:
            self.renderer.text = self._convert_markdown()

    def set_theme(self, theme: str) -> None:
        """
        Update the syntax highlighting theme.

        Args:
            theme: New theme name
        """
        self.theme = theme
        if self.renderer:
            self.renderer.text = self._convert_markdown()

    def set_show_line_numbers(self, show: bool) -> None:
        """
        Toggle line numbers display.

        Args:
            show: Whether to show line numbers
        """
        self.show_line_numbers = show
        if self.renderer:
            self.renderer.text = self._convert_markdown()
