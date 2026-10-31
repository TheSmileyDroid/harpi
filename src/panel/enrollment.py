from __future__ import annotations

import asyncio
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from loguru import logger

from src.panel import character_notes, sheet_store, sheet_write
from src.panel.character_notes import (
    ACTIVE,
    PENDING,
    REVIEW_NOTE_KEY,
    NoteRewrite,
)
from src.panel.notes import SheetNote
from src.panel.sheets import default_config, sha256_text
from src.panel.vault_index import (
    CAMPAIGN_ROOT,
    CHARACTERS_FOLDER,
    SHEETS_FOLDER,
    VaultIndex,
)
from src.panel.vault_write import create_exclusive
from src.storage.database import Database

APPROVE = "approve"
REJECT = "reject"
LIVE_OWNER_COLUMNS = "sheet_files.campaign, sheet_files.owner_id"
PENDING_APPROVAL_COLUMNS = "approvals.campaign_slug, approvals.sheet_path"
_LOCKS: dict[tuple[int, str], asyncio.Lock] = {}


class EnrollmentError(Exception):
    pass


class NameTaken(EnrollmentError):
    pass


class SheetAlreadyExists(EnrollmentError):
    pass


class InvalidRequest(EnrollmentError):
    pass


class ApprovalNotFound(EnrollmentError):
    pass


class AlreadyDecided(EnrollmentError):
    pass


class NotOwner(EnrollmentError):
    pass


class NotSubmittable(EnrollmentError):
    pass


class VaultWriteFailed(EnrollmentError):
    pass


class StorageFailed(EnrollmentError):
    pass


@dataclass(frozen=True, slots=True)
class Created:
    character_id: str
    sheet_id: str | None


@dataclass(frozen=True, slots=True)
class NewPair:
    character_path: str
    sheet_path: str
    character_body: str
    sheet_body: str | None
    character_id: str
    sheet_id: str | None


@dataclass(frozen=True, slots=True)
class StatusMirror:
    path: Path
    previous_text: str


@dataclass(frozen=True, slots=True)
class PendingApproval:
    id: str
    sheet_path: str
    sheet_id: str | None
    character_id: str | None
    character_name: str
    owner: str | None
    owner_name: str | None
    note: str
    requested_at: int


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


def note_path(slug: str, folder: str, stem: str) -> str:
    return PurePosixPath(*CAMPAIGN_ROOT, slug, folder, f"{stem}.md").as_posix()


async def create_character(
    database: Database,
    index: VaultIndex,
    *,
    slug: str,
    name: str,
    concept: str | None,
    summary: str | None,
    user_id: str,
    display_name: str | None,
    narrator: bool,
    with_sheet: bool | None,
) -> Created:
    root = _root(index)
    base = character_notes.file_stem(name)
    _refuse_player_skip(narrator, with_sheet)
    async with _named_lock("create", f"{slug}/{base}"):
        return await _create_locked(
            database,
            index,
            root,
            slug=slug,
            base=base,
            name=name,
            concept=concept,
            summary=summary,
            user_id=user_id,
            display_name=display_name,
            narrator=narrator,
            with_sheet=with_sheet,
        )


async def _create_locked(
    database: Database,
    index: VaultIndex,
    root: Path,
    *,
    slug: str,
    base: str,
    name: str,
    concept: str | None,
    summary: str | None,
    user_id: str,
    display_name: str | None,
    narrator: bool,
    with_sheet: bool | None,
) -> Created:
    character_id = new_id("chr")
    sheet_id = _new_sheet_id(narrator, with_sheet)
    if not narrator:
        await _refuse_second_pair(database, slug, user_id)
    stem = _available_stem(root, slug, base, character_id)
    pair = _build_pair(
        index,
        slug,
        stem,
        name=name,
        character_id=character_id,
        sheet_id=sheet_id,
        concept=concept,
        summary=summary,
        narrator=narrator,
        user_id=user_id,
        display_name=display_name,
    )
    created = _write_pair(root, pair)
    await _store_pair(
        database,
        root,
        created,
        pair,
        slug=slug,
        narrator=narrator,
        user_id=user_id,
        display_name=display_name,
    )
    return Created(character_id=pair.character_id, sheet_id=pair.sheet_id)


def _new_sheet_id(narrator: bool, with_sheet: bool | None) -> str | None:
    return None if narrator and not with_sheet else new_id("sht")


