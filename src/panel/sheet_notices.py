from __future__ import annotations

import asyncio
import json
import re
import secrets
import time
from dataclasses import dataclass, replace
from pathlib import PurePosixPath
from typing import Any

import discord
from loguru import logger

from src.bot_state import bot_running, get_bot, run_on_bot_loop
from src.config import Settings
from src.panel import sheet_store
from src.panel.schemas import SheetNoticeState
from src.storage.database import Database

CONFLICT = "conflito"
MISSING = "ausente"
INVALID = "invalido"
UNKNOWN = "desconhecido"
STATE_TITLES: dict[SheetNoticeState, str] = {
    CONFLICT: "ficha em conflito",
    MISSING: "ficha ausente",
    INVALID: "ficha inválida",
    UNKNOWN: "ficha desconhecida",
}
WARNED_STATES = frozenset(STATE_TITLES)
PANEL_PAGE = "personagens"
RESOLVED_TEXT = "aviso encerrado"
MAX_MESSAGE = 2000
ELLIPSIS = "…"
FIELD_PREFIX = "Campos: "
_MARKDOWN = re.compile(r"([\\*_`~|>])")
_LOCKS: dict[str, asyncio.Lock] = {}
_TASKS: set[asyncio.Task[None]] = set()
NOTICE_COLUMNS = (
    "SELECT id, path, sheet_id, character_id, owner_id, name, state, "
    "channel_id, message_id, fields_json, created_at, resolved_by "
    "FROM sheet_notices "
)


@dataclass(frozen=True, slots=True)
class NoticeRecord:
    id: str
    path: str
    sheet_id: str
    character_id: str | None
    owner_id: str | None
    name: str
    state: SheetNoticeState
    channel_id: str | None
    message_id: str | None
    created_at: int
    fields: tuple[str, ...] = ()
    resolved_by: str | None = None

    @property
    def title(self) -> str:
        return STATE_TITLES[self.state]


@dataclass(frozen=True, slots=True)
class NoticeContext:
    channel: str | None
    narrator: str | None
    fields: dict[str, tuple[str, ...]]


def panel_base() -> str:
    return (Settings.from_env().panel_base_url or "").strip().rstrip("/")


def panel_link(slug: str) -> str:
    base = panel_base()
    if not base:
        return ""
    return f"{base}/c/{slug}/{PANEL_PAGE}"


def notice_text(
    name: str,
    state: SheetNoticeState,
    owner: str | None,
    narrator: str | None,
    fields: tuple[str, ...],
    link: str,
) -> str:
    owner_text = f"<@{owner}>" if owner else "—"
    narrator_text = f"<@{narrator}>" if narrator else "—"
    head = [
        f"**{escape_markdown(name)}** — {STATE_TITLES[state]}",
        f"Dono: {owner_text} · Narrador: {narrator_text}",
    ]
    tail = [f"Painel: {link}"] if link else []
    budget = MAX_MESSAGE - len("\n".join(head + tail)) - 1
    lines = head + [line for line in [_fields_line(fields, budget)] if line]
    lines.extend(tail)
    return "\n".join(lines)[:MAX_MESSAGE]


def escape_markdown(text: str) -> str:
    return _MARKDOWN.sub(r"\\\1", text)


def _fields_line(fields: tuple[str, ...], budget: int) -> str:
    if not fields or budget <= len(FIELD_PREFIX):
        return ""
    text = ", ".join(escape_markdown(field) for field in fields)
    available = budget - len(FIELD_PREFIX)
    if len(text) > available:
        if available <= len(ELLIPSIS):
            return ""
        text = text[: available - len(ELLIPSIS)].rstrip() + ELLIPSIS
    return FIELD_PREFIX + text


async def pending(
    database: Database, campaign: str, owner: str | None
) -> list[NoticeRecord]:
    rows = await database.fetchall(
        f"{NOTICE_COLUMNS}WHERE campaign_slug = ? AND resolved_at IS NULL "
        "AND (? IS NULL OR owner_id = ?) ORDER BY created_at, path, id",
        (campaign, owner, owner),
    )
    fields = await _conflict_fields_by_path(database, campaign)
    return [_record(row, _fields_for(row, fields)) for row in rows]


