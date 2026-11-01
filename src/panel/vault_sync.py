from __future__ import annotations

import asyncio
import hashlib
import time
from collections import Counter
from collections.abc import Callable, Iterable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from loguru import logger
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from watchdog.events import (
    EVENT_TYPE_CLOSED_NO_WRITE,
    EVENT_TYPE_OPENED,
    FileSystemEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

from src.panel import sheet_store, sheet_write, vault_index
from src.panel.sheets import decode_text, load_sheet, sha256_text
from src.panel.vault import Vault
from src.panel.vault_index import CAMPAIGN_ROOT, NOTE_FOLDERS, SHEETS_FOLDER
from src.storage.database import Database

DEBOUNCE_SECONDS = 0.5
SCAN_INTERVAL_SECONDS = 60
MAX_NOTE_BYTES = 1024 * 1024
MAX_ID_LENGTH = 128
CONFIG_NAME = "config.md"
OK = "ok"
MISSING = "ausente"
INVALID = "invalido"
UNKNOWN = "desconhecido"
SHEET_STATUSES = frozenset({"pendente", "ativo", "arquivado"})
IGNORED_EVENTS = frozenset({EVENT_TYPE_OPENED, EVENT_TYPE_CLOSED_NO_WRITE})
UPSERT_ROW = (
    "INSERT INTO sheet_files ("
    "path, harpi_id, campaign, rev, hash, last_text, base_json, "
    "status, owner_id, state, updated_at"
    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
    "ON CONFLICT(path) DO UPDATE SET "
    "harpi_id = excluded.harpi_id, rev = excluded.rev, "
    "hash = excluded.hash, last_text = excluded.last_text, "
    "base_json = excluded.base_json, status = excluded.status, "
    "owner_id = excluded.owner_id, state = excluded.state, "
    "updated_at = excluded.updated_at"
)


@dataclass(frozen=True, slots=True)
class Stamp:
    mtime_ns: int
    size: int


@dataclass(frozen=True, slots=True)
class Listing:
    stamps: dict[str, Stamp]
    campaigns: frozenset[str]


@dataclass(frozen=True, slots=True)
class SheetFile:
    path: str
    harpi_id: str | None
    text: str | None
    digest: str
    valid: bool
    status: str | None
    owner: str | None
    rev: int
    base_json: str | None


@dataclass(frozen=True, slots=True)
class Row:
    path: str
    harpi_id: str
    hash: str
    last_text: str
    base_json: str
    rev: int
    status: str
    owner: str | None
    state: str


@dataclass(frozen=True, slots=True)
class CampaignPlan:
    writes: tuple[Row, ...]
    renames: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class Matched:
    row: Row | None
    state: str
    moved_from: str | None = None
    duplicate_of: str | None = None


def is_note(relative: str) -> bool:
    name = PurePosixPath(relative).name
    if vault_index.skipped(name):
        return False
    return vault_index.locate_note(relative) is not None


def list_vault(root: Path | None) -> Listing | None:
    if root is None or not root.is_dir():
        return None
    campaigns = root.joinpath(*CAMPAIGN_ROOT)
    try:
        entries = sorted(campaigns.iterdir())
    except OSError:
        return None
    found: dict[str, Stamp] = {}
    slugs: set[str] = set()
    for campaign in entries:
        if vault_index.skipped(campaign.name) or not campaign.is_dir():
            continue
        try:
            add_campaign(root, campaign.name, found)
        except OSError:
            return None
        slugs.add(campaign.name)
    return Listing(found, frozenset(slugs))


def add_campaign(root: Path, slug: str, found: dict[str, Stamp]) -> None:
    base = PurePosixPath(*CAMPAIGN_ROOT, slug)
    add_stamp(root, f"{base.as_posix()}/{CONFIG_NAME}", found)
    for folder in NOTE_FOLDERS:
        add_folder_stamps(root, base, folder, found)


def add_folder_stamps(
    root: Path, base: PurePosixPath, folder: str, found: dict[str, Stamp]
) -> None:
    directory = root / base / folder
    try:
        entries = sorted(directory.iterdir())
    except FileNotFoundError:
        return
    for entry in entries:
        relative = f"{base.as_posix()}/{folder}/{entry.name}"
        if is_note(relative):
            add_stamp(root, relative, found)


def add_stamp(root: Path, relative: str, found: dict[str, Stamp]) -> None:
    stamp = stamp_of(root / relative)
    if stamp is not None:
        found[relative] = stamp


def stamp_of(path: Path) -> Stamp | None:
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    return Stamp(mtime_ns=stat.st_mtime_ns, size=stat.st_size)


def changed_paths(
    previous: dict[str, Stamp], current: dict[str, Stamp]
) -> frozenset[str]:
    changed = {
        path
        for path, stamp in current.items()
        if differs(previous.get(path), stamp)
    }
    changed.update(previous.keys() - current.keys())
    return frozenset(changed)


def differs(previous: Stamp | None, current: Stamp) -> bool:
    return previous is None or not same_stamp(previous, current)


def same_stamp(left: Stamp, right: Stamp) -> bool:
    return left.mtime_ns == right.mtime_ns and left.size == right.size


def sheet_campaigns(paths: Iterable[str]) -> set[str]:
    found: set[str] = set()
    for path in paths:
        located = vault_index.locate_note(path)
        if located is not None and located[1] == SHEETS_FOLDER:
            found.add(located[0])
    return found


def read_sheet_file(root: Path, relative: str) -> SheetFile | None:
    path = root / relative
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return None
    if size > MAX_NOTE_BYTES:
        return undecodable(relative, b"")
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return None
    if len(raw) > MAX_NOTE_BYTES:
        return undecodable(relative, b"")
    return decoded_sheet(relative, raw)


def decoded_sheet(relative: str, raw: bytes) -> SheetFile:
    try:
        text = decode_text(raw)
    except UnicodeDecodeError:
        return undecodable(relative, raw)
    fields = frontmatter(text)
    loaded = load_sheet(text)
    valid = fields is not None and loaded.document is not None
    return SheetFile(
        path=relative,
        harpi_id=identity(fields),
        text=text,
        digest=sha256_text(text),
        valid=valid,
        status=sheet_status(field(fields, "harpi-status")),
        owner=field(fields, "harpi-owner"),
        rev=revision(fields),
        base_json=sheet_store.base_state(text) if valid else None,
    )


def frontmatter(text: str) -> dict[str, object] | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end = next(
        (
            index
            for index in range(1, len(lines))
            if lines[index].strip() == "---"
        ),
        None,
    )
    if end is None:
        return None
    try:
        loaded = YAML(typ="safe").load("\n".join(lines[1:end]))
    except YAMLError:
        return None
    return loaded if isinstance(loaded, dict) else None


def field(fields: dict[str, object] | None, key: str) -> str | None:
    if fields is None:
        return None
    value = fields.get(key)
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def identity(fields: dict[str, object] | None) -> str | None:
    value = field(fields, "harpi-id")
    if value is None or len(value) > MAX_ID_LENGTH:
        return None
    return None if any(char.isspace() for char in value) else value


def revision(fields: dict[str, object] | None) -> int:
    value = None if fields is None else fields.get("harpi-rev")
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def undecodable(relative: str, raw: bytes) -> SheetFile:
    return SheetFile(
        path=relative,
        harpi_id=None,
        text=None,
        digest=hashlib.sha256(raw).hexdigest() if raw else "",
        valid=False,
        status=None,
        owner=None,
        rev=0,
        base_json=None,
    )


def sheet_status(value: str | None) -> str | None:
    return value if value in SHEET_STATUSES else None


def read_sheets(root: Path, campaign: str) -> list[SheetFile] | None:
    folder = PurePosixPath(*CAMPAIGN_ROOT, campaign, SHEETS_FOLDER)
    try:
        entries = sorted((root / folder).iterdir())
    except FileNotFoundError:
        return []
    except OSError:
        return None
    files: list[SheetFile] = []
    for entry in entries:
        relative = f"{folder.as_posix()}/{entry.name}"
        if not is_note(relative):
            continue
        try:
            file = read_sheet_file(root, relative)
        except OSError:
            return None
        if file is not None:
            files.append(file)
    return files


async def load_rows(database: Database, campaign: str) -> list[Row]:
    rows = await database.fetchall(
        "SELECT path, harpi_id, hash, last_text, base_json, rev, status, "
        "owner_id, state FROM sheet_files WHERE campaign = ?",
        (campaign,),
    )
    return [
        Row(
            path=row["path"],
            harpi_id=row["harpi_id"],
            hash=row["hash"],
            last_text=row["last_text"],
            base_json=row["base_json"],
            rev=row["rev"],
            status=row["status"],
            owner=row["owner_id"],
            state=row["state"],
        )
        for row in rows
    ]


def group_rows(rows: Iterable[Row]) -> dict[str, tuple[Row, ...]]:
    grouped: dict[str, list[Row]] = {}
    for row in rows:
        grouped.setdefault(row.harpi_id, []).append(row)
    return {key: tuple(value) for key, value in grouped.items()}


def unique_identity(counts: Counter[str], file: SheetFile) -> bool:
    return file.harpi_id is not None and counts[file.harpi_id] == 1


def match_file(
    file: SheetFile,
    by_path: dict[str, Row],
    by_id: dict[str, tuple[Row, ...]],
    counts: Counter[str],
    disk: set[str],
) -> Matched:
    row = by_path.get(file.path)
    if not file.valid:
        return Matched(row, INVALID)
    if not unique_identity(counts, file):
        return Matched(row, UNKNOWN)
    known = by_id.get(file.harpi_id or "", ())
    return match_known(file, row, known, disk)


def match_known(
    file: SheetFile,
    row: Row | None,
    known: tuple[Row, ...],
    disk: set[str],
) -> Matched:
    if row is not None and row.harpi_id == file.harpi_id:
        return Matched(row, OK)
    if len(known) != 1:
        return Matched(row, UNKNOWN)
    target = known[0]
    if target.path in disk:
        return Matched(row, UNKNOWN)
    if row is not None:
        return Matched(row, UNKNOWN, duplicate_of=target.path)
    return Matched(target, OK, moved_from=target.path)


def plan_campaign(files: list[SheetFile], rows: list[Row]) -> CampaignPlan:
    disk = {file.path for file in files}
    matches = match_files(files, rows, disk)
    writes = {row.path: row for row in planned_rows(matches)}
    duplicates = duplicate_rows(matches, rows)
    for row in duplicates:
        writes.setdefault(row.path, row)
    renames = rename_pairs(matches)
    sources = {moved_from for moved_from, _ in renames}
    sources |= {row.path for row in duplicates}
    for row in rows:
        add_missing(row, writes, sources, disk)
    return CampaignPlan(tuple(writes.values()), renames)


def match_files(
    files: list[SheetFile], rows: list[Row], disk: set[str]
) -> list[tuple[SheetFile, Matched]]:
    by_path = {row.path: row for row in rows}
    by_id = group_rows(rows)
    counts = Counter(file_ids(files))
    return [
        (file, match_file(file, by_path, by_id, counts, disk))
        for file in files
    ]


def file_ids(files: list[SheetFile]) -> list[str]:
    return [file.harpi_id for file in files if file.harpi_id is not None]


def planned_rows(matches: list[tuple[SheetFile, Matched]]) -> list[Row]:
    rows = [plan_file(file, matched) for file, matched in matches]
    return [row for row in rows if row is not None]


def duplicate_rows(
    matches: list[tuple[SheetFile, Matched]], rows: list[Row]
) -> list[Row]:
    by_path = {row.path: row for row in rows}
    found: list[Row] = []
    for _, matched in matches:
        if matched.duplicate_of is None:
            continue
        row = by_path.get(matched.duplicate_of)
        changed = None if row is None else state_only(row, UNKNOWN)
        if changed is not None:
            found.append(changed)
    return found


def rename_pairs(
    matches: list[tuple[SheetFile, Matched]],
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (matched.moved_from, file.path)
        for file, matched in matches
        if matched.moved_from is not None
    )


def add_missing(
    row: Row, writes: dict[str, Row], sources: set[str], disk: set[str]
) -> None:
    if row.path in sources or row.path in disk:
        return
    missing = state_only(row, MISSING)
    if missing is not None:
        writes[row.path] = missing


def plan_file(file: SheetFile, matched: Matched) -> Row | None:
    if matched.duplicate_of is not None:
        return (
            None if matched.row is None else state_only(matched.row, UNKNOWN)
        )
    if matched.row is None:
        return inserted_row(matched.state, file)
    if matched.state == OK:
        return accepted(file, matched.row)
    return state_only(matched.row, matched.state)


def accepted(file: SheetFile, row: Row) -> Row | None:
    if is_echo(file, row):
        return None
    return Row(
        path=file.path,
        harpi_id=preferred(file.harpi_id, row.harpi_id),
        hash=file.digest,
        last_text=preferred(file.text, row.last_text),
        base_json=preferred(file.base_json, row.base_json),
        rev=row.rev,
        status=accepted_status(row, file),
        owner=row.owner,
        state=OK,
    )


def is_echo(file: SheetFile, row: Row) -> bool:
    return (
        row.path == file.path and row.state == OK and row.hash == file.digest
    )


def accepted_status(row: Row, file: SheetFile) -> str:
    if file.status is None or file.status == row.status:
        return row.status
    legal = (row.status, file.status) in sheet_write.LEGAL_TRANSITIONS
    return file.status if legal else row.status


def preferred(value: str | None, fallback: str) -> str:
    return fallback if value is None else value


def state_only(row: Row, state: str) -> Row | None:
    if row.state == state:
        return None
    return Row(
        path=row.path,
        harpi_id=row.harpi_id,
        hash=row.hash,
        last_text=row.last_text,
        base_json=row.base_json,
        rev=row.rev,
        status=row.status,
        owner=row.owner,
        state=state,
    )


def inserted_row(state: str, file: SheetFile) -> Row:
    return Row(
        path=file.path,
        harpi_id=file.harpi_id or file.path,
        hash=file.digest,
        last_text=file.text or "",
        base_json=file.base_json or "{}",
        rev=file.rev,
        status=file.status or "pendente",
        owner=None,
        state=state,
    )


async def apply_plan(
    database: Database, campaign: str, plan: CampaignPlan, now: int
) -> None:
    if not plan.writes and not plan.renames:
        return
    async with database.transaction() as connection:
        await connection.execute("PRAGMA defer_foreign_keys = ON")
        for moved_from, path in plan.renames:
            await connection.execute(
                "UPDATE sheet_files SET path = ? WHERE path = ?",
                (path, moved_from),
            )
            await connection.execute(
                "UPDATE sheet_conflicts SET path = ? WHERE path = ?",
                (path, moved_from),
            )
        for row in plan.writes:
            await connection.execute(
                UPSERT_ROW,
                (
                    row.path,
                    row.harpi_id,
                    campaign,
                    row.rev,
                    row.hash,
                    row.last_text,
                    row.base_json,
                    row.status,
                    row.owner,
                    row.state,
                    now,
                ),
            )


async def stored_campaigns(database: Database) -> set[str]:
    rows = await database.fetchall("SELECT DISTINCT campaign FROM sheet_files")
    return {row["campaign"] for row in rows}


async def known_campaigns(database: Database, campaigns: set[str]) -> set[str]:
    if not campaigns:
        return set()
    ordered = sorted(campaigns)
    placeholders = ", ".join("?" for _ in ordered)
    rows = await database.fetchall(
        f"SELECT slug FROM campaigns WHERE slug IN ({placeholders})",
        tuple(ordered),
    )
    return {row["slug"] for row in rows}


async def reconcile(
    database: Database, root: Path | None, campaigns: set[str]
) -> None:
    if root is None:
        return
    for campaign in sorted(await known_campaigns(database, campaigns)):
        files = await asyncio.to_thread(read_sheets, root, campaign)
        if files is None:
            logger.error(f"Vault campaign unreadable: {campaign}")
            continue
        rows = await load_rows(database, campaign)
        plan = plan_campaign(files, rows)
        await apply_plan(database, campaign, plan, int(time.time()))


class Debouncer:
    def __init__(self, delay: float = DEBOUNCE_SECONDS) -> None:
        self._delay = delay
        self._pending: dict[str, float] = {}
        self._ready = asyncio.Event()

    def notify(self, path: str) -> None:
        self._pending[path] = time.monotonic() + self._delay
        self._ready.set()

    async def next_batch(self) -> frozenset[str]:
        while True:
            await self._ready.wait()
            self._ready.clear()
            await self._wait_for_due()
            due = self._take_due()
            if due:
                return due
            if self._pending:
                self._ready.set()

    async def _wait_for_due(self) -> None:
        deadline = self._earliest()
        if deadline is None:
            return
        delay = deadline - time.monotonic()
        if delay > 0:
            await asyncio.sleep(delay)

    def _earliest(self) -> float | None:
        if not self._pending:
            return None
        return min(self._pending.values())

    def _take_due(self) -> frozenset[str]:
        now = time.monotonic()
        due = frozenset(
            path for path, deadline in self._pending.items() if deadline <= now
        )
        for path in due:
            del self._pending[path]
        return due


class CampaignObserver(FileSystemEventHandler):
    def __init__(self, root: Path, sink: Callable[[str], None]) -> None:
        self._root = root.resolve()
        self._sink = sink

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory or event.event_type in IGNORED_EVENTS:
            return
        for raw in (event.src_path, getattr(event, "dest_path", "")):
            relative = self._relative(raw)
            if relative is not None and is_note(relative):
                self._sink(relative)

    def _relative(self, raw: str | bytes) -> str | None:
        text = (
            raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
        )
        if not text:
            return None
        try:
            return Path(text).resolve().relative_to(self._root).as_posix()
        except (OSError, ValueError):
            return None


def campaign_observer(
    vault: Vault, sink: Callable[[str], None]
) -> BaseObserver | None:
    root = vault.root
    if root is None:
        return None
    campaigns = root.joinpath(*CAMPAIGN_ROOT)
    if not campaigns.is_dir():
        return None
    observer: BaseObserver = Observer()
    try:
        observer.schedule(
            CampaignObserver(root, sink), str(campaigns), recursive=True
        )
        observer.start()
    except OSError as failure:
        logger.error(f"Vault observer unavailable: {failure}")
        return None
    return observer


class VaultSync:
    def __init__(
        self,
        vault: Vault,
        database: Database | None = None,
        *,
        debounce: float = DEBOUNCE_SECONDS,
        interval: float = SCAN_INTERVAL_SECONDS,
    ) -> None:
        self.vault = vault
        self.database = database
        self.debounce = debounce
        self.interval = interval
        self.scanned = asyncio.Event()
        self._stamps: dict[str, Stamp] = {}
        self._primed = False
        self._lock = asyncio.Lock()

    async def scan(self) -> frozenset[str]:
        async with self._lock:
            try:
                return await self._scan_locked()
            finally:
                self.scanned.set()

    async def _scan_locked(self) -> frozenset[str]:
        listing = await asyncio.to_thread(list_vault, self.vault.root)
        if listing is None:
            logger.warning("Vault scan skipped: vault is not listable")
            return frozenset()
        if not await self._campaigns_listed(listing.campaigns):
            logger.warning(
                "Vault scan skipped: a campaign folder is unreadable"
            )
            return frozenset()
        changed = changed_paths(self._stamps, listing.stamps)
        first = not self._primed
        if not changed and not first:
            self._stamps = listing.stamps
            return changed
        try:
            await vault_index.refresh_once(self.vault)
            await self._reconcile(changed, first)
        except Exception as failure:
            logger.opt(exception=True).error(f"Vault sync failed: {failure}")
            return changed
        self._stamps = listing.stamps
        self._primed = True
        return changed

    async def _campaigns_listed(self, folders: frozenset[str]) -> bool:
        if self.database is None:
            return True
        return await stored_campaigns(self.database) <= folders

    async def _reconcile(self, changed: frozenset[str], first: bool) -> None:
        if self.database is None:
            return
        campaigns = sheet_campaigns(changed)
        if first:
            campaigns |= await stored_campaigns(self.database)
        await reconcile(self.database, self.vault.root, campaigns)


class Watcher:
    def __init__(
        self,
        sync: VaultSync,
        debouncer: Debouncer,
        observer_factory: Callable[
            [Vault, Callable[[str], None]], BaseObserver | None
        ],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._sync = sync
        self._debouncer = debouncer
        self._factory = observer_factory
        self._loop = loop
        self._observer: BaseObserver | None = None

    def attach(self) -> None:
        observer = self._observer
        if observer is not None and observer.is_alive():
            return
        self._observer = self._factory(
            self._sync.vault, deliver(self._loop, self._debouncer)
        )

    async def consume(self) -> None:
        while True:
            batch = await self._debouncer.next_batch()
            if batch:
                await self._sync.scan()
                self.attach()

    async def tick(self) -> None:
        while True:
            await asyncio.sleep(self._sync.interval)
            await self._sync.scan()
            self.attach()

    async def stop(self) -> None:
        observer = self._observer
        self._observer = None
        if observer is not None:
            await asyncio.to_thread(stop_observer, observer)


def deliver(
    loop: asyncio.AbstractEventLoop, debouncer: Debouncer
) -> Callable[[str], None]:
    def send(path: str) -> None:
        loop.call_soon_threadsafe(debouncer.notify, path)

    return send


async def run_watch(
    sync: VaultSync,
    *,
    observer_factory: Callable[
        [Vault, Callable[[str], None]], BaseObserver | None
    ] = campaign_observer,
) -> None:
    loop = asyncio.get_running_loop()
    watcher = Watcher(sync, Debouncer(sync.debounce), observer_factory, loop)
    try:
        await sync.scan()
        watcher.attach()
        await asyncio.gather(watcher.consume(), watcher.tick())
    except Exception as failure:
        logger.opt(exception=True).error(f"Vault watch stopped: {failure}")
    finally:
        await watcher.stop()


def stop_observer(observer: BaseObserver | None) -> None:
    if observer is None:
        return
    observer.stop()
    observer.join()


def start_sync(
    vault: Vault, database: Database | None = None
) -> asyncio.Task[None]:
    return asyncio.create_task(
        run_watch(VaultSync(vault, database)), name="harpi-vault-sync"
    )


async def stop_sync(task: asyncio.Task[None]) -> None:
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
