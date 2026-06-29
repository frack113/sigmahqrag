"""Download the SPLADE sparse model for hybrid search.

Downloads prithivida/Splade_PP_en_v1 PyTorch weights to SPARSE_MODEL_DIR.
"""

from __future__ import annotations

import logging

from transformers import AutoModelForMaskedLM, AutoTokenizer

from src.config.settings import SPARSE_MODEL_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    model_id = "prithivida/Splade_PP_en_v1"
    target = str(SPARSE_MODEL_DIR)

    logger.info("Downloading %s to %s ...", model_id, target)
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForMaskedLM.from_pretrained(model_id)

    SPARSE_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    tokenizer.save_pretrained(target)
    model.save_pretrained(target)
    logger.info("Done. Model saved to %s", target)


if __name__ == "__main__":
    main()
