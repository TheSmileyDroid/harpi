from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from watchdog.events import (
    DirModifiedEvent,
    FileClosedNoWriteEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileOpenedEvent,
)

from src.panel import notes, sheet_store, vault_sync, vault_index
from src.panel.sheets import sha256_text
from src.panel.vault import Vault
from src.panel.vault_index import VaultIndex
from src.storage.database import Database
from src.storage.seed import paratheos

SLUG = "paratheos"
CAMPAIGN = f"Harpi/Campaigns/{SLUG}"
ANA = f"{CAMPAIGN}/sheets/Ana.md"
NARRATOR = "100"
GUILD = "1"


def sheet(
    identifier: str = "sht_ana",
    *,
    refresh: int = 7,
    status: str = "ativo",
    owner: str = "555",
) -> str:
    return (
        "---\n"
        "tipo: ficha\n"
        f"harpi-id: {identifier}\n"
        "harpi-campanha: paratheos\n"
        "harpi-character-id: chr_ana\n"
        f"harpi-owner: '{owner}'\n"
        f"harpi-status: {status}\n"
        "harpi-rev: 3\n"
        "---\n\n## História\n\nAntes.\n\n"
        "```harpi-sheet\n"
        f"refresh: {refresh}\n"
        "```\n\n## Anotações\n\nFim.\n"
    )


def write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


async def store_row(
    database: Database,
    path: str,
    text: str,
    *,
    state: str = "ok",
    updated_at: int = 1,
) -> None:
    fields, _ = notes.split_frontmatter(text)
    await database.execute(
        "INSERT INTO sheet_files ("
        "path, harpi_id, campaign, rev, hash, last_text, base_json, "
        "status, owner_id, state, updated_at"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            path,
            notes.field_front(fields, "harpi-id"),
            SLUG,
            notes.revision(fields),
            sha256_text(text),
            text,
            sheet_store.base_state(text),
            notes.field_front(fields, "harpi-status"),
            notes.field_front(fields, "harpi-owner"),
            state,
            updated_at,
        ),
    )


async def row(database: Database, path: str):
    return await database.fetchone(
        "SELECT * FROM sheet_files WHERE path = ?", (path,)
    )


async def rows(database: Database) -> list:
    return await database.fetchall("SELECT * FROM sheet_files ORDER BY path")


@pytest.fixture
async def world(tmp_path: Path):
    root = tmp_path / "vault"
    root.mkdir()
    database = Database(
        tmp_path / "panel.db", campaign=paratheos(NARRATOR, GUILD)
    )
    await database.open()
    yield SimpleNamespace(
        root=root,
        database=database,
        sync=vault_sync.VaultSync(Vault(root=root), database),
    )
    vault_index.configure(VaultIndex())
    await database.close()


def test_the_watcher_takes_notes_only():
    assert vault_sync.is_note(f"{CAMPAIGN}/characters/Ana.md") is True
    assert vault_sync.is_note(f"{CAMPAIGN}/sheets/Ana.md") is True
    assert vault_sync.is_note(f"{CAMPAIGN}/config.md") is False
    for relative in (
        f"{CAMPAIGN}/scenes/cena.json",
        f"{CAMPAIGN}/tables/mesa.json",
        f"{CAMPAIGN}/assets/mapa.svg",
        f"{CAMPAIGN}/sheets/.hidden.md",
        f"{CAMPAIGN}/sheets/Ana.md.tmp",
        f"{CAMPAIGN}/sheets/~syncthing~Ana.md",
        f"{CAMPAIGN}/sheets/Ana.sync-conflict-20260101.md",
        "Harpi/Other/Ana.md",
        "Harpi/Campaigns/paratheos/sheets/Ana.txt",
    ):
        assert vault_sync.is_note(relative) is False


