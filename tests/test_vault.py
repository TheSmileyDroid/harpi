from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import app as quart_app
from pages.guard import vault_unavailable
from src.config import Settings
from src.panel import vault

SHEET_ROUTE = "/api/campaigns/paratheos/characters"


@pytest.fixture(autouse=True)
def reset_vault():
    yield
    vault.configure(vault.Vault())


def test_no_configured_path_is_unavailable(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("HARPI_VAULT_PATH", raising=False)

    assert vault.from_settings(Settings.from_env()).available is False


def test_a_missing_root_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("HARPI_VAULT_PATH", str(tmp_path / "missing"))

    assert vault.from_settings(Settings.from_env()).available is False


def test_an_existing_root_is_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("HARPI_VAULT_PATH", str(tmp_path))

    configured = vault.from_settings(Settings.from_env())

    assert configured.available is True
    assert configured.root == tmp_path


def test_the_configuration_is_read_once():
    configured = vault.Vault(root=Path("/vault"))

    vault.configure(configured)

    assert vault.configured() == configured


async def test_a_sheet_route_answers_503_without_the_vault():
    vault.configure(vault.Vault())

    async with quart_app.test_request_context(SHEET_ROUTE):
        response = vault_unavailable()

        assert response is not None
        assert response.status_code == 503
        payload = json.loads(await response.get_data())
        assert payload["error"]["code"] == "vault_unavailable"


async def test_a_sheet_route_passes_when_the_vault_is_available(
    tmp_path: Path,
):
    vault.configure(vault.Vault(root=tmp_path))

    async with quart_app.test_request_context(SHEET_ROUTE):
        assert vault_unavailable() is None
