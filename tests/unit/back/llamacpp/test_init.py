"""Tests for llama.cpp package init module."""

from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.llm.llamacpp import (
    _detect_llama_server_binary,
    _try_get_llama_version_from_binary,
    get_version,
    set_version,
)


class TestDetectLlamaServerBinary:
    def test_finds_binary_on_windows(self, tmp_path: pytest.TempPathFactory) -> None:
        exe = tmp_path / "llama-server.exe"
        exe.write_text("fake")
        mock_config = MagicMock()
        mock_config.resolve_llamacpp_bin_path.return_value = tmp_path
        with (
            patch("src.infrastructure.llm.llamacpp.get_config", return_value=mock_config),
            patch("sys.platform", "win32"),
        ):
            result = _detect_llama_server_binary()
        assert result == exe

    def test_finds_binary_on_unix(self, tmp_path: pytest.TempPathFactory) -> None:
        exe = tmp_path / "llama-server"
        exe.write_text("fake")
        mock_config = MagicMock()
        mock_config.resolve_llamacpp_bin_path.return_value = tmp_path
        with (
            patch("src.infrastructure.llm.llamacpp.get_config", return_value=mock_config),
            patch("sys.platform", "linux"),
        ):
            result = _detect_llama_server_binary()
        assert result == exe

    def test_returns_none_when_not_found(self, tmp_path: pytest.TempPathFactory) -> None:
        mock_config = MagicMock()
        mock_config.resolve_llamacpp_bin_path.return_value = tmp_path
        with (
            patch("src.infrastructure.llm.llamacpp.get_config", return_value=mock_config),
            patch("sys.platform", "win32"),
        ):
            result = _detect_llama_server_binary()
        assert result is None

    def test_windows_falls_back_to_no_ext(self, tmp_path: pytest.TempPathFactory) -> None:
        exe = tmp_path / "llama-server"
        exe.write_text("fake")
        mock_config = MagicMock()
        mock_config.resolve_llamacpp_bin_path.return_value = tmp_path
        with (
            patch("src.infrastructure.llm.llamacpp.get_config", return_value=mock_config),
            patch("sys.platform", "win32"),
        ):
            result = _detect_llama_server_binary()
        assert result == exe


class TestTryGetVersionFromBinary:
    def test_returns_none_when_no_binary(self) -> None:
        with patch(
            "src.infrastructure.llm.llamacpp._detect_llama_server_binary", return_value=None
        ):
            assert _try_get_llama_version_from_binary() is None

    def test_parses_build_number(self) -> None:
        mock_result = MagicMock()
        mock_result.stdout = "llama.cpp b1234"
        mock_result.stderr = ""
        with (
            patch(
                "src.infrastructure.llm.llamacpp._detect_llama_server_binary",
                return_value="/fake/exe",
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = _try_get_llama_version_from_binary()
        assert result == "b1234"

    def test_parses_version_prefix(self) -> None:
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = "version: b5678"
        with (
            patch(
                "src.infrastructure.llm.llamacpp._detect_llama_server_binary",
                return_value="/fake/exe",
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = _try_get_llama_version_from_binary()
        assert result == "b5678"

    def test_parses_llamacpp_prefix(self) -> None:
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = "llama.cpp b9012"
        with (
            patch(
                "src.infrastructure.llm.llamacpp._detect_llama_server_binary",
                return_value="/fake/exe",
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = _try_get_llama_version_from_binary()
        assert result == "b9012"

    def test_parses_build_suffix(self) -> None:
        mock_result = MagicMock()
        mock_result.stdout = "build b3456"
        mock_result.stderr = ""
        with (
            patch(
                "src.infrastructure.llm.llamacpp._detect_llama_server_binary",
                return_value="/fake/exe",
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = _try_get_llama_version_from_binary()
        assert result == "b3456"

    def test_falls_back_to_numeric(self) -> None:
        mock_result = MagicMock()
        mock_result.stdout = "some output 7890"
        mock_result.stderr = ""
        with (
            patch(
                "src.infrastructure.llm.llamacpp._detect_llama_server_binary",
                return_value="/fake/exe",
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = _try_get_llama_version_from_binary()
        assert result == "b7890"

    def test_returns_none_on_unmatched_output(self) -> None:
        mock_result = MagicMock()
        mock_result.stdout = "garbage output"
        mock_result.stderr = ""
        with (
            patch(
                "src.infrastructure.llm.llamacpp._detect_llama_server_binary",
                return_value="/fake/exe",
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = _try_get_llama_version_from_binary()
        assert result is None

    def test_returns_none_on_exception(self) -> None:
        with (
            patch(
                "src.infrastructure.llm.llamacpp._detect_llama_server_binary",
                return_value="/fake/exe",
            ),
            patch("subprocess.run", side_effect=OSError("fail")),
        ):
            result = _try_get_llama_version_from_binary()
        assert result is None


class TestGetVersion:
    def test_returns_configured_version(self) -> None:
        mock_config = MagicMock()
        mock_config.llamacpp_version = "b1234"
        with patch("src.infrastructure.llm.llamacpp.get_config", return_value=mock_config):
            result = get_version()
        assert result == "b1234"

    def test_detects_from_binary_when_zero(self) -> None:
        mock_config = MagicMock()
        mock_config.llamacpp_version = "0"
        with (
            patch("src.infrastructure.llm.llamacpp.get_config", return_value=mock_config),
            patch(
                "src.infrastructure.llm.llamacpp._detect_llama_server_binary",
                return_value="/fake/exe",
            ),
            patch(
                "src.infrastructure.llm.llamacpp._try_get_llama_version_from_binary",
                return_value="b9999",
            ),
        ):
            result = get_version()
        assert result == "b9999"
        assert mock_config.llamacpp_version == "b9999"
        mock_config.save.assert_called_once()

    def test_installed_when_binary_but_no_version(self) -> None:
        mock_config = MagicMock()
        mock_config.llamacpp_version = "0"
        with (
            patch("src.infrastructure.llm.llamacpp.get_config", return_value=mock_config),
            patch(
                "src.infrastructure.llm.llamacpp._detect_llama_server_binary",
                return_value="/fake/exe",
            ),
            patch(
                "src.infrastructure.llm.llamacpp._try_get_llama_version_from_binary",
                return_value=None,
            ),
        ):
            result = get_version()
        assert result == "installed"

    def test_returns_zero_when_no_binary(self) -> None:
        mock_config = MagicMock()
        mock_config.llamacpp_version = "0"
        with (
            patch("src.infrastructure.llm.llamacpp.get_config", return_value=mock_config),
            patch("src.infrastructure.llm.llamacpp._detect_llama_server_binary", return_value=None),
        ):
            result = get_version()
        assert result == "0"


class TestSetVersion:
    def test_sets_and_saves(self) -> None:
        mock_config = MagicMock()
        with patch("src.infrastructure.llm.llamacpp.get_config", return_value=mock_config):
            set_version("b9999")
        assert mock_config.llamacpp_version == "b9999"
        mock_config.save.assert_called_once()
