from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path

from loguru import logger
from pydantic import ValidationError
from quart import Blueprint, Response, g, request, send_file, session
from quart_schema import (
    document_request,
    document_response,
    validate_response,
)
from werkzeug.http import http_date

from pages.api import error_response, rate_limit_response
from pages.guard import csrf_refusal, vault_unavailable
from src.panel import (
    notes,
    rate_limit,
    sheet_store,
    sheet_write,
    state,
    vault_index,
)
from src.panel.campaigns import campaign_access
from src.panel.cast import campaign_cast, sheet_detail
from src.panel.schemas import (
    CampaignDetail,
    CampaignList,
    CampaignRole,
    CharacterDetail,
    CharacterList,
    ErrorEnvelope,
    SheetDetail,
    SheetPatch,
)
from src.panel.sheets import default_config
from src.panel.notes import SheetNote
from src.panel.vault_index import (
    PORTRAIT_TYPES,
    VaultIndex,
    configured,
    locate_note,
)
from src.storage import get_database
from src.storage.database import Database

bp = Blueprint("campaigns", __name__)

ALLOWED_GUILDS = "campaign_allowed_guilds"
PORTRAIT_CACHE = "private, max-age=60, must-revalidate"
SHEET_BODY_BYTES = 64 * 1024
SHEET_WRITE_BUCKETS = rate_limit.UserTokenBuckets(
    rate_limit.SHEET_WRITES_PER_MINUTE
)


@bp.before_request
async def guard_campaign_request() -> Response | None:
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
    return error_response("not_found", "Campaign not found", 404)


def _hidden() -> Response:
    return error_response("not_found", "Not found", 404)


def _vault_not_ready() -> Response:
    return error_response("vault_unavailable", "Vault unavailable", 503)


async def characters_page_refusal(slug: str) -> Response | None:
    user_id = _user_id()
    if user_id is None:
        return None
    access = campaign_access()
    if access is None:
        return Response("Not Found", status=404)
    campaign = await access.campaign(slug, user_id, await _guilds(user_id))
    if campaign is None:
        return Response("Not Found", status=404)
    return None


@bp.get("/api/campaigns")
@validate_response(CampaignList, 200)
async def read_campaigns() -> Response | CampaignList:
    access = campaign_access()
    user_id = _user_id()
    if access is None or user_id is None:
        return CampaignList(campaigns=[])
    campaigns = await access.campaigns(user_id, _allowed_guilds())
    return CampaignList(campaigns=campaigns)


@bp.get("/api/campaigns/<slug>")
@document_response(ErrorEnvelope, 404)
@validate_response(CampaignDetail, 200)
async def read_campaign(slug: str) -> Response | CampaignDetail:
    access = campaign_access()
    user_id = _user_id()
    if access is None or user_id is None:
        return _not_found()
    campaign = await access.campaign(slug, user_id, _allowed_guilds())
    if campaign is None:
        return _not_found()
    return campaign.model_copy(
        update={"config_error": configured().campaign(slug).config_error}
    )


@bp.get("/api/campaigns/<slug>/characters")
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 503)
@validate_response(CharacterList, 200)
async def read_characters(slug: str) -> Response | CharacterList:
    scope = await _character_scope(slug)
    if isinstance(scope, Response):
        return scope
    user_id, role = scope
    cast = campaign_cast()
    if cast is None:
        return _vault_not_ready()
    return CharacterList(characters=await cast.roster(slug, user_id, role))


@bp.get("/api/campaigns/<slug>/characters/<character_id>")
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 503)
@validate_response(CharacterDetail, 200)
async def read_character(
    slug: str, character_id: str
) -> Response | CharacterDetail:
    scope = await _character_scope(slug)
    if isinstance(scope, Response):
        return scope
    user_id, role = scope
    cast = campaign_cast()
    if cast is None:
        return _vault_not_ready()
    detail = await cast.character(slug, character_id, user_id, role)
    if detail is None:
        return _hidden()
    return detail


@bp.patch("/api/campaigns/<slug>/sheets/<sheet_id>")
@document_request(SheetPatch)
@document_response(ErrorEnvelope, 400)
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 409)
@document_response(ErrorEnvelope, 413)
@document_response(ErrorEnvelope, 422)
@document_response(ErrorEnvelope, 429)
@document_response(ErrorEnvelope, 503)
@validate_response(SheetDetail, 200)
async def write_sheet(slug: str, sheet_id: str) -> Response | SheetDetail:
    scope = await _character_scope(slug)
    if isinstance(scope, Response):
        return scope
    user_id, role = scope
    patch = await _prepared_patch()
    if isinstance(patch, Response):
        return patch
    index = vault_index.configured()
    target = await _write_target(index, slug, sheet_id, user_id, role, patch)
    if isinstance(target, Response):
        return target
    note, database, record = target
    result = await _run_write(
        database, index, slug, sheet_id, note, patch, record
    )
    if isinstance(result, Response):
        return result
    persisted = await _persist_or_restore(database, index, slug, note, result)
    if isinstance(persisted, Response):
        return persisted
    fresh = (
        index.refresh_sheet(note.path)
        or notes.parse_sheet(note.path, result.text).note
    )
    return sheet_detail(
        replace(fresh, character=note.character),
        index.campaign(slug).config or default_config(),
        result.warnings,
    )


