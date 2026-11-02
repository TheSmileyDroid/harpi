from __future__ import annotations

import asyncio
import json
from collections.abc import Iterable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TypeVar

from loguru import logger
from pydantic import BaseModel, ValidationError
from quart import Blueprint, Response, g, request, send_file, session
from quart_schema import (
    DataSource,
    document_request,
    document_response,
    validate_response,
)
from werkzeug.http import http_date

from pages.api import error_response, rate_limit_response
from pages.guard import csrf_refusal, vault_unavailable
from src.panel import (
    assets,
    enrollment,
    notes,
    rate_limit,
    scenes,
    sheet_conflicts,
    sheet_store,
    sheet_write,
    state,
    vault,
    vault_index,
)
from src.panel.character_notes import InvalidName
from src.panel.campaigns import campaign_access
from src.panel.cast import campaign_cast, sheet_detail
from src.panel.schemas import (
    ApprovalDecision,
    ApprovalItem,
    ApprovalList,
    AssetDetail,
    AssetUpload,
    CampaignDetail,
    CampaignList,
    CampaignRole,
    CharacterCreate,
    CharacterDetail,
    CharacterList,
    ErrorDetail,
    ErrorEnvelope,
    SceneCreate,
    SceneDetail,
    SceneList,
    SceneSave,
    SheetActionResult,
    SheetConflictDecision,
    SheetConflictDetail,
    SheetConflictField,
    SheetConflictList,
    SheetDetail,
    SheetPatch,
)
from src.panel.sheets import default_config
from src.panel.notes import SheetNote
from src.panel.vault_index import (
    IMAGE_TYPES,
    VaultIndex,
    configured,
    locate_note,
)
from src.storage import get_database
from src.storage.database import Database

BODY_MODEL = TypeVar("BODY_MODEL", bound=BaseModel)

bp = Blueprint("campaigns", __name__)

ALLOWED_GUILDS = "campaign_allowed_guilds"
IMAGE_CACHE = "private, max-age=60, must-revalidate"
SHEET_BODY_BYTES = 64 * 1024
UPLOAD_ENDPOINT = "campaigns.upload_asset"
SHEET_WRITE_BUCKETS = rate_limit.UserTokenBuckets(
    rate_limit.SHEET_WRITES_PER_MINUTE
)
APPROVAL_BUCKETS = rate_limit.UserTokenBuckets(rate_limit.APPROVALS_PER_MINUTE)
ASSET_READ_BUCKETS = rate_limit.UserTokenBuckets(
    rate_limit.ASSET_READS_PER_MINUTE
)
ASSET_UPLOAD_BUCKETS = rate_limit.UserTokenBuckets(
    rate_limit.ASSET_UPLOADS_PER_MINUTE
)
SCENE_WRITE_BUCKETS = rate_limit.UserTokenBuckets(
    rate_limit.SCENE_WRITES_PER_MINUTE
)


@bp.before_request
async def guard_campaign_request() -> Response | None:
    refusal = csrf_refusal(allow_multipart=request.endpoint == UPLOAD_ENDPOINT)
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


def _vault_write_failure(failure: Exception) -> Response:
    logger.opt(exception=failure).error(f"Vault write failed: {failure}")
    return error_response("vault_write_failed", _failure_reason(failure), 503)


def _storage_failure(failure: Exception) -> Response:
    logger.opt(exception=failure).error(f"Sheet storage failed: {failure}")
    return error_response("storage_unavailable", _failure_reason(failure), 503)


def _failure_reason(failure: Exception) -> str:
    cause = failure.__cause__
    return str(cause) if cause is not None else str(failure)


def _forbidden() -> Response:
    return error_response("forbidden", "Forbidden", 403)


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
    return CharacterList(
        characters=await cast.roster(slug, user_id, role),
        own_character_id=await cast.own_character_id(slug, user_id),
    )


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


@dataclass(frozen=True, slots=True)
class WriteContext:
    slug: str
    note: SheetNote
    database: Database
    record: sheet_write.SheetRecord | None
    index: vault_index.VaultIndex
    patch: SheetPatch


@dataclass(frozen=True, slots=True)
class RestoreContext:
    database: Database
    index: vault_index.VaultIndex
    root: Path
    stored: sheet_store.StoredSheet


@dataclass(frozen=True, slots=True)
class CreationContext:
    database: Database
    index: VaultIndex
    user_id: str
    narrator: bool


@bp.post("/api/campaigns/<slug>/characters")
@document_request(CharacterCreate)
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 409)
@document_response(ErrorEnvelope, 422)
@document_response(ErrorEnvelope, 429)
@document_response(ErrorEnvelope, 503)
@validate_response(CharacterDetail, 200)
async def create_character(slug: str) -> Response | CharacterDetail:
    context = await _creation_context(slug)
    if isinstance(context, Response):
        return context
    refusal = rate_limit_response(SHEET_WRITE_BUCKETS)
    if refusal is not None:
        return refusal
    payload = await _json_model(CharacterCreate, "Invalid character payload")
    if isinstance(payload, Response):
        return payload
    try:
        created = await enrollment.create_character(
            context.database,
            context.index,
            slug=slug,
            name=payload.name,
            concept=payload.concept,
            summary=payload.summary,
            user_id=context.user_id,
            display_name=session.get("username"),
            narrator=context.narrator,
            with_sheet=payload.sheet,
        )
    except (enrollment.EnrollmentError, InvalidName) as failure:
        return _creation_failure(failure)
    await _reload_vault()
    role: CampaignRole = "narrator" if context.narrator else "pending"
    return await _character_detail(
        slug, created.character_id, context.user_id, role
    )


