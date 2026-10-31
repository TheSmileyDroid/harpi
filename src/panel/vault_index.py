from __future__ import annotations

import asyncio
import os
from contextlib import suppress
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath

from loguru import logger

from src.panel import notes
from src.panel.notes import CharacterNote, SheetNote, SheetSource
from src.panel.sheets import CampaignConfig, parse_config
from src.panel.vault import Vault

SCAN_INTERVAL_SECONDS = 60
MAX_PORTRAIT_BYTES = 16 * 1024 * 1024
CAMPAIGN_ROOT = ("Harpi", "Campaigns")
CHARACTERS_FOLDER = "characters"
SHEETS_FOLDER = "sheets"
NOTE_FOLDERS = (CHARACTERS_FOLDER, SHEETS_FOLDER)
PORTRAIT_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
PORTRAIT_SUFFIXES = frozenset(PORTRAIT_TYPES)
HIDDEN_PREFIXES = (".", "~")


@dataclass(frozen=True, slots=True)
class VaultFile:
    path: str
    name: str


@dataclass(frozen=True, slots=True)
class CampaignNotes:
    characters: dict[str, CharacterNote]
    sheets: tuple[SheetNote, ...]
    config: CampaignConfig | None
    config_error: str | None


EMPTY_NOTES = CampaignNotes(
    characters={}, sheets=(), config=None, config_error=None
)


def skipped(name: str) -> bool:
    return (
        name.startswith(HIDDEN_PREFIXES)
        or name.endswith(".tmp")
        or ".sync-conflict-" in name
    )


def shortest_key(path: str) -> tuple[int, int, str]:
    return path.count("/"), len(path), path


def locate_note(path: str) -> tuple[str, str] | None:
    parts = PurePosixPath(path).parts
    depth = len(CAMPAIGN_ROOT)
    if len(parts) != depth + 3 or tuple(parts[:depth]) != CAMPAIGN_ROOT:
        return None
    slug, folder, name = parts[depth:]
    if folder not in NOTE_FOLDERS or not name.endswith(".md"):
        return None
    return slug, folder


def locate_config(path: str) -> str | None:
    parts = PurePosixPath(path).parts
    depth = len(CAMPAIGN_ROOT)
    if len(parts) != depth + 2 or tuple(parts[:depth]) != CAMPAIGN_ROOT:
        return None
    slug, name = parts[depth:]
    return slug if name == "config.md" else None


def clean_relative(reference: str | None) -> str | None:
    if not reference:
        return None
    parts = reference.strip().replace("\\", "/").split("/")
    if any(
        part in ("", ".", "..") or part.startswith(HIDDEN_PREFIXES)
        for part in parts
    ):
        return None
    return "/".join(parts)


