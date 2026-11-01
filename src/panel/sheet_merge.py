from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from src.panel import notes
from src.panel.schemas import SheetPatch, SheetStatus
from src.panel.sheets import (
    dump_plain_yaml,
    load_plain_yaml,
    load_sheet,
    prose_sections,
    sha256_text,
)

STATUS_BY_NAME: dict[str, str] = {
    "active": "ativo",
    "pending": "pendente",
    "archived": "arquivado",
}
SHEET_STATUS_NAMES: dict[str, SheetStatus] = {
    "ativo": "active",
    "pendente": "pending",
    "arquivado": "archived",
}
SCALAR_FIELDS = ("refresh", "fate_points")
PROSE_FIELDS = ("history", "notes")
LIST_KEYS: dict[str, tuple[str, ...]] = {
    "aspects": ("label",),
    "skills": ("name",),
    "stunts": ("name",),
    "stress": ("track",),
    "consequences": ("severity",),
    "extras": ("kind", "name"),
    "inventory": ("item",),
}
DUPLICABLE_FIELDS = frozenset({"aspects", "stunts", "extras", "inventory"})
SETTLED = object()


@dataclass(frozen=True, slots=True)
class SheetState:
    frontmatter: dict[str, str]
    history: str
    notes: str
    block: dict[str, Any]


@dataclass(frozen=True, slots=True)
class MergeConflict:
    field_path: str
    base: Any
    ours: Any
    theirs: Any
    allow_both: bool

    def rendered(self) -> tuple[str | None, str | None, str | None]:
        return render(self.base), render(self.ours), render(self.theirs)


@dataclass(frozen=True, slots=True)
class MergeResult:
    state: SheetState
    conflicts: tuple[MergeConflict, ...]
    remaining: tuple[MergeConflict, ...]


def state_from_text(text: str) -> SheetState:
    fields, _ = notes.split_frontmatter(text)
    history, prose = prose_sections(text)
    loaded = load_sheet(text)
    if loaded.document is None:
        raise ValueError(loaded.error or "bloco harpi-sheet ausente")
    return SheetState(dict(fields), history, prose, plain(loaded.document))


def state_from_base(base_json: str) -> SheetState:
    data = json.loads(base_json)
    if not isinstance(data, Mapping):
        raise ValueError("snapshot inválido")
    block_text = data.get("block")
    loaded = None if not block_text else plain(load_plain_yaml(block_text))
    return SheetState(
        {
            str(key): text(value)
            for key, value in _mapping(data.get("frontmatter")).items()
        },
        text(data.get("history")),
        text(data.get("notes")),
        loaded if isinstance(loaded, dict) else {},
    )


def apply_patch(state: SheetState, patch: SheetPatch) -> SheetState:
    return SheetState(
        patched_frontmatter(state.frontmatter, patch),
        patched_prose(state.history, patch.history),
        patched_prose(state.notes, patch.notes),
        patched_block(state.block, patch),
    )


def patched_frontmatter(
    frontmatter: dict[str, str], patch: SheetPatch
) -> dict[str, str]:
    merged = dict(frontmatter)
    if patch.status is not None:
        merged["harpi-status"] = STATUS_BY_NAME[patch.status]
    return merged


def patched_prose(current: str, value: str | None) -> str:
    return current if value is None else value


def patched_block(block: dict[str, Any], patch: SheetPatch) -> dict[str, Any]:
    merged = dict(block)
    merged.update(scalar_changes(patch))
    merged.update(list_changes(patch))
    return merged


def scalar_changes(patch: SheetPatch) -> dict[str, int]:
    return {
        key: getattr(patch, key)
        for key in SCALAR_FIELDS
        if getattr(patch, key) is not None
    }


def list_changes(patch: SheetPatch) -> dict[str, list[dict[str, Any]]]:
    return {
        key: [item.model_dump() for item in getattr(patch, key)]
        for key in LIST_KEYS
        if getattr(patch, key) is not None
    }


