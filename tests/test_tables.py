from __future__ import annotations

import asyncio
import io
import json
from collections.abc import Iterable
from types import SimpleNamespace
from typing import Any

import pytest
from aiosqlite import IntegrityError
from PIL import Image

from app import app as quart_app
from app import configure_panel_session
from pages import campaigns as campaigns_page
from pages import tables as tables_page
from src.config import Settings
from src.panel import login, state, vault, vault_index
from src.panel import rate_limit
from src.panel import tables as table_domain
from src.panel.vault_index import VaultIndex
from src.storage import (
    clear_database,
    clear_registry,
    init_database,
    init_registry,
)
from src.storage.database import Database
from src.storage.registry import Actor, SqliteRegistry
from src.storage.seed import paratheos

SECRET = "test-secret"
GUILD = 734174030701264906
OTHER_GUILD = 896066642948259960
NARRATOR = "100"
PLAYER = "555"
STRANGER = "777"
SLUG = "paratheos"
CAMPAIGN = f"Harpi/Campaigns/{SLUG}"
SCENES_ROUTE = f"/api/campaigns/{SLUG}/scenes"
TABLES_ROUTE = "/api/tables"
CSRF = {"Sec-Fetch-Site": "same-origin"}
CHANNEL = "123456789012345678"


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


async def sign_in(
    client, user_id: str, guilds: Iterable[int] = (GUILD,)
) -> None:
    async with client.session_transaction() as stored:
        stored["authenticated"] = True
        stored["user_id"] = user_id
        stored["username"] = "panel-user"
        stored[login.ISSUED_AT_KEY] = login.now()
        stored[login.LOGIN_EPOCH_KEY] = 0
    await state.record_user_guilds(
        Actor(id=user_id, username="panel-user"), guilds
    )


async def add_member(database: Database, user_id: str) -> None:
    await database.execute(
        "INSERT INTO members (campaign_slug, user_id, display_name, joined_at) "
        "VALUES (?, ?, 'Panel User', 1700000000)",
        (SLUG, user_id),
    )


async def activate_sheet(database: Database, user_id: str) -> None:
    await database.execute(
        "INSERT INTO sheet_files ("
        "path, harpi_id, campaign, rev, hash, last_text, base_json, "
        "status, owner_id, state, updated_at"
        ") VALUES (?, 'sht_player', ?, 1, 'hash', '', '{}', 'ativo', ?, "
        "'ok', 1700000000)",
        (f"{CAMPAIGN}/sheets/Player.md", SLUG, user_id),
    )


def image_bytes(
    color: str = "red", size: tuple[int, int] = (800, 600)
) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def vault_image(world, name: str = "mapa.png") -> str:
    target = world.root / CAMPAIGN / "assets" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(image_bytes())
    vault_index.configure(VaultIndex(world.root))
    return f"{CAMPAIGN}/assets/{name}"


async def body(response) -> dict[str, Any]:
    return json.loads(await response.get_data())


def zone(
    name: str = "Sala principal", zone_id: str = "zon_sala", **kwargs: Any
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": zone_id,
        "label": name,
        "revealed": False,
        "rects": [{"x": 1, "y": 2, "w": 3, "h": 2}],
    }
    data.update(kwargs)
    return data


async def create_scene(client, **payload: Any) -> dict[str, Any]:
    response = await client.post(SCENES_ROUTE, json=payload, headers=CSRF)
    assert response.status_code == 200, await body(response)
    return await body(response)


async def image_scene(client, world, name: str = "Cripta", **overrides: Any):
    image = vault_image(world, f"{name.casefold()}.png")
    payload: dict[str, Any] = {
        "name": name,
        "source": "image",
        "image": image,
        "zones": [zone()],
        "fog_outside": True,
    }
    payload.update(overrides)
    return await create_scene(client, **payload)


async def open_table(client, **overrides: Any) -> tuple[Any, dict[str, Any]]:
    payload: dict[str, Any] = {
        "campaign": SLUG,
        "channel_id": CHANNEL,
        "scene": "cripta",
    }
    payload.update(overrides)
    response = await client.post(TABLES_ROUTE, json=payload, headers=CSRF)
    return response, await body(response)


async def token_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "label": "Ana",
        "x": 2,
        "y": 2,
        "owner_id": PLAYER,
    }
    payload.update(overrides)
    return payload


async def create_token(client, table_id: str, **overrides: Any):
    response = await client.post(
        f"{TABLES_ROUTE}/{table_id}/tokens",
        json=await token_payload(**overrides),
        headers=CSRF,
    )
    return response, await body(response)


async def add_token(client, table_id: str, **overrides: Any) -> dict[str, Any]:
    label = overrides.get("label", "Ana")
    response, payload = await create_token(client, table_id, **overrides)
    assert response.status_code == 200, payload
    return next(
        token for token in payload["tokens"] if token["label"] == label
    )


async def summary(client, table_id: str) -> dict[str, Any]:
    response = await client.get(f"{TABLES_ROUTE}/{table_id}/summary")
    assert response.status_code == 200, await body(response)
    return await body(response)


async def player_access(client, world) -> None:
    await sign_in(client, PLAYER)
    await add_member(world.database, PLAYER)
    await activate_sheet(world.database, PLAYER)


async def test_the_narrator_opens_a_table_with_round_one_and_no_turn(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)

    response, table = await open_table(client)

    assert response.status_code == 200
    assert table["status"] == "open"
    assert table["round"] == 1
    assert table["role"] == "narrator"
    assert table["name"] == "Sessão"
    assert table["channel_id"] == CHANNEL
    assert table["scene"]["slug"] == "cripta"
    assert table["tokens"] == []
    row = await world.database.fetchone("SELECT * FROM tables")
    assert row is not None
    assert row["status"] == "open"
    assert row["round"] == 1
    assert row["campaign_slug"] == SLUG
    turns = await world.database.fetchone("SELECT COUNT(*) AS n FROM turns")
    assert turns is not None and turns["n"] == 0
    assert table["id"].startswith("tbl_")


async def test_a_second_table_in_the_campaign_is_a_conflict(client, world):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, first = await open_table(client, name="Sessão 12")

    response, payload = await open_table(client, name="Outra")

    assert response.status_code == 409
    assert payload["error"]["code"] == "table_already_open"
    assert payload["table"] == {
        "id": first["id"],
        "name": "Sessão 12",
        "channel_id": CHANNEL,
    }


async def test_a_second_table_in_the_channel_is_a_conflict(client, world):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    await world.database.execute(
        "INSERT INTO campaigns ("
        "slug, name, guild_id, narrator_id, system, content_source, "
        "created_at, updated_at"
        ") VALUES ('outra', 'Outra', ?, ?, 'fate', 'vault', 1, 1)",
        (str(GUILD), NARRATOR),
    )
    other = world.root / "Harpi" / "Campaigns" / "outra" / "assets" / "a.png"
    other.parent.mkdir(parents=True)
    other.write_bytes(image_bytes())
    await world.database.execute(
        "INSERT INTO scenes ("
        "id, campaign_slug, name, source, blueprint_path, blueprint_hash, "
        "image_path, image_width, image_height, grid_json, zones_json, "
        "fog_outside, rev, created_at, updated_at"
        ") VALUES ('scn_outra', 'outra', 'Cripta', 'image', ?, 'hash', ?, "
        "800, 600, ?, '[]', 1, 1, 1, 1)",
        (
            "Harpi/Campaigns/outra/scenes/cripta.json",
            "Harpi/Campaigns/outra/assets/a.png",
            json.dumps({
                "cell_px": 70,
                "offset_x": 0,
                "offset_y": 0,
                "visible": True,
            }),
        ),
    )
    await sign_in(client, NARRATOR)
    _, first = await open_table(client)

    response, payload = await open_table(client, campaign="outra")

    assert response.status_code == 409
    assert payload["error"]["code"] == "table_already_open"
    assert payload["table"]["id"] == first["id"]


