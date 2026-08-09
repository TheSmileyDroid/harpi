"""Routing tests for the music cog's chat commands.

The migrated commands must route through the SessionManager and the
PlaybackSession — never through the controller or mixer — and bind the
session's announcer to ``ctx.send`` so load failures land in the channel.
A recording fake session and a recording fake manager stand in for the
real objects; the commands themselves are real.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable, cast

import pytest
from discord.ext.commands import Command, Context

from src.cogs.music import MusicCog
from src.harpi_lib.api import LoopMode
from src.harpi_lib.harpi_bot import HarpiBot
from tests.conftest import CHANNEL_ID, GUILD_ID


async def _invoke(
    command: Command, cog: MusicCog, ctx: FakeContext, **kwargs: Any
) -> Any:
    """Call a cog command the way the framework would, without a bound bot."""
    callback = cast(Callable[..., Any], command.callback)
    return await callback(cog, cast(Context, ctx), **kwargs)


class RecordingSession:
    """Stands in for a PlaybackSession and records every verb it receives."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.announcer: Callable[[str], Any] | None = None
        self.play_error: ValueError | None = None
        self.add_layer_error: ValueError | None = None
        self.current_music: Any = None
        self.queue: tuple[Any, ...] = ()
        self.layers: list[Any] = []
        self.volume = 0.7
        self.seek_result = True

    def set_announcer(self, announcer: Callable[[str], Any] | None) -> None:
        self.announcer = announcer

    @property
    def status(self) -> SimpleNamespace:
        return SimpleNamespace(
            current_music=self.current_music,
            queue=self.queue,
            layers=tuple(self.layers),
            volume=self.volume,
        )

    async def play(self, link: str) -> int:
        if self.play_error is not None:
            raise self.play_error
        self.calls.append(f"play:{link}")
        track = SimpleNamespace(title=link, duration=60)
        if self.current_music is None:
            self.current_music = track
        else:
            self.queue = (*self.queue, track)
        return 1

    async def add_layer(self, link: str) -> str:
        if self.add_layer_error is not None:
            raise self.add_layer_error
        self.calls.append(f"add_layer:{link}")
        layer = SimpleNamespace(
            id=f"layer-{link}",
            title=link,
            url=f"https://example.com/{link}",
            volume=0.7,
        )
        self.layers.append(layer)
        return layer.id

    async def remove_layer(self, layer_id: str) -> bool:
        self.calls.append(f"remove_layer:{layer_id}")
        for index, layer in enumerate(self.layers):
            if layer.id == layer_id:
                self.layers.pop(index)
                return True
        return False

    async def clear_layers(self) -> None:
        self.calls.append("clear_layers")
        self.layers.clear()

    async def set_layer_volume(self, layer_id: str, volume: float) -> bool:
        self.calls.append(f"set_layer_volume:{layer_id}:{volume}")
        for layer in self.layers:
            if layer.id == layer_id:
                layer.volume = volume
                return True
        return False

    async def stop(self) -> None:
        self.calls.append("stop")

    async def skip(self) -> None:
        self.calls.append("skip")

    async def seek(self, position: float, absolute: bool = False) -> bool:
        self.calls.append(f"seek:{position}:{absolute}")
        return self.seek_result

    async def set_loop(self, loop: LoopMode) -> None:
        self.calls.append(f"loop:{loop.name}")

    async def set_volume(self, volume: float) -> None:
        self.volume = volume
        self.calls.append(f"volume:{volume}")

    async def pause(self) -> None:
        self.calls.append("pause")

    async def resume(self) -> None:
        self.calls.append("resume")


class RecordingManager:
    """Stands in for a SessionManager and records the verbs it receives."""

    def __init__(self, session: RecordingSession | None) -> None:
        self._session = session
        self.calls: list[str] = []

    async def ensure(self, guild_id: int, channel_id: int) -> RecordingSession:
        self.calls.append(f"ensure:{guild_id}:{channel_id}")
        assert self._session is not None
        return self._session

    def get(self, guild_id: int) -> RecordingSession | None:
        self.calls.append(f"get:{guild_id}")
        return self._session

    async def connect(
        self, guild_id: int, channel_id: int
    ) -> RecordingSession:
        self.calls.append(f"connect:{guild_id}:{channel_id}")
        assert self._session is not None
        return self._session

    async def disconnect(self, guild_id: int) -> None:
        self.calls.append(f"disconnect:{guild_id}")


class FakeHarpiBot:
    def __init__(self, manager: RecordingManager) -> None:
        self.sessions = manager
        self.api: Any = SimpleNamespace()


class FakeContext:
    """Minimal Context stand-in: records sent messages, has a voice author."""

    def __init__(self, guild_id: int = GUILD_ID) -> None:
        self.guild = SimpleNamespace(id=guild_id)
        self.author = SimpleNamespace(
            voice=SimpleNamespace(channel=SimpleNamespace(id=CHANNEL_ID))
        )
        self.sent: list[str] = []

    async def send(self, content: str) -> None:
        self.sent.append(content)

    def typing(self) -> Any:
        return _NoopContextManager()


