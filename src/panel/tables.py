from __future__ import annotations

import asyncio
import json
import math
import secrets
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from aiosqlite import IntegrityError, Row
from pydantic import BaseModel, ConfigDict, ValidationError

from src.panel import scenes
from src.panel.schemas import (
    SceneRect,
    SceneZone,
    TableParticipant,
    TableRole,
    TableScene,
    TableStatus,
    TableSummary,
    TableToken,
    TableTokenCreate,
    TableTokenPatch,
    TableTurn,
)
from src.panel.vault_index import CAMPAIGN_ROOT
from src.panel.vault_write import atomic_write
from src.storage.database import Database

TABLES_FOLDER = "tables"
SNAPSHOT_VERSION = 1
SNAPSHOT_KIND = "table_snapshot"
SNAPSHOT_INVALID = (
    "O snapshot está ausente ou inválido; a mesa reabriu a partir do SQLite."
)
EPSILON = 1e-9
_LOCKS: dict[str, asyncio.Lock] = {}


class TableError(Exception):
    pass


class TableNotFound(TableError):
    pass


class SceneNotFound(TableError):
    pass


class ZoneNotFound(TableError):
    pass


class TableClosed(TableError):
    pass


class TokenNotFound(TableError):
    pass


class SnapshotFailed(TableError):
    pass


class SceneUnreadable(TableError):
    pass


class TurnNotParticipant(TableError):
    pass


class TurnStale(TableError):
    pass


class TurnTaken(TableError):
    pass


class TurnAlreadyOpen(TableError):
    pass


class TurnMissing(TableError):
    pass


class TurnNotYours(TableError):
    pass


class TableAlreadyOpen(TableError):
    def __init__(self, table: TableRow) -> None:
        super().__init__(f"table {table.id} is already open")
        self.table = table


@dataclass(frozen=True, slots=True)
class TableRow:
    id: str
    campaign: str
    channel_id: str
    name: str
    status: TableStatus
    current_scene_id: str | None
    round: int
    spectators: bool
    rev: int
    narrator_id: str
    guild_id: str
    snapshot_path: str | None


@dataclass(frozen=True, slots=True)
class TokenRow:
    id: str
    table_id: str
    scene_id: str
    character_id: str | None
    label: str
    owner_id: str | None
    x: float
    y: float
    w: int
    h: int
    color: str
    visible: bool
    rev: int


@dataclass(frozen=True, slots=True)
class TurnRow:
    id: str
    round: int
    token_id: str | None
    character_id: str | None
    label: str
    owner_id: str | None
    started_at: int


