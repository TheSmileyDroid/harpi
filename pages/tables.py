from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TypeVar

from pydantic import BaseModel, ValidationError
from quart import Blueprint, Response, g, request, session
from quart_schema import (
    DataSource,
    document_request,
    document_response,
    validate_response,
)

from pages.api import error_response
from pages.campaigns import image_response, svg_response
from pages.guard import csrf_refusal
from src.panel import (
    scenes,
    state,
    tables,
    vault,
    vault_index,
)
from src.panel.campaigns import campaign_access
from src.panel.schemas import (
    ErrorDetail,
    ErrorEnvelope,
    TableConflictDetail,
    TableOpen,
    TableSceneChange,
    TableSpectators,
    TableSummary,
    TableTokenCreate,
    TableTokenPatch,
    TableRole,
)
from src.storage import get_database

BODY_MODEL = TypeVar("BODY_MODEL", bound=BaseModel)
BODY_BYTES = 64 * 1024
ALLOWED_GUILDS = "table_allowed_guilds"

bp = Blueprint("tables", __name__)


@bp.before_request
async def guard_table_request() -> Response | None:
    refusal = csrf_refusal()
    if refusal is not None:
        return refusal
    setattr(g, ALLOWED_GUILDS, await _guilds(_user_id()))
    return None


async def _guilds(user_id: str | None) -> frozenset[str]:
    if user_id is None:
        return frozenset()
    return frozenset(
        str(guild) for guild in await state.user_guild_ids(user_id)
    )


def _user_id() -> str | None:
    raw = session.get("user_id")
    return str(raw) if raw else None


def _allowed_guilds() -> frozenset[str]:
    return getattr(g, ALLOWED_GUILDS, frozenset())


def _not_found() -> Response:
    return error_response("not_found", "Not found", 404)


def _forbidden() -> Response:
    return error_response("forbidden", "Forbidden", 403)


def _closed() -> Response:
    return error_response("table_closed", "The table is closed", 409)


def _invalid(message: str) -> Response:
    return error_response("invalid_payload", message, 422)


def _conflict(active: tables.TableRow) -> Response:
    payload = TableConflictDetail(
        error=ErrorDetail(
            code="table_already_open",
            message="A table is already open in this campaign or channel",
        ),
        table={
            "id": active.id,
            "name": active.name,
            "channel_id": active.channel_id,
        },
    )
    return Response(
        payload.model_dump_json(), status=409, mimetype="application/json"
    )


@dataclass(frozen=True, slots=True)
class TableAccess:
    table: tables.TableRow
    user_id: str
    role: TableRole


async def _table_access(table_id: str) -> TableAccess | Response:
    user_id = _user_id()
    database = get_database()
    if user_id is None or database is None:
        return _not_found()
    row = await tables.table_row(database, table_id)
    if row is None:
        return _not_found()
    allowed = _allowed_guilds()
    if row.guild_id not in allowed:
        return _not_found()
    role = await _access_role(row, user_id, allowed)
    if role is None:
        return _not_found()
    return TableAccess(row, user_id, role)


async def _access_role(
    row: tables.TableRow, user_id: str, allowed: frozenset[str]
) -> TableRole | None:
    if row.narrator_id == user_id:
        return "narrator"
    access = campaign_access()
    campaign = (
        None
        if access is None
        else await access.campaign(row.campaign, user_id, allowed)
    )
    if campaign is not None:
        return campaign.role
    return "spectator" if row.spectators else None


async def _narrator_table(table_id: str) -> TableAccess | Response:
    access = await _table_access(table_id)
    if isinstance(access, Response):
        return access
    if access.role != "narrator":
        return _forbidden()
    if access.table.status != "open":
        return _closed()
    return access


async def _body(model: type[BODY_MODEL]) -> BODY_MODEL | Response:
    raw = await request.get_data()
    if len(raw) > BODY_BYTES:
        return error_response("payload_too_large", "Payload too large", 413)
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return error_response("bad_request", "Invalid JSON body", 400)
    if not isinstance(payload, dict):
        return error_response("bad_request", "Invalid JSON body", 400)
    try:
        return model.model_validate(payload)
    except ValidationError:
        return _invalid("Invalid table payload")


async def _summary(
    database, access: TableAccess, warning: str | None = None
) -> Response | TableSummary:
    return await tables.summary(
        database,
        access.table,
        viewer_id=access.user_id,
        role=access.role,
        warning=warning,
        root=vault.configured().root,
    )


async def _fresh(
    database, table_id: str, access: TableAccess
) -> Response | TableSummary:
    row = await tables.table_row(database, table_id)
    if row is None:
        return _not_found()
    return await _summary(
        database, TableAccess(row, access.user_id, access.role)
    )


