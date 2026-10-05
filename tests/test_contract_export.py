from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from src.panel.schemas import SSE_EVENTS
from tools.export_contract import build_document

ROOT = Path(__file__).resolve().parents[1]
SSE_CLIENT = ROOT / "web" / "src" / "lib" / "sse.ts"

EXPORT_SNIPPET = "\n".join([
    "import pathlib",
    "import sys",
    "from tools.export_contract import build_document",
    "pathlib.Path(sys.argv[1]).write_text(build_document())",
])


def export_with_hashseed(hashseed: str, target: Path) -> bytes:
    environment = {**os.environ, "PYTHONHASHSEED": hashseed}
    subprocess.run(
        [sys.executable, "-c", EXPORT_SNIPPET, str(target)],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
    )
    return target.read_bytes()


def test_export_is_openapi_3_1():
    document = json.loads(build_document())

    assert document["openapi"] == "3.1.0"
    assert "/api/status" in document["paths"]


def test_export_is_byte_identical_across_processes_and_hash_seeds(tmp_path):
    first = export_with_hashseed("0", tmp_path / "seed0.json")
    second = export_with_hashseed("12345", tmp_path / "seed1.json")

    assert first == second


def test_events_are_documented_as_text_event_stream():
    document = json.loads(build_document())
    content = document["paths"]["/api/events"]["get"]["responses"]["200"][
        "content"
    ]

    assert list(content) == ["text/event-stream"]


def test_top_level_models_are_hoisted_into_components():
    document = json.loads(build_document())
    schemas = set(document["components"]["schemas"])

    assert {
        "StatusSnapshot",
        "ConnectRequest",
        "SearchRequest",
        "ErrorEnvelope",
        "SseEnvelope",
    } <= schemas


def test_emitted_sse_event_names_match_the_client_schema_map():
    block = re.search(
        r"const SSE_SCHEMAS = \{(?P<body>.*?)\} as const;",
        SSE_CLIENT.read_text(),
        re.DOTALL,
    )

    assert block is not None, "SSE_SCHEMAS map not found in sse.ts"
    client_names = set(re.findall(r"(\w+)\s*:", block.group("body")))

    assert client_names == set(SSE_EVENTS)
