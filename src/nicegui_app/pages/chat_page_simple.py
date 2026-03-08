"""
Simplified Chat Page - Clean and Minimal

A simplified chat interface inspired by the provided example.
Uses OpenAI-compatible LLM service for chat responses.
"""

from nicegui import ui
from src.nicegui_app.models.llm_service import LLMService
from src.nicegui_app.models.llm_service import ChatMessage, ChatCompletionRequest


class SimpleChatPage:
    """
    A simplified chat page with clean, minimal interface.

    Features:
    - Simple input field and send button
    - Clean message display
    - Typing indicator
    - OpenAI-compatible LLM service integration
    """

    def __init__(self):
        # Configure LLM service
        self.llm_service = LLMService(
            model_name="mistralai/ministral-3-14b-reasoning",
            base_url="http://localhost:1234",
            temperature=0.7,
            max_tokens=512,
            api_key="lm-studio",
            enable_streaming=True,
        )
        self.is_processing = False
        self.messages = []

    def render(self):
        """
        Render the simplified chat interface.

        Returns:
            The root element of the chat page
        """
        # Main container with responsive layout
        main_container = ui.column().classes("w-full h-[70vh] bg-gray-100")

        with main_container:
            # Header
            with (
                ui.row()
                .classes("w-full bg-white border-b px-4 py-3 items-center")
                .style("box-shadow: 0 1px 2px rgba(0,0,0,0.05)")
            ):
                ui.label("Chat").classes("text-lg font-semibold text-gray-800")
                ui.space()
                ui.button(
                    icon="delete_sweep",
                    on_click=self.clear_chat,
                ).props(
                    "flat"
                ).tooltip("Clear chat history")

            # Chat messages area
            self.messages_container = ui.column().classes(
                "flex-1 overflow-y-auto p-4 gap-4 min-h-0"
            )

            # Input area
            with (
                ui.row()
                .classes("w-full bg-white border-t px-4 py-3 gap-3")
                .style("box-shadow: 0 -1px 2px rgba(0,0,0,0.05)")
            ):
                # Text input
                self.text_input = (
                    ui.input(
                        placeholder="Message Chat...",
                        value="",
                    )
                    .classes("flex-1")
                    .props('input-debounce="500" clearable')
                )

                # Send button
                ui.button(
                    icon="send",
                    on_click=self.send_message,
                    color="primary",
                ).props("flat")

        # Load initial messages
        self.load_messages()

        return main_container

    def load_messages(self):
        """Load and display existing messages."""
        self.messages_container.clear()
        self.messages = []

        # Add welcome message
        self.add_message("assistant", "Hello! How can I help you today?")

    def add_message(self, role: str, content: str):
        """Add a message to the chat."""
        self.messages.append({"role": role, "content": content})

        with self.messages_container:
            if role == "user":
                # User message - right aligned
                with ui.row().classes("w-full justify-end"):
                    with ui.card().classes(
                        "bg-blue-500 text-white px-4 py-2 rounded-lg max-w-md"
                    ):
                        ui.html(content).classes("whitespace-pre-wrap")
            else:
                # Assistant message - left aligned
                with ui.row().classes("w-full justify-start"):
                    with ui.card().classes(
                        "bg-gray-100 text-gray-800 px-4 py-2 rounded-lg max-w-md"
                    ):
                        ui.html(content).classes("whitespace-pre-wrap")

        # Scroll to bottom after a short delay
        ui.timer(0.1, self.scroll_to_bottom, once=True)

    def display_message(self, role: str, content: str):
        """Display a single message in the chat."""
        self.add_message(role, content)

    def send_message(self):
        """Send a message and handle the response."""
        message_text = self.text_input.value.strip()
        if not message_text:
            return

        # Store message text before clearing input
        user_message = message_text

        # Clear input
        self.text_input.value = ""

        # Display user message
        self.display_message("user", user_message)

        # Send and get response
        if not self.is_processing:
            self.is_processing = True
            ui.timer(0.1, lambda: self.get_response(user_message), once=True)

    async def get_response(self, user_message: str):
        """Get response from OpenAI-compatible LLM service with streaming."""
        stream_response = None
        typing_indicator = None
        try:
            # Show typing indicator
            typing_indicator = ui.spinner().classes("mx-auto my-2")

            # Build conversation history
            conversation_messages = []
            
            # Add conversation history (skip the first assistant message which is the welcome message)
            for msg in self.messages:
                # Skip the initial welcome message to avoid duplicate system messages
                if msg["role"] == "assistant" and "Hello!" in msg["content"] and len(self.messages) > 1:
                    continue
                conversation_messages.append(
                    ChatMessage(role=msg["role"], content=msg["content"])
                )

            # Add current user message
            conversation_messages.append(ChatMessage(role="user", content=user_message))

            # Create chat completion request
            request = ChatCompletionRequest(
                messages=conversation_messages,
                model=self.llm_service.model_name,
                temperature=self.llm_service.temperature,
                max_tokens=self.llm_service.max_tokens,
                stream=True,
            )

            # Get streaming response from LLM service
            response_text = ""
            chunks_received = 0

            # Get the streaming response
            stream_response = await self.llm_service.create_chat_completion(request)

            # Process streaming response
            if hasattr(stream_response, "__aiter__"):
                # Add a placeholder assistant message first
                self.add_message("assistant", "")
                # Get the last message element for direct updates
                last_message_index = len(self.messages) - 1
                
                async for chunk in stream_response:
                    if hasattr(chunk, "choices") and chunk.choices:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, "content") and delta.content:
                            content_chunk = delta.content
                            if content_chunk and content_chunk.strip():
                                chunks_received += 1
                                response_text += content_chunk
                                
                                # Update the message content directly
                                self.messages[last_message_index]["content"] = response_text
                                
                                # Update the UI by clearing and rebuilding only the last message
                                self.messages_container.clear()
                                # Only keep last 5 messages in UI to prevent DOM buildup
                                recent_ui_messages = self.messages[-5:] if len(self.messages) > 5 else self.messages
                                for msg in recent_ui_messages:
                                    self.add_message(msg["role"], msg["content"])

            # If no chunks were received, try non-streaming response
            if chunks_received == 0:
                request.stream = False
                response = await self.llm_service.create_chat_completion(request)
                if hasattr(response, "choices") and response.choices:
                    response_text = response.choices[0].message.content
                    # Remove the typing indicator
                    if typing_indicator:
                        typing_indicator.delete()
                        typing_indicator = None
                    
                    # Add the complete response
                    self.add_message("assistant", response_text)
                    return

            # Hide typing indicator
            if typing_indicator:
                typing_indicator.delete()
                typing_indicator = None

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.display_message("assistant", error_msg)

        finally:
            # Aggressive cleanup to prevent memory leaks
            if stream_response and hasattr(stream_response, 'close'):
                try:
                    stream_response.close()
                except Exception:
                    pass
            
            if typing_indicator:
                try:
                    typing_indicator.delete()
                except Exception:
                    pass
            
            self.is_processing = False
            self.scroll_to_bottom()
            
            # Periodic cleanup of old messages to prevent memory buildup
            if len(self.messages) > 20:
                # Keep only the last 10 messages
                self.messages = self.messages[-10:]
                # Clear and rebuild UI with recent messages
                self.messages_container.clear()
                for msg in self.messages:
                    self.add_message(msg["role"], msg["content"])

    def clear_chat(self):
        """Clear the chat history."""
        self.messages_container.clear()
        self.messages = []
        self.add_message("assistant", "Chat cleared. Hello! How can I help you today?")

    def scroll_to_bottom(self):
        """Scroll to the bottom of the messages container."""
        ui.run_javascript("""
            const container = document.querySelector('.nicegui-page .overflow-y-auto');
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        """)

    def cleanup(self):
        """Clean up resources and free memory."""
        if self.llm_service:
            self.llm_service.cleanup()
        # Clear message history to free memory
        self.messages.clear()
        # Clear the UI container
        if hasattr(self, 'messages_container'):
            self.messages_container.clear()


def create_chat_page():
    """Create and return the simplified chat page."""
    chat = SimpleChatPage()
    return chat.render()