async def _store_pair(
    database: Database,
    root: Path,
    created: list[str],
    pair: NewPair,
    *,
    slug: str,
    narrator: bool,
    user_id: str,
    display_name: str | None,
) -> None:
    try:
        await _record_creation(
            database,
            slug=slug,
            sheet_path=pair.sheet_path
            if pair.sheet_body is not None
            else None,
            character_id=pair.character_id,
            sheet_id=pair.sheet_id,
            sheet_body=pair.sheet_body,
            status=ACTIVE if narrator else PENDING,
            owner=None if narrator else user_id,
            display_name=display_name,
            requested_by=user_id,
            queue=not narrator,
        )
    except sqlite3.IntegrityError as failure:
        _discard(root, *created)
        if LIVE_OWNER_COLUMNS in str(failure):
            raise SheetAlreadyExists(
                "the user already has a pending or active sheet"
            ) from failure
        raise StorageFailed("character storage failed") from failure
    except BaseException as failure:
        _discard(root, *created)
        if isinstance(failure, Exception):
            raise StorageFailed("character storage failed") from failure
        raise


def _build_pair(
    index: VaultIndex,
    slug: str,
    stem: str,
    *,
    name: str,
    character_id: str,
    sheet_id: str | None,
    concept: str | None,
    summary: str | None,
    narrator: bool,
    user_id: str,
    display_name: str | None,
) -> NewPair:
    status = ACTIVE if narrator else PENDING
    character_body = character_notes.character_text(
        slug, character_id, name, concept, summary, status
    )
    sheet_body = _sheet_body(
        index,
        slug,
        stem,
        sheet_id,
        character_id,
        narrator,
        user_id,
        display_name,
        status,
    )
    return NewPair(
        character_path=note_path(slug, CHARACTERS_FOLDER, stem),
        sheet_path=note_path(slug, SHEETS_FOLDER, stem),
        character_body=character_body,
        sheet_body=sheet_body,
        character_id=character_id,
        sheet_id=sheet_id,
    )


def _sheet_body(
    index: VaultIndex,
    slug: str,
    stem: str,
    sheet_id: str | None,
    character_id: str,
    narrator: bool,
    user_id: str,
    display_name: str | None,
    status: str,
) -> str | None:
    if sheet_id is None:
        return None
    config = index.campaign(slug).config or default_config()
    return character_notes.sheet_text(
        slug,
        sheet_id,
        character_id,
        stem,
        None if narrator else user_id,
        None if narrator else display_name,
        status,
        config,
    )


def _write_pair(root: Path, pair: NewPair) -> list[str]:
    created: list[str] = []
    try:
        _create_file(root / pair.character_path, pair.character_body)
        created.append(pair.character_path)
        if pair.sheet_body is not None:
            _create_file(root / pair.sheet_path, pair.sheet_body)
            created.append(pair.sheet_path)
    except BaseException:
        _discard(root, *created)
        raise
    return created


def _available_stem(
    root: Path, slug: str, base: str, character_id: str
) -> str:
    if not _pair_exists(root, slug, base):
        return base
    suffix = character_id.removeprefix("chr_")[:6]
    room = character_notes.NAME_LIMIT - len(suffix) - 1
    candidate = f"{base[:room].rstrip()} {suffix}"
    if not _pair_exists(root, slug, candidate):
        return candidate
    raise NameTaken("a note with this name already exists")


def _pair_exists(root: Path, slug: str, stem: str) -> bool:
    return any(
        (root / note_path(slug, folder, stem)).exists()
        for folder in (CHARACTERS_FOLDER, SHEETS_FOLDER)
    )


async def pending_approvals(
    database: Database, index: VaultIndex, slug: str
) -> list[PendingApproval]:
    rows = await database.fetchall(
        "SELECT a.id, a.sheet_path, a.sheet_id, a.character_id, a.note, "
        "a.requested_by, a.requested_at, s.owner_id, m.display_name "
        "FROM approvals a "
        "LEFT JOIN sheet_files s ON s.path = a.sheet_path "
        "LEFT JOIN members m ON m.campaign_slug = a.campaign_slug "
        "AND m.user_id = COALESCE(s.owner_id, a.requested_by) "
        "WHERE a.campaign_slug = ? AND a.status = 'pending' "
        "ORDER BY a.requested_at, a.id",
        (slug,),
    )
    characters = index.campaign(slug).characters
    return [
        PendingApproval(
            id=row["id"],
            sheet_path=row["sheet_path"],
            sheet_id=row["sheet_id"],
            character_id=row["character_id"],
            character_name=_character_name(row, characters),
            owner=row["owner_id"],
            owner_name=row["display_name"],
            note=row["note"],
            requested_at=row["requested_at"],
        )
        for row in rows
    ]


