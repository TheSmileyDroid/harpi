from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.panel import sheet_merge, sheet_store
from src.panel.schemas import SheetPatch
from src.panel.sheet_merge import MergeConflict, MergeResult, SheetState
from src.panel.sheet_write import SheetRecord, read_text
from src.storage.database import Database

CONFLICT_STATE = "conflito"
OURS = "ours"
THEIRS = "theirs"
BOTH = "both"
DECISIONS = frozenset({OURS, THEIRS, BOTH})
CONFLICT_COLUMNS = (
    "SELECT c.id, c.path, c.field_path, c.base, c.ours, c.theirs, "
    "s.harpi_id, s.owner_id, s.base_json "
    "FROM sheet_conflicts c JOIN sheet_files s ON s.path = c.path "
)


@dataclass(frozen=True, slots=True)
class ConflictRecord:
    id: str
    sheet_id: str
    character_id: str | None
    path: str
    field_path: str
    base: str | None
    ours: str | None
    theirs: str | None
    allow_both: bool


@dataclass(frozen=True, slots=True)
class PendingWrite:
    path: str
    sheet_id: str
    patch: SheetPatch
    record: SheetRecord


@dataclass(frozen=True, slots=True)
class Resolution:
    conflicts: tuple[ConflictRecord, ...]
    write: PendingWrite | None
    field_path: str


class ConflictError(ValueError):
    pass


class ConflictNotFound(ConflictError):
    pass


class ConflictNotPending(ConflictError):
    pass


class InvalidDecision(ConflictError):
    pass


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


def allows_both(field_path: str) -> bool:
    prefix = "block."
    if not field_path.startswith(prefix) or "[" not in field_path:
        return False
    field = field_path[len(prefix) : field_path.index("[")]
    return field in sheet_merge.DUPLICABLE_FIELDS


async def record(
    database: Database,
    path: str,
    patch: SheetPatch,
    conflicts: tuple[MergeConflict, ...],
    base_json: str,
) -> list[ConflictRecord]:
    stored = await sheet_store.stored_sheet_by_path(database, path)
    if stored is None:
        return []
    pending = {
        "patch": json.loads(patch.model_dump_json()),
        "base": json.loads(base_json),
        "decisions": {},
    }
    now = int(time.time())
    async with database.transaction() as connection:
        await connection.execute(
            "UPDATE sheet_files SET state = ?, base_json = ?, "
            "updated_at = ? WHERE path = ?",
            (
                CONFLICT_STATE,
                sheet_store.with_pending(stored.base_json, pending),
                now,
                path,
            ),
        )
        await connection.execute(
            "DELETE FROM sheet_conflicts WHERE path = ? "
            "AND resolved_at IS NULL",
            (path,),
        )
        for conflict in conflicts:
            await _insert(connection, path, conflict, now)
    return await path_queue(database, path)


async def _insert(
    connection: Any, path: str, conflict: MergeConflict, now: int
) -> None:
    await connection.execute(
        "INSERT INTO sheet_conflicts ("
        "id, path, field_path, base, ours, theirs, created_at"
        ") VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            new_id("cnf"),
            path,
            conflict.field_path,
            *conflict.rendered(),
            now,
        ),
    )


async def queue(
    database: Database, campaign: str, owner: str | None
) -> list[ConflictRecord]:
    rows = await database.fetchall(
        f"{CONFLICT_COLUMNS} WHERE c.resolved_at IS NULL "
        "AND s.campaign = ? AND (? IS NULL OR s.owner_id = ?) "
        "ORDER BY c.created_at, c.id",
        (campaign, owner, owner),
    )
    return [_conflict_record(row) for row in rows]


async def path_queue(database: Database, path: str) -> list[ConflictRecord]:
    rows = await database.fetchall(
        f"{CONFLICT_COLUMNS} WHERE c.resolved_at IS NULL AND c.path = ? "
        "ORDER BY c.created_at, c.id",
        (path,),
    )
    return [_conflict_record(row) for row in rows]


