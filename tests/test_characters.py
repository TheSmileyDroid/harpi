from __future__ import annotations

import json
import os
from collections.abc import Iterable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import app as app_module
from app import app as quart_app
from app import configure_panel_session
from src.config import Settings
from src.panel import login, state, vault, vault_index
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
OTHER = "777"
SLUG = "paratheos"
CAMPAIGN = f"Harpi/Campaigns/{SLUG}"
CAST_ROUTE = f"/api/campaigns/{SLUG}/characters"


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


@pytest.fixture
def built(tmp_path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "index.html").write_text("<!doctype html><title>Harpi</title>")
    monkeypatch.setattr(app_module, "WEB_BUILD", tmp_path)
    return tmp_path


def write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def character(
    *,
    identifier: str,
    status: str = "ativo",
    image: str | None = None,
    body: str = "",
) -> str:
    extra = "" if image is None else f'imagem: "[[{image}]]"\n'
    return (
        "---\n"
        "tipo: personagem\n"
        f"harpi-id: {identifier}\n"
        "harpi-campanha: paratheos\n"
        f"harpi-status: {status}\n"
        f"{extra}"
        "---\n"
        f"{body}"
    )


def sheet(
    *,
    identifier: str,
    character_id: str,
    status: str = "ativo",
    owner: str = PLAYER,
) -> str:
    return (
        "---\n"
        "tipo: ficha\n"
        f"harpi-id: {identifier}\n"
        "harpi-campanha: paratheos\n"
        f"harpi-character-id: {character_id}\n"
        f"harpi-owner: {owner}\n"
        f"harpi-status: {status}\n"
        "---\n"
    )


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


async def add_player(database: Database, user_id: str) -> None:
    await add_member(database, user_id)
    await database.execute(
        "INSERT INTO sheet_files ("
        "path, harpi_id, campaign, rev, hash, last_text, base_json, "
        "status, owner_id, state, updated_at"
        ") VALUES (?, 'sht_x', ?, 1, 'h', 'text', '{}', 'ativo', ?, 'ok', 1)",
        (f"{CAMPAIGN}/sheets/Role.md", SLUG, user_id),
    )


def seed_cast(world: SimpleNamespace) -> None:
    write(
        world.root,
        f"{CAMPAIGN}/characters/Ana.md",
        character(
            identifier="chr_ana",
            image="Arte/ana.png",
            body="- **Conceito:** Piloto de carga\n\nMensageira sem memória.\n",
        ),
    )
    write(
        world.root,
        f"{CAMPAIGN}/sheets/Ana.md",
        sheet(identifier="sht_ana", character_id="chr_ana"),
    )
    write(
        world.root,
        f"{CAMPAIGN}/characters/Bob.md",
        character(identifier="chr_bob", status="pendente", body="Aprendiz.\n"),
    )
    write(
        world.root,
        f"{CAMPAIGN}/sheets/Bob.md",
        sheet(
            identifier="sht_bob",
            character_id="chr_bob",
            status="pendente",
            owner=OTHER,
        ),
    )
    write(
        world.root,
        f"{CAMPAIGN}/characters/Cid.md",
        character(identifier="chr_cid", body="Figura futura.\n"),
    )
    write(
        world.root,
        f"{CAMPAIGN}/characters/Dora.md",
        character(identifier="chr_dora", body="Guardiã do selo.\n"),
    )
    write(
        world.root,
        f"{CAMPAIGN}/characters/Eva.md",
        character(identifier="chr_eva", status="arquivado"),
    )
    write(
        world.root,
        f"{CAMPAIGN}/sheets/Eva.md",
        sheet(
            identifier="sht_eva",
            character_id="chr_eva",
            status="arquivado",
        ),
    )
    (world.root / "Arte").mkdir()
    (world.root / "Arte" / "ana.png").write_bytes(b"portrait-bytes")
    vault_index.configure(VaultIndex(world.root))


async def reveal(database: Database, character_id: str) -> None:
    await database.execute(
        "INSERT INTO character_visibility "
        "(campaign_slug, character_id, revealed_at, revealed_by) "
        "VALUES (?, ?, 1700000000, ?)",
        (SLUG, character_id, NARRATOR),
    )


async def body(response) -> dict[str, Any]:
    return json.loads(await response.get_data())


def names(payload: dict[str, Any]) -> list[str]:
    return [card["name"] for card in payload["characters"]]


async def test_an_anonymous_call_is_unauthorized(client, world):
    response = await client.get(CAST_ROUTE)

    assert response.status_code == 401


async def test_the_narrator_sees_every_character_but_the_archived(
    client, world
):
    seed_cast(world)
    await reveal(world.database, "chr_dora")
    await sign_in(client, NARRATOR)

    response = await client.get(CAST_ROUTE)

    assert response.status_code == 200
    assert names(await body(response)) == ["Ana", "Bob", "Cid", "Dora"]


