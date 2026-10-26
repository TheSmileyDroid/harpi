from __future__ import annotations

import pytest

from src.storage.database import Database
from src.storage.registry import (
    PRESENCE_TTL_SECONDS,
    Actor,
    Place,
    SqliteRegistry,
)

ALICE = Actor(id="555", username="alice", display_name="Alice")
BOB = Actor(id="556", username="bob")
VOICE = Place(
    guild_id="7",
    guild_name="Alpha Guild",
    channel_id="42",
    channel_name="Voice Channel",
)
LOUNGE = Place(
    guild_id="7",
    guild_name="Alpha Guild",
    channel_id="43",
    channel_name="Lounge",
)
BETA = Place(guild_id="8", guild_name="Beta Guild")
NOW = 1_700_000_000


async def open_registry(tmp_path) -> tuple[Database, SqliteRegistry]:
    database = Database(tmp_path / "harpi.db")
    await database.open()
    return database, SqliteRegistry(database)


async def test_open_creates_the_schema_and_applies_it_once(tmp_path):
    database, _ = await open_registry(tmp_path)

    row = await database.fetchone(
        "SELECT COUNT(*) AS n FROM schema_migrations"
    )
    assert row is not None
    assert row["n"] == 3

    await database.close()
    reopened = Database(tmp_path / "harpi.db")
    await reopened.open()
    row = await reopened.fetchone(
        "SELECT COUNT(*) AS n FROM schema_migrations"
    )
    assert row is not None
    assert row["n"] == 3
    await reopened.close()


async def test_open_creates_the_user_guilds_table(tmp_path):
    database, _ = await open_registry(tmp_path)

    columns = await database.fetchall("PRAGMA table_info(user_guilds)")

    assert [column["name"] for column in columns] == [
        "user_id",
        "guild_id",
        "seen_at",
    ]
    await database.close()


async def test_open_requires_an_open_connection(tmp_path):
    database = Database(tmp_path / "harpi.db")

    with pytest.raises(RuntimeError, match="not open"):
        await database.fetchall("SELECT 1")


async def test_select_records_a_viewer_with_its_channel(tmp_path):
    database, registry = await open_registry(tmp_path)

    await registry.select(ALICE, VOICE, now=NOW)

    viewers = await registry.viewers("7", now=NOW)
    assert len(viewers) == 1
    assert viewers[0].user_id == "555"
    assert viewers[0].username == "alice"
    assert viewers[0].display_name == "Alice"
    assert viewers[0].channel_id == "42"
    assert viewers[0].channel_name == "Voice Channel"
    assert viewers[0].seen_at == NOW
    await database.close()


async def test_select_moves_a_viewer_between_guilds(tmp_path):
    database, registry = await open_registry(tmp_path)

    await registry.select(ALICE, VOICE, now=NOW)
    await registry.select(ALICE, BETA, now=NOW + 1)

    assert await registry.viewers("7", now=NOW + 1) == []
    beta = await registry.viewers("8", now=NOW + 1)
    assert [viewer.user_id for viewer in beta] == ["555"]
    assert beta[0].channel_id is None
    await database.close()


async def test_viewers_drop_a_stale_heartbeat(tmp_path):
    database, registry = await open_registry(tmp_path)

    await registry.select(ALICE, VOICE, now=NOW)
    await registry.select(BOB, VOICE, now=NOW + PRESENCE_TTL_SECONDS)

    fresh = await registry.viewers("7", now=NOW + PRESENCE_TTL_SECONDS + 1)
    assert [viewer.user_id for viewer in fresh] == ["556"]

    stale = await registry.viewers("7", now=NOW + PRESENCE_TTL_SECONDS * 3)
    assert stale == []
    await database.close()


async def test_touch_refreshes_the_heartbeat_and_keeps_the_channel(tmp_path):
    database, registry = await open_registry(tmp_path)

    await registry.select(ALICE, VOICE, now=NOW)
    await registry.touch(ALICE, Place(guild_id="7", guild_name="Alpha Guild"))

    refreshed = await registry.viewers("7", now=NOW + PRESENCE_TTL_SECONDS)
    assert len(refreshed) == 1
    assert refreshed[0].channel_id == "42"
    assert refreshed[0].seen_at >= NOW
    await database.close()


async def test_viewers_are_ordered_by_the_freshest_heartbeat(tmp_path):
    database, registry = await open_registry(tmp_path)

    await registry.select(ALICE, VOICE, now=NOW)
    await registry.select(BOB, LOUNGE, now=NOW + 1)

    viewers = await registry.viewers("7", now=NOW + 1)

    assert [viewer.user_id for viewer in viewers] == ["556", "555"]
    await database.close()


async def test_record_connection_keeps_the_actor(tmp_path):
    database, registry = await open_registry(tmp_path)

    await registry.record_connection(ALICE, VOICE, "connect", now=NOW)
    last = await registry.last_connection("7")

    assert last is not None
    assert last.action == "connect"
    assert last.channel_id == "42"
    assert last.channel_name == "Voice Channel"
    assert last.actor_id == "555"
    assert last.actor_name == "Alice"
    assert last.at == NOW
    await database.close()