@bp.post("/api/tables")
@document_request(TableOpen)
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(TableConflictDetail, 409)
@document_response(ErrorEnvelope, 422)
@validate_response(TableSummary, 200)
async def open_table() -> Response | TableSummary:
    payload = await _body(TableOpen)
    if isinstance(payload, Response):
        return payload
    user_id = await _narrator_user(payload.campaign)
    if isinstance(user_id, Response):
        return user_id
    database = get_database()
    if database is None:
        return _not_found()
    try:
        row = await tables.open_table(
            database,
            campaign=payload.campaign,
            narrator_id=user_id,
            channel_id=payload.channel_id,
            name=payload.name or "Sessão",
            scene=payload.scene,
        )
    except tables.SceneNotFound:
        return _not_found()
    except tables.TableAlreadyOpen as failure:
        return _conflict(failure.table)
    return await _summary(database, TableAccess(row, user_id, "narrator"))


async def _narrator_user(campaign: str) -> str | Response:
    user_id = _user_id()
    access = campaign_access()
    if user_id is None or access is None:
        return _not_found()
    detail = await access.campaign(campaign, user_id, _allowed_guilds())
    if detail is None:
        return _not_found()
    return user_id if detail.role == "narrator" else _forbidden()


@bp.get("/api/tables/<table_id>/summary")
@document_response(ErrorEnvelope, 404)
@validate_response(TableSummary, 200)
async def read_summary(table_id: str) -> Response | TableSummary:
    access = await _table_access(table_id)
    if isinstance(access, Response):
        return access
    database = get_database()
    if database is None:
        return _not_found()
    return await _summary(database, access)


@bp.get("/api/tables/<table_id>/map")
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 503)
async def read_map(table_id: str) -> Response:
    access = await _table_access(table_id)
    if isinstance(access, Response):
        return access
    database = get_database()
    if database is None:
        return _not_found()
    if not vault.configured().available:
        return error_response("vault_unavailable", "Vault unavailable", 503)
    record = await _current_scene(database, access.table)
    if record is None:
        return _not_found()
    if record.source == "sketch":
        return await _sketch_response(access.table, record)
    path = vault_index.configured().portrait_path(record.image_path)
    if path is None:
        return _not_found()
    return await image_response(path)


async def _current_scene(
    database, table: tables.TableRow
) -> scenes.SceneRecord | None:
    if table.current_scene_id is None:
        return None
    return await scenes.scene_record_by_id(
        database, table.campaign, table.current_scene_id
    )


async def _sketch_response(
    table: tables.TableRow, record: scenes.SceneRecord
) -> Response:
    root = vault.configured().root
    if root is None:
        return _not_found()
    path = _sketch_map_path(root, table.campaign, record)
    if path is None:
        return _not_found()
    return await svg_response(path)


def _sketch_map_path(
    root: Path, campaign: str, record: scenes.SceneRecord
) -> Path | None:
    slug = PurePosixPath(record.blueprint_path).stem
    expected = scenes.sketch_image_path(campaign, slug)
    if record.image_path != expected:
        return None
    try:
        base = root.resolve()
        path = (base / expected).resolve()
        path.relative_to(base)
    except (OSError, ValueError):
        return None
    if path.suffix.casefold() != ".svg" or not path.is_file():
        return None
    return path


@bp.post("/api/tables/<table_id>/close")
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 409)
@document_response(ErrorEnvelope, 503)
@validate_response(TableSummary, 200)
async def close_table(table_id: str) -> Response | TableSummary:
    access = await _narrator_table(table_id)
    if isinstance(access, Response):
        return access
    database = get_database()
    root = vault.configured().root
    if database is None or root is None:
        return error_response(
            "snapshot_failed", "The table snapshot could not be written", 503
        )
    try:
        row = await tables.close_table(database, root, access.table)
    except tables.SnapshotFailed:
        return error_response(
            "snapshot_failed", "The table snapshot could not be written", 503
        )
    return await _summary(
        database, TableAccess(row, access.user_id, access.role)
    )


@bp.post("/api/tables/<table_id>/reopen")
@document_response(ErrorEnvelope, 404)
@document_response(TableConflictDetail, 409)
@document_response(ErrorEnvelope, 503)
@validate_response(TableSummary, 200)
async def reopen_table(table_id: str) -> Response | TableSummary:
    access = await _table_access(table_id)
    if isinstance(access, Response):
        return access
    if access.role != "narrator":
        return _forbidden()
    database = get_database()
    root = vault.configured().root
    if database is None or root is None:
        return error_response(
            "snapshot_failed", "The table snapshot could not be read", 503
        )
    try:
        row, warning = await tables.reopen_table(database, root, access.table)
    except tables.TableAlreadyOpen as failure:
        return _conflict(failure.table)
    return await _summary(
        database,
        TableAccess(row, access.user_id, access.role),
        warning,
    )