def test_the_stamps_skip_everything_outside_the_allowlist(tmp_path: Path):
    write(tmp_path, f"{CAMPAIGN}/sheets/Ana.md", sheet())
    write(tmp_path, f"{CAMPAIGN}/config.md", "```harpi-campaign\n```\n")
    for relative in (
        f"{CAMPAIGN}/scenes/cena.json",
        f"{CAMPAIGN}/tables/mesa.json",
        f"{CAMPAIGN}/sheets/Ana.md.tmp",
        f"{CAMPAIGN}/sheets/Ana.sync-conflict-20260101.md",
        f"{CAMPAIGN}/sheets/~syncthing~Ana.md",
        f"{CAMPAIGN}/.obsidian/workspace.md",
    ):
        write(tmp_path, relative, "x")
    write(tmp_path, "Harpi/Campaigns/loose.txt", "x")
    (tmp_path / "Harpi/Campaigns/.hidden").mkdir()

    listing = vault_sync.list_vault(tmp_path)

    assert listing is not None
    assert set(listing.stamps) == {ANA, f"{CAMPAIGN}/config.md"}
    assert listing.campaigns == frozenset({SLUG})


async def test_an_external_edit_is_accepted_and_appears_in_the_sheet(world):
    before = sheet(refresh=7)
    write(world.root, ANA, before)
    await store_row(world.database, ANA, before)
    after = sheet(refresh=9)
    write(world.root, ANA, after)

    changed = await world.sync.scan()

    assert changed == frozenset({ANA})
    stored = await row(world.database, ANA)
    assert stored["state"] == "ok"
    assert stored["hash"] == sha256_text(after)
    assert stored["last_text"] == after
    assert stored["rev"] == 3
    index = vault_index.configured()
    document = index.campaign(SLUG).sheets[0].loaded.document
    assert document is not None
    assert document["refresh"] == 9


async def test_the_app_echo_is_discarded_by_equal_hash(world):
    text = sheet()
    write(world.root, ANA, text)
    await store_row(world.database, ANA, text, updated_at=1)

    await world.sync.scan()

    stored = await row(world.database, ANA)
    assert stored["updated_at"] == 1
    assert stored["hash"] == sha256_text(text)
    assert await world.sync.scan() == frozenset()


async def test_a_deleted_sheet_turns_ausente_and_is_never_restored(world):
    text = sheet()
    path = write(world.root, ANA, text)
    await store_row(world.database, ANA, text)

    path.unlink()
    await world.sync.scan()

    stored = await row(world.database, ANA)
    assert stored["state"] == "ausente"
    assert stored["last_text"] == text
    assert not path.exists()


async def test_a_rename_by_the_same_id_only_changes_the_path(world):
    text = sheet()
    write(world.root, ANA, text)
    await store_row(world.database, ANA, text)
    await world.sync.scan()
    moved = f"{CAMPAIGN}/sheets/Ana PC.md"
    (world.root / ANA).rename(world.root / moved)

    await world.sync.scan()

    stored = await row(world.database, moved)
    assert stored is not None
    assert stored["harpi_id"] == "sht_ana"
    assert stored["state"] == "ok"
    assert stored["last_text"] == text
    assert await row(world.database, ANA) is None


async def test_a_hand_edited_id_becomes_ausente_plus_desconhecido(world):
    text = sheet()
    write(world.root, ANA, text)
    await store_row(world.database, ANA, text)
    await world.sync.scan()
    renamed = f"{CAMPAIGN}/sheets/Outra.md"
    (world.root / ANA).rename(world.root / renamed)
    write(world.root, renamed, sheet("sht_outra"))

    await world.sync.scan()

    old = await row(world.database, ANA)
    assert old["state"] == "ausente"
    new = await row(world.database, renamed)
    assert new["harpi_id"] == "sht_outra"
    assert new["state"] == "desconhecido"


async def test_an_in_place_id_edit_flags_the_row_as_desconhecido(world):
    text = sheet()
    write(world.root, ANA, text)
    await store_row(world.database, ANA, text)
    await world.sync.scan()

    write(world.root, ANA, sheet("sht_outra"))
    await world.sync.scan()

    stored = await row(world.database, ANA)
    assert stored["harpi_id"] == "sht_ana"
    assert stored["state"] == "desconhecido"
    assert stored["last_text"] == text

    write(world.root, ANA, text)
    await world.sync.scan()

    assert (await row(world.database, ANA))["state"] == "ok"