async def refresh(database: Database, campaign: str) -> None:
    now = int(time.time())
    active = await _active_sheets(database, campaign)
    known = {
        (notice.path, notice.state): notice
        for notice in await _open_notices(database, campaign)
    }
    context = NoticeContext(
        channel=await _open_channel(database, campaign),
        narrator=await _narrator(database, campaign),
        fields=await _conflict_fields_by_path(database, campaign),
    )
    for key, row in active.items():
        await _refresh_notice(
            database, campaign, key, row, known, context, now
        )
    for key, notice in known.items():
        if key not in active:
            await _settle_notice(database, campaign, notice, now)


async def refresh_background(database: Database, campaign: str) -> None:
    if not bot_running():
        await refresh(database, campaign)
        return
    task = asyncio.create_task(refresh(database, campaign))
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)


async def drain() -> None:
    while _TASKS:
        await asyncio.gather(*list(_TASKS), return_exceptions=True)


async def _active_sheets(
    database: Database, campaign: str
) -> dict[tuple[str, SheetNoticeState], Any]:
    rows = await database.fetchall(
        "SELECT path, harpi_id, owner_id, state, base_json FROM sheet_files "
        "WHERE campaign = ?",
        (campaign,),
    )
    return {
        (row["path"], row["state"]): row
        for row in rows
        if row["state"] in WARNED_STATES
    }


async def _refresh_notice(
    database: Database,
    campaign: str,
    key: tuple[str, SheetNoticeState],
    row: Any,
    known: dict[tuple[str, SheetNoticeState], NoticeRecord],
    context: NoticeContext,
    now: int,
) -> None:
    fields = _fields_for(row, context.fields)
    notice = known.get(key)
    if notice is None:
        notice = await _create(database, campaign, row, fields, now)
    if context.channel is None:
        return
    if notice.message_id is None or notice.channel_id != context.channel:
        await _post(
            database,
            campaign,
            notice,
            fields,
            context.narrator,
            context.channel,
        )
        return
    if notice.state == CONFLICT and notice.fields != fields:
        await _refresh_message(
            database, campaign, notice, fields, context.narrator
        )


async def resolve(
    database: Database,
    campaign: str,
    path: str,
    state: SheetNoticeState,
    actor: str,
) -> None:
    notice = await database.fetchone(
        f"{NOTICE_COLUMNS}WHERE campaign_slug = ? AND path = ? "
        "AND state = ? AND resolved_at IS NULL "
        "ORDER BY created_at LIMIT 1",
        (campaign, path, state),
    )
    if notice is None:
        return
    await database.execute(
        "UPDATE sheet_notices SET resolved_by = ? WHERE id = ?",
        (actor, notice["id"]),
    )
    await _settle_notice(
        database,
        campaign,
        replace(_record(notice), resolved_by=actor),
        int(time.time()),
    )


async def actor_name(database: Database, campaign: str, user_id: str) -> str:
    row = await database.fetchone(
        "SELECT display_name FROM members "
        "WHERE campaign_slug = ? AND user_id = ?",
        (campaign, user_id),
    )
    if row is not None and row["display_name"]:
        return str(row["display_name"])
    return user_id


async def _create(
    database: Database,
    campaign: str,
    row: Any,
    fields: tuple[str, ...],
    now: int,
) -> NoticeRecord:
    notice = NoticeRecord(
        id=f"ntc_{secrets.token_hex(8)}",
        path=row["path"],
        sheet_id=row["harpi_id"],
        character_id=sheet_store.character_id_from_base(row["base_json"]),
        owner_id=row["owner_id"],
        name=_sheet_name(row["path"]),
        state=row["state"],
        channel_id=None,
        message_id=None,
        created_at=now,
        fields=fields,
    )
    await database.execute(
        "INSERT OR IGNORE INTO sheet_notices ("
        "id, campaign_slug, path, sheet_id, character_id, owner_id, name, "
        "state, fields_json, created_at"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            notice.id,
            campaign,
            notice.path,
            notice.sheet_id,
            notice.character_id,
            notice.owner_id,
            notice.name,
            notice.state,
            _fields_json(fields),
            now,
        ),
    )
    stored = await database.fetchone(
        f"{NOTICE_COLUMNS}WHERE campaign_slug = ? AND path = ? "
        "AND state = ? AND resolved_at IS NULL ORDER BY created_at LIMIT 1",
        (campaign, notice.path, notice.state),
    )
    return notice if stored is None else _record(stored)


