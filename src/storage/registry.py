from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, Protocol

from src.storage.database import Database

PRESENCE_TTL_SECONDS = 15
VIEWER_LIMIT = 50

ConnectionAction = Literal["connect", "disconnect"]


@dataclass(frozen=True)
class Actor:
    id: str
    username: str
    display_name: str | None = None


@dataclass(frozen=True)
class Place:
    guild_id: str
    guild_name: str
    channel_id: str | None = None
    channel_name: str | None = None


@dataclass(frozen=True)
class ViewerRecord:
    user_id: str
    username: str
    display_name: str | None
    channel_id: str | None
    channel_name: str | None
    seen_at: int


@dataclass(frozen=True)
class ConnectionRecord:
    action: ConnectionAction
    channel_id: str | None
    channel_name: str | None
    actor_id: str | None
    actor_name: str | None
    at: int


class Registry(Protocol):
    async def sign_in(self, actor: Actor) -> None: ...

    async def select(
        self, actor: Actor, place: Place, *, now: int | None = None
    ) -> None: ...

    async def touch(
        self, actor: Actor, place: Place, *, now: int | None = None
    ) -> None: ...

    async def viewers(
        self, guild_id: str, *, now: int | None = None
    ) -> list[ViewerRecord]: ...

    async def last_connection(
        self, guild_id: str
    ) -> ConnectionRecord | None: ...

    async def record_connection(
        self,
        actor: Actor | None,
        place: Place,
        action: ConnectionAction,
        *,
        now: int | None = None,
    ) -> None: ...

    async def leave(self, user_id: str) -> None: ...

    async def record_user_guilds(
        self,
        actor: Actor,
        guild_ids: Iterable[str],
        *,
        now: int | None = None,
    ) -> None: ...

    async def user_guild_ids(self, user_id: str) -> frozenset[str]: ...

    async def login_epoch(self, user_id: str) -> int | None: ...

    async def increment_login_epoch(self, user_id: str) -> int | None: ...


