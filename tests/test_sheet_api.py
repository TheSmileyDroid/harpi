from __future__ import annotations

import json
import os
from collections.abc import Iterable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

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
ROUTE = f"/api/campaigns/{SLUG}/characters"

CONFIG = """\
```harpi-campaign
name: Paratheos
system: fate
ladder:
  - {rank: 4, label: Ótimo}
  - {rank: 3, label: Bom}
  - {rank: 2, label: Razoável}
  - {rank: 1, label: Regular}
  - {rank: 0, label: Medíocre}
stress:
  - {track: Físico, boxes: [1, 2, 3]}
  - {track: Mental, boxes: [1, 2]}
consequences:
  - {severity: Leve, value: 2}
  - {severity: Moderada, value: 4}
  - {severity: Severa, value: 6}
refresh: 7
extras:
  - Noética
```
"""

BLOCK = """\
```harpi-sheet
refresh: 7
fate_points: 3
aspects:
  - {label: Conceito, text: "Piloto de carga"}
  - {label: Problema, text: "Sem memória"}
skills:
  - {name: Hackear, rank: 4}
  - {name: Atirar, rank: 3}
stunts:
  - {name: "Escudo", text: "Torna um objeto indestrutível.", refresh_cost: 1}
stress:
  - track: Físico
    boxes:
      - {value: 1, checked: false}
      - {value: 2, checked: true}
consequences:
  - {severity: Leve, value: 2, text: "Casco rachado"}
extras:
  - {kind: Noética, name: Constructo, text: "Corpo artificial.", cost: 0}
inventory:
  - {item: "[[Espada de Lancelot]]", qty: 1, note: "Relíquia"}
```
"""


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


def write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def character(
    *,
    identifier: str,
    status: str = "ativo",
    body: str = "Piloto de carga.\n",
) -> str:
    return (
        "---\n"
        "tipo: personagem\n"
        f"harpi-id: {identifier}\n"
        "harpi-campanha: paratheos\n"
        f"harpi-status: {status}\n"
        "---\n"
        f"{body}"
    )


def sheet(
    *,
    identifier: str,
    character_id: str,
    status: str = "ativo",
    owner: str = PLAYER,
    block: str = BLOCK,
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
        "\n## História\n\nUma piloto.\n\n"
        f"{block}"
    )


def seed(world: SimpleNamespace) -> None:
    write(world.root, f"{CAMPAIGN}/config.md", CONFIG)
    write(
        world.root,
        f"{CAMPAIGN}/characters/Ana.md",
        character(identifier="chr_ana"),
    )
    write(
        world.root,
        f"{CAMPAIGN}/sheets/Ana.md",
        sheet(identifier="sht_ana", character_id="chr_ana"),
    )
    write(
        world.root,
        f"{CAMPAIGN}/characters/Bob.md",
        character(identifier="chr_bob", status="pendente"),
    )
    write(
        world.root,
        f"{CAMPAIGN}/sheets/Bob.md",
        sheet(
            identifier="sht_bob",
            character_id="chr_bob",
            status="pendente",
            owner=OTHER,
            block="```harpi-sheet\nrefresh: 3\n```\n",
        ),
    )
    write(
        world.root,
        f"{CAMPAIGN}/characters/Cid.md",
        character(identifier="chr_cid"),
    )
    write(
        world.root,
        f"{CAMPAIGN}/sheets/Cid.md",
        sheet(
            identifier="sht_cid",
            character_id="chr_cid",
            owner=OTHER,
            block="```harpi-sheet\nrefresh: 4\n```\n",
        ),
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
            block="```harpi-sheet\nrefresh: 2\n```\n",
        ),
    )
    write(
        world.root,
        f"{CAMPAIGN}/characters/Broken.md",
        character(identifier="chr_broken"),
    )
    write(
        world.root,
        f"{CAMPAIGN}/sheets/Broken.md",
        sheet(
            identifier="sht_broken",
            character_id="chr_broken",
            block="```harpi-sheet\nrefresh: [3\n```\n",
        ),
    )
    vault_index.configure(VaultIndex(world.root))


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
        ") VALUES (?, ?, ?, 1, 'h', 'text', '{}', 'ativo', ?, 'ok', 1)",
        (f"{CAMPAIGN}/sheets/Player.md", "sht_player", SLUG, user_id),
    )


