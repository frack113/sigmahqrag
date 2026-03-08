# NiceGUI Application
from nicegui import ui

from .pages.chat_page import ChatPage
from .pages.data_page import DataPage
from .pages.github_repo_page import initialize_page


def create_nicegui_app():
    """Create and run the NiceGUI application."""

    def root():
        pages = ui.sub_pages().classes('w-full h-full')
        ui.separator()
        
        # Header with navigation buttons
        with ui.header().classes('items-center bg-blue-100'):
            ui.button('Chat', on_click=lambda: ui.navigate.to('/')).props('flat')
            ui.button('Data', on_click=lambda: ui.navigate.to('/data')).props('flat')
            ui.button('GitHub', on_click=lambda: ui.navigate.to('/github')).props('flat')
            ui.button('Files', on_click=lambda: ui.navigate.to('/files')).props('flat')
            ui.button('Config', on_click=lambda: ui.navigate.to('/config')).props('flat')
            ui.button('Logs', on_click=lambda: ui.navigate.to('/logs')).props('flat')
            ui.space()
            ui.button('Logout', icon='logout').props('flat')

        # Add pages to sub-pages
        pages.add('/', lambda: chat_page())
        pages.add('/data', lambda: data_page())
        pages.add('/github', lambda: github_page())
        pages.add('/files', lambda: files_page())
        pages.add('/config', lambda: config_page())
        pages.add('/logs', lambda: logs_page())

    def chat_page():
        """Chat page - main functionality"""
        with ui.column().classes("w-full h-screen p-4"):
            chat = ChatPage()
            chat.render()

    def data_page():
        """Data management and database information"""
        with ui.column().classes("w-full h-screen p-4"):
            ui.markdown('''
                ### Database Management 📊
                
                This page displays database statistics and repository status.
            ''')
            data = DataPage()
            data.render()

    def github_page():
        """GitHub repository management"""
        with ui.column().classes("w-full h-screen p-4"):
            ui.markdown('''
                ### GitHub Repository Management 📁
                
                This page allows you to manage GitHub repositories for document analysis.
            ''')
            initialize_page()

    def files_page():
        """Local files management (WIP)"""
        with ui.column().classes("w-full h-screen bg-gray-100"):
            # Header
            with ui.row().classes("w-full bg-white border-b px-4 py-3 items-center"):
                ui.label("Local Files Management").classes("text-lg font-semibold text-gray-800")
                ui.element("div").classes("flex-1")

            # Main content area - use flex to fill available space
            with ui.column().classes("w-full p-4 gap-4 flex-1"):
                ui.markdown('''
                    ### Local Files Management 📂
                    
                    **Work in Progress**
                    
                    This page will allow you to upload and manage local files for analysis.
                ''')

    def config_page():
        """Configuration settings (WIP)"""
        with ui.column().classes("w-full h-screen bg-gray-100"):
            # Header
            with ui.row().classes("w-full bg-white border-b px-4 py-3 items-center"):
                ui.label("Configuration Settings").classes("text-lg font-semibold text-gray-800")
                ui.element("div").classes("flex-1")

            # Main content area - use flex to fill available space
            with ui.column().classes("w-full p-4 gap-4 flex-1"):
                ui.markdown('''
                    ### Configuration Settings ⚙️
                    
                    **Work in Progress**
                    
                    This page will allow you to configure application settings.
                ''')

    def logs_page():
        """Logs viewer (WIP)"""
        with ui.column().classes("w-full h-screen bg-gray-100"):
            # Header
            with ui.row().classes("w-full bg-white border-b px-4 py-3 items-center"):
                ui.label("Logs Viewer").classes("text-lg font-semibold text-gray-800")
                ui.element("div").classes("flex-1")

            # Main content area - use flex to fill available space
            with ui.column().classes("w-full p-4 gap-4 flex-1"):
                ui.markdown('''
                    ### Logs Viewer 📋
                    
                    **Work in Progress**
                    
                    This page will display application logs and system information.
                ''')

    # Create and run the NiceGUI application with port 8000
    ui.run(root, port=8000, storage_secret='demo_secret_key_change_in_production')


if __name__ in {"__main__", "__mp_main__"}:
    create_nicegui_app()