async def _creation_context(slug: str) -> CreationContext | Response:
    unavailable = vault_unavailable()
    if unavailable is not None:
        return unavailable
    access = campaign_access()
    database = get_database()
    user_id = _user_id()
    if access is None or database is None or user_id is None:
        return _not_found()
    scope = await access.scope(slug, user_id, _allowed_guilds())
    if scope is None:
        return _not_found()
    index = configured()
    if not index.available:
        return _vault_not_ready()
    return CreationContext(
        database=database,
        index=index,
        user_id=user_id,
        narrator=scope.narrator_id == user_id,
    )


def _creation_failure(failure: Exception) -> Response:
    if isinstance(failure, InvalidName):
        return error_response("invalid_payload", str(failure), 422)
    if isinstance(failure, enrollment.InvalidRequest):
        return error_response("invalid_payload", str(failure), 422)
    if isinstance(failure, enrollment.NameTaken):
        return error_response(
            "character_exists", "A note with this name already exists", 409
        )
    if isinstance(failure, enrollment.SheetAlreadyExists):
        return error_response(
            "sheet_already_exists",
            "You already have a pending or active sheet",
            409,
        )
    if isinstance(failure, enrollment.VaultWriteFailed):
        return _vault_write_failure(failure)
    return _storage_failure(failure)


async def _character_detail(
    slug: str, character_id: str, user_id: str, role: CampaignRole
) -> Response | CharacterDetail:
    cast = campaign_cast()
    if cast is None:
        return _vault_not_ready()
    detail = await cast.character(slug, character_id, user_id, role)
    return detail if detail is not None else _hidden()


@bp.post("/api/campaigns/<slug>/sheets/<sheet_id>/submit")
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 409)
@document_response(ErrorEnvelope, 503)
@validate_response(SheetDetail, 200)
async def submit_sheet(slug: str, sheet_id: str) -> Response | SheetDetail:
    scope = await _character_scope(slug)
    if isinstance(scope, Response):
        return scope
    user_id, role = scope
    if role == "narrator":
        return _forbidden()
    target = _database_index()
    if isinstance(target, Response):
        return target
    database, index = target
    try:
        await enrollment.submit(
            database, index, slug=slug, sheet_id=sheet_id, user_id=user_id
        )
    except enrollment.EnrollmentError as failure:
        return _submit_failure(failure)
    await _reload_vault()
    return _sheet_response(slug, sheet_id)


def _submit_failure(failure: enrollment.EnrollmentError) -> Response:
    if isinstance(failure, enrollment.ApprovalNotFound):
        return _hidden()
    if isinstance(failure, enrollment.NotOwner):
        return _forbidden()
    if isinstance(failure, enrollment.NotSubmittable):
        return error_response(
            "sheet_not_pending", "The sheet is not awaiting approval", 409
        )
    if isinstance(failure, enrollment.VaultWriteFailed):
        return _vault_write_failure(failure)
    return _storage_failure(failure)


def _database_index() -> tuple[Database, VaultIndex] | Response:
    database = get_database()
    index = configured()
    if database is None:
        return _not_found()
    if not index.available:
        return _vault_not_ready()
    return database, index


def _sheet_response(slug: str, sheet_id: str) -> Response | SheetDetail:
    index = configured()
    note = _find_sheet(index, slug, sheet_id)
    if note is None:
        return _hidden()
    return sheet_detail(
        note,
        index.campaign(slug).config or default_config(),
        archived=note.status == "arquivado",
    )


@bp.get("/api/campaigns/<slug>/approvals")
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 503)
@validate_response(ApprovalList, 200)
async def read_approvals(slug: str) -> Response | ApprovalList:
    user = await _narrator(slug)
    if isinstance(user, Response):
        return user
    return await _approval_queue(slug)


async def _narrator(slug: str) -> str | Response:
    scope = await _character_scope(slug)
    if isinstance(scope, Response):
        return scope
    user_id, role = scope
    return user_id if role == "narrator" else _forbidden()


@bp.post("/api/campaigns/<slug>/approvals/<approval_id>")
@document_request(ApprovalDecision)
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 422)
@document_response(ErrorEnvelope, 429)
@document_response(ErrorEnvelope, 503)
@validate_response(ApprovalList, 200)
async def decide_approval(
    slug: str, approval_id: str
) -> Response | ApprovalList:
    user = await _narrator(slug)
    if isinstance(user, Response):
        return user
    payload = await _decision_payload()
    if isinstance(payload, Response):
        return payload
    target = _database_index()
    if isinstance(target, Response):
        return target
    database, index = target
    try:
        await enrollment.decide(
            database,
            index,
            slug=slug,
            approval_id=approval_id,
            decision=payload.decision,
            note=payload.note,
            actor_id=user,
        )
    except enrollment.EnrollmentError as failure:
        return _decision_failure(failure)
    await _reload_vault()
    return await _approval_queue(slug)


