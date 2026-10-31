from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from src.panel import vault_index
from src.panel.notes import CharacterNote, SheetNote
from src.panel.schemas import (
    CampaignRole,
    CharacterCard,
    CharacterDetail,
    SheetAspect,
    SheetConsequence,
    SheetDetail,
    SheetExtra,
    SheetInventoryEntry,
    SheetLadderStep,
    SheetSkill,
    SheetStatus,
    SheetStressBox,
    SheetStressTrack,
    SheetStunt,
)
from src.panel.sheets import (
    CampaignConfig,
    SheetBlock,
    SheetError,
    StressBox,
    default_config,
    read_sheet,
)
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
    sheet: SheetNote | None


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
        sheet=state.sheet,
    )


def _current(sheets: list[SheetNote]) -> SheetState:
    active = _sheet_with_status(sheets, ACTIVE)
    if active is not None:
        return SheetState(active, "active", False)
    pending = _sheet_with_status(sheets, PENDING)
    if pending is not None:
        return SheetState(pending, "pending", False)
    archived = _sheet_with_status(sheets, ARCHIVED)
    if archived is not None:
        return SheetState(archived, "active", True)
    return SheetState(None, "active", False)


def _sheet_with_status(
    sheets: list[SheetNote], status: str
) -> SheetNote | None:
    return next((sheet for sheet in sheets if sheet.status == status), None)


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

    async def character(
        self, slug: str, character_id: str, user_id: str, role: CampaignRole
    ) -> CharacterDetail | None:
        member = self._entry(slug, character_id)
        if member is None or not await self._may_open(
            slug, member, user_id, role
        ):
            return None
        card = self._card(slug, member)
        if not _full_access(member, user_id, role) or member.sheet is None:
            return CharacterDetail(kind="card", card=card, sheet=None)
        notes = self._index.campaign(slug)
        config = notes.config or default_config()
        return CharacterDetail(
            kind="sheet",
            card=card,
            sheet=self._sheet_detail(member, config),
        )

    async def _may_open(
        self,
        slug: str,
        member: CastMember,
        user_id: str,
        role: CampaignRole,
    ) -> bool:
        if _full_access(member, user_id, role):
            return True
        return shown_to(member, user_id, role, await self._revealed(slug))

    def _entry(self, slug: str, character_id: str) -> CastMember | None:
        return next(
            (
                member
                for member in members(self._index.campaign(slug))
                if member.id == character_id
            ),
            None,
        )

    def _sheet_detail(
        self, member: CastMember, config: CampaignConfig
    ) -> SheetDetail:
        note = member.sheet
        if note is None:
            raise ValueError("a sheet detail needs a sheet note")
        status = _sheet_status(member)
        try:
            block = read_sheet(note.loaded, config)
        except SheetError as failure:
            return _broken_detail(note, status, config, str(failure))
        return SheetDetail(
            id=note.id,
            character_id=note.character,
            owner=note.owner,
            status=status,
            state="ok",
            read_only=status == "archived",
            error=None,
            refresh=block.refresh,
            fate_points=block.fate_points,
            ladder=_ladder_rows(config),
            aspects=_aspect_rows(block),
            skills=_skill_rows(block, config),
            stunts=_stunt_rows(block),
            stress=_stress_rows(block, config),
            consequences=_consequence_rows(block, config),
            extras=_extra_rows(block),
            inventory=_inventory_rows(block),
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


def _full_access(member: CastMember, user_id: str, role: CampaignRole) -> bool:
    return role == "narrator" or member.owner == user_id


def _sheet_status(member: CastMember) -> SheetStatus:
    if member.archived:
        return "archived"
    return "pending" if member.status == "pending" else "active"


def _broken_detail(
    note: SheetNote,
    status: SheetStatus,
    config: CampaignConfig,
    error: str,
) -> SheetDetail:
    return SheetDetail(
        id=note.id,
        character_id=note.character,
        owner=note.owner,
        status=status,
        state="invalid",
        read_only=True,
        error=error,
        refresh=None,
        fate_points=None,
        ladder=_ladder_rows(config),
        aspects=[],
        skills=[],
        stunts=[],
        stress=[],
        consequences=[],
        extras=[],
        inventory=[],
    )


def _ladder_rows(config: CampaignConfig) -> list[SheetLadderStep]:
    return [
        SheetLadderStep(rank=step.rank, label=step.label)
        for step in config.ladder
    ]


def _aspect_rows(block: SheetBlock) -> list[SheetAspect]:
    return [
        SheetAspect(label=aspect.label, text=aspect.text)
        for aspect in block.aspects
    ]


def _skill_rows(block: SheetBlock, config: CampaignConfig) -> list[SheetSkill]:
    return [
        SheetSkill(
            name=skill.name,
            rank=skill.rank,
            label=config.rank_label(skill.rank),
        )
        for skill in block.skills
    ]


def _stunt_rows(block: SheetBlock) -> list[SheetStunt]:
    return [
        SheetStunt(
            name=stunt.name,
            text=stunt.text,
            refresh_cost=stunt.refresh_cost,
        )
        for stunt in block.stunts
    ]


def _stress_rows(
    block: SheetBlock, config: CampaignConfig
) -> list[SheetStressTrack]:
    written = {track.track: track for track in block.stress}
    return [
        SheetStressTrack(
            track=spec.track,
            boxes=[
                SheetStressBox(value=box.value, checked=box.checked)
                for box in (
                    written[spec.track].boxes
                    if spec.track in written
                    else tuple(StressBox(value, False) for value in spec.boxes)
                )
            ],
        )
        for spec in config.stress
    ]


def _consequence_rows(
    block: SheetBlock, config: CampaignConfig
) -> list[SheetConsequence]:
    written = {
        consequence.severity: consequence for consequence in block.consequences
    }
    return [
        SheetConsequence(
            severity=slot.severity,
            value=slot.value,
            text=written[slot.severity].text
            if slot.severity in written
            else "",
        )
        for slot in config.consequences
    ]


def _extra_rows(block: SheetBlock) -> list[SheetExtra]:
    return [
        SheetExtra(
            kind=extra.kind, name=extra.name, text=extra.text, cost=extra.cost
        )
        for extra in block.extras
    ]


def _inventory_rows(block: SheetBlock) -> list[SheetInventoryEntry]:
    return [
        SheetInventoryEntry(item=item.item, qty=item.qty, note=item.note)
        for item in block.inventory
    ]


def campaign_cast() -> CampaignCast | None:
    database = get_database()
    index = vault_index.configured()
    if database is None or not index.available:
        return None
    return CampaignCast(database, index)
