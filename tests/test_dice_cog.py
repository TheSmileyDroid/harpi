"""Deterministic tests for the dice cog's command and listener layer.

A recording context/listener-message pair stands in for discord objects
and the parser is stubbed with fixed results so every assertion is exact.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Callable, cast

import pytest

from src.cogs.dice_cog import DiceCog
from src.harpi_lib.harpi_bot import HarpiBot


class StubParser:
    """DiceParser stand-in returning fixed results per expression."""

    def __init__(self, value: int = 7) -> None:
        self.value = value
        self.parsed: list[str] = []
        self.validated: list[str] = []

    def is_valid_dice_string(self, content: str) -> bool:
        self.validated.append(content)
        return "d" in content

    def roll(self, content: str) -> str:
        return f"rolled:{content}"

    def parse(self, expression: str) -> Any:
        self.parsed.append(expression)
        return SimpleRollResult(self.value)


@dataclass(frozen=True)
class SimpleRollResult:
    value: int


class FakeContext:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send(self, content: str, **kwargs: Any) -> None:
        self.sent.append(content)

    async def reply(self, content: str, **kwargs: Any) -> None:
        self.sent.append(content)


def _make_cog(
    monkeypatch: pytest.MonkeyPatch, parser: StubParser | None = None
) -> tuple[DiceCog, StubParser]:
    stub = parser or StubParser()
    monkeypatch.setattr("src.cogs.dice_cog.DiceParser", lambda: stub)
    cog = DiceCog(cast(HarpiBot, SimpleNamespace(user=SimpleNamespace())))
    return cog, stub


async def _invoke(
    command: Any, cog: DiceCog, ctx: FakeContext, **kwargs: Any
) -> Any:
    callback = cast(Callable[..., Any], command.callback)
    return await callback(cog, cast(Any, ctx), **kwargs)


# --- on_message listener ------------------------------------------------------


async def test_listener_ignores_the_bot_s_own_messages(monkeypatch):
    cog, parser = _make_cog(monkeypatch)
    message = SimpleMessage("1d6", author=cog.bot.user)

    await cog.on_message(cast(Any, message))

    assert parser.validated == []


async def test_listener_ignores_non_dice_messages(monkeypatch):
    cog, parser = _make_cog(monkeypatch)
    message = SimpleMessage("hello there", author=object())

    await cog.on_message(cast(Any, message))

    assert parser.validated == ["hello there"]
    assert message.replies == []


async def test_listener_replies_to_dice_messages(monkeypatch):
    cog, _ = _make_cog(monkeypatch)
    message = SimpleMessage("2d6", author=object())

    await cog.on_message(cast(Any, message))

    assert message.replies == ["rolled:2d6"]


# --- roll command -------------------------------------------------------------


async def test_roll_replies_with_the_parser_response(monkeypatch):
    cog, _ = _make_cog(monkeypatch)
    ctx = FakeContext()

    await _invoke(cog.roll, cog, ctx, args="1d20+5")

    assert ctx.sent == ["rolled:1d20+5"]


# --- monte carlo --------------------------------------------------------------


async def test_monte_carlo_runs_n_iterations_and_reports_statistics(
    monkeypatch,
):
    cog, parser = _make_cog(monkeypatch, StubParser(value=3))
    ctx = FakeContext()

    await _invoke(cog.monte_carlo, cog, ctx, n=5, roll_expression="1d6")

    assert parser.parsed == ["1d6"] * 5
    assert len(ctx.sent) == 1
    assert "Simulação Monte Carlo" in ctx.sent[0]
    assert "**Iterações:** 5" in ctx.sent[0]
    assert "**Média:** 3.00" in ctx.sent[0]
    assert "Máximo:** 3" in ctx.sent[0]


async def test_monte_carlo_rejects_non_positive_iterations(monkeypatch):
    cog, _ = _make_cog(monkeypatch)
    ctx = FakeContext()

    with pytest.raises(AssertionError):
        await _invoke(cog.monte_carlo, cog, ctx, n=0, roll_expression="1d6")

    assert ctx.sent == []


async def test_monte_carlo_rejects_more_than_10000_iterations(monkeypatch):
    cog, _ = _make_cog(monkeypatch)
    ctx = FakeContext()

    with pytest.raises(AssertionError):
        await _invoke(
            cog.monte_carlo, cog, ctx, n=10001, roll_expression="1d6"
        )

    assert ctx.sent == []


async def test_monte_carlo_reports_failures_from_the_expression(monkeypatch):
    class FailingParser(StubParser):
        def parse(self, expression: str) -> Any:
            raise ValueError("bad expression")

    cog, _ = _make_cog(monkeypatch, FailingParser())
    ctx = FakeContext()

    await _invoke(cog.monte_carlo, cog, ctx, n=2, roll_expression="1d6")

    assert ctx.sent == ["Erro ao executar simulação: bad expression"]


# --- formatting ----------------------------------------------------------------


def test_format_monte_carlo_results_lists_the_most_frequent_results():
    cog = DiceCog(cast(HarpiBot, object()))
    message = cog._format_monte_carlo_results([1, 1, 2], 3, "1d6")

    lines = message.split("\n")
    assert lines[0] == "🎲 **Simulação Monte Carlo** - 1d6"
    assert "📈 **Média:** 1.33" in lines
    assert "`1`: 2 vezes (66.7%)" in message
    assert "`2`: 1 vezes (33.3%)" in message


class SimpleMessage:
    def __init__(self, content: str, author: Any) -> None:
        self.content = content
        self.author = author
        self.replies: list[str] = []

    async def reply(self, content: str, **kwargs: Any) -> None:
        self.replies.append(content)
