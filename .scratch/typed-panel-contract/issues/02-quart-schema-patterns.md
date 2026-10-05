# 02: Establish the quart-schema Pydantic route pattern

**Type:** research
**Status:** resolved
**Blocked by:** None

## Question

How does `quart-schema` 0.23.0 wire Pydantic v2 models into the existing Quart blueprints for request and response validation, and how does that coexist with the app's session guard and error helper?

Cover the exact decorators (`@validate_request`, `@validate_response`) and how a route declares which status codes and which model each answers; how `error_response` and the `app.before_request` session guard interact with validation errors (including the shape of a validation error response and whether it matches the modeled error envelope); how to document `GET /api/events` as `text/event-stream` with a union of SSE payloads; how to attach an OpenAPI security scheme representing the session cookie; and how `format_schema` exposes the document for the export script. Confirm the emitted version is 3.1.0.

The finding decides tickets "Shape the generated module and the typed client", "Rewrite the panel models and convert the API routes", and "Author the export script and the make target".

## Answer

**Emitted document is OpenAPI `3.1.0`.** `OpenAPIProvider.schema()` hardcodes `"openapi": "3.1.0"` (`quart_schema/openapi.py:54`). Confirmed by fetching `/openapi.json` from a live test app.

**`format_schema` does not exist in 0.23.0.** No symbol, method, or CLI by that name anywhere in the installed package. The two real export surfaces:

- `app.extensions["QUART_SCHEMA"].openapi_provider.schema()` returns the document as a dict (`extension.py:274,305`, `openapi.py:48`).
- The `quart schema` click command (`extension.py:353-369`, registered at `extension.py:317`) writes the same dict with `app.json.dumps(schema, indent=2)` to stdout or `--output FILE`.

Recommendation: the export script imports the app and calls `app.extensions["QUART_SCHEMA"].openapi_provider.schema()` then `app.json.dumps(schema, indent=2, sort_keys=True)`. `sort_keys=True` is needed for byte-identical exports because `schema()` walks `url_map.iter_rules()` and returns `defaultdict` paths; the built-in CLI does not sort.

### Request and response decorators

`@validate_request(Model, source=DataSource.JSON)` (`validation.py:121-175`) stores `(Model, source)` on the view, reads `request.get_json()`, builds the model with `TypeAdapter(Model).validate_python(...)`, and calls the handler with `data=<model>`. Failure raises `RequestSchemaValidationError`, a subclass of `werkzeug.BadRequest` (code 400) (`validation.py:34-37`).

`@validate_response(Model, status_code=200, headers_model_class=None)` (`validation.py:178-260`) stores `{status_code: (Model, headers_model_class)}` on the view. Repeated decorators merge into one dict, so a route declares each status it answers by stacking decorators:

```python
@validate_response(StatusSnapshot, 200)
@validate_response(ErrorEnvelope, 404)
async def route(): ...
```

