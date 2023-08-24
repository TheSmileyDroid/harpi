from .music import Music
from .basic import Basic
from .dice import Dice
from .tts import TTS
from .chat import Chat

async def setup(bot):
    """Make the bot load the cogs.

    Args:
        bot (commands.Bot): The bot instance.
    """
    await bot.add_cog(Music(bot))
    await bot.add_cog(Basic(bot))
    await bot.add_cog(Dice(bot))
    await bot.add_cog(TTS(bot))
    await bot.add_cog(Chat(bot))
