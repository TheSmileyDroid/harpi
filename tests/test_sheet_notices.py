from __future__ import annotations

import asyncio
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from src import bot_state
from src.panel import sheet_notices
from src.storage.database import Database
from src.storage.seed import paratheos

SLUG = "paratheos"
NARRATOR = "100"
GUILD = "1"
OWNER = "555"
CHANNEL = "42"
ANA = f"Harpi/Campaigns/{SLUG}/sheets/Ana.md"
BIA = f"Harpi/Campaigns/{SLUG}/sheets/Bia.md"
CAIO = f"Harpi/Campaigns/{SLUG}/sheets/Caio.md"
DANI = f"Harpi/Campaigns/{SLUG}/sheets/Dani.md"
PANEL = "https://painel.example"


class FakeMessage:
    def __init__(self, message_id: int, content: str) -> None:
        self.id = message_id
        self.content = content
        self.edits: list[str] = []

    async def edit(self, content: str, *, allowed_mentions=None) -> None:
        del allowed_mentions
        self.content = content
        self.edits.append(content)


class FakeChannel:
    def __init__(self, fail: bool = False) -> None:
        self.sent: list[str] = []
        self.mentions: list[tuple[int, ...]] = []
        self.messages: dict[int, FakeMessage] = {}
        self.fail = fail

    async def send(
        self, content: str, *, allowed_mentions=None
    ) -> FakeMessage:
        if self.fail:
            raise RuntimeError("discord is down")
        users = (
            ()
            if allowed_mentions is None
            else tuple(user.id for user in allowed_mentions.users)
        )
        message = FakeMessage(9000 + len(self.sent), content)
        self.sent.append(content)
        self.mentions.append(users)
        self.messages[message.id] = message
        return message

    async def fetch_message(self, message_id: int) -> FakeMessage:
        return self.messages[message_id]


class FakeBot:
    def __init__(self, channel: FakeChannel) -> None:
        self.channel = channel

    def get_channel(self, channel_id: int) -> FakeChannel:
        del channel_id
        return self.channel


@pytest.fixture
async def world(tmp_path: Path):
    database = Database(
        tmp_path / "panel.db", campaign=paratheos(NARRATOR, GUILD)
    )
    await database.open()
    yield SimpleNamespace(database=database)
    await database.close()


@pytest.fixture
def discord(monkeypatch: pytest.MonkeyPatch):
    channel = FakeChannel()
    monkeypatch.setattr(bot_state, "_bot_ref", FakeBot(channel))

    async def inline(coro, timeout: float | None = None):
        del timeout
        return await coro

    monkeypatch.setattr(sheet_notices, "run_on_bot_loop", inline)
    return channel


async def add_sheet(
    database: Database,
    path: str,
    *,
    sheet_id: str,
    state: str = "ok",
    owner: str | None = OWNER,
) -> None:
    await database.execute(
        "INSERT INTO sheet_files ("
        "path, harpi_id, campaign, rev, hash, last_text, base_json, "
        "status, owner_id, state, updated_at"
        ") VALUES (?, ?, ?, 1, 'hash', '', '{}', 'ativo', ?, ?, 1)",
        (path, sheet_id, SLUG, owner, state),
    )


async def add_conflict(
    database: Database,
    path: str,
    field_path: str,
    now: int = 1,
) -> None:
    await database.execute(
        "INSERT INTO sheet_conflicts ("
        "id, path, field_path, base, ours, theirs, created_at"
        ") VALUES (?, ?, ?, '1', '2', '3', ?)",
        (f"cnf_{field_path}", path, field_path, now),
    )


async def open_table(database: Database, channel_id: str = CHANNEL) -> None:
    now = int(time.time())
    await database.execute(
        "INSERT INTO tables ("
        "id, campaign_slug, channel_id, name, status, round, spectators, rev, "
        "opened_by, opened_at, created_at, updated_at"
        ") VALUES ('tbl_1', ?, ?, 'Sessão', 'open', 1, 0, 1, ?, ?, ?, ?)",
        (SLUG, channel_id, NARRATOR, now, now, now),
    )


async def notice_rows(database: Database) -> list:
    return await database.fetchall(
        "SELECT * FROM sheet_notices ORDER BY created_at, id"
    )


