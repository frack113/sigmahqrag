"""
Loading Spinner Component

Component for displaying a loading spinner during async operations.
"""

from nicegui import ui


class LoadingSpinner:
    """
    A component that displays a loading spinner.

    Attributes:
        spinner: The UI element containing the spinner
    """

    def __init__(self, size: str = "md", color: str = "blue"):
        """
        Initialize the loading spinner component.

        Args:
            size: Size of the spinner ('xs', 'sm', 'md', 'lg', 'xl')
            color: Color of the spinner (default: 'blue')
        """
        self.size = size
        self.color = color
        self.spinner = None

    def render(self):
        """
        Render the loading spinner.

        Returns:
            The spinner element
        """
        # Create container
        container = ui.row().classes("items-center justify-center")

        with container:
            # Create spinner
            self.spinner = ui.spinner(
                value=0,
                color=self.color,
                size=self.size,
            ).classes("animate-spin")

        return container

    def show(self):
        """Show the loading spinner."""
        if self.spinner:
            self.spinner.visible = True

    def hide(self):
        """Hide the loading spinner."""
        if self.spinner:
            self.spinner.visible = False

    def set_size(self, size: str) -> None:
        """
        Update the spinner size.

        Args:
            size: New size ('xs', 'sm', 'md', 'lg', 'xl')
        """
        self.size = size
        if self.spinner:
            self.spinner.props(f"size={size}")

    def set_color(self, color: str) -> None:
        """
        Update the spinner color.

        Args:
            color: New color
        """
        self.color = color
        if self.spinner:
            self.spinner.props(f"color={color}")