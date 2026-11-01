from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.panel import sheet_conflicts, sheet_merge, sheet_store
from src.panel.schemas import SheetPatch
from src.panel.sheet_write import write_sheet
from src.panel.sheets import sha256_text
from src.storage.database import Database
from src.storage.seed import paratheos

SLUG = "paratheos"
NARRATOR = "100"
GUILD = "1"
PATH = f"Harpi/Campaigns/{SLUG}/sheets/Ana.md"
OWNER = "555"
BASE = (
    "---\n"
    "tipo: ficha\n"
    "harpi-id: sht_ana\n"
    "harpi-campaign: paratheos\n"
    "harpi-character-id: chr_ana\n"
    f"harpi-owner: '{OWNER}'\n"
    "harpi-status: ativo\n"
    "harpi-rev: 3\n"
    "---\n\n## História\n\nAntes.\n\n"
    "```harpi-sheet\n"
    "refresh: 7\n"
    "fate_points: 2\n"
    "aspects:\n"
    "  - {label: Conceito, text: Piloto}\n"
    "```\n\n## Anotações\n\nFim.\n"
)


@pytest.fixture
async def world(tmp_path: Path):
    root = tmp_path / "vault"
    write(root, PATH, BASE)
    database = Database(
        tmp_path / "panel.db", campaign=paratheos(NARRATOR, GUILD)
    )
    await database.open()
    await database.execute(
        "INSERT INTO sheet_files ("
        "path, harpi_id, campaign, rev, hash, last_text, base_json, "
        "status, owner_id, state, updated_at"
        ") VALUES (?, 'sht_ana', ?, 3, ?, ?, ?, 'ativo', ?, 'ok', 1)",
        (
            PATH,
            SLUG,
            sha256_text(BASE),
            BASE,
            sheet_store.base_state(BASE),
            OWNER,
        ),
    )
    yield SimpleNamespace(root=root, database=database, path=root / PATH)
    await database.close()


def write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def config():
    from src.panel.sheets import default_config

    return default_config()


async def open_conflict(
    world, *, refresh: int = 9, their_refresh: int = 4
) -> tuple[SheetPatch, list[sheet_conflicts.ConflictRecord]]:
    theirs = BASE.replace("refresh: 7", f"refresh: {their_refresh}")
    write(world.root, PATH, theirs)
    patch = SheetPatch(
        base_hash=sha256_text(BASE), refresh=refresh, history="Do painel."
    )
    base = sheet_merge.state_from_base(sheet_store.base_state(BASE))
    merged = sheet_merge.merge(
        base,
        sheet_merge.apply_patch(base, patch),
        sheet_merge.state_from_text(theirs),
    )
    conflicts = await sheet_conflicts.record(
        world.database,
        PATH,
        patch,
        merged.remaining,
        sheet_store.base_state(BASE),
    )
    return patch, conflicts


async def test_a_conflict_is_queued_with_the_three_values(world):
    await open_conflict(world)

    queue = await sheet_conflicts.queue(world.database, SLUG, None)

    assert [
        (item.field_path, item.base, item.ours, item.theirs) for item in queue
    ] == [("block.refresh", "7", "9", "4")]
    assert queue[0].sheet_id == "sht_ana"
    assert queue[0].character_id == "chr_ana"
    assert queue[0].allow_both is False


async def test_the_owner_sees_only_their_own_conflicts(world):
    await open_conflict(world)

    assert await sheet_conflicts.queue(world.database, SLUG, "999") == []
    assert len(await sheet_conflicts.queue(world.database, SLUG, OWNER)) == 1


async def test_resolving_the_last_field_writes_once_and_returns_to_ok(world):
    _, conflicts = await open_conflict(world)

    resolution = await sheet_conflicts.decide(
        world.database,
        world.root,
        campaign=SLUG,
        conflict_id=conflicts[0].id,
        decision="ours",
        actor=OWNER,
    )

    assert resolution.write is not None
    result = write_sheet(
        world.path,
        SLUG,
        "sht_ana",
        resolution.write.patch,
        config(),
        resolution.write.record,
        world.root.parent / "vault-backups",
    )
    await sheet_store.store_sheet(world.database, SLUG, PATH, result)
    await sheet_conflicts.settle(world.database, PATH, OWNER)

    text = world.path.read_text(encoding="utf-8")
    row = await world.database.fetchone(
        "SELECT state, rev, hash FROM sheet_files WHERE path = ?", (PATH,)
    )
    assert "refresh: 9" in text
    assert "Do painel." in text
    assert result.rev == 4
    assert row["state"] == "ok"
    assert row["rev"] == 4
    assert row["hash"] == sha256_text(text)
    backups = list((world.root.parent / "vault-backups").glob("**/*.md"))
    assert len(backups) == 1
    assert "refresh: 4" in backups[0].read_text(encoding="utf-8")


