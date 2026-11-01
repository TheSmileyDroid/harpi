from __future__ import annotations

import asyncio
import io
import json
import os
import random
import struct
import tracemalloc
import zlib
from collections.abc import Iterable
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from PIL import Image
from quart.datastructures import FileStorage

from app import app as quart_app
from app import configure_panel_session
from pages import campaigns as campaigns_page
from src.config import Settings
from src.panel import assets, login, rate_limit, state, vault, vault_index
from src.panel.vault_index import VaultIndex
from src.storage import (
    clear_database,
    clear_registry,
    init_database,
    init_registry,
)
from src.storage.database import Database
from src.storage.registry import Actor, SqliteRegistry
from src.storage.seed import paratheos

SECRET = "test-secret"
GUILD = 734174030701264906
OTHER_GUILD = 896066642948259960
NARRATOR = "100"
PLAYER = "555"
SLUG = "paratheos"
CAMPAIGN = f"Harpi/Campaigns/{SLUG}"
ASSETS_ROUTE = f"/api/campaigns/{SLUG}/assets"
IMAGES_ROUTE = f"/api/campaigns/{SLUG}/images"
CSRF = {"Sec-Fetch-Site": "same-origin"}
PRIVATE_CACHE = "private, max-age=60, must-revalidate"


@pytest.fixture
async def world(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SECRET_KEY", SECRET)
    configure_panel_session(Settings.from_env())
    quart_app.config["TESTING"] = True
    root = tmp_path / "vault"
    root.mkdir()
    database = Database(
        tmp_path / "panel.db", campaign=paratheos(NARRATOR, str(GUILD))
    )
    await database.open()
    init_registry(SqliteRegistry(database))
    init_database(database)
    vault.configure(vault.Vault(root=root))
    vault_index.configure(VaultIndex(root))
    yield SimpleNamespace(root=root, database=database)
    clear_registry()
    clear_database()
    vault.configure(vault.Vault())
    vault_index.configure(vault_index.VaultIndex())
    await database.close()


@pytest.fixture
async def client(world):
    return quart_app.test_client()


@pytest.fixture(autouse=True)
def fresh_asset_buckets(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        campaigns_page,
        "ASSET_UPLOAD_BUCKETS",
        rate_limit.UserTokenBuckets(rate_limit.ASSET_UPLOADS_PER_MINUTE),
    )
    monkeypatch.setattr(
        campaigns_page,
        "ASSET_READ_BUCKETS",
        rate_limit.UserTokenBuckets(rate_limit.ASSET_READS_PER_MINUTE),
    )


async def sign_in(
    client, user_id: str, guilds: Iterable[int] = (GUILD,)
) -> None:
    async with client.session_transaction() as stored:
        stored["authenticated"] = True
        stored["user_id"] = user_id
        stored["username"] = "panel-user"
        stored[login.ISSUED_AT_KEY] = login.now()
        stored[login.LOGIN_EPOCH_KEY] = 0
    await state.record_user_guilds(
        Actor(id=user_id, username="panel-user"), guilds
    )


async def add_member(database: Database, user_id: str) -> None:
    await database.execute(
        "INSERT INTO members (campaign_slug, user_id, display_name, joined_at) "
        "VALUES (?, ?, 'Panel User', 1700000000)",
        (SLUG, user_id),
    )


def image_bytes(
    image_format: str = "PNG",
    color: str = "red",
    size: tuple[int, int] = (8, 8),
    exif: bytes | None = None,
) -> bytes:
    image = Image.new("RGB", size, color)
    options: dict[str, Any] = {} if exif is None else {"exif": exif}
    buffer = io.BytesIO()
    image.save(buffer, format=image_format, **options)
    return buffer.getvalue()


def jpeg_with_exif() -> bytes:
    exif = Image.Exif()
    exif[0x010F] = "HarpiCam"
    exif[0x0112] = 1
    return image_bytes("JPEG", exif=exif.tobytes())


def upload(payload: bytes, filename: str = "portrait.png") -> FileStorage:
    return FileStorage(stream=io.BytesIO(payload), filename=filename)


async def post_image(
    client, payload: bytes, filename: str = "portrait.png", headers=None
):
    return await client.post(
        ASSETS_ROUTE,
        files={"file": upload(payload, filename)},
        headers=CSRF if headers is None else headers,
    )


async def body(response) -> dict[str, Any]:
    return json.loads(await response.get_data())


def stored(world, name: str) -> Path:
    return world.root / CAMPAIGN / "assets" / name


async def usage(world) -> int:
    row = await world.database.fetchone(
        "SELECT COALESCE(SUM(size), 0) AS used FROM assets "
        "WHERE campaign_slug = ?",
        (SLUG,),
    )
    return 0 if row is None else int(row["used"])


async def test_uploading_a_png_names_the_file_by_its_content_hash(
    client, world
):
    await sign_in(client, NARRATOR)
    payload = image_bytes()

    response = await post_image(client, payload, filename="../../evil.png")

    assert response.status_code == 200
    uploaded = await body(response)
    content = stored(world, uploaded["name"]).read_bytes()
    assert uploaded["name"] == f"{sha256(content).hexdigest()}.png"
    assert uploaded["hash"] == sha256(content).hexdigest()
    assert uploaded["path"] == f"{CAMPAIGN}/assets/{uploaded['name']}"
    assert uploaded["url"] == f"{ASSETS_ROUTE}/{uploaded['name']}"
    assert uploaded["size"] == len(content)
    assert uploaded["content_type"] == "image/png"
    assert uploaded["new_file"] is True
    assert Image.open(stored(world, uploaded["name"])).format == "PNG"


async def test_a_jpeg_upload_loses_its_exif(client, world):
    await sign_in(client, NARRATOR)
    payload = jpeg_with_exif()
    assert b"Exif" in payload

    response = await post_image(client, payload, filename="photo.jpg")

    assert response.status_code == 200
    uploaded = await body(response)
    content = stored(world, uploaded["name"]).read_bytes()
    assert uploaded["name"].endswith(".jpg")
    assert b"Exif" not in content
    assert Image.open(io.BytesIO(content)).getexif() == {}


async def test_a_rotated_photo_is_saved_upright(client, world):
    await sign_in(client, NARRATOR)
    exif = Image.Exif()
    exif[0x0112] = 6
    payload = image_bytes("JPEG", size=(8, 4), exif=exif.tobytes())
    assert Image.open(io.BytesIO(payload)).size == (8, 4)

    response = await post_image(client, payload, filename="photo.jpg")

    assert response.status_code == 200
    uploaded = await body(response)
    stored_image = Image.open(stored(world, uploaded["name"]))
    assert stored_image.size == (4, 8)
    assert stored_image.getexif() == {}


async def test_uploading_the_same_content_does_not_rewrite_the_file(
    client, world
):
    await sign_in(client, NARRATOR)
    payload = image_bytes()
    first = await post_image(client, payload)
    name = (await body(first))["name"]
    target = stored(world, name)
    os.utime(target, (1_000_000_000, 1_000_000_000))

    response = await post_image(client, payload)

    assert response.status_code == 200
    uploaded = await body(response)
    assert uploaded["name"] == name
    assert uploaded["new_file"] is False
    assert target.stat().st_mtime == 1_000_000_000


async def test_reuploading_after_the_file_vanished_does_not_double_count(
    client, world
):
    await sign_in(client, NARRATOR)
    payload = image_bytes()
    first = await body(await post_image(client, payload))
    stored(world, first["name"]).unlink()

    response = await post_image(client, payload)

    assert response.status_code == 200
    assert (await body(response))["new_file"] is True
    assert await usage(world) == first["size"]


async def test_concurrent_uploads_cannot_overshoot_the_quota(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    await sign_in(client, NARRATOR)
    red = await body(await post_image(client, image_bytes(color="red")))
    blue = await body(await post_image(client, image_bytes(color="blue")))
    await world.database.execute("DELETE FROM assets")
    for name in (red["name"], blue["name"]):
        stored(world, name).unlink()
    monkeypatch.setattr(assets, "QUOTA_BYTES", red["size"] + blue["size"] - 1)

    responses = await asyncio.gather(
        post_image(client, image_bytes(color="red")),
        post_image(client, image_bytes(color="blue")),
    )

    assert sorted(response.status_code for response in responses) == [
        200,
        413,
    ]
    assert await usage(world) <= assets.QUOTA_BYTES


@pytest.mark.parametrize(
    ("image_format", "suffix", "content_type"),
    [
        ("PNG", ".png", "image/png"),
        ("JPEG", ".jpg", "image/jpeg"),
        ("WEBP", ".webp", "image/webp"),
    ],
)
async def test_upload_accepts_each_allowed_format(
    client, world, image_format: str, suffix: str, content_type: str
):
    await sign_in(client, NARRATOR)

    response = await post_image(
        client, image_bytes(image_format), filename="picture.bin"
    )

    assert response.status_code == 200
    uploaded = await body(response)
    assert uploaded["name"].endswith(suffix)
    assert uploaded["content_type"] == content_type


async def test_an_upload_that_is_not_an_allowed_image_is_refused(
    client, world
):
    await sign_in(client, NARRATOR)
    payload = b"<svg xmlns='http://www.w3.org/2000/svg'><script/></svg>"

    response = await post_image(client, payload, filename="map.svg")

    assert response.status_code == 422
    assert (await body(response))["error"]["code"] == "invalid_payload"
    assert not (world.root / CAMPAIGN / "assets").exists()


async def test_an_upload_above_sixteen_megabytes_is_refused(client, world):
    await sign_in(client, NARRATOR)
    payload = b"\x89PNG\r\n\x1a\n" + b"\x00" * (16 * 1024 * 1024)

    response = await post_image(client, payload)

    assert response.status_code == 413
    assert (await body(response))["error"]["code"] == "payload_too_large"


async def test_the_campaign_quota_answers_413(client, world):
    await sign_in(client, NARRATOR)
    folder = world.root / CAMPAIGN / "assets"
    folder.mkdir(parents=True)
    filler = folder / "filler.png"
    filler.write_bytes(b"x")
    await world.database.execute(
        "INSERT INTO assets "
        "(campaign_slug, name, size, created_by, created_at) "
        "VALUES (?, 'filler.png', ?, ?, 1700000000)",
        (SLUG, assets.QUOTA_BYTES, NARRATOR),
    )

    response = await post_image(client, image_bytes())

    assert response.status_code == 413
    assert (await body(response))["error"]["code"] == "quota_exceeded"
    assert list(folder.iterdir()) == [filler]


async def test_uploading_beyond_the_bucket_answers_429(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    buckets = rate_limit.UserTokenBuckets(1)
    monkeypatch.setattr(campaigns_page, "ASSET_UPLOAD_BUCKETS", buckets)
    await sign_in(client, NARRATOR)

    allowed = await post_image(client, image_bytes())
    refused = await post_image(client, image_bytes(color="blue"))

    assert allowed.status_code == 200
    assert refused.status_code == 429
    assert int(refused.headers["Retry-After"]) >= 1


async def test_a_pending_member_may_upload(client, world):
    await sign_in(client, PLAYER)
    await add_member(world.database, PLAYER)

    response = await post_image(client, image_bytes())

    assert response.status_code == 200


async def test_an_outsider_cannot_upload_or_read(client, world):
    await sign_in(client, NARRATOR)
    uploaded = await body(await post_image(client, image_bytes()))
    await sign_in(client, PLAYER, guilds=(OTHER_GUILD,))

    read = await client.get(f"{ASSETS_ROUTE}/{uploaded['name']}")
    write = await post_image(client, image_bytes(color="blue"))

    assert read.status_code == 404
    assert write.status_code == 404


async def test_only_the_upload_route_accepts_a_multipart_body(client, world):
    await sign_in(client, NARRATOR)

    uploaded = await post_image(client, image_bytes())
    elsewhere = await client.post(
        f"/api/campaigns/{SLUG}/characters",
        files={"file": upload(image_bytes(), "portrait.png")},
        headers=CSRF,
    )
    cross_site = await post_image(
        client,
        image_bytes(color="blue"),
        headers={"Sec-Fetch-Site": "cross-site"},
    )

    assert uploaded.status_code == 200
    assert elsewhere.status_code == 403
    assert cross_site.status_code == 403


async def test_a_upload_without_a_file_is_422(client, world):
    await sign_in(client, NARRATOR)

    response = await client.post(
        ASSETS_ROUTE, json={"file": "x"}, headers=CSRF
    )

    assert response.status_code == 422
    assert (await body(response))["error"]["code"] == "invalid_payload"


async def test_a_missing_vault_answers_503(client, world):
    await sign_in(client, NARRATOR)
    vault.configure(vault.Vault())

    upload_response = await post_image(client, image_bytes())
    read_response = await client.get(f"{ASSETS_ROUTE}/a.png")
    image_response = await client.get(f"{IMAGES_ROUTE}/a.png")

    assert upload_response.status_code == 503
    assert read_response.status_code == 503
    assert image_response.status_code == 503


async def test_reading_an_asset_serves_it_with_private_cache_headers(
    client, world
):
    await sign_in(client, NARRATOR)
    uploaded = await body(await post_image(client, image_bytes()))
    content = stored(world, uploaded["name"]).read_bytes()

    response = await client.get(f"{ASSETS_ROUTE}/{uploaded['name']}")

    assert response.status_code == 200
    assert await response.get_data() == content
    assert response.headers["Content-Type"] == "image/png"
    assert response.headers["Cache-Control"] == PRIVATE_CACHE
    assert response.headers["ETag"]
    assert response.headers["Last-Modified"]


async def test_a_matching_etag_answers_304(client, world):
    await sign_in(client, NARRATOR)
    uploaded = await body(await post_image(client, image_bytes()))
    first = await client.get(f"{ASSETS_ROUTE}/{uploaded['name']}")

    response = await client.get(
        f"{ASSETS_ROUTE}/{uploaded['name']}",
        headers={"If-None-Match": first.headers["ETag"]},
    )

    assert response.status_code == 304
    assert await response.get_data() == b""
    assert response.headers["Cache-Control"] == PRIVATE_CACHE


async def test_an_orphan_asset_is_not_served_by_either_route(client, world):
    await sign_in(client, NARRATOR)
    name = f"{sha256(b'orphan').hexdigest()}.png"
    target = stored(world, name)
    target.parent.mkdir(parents=True)
    target.write_bytes(image_bytes())
    vault_index.configure(VaultIndex(world.root))

    read = await client.get(f"{ASSETS_ROUTE}/{name}")
    as_image = await client.get(f"{IMAGES_ROUTE}/{name}")

    assert read.status_code == 404
    assert as_image.status_code == 404


async def test_a_directory_named_like_an_asset_is_not_served(client, world):
    await sign_in(client, NARRATOR)
    name = "a" * 64 + ".png"
    await world.database.execute(
        "INSERT INTO assets "
        "(campaign_slug, name, size, created_by, created_at) "
        "VALUES (?, ?, 8, ?, 1700000000)",
        (SLUG, name, NARRATOR),
    )
    stored(world, name).mkdir(parents=True)

    response = await client.get(f"{ASSETS_ROUTE}/{name}")

    assert response.status_code == 404


async def test_a_symlink_escaping_the_root_is_not_served(client, world):
    await sign_in(client, NARRATOR)
    outside = world.root.parent / "secret.png"
    outside.write_bytes(image_bytes())
    name = "b" * 64 + ".png"
    folder = world.root / CAMPAIGN / "assets"
    folder.mkdir(parents=True)
    (folder / name).symlink_to(outside)
    await world.database.execute(
        "INSERT INTO assets "
        "(campaign_slug, name, size, created_by, created_at) "
        "VALUES (?, ?, 8, ?, 1700000000)",
        (SLUG, name, NARRATOR),
    )

    response = await client.get(f"{ASSETS_ROUTE}/{name}")

    assert response.status_code == 404


@pytest.mark.parametrize(
    "name",
    [
        "..",
        "%2e%2e",
        "..%2Fsecret.png",
        "evil%5Cpath.png",
        "map.svg",
        f"{'a' * 64}.gif",
        ".hidden.png",
        "a" * 300 + ".png",
    ],
)
async def test_a_name_outside_the_allowlist_is_404(client, world, name: str):
    await sign_in(client, NARRATOR)

    response = await client.get(f"{ASSETS_ROUTE}/{name}")

    assert response.status_code == 404


async def test_a_vault_image_is_served_by_name(client, world):
    await sign_in(client, NARRATOR)
    picture = world.root / "Arte" / "mapa.png"
    picture.parent.mkdir(parents=True)
    picture.write_bytes(image_bytes())
    vault_index.configure(VaultIndex(world.root))

    response = await client.get(f"{IMAGES_ROUTE}/mapa.png")

    assert response.status_code == 200
    assert await response.get_data() == picture.read_bytes()
    assert response.headers["Content-Type"] == "image/png"
    assert response.headers["Cache-Control"] == PRIVATE_CACHE


async def test_an_svg_is_not_served_as_an_image(client, world):
    await sign_in(client, NARRATOR)
    sketch = world.root / "Arte" / "mapa.svg"
    sketch.parent.mkdir(parents=True)
    sketch.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    vault_index.configure(VaultIndex(world.root))

    response = await client.get(f"{IMAGES_ROUTE}/mapa.svg")

    assert response.status_code == 404


async def test_an_image_above_sixteen_megabytes_is_404(client, world):
    await sign_in(client, NARRATOR)
    picture = world.root / "Arte" / "grande.png"
    picture.parent.mkdir(parents=True)
    picture.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * (16 * 1024 * 1024))
    vault_index.configure(VaultIndex(world.root))

    response = await client.get(f"{IMAGES_ROUTE}/grande.png")

    assert response.status_code == 404


async def test_reading_beyond_the_bucket_answers_429(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    buckets = rate_limit.UserTokenBuckets(1)
    monkeypatch.setattr(campaigns_page, "ASSET_READ_BUCKETS", buckets)
    await sign_in(client, NARRATOR)
    uploaded = await body(await post_image(client, image_bytes()))

    allowed = await client.get(f"{ASSETS_ROUTE}/{uploaded['name']}")
    refused = await client.get(f"{ASSETS_ROUTE}/{uploaded['name']}")

    assert allowed.status_code == 200
    assert refused.status_code == 429


async def test_reading_an_asset_lists_no_directory(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    await sign_in(client, NARRATOR)
    uploaded = await body(await post_image(client, image_bytes()))

    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("the request listed a directory")

    monkeypatch.setattr(os, "walk", refuse)
    response = await client.get(f"{ASSETS_ROUTE}/{uploaded['name']}")

    assert response.status_code == 200


def header_only_png(width: int, height: int) -> bytes:
    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    ihdr = (
        struct.pack(">I", len(header))
        + b"IHDR"
        + header
        + struct.pack(">I", zlib.crc32(b"IHDR" + header))
    )
    data = b"\x78\x9c\x03\x00\x00\x00\x00\x01"
    idat = (
        struct.pack(">I", len(data))
        + b"IDAT"
        + data
        + struct.pack(">I", zlib.crc32(b"IDAT" + data))
    )
    return (
        b"\x89PNG\r\n\x1a\n" + ihdr + idat + b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


async def test_a_pixel_bomb_is_refused_before_decoding(client, world):
    await sign_in(client, NARRATOR)
    payload = header_only_png(13_000, 13_000)
    assert len(payload) < 1024
    tracemalloc.start()
    try:
        response = await post_image(client, payload)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert response.status_code == 413
    assert (await body(response))["error"]["code"] == "payload_too_large"
    assert peak < 16 * 1024 * 1024
    assert await usage(world) == 0
    assert not (world.root / CAMPAIGN / "assets").exists()


async def test_an_image_beyond_the_pixel_ceiling_is_refused(client, world):
    await sign_in(client, NARRATOR)
    payload = header_only_png(13_000, 4_000)

    with pytest.warns(Image.DecompressionBombWarning):
        response = await post_image(client, payload)

    assert response.status_code == 413
    assert await usage(world) == 0


async def test_an_image_beyond_the_edge_ceiling_is_refused(client, world):
    await sign_in(client, NARRATOR)

    response = await post_image(client, header_only_png(20_000, 10))

    assert response.status_code == 413
    assert await usage(world) == 0


async def test_a_reencoded_image_above_the_read_cap_is_refused(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    await sign_in(client, NARRATOR)
    monkeypatch.setattr(
        assets, "reencode", lambda raw, suffix: b"x" * (16 * 1024 * 1024 + 1)
    )

    response = await post_image(client, image_bytes())

    assert response.status_code == 413
    assert (await body(response))["error"]["code"] == "payload_too_large"
    assert await usage(world) == 0


async def test_writing_outside_the_vault_is_refused(client, world):
    await sign_in(client, NARRATOR)
    outside = world.root.parent / "outside"
    outside.mkdir()
    (world.root / CAMPAIGN).mkdir(parents=True)
    (world.root / CAMPAIGN / "assets").symlink_to(outside)

    response = await post_image(client, image_bytes())

    assert response.status_code == 503
    assert str(world.root) not in (await body(response))["error"]["message"]
    assert list(outside.iterdir()) == []
    assert await usage(world) == 0


async def test_a_failed_write_leaves_no_asset_row(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    await sign_in(client, NARRATOR)

    def refuse(target: Path, data: bytes) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(assets, "_write", refuse)
    response = await post_image(client, image_bytes())

    assert response.status_code == 503
    assert await usage(world) == 0


async def test_a_row_without_a_file_does_not_hold_the_quota(client, world):
    await sign_in(client, NARRATOR)
    await world.database.execute(
        "INSERT INTO assets "
        "(campaign_slug, name, size, created_by, created_at) "
        "VALUES (?, 'gone.png', ?, ?, 1700000000)",
        (SLUG, assets.QUOTA_BYTES, NARRATOR),
    )

    response = await post_image(client, image_bytes())

    assert response.status_code == 200


async def test_weak_and_wildcard_etags_answer_304(client, world):
    await sign_in(client, NARRATOR)
    uploaded = await body(await post_image(client, image_bytes()))
    first = await client.get(f"{ASSETS_ROUTE}/{uploaded['name']}")
    etag = first.headers["ETag"]

    weak = await client.get(
        f"{ASSETS_ROUTE}/{uploaded['name']}",
        headers={"If-None-Match": f"W/{etag}"},
    )
    wildcard = await client.get(
        f"{ASSETS_ROUTE}/{uploaded['name']}",
        headers={"If-None-Match": "*"},
    )

    assert weak.status_code == 304
    assert wildcard.status_code == 304


async def test_an_image_from_another_campaign_is_hidden(client, world):
    await sign_in(client, NARRATOR)
    picture = world.root / "Harpi" / "Campaigns" / "outra" / "mapa.png"
    picture.parent.mkdir(parents=True)
    picture.write_bytes(image_bytes())
    vault_index.configure(VaultIndex(world.root))

    response = await client.get(f"{IMAGES_ROUTE}/mapa.png")

    assert response.status_code == 404


async def test_an_image_inside_the_campaign_is_served(client, world):
    await sign_in(client, NARRATOR)
    picture = world.root / CAMPAIGN / "portraits" / "ana.png"
    picture.parent.mkdir(parents=True)
    picture.write_bytes(image_bytes())
    vault_index.configure(VaultIndex(world.root))

    response = await client.get(f"{IMAGES_ROUTE}/ana.png")

    assert response.status_code == 200


async def test_an_upload_above_the_json_body_cap_is_accepted(client, world):
    await sign_in(client, NARRATOR)
    noise = random.Random(0).randbytes(300 * 300 * 3)
    buffer = io.BytesIO()
    Image.frombytes("RGB", (300, 300), noise).save(buffer, format="PNG")
    payload = buffer.getvalue()
    assert len(payload) > 64 * 1024

    response = await post_image(client, payload)

    assert response.status_code == 200