async def open_paths(database: Database, campaign: str) -> frozenset[str]:
    rows = await database.fetchall(
        "SELECT DISTINCT s.path FROM sheet_conflicts c "
        "JOIN sheet_files s ON s.path = c.path "
        "WHERE c.resolved_at IS NULL AND s.campaign = ?",
        (campaign,),
    )
    return frozenset(row["path"] for row in rows)


def _conflict_record(row: Any) -> ConflictRecord:
    return ConflictRecord(
        id=row["id"],
        sheet_id=row["harpi_id"],
        character_id=sheet_store.character_id_from_base(row["base_json"]),
        path=row["path"],
        field_path=row["field_path"],
        base=row["base"],
        ours=row["ours"],
        theirs=row["theirs"],
        allow_both=allows_both(row["field_path"]),
    )


async def owner_of(
    database: Database, campaign: str, conflict_id: str
) -> str | None:
    row = await database.fetchone(
        "SELECT s.owner_id FROM sheet_conflicts c "
        "JOIN sheet_files s ON s.path = c.path "
        "WHERE c.id = ? AND s.campaign = ?",
        (conflict_id, campaign),
    )
    if row is None:
        raise ConflictNotFound("conflict not found")
    return row["owner_id"]


async def decide(
    database: Database,
    root: Path,
    *,
    campaign: str,
    conflict_id: str,
    decision: str,
    actor: str,
) -> Resolution:
    _valid_decision(decision)
    row = await _conflict_row(database, campaign, conflict_id)
    pending = sheet_store.pending_of(row["base_json"])
    if pending is None:
        raise ConflictNotPending("the sheet is not in conflict")
    _, text, base, ours, theirs = _conflict_inputs(root, row, pending)
    current = sheet_merge.merge(base, ours, theirs)
    _check_decision(decision, current.conflicts, row["field_path"])
    decisions = await _store_decision(
        database, row["path"], row["field_path"], decision, actor
    )
    resolved = sheet_merge.merge(base, ours, theirs, decisions)
    if resolved.remaining:
        await _refresh(database, row["path"], resolved.remaining)
        return Resolution(
            tuple(await path_queue(database, row["path"])),
            None,
            row["field_path"],
        )
    return Resolution(
        (), _ready_write(row, text, theirs, resolved), row["field_path"]
    )


def _valid_decision(decision: str) -> None:
    if decision not in DECISIONS:
        raise InvalidDecision("unknown decision")


def _conflict_inputs(root: Path, row: Any, pending: dict[str, Any]):
    patch = SheetPatch.model_validate(pending["patch"])
    text = read_text(root / row["path"])
    base = sheet_merge.state_from_base(json.dumps(pending["base"]))
    ours = sheet_merge.apply_patch(base, patch)
    return patch, text, base, ours, sheet_merge.state_from_text(text)


def _check_decision(
    decision: str, conflicts: tuple[MergeConflict, ...], field_path: str
) -> None:
    if decision != BOTH:
        return
    target = next(
        (
            conflict
            for conflict in conflicts
            if conflict.field_path == field_path
        ),
        None,
    )
    if target is not None and not target.allow_both:
        raise InvalidDecision("keep both only applies to a list item")


def _ready_write(
    row: Any, text: str, theirs: SheetState, resolved: MergeResult
) -> PendingWrite:
    changes = sheet_merge.patch_from_state(theirs, resolved.state)
    return PendingWrite(
        path=row["path"],
        sheet_id=row["harpi_id"],
        patch=sheet_merge.consolidated_patch(text, changes),
        record=_sheet_record(row),
    )


async def _conflict_row(database: Database, campaign: str, conflict_id: str):
    row = await database.fetchone(
        "SELECT c.id, c.path, c.field_path, c.resolved_at, s.harpi_id, "
        "s.owner_id, s.rev, s.status, s.base_json, s.state "
        "FROM sheet_conflicts c "
        "JOIN sheet_files s ON s.path = c.path "
        "WHERE c.id = ? AND s.campaign = ?",
        (conflict_id, campaign),
    )
    if row is None:
        raise ConflictNotFound("conflict not found")
    if row["resolved_at"] is not None:
        raise ConflictNotPending("the conflict was already decided")
    if row["state"] != CONFLICT_STATE:
        raise ConflictNotPending("the sheet is not in conflict")
    return row


