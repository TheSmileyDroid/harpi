from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel

from src.panel import tables
from src.panel.schemas import (
    TABLE_SSE_EVENTS,
    Heartbeat,
    TableClosedEvent,
    TableDragMarker,
    TableParticipant,
    TableRoll,
    TableRole,
    TableScene,
    TableSheetChanged,
    TableStatus,
    TableStreamDelta,
    TableStreamSnapshot,
    TableStreamViewers,
    TableToken,
    TableTurn,
    TablePresenceEntry,
)
from src.storage.database import Database

TICK_SECONDS = 5.0
WINDOW_SIZE = 512
QUEUE_SIZE = 32
STREAMS_PER_TABLE = 16
STREAMS_PER_USER = 2
RETRY_AFTER_SECONDS = 30
DRAG_SECONDS = 3.0
CLOSED_REASON = "A mesa foi fechada."


@dataclass(frozen=True, slots=True)
class StateSignal:
    pass


@dataclass(frozen=True, slots=True)
class SnapshotSignal:
    pass


@dataclass(frozen=True, slots=True)
class Overflow:
    pass


Signal = (
    StateSignal
    | SnapshotSignal
    | Overflow
    | TableStreamViewers
    | TableDragMarker
    | TableSheetChanged
    | TableRoll
    | TableClosedEvent
)

_FRAME_NAMES = {model: name for name, model in TABLE_SSE_EVENTS.items()}


@dataclass(frozen=True, slots=True)
class RoleChange:
    tokens: tuple[TableToken, ...]
    removed: tuple[str, ...]
    scene: TableScene | None
    turn: TableTurn | None
    participants: tuple[TableParticipant, ...]


@dataclass(frozen=True, slots=True)
class Change:
    stream_rev: int
    scene_id: str | None
    round: int
    status: TableStatus
    spectators: bool
    narrator: RoleChange
    player: RoleChange
    changed: bool


@dataclass(frozen=True, slots=True)
class MergedDelta:
    tokens: list[TableToken]
    removed: list[str]
    scene: TableScene | None
    turn: TableTurn | None
    round: int
    status: TableStatus
    spectators: bool
    participants: list[TableParticipant]


@dataclass(eq=False, slots=True)
class Subscriber:
    user_id: str
    role: TableRole
    name: str
    stream_rev: int
    boundary_rev: int
    state_queued: bool = False
    drag_queued: bool = False
    queue: asyncio.Queue[Signal] = field(
        default_factory=lambda: asyncio.Queue(maxsize=QUEUE_SIZE)
    )


def _tokens_of(
    state: tables.StreamState, narrator: bool
) -> list[tables.TokenRow]:
    return state.tokens if narrator else state.public


def _changed_tokens(
    previous: tables.StreamState | None,
    state: tables.StreamState,
    narrator: bool,
) -> tuple[TableToken, ...]:
    before = (
        {}
        if previous is None
        else {token.id: token for token in _tokens_of(previous, narrator)}
    )
    return tuple(
        tables.wire_token(token)
        for token in _tokens_of(state, narrator)
        if before.get(token.id) != token
    )


def _removed_tokens(
    previous: tables.StreamState | None,
    state: tables.StreamState,
    narrator: bool,
) -> tuple[str, ...]:
    if previous is None:
        return ()
    before = {token.id for token in _tokens_of(previous, narrator)}
    now = {token.id for token in _tokens_of(state, narrator)}
    return tuple(sorted(before - now))


def _scene_changed(
    previous: tables.StreamState | None, state: tables.StreamState
) -> bool:
    return (
        previous is None
        or previous.record != state.record
        or previous.fog_outside != state.fog_outside
    )


def _same_table(
    previous: tables.StreamState, state: tables.StreamState
) -> bool:
    return (
        previous.turn,
        previous.table.round,
        previous.table.status,
        previous.table.spectators,
        previous.participants,
        previous.record,
        previous.fog_outside,
    ) == (
        state.turn,
        state.table.round,
        state.table.status,
        state.table.spectators,
        state.participants,
        state.record,
        state.fog_outside,
    )