async def _post(
    database: Database,
    campaign: str,
    notice: NoticeRecord,
    fields: tuple[str, ...],
    narrator: str | None,
    channel: str,
) -> None:
    if not bot_running():
        return
    async with _lock_for(notice.id):
        current = await database.fetchone(
            "SELECT channel_id, message_id FROM sheet_notices WHERE id = ?",
            (notice.id,),
        )
        if current is None:
            return
        if (
            current["message_id"] is not None
            and str(current["channel_id"]) == channel
        ):
            return
        content = _content(campaign, notice, fields, narrator)
        mentions = _mention_ids(notice.owner_id, narrator)
        try:
            message_id = await _send(channel, content, mentions)
        except Exception as failure:
            logger.opt(exception=True).warning(
                f"Sheet notice not posted: {failure}"
            )
            return
        await database.execute(
            "UPDATE sheet_notices SET channel_id = ?, message_id = ?, "
            "fields_json = ? WHERE id = ?",
            (channel, message_id, _fields_json(fields), notice.id),
        )


async def _refresh_message(
    database: Database,
    campaign: str,
    notice: NoticeRecord,
    fields: tuple[str, ...],
    narrator: str | None,
) -> None:
    content = _content(campaign, notice, fields, narrator)
    mentions = _mention_ids(notice.owner_id, narrator)
    if not await _edit(
        notice.channel_id, notice.message_id, content, mentions
    ):
        return
    await database.execute(
        "UPDATE sheet_notices SET fields_json = ? WHERE id = ?",
        (_fields_json(fields), notice.id),
    )


def _content(
    campaign: str,
    notice: NoticeRecord,
    fields: tuple[str, ...],
    narrator: str | None,
) -> str:
    return notice_text(
        notice.name,
        notice.state,
        notice.owner_id,
        narrator,
        fields,
        panel_link(campaign),
    )


async def _settle_notice(
    database: Database, campaign: str, notice: NoticeRecord, now: int
) -> None:
    text = await _resolution_text(database, campaign, notice.resolved_by)
    if (
        notice.message_id is not None
        and bot_running()
        and not await _edit(notice.channel_id, notice.message_id, text, ())
    ):
        logger.warning(
            f"Sheet notice {notice.id} closed after a failed message edit"
        )
    await _close(database, notice.id, now, notice.resolved_by)


async def _resolution_text(
    database: Database, campaign: str, resolved_by: str | None
) -> str:
    if resolved_by is None:
        return RESOLVED_TEXT
    name = await actor_name(database, campaign, resolved_by)
    return f"resolvido por {escape_markdown(name)}"


def _mention_ids(owner: str | None, narrator: str | None) -> tuple[str, ...]:
    return tuple(value for value in (owner, narrator) if value is not None)


def _allowed_mentions(ids: tuple[str, ...]) -> discord.AllowedMentions:
    users = [discord.Object(id=int(value)) for value in ids]
    return discord.AllowedMentions(
        everyone=False, roles=False, users=users, replied_user=False
    )


async def _send(
    channel_id: str, content: str, mentions: tuple[str, ...]
) -> str:
    return await run_on_bot_loop(
        _send_message(get_bot(), int(channel_id), content, mentions)
    )


async def _send_message(
    bot, channel_id: int, content: str, mentions: tuple[str, ...]
) -> str:
    channel = await _channel(bot, channel_id)
    message = await channel.send(
        content, allowed_mentions=_allowed_mentions(mentions)
    )
    return str(message.id)