class SqliteRegistry:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def sign_in(self, actor: Actor) -> None:
        await self._upsert_user(actor, now=_clock(None))

    async def select(
        self, actor: Actor, place: Place, *, now: int | None = None
    ) -> None:
        stamp = _clock(now)
        await self._upsert_user(actor, now=stamp)
        await self._upsert_place(place, now=stamp)
        await self._database.execute(
            "INSERT INTO viewers "
            "(user_id, guild_id, channel_id, last_seen_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "guild_id = excluded.guild_id, "
            "channel_id = excluded.channel_id, "
            "last_seen_at = excluded.last_seen_at",
            (actor.id, place.guild_id, place.channel_id, stamp),
        )

    async def touch(
        self, actor: Actor, place: Place, *, now: int | None = None
    ) -> None:
        stamp = _clock(now)
        await self._upsert_user(actor, now=stamp)
        await self._upsert_place(place, now=stamp)
        await self._database.execute(
            "INSERT INTO viewers "
            "(user_id, guild_id, channel_id, last_seen_at) "
            "VALUES (?, ?, NULL, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "guild_id = excluded.guild_id, "
            "last_seen_at = excluded.last_seen_at",
            (actor.id, place.guild_id, stamp),
        )

    async def viewers(
        self, guild_id: str, *, now: int | None = None
    ) -> list[ViewerRecord]:
        freshness = _clock(now) - PRESENCE_TTL_SECONDS
        rows = await self._database.fetchall(
            "SELECT v.user_id, u.username, u.display_name, "
            "v.channel_id, c.name AS channel_name, v.last_seen_at "
            "FROM viewers v "
            "JOIN users u ON u.id = v.user_id "
            "LEFT JOIN channels c ON c.id = v.channel_id "
            "WHERE v.guild_id = ? AND v.last_seen_at >= ? "
            "ORDER BY v.last_seen_at DESC, u.username ASC "
            "LIMIT ?",
            (guild_id, freshness, VIEWER_LIMIT),
        )
        return [
            ViewerRecord(
                user_id=row["user_id"],
                username=row["username"],
                display_name=row["display_name"],
                channel_id=row["channel_id"],
                channel_name=row["channel_name"],
                seen_at=row["last_seen_at"],
            )
            for row in rows
        ]

    async def last_connection(self, guild_id: str) -> ConnectionRecord | None:
        row = await self._database.fetchone(
            "SELECT e.action, e.channel_id, c.name AS channel_name, "
            "e.actor_user_id, "
            "COALESCE(u.display_name, u.username) AS actor_name, "
            "e.created_at "
            "FROM connection_events e "
            "LEFT JOIN channels c ON c.id = e.channel_id "
            "LEFT JOIN users u ON u.id = e.actor_user_id "
            "WHERE e.guild_id = ? "
            "ORDER BY e.id DESC LIMIT 1",
            (guild_id,),
        )
        if row is None:
            return None
        return ConnectionRecord(
            action=row["action"],
            channel_id=row["channel_id"],
            channel_name=row["channel_name"],
            actor_id=row["actor_user_id"],
            actor_name=row["actor_name"],
            at=row["created_at"],
        )

    async def record_connection(
        self,
        actor: Actor | None,
        place: Place,
        action: ConnectionAction,
        *,
        now: int | None = None,
    ) -> None:
        stamp = _clock(now)
        if actor is not None:
            await self._upsert_user(actor, now=stamp)
        await self._upsert_place(place, now=stamp)
        await self._database.execute(
            "INSERT INTO connection_events "
            "(guild_id, channel_id, actor_user_id, action, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                place.guild_id,
                place.channel_id,
                actor.id if actor is not None else None,
                action,
                stamp,
            ),
        )

    async def leave(self, user_id: str) -> None:
        await self._database.execute(
            "DELETE FROM viewers WHERE user_id = ?", (user_id,)
        )

    async def record_user_guilds(
        self,
        actor: Actor,
        guild_ids: Iterable[str],
        *,
        now: int | None = None,
    ) -> None:
        stamp = _clock(now)
        await self._upsert_user(actor, now=stamp)
        await self._database.execute(
            "DELETE FROM user_guilds WHERE user_id = ?", (actor.id,)
        )
        for guild_id in guild_ids:
            await self._database.execute(
                "INSERT INTO user_guilds (user_id, guild_id, seen_at) "
                "VALUES (?, ?, ?)",
                (actor.id, guild_id, stamp),
            )

    async def user_guild_ids(self, user_id: str) -> frozenset[str]:
        rows = await self._database.fetchall(
            "SELECT guild_id FROM user_guilds WHERE user_id = ?", (user_id,)
        )
        return frozenset(row["guild_id"] for row in rows)

    async def login_epoch(self, user_id: str) -> int | None:
        row = await self._database.fetchone(
            "SELECT login_epoch FROM users WHERE id = ?", (user_id,)
        )
        return None if row is None else int(row["login_epoch"])

    async def increment_login_epoch(self, user_id: str) -> int | None:
        await self._database.execute(
            "UPDATE users SET login_epoch = login_epoch + 1 WHERE id = ?",
            (user_id,),
        )
        return await self.login_epoch(user_id)

    async def _upsert_user(self, actor: Actor, *, now: int) -> None:
        await self._database.execute(
            "INSERT INTO users "
            "(id, username, display_name, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET "
            "username = excluded.username, "
            "display_name = excluded.display_name, "
            "updated_at = excluded.updated_at",
            (
                actor.id,
                actor.username,
                actor.display_name,
                now,
                now,
            ),
        )

    async def _upsert_place(self, place: Place, *, now: int) -> None:
        await self._database.execute(
            "INSERT INTO guilds (id, name, created_at, updated_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET "
            "name = excluded.name, "
            "updated_at = excluded.updated_at",
            (place.guild_id, place.guild_name, now, now),
        )
        if place.channel_id is None:
            return
        await self._database.execute(
            "INSERT INTO channels "
            "(id, guild_id, name, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET "
            "guild_id = excluded.guild_id, "
            "name = excluded.name, "
            "updated_at = excluded.updated_at",
            (
                place.channel_id,
                place.guild_id,
                place.channel_name or "",
                now,
                now,
            ),
        )


def _clock(now: int | None) -> int:
    return int(time.time()) if now is None else now
