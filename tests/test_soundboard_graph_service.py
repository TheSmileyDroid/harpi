"""Tests for SoundboardGraphService."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.harpi_lib.api import GuildConfig, SoundboardGraph
from src.harpi_lib.services.soundboard_graph import SoundboardGraphService


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.loop = asyncio.new_event_loop()
    return bot


@pytest.fixture
def guilds():
    return {}


@pytest.fixture
def service(mock_bot, guilds):
    return SoundboardGraphService(mock_bot, guilds)


def _make_guild_config(guild_id: int = 1, **kwargs) -> GuildConfig:
    return GuildConfig(
        id=guild_id,
        mixer=MagicMock(),
        controller=MagicMock(),
        **kwargs,
    )


class TestGetGraph:
    def test_returns_none_if_guild_not_connected(self, service):
        assert service.get_graph(guild_id=999) is None

    def test_creates_default_graph_when_none_exists(self, service, guilds):
        gc = _make_guild_config(guild_id=1, soundboard_graph=None)
        guilds[1] = gc
        graph = service.get_graph(guild_id=1)
        assert graph is not None
        assert len(graph.nodes) == 1
        assert graph.nodes[0]["type"] == "output"
        assert graph.edges == []

    def test_returns_existing_graph(self, service, guilds):
        existing = SoundboardGraph(
            nodes=[{"id": "o1", "type": "output"}],
            edges=[{"source": "s1", "target": "o1"}],
        )
        gc = _make_guild_config(guild_id=1, soundboard_graph=existing)
        guilds[1] = gc
        graph = service.get_graph(guild_id=1)
        assert graph is existing


class TestUpdateGraph:
    @pytest.mark.asyncio
    async def test_raises_when_guild_not_connected(self, service):
        with pytest.raises(ValueError, match="não conectada"):
            await service.update_graph(999, [], [])

    @pytest.mark.asyncio
    async def test_creates_new_graph_when_none(self, service, guilds):
        gc = _make_guild_config(guild_id=1, soundboard_graph=None)
        guilds[1] = gc
        nodes = [{"id": "o1", "type": "output"}]
        edges = []
        result = await service.update_graph(1, nodes, edges)
        assert result.nodes == nodes
        assert result.edges == edges

    @pytest.mark.asyncio
    async def test_updates_existing_graph_calls_edge_changes(
        self, service, guilds
    ):
        old_nodes = [{"id": "o1", "type": "output"}]
        old_edges = []
        gc = _make_guild_config(
            guild_id=1,
            soundboard_graph=SoundboardGraph(nodes=old_nodes, edges=old_edges),
        )
        guilds[1] = gc

        new_nodes = [
            {"id": "s1", "type": "sound-source"},
            {"id": "o1", "type": "output"},
        ]
        new_edges = [{"source": "s1", "target": "o1"}]

        with patch.object(
            service, "_handle_edge_changes", new_callable=AsyncMock
        ) as mock_handle:
            result = await service.update_graph(1, new_nodes, new_edges)
            mock_handle.assert_called_once()

        assert result.nodes == new_nodes
        assert result.edges == new_edges


class TestHandleEdgeChanges:
    @pytest.mark.asyncio
    async def test_added_edge_starts_prepared_source(self, service, guilds):
        mock_source = MagicMock()
        gc = _make_guild_config(guild_id=1)
        gc.prepared_sources = {"s1": mock_source}
        guilds[1] = gc

        nodes = [
            {"id": "s1", "type": "sound-source"},
            {"id": "o1", "type": "output"},
        ]
        old_edges = []
        new_edges = [{"source": "s1", "target": "o1"}]

        with patch.object(
            service, "start_source_playback", new_callable=AsyncMock
        ) as mock_start:
            await service._handle_edge_changes(gc, nodes, old_edges, new_edges)
            mock_start.assert_called_once_with(1, "s1")

    @pytest.mark.asyncio
    async def test_removed_edge_stops_disconnected_source(
        self, service, guilds
    ):
        gc = _make_guild_config(guild_id=1)
        guilds[1] = gc

        nodes = [
            {"id": "s1", "type": "sound-source"},
            {"id": "o1", "type": "output"},
        ]
        old_edges = [{"source": "s1", "target": "o1"}]
        new_edges = []

        with patch.object(
            service, "stop_source_playback", new_callable=AsyncMock
        ) as mock_stop:
            await service._handle_edge_changes(gc, nodes, old_edges, new_edges)
            mock_stop.assert_called_once_with(1, "s1")

    @pytest.mark.asyncio
    async def test_start_error_is_logged_not_raised(self, service, guilds):
        gc = _make_guild_config(guild_id=1)
        gc.prepared_sources = {"s1": MagicMock()}
        guilds[1] = gc

        nodes = [
            {"id": "s1", "type": "sound-source"},
            {"id": "o1", "type": "output"},
        ]

        with patch.object(
            service,
            "start_source_playback",
            new_callable=AsyncMock,
            side_effect=RuntimeError("boom"),
        ):
            # Should not raise
            await service._handle_edge_changes(
                gc, nodes, [], [{"source": "s1", "target": "o1"}]
            )


class TestSyncGraphPlayback:
    @pytest.mark.asyncio
    async def test_starts_connected_prepared_sources(self, service, guilds):
        gc = _make_guild_config(guild_id=1)
        gc.prepared_sources = {"s1": MagicMock()}
        guilds[1] = gc

        nodes = [
            {"id": "s1", "type": "sound-source"},
            {"id": "o1", "type": "output"},
        ]
        edges = [{"source": "s1", "target": "o1"}]

        with patch.object(
            service, "start_source_playback", new_callable=AsyncMock
        ) as mock_start:
            await service._sync_graph_playback(gc, nodes, edges)
            mock_start.assert_called_once_with(1, "s1")

    @pytest.mark.asyncio
    async def test_skips_non_prepared_sources(self, service, guilds):
        gc = _make_guild_config(guild_id=1)
        gc.prepared_sources = {}  # nothing prepared
        guilds[1] = gc

        nodes = [
            {"id": "s1", "type": "sound-source"},
            {"id": "o1", "type": "output"},
        ]
        edges = [{"source": "s1", "target": "o1"}]

        with patch.object(
            service, "start_source_playback", new_callable=AsyncMock
        ) as mock_start:
            await service._sync_graph_playback(gc, nodes, edges)
            mock_start.assert_not_called()


class TestStartSourcePlayback:
    @pytest.mark.asyncio
    async def test_raises_when_not_connected(self, service):
        with pytest.raises(ValueError, match="não conectada"):
            await service.start_source_playback(999, "s1")

    @pytest.mark.asyncio
    async def test_raises_when_source_not_prepared(self, service, guilds):
        gc = _make_guild_config(guild_id=1)
        gc.prepared_sources = {}
        guilds[1] = gc
        with pytest.raises(ValueError, match="not found"):
            await service.start_source_playback(1, "s1")

    @pytest.mark.asyncio
    async def test_adds_source_to_background(self, service, guilds):
        mock_source = MagicMock()
        mock_source.id = "src-id"
        gc = _make_guild_config(guild_id=1)
        gc.prepared_sources = {"s1": mock_source}
        gc.background = {}
        guilds[1] = gc

        gc.controller.add_layer.return_value = "layer-1"

        await service.start_source_playback(1, "s1")
        gc.controller.add_layer.assert_called_once_with(mock_source)
        assert gc.background["layer-1"] is mock_source

    @pytest.mark.asyncio
    async def test_noop_if_already_playing(self, service, guilds):
        mock_source = MagicMock()
        gc = _make_guild_config(guild_id=1)
        gc.prepared_sources = {"s1": mock_source}
        gc.background = {"existing": mock_source}  # already in background
        guilds[1] = gc

        await service.start_source_playback(1, "s1")
        gc.controller.add_layer.assert_not_called()

    @pytest.mark.asyncio
    async def test_initializes_background_if_none(self, service, guilds):
        mock_source = MagicMock()
        gc = _make_guild_config(guild_id=1)
        gc.prepared_sources = {"s1": mock_source}
        gc.background = None
        guilds[1] = gc

        gc.controller.add_layer.return_value = "layer-1"

        await service.start_source_playback(1, "s1")
        assert gc.background is not None
        assert "layer-1" in gc.background


class TestStopSourcePlayback:
    @pytest.mark.asyncio
    async def test_raises_when_not_connected(self, service):
        with pytest.raises(ValueError, match="não conectada"):
            await service.stop_source_playback(999, "s1")

    @pytest.mark.asyncio
    async def test_removes_from_background(self, service, guilds):
        mock_source = MagicMock()
        gc = _make_guild_config(guild_id=1)
        gc.prepared_sources = {"s1": mock_source}
        gc.background = {"layer-1": mock_source}
        guilds[1] = gc

        await service.stop_source_playback(1, "s1")
        gc.controller.remove_layer.assert_called_once_with("layer-1")
        assert "layer-1" not in gc.background

    @pytest.mark.asyncio
    async def test_noop_if_no_background(self, service, guilds):
        gc = _make_guild_config(guild_id=1)
        gc.prepared_sources = {"s1": MagicMock()}
        gc.background = None
        guilds[1] = gc

        # Should not raise
        await service.stop_source_playback(1, "s1")


class TestIsSourcePlaying:
    def test_returns_false_when_not_connected(self, service):
        assert service.is_source_playing(999, "s1") is False

    def test_returns_false_when_no_background(self, service, guilds):
        gc = _make_guild_config(guild_id=1)
        gc.background = None
        guilds[1] = gc
        assert service.is_source_playing(1, "s1") is False

    def test_returns_true_when_playing(self, service, guilds):
        mock_source = MagicMock()
        gc = _make_guild_config(guild_id=1)
        gc.background = {"layer-1": mock_source}
        gc.controller.get_layer_id.return_value = "s1"
        guilds[1] = gc

        assert service.is_source_playing(1, "s1") is True

    def test_returns_false_when_not_playing(self, service, guilds):
        mock_source = MagicMock()
        gc = _make_guild_config(guild_id=1)
        gc.background = {"layer-1": mock_source}
        gc.controller.get_layer_id.return_value = "other-node"
        guilds[1] = gc

        assert service.is_source_playing(1, "s1") is False
