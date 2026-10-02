"""The app serves the built Svelte SPA at the root and under its asset paths."""

from __future__ import annotations

import pytest

import app as app_module
from app import app as quart_app


@pytest.fixture
def built(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<!doctype html><title>Harpi</title>")
    assets = tmp_path / "_app"
    assets.mkdir()
    (assets / "app.js").write_text("console.log('hi')")
    monkeypatch.setattr(app_module, "WEB_BUILD", tmp_path)
    return tmp_path


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    quart_app.secret_key = "test-secret"
    quart_app.config["TESTING"] = True
    return quart_app.test_client()


@pytest.mark.usefixtures("built")
async def test_root_serves_the_built_index(client):
    response = await client.get("/")

    assert response.status_code == 200
    assert b"Harpi" in await response.get_data()


@pytest.mark.usefixtures("built")
async def test_root_serves_built_assets(client):
    response = await client.get("/_app/app.js")

    assert response.status_code == 200
    assert b"console.log" in await response.get_data()


@pytest.mark.usefixtures("built")
async def test_missing_asset_is_a_plain_404(client):
    response = await client.get("/nope.js")

    assert response.status_code == 404
    assert response.content_type.startswith("text/html")


@pytest.mark.usefixtures("built")
async def test_api_paths_keep_the_json_envelope(client):
    response = await client.get("/api/status")

    assert response.status_code == 401
    assert response.content_type.startswith("application/json")
