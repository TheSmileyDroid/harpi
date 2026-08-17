from quart import Blueprint

from src.api.deps import get_bot
from src.api.panel import render_page_or_fragment

bp = Blueprint("status", __name__)


@bp.get("/status")
async def status():
    bot = get_bot()
    connected = bool(bot and bot.is_ready() and not bot.is_closed())
    return await render_page_or_fragment(
        "pages/status.html", {"connected": connected}
    )
