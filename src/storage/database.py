from __future__ import annotations

import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import aiosqlite
from loguru import logger

MIGRATIONS = Path(__file__).with_name("migrations")


class Database:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._connection: aiosqlite.Connection | None = None

    @property
    def path(self) -> Path:
        return self._path

    async def open(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = await aiosqlite.connect(self._path)
        connection.row_factory = aiosqlite.Row
        await connection.execute("PRAGMA journal_mode=WAL")
        await connection.execute("PRAGMA foreign_keys=ON")
        await connection.execute("PRAGMA busy_timeout=5000")
        self._connection = connection
        await self._migrate()

    async def close(self) -> None:
        connection = self._connection
        self._connection = None
        if connection is not None:
            await connection.close()

    async def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        connection = self._require()
        await connection.execute(sql, params)
        await connection.commit()

    async def fetchall(
        self, sql: str, params: Sequence[Any] = ()
    ) -> list[aiosqlite.Row]:
        cursor = await self._require().execute(sql, params)
        return list(await cursor.fetchall())

    async def fetchone(
        self, sql: str, params: Sequence[Any] = ()
    ) -> aiosqlite.Row | None:
        cursor = await self._require().execute(sql, params)
        return await cursor.fetchone()

    async def _migrate(self) -> None:
        connection = self._require()
        await connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version INTEGER PRIMARY KEY, "
            "applied_at INTEGER NOT NULL)"
        )
        cursor = await connection.execute(
            "SELECT version FROM schema_migrations"
        )
        applied = {row["version"] for row in await cursor.fetchall()}
        for path in sorted(MIGRATIONS.glob("*.sql")):
            version = int(path.name.split("_", 1)[0])
            if version in applied:
                continue
            await connection.executescript(path.read_text())
            await connection.execute(
                "INSERT INTO schema_migrations (version, applied_at) "
                "VALUES (?, ?)",
                (version, int(time.time())),
            )
            await connection.commit()
            logger.info(f"Applied storage migration {path.name}")

    def _require(self) -> aiosqlite.Connection:
        if self._connection is None:
            raise RuntimeError("Database is not open")
        return self._connection
