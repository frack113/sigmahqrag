"""Debug script for github endpoint tests."""

import sys
from unittest.mock import patch, MagicMock

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from fastapi import FastAPI
from fastapi.testclient import TestClient


class ExceptionCaptureMiddleware(BaseHTTPMiddleware):
    """Catches all exceptions and returns them as JSON."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            import traceback

            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            print(f"[EXCEPTION CAUGHT] {exc}", file=sys.stderr)
            print(tb, file=sys.stderr)
            return JSONResponse(status_code=500, content={"detail": str(tb)[:3000]})


def make_app():
    app = FastAPI()

    @app.exception_handler(Exception)
    async def capture_exception(request: Request, exc: Exception):
        import traceback

        lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
        tb_lines = "\n".join(lines[-30:])
        return JSONResponse(status_code=500, content={"detail": str(tb_lines)})

    from src.api.v1.github import router

    app.include_router(router)
    return app


app = make_app()
client = TestClient(app, raise_server_exceptions=False)


def test_cloning_detailed():
    """Test cloning status with full exception capture."""
    mock_repos = [
        {
            "org": "test-org",
            "name": "cloning-repo",
            "path": "/tmp/test-org/cloning-repo",
            "branch": "main",
        }
    ]

    # First, let's just directly call the handler logic to isolate the issue
    with (
        patch("src.api.v1.github.list_repos", return_value=mock_repos),
        patch("src.api.v1.github.get_metadata") as mock_meta,
        patch("src.api.v1.github.is_repo_outdated") as mock_outdated,
    ):
        mock_meta.return_value = {"status": "cloning"}
        mock_outdated.return_value = False

        # Patch logger.error to see if it's logging something useful
        with patch("src.api.v1.github.logger") as mock_logger:
            r = client.get("/api/v1/github/repos")
            print(f"Response status: {r.status_code}")
            print(f"Response body: {r.text[:3000]}")

            # Check if logger was called (for error messages)
            for call in mock_logger.error.call_args_list:
                print(f"Logger error: {call}")


def test_tree_filesystem_mock():
    """Test tree endpoint with proper filesystem mocking."""

    mock_path = MagicMock()
    mock_path.exists.return_value = True

    with (
        patch("src.api.v1.github._get_repo_path", return_value=mock_path),
        patch("src.api.v1.github._is_valid_repo", return_value=True),
        patch("src.api.v1.github.get_metadata", return_value={"status": "synced"}),
        patch("src.api.v1.github.get_selected_dirs", return_value=[]),
        patch(
            "src.api.v1.github.list_directory_tree",
            return_value=[{"name": "folder", "path": "folder", "children": []}],
        ),
    ):
        r = client.get("/api/v1/github/repos/test-org/test-repo/tree")

    print(f"Tree - Status: {r.status_code}")
    print(f"Tree - Body: {r.text[:1000]}")


if __name__ == "__main__":
    print("=== Cloning detailed test ===")
    test_cloning_detailed()
    print("\n---\n")

    print("=== Tree filesystem mock ===")
    test_tree_filesystem_mock()