async def test_two_files_with_the_same_id_stay_untouched_and_flagged(world):
    text = sheet()
    write(world.root, ANA, text)
    await store_row(world.database, ANA, text)
    await world.sync.scan()
    copy = f"{CAMPAIGN}/sheets/Copia.md"
    copy_text = sheet(refresh=2)
    write(world.root, copy, copy_text)

    await world.sync.scan()

    first = await row(world.database, ANA)
    second = await row(world.database, copy)
    assert first["state"] == "desconhecido"
    assert second["state"] == "desconhecido"
    assert first["last_text"] == text
    assert (world.root / ANA).read_text(encoding="utf-8") == text
    assert (world.root / copy).read_text(encoding="utf-8") == copy_text


async def test_swapped_ids_are_flagged_instead_of_adopted(world):
    ana = sheet("sht_ana")
    bia = f"{CAMPAIGN}/sheets/Bia.md"
    bia_text = sheet("sht_bia", owner="556")
    write(world.root, ANA, ana)
    write(world.root, bia, bia_text)
    await store_row(world.database, ANA, ana)
    await store_row(world.database, bia, bia_text)
    await world.sync.scan()

    write(world.root, ANA, sheet("sht_bia"))
    write(world.root, bia, sheet("sht_ana"))
    await world.sync.scan()

    assert (await row(world.database, ANA))["state"] == "desconhecido"
    assert (await row(world.database, bia))["state"] == "desconhecido"


async def test_the_duplicate_clears_when_one_file_is_removed(world):
    text = sheet()
    write(world.root, ANA, text)
    await store_row(world.database, ANA, text)
    await world.sync.scan()
    copy = f"{CAMPAIGN}/sheets/Copia.md"
    write(world.root, copy, sheet(refresh=2))
    await world.sync.scan()

    (world.root / copy).unlink()
    await world.sync.scan()

    assert (await row(world.database, ANA))["state"] == "ok"
    assert (await row(world.database, copy))["state"] == "ausente"


async def test_a_missing_vault_root_never_marks_rows_ausente(world):
    text = sheet()
    write(world.root, ANA, text)
    await store_row(world.database, ANA, text)
    await world.sync.scan()

    shutil.rmtree(world.root)

    assert await world.sync.scan() == frozenset()
    assert (await row(world.database, ANA))["state"] == "ok"


async def test_a_rename_keeps_the_conflicts_of_the_sheet(world):
    text = sheet()
    write(world.root, ANA, text)
    await store_row(world.database, ANA, text)
    await world.sync.scan()
    await world.database.execute(
        "INSERT INTO sheet_conflicts ("
        "id, path, field_path, base, ours, theirs, created_at"
        ") VALUES ('cnf_1', ?, 'refresh', '1', '2', '3', 1)",
        (ANA,),
    )
    moved = f"{CAMPAIGN}/sheets/Ana PC.md"

    (world.root / ANA).rename(world.root / moved)
    await world.sync.scan()

    conflict = await world.database.fetchone(
        "SELECT path FROM sheet_conflicts WHERE id = 'cnf_1'"
    )
    assert conflict["path"] == moved
    assert await row(world.database, moved) is not None
    assert await row(world.database, ANA) is None


async def test_a_hand_edited_owner_is_ignored(world):
    text = sheet(owner="555")
    write(world.root, ANA, text)
    await store_row(world.database, ANA, text)
    await world.sync.scan()
    edited = sheet(owner="777", refresh=9)

    write(world.root, ANA, edited)
    await world.sync.scan()

    stored = await row(world.database, ANA)
    assert stored["owner_id"] == "555"
    assert stored["last_text"] == edited


