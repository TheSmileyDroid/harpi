from __future__ import annotations

import hashlib
import io
import json
from collections.abc import Iterable
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
from src.panel import login, rate_limit, scenes, state, vault, vault_index
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
SCENES_ROUTE = f"/api/campaigns/{SLUG}/scenes"
SCRIPTA = f"{CAMPAIGN}/scenes/cripta.json"
CSRF = {"Sec-Fetch-Site": "same-origin"}


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


async def activate_sheet(database: Database, user_id: str) -> None:
    await database.execute(
        "INSERT INTO sheet_files ("
        "path, harpi_id, campaign, rev, hash, last_text, base_json, "
        "status, owner_id, state, updated_at"
        ") VALUES (?, 'sht_player', ?, 1, 'hash', '', '{}', 'ativo', ?, "
        "'ok', 1700000000)",
        (f"{CAMPAIGN}/sheets/Player.md", SLUG, user_id),
    )


def image_bytes(
    color: str = "red", size: tuple[int, int] = (800, 600)
) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def vault_image(world, name: str = "mapa.png", **kwargs: Any) -> str:
    target = world.root / CAMPAIGN / "assets" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(image_bytes(**kwargs))
    vault_index.configure(VaultIndex(world.root))
    return f"{CAMPAIGN}/assets/{name}"


async def body(response) -> dict[str, Any]:
    return json.loads(await response.get_data())