async def test_only_the_narrator_opens(client, world):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    await player_access(client, world)

    forbidden, _ = await open_table(client, channel_id="1")

    await sign_in(client, STRANGER)
    hidden, _ = await open_table(client, channel_id="2")

    assert forbidden.status_code == 403
    assert hidden.status_code == 404


async def test_opening_needs_a_scene_in_the_campaign(client, world):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)

    response, payload = await open_table(client, scene="ausente")

    assert response.status_code == 404
    assert payload["error"]["code"] == "not_found"


async def test_closing_writes_the_snapshot_before_marking_closed(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)

    response = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/close", json={}, headers=CSRF
    )

    assert response.status_code == 200
    closed = await body(response)
    assert closed["status"] == "closed"
    snapshot = world.root / CAMPAIGN / "tables" / f"{table['id']}.json"
    assert snapshot.is_file()
    data = json.loads(snapshot.read_text(encoding="utf-8"))
    assert data["kind"] == "table_snapshot"
    assert data["version"] == 1
    assert data["table"]["status"] == "closed"
    assert data["table"]["round"] == 1
    assert data["turn"] is None
    assert data["table"]["id"] == table["id"]
    assert data["scene"]["id"] == table["scene"]["id"]
    row = await world.database.fetchone(
        "SELECT status, snapshot_path FROM tables WHERE id = ?",
        (table["id"],),
    )
    assert row is not None
    assert row["status"] == "closed"
    assert row["snapshot_path"] == (f"{CAMPAIGN}/tables/{table['id']}.json")


async def test_a_failed_snapshot_keeps_the_table_open(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)

    def refuse(*args: object, **kwargs: object) -> None:
        raise OSError("disk is read-only")

    monkeypatch.setattr(tables_page.tables, "write_snapshot", refuse)
    response = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/close", json={}, headers=CSRF
    )

    assert response.status_code == 503
    assert (await body(response))["error"]["code"] == "snapshot_failed"
    row = await world.database.fetchone(
        "SELECT status FROM tables WHERE id = ?", (table["id"],)
    )
    assert row is not None and row["status"] == "open"


async def test_reopening_restores_the_snapshot(client, world):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)
    await create_token(client, table["id"], label="Ana", x=2, y=2)
    await client.post(
        f"{TABLES_ROUTE}/{table['id']}/zones/zon_sala/reveal",
        json={},
        headers=CSRF,
    )
    await client.post(
        f"{TABLES_ROUTE}/{table['id']}/close", json={}, headers=CSRF
    )
    await world.database.execute("UPDATE scenes SET zones_json = '[]'", ())
    await world.database.execute("UPDATE scenes SET fog_outside = 0", ())
    await world.database.execute("DELETE FROM tokens", ())

    response = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/reopen", json={}, headers=CSRF
    )

    assert response.status_code == 200
    reopened = await body(response)
    assert reopened["status"] == "open"
    assert reopened["warning"] is None
    assert reopened["round"] == 2
    assert reopened["scene"]["zones"][0]["revealed"] is True
    assert reopened["scene"]["fog_outside"] is True
    assert [token["label"] for token in reopened["tokens"]] == ["Ana"]
    turns = await world.database.fetchone(
        "SELECT COUNT(*) AS n FROM turns WHERE ended_at IS NULL"
    )
    assert turns is not None and turns["n"] == 0


async def test_reopening_a_table_while_another_is_open_is_a_conflict(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, first = await open_table(client, name="Primeira")
    await client.post(
        f"{TABLES_ROUTE}/{first['id']}/close", json={}, headers=CSRF
    )
    _, second = await open_table(client, name="Segunda")

    response = await client.post(
        f"{TABLES_ROUTE}/{first['id']}/reopen", json={}, headers=CSRF
    )

    assert response.status_code == 409
    payload = await body(response)
    assert payload["error"]["code"] == "table_already_open"
    assert payload["table"] == {
        "id": second["id"],
        "name": "Segunda",
        "channel_id": CHANNEL,
    }
    row = await world.database.fetchone(
        "SELECT status FROM tables WHERE id = ?", (first["id"],)
    )
    assert row is not None and row["status"] == "closed"


async def test_an_invalid_snapshot_reopens_from_sqlite_with_a_warning(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)
    await create_token(client, table["id"], label="Ana", x=2, y=2)
    await client.post(
        f"{TABLES_ROUTE}/{table['id']}/close", json={}, headers=CSRF
    )
    snapshot = world.root / CAMPAIGN / "tables" / f"{table['id']}.json"
    snapshot.write_text("{ not json", encoding="utf-8")

    response = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/reopen", json={}, headers=CSRF
    )

    assert response.status_code == 200
    reopened = await body(response)
    assert reopened["status"] == "open"
    assert reopened["warning"] is not None
    assert [token["label"] for token in reopened["tokens"]] == ["Ana"]
    assert snapshot.read_text(encoding="utf-8") == "{ not json"


async def test_a_token_keeps_position_size_label_owner_character_and_fog(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)

    response, payload = await create_token(
        client,
        table["id"],
        label="Ana",
        character_id="chr_ana",
        owner_id=PLAYER,
        x=2.5,
        y=3,
        w=2,
        h=1,
        color="#CE7442",
        visible=False,
    )
    token = payload["tokens"][0]

    assert response.status_code == 200
    assert token["label"] == "Ana"
    assert token["character_id"] == "chr_ana"
    assert token["owner_id"] == PLAYER
    assert token["x"] == pytest.approx(2.5)
    assert token["y"] == pytest.approx(3.0)
    assert (token["w"], token["h"]) == (2, 1)
    assert token["color"] == "#ce7442"
    assert token["visible"] is False
    row = await world.database.fetchone(
        "SELECT * FROM tokens WHERE table_id = ?", (table["id"],)
    )
    assert row is not None
    assert row["scene_id"] == table["scene"]["id"]


@pytest.mark.parametrize(
    "payload",
    [
        {"x": -0.1, "y": 1},
        {"x": 100, "y": 1},
        {"x": 1, "y": 1, "w": 0},
        {"x": 1, "y": 1, "w": 20},
        {"x": 11, "y": 1, "w": 2},
        {"label": "   ", "x": 1, "y": 1},
        {"x": 1, "y": 1, "color": "red"},
        {"x": float("nan"), "y": 1},
    ],
)
async def test_an_out_of_bounds_or_bad_token_is_422(client, world, payload):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)

    response = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/tokens",
        json={"label": "Ana", **payload},
        headers=CSRF,
    )

    assert response.status_code == 422
    assert (await body(response))["error"]["code"] == "invalid_payload"


