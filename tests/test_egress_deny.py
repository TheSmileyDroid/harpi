"""Tests for the edge egress rule renderer."""

from __future__ import annotations

import ipaddress
import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "deploy" / "egress-deny.sh"
CHAIN = "DOCKER-USER"
TAG = "harpi-egress-deny"
SOURCE = "172.20.0.5"
IPV6_SOURCE = "fd00::5"
IPV4_DESTINATIONS = {
    "127.0.0.0/8",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "169.254.0.0/16",
    "224.0.0.0/4",
}
IPV6_DESTINATIONS = {"::1/128", "fc00::/7", "fe80::/10", "ff00::/8"}
FAKE_IPTABLES = """#!/usr/bin/env bash
set -euo pipefail
case "$1" in
  -S)
    printf -- '-N DOCKER-USER\\n'
    sed 's/^/-A /' "$STATE"
    ;;
  -C)
    shift
    grep -Fqx -- "$*" "$STATE"
    ;;
  -I)
    shift
    printf '%s\\n' "$*" >> "$STATE"
    ;;
  -D)
    shift
    grep -Fvx -- "$*" "$STATE" > "$STATE.new" || true
    mv "$STATE.new" "$STATE"
    ;;
esac
"""


def run_script(
    *arguments: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPT), *arguments],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def render(*sources: str) -> list[list[str]]:
    arguments = ["print"]
    for source in sources:
        arguments += ["--source", source]
    completed = run_script(*arguments)
    assert completed.returncode == 0, completed.stderr
    return [line.split() for line in completed.stdout.splitlines()]


def destinations(rules: list[list[str]]) -> set[str]:
    return {rule[rule.index("-d") + 1] for rule in rules}


def fake_environment(tmp_path: Path) -> dict[str, str]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    iptables = fake_bin / "iptables"
    iptables.write_text(FAKE_IPTABLES)
    iptables.chmod(0o755)
    state = tmp_path / "rules"
    state.touch()
    return {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "STATE": str(state),
    }


def test_ipv4_rules_target_the_docker_user_chain():
    rules = render(SOURCE)

    assert len(rules) == len(IPV4_DESTINATIONS)
    for rule in rules:
        assert rule[:3] == ["iptables", "-I", CHAIN]
        assert rule[-4:] == ["--comment", TAG, "-j", "DROP"]


def test_private_link_local_and_multicast_destinations_are_denied():
    assert destinations(render(SOURCE)) == IPV4_DESTINATIONS


def test_link_local_rule_covers_the_metadata_address():
    metadata = ipaddress.ip_address("169.254.169.254")

    assert any(
        metadata in ipaddress.ip_network(destination)
        for destination in destinations(render(SOURCE))
    )


def test_no_blocked_network_is_a_public_unicast_destination():
    for destination in IPV4_DESTINATIONS | IPV6_DESTINATIONS:
        network = ipaddress.ip_network(destination)
        assert not network.is_global or network.is_multicast


def test_ipv6_source_uses_ip6tables():
    rules = render(IPV6_SOURCE)

    assert len(rules) == len(IPV6_DESTINATIONS)
    assert {rule[0] for rule in rules} == {"ip6tables"}
    assert destinations(rules) == IPV6_DESTINATIONS


def test_each_source_renders_its_own_rule_set():
    rules = render(SOURCE, IPV6_SOURCE)

    assert len(rules) == len(IPV4_DESTINATIONS) + len(IPV6_DESTINATIONS)


def test_apply_inserts_each_rule_once(tmp_path: Path):
    environment = fake_environment(tmp_path)
    state = Path(environment["STATE"])

    first = run_script("apply", "--source", SOURCE, env=environment)
    second = run_script("apply", "--source", SOURCE, env=environment)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert "installed 6 rule(s)" in first.stdout
    assert "installed 0 rule(s)" in second.stdout
    assert len(state.read_text().splitlines()) == 6


def test_remove_deletes_the_tagged_rules(tmp_path: Path):
    environment = fake_environment(tmp_path)
    state = Path(environment["STATE"])
    run_script("apply", "--source", SOURCE, env=environment)

    removed = run_script("remove", env=environment)

    assert removed.returncode == 0, removed.stderr
    assert "removed 6 rule(s)" in removed.stdout
    assert state.read_text() == ""


def test_unknown_action_fails_loudly():
    completed = run_script("flush")

    assert completed.returncode == 2
    assert "usage:" in completed.stderr