async def decide(
    database: Database,
    index: VaultIndex,
    *,
    slug: str,
    approval_id: str,
    decision: str,
    note: str,
    actor_id: str,
) -> None:
    async with _named_lock("decide", f"{slug}/{approval_id}"):
        await _decide_locked(
            database,
            index,
            slug=slug,
            approval_id=approval_id,
            decision=decision,
            note=note,
            actor_id=actor_id,
        )


async def _decide_locked(
    database: Database,
    index: VaultIndex,
    *,
    slug: str,
    approval_id: str,
    decision: str,
    note: str,
    actor_id: str,
) -> None:
    root = _root(index)
    row = await database.fetchone(
        "SELECT id, sheet_path, sheet_id, character_id, status "
        "FROM approvals WHERE id = ? AND campaign_slug = ?",
        (approval_id, slug),
    )
    if row is None:
        raise ApprovalNotFound("approval not found")
    if row["status"] != "pending":
        raise AlreadyDecided("approval already decided")
    sheet = _sheet_at(index, slug, row["sheet_path"])
    if sheet is None:
        raise VaultWriteFailed("sheet note not found")
    if decision == APPROVE:
        await _approve(database, root, index, slug, row, sheet, actor_id)
        return
    if decision == REJECT:
        await _reject(database, root, slug, row, sheet, note.strip(), actor_id)
        return
    raise InvalidRequest("unknown decision")


async def submit(
    database: Database,
    index: VaultIndex,
    *,
    slug: str,
    sheet_id: str,
    user_id: str,
) -> None:
    sheet = _sheet_by_id(index, slug, sheet_id)
    if sheet is None:
        raise ApprovalNotFound("sheet not found")
    async with _named_lock("submit", sheet.path):
        await _submit_locked(database, index, slug, sheet, user_id)


async def _submit_locked(
    database: Database,
    index: VaultIndex,
    slug: str,
    sheet: SheetNote,
    user_id: str,
) -> None:
    root = _root(index)
    await _check_submittable(database, slug, sheet, user_id)
    path = root / sheet.path
    rewrite = _rewrite(
        path,
        {},
        _backups(database, slug),
        sheet.id,
        frozenset({REVIEW_NOTE_KEY}),
    )
    try:
        async with database.transaction() as connection:
            await _update_sheet(connection, sheet.path, rewrite, PENDING)
            await _insert_approval(connection, slug, sheet, user_id)
    except sqlite3.IntegrityError as failure:
        _restore(path, rewrite)
        if PENDING_APPROVAL_COLUMNS in str(failure):
            raise NotSubmittable("the sheet is already queued") from failure
        raise StorageFailed("approval storage failed") from failure
    except BaseException as failure:
        _restore(path, rewrite)
        if isinstance(failure, StorageFailed):
            raise
        if isinstance(failure, Exception):
            raise StorageFailed("approval storage failed") from failure
        raise


async def _check_submittable(
    database: Database, slug: str, sheet: SheetNote, user_id: str
) -> None:
    if await _sheet_owner(database, sheet) != user_id:
        raise NotOwner("only the sheet owner may submit")
    if sheet.status != PENDING:
        raise NotSubmittable("the sheet is not pending")
    queued = await database.fetchone(
        "SELECT 1 FROM approvals "
        "WHERE campaign_slug = ? AND sheet_path = ? AND status = 'pending'",
        (slug, sheet.path),
    )
    if queued is not None:
        raise NotSubmittable("the sheet is already queued")


def mirror_character_status(
    database: Database,
    index: VaultIndex,
    *,
    slug: str,
    character_id: str | None,
    status: str,
) -> StatusMirror | None:
    character = _managed_character(index, slug, character_id)
    if character is None or index.root is None:
        return None
    path = index.root / character.path
    if character_notes.review_status(path) == status:
        return None
    try:
        rewrite = character_notes.set_status(
            path, status, _backups(database, slug), character.id
        )
    except (OSError, ValueError) as failure:
        raise VaultWriteFailed("character write failed") from failure
    return StatusMirror(path=path, previous_text=rewrite.previous_text)