async def test_a_token_can_be_moved_renamed_and_removed(client, world):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)
    _, token = await create_token(client, table["id"])
    token = (await summary(client, table["id"]))["tokens"][0]

    moved = await client.patch(
        f"{TABLES_ROUTE}/{table['id']}/tokens/{token['id']}",
        json={"x": 4.5, "label": "Ana Velha", "visible": False},
        headers=CSRF,
    )
    removed = await client.delete(
        f"{TABLES_ROUTE}/{table['id']}/tokens/{token['id']}",
        headers={**CSRF, "Content-Type": "application/json"},
    )

    assert moved.status_code == 200
    assert (await body(moved))["tokens"][0]["x"] == pytest.approx(4.5)
    assert removed.status_code == 200
    assert (await body(removed))["tokens"] == []
    row = await world.database.fetchone(
        "SELECT COUNT(*) AS n FROM tokens WHERE table_id = ?", (table["id"],)
    )
    assert row is not None and row["n"] == 0


async def test_a_token_from_an_old_scene_cannot_be_patched_or_removed(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world, name="Cripta")
    await create_scene(
        client,
        name="Calabouço",
        source="sketch",
        image_width=800,
        image_height=600,
        zones=[zone("Cela", "zon_cela")],
    )
    _, table = await open_table(client)
    token = await add_token(client, table["id"], label="Ana", x=2, y=2)
    await client.post(
        f"{TABLES_ROUTE}/{table['id']}/scene",
        json={"scene": "calabouco"},
        headers=CSRF,
    )

    patched = await client.patch(
        f"{TABLES_ROUTE}/{table['id']}/tokens/{token['id']}",
        json={"x": 1},
        headers=CSRF,
    )
    removed = await client.delete(
        f"{TABLES_ROUTE}/{table['id']}/tokens/{token['id']}",
        headers={**CSRF, "Content-Type": "application/json"},
    )

    assert patched.status_code == 404
    assert removed.status_code == 404
    row = await world.database.fetchone(
        "SELECT scene_id FROM tokens WHERE id = ?", (token["id"],)
    )
    assert row is not None


async def test_only_the_narrator_manages_tokens(client, world):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)
    _, token = await create_token(client, table["id"])
    token = (await summary(client, table["id"]))["tokens"][0]
    await player_access(client, world)

    created, _ = await create_token(client, table["id"], x=1)
    patched = await client.patch(
        f"{TABLES_ROUTE}/{table['id']}/tokens/{token['id']}",
        json={"x": 1},
        headers=CSRF,
    )
    removed = await client.delete(
        f"{TABLES_ROUTE}/{table['id']}/tokens/{token['id']}",
        headers={**CSRF, "Content-Type": "application/json"},
    )

    assert [created.status_code, patched.status_code, removed.status_code] == [
        403,
        403,
        403,
    ]


async def test_the_player_cutout_hides_invisible_hidden_zone_and_outside(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world, fog_outside=True)
    _, table = await open_table(client)
    await create_token(client, table["id"], label="Visível", x=0, y=0)
    await create_token(
        client, table["id"], label="Invisível", x=2, y=2, visible=False
    )
    await create_token(client, table["id"], label="Zona oculta", x=2, y=2)
    await player_access(client, world)

    cut = await summary(client, table["id"])

    assert cut["role"] == "player"
    assert [token["label"] for token in cut["tokens"]] == []
    assert cut["scene"]["zones"] == []
    assert cut["scene"]["fog"] == [{"x": 1, "y": 2, "w": 3, "h": 2}]
    await sign_in(client, NARRATOR)
    full = await summary(client, table["id"])
    assert {token["label"] for token in full["tokens"]} == {
        "Visível",
        "Invisível",
        "Zona oculta",
    }
    assert len(full["scene"]["zones"]) == 1
    assert full["scene"]["fog"] == []


async def test_a_token_outside_every_zone_is_public_when_fog_outside_is_off(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world, fog_outside=False)
    _, table = await open_table(client)
    await create_token(client, table["id"], label="Fora", x=0, y=0)
    await player_access(client, world)

    cut = await summary(client, table["id"])

    assert [token["label"] for token in cut["tokens"]] == ["Fora"]


async def test_revealing_a_zone_updates_the_cutout_and_reveals_the_npc(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world, fog_outside=True)
    _, table = await open_table(client)
    _, _token = await create_token(
        client,
        table["id"],
        label="Goblin",
        character_id="chr_goblin",
        x=2,
        y=2,
    )
    await player_access(client, world)
    assert (await summary(client, table["id"]))["tokens"] == []

    await sign_in(client, NARRATOR)
    response = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/zones/zon_sala/reveal",
        json={},
        headers=CSRF,
    )

    assert response.status_code == 200
    revealed = await summary(client, table["id"])
    assert revealed["scene"]["zones"][0]["revealed"] is True
    assert [item["label"] for item in revealed["tokens"]] == ["Goblin"]
    row = await world.database.fetchone(
        "SELECT * FROM character_visibility WHERE character_id = ?",
        ("chr_goblin",),
    )
    assert row is not None
    assert row["revealed_by"] == NARRATOR

    hidden = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/zones/zon_sala/hide",
        json={},
        headers=CSRF,
    )
    assert hidden.status_code == 200
    assert (await body(hidden))["scene"]["zones"][0]["revealed"] is False


async def test_a_token_created_in_a_revealed_zone_reveals_its_character(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world, fog_outside=True)
    _, table = await open_table(client)
    await client.post(
        f"{TABLES_ROUTE}/{table['id']}/zones/zon_sala/reveal",
        json={},
        headers=CSRF,
    )

    await create_token(
        client,
        table["id"],
        label="Goblin",
        character_id="chr_goblin",
        x=2,
        y=2,
    )

    row = await world.database.fetchone(
        "SELECT * FROM character_visibility WHERE character_id = ?",
        ("chr_goblin",),
    )
    assert row is not None
    assert row["revealed_by"] == NARRATOR


async def test_moving_a_token_into_a_revealed_zone_reveals_its_character(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world, fog_outside=True)
    _, table = await open_table(client)
    await client.post(
        f"{TABLES_ROUTE}/{table['id']}/zones/zon_sala/reveal",
        json={},
        headers=CSRF,
    )
    token = await add_token(
        client,
        table["id"],
        label="Goblin",
        character_id="chr_goblin",
        x=0,
        y=0,
    )
    before = await world.database.fetchone(
        "SELECT COUNT(*) AS n FROM character_visibility"
    )
    assert before is not None and before["n"] == 0

    moved = await client.patch(
        f"{TABLES_ROUTE}/{table['id']}/tokens/{token['id']}",
        json={"x": 2, "y": 2},
        headers=CSRF,
    )

    assert moved.status_code == 200
    row = await world.database.fetchone(
        "SELECT * FROM character_visibility WHERE character_id = ?",
        ("chr_goblin",),
    )
    assert row is not None


