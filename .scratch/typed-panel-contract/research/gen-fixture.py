"""Regenerate the OpenAPI fixture used by 01-openapi-generator.md.

Run with the repo venv (quart-schema 0.23.0, pydantic 2.13.4):

    .venv/bin/python .scratch/typed-panel-contract/research/gen-fixture.py

Writes qs-openapi.json (raw quart-schema dump) and qs-events.json (same
document with the SSE union componentized, the shape the contract export
must produce). The componentization mirrors what ticket 02 must add to
quart-schema's OpenAPIProvider: quart-schema inlines the top-level
response model and rejects a union response model.
"""

import json
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field
from quart import Quart
from quart_schema import Info, QuartSchema, validate_request, validate_response


def _coerce_snowflake(value):
    if isinstance(value, int):
        return str(value)
    return value


Snowflake = Annotated[
    str,
    BeforeValidator(_coerce_snowflake),
    Field(description="Snowflake id on the wire"),
]


class Track(BaseModel):
    id: Snowflake
    title: str
    duration_s: float | None = None
    requested_by: str | None = None
    thumbnail: str | None = None


class Layers(BaseModel):
    loop: bool = False
    autoplay: bool = False


class StatusSnapshot(BaseModel):
    """Fresh status snapshot."""

    connected: bool
    guild_id: Snowflake | None = None
    now_playing: Track | None = None
    queue: list[Track]
    layers: Layers


class ConnectRequest(BaseModel):
    guild_id: int | str


app = Quart(__name__)
QuartSchema(app, info=Info(title="Harpi panel", version="1.0.0"))


@app.get("/api/status")
@validate_response(StatusSnapshot)
async def get_status():
    ...


@app.post("/api/connect")
@validate_request(ConnectRequest)
@validate_response(StatusSnapshot)
async def post_connect(data: ConnectRequest):
    ...


raw = app.extensions["QUART_SCHEMA"].openapi_provider.schema()
assert raw["openapi"] == "3.1.0"
with open("qs-openapi.json", "w") as fh:
    json.dump(raw, fh, indent=2)

document = json.loads(json.dumps(raw))
inline = document["paths"]["/api/status"]["get"]["responses"]["200"]["content"][
    "application/json"
]["schema"]
schemas = document["components"]["schemas"]
schemas["StatusSnapshot"] = inline
schemas["StatusEvent"] = {
    "type": "object",
    "required": ["event", "payload"],
    "properties": {
        "event": {"const": "status"},
        "payload": {"$ref": "#/components/schemas/StatusSnapshot"},
    },
}
schemas["ReloadEvent"] = {
    "type": "object",
    "required": ["event", "payload"],
    "properties": {
        "event": {"const": "reload"},
        "payload": {
            "type": "object",
            "required": ["reason"],
            "properties": {"reason": {"type": "string"}},
        },
    },
}
schemas["PanelEvent"] = {
    "oneOf": [
        {"$ref": "#/components/schemas/StatusEvent"},
        {"$ref": "#/components/schemas/ReloadEvent"},
    ],
    "discriminator": {
        "propertyName": "event",
        "mapping": {
            "status": "#/components/schemas/StatusEvent",
            "reload": "#/components/schemas/ReloadEvent",
        },
    },
}
document["paths"]["/api/events"] = {
    "get": {
        "operationId": "get_get_events",
        "responses": {
            "200": {
                "description": "stream",
                "content": {
                    "text/event-stream": {
                        "schema": {"$ref": "#/components/schemas/PanelEvent"}
                    }
                },
            }
        },
    }
}
with open("qs-events.json", "w") as fh:
    json.dump(document, fh, indent=2)
