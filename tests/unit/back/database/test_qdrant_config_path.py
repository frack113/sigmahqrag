"""Test that Qdrant config template path is resolved from PROJECT_ROOT, not CWD."""

from __future__ import annotations

import os
import tempfile

from src.config.settings import PROJECT_ROOT


class TestQdrantConfigPath:
    def test_template_resolved_from_project_root(self) -> None:
        expected = PROJECT_ROOT / "templates" / "qdrant" / "config.yaml.j2"
        assert expected.exists()

    def test_template_path_independent_of_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                from src.config.settings import Config as Cfg
                import inspect

                src = inspect.getsource(Cfg.ensure_qdrant_config)
                assert "PROJECT_ROOT" in src
                assert "templates/qdrant" not in src
            finally:
                os.chdir(cwd)