async def _decision_payload() -> ApprovalDecision | Response:
    refusal = rate_limit_response(APPROVAL_BUCKETS)
    if refusal is not None:
        return refusal
    payload = await _json_model(ApprovalDecision, "Invalid approval payload")
    if isinstance(payload, Response):
        return payload
    if payload.decision == enrollment.REJECT and not payload.note.strip():
        return error_response(
            "invalid_payload", "A rejection needs a note", 422
        )
    return payload


def _decision_failure(failure: enrollment.EnrollmentError) -> Response:
    if isinstance(failure, enrollment.ApprovalNotFound):
        return _hidden()
    if isinstance(failure, enrollment.AlreadyDecided):
        return error_response(
            "approval_already_decided",
            "This approval was already decided",
            409,
        )
    if isinstance(failure, enrollment.InvalidRequest):
        return error_response("invalid_payload", str(failure), 422)
    if isinstance(failure, enrollment.VaultWriteFailed):
        return _vault_write_failure(failure)
    return _storage_failure(failure)


async def _approval_queue(slug: str) -> Response | ApprovalList:
    target = _database_index()
    if isinstance(target, Response):
        return target
    database, index = target
    pending = await enrollment.pending_approvals(database, index, slug)
    return ApprovalList(
        approvals=[
            ApprovalItem(
                id=item.id,
                sheet_id=item.sheet_id,
                character_id=item.character_id,
                character_name=item.character_name,
                owner=item.owner,
                owner_name=item.owner_name,
                note=item.note,
                requested_at=item.requested_at,
            )
            for item in pending
        ]
    )


async def _reload_vault() -> None:
    await vault_index.refresh_once(vault.configured())


@bp.patch("/api/campaigns/<slug>/sheets/<sheet_id>")
@document_request(SheetPatch)
@document_response(ErrorEnvelope, 400)
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(SheetConflictDetail, 409)
@document_response(ErrorEnvelope, 413)
@document_response(ErrorEnvelope, 422)
@document_response(ErrorEnvelope, 429)
@document_response(ErrorEnvelope, 503)
@validate_response(SheetDetail, 200)
async def write_sheet(slug: str, sheet_id: str) -> Response | SheetDetail:
    context = await _write_context(slug, sheet_id)
    if isinstance(context, Response):
        return context
    return await _write_and_answer(context)


async def _write_context(slug: str, sheet_id: str) -> WriteContext | Response:
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
    return WriteContext(slug, note, database, record, index, patch)


async def _write_and_answer(
    context: WriteContext,
) -> Response | SheetDetail:
    try:
        result = await _run_write(
            context.database,
            context.index,
            context.slug,
            context.note.id,
            context.note,
            context.patch,
            context.record,
        )
    except sheet_write.SheetMergeConflict as failure:
        rows = await sheet_conflicts.record(
            context.database,
            context.note.path,
            failure.patch,
            failure.conflicts,
            failure.base_json,
        )
        return _conflict_detail(rows)
    if isinstance(result, Response):
        return result
    persisted = await _commit_write(
        context.database, context.index, context.slug, context.note, result
    )
    if isinstance(persisted, Response):
        return persisted
    fresh = (
        context.index.refresh_sheet(context.note.path)
        or notes.parse_sheet(context.note.path, result.text).note
    )
    return sheet_detail(
        replace(fresh, character=context.note.character),
        context.index.campaign(context.slug).config or default_config(),
        result.warnings,
    )


async def _commit_write(
    database: Database,
    index: VaultIndex,
    slug: str,
    note: SheetNote,
    result: sheet_write.SheetWriteResult,
) -> Response | None:
    mirror = await _mirror_sheet_status(database, index, slug, note, result)
    if isinstance(mirror, Response):
        return mirror
    return await _persist_or_restore(
        database, index, slug, note, result, mirror
    )


async def _mirror_sheet_status(
    database: Database,
    index: VaultIndex,
    slug: str,
    note: SheetNote,
    result: sheet_write.SheetWriteResult,
) -> enrollment.StatusMirror | Response | None:
    try:
        return await asyncio.to_thread(
            enrollment.mirror_character_status,
            database,
            index,
            slug=slug,
            character_id=note.character,
            status=result.status,
        )
    except enrollment.VaultWriteFailed as failure:
        root = index.root
        if root is not None:
            await asyncio.to_thread(
                sheet_write.restore_sheet,
                root / note.path,
                result.previous_text,
            )
        return _vault_write_failure(failure)


async def _prepared_patch() -> SheetPatch | Response:
    refusal = rate_limit_response(SHEET_WRITE_BUCKETS)
    if refusal is not None:
        return refusal
    return await _json_model(SheetPatch, "Invalid sheet payload")