async def test_a_conflict_posts_one_message_with_the_owner_narrator_and_link(
    world, discord, monkeypatch: pytest.MonkeyPatch
):
    await open_table(world.database)
    await add_sheet(world.database, ANA, sheet_id="sht_ana", state="conflito")
    await add_conflict(world.database, ANA, "block.refresh")
    monkeypatch.setattr(
        sheet_notices,
        "panel_link",
        lambda slug: f"{PANEL}/c/{slug}/personagens",
    )

    await sheet_notices.refresh(world.database, SLUG)

    assert len(discord.sent) == 1
    message = discord.sent[0]
    assert "Ana" in message
    assert f"<@{OWNER}>" in message
    assert f"<@{NARRATOR}>" in message
    assert "block.refresh" in message
    assert f"{PANEL}/c/{SLUG}/personagens" in message


async def test_five_conflicting_fields_still_make_one_message(world, discord):
    await open_table(world.database)
    await add_sheet(world.database, ANA, sheet_id="sht_ana", state="conflito")
    for field in (
        "block.refresh",
        "block.fate_points",
        "block.aspects[Conceito]",
        "block.stress[Físico].box[0]",
        "block.consequences[Leve]",
    ):
        await add_conflict(world.database, ANA, field)

    await sheet_notices.refresh(world.database, SLUG)
    await sheet_notices.refresh(world.database, SLUG)

    assert len(discord.sent) == 1
    assert "block.refresh" in discord.sent[0]
    assert "block.consequences[Leve]" in discord.sent[0]


async def test_without_an_open_table_nothing_is_posted_and_the_notice_waits(
    world, discord
):
    await add_sheet(world.database, ANA, sheet_id="sht_ana", state="conflito")
    await add_conflict(world.database, ANA, "block.refresh")

    await sheet_notices.refresh(world.database, SLUG)

    assert discord.sent == []
    pending = await sheet_notices.pending(world.database, SLUG, None)
    assert [(notice.name, notice.state) for notice in pending] == [
        ("Ana", "conflito")
    ]
    assert pending[0].fields == ("block.refresh",)
    rows = await notice_rows(world.database)
    assert rows[0]["message_id"] is None


async def test_missing_invalid_and_unknown_warn_once_each(world, discord):
    await open_table(world.database)
    await add_sheet(
        world.database, BIA, sheet_id="sht_bia", state="ausente", owner="501"
    )
    await add_sheet(
        world.database,
        CAIO,
        sheet_id="sht_caio",
        state="invalido",
        owner="502",
    )
    await add_sheet(
        world.database,
        DANI,
        sheet_id="sht_dani",
        state="desconhecido",
        owner="503",
    )

    await sheet_notices.refresh(world.database, SLUG)
    await sheet_notices.refresh(world.database, SLUG)

    assert len(discord.sent) == 3
    assert any(
        "Bia" in message and "ausente" in message for message in discord.sent
    )
    assert any(
        "Caio" in message and "inválida" in message for message in discord.sent
    )
    assert any(
        "Dani" in message and "desconhecida" in message
        for message in discord.sent
    )


async def test_resolving_edits_the_message_without_reposting(world, discord):
    await open_table(world.database)
    await add_sheet(world.database, ANA, sheet_id="sht_ana", state="conflito")
    await add_conflict(world.database, ANA, "block.refresh")
    await sheet_notices.refresh(world.database, SLUG)
    message = next(iter(discord.messages.values()))

    await world.database.execute(
        "UPDATE sheet_files SET state = 'ok' WHERE path = ?", (ANA,)
    )
    await sheet_notices.resolve(
        world.database, SLUG, ANA, "conflito", "Gabriel"
    )

    assert len(discord.sent) == 1
    assert message.content == "resolvido por Gabriel"
    pending = await sheet_notices.pending(world.database, SLUG, None)
    assert pending == []


async def test_a_state_that_leaves_closes_the_notice_without_a_duplicate(
    world, discord, monkeypatch: pytest.MonkeyPatch
):
    await open_table(world.database)
    await add_sheet(world.database, ANA, sheet_id="sht_ana", state="conflito")
    await add_conflict(world.database, ANA, "block.refresh")
    await sheet_notices.refresh(world.database, SLUG)

    monkeypatch.setattr(sheet_notices.time, "time", lambda: 500)
    await world.database.execute(
        "UPDATE sheet_files SET state = 'ok' WHERE path = ?", (ANA,)
    )
    await sheet_notices.refresh(world.database, SLUG)

    assert len(discord.sent) == 1
    assert await sheet_notices.pending(world.database, SLUG, None) == []
    rows = await notice_rows(world.database)
    assert rows[0]["resolved_at"] == 500


