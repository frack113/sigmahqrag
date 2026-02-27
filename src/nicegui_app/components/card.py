# Card component for NiceGUI
from nicegui import ui


def card(title, content):
    """
    Create a NiceGUI card with the given title and content.
    
    Args:
        title (str): Title of the card.
        content (str): Content of the card.
    """
    with ui.card():
        ui.label(title)
        ui.label(content)