from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONTRACT_DIR = ROOT / "web" / "src" / "lib" / "contract"
FIXTURES_PATH = CONTRACT_DIR / "fixtures" / "fixtures.json"


def build_fixtures() -> dict[str, object]:
    from src.panel.schemas import (
        Authenticated,
        BotStatus,
        Channel,
        ChannelList,
        Connection,
        ErrorDetail,
        ErrorEnvelope,
        Guild,
        GuildList,
        Layer,
        PlaybackStatus,
        ReloadEvent,
        SearchResults,
        StatusSnapshot,
        Track,
    )

    track = Track(
        title="Bohemian Rhapsody",
        url="https://example.com/track",
        uploader="Queen",
        duration=354,
        thumbnail="https://example.com/thumb.jpg",
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
        "ChannelList": ChannelList(
            channels=[Channel(id="10", name="Voice")],
        ),
        "ErrorEnvelope": ErrorEnvelope(
            error=ErrorDetail(code="not_found", message="Not found"),
        ),
        "GuildList": GuildList(guilds=[Guild(id="1", name="Alpha")]),
        "ReloadEvent": ReloadEvent(scope="shell"),
        "SearchResults": SearchResults(results=[track]),
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
    FIXTURES_PATH.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(build_fixtures(), indent=2, sort_keys=True)
    FIXTURES_PATH.write_text(body + "\n")


if __name__ == "__main__":
    main()
