from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml.comments import CommentedMap

from src.panel import notes, sheet_write
from src.panel.sheets import (
    CampaignConfig,
    dump_block,
    load_sheet,
    read_sheet,
    yaml_scalar,
)

PENDING = "pendente"
ACTIVE = "ativo"
REVIEW_NOTE_KEY = "harpi-review-note"
FORBIDDEN_NAME_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
NAME_LIMIT = 80


class InvalidName(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class NoteRewrite:
    text: str
    previous_text: str
    rev: int


def file_stem(name: str) -> str:
    cleaned = FORBIDDEN_NAME_CHARS.sub("", name.strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if not cleaned:
        raise InvalidName("o nome do personagem está em branco")
    return cleaned[:NAME_LIMIT].strip(" .")


def character_text(
    slug: str,
    identifier: str,
    name: str,
    concept: str | None,
    summary: str | None,
    status: str,
) -> str:
    lines = [
        "---",
        "tipo: personagem",
        f"harpi-id: {identifier}",
        f"harpi-campanha: {yaml_scalar(slug)}",
        f"harpi-status: {status}",
        "harpi-rev: 1",
        "aliases: []",
        "tags: []",
        f"nome: {yaml_scalar(name)}",
    ]
    if concept:
        lines.append(f"conceito: {yaml_scalar(concept)}")
    lines.append("---")
    text = "\n".join(lines) + "\n"
    if summary:
        text += f"\n{summary.strip()}\n"
    return text


def sheet_text(
    slug: str,
    identifier: str,
    character_id: str,
    character_name: str,
    owner: str | None,
    owner_name: str | None,
    status: str,
    config: CampaignConfig,
) -> str:
    lines = [
        "---",
        "tipo: ficha",
        f"harpi-id: {identifier}",
        f"harpi-campanha: {yaml_scalar(slug)}",
        f"harpi-character-id: {character_id}",
        f"harpi-character: {yaml_scalar(f'[[{character_name}]]')}",
    ]
    if owner is not None:
        lines.append(f'harpi-owner: "{owner}"')
    if owner_name:
        lines.append(f"harpi-owner-name: {yaml_scalar(owner_name)}")
    lines.extend([
        f"harpi-status: {status}",
        "harpi-rev: 1",
        "---",
        "## História",
        "",
        "## Anotações",
        "",
        "```harpi-sheet",
        dump_block(default_block(config)).rstrip("\n"),
        "```",
        "",
    ])
    text = "\n".join(lines)
    read_sheet(load_sheet(text), config)
    return text


def default_block(config: CampaignConfig) -> CommentedMap:
    document = CommentedMap()
    document["refresh"] = config.refresh
    document["fate_points"] = 0
    document["aspects"] = [
        {"label": label, "text": ""} for label in config.aspects
    ]
    document["skills"] = []
    document["stunts"] = []
    document["stress"] = [
        {
            "track": track.track,
            "boxes": [
                {"value": value, "checked": False} for value in track.boxes
            ],
        }
        for track in config.stress
    ]
    document["consequences"] = [
        {"severity": slot.severity, "value": slot.value, "text": ""}
        for slot in config.consequences
    ]
    document["extras"] = []
    document["inventory"] = []
    return document


def rewrite_frontmatter(
    path: Path,
    updates: dict[str, str],
    backup_dir: Path,
    backup_id: str,
    drops: frozenset[str] = frozenset(),
) -> NoteRewrite:
    with sheet_write.write_lock():
        text = sheet_write.read_text(path)
        head, body = sheet_write.split_head(text)
        fields, _ = notes.split_frontmatter(text)
        previous_rev = notes.revision(fields)
        rev = previous_rev + 1
        target = {**updates, "harpi-rev": str(rev)}
        new_text = "".join([
            *sheet_write.patch_frontmatter(head, target, drops),
            *body,
        ])
        sheet_write.backup_text(
            backup_dir / sheet_write.safe_component(backup_id),
            text,
            previous_rev,
        )
        sheet_write.atomic_write(path, new_text)
        return NoteRewrite(text=new_text, previous_text=text, rev=rev)


def set_status(
    path: Path, status: str, backup_dir: Path, backup_id: str
) -> NoteRewrite:
    return rewrite_frontmatter(
        path, {"harpi-status": status}, backup_dir, backup_id
    )


def review_status(path: Path) -> str | None:
    fields, _ = notes.split_frontmatter(sheet_write.read_text(path))
    return notes.field_front(fields, "harpi-status")