At runtime the wrapper reads the actual status (a tuple's second element, or the `Response.status_code`) and only validates when it equals the decorated `status_code`; otherwise it passes the value through untouched. The provider reads the same dict to emit one response object per status (`openapi.py:175-183`). Response schemas are generated in Pydantic `serialization` mode and request bodies in `validation` mode (`openapi.py:341-345`, `304-309`): the asymmetry that matters for the `Snowflake` string-on-the-wire type.

### Coexistence with the session guard and `error_response`

The guard (`app.py:49-57`) returns `error_response(...)` (a Quart `Response`) from `before_request`, so dispatch never reaches the view and no `@validate_response` wrapper runs on the 401. Safe. The guard's 401 does not appear in OpenAPI by itself; document it per route with `@document_response(ErrorEnvelope, 401)` if wanted.

**`error_response` plus `@validate_response` on the same status is a runtime bug.** The wrapper raises `RuntimeError("Cannot validate Response instance")` when the returned value is a `Response` whose status matches the decorated status (`validation.py:225-229`). `error_response` returns `jsonify(...)` with `status_code` set (`pages/api.py:16-19`), so a route decorated `@validate_response(ErrorEnvelope, 404)` that returns `error_response(...)` answers 500. Proven: `error_response(...)` 404 to a 404-validated route becomes 500; returning `({"error": {...}}, 404)` validates and answers 404.

Recommendation:

- Keep `error_response` for the guard and the global HTTPException handler. Those responses bypass view validation.
- For error statuses documented on a route use `@document_response(ErrorEnvelope, status)` (document-only, `documentation.py:84-114`), and keep `@validate_response` for success statuses. Mixing is safe: a 404 `Response` returned from a route validated only for 200 passes through unchanged.
- Refactoring `error_response` to return `(dict, status)` would let it validate, but that is application-code change and out of scope here.

**Request validation error shape.** With the current handler (`app.py:60-67`), a Pydantic failure arrives as `HTTPException` code 400. `API_ERROR_CODES` has no 400, so `code` is `"error"` and `message` is Werkzeug's generic description:

```
400 {"error": {"code": "error", "message": "The browser (or proxy) sent a request that this server could not understand."}}
```

The shape matches the modeled envelope; the code and message carry no field detail. `RequestSchemaValidationError.validation_error` holds the Pydantic `ValidationError`, available only if a dedicated `@app.errorhandler(RequestSchemaValidationError)` is registered (docs "Handling validation errors"). Add `400: "bad_request"` to `API_ERROR_CODES`, or register that handler, to make the envelope vocabulary match.

**Response validation failure** raises `ResponseSchemaValidationError`, a plain `Exception`, which Quart turns into 500 `InternalServerError` and the same global handler catches:

```
500 {"error": {"code": "internal_error", "message": "The server encountered an internal error..."}}
```

Proven with a wrongly typed response.

### `GET /api/events` as `text/event-stream` with a union

`build_response_object` hardcodes `application/json` (`openapi.py:349-354`), so SSE needs a custom provider:

```python
class SseOpenAPIProvider(OpenAPIProvider):
    def build_response_object(self, model, headers_model):
        obj, components = super().build_response_object(model, headers_model)
        if getattr(model, "__sse__", False):
            obj["content"] = {"text/event-stream": obj["content"].pop("application/json")}
        return obj, components

QuartSchema(app, openapi_provider_class=SseOpenAPIProvider)
```

The union must be a Pydantic `RootModel`. A bare `StatusEvent | ReloadEvent` fails `model_schema` with `TypeError: Cannot create schema`. A wrapper `BaseModel` holding a `payload` field also works but adds a spurious property.

```python
class SseEnvelope(RootModel[StatusEvent | ReloadEvent]):
    """Frames emitted by GET /api/events."""
    __sse__ = True
```

This emits `text/event-stream` with `schema: {anyOf: [{$ref: StatusEvent}, {$ref: ReloadEvent}], description: ...}`. Proven.

Do **not** put `@validate_response` on the events route: it returns a streaming `Response` with status 200, and the wrapper raises `RuntimeError("Cannot validate Response instance")`. Use `@document_response(SseEnvelope, 200)` instead: same document, no runtime wrapper. Proven: validated route answers 500, documented route answers 200 `text/event-stream`.

### Security scheme for the session cookie

```python
QuartSchema(
    app,
    security_schemes={"session": {"type": "apiKey", "name": "session", "in_": "cookie"}},
    security=[{"session": []}],
)
```

The dict key is `in_` (the dataclass field, aliased to `in` in output; `openapi.py:563-567`; docs "Security schemes"). Emits `components.securitySchemes.session = {"type": "apiKey", "name": "session", "in": "cookie"}` and global `security: [{"session": []}]`. The cookie name is Quart's default `"session"` because `app.py` sets no `SESSION_COOKIE_NAME`. Security schemes are documentation only; the real guard stays in `before_request`.

### Recommendation

1. Initialize `QuartSchema(app, info=..., security_schemes=..., security=..., openapi_provider_class=SseOpenAPIProvider)` in `app.py`, after the blueprints register. It is not wired anywhere today (no `QuartSchema` call exists in the repo).
2. Stack `@validate_request`/`@validate_response(..., status)` on success paths. Declare error statuses with `@document_response(ErrorEnvelope, status)` so `error_response`'s `Response` never meets a validating wrapper.
3. Model `/api/events` with `RootModel[StatusEvent | ReloadEvent]` and `@document_response(SseEnvelope, 200)`.
4. Export via `app.extensions["QUART_SCHEMA"].openapi_provider.schema()` plus `app.json.dumps(..., indent=2, sort_keys=True)`. There is no `format_schema`.
5. Add `400: "bad_request"` to `API_ERROR_CODES`, or register a `RequestSchemaValidationError` handler, so the request-validation envelope matches the modeled vocabulary.

### Evidence

- Installed source, version 0.23.0 per `quart_schema-0.23.0.dist-info/METADATA`: `.venv/lib/python3.14/site-packages/quart_schema/{validation,openapi,extension,documentation,conversion}.py`.
- Docs 0.23.0: [error handling](https://quart-schema.readthedocs.io/en/latest/how_to_guides/error_handling.html), [response validation](https://quart-schema.readthedocs.io/en/latest/how_to_guides/response_validation.html), [customising](https://quart-schema.readthedocs.io/en/latest/how_to_guides/customising.html), [security schemes](https://quart-schema.readthedocs.io/en/latest/how_to_guides/security_schemes.html), [documenting](https://quart-schema.readthedocs.io/en/latest/how_to_guides/documenting.html).
- Live ASGI experiments, throwaway and not committed: `/tmp/opencode/qtest.py`, `qtest2.py`, `qtest3.py`, `qtest4.py`, `qtest5.py`.