async def test_the_player_cutout_keeps_only_revealed_zones_and_fog_rects(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(
        client,
        world,
        zones=[
            zone(
                "Sala oculta",
                "zon_oculta",
                rects=[{"x": 0, "y": 0, "w": 3, "h": 3}],
            ),
            zone(
                "Sala revelada",
                "zon_revelada",
                revealed=True,
                rects=[{"x": 1, "y": 1, "w": 2, "h": 2}],
            ),
        ],
    )
    _, table = await open_table(client)
    await player_access(client, world)

    cut = await summary(client, table["id"])

    assert [zone["id"] for zone in cut["scene"]["zones"]] == ["zon_revelada"]
    assert cut["scene"]["fog"] == [{"x": 0, "y": 0, "w": 3, "h": 3}]


async def test_an_unknown_zone_is_404_and_players_cannot_toggle(client, world):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)
    await player_access(client, world)

    player = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/zones/zon_sala/reveal",
        json={},
        headers=CSRF,
    )
    await sign_in(client, NARRATOR)
    missing = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/zones/zon_nada/reveal",
        json={},
        headers=CSRF,
    )

    assert player.status_code == 403
    assert missing.status_code == 404


async def test_reloading_a_scene_keeps_fog_by_zone_id_and_token_rows(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(
        client,
        world,
        zones=[
            zone("Sala", "zon_sala"),
            zone(
                "Corredor",
                "zon_corredor",
                rects=[{"x": 5, "y": 5, "w": 2, "h": 2}],
            ),
        ],
    )
    _, table = await open_table(client)
    await create_token(client, table["id"], label="Ana", x=2, y=2)
    await client.post(
        f"{TABLES_ROUTE}/{table['id']}/zones/zon_sala/reveal",
        json={},
        headers=CSRF,
    )
    await world.database.execute(
        "INSERT INTO turns ("
        "id, table_id, scene_id, round, token_id, character_id, label, "
        "started_at, started_by"
        ") VALUES ('trn_open', ?, ?, 1, NULL, NULL, 'Ana', 1, ?)",
        (table["id"], table["scene"]["id"], NARRATOR),
    )
    blueprint = world.root / CAMPAIGN / "scenes" / "cripta.json"
    data = json.loads(blueprint.read_text(encoding="utf-8"))
    data["zones"] = [
        zone("Sala nova", "zon_sala"),
        zone("Cripta", "zon_nova", rects=[{"x": 3, "y": 3, "w": 2, "h": 2}]),
    ]
    blueprint.write_text(json.dumps(data), encoding="utf-8")

    response = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/scene/reload", json={}, headers=CSRF
    )

    assert response.status_code == 200
    reloaded = await body(response)
    zones = {item["id"]: item for item in reloaded["scene"]["zones"]}
    assert zones["zon_sala"]["revealed"] is True
    assert zones["zon_nova"]["revealed"] is False
    assert "zon_corredor" not in zones
    assert [token["label"] for token in reloaded["tokens"]] == ["Ana"]
    turn = await world.database.fetchone(
        "SELECT ended_at FROM turns WHERE id = 'trn_open'"
    )
    assert turn is not None and turn["ended_at"] is not None


async def test_switching_scene_keeps_each_scene_fog_and_tokens(client, world):
    await sign_in(client, NARRATOR)
    await image_scene(client, world, name="Cripta")
    await create_scene(
        client,
        name="Calabouço",
        source="sketch",
        image_width=800,
        image_height=600,
        zones=[zone("Cela", "zon_cela")],
        fog_outside=True,
    )
    _, table = await open_table(client)
    await create_token(client, table["id"], label="Ana", x=2, y=2)
    await client.post(
        f"{TABLES_ROUTE}/{table['id']}/zones/zon_sala/reveal",
        json={},
        headers=CSRF,
    )

    changed = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/scene",
        json={"scene": "calabouco"},
        headers=CSRF,
    )
    assert changed.status_code == 200
    assert (await body(changed))["tokens"] == []

    await create_token(client, table["id"], label="Goblin", x=3, y=3)
    back = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/scene",
        json={"scene": "cripta"},
        headers=CSRF,
    )
    restored = await body(back)

    assert [token["label"] for token in restored["tokens"]] == ["Ana"]
    assert restored["scene"]["zones"][0]["revealed"] is True
    assert restored["scene"]["slug"] == "cripta"


async def test_the_map_serves_the_current_scene_image_and_svg(client, world):
    await sign_in(client, NARRATOR)
    await image_scene(client, world, name="Cripta")
    calabouco = await create_scene(
        client,
        name="Calabouço",
        source="sketch",
        image_width=420,
        image_height=280,
        zones=[zone("Cela", "zon_cela")],
    )
    await client.put(
        f"{SCENES_ROUTE}/calabouco",
        json={
            "base_hash": calabouco["hash"],
            "name": "Calabouço",
            "grid": calabouco["grid"],
            "fog_outside": True,
            "zones": [zone("Cela", "zon_cela")],
        },
        headers=CSRF,
    )
    _, table = await open_table(client)

    image = await client.get(f"{TABLES_ROUTE}/{table['id']}/map")
    assert image.status_code == 200
    assert image.headers["Content-Type"] == "image/png"
    assert image.headers["Cache-Control"].startswith("private")

    await client.post(
        f"{TABLES_ROUTE}/{table['id']}/scene",
        json={"scene": "calabouco"},
        headers=CSRF,
    )
    sketch = await client.get(f"{TABLES_ROUTE}/{table['id']}/map")
    assert sketch.status_code == 200
    assert sketch.headers["Content-Type"] == "image/svg+xml"
    assert sketch.headers["X-Content-Type-Options"] == "nosniff"
    assert sketch.headers["Content-Security-Policy"] == "sandbox"


async def test_a_spectator_reads_the_player_cutout_and_cannot_mutate(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world, fog_outside=True)
    _, table = await open_table(client)
    await create_token(
        client, table["id"], label="Invisível", x=2, y=2, visible=False
    )
    enabled = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/spectators",
        json={"enabled": True},
        headers=CSRF,
    )
    assert enabled.status_code == 200
    assert (await body(enabled))["spectators"] is True

    await sign_in(client, STRANGER)
    cut = await summary(client, table["id"])
    mapped = await client.get(f"{TABLES_ROUTE}/{table['id']}/map")
    forbidden = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/spectators",
        json={"enabled": False},
        headers=CSRF,
    )

    assert cut["role"] == "spectator"
    assert cut["tokens"] == []
    assert mapped.status_code == 200
    assert forbidden.status_code == 403


async def test_an_outsider_without_the_spectator_flag_gets_404(client, world):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)

    await sign_in(client, STRANGER)
    response = await client.get(f"{TABLES_ROUTE}/{table['id']}/summary")

    assert response.status_code == 404


async def test_a_closed_table_refuses_mutations(client, world):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)
    await client.post(
        f"{TABLES_ROUTE}/{table['id']}/close", json={}, headers=CSRF
    )

    response, payload = await create_token(client, table["id"], x=1)
    zone_response = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/zones/zon_sala/reveal",
        json={},
        headers=CSRF,
    )
    scene_response = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/scene",
        json={"scene": "cripta"},
        headers=CSRF,
    )

    assert response.status_code == 409
    assert payload["error"]["code"] == "table_closed"
    assert zone_response.status_code == 409
    assert scene_response.status_code == 409


async def test_the_campaign_detail_and_gallery_mark_the_live_table(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)

    detail = await body(await client.get(f"/api/campaigns/{SLUG}"))
    cards = (await body(await client.get(SCENES_ROUTE)))["scenes"]

    assert detail["open_table"] == {
        "id": table["id"],
        "name": "Sessão",
        "channel_id": CHANNEL,
    }
    assert cards[0]["in_use"] is True


