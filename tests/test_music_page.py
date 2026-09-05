"""Web-route tests for the music page.

These drive ``pages.music`` through Quart's test client with a fake bot,
asserting external behaviour: what the rendered HTML contains and which
session verb a POST action reaches.  They do not inspect route internals.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, cast

# pi-lens-ignore: reportMissingImports
import pytest

from app import app as quart_app
from pages.music import looks_like_url
from src import bot_state as deps
from src.harpi_lib.audio.session import LayerInfo, LoopMode, SessionStatus
from src.harpi_lib.harpi_bot import HarpiBot
from src.harpi_lib.music.ytmusic import YTMusicData

GUILD_A = 1
GUILD_B = 2


@dataclass
class FakeVoiceChannel:
    id: int
    name: str


class FakeGuild:
    def __init__(self, guild_id: int, name: str) -> None:
        self.id = guild_id
        self.name = name
        self.voice_channels = [
            FakeVoiceChannel(guild_id * 10, f"Channel {guild_id}")
        ]


class FakeSession:
    def __init__(self, status: SessionStatus | None = None) -> None:
        self._status = status
        self.calls: list[Any] = []

    async def sample_status(self) -> SessionStatus | None:
        return self._status

    async def toggle_pause(self) -> None:
        self.calls.append("toggle_pause")

    async def skip(self) -> None:
        self.calls.append("skip")

    async def stop(self) -> None:
        self.calls.append("stop")

    async def clear_queue(self) -> None:
        self.calls.append("clear_queue")

    async def remove(self, value: str) -> None:
        self.calls.append(("remove", value))

    async def clear_layers(self) -> None:
        self.calls.append("clear_layers")

    async def remove_layer(self, value: str) -> None:
        self.calls.append(("remove_layer", value))

    async def add_layer(self, value: str) -> None:
        self.calls.append(("add_layer", value))

    async def play(self, value: str) -> None:
        self.calls.append(("play", value))
        # The real session starts the added track when idle; the panel's
        # skipped-tracks warning keys off that, so the fake mirrors it.
        self._status = SessionStatus(
            guild_id=GUILD_A,
            connected=True,
            is_playing=True,
            is_paused=False,
            current_music=YTMusicData({
                "title": value,
                "url": value,
                "duration": 60,
            }),
        )

    async def seek(self, value: float, absolute: bool = False) -> None:
        self.calls.append(("seek", value, absolute))

    async def set_volume(self, value: float) -> None:
        self.calls.append(("set_volume", value))

    async def set_layer_volume(self, layer_id: str, value: float) -> None:
        self.calls.append(("set_layer_volume", layer_id, value))

    async def previous(self) -> None:
        self.calls.append("previous")


class FakeSessionManager:
    def __init__(self, session: FakeSession | None = None) -> None:
        self._session = session
        self.connect_calls: list[tuple[int, int]] = []
        self.disconnect_calls: list[int] = []

    def get(self, _guild_id: int) -> FakeSession | None:
        return self._session

    async def connect(self, guild_id: int, channel_id: int) -> None:
        self.connect_calls.append((guild_id, channel_id))

    async def disconnect(self, guild_id: int) -> None:
        self.disconnect_calls.append(guild_id)


class FakeBot:
    def __init__(
        self,
        guilds: list[FakeGuild],
        session: FakeSession | None = None,
    ) -> None:
        self.user = SimpleNamespace(id=1234)
        self._guilds = {g.id: g for g in guilds}
        self.sessions = FakeSessionManager(session)

    @property
    def loop(self):
        return asyncio.get_running_loop()

    def get_guild(self, guild_id: int) -> FakeGuild | None:
        return self._guilds.get(guild_id)

    async def fetch_guilds(self, limit: int | None = None):
        del limit
        for guild in self._guilds.values():
            yield guild


GUILD_C = 3


def playing_status(**overrides: Any) -> SessionStatus:
    values: dict[str, Any] = {
        "guild_id": GUILD_A,
        "connected": True,
        "is_playing": True,
        "is_paused": False,
        "current_music": YTMusicData({
            "title": "Now Track",
            "uploader": "Artist",
            "duration": 120,
        }),
        "loop_mode": LoopMode.OFF,
        "volume": 0.7,
        "progress": 0.0,
    }
    values.update(overrides)
    return SessionStatus(**values)


async def render_queue(client, bot: FakeBot, status: SessionStatus) -> str:
    bot.sessions._session = FakeSession(status)
    # Throwaway GET: guild selection lives in the session cookie/server
    # state, so the queue-targeted fragment below only renders a queue
    # once a guild has been selected first.
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )
    response = await client.get(
        "/music", headers={"HX-Request": "true", "HX-Target": "queue"}
    )
    assert response.status_code == 200
    return (await response.get_data()).decode()


async def test_music_page_has_no_stale_font_references(client, bot):
    response = await client.get(f"/music?guild_id={GUILD_A}")

    body = (await response.get_data()).decode()
    assert "Fira+Code" not in body
    assert "Share+Tech+Mono" not in body


async def test_resting_music_page_carries_no_bracket_classes(client, bot):
    bot.sessions._session = FakeSession()

    response = await client.get(f"/music?guild_id={GUILD_A}")

    body = (await response.get_data()).decode()
    assert "hud-brackets" not in body
    assert "is-playing" not in body


async def test_now_playing_is_bracketed_only_while_playing(client, bot):
    bot.sessions._session = FakeSession(playing_status())
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    playing = await client.get(
        "/music", headers={"HX-Request": "true", "HX-Target": "now_playing"}
    )
    playing_body = (await playing.get_data()).decode()
    assert 'id="now_playing"' in playing_body
    assert "is-playing" in playing_body

    bot.sessions._session = FakeSession(
        playing_status(is_playing=False, is_paused=True)
    )
    paused = await client.get(
        "/music", headers={"HX-Request": "true", "HX-Target": "now_playing"}
    )
    paused_body = (await paused.get_data()).decode()
    assert 'id="now_playing"' in paused_body
    assert "is-playing" not in paused_body


async def test_queue_rows_carry_a_right_hand_metadata_column(client, bot):
    body = await render_queue(
        client,
        bot,
        playing_status(
            queue=(
                YTMusicData({
                    "title": "Queued One",
                    "url": "u1",
                    "duration": 61,
                }),
            ),
        ),
    )

    assert "queue-row" in body
    assert "row-meta" in body
    assert "1:01" in body


async def test_now_playing_payload_carries_the_track_thumbnail(client, bot):
    bot.sessions._session = FakeSession(
        playing_status(
            current_music=YTMusicData({
                "title": "Now Track",
                "uploader": "Artist",
                "duration": 120,
                "thumbnails": [
                    {
                        "url": "https://img.example.com/now.jpg",
                        "width": 336,
                    }
                ],
            })
        )
    )
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    response = await client.get(
        "/music", headers={"HX-Request": "true", "HX-Target": "now_playing"}
    )

    body = (await response.get_data()).decode()
    assert 'data-thumbnail="https://img.example.com/now.jpg"' in body


async def test_queue_payload_carries_each_track_thumbnail(client, bot):
    body = await render_queue(
        client,
        bot,
        playing_status(
            queue=(
                YTMusicData({
                    "title": "Queued One",
                    "url": "u1",
                    "duration": 61,
                    "thumbnails": [
                        {
                            "url": "https://img.example.com/queued.jpg",
                            "width": 336,
                        }
                    ],
                }),
            ),
        ),
    )

    assert 'data-thumbnail="https://img.example.com/queued.jpg"' in body


async def test_layers_payload_carries_the_layer_thumbnail(client, bot):
    bot.sessions._session = FakeSession(
        SessionStatus(
            guild_id=GUILD_A,
            connected=True,
            is_playing=True,
            is_paused=False,
            layers=(
                LayerInfo(
                    id="l1",
                    title="Layer One",
                    url="u",
                    volume=0.7,
                    thumbnail="https://img.example.com/layer.jpg",
                ),
            ),
            loop_mode=LoopMode.OFF,
            volume=0.7,
            progress=0.0,
        )
    )
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    response = await client.get(
        "/music", headers={"HX-Request": "true", "HX-Target": "layers"}
    )

    body = (await response.get_data()).decode()
    assert 'data-thumbnail="https://img.example.com/layer.jpg"' in body


async def render_layers(client, bot, status: SessionStatus) -> str:
    bot.sessions._session = FakeSession(status)
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )
    response = await client.get(
        "/music", headers={"HX-Request": "true", "HX-Target": "layers"}
    )
    assert response.status_code == 200
    return (await response.get_data()).decode()


async def render_now_playing(client, bot, status: SessionStatus) -> str:
    bot.sessions._session = FakeSession(status)
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )
    response = await client.get(
        "/music", headers={"HX-Request": "true", "HX-Target": "now_playing"}
    )
    assert response.status_code == 200
    return (await response.get_data()).decode()


def thumb_url(name: str) -> str:
    return f"https://img.example.com/{name}.jpg"


async def test_queue_rows_render_a_small_thumbnail_image(client, bot):
    body = await render_queue(
        client,
        bot,
        playing_status(
            queue=(
                YTMusicData({
                    "title": "Queued One",
                    "url": "u1",
                    "duration": 61,
                    "thumbnails": [{"url": thumb_url("queued"), "width": 336}],
                }),
            ),
        ),
    )

    collapsed = " ".join(body.split())
    assert '<img class="row-thumb"' in collapsed
    assert f'src="{thumb_url("queued")}"' in collapsed
    assert 'width="48"' in collapsed
    assert 'height="48"' in collapsed


async def test_queue_rows_render_a_placeholder_when_there_is_no_thumbnail(
    client, bot
):
    body = await render_queue(
        client,
        bot,
        playing_status(
            queue=(YTMusicData({"title": "Queued One", "url": "u1"}),),
        ),
    )

    collapsed = " ".join(body.split())
    assert '<span class="row-thumb thumb-empty"' in collapsed
    assert "<img" not in body


async def test_layer_rows_render_a_small_thumbnail_image(client, bot):
    body = await render_layers(
        client,
        bot,
        playing_status(
            layers=(
                LayerInfo(
                    id="l1",
                    title="Layer One",
                    url="u",
                    volume=0.7,
                    thumbnail=thumb_url("layer"),
                ),
            ),
        ),
    )

    collapsed = " ".join(body.split())
    assert '<img class="row-thumb"' in collapsed
    assert f'src="{thumb_url("layer")}"' in collapsed


async def test_layer_rows_render_a_placeholder_when_there_is_no_thumbnail(
    client, bot
):
    body = await render_layers(
        client,
        bot,
        playing_status(
            layers=(
                LayerInfo(id="l1", title="Layer One", url="u", volume=0.7),
            ),
        ),
    )

    collapsed = " ".join(body.split())
    assert '<span class="row-thumb thumb-empty"' in collapsed
    assert "<img" not in body


async def test_search_row_renders_a_placeholder_when_there_is_no_thumbnail(
    client, bot, monkeypatch
):
    patch_search(monkeypatch, [found_track(thumbnails=[])])
    await client.get(f"/music?guild_id={GUILD_A}")
    response = await client.post(
        "/music",
        form={"action": "search", "value": "found track"},
        headers={"HX-Request": "true", "HX-Target": "search_dropdown"},
    )

    body = (await response.get_data()).decode()
    collapsed = " ".join(body.split())
    assert '<span class="search-thumb thumb-empty"' in collapsed
    assert "<img" not in body


async def test_now_playing_renders_the_large_square_art(client, bot):
    body = await render_now_playing(
        client,
        bot,
        playing_status(
            current_music=YTMusicData({
                "title": "Now Track",
                "uploader": "Artist",
                "duration": 120,
                "thumbnails": [{"url": thumb_url("now"), "width": 336}],
            })
        ),
    )

    collapsed = " ".join(body.split())
    assert '<img class="now-playing-art"' in collapsed
    assert f'src="{thumb_url("now")}"' in collapsed
    # Title/uploader/duration sit below the art, and the art carries a
    # meaningful alt.
    assert 'alt="Now Track"' in collapsed
    assert "Artist" in body
    assert "2:00" in body


async def test_now_playing_renders_a_placeholder_when_there_is_no_art(
    client, bot
):
    body = await render_now_playing(client, bot, playing_status())

    collapsed = " ".join(body.split())
    assert '<span class="now-playing-art thumb-empty"' in collapsed
    assert "<img" not in body


async def test_now_playing_art_src_is_stable_across_polls(client, bot):
    # The status poll re-renders this fragment every 2s/500ms; the art
    # must point at the same URL every time so the browser cache keeps
    # the image up and the swap never flickers.
    status = playing_status(
        current_music=YTMusicData({
            "title": "Now Track",
            "uploader": "Artist",
            "duration": 120,
            "thumbnails": [{"url": thumb_url("now"), "width": 336}],
        })
    )
    first = await render_now_playing(client, bot, status)
    second = await render_now_playing(client, bot, status)

    assert f'src="{thumb_url("now")}"' in first
    assert f'src="{thumb_url("now")}"' in second


def found_track(**overrides: Any) -> YTMusicData:
    values: dict[str, Any] = {
        "title": "Found Track",
        "url": "https://www.youtube.com/watch?v=found",
        "uploader": "Artist",
        "duration": 30,
        "thumbnails": [
            {"url": "https://img.example.com/found.jpg", "width": 336}
        ],
    }
    values.update(overrides)
    return YTMusicData(values)


def patch_search(monkeypatch, results: list[YTMusicData]) -> None:
    async def fake_from_url(term: str) -> list[YTMusicData]:
        return results

    monkeypatch.setattr(YTMusicData, "from_url", staticmethod(fake_from_url))


async def search_dropdown_response(client, monkeypatch, term: str) -> str:
    patch_search(monkeypatch, [found_track()])
    await client.get(f"/music?guild_id={GUILD_A}")
    response = await client.post(
        "/music",
        form={"action": "search", "value": term},
        headers={"HX-Request": "true", "HX-Target": "search_dropdown"},
    )
    assert response.status_code == 200
    return (await response.get_data()).decode()


@pytest.mark.parametrize(
    "term",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "http://youtu.be/dQw4w9WgXcQ",
        "  https://www.youtube.com/watch?v=x  ",
    ],
)
def test_looks_like_url_accepts_pasted_links(term: str):
    assert looks_like_url(term)


@pytest.mark.parametrize(
    "term", ["daft punk", "warriors remix", "ace of base"]
)
def test_looks_like_url_rejects_search_terms(term: str):
    assert not looks_like_url(term)


async def test_pasted_url_skips_the_dropdown_and_goes_to_the_queue(
    client, bot, monkeypatch
):
    async def offline_from_url(term: str) -> list[YTMusicData]:
        raise RuntimeError("network touched")

    monkeypatch.setattr(
        YTMusicData, "from_url", staticmethod(offline_from_url)
    )
    session = FakeSession()
    bot.sessions._session = session
    url = "https://www.youtube.com/watch?v=direct"
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": "search", "value": url},
        headers={"HX-Request": "true", "HX-Target": "search_dropdown"},
    )

    body = (await response.get_data()).decode()
    assert ("play", url) in session.calls
    assert "search-row" not in body


async def test_search_dropdown_renders_rows_with_metadata_and_actions(
    client, bot, monkeypatch
):
    body = await search_dropdown_response(client, monkeypatch, "found track")

    assert "search-row" in body
    assert "Found Track" in body
    assert "Artist" in body
    assert "0:30" in body
    assert 'data-thumbnail="https://img.example.com/found.jpg"' in body
    assert "QUEUE" in body
    assert "LAYER" in body


async def test_search_dropdown_row_actions_keep_queue_and_layer_semantics(
    client, bot, monkeypatch
):
    body = await search_dropdown_response(client, monkeypatch, "found track")
    collapsed = " ".join(body.split())

    assert 'name="action" value="add"' in collapsed
    assert 'name="action" value="add_layer"' in collapsed
    assert (
        'name="value" value="https://www.youtube.com/watch?v=found"'
        in collapsed
    )


async def test_search_dropdown_row_shows_the_thumbnail_image(
    client, bot, monkeypatch
):
    body = await search_dropdown_response(client, monkeypatch, "found track")
    collapsed = " ".join(body.split())

    assert '<img class="search-thumb"' in collapsed
    assert 'src="https://img.example.com/found.jpg"' in collapsed


async def test_search_results_carry_a_thumbnail(client, bot, monkeypatch):
    patch_search(monkeypatch, [found_track()])
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": "search", "value": "Found Track"},
        headers={"HX-Request": "true", "HX-Target": "search_dropdown"},
    )

    body = (await response.get_data()).decode()
    assert 'data-thumbnail="https://img.example.com/found.jpg"' in body


async def test_full_page_ships_the_search_dropdown_shell(client, bot):
    response = await client.get(f"/music?guild_id={GUILD_A}")

    body = (await response.get_data()).decode()
    assert 'id="search_dropdown"' in body
    assert 'id="search-input"' in body
    assert "delay:300ms" in body


async def test_seek_posts_an_absolute_position(client, bot):
    bot.sessions._session = FakeSession(playing_status())
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": "seek", "value": "30"},
        headers={"HX-Request": "true", "HX-Target": "transport"},
    )

    assert response.status_code == 200
    assert bot.sessions._session.calls == [("seek", 30.0, True)]


async def test_seek_rejects_a_target_outside_the_track_duration(client, bot):
    bot.sessions._session = FakeSession(playing_status())
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": "seek", "value": "999"},
        headers={"HX-Request": "true", "HX-Target": "transport"},
    )

    assert response.status_code == 200
    assert (
        '<div id="panel_error" hx-swap-oob="true">'
        in await response.get_data(as_text=True)
    )
    assert bot.sessions._session.calls == []


async def test_seek_accepts_the_exact_track_duration(client, bot):
    bot.sessions._session = FakeSession(playing_status())
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": "seek", "value": "120"},
        headers={"HX-Request": "true", "HX-Target": "transport"},
    )

    assert response.status_code == 200
    assert bot.sessions._session.calls == [("seek", 120.0, True)]


async def _transport_fragment(
    client, bot, status: SessionStatus | None
) -> str:
    bot.sessions._session = FakeSession(status)
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )
    response = await client.get(
        "/music", headers={"HX-Request": "true", "HX-Target": "transport"}
    )
    assert response.status_code == 200
    return (await response.get_data()).decode()


async def test_transport_polls_fast_while_playing(client, bot):
    body = await _transport_fragment(client, bot, playing_status())

    assert 'hx-trigger="every 500ms"' in body


@pytest.mark.parametrize(
    "status",
    [
        playing_status(is_playing=False, is_paused=True),
        None,
    ],
    ids=["paused", "no-session"],
)
async def test_transport_polls_slow_off_the_playing_state(client, bot, status):
    body = await _transport_fragment(client, bot, status)

    assert 'hx-trigger="every 2s"' in body


@pytest.mark.parametrize(
    "status",
    [
        playing_status(),
        playing_status(is_playing=False, is_paused=True),
    ],
    ids=["playing", "paused"],
)
async def test_transport_poll_stays_a_background_poller(client, bot, status):
    # design.md: the global indicator excludes triggers containing
    # "every"; the adaptive interval must never drop that keyword.
    body = await _transport_fragment(client, bot, status)

    assert "every" in body


async def test_transport_exposes_the_preview_readout_times(client, bot):
    body = await _transport_fragment(client, bot, playing_status())

    assert "progress-times" in body
    assert 'data-duration="120"' in body


async def test_transport_seek_bar_is_clickable_without_a_relative_input(
    client, bot
):
    bot.sessions._session = FakeSession(playing_status())
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    fragment = await client.get(
        "/music", headers={"HX-Request": "true", "HX-Target": "transport"}
    )
    full = await client.get(f"/music?guild_id={GUILD_A}")

    fragment_body = (await fragment.get_data()).decode()
    full_body = (await full.get_data()).decode()
    # The numeric ±s input is gone; the bar itself is the seek surface and
    # carries the track duration so the click handler can compute the
    # absolute target.
    assert 'id="transport-seek"' not in fragment_body
    assert "± s" not in fragment_body
    assert 'data-duration="120"' in fragment_body
    # The click handler must survive the 2s transport poll swap, so the
    # script lives outside every swapped region and binds exactly once.
    assert full_body.count('id="progress-seek-script"') == 1
    assert 'id="progress-seek-script"' not in fragment_body


async def test_transport_carries_a_volume_slider_with_the_current_value(
    client, bot
):
    body = await _transport_fragment(client, bot, playing_status())
    collapsed = " ".join(body.split())

    assert 'id="transport-volume"' in collapsed
    assert 'type="range"' in collapsed
    assert 'min="0"' in collapsed
    assert 'max="1"' in collapsed
    assert 'step="0.01"' in collapsed
    assert 'name="value"' in collapsed
    assert 'value="0.84"' in collapsed
    assert 'name="action" value="set_volume"' in collapsed
    # The numeric ±0.1 input and its VOL button are gone.
    assert 'type="number"' not in collapsed
    assert ">VOL<" not in collapsed


async def test_transport_volume_slider_is_hx_preserved(client, bot):
    body = await _transport_fragment(client, bot, playing_status())
    collapsed = " ".join(body.split())

    form = collapsed.split('id="transport-volume"')[1]
    form = form[: form.index(">")]
    assert "hx-preserve" in form, (
        "the volume slider sits inside the transport poll swap region; "
        "without hx-preserve the 2s poll would wipe it mid-drag"
    )


async def test_volume_script_binds_once_outside_the_swap_region(client, bot):
    full = await client.get(f"/music?guild_id={GUILD_A}")
    fragment = await _transport_fragment(client, bot, playing_status())

    full_body = (await full.get_data()).decode()
    assert full_body.count('id="volume-slider-script"') == 1
    # The script lives outside every swapped region so the poll never
    # wipes (or doubles) its listeners.
    assert 'id="volume-slider-script"' not in fragment


async def test_now_playing_no_longer_repeats_the_volume_text(client, bot):
    bot.sessions._session = FakeSession(playing_status())
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    response = await client.get(
        "/music", headers={"HX-Request": "true", "HX-Target": "now_playing"}
    )

    body = (await response.get_data()).decode()
    assert "VOLUME" not in body


async def test_transport_uses_the_segmented_action_strip(client, bot):
    bot.sessions._session = FakeSession(playing_status())
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    response = await client.get(
        "/music", headers={"HX-Request": "true", "HX-Target": "transport"}
    )

    body = (await response.get_data()).decode()
    assert "action-strip" in body


@pytest.fixture
def bot() -> FakeBot:
    return FakeBot([
        FakeGuild(GUILD_A, "Alpha Guild"),
        FakeGuild(GUILD_B, "Beta Guild"),
    ])


@pytest.fixture
def client(bot: FakeBot):
    os.environ["DISCORD_TOKEN"] = "test"
    os.environ["SECRET_KEY"] = "test-secret"
    quart_app.secret_key = "test-secret"
    quart_app.config["TESTING"] = True
    deps.init_bot(cast(HarpiBot, bot))
    yield quart_app.test_client()
    deps._bot_ref = None


async def test_full_page_renders_guilds_and_status(client, bot: FakeBot):
    bot.sessions._session = FakeSession(
        SessionStatus(
            guild_id=GUILD_A,
            connected=True,
            is_playing=True,
            is_paused=False,
            current_music=YTMusicData({
                "title": "Now Track",
                "uploader": "Artist",
                "duration": 120,
            }),
            loop_mode=LoopMode.OFF,
            volume=0.7,
            progress=0.0,
        )
    )

    response = await client.get(f"/music?guild_id={GUILD_A}")

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "Alpha Guild" in body
    assert "Beta Guild" in body
    assert "Now Track" in body
    assert "No active session." not in body


async def test_guild_list_reflects_bot_changes_between_requests(
    client, bot: FakeBot
):
    response = await client.get("/music")
    body = (await response.get_data()).decode()
    assert "Alpha Guild" in body
    assert "Beta Guild" in body

    # Bot joins a new guild and one disappears.
    bot._guilds.pop(GUILD_B)
    bot._guilds[GUILD_C] = FakeGuild(GUILD_C, "Gamma Guild")

    response = await client.get("/music")
    body = (await response.get_data()).decode()
    assert "Alpha Guild" in body
    assert "Gamma Guild" in body
    assert "Beta Guild" not in body


async def test_stale_guild_cookie_renders_as_no_selection(client, bot):
    # A cookie pointing at a guild the bot can no longer see must not
    # render as a selection: no guild matched in the select, no channel
    # list, no disconnect button, and the cookie is cleared so the
    # broken link line never comes back.
    async with client.session_transaction() as sess:
        sess["guild_id"] = "99999"

    response = await client.get("/music")
    body = (await response.get_data()).decode()

    assert response.status_code == 200
    assert "selected>Guild" not in body  # no guild pre-selected
    assert 'value="99999"' not in body
    assert ">Disconnect<" not in body
    async with client.session_transaction() as sess:
        assert "guild_id" not in sess


async def test_unknown_guild_in_the_query_is_never_stored(client, bot):
    await client.get("/music?guild_id=99999")

    async with client.session_transaction() as sess:
        assert "guild_id" not in sess


async def test_search_renders_above_the_panels(client, bot: FakeBot):
    # The spec puts the single search right under the link line, before
    # the now playing / side panel grid; the dropdown opens downward
    # from the top instead of colliding with the fixed transport.
    response = await client.get("/music")
    body = (await response.get_data()).decode()

    assert body.index('id="search"') < body.index('id="status_panels"')


async def test_selector_branch_lists_guild_channels_and_persists_selection(
    client,
):
    response = await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "Channel 1" in body
    assert "MUSIC CONTROL" not in body

    full = await client.get("/music")
    full_body = (await full.get_data()).decode()
    assert "Channel 1" in full_body


async def test_now_playing_branch_renders_status_block_only(client, bot):
    bot.sessions._session = FakeSession(
        SessionStatus(
            guild_id=GUILD_A,
            connected=True,
            is_playing=True,
            is_paused=False,
            current_music=YTMusicData({
                "title": "Now Track",
                "uploader": "Artist",
                "duration": 120,
            }),
            loop_mode=LoopMode.OFF,
            volume=0.7,
            progress=0.0,
        )
    )
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    response = await client.get(
        "/music",
        headers={"HX-Request": "true", "HX-Target": "now_playing"},
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "Now Track" in body
    assert "MUSIC CONTROL" not in body


async def test_queue_branch_renders_queue_items(client, bot):
    bot.sessions._session = FakeSession(
        SessionStatus(
            guild_id=GUILD_A,
            connected=True,
            is_playing=True,
            is_paused=False,
            queue=(YTMusicData({"title": "Queued One", "url": "u1"}),),
            loop_mode=LoopMode.OFF,
            volume=0.7,
            progress=0.0,
        )
    )
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    response = await client.get(
        "/music",
        headers={"HX-Request": "true", "HX-Target": "queue"},
    )

    body = (await response.get_data()).decode()
    assert "Queued One" in body
    assert "MUSIC CONTROL" not in body


async def test_layers_branch_renders_layers(client, bot):
    bot.sessions._session = FakeSession(
        SessionStatus(
            guild_id=GUILD_A,
            connected=True,
            is_playing=True,
            is_paused=False,
            layers=(
                LayerInfo(id="l1", title="Layer One", url="u", volume=0.7),
            ),
            loop_mode=LoopMode.OFF,
            volume=0.7,
            progress=0.0,
        )
    )
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    response = await client.get(
        "/music",
        headers={"HX-Request": "true", "HX-Target": "layers"},
    )

    body = (await response.get_data()).decode()
    assert "Layer One" in body
    assert "MUSIC CONTROL" not in body


async def test_status_panels_branch_renders_the_wrapped_panels(client, bot):
    bot.sessions._session = FakeSession(
        SessionStatus(
            guild_id=GUILD_A,
            connected=True,
            is_playing=True,
            is_paused=False,
            current_music=YTMusicData({
                "title": "Now Track",
                "uploader": "Artist",
                "duration": 120,
            }),
            loop_mode=LoopMode.OFF,
            volume=0.7,
            progress=0.0,
        )
    )
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    response = await client.get(
        "/music",
        headers={"HX-Request": "true", "HX-Target": "status_panels"},
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "Now Track" in body
    assert "MUSIC CONTROL" not in body


async def test_transport_branch_renders_formatted_progress(client, bot):
    bot.sessions._session = FakeSession(
        SessionStatus(
            guild_id=GUILD_A,
            connected=True,
            is_playing=True,
            is_paused=False,
            current_music=YTMusicData({
                "title": "Now Track",
                "uploader": "Artist",
                "duration": 754,
            }),
            loop_mode=LoopMode.OFF,
            volume=0.7,
            progress=213.0,
        )
    )
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    response = await client.get(
        "/music",
        headers={"HX-Request": "true", "HX-Target": "transport"},
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "3:33" in body
    assert "12:34" in body
    assert "0:03" not in body
    assert "MUSIC CONTROL" not in body


async def test_connect_action_dispatches_to_session_manager(client, bot):
    response = await client.post(
        "/music",
        form={"action": "connect", "guild_id": GUILD_A, "channel_id": 10},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert bot.sessions.connect_calls == [(GUILD_A, 10)]


async def test_disconnect_action_dispatches_to_session_manager(client, bot):
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": "disconnect"},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert bot.sessions.disconnect_calls == [GUILD_A]


@pytest.mark.parametrize(
    ("action", "value", "expected_call", "target"),
    [
        ("toggle_pause", None, "toggle_pause", "transport"),
        ("skip", None, "skip", "transport"),
        ("toggle_pause", None, "toggle_pause", ""),
        ("skip", None, "skip", ""),
        ("stop", None, "stop", ""),
        ("clear_queue", None, "clear_queue", ""),
        ("remove", "u1", ("remove", "u1"), ""),
        ("clear_layers", None, "clear_layers", ""),
        ("remove_layer", "l1", ("remove_layer", "l1"), ""),
        ("add", "search me", ("play", "search me"), ""),
    ],
)
async def test_action_posts_dispatch_to_session(
    client, bot, action: str, value: str | None, expected_call, target: str
):
    session = FakeSession()
    bot.sessions._session = session
    await client.get(f"/music?guild_id={GUILD_A}")

    data = {"action": action}
    if value is not None:
        data["value"] = value
    headers = {"HX-Request": "true"}
    if target:
        headers["HX-Target"] = target
    await client.post("/music", form=data, headers=headers)

    assert expected_call in session.calls


async def test_non_htmx_post_returns_full_page(client, bot):
    bot.sessions._session = FakeSession()
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post("/music", form={"action": "toggle_pause"})

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "MUSIC CONTROL" in body
    assert bot.sessions._session.calls == ["toggle_pause"]


class ExplodingSessionManager(FakeSessionManager):
    async def connect(self, guild_id: int, channel_id: int) -> None:
        raise ValueError("Canal de voz não encontrado")


class FailingPlaySession(FakeSession):
    async def play(self, value: str) -> None:
        raise ValueError("yt explodiu")


async def test_add_without_session_reports_error(client, bot):
    bot.sessions._session = None
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": "add", "value": "warriors"},
        headers={"HX-Request": "true", "HX-Target": "queue"},
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "Não conectado a um canal de voz" in body
    assert '<div id="panel_error" hx-swap-oob="true">' in body


async def test_add_with_failing_play_surfaces_the_error(client, bot):
    bot.sessions._session = FailingPlaySession()
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": "add", "value": "warriors"},
        headers={"HX-Request": "true", "HX-Target": "queue"},
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "yt explodiu" in body
    assert '<div id="panel_error" hx-swap-oob="true">' in body


async def test_successful_add_leaves_the_error_region_empty(client, bot):
    bot.sessions._session = FakeSession()
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": "add", "value": "warriors"},
        headers={"HX-Request": "true", "HX-Target": "queue"},
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert '<div id="panel_error" hx-swap-oob="true">' in body
    assert "panel-error" not in body


async def test_failed_connect_reports_error_and_keeps_no_cookie(client, bot):
    bot.sessions = ExplodingSessionManager()

    response = await client.post(
        "/music",
        form={"action": "connect", "guild_id": GUILD_A, "channel_id": 11},
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "Canal de voz não encontrado" in body

    follow_up = await client.get("/music")
    follow_up_body = (await follow_up.get_data()).decode()
    assert "DISCONNECT" not in follow_up_body


async def test_selector_marks_the_connected_channel_selected(client, bot):
    bot.sessions._session = FakeSession(
        SessionStatus(
            guild_id=GUILD_A,
            connected=True,
            is_playing=False,
            is_paused=False,
            loop_mode=LoopMode.OFF,
            volume=0.7,
            progress=0.0,
            channel_id=10,
        )
    )

    response = await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    body = (await response.get_data()).decode()
    collapsed = " ".join(body.split())
    assert '<option value="10" selected >' in collapsed
    assert (
        "selected" not in collapsed.split('<option value="10" selected >')[1]
    )


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
async def test_seek_rejects_non_finite_values(client, bot, value: str):
    bot.sessions._session = FakeSession()
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": "seek", "value": value},
        headers={"HX-Request": "true", "HX-Target": "transport"},
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "Valor numérico inválido" in body


async def test_page_has_exactly_one_search_and_no_dead_quick_add(client, bot):
    response = await client.get(f"/music?guild_id={GUILD_A}")

    body = (await response.get_data()).decode()
    assert "04 // SEARCH" not in body
    assert body.count("Search YouTube or paste a URL") == 1
    assert 'id="queue-add"' not in body


async def test_selector_is_one_compact_line_with_disconnect(client, bot):
    response = await client.get(f"/music?guild_id={GUILD_A}")

    body = (await response.get_data()).decode()
    assert "00 // LINK" in body
    assert "Channel 1" in body
    assert "Connect" in body
    assert "Disconnect" in body


async def test_selector_hides_disconnect_without_a_selection(client):
    response = await client.get("/music")

    body = (await response.get_data()).decode()
    assert "Connect" in body
    assert "Disconnect" not in body


async def test_status_panels_is_a_grid_with_side_panel(client, bot):
    bot.sessions._session = FakeSession(playing_status())
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    response = await client.get(
        "/music", headers={"HX-Request": "true", "HX-Target": "status_panels"}
    )

    body = (await response.get_data()).decode()
    assert "music-grid" in body
    assert 'id="now_playing"' in body
    assert 'id="side_panel"' in body


async def test_side_panel_defaults_to_the_queue_tab(client, bot):
    response = await client.get(f"/music?guild_id={GUILD_A}")

    body = (await response.get_data()).decode()
    assert "02 // QUEUE" in body
    assert "03 // LAYERS" not in body


async def test_show_tab_switches_to_layers_and_persists(client, bot):
    bot.sessions._session = FakeSession(
        SessionStatus(
            guild_id=GUILD_A,
            connected=True,
            is_playing=True,
            is_paused=False,
            layers=(
                LayerInfo(id="l1", title="Layer One", url="u", volume=0.7),
            ),
            loop_mode=LoopMode.OFF,
            volume=0.7,
            progress=0.0,
        )
    )
    await client.get(f"/music?guild_id={GUILD_A}")

    switch = await client.post(
        "/music",
        form={"action": "show_tab", "value": "layers"},
        headers={"HX-Request": "true", "HX-Target": "side_panel"},
    )
    switch_body = (await switch.get_data()).decode()
    assert 'id="side_panel"' in switch_body
    assert "03 // LAYERS" in switch_body
    assert "Layer One" in switch_body

    full = await client.get(f"/music?guild_id={GUILD_A}")
    full_body = (await full.get_data()).decode()
    assert "03 // LAYERS" in full_body
    assert "02 // QUEUE" not in full_body


async def test_show_tab_switches_back_to_queue(client, bot):
    await client.get(f"/music?guild_id={GUILD_A}")
    await client.post(
        "/music",
        form={"action": "show_tab", "value": "layers"},
        headers={"HX-Request": "true", "HX-Target": "side_panel"},
    )

    back = await client.post(
        "/music",
        form={"action": "show_tab", "value": "queue"},
        headers={"HX-Request": "true", "HX-Target": "side_panel"},
    )

    body = (await back.get_data()).decode()
    assert "02 // QUEUE" in body
    assert "03 // LAYERS" not in body


async def test_show_tab_needs_no_connected_session(client):
    response = await client.post(
        "/music",
        form={"action": "show_tab", "value": "layers"},
        headers={"HX-Request": "true", "HX-Target": "side_panel"},
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert 'id="side_panel"' in body


async def test_show_tab_rejects_unknown_values(client, bot):
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": "show_tab", "value": "spoilers"},
        headers={"HX-Request": "true", "HX-Target": "side_panel"},
    )

    body = (await response.get_data()).decode()
    assert "Aba inválida" in body


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
async def test_volume_rejects_non_finite_values(client, bot, value: str):
    bot.sessions._session = FakeSession()
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": "set_volume", "value": value},
        headers={"HX-Request": "true", "HX-Target": "transport"},
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "Valor numérico inválido" in body


def layered_status(**overrides: Any) -> SessionStatus:
    values: dict[str, Any] = {
        "layers": (
            LayerInfo(id="l1", title="Layer One", url="u", volume=0.7),
        ),
        "queue": (YTMusicData({"title": "Queued One", "url": "u1"}),),
    }
    values.update(overrides)
    return playing_status(**values)


async def test_layer_rows_open_the_detail_dialog(client, bot):
    bot.sessions._session = FakeSession(layered_status())
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    response = await client.get(
        "/music", headers={"HX-Request": "true", "HX-Target": "layers"}
    )

    body = (await response.get_data()).decode()
    collapsed = " ".join(body.split())
    # The row is the dialog opener and carries the server truth as data,
    # so the dialog opens filled with no extra request.
    assert "data-layer-open" in collapsed
    assert 'data-layer-id="l1"' in collapsed
    assert 'data-layer-title="Layer One"' in collapsed
    assert 'data-layer-volume="0.7"' in collapsed
    # The inline per-layer forms are gone; the dialog owns both actions.
    assert 'type="number"' not in collapsed
    assert ">VOL<" not in collapsed
    assert ">DEL<" not in collapsed


async def test_layer_dialog_carries_the_layer_slider_form(client, bot):
    bot.sessions._session = FakeSession(layered_status())

    response = await client.get(f"/music?guild_id={GUILD_A}")

    body = (await response.get_data()).decode()
    collapsed = " ".join(body.split())
    assert 'id="layer_detail"' in collapsed
    assert 'id="layer_detail_volume"' in collapsed
    assert 'name="action" value="set_layer_volume"' in collapsed
    assert 'name="layer_id"' in collapsed
    assert 'type="range"' in collapsed
    assert 'min="0"' in collapsed
    assert 'max="1"' in collapsed
    assert 'step="0.01"' in collapsed
    assert 'name="action" value="remove_layer"' in collapsed
    # Both dialog posts re-render the side panel like the old rows did.
    assert 'hx-target="#side_panel"' in collapsed


async def test_full_page_ships_dialogs_outside_every_swap_region(client, bot):
    bot.sessions._session = FakeSession(layered_status())

    full = await client.get(f"/music?guild_id={GUILD_A}")
    full_body = (await full.get_data()).decode()
    assert full_body.count('id="layer_detail"') == 1
    assert full_body.count('id="confirm_dialog"') == 1
    assert full_body.count('id="dialog-script"') == 1

    for target in ("status_panels", "transport", "side_panel"):
        response = await client.get(
            "/music", headers={"HX-Request": "true", "HX-Target": target}
        )
        fragment = (await response.get_data()).decode()
        assert 'id="layer_detail"' not in fragment, target
        assert 'id="confirm_dialog"' not in fragment, target
        assert 'id="dialog-script"' not in fragment, target


@pytest.mark.parametrize(
    ("action", "message"),
    [
        ("clear_queue", "Limpar a fila inteira?"),
        ("disconnect", "Desconectar do canal de voz?"),
    ],
)
async def test_destructive_actions_carry_a_confirm_gate(
    client, bot, action: str, message: str
):
    bot.sessions._session = FakeSession(layered_status())

    response = await client.get(f"/music?guild_id={GUILD_A}")

    body = (await response.get_data()).decode()
    collapsed = " ".join(body.split())
    assert f'data-confirm="{message}"' in collapsed
    assert 'name="action"' in collapsed
    segment = collapsed.split(f'data-confirm="{message}"')[1]
    assert f'value="{action}"' in segment, (
        "the gated form must still post the original action"
    )


async def test_confirm_dialog_ships_with_cancel_and_execute(client, bot):
    bot.sessions._session = FakeSession(layered_status())

    response = await client.get(f"/music?guild_id={GUILD_A}")

    body = (await response.get_data()).decode()
    collapsed = " ".join(body.split())
    assert 'id="confirm_text"' in collapsed
    assert 'id="confirm_execute"' in collapsed
    assert "dialog-cancel" in collapsed
    assert "hud-btn-danger" in collapsed


@pytest.mark.parametrize(
    ("action", "fields", "message"),
    [
        ("add", {"value": "warriors"}, "Adicionado à fila"),
        ("add_layer", {"value": "warriors"}, "Virou camada"),
        ("set_volume", {"value": "0.8"}, "Volume alterado"),
        (
            "set_layer_volume",
            {"value": "0.8", "layer_id": "l1"},
            "Volume da camada alterado",
        ),
        ("seek", {"value": "30"}, "Posição ajustada"),
    ],
)
async def test_successful_actions_declare_the_toast_event(
    client,
    bot,
    action: str,
    fields: dict[str, str],
    message: str,
):
    # The server declares the confirmation through HX-Trigger; the client
    # listener renders it as an amber toast. Only successes carry it.
    session = FakeSession()
    bot.sessions._session = session
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": action, **fields},
        headers={"HX-Request": "true", "HX-Target": "transport"},
    )

    assert response.status_code == 200
    payload = json.loads(response.headers["HX-Trigger"])
    assert payload == {"harpi:toast": {"message": message}}


async def test_pasted_url_declares_the_queue_toast(client, bot, monkeypatch):
    async def offline_from_url(term: str) -> list[YTMusicData]:
        raise RuntimeError("network touched")

    monkeypatch.setattr(
        YTMusicData, "from_url", staticmethod(offline_from_url)
    )
    bot.sessions._session = FakeSession()
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": "search", "value": "https://youtu.be/direct"},
        headers={"HX-Request": "true", "HX-Target": "search_dropdown"},
    )

    assert response.status_code == 200
    payload = json.loads(response.headers["HX-Trigger"])
    assert payload == {"harpi:toast": {"message": "Adicionado à fila"}}


@pytest.mark.parametrize(
    ("action", "fields"),
    [
        ("add", {"value": "warriors"}),
        ("seek", {"value": "nan"}),
        ("set_volume", {"value": "0.8"}),
        ("add_layer", {"value": "warriors"}),
    ],
)
async def test_failed_actions_declare_no_toast_event(
    client, bot, action: str, fields: dict[str, str]
):
    # Bot offline / failing verbs / invalid values render the persistent
    # red panel_error; they must never raise an amber confirmation.
    bot.sessions._session = None
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": action, **fields},
        headers={"HX-Request": "true", "HX-Target": "queue"},
    )

    assert response.status_code == 200
    assert (
        '<div id="panel_error" hx-swap-oob="true">'
        in (await response.get_data()).decode()
    )
    assert "HX-Trigger" not in response.headers


async def test_failing_play_declares_no_toast_event(client, bot):
    bot.sessions._session = FailingPlaySession()
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": "add", "value": "warriors"},
        headers={"HX-Request": "true", "HX-Target": "queue"},
    )

    assert "yt explodiu" in (await response.get_data()).decode()
    assert "HX-Trigger" not in response.headers


async def test_search_dropdown_declares_no_toast_event(
    client, bot, monkeypatch
):
    patch_search(monkeypatch, [found_track()])
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": "search", "value": "found track"},
        headers={"HX-Request": "true", "HX-Target": "search_dropdown"},
    )

    assert response.status_code == 200
    assert "HX-Trigger" not in response.headers
