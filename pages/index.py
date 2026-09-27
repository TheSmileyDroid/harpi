import psutil

from quart import Blueprint, render_template

from src.panel import state

bp = Blueprint("index", __name__)


@bp.get("/")
async def index():
    vm = psutil.virtual_memory()
    ctx = {
        "cpu": psutil.cpu_percent(),
        "mem_percent": vm.percent,
        "mem_available": vm.available,
        "mem_total": vm.total,
        "connected": state.bot_connected(),
    }
    return await render_template(
        "pages/index.html",
        **ctx,
    )


@bp.get("/status")
async def status():
    return await render_template(
        "components/status.html", connected=state.bot_connected()
    )
