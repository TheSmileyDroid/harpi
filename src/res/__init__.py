from src.bot.iharpi import IHarpi
from .music import MusicCog
from .basic import BasicCog
from .dice import DiceCog
from .tts import TTSCog
from .chat import ChatCog
from .lol import LolCog


async def setup(bot: IHarpi) -> None:
    """Make the bot load the cogs.

    Args:
        bot (commands.Bot): The bot instance.
    """
    await bot.add_cog(MusicCog(bot))
    await bot.add_cog(BasicCog(bot))
    await bot.add_cog(DiceCog(bot))
    await bot.add_cog(TTSCog(bot))
    await bot.add_cog(ChatCog(bot))
    await bot.add_cog(LolCog(bot))
