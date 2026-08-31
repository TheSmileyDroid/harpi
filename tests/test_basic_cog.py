"""Tests for the general-purpose cog and its server-status image renderer.

The rendering helpers are exercised against a fixed `top` output so the
PNG bytes and layout decisions are deterministic; the `status` command
gets psutil faked out so no real system metrics are read.
"""

from __future__ import annotations

from typing import Any, Callable, cast

import pytest
from discord.ext.commands import Command, Context

import src.cogs.basic as basic_module
from src.cogs.basic import (
    GeneralCog,
    _line_color,
    _load_mono_font,
    _render_top_image,
)


def _top_output() -> str:
    return "\n".join([
        "top - 12:00:00 up 3 days",
        "Tasks: 120 total",
        "%Cpu(s): 12.3 us",
        "MiB Mem : 32000 total",
        "  PID USER      PR  NI    VIRT",
        "  101 root      20   0  123456",
        "  102 root      20   0  234567",
        "  103 root      20   0  345678",
    ])


def _make_cog() -> GeneralCog:
    return GeneralCog()


async def _invoke(
    command: Command, cog: GeneralCog, ctx: Any, **kwargs: Any
) -> Any:
    callback = cast(Callable[..., Any], command.callback)
    return await callback(cog, cast(Context, ctx), **kwargs)


class FakeContext:
    def __init__(self) -> None:
        self.bot: Any = None
        self.sent: list[str] = []
        self.embeds: list[Any] = []
        self.files: list[Any] = []

    async def send(self, content: str = "", **kwargs: Any) -> None:
        self.sent.append(content)
        if "embed" in kwargs:
            self.embeds.append(kwargs["embed"])
        if "file" in kwargs:
            self.files.append(kwargs["file"])


# --- rendering helpers ---------------------------------------------------------


@pytest.mark.parametrize(
    ("index", "expected"),
    [
        (0, (0, 255, 127)),
        (1, (102, 204, 255)),
        (2, (102, 204, 255)),
        (3, (255, 165, 0)),
        (6, (255, 165, 0)),
        (7, (220, 220, 220)),
        (19, (220, 220, 220)),
    ],
)
def test_line_color_follows_the_section_bandings(
    index: int, expected: tuple[int, int, int]
):
    assert _line_color(index) == expected


def test_load_mono_font_returns_a_font():
    font = _load_mono_font(14)
    assert font is not None


def test_load_mono_font_falls_back_to_the_default_font(monkeypatch):
    original_truetype = basic_module.PIL.ImageFont.truetype

    def fake_truetype(*args: Any, **kwargs: Any) -> Any:
        if "DejaVuSansMono" in str(args[0]):
            raise OSError("no such font")
        return original_truetype(*args, **kwargs)

    monkeypatch.setattr(basic_module.PIL.ImageFont, "truetype", fake_truetype)
    font = _load_mono_font(14)
    assert "DejaVuSansMono" not in str(getattr(font, "path", ""))


def test_render_top_image_produces_a_png_within_bounds():
    buffer = _render_top_image(_top_output())

    png = buffer.getvalue()
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(png) > 0


def test_render_top_image_clamps_the_output_to_twenty_lines():
    many_lines = "\n".join(f"line {i}" for i in range(50))
    buffer = _render_top_image(many_lines)
    assert buffer.getvalue().startswith(b"\x89PNG")


def test_render_top_image_sizes_the_width_to_the_longest_line():
    buffer = _render_top_image("short\na much longer line of output here")
    assert buffer.getvalue().startswith(b"\x89PNG")


# --- commands -------------------------------------------------------------------


async def test_ping_replies_with_pong():
    cog = _make_cog()
    ctx = FakeContext()

    await _invoke(cog.ping, cog, ctx)

    assert ctx.sent == ["Pong!"]


async def test_echo_replies_with_the_arguments():
    cog = _make_cog()
    ctx = FakeContext()

    await _invoke(cog.echo, cog, ctx, args="olá, mundo")

    assert ctx.sent == ["olá, mundo"]


async def test_status_builds_the_server_status_embed(monkeypatch):
    class FakeMemory:
        percent = 42.0

    class FakeDisk:
        percent = 10.0
        used = 10 * 1024**3
        total = 100 * 1024**3

    monkeypatch.setattr(
        basic_module.psutil, "virtual_memory", lambda: FakeMemory()
    )
    monkeypatch.setattr(
        basic_module.psutil, "disk_usage", lambda _path: FakeDisk()
    )
    monkeypatch.setattr(
        basic_module.psutil, "cpu_percent", lambda *_args, **_kwargs: 7.5
    )

    cog = _make_cog()
    ctx = FakeContext()

    await _invoke(cog.status, cog, ctx)

    assert len(ctx.embeds) == 1
    embed = ctx.embeds[0]
    field_values = {field.name: field.value for field in embed.fields}
    assert field_values["Uso de CPU"] == "7.5%"
    assert field_values["Uso de Memória"] == "42.0%"
    assert "Espaço em Disco" in field_values
    assert "Disco Externo" in field_values


async def test_top_replies_with_the_rendered_image(monkeypatch):
    monkeypatch.setattr(
        basic_module.subprocess,
        "check_output",
        lambda _cmd: _top_output().encode("utf-8"),
    )

    cog = _make_cog()
    ctx = FakeContext()

    await _invoke(cog.top, cog, ctx)

    assert ctx.sent == ["📊 **Informações do Sistema:**"]
    assert len(ctx.files) == 1
    assert ctx.files[0].filename == "top_command.png"


async def test_shutdown_closes_the_bot():
    cog = _make_cog()
    ctx = FakeContext()
    closed: list[bool] = []
    ctx.bot = cast(Any, SimpleBot(closed))

    await _invoke(cog.shutdown, cog, ctx)

    assert ctx.sent == ["Desligando..."]
    assert closed == [True]


class SimpleBot:
    def __init__(self, closed: list[bool]) -> None:
        self._closed = closed

    async def close(self) -> None:
        self._closed.append(True)