async def test_a_player_sees_active_pcs_and_revealed_npcs(client, world):
    seed_cast(world)
    await reveal(world.database, "chr_dora")
    await add_player(world.database, PLAYER)
    await sign_in(client, PLAYER)

    response = await client.get(CAST_ROUTE)
    raw = await response.get_data()

    assert response.status_code == 200
    assert names(json.loads(raw)) == ["Ana", "Dora"]
    assert b"Bob" not in raw
    assert b"Cid" not in raw


async def test_a_pending_character_of_another_player_never_shows(
    client, world
):
    seed_cast(world)
    await add_player(world.database, PLAYER)
    await sign_in(client, PLAYER)

    response = await client.get(CAST_ROUTE)

    assert "Bob" not in names(await body(response))


async def test_the_owner_sees_the_own_pending_character(client, world):
    seed_cast(world)
    await add_member(world.database, OTHER)
    await sign_in(client, OTHER)

    response = await client.get(CAST_ROUTE)
    payload = await body(response)

    assert response.status_code == 200
    assert "Bob" in names(payload)
    assert "Cid" not in names(payload)


async def test_revealing_an_npc_adds_it_to_the_player_cast(client, world):
    seed_cast(world)
    await add_player(world.database, PLAYER)
    await sign_in(client, PLAYER)
    await reveal(world.database, "chr_cid")

    response = await client.get(CAST_ROUTE)

    assert names(await body(response)) == ["Ana", "Cid"]


async def test_a_spectator_gets_a_404(client, world):
    seed_cast(world)
    await sign_in(client, "999")

    response = await client.get(CAST_ROUTE)

    assert response.status_code == 404
    assert (await body(response))["error"]["code"] == "not_found"


async def test_another_guild_gets_a_404(client, world):
    seed_cast(world)
    await sign_in(client, NARRATOR, {OTHER_GUILD})

    response = await client.get(CAST_ROUTE)

    assert response.status_code == 404


async def test_without_a_vault_the_cast_answers_503(client, world):
    vault.configure(vault.Vault())
    await sign_in(client, NARRATOR)

    response = await client.get(CAST_ROUTE)

    assert response.status_code == 503
    assert (await body(response))["error"]["code"] == "vault_unavailable"


async def test_the_card_carries_no_mechanical_field(client, world):
    seed_cast(world)
    await reveal(world.database, "chr_dora")
    await sign_in(client, NARRATOR)

    response = await client.get(CAST_ROUTE)
    card = (await body(response))["characters"][0]

    assert set(card) == {
        "id",
        "name",
        "concept",
        "summary",
        "portrait",
    }
    assert card == {
        "id": "chr_ana",
        "name": "Ana",
        "concept": "Piloto de carga",
        "summary": "Mensageira sem memória.",
        "portrait": f"{CAST_ROUTE}/chr_ana/portrait",
    }


async def test_a_character_without_a_portrait_has_a_null_portrait_url(
    client,
    world,
):
    seed_cast(world)
    await reveal(world.database, "chr_dora")
    await sign_in(client, NARRATOR)

    response = await client.get(CAST_ROUTE)
    cards = (await body(response))["characters"]

    dora = next(card for card in cards if card["name"] == "Dora")
    assert dora["portrait"] is None


