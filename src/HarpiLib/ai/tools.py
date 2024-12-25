import datetime
from typing import Callable, cast

from discord.ext import commands

from src.cogs.music import MusicCog
from src.HarpiLib.dice.dice_parser import DiceParser


def current_time() -> str:
    """Get current time in string format.

    Returns
    -------
    str
        Current time in string format.
    """
    current = datetime.datetime.now(
        tz=datetime.timezone(datetime.timedelta(hours=-3)),
    )
    return current.strftime("%d/%m/%Y %H:%M:%S")


class AiTools:
    def __init__(self, bot: commands.Bot) -> None:
        self.music_cog: MusicCog = cast(MusicCog, bot.get_cog("MusicCog"))

    def get_music_list(self, guild_id: int) -> Callable[[], str]:
        def get_music_list() -> str:
            """Get music list.

            Returns
            -------
            str
                Music list.
            """
            current = self.music_cog.current_music.get(guild_id, None)
            musics = self.music_cog.music_queue.get(guild_id, [])
            return "\n".join(
                ([f"{0}: {current.title}"] if current else [])
                + [
                    f"{idx + 1}: {music.title}"
                    for idx, music in enumerate(musics)
                ],
            )

        return get_music_list

    def roll_dice(self) -> Callable[[str], str]:
        def roll_dice(args: str) -> str:
            """Roll dices based on the input string.

            Parameters
            ----------
            args : str
                The dice string (ex: 2d6 or 1d20+5 or 3#d20+5 for rolling
                for the best).

            Returns
            -------
            str
                The rolled dices.
            """
            parser = DiceParser(args)
            rows = parser.roll()
            text = ""
            for i, row in enumerate(rows):
                total, results = row
                for component, result in zip(
                    parser.component_register[i],
                    results,
                ):
                    text += f"{component[0]}{component[1]}{result}"
                text += " = " + str(total)
                if i != len(rows) - 1:
                    text += "\n"

            return text

        return roll_dice

    def get_tools(self, guild_id: int) -> list[Callable[..., str]]:
        return [
            self.get_music_list(guild_id),
            self.roll_dice(),
            current_time,
        ]
