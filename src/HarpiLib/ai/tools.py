from __future__ import annotations

import datetime
from collections.abc import Coroutine
from typing import Any, Callable, cast

import wikipediaapi
from discord import TextChannel
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


wikipedia_client = wikipediaapi.Wikipedia(
    "Harpi (https://github.com/TheSmileyDroid/Harpi; ghsilha@gmail.com)",
    language="pt",
)


def get_wikipedia_summary(args: str) -> str:
    """Get Wikipedia summary based on the search term (Sua fonte mais
    útil de informações).

    Parameters
    ----------
    args : str
        Wikipedia search term.

    Returns
    -------
    str
        Wikipedia summary.
    """

    page = wikipedia_client.page(args)
    if not page.exists():
        return "Não encontrei nada."
    return page.summary


def get_full_wikipedia_page(args: str) -> str:
    """Get full Wikipedia page based on the search term.

    Parameters
    ----------
    args : str
        Wikipedia search term.

    Returns
    -------
    str
        Wikipedia page.
    """

    page = wikipedia_client.page(args)
    if not page.exists():
        return "Não encontrei nada."
    return page.text


class AiTools:
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
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

    def get_guild_members(self, guild_id: int) -> Callable[[], str]:
        def get_guild_members() -> str:
            """Get guild members.

            Returns
            -------
            str
                Guild members.
            """
            guild = self.bot.get_guild(guild_id)
            if guild:
                return "\n".join([
                    f"- {member.nick} ({member.name})"
                    for member in guild.members
                ])
            return "Não encontrei nada."

        return get_guild_members

    def get_last_messages(
        self,
        channel_id: int,
    ) -> Callable[[], Coroutine[Any, Any, str]]:
        """Obtém as últimas mensagens do canal.

        Returns
        -------
        Callable[[], str]
            Função que retorna as últimas mensagens.
        """

        async def get_last_messages() -> str:
            """Lê as últimas mensagens do canal.

            Returns
            -------
            str
                Last messages.
            """

            async def fetch_messages() -> str:
                channel = self.bot.get_channel(channel_id)
                if channel and isinstance(channel, TextChannel):
                    messages = [
                        message async for message in channel.history(limit=15)
                    ]
                    return "\n".join([
                        f"- {message.author.name}: {message.content}"
                        for message in messages
                    ])
                return "Não encontrei nada."

            return await fetch_messages()

        return get_last_messages

    async def get_tools(
        self,
        guild_id: int,
        channel_id: int,
    ) -> list[Callable[..., str]]:
        messages = await (self.get_last_messages(channel_id))()

        def get_message_history() -> str:
            """Obtém as últimas mensagens do canal.

            Returns
            -------
            str
                Last messages.
            """

            return messages

        return [
            self.get_music_list(guild_id),
            self.roll_dice(),
            current_time,
            get_wikipedia_summary,
            get_full_wikipedia_page,
            self.get_guild_members(guild_id),
            get_message_history,
        ]
