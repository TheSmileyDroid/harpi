from __future__ import annotations

import asyncio
import json
import sqlite3
from collections.abc import Iterable
from types import SimpleNamespace
from typing import Any

import pytest

from app import app as quart_app
from app import configure_panel_session
from src.config import Settings
from src.panel import (
    enrollment,
    login,
    sheet_store,
    state,
    vault,
    vault_index,
)
from src.panel.vault_index import VaultIndex
from src.panel.sheets import sha256_text
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
CHARACTERS = f"/api/campaigns/{SLUG}/characters"
APPROVALS = f"/api/campaigns/{SLUG}/approvals"
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


@pytest.fixture
async def world(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SECRET_KEY", SECRET)
    configure_panel_session(Settings.from_env())
    quart_app.config["TESTING"] = True
    root = tmp_path / "vault"
    root.mkdir()
    (root / CAMPAIGN).mkdir(parents=True)
    (root / CAMPAIGN / "config.md").write_text(CONFIG, encoding="utf-8")
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


async def add_sheet(database: Database, user_id: str, status: str) -> None:
    await database.execute(
        "INSERT INTO sheet_files ("
        "path, harpi_id, campaign, rev, hash, last_text, base_json, "
        "status, owner_id, state, updated_at"
        ") VALUES (?, 'sht_other', ?, 1, 'h', 'text', '{}', ?, ?, 'ok', 1)",
        (f"{CAMPAIGN}/sheets/Other.md", SLUG, status, user_id),
    )


async def body(response) -> dict[str, Any]:
    return json.loads(await response.get_data())


async def create_pair(client, name: str = "Nina", **extra: Any):
    payload = {
        "name": name,
        "concept": "Mensageira",
        "summary": "Sem memória.",
        **extra,
    }
    return await client.post(CHARACTERS, json=payload, headers=HEADERS)


async def create_and_sign_in(
    client, user_id: str = PLAYER, name: str = "Nina"
) -> str:
    await sign_in(client, user_id)
    response = await create_pair(client, name=name)
    assert response.status_code == 200
    return (await body(response))["card"]["id"]


async def queue_ids(client) -> list[str]:
    response = await client.get(APPROVALS)
    assert response.status_code == 200
    return [item["id"] for item in (await body(response))["approvals"]]


def read(world: SimpleNamespace, relative: str) -> str:
    return (world.root / relative).read_text(encoding="utf-8")


async def test_a_player_creates_the_pair_pending_with_member_and_queue(
    client, world
):
    await sign_in(client, PLAYER)

    response = await create_pair(client)
    payload = await body(response)

    assert response.status_code == 200
    assert payload["kind"] == "sheet"
    assert payload["sheet"]["status"] == "pending"
    assert payload["sheet"]["owner"] == PLAYER
    assert payload["sheet"]["review_note"] is None
    assert payload["sheet"]["aspects"][0]["label"] == "Conceito"
    character = read(world, f"{CAMPAIGN}/characters/Nina.md")
    sheet = read(world, f"{CAMPAIGN}/sheets/Nina.md")
    assert "harpi-status: pendente" in character
    assert "harpi-rev: 1" in character
    assert "harpi-status: pendente" in sheet
    assert "harpi-rev: 1" in sheet
    assert payload["card"]["id"] in character
    row = await world.database.fetchone(
        "SELECT "
        "(SELECT COUNT(*) FROM members WHERE user_id = ?) AS members, "
        "(SELECT status FROM sheet_files WHERE campaign = ?) AS status, "
        "(SELECT COUNT(*) FROM approvals WHERE status = 'pending') AS queue",
        (PLAYER, SLUG),
    )
    assert row is not None
    assert (row["members"], row["status"], row["queue"]) == (1, "pendente", 1)


async def test_the_owner_sees_the_own_pending_card_and_character(
    client, world
):
    await sign_in(client, PLAYER)
    character_id = (await body(await create_pair(client)))["card"]["id"]

    listing = await client.get(CHARACTERS)
    detail = await client.get(f"{CHARACTERS}/{character_id}")

    assert (await body(listing))["own_character_id"] == character_id
    assert (await body(detail))["kind"] == "sheet"


async def test_another_player_sees_nothing_of_the_pending_pair(client, world):
    await sign_in(client, PLAYER)
    character_id = (await body(await create_pair(client)))["card"]["id"]
    await add_member(world.database, OTHER)
    await add_sheet(world.database, OTHER, "ativo")
    await sign_in(client, OTHER)

    listing = await client.get(CHARACTERS)
    detail = await client.get(f"{CHARACTERS}/{character_id}")

    assert "Nina" not in [
        card["name"] for card in (await body(listing))["characters"]
    ]
    assert detail.status_code == 404


async def test_the_narrator_reads_the_queue_with_the_owner(client, world):
    await create_and_sign_in(client)
    await sign_in(client, NARRATOR)

    payload = await body(await client.get(APPROVALS))

    assert payload["approvals"][0]["character_name"] == "Nina"
    assert payload["approvals"][0]["owner"] == PLAYER
    assert payload["approvals"][0]["owner_name"] == "panel-user"


async def test_a_second_creation_for_the_same_player_is_a_409(client, world):
    await create_and_sign_in(client)

    response = await create_pair(client, name="Outra")

    assert response.status_code == 409
    assert (await body(response))["error"]["code"] == "sheet_already_exists"
    assert not (world.root / CAMPAIGN / "characters" / "Outra.md").exists()


async def test_a_taken_name_gets_an_id_suffix_instead_of_a_409(client, world):
    await create_and_sign_in(client)
    await add_member(world.database, OTHER)
    await sign_in(client, OTHER)

    response = await create_pair(client)

    assert response.status_code == 200
    assert (await body(response))["card"]["name"] == "Nina"
    files = sorted(
        path.name
        for path in (world.root / CAMPAIGN / "characters").glob("Nina*.md")
    )
    assert "Nina.md" in files
    suffixed = next(name for name in files if name != "Nina.md")
    assert suffixed.startswith("Nina ")
    assert suffixed.removesuffix(".md").split(" ")[-1].isalnum()


async def test_a_blank_name_is_a_422(client, world):
    await sign_in(client, PLAYER)

    response = await create_pair(client, name="   ")

    assert response.status_code == 422
    assert (await body(response))["error"]["code"] == "invalid_payload"


async def test_a_spectator_outside_the_guild_is_a_404(client, world):
    await sign_in(client, PLAYER, {OTHER_GUILD})

    response = await create_pair(client)

    assert response.status_code == 404


async def test_without_a_vault_the_creation_is_a_503(client, world):
    await sign_in(client, PLAYER)
    vault.configure(vault.Vault())

    response = await create_pair(client)

    assert response.status_code == 503
    assert (await body(response))["error"]["code"] == "vault_unavailable"


async def test_a_storage_failure_discards_the_new_files(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    async def fail(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("database down")

    monkeypatch.setattr(enrollment, "_record_creation", fail)
    await sign_in(client, PLAYER)

    response = await create_pair(client)

    assert response.status_code == 503
    assert not (world.root / CAMPAIGN / "characters" / "Nina.md").exists()
    assert not (world.root / CAMPAIGN / "sheets" / "Nina.md").exists()


async def test_the_owner_edits_the_pending_sheet(client, world):
    await sign_in(client, PLAYER)
    payload = await body(await create_pair(client))
    sheet = payload["sheet"]

    response = await client.patch(
        f"/api/campaigns/{SLUG}/sheets/{sheet['id']}",
        json={"base_hash": sheet["hash"], "fate_points": 2},
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert (await body(response))["fate_points"] == 2


async def test_the_narrator_creates_an_active_npc_without_a_queue(
    client, world
):
    await sign_in(client, NARRATOR)

    response = await client.post(
        CHARACTERS,
        json={"name": "Cid", "concept": "Guardião"},
        headers=HEADERS,
    )
    payload = await body(response)

    assert response.status_code == 200
    assert payload["kind"] == "card"
    assert payload["sheet"] is None
    assert "harpi-status: ativo" in read(
        world, f"{CAMPAIGN}/characters/Cid.md"
    )
    assert not (world.root / CAMPAIGN / "sheets" / "Cid.md").exists()
    assert await queue_ids(client) == []


async def test_the_narrator_can_give_the_npc_a_sheet(client, world):
    await sign_in(client, NARRATOR)

    response = await client.post(
        CHARACTERS,
        json={"name": "Cid", "sheet": True},
        headers=HEADERS,
    )
    payload = await body(response)

    assert response.status_code == 200
    assert payload["sheet"]["status"] == "active"
    assert "harpi-status: ativo" in read(world, f"{CAMPAIGN}/sheets/Cid.md")
    assert await queue_ids(client) == []


async def test_only_the_narrator_reads_the_queue(client, world):
    await create_and_sign_in(client)

    player = await client.get(APPROVALS)
    await sign_in(client, "999")
    spectator = await client.get(APPROVALS)

    assert player.status_code == 403
    assert spectator.status_code == 404


async def test_a_player_cannot_skip_the_sheet(client, world):
    await sign_in(client, PLAYER)

    response = await create_pair(client, sheet=False)

    assert response.status_code == 422
    assert (await body(response))["error"]["code"] == "invalid_payload"


async def test_a_player_cannot_decide_an_approval(client, world):
    await create_and_sign_in(client)
    await sign_in(client, NARRATOR)
    approval_id = (await queue_ids(client))[0]
    await sign_in(client, PLAYER)

    response = await client.post(
        f"{APPROVALS}/{approval_id}",
        json={"decision": "approve"},
        headers=HEADERS,
    )

    assert response.status_code == 403


async def test_an_unknown_approval_is_a_404(client, world):
    await sign_in(client, NARRATOR)

    response = await client.post(
        f"{APPROVALS}/apr_missing",
        json={"decision": "approve"},
        headers=HEADERS,
    )

    assert response.status_code == 404


async def test_approval_writes_both_files_and_then_closes_the_row(
    client, world
):
    await create_and_sign_in(client)
    await sign_in(client, NARRATOR)
    approval_id = (await queue_ids(client))[0]

    response = await client.post(
        f"{APPROVALS}/{approval_id}",
        json={"decision": "approve"},
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert (await body(response))["approvals"] == []
    assert "harpi-status: ativo" in read(
        world, f"{CAMPAIGN}/characters/Nina.md"
    )
    assert "harpi-status: ativo" in read(world, f"{CAMPAIGN}/sheets/Nina.md")
    assert "harpi-rev: 2" in read(world, f"{CAMPAIGN}/characters/Nina.md")
    row = await world.database.fetchone(
        "SELECT status FROM sheet_files WHERE campaign = ?", (SLUG,)
    )
    approval = await world.database.fetchone(
        "SELECT status, decided_by FROM approvals WHERE id = ?", (approval_id,)
    )
    assert row is not None and row["status"] == "ativo"
    assert approval is not None
    assert (approval["status"], approval["decided_by"]) == (
        "approved",
        NARRATOR,
    )
    await sign_in(client, PLAYER)
    assert (await body(await client.get(f"/api/campaigns/{SLUG}")))[
        "role"
    ] == ("player")


async def test_a_vault_failure_keeps_the_row_pending(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    await create_and_sign_in(client)
    await sign_in(client, NARRATOR)
    approval_id = (await queue_ids(client))[0]
    original = enrollment.character_notes.rewrite_frontmatter

    def fail_character(path, *args, **kwargs):
        if "characters" in path.parts:
            raise OSError("read-only vault")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(
        enrollment.character_notes, "rewrite_frontmatter", fail_character
    )

    response = await client.post(
        f"{APPROVALS}/{approval_id}",
        json={"decision": "approve"},
        headers=HEADERS,
    )

    assert response.status_code == 503
    assert (await body(response))["error"]["code"] == "vault_write_failed"
    assert "harpi-status: pendente" in read(
        world, f"{CAMPAIGN}/sheets/Nina.md"
    )
    assert "harpi-status: pendente" in read(
        world, f"{CAMPAIGN}/characters/Nina.md"
    )
    assert await queue_ids(client) == [approval_id]


async def test_a_storage_failure_restores_both_files(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    await create_and_sign_in(client)
    await sign_in(client, NARRATOR)
    approval_id = (await queue_ids(client))[0]

    async def fail(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("database down")

    monkeypatch.setattr(enrollment, "_close", fail)

    response = await client.post(
        f"{APPROVALS}/{approval_id}",
        json={"decision": "approve"},
        headers=HEADERS,
    )

    assert response.status_code == 503
    assert (await body(response))["error"]["code"] == "storage_unavailable"
    assert "harpi-status: pendente" in read(
        world, f"{CAMPAIGN}/sheets/Nina.md"
    )
    assert "harpi-status: pendente" in read(
        world, f"{CAMPAIGN}/characters/Nina.md"
    )


async def test_a_rejection_keeps_the_pair_pending_and_writes_the_note(
    client, world
):
    await create_and_sign_in(client)
    await sign_in(client, NARRATOR)
    approval_id = (await queue_ids(client))[0]

    response = await client.post(
        f"{APPROVALS}/{approval_id}",
        json={"decision": "reject", "note": "Falta o problema."},
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert (await body(response))["approvals"] == []
    sheet = read(world, f"{CAMPAIGN}/sheets/Nina.md")
    assert "harpi-status: pendente" in sheet
    assert "harpi-review-note: Falta o problema." in sheet
    row = await world.database.fetchone(
        "SELECT status, note FROM approvals WHERE id = ?", (approval_id,)
    )
    assert row is not None
    assert (row["status"], row["note"]) == ("rejected", "Falta o problema.")
    await sign_in(client, PLAYER)
    detail = await body(await client.get(f"{CHARACTERS}"))
    own = await body(
        await client.get(f"{CHARACTERS}/{detail['own_character_id']}")
    )
    assert own["sheet"]["review_note"] == "Falta o problema."


async def test_a_rejection_accepts_a_sheet_with_an_old_base(client, world):
    await create_and_sign_in(client)
    await sign_in(client, NARRATOR)
    approval_id = (await queue_ids(client))[0]
    path = world.root / CAMPAIGN / "sheets" / "Nina.md"
    edited = (
        path
        .read_text(encoding="utf-8")
        .replace("harpi-rev: 1", "harpi-rev: 9")
        .replace("refresh: 7", "refresh: 5")
    )
    path.write_text(edited, encoding="utf-8")
    await vault_index.refresh_once(vault.configured())

    response = await client.post(
        f"{APPROVALS}/{approval_id}",
        json={"decision": "reject", "note": "Falta o problema."},
        headers=HEADERS,
    )
    fresh = path.read_text(encoding="utf-8")
    row = await world.database.fetchone(
        "SELECT rev, hash FROM sheet_files WHERE path = ?",
        (f"{CAMPAIGN}/sheets/Nina.md",),
    )

    assert response.status_code == 200
    assert "harpi-review-note: Falta o problema." in fresh
    assert "harpi-rev: 10" in fresh
    assert row is not None
    assert row["rev"] == 10
    assert row["hash"] == sha256_text(fresh)


async def test_a_rejection_with_a_missing_sheet_file_reports_the_reason(
    client, world
):
    await create_and_sign_in(client)
    await sign_in(client, NARRATOR)
    approval_id = (await queue_ids(client))[0]
    (world.root / CAMPAIGN / "sheets" / "Nina.md").unlink()
    await vault_index.refresh_once(vault.configured())

    response = await client.post(
        f"{APPROVALS}/{approval_id}",
        json={"decision": "reject", "note": "Falta o problema."},
        headers=HEADERS,
    )
    payload = await body(response)
    row = await world.database.fetchone(
        "SELECT status FROM approvals WHERE id = ?", (approval_id,)
    )

    assert response.status_code == 503
    assert payload["error"]["code"] == "vault_write_failed"
    assert "sheet note not found" in payload["error"]["message"]
    assert row is not None and row["status"] == "pending"


async def test_a_rejection_without_a_note_is_a_422(client, world):
    await create_and_sign_in(client)
    await sign_in(client, NARRATOR)
    approval_id = (await queue_ids(client))[0]

    response = await client.post(
        f"{APPROVALS}/{approval_id}",
        json={"decision": "reject", "note": "  "},
        headers=HEADERS,
    )

    assert response.status_code == 422
    assert (await body(response))["error"]["code"] == "invalid_payload"


async def test_a_missing_sheet_row_blocks_the_rejection(client, world):
    await create_and_sign_in(client)
    await sign_in(client, NARRATOR)
    approval_id = (await queue_ids(client))[0]
    await world.database.execute(
        "DELETE FROM sheet_files WHERE campaign = ?", (SLUG,)
    )

    response = await client.post(
        f"{APPROVALS}/{approval_id}",
        json={"decision": "reject", "note": "Falta o problema."},
        headers=HEADERS,
    )
    row = await world.database.fetchone(
        "SELECT status FROM approvals WHERE id = ?", (approval_id,)
    )

    assert response.status_code == 503
    assert (await body(response))["error"]["code"] == "storage_unavailable"
    assert "harpi-review-note" not in read(world, f"{CAMPAIGN}/sheets/Nina.md")
    assert row is not None and row["status"] == "pending"


async def test_a_storage_failure_on_rejection_restores_the_note(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    await create_and_sign_in(client)
    await sign_in(client, NARRATOR)
    approval_id = (await queue_ids(client))[0]

    async def fail(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("database down")

    monkeypatch.setattr(enrollment, "_close", fail)

    response = await client.post(
        f"{APPROVALS}/{approval_id}",
        json={"decision": "reject", "note": "Falta o problema."},
        headers=HEADERS,
    )

    assert response.status_code == 503
    assert (await body(response))["error"]["code"] == "storage_unavailable"
    assert "harpi-review-note" not in read(world, f"{CAMPAIGN}/sheets/Nina.md")


async def test_a_cancelled_rejection_restores_the_note(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    await create_and_sign_in(client)
    await sign_in(client, NARRATOR)
    approval_id = (await queue_ids(client))[0]

    async def cancel(*args: Any, **kwargs: Any) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr(enrollment, "_close", cancel)

    with pytest.raises(asyncio.CancelledError):
        await enrollment.decide(
            world.database,
            vault_index.configured(),
            slug=SLUG,
            approval_id=approval_id,
            decision="reject",
            note="Falta o problema.",
            actor_id=NARRATOR,
        )

    assert "harpi-review-note" not in read(world, f"{CAMPAIGN}/sheets/Nina.md")
    row = await world.database.fetchone(
        "SELECT status FROM approvals WHERE id = ?", (approval_id,)
    )
    assert row is not None and row["status"] == "pending"


async def test_a_resubmit_clears_the_note_and_opens_a_new_row(client, world):
    await create_and_sign_in(client)
    await sign_in(client, NARRATOR)
    approval_id = (await queue_ids(client))[0]
    await client.post(
        f"{APPROVALS}/{approval_id}",
        json={"decision": "reject", "note": "Falta o problema."},
        headers=HEADERS,
    )
    index = vault_index.configured()
    sheet = next(
        note
        for note in index.campaign(SLUG).sheets
        if note.path.endswith("/Nina.md")
    )
    await sign_in(client, PLAYER)

    response = await client.post(
        f"/api/campaigns/{SLUG}/sheets/{sheet.id}/submit", headers=HEADERS
    )
    payload = await body(response)

    assert response.status_code == 200
    assert payload["review_note"] is None
    assert "harpi-review-note" not in read(world, f"{CAMPAIGN}/sheets/Nina.md")
    assert "harpi-status: pendente" in read(
        world, f"{CAMPAIGN}/sheets/Nina.md"
    )
    await sign_in(client, NARRATOR)
    assert len(await queue_ids(client)) == 1


async def test_a_second_submit_is_a_409(client, world):
    await sign_in(client, PLAYER)
    payload = await body(await create_pair(client))
    sheet_id = payload["sheet"]["id"]

    response = await client.post(
        f"/api/campaigns/{SLUG}/sheets/{sheet_id}/submit", headers=HEADERS
    )

    assert response.status_code == 409
    assert (await body(response))["error"]["code"] == "sheet_not_pending"


async def _rejected_pair(client) -> None:
    await create_and_sign_in(client)
    await sign_in(client, NARRATOR)
    approval_id = (await queue_ids(client))[0]
    response = await client.post(
        f"{APPROVALS}/{approval_id}",
        json={"decision": "reject", "note": "Falta o problema."},
        headers=HEADERS,
    )
    assert response.status_code == 200


async def _own_sheet(client) -> dict[str, Any]:
    await sign_in(client, PLAYER)
    listing = await body(await client.get(CHARACTERS))
    detail = await body(
        await client.get(f"{CHARACTERS}/{listing['own_character_id']}")
    )
    return detail["sheet"]


async def test_submitting_an_unknown_sheet_is_a_404(client, world):
    await sign_in(client, PLAYER)

    response = await client.post(
        f"/api/campaigns/{SLUG}/sheets/sht_missing/submit", headers=HEADERS
    )

    assert response.status_code == 404


async def test_a_vault_failure_on_submit_is_a_503(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    await _rejected_pair(client)
    sheet = await _own_sheet(client)
    original = enrollment.character_notes.rewrite_frontmatter

    def fail(path, *args, **kwargs):
        if "sheets" in path.parts:
            raise OSError("read-only vault")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(
        enrollment.character_notes, "rewrite_frontmatter", fail
    )

    response = await client.post(
        f"/api/campaigns/{SLUG}/sheets/{sheet['id']}/submit", headers=HEADERS
    )

    assert response.status_code == 503
    assert (await body(response))["error"]["code"] == "vault_write_failed"
    assert "harpi-review-note: Falta o problema." in read(
        world, f"{CAMPAIGN}/sheets/Nina.md"
    )


async def test_a_storage_failure_on_submit_restores_the_note(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    await _rejected_pair(client)
    sheet = await _own_sheet(client)

    async def fail(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("database down")

    monkeypatch.setattr(enrollment, "_insert_approval", fail)

    response = await client.post(
        f"/api/campaigns/{SLUG}/sheets/{sheet['id']}/submit", headers=HEADERS
    )

    assert response.status_code == 503
    assert (await body(response))["error"]["code"] == "storage_unavailable"
    assert "harpi-review-note: Falta o problema." in read(
        world, f"{CAMPAIGN}/sheets/Nina.md"
    )
    row = await world.database.fetchone(
        "SELECT COUNT(*) AS total FROM approvals WHERE status = 'pending'"
    )
    assert row is not None and row["total"] == 0


async def test_submit_is_owner_only_and_not_for_the_narrator(client, world):
    await sign_in(client, PLAYER)
    payload = await body(await create_pair(client))
    sheet_id = payload["sheet"]["id"]
    await add_member(world.database, OTHER)
    await add_sheet(world.database, OTHER, "ativo")
    await sign_in(client, OTHER)

    other = await client.post(
        f"/api/campaigns/{SLUG}/sheets/{sheet_id}/submit", headers=HEADERS
    )
    await sign_in(client, NARRATOR)
    narrator = await client.post(
        f"/api/campaigns/{SLUG}/sheets/{sheet_id}/submit", headers=HEADERS
    )

    assert other.status_code == 403
    assert narrator.status_code == 403


async def _approve_pair(client) -> None:
    await create_and_sign_in(client)
    await sign_in(client, NARRATOR)
    approval_id = (await queue_ids(client))[0]
    response = await client.post(
        f"{APPROVALS}/{approval_id}",
        json={"decision": "approve"},
        headers=HEADERS,
    )
    assert response.status_code == 200


async def _sheet_payload(client, name: str = "Nina") -> dict[str, Any]:
    listing = await body(await client.get(CHARACTERS))
    card = next(card for card in listing["characters"] if card["name"] == name)
    return await body(await client.get(f"{CHARACTERS}/{card['id']}"))


async def test_archiving_removes_the_card_and_demotes_the_role(client, world):
    await _approve_pair(client)
    sheet = (await _sheet_payload(client))["sheet"]

    response = await client.patch(
        f"/api/campaigns/{SLUG}/sheets/{sheet['id']}",
        json={"base_hash": sheet["hash"], "status": "archived"},
        headers=HEADERS,
    )
    listing = await client.get(CHARACTERS)
    await sign_in(client, PLAYER)
    campaign = await body(await client.get(f"/api/campaigns/{SLUG}"))

    assert response.status_code == 200
    assert "Nina" not in [
        card["name"] for card in (await body(listing))["characters"]
    ]
    assert campaign["role"] == "pending"
    assert "harpi-status: arquivado" in read(
        world, f"{CAMPAIGN}/characters/Nina.md"
    )


async def test_unarchiving_returns_the_card_and_the_role(client, world):
    await _approve_pair(client)
    sheet = (await _sheet_payload(client))["sheet"]
    archived = await body(
        await client.patch(
            f"/api/campaigns/{SLUG}/sheets/{sheet['id']}",
            json={"base_hash": sheet["hash"], "status": "archived"},
            headers=HEADERS,
        )
    )

    response = await client.patch(
        f"/api/campaigns/{SLUG}/sheets/{sheet['id']}",
        json={"base_hash": archived["hash"], "status": "active"},
        headers=HEADERS,
    )
    listing = await client.get(CHARACTERS)
    await sign_in(client, PLAYER)
    campaign = await body(await client.get(f"/api/campaigns/{SLUG}"))

    assert response.status_code == 200
    assert "Nina" in [
        card["name"] for card in (await body(listing))["characters"]
    ]
    assert campaign["role"] == "player"
    assert "harpi-status: ativo" in read(
        world, f"{CAMPAIGN}/characters/Nina.md"
    )
    row = await world.database.fetchone(
        "SELECT COUNT(*) AS total FROM members WHERE campaign_slug = ?",
        (SLUG,),
    )
    assert row is not None and row["total"] == 1


async def test_a_field_edit_does_not_touch_the_character_file(client, world):
    await _approve_pair(client)
    before = read(world, f"{CAMPAIGN}/characters/Nina.md")
    sheet = (await _sheet_payload(client))["sheet"]

    response = await client.patch(
        f"/api/campaigns/{SLUG}/sheets/{sheet['id']}",
        json={"base_hash": sheet["hash"], "fate_points": 4},
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert read(world, f"{CAMPAIGN}/characters/Nina.md") == before


async def test_a_hand_edited_owner_does_not_lock_out_the_owner(client, world):
    await _rejected_pair(client)
    row = await world.database.fetchone(
        "SELECT harpi_id FROM sheet_files WHERE owner_id = ?", (PLAYER,)
    )
    assert row is not None
    path = world.root / CAMPAIGN / "sheets" / "Nina.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            f'harpi-owner: "{PLAYER}"', "harpi-owner: 999"
        ),
        encoding="utf-8",
    )
    await vault_index.refresh_once(vault.configured())
    await sign_in(client, PLAYER)

    response = await client.post(
        f"/api/campaigns/{SLUG}/sheets/{row['harpi_id']}/submit",
        headers=HEADERS,
    )

    assert response.status_code == 200


async def test_a_name_with_a_slash_gets_a_safe_file(client, world):
    await sign_in(client, PLAYER)

    response = await create_pair(client, name="Ana / Lua")

    assert response.status_code == 200
    assert (world.root / CAMPAIGN / "characters" / "Ana Lua.md").exists()
    assert not (world.root / CAMPAIGN / "characters" / "Ana").exists()


async def test_an_unrelated_integrity_error_discards_the_new_files(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    async def fail(*args: Any, **kwargs: Any) -> None:
        raise sqlite3.IntegrityError("UNIQUE constraint failed: other")

    monkeypatch.setattr(enrollment, "_record_creation", fail)
    await sign_in(client, PLAYER)

    response = await create_pair(client)

    assert response.status_code == 503
    assert (await body(response))["error"]["code"] == "storage_unavailable"
    assert not (world.root / CAMPAIGN / "characters" / "Nina.md").exists()
    assert not (world.root / CAMPAIGN / "sheets" / "Nina.md").exists()


async def test_a_cancelled_creation_discards_the_new_files(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    async def cancel(*args: Any, **kwargs: Any) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr(enrollment, "_record_creation", cancel)
    await sign_in(client, PLAYER)

    with pytest.raises(asyncio.CancelledError):
        await enrollment.create_character(
            world.database,
            vault_index.configured(),
            slug=SLUG,
            name="Nina",
            concept=None,
            summary=None,
            user_id=PLAYER,
            display_name="Panel User",
            narrator=False,
            with_sheet=None,
        )

    assert not (world.root / CAMPAIGN / "characters" / "Nina.md").exists()
    assert not (world.root / CAMPAIGN / "sheets" / "Nina.md").exists()


async def test_two_identical_posts_create_one_pair(client, world):
    await sign_in(client, PLAYER)

    first, second = await asyncio.gather(
        create_pair(client), create_pair(client)
    )

    assert sorted([first.status_code, second.status_code]) == [200, 409]
    row = await world.database.fetchone(
        "SELECT "
        "(SELECT COUNT(*) FROM sheet_files WHERE owner_id = ?) AS sheets, "
        "(SELECT COUNT(*) FROM approvals WHERE status = 'pending') AS queue, "
        "(SELECT COUNT(*) FROM members WHERE user_id = ?) AS members",
        (PLAYER, PLAYER),
    )
    assert row is not None
    assert (row["sheets"], row["queue"], row["members"]) == (1, 1, 1)
    sheet = await world.database.fetchone(
        "SELECT path FROM sheet_files WHERE owner_id = ?", (PLAYER,)
    )
    assert sheet is not None
    stem = sheet["path"].rsplit("/", 1)[-1].removesuffix(".md")
    assert (world.root / CAMPAIGN / "characters" / f"{stem}.md").exists()
    assert (world.root / sheet["path"]).exists()


async def test_concurrent_names_for_one_player_keep_the_winner_files(world):
    index = vault_index.configured()

    async def create(name: str):
        return await enrollment.create_character(
            world.database,
            index,
            slug=SLUG,
            name=name,
            concept=None,
            summary=None,
            user_id=PLAYER,
            display_name="Panel User",
            narrator=False,
            with_sheet=None,
        )

    results = await asyncio.gather(
        create("Nina"), create("Outra"), return_exceptions=True
    )
    winners = [
        item for item in results if isinstance(item, enrollment.Created)
    ]
    failures = [
        item
        for item in results
        if isinstance(item, enrollment.SheetAlreadyExists)
    ]

    assert (len(winners), len(failures)) == (1, 1)
    row = await world.database.fetchone(
        "SELECT path FROM sheet_files WHERE owner_id = ?", (PLAYER,)
    )
    assert row is not None
    stem = row["path"].rsplit("/", 1)[-1].removesuffix(".md")
    assert (world.root / CAMPAIGN / "characters" / f"{stem}.md").exists()
    assert (world.root / row["path"]).exists()
    other = "Outra" if stem.startswith("Nina") else "Nina"
    assert not (world.root / CAMPAIGN / "characters" / f"{other}.md").exists()
    assert not (world.root / CAMPAIGN / "sheets" / f"{other}.md").exists()
    approvals = await world.database.fetchone(
        "SELECT COUNT(*) AS total FROM approvals WHERE status = 'pending'"
    )
    assert approvals is not None and approvals["total"] == 1


async def test_long_names_with_a_shared_prefix_get_distinct_files(
    client, world
):
    await sign_in(client, NARRATOR)
    base = "A" * 80

    first = await client.post(CHARACTERS, json={"name": base}, headers=HEADERS)
    second = await client.post(
        CHARACTERS, json={"name": f"{base}B"}, headers=HEADERS
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert (await body(first))["card"]["name"] == base
    assert (await body(second))["card"]["name"] == f"{base}B"
    files = list((world.root / CAMPAIGN / "characters").glob("A*.md"))
    assert len(files) == 2
    assert len({path.name for path in files}) == 2


async def test_a_second_decision_is_a_409(client, world):
    await create_and_sign_in(client)
    await sign_in(client, NARRATOR)
    approval_id = (await queue_ids(client))[0]

    first = await client.post(
        f"{APPROVALS}/{approval_id}",
        json={"decision": "approve"},
        headers=HEADERS,
    )
    second = await client.post(
        f"{APPROVALS}/{approval_id}",
        json={"decision": "approve"},
        headers=HEADERS,
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert (await body(second))["error"]["code"] == (
        "approval_already_decided"
    )


async def test_a_database_failure_on_archive_reverts_the_character(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    await _approve_pair(client)
    sheet = (await _sheet_payload(client))["sheet"]

    async def fail(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("database down")

    monkeypatch.setattr(sheet_store, "store_sheet", fail)

    response = await client.patch(
        f"/api/campaigns/{SLUG}/sheets/{sheet['id']}",
        json={"base_hash": sheet["hash"], "status": "archived"},
        headers=HEADERS,
    )
    row = await world.database.fetchone(
        "SELECT status FROM sheet_files WHERE harpi_id = ?", (sheet["id"],)
    )

    assert response.status_code == 503
    assert (await body(response))["error"]["code"] == "storage_unavailable"
    assert "harpi-status: ativo" in read(world, f"{CAMPAIGN}/sheets/Nina.md")
    assert "harpi-status: ativo" in read(
        world, f"{CAMPAIGN}/characters/Nina.md"
    )
    assert row is not None and row["status"] == "ativo"


async def test_a_missing_sheet_row_blocks_the_resubmit(client, world):
    await _rejected_pair(client)
    sheet = await _own_sheet(client)
    await world.database.execute(
        "DELETE FROM sheet_files WHERE campaign = ?", (SLUG,)
    )

    response = await client.post(
        f"/api/campaigns/{SLUG}/sheets/{sheet['id']}/submit", headers=HEADERS
    )

    assert response.status_code == 503
    assert (await body(response))["error"]["code"] == "storage_unavailable"
    assert "harpi-review-note: Falta o problema." in read(
        world, f"{CAMPAIGN}/sheets/Nina.md"
    )


async def test_a_failed_character_mirror_reverts_the_sheet(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    await _approve_pair(client)
    sheet = (await _sheet_payload(client))["sheet"]

    def fail(*args: Any, **kwargs: Any) -> None:
        raise OSError("read-only vault")

    monkeypatch.setattr(enrollment.character_notes, "set_status", fail)

    response = await client.patch(
        f"/api/campaigns/{SLUG}/sheets/{sheet['id']}",
        json={"base_hash": sheet["hash"], "status": "archived"},
        headers=HEADERS,
    )
    row = await world.database.fetchone(
        "SELECT status FROM sheet_files WHERE harpi_id = ?", (sheet["id"],)
    )

    assert response.status_code == 503
    assert (await body(response))["error"]["code"] == "vault_write_failed"
    assert "harpi-status: ativo" in read(world, f"{CAMPAIGN}/sheets/Nina.md")
    assert row is not None and row["status"] == "ativo"


async def test_a_cancelled_approval_restores_both_files(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    await create_and_sign_in(client)
    await sign_in(client, NARRATOR)
    approval_id = (await queue_ids(client))[0]

    async def cancel(*args: Any, **kwargs: Any) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr(enrollment, "_close", cancel)

    with pytest.raises(asyncio.CancelledError):
        await enrollment.decide(
            world.database,
            vault_index.configured(),
            slug=SLUG,
            approval_id=approval_id,
            decision="approve",
            note="",
            actor_id=NARRATOR,
        )

    assert "harpi-status: pendente" in read(
        world, f"{CAMPAIGN}/sheets/Nina.md"
    )
    assert "harpi-status: pendente" in read(
        world, f"{CAMPAIGN}/characters/Nina.md"
    )
    row = await world.database.fetchone(
        "SELECT status FROM approvals WHERE id = ?", (approval_id,)
    )
    assert row is not None and row["status"] == "pending"


async def test_a_missing_sheet_row_blocks_the_approval(client, world):
    await create_and_sign_in(client)
    await sign_in(client, NARRATOR)
    approval_id = (await queue_ids(client))[0]
    await world.database.execute(
        "DELETE FROM sheet_files WHERE campaign = ?", (SLUG,)
    )

    response = await client.post(
        f"{APPROVALS}/{approval_id}",
        json={"decision": "approve"},
        headers=HEADERS,
    )
    row = await world.database.fetchone(
        "SELECT status FROM approvals WHERE id = ?", (approval_id,)
    )

    assert response.status_code == 503
    assert (await body(response))["error"]["code"] == "storage_unavailable"
    assert "harpi-status: pendente" in read(
        world, f"{CAMPAIGN}/sheets/Nina.md"
    )
    assert row is not None and row["status"] == "pending"


async def test_concurrent_submits_queue_once(client, world):
    await _rejected_pair(client)
    sheet = await _own_sheet(client)
    index = vault_index.configured()

    results = await asyncio.gather(
        enrollment.submit(
            world.database,
            index,
            slug=SLUG,
            sheet_id=sheet["id"],
            user_id=PLAYER,
        ),
        enrollment.submit(
            world.database,
            index,
            slug=SLUG,
            sheet_id=sheet["id"],
            user_id=PLAYER,
        ),
        return_exceptions=True,
    )

    assert results.count(None) == 1
    assert (
        sum(isinstance(item, enrollment.NotSubmittable) for item in results)
        == 1
    )
    row = await world.database.fetchone(
        "SELECT COUNT(*) AS total FROM approvals WHERE status = 'pending'"
    )
    assert row is not None and row["total"] == 1
    assert "harpi-review-note" not in read(world, f"{CAMPAIGN}/sheets/Nina.md")
