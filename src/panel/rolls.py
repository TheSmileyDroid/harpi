from __future__ import annotations

import re
import secrets
import time
from dataclasses import dataclass

from aiosqlite import Connection, Row

from src.bot_state import get_bot, run_on_bot_loop
from src.harpi_lib.math.parser import DiceParser, RollResult
from src.panel import table_stream, tables
from src.panel.schemas import (
    RollSource,
    TableRoll,
    TableRollDice,
    TableRollDiceGroup,
)
from src.storage import get_database
from src.storage.database import Database

EXPRESSION_LIMIT = 120
GROUP_LIMIT = 20
REPEAT_LIMIT = 10
MESSAGE_LIMIT = 2000
INTEGER_MAX = 2**63 - 1

_REPEAT = re.compile(r"(\d+)#(.+)$")
_BARE_DICE = re.compile(r"\bd(\d+|[fF])")
_ULID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_RANDOM_BITS = 80


class RollInvalid(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class BadCursor(RollInvalid):
    def __init__(self) -> None:
        super().__init__("bad_cursor", "Unknown roll cursor")


class DiscordUnavailable(Exception):
    pass


@dataclass(frozen=True, slots=True)
class DiceGroup:
    notation: str
    values: tuple[int, ...]
    kept: tuple[bool, ...] | None
    total: int


@dataclass(frozen=True, slots=True)
class Evaluation:
    index: int
    of: int
    expression: str
    total: int
    groups: tuple[DiceGroup, ...]
    text: str


@dataclass(frozen=True, slots=True)
class RollPlan:
    expression: str
    evaluations: tuple[Evaluation, ...]

    @property
    def body(self) -> str:
        lines = [evaluation.text for evaluation in self.evaluations]
        if len(lines) > 1:
            lines.append(f"Max: {max(e.total for e in self.evaluations)}")
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class SceneContext:
    id: str | None
    label: str


@dataclass(frozen=True, slots=True)
class ChannelRoll:
    text: str | None
    refused: bool = False


@dataclass(frozen=True, slots=True)
class RollContext:
    actor_id: str | None
    actor_label: str
    source: RollSource
    message_id: str | None
    scene: SceneContext
    turn_id: str | None


class _Ulid:
    def __init__(self) -> None:
        self._millis = -1
        self._random = 0

    def new(self) -> str:
        millis = int(time.time() * 1000)
        if millis <= self._millis:
            millis = self._millis
            self._random += 1
            if self._random >= 1 << _RANDOM_BITS:
                millis += 1
                self._random = 0
                self._millis = millis
        else:
            self._millis = millis
            self._random = secrets.randbits(_RANDOM_BITS)
        return f"rol_{_encode(millis, 10)}{_encode(self._random, 16)}"


def _encode(value: int, size: int) -> str:
    digits: list[str] = []
    for _ in range(size):
        digits.append(_ULID_ALPHABET[value & 31])
        value >>= 5
    return "".join(reversed(digits))


_ULIDS = _Ulid()


def evaluate(expression: str) -> RollPlan:
    text = expression.strip()
    if len(text) > EXPRESSION_LIMIT:
        raise RollInvalid(
            "expression_too_long",
            f"An expression is at most {EXPRESSION_LIMIT} characters",
        )
    parser = DiceParser()
    if not parser.is_valid_dice_string(text):
        raise RollInvalid("no_dice", "The expression needs dice")
    count, raw = _repeat(text)
    normalized = _normalize(raw)
    _check_groups(parser, normalized)
    evaluations = tuple(
        _evaluate_once(parser, normalized, raw, index, count)
        for index in range(1, count + 1)
    )
    return RollPlan(expression=text, evaluations=evaluations)


def _repeat(expression: str) -> tuple[int, str]:
    match = _REPEAT.match(expression)
    if match is None:
        return 1, expression
    count = int(match.group(1))
    if count < 1:
        raise RollInvalid("invalid_expression", "A repeat count is positive")
    if count > REPEAT_LIMIT:
        raise RollInvalid(
            "too_many_repeats",
            f"A repeat is at most {REPEAT_LIMIT} rolls",
        )
    return count, match.group(2)


def _normalize(expression: str) -> str:
    return _BARE_DICE.sub(r"1d\1", expression)


def _check_groups(parser: DiceParser, expression: str) -> None:
    for token in parser.tokenize(expression):
        match = parser.dice_pattern.match(token)
        if match is not None and int(match.group(1)) > GROUP_LIMIT:
            raise RollInvalid(
                "too_many_dice",
                f"A dice group holds at most {GROUP_LIMIT} dice",
            )


def _evaluate_once(
    parser: DiceParser,
    expression: str,
    raw: str,
    index: int,
    of: int,
) -> Evaluation:
    try:
        result = parser.parse(expression)
    except (ValueError, ZeroDivisionError, OverflowError) as failure:
        raise RollInvalid("invalid_expression", str(failure)) from failure
    if not result.rolls:
        raise RollInvalid("no_dice", "The expression needs dice")
    return Evaluation(
        index=index,
        of=of,
        expression=raw,
        total=_whole(result),
        groups=tuple(_group(item) for item in result.rolls),
        text=_format(parser, result, expression),
    )


def _format(parser: DiceParser, result: RollResult, expression: str) -> str:
    try:
        return parser.format_result(result, expression)
    except (ValueError, OverflowError) as failure:
        raise RollInvalid(
            "result_too_large", "The roll result is too large to display"
        ) from failure


def _whole(result: RollResult) -> int:
    value = result.value
    if isinstance(value, float):
        raise RollInvalid(
            "non_integer_result", "A roll result must be an integer"
        )
    total = int(value)
    if not -INTEGER_MAX - 1 <= total <= INTEGER_MAX:
        raise RollInvalid(
            "result_too_large", "The roll result is too large to store"
        )
    return total


def _group(item: tuple[list[int], str, list[bool] | None]) -> DiceGroup:
    values, notation, mask = item
    kept = None if mask is None else tuple(mask)
    selected = (
        values
        if mask is None
        else [value for value, keep in zip(values, mask, strict=False) if keep]
    )
    return DiceGroup(
        notation=notation,
        values=tuple(values),
        kept=kept,
        total=sum(selected),
    )


def dice_wire(evaluation: Evaluation) -> TableRollDice:
    return TableRollDice(
        index=evaluation.index,
        of=evaluation.of,
        expression=evaluation.expression,
        groups=[
            TableRollDiceGroup(
                notation=group.notation,
                values=list(group.values),
                kept=None if group.kept is None else list(group.kept),
                total=group.total,
            )
            for group in evaluation.groups
        ],
    )


def message_text(actor_label: str, scene_label: str, body: str) -> str:
    header = f"**{actor_label.strip() or '?'}**"
    if scene_label:
        header = f"{header} · {scene_label}"
    message = f"{header} — {body}"
    if len(message) > MESSAGE_LIMIT:
        raise RollInvalid(
            "result_too_long",
            f"A roll message is at most {MESSAGE_LIMIT} characters",
        )
    return message


async def scene_context(
    database: Database, table: tables.TableRow
) -> SceneContext:
    if table.current_scene_id is None:
        return SceneContext(id=None, label="")
    row = await database.fetchone(
        "SELECT name FROM scenes WHERE id = ? AND campaign_slug = ?",
        (table.current_scene_id, table.campaign),
    )
    if row is None:
        return SceneContext(id=None, label="")
    return SceneContext(id=table.current_scene_id, label=str(row["name"]))


async def turn_for(
    database: Database, table: tables.TableRow, actor_id: str | None
) -> str | None:
    if actor_id is None or table.current_scene_id is None:
        return None
    row = await database.fetchone(
        "SELECT turns.id FROM turns "
        "JOIN tokens ON tokens.id = turns.token_id "
        "WHERE turns.table_id = ? AND turns.ended_at IS NULL "
        "AND turns.scene_id = ? AND tokens.owner_id = ?",
        (table.id, table.current_scene_id, actor_id),
    )
    return None if row is None else str(row["id"])


async def record(
    database: Database,
    table: tables.TableRow,
    *,
    plan: RollPlan,
    context: RollContext,
) -> list[TableRoll]:
    async with database.transaction() as connection:
        if context.message_id is not None and await _message_seen(
            connection, context.message_id
        ):
            return []
        return await _insert(connection, table, plan=plan, context=context)


async def _message_seen(connection: Connection, message_id: str) -> bool:
    cursor = await connection.execute(
        "SELECT 1 FROM rolls WHERE discord_message_id = ? LIMIT 1",
        (message_id,),
    )
    return await cursor.fetchone() is not None


async def _insert(
    connection: Connection,
    table: tables.TableRow,
    *,
    plan: RollPlan,
    context: RollContext,
) -> list[TableRoll]:
    now = int(time.time())
    rows: list[TableRoll] = []
    for evaluation in plan.evaluations:
        roll = _evaluation_to_wire(
            roll_id=_ULIDS.new(),
            table=table,
            plan=plan,
            evaluation=evaluation,
            context=context,
            message_id=context.message_id if evaluation.index == 1 else None,
            created_at=now,
        )
        await connection.execute(
            "INSERT INTO rolls ("
            "id, table_id, scene_id, scene_label, turn_id, actor_id, "
            "actor_label, source, expression, total, dice_json, text, "
            "discord_message_id, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                roll.id,
                roll.table_id,
                roll.scene_id,
                roll.scene_label,
                roll.turn_id,
                roll.actor_id,
                roll.actor_label,
                roll.source,
                roll.expression,
                roll.total,
                roll.dice.model_dump_json(),
                roll.text,
                roll.discord_message_id,
                roll.created_at,
            ),
        )
        rows.append(roll)
    return rows