async def test_a_hand_edited_status_follows_the_legal_transition(world):
    text = sheet(status="ativo")
    write(world.root, ANA, text)
    await store_row(world.database, ANA, text)
    await world.sync.scan()

    write(world.root, ANA, sheet(status="pendente"))
    await world.sync.scan()
    assert (await row(world.database, ANA))["status"] == "ativo"

    write(world.root, ANA, sheet(status="arquivado"))
    await world.sync.scan()
    assert (await row(world.database, ANA))["status"] == "arquivado"

    write(world.root, ANA, sheet(status="ativo"))
    await world.sync.scan()
    assert (await row(world.database, ANA))["status"] == "ativo"


async def test_an_invalid_block_turns_invalido_and_keeps_the_file(world):
    text = sheet()
    write(world.root, ANA, text)
    await store_row(world.database, ANA, text)
    await world.sync.scan()
    broken = text.replace("refresh: 7", "refresh: [7")
    write(world.root, ANA, broken)

    await world.sync.scan()

    stored = await row(world.database, ANA)
    assert stored["state"] == "invalido"
    assert stored["last_text"] == text
    assert stored["hash"] == sha256_text(text)
    assert (world.root / ANA).read_text(encoding="utf-8") == broken


async def test_a_new_identity_is_recorded_as_desconhecido(world):
    text = sheet("sht_nova")
    write(world.root, ANA, text)

    await world.sync.scan()

    stored = await row(world.database, ANA)
    assert stored["harpi_id"] == "sht_nova"
    assert stored["state"] == "desconhecido"
    assert stored["owner_id"] is None


async def test_a_sheet_in_an_unknown_campaign_is_left_alone(world):
    write(world.root, "Harpi/Campaigns/outra/sheets/Ana.md", sheet())

    await world.sync.scan()

    assert await rows(world.database) == []


async def test_a_non_utf8_sheet_is_invalido(world):
    path = world.root / ANA
    path.parent.mkdir(parents=True)
    path.write_bytes(b"\xff\xfe\x00broken")

    await world.sync.scan()

    stored = await row(world.database, ANA)
    assert stored["state"] == "invalido"
    assert stored["last_text"] == ""
    assert stored["owner_id"] is None


async def test_a_sheet_without_an_id_is_desconhecido(world):
    text = sheet().replace("harpi-id: sht_ana\n", "")
    write(world.root, ANA, text)

    await world.sync.scan()

    stored = await row(world.database, ANA)
    assert stored["state"] == "desconhecido"
    assert stored["harpi_id"] == ANA


async def test_syncthing_copies_and_temporaries_never_reach_the_rows(world):
    text = sheet()
    write(world.root, ANA, text)
    await store_row(world.database, ANA, text)
    await world.sync.scan()
    for name in (
        "Ana.sync-conflict-20260101-000000.md",
        "~syncthing~Ana.md.tmp",
        "Ana.md.tmp",
        ".hidden.md",
    ):
        write(world.root, f"{CAMPAIGN}/sheets/{name}", sheet("sht_copia"))

    await world.sync.scan()

    stored = await rows(world.database)
    assert [(item["path"], item["state"]) for item in stored] == [(ANA, "ok")]


async def test_the_config_is_reloaded_and_never_written(world):
    config = f"{CAMPAIGN}/config.md"
    original = "```harpi-campaign\nname: Paratheos\nrefresh: 7\n```\n"
    write(world.root, config, original)
    await world.sync.scan()

    updated = "```harpi-campaign\nname: Outro\nrefresh: 7\n```\n"
    write(world.root, config, updated)
    await world.sync.scan()

    parsed = vault_index.configured().campaign(SLUG).config
    assert parsed is not None
    assert parsed.name == "Outro"
    assert (world.root / config).read_text(encoding="utf-8") == updated
    assert await row(world.database, config) is None


async def test_an_unchanged_scan_reports_nothing(world):
    write(world.root, ANA, sheet())
    await world.sync.scan()

    assert await world.sync.scan() == frozenset()


