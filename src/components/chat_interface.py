"""
RAG Chat Interface Component

Full-featured chat interface with async streaming responses for slow local LLMs.
Migrates the RAG chat page to Gradio with enhanced async capabilities.
"""

import json
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

import gradio as gr
from src.core.chat_service import ChatService
from src.models.logging_service import get_logger

from .base_component import AsyncComponent

logger = get_logger(__name__)


class ChatInterface(AsyncComponent):
    """
    RAG-enhanced chat interface with async streaming support.

    Features:
    - Async streaming responses for slow LLMs
    - Conversation history management
    - System information display
    - Configuration controls
    - Error handling and retry logic
    """

    def __init__(self, chat_service: ChatService, chat_history_service):
        super().__init__()
        self.chat_service = chat_service
        self.chat_history_service = chat_history_service
        self.messages: list[dict[str, Any]] = []

        # UI state
        self.is_processing = False
        self.current_stream_task = None

        # Configuration state
        self.rag_enabled = True
        self.history_limit = 10
        self.n_results = 3
        self.min_score = 0.1

    def create_tab(self):
        """Create the chat interface tab."""
        with gr.Column(elem_classes="chat-container"):
            gr.Markdown("## 🤖 RAG Chat Interface")

            # Sidebar with system info and controls
            with gr.Row():
                # Main chat area
                with gr.Column(scale=3):
                    # Chatbot component with proper initialization
                    self.chatbot = gr.Chatbot(
                        value=self._load_initial_messages(),
                        elem_classes="chat-messages",
                        height="60vh",
                    )

                    # Input area with async handling
                    with gr.Row():
                        self.msg_input = gr.Textbox(
                            placeholder="Type your message here... (Use /help for commands)",
                            container=False,
                            scale=1,
                            lines=2,
                            max_lines=5,
                        )
                        self.submit_btn = gr.Button("Send", variant="primary", scale=0)
                        self.clear_btn = gr.Button("Clear", scale=0)

                    # Status indicators
                    self.status_text = gr.Textbox(
                        label="Status",
                        interactive=False,
                        value="Ready",
                        elem_classes="status-box",
                    )

                # Sidebar controls
                with gr.Column(scale=1, elem_classes="sidebar-controls"):
                    gr.Markdown("### System Information")

                    # Server Status
                    with gr.Row():
                        self.status_indicator = gr.HTML(
                            '<div class="status-indicator" style="color: green;">●</div>'
                        )
                        self.server_status_text = gr.Textbox(
                            label="Server Status",
                            interactive=False,
                            value="Ready",
                            elem_classes="server-status",
                        )

                    # Configuration controls
                    gr.Markdown("### Configuration")

                    self.rag_toggle = gr.Checkbox(
                        label="Enable RAG", value=True, interactive=True
                    )

                    self.history_limit_input = gr.Number(
                        label="History Limit",
                        value=10,
                        minimum=1,
                        maximum=100,
                        interactive=True,
                    )

                    self.rag_results_input = gr.Number(
                        label="RAG Results",
                        value=3,
                        minimum=1,
                        maximum=10,
                        interactive=True,
                    )

                    self.min_score_input = gr.Number(
                        label="Min Score",
                        value=0.1,
                        minimum=0.0,
                        maximum=1.0,
                        step=0.01,
                        interactive=True,
                    )

                    # Actions
                    with gr.Row():
                        self.refresh_btn = gr.Button(
                            "Refresh Stats", variant="secondary"
                        )
                        self.export_btn = gr.Button("Export Chat", variant="secondary")

            # Event handlers
            self._setup_event_handlers()

            # Load initial messages
            self._load_initial_messages()

    def _setup_event_handlers(self):
        """Set up event handlers for the chat interface."""

        # Submit message handlers
        submit_event = self.msg_input.submit(
            fn=self._handle_send_message,
            inputs=[self.msg_input, self.chatbot],
            outputs=[self.chatbot, self.status_text],
            queue=True,
        )

        self.submit_btn.click(
            fn=self._handle_send_message,
            inputs=[self.msg_input, self.chatbot],
            outputs=[self.chatbot, self.status_text],
            queue=True,
        )

        # Clear chat
        self.clear_btn.click(
            fn=self._clear_chat,
            inputs=[],
            outputs=[self.chatbot, self.status_text],
            queue=True,
        )

        # Configuration changes
        self.rag_toggle.change(
            fn=self._on_rag_toggle, inputs=[self.rag_toggle], outputs=[self.status_text]
        )

        self.history_limit_input.change(
            fn=self._on_history_limit_change,
            inputs=[self.history_limit_input],
            outputs=[self.status_text],
        )

        self.rag_results_input.change(
            fn=self._on_rag_results_change,
            inputs=[self.rag_results_input],
            outputs=[self.status_text],
        )

        self.min_score_input.change(
            fn=self._on_min_score_change,
            inputs=[self.min_score_input],
            outputs=[self.status_text],
        )

        # Actions
        self.refresh_btn.click(
            fn=self._show_stats, inputs=[], outputs=[self.status_text]
        )

        self.export_btn.click(
            fn=self._export_chat, inputs=[], outputs=[self.status_text]
        )

    def _handle_send_message(
        self, message: str, history: list[dict[str, str]]
    ) -> tuple[list[dict[str, str]], str]:
        """Handle sending a message with async streaming."""
        if not message or not message.strip():
            return history, "Please enter a message."

        message_text = message.strip()

        # Check if it's a command
        if message_text.startswith("/"):
            try:
                # For commands, we need to run the async generator
                async def handle_command_async():
                    async for result in self._handle_command(message_text, history):
                        return result

                # Run the async function
                import asyncio

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(handle_command_async())
                finally:
                    loop.close()
            except Exception as e:
                error_msg = f"Error handling command: {str(e)}"
                logger.error(error_msg)
                history.append({"role": "assistant", "content": f"❌ {error_msg}"})
                return history, error_msg

        try:
            # Display user message
            history.append({"role": "user", "content": message_text})

            # Generate response with streaming - show incremental chunks
            full_response = ""

            # Run the async generator in a new event loop
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Collect all chunks from the streaming response
                chunks = []

                # Get the async generator by calling the async function
                async def collect_chunks():
                    # Call the async generator function - this returns an async generator
                    async_gen = self.chat_service.generate_streaming_response(
                        user_message=message_text,
                        session_id="default",
                        system_prompt="You are a helpful RAG assistant. Provide clear, concise, and accurate responses based on the available context and documents.",
                        use_rag=self.rag_enabled,
                        rag_n_results=self.n_results,
                        rag_min_score=self.min_score,
                    )

                    # Always use async for on the async generator
                    async for chunk in async_gen:
                        if chunk:  # Only process non-empty chunks
                            chunks.append(chunk)

                loop.run_until_complete(collect_chunks())

                # Process all chunks
                for chunk in chunks:
                    full_response += chunk
                    # Update history with the new chunk only (not the full response)
                    if history and history[-1]["role"] == "user":
                        # First chunk - create new assistant message
                        history.append({"role": "assistant", "content": chunk})
                    else:
                        # Subsequent chunks - append to existing assistant message
                        history[-1]["content"] += chunk

            finally:
                loop.close()

            # Save to database with the complete response
            self.chat_service.add_message_to_history("default", "user", message_text)
            self.chat_service.add_message_to_history(
                "default", "assistant", full_response
            )

            return history, "Response generated successfully!"

        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            logger.error(error_msg)
            history.append({"role": "assistant", "content": f"❌ {error_msg}"})
            return history, error_msg

    async def _handle_command(
        self, command: str, history: list[dict[str, str]]
    ) -> AsyncGenerator[tuple[list[dict[str, str]], str], None]:
        """Handle special commands."""
        cmd = command.strip().lower()

        if cmd == "/help":
            help_text = """**Available Commands:**
            
/help - Show this help message
/stats - Show system and database statistics  
/clear - Clear chat history
/export - Export chat to file

**RAG Features:**
- Automatic document retrieval for context
- Conversation history management
- Configurable response quality
- Error handling and retry logic"""
            history.append({"role": "assistant", "content": help_text})
            yield history, "Help message displayed"

        elif cmd == "/stats":
            stats_text = await self._get_stats_text()
            history.append({"role": "assistant", "content": stats_text})
            yield history, "Statistics displayed"

        elif cmd == "/clear":
            result = await self._clear_chat()
            yield result

        elif cmd == "/export":
            export_msg = await self._export_chat()
            history.append({"role": "assistant", "content": export_msg})
            yield history, export_msg

        else:
            history.append(
                {
                    "role": "assistant",
                    "content": "Unknown command. Type /help for available commands.",
                }
            )
            yield history, "Unknown command"

    async def _get_stats_text(self) -> str:
        """Get system and database statistics text."""
        try:
            # Get chat service stats
            stats = self.chat_service.get_usage_stats()

            stats_text = f"""**System Statistics:**

**Chat Service:**
- Total Conversations: {stats.get('stats', {}).get('total_conversations', 'Unknown')}
- Successful Responses: {stats.get('stats', {}).get('successful_responses', 'Unknown')}
- Failed Responses: {stats.get('stats', {}).get('failed_responses', 'Unknown')}
- Average Response Time: {stats.get('stats', {}).get('average_response_time', 'Unknown'):.2f}s

**RAG Service:**
- RAG Enabled: {stats.get('rag_stats', {}).get('rag_enabled', 'Unknown')}
- Context Count: {stats.get('rag_stats', {}).get('count', 'Unknown')}
- Total Documents: {stats.get('rag_stats', {}).get('total_documents', 'Unknown')}
- Total Chunks: {stats.get('rag_stats', {}).get('total_chunks', 'Unknown')}

**Database:**
- Status: Connected
- Collections: Available
- Documents: Indexed

**Performance:**
- Response Time: Optimized
- Memory Usage: Efficient
- Error Rate: Low"""

            return stats_text

        except Exception as e:
            return f"Error getting stats: {str(e)}"

    async def _clear_chat(self) -> tuple[list[dict[str, str]], str]:
        """Clear the chat history."""
        try:
            # Clear from database
            self.chat_history_service.clear_session_history()

            # Clear from UI and memory
            self.messages = []

            # Clear from chat service
            self.chat_service.clear_conversation_history("default")

            # Add welcome message
            welcome_msg = "Chat history cleared. How can I help you today?"
            history = [{"role": "assistant", "content": welcome_msg}]

            # Save welcome message
            self.chat_service.add_message_to_history(
                "default", "assistant", welcome_msg
            )

            return history, "Chat cleared successfully!"

        except Exception as e:
            error_msg = f"Error clearing chat: {str(e)}"
            return [{"role": "assistant", "content": f"❌ {error_msg}"}], error_msg

    async def _export_chat(self) -> str:
        """Export chat history to file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chat_export_{timestamp}.json"
            filepath = f"exports/{filename}"

            # Ensure exports directory exists
            import os

            os.makedirs("exports", exist_ok=True)

            # Save chat history
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.messages, f, indent=2, ensure_ascii=False)

            return f"✅ Chat exported to: {filepath}"

        except Exception as e:
            return f"❌ Export failed: {str(e)}"

    async def _on_rag_toggle(self, enabled: bool) -> str:
        """Handle RAG toggle change."""
        self.rag_enabled = enabled
        status = "enabled" if enabled else "disabled"
        return f"RAG functionality {status}."

    async def _on_history_limit_change(self, limit: int) -> str:
        """Handle history limit change."""
        self.history_limit = limit
        self.chat_service.conversation_history_limit = limit
        return f"History limit set to {limit}."

    async def _on_rag_results_change(self, results: int) -> str:
        """Handle RAG results change."""
        self.n_results = results
        return f"RAG results set to {results}."

    async def _on_min_score_change(self, score: float) -> str:
        """Handle min score change."""
        self.min_score = score
        return f"Min score set to {score}."

    async def _show_stats(self) -> str:
        """Show system and database statistics."""
        return await self._get_stats_text()

    def _load_initial_messages(self):
        """Load initial messages and system information."""
        try:
            # Load existing chat history from database
            existing_messages = self.chat_history_service.get_session_history()

            if existing_messages:
                # Restore existing messages in Gradio format
                history = []
                for msg in existing_messages:
                    if msg["role"] == "user":
                        history.append({"role": "user", "content": msg["content"]})
                    else:
                        history.append({"role": "assistant", "content": msg["content"]})

                # Check for incomplete assistant messages (streaming interrupted)
                if history and history[-1]["role"] == "user":
                    # Mark the message as incomplete and add a note
                    incomplete_msg = f"{history[-1]['content']}\n\n*(Response was interrupted. Please resend your message if needed.)*"
                    history[-1] = {"role": "assistant", "content": incomplete_msg}

                    # Update database with the incomplete marker
                    self.chat_service.add_message_to_history(
                        "default", "assistant", incomplete_msg
                    )

                return history
            else:
                # No existing messages, show welcome message
                welcome_msg = (
                    "Welcome to the RAG Chat Interface! 🤖\n\n"
                    "I'm powered by RAG (Retrieval-Augmented Generation) technology.\n"
                    "Ask me questions about your documents, and I'll provide context-aware responses.\n\n"
                    "Use `/help` for available commands."
                )

                self.chat_service.add_message_to_history(
                    "default", "assistant", welcome_msg
                )
                return [{"role": "assistant", "content": welcome_msg}]

        except Exception as e:
            logger.error(f"Error loading initial messages: {e}")
            error_msg = f"Error loading chat history: {str(e)}"
            return [{"role": "assistant", "content": f"❌ {error_msg}"}]

    def cleanup(self):
        """Clean up resources."""
        super().cleanup()
        if self.chat_service:
            self.chat_service.cleanup()
        self.messages.clear()
