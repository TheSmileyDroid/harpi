import asyncio
import json
import sys
import tempfile
from pathlib import Path

import aiosqlite
from quart import Quart, Response, jsonify, request

app = Quart(__name__)

TOKEN_IDS = [f"01J8ZP4M7Q9R2S5T8V0W3X6Y{i:02d}" for i in range(8)]
DB_PATH = str(Path(tempfile.gettempdir()) / "vtt_bench.db")


def table_snapshot(rev=412):
    return {
        "table_id": "tbl_01J8ZP4M7Q9R2S5T8V0W3X6Y9A",
        "rev": rev,
        "scene_id": "scn_01J8ZP4M7Q9R2S5T8V0W3X6Y9B",
        "tokens": [
            {
                "id": TOKEN_IDS[i],
                "x": 120.5 + i * 37.25,
                "y": 340.0 + i * 21.5,
                "rotation": 0.0,
                "scale": 1.0,
                "label": f"Token {i}",
                "owner_id": f"12345678901234567{i}",
                "visible": True,
            }
            for i in range(8)
        ],
    }


def delta(rev):
    return {
        "table_id": "tbl_01J8ZP4M7Q9R2S5T8V0W3X6Y9A",
        "rev": rev,
        "moves": [{"id": TOKEN_IDS[3], "x": 341.75, "y": 412.0}],
    }


def frame(name, payload):
    return f"event: {name}\ndata: {json.dumps(payload)}\n\n"


@app.before_serving
async def open_db():
    app.db = await aiosqlite.connect(DB_PATH)
    await app.db.execute("PRAGMA journal_mode=WAL")
    await app.db.execute("PRAGMA synchronous=NORMAL")
    await app.db.execute(
        "CREATE TABLE IF NOT EXISTS token_pos (id TEXT PRIMARY KEY, x REAL, y REAL)"
    )
    await app.db.commit()


async def stream(payload_fn, seconds):
    async def gen():
        yield ": connected\n\n"
        rev = 1
        end = asyncio.get_running_loop().time() + seconds
        while asyncio.get_running_loop().time() < end:
            yield frame("table", payload_fn(rev))
            rev += 1
            await asyncio.sleep(0.1)

    return Response(gen(), mimetype="text/event-stream")


@app.get("/sse")
async def sse():
    return await stream(delta, float(request.args.get("seconds", "8")))


@app.get("/sse_full")
async def sse_full():
    return await stream(
        lambda rev: table_snapshot(rev), float(request.args.get("seconds", "8"))
    )


@app.get("/idle")
async def idle():
    await asyncio.sleep(float(request.args.get("seconds", "20")))
    return Response("event: heartbeat\ndata: {}\n\n", mimetype="text/event-stream")


@app.get("/poll")
async def poll():
    return jsonify(table_snapshot())


@app.post("/move")
async def move():
    body = await request.get_json()
    await app.db.execute(
        "INSERT INTO token_pos (id, x, y) VALUES (?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET x = excluded.x, y = excluded.y",
        (body["id"], body["x"], body["y"]),
    )
    await app.db.commit()
    return Response(status=204)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(sys.argv[1]), log_level="error")
