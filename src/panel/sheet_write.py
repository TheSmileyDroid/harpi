from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.panel import notes
from src.panel.schemas import SheetPatch
from src.panel.sheets import (
    CampaignConfig,
    LoadedSheet,
    SheetError,
    canonical_prose,
    dump_block,
    load_sheet,
    decode_text,
    read_sheet,
    section_bounds,
    section_count,
    sha256_text,
    yaml_scalar,
)
from src.panel.vault_write import atomic_write, backup_text, write_lock

FILE_STATUS = {
    "active": "ativo",
    "pending": "pendente",
    "archived": "arquivado",
}
LEGAL_TRANSITIONS = frozenset({
    ("ativo", "arquivado"),
    ("arquivado", "ativo"),
})
SCALAR_FIELDS = ("refresh", "fate_points")
LIST_FIELDS = (
    "aspects",
    "skills",
    "stunts",
    "stress",
    "consequences",
    "extras",
    "inventory",
)
TEXT_FIELDS = ("history", "notes")
KEY_LINE = re.compile(
    r"^(?P<key>[A-Za-z0-9_-]+)[ \t]*:[ \t]*(?P<value>[^\r\n]*?)[ \t]*$"
)
TARGET_KEYS = (
    "tipo",
    "harpi-id",
    "harpi-campanha",
    "harpi-status",
    "harpi-rev",
    "harpi-owner",
    "harpi-owner-name",
)
ID_WARNING = "harpi-id editado à mão foi corrigido."
CAMPAIGN_WARNING = "harpi-campanha editado à mão foi corrigido."
OWNER_WARNING = "harpi-owner editado à mão foi corrigido."
STATUS_WARNING = "harpi-status com transição ilegal foi corrigido."
TYPE_WARNING = "tipo editado à mão foi corrigido."


class SheetWriteError(ValueError):
    pass


class SheetConflict(SheetWriteError):
    pass


class SheetInvalid(SheetWriteError):
    pass


class SheetReadOnly(SheetWriteError):
    pass


class SheetRejected(SheetWriteError):
    pass


@dataclass(frozen=True, slots=True)
class SheetRecord:
    id: str
    owner: str | None
    status: str
    rev: int
    owner_name: str | None = None


@dataclass(frozen=True, slots=True)
class FrontValues:
    id: str
    owner: str | None
    status: str
    rev: int


@dataclass(frozen=True, slots=True)
class SheetWriteResult:
    text: str
    hash: str
    rev: int
    status: str
    owner: str | None
    warnings: tuple[str, ...]
    harpi_id: str
    backup_id: str
    previous_rev: int
    previous_text: str


def write_sheet(
    path: Path,
    slug: str,
    sheet_id: str,
    patch: SheetPatch,
    config: CampaignConfig,
    record: SheetRecord | None,
    backup_dir: Path,
) -> SheetWriteResult:
    with write_lock():
        return _write_sheet(
            path, slug, sheet_id, patch, config, record, backup_dir
        )


def _write_sheet(
    path: Path,
    slug: str,
    sheet_id: str,
    patch: SheetPatch,
    config: CampaignConfig,
    record: SheetRecord | None,
    backup_dir: Path,
) -> SheetWriteResult:
    text = read_text(path)
    if sha256_text(text) != patch.base_hash.strip():
        raise SheetConflict("a ficha mudou no disco")
    result = patch_sheet(text, slug, sheet_id, patch, config, record)
    if read_text(path) != text:
        raise SheetConflict("a ficha mudou no disco")
    backup_text(
        backup_dir / safe_component(slug) / safe_component(result.backup_id),
        text,
        result.previous_rev,
    )
    atomic_write(path, result.text)
    return result


def safe_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", value)
    return "_" if cleaned in ("", ".", "..") else cleaned


def read_text(path: Path) -> str:
    try:
        return decode_text(path.read_bytes())
    except UnicodeDecodeError as failure:
        raise SheetInvalid("a ficha não está em UTF-8") from failure


def restore_sheet(path: Path, text: str) -> None:
    with write_lock():
        atomic_write(path, text)