def _evaluation_to_wire(
    *,
    roll_id: str,
    table: tables.TableRow,
    plan: RollPlan,
    evaluation: Evaluation,
    context: RollContext,
    message_id: str | None,
    created_at: int,
) -> TableRoll:
    return TableRoll(
        id=roll_id,
        table_id=table.id,
        scene_id=context.scene.id,
        scene_label=context.scene.label,
        turn_id=context.turn_id,
        actor_id=context.actor_id,
        actor_label=context.actor_label,
        source=context.source,
        expression=plan.expression,
        total=evaluation.total,
        dice=dice_wire(evaluation),
        text=evaluation.text,
        discord_message_id=message_id,
        created_at=created_at,
    )


def _row_to_wire(row: Row) -> TableRoll:
    return TableRoll(
        id=row["id"],
        table_id=row["table_id"],
        scene_id=row["scene_id"],
        scene_label=row["scene_label"],
        turn_id=row["turn_id"],
        actor_id=row["actor_id"],
        actor_label=row["actor_label"],
        source=row["source"],
        expression=row["expression"],
        total=row["total"],
        dice=TableRollDice.model_validate_json(row["dice_json"]),
        text=row["text"],
        discord_message_id=row["discord_message_id"],
        created_at=row["created_at"],
    )


async def list_rolls(
    database: Database,
    table_id: str,
    *,
    after: str | None,
    limit: int,
) -> list[TableRoll]:
    if after is None:
        rows = await database.fetchall(
            "SELECT * FROM rolls WHERE table_id = ? "
            "ORDER BY created_at, id LIMIT ?",
            (table_id, limit),
        )
        return [_row_to_wire(row) for row in rows]
    cursor = await database.fetchone(
        "SELECT created_at, id FROM rolls WHERE table_id = ? AND id = ?",
        (table_id, after),
    )
    if cursor is None:
        raise BadCursor
    rows = await database.fetchall(
        "SELECT * FROM rolls WHERE table_id = ? AND "
        "(created_at > ? OR (created_at = ? AND id > ?)) "
        "ORDER BY created_at, id LIMIT ?",
        (table_id, cursor["created_at"], cursor["created_at"], after, limit),
    )
    return [_row_to_wire(row) for row in rows]


