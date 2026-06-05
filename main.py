import logging
import re
import sys
from pathlib import Path


class _Filter2xx(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelname != "INFO":
            return True
        msg = record.getMessage()
        # Uvicorn access log format: '127.0.0.1 - "GET /path HTTP/1.1" 200 OK'
        return not bool(re.search(r'"\s+2\d{2}\s+\d{3}', msg))


if __name__ == "__main__":
    import asyncio
    import copy
    import uvicorn
    from uvicorn.config import LOGGING_CONFIG

    # Check init.txt exists and has valid format
    init_file = Path("init.txt")
    if not init_file.exists():
        print(
            "✗ Project not initialized. Run 'uv run python init-projet.py' first.", file=sys.stderr
        )
        sys.exit(1)

    content = init_file.read_text(encoding="utf-8").strip()
    if not content.startswith("Init data structure the "):
        print("✗ Invalid init.txt format. Re-run initialization.", file=sys.stderr)
        sys.exit(1)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    log_config = copy.deepcopy(LOGGING_CONFIG)
    log_config["filters"] = {
        "filter2xx": {"()": _Filter2xx},
    }
    log_config["handlers"]["access"]["filters"] = ["filter2xx"]

    uvicorn.run(
        "src.main:create_app",
        host="0.0.0.0",
        port=7860,
        factory=True,
        log_config=log_config,
        timeout_graceful_shutdown=5,
    )
