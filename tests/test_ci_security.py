"""Tests for the CI scanner workflow and the pinned build inputs."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "security.yml"
DEPENDABOT = ROOT / ".github" / "dependabot.yml"
MAKEFILE = ROOT / "Makefile"
DOCKERFILE = ROOT / "Dockerfile"

ACTION_REF = re.compile(r"uses:\s*(\S+)")
PINNED_ACTION = re.compile(r"^[\w.-]+/[\w./-]*@[0-9a-f]{40}$")
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}(?=\s|$)")
GITLEAKS_IMAGE = re.compile(
    r"ghcr\.io/gitleaks/gitleaks@sha256:[0-9a-f]{64}(?=\s|$)"
)


def make_target(name: str) -> str:
    text = MAKEFILE.read_text(encoding="utf-8")
    start = text.index(f"\n{name}:\n") + 1
    end = text.find("\n\n", start)

    return text[start:] if end == -1 else text[start:end]


def test_workflow_pins_every_action_to_a_commit():
    refs = ACTION_REF.findall(WORKFLOW.read_text(encoding="utf-8"))

    assert refs
    assert [ref for ref in refs if not PINNED_ACTION.match(ref)] == []


def test_workflow_pins_the_scanner_image_by_digest():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert GITLEAKS_IMAGE.search(text) is not None


def test_workflow_runs_the_three_scanners_on_their_inputs():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "Scan the history with gitleaks" in text
    assert "Scan the lockfiles with osv-scanner" in text
    assert "Scan the image with trivy" in text
    assert "--lockfile=uv.lock" in text
    assert "--lockfile=web/bun.lock" in text
    assert "exit-code: 1" in text


def test_workflow_needs_no_secret_beyond_the_default_token():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "secrets." not in text
    assert "permissions:" in text
    assert "contents: read" in text


def test_dockerfile_pins_both_base_images_by_digest():
    from_lines = [
        line
        for line in DOCKERFILE.read_text(encoding="utf-8").splitlines()
        if line.startswith("FROM ")
    ]

    assert len(from_lines) == 2
    assert [line for line in from_lines if not DIGEST.search(line)] == []


def test_dependabot_covers_python_bun_docker_and_actions():
    text = DEPENDABOT.read_text(encoding="utf-8")

    for ecosystem in ("uv", "bun", "docker", "github-actions"):
        assert f'package-ecosystem: "{ecosystem}"' in text
    assert 'directory: "/web"' in text


def test_make_security_runs_each_local_scanner():
    target = make_target("security")

    assert "gitleaks detect" in target
    assert "osv-scanner scan source" in target
    assert "trivy image" in target