def canonical(data: dict[str, Any]) -> str:
    return json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def file_hash(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    return hashlib.sha256(canonical(data).encode()).hexdigest()


def zone(name: str = "Sala principal", **kwargs: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": "zon_sala",
        "label": name,
        "revealed": False,
        "rects": [{"x": 1, "y": 2, "w": 3, "h": 2}],
    }
    data.update(kwargs)
    return data


async def create_scene(client, **payload: Any) -> tuple[Any, dict[str, Any]]:
    response = await client.post(SCENES_ROUTE, json=payload, headers=CSRF)
    return response, await body(response)


async def create_image_scene(client, world, **overrides: Any):
    image = vault_image(world)
    payload: dict[str, Any] = {
        "name": "Cripta",
        "source": "image",
        "image": image,
        "zones": [zone()],
        "fog_outside": True,
    }
    payload.update(overrides)
    return await create_scene(client, **payload)


async def test_a_scene_is_created_from_a_vault_image(client, world):
    await sign_in(client, NARRATOR)

    response, scene = await create_image_scene(client, world)

    assert response.status_code == 200
    target = world.root / SCRIPTA
    stored = json.loads(target.read_text(encoding="utf-8"))
    assert scene["slug"] == "cripta"
    assert scene["source"] == "image"
    assert scene["name"] == "Cripta"
    assert scene["image"] == {
        "path": f"{CAMPAIGN}/assets/mapa.png",
        "width": 800,
        "height": 600,
    }
    assert scene["grid"] == {
        "cell_px": 70,
        "offset_x": 0,
        "offset_y": 0,
        "visible": True,
    }
    assert scene["zones"] == [
        {
            "id": "zon_sala",
            "label": "Sala principal",
            "revealed": False,
            "rects": [{"x": 1, "y": 2, "w": 3, "h": 2}],
        }
    ]
    assert stored["slug"] == "cripta"
    assert scene["hash"] == file_hash(target)
    assert scene["saved"] is True
    row = await world.database.fetchone(
        "SELECT * FROM scenes WHERE campaign_slug = ?", (SLUG,)
    )
    assert row is not None
    assert row["blueprint_path"] == SCRIPTA
    assert row["blueprint_hash"] == scene["hash"]
    assert row["image_path"] == f"{CAMPAIGN}/assets/mapa.png"
    assert (row["image_width"], row["image_height"]) == (800, 600)
    assert row["source"] == "image"


async def test_a_sketch_scene_points_at_its_future_svg(client, world):
    await sign_in(client, NARRATOR)

    response, scene = await create_scene(
        client,
        name="Calabouço",
        source="sketch",
        image_width=1600,
        image_height=900,
        zones=[zone()],
    )

    assert response.status_code == 200
    assert scene["slug"] == "calabouco"
    assert scene["image"] == {
        "path": f"{CAMPAIGN}/assets/calabouco-map.svg",
        "width": 1600,
        "height": 900,
    }
    target = world.root / CAMPAIGN / "scenes" / "calabouco.json"
    assert target.is_file()
    listing = await client.get(SCENES_ROUTE)
    assert (await body(listing))["scenes"][0]["thumbnail"] is None


async def test_the_gallery_lists_cards_with_origin_areas_and_saved_state(
    client, world
):
    await sign_in(client, NARRATOR)
    await create_image_scene(client, world)
    await create_scene(
        client,
        name="Calabouço",
        source="sketch",
        zones=[zone("Cela"), zone("Corredor", id="zon_corredor")],
    )

    response = await client.get(SCENES_ROUTE)

    assert response.status_code == 200
    cards = (await body(response))["scenes"]
    assert [card["name"] for card in cards] == ["Calabouço", "Cripta"]
    assert cards[0]["source"] == "sketch"
    assert cards[0]["zone_count"] == 2
    assert cards[0]["saved"] is True
    assert cards[0]["in_use"] is False
    assert cards[0]["width"] == 1920
    assert cards[0]["height"] == 1080
    assert cards[0]["grid"]["cell_px"] == 70
    assert [zone["label"] for zone in cards[0]["zones"]] == [
        "Cela",
        "Corredor",
    ]
    assert cards[1]["source"] == "image"
    assert cards[1]["zone_count"] == 1
    assert (
        cards[1]["thumbnail"] == f"/api/campaigns/{SLUG}/scenes/cripta/image"
    )


async def test_an_external_edit_marks_the_card_unsaved(client, world):
    await sign_in(client, NARRATOR)
    await create_image_scene(client, world)
    target = world.root / SCRIPTA
    data = json.loads(target.read_text(encoding="utf-8"))
    data["name"] = "Cripta do Obsidian"
    target.write_text(json.dumps(data), encoding="utf-8")

    listing = await client.get(SCENES_ROUTE)
    detail = await client.get(f"{SCENES_ROUTE}/cripta")

    cards = (await body(listing))["scenes"]
    assert cards[0]["saved"] is False
    assert (await body(detail))["saved"] is False


async def test_saving_keeps_zones_labels_and_revealed_without_renaming_the_file(
    client, world
):
    await sign_in(client, NARRATOR)
    _, scene = await create_image_scene(client, world)
    target = world.root / SCRIPTA
    changed = [
        zone(
            "Sala principal",
            revealed=True,
            rects=[{"x": 0, "y": 0, "w": 2, "h": 2}],
        ),
        zone("Cripta", id="zon_cripta", revealed=False),
    ]

    response = await client.put(
        f"{SCENES_ROUTE}/cripta",
        json={
            "base_hash": scene["hash"],
            "name": "Cripta Velha",
            "grid": {
                "cell_px": 35,
                "offset_x": 4,
                "offset_y": 6,
                "visible": False,
            },
            "fog_outside": False,
            "zones": changed,
        },
        headers=CSRF,
    )

    assert response.status_code == 200
    saved = await body(response)
    assert saved["slug"] == "cripta"
    assert saved["name"] == "Cripta Velha"
    assert saved["grid"]["cell_px"] == 35
    assert saved["fog_outside"] is False
    assert saved["zones"] == changed
    assert saved["saved"] is True
    assert saved["hash"] != scene["hash"]
    assert target.is_file()
    assert list(target.parent.iterdir()) == [target]
    row = await world.database.fetchone(
        "SELECT name, blueprint_hash, rev FROM scenes "
        "WHERE campaign_slug = ? AND blueprint_path = ?",
        (SLUG, SCRIPTA),
    )
    assert row is not None
    assert row["name"] == "Cripta Velha"
    assert row["blueprint_hash"] == saved["hash"]
    assert row["rev"] == 2

    reopened = await client.get(f"{SCENES_ROUTE}/cripta")

    assert reopened.status_code == 200
    detail = await body(reopened)
    assert detail["zones"] == changed
    assert detail["name"] == "Cripta Velha"
    assert detail["source"] == "image"
    assert detail["image"]["path"] == f"{CAMPAIGN}/assets/mapa.png"


async def test_a_stale_base_hash_is_refused_and_the_file_is_untouched(
    client, world
):
    await sign_in(client, NARRATOR)
    _, scene = await create_image_scene(client, world)
    target = world.root / SCRIPTA
    data = json.loads(target.read_text(encoding="utf-8"))
    data["name"] = "Editado no Obsidian"
    target.write_text(json.dumps(data), encoding="utf-8")
    before = target.read_bytes()

    response = await client.put(
        f"{SCENES_ROUTE}/cripta",
        json={
            "base_hash": scene["hash"],
            "name": "Cripta",
            "grid": scene["grid"],
            "fog_outside": True,
            "zones": scene["zones"],
        },
        headers=CSRF,
    )

    assert response.status_code == 409
    assert (await body(response))["error"]["code"] == "scene_conflict"
    assert target.read_bytes() == before


async def test_saving_duplicate_zone_ids_is_422(client, world):
    await sign_in(client, NARRATOR)
    _, scene = await create_image_scene(client, world)

    response = await client.put(
        f"{SCENES_ROUTE}/cripta",
        json={
            "base_hash": scene["hash"],
            "name": "Cripta",
            "grid": scene["grid"],
            "fog_outside": True,
            "zones": [
                {
                    "id": "zon_a",
                    "label": "A",
                    "rects": [{"x": 0, "y": 0, "w": 1, "h": 1}],
                },
                {
                    "id": "zon_a",
                    "label": "B",
                    "rects": [{"x": 1, "y": 1, "w": 1, "h": 1}],
                },
            ],
        },
        headers=CSRF,
    )

    assert response.status_code == 422
    assert (await body(response))["error"]["code"] == "invalid_payload"


async def test_a_missing_blueprint_file_answers_409(client, world):
    await sign_in(client, NARRATOR)
    await create_image_scene(client, world)
    (world.root / SCRIPTA).unlink()

    listing = await client.get(SCENES_ROUTE)
    detail = await client.get(f"{SCENES_ROUTE}/cripta")
    saved = await client.put(
        f"{SCENES_ROUTE}/cripta",
        json={
            "base_hash": "x",
            "name": "Cripta",
            "grid": {
                "cell_px": 70,
                "offset_x": 0,
                "offset_y": 0,
                "visible": True,
            },
            "fog_outside": True,
            "zones": [zone()],
        },
        headers=CSRF,
    )

    assert listing.status_code == 200
    assert (await body(listing))["scenes"][0]["saved"] is False
    assert detail.status_code == 409
    assert saved.status_code == 409
    assert (await body(saved))["error"]["code"] == "scene_unreadable"


async def test_an_image_from_another_campaign_is_refused(client, world):
    await sign_in(client, NARRATOR)
    other = world.root / "Harpi" / "Campaigns" / "outra" / "assets" / "a.png"
    other.parent.mkdir(parents=True)
    other.write_bytes(image_bytes())
    vault_index.configure(VaultIndex(world.root))

    response, payload = await create_scene(
        client,
        name="Cripta",
        source="image",
        image="Harpi/Campaigns/outra/assets/a.png",
    )

    assert response.status_code == 422
    assert payload["error"]["code"] == "invalid_payload"


async def test_a_zone_outside_the_map_is_422(client, world):
    await sign_in(client, NARRATOR)

    response, payload = await create_image_scene(
        client,
        world,
        zones=[zone(rects=[{"x": 9999, "y": 9999, "w": 5, "h": 5}])],
    )

    assert response.status_code == 422
    assert payload["error"]["code"] == "invalid_payload"
    assert not (world.root / SCRIPTA).exists()


async def test_saving_a_zone_outside_the_map_is_422(client, world):
    await sign_in(client, NARRATOR)
    _, scene = await create_image_scene(client, world)
    target = world.root / SCRIPTA
    before = target.read_bytes()

    response = await client.put(
        f"{SCENES_ROUTE}/cripta",
        json={
            "base_hash": scene["hash"],
            "name": "Cripta",
            "grid": scene["grid"],
            "fog_outside": True,
            "zones": [zone(rects=[{"x": 12, "y": 0, "w": 1, "h": 1}])],
        },
        headers=CSRF,
    )

    assert response.status_code == 422
    assert (await body(response))["error"]["code"] == "invalid_payload"
    assert target.read_bytes() == before


async def test_a_disk_change_between_read_and_replace_is_a_conflict(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    await sign_in(client, NARRATOR)
    _, scene = await create_image_scene(client, world)
    target = world.root / SCRIPTA
    unchanged = scenes._unchanged

    def tampered(path: Path, base_hash: str) -> bool:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["name"] = "Obsidian venceu"
        path.write_text(json.dumps(data), encoding="utf-8")
        return unchanged(path, base_hash)

    monkeypatch.setattr(scenes, "_unchanged", tampered)
    response = await client.put(
        f"{SCENES_ROUTE}/cripta",
        json={
            "base_hash": scene["hash"],
            "name": "Cripta",
            "grid": scene["grid"],
            "fog_outside": True,
            "zones": [zone()],
        },
        headers=CSRF,
    )

    assert response.status_code == 409
    assert (await body(response))["error"]["code"] == "scene_conflict"
    stored = json.loads(target.read_text(encoding="utf-8"))
    assert stored["name"] == "Obsidian venceu"
    assert list(target.parent.iterdir()) == [target]


async def test_the_gallery_reuses_the_cached_blueprint(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    await sign_in(client, NARRATOR)
    await create_image_scene(client, world)
    assert (await client.get(SCENES_ROUTE)).status_code == 200

    def refuse(self: Path) -> str:
        raise AssertionError("the gallery reread the blueprint")

    monkeypatch.setattr(Path, "read_text", refuse)
    response = await client.get(SCENES_ROUTE)

    assert response.status_code == 200
    assert (await body(response))["scenes"][0]["zone_count"] == 1


async def test_a_scene_serves_its_uploaded_image(client, world):
    await sign_in(client, NARRATOR)
    uploaded = await client.post(
        f"/api/campaigns/{SLUG}/assets",
        files={
            "file": FileStorage(
                stream=io.BytesIO(image_bytes()), filename="mapa.png"
            )
        },
        headers=CSRF,
    )
    asset = await body(uploaded)
    await create_scene(
        client,
        name="Cripta",
        source="image",
        image=asset["path"],
        zones=[zone()],
    )

    response = await client.get(f"{SCENES_ROUTE}/cripta/image")
    cards = (await body(await client.get(SCENES_ROUTE)))["scenes"]

    assert cards[0]["thumbnail"] == f"{SCENES_ROUTE}/cripta/image"
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "image/png"


async def test_a_scene_serves_an_image_placed_by_hand_in_assets(client, world):
    await sign_in(client, NARRATOR)
    await create_image_scene(client, world)

    response = await client.get(f"{SCENES_ROUTE}/cripta/image")
    cards = (await body(await client.get(SCENES_ROUTE)))["scenes"]

    assert cards[0]["thumbnail"] == f"{SCENES_ROUTE}/cripta/image"
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "image/png"


async def test_no_scene_is_marked_in_use_until_tables_exist(client, world):
    await sign_in(client, NARRATOR)
    await create_image_scene(client, world)

    cards = (await body(await client.get(SCENES_ROUTE)))["scenes"]

    assert [card["in_use"] for card in cards] == [False]


async def test_a_failed_restore_answers_a_clear_error(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    await sign_in(client, NARRATOR)
    _, scene = await create_image_scene(client, world)

    async def refuse(*args: object, **kwargs: object) -> None:
        raise RuntimeError("database is gone")

    def refuse_restore(*args: object, **kwargs: object) -> None:
        raise OSError("disk is read-only")

    monkeypatch.setattr(scenes, "store_save", refuse)
    monkeypatch.setattr(scenes, "restore_file", refuse_restore)
    response = await client.put(
        f"{SCENES_ROUTE}/cripta",
        json={
            "base_hash": scene["hash"],
            "name": "Cripta",
            "grid": scene["grid"],
            "fog_outside": True,
            "zones": [zone()],
        },
        headers=CSRF,
    )

    assert response.status_code == 503
    assert (await body(response))["error"]["code"] == "scene_restore_failed"


async def test_player_and_spectator_do_not_get_the_list_or_the_blueprint(
    client, world
):
    await sign_in(client, NARRATOR)
    await create_image_scene(client, world)
    await sign_in(client, PLAYER)
    await add_member(world.database, PLAYER)
    await activate_sheet(world.database, PLAYER)

    listing = await client.get(SCENES_ROUTE)
    detail = await client.get(f"{SCENES_ROUTE}/cripta")
    created, _ = await create_scene(client, name="Nova", source="sketch")
    saved = await client.put(
        f"{SCENES_ROUTE}/cripta",
        json={
            "base_hash": "x",
            "name": "Cripta",
            "grid": {
                "cell_px": 70,
                "offset_x": 0,
                "offset_y": 0,
                "visible": True,
            },
            "fog_outside": True,
            "zones": [],
        },
        headers=CSRF,
    )

    assert [listing.status_code, detail.status_code] == [403, 403]
    assert [created.status_code, saved.status_code] == [403, 403]

    await sign_in(client, PLAYER, guilds=(OTHER_GUILD,))

    assert (await client.get(SCENES_ROUTE)).status_code == 404
    assert (await client.get(f"{SCENES_ROUTE}/cripta")).status_code == 404


async def test_a_missing_vault_answers_503(client, world):
    await sign_in(client, NARRATOR)
    vault.configure(vault.Vault())

    response = await client.get(SCENES_ROUTE)

    assert response.status_code == 503
    assert (await body(response))["error"]["code"] == "vault_unavailable"


async def test_a_duplicate_scene_slug_is_a_conflict(client, world):
    await sign_in(client, NARRATOR)
    await create_image_scene(client, world)

    response, _ = await create_image_scene(client, world)

    assert response.status_code == 409
    assert (await body(response))["error"]["code"] == "scene_exists"


async def test_the_list_does_not_walk_the_vault(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    await sign_in(client, NARRATOR)
    await create_image_scene(client, world)

    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("the request listed a directory")

    monkeypatch.setattr("os.walk", refuse)
    monkeypatch.setattr("os.scandir", refuse)
    response = await client.get(SCENES_ROUTE)

    assert response.status_code == 200


async def test_an_orphan_blueprint_is_adopted_instead_of_locked_out(
    client, world
):
    await sign_in(client, NARRATOR)
    target = world.root / SCRIPTA
    target.parent.mkdir(parents=True)
    blueprint = {
        "slug": "cripta",
        "name": "Cripta",
        "source": "sketch",
        "image": {
            "path": f"{CAMPAIGN}/assets/cripta-map.svg",
            "width": 800,
            "height": 600,
        },
        "grid": {
            "cell_px": 40,
            "offset_x": 0,
            "offset_y": 0,
            "visible": True,
        },
        "fog_outside": True,
        "zones": [
            {
                "id": "zon_sala",
                "label": "Sala",
                "revealed": False,
                "rects": [{"x": 0, "y": 0, "w": 1, "h": 1}],
            }
        ],
    }
    target.write_text(canonical(blueprint) + "\n", encoding="utf-8")

    response, scene = await create_scene(
        client, name="Cripta", source="sketch", zones=[zone()]
    )

    assert response.status_code == 200
    assert scene["slug"] == "cripta"
    assert scene["saved"] is True
    row = await world.database.fetchone(
        "SELECT blueprint_hash FROM scenes WHERE blueprint_path = ?",
        (SCRIPTA,),
    )
    assert row is not None
    assert row["blueprint_hash"] == scene["hash"]


async def test_a_failed_save_restores_the_previous_blueprint(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    await sign_in(client, NARRATOR)
    _, scene = await create_image_scene(client, world)
    target = world.root / SCRIPTA
    before = target.read_bytes()

    async def refuse(*args: object, **kwargs: object) -> None:
        raise RuntimeError("database is gone")

    monkeypatch.setattr("src.panel.scenes.store_save", refuse)
    response = await client.put(
        f"{SCENES_ROUTE}/cripta",
        json={
            "base_hash": scene["hash"],
            "name": "Cripta Velha",
            "grid": scene["grid"],
            "fog_outside": False,
            "zones": [zone()],
        },
        headers=CSRF,
    )

    assert response.status_code == 503
    assert target.read_bytes() == before


async def test_creating_beyond_the_bucket_answers_429(
    client, world, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        campaigns_page,
        "SCENE_WRITE_BUCKETS",
        rate_limit.UserTokenBuckets(1),
    )
    await sign_in(client, NARRATOR)

    first, _ = await create_scene(
        client, name="Cripta", source="sketch", zones=[zone()]
    )
    second, payload = await create_scene(
        client, name="Calabouço", source="sketch", zones=[zone()]
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert payload["error"]["code"] == "too_many_requests"
    assert int(second.headers["Retry-After"]) >= 1


@pytest.mark.parametrize(
    "payload",
    [
        {"source": "image", "image": "Harpi/Campaigns/paratheos/a.png"},
        {"name": "!!!", "source": "sketch"},
        {"name": "   ", "source": "sketch"},
        {"name": "Cena", "source": "image"},
        {
            "name": "Cena",
            "source": "image",
            "image": "Harpi/Campaigns/outra/assets/a.png",
        },
        {
            "name": "Cena",
            "source": "sketch",
            "grid": {
                "cell_px": 0,
                "offset_x": 0,
                "offset_y": 0,
                "visible": True,
            },
        },
        {
            "name": "Cena",
            "source": "sketch",
            "zones": [
                {
                    "id": "zon_a",
                    "label": "A",
                    "rects": [{"x": 0, "y": 0, "w": 1, "h": 1}],
                },
                {
                    "id": "zon_a",
                    "label": "B",
                    "rects": [{"x": 1, "y": 1, "w": 1, "h": 1}],
                },
            ],
        },
        {
            "name": "Cena",
            "source": "sketch",
            "zones": [
                {
                    "id": "zon_a",
                    "label": "A",
                    "rects": [{"x": 0, "y": 0, "w": 0, "h": 1}],
                }
            ],
        },
    ],
)
async def test_an_invalid_creation_payload_is_422(client, world, payload):
    await sign_in(client, NARRATOR)

    response = await client.post(SCENES_ROUTE, json=payload, headers=CSRF)

    assert response.status_code == 422
    assert (await body(response))["error"]["code"] == "invalid_payload"


async def test_an_uploaded_image_can_seed_a_scene(client, world):
    await sign_in(client, NARRATOR)
    uploaded = await client.post(
        f"/api/campaigns/{SLUG}/assets",
        files={
            "file": FileStorage(
                stream=io.BytesIO(image_bytes()), filename="mapa.png"
            )
        },
        headers=CSRF,
    )
    assert uploaded.status_code == 200
    asset = await body(uploaded)

    response, scene = await create_scene(
        client,
        name="Cripta",
        source="image",
        image=asset["path"],
        zones=[zone()],
    )

    assert response.status_code == 200
    assert scene["image"]["path"] == asset["path"]
    assert scene["image"]["width"] == 800