def _different(
    previous: tables.StreamState | None,
    state: tables.StreamState,
    cut: RoleChange,
) -> bool:
    if previous is None:
        return True
    if cut.tokens or cut.removed:
        return True
    return not _same_table(previous, state)


def _role_change(
    previous: tables.StreamState | None,
    state: tables.StreamState,
    narrator: bool,
    public_ids: set[str],
    root: Path | None,
) -> RoleChange:
    scene = (
        tables.scene_view(
            state.table,
            state.record,
            state.zones,
            state.fog_outside,
            narrator,
            root if narrator else None,
        )
        if _scene_changed(previous, state)
        else None
    )
    return RoleChange(
        tokens=_changed_tokens(previous, state, narrator),
        removed=_removed_tokens(previous, state, narrator),
        scene=scene,
        turn=tables.stream_turn(state.turn, narrator, public_ids),
        participants=tuple(state.participants),
    )


def _confirm(
    previous: tables.StreamState | None,
    state: tables.StreamState,
    rev: int,
    root: Path | None,
) -> Change:
    public_ids = {token.id for token in state.public}
    narrator = _role_change(previous, state, True, public_ids, root)
    player = _role_change(previous, state, False, public_ids, root)
    return Change(
        stream_rev=rev,
        scene_id=None if state.record is None else state.record.id,
        round=state.table.round,
        status=state.table.status,
        spectators=state.table.spectators,
        narrator=narrator,
        player=player,
        changed=_different(previous, state, narrator),
    )


def merge_changes(changes: list[Change], narrator: bool) -> MergedDelta:
    tokens: dict[str, TableToken] = {}
    removed: dict[str, None] = {}
    scene: TableScene | None = None
    for change in changes:
        cut = change.narrator if narrator else change.player
        for token in cut.tokens:
            tokens[token.id] = token
            removed.pop(token.id, None)
        for token_id in cut.removed:
            tokens.pop(token_id, None)
            removed[token_id] = None
        if cut.scene is not None:
            scene = cut.scene
    last = changes[-1]
    cut = last.narrator if narrator else last.player
    return MergedDelta(
        tokens=list(tokens.values()),
        removed=list(removed),
        scene=scene,
        turn=cut.turn,
        round=last.round,
        status=last.status,
        spectators=last.spectators,
        participants=list(cut.participants),
    )