async def test_last_connection_is_the_newest_event(tmp_path):
    database, registry = await open_registry(tmp_path)

    await registry.record_connection(ALICE, VOICE, "connect", now=NOW)
    await registry.record_connection(BOB, VOICE, "disconnect", now=NOW + 5)

    last = await registry.last_connection("7")

    assert last is not None
    assert last.action == "disconnect"
    assert last.actor_id == "556"
    assert last.actor_name == "bob"
    assert last.at == NOW + 5
    await database.close()


async def test_record_connection_without_an_actor(tmp_path):
    database, registry = await open_registry(tmp_path)

    await registry.record_connection(None, BETA, "connect", now=NOW)

    last = await registry.last_connection("8")
    assert last is not None
    assert last.actor_id is None
    assert last.actor_name is None
    await database.close()


async def test_leave_drops_the_viewer(tmp_path):
    database, registry = await open_registry(tmp_path)

    await registry.select(ALICE, VOICE, now=NOW)
    await registry.leave("555")

    assert await registry.viewers("7", now=NOW) == []
    await database.close()


async def test_sign_in_upserts_the_display_name(tmp_path):
    database, registry = await open_registry(tmp_path)

    await registry.sign_in(Actor(id="555", username="alice"))
    await registry.sign_in(ALICE)
    await registry.select(ALICE, VOICE, now=NOW)

    assert (await registry.viewers("7", now=NOW))[0].display_name == "Alice"
    await database.close()


async def test_a_second_registry_sees_the_persisted_viewer(tmp_path):
    path = tmp_path / "harpi.db"
    first = Database(path)
    await first.open()
    await SqliteRegistry(first).select(ALICE, VOICE, now=NOW)
    await first.close()

    second = Database(path)
    await second.open()
    viewers = await SqliteRegistry(second).viewers("7", now=NOW)

    assert [viewer.user_id for viewer in viewers] == ["555"]
    await second.close()


async def test_record_user_guilds_keeps_the_allowed_set(tmp_path):
    database, registry = await open_registry(tmp_path)

    await registry.record_user_guilds(ALICE, ["7", "8"], now=NOW)

    assert await registry.user_guild_ids("555") == frozenset({"7", "8"})
    row = await database.fetchone(
        "SELECT MIN(seen_at) AS seen_at FROM user_guilds"
    )
    assert row is not None
    assert row["seen_at"] == NOW
    await database.close()


async def test_record_user_guilds_replaces_the_previous_set(tmp_path):
    database, registry = await open_registry(tmp_path)

    await registry.record_user_guilds(ALICE, ["7", "8"], now=NOW)
    await registry.record_user_guilds(ALICE, ["8"], now=NOW + 1)

    assert await registry.user_guild_ids("555") == frozenset({"8"})
    await database.close()


async def test_a_second_registry_sees_the_persisted_guilds(tmp_path):
    path = tmp_path / "harpi.db"
    first = Database(path)
    await first.open()
    await SqliteRegistry(first).record_user_guilds(ALICE, ["7", "8"], now=NOW)
    await first.close()

    second = Database(path)
    await second.open()
    guilds = await SqliteRegistry(second).user_guild_ids("555")

    assert guilds == frozenset({"7", "8"})
    await second.close()


async def test_open_adds_the_login_epoch_column(tmp_path):
    database, _ = await open_registry(tmp_path)

    columns = await database.fetchall("PRAGMA table_info(users)")
    login_epoch = next(
        column for column in columns if column["name"] == "login_epoch"
    )

    assert login_epoch["notnull"] == 1
    assert login_epoch["dflt_value"] == "0"
    await database.close()


async def test_a_new_user_starts_at_login_epoch_zero(tmp_path):
    database, registry = await open_registry(tmp_path)

    await registry.sign_in(ALICE)

    assert await registry.login_epoch("555") == 0
    await database.close()


async def test_login_epoch_is_unknown_for_a_user_without_a_row(tmp_path):
    database, registry = await open_registry(tmp_path)

    assert await registry.login_epoch("999") is None
    await database.close()


async def test_increment_login_epoch_bumps_the_stored_value(tmp_path):
    database, registry = await open_registry(tmp_path)
    await registry.sign_in(ALICE)

    assert await registry.increment_login_epoch("555") == 1
    assert await registry.increment_login_epoch("555") == 2
    assert await registry.login_epoch("555") == 2
    await database.close()


async def test_increment_login_epoch_ignores_an_unknown_user(tmp_path):
    database, registry = await open_registry(tmp_path)

    assert await registry.increment_login_epoch("999") is None
    await database.close()


async def test_a_second_registry_sees_the_persisted_login_epoch(tmp_path):
    path = tmp_path / "harpi.db"
    first = Database(path)
    await first.open()
    first_registry = SqliteRegistry(first)
    await first_registry.sign_in(ALICE)
    await first_registry.increment_login_epoch("555")
    await first.close()

    second = Database(path)
    await second.open()
    epoch = await SqliteRegistry(second).login_epoch("555")

    assert epoch == 1
    await second.close()