async def body(response) -> dict[str, Any]:
    return json.loads(await response.get_data())


async def test_an_anonymous_call_is_unauthorized(client, world):
    seed(world)

    response = await client.get(f"{ROUTE}/chr_ana")

    assert response.status_code == 401


async def test_the_narrator_reads_the_whole_sheet(client, world):
    seed(world)
    await sign_in(client, NARRATOR)

    response = await client.get(f"{ROUTE}/chr_ana")
    payload = await body(response)

    assert response.status_code == 200
    assert payload["kind"] == "sheet"
    sheet = payload["sheet"]
    assert sheet["id"] == "sht_ana"
    assert sheet["character_id"] == "chr_ana"
    assert sheet["status"] == "active"
    assert sheet["state"] == "ok"
    assert sheet["read_only"] is False
    assert sheet["error"] is None
    assert sheet["refresh"] == 7
    assert sheet["fate_points"] == 3
    assert sheet["aspects"] == [
        {"label": "Conceito", "text": "Piloto de carga"},
        {"label": "Problema", "text": "Sem memória"},
    ]
    assert sheet["skills"] == [
        {"name": "Hackear", "rank": 4, "label": "Ótimo"},
        {"name": "Atirar", "rank": 3, "label": "Bom"},
    ]
    assert sheet["stunts"] == [
        {
            "name": "Escudo",
            "text": "Torna um objeto indestrutível.",
            "refresh_cost": 1,
        }
    ]
    assert sheet["stress"] == [
        {
            "track": "Físico",
            "boxes": [
                {"value": 1, "checked": False},
                {"value": 2, "checked": True},
            ],
        },
        {
            "track": "Mental",
            "boxes": [
                {"value": 1, "checked": False},
                {"value": 2, "checked": False},
            ],
        },
    ]
    assert sheet["consequences"] == [
        {"severity": "Leve", "value": 2, "text": "Casco rachado"},
        {"severity": "Moderada", "value": 4, "text": ""},
        {"severity": "Severa", "value": 6, "text": ""},
    ]
    assert sheet["extras"] == [
        {
            "kind": "Noética",
            "name": "Constructo",
            "text": "Corpo artificial.",
            "cost": 0,
        }
    ]
    assert sheet["inventory"] == [
        {"item": "[[Espada de Lancelot]]", "qty": 1, "note": "Relíquia"}
    ]
    assert sheet["ladder"][0] == {"rank": 4, "label": "Ótimo"}


async def test_the_owner_reads_the_own_sheet(client, world):
    seed(world)
    await add_player(world.database, PLAYER)
    await sign_in(client, PLAYER)

    payload = await body(await client.get(f"{ROUTE}/chr_ana"))

    assert payload["kind"] == "sheet"
    assert payload["sheet"]["owner"] == PLAYER


async def test_a_pending_owner_reads_the_own_sheet(client, world):
    seed(world)
    await add_member(world.database, OTHER)
    await sign_in(client, OTHER)

    payload = await body(await client.get(f"{ROUTE}/chr_bob"))

    assert payload["kind"] == "sheet"
    assert payload["sheet"]["status"] == "pending"
    assert payload["sheet"]["read_only"] is False


async def test_another_player_receives_only_the_public_card(client, world):
    seed(world)
    await add_player(world.database, PLAYER)
    await sign_in(client, PLAYER)
    raw = await (await client.get(f"{ROUTE}/chr_cid")).get_data()

    assert b'"refresh"' not in raw
    payload = json.loads(raw)
    assert payload["kind"] == "card"
    assert payload["sheet"] is None
    assert payload["card"]["name"] == "Cid"
    assert set(payload["card"]) == {
        "id",
        "name",
        "concept",
        "summary",
        "portrait",
    }


async def test_an_archived_sheet_is_read_only_for_its_owner(client, world):
    seed(world)
    await add_player(world.database, PLAYER)
    await sign_in(client, PLAYER)

    payload = await body(await client.get(f"{ROUTE}/chr_eva"))

    assert payload["kind"] == "sheet"
    assert payload["sheet"]["status"] == "archived"
    assert payload["sheet"]["read_only"] is True