class SnapshotTable(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    campaign: str
    channel_id: str
    name: str
    status: TableStatus
    round: int
    current_scene_id: str | None


class SnapshotScene(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    blueprint_path: str
    blueprint_hash: str
    image: dict[str, Any]
    grid: dict[str, Any]
    fog_outside: bool
    zones: list[SceneZone]


class SnapshotToken(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    character_id: str | None = None
    label: str
    owner_id: str | None = None
    x: float
    y: float
    w: int = 1
    h: int = 1
    color: str = "#e9dfc7"
    visible: bool = True


class SnapshotTurn(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    round: int
    token_id: str | None = None
    character_id: str | None = None
    label: str
    started_at: int


class TableSnapshot(BaseModel):
    model_config = ConfigDict(extra="allow")

    version: int
    kind: str
    saved_at: int
    rev: int
    table: SnapshotTable
    scene: SnapshotScene | None = None
    tokens: list[SnapshotToken] = []
    turn: SnapshotTurn | None = None


def _lock(table_id: str) -> asyncio.Lock:
    lock = _LOCKS.get(table_id)
    if lock is None:
        lock = asyncio.Lock()
        _LOCKS[table_id] = lock
    return lock


def _table(row: Row) -> TableRow:
    return TableRow(
        id=row["id"],
        campaign=row["campaign_slug"],
        channel_id=row["channel_id"],
        name=row["name"],
        status=row["status"],
        current_scene_id=row["current_scene_id"],
        round=row["round"],
        spectators=bool(row["spectators"]),
        rev=row["rev"],
        narrator_id=row["narrator_id"],
        guild_id=row["guild_id"],
        snapshot_path=row["snapshot_path"],
    )


def _token(row: Row) -> TokenRow:
    return TokenRow(
        id=row["id"],
        table_id=row["table_id"],
        scene_id=row["scene_id"],
        character_id=row["character_id"],
        label=row["label"],
        owner_id=row["owner_id"],
        x=row["x"],
        y=row["y"],
        w=row["w"],
        h=row["h"],
        color=row["color"],
        visible=bool(row["visible"]),
        rev=row["rev"],
    )


_TABLE_SQL = (
    "SELECT t.*, c.narrator_id, c.guild_id FROM tables t "
    "JOIN campaigns c ON c.slug = t.campaign_slug "
)


async def table_row(database: Database, table_id: str) -> TableRow | None:
    row = await database.fetchone(f"{_TABLE_SQL} WHERE t.id = ?", (table_id,))
    return None if row is None else _table(row)


async def _active_table(
    database: Database, campaign: str, channel_id: str
) -> TableRow | None:
    row = await database.fetchone(
        f"{_TABLE_SQL} WHERE t.status = 'open' "
        "AND (t.campaign_slug = ? OR t.channel_id = ?) "
        "ORDER BY t.opened_at, t.id LIMIT 1",
        (campaign, channel_id),
    )
    return None if row is None else _table(row)


async def open_table(
    database: Database,
    *,
    campaign: str,
    narrator_id: str,
    channel_id: str,
    name: str,
    scene: str,
) -> TableRow:
    record = await scenes.scene_record(database, campaign, scene)
    if record is None:
        raise SceneNotFound(scene)
    active = await _active_table(database, campaign, channel_id)
    if active is not None:
        raise TableAlreadyOpen(active)
    now = int(time.time())
    table_id = f"tbl_{secrets.token_hex(12)}"
    try:
        await database.execute(
            "INSERT INTO tables ("
            "id, campaign_slug, channel_id, name, status, current_scene_id, "
            "round, spectators, rev, opened_by, opened_at, created_at, "
            "updated_at"
            ") VALUES (?, ?, ?, ?, 'open', ?, 1, 0, 1, ?, ?, ?, ?)",
            (
                table_id,
                campaign,
                channel_id,
                name,
                record.id,
                narrator_id,
                now,
                now,
                now,
            ),
        )
    except IntegrityError as failure:
        active = await _active_table(database, campaign, channel_id)
        if active is not None:
            raise TableAlreadyOpen(active) from failure
        raise
    row = await table_row(database, table_id)
    if row is None:
        raise TableNotFound(table_id)
    return row


def _columns(record: scenes.SceneRecord) -> int:
    grid = record.grid
    return max(
        1, math.ceil((record.image_width - grid.offset_x) / grid.cell_px)
    )


def _rows(record: scenes.SceneRecord) -> int:
    grid = record.grid
    return max(
        1, math.ceil((record.image_height - grid.offset_y) / grid.cell_px)
    )


def _fits(
    record: scenes.SceneRecord, x: float, y: float, w: int, h: int
) -> bool:
    return (
        x >= 0
        and y >= 0
        and x + w <= _columns(record) + EPSILON
        and y + h <= _rows(record) + EPSILON
    )


def _center(token: TokenRow) -> tuple[float, float]:
    return token.x + token.w / 2, token.y + token.h / 2


def _inside(zone: SceneZone, x: float, y: float) -> bool:
    return any(
        rect.x <= x < rect.x + rect.w and rect.y <= y < rect.y + rect.h
        for rect in zone.rects
    )


def _token_public(
    token: TokenRow, zones: list[SceneZone], fog_outside: bool
) -> bool:
    if not token.visible:
        return False
    x, y = _center(token)
    containing = [zone for zone in zones if _inside(zone, x, y)]
    if containing:
        return any(zone.revealed for zone in containing)
    return not fog_outside


async def token_rows(
    database: Database, table_id: str, scene_id: str | None
) -> list[TokenRow]:
    if scene_id is None:
        return []
    rows = await database.fetchall(
        "SELECT * FROM tokens WHERE table_id = ? AND scene_id = ? "
        "ORDER BY created_at, id",
        (table_id, scene_id),
    )
    return [_token(row) for row in rows]


async def token_row(
    database: Database, table_id: str, token_id: str
) -> TokenRow | None:
    row = await database.fetchone(
        "SELECT * FROM tokens WHERE table_id = ? AND id = ?",
        (table_id, token_id),
    )
    return None if row is None else _token(row)


async def _scene_for(
    database: Database, table: TableRow
) -> scenes.SceneRecord | None:
    if table.current_scene_id is None:
        return None
    return await scenes.scene_record_by_id(
        database, table.campaign, table.current_scene_id
    )


async def _require_scene(
    database: Database, table: TableRow
) -> scenes.SceneRecord:
    record = await _scene_for(database, table)
    if record is None:
        raise SceneNotFound(table.id)
    return record


def _turn(row: Row) -> TurnRow:
    return TurnRow(
        id=row["id"],
        round=row["round"],
        token_id=row["token_id"],
        character_id=row["character_id"],
        label=row["label"],
        owner_id=row["token_owner_id"],
        started_at=row["started_at"],
    )


async def _open_turn_row(database: Database, table_id: str) -> TurnRow | None:
    row = await database.fetchone(
        "SELECT turns.*, tokens.owner_id AS token_owner_id FROM turns "
        "LEFT JOIN tokens ON tokens.id = turns.token_id "
        "WHERE turns.table_id = ? AND turns.ended_at IS NULL",
        (table_id,),
    )
    return None if row is None else _turn(row)


async def _acted_token_ids(
    database: Database, table_id: str, scene_id: str, round_number: int
) -> set[str]:
    rows = await database.fetchall(
        "SELECT token_id FROM turns WHERE table_id = ? AND scene_id = ? "
        "AND round = ? AND token_id IS NOT NULL",
        (table_id, scene_id, round_number),
    )
    return {str(row["token_id"]) for row in rows}


async def _public_tokens(
    database: Database, table: TableRow
) -> tuple[list[TokenRow], scenes.SceneRecord | None]:
    record = await _scene_for(database, table)
    if record is None:
        return [], None
    zones = scenes.stored_zones(record.zones_json)
    fog_outside = await scene_fog_outside(database, record.id)
    tokens = await token_rows(database, table.id, record.id)
    return visible_tokens(tokens, zones, fog_outside), record


async def _pending_target(
    database: Database, table: TableRow, token_id: str
) -> TokenRow:
    current = await token_row(database, table.id, token_id)
    record = await _require_scene(database, table)
    if current is None or current.scene_id != record.id:
        raise TokenNotFound(token_id)
    public, _ = await _public_tokens(database, table)
    target = next((token for token in public if token.id == token_id), None)
    if target is None:
        raise TurnNotParticipant(token_id)
    acted = await _acted_token_ids(database, table.id, record.id, table.round)
    if target.id in acted:
        raise TurnTaken(token_id)
    return target


async def _insert_turn(
    database: Database, table: TableRow, token: TokenRow, actor_id: str
) -> None:
    now = int(time.time())
    await database.execute(
        "INSERT INTO turns ("
        "id, table_id, scene_id, round, token_id, character_id, label, "
        "started_at, started_by"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            f"trn_{secrets.token_hex(12)}",
            table.id,
            token.scene_id,
            table.round,
            token.id,
            token.character_id,
            token.label,
            now,
            actor_id,
        ),
    )
    await _touch_table(database, table.id)


async def _end_turn_row(
    database: Database, table_id: str, turn_id: str, actor_id: str
) -> None:
    await database.execute(
        "UPDATE turns SET ended_at = ?, ended_by = ? "
        "WHERE table_id = ? AND id = ? AND ended_at IS NULL",
        (int(time.time()), actor_id, table_id, turn_id),
    )
    await _touch_table(database, table_id)


async def _touch_table(database: Database, table_id: str) -> None:
    await database.execute(
        "UPDATE tables SET rev = rev + 1, updated_at = ? WHERE id = ?",
        (int(time.time()), table_id),
    )


async def _require_current_turn(
    database: Database, table: TableRow
) -> TurnRow:
    current = await _open_turn_row(database, table.id)
    if current is None:
        raise TurnMissing(table.id)
    return current


def _require_own_turn(current: TurnRow, actor_id: str) -> None:
    if current.owner_id is None or current.owner_id != actor_id:
        raise TurnNotYours(current.id)


def _require_expected(current: TurnRow, expected_turn_id: str | None) -> None:
    if expected_turn_id is not None and expected_turn_id != current.id:
        raise TurnStale(current.id)


async def _reconcile_table(
    database: Database, table_id: str, actor_id: str
) -> None:
    table = await table_row(database, table_id)
    if table is None or table.status != "open":
        return
    public, record = await _public_tokens(database, table)
    if record is None:
        return
    current = await _open_turn_row(database, table_id)
    public_ids = {token.id for token in public}
    if current is not None and current.token_id not in public_ids:
        await _end_turn_row(database, table_id, current.id, actor_id)
    await _settle_round(database, table_id)


async def _settle_round(database: Database, table_id: str) -> None:
    table = await table_row(database, table_id)
    if table is None:
        return
    public, record = await _public_tokens(database, table)
    if record is None or not public:
        return
    if await _open_turn_row(database, table_id) is not None:
        return
    acted = await _acted_token_ids(database, table_id, record.id, table.round)
    if any(token.id not in acted for token in public):
        return
    await database.execute(
        "UPDATE tables SET round = round + 1, rev = rev + 1, updated_at = ? "
        "WHERE id = ? AND status = 'open'",
        (int(time.time()), table_id),
    )


async def open_turn(
    database: Database, table: TableRow, *, token_id: str, actor_id: str
) -> None:
    async with _lock(table.id):
        fresh = await _require_fresh_table(database, table.id)
        if await _open_turn_row(database, fresh.id) is not None:
            raise TurnAlreadyOpen(fresh.id)
        target = await _pending_target(database, fresh, token_id)
        await _insert_turn(database, fresh, target, actor_id)


async def pass_turn(
    database: Database,
    table: TableRow,
    *,
    token_id: str,
    actor_id: str,
    narrator: bool,
    expected_turn_id: str | None = None,
) -> None:
    async with _lock(table.id):
        fresh = await _require_fresh_table(database, table.id)
        current = await _require_current_turn(database, fresh)
        _require_expected(current, expected_turn_id)
        if not narrator:
            _require_own_turn(current, actor_id)
        target = await _pending_target(database, fresh, token_id)
        await _end_turn_row(database, fresh.id, current.id, actor_id)
        await _insert_turn(database, fresh, target, actor_id)


async def end_turn(
    database: Database,
    table: TableRow,
    *,
    actor_id: str,
    narrator: bool,
    expected_turn_id: str | None = None,
) -> None:
    async with _lock(table.id):
        fresh = await _require_fresh_table(database, table.id)
        current = await _require_current_turn(database, fresh)
        _require_expected(current, expected_turn_id)
        if not narrator:
            _require_own_turn(current, actor_id)
        await _end_turn_row(database, fresh.id, current.id, actor_id)
        await _settle_round(database, fresh.id)


async def _require_fresh_table(database: Database, table_id: str) -> TableRow:
    fresh = await table_row(database, table_id)
    if fresh is None:
        raise TableNotFound(table_id)
    if fresh.status != "open":
        raise TableClosed(table_id)
    return fresh


def _zone_text(zones: list[SceneZone]) -> str:
    return json.dumps(
        [zone.model_dump(mode="json") for zone in zones],
        ensure_ascii=False,
        sort_keys=True,
    )


async def _store_zones(
    database: Database, record: scenes.SceneRecord, zones: list[SceneZone]
) -> None:
    await database.execute(
        "UPDATE scenes SET zones_json = ?, rev = rev + 1, updated_at = ? "
        "WHERE id = ?",
        (_zone_text(zones), int(time.time()), record.id),
    )


async def set_zone(
    database: Database,
    table: TableRow,
    zone_id: str,
    *,
    revealed: bool,
    actor_id: str,
) -> None:
    async with _lock(table.id):
        record = await _require_scene(database, table)
        zones = scenes.stored_zones(record.zones_json)
        if not any(zone.id == zone_id for zone in zones):
            raise ZoneNotFound(zone_id)
        updated = [
            zone.model_copy(update={"revealed": revealed})
            if zone.id == zone_id
            else zone
            for zone in zones
        ]
        await _store_zones(database, record, updated)
        if revealed:
            await _reveal_characters(database, table, updated, actor_id)
        await _reconcile_table(database, table.id, actor_id)


async def _reveal_characters(
    database: Database,
    table: TableRow,
    zones: list[SceneZone],
    actor_id: str,
) -> None:
    record = await _scene_for(database, table)
    if record is None:
        return
    fog_outside = await scene_fog_outside(database, record.id)
    for token in await token_rows(database, table.id, record.id):
        if _reveals_character(token, zones, fog_outside):
            await _remember_reveal(database, table.campaign, token, actor_id)


def _reveals_character(
    token: TokenRow, zones: list[SceneZone], fog_outside: bool
) -> bool:
    if token.character_id is None or not token.visible:
        return False
    if not _token_public(token, zones, fog_outside):
        return False
    x, y = _center(token)
    return any(_inside(zone, x, y) and zone.revealed for zone in zones)


async def _remember_reveal(
    database: Database,
    campaign: str,
    token: TokenRow,
    actor_id: str,
) -> None:
    await database.execute(
        "INSERT INTO character_visibility ("
        "campaign_slug, character_id, revealed_at, revealed_by"
        ") VALUES (?, ?, ?, ?) ON CONFLICT DO NOTHING",
        (campaign, token.character_id, int(time.time()), actor_id),
    )


async def _reveal_character(
    database: Database, table: TableRow, token: TokenRow
) -> None:
    if token.character_id is None or not token.visible:
        return
    record = await _scene_for(database, table)
    if record is None:
        return
    zones = scenes.stored_zones(record.zones_json)
    fog_outside = await scene_fog_outside(database, record.id)
    if _reveals_character(token, zones, fog_outside):
        await _remember_reveal(
            database, table.campaign, token, table.narrator_id
        )


async def scene_fog_outside(database: Database, scene_id: str) -> bool:
    row = await database.fetchone(
        "SELECT fog_outside FROM scenes WHERE id = ?", (scene_id,)
    )
    return bool(row["fog_outside"]) if row is not None else False


async def create_token(
    database: Database, table: TableRow, payload: TableTokenCreate
) -> TokenRow:
    async with _lock(table.id):
        record = await _require_scene(database, table)
        _check_bounds(record, payload.x, payload.y, payload.w, payload.h)
        now = int(time.time())
        token_id = f"tok_{secrets.token_hex(12)}"
        await database.execute(
            "INSERT INTO tokens ("
            "id, table_id, scene_id, character_id, label, owner_id, x, y, w, "
            "h, color, visible, rev, created_at, updated_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
            (
                token_id,
                table.id,
                record.id,
                payload.character_id,
                payload.label,
                payload.owner_id,
                payload.x,
                payload.y,
                payload.w,
                payload.h,
                payload.color,
                int(payload.visible),
                now,
                now,
            ),
        )
        row = await token_row(database, table.id, token_id)
        if row is None:
            raise TokenNotFound(token_id)
        await _reveal_character(database, table, row)
        return row


def _check_bounds(
    record: scenes.SceneRecord, x: float, y: float, w: int, h: int
) -> None:
    if not _fits(record, x, y, w, h):
        raise ValueError("The token leaves the map")


async def update_token(
    database: Database, table: TableRow, token_id: str, patch: TableTokenPatch
) -> TokenRow:
    async with _lock(table.id):
        current = await token_row(database, table.id, token_id)
        if current is None:
            raise TokenNotFound(token_id)
        record = await _require_scene(database, table)
        if current.scene_id != record.id:
            raise TokenNotFound(token_id)
        values = _merged_token(current, patch)
        _check_bounds(
            record, values["x"], values["y"], values["w"], values["h"]
        )
        await database.execute(
            "UPDATE tokens SET character_id = ?, label = ?, owner_id = ?, "
            "x = ?, y = ?, w = ?, h = ?, color = ?, visible = ?, rev = "
            "rev + 1, updated_at = ? WHERE table_id = ? AND id = ?",
            (
                values["character_id"],
                values["label"],
                values["owner_id"],
                values["x"],
                values["y"],
                values["w"],
                values["h"],
                values["color"],
                int(values["visible"]),
                int(time.time()),
                table.id,
                token_id,
            ),
        )
        row = await token_row(database, table.id, token_id)
        if row is None:
            raise TokenNotFound(token_id)
        await _reveal_character(database, table, row)
        await _reconcile_table(database, table.id, "system")
        return row


def _merged_token(current: TokenRow, patch: TableTokenPatch) -> dict[str, Any]:
    values: dict[str, Any] = {
        "character_id": current.character_id,
        "label": current.label,
        "owner_id": current.owner_id,
        "x": current.x,
        "y": current.y,
        "w": current.w,
        "h": current.h,
        "color": current.color,
        "visible": current.visible,
    }
    values.update({
        name: value
        for name, value in patch.model_dump(exclude_unset=True).items()
        if value is not None
    })
    return values


async def delete_token(
    database: Database, table: TableRow, token_id: str
) -> None:
    async with _lock(table.id):
        current = await token_row(database, table.id, token_id)
        if current is None or current.scene_id != table.current_scene_id:
            raise TokenNotFound(token_id)
        open_turn = await _open_turn_row(database, table.id)
        if open_turn is not None and open_turn.token_id == token_id:
            await _end_turn_row(database, table.id, open_turn.id, "system")
        await database.execute(
            "DELETE FROM tokens WHERE table_id = ? AND id = ?",
            (table.id, token_id),
        )
        await _settle_round(database, table.id)


async def set_spectators(
    database: Database, table: TableRow, enabled: bool
) -> None:
    await database.execute(
        "UPDATE tables SET spectators = ?, rev = rev + 1, updated_at = ? "
        "WHERE id = ?",
        (int(enabled), int(time.time()), table.id),
    )


async def end_turns(database: Database, table_id: str, actor: str) -> None:
    await database.execute(
        "UPDATE turns SET ended_at = ?, ended_by = ? "
        "WHERE table_id = ? AND ended_at IS NULL",
        (int(time.time()), actor, table_id),
    )


async def change_scene(
    database: Database, table: TableRow, scene: str
) -> None:
    async with _lock(table.id):
        record = await scenes.scene_record(database, table.campaign, scene)
        if record is None:
            raise SceneNotFound(scene)
        await end_turns(database, table.id, "system")
        await _settle_round(database, table.id)
        await database.execute(
            "UPDATE tables SET current_scene_id = ?, rev = rev + 1, "
            "updated_at = ? WHERE id = ?",
            (record.id, int(time.time()), table.id),
        )


async def reload_scene(
    database: Database, root: Path, table: TableRow
) -> None:
    async with _lock(table.id):
        record = await _require_scene(database, table)
        blueprint = scenes.load_blueprint(root / record.blueprint_path)
        if blueprint is None:
            raise SceneUnreadable(record.blueprint_path)
        revealed = {
            zone.id: zone.revealed
            for zone in scenes.stored_zones(record.zones_json)
        }
        zones = [
            zone.model_copy(update={"revealed": revealed.get(zone.id, False)})
            for zone in blueprint.zones
        ]
        await database.execute(
            "UPDATE scenes SET name = ?, source = ?, blueprint_hash = ?, "
            "image_path = ?, image_width = ?, image_height = ?, grid_json = ?, "
            "zones_json = ?, fog_outside = ?, rev = rev + 1, updated_at = ? "
            "WHERE id = ?",
            (
                blueprint.name,
                blueprint.source,
                scenes.blueprint_hash(blueprint),
                blueprint.image.path,
                blueprint.image.width,
                blueprint.image.height,
                json.dumps(
                    blueprint.grid.model_dump(mode="json"),
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                _zone_text(zones),
                int(blueprint.fog_outside),
                int(time.time()),
                record.id,
            ),
        )
        await end_turns(database, table.id, "system")
        await _settle_round(database, table.id)


async def summary(
    database: Database,
    table: TableRow,
    *,
    viewer_id: str,
    role: TableRole,
    warning: str | None = None,
    root: Path | None = None,
) -> TableSummary:
    record = await _scene_for(database, table)
    zones, tokens, fog_outside = await _table_view(database, table, record)
    narrator = role == "narrator"
    public = visible_tokens(tokens, zones, fog_outside)
    public_ids = {token.id for token in public}
    return TableSummary(
        id=table.id,
        campaign=table.campaign,
        channel_id=table.channel_id,
        name=table.name,
        viewer_id=viewer_id,
        role=role,
        status=table.status,
        round=table.round,
        spectators=table.spectators,
        scene=_summary_scene(
            table,
            record,
            zones,
            fog_outside,
            narrator,
            root if narrator else None,
        ),
        tokens=_summary_tokens(tokens, public, narrator),
        turn=_table_turn(
            await _open_turn_row(database, table.id), narrator, public_ids
        ),
        participants=await _summary_participants(
            database, table, record, public
        ),
        warning=warning,
    )


async def _summary_participants(
    database: Database,
    table: TableRow,
    record: scenes.SceneRecord | None,
    public: list[TokenRow],
) -> list[TableParticipant]:
    if record is None:
        return []
    acted = await _acted_token_ids(database, table.id, record.id, table.round)
    return [
        TableParticipant(
            token_id=token.id,
            character_id=token.character_id,
            label=token.label,
            owner_id=token.owner_id,
            acted=token.id in acted,
        )
        for token in public
    ]


def _table_turn(
    turn: TurnRow | None, narrator: bool, public_ids: set[str]
) -> TableTurn | None:
    if turn is None:
        return None
    if narrator or turn.token_id in public_ids:
        return TableTurn(
            id=turn.id,
            round=turn.round,
            token_id=turn.token_id,
            character_id=turn.character_id,
            label=turn.label,
            owner_id=turn.owner_id,
            started_at=turn.started_at,
        )
    return TableTurn(
        id=turn.id,
        round=turn.round,
        token_id=None,
        character_id=None,
        label="",
        owner_id=None,
        started_at=turn.started_at,
    )


async def _table_view(
    database: Database,
    table: TableRow,
    record: scenes.SceneRecord | None,
) -> tuple[list[SceneZone], list[TokenRow], bool]:
    zones = [] if record is None else scenes.stored_zones(record.zones_json)
    tokens = await token_rows(database, table.id, table.current_scene_id)
    fog_outside = (
        False
        if record is None
        else await scene_fog_outside(database, record.id)
    )
    return zones, tokens, fog_outside


def visible_tokens(
    tokens: list[TokenRow], zones: list[SceneZone], fog_outside: bool
) -> list[TokenRow]:
    return [
        token for token in tokens if _token_public(token, zones, fog_outside)
    ]


@dataclass(frozen=True, slots=True)
class StreamState:
    table: TableRow
    record: scenes.SceneRecord | None
    zones: list[SceneZone]
    fog_outside: bool
    tokens: list[TokenRow]
    public: list[TokenRow]
    turn: TurnRow | None
    participants: list[TableParticipant]


async def stream_state(database: Database, table: TableRow) -> StreamState:
    record = await _scene_for(database, table)
    zones, tokens, fog_outside = await _table_view(database, table, record)
    public = visible_tokens(tokens, zones, fog_outside)
    return StreamState(
        table=table,
        record=record,
        zones=zones,
        fog_outside=fog_outside,
        tokens=tokens,
        public=public,
        turn=await _open_turn_row(database, table.id),
        participants=await _summary_participants(
            database, table, record, public
        ),
    )


async def open_table_ids(database: Database, campaign: str) -> list[str]:
    rows = await database.fetchall(
        "SELECT id FROM tables WHERE campaign_slug = ? AND status = 'open' "
        "ORDER BY opened_at, id",
        (campaign,),
    )
    return [str(row["id"]) for row in rows]


def scene_view(
    table: TableRow,
    record: scenes.SceneRecord | None,
    zones: list[SceneZone],
    fog_outside: bool,
    narrator: bool,
    root: Path | None,
) -> TableScene | None:
    return _summary_scene(table, record, zones, fog_outside, narrator, root)


def stream_turn(
    turn: TurnRow | None, narrator: bool, public_ids: set[str]
) -> TableTurn | None:
    return _table_turn(turn, narrator, public_ids)


def wire_token(token: TokenRow) -> TableToken:
    return _table_token(token)


def _summary_scene(
    table: TableRow,
    record: scenes.SceneRecord | None,
    zones: list[SceneZone],
    fog_outside: bool,
    narrator: bool,
    root: Path | None,
) -> TableScene | None:
    if record is None:
        return None
    shown, fog = _player_view(zones) if not narrator else (zones, [])
    return _table_scene(
        table, record, shown, fog, fog_outside, scene_saved(record, root)
    )


def _player_view(
    zones: list[SceneZone],
) -> tuple[list[SceneZone], list[SceneRect]]:
    shown = [zone for zone in zones if zone.revealed]
    fog = [rect for zone in zones if not zone.revealed for rect in zone.rects]
    return shown, fog


def scene_saved(record: scenes.SceneRecord, root: Path | None) -> bool:
    if root is None:
        return True
    blueprint = scenes.load_blueprint(root / record.blueprint_path)
    return (
        blueprint is not None
        and scenes.blueprint_hash(blueprint) == record.blueprint_hash
    )


def _summary_tokens(
    tokens: list[TokenRow],
    public: list[TokenRow],
    narrator: bool,
) -> list[TableToken]:
    shown = tokens if narrator else public
    return [_table_token(token) for token in shown]


def _table_scene(
    table: TableRow,
    record: scenes.SceneRecord,
    zones: list[SceneZone],
    fog: list[SceneRect],
    fog_outside: bool,
    saved: bool,
) -> TableScene:
    return TableScene(
        id=record.id,
        slug=PurePosixPath(record.blueprint_path).stem,
        name=record.name,
        source=record.source,
        width=record.image_width,
        height=record.image_height,
        grid=record.grid,
        fog_outside=fog_outside,
        zones=zones,
        fog=fog,
        map_url=f"/api/tables/{table.id}/map",
        saved=saved,
    )


def _table_token(token: TokenRow) -> TableToken:
    return TableToken(
        id=token.id,
        character_id=token.character_id,
        label=token.label,
        owner_id=token.owner_id,
        x=token.x,
        y=token.y,
        w=token.w,
        h=token.h,
        color=token.color,
        visible=token.visible,
        rev=token.rev,
    )


def snapshot_relative(campaign: str, table_id: str) -> str:
    return "/".join((
        *CAMPAIGN_ROOT,
        campaign,
        TABLES_FOLDER,
        f"{table_id}.json",
    ))


def snapshot_file(
    root: Path, campaign: str, table_id: str, stored: str | None = None
) -> Path:
    relative = stored or snapshot_relative(campaign, table_id)
    base = root.resolve()
    path = (base / relative).resolve()
    path.relative_to(base)
    return path


async def build_snapshot(
    database: Database, table: TableRow, *, status: TableStatus
) -> TableSnapshot:
    record = await _scene_for(database, table)
    tokens = await token_rows(database, table.id, table.current_scene_id)
    fog_outside = (
        False
        if record is None
        else await scene_fog_outside(database, record.id)
    )
    turn = None
    if status == "open":
        turn = await _open_turn(database, table.id)
    return TableSnapshot(
        version=SNAPSHOT_VERSION,
        kind=SNAPSHOT_KIND,
        saved_at=int(time.time()),
        rev=table.rev,
        table=SnapshotTable(
            id=table.id,
            campaign=table.campaign,
            channel_id=table.channel_id,
            name=table.name,
            status=status,
            round=table.round,
            current_scene_id=table.current_scene_id,
        ),
        scene=None if record is None else _snapshot_scene(record, fog_outside),
        tokens=[
            SnapshotToken(
                id=token.id,
                character_id=token.character_id,
                label=token.label,
                owner_id=token.owner_id,
                x=token.x,
                y=token.y,
                w=token.w,
                h=token.h,
                color=token.color,
                visible=token.visible,
            )
            for token in tokens
        ],
        turn=turn,
    )


def _snapshot_scene(
    record: scenes.SceneRecord, fog_outside: bool
) -> SnapshotScene:
    return SnapshotScene(
        id=record.id,
        name=record.name,
        blueprint_path=record.blueprint_path,
        blueprint_hash=record.blueprint_hash,
        image={
            "path": record.image_path,
            "width": record.image_width,
            "height": record.image_height,
        },
        grid=record.grid.model_dump(mode="json"),
        fog_outside=fog_outside,
        zones=scenes.stored_zones(record.zones_json),
    )


async def _open_turn(database: Database, table_id: str) -> SnapshotTurn | None:
    turn = await _open_turn_row(database, table_id)
    if turn is None:
        return None
    return SnapshotTurn(
        id=turn.id,
        round=turn.round,
        token_id=turn.token_id,
        character_id=turn.character_id,
        label=turn.label,
        started_at=turn.started_at,
    )


def write_snapshot(root: Path, snapshot: TableSnapshot) -> str:
    relative = snapshot_relative(snapshot.table.campaign, snapshot.table.id)
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        snapshot.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )
    atomic_write(path, f"{text}\n")
    return relative


def read_snapshot(path: Path) -> TableSnapshot | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        snapshot = TableSnapshot.model_validate(data)
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValidationError,
    ):
        return None
    if snapshot.version != SNAPSHOT_VERSION or snapshot.kind != SNAPSHOT_KIND:
        return None
    return snapshot


def _snapshot_file(root: Path, table: TableRow) -> Path | None:
    try:
        return snapshot_file(
            root, table.campaign, table.id, table.snapshot_path
        )
    except (OSError, ValueError):
        return None


async def close_table(
    database: Database, root: Path, table: TableRow
) -> TableRow:
    async with _lock(table.id):
        fresh = await _require_fresh_table(database, table.id)
        await end_turns(database, fresh.id, "system")
        snapshot = await build_snapshot(database, fresh, status="closed")
        relative = snapshot_relative(fresh.campaign, fresh.id)
        try:
            await asyncio.to_thread(write_snapshot, root, snapshot)
        except OSError as failure:
            raise SnapshotFailed(str(failure)) from failure
        now = int(time.time())
        await database.execute(
            "UPDATE tables SET status = 'closed', closed_at = ?, "
            "snapshot_path = ?, rev = rev + 1, updated_at = ? WHERE id = ?",
            (now, relative, now, fresh.id),
        )
        closed = await table_row(database, fresh.id)
        if closed is None:
            raise TableNotFound(fresh.id)
        return closed


async def reopen_table(
    database: Database, root: Path, table: TableRow
) -> tuple[TableRow, str | None]:
    async with _lock(table.id):
        fresh = await table_row(database, table.id)
        if fresh is None:
            raise TableNotFound(table.id)
        if fresh.status == "open":
            raise TableAlreadyOpen(fresh)
        await _refuse_other_open(database, fresh)
        await end_turns(database, fresh.id, "system")
        warning = None
        round_number = fresh.round + 1
        path = _snapshot_file(root, fresh)
        snapshot = None if path is None else read_snapshot(path)
        if snapshot is None:
            warning = SNAPSHOT_INVALID
        else:
            restored = await _restore_snapshot(database, fresh, snapshot)
            if restored is None:
                warning = SNAPSHOT_INVALID
            else:
                round_number = restored + 1
        now = int(time.time())
        await database.execute(
            "UPDATE tables SET status = 'open', round = ?, closed_by = NULL, "
            "closed_at = NULL, rev = rev + 1, updated_at = ? WHERE id = ?",
            (round_number, now, fresh.id),
        )
        opened = await table_row(database, fresh.id)
        if opened is None:
            raise TableNotFound(fresh.id)
        return opened, warning


async def _refuse_other_open(database: Database, table: TableRow) -> None:
    active = await _active_table(database, table.campaign, table.channel_id)
    if active is not None:
        raise TableAlreadyOpen(active)


async def _restore_snapshot(
    database: Database, table: TableRow, snapshot: TableSnapshot
) -> int | None:
    if (
        snapshot.table.id != table.id
        or snapshot.table.campaign != table.campaign
        or snapshot.scene is None
    ):
        return None
    scene = await scenes.scene_record_by_id(
        database, table.campaign, snapshot.scene.id
    )
    if scene is None:
        return None
    await _restore_scene(database, scene, snapshot.scene)
    await database.execute(
        "DELETE FROM tokens WHERE table_id = ? AND scene_id = ?",
        (table.id, scene.id),
    )
    now = int(time.time())
    for token in snapshot.tokens:
        await database.execute(
            "INSERT INTO tokens ("
            "id, table_id, scene_id, character_id, label, owner_id, x, y, w, "
            "h, color, visible, rev, created_at, updated_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
            (
                token.id,
                table.id,
                scene.id,
                token.character_id,
                token.label,
                token.owner_id,
                token.x,
                token.y,
                token.w,
                token.h,
                token.color,
                int(token.visible),
                now,
                now,
            ),
        )
    await database.execute(
        "UPDATE tables SET current_scene_id = ? WHERE id = ?",
        (scene.id, table.id),
    )
    return snapshot.table.round


async def _restore_scene(
    database: Database,
    scene: scenes.SceneRecord,
    snapshot: SnapshotScene,
) -> None:
    await database.execute(
        "UPDATE scenes SET zones_json = ?, fog_outside = ?, rev = rev + 1, "
        "updated_at = ? WHERE id = ?",
        (
            _zone_text(snapshot.zones),
            int(snapshot.fog_outside),
            int(time.time()),
            scene.id,
        ),
    )
