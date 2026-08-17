from quart import Blueprint, request, session

from src.api.deps import get_bot, run_on_bot_loop
from src.api.guild import _get_guilds
from src.api.panel import render_page_or_fragment

bp = Blueprint("music", __name__)


def _guild_id() -> int | None:
    raw = session.get("guild_id")
    return int(raw) if raw else None


async def _context() -> dict:
    bot = get_bot()
    guild_id = _guild_id()
    guilds = await _get_guilds()
    channels = []
    if guild_id is not None and bot:
        guild = bot.get_guild(guild_id)
        if guild:
            channels = guild.voice_channels
    status = None
    if guild_id is not None and bot:
        session_obj = bot.sessions.get(guild_id)
        if session_obj is not None:
            status = await run_on_bot_loop(session_obj.sample_status())
    return {
        "guilds": guilds,
        "selected_guild_id": guild_id,
        "channels": channels,
        "status": status,
    }


async def _handle_action(request) -> None:
    form = await request.form
    action = (form.get("action") or "").strip()
    bot = get_bot()

    if action == "connect":
        guild_id = int(form["guild_id"])
        channel_id = int(form["channel_id"])
        session["guild_id"] = str(guild_id)
        await run_on_bot_loop(bot.sessions.connect(guild_id, channel_id))
        return

    if action == "disconnect":
        guild_id = _guild_id()
        if guild_id is not None:
            session.pop("guild_id", None)
            await run_on_bot_loop(bot.sessions.disconnect(guild_id))
        return

    guild_id = _guild_id()
    if guild_id is None:
        return
    session_obj = bot.sessions.get(guild_id)
    if session_obj is None:
        return

    value = form.get("value")
    if action == "toggle_pause":
        await run_on_bot_loop(session_obj.toggle_pause())
    elif action == "skip":
        await run_on_bot_loop(session_obj.skip())
    elif action == "stop":
        await run_on_bot_loop(session_obj.stop())
    elif action == "clear_queue":
        await run_on_bot_loop(session_obj.clear_queue())
    elif action == "remove" and value:
        await run_on_bot_loop(session_obj.remove(value))
    elif action == "clear_layers":
        await run_on_bot_loop(session_obj.clear_layers())
    elif action == "remove_layer" and value:
        await run_on_bot_loop(session_obj.remove_layer(value))
    elif action == "add" and value:
        await run_on_bot_loop(session_obj.play(value))


@bp.route("/music", methods=["GET", "POST"])
async def music():
    if request.method == "POST":
        await _handle_action(request)
    return await render_page_or_fragment("pages/music.html", await _context())
