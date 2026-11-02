from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.panel import notes
from src.panel.sheet_write import SheetRecord, SheetWriteResult
from src.panel.sheets import (
    dump_block,
    load_sheet,
    prose_sections,
    sha256_text,
)
from src.storage.database import Database

STATE_KEYS = ("frontmatter", "history", "notes", "block")


@dataclass(frozen=True, slots=True)
class StoredSheet:
    path: str
    harpi_id: str
    campaign: str
    rev: int
    hash: str
    last_text: str
    base_json: str
    status: str
    owner_id: str | None
    state: str

    def record(self) -> SheetRecord:
        return SheetRecord(
            id=self.harpi_id,
            owner=self.owner_id,
            status=self.status,
            rev=self.rev,
            base_json=self.base_json,
            state=self.state,
        )


async def stored_sheet(
    database: Database, campaign: str, sheet_id: str
) -> StoredSheet | None:
    row = await database.fetchone(
        "SELECT path, harpi_id, campaign, rev, hash, last_text, base_json, "
        "status, owner_id, state FROM sheet_files "
        "WHERE campaign = ? AND harpi_id = ? ORDER BY path LIMIT 1",
        (campaign, sheet_id),
    )
    return None if row is None else _stored(row)


async def stored_sheet_by_path(
    database: Database, path: str
) -> StoredSheet | None:
    row = await database.fetchone(
        "SELECT path, harpi_id, campaign, rev, hash, last_text, base_json, "
        "status, owner_id, state FROM sheet_files WHERE path = ?",
        (path,),
    )
    return None if row is None else _stored(row)


def _stored(row) -> StoredSheet:
    return StoredSheet(
        path=row["path"],
        harpi_id=row["harpi_id"],
        campaign=row["campaign"],
        rev=row["rev"],
        hash=row["hash"],
        last_text=row["last_text"],
        base_json=row["base_json"],
        status=row["status"],
        owner_id=row["owner_id"],
        state=row["state"],
    )


async def sheet_record(database: Database, path: str) -> SheetRecord | None:
    row = await database.fetchone(
        "SELECT s.harpi_id, s.owner_id, s.status, s.rev, s.base_json, "
        "s.state, m.display_name "
        "FROM sheet_files s "
        "LEFT JOIN members m ON m.campaign_slug = s.campaign "
        "AND m.user_id = s.owner_id "
        "WHERE s.path = ?",
        (path,),
    )
    if row is None:
        return None
    previous_hash, previous_json = previous_of(row["base_json"])
    return SheetRecord(
        id=row["harpi_id"],
        owner=row["owner_id"],
        status=row["status"],
        rev=row["rev"],
        owner_name=row["display_name"],
        base_json=row["base_json"],
        state=row["state"],
        previous_hash=previous_hash,
        previous_json=previous_json,
    )


async def store_sheet(
    database: Database,
    slug: str,
    path: str,
    result: SheetWriteResult,
) -> None:
    previous = (
        None
        if result.previous_text is None
        else previous_state(result.previous_text)
    )
    await database.execute(
        "INSERT INTO sheet_files ("
        "path, harpi_id, campaign, rev, hash, last_text, base_json, "
        "status, owner_id, state, updated_at"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ok', ?) "
        "ON CONFLICT(path) DO UPDATE SET "
        "harpi_id = excluded.harpi_id, campaign = excluded.campaign, "
        "rev = excluded.rev, hash = excluded.hash, "
        "last_text = excluded.last_text, base_json = excluded.base_json, "
        "status = excluded.status, owner_id = excluded.owner_id, "
        "state = 'ok', updated_at = excluded.updated_at",
        (
            path,
            result.harpi_id,
            slug,
            result.rev,
            result.hash,
            result.text,
            base_state(result.text, previous=previous),
            result.status,
            result.owner,
            int(time.time()),
        ),
    )


async def forget_sheet(database: Database, path: str) -> None:
    await database.execute("DELETE FROM sheet_files WHERE path = ?", (path,))


def state_dict(text: str) -> dict[str, Any]:
    fields, _ = notes.split_frontmatter(text)
    history, prose = prose_sections(text)
    loaded = load_sheet(text)
    block = None if loaded.document is None else dump_block(loaded.document)
    return {
        "frontmatter": fields,
        "history": history,
        "notes": prose,
        "block": block,
    }


def base_state(text: str, *, previous: dict[str, Any] | None = None) -> str:
    data = state_dict(text)
    if previous is not None:
        data["previous"] = previous
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def previous_state(text: str) -> dict[str, Any]:
    return {**state_dict(text), "hash": sha256_text(text)}


def previous_of(base_json: str | None) -> tuple[str | None, str | None]:
    data = _document(base_json)
    previous = data.get("previous")
    if not isinstance(previous, dict):
        return None, None
    digest = previous.get("hash")
    state = {key: previous.get(key) for key in STATE_KEYS}
    return (
        digest if isinstance(digest, str) else None,
        json.dumps(state, ensure_ascii=False, sort_keys=True),
    )


def current_state(base_json: str) -> dict[str, Any]:
    data = _document(base_json)
    return {key: data.get(key) for key in STATE_KEYS}


def character_id_from_base(base_json: str | None) -> str | None:
    data = current_state(base_json or "{}")
    frontmatter = data.get("frontmatter")
    if not isinstance(frontmatter, dict):
        return None
    return notes.field_front(frontmatter, "harpi-character-id")


def pending_of(base_json: str | None) -> dict[str, Any] | None:
    pending = _document(base_json).get("pending")
    return pending if isinstance(pending, dict) else None


def with_pending(base_json: str, pending: dict[str, Any]) -> str:
    data = _document(base_json)
    data["pending"] = pending
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def without_pending(base_json: str) -> str:
    data = _document(base_json)
    data.pop("pending", None)
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def _document(base_json: str | None) -> dict[str, Any]:
    if not base_json:
        return {}
    try:
        data = json.loads(base_json)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def backup_root(database: Database) -> Path:
    return database.path.parent / "vault-backups"
