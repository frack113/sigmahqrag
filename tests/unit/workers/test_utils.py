"""Tests for worker utility functions."""

from src.shared.utils import iso_now


class TestWorkerIsoNow:
    def test_exports_iso_now(self) -> None:
        result = iso_now()
        assert isinstance(result, str)
        assert "T" in result
        assert result.endswith("Z")