async def test_the_summary_answers_every_role_without_leaking_tokens(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)
    await player_access(client, world)
    viewer = await summary(client, table["id"])

    assert viewer["viewer_id"] == PLAYER
    assert viewer["role"] == "player"
    assert viewer["channel_id"] == CHANNEL
    assert viewer["campaign"] == SLUG


async def test_an_unknown_table_is_404(client, world):
    await sign_in(client, NARRATOR)

    response = await client.get(f"{TABLES_ROUTE}/tbl_nada/summary")

    assert response.status_code == 404
    assert (await body(response))["error"]["code"] == "not_found"


async def test_mutating_a_table_needs_json_and_same_origin(client, world):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)

    no_json = await client.post(f"{TABLES_ROUTE}/{table['id']}/close")
    no_origin = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/close", json={}
    )

    assert no_json.status_code == 403
    assert no_origin.status_code == 403


async def test_a_missing_token_or_out_of_bounds_patch_is_refused(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)
    token = await add_token(client, table["id"])

    missing = await client.patch(
        f"{TABLES_ROUTE}/{table['id']}/tokens/tok_nada",
        json={"x": 1},
        headers=CSRF,
    )
    bounds = await client.patch(
        f"{TABLES_ROUTE}/{table['id']}/tokens/{token['id']}",
        json={"x": 99},
        headers=CSRF,
    )

    assert missing.status_code == 404
    assert bounds.status_code == 422
    assert (await body(bounds))["error"]["code"] == "invalid_payload"


async def test_a_token_without_a_current_scene_is_404(client, world):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)
    token = await add_token(client, table["id"])
    await world.database.execute(
        "UPDATE tables SET current_scene_id = NULL WHERE id = ?",
        (table["id"],),
    )

    patched = await client.patch(
        f"{TABLES_ROUTE}/{table['id']}/tokens/{token['id']}",
        json={"x": 1},
        headers=CSRF,
    )
    created, _ = await create_token(client, table["id"], x=1)

    assert patched.status_code == 404
    assert created.status_code == 404


async def test_reloading_an_unreadable_or_absent_scene_fails_cleanly(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)
    blueprint = world.root / CAMPAIGN / "scenes" / "cripta.json"
    blueprint.unlink()

    unreadable = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/scene/reload", json={}, headers=CSRF
    )
    await world.database.execute(
        "UPDATE tables SET current_scene_id = NULL WHERE id = ?",
        (table["id"],),
    )
    absent = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/scene/reload", json={}, headers=CSRF
    )

    assert unreadable.status_code == 409
    assert (await body(unreadable))["error"]["code"] == "scene_unreadable"
    assert absent.status_code == 404


async def test_reloading_without_a_vault_is_503(client, world):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)
    vault.configure(vault.Vault())

    response = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/scene/reload", json={}, headers=CSRF
    )

    assert response.status_code == 503
    assert (await body(response))["error"]["code"] == "vault_unavailable"


async def test_the_map_is_404_without_scene_or_image_and_503_without_vault(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)
    vault.configure(vault.Vault())
    unavailable = await client.get(f"{TABLES_ROUTE}/{table['id']}/map")
    vault.configure(vault.Vault(root=world.root))
    vault_index.configure(VaultIndex(world.root))
    (world.root / CAMPAIGN / "assets" / "cripta.png").unlink()
    missing_image = await client.get(f"{TABLES_ROUTE}/{table['id']}/map")
    await world.database.execute(
        "UPDATE tables SET current_scene_id = NULL WHERE id = ?",
        (table["id"],),
    )
    missing_scene = await client.get(f"{TABLES_ROUTE}/{table['id']}/map")

    assert unavailable.status_code == 503
    assert missing_image.status_code == 404
    assert missing_scene.status_code == 404


async def test_closing_a_closed_table_and_reopening_an_open_one_conflict(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)
    reopened = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/reopen", json={}, headers=CSRF
    )
    await client.post(
        f"{TABLES_ROUTE}/{table['id']}/close", json={}, headers=CSRF
    )
    closed = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/close", json={}, headers=CSRF
    )

    assert reopened.status_code == 409
    assert closed.status_code == 409
    assert (await body(closed))["error"]["code"] == "table_closed"


async def test_changing_to_an_unknown_scene_is_404(client, world):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)

    response = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/scene",
        json={"scene": "ausente"},
        headers=CSRF,
    )

    assert response.status_code == 404


async def test_the_summary_flags_a_scene_changed_on_disk(client, world):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)
    blueprint = world.root / CAMPAIGN / "scenes" / "cripta.json"
    data = json.loads(blueprint.read_text(encoding="utf-8"))
    data["name"] = "Cripta do Obsidian"
    blueprint.write_text(json.dumps(data), encoding="utf-8")

    response = await summary(client, table["id"])

    assert response["scene"]["saved"] is False


async def test_the_summary_marks_an_unchanged_scene_as_saved(client, world):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)

    response = await summary(client, table["id"])

    assert response["scene"]["saved"] is True


async def test_the_player_summary_does_not_read_the_blueprint(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world)
    _, table = await open_table(client)
    blueprint = world.root / CAMPAIGN / "scenes" / "cripta.json"
    data = json.loads(blueprint.read_text(encoding="utf-8"))
    data["name"] = "Cripta do Obsidian"
    blueprint.write_text(json.dumps(data), encoding="utf-8")
    await player_access(client, world)

    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("the player summary read the blueprint")

    monkeypatch.setattr("src.panel.scenes.load_blueprint", refuse)
    response = await summary(client, table["id"])

    assert response["scene"]["saved"] is True


async def public_scene(client, world) -> dict[str, Any]:
    await sign_in(client, NARRATOR)
    await image_scene(client, world, fog_outside=False)
    _, table = await open_table(client)
    return table


AUTO = object()


async def turn(
    client,
    table_id: str,
    action: str,
    token_id: str | None = None,
    expected: object = AUTO,
):
    payload: dict[str, Any] = {"action": action}
    if token_id is not None:
        payload["token_id"] = token_id
    if expected is AUTO:
        expected = None
        if action in {"pass", "end"}:
            view = await summary(client, table_id)
            expected = None if view["turn"] is None else view["turn"]["id"]
    if expected is not None:
        payload["expected_turn_id"] = expected
    response = await client.post(
        f"{TABLES_ROUTE}/{table_id}/turns", json=payload, headers=CSRF
    )
    return response, await body(response)


def participant(payload: dict[str, Any], label: str) -> dict[str, Any]:
    return next(
        item for item in payload["participants"] if item["label"] == label
    )


async def test_the_narrator_opens_the_turn_of_a_pending_participant(
    client, world
):
    table = await public_scene(client, world)
    ana = await add_token(client, table["id"], label="Ana", x=0, y=0)
    await add_token(client, table["id"], label="Bob", x=5, y=5)

    response, payload = await turn(client, table["id"], "open", ana["id"])

    assert response.status_code == 200, payload
    assert payload["turn"]["token_id"] == ana["id"]
    assert payload["turn"]["label"] == "Ana"
    assert payload["turn"]["round"] == 1
    assert participant(payload, "Ana")["acted"] is True
    assert participant(payload, "Bob")["acted"] is False
    row = await world.database.fetchone(
        "SELECT * FROM turns WHERE table_id = ?", (table["id"],)
    )
    assert row is not None
    assert row["ended_at"] is None
    assert row["round"] == 1
    assert row["started_by"] == NARRATOR


