"""Export openapi.json file."""

import json
from pathlib import Path

from app import app

with Path(Path.cwd() / "frontend" / "openapi.json").open(
    "w",
    encoding="utf-8",
) as f:
    f.write(json.dumps(app.openapi()))
