from __future__ import annotations

import hashlib
import html
import json
import math
import re
import secrets
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from PIL import Image
from pydantic import ValidationError

from src.panel.schemas import (
    SceneBlueprint,
    SceneCreate,
    SceneDetail,
    SceneGrid,
    SceneImage,
    SceneRect,
    SceneSave,
    SceneSource,
    SceneSummary,
    SceneZone,
)
from src.panel.vault_index import ASSETS_FOLDER, CAMPAIGN_ROOT, VaultIndex
from src.panel.vault_write import (
    WriteConflict,
    atomic_write,
    atomic_write_guarded,
    write_lock,
)
from src.storage.database import Database

SCENES_FOLDER = "scenes"
SCENE_SLUG_LENGTH = 64
SLUG_PATTERN = re.compile(rf"^[a-z0-9][a-z0-9-]{{0,{SCENE_SLUG_LENGTH - 1}}}$")
DEFAULT_CELL_PX = 70
DEFAULT_IMAGE_WIDTH = 1920
DEFAULT_IMAGE_HEIGHT = 1080
DEFAULT_GRID = SceneGrid(
    cell_px=DEFAULT_CELL_PX, offset_x=0, offset_y=0, visible=True
)
SUNKEN = "#0d0b08"
PLATE = "#1f1b15"
RULE_STRONG = "#3d3527"
SAND = "#e9dfc7"
SVG_STROKE_WIDTH = 2


class SceneError(Exception):
    pass


class InvalidSceneName(SceneError):
    pass


class InvalidSceneImage(SceneError):
    pass


class InvalidSceneZones(SceneError):
    pass


class SceneExists(SceneError):
    pass


class SceneConflict(SceneError):
    pass


class SceneMissing(SceneError):
    pass


@dataclass(frozen=True, slots=True)
class SavedScene:
    blueprint: SceneBlueprint
    digest: str
    previous_text: str
    previous_map: str | None


@dataclass(frozen=True, slots=True)
class SceneRecord:
    id: str
    campaign: str
    name: str
    source: SceneSource
    blueprint_path: str
    blueprint_hash: str
    image_path: str
    image_width: int
    image_height: int
    zones_json: str
    rev: int


def scene_slug(name: str) -> str:
    ascii_name = (
        unicodedata
        .normalize("NFKD", name)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.casefold()).strip("-")
    slug = slug[:SCENE_SLUG_LENGTH].strip("-")
    if not slug:
        raise InvalidSceneName("The scene name has no usable letters")
    return slug


def valid_scene_slug(slug: str) -> bool:
    return SLUG_PATTERN.fullmatch(slug) is not None


def blueprint_path(campaign: str, slug: str) -> str:
    return "/".join((*CAMPAIGN_ROOT, campaign, SCENES_FOLDER, f"{slug}.json"))


def sketch_image_path(campaign: str, slug: str) -> str:
    return "/".join((
        *CAMPAIGN_ROOT,
        campaign,
        ASSETS_FOLDER,
        f"{slug}-map.svg",
    ))


def canonical_json(blueprint: SceneBlueprint) -> str:
    data = blueprint.model_dump(mode="json")
    return json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def canonical_text(blueprint: SceneBlueprint) -> str:
    return f"{canonical_json(blueprint)}\n"


def blueprint_hash(blueprint: SceneBlueprint) -> str:
    return hashlib.sha256(
        canonical_json(blueprint).encode("utf-8")
    ).hexdigest()


_BLUEPRINT_CACHE: dict[tuple[str, int, int], SceneBlueprint | None] = {}
_CACHE_LIMIT = 256


def load_blueprint(path: Path) -> SceneBlueprint | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    key = (str(path), stat.st_mtime_ns, stat.st_size)
    if key in _BLUEPRINT_CACHE:
        return _BLUEPRINT_CACHE[key]
    blueprint = _parse_blueprint(path)
    if len(_BLUEPRINT_CACHE) >= _CACHE_LIMIT:
        _BLUEPRINT_CACHE.clear()
    _BLUEPRINT_CACHE[key] = blueprint
    return blueprint


