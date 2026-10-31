from __future__ import annotations

import json
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
NARRATOR = "100"
PLAYER = "555"
OTHER = "777"
SLUG = "paratheos"
CAMPAIGN = f"Harpi/Campaigns/{SLUG}"
SHEET = f"{CAMPAIGN}/sheets/Ana.md"
ROUTE = f"/api/campaigns/{SLUG}/sheets/sht_ana"
HEADERS = {
    "Content-Type": "application/json",
    "Sec-Fetch-Site": "same-origin",
}

CONFIG = """\
```harpi-campaign
name: Paratheos
system: fate
ladder:
  - {rank: 4, label: Ótimo}
  - {rank: 3, label: Bom}
stress:
  - {track: Físico, boxes: [1, 2, 3]}
  - {track: Mental, boxes: [1, 2]}
consequences:
  - {severity: Leve, value: 2}
  - {severity: Moderada, value: 4}
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
stress:
  - track: Físico
    boxes:
      - {value: 1, checked: false}
      - {value: 2, checked: false}
consequences:
  - {severity: Leve, value: 2, text: ""}
extras: []
inventory:
  - {item: "[[Espada de Lancelot]]", qty: 1, note: "Relíquia"}
house_rule: vento forte
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


def sheet_text(status: str = "ativo") -> str:
    return (
        "---\n"
        "tipo: ficha\n"
        "harpi-id: sht_ana\n"
        "harpi-campanha: paratheos\n"
        "harpi-character-id: chr_ana\n"
        f"harpi-owner: {PLAYER}\n"
        f"harpi-status: {status}\n"
        "harpi-rev: 1\n"
        "aliases: []\n"
        "nota-livre: fica\n"
        "---\n"
        "\n"
        "Abertura intacta.\n"
        "\n"
        "## História\n"
        "\n"
        "Uma piloto.\n"
        "\n"
        f"{BLOCK}"
        "\n"
        "## Anotações\n"
        "\n"
        "Fim.\n"
    )


def seed(world: SimpleNamespace, status: str = "ativo") -> None:
    write(world.root, f"{CAMPAIGN}/config.md", CONFIG)
    write(
        world.root,
        f"{CAMPAIGN}/characters/Ana.md",
        "---\ntipo: personagem\nharpi-id: chr_ana\n"
        "harpi-campanha: paratheos\nharpi-status: ativo\n---\n"
        "Piloto de carga.\n",
    )
    write(world.root, SHEET, sheet_text(status))
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
        ") VALUES (?, 'sht_ana', ?, 1, 'h', 'text', '{}', 'ativo', ?, "
        "'ok', 1)",
        (SHEET, SLUG, user_id),
    )


async def body(response) -> dict[str, Any]:
    return json.loads(await response.get_data())


async def read_sheet(client) -> dict[str, Any]:
    payload = await body(
        await client.get(f"/api/campaigns/{SLUG}/characters/chr_ana")
    )
    return payload["sheet"]


async def send_patch(client, **changes: Any):
    return await client.patch(ROUTE, json=changes, headers=HEADERS)


async def test_the_read_exposes_the_hash_revision_and_prose(client, world):
    seed(world)
    await sign_in(client, NARRATOR)

    sheet = await read_sheet(client)

    assert len(sheet["hash"]) == 64
    assert sheet["rev"] == 1
    assert sheet["history"] == "Uma piloto."
    assert sheet["notes"] == "Fim."
    assert sheet["warnings"] == []


async def test_marking_stress_writes_and_reloads_the_new_value(client, world):
    seed(world)
    await sign_in(client, NARRATOR)
    sheet = await read_sheet(client)

    response = await send_patch(
        client,
        base_hash=sheet["hash"],
        stress=[
            {
                "track": "Físico",
                "boxes": [
                    {"value": 1, "checked": True},
                    {"value": 2, "checked": False},
                ],
            }
        ],
    )
    payload = await body(response)
    fresh = await read_sheet(client)

    assert response.status_code == 200
    assert payload["stress"][0]["boxes"][0]["checked"] is True
    assert fresh["stress"][0]["boxes"][0]["checked"] is True
    assert fresh["rev"] == 2
    assert fresh["hash"] != sheet["hash"]


async def test_aspect_consequence_extra_and_inventory_reload(client, world):
    seed(world)
    await sign_in(client, NARRATOR)
    sheet = await read_sheet(client)

    response = await send_patch(
        client,
        base_hash=sheet["hash"],
        aspects=[{"label": "Conceito", "text": "Mensageira"}],
        consequences=[{"severity": "Leve", "text": "Casco rachado"}],
        extras=[
            {
                "kind": "Noética",
                "name": "Constructo",
                "text": "Corpo artificial.",
                "cost": 1,
            }
        ],
        inventory=[{"item": "[[Corda]]", "qty": 2, "note": "Nova"}],
    )
    fresh = await read_sheet(client)

    assert response.status_code == 200
    assert fresh["aspects"] == [{"label": "Conceito", "text": "Mensageira"}]
    assert fresh["consequences"] == [
        {"severity": "Leve", "value": 2, "text": "Casco rachado"},
        {"severity": "Moderada", "value": 4, "text": ""},
    ]
    assert fresh["extras"][0]["name"] == "Constructo"
    assert fresh["inventory"] == [
        {"item": "[[Corda]]", "qty": 2, "note": "Nova"}
    ]


async def test_the_prose_is_written_only_in_the_app_sections(client, world):
    seed(world)
    await sign_in(client, NARRATOR)
    sheet = await read_sheet(client)

    response = await send_patch(
        client,
        base_hash=sheet["hash"],
        history="História nova.  \n\nOutra linha.",
        notes="",
    )
    fresh = await read_sheet(client)
    text = (world.root / SHEET).read_text(encoding="utf-8")

    assert response.status_code == 200
    assert fresh["history"] == "História nova.\n\nOutra linha."
    assert fresh["notes"] == ""
    assert "Abertura intacta." in text
    assert "nota-livre: fica" in text
    assert "house_rule: vento forte" in text
    assert "Uma piloto." not in text
    assert "Fim." not in text


async def test_an_old_base_hash_is_a_409_without_touching_the_disk(
    client, world
):
    seed(world)
    await sign_in(client, NARRATOR)
    sheet = await read_sheet(client)
    path = world.root / SHEET
    path.write_text(sheet_text().replace("Uma piloto.", "Editada fora."))
    before = path.read_bytes()

    response = await send_patch(client, base_hash=sheet["hash"], fate_points=1)

    assert response.status_code == 409
    assert (await body(response))["error"]["code"] == "sheet_conflict"
    assert path.read_bytes() == before
    assert not (world.root.parent / "vault-backups").exists()


async def test_invalid_yaml_is_read_only_and_never_overwritten(client, world):
    seed(world)
    write(world.root, SHEET, sheet_text().replace("refresh: 7", "refresh: [7"))
    vault_index.configure(VaultIndex(world.root))
    await sign_in(client, NARRATOR)
    sheet = await read_sheet(client)
    before = (world.root / SHEET).read_bytes()

    response = await send_patch(client, base_hash=sheet["hash"], fate_points=1)

    assert sheet["state"] == "invalid"
    assert response.status_code == 422
    assert (await body(response))["error"]["code"] == "sheet_invalid"
    assert (world.root / SHEET).read_bytes() == before


async def test_another_player_is_forbidden_and_a_spectator_is_hidden(
    client, world
):
    seed(world)
    await add_member(world.database, OTHER)
    await sign_in(client, OTHER)

    response = await send_patch(client, base_hash="x", fate_points=1)
    await sign_in(client, "999")
    hidden = await send_patch(client, base_hash="x", fate_points=1)

    assert response.status_code == 403
    assert hidden.status_code == 404


async def test_an_archived_sheet_is_read_only_for_its_owner(client, world):
    seed(world, status="arquivado")
    await add_player(world.database, PLAYER)
    await sign_in(client, PLAYER)
    sheet = await read_sheet(client)

    response = await send_patch(client, base_hash=sheet["hash"], fate_points=1)

    assert sheet["read_only"] is True
    assert response.status_code == 403
    assert (await body(response))["error"]["code"] == "sheet_read_only"


async def test_a_player_cannot_unarchive_the_own_sheet(client, world):
    seed(world, status="arquivado")
    await add_player(world.database, PLAYER)
    await sign_in(client, PLAYER)
    sheet = await read_sheet(client)

    response = await send_patch(
        client, base_hash=sheet["hash"], status="active"
    )

    assert response.status_code == 403
    assert (await body(response))["error"]["code"] == "forbidden"


async def test_a_status_comment_keeps_the_sheet_archived(client, world):
    seed(world)
    path = world.root / SHEET
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "harpi-status: ativo", "harpi-status: arquivado   # congelada"
        ),
        encoding="utf-8",
    )
    vault_index.configure(VaultIndex(world.root))
    await sign_in(client, NARRATOR)
    sheet = await read_sheet(client)

    assert sheet["status"] == "archived"
    response = await send_patch(client, base_hash=sheet["hash"], fate_points=1)

    assert response.status_code == 403
    assert (await body(response))["error"]["code"] == "sheet_read_only"


async def test_a_database_failure_restores_the_previous_file(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    from src.panel import sheet_store

    seed(world)
    await sign_in(client, NARRATOR)
    sheet = await read_sheet(client)
    path = world.root / SHEET
    before = path.read_bytes()

    async def fail(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("database down")

    monkeypatch.setattr(sheet_store, "store_sheet", fail)
    response = await send_patch(client, base_hash=sheet["hash"], fate_points=1)

    assert response.status_code == 503
    assert (await body(response))["error"]["code"] == "storage_unavailable"
    assert path.read_bytes() == before


async def test_duplicate_prose_sections_are_a_visible_422(client, world):
    seed(world)
    path = world.root / SHEET
    path.write_text(
        path.read_text(encoding="utf-8") + "\n## História\n\nDuplicada.\n",
        encoding="utf-8",
    )
    vault_index.configure(VaultIndex(world.root))
    await sign_in(client, NARRATOR)
    sheet = await read_sheet(client)

    response = await send_patch(
        client, base_hash=sheet["hash"], history="Nova."
    )

    assert response.status_code == 422
    assert (await body(response))["error"]["code"] == "invalid_sheet"
    assert "duplicada" in (await body(response))["error"]["message"]


async def test_the_status_walks_the_legal_transitions(client, world):
    seed(world)
    await sign_in(client, NARRATOR)
    sheet = await read_sheet(client)

    archived = await send_patch(
        client, base_hash=sheet["hash"], status="archived"
    )
    archived_payload = await body(archived)
    after_archive = await read_sheet(client)

    assert archived.status_code == 200
    assert archived_payload["status"] == "archived"
    assert after_archive["read_only"] is True

    active = await send_patch(
        client, base_hash=after_archive["hash"], status="active"
    )
    after_active = await read_sheet(client)

    assert active.status_code == 200
    assert after_active["status"] == "active"
    assert after_active["read_only"] is False


async def test_a_hand_edited_owner_is_corrected_on_the_next_write(
    client, world
):
    seed(world)
    await sign_in(client, NARRATOR)
    sheet = await read_sheet(client)
    first = await send_patch(client, base_hash=sheet["hash"], fate_points=1)
    assert first.status_code == 200
    path = world.root / SHEET
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            f"harpi-owner: {PLAYER}", "harpi-owner: 999"
        )
    )
    vault_index.configure(VaultIndex(world.root))

    changed = await read_sheet(client)
    response = await send_patch(
        client, base_hash=changed["hash"], fate_points=2
    )
    payload = await body(response)

    assert response.status_code == 200
    assert payload["warnings"]
    assert f'harpi-owner: "{PLAYER}"' in path.read_text(encoding="utf-8")


async def test_a_hand_edited_owner_does_not_lock_out_the_real_owner(
    client, world
):
    from src.panel.sheets import sha256_text

    seed(world)
    await add_player(world.database, PLAYER)
    await sign_in(client, PLAYER)
    sheet = await read_sheet(client)
    first = await send_patch(client, base_hash=sheet["hash"], fate_points=1)
    assert first.status_code == 200
    path = world.root / SHEET
    edited = path.read_text(encoding="utf-8").replace(
        f"harpi-owner: {PLAYER}", "harpi-owner: 999"
    )
    path.write_text(edited, encoding="utf-8")

    response = await send_patch(
        client, base_hash=sha256_text(edited), fate_points=2
    )

    assert response.status_code == 200
    assert f'harpi-owner: "{PLAYER}"' in path.read_text(encoding="utf-8")


async def test_the_previous_version_is_backed_up(client, world):
    seed(world)
    await sign_in(client, NARRATOR)
    sheet = await read_sheet(client)

    await send_patch(client, base_hash=sheet["hash"], fate_points=1)

    backups = list(
        (world.root.parent / "vault-backups/paratheos/sht_ana").glob("*.md")
    )
    assert len(backups) == 1
    assert "Uma piloto." in backups[0].read_text(encoding="utf-8")


async def test_a_malformed_body_is_a_400(client, world):
    seed(world)
    await sign_in(client, NARRATOR)

    response = await client.patch(ROUTE, data="{", headers=HEADERS)

    assert response.status_code == 400


async def test_an_invalid_payload_is_a_422(client, world):
    seed(world)
    await sign_in(client, NARRATOR)

    response = await send_patch(client, fate_points=1)

    assert response.status_code == 422
    assert (await body(response))["error"]["code"] == "invalid_payload"


async def test_a_body_above_the_limit_is_a_413(client, world):
    seed(world)
    await sign_in(client, NARRATOR)
    sheet = await read_sheet(client)

    response = await send_patch(
        client, base_hash=sheet["hash"], history="x" * (64 * 1024)
    )

    assert response.status_code == 413
