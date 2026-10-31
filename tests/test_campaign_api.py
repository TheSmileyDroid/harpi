from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

import pytest

from app import app as quart_app
from app import configure_panel_session
from pages.campaigns import guard_campaign_request
from src.config import Settings
from src.panel import login, state
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
SHEET_PATH = "Harpi/Campaigns/paratheos/sheets/Ana.md"


@pytest.fixture
async def campaigns(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SECRET_KEY", SECRET)
    configure_panel_session(Settings.from_env())
    quart_app.config["TESTING"] = True
    database = Database(
        tmp_path / "panel.db", campaign=paratheos(NARRATOR, str(GUILD))
    )
    await database.open()
    init_registry(SqliteRegistry(database))
    init_database(database)
    yield database
    clear_registry()
    clear_database()
    await database.close()


@pytest.fixture
async def client(campaigns):
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


async def add_sheet(database: Database, user_id: str, status: str) -> None:
    await database.execute(
        "INSERT INTO sheet_files ("
        "path, harpi_id, campaign, rev, hash, last_text, base_json, "
        "status, owner_id, state, updated_at"
        ") VALUES (?, 'sht_1', ?, 1, 'h', 'text', '{}', ?, ?, 'ok', 1)",
        (SHEET_PATH, SLUG, status, user_id),
    )


async def body(response) -> dict[str, Any]:
    return json.loads(await response.get_data())


async def test_campaigns_reject_an_anonymous_call(client):
    response = await client.get("/api/campaigns")

    assert response.status_code == 401


async def test_campaign_detail_rejects_an_anonymous_call(client):
    response = await client.get(f"/api/campaigns/{SLUG}")

    assert response.status_code == 401


async def test_the_narrator_lists_the_campaign(client):
    await sign_in(client, NARRATOR)

    response = await client.get("/api/campaigns")

    assert response.status_code == 200
    assert await body(response) == {
        "campaigns": [
            {
                "slug": SLUG,
                "name": "Paratheos",
                "system": "fate",
                "role": "narrator",
            }
        ]
    }


async def test_a_player_lists_the_campaign(client, campaigns):
    await sign_in(client, PLAYER)
    await add_member(campaigns, PLAYER)
    await add_sheet(campaigns, PLAYER, "ativo")

    response = await client.get("/api/campaigns")

    assert response.status_code == 200
    assert (await body(response))["campaigns"][0]["role"] == "player"


async def test_a_pending_member_lists_the_campaign(client, campaigns):
    await sign_in(client, PLAYER)
    await add_member(campaigns, PLAYER)

    response = await client.get("/api/campaigns")

    assert response.status_code == 200
    assert (await body(response))["campaigns"][0]["role"] == "pending"


async def test_a_stranger_lists_nothing(client):
    await sign_in(client, "777")

    response = await client.get("/api/campaigns")

    assert response.status_code == 200
    assert await body(response) == {"campaigns": []}


async def test_a_stranger_gets_a_404_for_the_detail(client):
    await sign_in(client, "777")

    response = await client.get(f"/api/campaigns/{SLUG}")

    assert response.status_code == 404
    assert (await body(response))["error"]["code"] == "not_found"


async def test_a_campaign_outside_the_users_guilds_is_a_404(client):
    await sign_in(client, NARRATOR, {OTHER_GUILD})

    response = await client.get(f"/api/campaigns/{SLUG}")

    assert response.status_code == 404


async def test_an_unknown_slug_is_a_404(client):
    await sign_in(client, NARRATOR)

    response = await client.get("/api/campaigns/nowhere")

    assert response.status_code == 404
    assert (await body(response))["error"]["code"] == "not_found"


async def test_the_detail_reports_the_role_and_no_open_table(client):
    await sign_in(client, NARRATOR)

    response = await client.get(f"/api/campaigns/{SLUG}")

    assert response.status_code == 200
    assert await body(response) == {
        "slug": SLUG,
        "name": "Paratheos",
        "system": "fate",
        "role": "narrator",
        "open_table": None,
        "config_error": None,
    }


async def test_reading_a_campaign_does_not_write(client, campaigns):
    await sign_in(client, NARRATOR)

    await client.get("/api/campaigns")
    await client.get(f"/api/campaigns/{SLUG}")

    row = await campaigns.fetchone(
        "SELECT "
        "(SELECT COUNT(*) FROM campaigns) AS campaigns, "
        "(SELECT COUNT(*) FROM members) AS members, "
        "(SELECT COUNT(*) FROM sheet_files) AS sheets"
    )
    assert row is not None
    assert (row["campaigns"], row["members"], row["sheets"]) == (1, 0, 0)


async def guard(
    method: str,
    headers: dict[str, str] | None = None,
):
    async with quart_app.test_request_context(
        "/api/campaigns", method=method, headers=headers or {}
    ):
        return await guard_campaign_request()


def status(response) -> int | None:
    return None if response is None else response.status_code


@pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
async def test_safe_methods_need_no_csrf_proof(method: str):
    assert status(await guard(method)) is None


async def test_a_json_mutation_from_the_same_origin_passes():
    response = await guard(
        "POST",
        {
            "Content-Type": "application/json",
            "Sec-Fetch-Site": "same-origin",
        },
    )

    assert response is None


async def test_a_mutation_without_a_content_type_is_forbidden():
    response = await guard("POST", {"Sec-Fetch-Site": "same-origin"})

    assert status(response) == 403


async def test_a_form_post_is_forbidden():
    response = await guard(
        "POST",
        {
            "Content-Type": "application/x-www-form-urlencoded",
            "Sec-Fetch-Site": "same-origin",
        },
    )

    assert status(response) == 403


async def test_a_cross_site_mutation_is_forbidden():
    response = await guard(
        "POST",
        {
            "Content-Type": "application/json",
            "Sec-Fetch-Site": "cross-site",
            "Origin": "https://evil.example",
        },
    )

    assert status(response) == 403


async def test_same_site_passes_when_the_origin_is_trusted():
    response = await guard(
        "PATCH",
        {
            "Content-Type": "application/json",
            "Sec-Fetch-Site": "same-site",
            "Origin": "https://harpi.smileydroid.com.br",
        },
    )

    assert response is None


async def test_same_site_with_an_untrusted_origin_is_forbidden():
    response = await guard(
        "DELETE",
        {
            "Content-Type": "application/json",
            "Sec-Fetch-Site": "same-site",
            "Origin": "https://evil.example",
        },
    )

    assert status(response) == 403


async def test_a_missing_fetch_site_falls_back_to_the_origin():
    response = await guard(
        "POST",
        {
            "Content-Type": "application/json",
            "Origin": "http://localhost",
        },
    )

    assert response is None


async def test_a_missing_fetch_site_without_an_origin_is_forbidden():
    response = await guard("POST", {"Content-Type": "application/json"})

    assert status(response) == 403


async def test_a_missing_fetch_site_rejects_a_different_port():
    response = await guard(
        "POST",
        {
            "Content-Type": "application/json",
            "Origin": "http://localhost:8080",
        },
    )

    assert status(response) == 403


async def test_a_multipart_mutation_is_forbidden_until_an_upload_route_asks_for_it():
    response = await guard(
        "POST",
        {
            "Content-Type": "multipart/form-data",
            "Sec-Fetch-Site": "same-origin",
        },
    )

    assert status(response) == 403


async def test_the_forbidden_answer_uses_the_error_envelope():
    response = await guard("POST", {"Sec-Fetch-Site": "same-origin"})

    assert response is not None
    assert (await body(response))["error"]["code"] == "forbidden"