def _parse_blueprint(path: Path) -> SceneBlueprint | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return SceneBlueprint.model_validate(data)
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValidationError,
    ):
        return None


def scene_file(root: Path, campaign: str, slug: str) -> Path:
    return root / blueprint_path(campaign, slug)


def build_blueprint(
    index: VaultIndex, campaign: str, payload: SceneCreate
) -> SceneBlueprint:
    slug = scene_slug(payload.name)
    image = _scene_image(index, campaign, slug, payload)
    grid = payload.grid or DEFAULT_GRID
    return SceneBlueprint(
        slug=slug,
        name=payload.name,
        source=payload.source,
        image=image,
        grid=grid,
        fog_outside=payload.fog_outside,
        zones=normalized_zones(payload.zones, image.width, image.height, grid),
    )


def _scene_image(
    index: VaultIndex, campaign: str, slug: str, payload: SceneCreate
) -> SceneImage:
    if payload.source == "sketch":
        return SceneImage(
            path=sketch_image_path(campaign, slug),
            width=payload.image_width or DEFAULT_IMAGE_WIDTH,
            height=payload.image_height or DEFAULT_IMAGE_HEIGHT,
        )
    source = _resolved_image(index, campaign, payload.image)
    width, height = _image_size(source)
    return SceneImage(
        path=_relative_to_root(index.root, source),
        width=width,
        height=height,
    )


def _resolved_image(
    index: VaultIndex, campaign: str, reference: str | None
) -> Path:
    path = None if not reference else index.portrait_path(reference)
    if path is None:
        raise InvalidSceneImage("The scene image is not in the vault")
    owner = index.campaign_of(path)
    if owner is not None and owner != campaign:
        raise InvalidSceneImage("The scene image is not in the campaign")
    return path


def _image_size(path: Path) -> tuple[int, int]:
    try:
        with Image.open(path) as image:
            width, height = image.size
    except (OSError, ValueError, Image.DecompressionBombError) as failure:
        raise InvalidSceneImage("The scene image cannot be read") from failure
    if width < 1 or height < 1:
        raise InvalidSceneImage("The scene image has no area")
    return width, height


def _relative_to_root(root: Path | None, path: Path) -> str:
    if root is None:
        raise InvalidSceneImage("The scene image is not in the vault")
    try:
        return path.relative_to(root.resolve()).as_posix()
    except ValueError as failure:
        raise InvalidSceneImage("The scene image left the vault") from failure


def normalized_zones(
    zones: list[SceneZone], width: int, height: int, grid: SceneGrid
) -> list[SceneZone]:
    columns = math.ceil(max(0, width - grid.offset_x) / grid.cell_px)
    rows = math.ceil(max(0, height - grid.offset_y) / grid.cell_px)
    seen: set[str] = set()
    normalized: list[SceneZone] = []
    for item in zones:
        label = item.label.strip()
        if not label:
            raise InvalidSceneZones("A zone needs a label")
        zone_id = _zone_identity(item)
        if zone_id in seen:
            raise InvalidSceneZones("Zone ids must be unique")
        if _leaves_map(item, columns, rows):
            raise InvalidSceneZones("A zone rectangle leaves the map")
        seen.add(zone_id)
        normalized.append(
            item.model_copy(
                update={
                    "id": zone_id,
                    "label": label,
                    "rects": normalize_rects(item.rects),
                }
            )
        )
    return normalized


