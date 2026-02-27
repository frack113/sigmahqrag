# Notification component for NiceGUI
from nicegui import ui, app


def notify(title, content):
    """
    Display a notification with the given title and content.
    
    Args:
        title (str): Title of the notification.
        content (str): Content of the notification.
    """
    async def _notify():
        ui.notify(title, content)

    asyncio.create_task(_notify())