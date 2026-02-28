"""
Chat Page Implementation

Main chat interface page that integrates all components:
- Message display area with scrolling
- Input area with send button
- File upload integration
- Real-time updates
"""
from nicegui import ui, events
from typing import Optional, List
import asyncio
from datetime import datetime

# Import local components and services
from ..components.chat_message import ChatMessage
from ..components.file_upload import FileUpload
from ..models.chat_service import ChatService, ChatMessage as ChatMessageData
from ..models.data_service import DataService


class ChatPage:
    """
    Main chat page that handles the UI and integrates with services.
    
    Attributes:
        chat_service: Service for managing conversation state
        data_service: Service for RAG operations
        message_container: UI element containing all messages
        typing_indicator: Optional typing indicator element
    """
    
    def __init__(self):
        self.chat_service = ChatService()
        self.data_service = DataService()
        self.message_container = None
        self.typing_indicator = None
        self.file_upload_component = None
        
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
            
            # Chat messages area
            self.message_container = ui.column().classes("flex-1 overflow-y-auto p-4 gap-3")
            
            # File upload component
            self.file_upload_component = FileUpload(
                on_upload=self._handle_file_upload,
                on_error=self._handle_upload_error
            )
            
            # Input area
            self._render_input_area()
        
        return main_container
    
    def _render_header(self):
        """
        Render the chat header with title and controls.
        """
        with ui.row().classes("w-full bg-white border-b px-4 py-3 items-center").style("box-shadow: 0 2px 4px rgba(0,0,0,0.1)"):
            ui.label("SigmaHQ Multi-Modal Chat").classes("text-xl font-semibold text-gray-800")
            
            # Spacer
            ui.element('div').classes('flex-1')
            
            # Clear history button
            ui.button(
                icon='delete_sweep',
                on_click=self._clear_chat_history
            ).tooltip('Clear chat history').props('size=sm')
    
    def _render_input_area(self):
        """
        Render the input area with text box, file upload, and send button.
        """
        with ui.row().classes("w-full bg-white border-t p-4 gap-2").style("box-shadow: 0 -2px 4px rgba(0,0,0,0.1)"):
            # File upload component
            self.file_upload_component.render()
            
            # Text input
            text_input = ui.input(
                placeholder="Type your message here..."
            ).classes("flex-1").props('input-debounce="500" onKeyPress="() => $handle_key_press()"')
            
            # Send button
            send_button = ui.button(
                icon='send',
                on_click=lambda: self._send_message(text_input.value)
            ).classes("bg-blue-600 text-white hover:bg-blue-700")
        
        return text_input, send_button
    
    def _handle_key_press(self, e):
        """
        Handle key press events in the input field.
        
        Args:
            e: Key press event
        """
        if e.key == 'Enter' and not e.shift_key:
            # Get the input element from the event
            input_element = e.sender
            self._send_message(input_element.value)
    
    def _handle_file_upload(self, file_paths: List[str]):
        """
        Handle successful file uploads.
        
        Args:
            file_paths: List of paths to uploaded files
        """
        ui.notify(f"Uploaded {len(file_paths)} file(s)")
        
        # Process each file and add to chat
        for file_path in file_paths:
            try:
                # Add user message with document reference
                user_msg = self.chat_service.add_message(
                    'user', f"Uploaded: {file_path}",
                    document_path=file_path
                )
                
                # Process the document and get preview
                doc_content, preview = asyncio.run(self.chat_service.process_document(file_path))
                
                # Update message with document content info
                user_msg.content = f"Uploaded: {file_path}\n\nDocument contains {len(doc_content.split()):,} words"
                
                # Render the message with preview
                self._render_message(user_msg, document_preview=preview)
                
                # Store context for RAG
                doc_id = f"doc_{datetime.now().timestamp()}"
                self.data_service.store_context(doc_id, doc_content, {
                    'filename': file_path.split('/')[-1],
                    'upload_time': datetime.now().isoformat(),
                    'word_count': len(doc_content.split())
                })
                
            except Exception as e:
                self._handle_upload_error(str(e))
    
    def _handle_upload_error(self, error: str):
        """
        Handle upload errors with user notification.
        
        Args:
            error: Error message
        """
        ui.notify(error, type='negative')
    
    async def _send_message(self, message_text: str):
        """
        Send a message and get assistant response.
        
        Args:
            message_text: The user's message text
        """
        if not message_text or message_text.strip() == "":
            return
        
        # Clear the text input (message_text is passed as parameter)
        
        try:
            # Show typing indicator
            self._show_typing_indicator()
            
            # Process the chat turn (user input + any uploaded files)
            user_message, assistant_message = await self.chat_service.process_chat_turn(
                message_text,
                file_paths=self.file_upload_component.uploaded_files if hasattr(self.file_upload_component, 'uploaded_files') else None
            )
            
            # Clear uploaded files after processing
            if hasattr(self.file_upload_component, 'clear_uploads'):
                self.file_upload_component.clear_uploads()
            
            # Render messages
            self._render_message(user_message)
            self._render_message(assistant_message, role='assistant')
            
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            ui.notify(error_msg, type='negative')
            
            # Add error message to chat
            error_message = self.chat_service.add_message('system', error_msg)
            self._render_message(error_message)
            
        finally:
            # Hide typing indicator
            self._hide_typing_indicator()
    
    def _show_typing_indicator(self):
        """
        Show a typing indicator in the chat.
        """
        if self.typing_indicator is None:
            # Create typing indicator
            self.typing_indicator = ui.html('<div class="typing-indicator">...</div>')
            
            # Add to message container
            if hasattr(self.message_container, 'children'):
                self.message_container.children.append(self.typing_indicator)
    
    def _hide_typing_indicator(self):
        """
        Hide the typing indicator.
        """
        if self.typing_indicator is not None:
            try:
                self.typing_indicator.delete()
                self.typing_indicator = None
            except Exception:
                pass  # Ignore cleanup errors
    
    def _render_message(
        self,
        message: ChatMessageData,
        role: Optional[str] = None,
        document_preview: Optional[str] = None
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
            role=msg_role,
            content=message.content,
            timestamp=message.timestamp,
            document_preview=document_preview
        )
        
        rendered_msg = chat_msg.render()
        self.message_container.append(rendered_msg)
        
        # Scroll to bottom
        self._scroll_to_bottom()
    
    def _scroll_to_bottom(self):
        """
        Scroll the message container to show the latest messages.
        """
        if self.message_container:
            try:
                # Force scroll to bottom using JavaScript
                js_code = """
                var element = document.querySelector('.nicegui-page .overflow-y-auto');
                if (element) {
                    element.scrollTop = element.scrollHeight;
                }
                """
                ui.run_javascript(js_code)
            except Exception as e:
                print(f"Error scrolling: {e}")
    
    def _clear_chat_history(self):
        """
        Clear the chat history and update the UI.
        """
        self.chat_service.clear_history()
        
        # Remove all messages from container
        if self.message_container:
            for child in list(self.message_container.children):
                try:
                    child.delete()
                except Exception:
                    pass
    
    def load_initial_messages(self, initial_messages: Optional[List[ChatMessageData]] = None):
        """
        Load initial messages into the chat (e.g., welcome message).
        
        Args:
            initial_messages: List of ChatMessage objects to display initially
        """
        if not initial_messages:
            # Add a default welcome message
            welcome_msg = self.chat_service.add_message(
                'assistant',
                "Hello! I'm your SigmaHQ AI assistant. You can upload documents (PDF, TXT, DOCX, images) and ask questions about their content."
            )
            initial_messages = [welcome_msg]
        
        # Render each message
        for msg in initial_messages:
            self._render_message(msg)
    
    def get_chat_state(self):
        """
        Get the current state of the chat.
        
        Returns:
            Dictionary containing chat state information
        """
        return {
            'message_count': len(self.chat_service.message_history),
            'context_stats': self.data_service.get_context_stats()
        }
