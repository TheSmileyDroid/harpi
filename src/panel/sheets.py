from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from io import StringIO
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.error import YAMLError

SHEET_TAG = "harpi-sheet"
CONFIG_TAG = "harpi-campaign"

SHEET_KEYS = frozenset({
    "refresh",
    "fate_points",
    "aspects",
    "skills",
    "stunts",
    "stress",
    "consequences",
    "extras",
    "inventory",
})

DEFAULT_LADDER = (
    (4, "Ótimo"),
    (3, "Bom"),
    (2, "Razoável"),
    (1, "Regular"),
    (0, "Medíocre"),
    (-1, "Ruim"),
    (-2, "Terrível"),
)
DEFAULT_ASPECTS = ("Conceito", "Problema", "Aspecto", "Aspecto", "Aspecto")
DEFAULT_REFRESH = 3


class SheetError(ValueError):
    pass


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def decode_text(data: bytes) -> str:
    return data.decode("utf-8-sig")


@dataclass(frozen=True, slots=True)
class LadderStep:
    rank: int
    label: str


@dataclass(frozen=True, slots=True)
class TrackSpec:
    track: str
    boxes: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ConsequenceSlot:
    severity: str
    value: int


@dataclass(frozen=True, slots=True)
class CampaignConfig:
    name: str
    system: str
    ladder: tuple[LadderStep, ...]
    skills: tuple[str, ...]
    aspects: tuple[str, ...]
    stress: tuple[TrackSpec, ...]
    consequences: tuple[ConsequenceSlot, ...]
    refresh: int
    extras: tuple[str, ...]

    def rank_label(self, rank: int) -> str:
        for step in self.ladder:
            if step.rank == rank:
                return step.label
        raise SheetError(f"rank fora da escada: {rank}")

    def knows_rank(self, rank: int) -> bool:
        return any(step.rank == rank for step in self.ladder)


@dataclass(frozen=True, slots=True)
class LoadedSheet:
    document: CommentedMap | None
    error: str | None


@dataclass(frozen=True, slots=True)
class Aspect:
    label: str
    text: str


@dataclass(frozen=True, slots=True)
class Skill:
    name: str
    rank: int


@dataclass(frozen=True, slots=True)
class Stunt:
    name: str
    text: str
    refresh_cost: int


@dataclass(frozen=True, slots=True)
class StressBox:
    value: int
    checked: bool


@dataclass(frozen=True, slots=True)
class StressTrack:
    track: str
    boxes: tuple[StressBox, ...]


@dataclass(frozen=True, slots=True)
class Consequence:
    severity: str
    value: int
    text: str


@dataclass(frozen=True, slots=True)
class Extra:
    kind: str
    name: str
    text: str
    cost: int | None


@dataclass(frozen=True, slots=True)
class InventoryEntry:
    item: str
    qty: int
    note: str


@dataclass(frozen=True, slots=True)
class SheetBlock:
    refresh: int
    fate_points: int
    aspects: tuple[Aspect, ...]
    skills: tuple[Skill, ...]
    stunts: tuple[Stunt, ...]
    stress: tuple[StressTrack, ...]
    consequences: tuple[Consequence, ...]
    extras: tuple[Extra, ...]
    inventory: tuple[InventoryEntry, ...]
    unknown: dict[str, Any]
    document: CommentedMap


def default_config() -> CampaignConfig:
    return CampaignConfig(
        name="",
        system="fate",
        ladder=tuple(
            LadderStep(rank, label) for rank, label in DEFAULT_LADDER
        ),
        skills=(),
        aspects=DEFAULT_ASPECTS,
        stress=(
            TrackSpec("Físico", (1, 2, 3)),
            TrackSpec("Mental", (1, 2)),
        ),
        consequences=(
            ConsequenceSlot("Leve", 2),
            ConsequenceSlot("Moderada", 4),
            ConsequenceSlot("Severa", 6),
        ),
        refresh=DEFAULT_REFRESH,
        extras=(),
    )