def normalize_rects(rects: list[SceneRect]) -> list[SceneRect]:
    xs = _horizontal_bounds(rects)
    ys = _vertical_bounds(rects)
    if len(xs) < 2 or len(ys) < 2:
        return []
    covered = _covered_cells(xs, ys, rects)
    result: list[SceneRect] = []
    active: dict[tuple[int, int], SceneRect] = {}
    for row in range(len(ys) - 1):
        next_active: dict[tuple[int, int], SceneRect] = {}
        for first, last in _covered_runs(xs, row, covered):
            key = (xs[first], xs[last + 1])
            previous = active.get(key)
            height = ys[row + 1] - ys[row]
            if previous is not None:
                previous.h += height
                next_active[key] = previous
                continue
            rect = SceneRect(x=key[0], y=ys[row], w=key[1] - key[0], h=height)
            result.append(rect)
            next_active[key] = rect
        active = next_active
    return result


def _covered_runs(
    xs: list[int], row: int, covered: set[tuple[int, int]]
) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for column in range(len(xs) - 1):
        filled = (column, row) in covered
        if filled and start is None:
            start = column
        if not filled and start is not None:
            runs.append((start, column - 1))
            start = None
    if start is not None:
        runs.append((start, len(xs) - 2))
    return runs


def _zone_identity(item: SceneZone) -> str:
    return item.id.strip() or f"zon_{secrets.token_hex(6)}"


def _leaves_map(item: SceneZone, columns: int, rows: int) -> bool:
    return any(
        rect.x + rect.w > columns or rect.y + rect.h > rows
        for rect in item.rects
    )


def map_svg(blueprint: SceneBlueprint) -> str:
    image = blueprint.image
    paths = "".join(
        f'<path d="{_zone_path(zone, blueprint.grid)}"/>'
        for zone in blueprint.zones
    )
    labels = "".join(
        _zone_label(zone, blueprint.grid) for zone in blueprint.zones
    )
    font_size = max(11, blueprint.grid.cell_px // 3)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{image.width}" '
        f'height="{image.height}" viewBox="0 0 {image.width} '
        f'{image.height}">\n'
        f'<rect width="{image.width}" height="{image.height}" '
        f'fill="{SUNKEN}"/>\n'
        f'<g fill="{PLATE}" stroke="{RULE_STRONG}" '
        f'stroke-width="{SVG_STROKE_WIDTH}" fill-rule="evenodd">\n'
        f"{paths}\n"
        "</g>\n"
        f'<g font-family="Barlow, sans-serif" font-size="{font_size}" '
        f'font-weight="600" fill="{SAND}" stroke="{SUNKEN}" '
        'stroke-width="3" paint-order="stroke" text-anchor="middle" '
        f'dominant-baseline="middle">\n{labels}\n</g>\n'
        "</svg>\n"
    )


def _zone_label(zone: SceneZone, grid: SceneGrid) -> str:
    left = min(rect.x for rect in zone.rects)
    top = min(rect.y for rect in zone.rects)
    right = max(rect.x + rect.w for rect in zone.rects)
    bottom = max(rect.y + rect.h for rect in zone.rects)
    x = ((left + right) * grid.cell_px) // 2 + grid.offset_x
    y = ((top + bottom) * grid.cell_px) // 2 + grid.offset_y
    return (
        f'<text x="{x}" y="{y}">{html.escape(zone.label, quote=True)}</text>'
    )


def _zone_path(zone: SceneZone, grid: SceneGrid) -> str:
    loops = _contour_loops(zone.rects)
    return " ".join(_loop_path(loop, grid) for loop in loops)


def _contour_loops(rects: list[SceneRect]) -> list[list[tuple[int, int]]]:
    xs = _horizontal_bounds(rects)
    ys = _vertical_bounds(rects)
    covered = _covered_cells(xs, ys, rects)
    return _trace_loops(_boundary_edges(xs, ys, covered))


def _horizontal_bounds(rects: list[SceneRect]) -> list[int]:
    return sorted({
        value for rect in rects for value in (rect.x, rect.x + rect.w)
    })


def _vertical_bounds(rects: list[SceneRect]) -> list[int]:
    return sorted({
        value for rect in rects for value in (rect.y, rect.y + rect.h)
    })


