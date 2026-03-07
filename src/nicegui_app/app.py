# NiceGUI Application
from nicegui import ui
from .pages.chat_page import ChatPage
from .pages.github_repo_page import initialize_page


def chat_page():
    """
    Create the chat page for document analysis.
    """
    # Main container with padding
    with ui.column().classes("w-full h-screen p-4"):
        chat = ChatPage()

        # Navigation links in chat page
        with ui.row().classes("mb-4"):
            with ui.row().classes("ml-2"):
                ui.icon("github").classes("mr-1")
                ui.link("GitHub Repository Management", "/github-repo").classes(
                    "no-underline"
                )

        return chat.render()


def create_nicegui_app():
    """Create and run the NiceGUI application."""

    # Make chat page the default landing page
    @ui.page("/", title="Sigma RAG")
    def chat_route():
        return chat_page()

    # GitHub repository management route
    @ui.page("/github-repo", title="GitHub Repositories Manage")
    def github_repo_route():
        initialize_page()

    # Create and run the NiceGUI application with port 8000
    ui.run(port=8000)


if __name__ in {"__main__", "__mp_main__"}:
    create_nicegui_app()
