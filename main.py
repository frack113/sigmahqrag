# Main Entry Point - Gradio Version
from src.gradio_app.app import SigmaHQGradioApp

if __name__ in {"__main__", "__mp_main__"}:
    app = SigmaHQGradioApp()
    try:
        app.launch(port=8000)
    except KeyboardInterrupt:
        print("Application shutdown requested")
    finally:
        app.cleanup()