async def test_a_hidden_token_never_takes_a_turn(client, world):
    await sign_in(client, NARRATOR)
    await image_scene(client, world, fog_outside=True)
    _, table = await open_table(client)
    goblin = await add_token(
        client, table["id"], label="Goblin", x=2, y=2, visible=False
    )

    response, payload = await turn(client, table["id"], "open", goblin["id"])

    assert response.status_code == 422
    assert payload["error"]["code"] == "turn_not_participant"
    view = await summary(client, table["id"])
    assert view["participants"] == []
    assert view["turn"] is None


async def test_only_one_turn_is_open_and_an_acted_token_is_not_pending(
    client, world
):
    table = await public_scene(client, world)
    ana = await add_token(client, table["id"], label="Ana", x=0, y=0)
    bob = await add_token(client, table["id"], label="Bob", x=5, y=5)
    await turn(client, table["id"], "open", ana["id"])

    second, payload = await turn(client, table["id"], "open", bob["id"])

    assert second.status_code == 422
    assert payload["error"]["code"] == "turn_open"
    await turn(client, table["id"], "end", ana["id"])
    acted, again = await turn(client, table["id"], "open", ana["id"])
    assert acted.status_code == 422
    assert again["error"]["code"] == "turn_taken"


async def test_the_player_passes_their_turn_and_ends_up_without_one(
    client, world
):
    table = await public_scene(client, world)
    ana = await add_token(
        client, table["id"], label="Ana", x=0, y=0, owner_id=PLAYER
    )
    bob = await add_token(
        client, table["id"], label="Bob", x=5, y=5, owner_id=PLAYER
    )
    await add_token(client, table["id"], label="Cid", x=8, y=8)
    await turn(client, table["id"], "open", ana["id"])
    await player_access(client, world)

    passed, payload = await turn(client, table["id"], "pass", bob["id"])

    assert passed.status_code == 200, payload
    assert payload["turn"]["token_id"] == bob["id"]
    assert participant(payload, "Ana")["acted"] is True
    assert participant(payload, "Bob")["acted"] is True
    ended, done = await turn(client, table["id"], "end")

    assert ended.status_code == 200, done
    assert done["turn"] is None
    assert done["round"] == 1
    assert participant(done, "Bob")["acted"] is True


async def test_passing_to_someone_who_already_acted_is_422(client, world):
    table = await public_scene(client, world)
    ana = await add_token(
        client, table["id"], label="Ana", x=0, y=0, owner_id=PLAYER
    )
    bob = await add_token(client, table["id"], label="Bob", x=5, y=5)
    await turn(client, table["id"], "open", ana["id"])
    await player_access(client, world)

    response, payload = await turn(client, table["id"], "pass", ana["id"])

    assert response.status_code == 422
    assert payload["error"]["code"] == "turn_taken"
    await turn(client, table["id"], "pass", bob["id"])
    await sign_in(client, NARRATOR)
    again, taken = await turn(client, table["id"], "pass", ana["id"])
    assert again.status_code == 422
    assert taken["error"]["code"] == "turn_taken"


async def test_the_last_pending_ends_the_round_and_nobody_starts_alone(
    client, world
):
    table = await public_scene(client, world)
    ana = await add_token(client, table["id"], label="Ana", x=0, y=0)
    bob = await add_token(client, table["id"], label="Bob", x=5, y=5)
    await turn(client, table["id"], "open", ana["id"])

    _, passed = await turn(client, table["id"], "pass", bob["id"])

    assert passed["round"] == 1
    assert passed["turn"]["token_id"] == bob["id"]
    response, closed = await turn(client, table["id"], "end")

    assert response.status_code == 200
    assert closed["round"] == 2
    assert closed["turn"] is None
    assert participant(closed, "Ana")["acted"] is False
    assert participant(closed, "Bob")["acted"] is False
    rows = await world.database.fetchall(
        "SELECT * FROM turns WHERE table_id = ? ORDER BY started_at",
        (table["id"],),
    )
    assert [row["round"] for row in rows] == [1, 1]
    assert all(row["ended_at"] is not None for row in rows)


async def test_ending_without_passing_leaves_the_table_without_a_turn(
    client, world
):
    table = await public_scene(client, world)
    ana = await add_token(client, table["id"], label="Ana", x=0, y=0)
    await add_token(client, table["id"], label="Bob", x=5, y=5)
    await turn(client, table["id"], "open", ana["id"])

    response, payload = await turn(client, table["id"], "end", ana["id"])

    assert response.status_code == 200
    assert payload["turn"] is None
    assert payload["round"] == 1


async def test_a_token_created_mid_round_enters_pending(client, world):
    table = await public_scene(client, world)
    ana = await add_token(client, table["id"], label="Ana", x=0, y=0)
    await add_token(client, table["id"], label="Bob", x=5, y=5)
    await turn(client, table["id"], "open", ana["id"])
    await turn(client, table["id"], "end", ana["id"])

    cid = await add_token(client, table["id"], label="Cid", x=8, y=8)

    view = await summary(client, table["id"])
    assert participant(view, "Ana")["acted"] is True
    assert participant(view, "Cid")["acted"] is False
    opened, payload = await turn(client, table["id"], "open", cid["id"])
    assert opened.status_code == 200, payload


async def test_a_token_that_enters_a_revealed_zone_enters_pending(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world, fog_outside=True)
    _, table = await open_table(client)
    hidden = await add_token(client, table["id"], label="Goblin", x=2, y=2)
    view = await summary(client, table["id"])
    assert view["participants"] == []

    await client.post(
        f"{TABLES_ROUTE}/{table['id']}/zones/zon_sala/reveal",
        json={},
        headers=CSRF,
    )

    view = await summary(client, table["id"])
    assert participant(view, "Goblin")["acted"] is False
    response, payload = await turn(client, table["id"], "open", hidden["id"])
    assert response.status_code == 200, payload


async def test_moving_a_token_into_a_revealed_zone_enters_pending(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world, fog_outside=True)
    _, table = await open_table(client)
    hidden = await add_token(client, table["id"], label="Goblin", x=0, y=0)
    await client.post(
        f"{TABLES_ROUTE}/{table['id']}/zones/zon_sala/reveal",
        json={},
        headers=CSRF,
    )
    assert (await summary(client, table["id"]))["participants"] == []

    await client.patch(
        f"{TABLES_ROUTE}/{table['id']}/tokens/{hidden['id']}",
        json={"x": 2, "y": 2},
        headers=CSRF,
    )

    view = await summary(client, table["id"])
    assert participant(view, "Goblin")["acted"] is False


async def test_hiding_the_last_pending_closes_the_round(client, world):
    table = await public_scene(client, world)
    ana = await add_token(client, table["id"], label="Ana", x=0, y=0)
    bob = await add_token(client, table["id"], label="Bob", x=5, y=5)
    await turn(client, table["id"], "open", ana["id"])
    await turn(client, table["id"], "end")

    response = await client.patch(
        f"{TABLES_ROUTE}/{table['id']}/tokens/{bob['id']}",
        json={"visible": False},
        headers=CSRF,
    )

    assert response.status_code == 200
    view = await body(response)
    assert view["round"] == 2
    assert view["turn"] is None
    assert [item["label"] for item in view["participants"]] == ["Ana"]
    assert view["participants"][0]["acted"] is False


