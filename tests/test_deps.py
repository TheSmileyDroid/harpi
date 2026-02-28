"""Tests for API dependency injection module."""

from unittest.mock import MagicMock

import pytest

import src.api.deps as deps


@pytest.fixture(autouse=True)
def _reset_bot_ref():
    """Reset the global _bot_ref between tests."""
    original = deps._bot_ref
    deps._bot_ref = None
    yield
    deps._bot_ref = original


class TestDeps:
    def test_get_bot_raises_when_not_initialized(self):
        with pytest.raises(AssertionError, match="Bot not initialized"):
            deps.get_bot()

    def test_init_bot_then_get_bot(self):
        mock_bot = MagicMock()
        deps.init_bot(mock_bot)
        assert deps.get_bot() is mock_bot

    def test_get_api_returns_bot_api(self):
        mock_bot = MagicMock()
        mock_bot.api = MagicMock()
        deps.init_bot(mock_bot)
        assert deps.get_api() is mock_bot.api

    def test_init_bot_overwrites_previous(self):
        bot1 = MagicMock()
        bot2 = MagicMock()
        deps.init_bot(bot1)
        deps.init_bot(bot2)
        assert deps.get_bot() is bot2
