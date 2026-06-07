"""Tests for base worker class."""

from unittest.mock import MagicMock

import pytest

from src.workers.base import BaseWorker


class _ConcreteWorker(BaseWorker):
    def process(self, task: dict) -> None:
        pass


class TestBaseWorker:
    def test_init(self) -> None:
        db = MagicMock()
        worker = _ConcreteWorker(db=db)
        assert worker.db is db
        assert worker.dispatcher is None

    def test_init_with_dispatcher(self) -> None:
        db = MagicMock()
        dispatcher = MagicMock()
        worker = _ConcreteWorker(db=db, dispatcher=dispatcher)
        assert worker.dispatcher is dispatcher

    def test_abstract_class_cannot_be_instantiated(self) -> None:
        with pytest.raises(TypeError):
            BaseWorker(db=MagicMock())