async def open_table_for_channel(
    database: Database, channel_id: str
) -> tables.TableRow | None:
    row = await database.fetchone(
        "SELECT id FROM tables WHERE channel_id = ? AND status = 'open'",
        (channel_id,),
    )
    if row is None:
        return None
    return await tables.table_row(database, str(row["id"]))


async def _channel_actor(
    database: Database, table: tables.TableRow, author_id: str
) -> str | None:
    if table.narrator_id == author_id:
        return author_id
    player = await database.fetchone(
        "SELECT 1 FROM members m WHERE m.campaign_slug = ? AND m.user_id = ? "
        "AND EXISTS (SELECT 1 FROM sheet_files s "
        "WHERE s.campaign = m.campaign_slug AND s.owner_id = m.user_id "
        "AND s.status = 'ativo')",
        (table.campaign, author_id),
    )
    return author_id if player is not None else None


async def channel_roll(
    *,
    channel_id: str,
    guild_id: str,
    author_id: str,
    author_label: str,
    message_id: str,
    expression: str,
) -> ChannelRoll | None:
    opened = await _open_channel_table(channel_id, guild_id)
    if opened is None:
        return None
    database, table = opened
    plan = _plan(expression)
    if plan is None:
        return None
    return await _record_channel_roll(
        database,
        table,
        plan,
        author_id=str(author_id),
        author_label=author_label,
        message_id=str(message_id),
    )


