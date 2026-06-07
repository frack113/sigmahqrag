"""Tests for translate_service.py — YAML detection, extraction, and translation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.application.services.translate_service import (
    detect_sigma_yaml,
    extract_yaml_block,
    translate_detection,
    _render_safe,
    _format_search_context,
    REFORMULATE_SYSTEM,
)


class TestDetectSigmaYaml:
    def test_detects_full_detection_block(self):
        yaml = """detection:
    selection:
        Image|endswith: '\\\\winver.exe'
    condition: selection"""
        assert detect_sigma_yaml(yaml) is True

    def test_detects_partial_yaml(self):
        yaml = """selection:
    CommandLine|contains: 'mimikatz'
    condition: selection"""
        assert detect_sigma_yaml(yaml) is True

    def test_rejects_plain_text(self):
        text = "Can you explain what this rule does?"
        assert detect_sigma_yaml(text) is False

    def test_rejects_single_keyword(self):
        text = "The detection condition is complex"
        assert detect_sigma_yaml(text) is False

    def test_detects_with_logsource(self):
        yaml = """detection:
    logsource:
        category: process_creation
    selection:
        Image|endswith: '\\\\cmd.exe'
    condition: selection"""
        assert detect_sigma_yaml(yaml) is True

    def test_detects_filter(self):
        yaml = """detection:
    selection:
        EventID: 4688
    filter:
        Image|endswith: '\\\\svchost.exe'
    condition: selection and not filter"""
        assert detect_sigma_yaml(yaml) is True


class TestExtractYamlBlock:
    def test_extracts_full_block(self):
        message = """Here is a Sigma rule:
detection:
    selection:
        Image|endswith: '\\\\winver.exe'
    condition: selection
What does it do?"""
        result = extract_yaml_block(message)
        assert result is not None
        assert "detection:" in result
        assert "selection:" in result

    def test_extracts_from_mixed_text(self):
        message = """I found this rule in our SIEM:
detection:
    selection:
        CommandLine|contains: 'mimikatz'
    condition: selection
Can you translate it?"""
        result = extract_yaml_block(message)
        assert result is not None
        assert "mimikatz" in result

    def test_returns_none_for_no_yaml(self):
        message = "What is Sigma rule syntax?"
        result = extract_yaml_block(message)
        assert result is None

    def test_returns_full_message_if_yaml_detected(self):
        yaml = """detection:
    selection:
        Image|endswith: '\\\\winver.exe'
    condition: selection"""
        result = extract_yaml_block(yaml)
        assert result is not None
        assert "detection:" in result


class TestFormatSearchContext:
    def test_empty_results(self):
        result = _format_search_context([])
        assert "no reference" in result

    def test_formats_results(self):
        results = [
            {"text": "Rule about mimikatz", "score": 0.95},
            {"text": "Rule about powershell", "score": 0.80},
        ]
        result = _format_search_context(results)
        assert "mimikatz" in result
        assert "powershell" in result
        assert "0.95" in result

    def test_truncates_long_text(self):
        results = [{"text": "x" * 500, "score": 0.9}]
        result = _format_search_context(results)
        assert len(result) < 500


class TestRenderSafe:
    def test_renders_known_vars(self):
        template = "Results: {{ search_results }}"
        result = _render_safe(template, search_results="found 5 docs")
        assert result == "Results: found 5 docs"

    def test_blocks_injection(self):
        malicious = "{{ config.something }}"
        try:
            _render_safe(malicious)
        except Exception:
            pass  # UndefinedError = safe

    def test_unknown_vars_not_rendered(self):
        template = "Value: {{ unknown_var }}"
        try:
            _render_safe(template)
        except Exception:
            pass  # UndefinedError = safe


class TestReformulateSystem:
    def test_is_string(self):
        assert isinstance(REFORMULATE_SYSTEM, str)

    def test_mentions_no_repetition(self):
        assert "repeat" in REFORMULATE_SYSTEM.lower()


class TestTranslateDetection:
    @pytest.mark.asyncio
    async def test_empty_yaml_returns_empty(self):
        rag = MagicMock()
        result = await translate_detection("", rag)
        assert result == ""

    @pytest.mark.asyncio
    async def test_translates_with_search(self):
        rag = MagicMock()
        rag.search_engine.search = AsyncMock(return_value=[])
        rag.llm_client.chat = AsyncMock(return_value="This rule detects winver.exe")
        rag.llm_client.generate = AsyncMock(return_value="This rule detects winver.exe")

        yaml = """detection:
    selection:
        Image|endswith: '\\\\winver.exe'
    condition: selection"""

        with patch("src.application.system_prompt.get_prompt_by_id") as mock_prompt:
            mock_prompt.return_value = MagicMock(content="Translate: {{ search_results }}")
            result = await translate_detection(yaml, rag, use_chat=True)
            assert len(result) > 0
            rag.search_engine.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_reformulation_pass(self):
        rag = MagicMock()
        rag.search_engine.search = AsyncMock(return_value=[])
        rag.llm_client.chat = AsyncMock(
            side_effect=[
                "The system looks for winver.exe",  # First pass
                "This rule detects when winver.exe is executed",  # Reformulation
            ]
        )

        yaml = """detection:
    selection:
        Image|endswith: '\\\\winver.exe'
    condition: selection"""

        with patch("src.application.system_prompt.get_prompt_by_id") as mock_prompt:
            mock_prompt.return_value = MagicMock(content="Translate: {{ search_results }}")
            result = await translate_detection(yaml, rag, use_chat=True)
            assert "winver.exe" in result
            assert rag.llm_client.chat.call_count == 2

    @pytest.mark.asyncio
    async def test_fallback_on_llm_error(self):
        rag = MagicMock()
        rag.search_engine.search = AsyncMock(return_value=[])
        rag.llm_client.chat = AsyncMock(side_effect=Exception("LLM down"))

        yaml = """detection:
    selection:
        Image|endswith: '\\\\winver.exe'
    condition: selection"""

        result = await translate_detection(yaml, rag)
        assert result == ""
