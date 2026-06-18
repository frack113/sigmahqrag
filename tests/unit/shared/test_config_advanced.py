"""Advanced tests for config module."""

from pathlib import Path
from unittest.mock import patch

from src.config.settings import Config, get_config


class TestConfigToDict:
    def test_returns_all_sections(self) -> None:
        cfg = Config()
        d = cfg.to_dict()
        assert "backend" not in d  # backend section removed - stored in DuckDB
        assert "services" in d
        assert "logging" in d
        assert d["services"]["llama"]["base_url"] == "http://127.0.0.1:8080"


class TestConfigSave:
    def test_save_returns_true(self) -> None:
        cfg = Config()
        with patch("src.infrastructure.database.service.DatabaseService.get_instance"):
            result = cfg.save()
        assert result is True


class TestConfigApplyDbOverrides:
    def test_method_exists(self) -> None:
        assert hasattr(Config, "apply_db_overrides")


class TestConfigInitApp:
    def test_init_app_returns_config(self) -> None:
        with patch("src.config.settings.Config.ensure_qdrant_config"):
            cfg = Config.init_app()
            assert isinstance(cfg, Config)

    def test_init_app_creates_global_config(self) -> None:
        with (
            patch("src.config.settings._config", None),
            patch("src.config.settings.Config.ensure_qdrant_config"),
        ):
            cfg = Config.init_app()
            from src.config.settings import _config as global_cfg

            assert global_cfg is cfg


class TestConfigResolveLlamaCppBinPath:
    def test_returns_path_if_exists(self, tmp_path: Path) -> None:
        cfg = Config()
        cfg.llama_binary_path = str(tmp_path / "llama" / "server")
        (tmp_path / "llama").mkdir(parents=True)
        (tmp_path / "llama" / "server").write_text("")
        result = cfg.resolve_llamacpp_bin_path()
        assert result == (tmp_path / "llama" / "server").resolve()

    def test_falls_back_to_old_path(self, tmp_path: Path) -> None:
        old_path = Path("data/bin/llamacpp").resolve()
        old_path.mkdir(parents=True, exist_ok=True)
        (old_path / "dummy").write_text("")
        cfg = Config()
        cfg.llama_binary_path = str(tmp_path / "nonexistent" / "bin")
        result = cfg.resolve_llamacpp_bin_path()
        assert result == old_path

    def test_returns_default_when_none_exist(self) -> None:
        cfg = Config()
        cfg.llama_binary_path = "data/bin/llamacpp"
        result = cfg.resolve_llamacpp_bin_path()
        assert result == Path("data/bin/llamacpp").resolve()


class TestEnsureQdrantConfig:
    def test_skips_when_config_exists(self, tmp_path: Path) -> None:
        qdrant_dir = tmp_path / "qdrant"
        config_file = qdrant_dir / "config" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("existing")
        cfg = Config()
        cfg.qdrant_binary_path = str(qdrant_dir)
        with patch("src.config.settings.Config", return_value=cfg):
            Config.ensure_qdrant_config()
        assert config_file.read_text() == "existing"

    def test_handles_jinja_error(self, tmp_path: Path) -> None:
        qdrant_dir = tmp_path / "qdrant"
        cfg = Config()
        cfg.qdrant_binary_path = str(qdrant_dir)
        cfg.qdrant_storage_path = str(tmp_path / "storage")
        cfg.qdrant_snapshots_path = str(tmp_path / "snapshots")
        with (
            patch("src.config.settings.Config", return_value=cfg),
            patch.dict("sys.modules", {"jinja2": None}),
        ):
            Config.ensure_qdrant_config()
        assert not (qdrant_dir / "config" / "config.yaml").exists()

    def test_generates_config_successfully(self, tmp_path: Path) -> None:
        qdrant_dir = tmp_path / "qdrant"
        cfg = Config()
        cfg.qdrant_binary_path = str(qdrant_dir)
        cfg.qdrant_storage_path = str(tmp_path / "storage")
        cfg.qdrant_snapshots_path = str(tmp_path / "snapshots")
        with patch("src.config.settings.Config", return_value=cfg):
            Config.ensure_qdrant_config()
        assert (qdrant_dir / "config" / "config.yaml").exists()


class TestConfigRemaining:
    def test_resolve_returns_default_when_nonexistent(self) -> None:
        cfg = Config()
        cfg.llama_binary_path = "data/bin/nonexistent"
        with patch("src.config.settings.Path.exists", return_value=False):
            result = cfg.resolve_llamacpp_bin_path()
            assert result == Path("data/bin/nonexistent").resolve()

    def test_ensure_qdrant_generates_from_template(self, tmp_path: Path) -> None:
        qdrant_dir = tmp_path / "qdrant"
        cfg = Config()
        cfg.qdrant_binary_path = str(qdrant_dir)
        template_path = Path("templates/qdrant/config.yaml.j2")
        assert template_path.exists(), "Template file must exist for this test"
        with patch("src.config.settings.Config", return_value=cfg):
            Config.ensure_qdrant_config()
        generated = qdrant_dir / "config" / "config.yaml"
        assert generated.exists()


class TestGetConfig:
    def test_returns_global_config(self) -> None:
        with (
            patch("src.config.settings._config", None),
            patch.object(Config, "init_app") as mock_init,
        ):
            mock_init.return_value = "test"
            result = get_config()
            assert result == "test"

    def test_returns_cached(self) -> None:
        cached = Config()
        with patch("src.config.settings._config", cached):
            result = get_config()
            assert result is cached