def _covered_cells(
    xs: list[int], ys: list[int], rects: list[SceneRect]
) -> set[tuple[int, int]]:
    return {
        (index, row)
        for index in range(len(xs) - 1)
        for row in range(len(ys) - 1)
        if _covers(rects, xs, ys, index, row)
    }


def _covers(
    rects: list[SceneRect],
    xs: list[int],
    ys: list[int],
    index: int,
    row: int,
) -> bool:
    left, right = xs[index], xs[index + 1]
    top, bottom = ys[row], ys[row + 1]
    return any(
        rect.x <= left
        and right <= rect.x + rect.w
        and rect.y <= top
        and bottom <= rect.y + rect.h
        for rect in rects
    )


def _boundary_edges(
    xs: list[int], ys: list[int], covered: set[tuple[int, int]]
) -> set[tuple[tuple[int, int], tuple[int, int]]]:
    edges: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    for index, row in covered:
        left, right = xs[index], xs[index + 1]
        top, bottom = ys[row], ys[row + 1]
        edges.add(((left, top), (right, top)))
        edges.add(((right, top), (right, bottom)))
        edges.add(((right, bottom), (left, bottom)))
        edges.add(((left, bottom), (left, top)))
    return {edge for edge in edges if (edge[1], edge[0]) not in edges}


def _trace_loops(
    edges: set[tuple[tuple[int, int], tuple[int, int]]],
) -> list[list[tuple[int, int]]]:
    outgoing: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for start, end in sorted(edges, key=lambda edge: (edge[0][::-1], edge[1])):
        outgoing.setdefault(start, []).append(end)
    loops: list[list[tuple[int, int]]] = []
    for start in sorted(outgoing, key=lambda point: (point[1], point[0])):
        while outgoing.get(start):
            loops.append(_walk(start, outgoing))
    return loops


def _walk(
    start: tuple[int, int],
    outgoing: dict[tuple[int, int], list[tuple[int, int]]],
) -> list[tuple[int, int]]:
    loop = [start]
    current = start
    while True:
        ends = outgoing.get(current)
        if not ends:
            return loop
        following = ends.pop(0)
        if not ends:
            del outgoing[current]
        loop.append(following)
        current = following
        if current == start:
            return _simplified(loop)


def _simplified(loop: list[tuple[int, int]]) -> list[tuple[int, int]]:
    points = loop[:-1] if loop[0] == loop[-1] else loop
    if len(points) < 3:
        return loop
    kept: list[tuple[int, int]] = []
    for index, point in enumerate(points):
        before = points[index - 1]
        after = points[(index + 1) % len(points)]
        if _collinear(before, point, after):
            continue
        kept.append(point)
    return kept


def _collinear(
    before: tuple[int, int],
    point: tuple[int, int],
    after: tuple[int, int],
) -> bool:
    return (point[0] - before[0]) * (after[1] - point[1]) == (
        point[1] - before[1]
    ) * (after[0] - point[0])


def _loop_path(loop: list[tuple[int, int]], grid: SceneGrid) -> str:
    points = [
        (
            x * grid.cell_px + grid.offset_x,
            y * grid.cell_px + grid.offset_y,
        )
        for x, y in loop
    ]
    head, *tail = points
    commands = [f"M {head[0]} {head[1]}"]
    commands.extend(f"L {x} {y}" for x, y in tail)
    commands.append("Z")
    return " ".join(commands)


def read_map_svg(root: Path, campaign: str, slug: str) -> str | None:
    path = root / sketch_image_path(campaign, slug)
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def write_map_svg(
    root: Path, campaign: str, slug: str, blueprint: SceneBlueprint
) -> None:
    path = root / sketch_image_path(campaign, slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, map_svg(blueprint))