async def _json_model(
    model: type[BODY_MODEL], message: str
) -> BODY_MODEL | Response:
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
        return model.model_validate(payload)
    except ValidationError:
        return error_response("invalid_payload", message, 422)


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
    refusal = _write_refusal(note, record, user_id, role, patch)
    if refusal is not None:
        return refusal
    return note, database, record


def _write_refusal(
    note: SheetNote,
    record: sheet_write.SheetRecord | None,
    user_id: str,
    role: CampaignRole,
    patch: SheetPatch,
) -> Response | None:
    locked = _state_refusal(record)
    if locked is not None:
        return locked
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


def _state_refusal(record: sheet_write.SheetRecord | None) -> Response | None:
    if record is None:
        return None
    if record.state == "conflito":
        return error_response(
            "sheet_conflict", "Resolve the sheet conflicts first", 409
        )
    if record.state == "ausente":
        return error_response("sheet_missing", "The sheet is missing", 409)
    return None


async def _persist_or_restore(
    database: Database,
    index: VaultIndex,
    slug: str,
    note: SheetNote,
    result: sheet_write.SheetWriteResult,
    mirror: enrollment.StatusMirror | None = None,
) -> Response | None:
    try:
        await sheet_store.store_sheet(database, slug, note.path, result)
    except Exception as failure:
        root = index.root
        if root is not None:
            await asyncio.to_thread(
                sheet_write.restore_sheet,
                root / note.path,
                result.previous_text,
            )
        if mirror is not None:
            await asyncio.to_thread(enrollment.revert_status_mirror, mirror)
        return _storage_failure(failure)
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
    except sheet_write.SheetMergeConflict:
        raise
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
    return next(
        (
            note
            for note in index.campaign(slug).sheets
            if note.id == sheet_id and _is_sheet_note(note)
        ),
        None,
    )


def _is_sheet_note(note: SheetNote) -> bool:
    placed = locate_note(note.path)
    return placed is not None and placed[1] == "sheets"


@bp.get("/api/campaigns/<slug>/conflicts")
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 503)
@validate_response(SheetConflictList, 200)
async def read_conflicts(slug: str) -> Response | SheetConflictList:
    scope = await _character_scope(slug)
    if isinstance(scope, Response):
        return scope
    user_id, role = scope
    database = get_database()
    if database is None:
        return _not_found()
    owner = None if role == "narrator" else user_id
    return _conflict_list(await sheet_conflicts.queue(database, slug, owner))


@bp.post("/api/campaigns/<slug>/conflicts/<conflict_id>/resolve")
@document_request(SheetConflictDecision)
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 409)
@document_response(ErrorEnvelope, 422)
@document_response(ErrorEnvelope, 429)
@document_response(ErrorEnvelope, 503)
@validate_response(SheetConflictList, 200)
async def resolve_conflict(
    slug: str, conflict_id: str
) -> Response | SheetConflictList:
    scope = await _character_scope(slug)
    if isinstance(scope, Response):
        return scope
    user_id, role = scope
    refusal = rate_limit_response(SHEET_WRITE_BUCKETS)
    if refusal is not None:
        return refusal
    payload = await _json_model(SheetConflictDecision, "Invalid decision")
    if isinstance(payload, Response):
        return payload
    target = _database_index()
    if isinstance(target, Response):
        return target
    database, index = target
    if index.root is None:
        return _vault_not_ready()
    refusal = await _conflict_refusal(
        database, slug, conflict_id, user_id, role
    )
    if refusal is not None:
        return refusal
    return await _apply_resolution(
        database, index, slug, conflict_id, payload, user_id
    )


async def _conflict_refusal(
    database: Database,
    slug: str,
    conflict_id: str,
    user_id: str,
    role: CampaignRole,
) -> Response | None:
    try:
        owner = await sheet_conflicts.owner_of(database, slug, conflict_id)
    except sheet_conflicts.ConflictNotFound:
        return _hidden()
    if role != "narrator" and owner != user_id:
        return _forbidden()
    return None


async def _apply_resolution(
    database: Database,
    index: vault_index.VaultIndex,
    slug: str,
    conflict_id: str,
    payload: SheetConflictDecision,
    user_id: str,
) -> Response | SheetConflictList:
    if index.root is None:
        return _vault_not_ready()
    resolution = await _decide(
        database, index.root, slug, conflict_id, payload, user_id
    )
    if isinstance(resolution, Response):
        return resolution
    if resolution.write is None:
        return _conflict_list(resolution.conflicts)
    note = _find_sheet(index, slug, resolution.write.sheet_id)
    if note is None:
        return _hidden()
    result = await _run_resolution(
        database, index, slug, note, resolution.write
    )
    if isinstance(result, Response):
        await sheet_conflicts.undo_decision(
            database, note.path, resolution.field_path
        )
        return result
    persisted = await _commit_write(database, index, slug, note, result)
    if isinstance(persisted, Response):
        await sheet_conflicts.undo_decision(
            database, note.path, resolution.field_path
        )
        return persisted
    await sheet_conflicts.settle(database, note.path, user_id)
    await _reload_vault()
    return SheetConflictList(conflicts=[])


