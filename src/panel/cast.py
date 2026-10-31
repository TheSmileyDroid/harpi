from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from src.panel import vault_index
from src.panel.notes import CharacterNote, SheetNote
from src.panel.schemas import CampaignRole, CharacterCard
from src.panel.vault_index import CampaignNotes, VaultIndex
from src.storage import get_database
from src.storage.database import Database

ACTIVE = "ativo"
PENDING = "pendente"
ARCHIVED = "arquivado"
CastStatus = Literal["active", "pending"]


@dataclass(frozen=True, slots=True)
class CastMember:
    id: str
    name: str
    concept: str | None
    summary: str | None
    portrait_ref: str | None
    owner: str | None
    status: CastStatus
    is_pc: bool
    archived: bool


@dataclass(frozen=True, slots=True)
class SheetState:
    sheet: SheetNote | None
    status: CastStatus
    archived: bool


def portrait_url(slug: str, character_id: str) -> str:
    campaign = quote(slug, safe="")
    character = quote(character_id, safe="")
    return f"/api/campaigns/{campaign}/characters/{character}/portrait"


def members(notes: CampaignNotes) -> list[CastMember]:
    sheets = _group_sheets(notes.sheets)
    return [
        _member(key, character, sheets.pop(key, []))
        for key, character in notes.characters.items()
    ]


def _group_sheets(sheets: tuple[SheetNote, ...]) -> dict[str, list[SheetNote]]:
    grouped: dict[str, list[SheetNote]] = {}
    for sheet in sheets:
        if sheet.character is not None:
            grouped.setdefault(sheet.character, []).append(sheet)
    return grouped


def _member(
    key: str, character: CharacterNote, sheets: list[SheetNote]
) -> CastMember:
    state = _current(sheets)
    owner = None if state.sheet is None else state.sheet.owner
    return CastMember(
        id=key,
        name=character.name,
        concept=character.concept,
        summary=character.summary,
        portrait_ref=character.portrait,
        owner=owner,
        status=state.status,
        is_pc=owner is not None,
        archived=state.archived or character.status == ARCHIVED,
    )


def _current(sheets: list[SheetNote]) -> SheetState:
    active = [sheet for sheet in sheets if sheet.status == ACTIVE]
    if active:
        return SheetState(active[0], "active", False)
    pending = [sheet for sheet in sheets if sheet.status == PENDING]
    if pending:
        return SheetState(pending[0], "pending", False)
    return SheetState(None, "active", bool(sheets))


def shown_to(
    member: CastMember,
    user_id: str,
    role: CampaignRole,
    revealed: frozenset[str],
) -> bool:
    if member.archived:
        return False
    if role == "narrator":
        return True
    if member.is_pc and member.status == "active":
        return True
    if member.status == "pending":
        return member.owner == user_id
    return member.id in revealed


class CampaignCast:
    def __init__(self, database: Database, index: VaultIndex) -> None:
        self._database = database
        self._index = index

    async def roster(
        self, slug: str, user_id: str, role: CampaignRole
    ) -> list[CharacterCard]:
        shown = await self._shown(slug, user_id, role)
        cards = [self._card(slug, member) for member in shown]
        return sorted(cards, key=lambda card: (card.name.casefold(), card.id))

    async def member(
        self, slug: str, character_id: str, user_id: str, role: CampaignRole
    ) -> CastMember | None:
        shown = await self._shown(slug, user_id, role)
        return next(
            (member for member in shown if member.id == character_id), None
        )

    def portrait(self, member: CastMember) -> Path | None:
        return self._index.portrait_path(member.portrait_ref)

    async def _shown(
        self, slug: str, user_id: str, role: CampaignRole
    ) -> list[CastMember]:
        revealed = await self._revealed(slug)
        return [
            member
            for member in members(self._index.campaign(slug))
            if shown_to(member, user_id, role, revealed)
        ]

    def _card(self, slug: str, member: CastMember) -> CharacterCard:
        portrait = (
            portrait_url(slug, member.id)
            if self.portrait(member) is not None
            else None
        )
        return CharacterCard(
            id=member.id,
            name=member.name,
            concept=member.concept,
            summary=member.summary,
            portrait=portrait,
        )

    async def _revealed(self, slug: str) -> frozenset[str]:
        rows = await self._database.fetchall(
            "SELECT character_id FROM character_visibility "
            "WHERE campaign_slug = ?",
            (slug,),
        )
        return frozenset(row["character_id"] for row in rows)


def campaign_cast() -> CampaignCast | None:
    database = get_database()
    index = vault_index.configured()
    if database is None or not index.available:
        return None
    return CampaignCast(database, index)