async def test_nothing_is_written_while_a_field_remains_undecided(world):
    theirs = BASE.replace("refresh: 7", "refresh: 4").replace(
        "fate_points: 2", "fate_points: 5"
    )
    write(world.root, PATH, theirs)
    patch = SheetPatch(base_hash=sha256_text(BASE), refresh=9, fate_points=1)
    base = sheet_merge.state_from_base(sheet_store.base_state(BASE))
    merged = sheet_merge.merge(
        base,
        sheet_merge.apply_patch(base, patch),
        sheet_merge.state_from_text(theirs),
    )
    conflicts = await sheet_conflicts.record(
        world.database,
        PATH,
        patch,
        merged.remaining,
        sheet_store.base_state(BASE),
    )
    before = world.path.read_bytes()

    resolution = await sheet_conflicts.decide(
        world.database,
        world.root,
        campaign=SLUG,
        conflict_id=conflicts[0].id,
        decision="ours",
        actor=OWNER,
    )

    assert resolution.write is None
    assert len(resolution.conflicts) == 1
    assert world.path.read_bytes() == before


async def test_keep_both_is_refused_on_a_scalar(world):
    _, conflicts = await open_conflict(world)

    with pytest.raises(sheet_conflicts.InvalidDecision):
        await sheet_conflicts.decide(
            world.database,
            world.root,
            campaign=SLUG,
            conflict_id=conflicts[0].id,
            decision="both",
            actor=OWNER,
        )


async def test_an_unknown_conflict_is_not_found(world):
    with pytest.raises(sheet_conflicts.ConflictNotFound):
        await sheet_conflicts.decide(
            world.database,
            world.root,
            campaign=SLUG,
            conflict_id="cnf_missing",
            decision="ours",
            actor=OWNER,
        )


async def test_open_paths_lists_the_sheets_in_conflict(world):
    await open_conflict(world)

    assert await sheet_conflicts.open_paths(world.database, SLUG) == frozenset({
        PATH
    })


async def test_keep_both_writes_a_second_item_with_the_same_label(world):
    theirs = BASE.replace("text: Piloto", "text: Contrabandista")
    write(world.root, PATH, theirs)
    patch = SheetPatch(
        base_hash=sha256_text(BASE),
        aspects=[{"label": "Conceito", "text": "Mensageira"}],
    )
    base = sheet_merge.state_from_base(sheet_store.base_state(BASE))
    merged = sheet_merge.merge(
        base,
        sheet_merge.apply_patch(base, patch),
        sheet_merge.state_from_text(theirs),
    )
    conflicts = await sheet_conflicts.record(
        world.database,
        PATH,
        patch,
        merged.remaining,
        sheet_store.base_state(BASE),
    )

    resolution = await sheet_conflicts.decide(
        world.database,
        world.root,
        campaign=SLUG,
        conflict_id=conflicts[0].id,
        decision="both",
        actor=OWNER,
    )

    assert resolution.write is not None
    text = resolution.write.patch.model_dump()
    assert text["aspects"] == [
        {"label": "Conceito", "text": "Mensageira"},
        {"label": "Conceito", "text": "Contrabandista"},
    ]


async def open_two_conflicts(world):
    theirs = BASE.replace("refresh: 7", "refresh: 4").replace(
        "fate_points: 2", "fate_points: 5"
    )
    write(world.root, PATH, theirs)
    patch = SheetPatch(base_hash=sha256_text(BASE), refresh=9, fate_points=1)
    base = sheet_merge.state_from_base(sheet_store.base_state(BASE))
    merged = sheet_merge.merge(
        base,
        sheet_merge.apply_patch(base, patch),
        sheet_merge.state_from_text(theirs),
    )
    return await sheet_conflicts.record(
        world.database,
        PATH,
        patch,
        merged.remaining,
        sheet_store.base_state(BASE),
    )


async def test_two_simultaneous_resolutions_of_one_field_leave_one_winner(
    world,
):
    import asyncio

    _, conflicts = await open_conflict(world)

    results = await asyncio.gather(
        sheet_conflicts.decide(
            world.database,
            world.root,
            campaign=SLUG,
            conflict_id=conflicts[0].id,
            decision="ours",
            actor=OWNER,
        ),
        sheet_conflicts.decide(
            world.database,
            world.root,
            campaign=SLUG,
            conflict_id=conflicts[0].id,
            decision="theirs",
            actor=OWNER,
        ),
        return_exceptions=True,
    )

    writes = [
        result
        for result in results
        if isinstance(result, sheet_conflicts.Resolution)
        and result.write is not None
    ]
    refusals = [
        result
        for result in results
        if isinstance(result, sheet_conflicts.ConflictNotPending)
    ]
    assert len(writes) == 1
    assert len(refusals) == 1


async def test_a_remaining_conflict_keeps_its_id_while_the_other_is_decided(
    world,
):
    conflicts = await open_two_conflicts(world)
    ids = {conflict.field_path: conflict.id for conflict in conflicts}

    resolution = await sheet_conflicts.decide(
        world.database,
        world.root,
        campaign=SLUG,
        conflict_id=ids["block.refresh"],
        decision="ours",
        actor=OWNER,
    )
    queue = await sheet_conflicts.path_queue(world.database, PATH)

    assert resolution.write is None
    assert {conflict.field_path: conflict.id for conflict in queue} == {
        "block.fate_points": ids["block.fate_points"]
    }
    assert (queue[0].base, queue[0].ours, queue[0].theirs) == ("2", "1", "5")