async def _decide(
    database: Database,
    root: Path,
    slug: str,
    conflict_id: str,
    payload: SheetConflictDecision,
    user_id: str,
) -> Response | sheet_conflicts.Resolution:
    try:
        return await sheet_conflicts.decide(
            database,
            root,
            campaign=slug,
            conflict_id=conflict_id,
            decision=payload.decision,
            actor=user_id,
        )
    except sheet_conflicts.ConflictNotFound:
        return _hidden()
    except sheet_conflicts.InvalidDecision as failure:
        return error_response("invalid_decision", str(failure), 422)
    except sheet_conflicts.ConflictNotPending:
        return error_response(
            "conflict_not_pending", "This conflict was already decided", 409
        )
    except sheet_write.SheetInvalid as failure:
        return _write_failure(failure)


async def _run_resolution(
    database: Database,
    index: vault_index.VaultIndex,
    slug: str,
    note: SheetNote,
    pending: sheet_conflicts.PendingWrite,
) -> Response | sheet_write.SheetWriteResult:
    root = index.root
    if root is None:
        return _vault_not_ready()
    try:
        return await asyncio.to_thread(
            sheet_write.write_sheet,
            root / note.path,
            slug,
            note.id,
            pending.patch,
            index.campaign(slug).config or default_config(),
            pending.record,
            sheet_store.backup_root(database),
        )
    except sheet_write.SheetWriteError as failure:
        return _write_failure(failure)


def _conflict_list(
    rows: Iterable[sheet_conflicts.ConflictRecord],
) -> SheetConflictList:
    return SheetConflictList(
        conflicts=[
            SheetConflictField(
                id=row.id,
                sheet_id=row.sheet_id,
                character_id=row.character_id,
                field_path=row.field_path,
                base=row.base,
                ours=row.ours,
                theirs=row.theirs,
                allow_both=row.allow_both,
            )
            for row in rows
        ]
    )


def _conflict_detail(
    rows: list[sheet_conflicts.ConflictRecord],
) -> Response:
    payload = SheetConflictDetail(
        error=ErrorDetail(
            code="sheet_field_conflict",
            message="The same field changed in the panel and in the vault",
        ),
        conflicts=_conflict_list(rows).conflicts,
    )
    return Response(
        payload.model_dump_json(), status=409, mimetype="application/json"
    )


def _recovery_refusal(
    stored: sheet_store.StoredSheet,
    user_id: str,
    role: CampaignRole,
) -> Response | None:
    if stored.state != "ausente":
        return error_response("sheet_present", "The sheet is not missing", 409)
    if role != "narrator" and stored.owner_id != user_id:
        return _forbidden()
    return None


@bp.post("/api/campaigns/<slug>/sheets/<sheet_id>/restore")
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 409)
@document_response(ErrorEnvelope, 429)
@document_response(ErrorEnvelope, 503)
@validate_response(SheetDetail, 200)
async def restore_sheet(slug: str, sheet_id: str) -> Response | SheetDetail:
    context = await _restore_context(slug, sheet_id)
    if isinstance(context, Response):
        return context
    return await _restore(context)


async def _restore_context(
    slug: str, sheet_id: str
) -> RestoreContext | Response:
    scope = await _character_scope(slug)
    if isinstance(scope, Response):
        return scope
    user_id, role = scope
    refusal = rate_limit_response(SHEET_WRITE_BUCKETS)
    if refusal is not None:
        return refusal
    target = _database_index()
    if isinstance(target, Response):
        return target
    database, index = target
    stored = await sheet_store.stored_sheet(database, slug, sheet_id)
    if stored is None or index.root is None:
        return _hidden()
    blocked = _recovery_refusal(stored, user_id, role)
    if blocked is not None:
        return blocked
    return RestoreContext(database, index, index.root, stored)


async def _restore(context: RestoreContext) -> Response | SheetDetail:
    slug = context.stored.campaign
    try:
        result = await asyncio.to_thread(
            sheet_write.restore_missing,
            context.root / context.stored.path,
            slug,
            context.stored.harpi_id,
            context.stored.record(),
            context.stored.last_text,
            context.index.campaign(slug).config or default_config(),
        )
        await sheet_store.store_sheet(
            context.database, slug, context.stored.path, result
        )
    except sheet_write.SheetWriteError as failure:
        return _write_failure(failure)
    except Exception as failure:
        return _storage_failure(failure)
    await _reload_vault()
    return _sheet_response(slug, context.stored.harpi_id)


@bp.post("/api/campaigns/<slug>/sheets/<sheet_id>/forget")
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 409)
@validate_response(SheetActionResult, 200)
async def forget_sheet(
    slug: str, sheet_id: str
) -> Response | SheetActionResult:
    scope = await _character_scope(slug)
    if isinstance(scope, Response):
        return scope
    user_id, role = scope
    database = get_database()
    if database is None:
        return _not_found()
    stored = await sheet_store.stored_sheet(database, slug, sheet_id)
    if stored is None:
        return _hidden()
    refusal = _recovery_refusal(stored, user_id, role)
    if refusal is not None:
        return refusal
    await sheet_store.forget_sheet(database, stored.path)
    return SheetActionResult(action="forget", sheet_id=sheet_id)


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
    return await image_response(path)


