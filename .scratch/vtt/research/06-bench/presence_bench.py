import asyncio
import statistics
import tempfile
import time
from pathlib import Path

from src.storage.database import Database
from src.storage.registry import Actor, Place, SqliteRegistry


async def timed(fn, n=300):
    samples = []
    for _ in range(20):
        await fn()
    for _ in range(5):
        start = time.perf_counter()
        for _ in range(n):
            await fn()
        samples.append((time.perf_counter() - start) / n * 1e6)
    return statistics.median(samples)


async def main():
    database = Database(str(Path(tempfile.gettempdir()) / "vtt_presence_bench.db"))
    await database.open()
    registry = SqliteRegistry(database)
    actor = Actor(id="555", username="alice", display_name="Alice")
    place = Place(guild_id="7", guild_name="Table", channel_id="10", channel_name="Voice")
    await registry.sign_in(actor)
    await registry.select(actor, place)
    await registry.record_user_guilds(actor, ["7"])

    touch = await timed(lambda: registry.touch(actor, place))
    viewers = await timed(lambda: registry.viewers("7"))
    last = await timed(lambda: registry.last_connection("7"))
    guilds = await timed(lambda: registry.user_guild_ids("555"))
    print(f"touch (3 writes + commit): {touch:.0f} us")
    print(f"viewers (join + limit):    {viewers:.0f} us")
    print(f"last_connection:           {last:.0f} us")
    print(f"user_guild_ids:            {guilds:.0f} us")
    print(f"presence() per tick:       {touch + viewers + last:.0f} us")
    print(f"8 streams at 10 Hz:        {(touch+viewers+last)*80/1000:.1f} ms/s")
    await database.close()


asyncio.run(main())