def merge(
    base: SheetState,
    ours: SheetState,
    theirs: SheetState,
    decisions: Mapping[str, str] | None = None,
) -> MergeResult:
    chosen = {} if decisions is None else dict(decisions)
    conflicts: list[MergeConflict] = []
    frontmatter = dict(theirs.frontmatter)
    _merge_status(base, ours, theirs, frontmatter)
    history = _merge_value(
        base.history,
        ours.history,
        theirs.history,
        "history",
        True,
        chosen,
        conflicts,
    )
    prose = _merge_value(
        base.notes,
        ours.notes,
        theirs.notes,
        "notes",
        True,
        chosen,
        conflicts,
    )
    block = dict(theirs.block)
    for key in SCALAR_FIELDS:
        block[key] = _merge_value(
            base.block.get(key),
            ours.block.get(key),
            theirs.block.get(key),
            f"block.{key}",
            False,
            chosen,
            conflicts,
        )
    for key in LIST_KEYS:
        block[key] = _merge_items(key, base, ours, theirs, chosen, conflicts)
    remaining = tuple(
        conflict for conflict in conflicts if conflict.field_path not in chosen
    )
    return MergeResult(
        SheetState(frontmatter, history, prose, block),
        tuple(conflicts),
        remaining,
    )


def patch_from_state(theirs: SheetState, merged: SheetState) -> dict[str, Any]:
    changes: dict[str, Any] = {}
    changes.update(scalar_patch(theirs, merged))
    changes.update(list_patch(theirs, merged))
    changes.update(prose_patch(theirs, merged))
    status = _status_change(theirs, merged)
    if status is not None:
        changes["status"] = status
    return changes


def scalar_patch(theirs: SheetState, merged: SheetState) -> dict[str, Any]:
    return {
        key: merged.block.get(key)
        for key in SCALAR_FIELDS
        if merged.block.get(key) != theirs.block.get(key)
    }


def list_patch(
    theirs: SheetState, merged: SheetState
) -> dict[str, list[dict[str, Any]]]:
    patched: dict[str, list[dict[str, Any]]] = {}
    for key in LIST_KEYS:
        disk = normalized_list(key, theirs.block.get(key))
        wanted = normalized_list(key, merged.block.get(key))
        if wanted != disk:
            patched[key] = wanted
    return patched


def normalized_list(field: str, items: Any) -> list[dict[str, Any]]:
    return [normalized_item(field, item) for item in items or ()]


def prose_patch(theirs: SheetState, merged: SheetState) -> dict[str, str]:
    return {
        key: getattr(merged, key)
        for key in PROSE_FIELDS
        if getattr(merged, key) != getattr(theirs, key)
    }


def consolidated_patch(
    theirs_text: str, changes: Mapping[str, Any]
) -> SheetPatch:
    return SheetPatch(base_hash=sha256_text(theirs_text), **changes)


def _status_change(
    theirs: SheetState, merged: SheetState
) -> SheetStatus | None:
    wanted = merged.frontmatter.get("harpi-status")
    if wanted is None or wanted == theirs.frontmatter.get("harpi-status"):
        return None
    return SHEET_STATUS_NAMES.get(wanted)


def _merge_status(
    base: SheetState,
    ours: SheetState,
    theirs: SheetState,
    frontmatter: dict[str, str],
) -> None:
    left = base.frontmatter.get("harpi-status")
    right = ours.frontmatter.get("harpi-status")
    disk = theirs.frontmatter.get("harpi-status")
    value = right if disk == left else disk
    if value is None:
        frontmatter.pop("harpi-status", None)
    else:
        frontmatter["harpi-status"] = value


