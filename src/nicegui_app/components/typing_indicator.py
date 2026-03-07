"""
Typing Indicator Component

Simplified typing indicator component for NiceGUI 3.x compatibility.
Uses built-in NiceGUI elements with CSS animations.
"""

from nicegui import ui


class TypingIndicator:
    """
    A component that displays an animated typing indicator.

    Attributes:
        container: The UI container element
        visible: Boolean indicating if the indicator is visible
    """

    def __init__(self):
        """Initialize the typing indicator component."""
        self.container = None
        self.visible = False

    def render(self):
        """
        Render the typing indicator with animated dots.

        Returns:
            The typing indicator element
        """
        # Create container using NiceGUI's row component
        self.container = ui.row().classes("items-center gap-2 py-2")

        with self.container:
            # Create three animated dots using NiceGUI's element
            self.dot1 = ui.element("div").classes(
                "w-2 h-2 bg-gray-400 rounded-full"
            )
            self.dot2 = ui.element("div").classes(
                "w-2 h-2 bg-gray-400 rounded-full"
            )
            self.dot3 = ui.element("div").classes(
                "w-2 h-2 bg-gray-400 rounded-full"
            )

        # Add CSS animations using style method
        self._apply_animations()
        
        # Set initial visibility
        self.container.visible = self.visible
        
        return self.container

    def _apply_animations(self):
        """Apply CSS animations to the dots."""
        if self.container:
            # Use CSS-in-JS style for animations
            self.container.style("""
                .w-2.h-2.bg-gray-400.rounded-full:nth-child(1) {
                    animation: typing-bounce 1.4s ease-in-out infinite;
                    animation-delay: 0s;
                }
                .w-2.h-2.bg-gray-400.rounded-full:nth-child(2) {
                    animation: typing-bounce 1.4s ease-in-out infinite;
                    animation-delay: 0.2s;
                }
                .w-2.h-2.bg-gray-400.rounded-full:nth-child(3) {
                    animation: typing-bounce 1.4s ease-in-out infinite;
                    animation-delay: 0.4s;
                }
                @keyframes typing-bounce {
                    0%, 80%, 100% { transform: scale(0); }
                    40% { transform: scale(1.0); }
                }
            """)

    def show(self):
        """Show the typing indicator."""
        self.visible = True
        if self.container:
            self.container.visible = True

    def hide(self):
        """Hide the typing indicator."""
        self.visible = False
        if self.container:
            self.container.visible = False
