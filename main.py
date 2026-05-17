from pathlib import Path


def _ensure_data_folders() -> None:
    base = Path("data").resolve()
    for d in (
        base,
        base / "bin",
        base / "models",
        base / "models" / "llm",
        base / "models" / "embeddings",
        base / "duckdb",
        base / "logs",
        base / "pids",
        base / "qdrant_storage",
        base / "temp",
    ):
        d.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    import uvicorn

    _ensure_data_folders()

    uvicorn.run("src.main:create_app", host="0.0.0.0", port=7860, reload=True, factory=True)