async def test_a_duplicate_identity_warns_once_per_file(world, discord):
    await open_table(world.database)
    await add_sheet(
        world.database, ANA, sheet_id="sht_ana", state="desconhecido"
    )
    await add_sheet(
        world.database,
        BIA,
        sheet_id="sht_ana",
        state="desconhecido",
        owner="556",
    )

    await sheet_notices.refresh(world.database, SLUG)

    assert len(discord.sent) == 2
    assert any("Ana" in message for message in discord.sent)
    assert any("Bia" in message for message in discord.sent)
    pending = await sheet_notices.pending(world.database, SLUG, None)
    assert [notice.path for notice in pending] == [ANA, BIA]


async def test_a_new_table_channel_gets_the_notice_again(world, discord):
    await open_table(world.database)
    await add_sheet(world.database, ANA, sheet_id="sht_ana", state="ausente")
    await sheet_notices.refresh(world.database, SLUG)

    await world.database.execute(
        "UPDATE tables SET channel_id = '43' WHERE status = 'open'"
    )
    await sheet_notices.refresh(world.database, SLUG)

    assert len(discord.sent) == 2
    rows = await notice_rows(world.database)
    assert rows[0]["channel_id"] == "43"


async def test_the_message_escapes_markdown_and_pings_only_the_users(
    world, discord, monkeypatch: pytest.MonkeyPatch
):
    await open_table(world.database)
    everywhere = f"Harpi/Campaigns/{SLUG}/sheets/@everyone.md"
    starred = f"Harpi/Campaigns/{SLUG}/sheets/A**B.md"
    await add_sheet(
        world.database, everywhere, sheet_id="sht_every", state="ausente"
    )
    await add_sheet(
        world.database,
        starred,
        sheet_id="sht_star",
        state="ausente",
        owner="556",
    )
    monkeypatch.setattr(
        sheet_notices,
        "panel_link",
        lambda slug: f"{PANEL}/c/{slug}/personagens",
    )

    await sheet_notices.refresh(world.database, SLUG)

    assert len(discord.sent) == 2
    assert "@everyone" in discord.sent[0]
    assert all(user != 0 for users in discord.mentions for user in users)
    assert discord.mentions[0] == (int(OWNER), int(NARRATOR))
    assert "A\\*\\*B" in discord.sent[1]
    assert "A**B" not in discord.sent[1].replace("A\\*\\*B", "")


async def test_a_huge_field_list_is_truncated_under_the_discord_limit(
    world, discord
):
    await open_table(world.database)
    await add_sheet(world.database, ANA, sheet_id="sht_ana", state="conflito")
    for index in range(60):
        await add_conflict(
            world.database,
            ANA,
            f"block.a_very_long_conflict_field_name_number_{index:02d}",
        )

    await sheet_notices.refresh(world.database, SLUG)

    assert len(discord.sent) == 1
    assert len(discord.sent[0]) <= 2000
    assert sheet_notices.ELLIPSIS in discord.sent[0]


async def test_concurrent_refreshes_post_one_message(
    world, monkeypatch: pytest.MonkeyPatch
):
    release = asyncio.Event()
    started = asyncio.Event()

    class SlowChannel(FakeChannel):
        async def send(self, content: str, *, allowed_mentions=None):
            started.set()
            await release.wait()
            return await super().send(
                content, allowed_mentions=allowed_mentions
            )

    channel = SlowChannel()
    monkeypatch.setattr(bot_state, "_bot_ref", FakeBot(channel))

    async def inline(coro, timeout: float | None = None):
        del timeout
        return await coro

    monkeypatch.setattr(sheet_notices, "run_on_bot_loop", inline)
    await open_table(world.database)
    await add_sheet(world.database, ANA, sheet_id="sht_ana", state="ausente")

    first = asyncio.create_task(sheet_notices.refresh(world.database, SLUG))
    await started.wait()
    second = asyncio.create_task(sheet_notices.refresh(world.database, SLUG))
    await asyncio.sleep(0)
    release.set()
    await asyncio.gather(first, second)

    assert len(channel.sent) == 1