class TableBroadcaster:
    def __init__(self, table_id: str, clock=time.monotonic) -> None:
        self.table_id = table_id
        self.stream_rev = 0
        self._clock = clock
        self._window: deque[Change] = deque(maxlen=WINDOW_SIZE)
        self._raw: tables.StreamState | None = None
        self._subscribers: dict[Subscriber, None] = {}
        self._drags: dict[str, TableDragMarker] = {}
        self._drag_seen: dict[str, float] = {}
        self._drag_ids: dict[str, str] = {}
        self._closed = False

    @property
    def empty(self) -> bool:
        return not self._subscribers

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def state(self) -> tables.StreamState | None:
        return self._raw

    async def bind(self, database: Database, table: tables.TableRow) -> None:
        if self._raw is None:
            self._raw = await tables.stream_state(database, table)

    def subscribe(
        self, user_id: str, role: TableRole, name: str
    ) -> Subscriber:
        subscriber = Subscriber(
            user_id=user_id,
            role=role,
            name=name,
            stream_rev=self.stream_rev,
            boundary_rev=self.stream_rev,
        )
        self._subscribers[subscriber] = None
        self._announce(skip=subscriber)
        return subscriber

    def unsubscribe(self, subscriber: Subscriber) -> None:
        if self._subscribers.pop(subscriber, None) is None:
            return
        self._announce()

    def viewers(self) -> list[TablePresenceEntry]:
        shown: dict[str, TablePresenceEntry] = {}
        for subscriber in self._subscribers:
            shown.setdefault(
                subscriber.user_id,
                TablePresenceEntry(name=subscriber.name, role=subscriber.role),
            )
        return list(shown.values())

    def drags(self) -> list[TableDragMarker]:
        now = self._clock()
        expired = [
            token_id
            for token_id, seen in self._drag_seen.items()
            if now - seen >= DRAG_SECONDS
        ]
        for token_id in expired:
            self._drag_seen.pop(token_id, None)
            self._drags.pop(token_id, None)
            self._drag_ids.pop(token_id, None)
        return list(self._drags.values())

    def set_drag(
        self,
        token_id: str,
        actor: str,
        active: bool,
        drag_id: str | None = None,
    ) -> None:
        if not active and not self._drag_ends(token_id, drag_id):
            return
        event = TableDragMarker(token_id=token_id, actor=actor, active=active)
        if active:
            refreshed = self._drag_refreshes(token_id, actor)
            self._remember_drag(token_id, event, drag_id)
            if refreshed:
                return
        else:
            self._forget_drag(token_id)
        self._broadcast(event)

    def _drag_ends(self, token_id: str, drag_id: str | None) -> bool:
        if token_id not in self._drags:
            return False
        return (
            drag_id is None or self._drag_ids.get(token_id, drag_id) == drag_id
        )

    def _drag_refreshes(self, token_id: str, actor: str) -> bool:
        current = self._drags.get(token_id)
        return current is not None and current.actor == actor

    def _remember_drag(
        self, token_id: str, event: TableDragMarker, drag_id: str | None
    ) -> None:
        self._drags[token_id] = event
        self._drag_seen[token_id] = self._clock()
        if drag_id is not None:
            self._drag_ids[token_id] = drag_id

    def _forget_drag(self, token_id: str) -> None:
        self._drags.pop(token_id, None)
        self._drag_seen.pop(token_id, None)
        self._drag_ids.pop(token_id, None)

    def start_drag(
        self, token_ids: list[str], actor: str, drag_id: str
    ) -> None:
        for token_id in token_ids:
            self.set_drag(token_id, actor, True, drag_id)

    def end_drag(self, token_ids: list[str], actor: str, drag_id: str) -> None:
        for token_id in token_ids:
            self.set_drag(token_id, actor, False, drag_id)

    def clear_drags(self) -> None:
        self._drags.clear()
        self._drag_seen.clear()
        self._drag_ids.clear()

    def publish(
        self, state: tables.StreamState, root: Path | None = None
    ) -> int:
        if self._closed:
            return self.stream_rev
        change = _confirm(self._raw, state, self.stream_rev + 1, root)
        self._raw = state
        if not change.changed:
            return self.stream_rev
        self._accept(change)
        self._notify_state()
        return self.stream_rev

    def publish_snapshot(
        self, state: tables.StreamState, root: Path | None = None
    ) -> None:
        self._closed = False
        self.clear_drags()
        change = _confirm(self._raw, state, self.stream_rev + 1, root)
        self._raw = state
        if change.changed:
            self._accept(change)
        self._broadcast(SnapshotSignal())

    def publish_closed(self, reason: str) -> None:
        if self._closed:
            return
        self._closed = True
        self._broadcast(TableClosedEvent(reason=reason))

    def publish_sheet(
        self, event: TableSheetChanged, owner_id: str | None
    ) -> None:
        if self._closed:
            return
        for subscriber in self._subscribers:
            if subscriber.role == "narrator" or subscriber.user_id == owner_id:
                self._enqueue(subscriber, event)

    def publish_roll(self, roll: TableRoll) -> None:
        if self._closed:
            return
        self._broadcast(roll)

    def changes_between(
        self, from_rev: int, to_rev: int
    ) -> list[Change] | None:
        if to_rev > self.stream_rev or from_rev > to_rev or not self._window:
            return None
        if self._window[0].stream_rev > from_rev + 1:
            return None
        return [
            change for change in self._window if change.stream_rev > from_rev
        ]

    def _accept(self, change: Change) -> None:
        self.stream_rev += 1
        self._window.append(change)

    def _notify_state(self) -> None:
        for subscriber in self._subscribers:
            self._enqueue(subscriber, StateSignal())

    def _broadcast(self, item: Signal) -> None:
        for subscriber in self._subscribers:
            self._enqueue(subscriber, item)

    def _announce(self, skip: Subscriber | None = None) -> None:
        payload = TableStreamViewers(viewers=self.viewers())
        for subscriber in self._subscribers:
            if subscriber is not skip:
                self._enqueue(subscriber, payload)

    def _enqueue(self, subscriber: Subscriber, item: Signal) -> None:
        if isinstance(item, StateSignal):
            if subscriber.state_queued:
                return
            subscriber.state_queued = True
        if isinstance(item, TableDragMarker):
            if item.active and subscriber.drag_queued:
                return
            subscriber.drag_queued = item.active
        try:
            subscriber.queue.put_nowait(item)
        except asyncio.QueueFull:
            self._overflow(subscriber)

    @staticmethod
    def _overflow(subscriber: Subscriber) -> None:
        while not subscriber.queue.empty():
            subscriber.queue.get_nowait()
        subscriber.queue.put_nowait(Overflow())


