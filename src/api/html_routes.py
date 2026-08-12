from __future__ import annotations

from quart import Blueprint, redirect, render_template, url_for

from src.api.panel_context import resolve_page_context

bp = Blueprint("html_routes", __name__)


@bp.route("/")
async def index():
    """Entry point: land on the dashboard."""
    return redirect(url_for("html_routes.route", page="dashboard"))


@bp.route("/pages/<path:page>")
async def route(page):
    """Render a panel page with only the context it resolves."""
    context = await resolve_page_context(page)
    return await render_template(f"pages/{page}.html", **context)