async def test_the_debouncer_coalesces_a_burst(world):
    debouncer = vault_sync.Debouncer(delay=0)
    debouncer.notify(ANA)
    debouncer.notify(f"{CAMPAIGN}/config.md")

    assert await debouncer.next_batch() == frozenset({
        ANA,
        f"{CAMPAIGN}/config.md",
    })

    pending = asyncio.create_task(debouncer.next_batch())
    await asyncio.sleep(0)
    assert not pending.done()
    debouncer.notify(ANA)
    assert await pending == frozenset({ANA})


class FakeObserver:
    def __init__(self, sink) -> None:
        self.sink = sink
        self.alive = True
        self.stopped = False
        self.joined = False

    def is_alive(self) -> bool:
        return self.alive

    def stop(self) -> None:
        self.stopped = True

    def join(self) -> None:
        self.joined = True


async def test_a_watched_change_runs_one_scan_and_stops_cleanly(world):
    write(world.root, ANA, sheet(refresh=7))
    await store_row(world.database, ANA, sheet(refresh=7))
    sync = vault_sync.VaultSync(
        Vault(root=world.root), world.database, debounce=0, interval=3600
    )
    created: list[FakeObserver] = []

    def factory(vault, sink):
        observer = FakeObserver(sink)
        created.append(observer)
        return observer

    task = asyncio.create_task(
        vault_sync.run_watch(sync, observer_factory=factory)
    )
    await sync.scanned.wait()
    sync.scanned.clear()
    edited = sheet(refresh=11)
    write(world.root, ANA, edited)
    created[0].sink(ANA)
    await sync.scanned.wait()

    await vault_sync.stop_sync(task)

    stored = await row(world.database, ANA)
    assert stored["last_text"] == edited
    assert created[0].stopped is True
    assert created[0].joined is True


async def test_the_watch_loop_runs_without_a_vault():
    sync = vault_sync.VaultSync(Vault(), debounce=0)

    task = asyncio.create_task(
        vault_sync.run_watch(sync, observer_factory=lambda vault, sink: None)
    )
    await sync.scanned.wait()
    await vault_sync.stop_sync(task)


def test_the_observer_is_absent_without_a_campaigns_folder(tmp_path: Path):
    assert vault_sync.campaign_observer(Vault(), lambda path: None) is None
    assert (
        vault_sync.campaign_observer(Vault(root=tmp_path), lambda path: None)
        is None
    )


def test_the_observer_watches_the_campaigns_folder(tmp_path: Path):
    write(tmp_path, ANA, sheet())

    observer = vault_sync.campaign_observer(
        Vault(root=tmp_path), lambda path: None
    )

    assert observer is not None
    assert observer.is_alive()
    vault_sync.stop_observer(observer)
    vault_sync.stop_observer(None)


def test_the_observer_forwards_only_watched_paths(tmp_path: Path):
    seen: list[str] = []
    handler = vault_sync.CampaignObserver(tmp_path, seen.append)
    moved = f"{CAMPAIGN}/sheets/Ana PC.md"

    handler.on_any_event(FileModifiedEvent(str(tmp_path / ANA)))
    handler.on_any_event(FileOpenedEvent(str(tmp_path / ANA)))
    handler.on_any_event(FileClosedNoWriteEvent(str(tmp_path / ANA)))
    handler.on_any_event(
        FileModifiedEvent(str(tmp_path / f"{CAMPAIGN}/config.md"))
    )
    handler.on_any_event(
        FileModifiedEvent(str(tmp_path / f"{CAMPAIGN}/sheets/Ana.md.tmp"))
    )
    handler.on_any_event(DirModifiedEvent(str(tmp_path / CAMPAIGN)))
    handler.on_any_event(
        FileMovedEvent(str(tmp_path / ANA), str(tmp_path / moved))
    )
    handler.on_any_event(FileModifiedEvent(str(tmp_path / "fora/Ana.md")))

    assert seen == [ANA, ANA, moved]