_BROADCASTERS: dict[str, TableBroadcaster] = {}


def broadcaster_for(table_id: str) -> TableBroadcaster | None:
    return _BROADCASTERS.get(table_id)


def _broadcaster(table_id: str, *, fresh: bool = False) -> TableBroadcaster:
    broadcaster = None if fresh else _BROADCASTERS.get(table_id)
    if broadcaster is None:
        broadcaster = TableBroadcaster(table_id)
        _BROADCASTERS[table_id] = broadcaster
    return broadcaster


async def subscribe(
    database: Database,
    table: tables.TableRow,
    *,
    user_id: str,
    role: TableRole,
    name: str,
) -> tuple[TableBroadcaster, Subscriber]:
    current = _BROADCASTERS.get(table.id)
    broadcaster = _broadcaster(
        table.id, fresh=current is not None and current.closed
    )
    await broadcaster.bind(database, table)
    return broadcaster, broadcaster.subscribe(user_id, role, name)


def unsubscribe(broadcaster: TableBroadcaster, subscriber: Subscriber) -> None:
    broadcaster.unsubscribe(subscriber)
    if (
        broadcaster.empty
        and _BROADCASTERS.get(broadcaster.table_id) is broadcaster
    ):
        del _BROADCASTERS[broadcaster.table_id]


async def _load(
    database: Database, table_id: str
) -> tables.StreamState | None:
    table = await tables.table_row(database, table_id)
    return (
        None if table is None else await tables.stream_state(database, table)
    )


async def publish(
    database: Database, table_id: str, *, root: Path | None = None
) -> int:
    broadcaster = _BROADCASTERS.get(table_id)
    if broadcaster is None:
        return 0
    state = await _load(database, table_id)
    if state is None:
        return broadcaster.stream_rev
    return broadcaster.publish(state, root)


def start_drag(
    table_id: str, token_ids: list[str], actor: str, drag_id: str
) -> None:
    broadcaster = _BROADCASTERS.get(table_id)
    if broadcaster is not None:
        broadcaster.start_drag(token_ids, actor, drag_id)


def end_drag(
    table_id: str, token_ids: list[str], actor: str, drag_id: str
) -> None:
    broadcaster = _BROADCASTERS.get(table_id)
    if broadcaster is not None:
        broadcaster.end_drag(token_ids, actor, drag_id)


async def publish_snapshot(
    database: Database, table_id: str, *, root: Path | None = None
) -> None:
    broadcaster = _BROADCASTERS.get(table_id)
    if broadcaster is None:
        return
    state = await _load(database, table_id)
    if state is not None:
        broadcaster.publish_snapshot(state, root)


def publish_closed(table_id: str, reason: str = CLOSED_REASON) -> None:
    broadcaster = _BROADCASTERS.get(table_id)
    if broadcaster is not None:
        broadcaster.publish_closed(reason)


