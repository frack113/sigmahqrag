"""LlamaService - High-level llama.cpp server wrapper using llama-index."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class LlamaService:
    """High-level service wrapper for llama.cpp server via llama-index."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        model_name: str | None = None,
    ) -> None:
        """Initialize LlamaService."""
        self.base_url = base_url
        self.model_name = model_name
        self._llm: object | None = None

    async def initialize(self) -> None:
        """Initialize the llama-index LLM client."""
        from llama_index.llms.llamafile import Llamafile

        self._llm = Llamafile(base_url=self.base_url)
        logger.info(f"LlamaService initialized: {self.base_url}")

    async def complete(self, prompt: str) -> str:
        """Generate completion for prompt."""
        if self._llm is None:
            await self.initialize()

        response = await self._llm.acomplete(prompt)  # type: ignore[union-attr]
        return str(response)

    async def chat(self, messages: list[dict[str, str]]) -> str:
        """Generate chat completion."""
        if self._llm is None:
            await self.initialize()

        response = await self._llm.achat(messages)  # type: ignore[union-attr]
        return str(response)

    async def health_check(self) -> bool:
        """Check if service is healthy."""
        if self._llm is None:
            await self.initialize()

        try:
            await self._llm.is_busy()  # type: ignore[union-attr]
            return True
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    def __repr__(self) -> str:
        return f"LlamaService(base_url={self.base_url}, model={self.model_name})"