async def _edit(
    channel_id: str | None,
    message_id: str | None,
    content: str,
    mentions: tuple[str, ...],
) -> bool:
    if channel_id is None or message_id is None or not bot_running():
        return False
    try:
        await run_on_bot_loop(
            _edit_message(
                get_bot(),
                int(channel_id),
                int(message_id),
                content,
                mentions,
            )
        )
    except Exception as failure:
        logger.opt(exception=True).warning(
            f"Sheet notice not edited: {failure}"
        )
        return False
    return True


async def _edit_message(
    bot,
    channel_id: int,
    message_id: int,
    content: str,
    mentions: tuple[str, ...],
) -> None:
    channel = await _channel(bot, channel_id)
    message = await channel.fetch_message(message_id)
    await message.edit(
        content=content, allowed_mentions=_allowed_mentions(mentions)
    )


async def _channel(bot, channel_id: int):
    channel = bot.get_channel(channel_id)
    if channel is None:
        channel = await bot.fetch_channel(channel_id)
    if channel is None:
        raise RuntimeError(f"channel {channel_id} is unavailable")
    return channel


async def _open_notices(
    database: Database, campaign: str
) -> list[NoticeRecord]:
    rows = await database.fetchall(
        f"{NOTICE_COLUMNS}WHERE campaign_slug = ? AND resolved_at IS NULL "
        "ORDER BY created_at, path, id",
        (campaign,),
    )
    return [_record(row) for row in rows]


async def _close(
    database: Database, notice_id: str, now: int, resolved_by: str | None
) -> None:
    await database.execute(
        "UPDATE sheet_notices SET resolved_at = ?, resolved_by = ? "
        "WHERE id = ? AND resolved_at IS NULL",
        (now, resolved_by, notice_id),
    )


async def _open_channel(database: Database, campaign: str) -> str | None:
    row = await database.fetchone(
        "SELECT channel_id FROM tables WHERE campaign_slug = ? "
        "AND status = 'open' ORDER BY opened_at DESC LIMIT 1",
        (campaign,),
    )
    return None if row is None else str(row["channel_id"])


async def _narrator(database: Database, campaign: str) -> str | None:
    row = await database.fetchone(
        "SELECT narrator_id FROM campaigns WHERE slug = ?", (campaign,)
    )
    return None if row is None else str(row["narrator_id"])


async def _conflict_fields_by_path(
    database: Database, campaign: str
) -> dict[str, tuple[str, ...]]:
    rows = await database.fetchall(
        "SELECT c.path, c.field_path FROM sheet_conflicts c "
        "JOIN sheet_files s ON s.path = c.path "
        "WHERE c.resolved_at IS NULL AND s.campaign = ? "
        "ORDER BY c.created_at, c.id",
        (campaign,),
    )
    found: dict[str, list[str]] = {}
    for row in rows:
        found.setdefault(row["path"], []).append(row["field_path"])
    return {path: tuple(items) for path, items in found.items()}


def _fields_for(
    row: Any, fields: dict[str, tuple[str, ...]]
) -> tuple[str, ...]:
    if row["state"] != CONFLICT:
        return ()
    return fields.get(row["path"], ())


def _lock_for(notice_id: str) -> asyncio.Lock:
    lock = _LOCKS.get(notice_id)
    if lock is None:
        lock = asyncio.Lock()
        _LOCKS[notice_id] = lock
    return lock


def _fields_json(fields: tuple[str, ...]) -> str:
    return json.dumps(list(fields))


def _parse_fields(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    try:
        loaded = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return ()
    return tuple(str(item) for item in loaded if isinstance(item, str))


def _record(row: Any, fields: tuple[str, ...] | None = None) -> NoticeRecord:
    return NoticeRecord(
        id=row["id"],
        path=row["path"],
        sheet_id=row["sheet_id"],
        character_id=row["character_id"],
        owner_id=row["owner_id"],
        name=row["name"],
        state=row["state"],
        channel_id=row["channel_id"],
        message_id=row["message_id"],
        created_at=row["created_at"],
        fields=_parse_fields(row["fields_json"]) if fields is None else fields,
        resolved_by=row["resolved_by"],
    )


def _sheet_name(path: str) -> str:
    return PurePosixPath(path).stem or path
