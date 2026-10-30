import json
import statistics
import time

from pages.events import _frame
from src.panel.schemas import Heartbeat, Position, Presence, StatusSnapshot, Viewer


def snap(queue_len=5):
    return StatusSnapshot.model_validate({
        "bot": {"online": True},
        "guild_id": "1",
        "connection": {"connected": True, "channel_id": "10"},
        "playback": {
            "guild_id": "1",
            "connected": True,
            "is_playing": True,
            "is_paused": False,
            "current_music": {
                "title": "A Rather Long Track Title For Sizing",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "uploader": "Some Uploader Name",
                "duration": 245,
                "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
            },
            "queue": [
                {
                    "title": f"Queued Track {i} With A Name",
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "uploader": "Some Uploader Name",
                    "duration": 200 + i,
                    "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
                }
                for i in range(queue_len)
            ],
            "layers": [],
            "loop_mode": "OFF",
            "volume": 1.0,
            "progress": 123.4,
            "channel_id": "10",
        },
    })


TOKEN_IDS = [f"01J8ZP4M7Q9R2S5T8V0W3X6Y{i:02d}" for i in range(8)]


def table_snapshot(rev=412):
    return {
        "table_id": "tbl_01J8ZP4M7Q9R2S5T8V0W3X6Y9A",
        "rev": rev,
        "scene_id": "scn_01J8ZP4M7Q9R2S5T8V0W3X6Y9B",
        "tokens": [
            {
                "id": TOKEN_IDS[i],
                "x": round(120.5 + i * 37.25, 2),
                "y": round(340.0 + i * 21.5, 2),
                "rotation": 0.0,
                "scale": 1.0,
                "label": f"Token {i}",
                "owner_id": f"12345678901234567{i}",
                "visible": True,
            }
            for i in range(8)
        ],
    }


def table_delta(rev=413):
    return {
        "table_id": "tbl_01J8ZP4M7Q9R2S5T8V0W3X6Y9A",
        "rev": rev,
        "moves": [
            {"id": TOKEN_IDS[3], "x": 341.75, "y": 412.0},
        ],
    }


def frame(name, payload):
    return f"event: {name}\ndata: {json.dumps(payload)}\n\n"


def measure(fn, n=20000):
    for _ in range(1000):
        fn()
    samples = []
    for _ in range(7):
        start = time.perf_counter()
        for _ in range(n):
            fn()
        samples.append((time.perf_counter() - start) / n * 1e6)
    return statistics.median(samples)


cases = {
    "position": lambda: _frame(Position, Position(progress=123.4)),
    "heartbeat": lambda: _frame(Heartbeat, Heartbeat()),
    "presence(8 viewers)": lambda: _frame(
        Presence,
        Presence(
            guild_id="1",
            viewers=[
                Viewer(
                    user_id=str(100000000000000000 + i),
                    username=f"player{i}",
                    display_name=f"Player {i}",
                    channel_id="10",
                    channel_name="Table Voice",
                    seen_at=1729000000,
                )
                for i in range(8)
            ],
            last_connection=None,
        ),
    ),
    "status music (5 queued)": lambda: _frame(StatusSnapshot, snap()),
    "table full (8 tokens)": lambda: frame("table", table_snapshot()),
    "table delta (1 token)": lambda: frame("table", table_delta()),
}

for label, fn in cases.items():
    body = fn()
    print(f"{label:28s} {len(body.encode()):5d} bytes  {measure(fn):7.2f} us/frame")

status = snap()
print("status model_dump us:", measure(lambda: status.model_dump(), 5000))
print("status json.dumps us:", measure(lambda: json.dumps(status.model_dump()), 5000))