def patch_sheet(
    text: str,
    slug: str,
    sheet_id: str,
    patch: SheetPatch,
    config: CampaignConfig,
    record: SheetRecord | None,
) -> SheetWriteResult:
    text = text.removeprefix("\ufeff")
    document = load_document(text)
    fields, _ = notes.split_frontmatter(text)
    front = front_values(fields, sheet_id)
    warnings = correction_warnings(fields, front, record, slug)
    owner, canonical_id = canonical_identity(front, record)
    status = target_status(front.status, record, patch, warnings)
    ensure_writable(front, patch)
    apply_block(document, patch)
    validate_block(document, config)
    revision = max(record.rev if record is not None else 0, front.rev) + 1
    target = frontmatter_target(
        record, owner, canonical_id, slug, status, revision
    )
    head, body = split_head(text)
    new_text = "".join([
        *patch_frontmatter(head, target),
        *patch_body(body, document, patch),
    ])
    validate_text(new_text, config)
    return SheetWriteResult(
        text=new_text,
        hash=sha256_text(new_text),
        rev=revision,
        status=status,
        owner=owner,
        warnings=tuple(warnings),
        harpi_id=canonical_id,
        backup_id=canonical_id,
        previous_rev=front.rev,
        previous_text=text,
    )


def load_document(text: str) -> Any:
    loaded = load_sheet(text)
    if loaded.document is None:
        raise SheetInvalid(loaded.error or "bloco harpi-sheet ausente")
    return loaded.document


def ensure_writable(front: FrontValues, patch: SheetPatch) -> None:
    if front.status == "arquivado" and touches_fields(patch):
        raise SheetReadOnly("a ficha arquivada é somente leitura")


def frontmatter_target(
    record: SheetRecord | None,
    owner: str | None,
    canonical_id: str,
    slug: str,
    status: str,
    revision: int,
) -> dict[str, str]:
    target = {
        "tipo": "ficha",
        "harpi-id": canonical_id,
        "harpi-campanha": slug,
        "harpi-status": status,
        "harpi-rev": str(revision),
    }
    if owner is not None:
        target["harpi-owner"] = owner
    if record is not None and record.owner_name is not None:
        target["harpi-owner-name"] = record.owner_name
    return target


def front_values(fields: dict[str, str], sheet_id: str) -> FrontValues:
    return FrontValues(
        id=notes.field_front(fields, "harpi-id") or sheet_id,
        owner=notes.field_front(fields, "harpi-owner"),
        status=notes.field_front(fields, "harpi-status") or "",
        rev=notes.revision(fields),
    )


def canonical_identity(
    front: FrontValues, record: SheetRecord | None
) -> tuple[str | None, str]:
    if record is None:
        return front.owner, front.id
    owner = record.owner if record.owner is not None else front.owner
    return owner, record.id


def correction_warnings(
    fields: dict[str, str],
    front: FrontValues,
    record: SheetRecord | None,
    slug: str,
) -> list[str]:
    wrong_id = front.id != (record.id if record is not None else front.id)
    wrong_campaign = notes.field_front(fields, "harpi-campanha") not in (
        None,
        slug,
    )
    wrong_owner = (
        record is not None
        and record.owner is not None
        and front.owner != record.owner
    )
    wrong_type = notes.field_front(fields, "tipo") not in (None, "ficha")
    checks = (
        (wrong_id, ID_WARNING),
        (wrong_campaign, CAMPAIGN_WARNING),
        (wrong_owner, OWNER_WARNING),
        (wrong_type, TYPE_WARNING),
    )
    return [message for failed, message in checks if failed]


def target_status(
    file_status: str,
    record: SheetRecord | None,
    patch: SheetPatch,
    warnings: list[str],
) -> str:
    accepted = accepted_status(file_status, record, warnings)
    return requested_status(accepted, patch, warnings)


def accepted_status(
    file_status: str,
    record: SheetRecord | None,
    warnings: list[str],
) -> str:
    accepted = file_status or (record.status if record is not None else "")
    if record is None or not file_status or file_status == record.status:
        return accepted or "ativo"
    if legal(record.status, file_status):
        return file_status
    warnings.append(STATUS_WARNING)
    return record.status


def requested_status(
    accepted: str, patch: SheetPatch, warnings: list[str]
) -> str:
    if patch.status is None:
        return accepted
    requested = FILE_STATUS[patch.status]
    if requested == accepted or legal(accepted, requested):
        return requested
    if STATUS_WARNING not in warnings:
        warnings.append(STATUS_WARNING)
    return accepted


def legal(current: str, wanted: str) -> bool:
    return (current, wanted) in LEGAL_TRANSITIONS


def touches_fields(patch: SheetPatch) -> bool:
    keys = (*SCALAR_FIELDS, *LIST_FIELDS, *TEXT_FIELDS)
    return any(getattr(patch, key) is not None for key in keys)


def apply_block(document: Any, patch: SheetPatch) -> None:
    for key in SCALAR_FIELDS:
        value = getattr(patch, key)
        if value is not None:
            document[key] = value
    for key in LIST_FIELDS:
        value = getattr(patch, key)
        if value is not None:
            document[key] = [item.model_dump() for item in value]


def validate_block(document: Any, config: CampaignConfig) -> None:
    try:
        read_sheet(LoadedSheet(document, None), config)
    except SheetError as failure:
        raise SheetRejected(str(failure)) from failure