def _merge_value(
    base: Any,
    ours: Any,
    theirs: Any,
    field_path: str,
    allow_both: bool,
    decisions: Mapping[str, str],
    conflicts: list[MergeConflict],
) -> Any:
    if ours == theirs:
        return ours
    if ours == base:
        return theirs
    if theirs == base:
        return ours
    conflicts.append(MergeConflict(field_path, base, ours, theirs, allow_both))
    decision = decisions.get(field_path)
    if decision == "both" and allow_both:
        return both_text(ours, theirs)
    return ours if decision == "ours" else theirs


def both_text(ours: str, theirs: str) -> str:
    if not ours or not theirs:
        return ours or theirs
    return f"{ours}\n\n{theirs}"


def _merge_items(
    key: str,
    base: SheetState,
    ours: SheetState,
    theirs: SheetState,
    decisions: Mapping[str, str],
    conflicts: list[MergeConflict],
) -> list[dict[str, Any]]:
    base_items = keyed_items(key, base.block.get(key) or ())
    ours_items = keyed_items(key, ours.block.get(key) or ())
    theirs_items = keyed_items(key, theirs.block.get(key) or ())
    merge = _merge_stress_item if key == "stress" else _merge_list_item
    merged: list[dict[str, Any]] = []
    for item_key in item_order(base_items, ours_items, theirs_items):
        merged.extend(
            merge(
                f"block.{key}[{item_key}]",
                base_items.get(item_key),
                ours_items.get(item_key),
                theirs_items.get(item_key),
                key in DUPLICABLE_FIELDS,
                decisions,
                conflicts,
            )
        )
    return merged


def _merge_list_item(
    field_path: str,
    base: dict[str, Any] | None,
    ours: dict[str, Any] | None,
    theirs: dict[str, Any] | None,
    allow_both: bool,
    decisions: Mapping[str, str],
    conflicts: list[MergeConflict],
) -> list[dict[str, Any]]:
    if ours == theirs:
        return present(ours)
    if ours == base:
        return present(theirs)
    if theirs == base:
        return present(ours)
    conflicts.append(MergeConflict(field_path, base, ours, theirs, allow_both))
    decision = decisions.get(field_path)
    if decision == "ours":
        return present(ours)
    if decision == "both":
        return both(ours, theirs)
    return present(theirs)


def _merge_stress_item(
    field_path: str,
    base: dict[str, Any] | None,
    ours: dict[str, Any] | None,
    theirs: dict[str, Any] | None,
    allow_both: bool,
    decisions: Mapping[str, str],
    conflicts: list[MergeConflict],
) -> list[dict[str, Any]]:
    del allow_both
    settled = _settled_merge(base, ours, theirs)
    if settled is not SETTLED:
        return present(settled)
    if base is None or ours is None or theirs is None:
        conflicts.append(MergeConflict(field_path, base, ours, theirs, False))
        return present(ours if decisions.get(field_path) == "ours" else theirs)
    return [_merge_boxes(field_path, base, ours, theirs, decisions, conflicts)]


def _settled_merge(base: Any, ours: Any, theirs: Any) -> Any:
    if ours == theirs:
        return ours
    if ours == base:
        return theirs
    if theirs == base:
        return ours
    return SETTLED


def _merge_boxes(
    field_path: str,
    base: dict[str, Any],
    ours: dict[str, Any],
    theirs: dict[str, Any],
    decisions: Mapping[str, str],
    conflicts: list[MergeConflict],
) -> dict[str, Any]:
    base_boxes = box_values(base)
    ours_boxes = box_values(ours)
    theirs_boxes = box_values(theirs)
    merged: list[dict[str, Any]] = []
    for value in item_order(base_boxes, ours_boxes, theirs_boxes):
        checked = _merge_value(
            base_boxes.get(value),
            ours_boxes.get(value),
            theirs_boxes.get(value),
            f"{field_path}.box[{value}]",
            False,
            decisions,
            conflicts,
        )
        if checked is not None:
            merged.append({"value": value, "checked": checked})
    return {"track": text(theirs.get("track")), "boxes": merged}


