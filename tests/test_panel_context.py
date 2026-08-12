"""Panel context projection tests.

``project_music_panel`` is the pure projection from the music read-model
into the render context of the self-polling fragments; it must produce the
same defaults as the fragment routes when there is no session and format
the playback position for the UI.
"""

from __future__ import annotations

from pathlib import Path

from src.api.music import (
    MusicStatusResponse,
    MusicTrackResponse,
    QueueItemResponse,
)
from src.api.panel_context import (
    MusicPanelContext,
    SETTINGS_SECTIONS,
    project_music_panel,
)
from src.harpi_lib.audio.session import LoopMode


def test_project_music_panel_defaults_without_a_session():
    panel = project_music_panel(None)

    assert panel == MusicPanelContext()


def test_settings_sections_render_from_real_partials():
    """Every settings section resolves to an existing partial with icon+label."""
    templates = Path(__file__).resolve().parents[1] / "templates"

    for section, config in SETTINGS_SECTIONS.items():
        assert set(config) == {"label", "icon", "partial"}
        partial = templates / config["partial"]
        assert partial.is_file(), f"settings section '{section}' has no partial"


def test_project_music_panel_formats_the_position_in_minutes_and_seconds():
    status = MusicStatusResponse(
        current_music=MusicTrackResponse(title="one", duration=210, url="u"),
        progress=125_000,
        queue=[],
        layers=[],
        is_playing=True,
        is_paused=False,
        loop_mode=LoopMode.QUEUE.name.lower(),
        volume=0.7,
    )

    panel = project_music_panel(status)

    assert panel.current_position == 125_000
    assert panel.current_position_formatted == "2:05"
    assert panel.current_track is not None
    assert panel.current_track.title == "one"
    assert panel.paused is False
    assert panel.volume == 0.7
    assert panel.loop_mode == "queue"


def test_project_music_panel_carries_the_queue_into_the_context():
    status = MusicStatusResponse(
        current_music=None,
        progress=0,
        queue=[QueueItemResponse(title="two", duration=200, url="u")],
        layers=[],
        is_playing=False,
        is_paused=False,
        loop_mode=LoopMode.OFF.name.lower(),
        volume=0.5,
    )

    panel = project_music_panel(status)

    assert panel.queue == status.queue
    assert panel.layers == []
