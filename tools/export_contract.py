from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONTRACT_DIR = ROOT / "web" / "src" / "lib" / "contract"
DOCUMENT_PATH = CONTRACT_DIR / "openapi.json"


def build_document() -> str:
    from app import app

    provider = app.extensions["QUART_SCHEMA"].openapi_provider
    return app.json.dumps(provider.schema(), indent=2, sort_keys=True)


def main() -> None:
    CONTRACT_DIR.mkdir(parents=True, exist_ok=True)
    DOCUMENT_PATH.write_text(build_document() + "\n")


if __name__ == "__main__":
    main()