class _NoopContextManager:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *args: Any) -> None:
        return None


def _make_cog(
    session: RecordingSession | None,
) -> tuple[MusicCog, RecordingSession | None, FakeContext]:
    recording_session = session if session is not None else None
    manager = RecordingManager(session)
    bot = FakeHarpiBot(manager)
    cog = MusicCog(cast(HarpiBot, bot))
    ctx = FakeContext()
    return cog, recording_session, ctx


async def test_play_routes_through_the_session_and_binds_the_announcer():
    session = RecordingSession()
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.play, cog, ctx, link="one")

    assert session is not None
    assert session.calls == ["play:one"]
    assert session.current_music.title == "one"
    announcer = session.announcer
    assert announcer is not None
    assert announcer == ctx.send
    assert ctx.sent == ["Adicionada(s) 1 música(s) à fila."]
    await announcer("anúncio")
    assert ctx.sent == ["Adicionada(s) 1 música(s) à fila.", "anúncio"]


async def test_play_connects_when_there_is_no_session_yet():
    session = RecordingSession()
    cog, _, ctx = _make_cog(session)

    await _invoke(cog.play, cog, ctx, link="one")

    assert session.calls == ["play:one"]


async def test_play_reports_when_nothing_is_found():
    session = RecordingSession()
    session.play_error = ValueError("Nenhuma música encontrada para este link")
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.play, cog, ctx, link="nothing")

    assert session is not None
    assert session.calls == []
    assert ctx.sent == ["Nenhuma música encontrada para este link"]


async def test_stop_routes_through_the_session():
    session = RecordingSession()
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.stop, cog, ctx)

    assert session is not None
    assert session.calls == ["stop"]
    assert ctx.sent == ["Música parada"]


async def test_stop_without_a_session_tells_the_user():
    cog, _, ctx = _make_cog(None)

    await _invoke(cog.stop, cog, ctx)

    assert ctx.sent == ["Guilda não conectada"]


async def test_skip_routes_through_the_session():
    session = RecordingSession()
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.skip, cog, ctx)

    assert session is not None
    assert session.calls == ["skip"]
    assert ctx.sent == ["Música pulada"]


async def test_absolute_seek_routes_through_the_session():
    session = RecordingSession()
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.seek, cog, ctx, position="90")

    assert session is not None
    assert session.calls == ["seek:90.0:True"]
    assert ctx.sent == ["Posição alterada"]


async def test_relative_seek_routes_through_the_session():
    session = RecordingSession()
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.seek, cog, ctx, position="+30")

    assert session is not None
    assert session.calls == ["seek:30.0:False"]
    assert ctx.sent == ["Posição alterada"]


async def test_seek_rejects_invalid_positions():
    session = RecordingSession()
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.seek, cog, ctx, position="abc")

    assert session is not None
    assert session.calls == []
    assert ctx.sent == ["Posição inválida"]


async def test_seek_rejects_non_finite_positions():
    session = RecordingSession()
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.seek, cog, ctx, position="inf")

    assert session is not None
    assert session.calls == []
    assert ctx.sent == ["Posição inválida"]


async def test_seek_without_a_session_tells_the_user():
    cog, _, ctx = _make_cog(None)

    await _invoke(cog.seek, cog, ctx, position="90")

    assert ctx.sent == ["Guilda não conectada"]


async def test_seek_stays_silent_when_nothing_can_be_moved():
    session = RecordingSession()
    session.seek_result = False
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.seek, cog, ctx, position="90")

    assert session is not None
    assert session.calls == ["seek:90.0:True"]
    assert ctx.sent == []


async def test_loop_routes_through_the_session():
    session = RecordingSession()
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.loop, cog, ctx, mode="track")

    assert session is not None
    assert session.calls == ["loop:TRACK"]
    assert ctx.sent == ["Loop mode: TRACK"]


async def test_loop_rejects_unknown_modes():
    session = RecordingSession()
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.loop, cog, ctx, mode="bogus")

    assert session is not None
    assert session.calls == []
    assert ctx.sent == ["Modo de loop inválido. Use off, track ou queue."]


async def test_volume_shows_the_current_level():
    session = RecordingSession()
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.volume, cog, ctx, level=None)

    assert session is not None
    assert session.calls == []
    assert ctx.sent == ["Volume atual: 0.70"]


async def test_volume_sets_and_reports_the_new_level():
    session = RecordingSession()
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.volume, cog, ctx, level="1.5")

    assert session is not None
    assert session.calls == ["volume:1.5"]
    assert ctx.sent == ["Volume definido para 1.50"]


async def test_pause_routes_through_the_session():
    session = RecordingSession()
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.pause, cog, ctx)

    assert session is not None
    assert session.calls == ["pause"]
    assert ctx.sent == ["Música pausada"]


async def test_resume_routes_through_the_session():
    session = RecordingSession()
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.resume, cog, ctx)

    assert session is not None
    assert session.calls == ["resume"]
    assert ctx.sent == ["Música retomada"]


