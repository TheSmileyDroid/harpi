"""Tests for the Nginx Proxy Manager host plan and the verification scripts."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deploy" / "npm-proxy-host.sh"
VERIFY = ROOT / "deploy" / "verify-proxy.sh"
ADMIN_CHECK = ROOT / "deploy" / "check-admin-exposure.sh"
FAIL2BAN_INSTALL = ROOT / "deploy" / "fail2ban" / "install.sh"
HOSTNAME = "harpi.smileydroid.com.br"
UNREACHABLE_URL = "http://127.0.0.1:9"


def run(
    *arguments: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPT), *arguments],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def plan(*arguments: str) -> dict[str, object]:
    completed = run("--url", UNREACHABLE_URL, *arguments)
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def create_body() -> dict[str, object]:
    return plan()["create"]["body"]


def tls_body() -> dict[str, object]:
    return plan("--certificate", "new")["attach_certificate"]["body"]


def test_create_body_forwards_the_panel_over_the_edge_network():
    body = create_body()

    assert body["domain_names"] == [HOSTNAME]
    assert (
        body["forward_scheme"],
        body["forward_host"],
        body["forward_port"],
    ) == (
        "http",
        "harpi-backend",
        8000,
    )


def test_create_body_leaves_tls_off_because_npm_drops_it_without_a_certificate():
    body = create_body()

    assert body["certificate_id"] == 0
    assert body["ssl_forced"] is False
    assert body["http2_support"] is False
    assert body["hsts_enabled"] is False


def test_attaching_a_certificate_enables_forced_https_http2_and_hsts_without_subdomains():
    body = tls_body()

    assert body["certificate_id"] == "new"
    assert body["ssl_forced"] is True
    assert body["http2_support"] is True
    assert body["hsts_enabled"] is True
    assert body["hsts_subdomains"] is False


def test_an_existing_certificate_can_be_attached_by_id():
    body = plan("--certificate", "7")["attach_certificate"]["body"]

    assert body["certificate_id"] == 7
    assert body["ssl_forced"] is True


def test_websocket_upgrade_and_block_exploits_are_on_and_caching_is_off():
    body = tls_body()

    assert body["allow_websocket_upgrade"] is True
    assert body["block_exploits"] is True
    assert body["caching_enabled"] is False
    assert body["access_list_id"] == 0


def test_advanced_config_disables_server_tokens_and_buffering_for_the_stream():
    text = tls_body()["advanced_config"]

    assert "server_tokens off;" in text
    assert "proxy_buffering off;" in text
    assert "proxy_read_timeout 1h;" in text
    assert "proxy_send_timeout 1h;" in text


def test_advanced_config_leaves_body_and_rate_limits_to_the_rate_limit_ticket():
    text = tls_body()["advanced_config"]

    assert "client_max_body_size" not in text
    assert "limit_req" not in text
    assert "limit_conn" not in text


def test_plan_reports_the_query_and_the_create_without_touching_the_network():
    completed = run("--url", UNREACHABLE_URL)

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["query"]["method"] == "GET"
    assert report["create"]["method"] == "POST"
    assert report["attach_certificate"] is None


def test_plan_without_a_certificate_requests_no_certificate():
    report = plan()

    assert report["attach_certificate"] is None


def test_apply_refuses_without_credentials():
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in {"NPM_TOKEN", "NPM_IDENTITY", "NPM_PASSWORD"}
    }

    completed = run("--apply", env=environment)

    assert completed.returncode == 1
    assert "NPM_TOKEN" in completed.stderr


def test_apply_and_check_are_exclusive():
    completed = run("--apply", "--check", "--url", UNREACHABLE_URL)

    assert completed.returncode == 1
    assert "exclusive" in completed.stderr


def test_unknown_flag_fails_with_usage():
    completed = run("--flush")

    assert completed.returncode == 2
    assert "usage:" in completed.stderr


def test_a_bad_certificate_value_fails_loudly():
    completed = run("--certificate", "expired", "--url", UNREACHABLE_URL)

    assert completed.returncode == 1
    assert "new or a certificate id" in completed.stderr


@pytest.mark.parametrize(
    "script",
    [SCRIPT, VERIFY, ADMIN_CHECK, FAIL2BAN_INSTALL],
    ids=lambda path: path.name,
)
def test_shell_scripts_parse(script: Path):
    completed = subprocess.run(
        ["bash", "-n", str(script)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_verification_script_never_writes():
    text = VERIFY.read_text()

    for verb in (
        "-X POST",
        "-X PUT",
        "-X DELETE",
        "iptables",
        "docker restart",
    ):
        assert verb not in text