async def test_an_archived_character_is_hidden_from_other_players(
    client, world
):
    seed(world)
    await add_player(world.database, OTHER)
    await sign_in(client, OTHER)

    response = await client.get(f"{ROUTE}/chr_eva")

    assert response.status_code == 404


async def test_a_pending_sheet_of_another_player_is_hidden(client, world):
    seed(world)
    await add_player(world.database, PLAYER)
    await sign_in(client, PLAYER)

    response = await client.get(f"{ROUTE}/chr_bob")

    assert response.status_code == 404


async def test_a_spectator_gets_a_404(client, world):
    seed(world)
    await sign_in(client, "999")

    response = await client.get(f"{ROUTE}/chr_ana")

    assert response.status_code == 404
    assert (await body(response))["error"]["code"] == "not_found"


async def test_without_a_vault_the_sheet_answers_503(client, world):
    seed(world)
    vault.configure(vault.Vault())
    await sign_in(client, NARRATOR)

    response = await client.get(f"{ROUTE}/chr_ana")

    assert response.status_code == 503


async def test_broken_yaml_turns_the_sheet_read_only_with_a_visible_error(
    client, world
):
    seed(world)
    await sign_in(client, NARRATOR)

    payload = await body(await client.get(f"{ROUTE}/chr_broken"))

    assert payload["sheet"]["state"] == "invalid"
    assert payload["sheet"]["read_only"] is True
    assert payload["sheet"]["error"]
    assert payload["sheet"]["aspects"] == []
    assert payload["sheet"]["skills"] == []


async def test_reading_a_broken_sheet_never_rewrites_the_file(client, world):
    seed(world)
    await sign_in(client, NARRATOR)
    path = world.root / f"{CAMPAIGN}/sheets/Broken.md"
    before = path.read_bytes()

    await client.get(f"{ROUTE}/chr_broken")

    assert path.read_bytes() == before


async def test_the_campaign_config_labels_the_sheet(client, world):
    seed(world)
    write(
        world.root,
        f"{CAMPAIGN}/config.md",
        CONFIG.replace(
            "{rank: 4, label: Ótimo}", "{rank: 4, label: Lendário}"
        ),
    )
    vault_index.configure(VaultIndex(world.root))
    await sign_in(client, NARRATOR)

    payload = await body(await client.get(f"{ROUTE}/chr_ana"))

    assert payload["sheet"]["skills"][0]["label"] == "Lendário"


async def test_a_broken_config_does_not_lock_the_sheet(client, world):
    seed(world)
    write(
        world.root,
        f"{CAMPAIGN}/config.md",
        "```harpi-campaign\nname: [Paratheos\n```\n",
    )
    vault_index.configure(VaultIndex(world.root))
    await sign_in(client, NARRATOR)

    payload = await body(await client.get(f"{ROUTE}/chr_ana"))
    campaign = await body(await client.get(f"/api/campaigns/{SLUG}"))

    assert payload["sheet"]["state"] == "ok"
    assert payload["sheet"]["read_only"] is False
    assert campaign["config_error"]


async def test_the_sheet_falls_back_to_the_fate_ladder_without_config(
    client, world
):
    seed(world)
    (world.root / f"{CAMPAIGN}/config.md").unlink()
    vault_index.configure(VaultIndex(world.root))
    await sign_in(client, NARRATOR)

    payload = await body(await client.get(f"{ROUTE}/chr_ana"))

    assert payload["sheet"]["state"] == "ok"
    assert payload["sheet"]["skills"][0]["label"] == "Ótimo"


async def test_reading_the_sheet_lists_no_directory(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    seed(world)
    await sign_in(client, NARRATOR)

    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("the request listed a directory")

    monkeypatch.setattr(os, "walk", refuse)
    response = await client.get(f"{ROUTE}/chr_ana")

    assert response.status_code == 200


async def test_an_unknown_character_is_a_404(client, world):
    seed(world)
    await sign_in(client, NARRATOR)

    response = await client.get(f"{ROUTE}/chr_missing")

    assert response.status_code == 404
    assert (await body(response))["error"]["code"] == "not_found"
