"""Admin UI components using Gradio."""

from __future__ import annotations

import logging
from typing import Any

import gradio as gr

from sigmahqrag.admin.health import ServiceHealth, create_health_checker
from sigmahqrag.config import LLAMA_BIN_PATH, QDRANT_BIN_PATH, get_backend, set_backend

logger = logging.getLogger(__name__)


def _get_status_display(health: ServiceHealth, binary_path: object) -> dict[str, Any]:
    """Get display data for a service health status."""
    from sigmahqrag.admin.health import ServiceStatus

    if health.status == ServiceStatus.RUNNING:
        color = "green"
        display_status = "running"
    elif health.status == ServiceStatus.STOPPED:
        color = "red"
        display_status = "stopped"
    else:
        color = "yellow"
        display_status = "unknown"

    result: dict[str, Any] = {
        "name": health.name,
        "status": display_status,
        "color": color,
        "port": health.port,
        "url": health.url,
    }

    if health.message:
        result["message"] = health.message

    if not binary_path.exists():
        result["status"] = "not installed"
        result["color"] = "yellow"
        result["message"] = "Binary not found"

    return result


def create_admin_ui() -> gr.Blocks:
    """Create the admin page Gradio UI.

    Returns:
        Gradio Blocks with admin interface
    """

    with gr.Blocks(title="SigmaHQ Admin") as admin_demo:
        gr.Markdown("# 📊 SigmaHQ Admin")

        with gr.Tabs():
            with gr.Tab("Services"):
                gr.Markdown("### Service Management")

                llama_status = gr.Label(
                    label="llama.cpp",
                    value={"status": "loading...", "color": "yellow"},
                )
                qdrant_status = gr.Label(
                    label="Qdrant",
                    value={"status": "loading...", "color": "yellow"},
                )

                with gr.Row():
                    refresh_btn = gr.Button("Refresh", variant="secondary")
                    llama_start_btn = gr.Button("Start llama.cpp", variant="primary")
                    llama_stop_btn = gr.Button("Stop llama.cpp", variant="stop")
                    llama_logs_btn = gr.Button("Logs", variant="secondary")
                    qdrant_start_btn = gr.Button("Start Qdrant", variant="primary")
                    qdrant_stop_btn = gr.Button("Stop Qdrant", variant="stop")
                    qdrant_logs_btn = gr.Button("Logs", variant="secondary")

                llama_logs_output = gr.Textbox(
                    label="llama.cpp logs",
                    lines=10,
                    interactive=False,
                    visible=False,
                )
                qdrant_logs_output = gr.Textbox(
                    label="Qdrant logs",
                    lines=10,
                    interactive=False,
                    visible=False,
                )

            with gr.Tab("Settings"):
                gr.Markdown("### Configuration")

                backend_dropdown = gr.Dropdown(
                    label="llama.cpp Backend",
                    choices=["cpu", "cuda", "hip", "vulkan"],
                    value=get_backend(),
                )
                backend_save_btn = gr.Button("Save Backend", variant="primary")
                backend_status = gr.Textbox(label="Status", interactive=False)

                gr.Markdown("### Binary Management")

                with gr.Row():
                    llama_download_btn = gr.Button("Download llama.cpp", variant="secondary")
                    qdrant_download_btn = gr.Button("Download Qdrant", variant="secondary")

                download_status = gr.Textbox(label="Download Status", interactive=False)

        llama_logs_output = gr.Textbox(
            label="llama.cpp logs",
            lines=10,
            interactive=False,
            visible=False,
        )
        qdrant_logs_output = gr.Textbox(
            label="Qdrant logs",
            lines=10,
            interactive=False,
            visible=False,
        )

        async def fetch_status() -> tuple[dict[str, Any], dict[str, Any]]:
            try:
                checker = create_health_checker()
                all_health = await checker.check_all()

                return (
                    _get_status_display(all_health["llama"], LLAMA_BIN_PATH),
                    _get_status_display(all_health["qdrant"], QDRANT_BIN_PATH),
                )
            except Exception as e:
                logger.error(f"Status fetch failed: {e}")
                return (
                    {"status": "error", "color": "red", "message": str(e)},
                    {"status": "error", "color": "red", "message": str(e)},
                )

        async def start_llama_service() -> tuple[dict[str, Any], dict[str, Any]]:
            try:
                from sigmahqrag.admin.service_manager import create_service_manager
                manager = create_service_manager()
                result = await manager.start_llama(str(LLAMA_BIN_PATH))
                return await fetch_status()
            except Exception as e:
                logger.error(f"Start llama failed: {e}")
                return await fetch_status()

        async def stop_llama_service() -> tuple[dict[str, Any], dict[str, Any]]:
            try:
                from sigmahqrag.admin.service_manager import create_service_manager
                manager = create_service_manager()
                await manager.stop_llama()
                return await fetch_status()
            except Exception as e:
                logger.error(f"Stop llama failed: {e}")
                return await fetch_status()

        async def start_qdrant_service() -> tuple[dict[str, Any], dict[str, Any]]:
            try:
                from sigmahqrag.admin.service_manager import create_service_manager
                manager = create_service_manager()
                await manager.start_qdrant()
                return await fetch_status()
            except Exception as e:
                logger.error(f"Start qdrant failed: {e}")
                return await fetch_status()

        async def stop_qdrant_service() -> tuple[dict[str, Any], dict[str, Any]]:
            try:
                from sigmahqrag.admin.service_manager import create_service_manager
                manager = create_service_manager()
                await manager.stop_qdrant()
                return await fetch_status()
            except Exception as e:
                logger.error(f"Stop qdrant failed: {e}")
                return await fetch_status()

        async def fetch_llama_logs() -> tuple[str, bool]:
            try:
                from sigmahqrag.admin.service_manager import create_service_manager
                manager = create_service_manager()
                logs = manager.get_logs("llama.cpp")
                return logs, True
            except Exception as e:
                return f"Error: {e}", True

        async def fetch_qdrant_logs() -> tuple[str, bool]:
            try:
                from sigmahqrag.admin.service_manager import create_service_manager
                manager = create_service_manager()
                logs = manager.get_logs("qdrant")
                return logs, True
            except Exception as e:
                return f"Error: {e}", True

        async def save_backend(backend: str) -> str:
            try:
                set_backend(backend)
                return f"Backend saved: {backend}"
            except Exception as e:
                return f"Error: {e}"

        async def download_llama_binary() -> str:
            try:
                from sigmahqrag.services.llama import download_llama_cpp
                path = await download_llama_cpp()
                return f"Downloaded to {path}"
            except Exception as e:
                return f"Error: {e}"

        async def download_qdrant_binary() -> str:
            try:
                from sigmahqrag.services.vectorstore import download_qdrant
                path = await download_qdrant()
                return f"Downloaded to {path}"
            except Exception as e:
                return f"Error: {e}"

        refresh_btn.click(fn=fetch_status, outputs=[llama_status, qdrant_status])
        llama_start_btn.click(fn=start_llama_service, outputs=[llama_status, qdrant_status])
        llama_stop_btn.click(fn=stop_llama_service, outputs=[llama_status, qdrant_status])
        llama_logs_btn.click(fn=fetch_llama_logs, outputs=[llama_logs_output, llama_logs_output])
        qdrant_start_btn.click(fn=start_qdrant_service, outputs=[llama_status, qdrant_status])
        qdrant_stop_btn.click(fn=stop_qdrant_service, outputs=[llama_status, qdrant_status])
        qdrant_logs_btn.click(fn=fetch_qdrant_logs, outputs=[qdrant_logs_output, qdrant_logs_output])

        backend_save_btn.click(fn=save_backend, inputs=[backend_dropdown], outputs=[backend_status])
        llama_download_btn.click(fn=download_llama_binary, outputs=[download_status])
        qdrant_download_btn.click(fn=download_qdrant_binary, outputs=[download_status])

        admin_demo.load(fn=fetch_status, outputs=[llama_status, qdrant_status])

    return admin_demo