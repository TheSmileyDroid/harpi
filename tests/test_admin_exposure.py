"""Tests for the admin exposure check against a fake listener and HTTP client."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deploy" / "check-admin-exposure.sh"
PUBLIC_IP = "203.0.113.10"
TAILSCALE_IP = "100.64.0.1"
FAKE_CURL = """#!/usr/bin/env bash
for argument in "$@"; do url=$argument; done
case $url in
  *203.0.113.10:81*)
    if [[ ${PUBLIC_ANSWERS:-0} == 1 ]]; then
      printf '302'
      exit 0
    fi
    printf '000'
    exit 7
    ;;
  *)
    if [[ ${TAILSCALE_ANSWERS:-1} == 1 ]]; then
      printf '302'
      exit 0
    fi
    printf '000'
    exit 7
    ;;
esac
"""
FAKE_SS = """#!/usr/bin/env bash
if [[ ${FAKE_LISTENER+x} && -z $FAKE_LISTENER ]]; then exit 0; fi
printf 'LISTEN 0 511 %s 0.0.0.0:*\\n' "${FAKE_LISTENER-100.64.0.1:81}"
"""


def environment(tmp_path: Path, **extra: str) -> dict[str, str]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    for name, body in (("curl", FAKE_CURL), ("ss", FAKE_SS)):
        path = fake_bin / name
        path.write_text(body)
        path.chmod(0o755)
    return {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        **extra,
    }


def check(tmp_path: Path, **extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(SCRIPT),
            "--public-ip",
            PUBLIC_IP,
            "--tailscale-ip",
            TAILSCALE_IP,
            "--timeout",
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=environment(tmp_path, **extra),
    )


def test_an_admin_port_that_answers_on_the_public_address_fails(
    tmp_path: Path,
):
    completed = check(tmp_path, PUBLIC_ANSWERS="1")

    assert completed.returncode == 1
    assert f"FAIL {PUBLIC_IP}:81 answered 302" in completed.stdout


def test_a_silent_public_address_and_a_live_tailscale_address_passes(
    tmp_path: Path,
):
    completed = check(tmp_path)

    assert completed.returncode == 0, completed.stdout
    assert f"PASS {TAILSCALE_IP}:81 answered 302" in completed.stdout


def test_a_wildcard_listener_is_reported_without_deciding_alone(
    tmp_path: Path,
):
    completed = check(tmp_path, FAKE_LISTENER="0.0.0.0:81")

    assert completed.returncode == 0, completed.stdout
    assert "WARN port 81 listens on 0.0.0.0:81" in completed.stdout


def test_a_tailscale_address_that_does_not_answer_fails(tmp_path: Path):
    completed = check(tmp_path, TAILSCALE_ANSWERS="0")

    assert completed.returncode == 1
    assert f"FAIL {TAILSCALE_IP}:81 does not answer" in completed.stdout


def test_a_missing_listener_fails(tmp_path: Path):
    completed = subprocess.run(
        [
            str(SCRIPT),
            "--public-ip",
            PUBLIC_IP,
            "--tailscale-ip",
            TAILSCALE_IP,
            "--timeout",
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=environment(tmp_path, FAKE_LISTENER="", PUBLIC_ANSWERS="1"),
    )

    assert completed.returncode == 1
