"""
Typing Indicator Component

A component that displays a typing animation to indicate when the assistant
is generating a response.
"""

from nicegui import ui
from typing import Optional


class TypingIndicator:
    """
    A typing indicator component with animated dots.
    
    Features:
    - Animated dots to simulate typing
    - Configurable dot count and animation speed
    - Easy show/hide control
    """
    
    def __init__(self, dot_count: int = 3, animation_speed: str = "1s"):
        """
        Initialize the typing indicator.
        
        Args:
            dot_count: Number of dots in the animation (default: 3)
            animation_speed: CSS animation duration (default: "1s")
        """
        self.dot_count = dot_count
        self.animation_speed = animation_speed
        self.dots = []
        
        self._create_indicator()
    
    def _create_indicator(self):
        """Create the typing indicator UI."""
        with ui.row().classes("items-center gap-2 py-2 px-4 bg-gray-100 rounded-lg border hidden") as container:
            self.container = container
            # Create animated dots
            for i in range(self.dot_count):
                dot = ui.label("•").classes(
                    f"text-gray-500 text-2xl animate-bounce"
                )
                # Add delay to create cascading effect
                dot.style(f"animation-delay: {i * 0.15}s; animation-duration: {self.animation_speed}")
                self.dots.append(dot)
    
    def show(self):
        """Show the typing indicator."""
        if self.container:
            self.container.classes(remove="hidden")
    
    def hide(self):
        """Hide the typing indicator."""
        if self.container:
            self.container.classes(add="hidden")
    
    def set_animation_speed(self, speed: str):
        """
        Set the animation speed.
        
        Args:
            speed: CSS animation duration (e.g., "0.5s", "1s", "2s")
        """
        self.animation_speed = speed
        # Update all dot animations
        for dot in self.dots:
            dot.style(f"animation-duration: {speed}")


def create_typing_indicator(dot_count: int = 3, animation_speed: str = "1s"):
    """
    Factory function to create a typing indicator.
    
    Args:
        dot_count: Number of dots in the animation
        animation_speed: CSS animation duration
        
    Returns:
        TypingIndicator instance
    """
    return TypingIndicator(dot_count, animation_speed)