@bp.post("/api/tables/<table_id>/scene")
@document_request(TableSceneChange)
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 409)
@validate_response(TableSummary, 200)
async def change_scene(table_id: str) -> Response | TableSummary:
    access = await _narrator_table(table_id)
    if isinstance(access, Response):
        return access
    payload = await _body(TableSceneChange)
    if isinstance(payload, Response):
        return payload
    database = get_database()
    if database is None:
        return _not_found()
    try:
        await tables.change_scene(database, access.table, payload.scene)
    except tables.SceneNotFound:
        return _not_found()
    return await _fresh(database, table_id, access)


@bp.post("/api/tables/<table_id>/scene/reload")
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 409)
@document_response(ErrorEnvelope, 503)
@validate_response(TableSummary, 200)
async def reload_scene(table_id: str) -> Response | TableSummary:
    access = await _narrator_table(table_id)
    if isinstance(access, Response):
        return access
    database = get_database()
    root = vault.configured().root
    if database is None:
        return _not_found()
    if root is None:
        return error_response("vault_unavailable", "Vault unavailable", 503)
    try:
        await tables.reload_scene(database, root, access.table)
    except tables.SceneUnreadable:
        return error_response(
            "scene_unreadable", "The scene file cannot be read", 409
        )
    except tables.SceneNotFound:
        return _not_found()
    return await _fresh(database, table_id, access)


@bp.post("/api/tables/<table_id>/zones/<zone_id>/reveal")
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 409)
@validate_response(TableSummary, 200)
async def reveal_zone(table_id: str, zone_id: str) -> Response | TableSummary:
    return await _set_zone(table_id, zone_id, revealed=True)


@bp.post("/api/tables/<table_id>/zones/<zone_id>/hide")
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 409)
@validate_response(TableSummary, 200)
async def hide_zone(table_id: str, zone_id: str) -> Response | TableSummary:
    return await _set_zone(table_id, zone_id, revealed=False)


async def _set_zone(
    table_id: str, zone_id: str, *, revealed: bool
) -> Response | TableSummary:
    access = await _narrator_table(table_id)
    if isinstance(access, Response):
        return access
    database = get_database()
    if database is None:
        return _not_found()
    try:
        await tables.set_zone(
            database,
            access.table,
            zone_id,
            revealed=revealed,
            actor_id=access.user_id,
        )
    except tables.ZoneNotFound:
        return _not_found()
    except tables.SceneNotFound:
        return _not_found()
    return await _fresh(database, table_id, access)


@bp.post("/api/tables/<table_id>/tokens")
@document_request(TableTokenCreate)
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 409)
@document_response(ErrorEnvelope, 422)
@validate_response(TableSummary, 200)
async def create_token(table_id: str) -> Response | TableSummary:
    access = await _narrator_table(table_id)
    if isinstance(access, Response):
        return access
    payload = await _body(TableTokenCreate)
    if isinstance(payload, Response):
        return payload
    database = get_database()
    if database is None:
        return _not_found()
    try:
        await tables.create_token(database, access.table, payload)
    except ValueError as failure:
        return _invalid(str(failure))
    except tables.SceneNotFound:
        return _not_found()
    return await _fresh(database, table_id, access)


@bp.patch("/api/tables/<table_id>/tokens/<token_id>")
@document_request(TableTokenPatch)
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 409)
@document_response(ErrorEnvelope, 422)
@validate_response(TableSummary, 200)
async def patch_token(table_id: str, token_id: str) -> Response | TableSummary:
    access = await _narrator_table(table_id)
    if isinstance(access, Response):
        return access
    payload = await _body(TableTokenPatch)
    if isinstance(payload, Response):
        return payload
    database = get_database()
    if database is None:
        return _not_found()
    try:
        await tables.update_token(database, access.table, token_id, payload)
    except tables.TokenNotFound:
        return _not_found()
    except ValueError as failure:
        return _invalid(str(failure))
    except tables.SceneNotFound:
        return _not_found()
    return await _fresh(database, table_id, access)


@bp.delete("/api/tables/<table_id>/tokens/<token_id>")
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 409)
@validate_response(TableSummary, 200)
async def delete_token(
    table_id: str, token_id: str
) -> Response | TableSummary:
    access = await _narrator_table(table_id)
    if isinstance(access, Response):
        return access
    database = get_database()
    if database is None:
        return _not_found()
    try:
        await tables.delete_token(database, access.table, token_id)
    except tables.TokenNotFound:
        return _not_found()
    return await _fresh(database, table_id, access)


@bp.post("/api/tables/<table_id>/spectators")
@document_request(TableSpectators, source=DataSource.JSON)
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 409)
@validate_response(TableSummary, 200)
async def set_spectators(table_id: str) -> Response | TableSummary:
    access = await _narrator_table(table_id)
    if isinstance(access, Response):
        return access
    payload = await _body(TableSpectators)
    if isinstance(payload, Response):
        return payload
    database = get_database()
    if database is None:
        return _not_found()
    await tables.set_spectators(database, access.table, payload.enabled)
    return await _fresh(database, table_id, access)
