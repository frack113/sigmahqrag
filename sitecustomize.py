"""Site customization - runs before any other imports to disable verbose output."""
import os

# Force air-gap mode
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_TOKEN", "")
os.environ.setdefault("TQDM_DISABLE", "1")