def require_permission_checks() -> None:
    if os.geteuid() == 0:
        pytest.skip("root ignores file permissions")


async def test_a_vanished_campaign_folder_never_marks_rows_ausente(world):
    text = sheet()
    write(world.root, ANA, text)
    await store_row(world.database, ANA, text)
    await world.sync.scan()

    shutil.rmtree(world.root / CAMPAIGN)

    assert await world.sync.scan() == frozenset()
    assert (await row(world.database, ANA))["state"] == "ok"


async def test_an_unreadable_campaign_folder_never_marks_rows_ausente(world):
    require_permission_checks()
    text = sheet()
    write(world.root, ANA, text)
    await store_row(world.database, ANA, text)
    await world.sync.scan()
    folder = world.root / CAMPAIGN

    folder.chmod(0o000)
    try:
        assert await world.sync.scan() == frozenset()
        assert (await row(world.database, ANA))["state"] == "ok"
    finally:
        folder.chmod(0o755)


async def test_an_unreadable_sheet_keeps_the_row_untouched(world):
    require_permission_checks()
    text = sheet()
    path = write(world.root, ANA, text)
    await store_row(world.database, ANA, text, updated_at=1)

    path.chmod(0o000)
    try:
        await world.sync.scan()
        stored = await row(world.database, ANA)
        assert stored["state"] == "ok"
        assert stored["updated_at"] == 1
    finally:
        path.chmod(0o644)


async def test_an_oversized_sheet_is_invalido(world):
    path = world.root / ANA
    path.parent.mkdir(parents=True)
    path.write_text(
        sheet() + "x" * (vault_sync.MAX_NOTE_BYTES + 1), encoding="utf-8"
    )

    await world.sync.scan()

    stored = await row(world.database, ANA)
    assert stored["state"] == "invalido"
    assert stored["last_text"] == ""


async def test_broken_frontmatter_is_invalido_and_keeps_the_identity(world):
    text = sheet()
    write(world.root, ANA, text)
    await store_row(world.database, ANA, text)
    await world.sync.scan()

    write(
        world.root,
        ANA,
        text.replace("harpi-id: sht_ana", "harpi-id: [sht_ana"),
    )
    await world.sync.scan()

    stored = await row(world.database, ANA)
    assert stored["state"] == "invalido"
    assert stored["harpi_id"] == "sht_ana"
    assert stored["last_text"] == text

    write(world.root, ANA, text)
    await world.sync.scan()

    assert (await row(world.database, ANA))["state"] == "ok"


async def test_a_rename_never_evicts_the_sheet_at_the_destination(world):
    ana = sheet("sht_ana", owner="555")
    bia = f"{CAMPAIGN}/sheets/Bia.md"
    bia_text = sheet("sht_bia", owner="556")
    write(world.root, ANA, ana)
    write(world.root, bia, bia_text)
    await store_row(world.database, ANA, ana)
    await store_row(world.database, bia, bia_text)
    await world.sync.scan()
    (world.root / bia).unlink()
    await world.sync.scan()

    (world.root / ANA).rename(world.root / bia)
    await world.sync.scan()

    moved = await row(world.database, ANA)
    destination = await row(world.database, bia)
    assert moved["harpi_id"] == "sht_ana"
    assert moved["state"] == "desconhecido"
    assert moved["last_text"] == ana
    assert destination["harpi_id"] == "sht_bia"
    assert destination["state"] == "desconhecido"
    assert destination["last_text"] == bia_text
    assert (world.root / bia).read_text(encoding="utf-8") == ana


async def test_a_vault_that_appears_later_is_read(tmp_path: Path):
    root = tmp_path / "vault"
    sync = vault_sync.VaultSync(Vault(root=root), None)
    try:
        assert await sync.scan() == frozenset()

        write(root, ANA, sheet())
        assert await sync.scan() == frozenset({ANA})

        sheets = vault_index.configured().campaign(SLUG).sheets
        assert sheets[0].id == "sht_ana"
    finally:
        vault_index.configure(VaultIndex())


