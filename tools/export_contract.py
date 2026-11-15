"""Write the committed panel contract: the OpenAPI document and its fixtures."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONTRACT_DIR = ROOT / "web" / "src" / "lib" / "contract"
DOCUMENT_PATH = CONTRACT_DIR / "openapi.json"
FIXTURES_PATH = CONTRACT_DIR / "fixtures" / "fixtures.json"


def build_document() -> str:
    from app import app

    provider = app.extensions["QUART_SCHEMA"].openapi_provider
    return app.json.dumps(provider.schema(), indent=2, sort_keys=True)


def build_fixtures() -> dict[str, object]:
    from pydantic import BaseModel

    from src.panel.schemas import (
        Authenticated,
        BotStatus,
        Channel,
        ChannelList,
        Connection,
        ConnectionEvent,
        Directory,
        ErrorDetail,
        ErrorEnvelope,
        Guild,
        GuildList,
        Heartbeat,
        Layer,
        PlaybackStatus,
        Position,
        Presence,
        ReloadEvent,
        SearchResults,
        StatusSnapshot,
        Track,
        Viewer,
    )

    track = Track(
        title="Now Track",
        url="https://example.com/track",
        uploader="Harvester",
        duration=180,
        thumbnail="https://example.com/track.jpg",
    )
    layer = Layer(
        id="layer-1",
        title="Rain",
        url="https://example.com/layer",
        volume=0.25,
        thumbnail="https://example.com/layer.jpg",
    )
    fixtures: dict[str, BaseModel] = {
        "Authenticated": Authenticated(authenticated=True),
        "Directory": Directory(
            guild_id="7",
            guilds=[Guild(id="1", name="Alpha")],
            channels=[Channel(id="10", name="Voice")],
        ),
        "Heartbeat": Heartbeat(),
        "Position": Position(progress=42.5),
        "ChannelList": ChannelList(
            channels=[Channel(id="10", name="Voice")],
        ),
        "ErrorEnvelope": ErrorEnvelope(
            error=ErrorDetail(code="not_found", message="Not found"),
        ),
        "GuildList": GuildList(guilds=[Guild(id="1", name="Alpha")]),
        "ReloadEvent": ReloadEvent(scope="shell"),
        "SearchResults": SearchResults(results=[track]),
        "Presence": Presence(
            guild_id="7",
            viewers=[
                Viewer(
                    user_id="555",
                    username="harpi-user",
                    display_name="Harpi",
                    channel_id="42",
                    channel_name="Voice",
                    seen_at=1700000000,
                )
            ],
            last_connection=ConnectionEvent(
                action="connect",
                channel_id="42",
                channel_name="Voice",
                actor_id="555",
                actor_name="Harpi",
                at=1700000000,
            ),
        ),
        "StatusSnapshot": StatusSnapshot(
            bot=BotStatus(online=True),
            guild_id="7",
            connection=Connection(connected=True, channel_id="42"),
            playback=PlaybackStatus(
                guild_id="7",
                connected=True,
                is_playing=True,
                is_paused=False,
                current_music=track,
                queue=[track],
                layers=[layer],
                loop_mode="QUEUE",
                volume=0.7,
                progress=42.5,
                channel_id="42",
            ),
        ),
    }
    return {
        name: model.model_dump(mode="json") for name, model in fixtures.items()
    }


def main() -> None:
    CONTRACT_DIR.mkdir(parents=True, exist_ok=True)
    DOCUMENT_PATH.write_text(build_document() + "\n")
    FIXTURES_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURES_PATH.write_text(
        json.dumps(build_fixtures(), indent=2, sort_keys=True) + "\n"
    )


if __name__ == "__main__":
    main()
