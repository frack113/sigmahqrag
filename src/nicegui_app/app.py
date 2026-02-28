# NiceGUI Application
from nicegui import ui
from .components.card import card
from .components.notification import notify
from .pages.chat_page import ChatPage
from .pages.github_repo_page import initialize_page


def dashboard_page():
    """
    Create the dashboard page with cards and notifications.
    """
    # Add a card to the dashboard
    card("Welcome", "This is the NiceGUI dashboard.")
    
    # Button to trigger a notification
    with ui.row():
        ui.button("Show Notification", on_click=lambda: notify("Info", "This is a test notification."))
    
    # Navigation links
    with ui.row().classes('mt-4'):
        ui.link('Go to Dashboard', '/dashboard')
        with ui.row().classes("ml-2"):
            ui.icon("github").classes("mr-1")
            ui.link('GitHub Repository Management', '/github-repo').classes("no-underline")


def chat_page():
    """
    Create the chat page for document analysis.
    """
    chat = ChatPage()
    return chat.render()


def create_nicegui_app():
    """Create and run the NiceGUI application."""
    # Create the FastAPI app by calling ui.run()
    app = ui.run(title="Sigma Dashboard", port=8000)
    
    # Add routes for different pages
    # Make chat page the default landing page
    @ui.page("/")
    def chat_route():
        return chat_page()
    
    # Dashboard route
    @ui.page("/dashboard")
    def dashboard_route():
        return dashboard_page()

    # GitHub repository management route
    @ui.page("/github-repo")
    def github_repo_route():
        initialize_page()


if __name__ in {"__main__", "__mp_main__"}:
    create_nicegui_app()