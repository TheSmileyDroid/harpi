"""Back up the panel registry and verify a restore by hand.

    .venv/bin/python -m tools.backup_db backup
    .venv/bin/python -m tools.backup_db verify

``verify`` restores the newest backup into a temporary database and compares
the row counts with the live registry. Exit code is 1 on a mismatch.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from src.config import Settings
from src.panel import backup


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Back up the Harpi registry")
    parser.add_argument("command", choices=("backup", "verify"))
    parser.add_argument(
        "backup_file",
        nargs="?",
        help="backup file for verify (default: the newest one)",
    )
    parser.add_argument("--database", default=None)
    parser.add_argument("--directory", default=None)
    parser.add_argument("--keep", type=int, default=backup.BACKUPS_KEPT)
    return parser.parse_args(argv)


def _directory(settings: Settings, args: argparse.Namespace) -> Path:
    if args.directory:
        return Path(args.directory)
    return backup.backup_directory(settings)


def _print_counts(label: str, counts: dict[str, int]) -> None:
    detail = " ".join(f"{table}={count}" for table, count in counts.items())
    print(f"{label} {detail}")


def run_backup(settings: Settings, args: argparse.Namespace) -> int:
    source = args.database or settings.db_path
    try:
        target = backup.backup_database(
            source, _directory(settings, args), keep=args.keep
        )
    except (OSError, sqlite3.Error) as error:
        print(f"backup failed: {error}", file=sys.stderr)
        return 1
    print(f"backup written to {target}")
    _print_counts("rows", backup.table_counts(target))
    return 0


def _verify_target(
    settings: Settings, args: argparse.Namespace
) -> Path | None:
    if args.backup_file:
        return Path(args.backup_file)
    return backup.latest_backup(_directory(settings, args))


def _live_counts(source: str) -> dict[str, int] | None:
    if not Path(source).exists():
        return None
    return backup.table_counts(source)


def run_verify(settings: Settings, args: argparse.Namespace) -> int:
    target = _verify_target(settings, args)
    if target is None or not target.exists():
        print("no backup found", file=sys.stderr)
        return 1
    source = args.database or settings.db_path
    expected = _live_counts(source)
    try:
        check = backup.restore_check(target, expected=expected)
    except (OSError, sqlite3.Error) as error:
        print(f"restore failed: {error}", file=sys.stderr)
        return 1
    _print_counts("backup", check.expected)
    _print_counts("restored", check.restored)
    if not check.matches:
        print("restore check failed: row counts differ", file=sys.stderr)
        return 1
    print(f"restore check passed for {target}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = Settings.from_env()
    if args.command == "backup":
        return run_backup(settings, args)
    return run_verify(settings, args)


if __name__ == "__main__":
    raise SystemExit(main())
