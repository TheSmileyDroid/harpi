import psutil

from quart import Blueprint, render_template

from src.bot_state import get_bot

bp = Blueprint("index", __name__)


@bp.get("/")
async def index():
    bot = get_bot()
    vm = psutil.virtual_memory()
    connected = bool(bot and bot.is_ready() and not bot.is_closed())
    ctx = {
        "cpu": psutil.cpu_percent(),
        "mem_percent": vm.percent,
        "mem_available": vm.available,
        "mem_total": vm.total,
        "connected": connected,
    }
    return await render_template(
        "pages/index.html",
        **ctx,
    )


@bp.get("/status")
async def status():
    bot = get_bot()
    connected = bool(bot and bot.is_ready() and not bot.is_closed())
    return await render_template("components/status.html", connected=connected)
