from __future__ import annotations

from typing import Any

from quart import Blueprint, g, session
from quart_schema import document_response, validate_response

from pages.api import error_response
from pages.guard import csrf_refusal
from src.panel import state
from src.panel.campaigns import campaign_access
from src.panel.schemas import CampaignDetail, CampaignList, ErrorEnvelope

bp = Blueprint("campaigns", __name__)

ALLOWED_GUILDS = "campaign_allowed_guilds"


@bp.before_request
async def guard_campaign_request() -> Any:
    refusal = csrf_refusal()
    if refusal is not None:
        return refusal
    user_id = _user_id()
    guilds = (
        frozenset() if user_id is None else await state.user_guild_ids(user_id)
    )
    setattr(g, ALLOWED_GUILDS, frozenset(str(guild) for guild in guilds))
    return None


def _user_id() -> str | None:
    raw = session.get("user_id")
    return str(raw) if raw else None


def _allowed_guilds() -> frozenset[str]:
    return getattr(g, ALLOWED_GUILDS, frozenset())


def _not_found() -> Any:
    return error_response("not_found", "Campaign not found", 404)


@bp.get("/api/campaigns")
@validate_response(CampaignList, 200)
async def read_campaigns() -> Any:
    access = campaign_access()
    user_id = _user_id()
    if access is None or user_id is None:
        return CampaignList(campaigns=[])
    campaigns = await access.campaigns(user_id, _allowed_guilds())
    return CampaignList(campaigns=campaigns)


@bp.get("/api/campaigns/<slug>")
@document_response(ErrorEnvelope, 404)
@validate_response(CampaignDetail, 200)
async def read_campaign(slug: str) -> Any:
    access = campaign_access()
    user_id = _user_id()
    if access is None or user_id is None:
        return _not_found()
    campaign = await access.campaign(slug, user_id, _allowed_guilds())
    if campaign is None:
        return _not_found()
    return campaign
