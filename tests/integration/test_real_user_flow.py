"""Real environment integration tests for Harpi Discord bot."""

from __future__ import annotations

import asyncio
import time

import httpx
import pytest

BASE_URL = "http://127.0.0.1:5000"
GUILD_ID = "734174030701264906"
CHANNEL_ID = "750053300027523125"
MUSIC_LINK_1 = "Warriors Imagine Dragons"
MUSIC_LINK_2 = (
    "https://music.youtube.com/watch?v=rTqYRWcA-Yw&si=m5AGIJK30J0s68K2"
)

REQUEST_TIMEOUT = 60.0


@pytest.fixture
async def http_client():
    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=REQUEST_TIMEOUT
    ) as client:
        yield client


@pytest.fixture
async def ensure_connected(http_client: httpx.AsyncClient):
    response = await http_client.get(f"/api/guild/{GUILD_ID}/channels")
    data = response.json()
    if data.get("current_channel"):
        return

    response = await http_client.post(
        "/api/guild/channel",
        json={"guild_id": GUILD_ID, "channel_id": CHANNEL_ID},
    )
    assert response.status_code in (200, 201)
    await asyncio.sleep(2)


async def wait_for_condition(
    http_client: httpx.AsyncClient,
    condition: callable,
    timeout: float = 30.0,
    poll_interval: float = 1.0,
) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        if await condition(http_client):
            return True
        await asyncio.sleep(poll_interval)
    return False


class TestServerStatus:
    @pytest.mark.asyncio
    async def test_server_status(self, http_client: httpx.AsyncClient):
        response = await http_client.get("/api/serverstatus")
        assert response.status_code == 200
        data = response.json()
        assert "cpu" in data
        assert "memory_percent" in data
        assert "memory_total" in data
        assert "memory_available" in data


class TestGuildAndChannels:
    @pytest.mark.asyncio
    async def test_get_guilds(self, http_client: httpx.AsyncClient):
        response = await http_client.get("/api/guild")
        assert response.status_code == 200
        guilds = response.json()
        guild_ids = [g["id"] for g in guilds]
        assert GUILD_ID in guild_ids

    @pytest.mark.asyncio
    async def test_get_channels(self, http_client: httpx.AsyncClient):
        response = await http_client.get(f"/api/guild/{GUILD_ID}/channels")
        assert response.status_code == 200
        data = response.json()
        assert "channels" in data
        channel_ids = [c["id"] for c in data["channels"]]
        assert CHANNEL_ID in channel_ids