def restore_map_svg(
    root: Path, campaign: str, slug: str, text: str | None
) -> None:
    path = root / sketch_image_path(campaign, slug)
    if text is None:
        path.unlink(missing_ok=True)
        return
    atomic_write(path, text)


def write_new(root: Path, campaign: str, slug: str, text: str) -> None:
    path = scene_file(root, campaign, slug)
    with write_lock():
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise SceneExists("A scene with this name already exists")
        atomic_write(path, text)


def save_existing(
    root: Path, campaign: str, slug: str, payload: SceneSave
) -> SavedScene:
    path = scene_file(root, campaign, slug)
    with write_lock():
        current = load_blueprint(path)
        if current is None:
            raise SceneMissing("The scene file is not readable")
        if blueprint_hash(current) != payload.base_hash:
            raise SceneConflict("The scene changed on disk")
        updated = current.model_copy(
            update={
                "slug": slug,
                "name": payload.name,
                "grid": payload.grid,
                "fog_outside": payload.fog_outside,
                "zones": normalized_zones(
                    payload.zones,
                    current.image.width,
                    current.image.height,
                    payload.grid,
                ),
            }
        )
        previous_text = canonical_text(current)
        previous_map = None
        if updated.source == "sketch":
            previous_map = read_map_svg(root, campaign, slug)
        try:
            atomic_write_guarded(
                path,
                canonical_text(updated),
                lambda: _unchanged(path, payload.base_hash),
            )
        except WriteConflict as failure:
            raise SceneConflict("The scene changed on disk") from failure
        _write_sketch_map(root, campaign, slug, updated, path, previous_text)
    return SavedScene(
        blueprint=updated,
        digest=blueprint_hash(updated),
        previous_text=previous_text,
        previous_map=previous_map,
    )


def _write_sketch_map(
    root: Path,
    campaign: str,
    slug: str,
    blueprint: SceneBlueprint,
    blueprint_file: Path,
    previous_text: str,
) -> None:
    if blueprint.source != "sketch":
        return
    try:
        write_map_svg(root, campaign, slug, blueprint)
    except OSError:
        atomic_write(blueprint_file, previous_text)
        raise


def _unchanged(path: Path, base_hash: str) -> bool:
    current = load_blueprint(path)
    return current is not None and blueprint_hash(current) == base_hash


def restore_file(root: Path, campaign: str, slug: str, text: str) -> None:
    with write_lock():
        atomic_write(scene_file(root, campaign, slug), text)


def adopt_existing(root: Path, campaign: str, slug: str) -> SceneBlueprint:
    blueprint = load_blueprint(scene_file(root, campaign, slug))
    if blueprint is None or blueprint.slug != slug:
        raise SceneMissing("The scene file is not readable")
    return blueprint


async def store_new(
    database: Database,
    campaign: str,
    blueprint: SceneBlueprint,
    digest: str,
) -> None:
    now = int(time.time())
    grid_json, zones_json = _grid_zones(blueprint)
    await database.execute(
        "INSERT INTO scenes ("
        "id, campaign_slug, name, source, blueprint_path, blueprint_hash, "
        "image_path, image_width, image_height, grid_json, zones_json, "
        "fog_outside, rev, created_at, updated_at"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
        (
            f"scn_{secrets.token_hex(12)}",
            campaign,
            blueprint.name,
            blueprint.source,
            blueprint_path(campaign, blueprint.slug),
            digest,
            blueprint.image.path,
            blueprint.image.width,
            blueprint.image.height,
            grid_json,
            zones_json,
            int(blueprint.fog_outside),
            now,
            now,
        ),
    )


async def store_save(
    database: Database,
    campaign: str,
    blueprint: SceneBlueprint,
    digest: str,
) -> None:
    grid_json, zones_json = _grid_zones(blueprint)
    await database.execute(
        "UPDATE scenes SET name = ?, blueprint_hash = ?, grid_json = ?, "
        "zones_json = ?, fog_outside = ?, rev = rev + 1, updated_at = ? "
        "WHERE campaign_slug = ? AND blueprint_path = ?",
        (
            blueprint.name,
            digest,
            grid_json,
            zones_json,
            int(blueprint.fog_outside),
            int(time.time()),
            campaign,
            blueprint_path(campaign, blueprint.slug),
        ),
    )


