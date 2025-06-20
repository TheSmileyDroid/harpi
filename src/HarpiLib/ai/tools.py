from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, cast

import discord
import discord.ext
import discord.ext.commands
import wikipediaapi
from discord import Message, TextChannel
from google.generativeai import types

from src.cogs.music import MusicCog
from src.HarpiLib.math.parser import DiceParser
from src.HarpiLib.musicdata.ytmusicdata import YTMusicData

if TYPE_CHECKING:
    from discord.ext import commands


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


class AiTools:
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.music_cog: MusicCog = cast(MusicCog, bot.get_cog("MusicCog"))

    async def get_wikipedia_summary(
        self,
        ctx: commands.Context,
        args: str,
    ) -> str:
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

        await ctx.send(
            "*Procurando na wikipedia*",
            silent=True,
            delete_after=5.0,
        )
        page = wikipedia_client.page(args)
        if not page.exists():
            return "<Nenhum resultado encontrado>"
        return page.summary

    async def get_full_wikipedia_page(
        self,
        ctx: commands.Context,
        args: str,
    ) -> str:
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
        await ctx.send(
            "*Procurando na wikipedia*",
            silent=True,
            delete_after=5.0,
        )
        page = wikipedia_client.page(args)
        if not page.exists():
            return "<Nenhum resultado encontrado>"
        return page.text

    async def get_music_list(
        self,
        ctx: commands.Context,
    ) -> str:
        """Get music list that is playing now.

        Returns
        -------
        str
            Music list.
        """
        await ctx.send(
            "*Lendo lista de músicas*",
            silent=True,
            delete_after=5.0,
        )
        guild_id = ctx.channel.guild.id if ctx.channel.guild else 0
        current = self.music_cog.current_music.get(guild_id, None)
        musics = self.music_cog.music_queue.get(guild_id, [])
        return "\n".join(
            ([f"0: {current.title}"] if current else [])
            + [
                f"{idx + 1}: {music.title}" for idx, music in enumerate(musics)
            ],
        )

    async def play_music(
        self,
        ctx: commands.Context,
        args: str,
    ) -> str:
        """Play music based on the search term.

        Parameters
        ----------
        args : str
            Music search term.

        Returns
        -------
        str
            Music search term.
        """
        await ctx.send(
            "*Procurando música*",
            silent=True,
            delete_after=5.0,
        )
        guild_id = ctx.channel.guild.id if ctx.channel.guild else 0
        music_data = await YTMusicData.from_url(args)
        voice_client = ctx.guild.voice_client if ctx.guild else None
        if not voice_client:
            await self.music_cog.connect_to_voice(
                guild_id,
                ctx.author.voice.channel,  # type: ignore Discord member
            )

        await self.music_cog.add_music_to_queue(
            guild_id,
            music_data,
        )
        await self.music_cog.play_channel.put(guild_id)
        return f'"{music_data[0].title}" adicionado à fila. ({args})'

    async def roll_dice(
        self,
        ctx: commands.Context,
        args: str,
    ) -> str:
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
        await ctx.send(
            "*Rolando dados*",
            silent=True,
            delete_after=5.0,
        )
        parser = DiceParser()
        text = parser.roll(args)

        return text

    async def get_guild_members(
        self,
        ctx: commands.Context,
    ) -> str:
        """Get guild members.

        Returns
        -------
        str
            Guild members.
        """
        guild_id = ctx.channel.guild.id if ctx.channel.guild else 0
        guild = self.bot.get_guild(guild_id)
        if guild:
            return "\n".join([
                f"- {member.nick} ({member.name})" for member in guild.members
            ])
        return "<Nenhum resultado encontrado>"

    async def get_last_messages(
        self,
        ctx: discord.ext.commands.Context,
    ) -> str:
        """Obtém as últimas mensagens do canal.
        Mais útil para obter contexto da conversa.

        Returns
        -------
        str
            Last messages.
        """
        await ctx.send(
            "*Lendo mensagens antigas*",
            silent=True,
            delete_after=5.0,
        )
        channel_id = ctx.channel.id
        channel = self.bot.get_channel(channel_id)
        if channel and isinstance(channel, TextChannel):
            messages: list[Message] = [
                message async for message in channel.history(limit=40)
            ]
            return "\n".join([
                f"[{message.created_at} - {message.author.display_name} ({message.author.name})] : {message.content}"
                for message in messages
            ])

        return "<Nenhum resultado encontrado>"

    async def disconnect_from_voice(
        self,
        ctx: commands.Context,
    ) -> str:
        """Desconecta o bot do canal de voz atual.

        Returns
        -------
        str
            Mensagem de confirmação da desconexão.
        """
        await ctx.send(
            "*Desconectando do canal de voz*",
            silent=True,
            delete_after=5.0,
        )

        guild_id = ctx.channel.guild.id if ctx.channel.guild else 0

        try:
            # Usando o método do MusicCog para desconectar
            await self.music_cog.disconnect_guild(guild_id)
            return "Desconectado do canal de voz com sucesso."
        except Exception as e:
            return f"Não foi possível desconectar: {str(e)}"

    async def skip_music(
        self,
        ctx: commands.Context,
    ) -> str:
        """Pula a música atual que está sendo reproduzida.

        Returns
        -------
        str
            Mensagem de confirmação de que a música foi pulada.
        """
        await ctx.send(
            "*Pulando música*",
            silent=True,
            delete_after=5.0,
        )

        guild_id = ctx.channel.guild.id if ctx.channel.guild else 0

        try:
            await self.music_cog.skip_guild(guild_id)
            return "Música pulada com sucesso."
        except Exception as e:
            return f"Não foi possível pular a música: {str(e)}"

    async def call_function(
        self,
        ctx: discord.ext.commands.Context,
        name: str,
        args: Any,  # noqa: ANN401
    ) -> Any:  # noqa: ANN401
        """Call a function by name.

        Parameters
        ----------
        name : str
            Function name.
        args : Any
            Function arguments.

        Returns
        -------
        Any
            Function return.
        """
        return await getattr(self, name)(ctx, **dict(args))

    def get_tools(
        self,
    ) -> types.Tool:
        return types.Tool(
            function_declarations=[
                {
                    "name": "get_music_list",
                    "description": "Get music list that is playing now.",
                },
                {
                    "name": "play_music",
                    "description": "Play music based on the search term.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "args": {
                                "type": "string",
                                "description": "Music search term.",
                            },
                        },
                        "required": ["args"],
                    },
                },
                {
                    "name": "disconnect_from_voice",
                    "description": "Desconecta o bot do canal de voz atual. Use esta função quando o usuário pedir para sair da chamada, desconectar do canal de voz ou parar de tocar música definitivamente.",
                },
                {
                    "name": "skip_music",
                    "description": "Pula a música atual que está sendo reproduzida. Use esta função quando o usuário pedir para pular, avançar ou passar para a próxima música.",
                },
                {
                    "name": "roll_dice",
                    "description": "Roll dices based on the input string.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "args": {
                                "type": "string",
                                "description": (
                                    "The dice string (ex: 2d6, 1d20+5, or 3#d20+5)."
                                ),
                            },
                        },
                        "required": ["args"],
                    },
                },
                {
                    "name": "get_guild_members",
                    "description": "Get guild members.",
                },
                {
                    "name": "get_last_messages",
                    "description": (
                        "Get the last 30 messages of the current channel."
                        " It is useful to know exactaly whats is happening if you are not sure."
                    ),
                },
            ],
        )
