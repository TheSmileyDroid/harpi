"""Every response carries the security headers and public mode closes the docs."""

from __future__ import annotations

from dataclasses import replace

import pytest

import app as app_module
from app import DOCUMENTATION_PATHS, SECURITY_HEADERS
from app import app as quart_app
from app import configure_security
from src.config import Settings

SECRET = "test-secret"


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
    monkeypatch.setenv("SECRET_KEY", SECRET)
    monkeypatch.delenv("PANEL_PUBLIC_MODE", raising=False)
    configure_security(Settings.from_env())
    quart_app.secret_key = SECRET
    quart_app.config["TESTING"] = True
    return quart_app.test_client()


@pytest.fixture
def public_client(client):
    configure_security(replace(Settings.from_env(), public_mode=True))
    yield client
    configure_security(replace(Settings.from_env(), public_mode=False))


def assert_security_headers(response):
    for name, value in SECURITY_HEADERS.items():
        assert response.headers.get(name) == value


@pytest.mark.usefixtures("built")
async def test_html_response_carries_the_security_headers(client):
    response = await client.get("/")

    assert response.status_code == 200
    assert_security_headers(response)


async def test_api_response_carries_the_security_headers(client):
    response = await client.get("/api/status")

    assert response.status_code == 401
    assert_security_headers(response)


@pytest.mark.usefixtures("built")
async def test_error_response_carries_the_security_headers(client):
    response = await client.get("/nope.js")

    assert response.status_code == 404
    assert_security_headers(response)


@pytest.mark.usefixtures("built")
async def test_static_asset_carries_the_security_headers(client):
    response = await client.get("/_app/app.js")

    assert response.status_code == 200
    assert_security_headers(response)


async def test_hsts_is_one_year_without_subdomains_or_preload(client):
    response = await client.get("/api/status")
    hsts = response.headers["Strict-Transport-Security"]

    assert hsts == "max-age=31536000"
    assert "includeSubDomains" not in hsts
    assert "preload" not in hsts


async def test_csp_forbids_framing_and_objects(client):
    response = await client.get("/api/status")
    csp = response.headers["Content-Security-Policy"]

    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp


@pytest.mark.parametrize("path", sorted(DOCUMENTATION_PATHS))
async def test_documentation_is_hidden_in_public_mode(public_client, path):
    response = await public_client.get(path)

    assert response.status_code == 404


@pytest.mark.parametrize("path", sorted(DOCUMENTATION_PATHS))
async def test_documentation_is_available_outside_public_mode(client, path):
    response = await client.get(path)

    assert response.status_code == 200
