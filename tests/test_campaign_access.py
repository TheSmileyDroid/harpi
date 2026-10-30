from __future__ import annotations

import pytest

from src.panel.campaigns import CampaignAccess
from src.storage.database import Database
from src.storage.seed import paratheos

GUILD = "734174030701264906"
OTHER_GUILD = "896066642948259960"
NARRATOR = "100"
PLAYER = "555"
STRANGER = "777"
SLUG = "paratheos"
JOINED_AT = 1_700_000_000


@pytest.fixture
async def database(tmp_path):
    database = Database(
        tmp_path / "panel.db", campaign=paratheos(NARRATOR, GUILD)
    )
    await database.open()
    yield database
    await database.close()


@pytest.fixture
def access(database: Database) -> CampaignAccess:
    return CampaignAccess(database)


async def add_member(
    database: Database, user_id: str = PLAYER, slug: str = SLUG
) -> None:
    await database.execute(
        "INSERT INTO members (campaign_slug, user_id, display_name, joined_at) "
        "VALUES (?, ?, ?, ?)",
        (slug, user_id, "Panel User", JOINED_AT),
    )


async def add_sheet(
    database: Database,
    user_id: str = PLAYER,
    status: str = "ativo",
    path: str = "Harpi/Campaigns/paratheos/sheets/Ana.md",
) -> None:
    await database.execute(
        "INSERT INTO sheet_files ("
        "path, harpi_id, campaign, rev, hash, last_text, base_json, "
        "status, owner_id, state, updated_at"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (path, "sht_1", SLUG, 1, "h", "text", "{}", status, user_id, "ok", 1),
    )


async def members(database: Database) -> list[tuple[object, ...]]:
    rows = await database.fetchall(
        "SELECT campaign_slug, user_id, display_name, joined_at FROM members"
    )
    return [tuple(row) for row in rows]


async def test_the_seed_creates_the_paratheos_campaign(database: Database):
    row = await database.fetchone("SELECT * FROM campaigns")

    assert row is not None
    assert row["slug"] == SLUG
    assert row["name"] == "Paratheos"
    assert row["guild_id"] == GUILD
    assert row["narrator_id"] == NARRATOR
    assert row["system"] == "fate"
    assert row["content_source"] == "vault"


async def test_the_seed_keeps_the_first_row(tmp_path):
    first = Database(tmp_path / "seed.db", campaign=paratheos(NARRATOR, GUILD))
    await first.open()
    await first.close()

    second = Database(
        tmp_path / "seed.db", campaign=paratheos("200", OTHER_GUILD)
    )
    await second.open()
    rows = await second.fetchall("SELECT * FROM campaigns")
    await second.close()

    assert len(rows) == 1
    assert rows[0]["narrator_id"] == NARRATOR
    assert rows[0]["guild_id"] == GUILD


async def test_without_the_ids_no_campaign_is_seeded(tmp_path):
    assert paratheos(None, GUILD) is None
    assert paratheos(NARRATOR, None) is None

    database = Database(tmp_path / "empty.db", campaign=paratheos(None, GUILD))
    await database.open()
    row = await database.fetchone("SELECT COUNT(*) AS n FROM campaigns")
    await database.close()

    assert row is not None
    assert row["n"] == 0


async def test_the_narrator_sees_the_campaign_without_a_member_row(
    access: CampaignAccess,
):
    campaigns = await access.campaigns(NARRATOR, {GUILD})

    assert [(campaign.slug, campaign.role) for campaign in campaigns] == [
        (SLUG, "narrator")
    ]


async def test_a_member_with_an_active_sheet_is_a_player(
    database: Database, access: CampaignAccess
):
    await add_member(database)
    await add_sheet(database)

    campaign = await access.campaign(SLUG, PLAYER, {GUILD})

    assert campaign is not None
    assert campaign.role == "player"


async def test_a_member_without_an_active_sheet_is_pending(
    database: Database, access: CampaignAccess
):
    await add_member(database)

    campaign = await access.campaign(SLUG, PLAYER, {GUILD})

    assert campaign is not None
    assert campaign.role == "pending"


async def test_a_pending_sheet_keeps_the_member_pending(
    database: Database, access: CampaignAccess
):
    await add_member(database)
    await add_sheet(database, status="pendente")

    campaign = await access.campaign(SLUG, PLAYER, {GUILD})

    assert campaign is not None
    assert campaign.role == "pending"


async def test_an_archived_sheet_keeps_the_member_pending(
    database: Database, access: CampaignAccess
):
    await add_member(database)
    await add_sheet(database, status="arquivado")

    campaign = await access.campaign(SLUG, PLAYER, {GUILD})

    assert campaign is not None
    assert campaign.role == "pending"


async def test_an_active_sheet_outranks_an_archived_one(
    database: Database, access: CampaignAccess
):
    await add_member(database)
    await add_sheet(database, status="arquivado", path="sheets/old.md")
    await add_sheet(database, status="ativo", path="sheets/new.md")

    campaign = await access.campaign(SLUG, PLAYER, {GUILD})

    assert campaign is not None
    assert campaign.role == "player"


async def test_approving_a_sheet_changes_the_role_without_member_writes(
    database: Database, access: CampaignAccess
):
    await add_member(database)
    await add_sheet(database, status="pendente")
    before = await members(database)
    await database.execute(
        "UPDATE sheet_files SET status = 'ativo' WHERE path = ?",
        ("Harpi/Campaigns/paratheos/sheets/Ana.md",),
    )
    campaign = await access.campaign(SLUG, PLAYER, {GUILD})

    assert campaign is not None
    assert campaign.role == "player"
    assert await members(database) == before


async def test_a_stranger_has_no_access(access: CampaignAccess):
    assert await access.campaigns(STRANGER, {GUILD}) == []
    assert await access.campaign(SLUG, STRANGER, {GUILD}) is None


async def test_a_campaign_outside_the_users_guilds_is_hidden(
    database: Database, access: CampaignAccess
):
    await add_member(database)

    assert await access.campaigns(PLAYER, {OTHER_GUILD}) == []
    assert await access.campaign(SLUG, PLAYER, {OTHER_GUILD}) is None


async def test_an_unknown_slug_is_none(access: CampaignAccess):
    assert await access.campaign("nowhere", NARRATOR, {GUILD}) is None


async def test_the_detail_reports_no_open_table(access: CampaignAccess):
    campaign = await access.campaign(SLUG, NARRATOR, {GUILD})

    assert campaign is not None
    assert campaign.open_table is None
    assert campaign.name == "Paratheos"
    assert campaign.system == "fate"
