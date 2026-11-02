from __future__ import annotations

import asyncio
import json
import random
import threading
from types import SimpleNamespace
from typing import Any, cast

import pytest

from app import app as quart_app
from app import configure_panel_session
from pages import campaigns as campaigns_page
from pages import tables as tables_page
from src import bot_state
from src.config import Settings
from src.cogs.dice_cog import NO_TABLE_ACCESS, DiceCog
from src.harpi_lib.harpi_bot import HarpiBot
from src.panel import (
    rate_limit,
    rolls,
    table_stream,
    vault,
    vault_index,
)
from src.panel import tables as table_domain
from src.panel.vault_index import VaultIndex
from src.storage import (
    clear_database,
    clear_registry,
    init_database,
    init_registry,
)
from src.storage.database import Database
from src.storage.registry import SqliteRegistry
from src.storage.seed import paratheos
from tests.test_tables import (
    CHANNEL,
    CSRF,
    GUILD,
    NARRATOR,
    PLAYER,
    SECRET,
    STRANGER,
    add_member,
    activate_sheet,
    body,
    image_scene,
    open_table,
    sign_in,
)

TABLES_ROUTE = "/api/tables"


@pytest.fixture
async def world(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SECRET_KEY", SECRET)
    configure_panel_session(Settings.from_env())
    quart_app.config["TESTING"] = True
    root = tmp_path / "vault"
    root.mkdir()
    database = Database(
        tmp_path / "panel.db", campaign=paratheos(NARRATOR, str(GUILD))
    )
    await database.open()
    init_registry(SqliteRegistry(database))
    init_database(database)
    campaigns_page.SCENE_WRITE_BUCKETS = rate_limit.UserTokenBuckets(
        rate_limit.SCENE_WRITES_PER_MINUTE
    )
    tables_page.ROLL_POST_BUCKETS = rate_limit.UserTokenBuckets(
        rate_limit.ROLLS_PER_MINUTE
    )
    tables_page.ROLL_READ_BUCKETS = rate_limit.UserTokenBuckets(
        rate_limit.ROLL_READS_PER_MINUTE
    )
    vault.configure(vault.Vault(root=root))
    vault_index.configure(VaultIndex(root))
    yield SimpleNamespace(root=root, database=database)
    clear_registry()
    clear_database()
    vault.configure(vault.Vault())
    vault_index.configure(vault_index.VaultIndex())
    await database.close()


@pytest.fixture
async def client(world):
    return quart_app.test_client()


class FakeTextChannel:
    def __init__(self, fail: bool = False) -> None:
        self.sent: list[str] = []
        self.fail = fail

    async def send(self, content: str) -> SimpleNamespace:
        if self.fail:
            raise RuntimeError("discord is down")
        self.sent.append(content)
        return SimpleNamespace(id=9000 + len(self.sent))


class FakeBot:
    def __init__(self, channel: FakeTextChannel | None = None) -> None:
        self.user = SimpleNamespace(id=1234, bot=True)
        self.channel = channel or FakeTextChannel()

    def get_channel(self, channel_id: int) -> FakeTextChannel:
        del channel_id
        return self.channel


class RecordingMessage:
    def __init__(
        self,
        *,
        content: str = "1d1",
        bot: bool = False,
        webhook_id: int | None = None,
        channel_id: str = CHANNEL,
        guild_id: int = GUILD,
        message_id: int = 990,
        author_id: str = PLAYER,
        label: str = "Jogadora",
    ) -> None:
        self.content = content
        self.author = SimpleNamespace(
            id=author_id, bot=bot, display_name=label, name=label
        )
        self.guild = SimpleNamespace(id=guild_id)
        self.channel = SimpleNamespace(id=channel_id)
        self.id = message_id
        self.webhook_id = webhook_id
        self.replies: list[str] = []

    async def reply(self, content: str) -> None:
        self.replies.append(content)


@pytest.fixture
def discord(monkeypatch: pytest.MonkeyPatch):
    channel = FakeTextChannel()
    bot = FakeBot(channel)
    monkeypatch.setattr(bot_state, "_bot_ref", bot)

    async def inline(coro, timeout: float | None = None):
        del timeout
        return await coro

    monkeypatch.setattr(rolls, "run_on_bot_loop", inline)
    return SimpleNamespace(bot=bot, channel=channel)


@pytest.fixture
async def panel_loop():
    bot_state.init_panel_loop(asyncio.get_running_loop())
    yield
    bot_state.clear_panel_loop()


async def live_table(client, world, **scene: Any) -> str:
    await sign_in(client, NARRATOR)
    await image_scene(client, world, fog_outside=False, **scene)
    response, summary = await open_table(client)
    assert response.status_code == 200, summary
    return summary["id"]


async def post_roll(client, table_id: str, expression: str):
    return await client.post(
        f"{TABLES_ROUTE}/{table_id}/rolls",
        json={"expression": expression},
        headers=CSRF,
    )


async def roll_rows(world, table_id: str) -> list[dict[str, Any]]:
    rows = await world.database.fetchall(
        "SELECT * FROM rolls WHERE table_id = ? ORDER BY created_at, id",
        (table_id,),
    )
    return [dict(row) for row in rows]


def fixed_dice(monkeypatch: pytest.MonkeyPatch, *values: int) -> None:
    pool = list(values)

    def take(*_args: Any, **_kwargs: Any) -> int:
        return pool.pop(0) if pool else values[-1]

    monkeypatch.setattr(random, "randint", take)
    monkeypatch.setattr(random, "choice", take)


async def test_panel_roll_posts_the_message_and_records_its_id(
    client, world, discord, monkeypatch
):
    table_id = await live_table(client, world)
    fixed_dice(monkeypatch, 1, 0, 1, 0)

    response = await post_roll(client, table_id, "4dF")

    assert response.status_code == 200, await body(response)
    payload = await body(response)
    assert len(payload["rolls"]) == 1
    roll = payload["rolls"][0]
    assert roll["source"] == "panel"
    assert roll["actor_id"] == NARRATOR
    assert roll["scene_label"] == "Cripta"
    assert roll["discord_message_id"] == "9001"
    assert roll["total"] == roll["dice"]["groups"][0]["total"]
    assert roll["id"].startswith("rol_")
    assert discord.channel.sent == [
        f"**panel-user** · Cripta — {roll['text']}"
    ]
    rows = await roll_rows(world, table_id)
    assert len(rows) == 1
    assert rows[0]["discord_message_id"] == "9001"


async def test_panel_roll_frozen_text_matches_the_parser(
    monkeypatch, client, world, discord
):
    table_id = await live_table(client, world)
    fixed_dice(monkeypatch, 3, 5)
    response = await post_roll(client, table_id, "2d6+1")
    assert response.status_code == 200, await body(response)
    roll = (await body(response))["rolls"][0]
    assert roll["text"] == "` 9 ` ⟵ [3, 5] 2d6 + 1"
    assert roll["dice"] == {
        "index": 1,
        "of": 1,
        "expression": "2d6+1",
        "groups": [
            {
                "notation": "2d6",
                "values": [3, 5],
                "kept": None,
                "total": 8,
            }
        ],
    }


async def test_discord_failure_is_502_and_writes_nothing(
    client, world, monkeypatch
):
    table_id = await live_table(client, world)
    channel = FakeTextChannel(fail=True)
    monkeypatch.setattr(bot_state, "_bot_ref", FakeBot(channel))

    async def inline(coro, timeout: float | None = None):
        del timeout
        return await coro

    monkeypatch.setattr(rolls, "run_on_bot_loop", inline)

    response = await post_roll(client, table_id, "1d6")

    assert response.status_code == 502
    assert (await body(response))["error"]["code"] == "discord_unavailable"
    assert await roll_rows(world, table_id) == []


async def test_panel_roll_publishes_one_table_roll_frame(
    client, world, discord
):
    table_id = await live_table(client, world)
    row = await table_domain.table_row(world.database, table_id)
    assert row is not None
    stream = table_stream.open_stream(
        world.database,
        row,
        user_id=NARRATOR,
        role="narrator",
        name="Narrador",
        root=None,
    )
    await anext(stream)
    await anext(stream)

    response = await post_roll(client, table_id, "1d1")
    assert response.status_code == 200, await body(response)

    raw = await asyncio.wait_for(anext(stream), 1)
    lines = raw.splitlines()
    assert lines[0] == "event: table.roll"
    frame = json.loads(lines[1][len("data: ") :])
    assert frame["id"] == (await body(response))["rolls"][0]["id"]
    await stream.aclose()


async def test_repeat_records_one_row_per_roll_and_one_message(
    client, world, discord
):
    table_id = await live_table(client, world)
    response = await post_roll(client, table_id, "3#1d1")
    assert response.status_code == 200, await body(response)
    payload = await body(response)
    assert len(payload["rolls"]) == 3
    assert [roll["dice"]["index"] for roll in payload["rolls"]] == [1, 2, 3]
    assert [roll["discord_message_id"] for roll in payload["rolls"]] == [
        "9001",
        None,
        None,
    ]
    assert len(discord.channel.sent) == 1
    assert "Max: 1" in discord.channel.sent[0]
    assert len(await roll_rows(world, table_id)) == 3


@pytest.mark.parametrize(
    ("expression", "code"),
    [
        ("2+2", "no_dice"),
        ("1d0", "invalid_expression"),
        ("1d6/0", "invalid_expression"),
        ("21d6", "too_many_dice"),
        ("11#1d6", "too_many_repeats"),
        ("1d6^100000", "result_too_large"),
        ("x" * 121, "expression_too_long"),
    ],
)
async def test_expression_limits_answer_422(
    client, world, discord, monkeypatch, expression, code
):
    monkeypatch.setattr(random, "randint", lambda _low, _high: 6)
    table_id = await live_table(client, world)
    response = await post_roll(client, table_id, expression)
    assert response.status_code == 422, await body(response)
    assert (await body(response))["error"]["code"] == code
    assert await roll_rows(world, table_id) == []


async def test_non_integer_result_is_422(client, world, discord, monkeypatch):
    table_id = await live_table(client, world)
    monkeypatch.setattr(random, "randint", lambda _low, _high: 4)
    response = await post_roll(client, table_id, "1d6/2")
    assert response.status_code == 422
    assert (await body(response))["error"]["code"] == "non_integer_result"


async def test_pending_and_spectator_cannot_post(client, world, discord):
    table_id = await live_table(client, world)
    await add_member(world.database, STRANGER)
    await sign_in(client, STRANGER)
    pending = await post_roll(client, table_id, "1d6")
    assert pending.status_code == 403
    await sign_in(client, "888")
    await world.database.execute(
        "UPDATE tables SET spectators = 1 WHERE id = ?", (table_id,)
    )
    spectator = await post_roll(client, table_id, "1d6")
    assert spectator.status_code == 403
    assert await roll_rows(world, table_id) == []


async def test_closed_table_rejects_post_and_allows_member_get(
    client, world, discord
):
    table_id = await live_table(client, world)
    await post_roll(client, table_id, "1d6")
    await client.post(
        f"{TABLES_ROUTE}/{table_id}/close", json={}, headers=CSRF
    )
    await add_member(world.database, PLAYER)
    await activate_sheet(world.database, PLAYER)
    await sign_in(client, PLAYER)

    response = await post_roll(client, table_id, "1d6")

    assert response.status_code == 409
    assert (await body(response))["error"]["code"] == "table_closed"
    read = await client.get(f"{TABLES_ROUTE}/{table_id}/rolls")
    assert read.status_code == 200
    assert len((await body(read))["rolls"]) == 1


async def test_get_rolls_pages_by_created_at_and_id(client, world, discord):
    table_id = await live_table(client, world)
    for expression in ("1d1", "1d1", "1d1"):
        assert (
            await post_roll(client, table_id, expression)
        ).status_code == 200
    first = await body(
        await client.get(f"{TABLES_ROUTE}/{table_id}/rolls?limit=2")
    )
    assert len(first["rolls"]) == 2
    after = first["rolls"][-1]["id"]
    second = await body(
        await client.get(
            f"{TABLES_ROUTE}/{table_id}/rolls?after={after}&limit=50"
        )
    )
    assert len(second["rolls"]) == 1
    assert second["rolls"][0]["id"] not in {
        roll["id"] for roll in first["rolls"]
    }
    bad = await client.get(
        f"{TABLES_ROUTE}/{table_id}/rolls?after=rol_unknown"
    )
    assert bad.status_code == 422
    assert (await body(bad))["error"]["code"] == "bad_cursor"
    for limit in ("0", "201", "x"):
        invalid = await client.get(
            f"{TABLES_ROUTE}/{table_id}/rolls?limit={limit}"
        )
        assert invalid.status_code == 422


async def test_spectator_reads_only_while_the_table_is_open(client, world):
    table_id = await live_table(client, world)
    await sign_in(client, STRANGER)
    closed_spectator = await client.get(f"{TABLES_ROUTE}/{table_id}/rolls")
    assert closed_spectator.status_code == 404
    await world.database.execute(
        "UPDATE tables SET spectators = 1 WHERE id = ?", (table_id,)
    )
    open_spectator = await client.get(f"{TABLES_ROUTE}/{table_id}/rolls")
    assert open_spectator.status_code == 200


async def test_channel_roll_records_once_and_replies(client, world):
    table_id = await live_table(client, world)
    await add_member(world.database, PLAYER)
    await activate_sheet(world.database, PLAYER)

    first = await rolls.channel_roll(
        channel_id=CHANNEL,
        guild_id=str(GUILD),
        author_id=PLAYER,
        author_label="Jogadora",
        message_id="555000111",
        expression="1d1",
    )
    second = await rolls.channel_roll(
        channel_id=CHANNEL,
        guild_id=str(GUILD),
        author_id=PLAYER,
        author_label="Jogadora",
        message_id="555000111",
        expression="1d1",
    )

    assert first is not None
    assert first.text is not None
    assert first.text.startswith("**Jogadora** · Cripta — `")
    assert second is not None
    assert second.text is None
    rows = await roll_rows(world, table_id)
    assert len(rows) == 1
    assert rows[0]["source"] == "discord"
    assert rows[0]["actor_id"] == PLAYER
    assert rows[0]["discord_message_id"] == "555000111"


async def test_channel_roll_outside_a_table_is_not_recorded(world):
    result = await rolls.channel_roll(
        channel_id="999",
        guild_id=str(GUILD),
        author_id=PLAYER,
        author_label="Jogadora",
        message_id="1",
        expression="1d6",
    )
    assert result is None


async def test_channel_roll_refuses_a_stranger(client, world):
    table_id = await live_table(client, world)
    result = await rolls.channel_roll(
        channel_id=CHANNEL,
        guild_id=str(GUILD),
        author_id=STRANGER,
        author_label="Visitante",
        message_id="42",
        expression="1d1",
    )
    assert result is not None
    assert result.refused is True
    assert await roll_rows(world, table_id) == []


async def test_channel_roll_refuses_a_pending_member(client, world):
    table_id = await live_table(client, world)
    await add_member(world.database, STRANGER)
    result = await rolls.channel_roll(
        channel_id=CHANNEL,
        guild_id=str(GUILD),
        author_id=STRANGER,
        author_label="Pendente",
        message_id="43",
        expression="1d1",
    )
    assert result is not None
    assert result.refused is True
    assert await roll_rows(world, table_id) == []


async def test_turn_id_is_context_for_the_authors_token(client, world):
    table_id = await live_table(client, world)
    await add_member(world.database, PLAYER)
    await activate_sheet(world.database, PLAYER)
    await sign_in(client, NARRATOR)
    created = await client.post(
        f"{TABLES_ROUTE}/{table_id}/tokens",
        json={"label": "Ana", "x": 1, "y": 1, "owner_id": PLAYER},
        headers=CSRF,
    )
    token_id = (await body(created))["tokens"][0]["id"]
    opened = await client.post(
        f"{TABLES_ROUTE}/{table_id}/turns",
        json={"action": "open", "token_id": token_id},
        headers=CSRF,
    )
    assert opened.status_code == 200, await body(opened)
    turn_id = (await body(opened))["turn"]["id"]

    narrator = await rolls.channel_roll(
        channel_id=CHANNEL,
        guild_id=str(GUILD),
        author_id=NARRATOR,
        author_label="Narrador",
        message_id="700",
        expression="1d1",
    )
    player = await rolls.channel_roll(
        channel_id=CHANNEL,
        guild_id=str(GUILD),
        author_id=PLAYER,
        author_label="Jogadora",
        message_id="701",
        expression="1d1",
    )

    assert narrator is not None and player is not None
    rows = await roll_rows(world, table_id)
    assert rows[0]["turn_id"] is None
    assert rows[1]["turn_id"] == turn_id


async def test_scene_label_survives_scene_removal(client, world, discord):
    table_id = await live_table(client, world)
    assert (await post_roll(client, table_id, "1d1")).status_code == 200
    await world.database.execute("DELETE FROM scenes")
    read = await client.get(f"{TABLES_ROUTE}/{table_id}/rolls")
    roll = (await body(read))["rolls"][0]
    assert roll["scene_id"] is None
    assert roll["scene_label"] == "Cripta"


@pytest.mark.usefixtures("panel_loop")
async def test_cog_ignores_bots_and_webhooks(client, world):
    await live_table(client, world)
    cog = DiceCog(
        cast(HarpiBot, SimpleNamespace(user=SimpleNamespace(id=1234)))
    )

    class Message:
        def __init__(self, content: str, bot: bool = False) -> None:
            self.content = content
            self.author = SimpleNamespace(
                id=PLAYER, bot=bot, display_name="Jogadora", name="Jogadora"
            )
            self.guild = SimpleNamespace(id=GUILD)
            self.channel = SimpleNamespace(id=CHANNEL)
            self.id = 900
            self.webhook_id = 77 if bot else None
            self.replies: list[str] = []

        async def reply(self, content: str) -> None:
            self.replies.append(content)

    bot_message = Message("1d6", bot=True)
    await cog.on_message(cast(Any, bot_message))

    class Webhook(Message):
        def __init__(self) -> None:
            super().__init__("1d6")
            self.webhook_id = 77

    webhook = Webhook()
    await cog.on_message(cast(Any, webhook))

    assert bot_message.replies == []
    assert webhook.replies == []
    assert await world.database.fetchall("SELECT * FROM rolls") == []


@pytest.mark.usefixtures("panel_loop")
async def test_cog_mirrors_a_channel_roll(client, world):
    table_id = await live_table(client, world)
    await add_member(world.database, PLAYER)
    await activate_sheet(world.database, PLAYER)
    cog = DiceCog(
        cast(HarpiBot, SimpleNamespace(user=SimpleNamespace(id=1234)))
    )

    class Message:
        def __init__(self) -> None:
            self.content = "1d1"
            self.author = SimpleNamespace(
                id=PLAYER, bot=False, display_name="Jogadora", name="Jogadora"
            )
            self.guild = SimpleNamespace(id=GUILD)
            self.channel = SimpleNamespace(id=CHANNEL)
            self.id = 901
            self.webhook_id = None
            self.replies: list[str] = []

        async def reply(self, content: str) -> None:
            self.replies.append(content)

    message = Message()
    await cog.on_message(cast(Any, message))

    rows = await roll_rows(world, table_id)
    assert len(rows) == 1
    assert message.replies == [f"**Jogadora** · Cripta — {rows[0]['text']}"]


@pytest.mark.usefixtures("panel_loop")
async def test_cog_answers_dice_outside_a_table_as_before(client, world):
    await live_table(client, world)
    cog = DiceCog(
        cast(HarpiBot, SimpleNamespace(user=SimpleNamespace(id=1234)))
    )

    class Message:
        def __init__(self) -> None:
            self.content = "1d1"
            self.author = SimpleNamespace(
                id=PLAYER, bot=False, display_name="Jogadora", name="Jogadora"
            )
            self.guild = SimpleNamespace(id=GUILD)
            self.channel = SimpleNamespace(id=999)
            self.id = 902
            self.webhook_id = None
            self.replies: list[str] = []

        async def reply(self, content: str) -> None:
            self.replies.append(content)

    message = Message()
    await cog.on_message(cast(Any, message))

    assert message.replies == ["` 1 ` ⟵ [**1**] 1d1"]
    assert await world.database.fetchall("SELECT * FROM rolls") == []


async def test_panel_loop_bridge_runs_on_its_own_loop():
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    bot_state.init_panel_loop(loop)
    try:
        assert (
            await bot_state.run_on_panel_loop(asyncio.sleep(0, result=7)) == 7
        )
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join()
        loop.close()
        bot_state.clear_panel_loop()


async def test_panel_loop_bridge_refuses_without_a_loop():
    with pytest.raises(RuntimeError):
        await bot_state.run_on_panel_loop(asyncio.sleep(0))


async def test_roll_list_is_empty_for_a_table_without_rolls(client, world):
    table_id = await live_table(client, world)
    read = await client.get(f"{TABLES_ROUTE}/{table_id}/rolls")
    assert read.status_code == 200
    assert (await body(read)) == {"rolls": []}


async def test_zero_repeats_and_kept_masks(
    client, world, discord, monkeypatch
):
    table_id = await live_table(client, world)
    zero = await post_roll(client, table_id, "0#1d6")
    assert zero.status_code == 422
    assert (await body(zero))["error"]["code"] == "invalid_expression"
    fixed_dice(monkeypatch, 7, 15)
    kept = await post_roll(client, table_id, "2d20kh1")
    assert kept.status_code == 200, await body(kept)
    roll = (await body(kept))["rolls"][0]
    assert roll["total"] == 15
    assert roll["dice"]["groups"][0]["kept"] == [False, True]
    assert roll["dice"]["groups"][0]["total"] == 15


async def test_roll_without_a_scene_has_no_scene_segment(
    client, world, discord
):
    table_id = await live_table(client, world)
    await world.database.execute("DELETE FROM scenes")
    response = await post_roll(client, table_id, "1d1")
    assert response.status_code == 200, await body(response)
    roll = (await body(response))["rolls"][0]
    assert roll["scene_id"] is None
    assert roll["scene_label"] == ""
    assert discord.channel.sent == [f"**panel-user** — {roll['text']}"]


async def test_body_above_one_kilobyte_is_413(client, world, discord):
    table_id = await live_table(client, world)
    response = await post_roll(client, table_id, "1d6" + " " * 1100)
    assert response.status_code == 413
    assert (await body(response))["error"]["code"] == "payload_too_large"


async def test_roll_buckets_refuse_after_the_budget(
    client, world, discord, monkeypatch
):
    table_id = await live_table(client, world)
    monkeypatch.setattr(
        tables_page, "ROLL_POST_BUCKETS", rate_limit.UserTokenBuckets(1)
    )
    assert (await post_roll(client, table_id, "1d1")).status_code == 200
    limited = await post_roll(client, table_id, "1d1")
    assert limited.status_code == 429
    assert limited.headers["Retry-After"]
    monkeypatch.setattr(
        tables_page, "ROLL_READ_BUCKETS", rate_limit.UserTokenBuckets(1)
    )
    assert (
        await client.get(f"{TABLES_ROUTE}/{table_id}/rolls")
    ).status_code == 200
    read_limited = await client.get(f"{TABLES_ROUTE}/{table_id}/rolls")
    assert read_limited.status_code == 429


async def test_channel_roll_rejects_an_expression_without_dice(client, world):
    table_id = await live_table(client, world)
    result = await rolls.channel_roll(
        channel_id=CHANNEL,
        guild_id=str(GUILD),
        author_id=PLAYER,
        author_label="Jogadora",
        message_id="1",
        expression="2+2",
    )
    assert result is None
    assert await roll_rows(world, table_id) == []


async def test_post_message_uses_fetch_when_the_cache_misses(
    monkeypatch, discord
):
    channel = FakeTextChannel()

    class FetchBot(FakeBot):
        def get_channel(self, channel_id: int):
            del channel_id
            return

        async def fetch_channel(self, channel_id: int):
            del channel_id
            return channel

    monkeypatch.setattr(bot_state, "_bot_ref", FetchBot())

    async def inline(coro, timeout: float | None = None):
        del timeout
        return await coro

    monkeypatch.setattr(rolls, "run_on_bot_loop", inline)

    message_id = await rolls.post_message("42", "hello")

    assert message_id == "9001"
    assert channel.sent == ["hello"]

    class MissingBot(FetchBot):
        async def fetch_channel(self, channel_id: int):
            del channel_id
            return

    monkeypatch.setattr(bot_state, "_bot_ref", MissingBot())
    with pytest.raises(rolls.DiscordUnavailable):
        await rolls.post_message("42", "hello")


async def test_the_log_survives_a_database_reopen(client, world, discord):
    table_id = await live_table(client, world)
    assert (await post_roll(client, table_id, "1d1")).status_code == 200
    path = world.database.path
    await world.database.close()
    reopened = Database(path)
    await reopened.open()
    try:
        rows = await rolls.list_rolls(reopened, table_id, after=None, limit=50)
        assert len(rows) == 1
        assert rows[0].table_id == table_id
    finally:
        await reopened.close()


@pytest.mark.usefixtures("panel_loop")
async def test_d_command_mirrors_inside_a_table_channel(client, world):
    table_id = await live_table(client, world)
    await add_member(world.database, PLAYER)
    await activate_sheet(world.database, PLAYER)
    cog = DiceCog(
        cast(HarpiBot, SimpleNamespace(user=SimpleNamespace(id=1234)))
    )

    class Context:
        def __init__(self) -> None:
            self.message = SimpleNamespace(
                id=950,
                guild=SimpleNamespace(id=GUILD),
                channel=SimpleNamespace(id=CHANNEL),
                author=SimpleNamespace(
                    id=PLAYER,
                    bot=False,
                    display_name="Jogadora",
                    name="Jogadora",
                ),
            )
            self.sent: list[str] = []

        async def reply(self, content: str) -> None:
            self.sent.append(content)

    ctx = Context()
    callback = cast(Any, cog.roll.callback)
    await callback(cog, ctx, args="1d1")

    rows = await roll_rows(world, table_id)
    assert len(rows) == 1
    assert ctx.sent == [f"**Jogadora** · Cripta — {rows[0]['text']}"]


@pytest.mark.usefixtures("panel_loop")
async def test_d_command_outside_a_table_answers_as_before(client, world):
    await live_table(client, world)
    cog = DiceCog(
        cast(HarpiBot, SimpleNamespace(user=SimpleNamespace(id=1234)))
    )

    class Context:
        def __init__(self) -> None:
            self.message = SimpleNamespace(
                id=951,
                guild=SimpleNamespace(id=GUILD),
                channel=SimpleNamespace(id=999),
                author=SimpleNamespace(
                    id=PLAYER,
                    bot=False,
                    display_name="Jogadora",
                    name="Jogadora",
                ),
            )
            self.sent: list[str] = []

        async def reply(self, content: str) -> None:
            self.sent.append(content)

    ctx = Context()
    callback = cast(Any, cog.roll.callback)
    await callback(cog, ctx, args="1d1")

    assert ctx.sent == ["` 1 ` ⟵ [**1**] 1d1"]


async def test_bare_dice_shorthand_rolls_every_group(
    client, world, discord, monkeypatch
):
    table_id = await live_table(client, world)
    fixed_dice(monkeypatch, 3, 11)
    response = await post_roll(client, table_id, "1d6+d20")
    assert response.status_code == 200, await body(response)
    roll = (await body(response))["rolls"][0]
    assert len(roll["dice"]["groups"]) == 2
    assert roll["total"] == 14


async def test_a_message_above_the_discord_limit_is_422(
    client, world, discord, monkeypatch
):
    table_id = await live_table(client, world)
    fixed_dice(monkeypatch, 6)
    response = await post_roll(client, table_id, "10#20d6+20d6")
    assert response.status_code == 422, await body(response)
    assert (await body(response))["error"]["code"] == "result_too_long"
    assert discord.channel.sent == []
    assert await roll_rows(world, table_id) == []


@pytest.mark.usefixtures("panel_loop")
async def test_cog_refuses_a_stranger_in_a_table_channel(client, world):
    table_id = await live_table(client, world)
    cog = DiceCog(
        cast(HarpiBot, SimpleNamespace(user=SimpleNamespace(id=1234)))
    )
    message = RecordingMessage(author_id=STRANGER, label="Visitante")
    await cog.on_message(cast(Any, message))
    assert message.replies == [NO_TABLE_ACCESS]
    assert await roll_rows(world, table_id) == []


async def test_channel_roll_without_a_database_is_ignored(monkeypatch):
    monkeypatch.setattr(rolls, "get_database", lambda: None)
    result = await rolls.channel_roll(
        channel_id=CHANNEL,
        guild_id=str(GUILD),
        author_id=PLAYER,
        author_label="Jogadora",
        message_id="1",
        expression="1d1",
    )
    assert result is None


async def test_channel_roll_in_a_foreign_guild_is_ignored(client, world):
    await live_table(client, world)
    result = await rolls.channel_roll(
        channel_id=CHANNEL,
        guild_id="999",
        author_id=NARRATOR,
        author_label="Narrador",
        message_id="1",
        expression="1d1",
    )
    assert result is None


async def test_channel_roll_refuses_an_oversized_message(
    client, world, monkeypatch
):
    table_id = await live_table(client, world)
    fixed_dice(monkeypatch, 6)
    result = await rolls.channel_roll(
        channel_id=CHANNEL,
        guild_id=str(GUILD),
        author_id=NARRATOR,
        author_label="Narrador",
        message_id="1",
        expression="10#20d6+20d6",
    )
    assert result is not None
    assert result.text is not None
    assert "2000" in result.text
    assert await roll_rows(world, table_id) == []