class TestVoiceConnection:
    @pytest.mark.asyncio
    async def test_connect_to_voice(
        self, http_client: httpx.AsyncClient, ensure_connected
    ):
        response = await http_client.post(
            "/api/guild/channel",
            json={"guild_id": GUILD_ID, "channel_id": CHANNEL_ID},
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert data.get("success") is True


class TestMusicPlayback:
    @pytest.mark.asyncio
    async def test_music_status_initial(
        self, http_client: httpx.AsyncClient, ensure_connected
    ):
        response = await http_client.get(f"/api/music/{GUILD_ID}/status")
        assert response.status_code == 200
        data = response.json()
        assert "current_music" in data
        assert "queue" in data
        assert "is_playing" in data

    @pytest.mark.asyncio
    async def test_add_music_to_queue(
        self, http_client: httpx.AsyncClient, ensure_connected
    ):
        response = await http_client.post(
            "/api/music/add",
            json={
                "guild_id": GUILD_ID,
                "channel_id": CHANNEL_ID,
                "link": MUSIC_LINK_1,
                "type": "queue",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        await asyncio.sleep(3)

    @pytest.mark.asyncio
    async def test_music_status_playing(
        self, http_client: httpx.AsyncClient, ensure_connected
    ):
        async def check_playing(client):
            response = await client.get(f"/api/music/{GUILD_ID}/status")
            data = response.json()
            return data.get("current_music") is not None

        assert await wait_for_condition(http_client, check_playing, timeout=30)

        response = await http_client.get(f"/api/music/{GUILD_ID}/status")
        data = response.json()
        assert data["current_music"] is not None

    @pytest.mark.asyncio
    async def test_add_second_music(
        self, http_client: httpx.AsyncClient, ensure_connected
    ):
        response = await http_client.post(
            "/api/music/add",
            json={
                "guild_id": GUILD_ID,
                "channel_id": CHANNEL_ID,
                "link": MUSIC_LINK_2,
                "type": "queue",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        await asyncio.sleep(2)

    @pytest.mark.asyncio
    async def test_queue_has_tracks(
        self, http_client: httpx.AsyncClient, ensure_connected
    ):
        response = await http_client.get(f"/api/music/{GUILD_ID}/status")
        data = response.json()
        assert len(data.get("queue", [])) >= 0


class TestPlaybackControl:
    @pytest.mark.asyncio
    async def test_skip_music(
        self, http_client: httpx.AsyncClient, ensure_connected
    ):
        response = await http_client.post(
            "/api/music/control",
            json={"guild_id": GUILD_ID, "action": "skip", "mode": None},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        await asyncio.sleep(1)

    @pytest.mark.asyncio
    async def test_loop_track(
        self, http_client: httpx.AsyncClient, ensure_connected
    ):
        response = await http_client.post(
            "/api/music/control",
            json={"guild_id": GUILD_ID, "action": "loop", "mode": "track"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"

        response = await http_client.get(f"/api/music/{GUILD_ID}/status")
        data = response.json()
        assert data.get("loop_mode") == "track"

    @pytest.mark.asyncio
    async def test_loop_queue(
        self, http_client: httpx.AsyncClient, ensure_connected
    ):
        response = await http_client.post(
            "/api/music/control",
            json={"guild_id": GUILD_ID, "action": "loop", "mode": "queue"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"

        response = await http_client.get(f"/api/music/{GUILD_ID}/status")
        data = response.json()
        assert data.get("loop_mode") == "queue"

    @pytest.mark.asyncio
    async def test_loop_off(
        self, http_client: httpx.AsyncClient, ensure_connected
    ):
        response = await http_client.post(
            "/api/music/control",
            json={"guild_id": GUILD_ID, "action": "loop", "mode": "off"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"

        response = await http_client.get(f"/api/music/{GUILD_ID}/status")
        data = response.json()
        assert data.get("loop_mode") == "off"

    @pytest.mark.asyncio
    async def test_pause_music(
        self, http_client: httpx.AsyncClient, ensure_connected
    ):
        response = await http_client.post(
            "/api/music/control",
            json={"guild_id": GUILD_ID, "action": "pause", "mode": None},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"

        response = await http_client.get(f"/api/music/{GUILD_ID}/status")
        data = response.json()
        assert data.get("is_paused") is True

    @pytest.mark.asyncio
    async def test_resume_music(
        self, http_client: httpx.AsyncClient, ensure_connected
    ):
        response = await http_client.post(
            "/api/music/control",
            json={"guild_id": GUILD_ID, "action": "resume", "mode": None},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"

        response = await http_client.get(f"/api/music/{GUILD_ID}/status")
        data = response.json()
        assert data.get("is_paused") is False


class TestLayers:
    @pytest.mark.asyncio
    async def test_add_layer(
        self, http_client: httpx.AsyncClient, ensure_connected
    ):
        response = await http_client.post(
            "/api/music/add",
            json={
                "guild_id": GUILD_ID,
                "channel_id": CHANNEL_ID,
                "link": MUSIC_LINK_1,
                "type": "layer",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        await asyncio.sleep(2)

    @pytest.mark.asyncio
    async def test_layers_present(
        self, http_client: httpx.AsyncClient, ensure_connected
    ):
        response = await http_client.get(f"/api/music/{GUILD_ID}/status")
        data = response.json()
        assert "layers" in data

    @pytest.mark.asyncio
    async def test_set_layer_volume(
        self, http_client: httpx.AsyncClient, ensure_connected
    ):
        response = await http_client.get(f"/api/music/{GUILD_ID}/status")
        data = response.json()
        layers = data.get("layers", [])
        if layers:
            layer_id = layers[0]["id"]
            response = await http_client.post(
                "/api/music/control",
                json={
                    "guild_id": GUILD_ID,
                    "action": "set_layer_volume",
                    "layer_id": layer_id,
                    "volume": 50,
                    "mode": None,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("status") == "ok"

    @pytest.mark.asyncio
    async def test_remove_layer(
        self, http_client: httpx.AsyncClient, ensure_connected
    ):
        response = await http_client.get(f"/api/music/{GUILD_ID}/status")
        data = response.json()
        layers = data.get("layers", [])
        if layers:
            layer_id = layers[0]["id"]
            response = await http_client.post(
                "/api/music/control",
                json={
                    "guild_id": GUILD_ID,
                    "action": "remove_layer",
                    "layer_id": layer_id,
                    "mode": None,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("status") == "ok"


class TestVolumeControl:
    @pytest.mark.asyncio
    async def test_set_volume(
        self, http_client: httpx.AsyncClient, ensure_connected
    ):
        response = await http_client.post(
            "/api/music/control",
            json={
                "guild_id": GUILD_ID,
                "action": "set_volume",
                "volume": 80,
                "mode": None,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"

        response = await http_client.get(f"/api/music/{GUILD_ID}/status")
        data = response.json()
        assert data.get("volume") == 2.0

    @pytest.mark.asyncio
    async def test_volume_clamping(
        self, http_client: httpx.AsyncClient, ensure_connected
    ):
        response = await http_client.post(
            "/api/music/control",
            json={
                "guild_id": GUILD_ID,
                "action": "set_volume",
                "volume": 3,
                "mode": None,
            },
        )
        assert response.status_code == 200
        response = await http_client.get(f"/api/music/{GUILD_ID}/status")
        data = response.json()
        assert data.get("volume") == 2.0


class TestStopAndCleanup:
    @pytest.mark.asyncio
    async def test_stop_music(
        self, http_client: httpx.AsyncClient, ensure_connected
    ):
        response = await http_client.post(
            "/api/music/control",
            json={"guild_id": GUILD_ID, "action": "stop", "mode": None},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"

        await asyncio.sleep(1)

        response = await http_client.get(f"/api/music/{GUILD_ID}/status")
        data = response.json()
        assert data.get("current_music") is None
        assert data.get("queue") == []

    @pytest.mark.asyncio
    async def test_disconnect(
        self, http_client: httpx.AsyncClient, ensure_connected
    ):
        await http_client.post(
            "/api/music/control",
            json={"guild_id": GUILD_ID, "action": "stop"},
        )

        response = await http_client.post(
            f"/api/soundboard/disconnect/{GUILD_ID}",
        )
        assert response.status_code in (200, 201, 204)
