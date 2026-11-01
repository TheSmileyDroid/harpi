from __future__ import annotations

import asyncio
import hashlib
import io
import re
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import aiosqlite
from PIL import Image, ImageOps

from src.panel.vault_index import (
    ASSETS_FOLDER,
    CAMPAIGN_ROOT,
    HIDDEN_PREFIXES,
    IMAGE_SUFFIXES,
    IMAGE_TYPES,
    MAX_IMAGE_BYTES,
)
from src.panel.vault_write import atomic_write_bytes
from src.storage.database import Database

QUOTA_BYTES = 100 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
MAX_IMAGE_EDGE = 16_384
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"
RIFF_SIGNATURE = b"RIFF"
WEBP_SIGNATURE = b"WEBP"
FORMATS = {".jpg": "JPEG", ".png": "PNG", ".webp": "WEBP"}
ENCODING: dict[str, dict[str, object]] = {
    ".jpg": {"quality": 90, "optimize": True},
    ".png": {"optimize": True},
    ".webp": {"quality": 90, "method": 4},
}
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


class AssetError(Exception):
    pass


class UnsupportedImage(AssetError):
    pass


class ImageTooLarge(AssetError):
    pass


class QuotaExceeded(AssetError):
    pass


class UnsafeLocation(AssetError):
    pass


@dataclass(frozen=True, slots=True)
class SavedAsset:
    name: str
    path: str
    digest: str
    size: int
    content_type: str
    new_file: bool


def upload_folder(slug: str) -> str:
    return "/".join((*CAMPAIGN_ROOT, slug, ASSETS_FOLDER))


def valid_name(name: str) -> bool:
    return NAME_PATTERN.fullmatch(name) is not None


def valid_image_name(name: str) -> bool:
    return (
        0 < len(name) <= 128
        and "/" not in name
        and "\\" not in name
        and not name.startswith(HIDDEN_PREFIXES)
    )


def sniff(raw: bytes) -> str | None:
    if raw.startswith(PNG_SIGNATURE):
        return ".png"
    if raw.startswith(JPEG_SIGNATURE):
        return ".jpg"
    if raw.startswith(RIFF_SIGNATURE) and raw[8:12] == WEBP_SIGNATURE:
        return ".webp"
    return None


def reencode(raw: bytes, suffix: str) -> bytes:
    with Image.open(io.BytesIO(raw)) as image:
        _guard_dimensions(image)
        image.load()
        buffer = io.BytesIO()
        _raster(ImageOps.exif_transpose(image), suffix).save(
            buffer, format=FORMATS[suffix], **ENCODING[suffix]
        )
    return buffer.getvalue()


def _guard_dimensions(image: Image.Image) -> None:
    width, height = image.size
    if (
        width * height > MAX_IMAGE_PIXELS
        or max(width, height) > MAX_IMAGE_EDGE
    ):
        raise ImageTooLarge("The image dimensions are too large")


def _raster(image: Image.Image, suffix: str) -> Image.Image:
    mode = "RGBA" if suffix != ".jpg" and _has_alpha(image) else "RGB"
    return image if image.mode == mode else image.convert(mode)


def _has_alpha(image: Image.Image) -> bool:
    if image.mode in ("RGBA", "LA", "PA"):
        return True
    return image.mode == "P" and "transparency" in image.info


def _encode(raw: bytes, suffix: str) -> bytes:
    try:
        return reencode(raw, suffix)
    except ImageTooLarge:
        raise
    except Image.DecompressionBombError as failure:
        raise ImageTooLarge("The image dimensions are too large") from failure
    except (OSError, ValueError) as failure:
        raise UnsupportedImage("The image could not be decoded") from failure


async def save_upload(
    database: Database,
    root: Path,
    slug: str,
    raw: bytes,
    actor: str,
) -> SavedAsset:
    suffix = sniff(raw)
    if suffix is None:
        raise UnsupportedImage("The file is not a PNG, JPG or WebP image")
    if len(raw) > MAX_IMAGE_BYTES:
        raise ImageTooLarge("The upload is too large")
    encoded = await asyncio.to_thread(_encode, raw, suffix)
    if len(encoded) > MAX_IMAGE_BYTES:
        raise ImageTooLarge("The re-encoded image is too large")
    digest = hashlib.sha256(encoded).hexdigest()
    name = f"{digest}{suffix}"
    relative = f"{upload_folder(slug)}/{name}"
    folder = root / upload_folder(slug)
    target = _write_target(root, folder, name)
    if target is None:
        raise UnsafeLocation(f"Refusing to write {relative} outside the vault")
    new_file = not target.is_file()
    async with database.transaction() as connection:
        if new_file:
            await _require_room(connection, folder, slug, name, len(encoded))
            await asyncio.to_thread(_write, target, encoded)
        await connection.execute(
            "INSERT OR IGNORE INTO assets "
            "(campaign_slug, name, size, created_by, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (slug, name, len(encoded), actor, int(time.time())),
        )
    return SavedAsset(
        name=name,
        path=relative,
        digest=digest,
        size=len(encoded),
        content_type=IMAGE_TYPES[suffix],
        new_file=new_file,
    )


def resolve_upload(root: Path, slug: str, name: str) -> Path | None:
    if (
        not valid_name(name)
        or PurePosixPath(name).suffix.casefold() not in IMAGE_SUFFIXES
    ):
        return None
    return _inside_root(root, root / upload_folder(slug) / name)


def _write_target(root: Path, folder: Path, name: str) -> Path | None:
    try:
        resolved = (folder / name).resolve()
        resolved.relative_to(root.resolve())
    except (OSError, ValueError):
        return None
    return resolved


def _write(target: Path, data: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(target, data)


def _inside_root(root: Path, candidate: Path) -> Path | None:
    try:
        resolved = candidate.resolve()
        resolved.relative_to(root.resolve())
        if not resolved.is_file():
            return None
        if resolved.suffix.casefold() not in IMAGE_SUFFIXES:
            return None
        if resolved.stat().st_size > MAX_IMAGE_BYTES:
            return None
    except (OSError, ValueError):
        return None
    return resolved


async def registered(database: Database, slug: str, name: str) -> bool:
    row = await database.fetchone(
        "SELECT 1 FROM assets WHERE campaign_slug = ? AND name = ?",
        (slug, name),
    )
    return row is not None


async def _require_room(
    connection: aiosqlite.Connection,
    folder: Path,
    slug: str,
    name: str,
    size: int,
) -> None:
    cursor = await connection.execute(
        "SELECT name, size FROM assets WHERE campaign_slug = ? AND name <> ?",
        (slug, name),
    )
    rows = await cursor.fetchall()
    used = sum(row["size"] for row in rows if (folder / row["name"]).is_file())
    if used + size > QUOTA_BYTES:
        raise QuotaExceeded("The campaign asset quota is full")