def revert_status_mirror(mirror: StatusMirror) -> None:
    try:
        sheet_write.restore_sheet(mirror.path, mirror.previous_text)
    except OSError as failure:
        logger.error(f"Could not revert {mirror.path}: {failure}")


def _managed_character(index: VaultIndex, slug: str, character_id: str | None):
    if character_id is None or not character_id.startswith("chr_"):
        return None
    return index.campaign(slug).characters.get(character_id)


async def _sheet_owner(database: Database, sheet: SheetNote) -> str | None:
    row = await database.fetchone(
        "SELECT owner_id FROM sheet_files WHERE path = ?", (sheet.path,)
    )
    if row is not None and row["owner_id"]:
        return row["owner_id"]
    return sheet.owner


def _character_name(row, characters) -> str:
    character = characters.get(row["character_id"])
    if character is not None:
        return character.name
    return PurePosixPath(row["sheet_path"]).stem


async def _approve(
    database: Database,
    root: Path,
    index: VaultIndex,
    slug: str,
    row,
    sheet: SheetNote,
    actor_id: str,
) -> None:
    character = index.campaign(slug).characters.get(row["character_id"])
    if character is None:
        raise VaultWriteFailed("character note not found")
    backups = _backups(database, slug)
    sheet_rewrite = _rewrite(
        root / sheet.path, _status(ACTIVE), backups, sheet.id
    )
    try:
        character_rewrite = _rewrite(
            root / character.path, _status(ACTIVE), backups, character.id
        )
    except BaseException as failure:
        _restore(root / sheet.path, sheet_rewrite)
        raise VaultWriteFailed("character write failed") from failure
    try:
        async with database.transaction() as connection:
            await _update_sheet(connection, sheet.path, sheet_rewrite, ACTIVE)
            await _close(connection, row["id"], "approved", "", actor_id)
    except BaseException as failure:
        _restore(root / sheet.path, sheet_rewrite)
        _restore(root / character.path, character_rewrite)
        if isinstance(failure, StorageFailed):
            raise
        if isinstance(failure, Exception):
            raise StorageFailed("approval storage failed") from failure
        raise


async def _reject(
    database: Database,
    root: Path,
    slug: str,
    row,
    sheet: SheetNote,
    note: str,
    actor_id: str,
) -> None:
    if not note:
        raise InvalidRequest("a rejection needs a note")
    path = root / sheet.path
    rewrite = _rewrite(
        path, {REVIEW_NOTE_KEY: note}, _backups(database, slug), sheet.id
    )
    try:
        async with database.transaction() as connection:
            await _update_sheet(connection, sheet.path, rewrite, PENDING)
            await _close(connection, row["id"], "rejected", note, actor_id)
    except BaseException as failure:
        _restore(path, rewrite)
        if isinstance(failure, StorageFailed):
            raise
        if isinstance(failure, Exception):
            raise StorageFailed("approval storage failed") from failure
        raise


async def _close(
    connection,
    approval_id: str,
    status: str,
    note: str,
    actor_id: str,
) -> None:
    cursor = await connection.execute(
        "UPDATE approvals SET status = ?, note = ?, decided_by = ?, "
        "decided_at = ? WHERE id = ? AND status = 'pending'",
        (status, note, actor_id, int(time.time()), approval_id),
    )
    if cursor.rowcount != 1:
        raise ApprovalNotFound("approval not found")


async def _update_sheet(
    connection, path: str, rewrite: NoteRewrite, status: str
) -> None:
    cursor = await connection.execute(
        "UPDATE sheet_files SET rev = ?, hash = ?, last_text = ?, "
        "base_json = ?, status = ?, updated_at = ? WHERE path = ?",
        (
            rewrite.rev,
            sha256_text(rewrite.text),
            rewrite.text,
            sheet_store.base_state(rewrite.text),
            status,
            int(time.time()),
            path,
        ),
    )
    if cursor.rowcount != 1:
        raise StorageFailed("the sheet row is missing")


async def _insert_approval(
    connection, slug: str, sheet: SheetNote, user_id: str
) -> None:
    await connection.execute(
        "INSERT INTO approvals ("
        "id, campaign_slug, sheet_path, sheet_id, character_id, "
        "status, note, requested_by, requested_at"
        ") VALUES (?, ?, ?, ?, ?, 'pending', '', ?, ?)",
        (
            new_id("apr"),
            slug,
            sheet.path,
            sheet.id,
            sheet.character,
            user_id,
            int(time.time()),
        ),
    )