def _grid_zones(blueprint: SceneBlueprint) -> tuple[str, str]:
    grid = _json_text(blueprint.grid.model_dump(mode="json"))
    zones = _json_text([
        zone.model_dump(mode="json") for zone in blueprint.zones
    ])
    return grid, zones


def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


async def scene_rows(database: Database, campaign: str) -> list[SceneRecord]:
    rows = await database.fetchall(
        "SELECT id, campaign_slug, name, source, blueprint_path, "
        "blueprint_hash, image_path, image_width, image_height, zones_json, "
        "rev FROM scenes "
        "WHERE campaign_slug = ? ORDER BY name, blueprint_path",
        (campaign,),
    )
    return [_record(row) for row in rows]


async def scene_record(
    database: Database, campaign: str, slug: str
) -> SceneRecord | None:
    row = await database.fetchone(
        "SELECT id, campaign_slug, name, source, blueprint_path, "
        "blueprint_hash, image_path, image_width, image_height, zones_json, "
        "rev FROM scenes "
        "WHERE campaign_slug = ? AND blueprint_path = ?",
        (campaign, blueprint_path(campaign, slug)),
    )
    return None if row is None else _record(row)


def _record(row) -> SceneRecord:
    return SceneRecord(
        id=row["id"],
        campaign=row["campaign_slug"],
        name=row["name"],
        source=row["source"],
        blueprint_path=row["blueprint_path"],
        blueprint_hash=row["blueprint_hash"],
        image_path=row["image_path"],
        image_width=row["image_width"],
        image_height=row["image_height"],
        zones_json=row["zones_json"],
        rev=row["rev"],
    )


def summary(record: SceneRecord, root: Path) -> SceneSummary:
    blueprint = load_blueprint(root / record.blueprint_path)
    source = record.source if blueprint is None else blueprint.source
    name = record.name if blueprint is None else blueprint.name
    slug = PurePosixPath(record.blueprint_path).stem
    if blueprint is None:
        width, height = record.image_width, record.image_height
        grid = DEFAULT_GRID
        zones = _stored_zones(record.zones_json)
    else:
        width, height = blueprint.image.width, blueprint.image.height
        grid = blueprint.grid
        zones = blueprint.zones
    saved = (
        blueprint is not None
        and blueprint_hash(blueprint) == record.blueprint_hash
    )
    return SceneSummary(
        slug=slug,
        name=name,
        source=source,
        thumbnail=thumbnail_url(record.campaign, slug, source),
        width=width,
        height=height,
        grid=grid,
        zones=zones,
        zone_count=len(zones),
        saved=saved,
        in_use=False,
    )


def _stored_zones(zones_json: str) -> list[SceneZone]:
    try:
        data = json.loads(zones_json)
        return [SceneZone.model_validate(item) for item in data]
    except (json.JSONDecodeError, TypeError, ValidationError):
        return []


def thumbnail_url(campaign: str, slug: str, source: SceneSource) -> str | None:
    if source == "sketch":
        return None
    return f"/api/campaigns/{campaign}/scenes/{slug}/image"


def as_detail(
    blueprint: SceneBlueprint, digest: str, *, saved: bool
) -> SceneDetail:
    return SceneDetail(**blueprint.model_dump(), hash=digest, saved=saved)


def detail(record: SceneRecord, root: Path) -> SceneDetail | None:
    blueprint = load_blueprint(root / record.blueprint_path)
    if blueprint is None:
        return None
    digest = blueprint_hash(blueprint)
    return as_detail(blueprint, digest, saved=digest == record.blueprint_hash)
