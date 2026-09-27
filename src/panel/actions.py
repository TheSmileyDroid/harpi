from __future__ import annotations

from typing import Any

from src.bot_state import get_bot, run_on_bot_loop
from src.harpi_lib.audio.session import LOOP_MODE_ALIASES, PlaybackSession
from src.harpi_lib.music.ytmusic import YTMusicData
from src.panel import serialization

SEARCH_RESULT_LIMIT = 5

_ALL_SKIPPED_WARNING = (
    "As faixas foram adicionadas, mas nenhuma pôde ser tocada. "
    "O motivo foi anunciado no canal do Discord."
)


def _session(guild_id: int) -> PlaybackSession:
    session_obj = get_bot().sessions.get(guild_id)
    if session_obj is None:
        raise ValueError("Não conectado a um canal de voz")
    return session_obj


def require_session(guild_id: int) -> None:
    _session(guild_id)


async def connect(guild_id: int, channel_id: int) -> None:
    await run_on_bot_loop(get_bot().sessions.connect(guild_id, channel_id))


async def disconnect(guild_id: int) -> None:
    await run_on_bot_loop(get_bot().sessions.disconnect(guild_id))


async def search(
    term: str, track_source: type[YTMusicData] = YTMusicData
) -> list[dict[str, Any]]:
    term = term.strip()
    if not term:
        return []
    results = await track_source.from_url(term)
    if not results:
        raise ValueError("Nenhuma música encontrada para esta busca")
    return [
        serialization.track_data(track)
        for track in results[:SEARCH_RESULT_LIMIT]
    ]


async def _skipped_warning(session_obj: PlaybackSession) -> str | None:
    status = await run_on_bot_loop(session_obj.sample_status())
    if status.current_music is None and not status.queue:
        return _ALL_SKIPPED_WARNING
    return None


async def add_track(guild_id: int, link: str | None) -> str | None:
    session_obj = _session(guild_id)
    if link:
        await run_on_bot_loop(session_obj.play(link))
    return await _skipped_warning(session_obj)


async def add_layer(guild_id: int, link: str | None) -> str | None:
    session_obj = _session(guild_id)
    if not link:
        return None
    return await run_on_bot_loop(session_obj.add_layer(link))


async def remove_track(guild_id: int, url: str | None) -> bool:
    session_obj = _session(guild_id)
    if not url:
        return False
    return await run_on_bot_loop(session_obj.remove(url))


async def remove_layer(guild_id: int, layer_id: str | None) -> bool:
    session_obj = _session(guild_id)
    if not layer_id:
        return False
    return await run_on_bot_loop(session_obj.remove_layer(layer_id))


async def clear_queue(guild_id: int) -> None:
    await run_on_bot_loop(_session(guild_id).clear_queue())


async def stop(guild_id: int) -> None:
    await run_on_bot_loop(_session(guild_id).stop())


async def clear_layers(guild_id: int) -> None:
    await run_on_bot_loop(_session(guild_id).clear_layers())


async def toggle_pause(guild_id: int) -> None:
    await run_on_bot_loop(_session(guild_id).toggle_pause())


async def pause(guild_id: int) -> None:
    await run_on_bot_loop(_session(guild_id).pause())


async def resume(guild_id: int) -> None:
    await run_on_bot_loop(_session(guild_id).resume())


async def skip(guild_id: int) -> None:
    await run_on_bot_loop(_session(guild_id).skip())


async def previous(guild_id: int) -> None:
    await run_on_bot_loop(_session(guild_id).previous())


async def set_loop(guild_id: int, mode: str | None) -> None:
    session_obj = _session(guild_id)
    if not mode:
        return
    loop_mode = LOOP_MODE_ALIASES.get(mode)
    if loop_mode is None:
        raise ValueError("Modo de loop inválido")
    await run_on_bot_loop(session_obj.set_loop(loop_mode))


async def set_volume(guild_id: int, volume: float | None) -> None:
    session_obj = _session(guild_id)
    if volume is None:
        return
    await run_on_bot_loop(session_obj.set_volume(volume))


async def set_layer_volume(
    guild_id: int, layer_id: str, volume: float | None
) -> bool:
    session_obj = _session(guild_id)
    if volume is None:
        return False
    return await run_on_bot_loop(
        session_obj.set_layer_volume(layer_id, volume)
    )


async def seek(guild_id: int, position: float | None) -> None:
    session_obj = _session(guild_id)
    if position is None:
        return
    await _reject_seek_out_of_range(session_obj, position)
    await run_on_bot_loop(session_obj.seek(position, absolute=True))


async def _reject_seek_out_of_range(
    session_obj: PlaybackSession, target: float
) -> None:
    status = await run_on_bot_loop(session_obj.sample_status())
    current = status.current_music if status else None
    duration = current.duration if current else 0
    if duration and not 0 <= target <= duration:
        raise ValueError("Posição fora da duração da faixa")
