from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.storage.database import Database

PARATHEOS_SLUG = "paratheos"
PARATHEOS_NAME = "Paratheos"
PARATHEOS_SYSTEM = "fate"


@dataclass(frozen=True)
class CampaignSeed:
    slug: str
    name: str
    guild_id: str
    narrator_id: str
    system: str = PARATHEOS_SYSTEM


def paratheos(
    narrator_id: str | None, guild_id: str | None
) -> CampaignSeed | None:
    if not narrator_id or not guild_id:
        return None
    return CampaignSeed(
        slug=PARATHEOS_SLUG,
        name=PARATHEOS_NAME,
        guild_id=guild_id,
        narrator_id=narrator_id,
    )


async def seed_campaign(database: Database, campaign: CampaignSeed) -> None:
    now = int(time.time())
    await database.execute(
        "INSERT INTO campaigns ("
        "slug, name, guild_id, narrator_id, system, content_source, "
        "created_at, updated_at"
        ") VALUES (?, ?, ?, ?, ?, 'vault', ?, ?) "
        "ON CONFLICT (slug) DO NOTHING",
        (
            campaign.slug,
            campaign.name,
            campaign.guild_id,
            campaign.narrator_id,
            campaign.system,
            now,
            now,
        ),
    )