async def _open_channel_table(
    channel_id: str, guild_id: str
) -> tuple[Database, tables.TableRow] | None:
    database = get_database()
    if database is None:
        return None
    table = await open_table_for_channel(database, str(channel_id))
    if table is None or table.guild_id != str(guild_id):
        return None
    return database, table


def _plan(expression: str) -> RollPlan | None:
    try:
        return evaluate(expression)
    except RollInvalid:
        return None


async def _record_channel_roll(
    database: Database,
    table: tables.TableRow,
    plan: RollPlan,
    *,
    author_id: str,
    author_label: str,
    message_id: str,
) -> ChannelRoll:
    actor_id = await _channel_actor(database, table, author_id)
    if actor_id is None:
        return ChannelRoll(text=None, refused=True)
    scene = await scene_context(database, table)
    text = _channel_text(author_label, scene.label, plan.body)
    if isinstance(text, ChannelRoll):
        return text
    rows = await record(
        database,
        table,
        plan=plan,
        context=RollContext(
            actor_id=actor_id,
            actor_label=author_label,
            source="discord",
            message_id=message_id,
            scene=scene,
            turn_id=await turn_for(database, table, actor_id),
        ),
    )
    if not rows:
        return ChannelRoll(text=None)
    for row in rows:
        table_stream.publish_roll(table.id, row)
    return ChannelRoll(text=text)


def _channel_text(
    actor_label: str, scene_label: str, body: str
) -> str | ChannelRoll:
    try:
        return message_text(actor_label, scene_label, body)
    except RollInvalid as failure:
        return ChannelRoll(text=failure.message)


async def post_message(channel_id: str, content: str) -> str:
    bot = get_bot()
    return await run_on_bot_loop(_send(bot, int(channel_id), content))


async def _send(bot, channel_id: int, content: str) -> str:
    channel = bot.get_channel(channel_id)
    if channel is None:
        channel = await bot.fetch_channel(channel_id)
    if channel is None:
        raise DiscordUnavailable(f"channel {channel_id} is unavailable")
    message = await channel.send(content)
    return str(message.id)
