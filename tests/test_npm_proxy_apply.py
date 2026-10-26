"""End-to-end tests for the proxy host script against a fake NPM admin API."""

from __future__ import annotations

import json
import os
import subprocess
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deploy" / "npm-proxy-host.sh"
HOSTNAME = "harpi.smileydroid.com.br"


def normalize(host: dict[str, Any]) -> None:
    if not host.get("certificate_id"):
        host["ssl_forced"] = False
        host["http2_support"] = False
    if not host.get("ssl_forced"):
        host["hsts_enabled"] = False
    if not host.get("hsts_enabled"):
        host["hsts_subdomains"] = False


class FakeNpm:
    def __init__(self) -> None:
        self.hosts: dict[int, dict[str, Any]] = {}
        self.next_id = 1
        self.certificate_id = 0
        self.calls: list[tuple[str, str]] = []

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        host = dict(payload)
        if host.get("certificate_id") == "new":
            host.pop("certificate_id")
        host["id"] = self.next_id
        self.next_id += 1
        normalize(host)
        self.hosts[host["id"]] = host
        return host

    def update(self, host_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        host = {**self.hosts[host_id], **payload}
        if host.get("certificate_id") == "new":
            self.certificate_id += 1
            host["certificate_id"] = self.certificate_id
        normalize(host)
        self.hosts[host_id] = host
        return host


class Handler(BaseHTTPRequestHandler):
    npm: FakeNpm

    def log_message(self, format: str, *args: object) -> None:
        return

    def reply(self, status: int, payload: Any) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def host_id(self) -> int | None:
        if not self.path.startswith("/api/nginx/proxy-hosts/"):
            return None
        return int(self.path.rsplit("/", 1)[1])

    def do_POST(self) -> None:
        self.npm.calls.append(("POST", self.path))
        if self.path == "/api/tokens":
            self.body()
            self.reply(200, {"token": "test-token", "expires": 3600})
            return
        if self.path == "/api/nginx/proxy-hosts":
            self.reply(201, self.npm.create(self.body()))
            return
        self.reply(404, {"error": {"code": 404}})

    def do_GET(self) -> None:
        self.npm.calls.append(("GET", self.path))
        if self.path == "/api/nginx/proxy-hosts":
            self.reply(200, list(self.npm.hosts.values()))
            return
        host_id = self.host_id()
        if host_id in self.npm.hosts:
            self.reply(200, self.npm.hosts[host_id])
            return
        self.reply(404, {"error": {"code": 404}})

    def do_PUT(self) -> None:
        self.npm.calls.append(("PUT", self.path))
        host_id = self.host_id()
        if host_id in self.npm.hosts:
            self.reply(200, self.npm.update(host_id, self.body()))
            return
        self.reply(404, {"error": {"code": 404}})


def handler_for(npm: FakeNpm) -> type[BaseHTTPRequestHandler]:
    return type("BoundHandler", (Handler,), {"npm": npm})


@pytest.fixture(name="npm")
def npm_fixture() -> Iterator[tuple[FakeNpm, str]]:
    npm = FakeNpm()
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(npm))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield npm, f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()


def apply(base_url: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = {
        **os.environ,
        "NPM_IDENTITY": "operator@example.com",
        "NPM_PASSWORD": "secret",
    }
    environment.pop("NPM_TOKEN", None)
    return subprocess.run(
        [str(SCRIPT), "--apply", "--url", base_url, *arguments],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )


def test_apply_creates_the_host_and_requests_the_certificate(
    npm: tuple[FakeNpm, str],
):
    state, base_url = npm

    completed = apply(base_url, "--certificate", "new")

    assert completed.returncode == 0, completed.stderr
    assert len(state.hosts) == 1
    host = next(iter(state.hosts.values()))
    assert host["domain_names"] == [HOSTNAME]
    assert (
        host["forward_scheme"],
        host["forward_host"],
        host["forward_port"],
    ) == (
        "http",
        "harpi-backend",
        8000,
    )
    assert host["certificate_id"] == 1
    assert host["ssl_forced"] is True
    assert host["http2_support"] is True
    assert host["hsts_enabled"] is True
    assert host["hsts_subdomains"] is False
    assert host["allow_websocket_upgrade"] is True


def test_a_second_apply_reuses_the_certificate_and_the_host(
    npm: tuple[FakeNpm, str],
):
    state, base_url = npm
    assert apply(base_url, "--certificate", "new").returncode == 0

    completed = apply(base_url, "--certificate", "new")

    assert completed.returncode == 0, completed.stderr
    assert len(state.hosts) == 1
    assert state.certificate_id == 1
    creates = [
        call
        for call in state.calls
        if call == ("POST", "/api/nginx/proxy-hosts")
    ]
    assert len(creates) == 1


def test_apply_without_a_certificate_creates_a_host_without_tls(
    npm: tuple[FakeNpm, str],
):
    state, base_url = npm

    completed = apply(base_url)

    assert completed.returncode == 0, completed.stderr
    host = next(iter(state.hosts.values()))
    assert host["certificate_id"] == 0
    assert host["ssl_forced"] is False
    assert host["hsts_enabled"] is False
    assert "no certificate attached" in completed.stdout


def test_apply_refuses_to_run_with_two_hosts_for_the_hostname(
    npm: tuple[FakeNpm, str],
):
    state, base_url = npm
    state.create({"domain_names": [HOSTNAME], "certificate_id": 0})
    state.create({"domain_names": [HOSTNAME], "certificate_id": 0})

    completed = apply(base_url, "--certificate", "new")

    assert completed.returncode == 1
    assert "remove the extra rows" in completed.stderr
    assert len(state.hosts) == 2


def test_check_reports_a_single_host(npm: tuple[FakeNpm, str]):
    state, base_url = npm
    state.create({"domain_names": [HOSTNAME], "certificate_id": 0})

    completed = subprocess.run(
        [str(SCRIPT), "--check", "--url", base_url],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "NPM_TOKEN": "test-token"},
    )

    assert completed.returncode == 0, completed.stderr
    assert f"one host claims {HOSTNAME}" in completed.stdout