async def test_the_watcher_attaches_again_when_the_observer_dies(tmp_path):
    sync = vault_sync.VaultSync(Vault(root=tmp_path), None, debounce=0)
    created: list[FakeObserver] = []

    def factory(vault, sink):
        observer = FakeObserver(sink)
        created.append(observer)
        return observer

    watcher = vault_sync.Watcher(
        sync,
        vault_sync.Debouncer(0),
        factory,
        asyncio.get_running_loop(),
    )
    watcher.attach()
    watcher.attach()
    assert len(created) == 1

    created[0].alive = False
    watcher.attach()
    assert len(created) == 2

    await watcher.stop()
    assert created[-1].stopped is True
    assert created[-1].joined is True


async def test_an_unlistable_campaigns_root_is_not_an_absence(world):
    require_permission_checks()
    text = sheet()
    write(world.root, ANA, text)
    await store_row(world.database, ANA, text)
    await world.sync.scan()
    campaigns = world.root / "Harpi" / "Campaigns"

    campaigns.chmod(0o000)
    try:
        assert await world.sync.scan() == frozenset()
        assert (await row(world.database, ANA))["state"] == "ok"
    finally:
        campaigns.chmod(0o755)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("harpi-rev: 7", 7),
        ("harpi-rev: abc", 0),
        ("harpi-rev: true", 0),
        ("harpi-rev: [1, 2]", 0),
        ("", 0),
    ],
)
async def test_the_revision_is_read_leniently(world, line, expected):
    text = sheet().replace("harpi-rev: 3\n", f"{line}\n" if line else "")
    write(world.root, ANA, text)

    await world.sync.scan()

    assert (await row(world.database, ANA))["rev"] == expected


@pytest.mark.parametrize(
    "text",
    [
        "ficha sem frontmatter\n",
        "---\ntipo: ficha\nharpi-id: sht_ana\n",
    ],
)
async def test_missing_or_unclosed_frontmatter_is_invalido(world, text):
    write(world.root, ANA, text)

    await world.sync.scan()

    stored = await row(world.database, ANA)
    assert stored["state"] == "invalido"
    assert stored["last_text"] == text


async def test_an_external_change_never_accepts_a_sheet_in_conflict(world):
    text = sheet()
    write(world.root, ANA, text)
    await store_row(world.database, ANA, text)
    await world.sync.scan()
    await world.database.execute(
        "INSERT INTO sheet_conflicts ("
        "id, path, field_path, base, ours, theirs, created_at"
        ") VALUES ('cnf_1', ?, 'block.refresh', '7', '9', '5', 1)",
        (ANA,),
    )
    await world.database.execute(
        "UPDATE sheet_files SET state = 'conflito' WHERE path = ?", (ANA,)
    )
    edited = sheet(refresh=11)

    write(world.root, ANA, edited)
    await world.sync.scan()

    stored = await row(world.database, ANA)
    assert stored["state"] == "conflito"
    assert stored["hash"] == sha256_text(text)
    assert stored["last_text"] == text


async def test_the_conflict_clears_only_when_its_rows_are_resolved(world):
    text = sheet()
    write(world.root, ANA, text)
    await store_row(world.database, ANA, text)
    await world.sync.scan()
    await world.database.execute(
        "INSERT INTO sheet_conflicts ("
        "id, path, field_path, base, ours, theirs, created_at, "
        "resolved_at, resolved_by"
        ") VALUES ('cnf_1', ?, 'block.refresh', '7', '9', '5', 1, 2, '100')",
        (ANA,),
    )
    await world.database.execute(
        "UPDATE sheet_files SET state = 'conflito' WHERE path = ?", (ANA,)
    )
    edited = sheet(refresh=11)

    write(world.root, ANA, edited)
    await world.sync.scan()

    stored = await row(world.database, ANA)
    assert stored["state"] == "ok"
    assert stored["last_text"] == edited
