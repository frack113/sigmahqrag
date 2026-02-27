# NiceGUI Application
from nicegui import ui
from .components.card import card
from .components.notification import notify


def dashboard_page():
    """
    Create the dashboard page with cards and notifications.
    """
    # Add a card to the dashboard
    card("Welcome", "This is the NiceGUI dashboard.")
    
    # Button to trigger a notification
    with ui.row():
        ui.button("Show Notification", on_click=lambda: notify("Info", "This is a test notification."))


def create_nicegui_app():
    """Create and run the NiceGUI application."""
    dashboard_page()
    return ui.run(title="Sigma Dashboard", port=8000)


if __name__ in {"__main__", "__mp_main__"}:
    create_nicegui_app()