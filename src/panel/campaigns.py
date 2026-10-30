from __future__ import annotations

from collections.abc import Collection
from typing import Any

from aiosqlite import Row

from src.panel.schemas import CampaignDetail, CampaignRole, CampaignSummary
from src.storage import get_database
from src.storage.database import Database

_BASE_SQL = """
SELECT c.slug, c.name, c.system, c.narrator_id,
       EXISTS (
           SELECT 1 FROM members m
           WHERE m.campaign_slug = c.slug AND m.user_id = ?
       ) AS is_member,
       EXISTS (
           SELECT 1 FROM sheet_files s
           WHERE s.campaign = c.slug AND s.owner_id = ? AND s.status = 'ativo'
       ) AS is_player
FROM campaigns c
WHERE c.guild_id IN ({guilds})
"""

_LIST_SQL = _BASE_SQL + " ORDER BY c.name, c.slug"

_DETAIL_SQL = _BASE_SQL + " AND c.slug = ?"


def _placeholders(count: int) -> str:
    return ", ".join("?" for _ in range(count))


def _role(row: Row, user_id: str) -> CampaignRole | None:
    if row["narrator_id"] == user_id:
        return "narrator"
    if not row["is_member"]:
        return None
    return "player" if row["is_player"] else "pending"


def _summary(row: Row, role: CampaignRole) -> CampaignSummary:
    return CampaignSummary(
        slug=row["slug"],
        name=row["name"],
        system=row["system"],
        role=role,
    )


class CampaignAccess:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def campaigns(
        self, user_id: str, guilds: Collection[str]
    ) -> list[CampaignSummary]:
        if not guilds:
            return []
        rows = await self._rows(_LIST_SQL, user_id, guilds)
        allowed: list[CampaignSummary] = []
        for row in rows:
            summary = _visible_summary(row, user_id)
            if summary is not None:
                allowed.append(summary)
        return allowed

    async def campaign(
        self, slug: str, user_id: str, guilds: Collection[str]
    ) -> CampaignDetail | None:
        if not guilds:
            return None
        rows = await self._rows(_DETAIL_SQL, user_id, guilds, slug)
        if not rows:
            return None
        summary = _visible_summary(rows[0], user_id)
        if summary is None:
            return None
        return CampaignDetail(**summary.model_dump(), open_table=None)

    async def _rows(
        self,
        sql: str,
        user_id: str,
        guilds: Collection[str],
        slug: str | None = None,
    ) -> list[Row]:
        params: list[Any] = [user_id, user_id, *guilds]
        if slug is not None:
            params.append(slug)
        return await self._database.fetchall(
            sql.format(guilds=_placeholders(len(guilds))), params
        )


def _visible_summary(row: Row, user_id: str) -> CampaignSummary | None:
    role = _role(row, user_id)
    return None if role is None else _summary(row, role)


def campaign_access() -> CampaignAccess | None:
    database = get_database()
    if database is None:
        return None
    return CampaignAccess(database)