async def test_hiding_the_token_that_holds_the_turn_ends_it(client, world):
    table = await public_scene(client, world)
    ana = await add_token(client, table["id"], label="Ana", x=0, y=0)
    await add_token(client, table["id"], label="Bob", x=5, y=5)
    await turn(client, table["id"], "open", ana["id"])

    response = await client.patch(
        f"{TABLES_ROUTE}/{table['id']}/tokens/{ana['id']}",
        json={"visible": False},
        headers=CSRF,
    )

    assert response.status_code == 200
    view = await body(response)
    assert view["turn"] is None
    assert view["round"] == 1
    assert [item["label"] for item in view["participants"]] == ["Bob"]
    row = await world.database.fetchone(
        "SELECT ended_at FROM turns WHERE table_id = ?", (table["id"],)
    )
    assert row is not None and row["ended_at"] is not None


async def test_hiding_another_token_keeps_the_open_turn(client, world):
    table = await public_scene(client, world)
    ana = await add_token(client, table["id"], label="Ana", x=0, y=0)
    bob = await add_token(client, table["id"], label="Bob", x=5, y=5)
    await turn(client, table["id"], "open", bob["id"])

    response = await client.patch(
        f"{TABLES_ROUTE}/{table['id']}/tokens/{ana['id']}",
        json={"visible": False},
        headers=CSRF,
    )

    assert response.status_code == 200
    view = await body(response)
    assert view["turn"]["token_id"] == bob["id"]
    assert [item["token_id"] for item in view["participants"]] == [bob["id"]]


async def test_hiding_a_token_that_already_acted_does_not_block_the_round(
    client, world
):
    table = await public_scene(client, world)
    ana = await add_token(client, table["id"], label="Ana", x=0, y=0)
    bob = await add_token(client, table["id"], label="Bob", x=5, y=5)
    await turn(client, table["id"], "open", ana["id"])
    await turn(client, table["id"], "end")
    await client.patch(
        f"{TABLES_ROUTE}/{table['id']}/tokens/{ana['id']}",
        json={"visible": False},
        headers=CSRF,
    )
    await turn(client, table["id"], "open", bob["id"])

    response, payload = await turn(client, table["id"], "end")

    assert response.status_code == 200
    assert payload["round"] == 2
    assert payload["turn"] is None
    assert [item["label"] for item in payload["participants"]] == ["Bob"]
    assert payload["participants"][0]["acted"] is False


async def test_removing_a_token_ends_its_open_turn(client, world):
    table = await public_scene(client, world)
    ana = await add_token(client, table["id"], label="Ana", x=0, y=0)
    await turn(client, table["id"], "open", ana["id"])

    removed = await client.delete(
        f"{TABLES_ROUTE}/{table['id']}/tokens/{ana['id']}",
        headers={**CSRF, "Content-Type": "application/json"},
    )

    assert removed.status_code == 200
    view = await body(removed)
    assert view["participants"] == []
    assert view["turn"] is None
    row = await world.database.fetchone(
        "SELECT ended_at FROM turns WHERE table_id = ?", (table["id"],)
    )
    assert row is not None and row["ended_at"] is not None


async def test_removing_another_token_keeps_the_open_turn(client, world):
    table = await public_scene(client, world)
    ana = await add_token(client, table["id"], label="Ana", x=0, y=0)
    bob = await add_token(client, table["id"], label="Bob", x=5, y=5)
    await turn(client, table["id"], "open", ana["id"])

    removed = await client.delete(
        f"{TABLES_ROUTE}/{table['id']}/tokens/{bob['id']}",
        headers={**CSRF, "Content-Type": "application/json"},
    )

    assert removed.status_code == 200
    view = await body(removed)
    assert view["turn"]["token_id"] == ana["id"]
    assert [item["label"] for item in view["participants"]] == ["Ana"]


async def test_closing_ends_the_round_and_reopening_starts_a_new_one(
    client, world
):
    table = await public_scene(client, world)
    ana = await add_token(client, table["id"], label="Ana", x=0, y=0)
    await add_token(client, table["id"], label="Bob", x=5, y=5)
    await turn(client, table["id"], "open", ana["id"])
    await turn(client, table["id"], "end", ana["id"])

    closed = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/close", json={}, headers=CSRF
    )
    assert closed.status_code == 200
    reopened = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/reopen", json={}, headers=CSRF
    )

    assert reopened.status_code == 200
    view = await body(reopened)
    assert view["status"] == "open"
    assert view["round"] == 2
    assert view["turn"] is None
    assert all(item["acted"] is False for item in view["participants"])
    snapshot = world.root / CAMPAIGN / "tables" / f"{table['id']}.json"
    data = json.loads(snapshot.read_text(encoding="utf-8"))
    assert data["table"]["status"] == "closed"
    assert data["table"]["round"] == 1
    assert data["turn"] is None


async def test_only_the_player_of_the_turn_passes_or_ends_it(client, world):
    table = await public_scene(client, world)
    ana = await add_token(
        client, table["id"], label="Ana", x=0, y=0, owner_id=PLAYER
    )
    bob = await add_token(
        client, table["id"], label="Bob", x=5, y=5, owner_id=None
    )
    await turn(client, table["id"], "open", bob["id"])
    await player_access(client, world)

    ended, payload = await turn(client, table["id"], "end")

    assert ended.status_code == 403
    assert payload["error"]["code"] == "turn_not_yours"
    await sign_in(client, NARRATOR)
    await turn(client, table["id"], "end")
    await turn(client, table["id"], "open", ana["id"])
    await sign_in(client, PLAYER)
    own, own_payload = await turn(client, table["id"], "end")

    assert own.status_code == 200, own_payload
    assert own_payload["turn"] is None


async def test_players_cannot_open_and_pending_or_spectators_cannot_act(
    client, world
):
    table = await public_scene(client, world)
    ana = await add_token(
        client, table["id"], label="Ana", x=0, y=0, owner_id=PLAYER
    )
    await player_access(client, world)

    opened, opened_payload = await turn(client, table["id"], "open", ana["id"])
    assert opened.status_code == 403
    assert opened_payload["error"]["code"] == "forbidden"

    await add_member(world.database, STRANGER)
    await sign_in(client, STRANGER)
    pending, pending_payload = await turn(
        client, table["id"], "open", ana["id"]
    )
    assert pending.status_code == 403
    assert pending_payload["error"]["code"] == "forbidden"

    await sign_in(client, NARRATOR)
    await turn(client, table["id"], "open", ana["id"])
    await client.post(
        f"{TABLES_ROUTE}/{table['id']}/spectators",
        json={"enabled": True},
        headers=CSRF,
    )
    await sign_in(client, "999")
    spectator, spectator_payload = await turn(client, table["id"], "end")

    assert spectator.status_code == 403
    assert spectator_payload["error"]["code"] == "forbidden"


async def test_a_closed_table_refuses_turn_actions(client, world):
    table = await public_scene(client, world)
    ana = await add_token(client, table["id"], label="Ana", x=0, y=0)
    await client.post(
        f"{TABLES_ROUTE}/{table['id']}/close", json={}, headers=CSRF
    )

    response, payload = await turn(client, table["id"], "open", ana["id"])

    assert response.status_code == 409
    assert payload["error"]["code"] == "table_closed"