class VaultIndex:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root
        self.files: dict[str, VaultFile] = {}
        self.by_name: dict[str, tuple[str, ...]] = {}
        self.campaigns: dict[str, CampaignNotes] = {}
        if root is None:
            return
        self._resolved_root = root.resolve()
        self._collect()
        self.campaigns = self._parse_campaigns()

    @property
    def available(self) -> bool:
        return self.root is not None and self.root.is_dir()

    def campaign(self, slug: str) -> CampaignNotes:
        return self.campaigns.get(slug, EMPTY_NOTES)

    def portrait_path(self, reference: str | None) -> Path | None:
        relative = clean_relative(reference)
        if relative is None or self.root is None:
            return None
        candidate = (
            self._relative_file(relative)
            if "/" in relative
            else self._shortest(relative)
        )
        return None if candidate is None else self._inside_root(candidate)

    def _collect(self) -> None:
        names: dict[str, list[str]] = {}
        for entry in self._walk():
            self.files[entry.path] = entry
            names.setdefault(entry.name, []).append(entry.path)
        self.by_name = {
            name: tuple(sorted(paths, key=shortest_key))
            for name, paths in names.items()
        }

    def _walk(self) -> list[VaultFile]:
        found: list[VaultFile] = []
        root = self.root
        if root is None:
            return found
        for base, folders, names in os.walk(root):
            folders[:] = sorted(name for name in folders if not skipped(name))
            for name in sorted(names):
                entry = self._entry(Path(base, name), root)
                if entry is not None:
                    found.append(entry)
        return found

    def _entry(self, path: Path, root: Path) -> VaultFile | None:
        if skipped(path.name) or not path.is_file():
            return None
        return VaultFile(
            path=path.relative_to(root).as_posix(),
            name=path.name,
        )

    def _parse_campaigns(self) -> dict[str, CampaignNotes]:
        characters: dict[str, dict[str, CharacterNote]] = {}
        sheets: dict[str, list[SheetSource]] = {}
        configs: dict[str, CampaignConfig] = {}
        config_errors: dict[str, str] = {}
        for path in self.files:
            self._parse_file(path, characters, sheets, configs, config_errors)
        slugs = (
            set(characters) | set(sheets) | set(configs) | set(config_errors)
        )
        return {
            slug: self._campaign_notes(
                characters.get(slug, {}),
                sheets.get(slug, []),
                configs.get(slug),
                config_errors.get(slug),
            )
            for slug in slugs
        }

    def _parse_file(
        self,
        path: str,
        characters: dict[str, dict[str, CharacterNote]],
        sheets: dict[str, list[SheetSource]],
        configs: dict[str, CampaignConfig],
        config_errors: dict[str, str],
    ) -> None:
        config_slug = locate_config(path)
        if config_slug is not None:
            config, error = self._load_config(path)
            if config is not None:
                configs[config_slug] = config
            if error is not None:
                config_errors[config_slug] = error
            return
        located = locate_note(path)
        if located is None:
            return
        slug, folder = located
        text = self._read(path)
        if text is None:
            return
        if folder == CHARACTERS_FOLDER:
            note = notes.parse_character(path, text, fallback_id=path)
            characters.setdefault(slug, {}).setdefault(note.id, note)
        else:
            sheets.setdefault(slug, []).append(notes.parse_sheet(path, text))

    def _load_config(
        self, path: str
    ) -> tuple[CampaignConfig | None, str | None]:
        text = self._read(path)
        if text is None:
            return None, "config.md da campanha não pôde ser lido"
        config = parse_config(text)
        if config is not None:
            return config, None
        return None, "config.md da campanha inválido"

    def _campaign_notes(
        self,
        characters: dict[str, CharacterNote],
        sources: list[SheetSource],
        config: CampaignConfig | None,
        config_error: str | None,
    ) -> CampaignNotes:
        external: dict[str, CharacterNote] = {}
        resolved = tuple(
            self._resolve_sheet(source, characters, external)
            for source in sources
        )
        merged = dict(characters)
        for note in external.values():
            merged.setdefault(note.id, note)
        return CampaignNotes(
            characters=merged,
            sheets=resolved,
            config=config,
            config_error=config_error,
        )

    def _resolve_sheet(
        self,
        source: SheetSource,
        characters: dict[str, CharacterNote],
        external: dict[str, CharacterNote],
    ) -> SheetNote:
        key = self._character_key(source, characters, external)
        return replace(source.note, character=key)

    def _character_key(
        self,
        source: SheetSource,
        characters: dict[str, CharacterNote],
        external: dict[str, CharacterNote],
    ) -> str | None:
        if source.character_id in characters:
            return source.character_id
        if not source.link:
            return None
        path = self._note_path(source.link)
        if path is None:
            return None
        return self._external_key(path, source.note.id, characters, external)

    def _external_key(
        self,
        path: str,
        sheet_id: str,
        characters: dict[str, CharacterNote],
        external: dict[str, CharacterNote],
    ) -> str | None:
        if path in external:
            return external[path].id
        known = next(
            (note.id for note in characters.values() if note.path == path),
            None,
        )
        if known is not None:
            return known
        text = self._read(path)
        if text is None:
            return None
        note = notes.parse_character(path, text, fallback_id=sheet_id)
        external[path] = note
        return note.id

    def _note_path(self, target: str) -> str | None:
        cleaned = clean_relative(target)
        if cleaned is None:
            return None
        if "/" in cleaned:
            return self._path_file(cleaned)
        return self._named_note(cleaned)

    def _path_file(self, cleaned: str) -> str | None:
        path = cleaned if cleaned.endswith(".md") else f"{cleaned}.md"
        if path not in self.files or not self._is_character_note(path):
            return None
        return path

    def _named_note(self, name: str) -> str | None:
        for candidate_name in (name, f"{name}.md"):
            for path in self.by_name.get(candidate_name, ()):
                if self._is_character_note(path):
                    return path
        return None

    def _is_character_note(self, path: str) -> bool:
        if not path.endswith(".md"):
            return False
        located = locate_note(path)
        return located is None or located[1] == CHARACTERS_FOLDER

    def _relative_file(self, relative: str) -> Path | None:
        entry = self.files.get(relative)
        return (
            None
            if entry is None or self.root is None
            else self.root / entry.path
        )

    def _shortest(self, name: str) -> Path | None:
        paths = self.by_name.get(name, ())
        return None if not paths or self.root is None else self.root / paths[0]

    def _read(self, path: str) -> str | None:
        if self.root is None:
            return None
        try:
            return (self.root / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    def _inside_root(self, candidate: Path) -> Path | None:
        if candidate.suffix.casefold() not in PORTRAIT_SUFFIXES:
            return None
        try:
            resolved = candidate.resolve()
            if not resolved.is_file():
                return None
            resolved.relative_to(self._resolved_root)
            if resolved.suffix.casefold() not in PORTRAIT_SUFFIXES:
                return None
            if resolved.stat().st_size > MAX_PORTRAIT_BYTES:
                return None
        except (OSError, ValueError):
            return None
        return resolved


_index = VaultIndex()


def configure(index: VaultIndex) -> None:
    global _index
    _index = index


def configured() -> VaultIndex:
    return _index


async def refresh_once(vault: Vault) -> None:
    try:
        index = await asyncio.to_thread(VaultIndex, vault.root)
    except Exception as e:
        logger.opt(exception=True).error(f"Vault scan failed: {e}")
        return
    configure(index)


async def run_periodically(vault: Vault) -> None:
    while True:
        await asyncio.sleep(SCAN_INTERVAL_SECONDS)
        await refresh_once(vault)


def start_scan(vault: Vault) -> asyncio.Task[None]:
    return asyncio.create_task(
        run_periodically(vault), name="harpi-vault-scan"
    )


async def stop_scan(task: asyncio.Task[None]) -> None:
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