@bp.post("/api/campaigns/<slug>/assets")
@document_request(AssetUpload, source=DataSource.FORM_MULTIPART)
@document_response(AssetDetail, 200)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 413)
@document_response(ErrorEnvelope, 422)
@document_response(ErrorEnvelope, 429)
@document_response(ErrorEnvelope, 503)
@validate_response(AssetDetail, 200)
async def upload_asset(slug: str) -> Response | AssetDetail:
    scope = await _character_scope(slug)
    if isinstance(scope, Response):
        return scope
    user_id, _role = scope
    refusal = rate_limit_response(ASSET_UPLOAD_BUCKETS)
    if refusal is not None:
        return refusal
    target = _database_index()
    if isinstance(target, Response):
        return target
    database, index = target
    root = index.root
    if root is None:
        return _vault_not_ready()
    saved = await _store_upload(database, root, slug, user_id)
    if isinstance(saved, Response):
        return saved
    await _reload_vault()
    return AssetDetail(
        name=saved.name,
        path=saved.path,
        url=f"/api/campaigns/{slug}/assets/{saved.name}",
        hash=saved.digest,
        size=saved.size,
        content_type=saved.content_type,
        new_file=saved.new_file,
    )


async def _store_upload(
    database: Database,
    root: Path,
    slug: str,
    user_id: str,
) -> assets.SavedAsset | Response:
    raw = await _uploaded_bytes()
    if isinstance(raw, Response):
        return raw
    try:
        return await assets.save_upload(database, root, slug, raw, user_id)
    except assets.ImageTooLarge as failure:
        return error_response("payload_too_large", str(failure), 413)
    except assets.QuotaExceeded as failure:
        return error_response("quota_exceeded", str(failure), 413)
    except assets.UnsupportedImage as failure:
        return error_response("invalid_payload", str(failure), 422)
    except (assets.UnsafeLocation, OSError) as failure:
        return _upload_failure(failure)


def _upload_failure(failure: Exception) -> Response:
    logger.opt(exception=failure).error(f"Asset write failed: {failure}")
    return error_response(
        "vault_write_failed", "The vault could not store the file", 503
    )


async def _uploaded_bytes() -> bytes | Response:
    upload = (await request.files).get("file")
    if upload is None:
        return error_response("invalid_payload", "A file is required", 422)
    return upload.read()


@bp.get("/api/campaigns/<slug>/assets/<name>")
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 429)
@document_response(ErrorEnvelope, 503)
async def read_asset(slug: str, name: str) -> Response:
    refusal = await _asset_read_refusal(slug)
    if refusal is not None:
        return refusal
    target = _database_index()
    if isinstance(target, Response):
        return target
    database, index = target
    if index.root is None:
        return _vault_not_ready()
    if not await assets.registered(database, slug, name):
        return _hidden()
    path = assets.resolve_upload(index.root, slug, name)
    if path is None:
        return _hidden()
    return await image_response(path)


@bp.get("/api/campaigns/<slug>/images/<name>")
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 429)
@document_response(ErrorEnvelope, 503)
async def read_image(slug: str, name: str) -> Response:
    refusal = await _asset_read_refusal(slug)
    if refusal is not None:
        return refusal
    index = configured()
    path = index.portrait_path(name) if assets.valid_image_name(name) else None
    owner = None if path is None else index.campaign_of(path)
    if path is None or index.is_upload(path):
        return _hidden()
    if owner is not None and owner != slug:
        return _hidden()
    return await image_response(path)


async def _asset_read_refusal(slug: str) -> Response | None:
    scope = await _character_scope(slug)
    if isinstance(scope, Response):
        return scope
    return rate_limit_response(ASSET_READ_BUCKETS)


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


def _etag_matches(header: str | None, token: str) -> bool:
    if header is None:
        return False
    for candidate in header.split(","):
        value = candidate.strip()
        if value == "*":
            return True
        if value.startswith("W/"):
            value = value[2:].strip()
        if value.strip('"') == token:
            return True
    return False


async def image_response(path: Path) -> Response:
    try:
        stat = path.stat()
    except OSError:
        return _hidden()
    token = f"{stat.st_mtime_ns:x}-{stat.st_size:x}"
    etag = f'"{token}"'
    headers = {
        "Cache-Control": IMAGE_CACHE,
        "ETag": etag,
        "Last-Modified": http_date(stat.st_mtime),
    }
    if _etag_matches(request.headers.get("If-None-Match"), token):
        return Response(status=304, headers=headers)
    response = await send_file(
        path,
        mimetype=IMAGE_TYPES[path.suffix.casefold()],
        conditional=False,
    )
    response.headers.update(headers)
    return response


@dataclass(frozen=True, slots=True)
class SceneContext:
    database: Database
    index: vault_index.VaultIndex
    root: Path
    user_id: str


async def _scene_scope(slug: str) -> SceneContext | Response:
    user_id = await _narrator(slug)
    if isinstance(user_id, Response):
        return user_id
    database = get_database()
    index = configured()
    root = index.root
    if database is None:
        return _not_found()
    if root is None or not index.available:
        return _vault_not_ready()
    return SceneContext(database, index, root, user_id)


