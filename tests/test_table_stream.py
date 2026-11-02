from __future__ import annotations

import asyncio
import gc
import json
from typing import Any

import pytest

from types import SimpleNamespace

from quart import session

from app import app as quart_app
from app import configure_panel_session
from pages import campaigns as campaigns_page
from pages import events as events_page
from pages import tables as tables_page
from src.config import Settings
from src.panel import (
    rate_limit,
    table_stream,
    vault,
    vault_index,
)
from src.panel import tables as table_domain
from src.panel.schemas import (
    TableDragMarker,
    TableRole,
    TableSheetChanged,
    TableStreamDelta,
    TableStreamSnapshot,
    TableStreamViewers,
)
from src.panel.vault_index import VaultIndex
from src.storage import (
    clear_database,
    clear_registry,
    init_database,
    init_registry,
)
from src.storage.database import Database
from src.storage.registry import SqliteRegistry
from src.storage.seed import paratheos
from tests.test_tables import (
    CSRF,
    GUILD,
    NARRATOR,
    PLAYER,
    SECRET,
    STRANGER,
    FakeClock,
    add_member,
    add_token,
    body,
    image_scene,
    open_table,
    player_access,
    sign_in,
)

TABLES_ROUTE = "/api/tables"
SLUG = "paratheos"


