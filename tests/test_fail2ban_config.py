"""Tests for the fail2ban filters and jail covering the proxy auth surface."""

from __future__ import annotations

import configparser
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILTERS = ROOT / "deploy" / "fail2ban" / "filter.d"
JAIL = ROOT / "deploy" / "fail2ban" / "jail.d" / "harpi-edge.local"
ADMIN_LOG_LINE = (
    "[26/Oct/2026:11:00:00 +0000] {status} - POST http nginxproxymanager "
    '"/api/tokens" [Client 100.64.0.2] [Length 47] [Gzip -] "curl/8.5.0" "-"'
)
PROXY_LOG_LINE = (
    "[26/Oct/2026:11:00:00 +0000] - {upstream} {status} - {method} https "
    'harpi.smileydroid.com.br "{path}" [Client 203.0.113.5] [Length 47] '
    '[Gzip -] "curl/8.5.0" "-"'
)


def failregexes(name: str) -> list[re.Pattern[str]]:
    lines = (FILTERS / name).read_text().splitlines()
    definition = next(line for line in lines if line.startswith("failregex"))
    value = definition.split("=", 1)[1]
    return [
        re.compile(expression.strip().replace("<HOST>", r"\S+"))
        for expression in value.splitlines()
        if expression.strip()
    ]


def matches(name: str, line: str) -> bool:
    return any(expression.search(line) for expression in failregexes(name))


def jail() -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(JAIL)
    return parser


def test_admin_login_failures_match_the_admin_filter():
    assert matches("npm-admin-auth.conf", ADMIN_LOG_LINE.format(status=401))
    assert matches("npm-admin-auth.conf", ADMIN_LOG_LINE.format(status=403))


def test_successful_admin_logins_and_reads_do_not_match():
    assert not matches(
        "npm-admin-auth.conf", ADMIN_LOG_LINE.format(status=200)
    )
    assert not matches(
        "npm-admin-auth.conf",
        ADMIN_LOG_LINE
        .format(status=200)
        .replace("POST", "GET")
        .replace("/api/tokens", "/"),
    )


def test_panel_auth_failures_match_the_proxy_filter():
    line = PROXY_LOG_LINE.format(
        upstream=401, status=401, method="POST", path="/api/auth/discord"
    )

    assert matches("harpi-auth.conf", line)


def test_successful_panel_requests_and_other_paths_do_not_match():
    successful = PROXY_LOG_LINE.format(
        upstream=200, status=200, method="GET", path="/api/auth/discord"
    )
    other_path = PROXY_LOG_LINE.format(
        upstream=401, status=401, method="GET", path="/api/guilds"
    )

    assert not matches("harpi-auth.conf", successful)
    assert not matches("harpi-auth.conf", other_path)


def test_jail_covers_the_proxy_admin_surface_the_panel_and_ssh():
    parser = jail()

    assert set(parser.sections()) >= {"npm-admin-auth", "harpi-auth", "sshd"}
    for section in ("npm-admin-auth", "harpi-auth", "sshd"):
        assert parser.getboolean(section, "enabled") is True
    assert parser.get("npm-admin-auth", "filter") == "npm-admin-auth"
    assert parser.get("harpi-auth", "filter") == "harpi-auth"
    assert parser.get("npm-admin-auth", "action") == "npm-docker-user"
    assert parser.get("harpi-auth", "action") == "npm-docker-user"
    assert parser.get("npm-admin-auth", "port") == "81"


def test_jail_reads_the_admin_and_proxy_access_logs():
    parser = jail()

    assert parser.get("npm-admin-auth", "logpath").endswith("admin_access.log")
    assert parser.get("harpi-auth", "logpath").endswith(
        "proxy-host-*_access.log"
    )


def test_jail_bans_for_an_hour_and_ignores_localhost():
    parser = jail()

    assert parser.get("DEFAULT", "bantime") == "1h"
    assert "127.0.0.1" in parser.get("DEFAULT", "ignoreip")