def validate_text(text: str, config: CampaignConfig) -> None:
    validate_block(load_document(text), config)


def split_head(text: str) -> tuple[list[str], list[str]]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise SheetInvalid("frontmatter ausente")
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[: index + 1], lines[index + 1 :]
    raise SheetInvalid("frontmatter ausente")


def newline_of(lines: list[str]) -> str:
    for line in lines:
        if line.endswith("\r\n"):
            return "\r\n"
        if line.endswith("\n"):
            return "\n"
    return "\n"


def patch_frontmatter(head: list[str], target: dict[str, str]) -> list[str]:
    newline = newline_of(head)
    entries, present = replace_entries(head[1:-1], target, newline)
    missing = [
        key for key in TARGET_KEYS if key in target and key not in present
    ]
    inserted = [
        f"{key}: {render_value(key, target[key])}{newline}" for key in missing
    ]
    return [head[0], *entries, *inserted, head[-1]]


def replace_entries(
    lines: list[str], target: dict[str, str], newline: str
) -> tuple[list[str], set[str]]:
    entries: list[str] = []
    present: set[str] = set()
    index = 0
    while index < len(lines):
        match = KEY_LINE.match(lines[index].rstrip("\r\n"))
        if match is None or match.group("key") not in target:
            entries.append(lines[index])
            index += 1
            continue
        key = match.group("key")
        present.add(key)
        end = entry_end(lines, index)
        entries.extend(
            render_entry(
                key,
                target[key],
                match.group("value"),
                lines[index],
                newline,
            )
        )
        index = end
    return entries, present


def entry_end(lines: list[str], index: int) -> int:
    end = index + 1
    while end < len(lines) and lines[end][:1].isspace() and lines[end].strip():
        end += 1
    return end


def render_entry(
    key: str,
    value: str,
    current: str,
    line: str,
    newline: str,
) -> list[str]:
    if key == "harpi-rev" or notes.scalar(current) != value:
        comment = inline_comment(line)
        return [f"{key}: {render_value(key, value)}{comment}{newline}"]
    return [line]


def render_value(key: str, value: str) -> str:
    if key == "harpi-owner":
        return f'"{value}"'
    if key == "harpi-rev":
        return value
    return yaml_scalar(value)


def inline_comment(line: str) -> str:
    body = line.rstrip("\r\n")
    position = comment_start(body)
    return "" if position < 0 else body[max(position - 1, 0) :]


def comment_start(body: str) -> int:
    quote = ""
    for index, char in enumerate(body):
        if quote:
            quote = "" if char == quote else quote
        elif char in "\"'":
            quote = char
        elif comment_at(body, index):
            return index
    return -1


def comment_at(body: str, index: int) -> bool:
    return body[index] == "#" and (index == 0 or body[index - 1] in " \t")


def patch_body(body: list[str], document: Any, patch: SheetPatch) -> list[str]:
    newline = newline_of(body)
    lines = replace_block(body, document, newline)
    return patch_prose(lines, patch, newline)


def replace_block(lines: list[str], document: Any, newline: str) -> list[str]:
    for index, line in enumerate(lines):
        if line.strip() != "```harpi-sheet":
            continue
        for end in range(index + 1, len(lines)):
            if lines[end].strip() == "```":
                block = dump_block(document).replace("\n", newline)
                return (
                    lines[: index + 1] + block.splitlines(True) + lines[end:]
                )
        break
    raise SheetInvalid("bloco harpi-sheet ausente")


def patch_prose(
    lines: list[str], patch: SheetPatch, newline: str
) -> list[str]:
    for heading, value in (
        ("## História", patch.history),
        ("## Anotações", patch.notes),
    ):
        if value is None:
            continue
        if section_count(lines, heading) > 1:
            raise SheetRejected(f"seção duplicada: {heading}")
        content = canonical_prose(value)
        bounds = section_bounds(lines, heading)
        replacement = section_lines(content, newline)
        if bounds is None:
            lines = append_section(lines, heading, replacement, newline)
        else:
            start, end = bounds
            lines = lines[: start + 1] + replacement + lines[end:]
    return lines


def section_lines(content: str, newline: str) -> list[str]:
    rows = (
        [] if not content else [line + newline for line in content.split("\n")]
    )
    return [newline, *rows, newline]


def append_section(
    lines: list[str], heading: str, replacement: list[str], newline: str
) -> list[str]:
    body = list(lines)
    if body and not body[-1].endswith(("\n", "\r")):
        body[-1] = body[-1] + newline
    if body and body[-1].strip():
        body.append(newline)
    return [*body, f"{heading}{newline}", *replacement]
