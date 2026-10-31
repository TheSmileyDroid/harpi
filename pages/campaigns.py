from __future__ import annotations

from pathlib import Path

from quart import Blueprint, Response, g, request, send_file, session
from quart_schema import document_response, validate_response
from werkzeug.http import http_date

from pages.api import error_response
from pages.guard import csrf_refusal, vault_unavailable
from src.panel import state
from src.panel.campaigns import campaign_access
from src.panel.cast import campaign_cast
from src.panel.schemas import (
    CampaignDetail,
    CampaignList,
    CampaignRole,
    CharacterList,
    ErrorEnvelope,
)
from src.panel.vault_index import PORTRAIT_TYPES

bp = Blueprint("campaigns", __name__)

ALLOWED_GUILDS = "campaign_allowed_guilds"
PORTRAIT_CACHE = "private, max-age=60, must-revalidate"


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
    return campaign


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
