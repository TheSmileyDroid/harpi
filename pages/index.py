import psutil

from quart import Blueprint

from src.api.deps import get_bot
from src.api.panel import render_page_or_fragment

bp = Blueprint("index", __name__)


@bp.get("/")
async def index():
    bot = get_bot()
    vm = psutil.virtual_memory()
    connected = bool(bot and bot.is_ready() and not bot.is_closed())
    return await render_page_or_fragment(
        "pages/index.html",
        {
            "cpu": psutil.cpu_percent(),
            "mem_percent": vm.percent,
            "mem_available": vm.available,
            "mem_total": vm.total,
            "connected": connected,
        },
    )