async def test_an_unknown_turn_target_is_404(client, world):
    table = await public_scene(client, world)
    await add_token(client, table["id"], label="Ana", x=0, y=0)

    response, payload = await turn(client, table["id"], "open", "tok_nada")

    assert response.status_code == 404
    assert payload["error"]["code"] == "not_found"


async def test_changing_scene_with_the_last_turn_closes_the_round(
    client, world
):
    await sign_in(client, NARRATOR)
    await image_scene(client, world, name="Cripta", fog_outside=False)
    await create_scene(
        client,
        name="Calabouço",
        source="sketch",
        image_width=800,
        image_height=600,
        zones=[zone("Cela", "zon_cela")],
    )
    _, table = await open_table(client)
    ana = await add_token(client, table["id"], label="Ana", x=0, y=0)
    await turn(client, table["id"], "open", ana["id"])

    response = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/scene",
        json={"scene": "calabouco"},
        headers=CSRF,
    )

    assert response.status_code == 200
    view = await body(response)
    assert view["scene"]["slug"] == "calabouco"
    assert view["round"] == 2
    assert view["turn"] is None
    assert view["participants"] == []


async def test_reloading_a_scene_with_the_last_turn_closes_the_round(
    client, world
):
    table = await public_scene(client, world)
    ana = await add_token(client, table["id"], label="Ana", x=0, y=0)
    bob = await add_token(client, table["id"], label="Bob", x=5, y=5)
    await turn(client, table["id"], "open", ana["id"])
    await turn(client, table["id"], "pass", bob["id"])

    response = await client.post(
        f"{TABLES_ROUTE}/{table['id']}/scene/reload", json={}, headers=CSRF
    )

    assert response.status_code == 200
    view = await body(response)
    assert view["round"] == 2
    assert view["turn"] is None
    assert [item["label"] for item in view["participants"]] == ["Ana", "Bob"]
    assert all(item["acted"] is False for item in view["participants"])


async def test_the_player_cutout_redacts_the_hidden_turn(client, world):
    await sign_in(client, NARRATOR)
    await image_scene(client, world, fog_outside=False)
    _, table = await open_table(client)
    goblin = await add_token(
        client,
        table["id"],
        label="Goblin",
        character_id="chr_goblin",
        owner_id=None,
        x=0,
        y=0,
    )
    await turn(client, table["id"], "open", goblin["id"])
    await world.database.execute(
        "UPDATE tokens SET visible = 0 WHERE id = ?", (goblin["id"],)
    )
    await player_access(client, world)

    cut = await summary(client, table["id"])

    assert cut["turn"] is not None
    assert cut["turn"]["token_id"] is None
    assert cut["turn"]["label"] == ""
    assert cut["turn"]["character_id"] is None
    assert cut["turn"]["owner_id"] is None
    await sign_in(client, NARRATOR)
    full = await summary(client, table["id"])
    assert full["turn"]["token_id"] == goblin["id"]
    assert full["turn"]["label"] == "Goblin"
    assert full["turn"]["character_id"] == "chr_goblin"


async def test_a_stale_tab_cannot_move_the_turn(client, world):
    table = await public_scene(client, world)
    ana = await add_token(client, table["id"], label="Ana", x=0, y=0)
    bob = await add_token(client, table["id"], label="Bob", x=5, y=5)
    cid = await add_token(client, table["id"], label="Cid", x=8, y=8)
    _, opened = await turn(client, table["id"], "open", ana["id"])
    stale = opened["turn"]["id"]
    passed, payload = await turn(
        client, table["id"], "pass", bob["id"], expected=stale
    )
    assert passed.status_code == 200, payload

    stale_pass, rejected = await turn(
        client, table["id"], "pass", cid["id"], expected=stale
    )
    stale_end, ended = await turn(client, table["id"], "end", expected=stale)
    view = await summary(client, table["id"])

    assert stale_pass.status_code == 409
    assert rejected["error"]["code"] == "turn_stale"
    assert stale_end.status_code == 409
    assert ended["error"]["code"] == "turn_stale"
    assert view["turn"]["token_id"] == bob["id"]


async def test_a_token_from_another_scene_cannot_take_the_turn(client, world):
    table = await public_scene(client, world)
    await create_scene(
        client,
        name="Calabouço",
        source="sketch",
        image_width=800,
        image_height=600,
        zones=[zone("Cela", "zon_cela")],
    )
    await client.post(
        f"{TABLES_ROUTE}/{table['id']}/scene",
        json={"scene": "calabouco"},
        headers=CSRF,
    )
    goblin = await add_token(client, table["id"], label="Goblin", x=0, y=0)
    await client.post(
        f"{TABLES_ROUTE}/{table['id']}/scene",
        json={"scene": "cripta"},
        headers=CSRF,
    )

    response, payload = await turn(client, table["id"], "open", goblin["id"])

    assert response.status_code == 404
    assert payload["error"]["code"] == "not_found"


async def test_concurrent_open_turns_leave_only_one_open(client, world):
    table = await public_scene(client, world)
    ana = await add_token(client, table["id"], label="Ana", x=0, y=0)
    bob = await add_token(client, table["id"], label="Bob", x=5, y=5)
    row = await table_domain.table_row(world.database, table["id"])
    assert row is not None

    results = await asyncio.gather(
        table_domain.open_turn(
            world.database, row, token_id=ana["id"], actor_id=NARRATOR
        ),
        table_domain.open_turn(
            world.database, row, token_id=bob["id"], actor_id=NARRATOR
        ),
        return_exceptions=True,
    )

    failures = [item for item in results if isinstance(item, Exception)]
    assert len(failures) == 1
    assert isinstance(failures[0], table_domain.TurnAlreadyOpen)
    rows = await world.database.fetchall(
        "SELECT id FROM turns WHERE table_id = ? AND ended_at IS NULL",
        (table["id"],),
    )
    assert len(rows) == 1


async def insert_turn(
    database: Database,
    table_id: str,
    scene_id: str,
    turn_id: str,
    token_id: str,
    ended_at: int | None,
) -> None:
    await database.execute(
        "INSERT INTO turns ("
        "id, table_id, scene_id, round, token_id, label, started_at, "
        "ended_at, started_by"
        ") VALUES (?, ?, ?, 1, ?, 'X', 1, ?, ?)",
        (turn_id, table_id, scene_id, token_id, ended_at, NARRATOR),
    )


async def test_the_turn_indexes_refuse_two_open_and_two_per_token_round(
    client, world
):
    table = await public_scene(client, world)
    ana = await add_token(client, table["id"], label="Ana", x=0, y=0)
    bob = await add_token(client, table["id"], label="Bob", x=5, y=5)
    scene_id = table["scene"]["id"]
    await insert_turn(
        world.database, table["id"], scene_id, "trn_index_a", ana["id"], None
    )

    with pytest.raises(IntegrityError):
        await insert_turn(
            world.database,
            table["id"],
            scene_id,
            "trn_index_b",
            bob["id"],
            None,
        )
    await world.database.execute(
        "UPDATE turns SET ended_at = 2 WHERE id = 'trn_index_a'"
    )
    with pytest.raises(IntegrityError):
        await insert_turn(
            world.database,
            table["id"],
            scene_id,
            "trn_index_c",
            ana["id"],
            2,
        )
