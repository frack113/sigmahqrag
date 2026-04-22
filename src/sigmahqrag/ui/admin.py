"""Admin UI components using Gradio."""

from __future__ import annotations

import logging
from typing import Any

import gradio as gr

from sigmahqrag.admin.health import ServiceHealth, create_health_checker
from sigmahqrag.config import (
    EMBEDDINGS_DIR,
    LLAMA_BIN_PATH,
    LLM_DIR,
    QDRANT_BIN_PATH,
    get_backend,
    set_backend,
)

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
                    llama_download_btn = gr.Button(
                        "Download llama.cpp", variant="secondary"
                    )
                    qdrant_download_btn = gr.Button(
                        "Download Qdrant", variant="secondary"
                    )

                download_status = gr.Textbox(label="Download Status", interactive=False)

                gr.Markdown("### Model Selection")

                def scan_llm_models() -> list[str]:
                    """Scan available LLM models."""
                    from sigmahqrag.ui.model_selector import scan_models

                    models = scan_models(str(LLM_DIR))
                    return models if models else ["No models found"]

                def scan_embedding_models() -> list[str]:
                    """Scan available embedding models."""
                    models = []
                    if EMBEDDINGS_DIR.exists():
                        for f in EMBEDDINGS_DIR.iterdir():
                            if f.suffix.lower() == ".gguf":
                                models.append(f.stem)
                    return models if models else ["No models found"]

                llm_model_dropdown = gr.Dropdown(
                    label="LLM Model",
                    choices=scan_llm_models(),
                )
                embedding_model_dropdown = gr.Dropdown(
                    label="Embedding Model",
                    choices=scan_embedding_models(),
                )
                model_save_btn = gr.Button("Save Model Selection", variant="primary")
                model_status = gr.Textbox(label="Model Status", interactive=False)

                model_info_output = gr.Markdown(
                    value="Select a model to view VRAM requirements"
                )

                def get_model_vram(model_name: str) -> str:
                    """Calculate and display VRAM for a model."""
                    if not model_name or model_name == "No models found":
                        return "No model selected"

                    model_path = LLM_DIR / f"{model_name}.gguf"
                    if not model_path.exists():
                        return f"Model file not found: {model_name}.gguf"

                    size_bytes = model_path.stat().st_size
                    size_gb = size_bytes / (1024**3)

                    size_mb = size_bytes / (1024**2)
                    if size_mb < 4096:
                        vram_note = "~1x model size (Q4)"
                    else:
                        vram_note = "~1.2x model size + context"

                    return f"""**{model_name}**

- **File Size:** {size_mb:.0f} MB ({size_gb:.2f} GB)
- **Est. VRAM:** {vram_note}
- **Note:** Actual VRAM depends on quantization and context length"""

                with gr.Accordion("Download Models Info"):
                    gr.Markdown("""
                    **Recommended LLM Models:**
                    - llama-3.1-8b-q4_0.gguf (~5GB)
                    - phi-3.5-q4_0.gguf (~4GB)

                    **Recommended Embedding Models:**
                    - bge-small-en-v1.5-q4_0.gguf (~130MB)
                    """)

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
                await manager.start_llama(str(LLAMA_BIN_PATH))
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
        llama_start_btn.click(
            fn=start_llama_service, outputs=[llama_status, qdrant_status]
        )
        llama_stop_btn.click(
            fn=stop_llama_service, outputs=[llama_status, qdrant_status]
        )
        llama_logs_btn.click(
            fn=fetch_llama_logs, outputs=[llama_logs_output, llama_logs_output]
        )
        qdrant_start_btn.click(
            fn=start_qdrant_service, outputs=[llama_status, qdrant_status]
        )
        qdrant_stop_btn.click(
            fn=stop_qdrant_service, outputs=[llama_status, qdrant_status]
        )
        qdrant_logs_btn.click(
            fn=fetch_qdrant_logs, outputs=[qdrant_logs_output, qdrant_logs_output]
        )

        async def save_model_selection(llm_model: str, embedding_model: str) -> str:
            try:
                from sigmahqrag.config import load_config, save_config

                config = load_config()
                config["llm_model"] = llm_model
                config["embedding_model"] = embedding_model
                save_config(config)
                return f"Saved: LLM={llm_model}, Embedding={embedding_model}"
            except Exception as e:
                return f"Error: {e}"

        backend_save_btn.click(
            fn=save_backend, inputs=[backend_dropdown], outputs=[backend_status]
        )
        llama_download_btn.click(fn=download_llama_binary, outputs=[download_status])
        qdrant_download_btn.click(fn=download_qdrant_binary, outputs=[download_status])
        model_save_btn.click(
            fn=save_model_selection,
            inputs=[llm_model_dropdown, embedding_model_dropdown],
            outputs=[model_status],
        )

        def on_model_select(model_name: str) -> str:
            return get_model_vram(model_name)

        llm_model_dropdown.change(
            fn=on_model_select, inputs=[llm_model_dropdown], outputs=[model_info_output]
        )

        admin_demo.load(fn=fetch_status, outputs=[llama_status, qdrant_status])

    return admin_demo