def _block(text: str, tag: str) -> str | None:
    pattern = re.compile(
        rf"^[ \t]*```{re.escape(tag)}[ \t]*\r?\n(?P<body>.*?)"
        r"^[ \t]*```[ \t]*\r?$",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    return None if match is None else match.group("body")


def _yaml() -> YAML:
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.width = 4096
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml


def _load_yaml(body: str) -> CommentedMap | str:
    try:
        document = _yaml().load(body)
    except YAMLError as error:
        return _yaml_error_message(error)
    if not isinstance(document, CommentedMap):
        return "o bloco não é um mapa YAML"
    return document


def _yaml_error_message(error: YAMLError) -> str:
    text = str(error).strip().splitlines()
    return "YAML inválido: " + (text[0] if text else "não foi possível ler")


def load_sheet(text: str) -> LoadedSheet:
    body = _block(text, SHEET_TAG)
    if body is None:
        return LoadedSheet(None, "bloco harpi-sheet ausente")
    loaded = _load_yaml(body)
    if isinstance(loaded, str):
        return LoadedSheet(None, loaded)
    return LoadedSheet(loaded, None)


def dump_block(document: CommentedMap) -> str:
    stream = StringIO()
    _yaml().dump(document, stream)
    return stream.getvalue()


def yaml_scalar(value: str) -> str:
    stream = StringIO()
    _yaml().dump(value, stream)
    lines = stream.getvalue().strip().splitlines()
    if lines and lines[-1] == "...":
        lines.pop()
    return " ".join(lines).strip()


def canonical_prose(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cleaned = [line.rstrip() for line in lines]
    while cleaned and not cleaned[0]:
        cleaned.pop(0)
    while cleaned and not cleaned[-1]:
        cleaned.pop()
    return "\n".join(cleaned)


def major_heading(line: str) -> bool:
    return bool(re.match(r"^#{1,2}[ \t]", line))


def content_lines(lines: Sequence[str]) -> Iterator[tuple[int, str]]:
    in_fence = False
    in_block = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if in_block:
            if stripped.startswith("```"):
                in_block = False
            continue
        if stripped == f"```{SHEET_TAG}":
            in_block = True
            continue
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield index, line


def section_count(lines: Sequence[str], heading: str) -> int:
    return sum(
        1 for _, line in content_lines(lines) if line.strip() == heading
    )


def section_bounds(
    lines: Sequence[str], heading: str
) -> tuple[int, int] | None:
    start = next(
        (
            index
            for index, line in content_lines(lines)
            if line.strip() == heading
        ),
        None,
    )
    if start is None:
        return None
    return start, section_end(lines, start + 1)


def section_end(lines: Sequence[str], offset: int) -> int:
    in_fence = False
    while offset < len(lines):
        stripped = lines[offset].strip()
        if stripped == f"```{SHEET_TAG}":
            return offset
        if stripped.startswith("```"):
            in_fence = not in_fence
        elif not in_fence and major_heading(lines[offset]):
            return offset
        offset += 1
    return offset


def section_text(lines: Sequence[str], heading: str) -> str:
    bounds = section_bounds(lines, heading)
    if bounds is None:
        return ""
    start, end = bounds
    return "".join(lines[start + 1 : end]).strip("\r\n")


def prose_sections(text: str) -> tuple[str, str]:
    lines = text.splitlines(keepends=True)
    return section_text(lines, "## História"), section_text(
        lines, "## Anotações"
    )


def parse_config(text: str) -> CampaignConfig | None:
    body = _block(text, CONFIG_TAG)
    if body is None:
        return None
    loaded = _load_yaml(body)
    if isinstance(loaded, str):
        return None
    try:
        return _read_config(loaded)
    except SheetError:
        return None


def _read_config(document: CommentedMap) -> CampaignConfig:
    base = default_config()
    return CampaignConfig(
        name=_scalar(document.get("name"), "") or "",
        system=_scalar(document.get("system"), "") or "fate",
        ladder=_pick(document, "ladder", base.ladder, _ladder),
        skills=_pick(document, "skills", base.skills, _labels),
        aspects=_pick(document, "aspects", base.aspects, _labels),
        stress=_pick(document, "stress", base.stress, _track_specs),
        consequences=_pick(
            document, "consequences", base.consequences, _slot_specs
        ),
        refresh=_integer(document.get("refresh"), base.refresh),
        extras=_pick(document, "extras", base.extras, _labels),
    )


def _pick(
    document: CommentedMap,
    key: str,
    fallback: Any,
    reader: Callable[[Any], Any],
) -> Any:
    value = document.get(key)
    return fallback if value is None else reader(value)


def _ladder(value: Any) -> tuple[LadderStep, ...]:
    steps = tuple(
        LadderStep(
            rank=_integer(item.get("rank"), 0),
            label=_required(item.get("label"), "rótulo da escada"),
        )
        for item in _maps(value, "ladder")
    )
    if not steps:
        raise SheetError("a escada da campanha está vazia")
    ranks = [step.rank for step in steps]
    if len(set(ranks)) != len(ranks):
        raise SheetError("a escada da campanha tem ranks duplicados")
    return steps


def _track_specs(value: Any) -> tuple[TrackSpec, ...]:
    return tuple(
        TrackSpec(
            track=_required(item.get("track"), "trilha de estresse"),
            boxes=_integers(item.get("boxes"), "caixas da trilha"),
        )
        for item in _maps(value, "stress")
    )


def _slot_specs(value: Any) -> tuple[ConsequenceSlot, ...]:
    return tuple(
        ConsequenceSlot(
            severity=_required(item.get("severity"), "severidade"),
            value=_integer(item.get("value"), 0),
        )
        for item in _maps(value, "consequences")
    )


def _labels(value: Any) -> tuple[str, ...]:
    return tuple(
        _required(item, "rótulo")
        for item in _sequence(value, "rótulos")
        if _present(item)
    )


def _integers(value: Any, name: str) -> tuple[int, ...]:
    return tuple(_integer(item, 0) for item in _sequence(value, name))


def read_sheet(loaded: LoadedSheet, config: CampaignConfig) -> SheetBlock:
    document = loaded.document
    if document is None:
        raise SheetError(loaded.error or "bloco harpi-sheet ausente")
    return SheetBlock(
        refresh=_integer(document.get("refresh"), config.refresh),
        fate_points=_integer(document.get("fate_points"), 0),
        aspects=_aspects(document.get("aspects"), config),
        skills=_skills(document.get("skills"), config),
        stunts=_stunts(document.get("stunts")),
        stress=_stress(document.get("stress"), config),
        consequences=_consequences(document.get("consequences"), config),
        extras=_extras(document.get("extras"), config),
        inventory=_inventory(document.get("inventory")),
        unknown={
            str(key): value
            for key, value in document.items()
            if str(key) not in SHEET_KEYS
        },
        document=document,
    )


def _aspects(value: Any, config: CampaignConfig) -> tuple[Aspect, ...]:
    if value is None:
        return tuple(Aspect(label=label, text="") for label in config.aspects)
    return tuple(
        Aspect(
            label=_required(item.get("label"), "rótulo do aspecto"),
            text=_scalar(item.get("text"), "") or "",
        )
        for item in _maps(value, "aspects")
    )


def _skills(value: Any, config: CampaignConfig) -> tuple[Skill, ...]:
    known = frozenset(name.casefold() for name in config.skills)
    seen: set[str] = set()
    skills: list[Skill] = []
    for item in _maps(value, "skills"):
        name = _required(item.get("name"), "nome da perícia")
        rank = _integer(item.get("rank"), 0)
        if not config.knows_rank(rank):
            raise SheetError(f"rank fora da escada: {name} ({rank})")
        if rank < 1:
            raise SheetError(f"perícia com rank menor que 1: {name}")
        key = name.casefold()
        if known and key not in known:
            raise SheetError(f"perícia fora da config: {name}")
        if key in seen:
            raise SheetError(f"perícia duplicada: {name}")
        seen.add(key)
        skills.append(Skill(name=name, rank=rank))
    return tuple(skills)


def _stunts(value: Any) -> tuple[Stunt, ...]:
    return tuple(
        Stunt(
            name=_required(item.get("name"), "nome da façanha"),
            text=_scalar(item.get("text"), "") or "",
            refresh_cost=_integer(item.get("refresh_cost"), 0),
        )
        for item in _maps(value, "stunts")
    )


def _stress(value: Any, config: CampaignConfig) -> tuple[StressTrack, ...]:
    tracks = {track.track: track for track in config.stress}
    seen: set[str] = set()
    result: list[StressTrack] = []
    for item in _maps(value, "stress"):
        track = _required(item.get("track"), "trilha de estresse")
        if track not in tracks:
            raise SheetError(f"trilha de estresse desconhecida: {track}")
        if track in seen:
            raise SheetError(f"trilha de estresse duplicada: {track}")
        seen.add(track)
        boxes = _boxes(item.get("boxes"))
        _check_boxes(track, boxes, tracks[track].boxes)
        result.append(StressTrack(track=track, boxes=boxes))
    return tuple(result)


def _check_boxes(
    track: str, boxes: tuple[StressBox, ...], allowed: tuple[int, ...]
) -> None:
    values = [box.value for box in boxes]
    if len(values) > len(allowed):
        raise SheetError(f"trilha de estresse com caixas demais: {track}")
    if len(set(values)) != len(values):
        raise SheetError(f"trilha de estresse com caixas duplicadas: {track}")
    if any(value not in allowed for value in values):
        raise SheetError(f"trilha de estresse fora da config: {track}")


def _boxes(value: Any) -> tuple[StressBox, ...]:
    return tuple(
        StressBox(
            value=_integer(item.get("value"), 0),
            checked=_boolean(item.get("checked"), False),
        )
        for item in _maps(value, "boxes")
    )


def _consequences(
    value: Any, config: CampaignConfig
) -> tuple[Consequence, ...]:
    slots = {slot.severity: slot.value for slot in config.consequences}
    seen: set[str] = set()
    result: list[Consequence] = []
    for item in _maps(value, "consequences"):
        severity = _required(item.get("severity"), "severidade")
        if severity not in slots:
            raise SheetError(f"slot de consequência desconhecido: {severity}")
        if severity in seen:
            raise SheetError(f"slot de consequência duplicado: {severity}")
        seen.add(severity)
        value = _integer(item.get("value"), slots[severity])
        if value != slots[severity]:
            raise SheetError(f"valor da consequência fora do slot: {severity}")
        result.append(
            Consequence(
                severity=severity,
                value=slots[severity],
                text=_scalar(item.get("text"), "") or "",
            )
        )
    return tuple(result)


def _extras(value: Any, config: CampaignConfig) -> tuple[Extra, ...]:
    kinds = frozenset(kind.casefold() for kind in config.extras)
    result: list[Extra] = []
    for item in _maps(value, "extras"):
        kind = _required(item.get("kind"), "tipo do extra")
        if kinds and kind.casefold() not in kinds:
            raise SheetError(f"extra fora da config: {kind}")
        result.append(
            Extra(
                kind=kind,
                name=_scalar(item.get("name"), "") or "",
                text=_scalar(item.get("text"), "") or "",
                cost=_optional_integer(item.get("cost")),
            )
        )
    return tuple(result)


def _inventory(value: Any) -> tuple[InventoryEntry, ...]:
    return tuple(
        InventoryEntry(
            item=_required(item.get("item"), "item do inventário"),
            qty=_integer(item.get("qty"), 1),
            note=_scalar(item.get("note"), "") or "",
        )
        for item in _maps(value, "inventory")
    )


def _sequence(value: Any, name: str) -> tuple[Any, ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        raise SheetError(f"{name} precisa ser uma lista")
    return tuple(value)


def _maps(value: Any, name: str) -> tuple[Mapping[str, Any], ...]:
    result: list[Mapping[str, Any]] = []
    for item in _sequence(value, name):
        if not isinstance(item, Mapping):
            raise SheetError(f"{name} tem um item que não é um mapa")
        result.append(item)
    return tuple(result)


def _present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _required(value: Any, name: str) -> str:
    text = _scalar(value, "")
    if text is None or text.strip() == "":
        raise SheetError(f"{name} em branco")
    return text.strip()


def _scalar(value: Any, default: str | None) -> str | None:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, str | int | float):
        raise SheetError("valor de texto inválido")
    return str(value)


def _integer(value: Any, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise SheetError("valor inteiro inválido")
    return value


def _optional_integer(value: Any) -> int | None:
    return None if value is None else _integer(value, 0)


def _boolean(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise SheetError("valor booleano inválido")
    return value
