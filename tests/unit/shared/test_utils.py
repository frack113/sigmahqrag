"""Tests for shared utility functions."""

import re

from src.shared.utils import iso_now


class TestIsoNow:
    def test_returns_string(self) -> None:
        result = iso_now()
        assert isinstance(result, str)

    def test_iso_format(self) -> None:
        result = iso_now()
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", result)

    def test_utc_time(self) -> None:
        from datetime import datetime, timezone

        result = iso_now()
        parsed = datetime.strptime(result, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        diff = abs((now - parsed).total_seconds())
        assert diff < 5
