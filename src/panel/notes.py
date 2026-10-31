from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import PurePosixPath

_DELIMITER = "---"
_EMBED = re.compile(r"!\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
_LINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
_ASPECT = re.compile(
    r"^\s*[-*]\s*\*\*(?P<label>[^*:]+?)\s*:?\*\*\s*:?\s*(?P<text>.+?)\s*$"
)
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_EMPTY = frozenset({"", "~", "null", "none"})
_SKIP_PREFIXES = ("#", "!", "-", "*", ">", "|")
_CONCEPT_LABELS = frozenset({"conceito", "funcao", "concept", "function"})
_SUMMARY_HEADINGS = frozenset({"resumo", "summary"})


@dataclass(frozen=True, slots=True)
class CharacterNote:
    id: str
    path: str
    name: str
    concept: str | None
    summary: str | None
    portrait: str | None
    status: str | None


@dataclass(frozen=True, slots=True)
class SheetNote:
    id: str
    path: str
    character: str | None
    owner: str | None
    status: str | None


@dataclass(frozen=True, slots=True)
class SheetSource:
    note: SheetNote
    character_id: str | None
    link: str | None


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )


def scalar(value: str) -> str | None:
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    return None if text.casefold() in _EMPTY else text or None


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != _DELIMITER:
        return {}, text
    for index in range(1, len(lines)):
        if lines[index].strip() != _DELIMITER:
            continue
        return _fields(lines[1:index]), "\n".join(lines[index + 1 :])
    return {}, text


def _fields(lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in lines:
        if not line or line[:1].isspace():
            continue
        key, separator, value = line.partition(":")
        if not separator:
            continue
        cleaned = scalar(value)
        if cleaned is not None:
            fields[key.strip().casefold()] = cleaned
    return fields


def field_front(fields: dict[str, str], *names: str) -> str | None:
    for name in names:
        value = fields.get(name)
        if value:
            return value
    return None


def link_target(value: str) -> str:
    match = _LINK.search(value)
    return match.group(1).strip() if match else value.strip()


def first_embed(body: str) -> str | None:
    match = _EMBED.search(body)
    return match.group(1).strip() if match else None


def _plain_lines(text: str) -> list[str]:
    lines: list[str] = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
        elif not in_fence:
            lines.append(stripped)
    return lines


def first_paragraph(text: str) -> str | None:
    block: list[str] = []
    for line in _plain_lines(text):
        if line and not line.startswith(_SKIP_PREFIXES):
            block.append(line)
        elif block:
            break
    return " ".join(block) or None


def section_paragraph(body: str, names: frozenset[str]) -> str | None:
    headings = list(_HEADING.finditer(body))
    for index, heading in enumerate(headings):
        if normalize(heading.group(2)) not in names:
            continue
        end = (
            headings[index + 1].start()
            if index + 1 < len(headings)
            else len(body)
        )
        return first_paragraph(body[heading.end() : end])
    return None


def aspect_text(body: str, labels: frozenset[str]) -> str | None:
    for line in body.splitlines():
        match = _ASPECT.match(line)
        if match and normalize(match.group("label")) in labels:
            return match.group("text").strip() or None
    return None


def parse_character(path: str, text: str, fallback_id: str) -> CharacterNote:
    fields, body = split_frontmatter(text)
    concept = field_front(fields, "conceito", "concept") or aspect_text(
        body, _CONCEPT_LABELS
    )
    summary = (
        field_front(fields, "resumo", "summary")
        or section_paragraph(body, _SUMMARY_HEADINGS)
        or first_paragraph(body)
    )
    portrait = field_front(fields, "harpi-portrait", "imagem", "image")
    return CharacterNote(
        id=field_front(fields, "harpi-id") or fallback_id,
        path=path,
        name=field_front(fields, "nome", "name") or PurePosixPath(path).stem,
        concept=concept,
        summary=summary,
        portrait=link_target(portrait) if portrait else first_embed(body),
        status=field_front(fields, "harpi-status"),
    )


def parse_sheet(path: str, text: str) -> SheetSource:
    fields, _ = split_frontmatter(text)
    link = field_front(fields, "harpi-character")
    note = SheetNote(
        id=field_front(fields, "harpi-id") or path,
        path=path,
        character=None,
        owner=field_front(fields, "harpi-owner"),
        status=field_front(fields, "harpi-status"),
    )
    return SheetSource(
        note=note,
        character_id=field_front(fields, "harpi-character-id"),
        link=link_target(link) if link else None,
    )
