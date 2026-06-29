"""Site customization - runs before any other imports to disable verbose output."""

import os

# Force air-gap mode
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_TOKEN", "")
os.environ.setdefault("TQDM_DISABLE", "1")

# Point fastembed cache to fastembed model directory so sparse models (Splade_PP_en_v1) are found locally
os.environ.setdefault(
    "FASTEMBED_CACHE_PATH",
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "models",
        "embedding_fast",
    ),
)
