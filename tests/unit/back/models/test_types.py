"""Tests for model management types."""

import pytest

from src.back.models.types import HFRepo


class TestHFRepo:
    def test_init_with_valid_repo_type(self) -> None:
        repo = HFRepo(owner="test-org", name="test-model", repo_type="models")
        assert repo.owner == "test-org"
        assert repo.name == "test-model"
        assert repo.repo_type == "models"

    def test_init_defaults_to_models(self) -> None:
        repo = HFRepo(owner="org", name="model")
        assert repo.repo_type == "models"

    def test_init_rejects_invalid_repo_type(self) -> None:
        with pytest.raises(ValueError, match="Invalid repo_type"):
            HFRepo(owner="org", name="model", repo_type="invalid")

    def test_full_id(self) -> None:
        repo = HFRepo(owner="org", name="model")
        assert repo.full_id == "org/model"

    def test_from_string(self) -> None:
        repo = HFRepo.from_string("org/model")
        assert repo.owner == "org"
        assert repo.name == "model"
        assert repo.repo_type == "models"

    def test_from_string_with_datasets(self) -> None:
        repo = HFRepo.from_string("org/dataset")
        assert repo.owner == "org"
        assert repo.name == "dataset"

    def test_from_string_invalid_format(self) -> None:
        with pytest.raises(ValueError, match="Invalid repo_id format"):
            HFRepo.from_string("no-slash")

    def test_from_string_multiple_slashes(self) -> None:
        with pytest.raises(ValueError, match="Invalid repo_id format"):
            HFRepo.from_string("a/b/c")

    def test_repr(self) -> None:
        repo = HFRepo(owner="org", name="model")
        assert repr(repo) == "HFRepo(org/model)"

    def test_equality_same(self) -> None:
        r1 = HFRepo(owner="org", name="model")
        r2 = HFRepo(owner="org", name="model")
        assert r1 == r2

    def test_equality_different(self) -> None:
        r1 = HFRepo(owner="org", name="model")
        r2 = HFRepo(owner="org", name="other")
        assert r1 != r2

    def test_equality_with_non_hfrepo(self) -> None:
        repo = HFRepo(owner="org", name="model")
        assert repo != "not-a-repo"
        assert repo != 42
        assert repo is not None

    def test_hashable(self) -> None:
        r1 = HFRepo(owner="org", name="model")
        r2 = HFRepo(owner="org", name="model")
        s = {r1, r2}
        assert len(s) == 1

    def test_hash_different(self) -> None:
        r1 = HFRepo(owner="org", name="model")
        r2 = HFRepo(owner="org", name="other")
        s = {r1, r2}
        assert len(s) == 2
