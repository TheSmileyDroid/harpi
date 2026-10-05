from __future__ import annotations

from typing import Any

from quart_schema.openapi import OpenAPIProvider
from quart_schema.typing import Model
from quart_schema.validation import DataSource

COMPONENT_PREFIX = "#/components/schemas"


class ContractOpenAPIProvider(OpenAPIProvider):
    def build_request_body(
        self, model: type[Model], source: DataSource
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        body, components = super().build_request_body(model, source)
        return self._hoist(model, body, components)

    def build_response_object(
        self, model: type[Model], headers_model: type[Model] | None
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        obj, components = super().build_response_object(model, headers_model)
        if getattr(model, "__sse__", False):
            obj["content"]["text/event-stream"] = obj["content"].pop(
                "application/json"
            )
        return self._hoist(model, obj, components)

    @staticmethod
    def _hoist(
        model: type[Model],
        obj: dict[str, Any],
        components: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        content = obj["content"]
        content_type = next(iter(content))
        components[model.__name__] = content[content_type]["schema"]
        content[content_type]["schema"] = {
            "$ref": f"{COMPONENT_PREFIX}/{model.__name__}"
        }
        return obj, components