async def _record_creation(
    database: Database,
    *,
    slug: str,
    sheet_path: str | None,
    character_id: str,
    sheet_id: str | None,
    sheet_body: str | None,
    status: str,
    owner: str | None,
    display_name: str | None,
    requested_by: str,
    queue: bool,
) -> None:
    now = int(time.time())
    async with database.transaction() as connection:
        if owner is not None:
            await connection.execute(
                "INSERT OR IGNORE INTO members ("
                "campaign_slug, user_id, display_name, joined_at"
                ") VALUES (?, ?, ?, ?)",
                (slug, owner, display_name, now),
            )
        if sheet_body is None or sheet_path is None or sheet_id is None:
            return
        await connection.execute(
            "INSERT INTO sheet_files ("
            "path, harpi_id, campaign, rev, hash, last_text, base_json, "
            "status, owner_id, state, updated_at"
            ") VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, 'ok', ?)",
            (
                sheet_path,
                sheet_id,
                slug,
                sha256_text(sheet_body),
                sheet_body,
                sheet_store.base_state(sheet_body),
                status,
                owner,
                now,
            ),
        )
        if not queue:
            return
        await connection.execute(
            "INSERT INTO approvals ("
            "id, campaign_slug, sheet_path, sheet_id, character_id, "
            "status, note, requested_by, requested_at"
            ") VALUES (?, ?, ?, ?, ?, 'pending', '', ?, ?)",
            (
                new_id("apr"),
                slug,
                sheet_path,
                sheet_id,
                character_id,
                requested_by,
                now,
            ),
        )


def _refuse_player_skip(narrator: bool, with_sheet: bool | None) -> None:
    if not narrator and with_sheet is False:
        raise InvalidRequest("a player creates the character and the sheet")


def _named_lock(scope: str, key: str) -> asyncio.Lock:
    token = (id(asyncio.get_running_loop()), f"{scope}:{key}")
    lock = _LOCKS.get(token)
    if lock is None:
        lock = asyncio.Lock()
        _LOCKS[token] = lock
    return lock


async def _refuse_second_pair(
    database: Database, slug: str, user_id: str
) -> None:
    row = await database.fetchone(
        "SELECT 1 FROM sheet_files WHERE campaign = ? AND owner_id = ? "
        "AND status IN ('pendente', 'ativo') LIMIT 1",
        (slug, user_id),
    )
    if row is not None:
        raise SheetAlreadyExists(
            "the user already has a pending or active sheet"
        )


def _root(index: VaultIndex) -> Path:
    if index.root is None:
        raise VaultWriteFailed("vault unavailable")
    return index.root


def _create_file(path: Path, text: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        create_exclusive(path, text)
    except FileExistsError as failure:
        raise NameTaken("a note with this name already exists") from failure
    except OSError as failure:
        raise VaultWriteFailed("vault write failed") from failure


def _discard(root: Path, *paths: str | None) -> None:
    for relative in paths:
        if relative is None:
            continue
        try:
            (root / relative).unlink(missing_ok=True)
        except OSError as failure:
            logger.warning(f"Could not discard {relative}: {failure}")


def _rewrite(
    path: Path,
    updates: dict[str, str],
    backups: Path,
    backup_id: str,
    drops: frozenset[str] = frozenset(),
) -> NoteRewrite:
    try:
        return character_notes.rewrite_frontmatter(
            path, updates, backups, backup_id, drops
        )
    except (OSError, ValueError) as failure:
        raise VaultWriteFailed("vault write failed") from failure


def _restore(path: Path, rewrite: NoteRewrite) -> None:
    try:
        sheet_write.restore_sheet(path, rewrite.previous_text)
    except OSError as failure:
        logger.error(f"Could not restore {path}: {failure}")


def _backups(database: Database, slug: str) -> Path:
    return sheet_store.backup_root(database) / sheet_write.safe_component(slug)


def _status(status: str) -> dict[str, str]:
    return {"harpi-status": status}


def _sheet_at(index: VaultIndex, slug: str, path: str) -> SheetNote | None:
    return next(
        (sheet for sheet in index.campaign(slug).sheets if sheet.path == path),
        None,
    )


def _sheet_by_id(
    index: VaultIndex, slug: str, sheet_id: str
) -> SheetNote | None:
    return next(
        (
            sheet
            for sheet in index.campaign(slug).sheets
            if sheet.id == sheet_id
        ),
        None,
    )
