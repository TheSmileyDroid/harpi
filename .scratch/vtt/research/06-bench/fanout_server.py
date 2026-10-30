import asyncio
import json
import sys

from quart import Quart, Response, request

app = Quart(__name__)

TOKEN_IDS = [f"01J8ZP4M7Q9R2S5T8V0W3X6Y{i:02d}" for i in range(8)]
QUEUE_LIMIT = 32

state = {"rev": 0, "subscribers": set(), "positions": {tid: [0.0, 0.0] for tid in TOKEN_IDS}}


def frame(name, payload):
    return f"event: {name}\ndata: {json.dumps(payload)}\n\n"


def snapshot():
    return {
        "table_id": "tbl_01J8ZP4M7Q9R2S5T8V0W3X6Y9A",
        "rev": state["rev"],
        "tokens": [
            {"id": tid, "x": x, "y": y} for tid, (x, y) in state["positions"].items()
        ],
    }


def publish():
    payload = frame("table", snapshot())
    for queue in tuple(state["subscribers"]):
        if queue.full():
            queue.get_nowait()
        queue.put_nowait(payload)


@app.get("/table/sse")
async def sse():
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=QUEUE_LIMIT)
    state["subscribers"].add(queue)

    async def gen():
        try:
            yield ": connected\n\n"
            yield frame("table", snapshot())
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), 5.0)
                except TimeoutError:
                    item = frame("heartbeat", {})
                yield item
        finally:
            state["subscribers"].discard(queue)

    return Response(gen(), mimetype="text/event-stream")


@app.post("/table/move")
async def move():
    body = await request.get_json()
    state["positions"][body["id"]] = [body["x"], body["y"]]
    state["rev"] += 1
    publish()
    return Response(status=204)


@app.get("/table/snapshot")
async def table_snapshot():
    return snapshot()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(sys.argv[1]), log_level="error")