async def publish_sheet(
    database: Database,
    campaign: str,
    event: TableSheetChanged,
    owner_id: str | None,
) -> None:
    for table_id in await tables.open_table_ids(database, campaign):
        broadcaster = _BROADCASTERS.get(table_id)
        if broadcaster is not None:
            broadcaster.publish_sheet(event, owner_id)


def publish_roll(table_id: str, roll: TableRoll) -> None:
    broadcaster = _BROADCASTERS.get(table_id)
    if broadcaster is not None:
        broadcaster.publish_roll(roll)


class TableStreamSlot:
    def __init__(
        self, slots: TableStreamSlots, user_id: str, table_id: str
    ) -> None:
        self._slots = slots
        self._user_id = user_id
        self._table_id = table_id
        self._released = False

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        self._slots._release(self._user_id, self._table_id)


class TableStreamSlots:
    def __init__(
        self,
        per_table: int = STREAMS_PER_TABLE,
        per_user: int = STREAMS_PER_USER,
    ) -> None:
        self._per_table = per_table
        self._per_user = per_user
        self._users: dict[str, int] = {}
        self._tables: dict[str, int] = {}

    def acquire(self, user_id: str, table_id: str) -> TableStreamSlot | None:
        if self._users.get(user_id, 0) >= self._per_user:
            return None
        if self._tables.get(table_id, 0) >= self._per_table:
            return None
        self._users[user_id] = self._users.get(user_id, 0) + 1
        self._tables[table_id] = self._tables.get(table_id, 0) + 1
        return TableStreamSlot(self, user_id, table_id)

    def _release(self, user_id: str, table_id: str) -> None:
        self._users[user_id] -= 1
        if self._users[user_id] <= 0:
            del self._users[user_id]
        self._tables[table_id] -= 1
        if self._tables[table_id] <= 0:
            del self._tables[table_id]


TABLE_STREAM_SLOTS = TableStreamSlots()


def _frame(name: str, payload: BaseModel) -> str:
    return f"event: {name}\ndata: {json.dumps(payload.model_dump())}\n\n"


def closed_frame(reason: str = CLOSED_REASON) -> str:
    return _frame("table.closed", TableClosedEvent(reason=reason))


async def _snapshot(
    broadcaster: TableBroadcaster,
    subscriber: Subscriber,
    database: Database,
    root: Path | None,
) -> str:
    captured = broadcaster.stream_rev
    table = await tables.table_row(database, broadcaster.table_id)
    if table is None:
        return _frame("table.closed", TableClosedEvent(reason=CLOSED_REASON))
    state = await tables.summary(
        database,
        table,
        viewer_id=subscriber.user_id,
        role=subscriber.role,
        root=root,
    )
    subscriber.stream_rev = captured
    subscriber.boundary_rev = captured
    drags = broadcaster.drags()
    if subscriber.role != "narrator":
        visible = {token.id for token in state.tokens}
        drags = [drag for drag in drags if drag.token_id in visible]
    return _frame(
        "table.snapshot",
        TableStreamSnapshot(
            stream_rev=captured,
            table_id=broadcaster.table_id,
            state=state,
            viewers=broadcaster.viewers(),
            drags=drags,
        ),
    )


async def _state_frame(
    broadcaster: TableBroadcaster,
    subscriber: Subscriber,
    database: Database,
    root: Path | None,
) -> str | None:
    if subscriber.stream_rev >= broadcaster.stream_rev:
        return None
    changes = broadcaster.changes_between(
        subscriber.stream_rev, broadcaster.stream_rev
    )
    if changes is None:
        return await _snapshot(broadcaster, subscriber, database, root)
    merged = merge_changes(changes, subscriber.role == "narrator")
    payload = TableStreamDelta(
        from_stream_rev=subscriber.stream_rev,
        stream_rev=broadcaster.stream_rev,
        scene_id=changes[-1].scene_id,
        tokens=merged.tokens,
        removed=merged.removed,
        turn=merged.turn,
        round=merged.round,
        status=merged.status,
        spectators=merged.spectators,
        participants=merged.participants,
        scene=merged.scene,
    )
    subscriber.stream_rev = broadcaster.stream_rev
    return _frame("table.delta", payload)


