"""Admin UI components using Gradio."""

from __future__ import annotations

import logging
from typing import Any

import gradio as gr

from src.admin.health import ServiceHealth, create_health_checker
from src.admin.version_manager import check_for_updates, get_current_version
from src.config import (
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
    from src.admin.health import ServiceStatus

    if health.status == ServiceStatus.RUNNING:
        result = {"running": 1.0}
    elif health.status == ServiceStatus.STOPPED:
        result = {"stopped": 1.0}
    else:
        result = {"unknown": 0.5}

    if not binary_path.exists():
        result = {"not installed": 0.5}

    return result


async def _get_version_info(service: str) -> str:
    """Get version info for a service."""
    version = await get_current_version(service)
    if version:
        return f"v{version}"
    return "unknown"


def create_admin_ui() -> gr.Blocks:
    """Create the admin page Gradio UI.

    Returns:
        Gradio Blocks with admin interface
    """

    with gr.Blocks(title="SigmaHQ Admin") as admin_demo:
        gr.Markdown("# 📊 SigmaHQ Admin")

        update_banner = gr.HTML(
            visible=False,
        )

        with gr.Tabs():
            with gr.Tab("Services"):
                gr.Markdown("### Service Management")

                with gr.Row():
                    with gr.Column(scale=2):
                        llama_status = gr.Label(
                            label="llama.cpp - click to refresh",
                            value={"loading...": 0.5},
                        )
                    with gr.Column(scale=1):
                        llama_version = gr.Label(
                            label="Version",
                            value={"checking...": 0.5},
                        )

                with gr.Row():
                    with gr.Column(scale=2):
                        qdrant_status = gr.Label(
                            label="Qdrant - click to refresh",
                            value={"loading...": 0.5},
                        )
                    with gr.Column(scale=1):
                        qdrant_version = gr.Label(
                            label="Version",
                            value={"checking...": 0.5},
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
                # In Gradio, gr.Progress() is not a UI element that is "shown".
                # Instead, it is passed as an argument to the function.
                # We'll use a dummy variable here to satisfy the code structure,
                # but the actual progress bar is triggered by the function call.
                download_progress = gr.Progress()
                # Gr.Progress is usually passed to functions, not instantiated as a UI component like Textbox
                # To show it, it needs to be used within a function decorated with @gr.on(...) or similar
                # For now, we'll ensure it's available for the backend to use.
                download_progress = gr.Progress()

                gr.Markdown("### Model Selection")

                def scan_llm_models() -> list[str]:
                    """Scan available LLM models."""
                    from src.ui.model_selector import scan_models

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

        async def fetch_status() -> tuple[dict[str, Any], dict[str, Any], str, str, str]:
            try:
                checker = create_health_checker()
                all_health = await checker.check_all()

                llama_version = await _get_version_info("llama.cpp")
                qdrant_version = await _get_version_info("qdrant")

                banner_html = ""

                llama_update = await check_for_updates("llama.cpp")
                if llama_update and llama_update.get("update_available"):
                    banner_html += f'''
                    <div style="background: #f59e0b; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
                        <strong>Update available for llama.cpp:</strong> v{llama_update["latest_version"]} available
                    </div>
                    '''

                qdrant_update = await check_for_updates("qdrant")
                if qdrant_update and qdrant_update.get("update_available"):
                    banner_html += f'''
                    <div style="background: #f59e0b; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
                        <strong>Update available for Qdrant:</strong> v{qdrant_update["latest_version"]} available
                    </div>
                    '''

                llama_version_display = {f"v{llama_version}": 1.0} if llama_version else {"unknown": 0.5}
                qdrant_version_display = {f"v{qdrant_version}": 1.0} if qdrant_version else {"unknown": 0.5}

                return (
                    _get_status_display(all_health["llama"], LLAMA_BIN_PATH),
                    _get_status_display(all_health["qdrant"], QDRANT_BIN_PATH),
                    banner_html if banner_html else "",
                    llama_version_display,
                    qdrant_version_display,
                )
            except Exception as e:
                logger.error(f"Status fetch failed: {e}")
                return (
                    {"status": "error", "color": "red", "message": str(e)},
                    {"status": "error", "color": "red", "message": str(e)},
                    "",
                    {"error": 0.5},
                    {"error": 0.5},
                )

        async def start_llama_service() -> tuple[dict[str, Any], dict[str, Any], str, str, str]:
            try:
                from src.admin.service_manager import create_service_manager

                manager = create_service_manager()
                await manager.start_llama(str(LLAMA_BIN_PATH))
                return await fetch_status()
            except Exception as e:
                logger.error(f"Start llama failed: {e}")
                return await fetch_status()

        async def stop_llama_service() -> tuple[dict[str, Any], dict[str, Any], str, str, str]:
            try:
                from src.admin.service_manager import create_service_manager

                manager = create_service_manager()
                await manager.stop_llama()
                return await fetch_status()
            except Exception as e:
                logger.error(f"Stop llama failed: {e}")
                return await fetch_status()

        async def start_qdrant_service() -> tuple[dict[str, Any], dict[str, Any], str, str, str]:
            try:
                from src.admin.service_manager import create_service_manager

                manager = create_service_manager()
                await manager.start_qdrant()
                return await fetch_status()
            except Exception as e:
                logger.error(f"Start qdrant failed: {e}")
                return await fetch_status()

        async def stop_qdrant_service() -> tuple[dict[str, Any], dict[str, Any], str, str, str]:
            try:
                from src.admin.service_manager import create_service_manager

                manager = create_service_manager()
                await manager.stop_qdrant()
                return await fetch_status()
            except Exception as e:
                logger.error(f"Stop qdrant failed: {e}")
                return await fetch_status()

        async def fetch_llama_logs() -> tuple[str, bool]:
            try:
                from src.admin.service_manager import create_service_manager

                manager = create_service_manager()
                logs = manager.get_logs("llama.cpp")
                return logs, True
            except Exception as e:
                return f"Error: {e}", True

        async def fetch_qdrant_logs() -> tuple[str, bool]:
            try:
                from src.admin.service_manager import create_service_manager

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

        async def download_llama_binary(progress=gr.Progress()):
            try:
                from src.admin.download_manager import create_download_manager
                from src.admin.version_manager import VersionManager

                vm = VersionManager()
                release = await vm.get_release("llama.cpp", "latest")
                total_size = 0
                for asset in release.assets:
                    if "windows" in asset.name.lower() and "x64" in asset.name.lower():
                        total_size = asset.size
                        break

                dm = create_download_manager()
                result = await dm.start_download("llama.cpp", "latest")
                
                task = None
                if total_size > 0:
                    for _ in range(60):
                        await asyncio.sleep(1)
                        task = dm.active_downloads.get(result["download_id"])
                        if not task:
                            break
                        progress_val = task.bytes_downloaded / total_size
                        progress(progress_val, desc=f"Downloading: {task.bytes_downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB")
                        if task.status in ("completed", "failed", "cancelled"):
                            break
                else:
                    # If no size found, at least get the task once
                    task = dm.active_downloads.get(result["download_id"])

                return f"Download completed!" if task and task.status == "completed" else f"Status: {task.status if task else 'unknown'}"
            except Exception as e:
                return f"Error: {e}"

        async def download_qdrant_binary(progress=gr.Progress()):
            try:
                from src.admin.download_manager import create_download_manager
                from src.admin.version_manager import VersionManager

                vm = VersionManager()
                release = await vm.get_release("qdrant", "latest")
                total_size = 0
                for asset in release.assets:
                    if "windows" in asset.name.lower() and "x64" in asset.name.lower():
                        total_size = asset.size
                        break

                dm = create_download_manager()
                result = await dm.start_download("qdrant", "latest")
                
                task = None
                if total_size > 0:
                    for _ in range(60):
                        await asyncio.sleep(1)
                        task = dm.active_downloads.get(result["download_id"])
                        if not task:
                            break
                        progress_val = task.bytes_downloaded / total_size
                        progress(progress_val, desc=f"Downloading: {task.bytes_downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB")
                        if task.status in ("completed", "failed", "cancelled"):
                            break
                else:
                    task = dm.active_downloads.get(result["download_id"])

                return f"Download completed!" if task and task.status == "completed" else f"Status: {task.status if task else 'unknown'}"
            except Exception as e:
                return f"Error: {e}"

        refresh_btn.click(fn=fetch_status, outputs=[llama_status, qdrant_status, update_banner, llama_version, qdrant_version])
        llama_start_btn.click(
            fn=start_llama_service, outputs=[llama_status, qdrant_status, update_banner, llama_version, qdrant_version]
        )
        llama_stop_btn.click(
            fn=stop_llama_service, outputs=[llama_status, qdrant_status, update_banner, llama_version, qdrant_version]
        )
        llama_logs_btn.click(
            fn=fetch_llama_logs, outputs=[llama_logs_output, llama_logs_output]
        )
        qdrant_start_btn.click(
            fn=start_qdrant_service, outputs=[llama_status, qdrant_status, update_banner, llama_version, qdrant_version]
        )
        qdrant_stop_btn.click(
            fn=stop_qdrant_service, outputs=[llama_status, qdrant_status, update_banner, llama_version, qdrant_version]
        )
        qdrant_logs_btn.click(
            fn=fetch_qdrant_logs, outputs=[qdrant_logs_output, qdrant_logs_output]
        )

        async def save_model_selection(llm_model: str, embedding_model: str) -> str:
            try:
                from src.config import load_config, save_config

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

        admin_demo.load(fn=fetch_status, outputs=[llama_status, qdrant_status, update_banner, llama_version, qdrant_version])

    return admin_demo
