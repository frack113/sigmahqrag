"""
Chat Page Implementation

Main chat interface page that integrates all components:
- Message display area with scrolling
- Input area with send button
- File upload integration
- Real-time updates
"""

import asyncio

from nicegui import ui

# Import local components and services
from ..components.chat_message import ChatMessage
from ..components.typing_indicator import TypingIndicator
from ..models.chat_service import ChatMessage as ChatMessageData
from ..models.chat_service import ChatService
from ..models.config_service import ConfigService
from ..models.data_service import DataService


class ChatPage:
    """
    Main chat page that handles the UI and integrates with services.

    Attributes:
        chat_service: Service for managing conversation state
        data_service: Service for RAG operations
        config_service: Service for configuration management
        message_container: UI element containing all messages
        typing_indicator: Optional typing indicator element
        loading_spinner: Optional loading spinner element
        confirm_dialog: Optional confirmation dialog element
        conversation_key: Key for localStorage storage
    """

    def __init__(self):
        self.chat_service = ChatService()
        self.data_service = DataService()
        self.config_service = ConfigService()
        self.message_container = None
        self.typing_indicator = None
        self.loading_spinner = None
        self.confirm_dialog = None
        self.conversation_key = "sigmahq_chat_history"

    def render(self):
        """
        Render the complete chat interface.

        Returns:
            The root element of the chat page
        """
        # Main container with responsive layout
        main_container = ui.column().classes("w-full h-screen bg-gray-100")

        with main_container:
            # Header
            self._render_header()

            # Chat messages area - use flex to fill available space with responsive design
            self.message_container = ui.column().classes(
                "flex-1 overflow-y-auto p-4 gap-4 min-h-0"
            )

            # Input area
            self._render_input_area()

        # Load conversation from localStorage
        asyncio.create_task(self._load_conversation_from_storage())

        return main_container

    def _render_header(self):
        """
        Render the chat header with title and controls.
        """
        with (
            ui.row()
            .classes("w-full bg-white border-b px-4 py-3 items-center")
            .style("box-shadow: 0 1px 2px rgba(0,0,0,0.05)")
        ):
            ui.label("SigmaHQ Chat").classes("text-lg font-semibold text-gray-800")

            # Spacer
            ui.element("div").classes("flex-1")

            # Clear history button
            ui.button(
                icon="delete_sweep",
                on_click=self._clear_chat_history,
            ).props(
                "flat"
            ).tooltip("Clear chat history")

            # Update database button
            ui.button(
                icon="update",
                on_click=self._update_database,
                color="primary",
            ).props("flat").tooltip("Update knowledge base from GitHub repositories")

    def _render_input_area(self):
        """
        Render the input area with text box, file upload, and send button.
        """
        with (
            ui.row()
            .classes("w-full bg-white border-t px-4 py-3 gap-3")
            .style("box-shadow: 0 -1px 2px rgba(0,0,0,0.05)")
        ):

            # Text input
            text_input = (
                ui.input(
                    placeholder="Message SigmaHQ...",
                    value="",
                )
                .classes("flex-1")
                .props('input-debounce="500" clearable')
            )

            # Handle Enter key press using NiceGUI 3.x pattern
            text_input.on("keydown", self._handle_key_press)

            # Send button
            send_button = ui.button(
                icon="send",
                on_click=lambda: self._send_message(text_input.value),
                color="primary",
            ).props("flat")

        return text_input, send_button

    def _handle_key_press(self, e):
        """
        Handle key press events in the input field.

        Args:
            e: Key press event
        """
        # Check if this is an Enter key press without shift
        if (
            hasattr(e, "key")
            and e.key == "Enter"
            and not getattr(e, "shift_key", False)
        ):
            # Get the input element from the event
            input_element = e.sender
            self._send_message(input_element.value)
        elif hasattr(e, "key") and e.key == "Enter":
            # If shift is pressed, don't send message (allow new line)
            pass
        else:
            # Handle other key presses if needed
            pass

    async def _send_message(self, message_text: str):
        """
        Send a message and get assistant response with streaming.

        Args:
            message_text: The user's message text
        """
        if not message_text or message_text.strip() == "":
            return

        # Clear the text input (message_text is passed as parameter)

        try:
            # Show typing indicator
            self._show_typing_indicator()

            # Add user message to chat
            user_message = self.chat_service.add_message("user", message_text)
            self._render_message(user_message)

            # Get assistant response with streaming
            assistant_response = ""
            response_message = None

            # Create a placeholder for the assistant message
            with self.message_container:
                response_message = ui.chat_message(name="Bot", sent=False)
                spinner = ui.spinner(type="dots")

            # Get streaming response from LLM
            llm_service = self.chat_service.llm_service
            async for chunk in llm_service.generate_streaming_response(
                message_text,
            ):
                assistant_response += chunk
                if response_message:
                    with response_message.clear():
                        # Convert markdown to HTML for rendering
                        html_content = llm_service.convert_markdown_to_html(
                            assistant_response
                        )
                        ui.html(html_content, sanitize=True)
                    # Scroll to bottom after each update
                    ui.run_javascript("window.scrollTo(0, document.body.scrollHeight)")

            # Remove spinner when done
            if response_message and spinner:
                self.message_container.remove(spinner)

            # Create final assistant message
            self.chat_service.add_message("assistant", assistant_response)

        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            ui.notify(error_msg, type="negative")

            # Add error message to chat
            error_message = self.chat_service.add_message("system", error_msg)
            self._render_message(error_message)

        finally:
            # Hide typing indicator
            self._hide_typing_indicator()

    def _show_typing_indicator(self):
        """
        Show a typing indicator in the chat.
        """
        if self.typing_indicator is None:
            # Create typing indicator component
            self.typing_indicator = TypingIndicator()

            # Add to message container
            if self.message_container:
                with self.message_container:
                    self.typing_indicator.render()

    def _hide_typing_indicator(self):
        """
        Hide the typing indicator.
        """
        if self.typing_indicator is not None:
            try:
                # Hide the component instead of deleting it
                self.typing_indicator.hide()
            except Exception:
                pass  # Ignore cleanup errors

    def _render_message(
        self,
        message: ChatMessageData,
        role: str | None = None,
        document_preview: str | None = None,
    ):
        """
        Render a chat message in the UI.

        Args:
            message: The ChatMessage object to render
            role: Optional override for message role
            document_preview: Optional base64 preview image
        """
        if self.message_container is None:
            return

        # Use the specified role or get from message
        msg_role = role or message.role

        # Create and render the chat message component
        chat_msg = ChatMessage(
            role=msg_role,  # type: ignore[arg-type]
            content=message.content,
            timestamp=message.timestamp,
            document_preview=document_preview,
        )

        rendered_msg = chat_msg.render()
        # Use ui.row() to add the rendered message to the container
        with self.message_container:
            rendered_msg

        # Scroll to bottom
        self._scroll_to_bottom()

        # Save conversation to localStorage after each message
        self._save_conversation_to_storage()

    def _scroll_to_bottom(self):
        """
        Scroll the message container to show the latest messages.
        """
        if self.message_container:
            try:
                # Use NiceGUI's run_javascript to scroll to bottom
                ui.run_javascript("""
                const container = document.querySelector('.nicegui-page .overflow-y-auto');
                if (container) {
                    container.scrollTop = container.scrollHeight;
                }
                """)
            except Exception as e:
                print(f"Error scrolling: {e}")

    def _clear_chat_history(self):
        """
        Clear the chat history and update the UI.
        """
        self.chat_service.clear_history()

        # Remove all messages from container
        if self.message_container:
            # Clear all children by recreating the container
            self.message_container.clear()

        # Clear conversation from localStorage
        self._clear_conversation_from_storage()

    async def _update_database(self):
        """
        Update the knowledge base by indexing enabled GitHub repositories.
        Shows progress notification and runs the update process in the background.
        """
        # Create a persistent notification for progress updates
        self.progress_notification = ui.notification(timeout=None)
        
        # Start the background update process
        asyncio.create_task(self._update_database_with_progress())

    async def _update_database_with_progress(self):
        """
        Background task to update the knowledge base with progress notifications.
        """
        try:
            # Step 1: Load configuration
            self.progress_notification.message = "Loading configuration..."
            self.progress_notification.spinner = True
            
            config_service = ConfigService()
            repo_config = config_service.get_repositories()

            # Convert RepositoryConfig objects to dict format
            repo_dict = {
                "repositories": [
                    {
                        "url": repo.url,
                        "branch": repo.branch,
                        "enabled": repo.enabled,
                        "file_extensions": repo.file_extensions,
                    }
                    for repo in repo_config
                ]
            }

            enabled_repos = [repo for repo in repo_config if repo.enabled]
            
            if not enabled_repos:
                self.progress_notification.message = "No enabled repositories found in configuration."
                self.progress_notification.spinner = False
                await asyncio.sleep(2)
                self.progress_notification.dismiss()
                return

            # Step 2: Clone repositories (Step 1/2)
            self.progress_notification.message = f"Step 1/2: Updating {len(enabled_repos)} repositories..."
            self.progress_notification.spinner = True
            
            # Run clone operation in thread pool
            import concurrent.futures
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                clone_result = await loop.run_in_executor(
                    executor, 
                    self.data_service.clone_enabled_repositories, 
                    repo_dict
                )
            
            if not clone_result:
                self.progress_notification.message = "Failed to update repositories. Please check the configuration."
                self.progress_notification.spinner = False
                await asyncio.sleep(3)
                self.progress_notification.dismiss()
                return
            
            # Step 3: Index repositories (Step 2/2)
            self.progress_notification.message = "Step 2/2: Indexing repository content..."
            self.progress_notification.spinner = True
            
            # Run indexing operation in thread pool
            with concurrent.futures.ThreadPoolExecutor() as executor:
                index_result = await loop.run_in_executor(
                    executor, 
                    self.data_service.index_enabled_repositories, 
                    repo_dict
                )
            
            if index_result:
                # Get context stats for detailed feedback
                stats = self.data_service.get_context_stats()
                total_docs = stats.get('total_documents', 0)
                self.progress_notification.message = (
                    f"✅ Knowledge base updated successfully! "
                    f"Indexed {total_docs} documents from {len(enabled_repos)} repositories."
                )
                self.progress_notification.spinner = False
                await asyncio.sleep(3)
                self.progress_notification.dismiss()
            else:
                self.progress_notification.message = "No repositories were indexed. Please check the configuration."
                self.progress_notification.spinner = False
                await asyncio.sleep(3)
                self.progress_notification.dismiss()

        except Exception as e:
            error_msg = f"Error updating knowledge base: {str(e)}"
            self.progress_notification.message = error_msg
            self.progress_notification.spinner = False
            await asyncio.sleep(3)
            self.progress_notification.dismiss()

    def load_initial_messages(
        self, initial_messages: list[ChatMessageData] | None = None
    ):
        """
        Load initial messages into the chat (e.g., welcome message).

        Args:
            initial_messages: List of ChatMessage objects to display initially
        """
        if not initial_messages:
            # Add a default welcome message
            welcome_msg = self.chat_service.add_message(
                "assistant",
                "Hello! I'm your SigmaHQ AI assistant. You can upload documents (PDF, TXT, DOCX, images) and ask questions about their content.",
            )
            initial_messages = [welcome_msg]

        # Render each message
        for msg in initial_messages:
            self._render_message(msg)

    def _save_conversation_to_storage(self):
        """
        Save the current conversation to localStorage using JavaScript.
        """
        try:
            import json

            conversation_data = self.chat_service.export_conversation()
            json_data = json.dumps(conversation_data)

            # Use JavaScript to save to localStorage
            ui.run_javascript(f"""
                if (typeof(Storage) !== 'undefined') {{
                    localStorage.setItem('{self.conversation_key}', '{json_data}');
                }}
            """)
        except Exception as e:
            print(f"Error saving conversation to storage: {e}")

    async def _load_conversation_from_storage(self):
        """
        Load conversation from localStorage using JavaScript.
        """
        try:
            # Use JavaScript to get from localStorage
            result = await ui.run_javascript(f"""
                if (typeof(Storage) !== 'undefined') {{
                    const data = localStorage.getItem('{self.conversation_key}');
                    return data || null;
                }}
                return null;
            """)

            import json

            if result and result != "null":
                conversation_data = json.loads(result)
                self.chat_service = ChatService.import_conversation(conversation_data)

                # Re-render all messages from the loaded conversation
                # Use ui.timer to ensure we're in the correct context
                def render_messages():
                    for msg in self.chat_service.get_message_history():
                        self._render_message(msg)
                
                # Schedule rendering in the main UI thread
                ui.timer(0.1, render_messages, once=True)
        except Exception as e:
            print(f"Error loading conversation from storage: {e}")

    def _clear_conversation_from_storage(self):
        """
        Clear the conversation from localStorage using JavaScript.
        """
        try:
            ui.run_javascript(f"""
                if (typeof(Storage) !== 'undefined') {{
                    localStorage.removeItem('{self.conversation_key}');
                }}
            """)
        except Exception as e:
            print(f"Error clearing conversation from storage: {e}")

    def get_chat_state(self):
        """
        Get the current state of the chat.

        Returns:
            Dictionary containing chat state information
        """
        return {
            "message_count": len(self.chat_service.message_history),
            "context_stats": self.data_service.get_context_stats(),
        }