async def _deliver(
    broadcaster: TableBroadcaster,
    subscriber: Subscriber,
    database: Database,
    root: Path | None,
    item: Signal,
) -> str | None:
    if isinstance(item, Overflow):
        return None
    if isinstance(item, StateSignal):
        subscriber.state_queued = False
        return await _state_frame(broadcaster, subscriber, database, root)
    if isinstance(item, SnapshotSignal):
        return await _snapshot(broadcaster, subscriber, database, root)
    if isinstance(item, TableClosedEvent):
        if not broadcaster.closed:
            return None
        return _frame("table.closed", item)
    if isinstance(item, TableDragMarker):
        return _drag_frame(broadcaster, subscriber, item)
    return _frame(_FRAME_NAMES[type(item)], item)


def _drag_frame(
    broadcaster: TableBroadcaster,
    subscriber: Subscriber,
    item: TableDragMarker,
) -> str | None:
    subscriber.drag_queued = False
    if not _drag_visible(broadcaster, subscriber, item):
        return None
    return _frame("table.drag", item)


def _drag_visible(
    broadcaster: TableBroadcaster,
    subscriber: Subscriber,
    item: TableDragMarker,
) -> bool:
    if subscriber.role == "narrator":
        return True
    state = broadcaster.state
    return state is not None and any(
        token.id == item.token_id for token in state.public
    )


async def _periodic(
    broadcaster: TableBroadcaster,
    subscriber: Subscriber,
    database: Database,
    root: Path | None,
) -> str:
    if broadcaster.stream_rev != subscriber.boundary_rev:
        return await _snapshot(broadcaster, subscriber, database, root)
    return _frame("heartbeat", Heartbeat())


async def _next_signal(
    subscriber: Subscriber, deadline: float
) -> tuple[Signal | None, float]:
    try:
        return subscriber.queue.get_nowait(), deadline
    except asyncio.QueueEmpty:
        pass
    now = time.monotonic()
    if now >= deadline:
        return None, now + TICK_SECONDS
    try:
        queued = await asyncio.wait_for(subscriber.queue.get(), deadline - now)
    except TimeoutError:
        return None, deadline
    return queued, deadline


def _ends_stream(item: Signal, broadcaster: TableBroadcaster) -> bool:
    return isinstance(item, TableClosedEvent) and broadcaster.closed


async def _due_periodic(
    broadcaster: TableBroadcaster,
    subscriber: Subscriber,
    database: Database,
    root: Path | None,
    deadline: float,
) -> tuple[str | None, float]:
    if time.monotonic() < deadline:
        return None, deadline
    frame = await _periodic(broadcaster, subscriber, database, root)
    return frame, time.monotonic() + TICK_SECONDS


async def _frames(
    broadcaster: TableBroadcaster,
    subscriber: Subscriber,
    database: Database,
    root: Path | None,
) -> AsyncGenerator[str, None]:
    deadline = time.monotonic() + TICK_SECONDS
    while True:
        queued, deadline = await _next_signal(subscriber, deadline)
        if queued is None:
            yield await _periodic(broadcaster, subscriber, database, root)
            continue
        if isinstance(queued, Overflow):
            return
        frame = await _deliver(broadcaster, subscriber, database, root, queued)
        if frame is not None:
            yield frame
        if _ends_stream(queued, broadcaster):
            return
        periodic, deadline = await _due_periodic(
            broadcaster, subscriber, database, root, deadline
        )
        if periodic is not None:
            yield periodic


async def open_stream(
    database: Database,
    table: tables.TableRow,
    *,
    user_id: str,
    role: TableRole,
    name: str,
    root: Path | None,
) -> AsyncGenerator[str, None]:
    broadcaster, subscriber = await subscribe(
        database, table, user_id=user_id, role=role, name=name
    )
    try:
        yield ": connected\n\n"
        yield await _snapshot(broadcaster, subscriber, database, root)
        async for frame in _frames(broadcaster, subscriber, database, root):
            yield frame
    finally:
        unsubscribe(broadcaster, subscriber)
