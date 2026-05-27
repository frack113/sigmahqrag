"""Advanced tests for config module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.shared.config import Config, get_config


class TestConfigToDict:
    def test_returns_all_sections(self) -> None:
        cfg = Config()
        d = cfg.to_dict()
        assert "backend" in d
        assert "services" in d
        assert "logging" in d
        assert d["backend"]["os"] == "windows"


class TestConfigSave:
    def test_saves_via_db(self) -> None:
        mock_db = MagicMock()
        cfg = Config()
        with patch("src.shared.config.DatabaseService.get_instance", return_value=mock_db):
            result = cfg.save()
            assert result is True
            mock_db.set_config.assert_called()
            mock_db.persist.assert_called_once()

    def test_fails_on_db_error(self) -> None:
        mock_db = MagicMock()
        mock_db.set_config.side_effect = RuntimeError("db error")
        cfg = Config()
        with patch("src.shared.config.DatabaseService.get_instance", return_value=mock_db):
            result = cfg.save()
            assert result is False


class TestConfigApplyDbOverrides:
    def test_applies_overrides(self) -> None:
        mock_db = MagicMock()
        mock_db.get_config.side_effect = lambda k: {
            "backend.os": "linux",
            "backend.gpu_type": "cuda",
        }.get(k)
        cfg = Config()
        with patch("src.shared.config.DatabaseService.get_instance", return_value=mock_db):
            cfg.apply_db_overrides()
            assert cfg.os == "linux"
            assert cfg.gpu_type == "cuda"

    def test_handles_legacy_dict_value(self) -> None:
        mock_db = MagicMock()
        mock_db.get_config.return_value = {"value": "nvidia"}
        cfg = Config()
        with patch("src.shared.config.DatabaseService.get_instance", return_value=mock_db):
            cfg.apply_db_overrides()
            assert cfg.gpu_type == "nvidia"

    def test_skips_none_value(self) -> None:
        mock_db = MagicMock()
        mock_db.get_config.return_value = None
        cfg = Config()
        with patch("src.shared.config.DatabaseService.get_instance", return_value=mock_db):
            cfg.apply_db_overrides()
            assert cfg.os == "windows"


class TestConfigInitApp:
    def test_init_app_returns_config(self) -> None:
        with (
            patch("src.shared.config.Config.ensure_config_file"),
            patch("src.shared.config.Config.ensure_qdrant_config"),
            patch.object(Config, "apply_db_overrides"),
        ):
            cfg = Config.init_app()
            assert isinstance(cfg, Config)

    def test_init_app_handles_db_error(self) -> None:
        with (
            patch("src.shared.config.Config.ensure_config_file"),
            patch("src.shared.config.Config.ensure_qdrant_config"),
            patch.object(Config, "apply_db_overrides", side_effect=RuntimeError("fail")),
        ):
            cfg = Config.init_app()
            assert isinstance(cfg, Config)


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


class TestConfigEnsureConfigFile:
    def test_creates_config_when_missing(self, tmp_path: Path) -> None:
        with (
            patch("src.shared.config.CONFIG_FILE", tmp_path / "sigmahqrag.toml"),
            patch("src.shared.config.Config.to_dict", return_value={"key": "val"}),
        ):
            Config.ensure_config_file()
            assert (tmp_path / "sigmahqrag.toml").exists()

    def test_skips_when_exists(self, tmp_path: Path) -> None:
        config_file = tmp_path / "sigmahqrag.toml"
        config_file.write_text("existing")
        with patch("src.shared.config.CONFIG_FILE", config_file):
            Config.ensure_config_file()
            assert config_file.read_text() == "existing"

    def test_handles_save_error(self, tmp_path: Path) -> None:
        with (
            patch("src.shared.config.CONFIG_FILE", tmp_path / "sigmahqrag.toml"),
            patch("src.shared.toml_service.TOMLService") as mock_svc,
        ):
            mock_svc.return_value.save.return_value = False
            Config.ensure_config_file()


class TestLoadFromToml:
    def test_returns_early_when_no_file(self, tmp_path: Path) -> None:
        with patch("src.shared.config.CONFIG_FILE", tmp_path / "nonexistent.toml"):
            cfg = Config()
            assert cfg.os == "windows"

    def test_handles_toml_service_error(self, tmp_path: Path) -> None:
        config_file = tmp_path / "sigmahqrag.toml"
        config_file.write_text("key = 'val'", encoding="utf-8")
        with (
            patch("src.shared.config.CONFIG_FILE", config_file),
            patch("src.shared.toml_service.TOMLService.load", side_effect=RuntimeError("fail")),
        ):
            cfg = Config()
            assert cfg.os == "windows"


class TestEnsureQdrantConfig:
    def test_skips_when_config_exists(self, tmp_path: Path) -> None:
        qdrant_dir = tmp_path / "qdrant"
        config_file = qdrant_dir / "config" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("existing")
        cfg = Config()
        cfg.qdrant_binary_path = str(qdrant_dir)
        with (
            patch("src.shared.config.CONFIG_FILE", tmp_path / "nonexistent.toml"),
            patch("src.shared.config.Config", return_value=cfg),
        ):
            Config.ensure_qdrant_config()
        assert config_file.read_text() == "existing"

    def test_handles_jinja_error(self, tmp_path: Path) -> None:
        qdrant_dir = tmp_path / "qdrant"
        cfg = Config()
        cfg.qdrant_binary_path = str(qdrant_dir)
        cfg.qdrant_storage_path = str(tmp_path / "storage")
        cfg.qdrant_snapshots_path = str(tmp_path / "snapshots")
        with (
            patch("src.shared.config.CONFIG_FILE", tmp_path / "nonexistent.toml"),
            patch("src.shared.config.Config", return_value=cfg),
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
        with (
            patch("src.shared.config.CONFIG_FILE", tmp_path / "nonexistent.toml"),
            patch("src.shared.config.Config", return_value=cfg),
        ):
            Config.ensure_qdrant_config()
        assert (qdrant_dir / "config" / "config.yaml").exists()


class TestConfigRemaining:
    def test_resolve_returns_default_when_nonexistent(self) -> None:
        cfg = Config()
        cfg.llama_binary_path = "data/bin/nonexistent"
        with patch("src.shared.config.Path.exists", return_value=False):
            result = cfg.resolve_llamacpp_bin_path()
            assert result == Path("data/bin/nonexistent").resolve()

    def test_ensure_config_file_handles_error(self, tmp_path: Path) -> None:
        with (
            patch("src.shared.config.CONFIG_FILE", tmp_path / "sigmahqrag.toml"),
            patch("src.shared.toml_service.TOMLService") as mock_svc,
        ):
            mock_svc.return_value.save.side_effect = RuntimeError("save failed")
            Config.ensure_config_file()

    def test_ensure_qdrant_generates_from_template(self, tmp_path: Path) -> None:
        qdrant_dir = tmp_path / "qdrant"
        cfg = Config()
        cfg.qdrant_binary_path = str(qdrant_dir)
        template_path = Path("templates/qdrant/config.yaml.j2")
        assert template_path.exists(), "Template file must exist for this test"
        with (
            patch("src.shared.config.CONFIG_FILE", tmp_path / "nonexistent.toml"),
            patch("src.shared.config.Config", return_value=cfg),
        ):
            Config.ensure_qdrant_config()
        generated = qdrant_dir / "config" / "config.yaml"
        assert generated.exists()


class TestGetConfig:
    def test_returns_global_config(self) -> None:
        with (
            patch("src.shared.config._config", None),
            patch.object(Config, "init_app") as mock_init,
        ):
            mock_init.return_value = "test"
            result = get_config()
            assert result == "test"

    def test_returns_cached(self) -> None:
        cached = Config()
        with patch("src.shared.config._config", cached):
            result = get_config()
            assert result is cached