def _scene_exists() -> Response:
    return error_response(
        "scene_exists", "A scene with this name already exists", 409
    )


def _scene_unreadable() -> Response:
    return error_response(
        "scene_unreadable", "The scene file cannot be read", 409
    )


@bp.get("/api/campaigns/<slug>/scenes")
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 503)
@validate_response(SceneList, 200)
async def read_scenes(slug: str) -> Response | SceneList:
    context = await _scene_scope(slug)
    if isinstance(context, Response):
        return context
    records = await scenes.scene_rows(context.database, slug)
    live = await context.database.fetchone(
        "SELECT current_scene_id FROM tables "
        "WHERE campaign_slug = ? AND status = 'open'",
        (slug,),
    )
    current = None if live is None else live["current_scene_id"]
    return SceneList(
        scenes=[
            scenes.summary(record, context.root).model_copy(
                update={"in_use": record.id == current}
            )
            for record in records
        ]
    )


@bp.get("/api/campaigns/<slug>/scenes/<scene>")
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 409)
@document_response(ErrorEnvelope, 503)
@validate_response(SceneDetail, 200)
async def read_scene(slug: str, scene: str) -> Response | SceneDetail:
    context = await _scene_scope(slug)
    if isinstance(context, Response):
        return context
    return await _stored_scene(context.database, context.root, slug, scene)


async def _stored_scene(
    database: Database,
    root: Path,
    slug: str,
    scene: str,
) -> SceneDetail | Response:
    if not scenes.valid_scene_slug(scene):
        return _hidden()
    record = await scenes.scene_record(database, slug, scene)
    if record is None:
        return _hidden()
    detail = scenes.detail(record, root)
    return _scene_unreadable() if detail is None else detail


@bp.get("/api/campaigns/<slug>/scenes/<scene>/image")
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 503)
async def read_scene_image(slug: str, scene: str) -> Response:
    context = await _scene_scope(slug)
    if isinstance(context, Response):
        return context
    if not scenes.valid_scene_slug(scene):
        return _hidden()
    record = await scenes.scene_record(context.database, slug, scene)
    if record is None:
        return _hidden()
    if record.source == "sketch":
        return await _sketch_map_response(context, slug, scene, record)
    path = context.index.portrait_path(record.image_path)
    if path is None:
        return _hidden()
    return await image_response(path)


async def _sketch_map_response(
    context: SceneContext,
    campaign: str,
    scene: str,
    record: scenes.SceneRecord,
) -> Response:
    path = _sketch_map_path(context.root, campaign, scene, record)
    if path is None:
        return _hidden()
    return await svg_response(path)


def _sketch_map_path(
    root: Path,
    campaign: str,
    scene: str,
    record: scenes.SceneRecord,
) -> Path | None:
    expected = scenes.sketch_image_path(campaign, scene)
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


async def svg_response(path: Path) -> Response:
    try:
        stat = path.stat()
    except OSError:
        return _hidden()
    token = f"{stat.st_mtime_ns:x}-{stat.st_size:x}"
    etag = f'"{token}"'
    headers = {
        "Cache-Control": IMAGE_CACHE,
        "ETag": etag,
        "Last-Modified": http_date(stat.st_mtime),
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "sandbox",
    }
    if _etag_matches(request.headers.get("If-None-Match"), token):
        return Response(status=304, headers=headers)
    response = await send_file(
        path, mimetype="image/svg+xml", conditional=False
    )
    response.headers["Content-Type"] = "image/svg+xml"
    response.headers.update(headers)
    return response


@bp.post("/api/campaigns/<slug>/scenes")
@document_request(SceneCreate)
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 409)
@document_response(ErrorEnvelope, 422)
@document_response(ErrorEnvelope, 429)
@document_response(ErrorEnvelope, 503)
@validate_response(SceneDetail, 200)
async def create_scene(slug: str) -> Response | SceneDetail:
    context = await _scene_scope(slug)
    if isinstance(context, Response):
        return context
    refusal = rate_limit_response(SCENE_WRITE_BUCKETS)
    if refusal is not None:
        return refusal
    payload = await _json_model(SceneCreate, "Invalid scene payload")
    if isinstance(payload, Response):
        return payload
    blueprint = _blueprint_for(context.index, slug, payload)
    if isinstance(blueprint, Response):
        return blueprint
    if (
        await scenes.scene_record(context.database, slug, blueprint.slug)
        is not None
    ):
        return _scene_exists()
    return await _create_scene(context, slug, blueprint)


def _blueprint_for(
    index: vault_index.VaultIndex, slug: str, payload: SceneCreate
) -> scenes.SceneBlueprint | Response:
    try:
        return scenes.build_blueprint(index, slug, payload)
    except (
        scenes.InvalidSceneName,
        scenes.InvalidSceneImage,
        scenes.InvalidSceneZones,
    ) as failure:
        return error_response("invalid_payload", str(failure), 422)


