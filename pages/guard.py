from __future__ import annotations

from urllib.parse import urlsplit

from quart import Response, current_app, request
from werkzeug.wsgi import host_is_trusted

from pages.api import error_response
from src.panel import vault

JSON_MIMETYPE = "application/json"
MULTIPART_MIMETYPE = "multipart/form-data"
MUTATING_METHODS: frozenset[str] = frozenset({"POST", "PATCH", "DELETE"})


def _forbidden() -> Response:
    return error_response("forbidden", "Forbidden", 403)


def _content_type_allowed(allow_multipart: bool) -> bool:
    mimetype = request.mimetype
    if mimetype == JSON_MIMETYPE:
        return True
    return allow_multipart and mimetype == MULTIPART_MIMETYPE


def _origin_hostname(origin: str) -> str | None:
    parsed = urlsplit(origin)
    if parsed.scheme not in ("http", "https"):
        return None
    return parsed.hostname


def _same_origin(origin: str) -> bool:
    parsed = urlsplit(origin)
    if parsed.scheme not in ("http", "https"):
        return False
    return parsed.netloc.casefold() == request.host.casefold()


def _trusted_origin(origin: str) -> bool:
    hostname = _origin_hostname(origin)
    return hostname is not None and host_is_trusted(
        hostname, current_app.config["TRUSTED_HOSTS"]
    )


def csrf_refusal(*, allow_multipart: bool = False) -> Response | None:
    if request.method not in MUTATING_METHODS:
        return None
    if not _content_type_allowed(allow_multipart):
        return _forbidden()
    return None if _fetch_metadata_allows() else _forbidden()


def _fetch_metadata_allows() -> bool:
    site = request.headers.get("Sec-Fetch-Site")
    origin = request.headers.get("Origin")
    if site == "same-origin":
        return True
    if site == "same-site":
        return origin is not None and _trusted_origin(origin)
    if site is not None:
        return False
    return origin is not None and _same_origin(origin)


def vault_unavailable() -> Response | None:
    if vault.configured().available:
        return None
    return error_response("vault_unavailable", "Vault unavailable", 503)