def box_values(track: Mapping[str, Any]) -> dict[Any, Any]:
    return {
        box.get("value"): box.get("checked") is True
        for box in boxes(track.get("boxes"))
    }


def both(
    ours: dict[str, Any] | None, theirs: dict[str, Any] | None
) -> list[dict[str, Any]]:
    if ours is None or theirs is None:
        return present(ours if ours is not None else theirs)
    return [ours, theirs]


def present(item: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [] if item is None else [item]


def item_order(
    base: Mapping[str, Any],
    ours: Mapping[str, Any],
    theirs: Mapping[str, Any],
) -> list[str]:
    order = list(theirs)
    order.extend(key for key in ours if key not in theirs)
    order.extend(key for key in base if key not in theirs and key not in ours)
    return order


def keyed_items(field: str, items: Iterable[Any]) -> dict[str, dict[str, Any]]:
    return {
        key: normalized_item(field, raw)
        for key, raw in keyed_raw_items(field, items).items()
    }


def keyed_raw_items(field: str, items: Iterable[Any]) -> dict[str, Any]:
    keyed: dict[str, Any] = {}
    counts: dict[str, int] = {}
    for raw in items:
        item = raw if isinstance(raw, Mapping) else {}
        label = item_key(field, normalized_item(field, item))
        count = counts.get(label, 0) + 1
        counts[label] = count
        keyed[label if count == 1 else f"{label}#{count}"] = item
    return keyed


def item_key(field: str, item: Mapping[str, Any]) -> str:
    return "|".join(str(item.get(part) or "") for part in LIST_KEYS[field])


def normalized_item(field: str, raw: Any) -> dict[str, Any]:
    item = raw if isinstance(raw, Mapping) else {}
    return NORMALIZERS.get(field, normalized_inventory)(item)


def normalized_aspect(item: Mapping[str, Any]) -> dict[str, Any]:
    return {"label": text(item.get("label")), "text": text(item.get("text"))}


def normalized_skill(item: Mapping[str, Any]) -> dict[str, Any]:
    return {"name": text(item.get("name")), "rank": integer(item.get("rank"))}


def normalized_stunt(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "name": text(item.get("name")),
        "text": text(item.get("text")),
        "refresh_cost": integer(item.get("refresh_cost")),
    }


def normalized_stress(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "track": text(item.get("track")),
        "boxes": [normalized_box(box) for box in boxes(item.get("boxes"))],
    }


def normalized_consequence(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "severity": text(item.get("severity")),
        "text": text(item.get("text")),
    }


def normalized_extra(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "kind": text(item.get("kind")),
        "name": text(item.get("name")),
        "text": text(item.get("text")),
        "cost": optional_integer(item.get("cost")),
    }


def normalized_inventory(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "item": text(item.get("item")),
        "qty": integer(item.get("qty"), 1),
        "note": text(item.get("note")),
    }


NORMALIZERS = {
    "aspects": normalized_aspect,
    "skills": normalized_skill,
    "stunts": normalized_stunt,
    "stress": normalized_stress,
    "consequences": normalized_consequence,
    "extras": normalized_extra,
    "inventory": normalized_inventory,
}


def normalized_box(box: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "value": integer(box.get("value")),
        "checked": box.get("checked") is True,
    }


def boxes(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [box for box in value if isinstance(box, Mapping)]


def text(value: Any) -> str:
    return "" if value is None else str(value)


def integer(value: Any, default: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return value


def optional_integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def plain(node: Any) -> Any:
    if isinstance(node, Mapping):
        return {str(key): plain(value) for key, value in node.items()}
    if isinstance(node, list):
        return [plain(item) for item in node]
    return node


def _mapping(data: Any) -> Mapping[str, Any]:
    return data if isinstance(data, Mapping) else {}


def render(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if not isinstance(value, Mapping | list):
        return str(value)
    return dump_plain_yaml(plain(value))