async def test_a_deleted_message_still_closes_the_notice(world, discord):
    await open_table(world.database)
    await add_sheet(world.database, ANA, sheet_id="sht_ana", state="conflito")
    await sheet_notices.refresh(world.database, SLUG)
    message = next(iter(discord.messages.values()))
    del discord.messages[message.id]

    await world.database.execute(
        "UPDATE sheet_files SET state = 'ok' WHERE path = ?", (ANA,)
    )
    await sheet_notices.resolve(
        world.database, SLUG, ANA, "conflito", "Gabriel"
    )

    assert await sheet_notices.pending(world.database, SLUG, None) == []


async def test_a_new_conflict_field_edits_the_existing_message(world, discord):
    await open_table(world.database)
    await add_sheet(world.database, ANA, sheet_id="sht_ana", state="conflito")
    await add_conflict(world.database, ANA, "block.refresh")
    await sheet_notices.refresh(world.database, SLUG)

    await add_conflict(world.database, ANA, "block.fate_points")
    await sheet_notices.refresh(world.database, SLUG)

    assert len(discord.sent) == 1
    message = next(iter(discord.messages.values()))
    assert "block.fate\\_points" in message.content
    assert message.edits[-1] == message.content


async def test_a_fixed_invalid_sheet_closes_the_message(world, discord):
    await open_table(world.database)
    await add_sheet(
        world.database, CAIO, sheet_id="sht_caio", state="invalido"
    )
    await sheet_notices.refresh(world.database, SLUG)
    message = next(iter(discord.messages.values()))

    await world.database.execute(
        "UPDATE sheet_files SET state = 'ok' WHERE path = ?", (CAIO,)
    )
    await sheet_notices.refresh(world.database, SLUG)

    assert message.content == "aviso encerrado"
    assert await sheet_notices.pending(world.database, SLUG, None) == []


async def test_a_failing_discord_keeps_the_notice_for_the_panel(
    world, discord
):
    discord.fail = True
    await open_table(world.database)
    await add_sheet(world.database, ANA, sheet_id="sht_ana", state="conflito")

    await sheet_notices.refresh(world.database, SLUG)

    rows = await notice_rows(world.database)
    assert rows[0]["message_id"] is None
    assert len(await sheet_notices.pending(world.database, SLUG, None)) == 1


def test_panel_link_requires_a_public_base(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("PANEL_BASE_URL", raising=False)
    assert sheet_notices.panel_link(SLUG) == ""
    assert "Painel:" not in sheet_notices.notice_text(
        "Ana", "ausente", None, None, (), ""
    )

    monkeypatch.setenv("PANEL_BASE_URL", f"{PANEL}/")

    assert sheet_notices.panel_link(SLUG) == f"{PANEL}/c/{SLUG}/personagens"


async def test_background_refresh_does_not_wait_for_discord(
    world, monkeypatch: pytest.MonkeyPatch
):
    release = asyncio.Event()
    started = asyncio.Event()

    class SlowChannel(FakeChannel):
        async def send(self, content: str, *, allowed_mentions=None):
            started.set()
            await release.wait()
            return await super().send(
                content, allowed_mentions=allowed_mentions
            )

    channel = SlowChannel()
    monkeypatch.setattr(bot_state, "_bot_ref", FakeBot(channel))

    async def inline(coro, timeout: float | None = None):
        del timeout
        return await coro

    monkeypatch.setattr(sheet_notices, "run_on_bot_loop", inline)
    await open_table(world.database)
    await add_sheet(world.database, ANA, sheet_id="sht_ana", state="ausente")

    background = asyncio.create_task(
        sheet_notices.refresh_background(world.database, SLUG)
    )
    await asyncio.sleep(0)
    assert background.done()
    await asyncio.wait_for(started.wait(), 1)
    release.set()
    await sheet_notices.drain()
    assert len(channel.sent) == 1


async def test_the_owner_sees_only_the_own_notices(world):
    await add_sheet(world.database, ANA, sheet_id="sht_ana", state="ausente")
    await add_sheet(
        world.database, BIA, sheet_id="sht_bia", state="ausente", owner="999"
    )
    await sheet_notices.refresh(world.database, SLUG)

    narrator = await sheet_notices.pending(world.database, SLUG, None)
    owner = await sheet_notices.pending(world.database, SLUG, OWNER)

    assert [notice.name for notice in narrator] == ["Ana", "Bia"]
    assert [notice.name for notice in owner] == ["Ana"]
