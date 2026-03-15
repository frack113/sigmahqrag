"""
Chat Interface Component - Native Gradio Features

Uses Gradio's native features:
- Generator functions for streaming (queue=True handles async)
- Simple event handlers
- No custom threading infrastructure needed
"""

import json
import logging
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Any

import gradio as gr
from src.models.rag_chat_service import RAGChatService

logger = logging.getLogger(__name__)


class ChatInterface:
    """
    RAG-enhanced chat interface using Gradio's native features.

    Features:
    - Streaming responses via generator functions (queue=True)
    - Conversation history managed by Gradio state
    - Simple click handlers (queue=True for async)
    """

    def __init__(self, chat_service: RAGChatService):
        self.chat_service = chat_service

    def create_tab(self) -> None:
        """Create the chat interface tab with native Gradio components."""
        with gr.Column():
            gr.Markdown("## 🤖 RAG Chat Interface")

            # Main chat area
            with gr.Row():
                with gr.Column(scale=3):
                    self.chatbot = gr.Chatbot(
                        value=self._load_initial_messages(),
                        elem_id="chat-messages",
                        show_label=False,
                    )

                    # Input and submit row
                    with gr.Row():
                        self.msg_input = gr.Textbox(
                            placeholder=(
                                "Type your message here... " "(Use /help for commands)"
                            ),
                            container=False,
                            scale=1,
                        )
                        self.submit_btn = gr.Button("Send", variant="primary", scale=0)
                        self.clear_btn = gr.Button("Clear", scale=0)

                    # Status textbox
                    self.status_text = gr.Textbox(
                        label="Status",
                        interactive=False,
                        value="Ready",
                        max_lines=2,
                    )

                # Sidebar with controls
                with gr.Column(scale=1):
                    gr.Markdown("### Configuration")

                    with gr.Accordion("RAG Settings", open=False):
                        with gr.Row():
                            self.rag_toggle = gr.Checkbox(
                                label="Enable RAG", value=True, interactive=True
                            )
                            self.history_limit_input = gr.Number(
                                label="History Limit",
                                value=10,
                                minimum=1,
                                maximum=100,
                                precision=0,
                            )

                        with gr.Row():
                            self.rag_results_input = gr.Number(
                                label="RAG Results",
                                value=3,
                                minimum=1,
                                maximum=10,
                                precision=0,
                            )
                            self.min_score_input = gr.Number(
                                label="Min Score",
                                value=0.1,
                                minimum=0.0,
                                maximum=1.0,
                                step=0.01,
                            )

                    with gr.Row():
                        self.refresh_btn = gr.Button(
                            "Stats", variant="secondary", scale=0
                        )
                        self.export_btn = gr.Button(
                            "Export", variant="secondary", scale=0
                        )

            # Setup event handlers (Gradio handles async via queue=True)
            self.msg_input.submit(
                fn=self._handle_send_message,
                inputs=[self.msg_input],
                outputs=[self.chatbot, self.status_text],
                queue=True,
            )

            self.submit_btn.click(
                fn=self._handle_send_message,
                inputs=[self.msg_input],
                outputs=[self.chatbot, self.status_text],
                queue=True,
            )

            self.clear_btn.click(
                fn=self._clear_chat_handler,
                inputs=[],
                outputs=[self.chatbot, self.status_text],
                queue=True,
            )

    def _handle_send_message(
        self, message: str
    ) -> Generator[tuple[list[dict[str, str]], str], Any, None]:
        """Handle sending a message with streaming response."""
        if not message or not message.strip():
            yield [
                [{"role": "assistant", "content": "Please enter a message."}]
            ], "Please enter a message."
            return

        message_text = message.strip()

        # Handle commands
        if message_text.startswith("/"):
            result = self._handle_command(message_text)
            yield result[0], result[1]
            return

        try:
            # Add user message to history
            history = [{"role": "user", "content": message_text}]
            full_response = ""

            # Stream response using generator (Gradio handles async via queue=True)
            for chunk in self.chat_service.stream_response(user_message=message_text):
                full_response += chunk
                history.append({"role": "assistant", "content": full_response})
                yield [history], "Generating..."

        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            logger.error(error_msg)
            yield [
                [
                    {"role": "user", "content": message_text},
                    {"role": "assistant", "content": f"❌ {error_msg}"},
                ]
            ], error_msg

    def _handle_command(self, command: str) -> tuple[list[dict[str, str]], str]:
        """Handle special commands."""
        cmd = command.strip().lower()

        if cmd == "/help":
            help_text = """**Available Commands:**

/help - Show this help message
/stats - Show system statistics  
/clear - Clear chat history
/export - Export chat to file

**RAG Features:**
- Automatic document retrieval for context
- Conversation history management"""
            return [[{"role": "assistant", "content": help_text}]], "Help displayed"

        elif cmd == "/stats":
            stats = self._get_stats()
            return [
                [{"role": "assistant", "content": f"**System Statistics**:\n{stats}"}]
            ], "Statistics displayed"

        elif cmd == "/clear":
            welcome_msg = "Chat history cleared. How can I help you today?"
            # Clear Gradio's internal state directly
            self.chatbot[:] = []
            yield [[{"role": "assistant", "content": welcome_msg}]], "Ready"

        elif cmd == "/export":
            yield from self._export_chat_handler()

        else:
            return [
                [
                    {
                        "role": "assistant",
                        "content": "Unknown command. Type /help for available commands.",
                    }
                ],
                "Unknown command",
            ]

    def _get_stats(self) -> str:
        """Get system statistics text using the chatbot's internal state."""
        try:
            total = len(self.chatbot[0]) if self.chatbot else 0
            return f"**Total Conversations:** {total}"
        except Exception as e:
            return f"Error getting stats: {str(e)}"

    def _clear_chat_handler(
        self,
    ) -> Generator[tuple[list[dict[str, str]], str], Any, None]:
        """Clear the chat history."""
        try:
            welcome_msg = "Chat history cleared. How can I help you today?"
            # Clear Gradio's internal state directly
            self.chatbot[:] = []

            yield [[{"role": "assistant", "content": welcome_msg}]], "Ready"

        except Exception as e:
            yield [[{"role": "assistant", "content": f"❌ {str(e)}"}]], str(e)

    def _export_chat_handler(
        self,
    ) -> Generator[tuple[list[dict[str, str]], str], Any, None]:
        """Export chat history to file using native Gradio state."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chat_export_{timestamp}.json"

            exports_dir = Path("exports")
            exports_dir.mkdir(exist_ok=True)
            filepath = exports_dir / filename

            # Use Gradio's internal state directly
            chat_content = self.chatbot[0] if self.chatbot else []
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(chat_content, f, indent=2)

            yield [
                [{"role": "assistant", "content": f"✅ Chat exported to: {filepath}"}]
            ], f"✅ Chat exported to: {filepath}"
        except Exception as e:
            yield [
                [{"role": "assistant", "content": f"❌ Export failed: {str(e)}"}]
            ], f"❌ Export failed: {str(e)}"

    def cleanup(self) -> None:
        """Clean up resources using native Gradio state."""
        pass

    def _load_initial_messages(self) -> list[dict[str, Any]]:
        """Load initial welcome message only - chat history stored in Gradio state."""
        return [
            {
                "role": "assistant",
                "content": "Welcome to the RAG Chat Interface! 🤖\n\nI'm powered by RAG technology. Ask me questions about your documents.",
            }
        ]