async def _prepared_patch() -> SheetPatch | Response:
    refusal = rate_limit_response(SHEET_WRITE_BUCKETS)
    if refusal is not None:
        return refusal
    raw = await request.get_data()
    if len(raw) > SHEET_BODY_BYTES:
        return error_response("payload_too_large", "Payload too large", 413)
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return error_response("bad_request", "Invalid JSON body", 400)
    if not isinstance(payload, dict):
        return error_response("bad_request", "Invalid JSON body", 400)
    try:
        return SheetPatch.model_validate(payload)
    except ValidationError:
        return error_response("invalid_payload", "Invalid sheet payload", 422)


async def _write_target(
    index: VaultIndex,
    slug: str,
    sheet_id: str,
    user_id: str,
    role: CampaignRole,
    patch: SheetPatch,
) -> tuple[SheetNote, Database, sheet_write.SheetRecord | None] | Response:
    note = _find_sheet(index, slug, sheet_id)
    if note is None:
        return _hidden()
    database = get_database()
    if database is None:
        return _not_found()
    record = await sheet_store.sheet_record(database, note.path)
    refusal = _owner_refusal(note, record, user_id, role, patch)
    if refusal is not None:
        return refusal
    return note, database, record


def _owner_refusal(
    note: SheetNote,
    record: sheet_write.SheetRecord | None,
    user_id: str,
    role: CampaignRole,
    patch: SheetPatch,
) -> Response | None:
    owner = (
        record.owner
        if record is not None and record.owner is not None
        else note.owner
    )
    if role == "narrator":
        return None
    if owner != user_id:
        return error_response("forbidden", "Forbidden", 403)
    if patch.status == "active" and note.status == "arquivado":
        return error_response(
            "forbidden", "Only the narrator can unarchive a sheet", 403
        )
    return None


async def _persist_or_restore(
    database: Database,
    index: VaultIndex,
    slug: str,
    note: SheetNote,
    result: sheet_write.SheetWriteResult,
) -> Response | None:
    try:
        await sheet_store.store_sheet(database, slug, note.path, result)
    except Exception as failure:
        logger.opt(exception=True).error(f"Sheet storage failed: {failure}")
        root = index.root
        if root is not None:
            await asyncio.to_thread(
                sheet_write.restore_sheet,
                root / note.path,
                result.previous_text,
            )
        return error_response(
            "storage_unavailable", "Sheet storage failed", 503
        )
    return None


async def _run_write(
    database: Database,
    index: VaultIndex,
    slug: str,
    sheet_id: str,
    note: SheetNote,
    patch: SheetPatch,
    record: sheet_write.SheetRecord | None,
) -> sheet_write.SheetWriteResult | Response:
    root = index.root
    if root is None:
        return _vault_not_ready()
    try:
        return await asyncio.to_thread(
            sheet_write.write_sheet,
            root / note.path,
            slug,
            sheet_id,
            patch,
            index.campaign(slug).config or default_config(),
            record,
            sheet_store.backup_root(database),
        )
    except sheet_write.SheetWriteError as failure:
        return _write_failure(failure)


def _write_failure(failure: sheet_write.SheetWriteError) -> Response:
    if isinstance(failure, sheet_write.SheetConflict):
        return error_response("sheet_conflict", "Sheet changed on disk", 409)
    if isinstance(failure, sheet_write.SheetInvalid):
        return error_response("sheet_invalid", str(failure), 422)
    if isinstance(failure, sheet_write.SheetReadOnly):
        return error_response("sheet_read_only", str(failure), 403)
    return error_response("invalid_sheet", str(failure), 422)


def _find_sheet(
    index: VaultIndex, slug: str, sheet_id: str
) -> SheetNote | None:
    for note in index.campaign(slug).sheets:
        if note.id != sheet_id:
            continue
        place = locate_note(note.path)
        return note if place is not None and place[1] == "sheets" else None
    return None


@bp.get("/api/campaigns/<slug>/characters/<character_id>/portrait")
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 503)
async def read_portrait(slug: str, character_id: str) -> Response:
    scope = await _character_scope(slug)
    if isinstance(scope, Response):
        return scope
    user_id, role = scope
    cast = campaign_cast()
    if cast is None:
        return _vault_not_ready()
    member = await cast.member(slug, character_id, user_id, role)
    path = None if member is None else cast.portrait(member)
    if path is None:
        return _hidden()
    return await _portrait_response(path)


async def _character_scope(
    slug: str,
) -> tuple[str, CampaignRole] | Response:
    unavailable = vault_unavailable()
    if unavailable is not None:
        return unavailable
    access = campaign_access()
    user_id = _user_id()
    if access is None or user_id is None:
        return _not_found()
    campaign = await access.campaign(slug, user_id, _allowed_guilds())
    if campaign is None:
        return _not_found()
    return user_id, campaign.role


async def _portrait_response(path: Path) -> Response:
    try:
        stat = path.stat()
    except OSError:
        return _hidden()
    token = f"{stat.st_mtime_ns:x}-{stat.st_size:x}"
    etag = f'"{token}"'
    headers = {
        "Cache-Control": PORTRAIT_CACHE,
        "ETag": etag,
        "Last-Modified": http_date(stat.st_mtime),
    }
    if request.if_none_match.contains(token):
        return Response(status=304, headers=headers)
    response = await send_file(
        path,
        mimetype=PORTRAIT_TYPES[path.suffix.casefold()],
        conditional=False,
    )
    response.headers.update(headers)
    return response
