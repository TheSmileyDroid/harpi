from __future__ import annotations

import hashlib
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
            item.model_copy(update={"id": zone_id, "label": label})
        )
    return normalized


def _zone_identity(item: SceneZone) -> str:
    return item.id.strip() or f"zon_{secrets.token_hex(6)}"


def _leaves_map(item: SceneZone, columns: int, rows: int) -> bool:
    return any(
        rect.x + rect.w > columns or rect.y + rect.h > rows
        for rect in item.rects
    )


def write_new(root: Path, campaign: str, slug: str, text: str) -> None:
    path = scene_file(root, campaign, slug)
    with write_lock():
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise SceneExists("A scene with this name already exists")
        atomic_write(path, text)


def save_existing(
    root: Path, campaign: str, slug: str, payload: SceneSave
) -> tuple[SceneBlueprint, str, str]:
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
        try:
            atomic_write_guarded(
                path,
                canonical_text(updated),
                lambda: _unchanged(path, payload.base_hash),
            )
        except WriteConflict as failure:
            raise SceneConflict("The scene changed on disk") from failure
    return updated, blueprint_hash(updated), canonical_text(current)


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
