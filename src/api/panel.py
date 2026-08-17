from typing import Any

from quart import current_app, render_template, request
from jinja2_fragments import render_block_async


async def render_page_or_fragment(template: str, ctx: dict[str, Any]) -> str:
    """Render the full page, or just the htmx-requested fragment block.

    An htmx fragment request carries ``HX-Request`` and ``HX-Target``; the
    target element id names the ``{% block %}`` to render alone.
    """
    if "HX-Request" in request.headers:
        block = (request.headers.get("HX-Target") or "").replace("-", "_")
        if block:
            return await render_block_async(
                current_app.jinja_env, template, block, **ctx
            )
    return await render_template(template, **ctx)
