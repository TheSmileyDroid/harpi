from typing import cast

from discord import VoiceClient
from loguru import logger
from quart import Blueprint, jsonify, request

from src.discord_bot import get_bot_instance
from src.models.guild import AudioSourceTrackedProtocol

bp = Blueprint("music", __name__)


def get_music_data(guild_id: int):
    """Get music status data for a specific guild.

    Args:
        guild_id: The guild ID to get music data for.

    Returns:
        dict: Music data including current track, progress, queue, and playback state.
        None: If bot is not ready or guild not found.
    """
    bot = get_bot_instance()
    if not bot:
        return None

    guild = bot.get_guild(guild_id)
    if not guild:
        return None

    guild_config = bot.api.get_guild_config(guild_id)
    current_music = guild_config.current_music if guild_config else None
    queue = guild_config.queue if guild_config else None
    progress = 0

    voice_client = (
        cast(VoiceClient, guild.voice_client) if guild.voice_client else None
    )
    if voice_client and (source := voice_client.source):
        source = cast(AudioSourceTrackedProtocol, cast(object, source))
        progress = 0

    return {
        "current_music": {
            "title": current_music.title,
            "duration": current_music.duration,
            "url": current_music.url,
        }
        if current_music
        else None,
        "progress": round(progress),
        "queue": [
            {"title": m.title, "duration": m.duration, "url": m.url}
            for m in (queue if queue else [])
        ],
        "is_playing": voice_client.is_playing() if voice_client else False,
        "is_paused": voice_client.is_paused() if voice_client else False,
    }


@bp.route("/api/music/status")
async def music_status():
    """Get music status for a guild.

    Query params:
        guild_id: The guild ID to get status for.

    Returns:
        JSON with music data or error.
    """
    guild_id_str = request.args.get("guild_id")
    if not guild_id_str:
        return jsonify({"error": "guild_id required"}), 400

    try:
        guild_id = int(guild_id_str)
    except ValueError:
        return jsonify({"error": "Invalid guild_id"}), 400

    data = get_music_data(guild_id)
    if data is None:
        return jsonify({"error": "Guild not found or bot not ready"}), 404

    return jsonify(data)


@bp.route("/api/music/control", methods=["POST"])
async def music_control():
    """Control music playback for a guild.

    Body:
        guild_id: The guild ID.
        action: One of 'stop', 'skip', 'pause', 'resume'.

    Returns:
        JSON with status or error.
    """
    body = await request.get_json() or {}
    guild_id = body.get("guild_id")
    action = body.get("action")

    if not guild_id:
        return jsonify({"error": "guild_id required"}), 400

    try:
        guild_id = int(guild_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid guild_id"}), 400

    bot = get_bot_instance()
    if not bot:
        return jsonify({"error": "Bot not ready"}), 503

    try:
        if action == "stop":
            await bot.api.stop_music(guild_id)
        elif action == "skip":
            await bot.api.skip_music(guild_id)
        elif action == "pause":
            guild = bot.get_guild(guild_id)
            if guild and guild.voice_client:
                voice_client = cast(VoiceClient, guild.voice_client)
                voice_client.pause()
        elif action == "resume":
            guild = bot.get_guild(guild_id)
            if guild and guild.voice_client:
                voice_client = cast(VoiceClient, guild.voice_client)
                voice_client.resume()
        else:
            return jsonify({"error": "Invalid action"}), 400
        return jsonify({"status": "ok"})

    except Exception as e:
        logger.error(f"Error in music control: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/api/music/add", methods=["POST"])
async def music_add():
    """Add music to queue via link.

    Body:
        guild_id: The guild ID.
        channel_id: The voice channel ID to connect to.
        link: The music URL (YouTube, etc).

    Returns:
        JSON with status or error.
    """
    body = await request.get_json() or {}
    guild_id = body.get("guild_id")
    channel_id = body.get("channel_id")
    link = body.get("link")

    if not guild_id or not link:
        return jsonify({"error": "guild_id and link required"}), 400

    try:
        guild_id = int(guild_id)
        channel_id = int(channel_id) if channel_id else None
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid guild_id or channel_id"}), 400

    bot = get_bot_instance()
    if not bot:
        return jsonify({"error": "Bot not ready"}), 503

    try:
        guild_config = bot.api.get_guild_config(guild_id)
        if not guild_config and not channel_id:
            return jsonify(
                {"error": "channel_id required when bot not connected"}
            ), 400

        await bot.api.add_music_to_queue(guild_id, channel_id or 0, link)
        return jsonify({"status": "ok"})

    except Exception as e:
        logger.error(f"Error adding music: {e}")
        return jsonify({"error": str(e)}), 500