@pytest.fixture
async def world(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SECRET_KEY", SECRET)
    configure_panel_session(Settings.from_env())
    quart_app.config["TESTING"] = True
    root = tmp_path / "vault"
    root.mkdir()
    database = Database(
        tmp_path / "panel.db", campaign=paratheos(NARRATOR, str(GUILD))
    )
    await database.open()
    init_registry(SqliteRegistry(database))
    init_database(database)
    campaigns_page.SCENE_WRITE_BUCKETS = rate_limit.UserTokenBuckets(
        rate_limit.SCENE_WRITES_PER_MINUTE
    )
    vault.configure(vault.Vault(root=root))
    vault_index.configure(VaultIndex(root))
    yield SimpleNamespace(root=root, database=database)
    clear_registry()
    clear_database()
    vault.configure(vault.Vault())
    vault_index.configure(vault_index.VaultIndex())
    await database.close()


@pytest.fixture
async def client(world):
    return quart_app.test_client()


async def live_table(world, client, **scene: Any):
    await sign_in(client, NARRATOR)
    await image_scene(client, world, fog_outside=False, **scene)
    response, summary = await open_table(client)
    assert response.status_code == 200, summary
    table_id = summary["id"]
    await add_token(client, table_id, x=0, y=0)
    await add_token(client, table_id, label="Oculto", x=4, y=4, visible=False)
    row = await table_domain.table_row(world.database, table_id)
    assert row is not None
    return row


def frame(raw: str) -> tuple[str, dict[str, Any]]:
    lines = raw.splitlines()
    return lines[0][len("event: ") :], json.loads(lines[1][len("data: ") :])


async def next_frame(stream) -> tuple[str, dict[str, Any]]:
    return frame(await asyncio.wait_for(anext(stream), 1))


async def open_stream(world, row, user_id: str, role: TableRole, name: str):
    return table_stream.open_stream(
        world.database,
        row,
        user_id=user_id,
        role=role,
        name=name,
        root=world.root,
    )


async def test_the_table_events_route_is_registered():
    paths = {rule.rule for rule in quart_app.url_map.iter_rules()}

    assert "/api/tables/<table_id>/events" in paths


async def test_an_outsider_gets_404_before_a_stream_opens(client, world):
    row = await live_table(world, client)
    await sign_in(client, STRANGER)

    response = await client.get(f"{TABLES_ROUTE}/{row.id}/events")

    assert response.status_code == 404


async def test_a_closed_table_streams_a_closed_event(client, world):
    row = await live_table(world, client)
    await client.post(f"{TABLES_ROUTE}/{row.id}/close", json={}, headers=CSRF)

    response = await client.get(f"{TABLES_ROUTE}/{row.id}/events")

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    body = (await response.get_data()).decode()
    assert "event: table.closed" in body
    assert table_stream.CLOSED_REASON in body


async def test_the_third_stream_of_a_user_is_429(client, world, monkeypatch):
    row = await live_table(world, client)
    monkeypatch.setattr(
        table_stream,
        "TABLE_STREAM_SLOTS",
        table_stream.TableStreamSlots(per_table=16, per_user=2),
    )
    table_stream.TABLE_STREAM_SLOTS.acquire(NARRATOR, row.id)
    table_stream.TABLE_STREAM_SLOTS.acquire(NARRATOR, row.id)

    response = await client.get(f"{TABLES_ROUTE}/{row.id}/events")

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "30"


async def test_the_seventeenth_stream_of_a_table_is_429(
    client, world, monkeypatch
):
    row = await live_table(world, client)
    monkeypatch.setattr(
        table_stream,
        "TABLE_STREAM_SLOTS",
        table_stream.TableStreamSlots(per_table=2, per_user=2),
    )
    table_stream.TABLE_STREAM_SLOTS.acquire("1", row.id)
    table_stream.TABLE_STREAM_SLOTS.acquire("2", row.id)

    response = await client.get(f"{TABLES_ROUTE}/{row.id}/events")

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "30"


async def test_the_route_answers_text_event_stream(client, world, monkeypatch):
    row = await live_table(world, client)

    async def fake_stream(*args, **kwargs):
        yield "event: heartbeat\ndata: {}\n\n"

    monkeypatch.setattr(table_stream, "open_stream", fake_stream)

    response = await client.get(f"{TABLES_ROUTE}/{row.id}/events")

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    assert b"heartbeat" in await response.get_data()
    assert (
        table_stream.TABLE_STREAM_SLOTS.acquire(NARRATOR, row.id) is not None
    )


async def test_the_viewer_name_prefers_the_member_display_name(client, world):
    await sign_in(client, PLAYER)
    await add_member(world.database, PLAYER)
    async with quart_app.test_request_context("/"):
        session["username"] = "session-user"
        name = await tables_page._viewer_name(world.database, SLUG, PLAYER)

    assert name == "Panel User"


async def test_the_viewer_name_falls_back_to_the_session(client, world):
    await sign_in(client, PLAYER)
    async with quart_app.test_request_context("/"):
        session["username"] = "session-user"
        name = await tables_page._viewer_name(world.database, SLUG, PLAYER)

    assert name == "session-user"


async def test_the_viewer_name_ends_at_a_placeholder(client, world):
    async with quart_app.test_request_context("/"):
        name = await tables_page._viewer_name(world.database, SLUG, "999")

    assert name == "Convidado"


async def test_the_stream_opens_with_the_narrator_snapshot(world, client):
    row = await live_table(world, client)
    stream = await open_stream(world, row, NARRATOR, "narrator", "Mestre")

    assert await anext(stream) == ": connected\n\n"
    name, payload = await next_frame(stream)

    snapshot = TableStreamSnapshot.model_validate(payload)
    assert name == "table.snapshot"
    assert snapshot.stream_rev == 0
    assert snapshot.table_id == row.id
    assert snapshot.state.role == "narrator"
    assert {token.label for token in snapshot.state.tokens} == {
        "Ana",
        "Oculto",
    }
    await stream.aclose()


async def test_the_player_snapshot_hides_the_private_token_and_zone(
    world, client
):
    row = await live_table(world, client)
    await player_access(client, world)
    stream = await open_stream(world, row, PLAYER, "player", "Jogadora")

    await anext(stream)
    name, payload = await next_frame(stream)

    snapshot = TableStreamSnapshot.model_validate(payload)
    assert name == "table.snapshot"
    assert [token.label for token in snapshot.state.tokens] == ["Ana"]
    assert snapshot.state.scene is not None
    assert snapshot.state.scene.zones == []
    assert snapshot.state.scene.fog
    await stream.aclose()


async def test_the_roster_carries_display_names_and_roles(world, client):
    row = await live_table(world, client)
    await player_access(client, world)
    narrator = await open_stream(world, row, NARRATOR, "narrator", "Mestre")
    await anext(narrator)
    await next_frame(narrator)
    player = await open_stream(world, row, PLAYER, "player", "Jogadora")
    await anext(player)
    await next_frame(player)

    _, payload = await next_frame(narrator)

    viewers = TableStreamViewers.model_validate(payload)
    assert {(item.name, item.role) for item in viewers.viewers} == {
        ("Mestre", "narrator"),
        ("Jogadora", "player"),
    }
    assert NARRATOR not in json.dumps(payload)
    assert PLAYER not in json.dumps(payload)
    await narrator.aclose()
    await player.aclose()


async def test_a_token_edit_ships_an_absolute_delta(world, client):
    row = await live_table(world, client)
    stream = await open_stream(world, row, NARRATOR, "narrator", "Mestre")
    await anext(stream)
    _, snapshot = await next_frame(stream)
    token = next(
        item for item in snapshot["state"]["tokens"] if item["label"] == "Ana"
    )

    await client.patch(
        f"{TABLES_ROUTE}/{row.id}/tokens/{token['id']}",
        json={"x": 3, "y": 3},
        headers=CSRF,
    )
    name, payload = await next_frame(stream)

    delta = TableStreamDelta.model_validate(payload)
    assert name == "table.delta"
    assert delta.from_stream_rev == 0
    assert delta.stream_rev == 1
    assert [(item.id, item.x, item.y) for item in delta.tokens] == [
        (token["id"], 3.0, 3.0)
    ]
    assert delta.removed == []
    assert delta.round == 1
    await stream.aclose()


async def test_a_removed_token_travels_as_removed(world, client):
    row = await live_table(world, client)
    stream = await open_stream(world, row, NARRATOR, "narrator", "Mestre")
    await anext(stream)
    _, snapshot = await next_frame(stream)
    token = next(
        item for item in snapshot["state"]["tokens"] if item["label"] == "Ana"
    )

    await client.delete(
        f"{TABLES_ROUTE}/{row.id}/tokens/{token['id']}",
        headers={**CSRF, "Content-Type": "application/json"},
    )
    _, payload = await next_frame(stream)

    delta = TableStreamDelta.model_validate(payload)
    assert delta.removed == [token["id"]]
    assert delta.tokens == []
    await stream.aclose()


async def test_a_burst_of_changes_coalesces_into_one_delta(world, client):
    row = await live_table(world, client)
    stream = await open_stream(world, row, NARRATOR, "narrator", "Mestre")
    await anext(stream)
    _, snapshot = await next_frame(stream)
    token = next(
        item for item in snapshot["state"]["tokens"] if item["label"] == "Ana"
    )

    for x in (1, 2, 3):
        await client.patch(
            f"{TABLES_ROUTE}/{row.id}/tokens/{token['id']}",
            json={"x": x},
            headers=CSRF,
        )
    _, payload = await next_frame(stream)

    delta = TableStreamDelta.model_validate(payload)
    assert delta.from_stream_rev == 0
    assert delta.stream_rev == 3
    assert [(item.x, item.y) for item in delta.tokens] == [(3.0, 0.0)]
    await stream.aclose()


async def test_an_expired_window_falls_back_to_a_snapshot(
    world, client, monkeypatch
):
    monkeypatch.setattr(table_stream, "WINDOW_SIZE", 2)
    row = await live_table(world, client)
    stream = await open_stream(world, row, NARRATOR, "narrator", "Mestre")
    await anext(stream)
    _, snapshot = await next_frame(stream)
    token = next(
        item for item in snapshot["state"]["tokens"] if item["label"] == "Ana"
    )

    for x in (1, 2, 3):
        await client.patch(
            f"{TABLES_ROUTE}/{row.id}/tokens/{token['id']}",
            json={"x": x},
            headers=CSRF,
        )
    name, payload = await next_frame(stream)

    assert name == "table.snapshot"
    assert payload["stream_rev"] == 3
    await stream.aclose()


async def test_the_keyframe_repairs_after_a_delta(world, client, monkeypatch):
    monkeypatch.setattr(table_stream, "TICK_SECONDS", 0)
    row = await live_table(world, client)
    stream = await open_stream(world, row, NARRATOR, "narrator", "Mestre")
    await anext(stream)
    _, snapshot = await next_frame(stream)
    token = next(
        item for item in snapshot["state"]["tokens"] if item["label"] == "Ana"
    )
    await client.patch(
        f"{TABLES_ROUTE}/{row.id}/tokens/{token['id']}",
        json={"x": 5},
        headers=CSRF,
    )

    name, _ = await next_frame(stream)
    assert name == "table.delta"
    name, payload = await next_frame(stream)

    assert name == "table.snapshot"
    assert payload["stream_rev"] == 1
    await stream.aclose()


async def test_a_still_table_only_sends_heartbeats(world, client, monkeypatch):
    monkeypatch.setattr(table_stream, "TICK_SECONDS", 0)
    row = await live_table(world, client)
    stream = await open_stream(world, row, NARRATOR, "narrator", "Mestre")
    await anext(stream)
    await next_frame(stream)

    for _ in range(3):
        name, _ = await next_frame(stream)
        assert name == "heartbeat"
    await stream.aclose()


async def test_a_full_queue_closes_the_stream(world, client):
    row = await live_table(world, client)
    broadcaster, subscriber = await table_stream.subscribe(
        world.database, row, user_id=NARRATOR, role="narrator", name="Mestre"
    )
    try:
        assert subscriber.queue.maxsize == 32
        event = TableSheetChanged(
            sheet_id="sht_ana",
            character_id="chr_ana",
            rev=1,
            state="ok",
        )
        for _ in range(33):
            broadcaster.publish_sheet(event, NARRATOR)
        assert subscriber.queue.qsize() == 1
        assert isinstance(subscriber.queue.get_nowait(), table_stream.Overflow)
    finally:
        table_stream.unsubscribe(broadcaster, subscriber)
    assert table_stream.broadcaster_for(row.id) is None


async def test_a_change_published_during_the_snapshot_ships_a_delta(
    world, client, monkeypatch
):
    row = await live_table(world, client)
    original = table_domain.summary
    raced = False

    async def racing(database, table, **kwargs):
        nonlocal raced
        if not raced:
            raced = True
            await database.execute(
                "UPDATE tokens SET x = 5 WHERE table_id = ?", (row.id,)
            )
            await table_stream.publish(database, row.id, root=world.root)
        return await original(database, table, **kwargs)

    monkeypatch.setattr(table_domain, "summary", racing)
    stream = await open_stream(world, row, NARRATOR, "narrator", "Mestre")
    await anext(stream)
    name, snapshot = await next_frame(stream)
    assert name == "table.snapshot"
    assert snapshot["stream_rev"] == 0
    name, payload = await next_frame(stream)

    assert name == "table.delta"
    assert payload["from_stream_rev"] == 0
    assert payload["stream_rev"] == 1
    assert all(token["x"] == pytest.approx(5.0) for token in payload["tokens"])
    await stream.aclose()


async def test_an_aborted_response_releases_its_slot():
    slots = table_stream.TableStreamSlots(per_user=1, per_table=1)
    slot = slots.acquire(NARRATOR, "tbl_1")
    assert slot is not None
    lease = tables_page._SlotLease(slot)

    del lease
    gc.collect()

    assert slots.acquire(NARRATOR, "tbl_1") is not None


async def test_a_reopened_table_snapshots_attached_subscribers(world, client):
    row = await live_table(world, client)
    stream = await open_stream(world, row, NARRATOR, "narrator", "Mestre")
    await anext(stream)
    await next_frame(stream)
    broadcaster = table_stream.broadcaster_for(row.id)
    assert broadcaster is not None
    broadcaster.publish_closed("fim")
    state = await table_domain.stream_state(world.database, row)

    broadcaster.publish_snapshot(state, world.root)
    name, _ = await next_frame(stream)

    assert name == "table.snapshot"
    assert not broadcaster.closed
    await stream.aclose()


async def test_a_closed_broadcaster_is_replaced_on_the_next_stream(
    world, client
):
    table = await live_table(world, client)
    old, first = await table_stream.subscribe(
        world.database, table, user_id=NARRATOR, role="narrator", name="Mestre"
    )
    old.publish_closed("fim")
    table_stream.unsubscribe(old, first)

    fresh, second = await table_stream.subscribe(
        world.database, table, user_id=NARRATOR, role="narrator", name="Mestre"
    )

    assert fresh is not old
    assert not fresh.closed
    table_stream.unsubscribe(fresh, second)


async def test_a_drag_marker_reaches_the_subscribers_and_the_snapshot(
    world, client
):
    table = await live_table(world, client)
    broadcaster, subscriber = await table_stream.subscribe(
        world.database, table, user_id=NARRATOR, role="narrator", name="Mestre"
    )

    broadcaster.set_drag("tok_1", "Mestre", True)

    assert [item.token_id for item in broadcaster.drags()] == ["tok_1"]
    event = subscriber.queue.get_nowait()
    assert isinstance(event, TableDragMarker)
    assert event.actor == "Mestre"
    broadcaster.set_drag("tok_1", "Mestre", False)
    assert broadcaster.drags() == []
    table_stream.unsubscribe(broadcaster, subscriber)


async def test_sheet_changes_only_reach_the_owner_and_the_narrator(
    world, client
):
    table = await live_table(world, client)
    broadcaster, narrator = await table_stream.subscribe(
        world.database, table, user_id=NARRATOR, role="narrator", name="Mestre"
    )
    _, owner = await table_stream.subscribe(
        world.database, table, user_id=PLAYER, role="player", name="Dona"
    )
    _, other = await table_stream.subscribe(
        world.database, table, user_id="888", role="player", name="Outro"
    )
    event = TableSheetChanged(
        sheet_id="sht_ana", character_id="chr_ana", rev=4, state="ok"
    )

    broadcaster.publish_sheet(event, PLAYER)

    assert _types(narrator) == [
        TableStreamViewers,
        TableStreamViewers,
        TableSheetChanged,
    ]
    assert _types(owner) == [TableStreamViewers, TableSheetChanged]
    assert _types(other) == []
    table_stream.unsubscribe(broadcaster, narrator)
    table_stream.unsubscribe(broadcaster, owner)
    table_stream.unsubscribe(broadcaster, other)


def _types(subscriber) -> list[type]:
    return [type(item) for item in list(subscriber.queue._queue)]


async def test_a_scene_change_sends_a_snapshot(world, client):
    row = await live_table(world, client)
    await image_scene(client, world, name="Torre")
    stream = await open_stream(world, row, NARRATOR, "narrator", "Mestre")
    await anext(stream)
    await next_frame(stream)

    await client.post(
        f"{TABLES_ROUTE}/{row.id}/scene",
        json={"scene": "torre"},
        headers=CSRF,
    )
    name, payload = await next_frame(stream)

    assert name == "table.snapshot"
    assert payload["state"]["scene"]["slug"] == "torre"
    await stream.aclose()


async def test_closing_the_table_ends_the_stream(world, client):
    row = await live_table(world, client)
    stream = await open_stream(world, row, NARRATOR, "narrator", "Mestre")
    await anext(stream)
    await next_frame(stream)

    await client.post(f"{TABLES_ROUTE}/{row.id}/close", json={}, headers=CSRF)
    name, payload = await next_frame(stream)

    assert name == "table.closed"
    assert payload["reason"] == table_stream.CLOSED_REASON
    with pytest.raises(StopAsyncIteration):
        await asyncio.wait_for(anext(stream), 1)


async def test_the_broadcaster_dies_with_its_last_subscriber(world, client):
    row = await live_table(world, client)
    stream = await open_stream(world, row, NARRATOR, "narrator", "Mestre")
    await anext(stream)
    await next_frame(stream)
    assert table_stream.broadcaster_for(row.id) is not None

    await stream.aclose()

    assert table_stream.broadcaster_for(row.id) is None


async def test_a_table_stream_does_not_touch_the_music_stream_slots(world):
    before = events_page.STREAM_SLOTS.live_streams
    slots = table_stream.TableStreamSlots()
    slot = slots.acquire(NARRATOR, "tbl_1")

    assert slot is not None
    assert events_page.STREAM_SLOTS.live_streams == before
    slot.release()
    assert slots.acquire(NARRATOR, "tbl_1") is not None


async def test_a_move_publishes_a_delta_and_a_drag_marker(world, client):
    row = await live_table(world, client)
    stream = await open_stream(world, row, NARRATOR, "narrator", "Mestre")
    await anext(stream)
    _, snapshot = await next_frame(stream)
    token = snapshot["state"]["tokens"][0]

    response = await client.post(
        f"{TABLES_ROUTE}/{row.id}/moves",
        json={
            "drag_id": "drag_1",
            "final": False,
            "moves": [{"token_id": token["id"], "x": 3, "y": 2}],
        },
        headers=CSRF,
    )
    payload = await body(response)
    frames = [await next_frame(stream), await next_frame(stream)]
    delta = next(data for name, data in frames if name == "table.delta")
    drag = next(data for name, data in frames if name == "table.drag")

    assert response.status_code == 200
    assert payload["stream_rev"] == snapshot["stream_rev"] + 1
    assert delta["from_stream_rev"] == snapshot["stream_rev"]
    assert delta["stream_rev"] == payload["stream_rev"]
    moved = next(item for item in delta["tokens"] if item["id"] == token["id"])
    assert (moved["x"], moved["y"]) == (3.0, 2.0)
    assert drag["token_id"] == token["id"]
    assert drag["active"] is True
    assert drag["actor"]

    await client.post(
        f"{TABLES_ROUTE}/{row.id}/moves",
        json={
            "drag_id": "drag_1",
            "final": True,
            "moves": [{"token_id": token["id"], "x": 4, "y": 2}],
        },
        headers=CSRF,
    )
    await next_frame(stream)
    ended = await next_frame(stream)

    assert ended[0] == "table.drag"
    assert ended[1]["active"] is False
    broadcaster = table_stream.broadcaster_for(row.id)
    assert broadcaster is not None
    assert broadcaster.drags() == []
    await stream.aclose()


def test_a_drag_marker_expires_after_three_seconds():
    clock = FakeClock()
    broadcaster = table_stream.TableBroadcaster("tbl_1", clock=clock)
    broadcaster.set_drag("tok_1", "Mestre", True)

    clock.now += table_stream.DRAG_SECONDS - 0.1
    assert [item.token_id for item in broadcaster.drags()] == ["tok_1"]

    clock.now += 0.2
    assert broadcaster.drags() == []


async def test_a_scene_change_clears_the_drag_markers(world, client):
    row = await live_table(world, client)
    broadcaster, subscriber = await table_stream.subscribe(
        world.database, row, user_id=NARRATOR, role="narrator", name="Mestre"
    )
    broadcaster.set_drag("tok_1", "Mestre", True)
    state = await table_domain.stream_state(world.database, row)

    broadcaster.publish_snapshot(state, world.root)

    assert broadcaster.drags() == []
    assert isinstance(subscriber.queue.get_nowait(), TableDragMarker)
    assert isinstance(
        subscriber.queue.get_nowait(), table_stream.SnapshotSignal
    )
    table_stream.unsubscribe(broadcaster, subscriber)


def test_a_stale_drop_does_not_clear_a_newer_drag_marker():
    broadcaster = table_stream.TableBroadcaster("tbl_1")
    broadcaster.start_drag(["tok_1"], "Ana", "drag_a")
    broadcaster.start_drag(["tok_1"], "Bob", "drag_b")

    broadcaster.end_drag(["tok_1"], "Ana", "drag_a")

    assert [item.actor for item in broadcaster.drags()] == ["Bob"]

    broadcaster.end_drag(["tok_1"], "Bob", "drag_b")

    assert broadcaster.drags() == []


def test_repeated_drag_frames_broadcast_once_until_the_drop():
    broadcaster = table_stream.TableBroadcaster("tbl_1")
    subscriber = broadcaster.subscribe("1", "narrator", "Mestre")

    broadcaster.start_drag(["tok_1"], "Ana", "drag_a")
    broadcaster.start_drag(["tok_1"], "Ana", "drag_a")
    broadcaster.start_drag(["tok_1"], "Ana", "drag_a")

    assert _types(subscriber) == [TableDragMarker]

    broadcaster.end_drag(["tok_1"], "Ana", "drag_a")

    assert _types(subscriber) == [TableDragMarker, TableDragMarker]
    table_stream.unsubscribe(broadcaster, subscriber)


async def test_a_hidden_token_drag_stays_out_of_the_player_cutout(
    world, client
):
    row = await live_table(world, client)
    tokens = await table_domain.token_rows(
        world.database, row.id, row.current_scene_id
    )
    hidden = next(token for token in tokens if not token.visible)
    visible = next(token for token in tokens if token.visible)
    narrator = await open_stream(world, row, NARRATOR, "narrator", "Mestre")
    await anext(narrator)
    await next_frame(narrator)
    broadcaster = table_stream.broadcaster_for(row.id)
    assert broadcaster is not None
    broadcaster.set_drag(hidden.id, "Mestre", True)
    broadcaster.set_drag(visible.id, "Mestre", True)

    player = await open_stream(world, row, PLAYER, "player", "Dona")
    await anext(player)
    name, snapshot = await next_frame(player)

    assert name == "table.snapshot"
    assert [drag["token_id"] for drag in snapshot["drags"]] == [visible.id]
    await player.aclose()

    _, subscriber = await table_stream.subscribe(
        world.database, row, user_id=PLAYER, role="player", name="Dona"
    )
    hidden_frame = await table_stream._deliver(
        broadcaster,
        subscriber,
        world.database,
        world.root,
        TableDragMarker(token_id=hidden.id, actor="Mestre", active=True),
    )
    visible_frame = await table_stream._deliver(
        broadcaster,
        subscriber,
        world.database,
        world.root,
        TableDragMarker(token_id=visible.id, actor="Mestre", active=True),
    )

    assert hidden_frame is None
    assert visible_frame is not None
    table_stream.unsubscribe(broadcaster, subscriber)
    await narrator.aclose()