async def _create_scene(
    context: SceneContext,
    slug: str,
    blueprint: scenes.SceneBlueprint,
) -> Response | SceneDetail:
    text = scenes.canonical_text(blueprint)
    try:
        await asyncio.to_thread(
            scenes.write_new, context.root, slug, blueprint.slug, text
        )
    except scenes.SceneExists:
        return await _adopt_scene(context, slug, blueprint.slug)
    except OSError as failure:
        return _vault_write_failure(failure)
    digest = scenes.blueprint_hash(blueprint)
    try:
        await scenes.store_new(context.database, slug, blueprint, digest)
    except Exception as failure:
        return _storage_failure(failure)
    return _scene_detail(blueprint, digest)


async def _adopt_scene(
    context: SceneContext, campaign: str, scene: str
) -> Response | SceneDetail:
    try:
        blueprint = await asyncio.to_thread(
            scenes.adopt_existing, context.root, campaign, scene
        )
    except scenes.SceneMissing:
        return _scene_exists()
    if (
        await scenes.scene_record(context.database, campaign, blueprint.slug)
        is not None
    ):
        return _scene_exists()
    digest = scenes.blueprint_hash(blueprint)
    try:
        await scenes.store_new(context.database, campaign, blueprint, digest)
    except Exception as failure:
        return _storage_failure(failure)
    return _scene_detail(blueprint, digest)


def _scene_detail(
    blueprint: scenes.SceneBlueprint, digest: str
) -> SceneDetail:
    return scenes.as_detail(blueprint, digest, saved=True)


@bp.put("/api/campaigns/<slug>/scenes/<scene>")
@document_request(SceneSave)
@document_response(ErrorEnvelope, 403)
@document_response(ErrorEnvelope, 404)
@document_response(ErrorEnvelope, 409)
@document_response(ErrorEnvelope, 422)
@document_response(ErrorEnvelope, 429)
@document_response(ErrorEnvelope, 503)
@validate_response(SceneDetail, 200)
async def save_scene(slug: str, scene: str) -> Response | SceneDetail:
    context = await _scene_scope(slug)
    if isinstance(context, Response):
        return context
    return await _save_scene(context, slug, scene)


async def _save_scene(
    context: SceneContext, slug: str, scene: str
) -> Response | SceneDetail:
    refusal = rate_limit_response(SCENE_WRITE_BUCKETS)
    if refusal is not None:
        return refusal
    if not scenes.valid_scene_slug(scene):
        return _hidden()
    payload = await _json_model(SceneSave, "Invalid scene payload")
    if isinstance(payload, Response):
        return payload
    record = await scenes.scene_record(context.database, slug, scene)
    if record is None:
        return _hidden()
    saved = await _saved_scene(context.root, slug, scene, payload)
    if isinstance(saved, Response):
        return saved
    return await _persist_scene(context, slug, scene, saved)


async def _persist_scene(
    context: SceneContext,
    slug: str,
    scene: str,
    saved: scenes.SavedScene,
) -> Response | SceneDetail:
    try:
        await scenes.store_save(
            context.database, slug, saved.blueprint, saved.digest
        )
    except Exception as failure:
        scene_ok = await _restore_scene(
            context.root, slug, scene, saved.previous_text
        )
        map_ok = True
        if saved.blueprint.source == "sketch":
            map_ok = await _restore_map(
                context.root, slug, scene, saved.previous_map
            )
        if not (scene_ok and map_ok):
            return error_response(
                "scene_restore_failed",
                _inconsistent_scene_message(scene_ok, map_ok),
                503,
            )
        return _storage_failure(failure)
    return _scene_detail(saved.blueprint, saved.digest)


def _inconsistent_scene_message(scene_ok: bool, map_ok: bool) -> str:
    files = []
    if not scene_ok:
        files.append("blueprint")
    if not map_ok:
        files.append("map SVG")
    return (
        "The save failed and the previous scene could not be restored for: "
        + ", ".join(files)
    )


async def _restore_map(
    root: Path, slug: str, scene: str, text: str | None
) -> bool:
    try:
        await asyncio.to_thread(
            scenes.restore_map_svg, root, slug, scene, text
        )
    except (OSError, UnicodeDecodeError) as failure:
        logger.opt(exception=failure).error(
            f"Scene map restore failed: {failure}"
        )
        return False
    return True


async def _restore_scene(root: Path, slug: str, scene: str, text: str) -> bool:
    try:
        await asyncio.to_thread(scenes.restore_file, root, slug, scene, text)
    except OSError as failure:
        logger.opt(exception=failure).error(f"Scene restore failed: {failure}")
        return False
    return True


async def _saved_scene(
    root: Path,
    slug: str,
    scene: str,
    payload: SceneSave,
) -> scenes.SavedScene | Response:
    try:
        return await asyncio.to_thread(
            scenes.save_existing, root, slug, scene, payload
        )
    except scenes.SceneMissing:
        return _scene_unreadable()
    except scenes.SceneConflict:
        return error_response(
            "scene_conflict", "The scene changed on disk", 409
        )
    except scenes.InvalidSceneZones as failure:
        return error_response("invalid_payload", str(failure), 422)
    except (OSError, UnicodeDecodeError) as failure:
        return _vault_write_failure(failure)