async def test_reading_the_cast_lists_no_directory(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    seed_cast(world)
    await sign_in(client, NARRATOR)

    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("the request listed a directory")

    monkeypatch.setattr(os, "walk", refuse)
    response = await client.get(CAST_ROUTE)

    assert response.status_code == 200


async def test_the_portrait_is_served_with_private_cache_headers(
    client, world
):
    seed_cast(world)
    await sign_in(client, NARRATOR)

    response = await client.get(f"{CAST_ROUTE}/chr_ana/portrait")

    assert response.status_code == 200
    assert await response.get_data() == b"portrait-bytes"
    assert response.headers["Content-Type"] == "image/png"
    assert (
        response.headers["Cache-Control"]
        == "private, max-age=60, must-revalidate"
    )
    assert response.headers["ETag"]
    assert response.headers["Last-Modified"]


async def test_a_matching_etag_answers_304(client, world):
    seed_cast(world)
    await sign_in(client, NARRATOR)
    first = await client.get(f"{CAST_ROUTE}/chr_ana/portrait")

    response = await client.get(
        f"{CAST_ROUTE}/chr_ana/portrait",
        headers={"If-None-Match": first.headers["ETag"]},
    )

    assert response.status_code == 304
    assert await response.get_data() == b""
    assert (
        response.headers["Cache-Control"]
        == "private, max-age=60, must-revalidate"
    )


async def test_a_changed_portrait_misses_the_etag(client, world):
    seed_cast(world)
    await sign_in(client, NARRATOR)
    first = await client.get(f"{CAST_ROUTE}/chr_ana/portrait")
    (world.root / "Arte" / "ana.png").write_bytes(b"other-bytes")

    response = await client.get(
        f"{CAST_ROUTE}/chr_ana/portrait",
        headers={"If-None-Match": first.headers["ETag"]},
    )

    assert response.status_code == 200
    assert await response.get_data() == b"other-bytes"


async def test_a_hidden_character_portrait_is_a_404(client, world):
    seed_cast(world)
    await add_player(world.database, PLAYER)
    await sign_in(client, PLAYER)

    response = await client.get(f"{CAST_ROUTE}/chr_bob/portrait")

    assert response.status_code == 404


async def test_a_hidden_portrait_answers_like_a_missing_one(client, world):
    seed_cast(world)
    await add_player(world.database, PLAYER)
    await sign_in(client, PLAYER)

    hidden = await client.get(f"{CAST_ROUTE}/chr_bob/portrait")
    missing = await client.get(f"{CAST_ROUTE}/chr_nobody/portrait")

    assert hidden.status_code == missing.status_code == 404
    assert await hidden.get_data() == await missing.get_data()


async def test_an_unknown_portrait_is_a_404(client, world):
    seed_cast(world)
    await sign_in(client, NARRATOR)

    response = await client.get(f"{CAST_ROUTE}/chr_nobody/portrait")

    assert response.status_code == 404
    payload = await body(response)
    assert payload["error"] == {"code": "not_found", "message": "Not found"}


async def test_an_unbuilt_index_answers_503(client, world):
    seed_cast(world)
    vault_index.configure(vault_index.VaultIndex())
    await sign_in(client, NARRATOR)

    response = await client.get(CAST_ROUTE)

    assert response.status_code == 503
    assert (await body(response))["error"]["code"] == "vault_unavailable"


async def test_a_portrait_outside_the_allowlist_is_a_404(client, world):
    write(
        world.root,
        f"{CAMPAIGN}/characters/Ana.md",
        character(identifier="chr_ana", image="Arte/ana.svg"),
    )
    (world.root / "Arte").mkdir()
    (world.root / "Arte" / "ana.svg").write_text("<svg/>", encoding="utf-8")
    vault_index.configure(VaultIndex(world.root))
    await sign_in(client, NARRATOR)

    response = await client.get(f"{CAST_ROUTE}/chr_ana/portrait")

    assert response.status_code == 404


async def test_a_portrait_path_escape_is_a_404(client, world):
    write(
        world.root,
        f"{CAMPAIGN}/characters/Ana.md",
        character(identifier="chr_ana", image="../outside.png"),
    )
    (world.root.parent / "outside.png").write_bytes(b"secret")
    vault_index.configure(VaultIndex(world.root))
    await sign_in(client, NARRATOR)

    response = await client.get(f"{CAST_ROUTE}/chr_ana/portrait")

    assert response.status_code == 404


async def test_a_missing_portrait_file_is_a_404(client, world):
    write(
        world.root,
        f"{CAMPAIGN}/characters/Ana.md",
        character(identifier="chr_ana", image="Arte/ana.png"),
    )
    vault_index.configure(VaultIndex(world.root))
    await sign_in(client, NARRATOR)

    response = await client.get(f"{CAST_ROUTE}/chr_ana/portrait")

    assert response.status_code == 404
    assert b"missing" not in await response.get_data()


async def test_an_oversized_portrait_is_a_404(client, world):
    seed_cast(world)
    oversized = world.root / "Arte" / "ana.png"
    with oversized.open("wb") as handle:
        handle.truncate(16 * 1024 * 1024 + 1)
    vault_index.configure(VaultIndex(world.root))
    await sign_in(client, NARRATOR)

    response = await client.get(f"{CAST_ROUTE}/chr_ana/portrait")
    cards = await body(await client.get(CAST_ROUTE))

    assert response.status_code == 404
    assert cards["characters"][0]["portrait"] is None


@pytest.mark.usefixtures("built")
async def test_the_personagens_page_serves_the_shell_to_a_member(
    client,
    world,
):
    await add_player(world.database, PLAYER)
    await sign_in(client, PLAYER)

    response = await client.get(f"/c/{SLUG}/personagens")

    assert response.status_code == 200
    assert b"Harpi" in await response.get_data()


@pytest.mark.usefixtures("built")
async def test_the_personagens_page_serves_the_shell_to_the_narrator(
    client,
    world,
):
    await sign_in(client, NARRATOR)

    response = await client.get(f"/c/{SLUG}/personagens")

    assert response.status_code == 200
    assert b"Harpi" in await response.get_data()


@pytest.mark.usefixtures("built")
async def test_the_personagens_page_is_a_404_for_a_spectator(
    client,
    world,
):
    await sign_in(client, "999")

    response = await client.get(f"/c/{SLUG}/personagens")

    assert response.status_code == 404


@pytest.mark.usefixtures("built")
async def test_the_personagens_page_is_a_404_outside_the_guild(
    client,
    world,
):
    await sign_in(client, NARRATOR, {OTHER_GUILD})

    response = await client.get(f"/c/{SLUG}/personagens")

    assert response.status_code == 404


@pytest.mark.usefixtures("built")
async def test_an_anonymous_visitor_gets_the_shell(client, world):
    response = await client.get(f"/c/{SLUG}/personagens")

    assert response.status_code == 200