async def _store_decision(
    database: Database, path: str, field_path: str, decision: str, actor: str
) -> dict[str, str]:
    async with database.transaction() as connection:
        row = await _open_pending(connection, path)
        pending = sheet_store.pending_of(row["base_json"])
        if pending is None:
            raise ConflictNotPending("the sheet is not in conflict")
        await _claim(connection, path, field_path, actor)
        decisions = dict(pending.get("decisions") or {})
        decisions[field_path] = decision
        pending["decisions"] = decisions
        await connection.execute(
            "UPDATE sheet_files SET base_json = ? WHERE path = ?",
            (sheet_store.with_pending(row["base_json"], pending), path),
        )
    return decisions


async def _open_pending(connection: Any, path: str) -> Any:
    cursor = await connection.execute(
        "SELECT base_json FROM sheet_files WHERE path = ?", (path,)
    )
    row = await cursor.fetchone()
    if row is None:
        raise ConflictNotFound("conflict not found")
    return row


async def _claim(
    connection: Any, path: str, field_path: str, actor: str
) -> None:
    cursor = await connection.execute(
        "UPDATE sheet_conflicts SET resolved_by = ?, resolved_at = ? "
        "WHERE path = ? AND field_path = ? AND resolved_at IS NULL",
        (actor, int(time.time()), path, field_path),
    )
    if cursor.rowcount != 1:
        raise ConflictNotPending("the conflict was already decided")


async def undo_decision(
    database: Database, path: str, field_path: str
) -> None:
    async with database.transaction() as connection:
        row = await _open_pending(connection, path)
        pending = sheet_store.pending_of(row["base_json"])
        if pending is None:
            return
        decisions = dict(pending.get("decisions") or {})
        decisions.pop(field_path, None)
        pending["decisions"] = decisions
        await connection.execute(
            "UPDATE sheet_files SET base_json = ? WHERE path = ?",
            (sheet_store.with_pending(row["base_json"], pending), path),
        )
        await connection.execute(
            "UPDATE sheet_conflicts SET resolved_at = NULL, resolved_by = NULL "
            "WHERE path = ? AND field_path = ?",
            (path, field_path),
        )


async def _refresh(
    database: Database,
    path: str,
    remaining: tuple[MergeConflict, ...],
) -> None:
    now = int(time.time())
    async with database.transaction() as connection:
        existing = await _open_ids(connection, path)
        keep = {conflict.field_path for conflict in remaining}
        for field_path, conflict_id in existing.items():
            if field_path not in keep:
                await connection.execute(
                    "DELETE FROM sheet_conflicts WHERE id = ?", (conflict_id,)
                )
        for conflict in remaining:
            conflict_id = existing.get(conflict.field_path)
            if conflict_id is None:
                await _insert(connection, path, conflict, now)
            else:
                await connection.execute(
                    "UPDATE sheet_conflicts SET base = ?, ours = ?, "
                    "theirs = ? WHERE id = ?",
                    (*conflict.rendered(), conflict_id),
                )


async def _open_ids(connection: Any, path: str) -> dict[str, str]:
    cursor = await connection.execute(
        "SELECT id, field_path FROM sheet_conflicts "
        "WHERE path = ? AND resolved_at IS NULL",
        (path,),
    )
    return {row["field_path"]: row["id"] for row in await cursor.fetchall()}


async def settle(database: Database, path: str, actor: str) -> None:
    await database.execute(
        "UPDATE sheet_conflicts SET resolved_at = ?, resolved_by = ? "
        "WHERE path = ? AND resolved_at IS NULL",
        (int(time.time()), actor, path),
    )


def _sheet_record(row: Any) -> SheetRecord:
    return SheetRecord(
        id=row["harpi_id"],
        owner=row["owner_id"],
        status=row["status"],
        rev=row["rev"],
        base_json=row["base_json"],
        state=CONFLICT_STATE,
    )