async def test_list_renders_the_current_track_and_queue():
    session = RecordingSession()
    session.current_music = SimpleNamespace(title="one", duration=180)
    session.queue = (SimpleNamespace(title="two", duration=60),)
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.list_queue, cog, ctx)

    assert session is not None
    assert ctx.sent == [
        "**Tocando agora:** one (180)\n**Próximas na fila:**\n1. two (60)"
    ]


async def test_join_connects_through_the_manager():
    session = RecordingSession()
    cog, session, ctx = _make_cog(session)
    manager = cast(RecordingManager, cog.bot.sessions)

    await _invoke(cog.join, cog, ctx)

    assert session is not None
    assert manager.calls == ["connect:1:10"]
    assert ctx.sent[0].startswith("Conectado e pronto!")


async def test_disconnect_goes_through_the_manager():
    session = RecordingSession()
    cog, _, ctx = _make_cog(session)
    manager = cast(RecordingManager, cog.bot.sessions)

    await _invoke(cog.disconnect, cog, ctx)

    assert manager.calls == ["disconnect:1"]
    assert ctx.sent == ["Desconectado do canal de voz"]


async def test_command_requires_the_user_to_be_in_voice():
    session = RecordingSession()
    cog, session, ctx = _make_cog(session)
    ctx.author = SimpleNamespace(voice=None)

    with pytest.raises(Exception):
        await _invoke(cog.stop, cog, ctx)

    assert session is not None
    assert session.calls == []


# --- Background layer commands ---


async def test_add_layer_routes_through_the_session_and_binds_the_announcer():
    session = RecordingSession()
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.add_layer, cog, ctx, link="rain")

    assert session is not None
    assert session.calls == ["add_layer:rain"]
    assert [layer.id for layer in session.layers] == ["layer-rain"]
    announcer = session.announcer
    assert announcer is not None
    assert announcer == ctx.send
    assert ctx.sent == ["Adicionado **rain** ao mixer."]


async def test_add_layer_connects_when_there_is_no_session_yet():
    session = RecordingSession()
    cog, _, ctx = _make_cog(session)

    await _invoke(cog.add_layer, cog, ctx, link="rain")

    assert session.calls == ["add_layer:rain"]


async def test_add_layer_reports_when_nothing_is_found():
    session = RecordingSession()
    session.add_layer_error = ValueError(
        "Nenhuma música encontrada para este link"
    )
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.add_layer, cog, ctx, link="nothing")

    assert session is not None
    assert session.calls == []
    assert ctx.sent == ["Nenhuma música encontrada para este link"]


async def test_remove_layer_routes_through_the_session_by_index():
    session = RecordingSession()
    session.layers = [SimpleNamespace(id="layer-rain", title="rain")]
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.remove_layer, cog, ctx, index=1)

    assert session is not None
    assert session.calls == ["remove_layer:layer-rain"]
    assert session.layers == []
    assert ctx.sent == ["Layer removido: rain"]


async def test_remove_layer_rejects_out_of_range_indices():
    session = RecordingSession()
    session.layers = [SimpleNamespace(id="layer-rain", title="rain")]
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.remove_layer, cog, ctx, index=2)

    assert session is not None
    assert session.calls == []
    assert ctx.sent == ["Layer inválido."]


async def test_remove_layer_without_a_session_tells_the_user():
    cog, _, ctx = _make_cog(None)

    await _invoke(cog.remove_layer, cog, ctx, index=1)

    assert ctx.sent == ["Guilda não conectada"]


async def test_clean_layers_routes_through_the_session():
    session = RecordingSession()
    session.layers = [SimpleNamespace(id="layer-rain", title="rain")]
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.clean_layers, cog, ctx)

    assert session is not None
    assert session.calls == ["clear_layers"]
    assert session.layers == []
    assert ctx.sent == ["Layers de áudio de fundo limpos."]


async def test_clean_layers_without_a_session_tells_the_user():
    cog, _, ctx = _make_cog(None)

    await _invoke(cog.clean_layers, cog, ctx)

    assert ctx.sent == ["Guilda não conectada"]


async def test_list_layers_renders_every_layer():
    session = RecordingSession()
    session.layers = [
        SimpleNamespace(id="layer-rain", title="rain"),
        SimpleNamespace(id="layer-wind", title="wind"),
    ]
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.list_layers, cog, ctx)

    assert session is not None
    assert session.calls == []
    assert ctx.sent == ["**Layers de áudio de fundo:**\n1. rain\n2. wind"]


async def test_list_layers_reports_when_there_are_no_layers():
    session = RecordingSession()
    cog, session, ctx = _make_cog(session)

    await _invoke(cog.list_layers, cog, ctx)

    assert session is not None
    assert session.calls == []
    assert ctx.sent == ["Nenhum layer de áudio de fundo adicionado"]


async def test_list_layers_without_a_session_tells_the_user():
    cog, _, ctx = _make_cog(None)

    await _invoke(cog.list_layers, cog, ctx)

    assert ctx.sent == ["Guilda não conectada"]
