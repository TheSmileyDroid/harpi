from __future__ import annotations

import json
import time
from pathlib import Path

from src.panel import notes
from src.panel.sheet_write import SheetRecord, SheetWriteResult
from src.panel.sheets import dump_block, load_sheet, prose_sections
from src.storage.database import Database


async def sheet_record(database: Database, path: str) -> SheetRecord | None:
    row = await database.fetchone(
        "SELECT s.harpi_id, s.owner_id, s.status, s.rev, m.display_name "
        "FROM sheet_files s "
        "LEFT JOIN members m ON m.campaign_slug = s.campaign "
        "AND m.user_id = s.owner_id "
        "WHERE s.path = ?",
        (path,),
    )
    if row is None:
        return None
    return SheetRecord(
        id=row["harpi_id"],
        owner=row["owner_id"],
        status=row["status"],
        rev=row["rev"],
        owner_name=row["display_name"],
    )


async def store_sheet(
    database: Database,
    slug: str,
    path: str,
    result: SheetWriteResult,
) -> None:
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
            base_state(result.text),
            result.status,
            result.owner,
            int(time.time()),
        ),
    )


def base_state(text: str) -> str:
    fields, _ = notes.split_frontmatter(text)
    history, prose = prose_sections(text)
    loaded = load_sheet(text)
    block = None if loaded.document is None else dump_block(loaded.document)
    return json.dumps(
        {
            "frontmatter": fields,
            "history": history,
            "notes": prose,
            "block": block,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def backup_root(database: Database) -> Path:
    return database.path.parent / "vault-backups"
