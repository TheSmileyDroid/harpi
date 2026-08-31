"""Command-layer tests for the music cog.

The cog is tested the way the framework invokes it: through the command
callbacks with fake contexts, a recording session manager and a fake
session.  Arg parsing, delegation, reply formatting and error paths are
asserted; the session itself is exercised by tests/test_session.py.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable, cast
from unittest.mock import Mock

import pytest
from discord import StageChannel
from discord.ext.commands import Command, CommandError, Context

from src.cogs.music import MusicCog, _layers_message, _queue_message
from src.harpi_lib.audio.session import LayerInfo, LoopMode, SessionStatus
from src.harpi_lib.harpi_bot import HarpiBot
from src.harpi_lib.music.ytmusic import YTMusicData
from tests.conftest import CHANNEL_ID, GUILD_ID


def _status(
    *,
    queue: tuple[YTMusicData, ...] = (),
    layers: tuple[LayerInfo, ...] = (),
    volume: float = 0.5,
) -> SessionStatus:
    return SessionStatus(
        guild_id=GUILD_ID,
        connected=True,
        is_playing=True,
        is_paused=False,
        current_music=YTMusicData({
            "title": "Now Track",
            "uploader": "Artist",
            "duration": 120,
        }),
        queue=queue,
        layers=layers,
        volume=volume,
    )


class FakeSession:
    """Stands in for a PlaybackSession and records every verb."""

    def __init__(self, status: SessionStatus | None = None) -> None:
        self._status = status or _status()
        self.calls: list[Any] = []
        self.announcer: Callable[[str], Any] | None = None
        self.fail_next: str | None = None

    @property
    def status(self) -> SessionStatus:
        return self._status

    def set_announcer(self, announcer: Callable[[str], Any]) -> None:
        self.announcer = announcer

    def _fail(self, verb: str) -> None:
        if self.fail_next == verb:
            self.fail_next = None
            raise ValueError(f"boom:{verb}")

    async def play(self, link: str) -> int:
        self.calls.append(("play", link))
        self._fail("play")
        return 2

    async def stop(self) -> None:
        self.calls.append("stop")

    async def skip(self) -> None:
        self.calls.append("skip")

    async def seek(self, position: float, absolute: bool = False) -> bool:
        self.calls.append(("seek", position, absolute))
        self._fail("seek")
        return True

    async def set_loop(self, loop: LoopMode) -> None:
        self.calls.append(("set_loop", loop))
        self._status = _status()

    async def set_volume(self, volume: float) -> None:
        self.calls.append(("set_volume", volume))
        self._status = _status(volume=volume)

    async def pause(self) -> None:
        self.calls.append("pause")

    async def resume(self) -> None:
        self.calls.append("resume")

    async def add_layer(self, link: str) -> str:
        self.calls.append(("add_layer", link))
        self._fail("add_layer")
        return "l1"

    async def remove_layer(self, layer_id: str) -> bool:
        self.calls.append(("remove_layer", layer_id))
        return True

    async def clear_layers(self) -> None:
        self.calls.append("clear_layers")


class RecordingManager:
    """Stands in for a SessionManager and records connect/disconnect verbs."""

    def __init__(self, session: FakeSession | None) -> None:
        self._session = session
        self.calls: list[str] = []
        self.disconnect_fails = False

    def get(self, guild_id: int) -> FakeSession | None:
        self.calls.append(f"get:{guild_id}")
        return self._session

    async def ensure(self, guild_id: int, channel_id: int) -> FakeSession:
        self.calls.append(f"ensure:{guild_id}:{channel_id}")
        assert self._session is not None
        return self._session

    async def connect(self, guild_id: int, channel_id: int) -> FakeSession:
        self.calls.append(f"connect:{guild_id}:{channel_id}")
        assert self._session is not None
        return self._session

    async def disconnect(self, guild_id: int) -> None:
        self.calls.append(f"disconnect:{guild_id}")
        if self.disconnect_fails:
            raise ValueError("Não conectado")


class FakeContext:
    """Minimal Context stand-in: records sent messages, has a voice author."""

    def __init__(self, guild_id: int = GUILD_ID) -> None:
        self.guild: SimpleNamespace | None = SimpleNamespace(id=guild_id)
        self.author = SimpleNamespace(
            voice=SimpleNamespace(channel=SimpleNamespace(id=CHANNEL_ID))
        )
        self.sent: list[str] = []

    async def send(self, content: str, **kwargs: Any) -> None:
        self.sent.append(content)

    def typing(self) -> _FakeTyping:
        return _FakeTyping()


class _FakeTyping:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *args: Any) -> None:
        return None


def _make_cog(
    session: FakeSession | None = None,
) -> tuple[MusicCog, FakeContext, RecordingManager]:
    bot = SimpleNamespace(sessions=RecordingManager(session))
    cog = MusicCog(cast(HarpiBot, bot))
    return cog, FakeContext(), bot.sessions


async def _invoke(
    command: Command, cog: MusicCog, ctx: FakeContext, **kwargs: Any
) -> Any:
    callback = cast(Callable[..., Any], command.callback)
    return await callback(cog, cast(Context, ctx), **kwargs)


def _sent_join(sent: list[str]) -> str:
    return sent[0]


# --- _resolve_voice_context / _require_session -------------------------------


async def test_commands_require_the_user_to_be_in_a_server():
    cog, ctx, manager = _make_cog()
    ctx.author = SimpleNamespace(voice=None)

    with pytest.raises(CommandError):
        await _invoke(cog.stop, cog, ctx)

    assert ctx.sent == ["Você não está em um servidor"]
    assert manager.calls == []


async def test_commands_require_a_normal_voice_channel():
    cog, ctx, _ = _make_cog()

    ctx.author = SimpleNamespace(
        voice=SimpleNamespace(channel=Mock(spec=StageChannel))
    )

    with pytest.raises(CommandError):
        await _invoke(cog.stop, cog, ctx)

    assert ctx.sent == ["Canal de voz inválido"]


async def test_commands_without_a_connected_session_announce_it():
    cog, ctx, manager = _make_cog()

    await _invoke(cog.stop, cog, ctx)

    assert ctx.sent == ["Guilda não conectada"]
    assert manager.calls == [f"get:{GUILD_ID}"]


# --- join / play / add_layer (connect paths) ---------------------------------


async def test_join_connects_forced_and_announces_readiness():
    session = FakeSession()
    cog, ctx, manager = _make_cog(session)

    await _invoke(cog.join, cog, ctx)

    assert manager.calls == [f"connect:{GUILD_ID}:{CHANNEL_ID}"]
    assert session.announcer == ctx.send
    assert "Conectado e pronto!" in _sent_join(ctx.sent)


async def test_join_reports_resolution_errors():
    cog, ctx, manager = _make_cog()
    ctx.author = SimpleNamespace(voice=None)

    await _invoke(cog.join, cog, ctx)

    assert manager.calls == []
    # _resolve_voice_context announces the failure and join re-announces str(e).
    assert ctx.sent == [
        "Você não está em um servidor",
        "Você não está em um servidor",
    ]


async def test_play_ensures_the_session_and_reports_the_added_count():
    session = FakeSession()
    cog, ctx, manager = _make_cog(session)

    await _invoke(cog.play, cog, ctx, link="http://song")

    assert manager.calls == [f"ensure:{GUILD_ID}:{CHANNEL_ID}"]
    assert session.calls == [("play", "http://song")]
    assert ctx.sent == ["Adicionada(s) 2 música(s) à fila."]


async def test_play_reports_load_failures_from_the_session():
    session = FakeSession()
    cog, ctx, _ = _make_cog(session)
    session.fail_next = "play"

    await _invoke(cog.play, cog, ctx, link="http://song")

    assert ctx.sent == ["boom:play"]


async def test_add_layer_ensures_the_session_and_announces_it():
    session = FakeSession()
    cog, ctx, _ = _make_cog(session)

    await _invoke(cog.add_layer, cog, ctx, link="http://rain")

    assert session.calls == [("add_layer", "http://rain")]
    assert ctx.sent == ["Adicionado **http://rain** ao mixer."]


async def test_add_layer_reports_load_failures():
    session = FakeSession()
    cog, ctx, _ = _make_cog(session)
    session.fail_next = "add_layer"

    await _invoke(cog.add_layer, cog, ctx, link="http://rain")

    assert ctx.sent == ["boom:add_layer"]


# --- stop / skip / pause / resume --------------------------------------------


@pytest.mark.parametrize(
    ("command_name", "expected_call", "reply"),
    [
        ("stop", "stop", "Música parada"),
        ("skip", "skip", "Música pulada"),
        ("pause", "pause", "Música pausada"),
        ("resume", "resume", "Música retomada"),
        ("clean_layers", "clear_layers", "Layers de áudio de fundo limpos."),
    ],
)
async def test_simple_verbs_delegate_and_reply(
    command_name: str, expected_call: str, reply: str
):
    session = FakeSession()
    cog, ctx, _ = _make_cog(session)

    await _invoke(getattr(cog, command_name), cog, ctx)

    assert expected_call in session.calls
    assert ctx.sent == [reply]


# --- seek --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("position", "expected_position", "expected_absolute"),
    [
        ("30", 30.0, True),
        ("+10", 10.0, False),
        ("-10", -10.0, False),
        ("1.5", 1.5, True),
    ],
)
async def test_seek_parses_absolute_and_relative_positions(
    position: str, expected_position: float, expected_absolute: bool
):
    session = FakeSession()
    cog, ctx, _ = _make_cog(session)

    await _invoke(cog.seek, cog, ctx, position=position)

    assert session.calls == [("seek", expected_position, expected_absolute)]
    assert ctx.sent == ["Posição alterada"]


@pytest.mark.parametrize("position", ["abc", "nan", "inf"])
async def test_seek_rejects_unparsable_positions(position: str):
    session = FakeSession()
    cog, ctx, _ = _make_cog(session)

    await _invoke(cog.seek, cog, ctx, position=position)

    assert session.calls == []
    assert ctx.sent == ["Posição inválida"]


async def test_seek_reports_positions_the_session_rejects():
    session = FakeSession()
    cog, ctx, _ = _make_cog(session)
    session.fail_next = "seek"

    await _invoke(cog.seek, cog, ctx, position="500")

    assert ctx.sent == ["Posição inválida"]


# --- loop / volume -----------------------------------------------------------


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("off", LoopMode.OFF),
        ("track", LoopMode.TRACK),
        ("queue", LoopMode.QUEUE),
        ("fila", LoopMode.QUEUE),
    ],
)
async def test_loop_sets_the_requested_mode(mode: str, expected: LoopMode):
    session = FakeSession()
    cog, ctx, _ = _make_cog(session)

    await _invoke(cog.loop, cog, ctx, mode=mode)

    assert session.calls == [("set_loop", expected)]
    assert ctx.sent == [f"Loop mode: {expected.name}"]


@pytest.mark.parametrize("mode", ["whatever", None])
async def test_loop_rejects_unknown_modes(mode: str | None):
    session = FakeSession()
    cog, ctx, _ = _make_cog(session)

    await _invoke(cog.loop, cog, ctx, mode=mode)

    assert session.calls == []
    assert ctx.sent == ["Modo de loop inválido. Use off, track ou queue."]


async def test_volume_without_a_level_reports_the_current_one():
    session = FakeSession()
    cog, ctx, _ = _make_cog(session)

    await _invoke(cog.volume, cog, ctx)

    assert session.calls == []
    assert ctx.sent == ["Volume atual: 0.50"]


@pytest.mark.parametrize("level", ["abc", "nan", "inf"])
async def test_volume_rejects_unparsable_levels(level: str):
    session = FakeSession()
    cog, ctx, _ = _make_cog(session)

    await _invoke(cog.volume, cog, ctx, level=level)

    assert session.calls == []
    assert ctx.sent == ["Volume inválido"]


async def test_volume_sets_the_level():
    session = FakeSession()
    cog, ctx, _ = _make_cog(session)

    await _invoke(cog.volume, cog, ctx, level="1.25")

    assert session.calls == [("set_volume", 1.25)]
    assert ctx.sent == ["Volume definido para 1.25"]


# --- disconnect --------------------------------------------------------------


async def test_disconnect_disconnects_and_replies():
    cog, ctx, manager = _make_cog()

    await _invoke(cog.disconnect, cog, ctx)

    assert manager.calls == [f"disconnect:{GUILD_ID}"]
    assert ctx.sent == ["Desconectado do canal de voz"]


async def test_disconnect_reports_failures():
    cog, ctx, manager = _make_cog()
    manager.disconnect_fails = True

    await _invoke(cog.disconnect, cog, ctx)

    assert ctx.sent == ["Não conectado"]


# --- list / list_layers / remove_layer ---------------------------------------


def test_queue_message_lists_current_track_and_queue():
    message = _queue_message(
        _status(
            queue=(
                YTMusicData({"title": "Next One", "duration": 90}),
                YTMusicData({"title": "Next Two", "duration": 80}),
            )
        )
    )

    assert message == (
        "**Tocando agora:** Now Track (120)\n"
        "**Próximas na fila:**\n"
        "1. Next One (90)\n"
        "2. Next Two (80)"
    )


def test_queue_message_for_an_empty_queue():
    message = _queue_message(_status())
    assert message == "**Tocando agora:** Now Track (120)\nA fila está vazia."


def test_layers_message_for_empty_layers():
    assert _layers_message(_status()) == (
        "Nenhum layer de áudio de fundo adicionado"
    )


def test_layers_message_lists_layers():
    message = _layers_message(
        _status(
            layers=(
                LayerInfo(id="l1", title="Rain", url="u", volume=0.5),
                LayerInfo(id="l2", title="Fire", url="u", volume=0.5),
            )
        )
    )
    assert message == "**Layers de áudio de fundo:**\n1. Rain\n2. Fire"


async def test_list_queue_sends_the_formatted_queue():
    session = FakeSession()
    cog, ctx, _ = _make_cog(session)

    await _invoke(cog.list_queue, cog, ctx)

    assert ctx.sent == [
        "**Tocando agora:** Now Track (120)\nA fila está vazia."
    ]


async def test_list_layers_sends_the_formatted_layers():
    session = FakeSession()
    cog, ctx, _ = _make_cog(session)

    await _invoke(cog.list_layers, cog, ctx)

    assert ctx.sent == ["Nenhum layer de áudio de fundo adicionado"]


@pytest.mark.parametrize("index", [0, 2, -1])
async def test_remove_layer_rejects_out_of_range_indices(index: int):
    session = FakeSession()
    cog, ctx, _ = _make_cog(session)
    session._status = _status(
        layers=(LayerInfo(id="l1", title="Rain", url="u", volume=0.5),)
    )

    await _invoke(cog.remove_layer, cog, ctx, index=index)

    assert ctx.sent == ["Layer inválido."]


async def test_remove_layer_removes_by_display_index():
    session = FakeSession()
    cog, ctx, _ = _make_cog(session)
    session._status = _status(
        layers=(
            LayerInfo(id="l1", title="Rain", url="u", volume=0.5),
            LayerInfo(id="l2", title="Fire", url="u", volume=0.5),
        )
    )

    await _invoke(cog.remove_layer, cog, ctx, index=2)

    assert session.calls == [("remove_layer", "l2")]
    assert ctx.sent == ["Layer removido: Fire"]
