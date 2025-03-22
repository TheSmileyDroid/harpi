"""Módulo para gravar áudio dos canais de voz do Discord."""

import logging
from typing import Dict, Optional

from discord import File, TextChannel, VoiceClient
from discord.ext import commands
from discord.sinks import WaveSink

logger = logging.getLogger(__name__)


class ReceiveAudioCog(commands.Cog):
    """Cog responsável pela gravação de áudio dos canais de voz."""

    def __init__(self, bot: commands.Bot) -> None:
        """Inicializa o cog de gravação de áudio.

        Args:
            bot: Bot do Discord ao qual este cog será anexado.
        """
        self.bot = bot
        self.connections: Dict[int, VoiceClient] = {}
        self._setup_logger()

    def _setup_logger(self) -> None:
        """Configura o logger para este módulo."""
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            logger.addHandler(handler)

    @commands.command(name="record")
    async def record(self, ctx: commands.Context) -> None:
        """Inicia a gravação de áudio do canal de voz.

        Args:
            ctx: Contexto do comando.
        """
        # Verifica se o autor do comando está em um canal de voz
        if not ctx.author.voice:
            await ctx.send("Você não está em um canal de voz!")
            return

        # Verifica se já existe uma gravação em andamento no servidor
        if ctx.guild.id in self.connections:
            await ctx.send(
                "Já existe uma gravação em andamento neste servidor!"
            )
            return

        try:
            # Conecta ao canal de voz do autor
            vc = await ctx.author.voice.channel.connect()
            self.connections[ctx.guild.id] = vc

            # Inicia a gravação
            vc.start_recording(
                WaveSink(),
                self.once_done,
                ctx.channel,
            )
            await ctx.send("Gravação iniciada!")
            logger.info(f"Gravação iniciada no servidor {ctx.guild.id}")
        except Exception as e:
            logger.error(f"Erro ao iniciar gravação: {e}")
            await ctx.send(f"Erro ao iniciar gravação: {e}")

    @commands.command(name="stop_recording")
    async def stop_recording(self, ctx: commands.Context) -> None:
        """Para a gravação de áudio em andamento.

        Args:
            ctx: Contexto do comando.
        """
        guild_id = getattr(ctx.guild, "id", None)
        if not guild_id:
            await ctx.send("Este comando só pode ser usado em servidores.")
            return

        if guild_id in self.connections:
            try:
                vc = self.connections[guild_id]
                vc.stop_recording()  # Isso chamará o callback once_done
                logger.info(f"Gravação finalizada no servidor {guild_id}")
                await ctx.send("Gravação finalizada!")
            except Exception as e:
                logger.error(f"Erro ao parar gravação: {e}")
                await ctx.send(f"Erro ao parar gravação: {e}")
        else:
            await ctx.send("Não há gravação em andamento neste servidor.")

    async def once_done(
        self, sink: WaveSink, channel: TextChannel, *args
    ) -> None:
        """Callback chamado quando a gravação é finalizada.

        Args:
            sink: Sink contendo os dados de áudio gravados.
            channel: Canal de texto onde a mensagem será enviada.
            args: Argumentos adicionais.
        """
        # Obtém o ID do servidor a partir da conexão de voz
        guild_id: Optional[int] = None
        for gid, vc in self.connections.items():
            if vc == sink.vc:
                guild_id = gid
                break

        if guild_id is not None:
            del self.connections[guild_id]

        # Desconecta do canal de voz
        await sink.vc.disconnect()

        # Prepara os arquivos de áudio e os usuários gravados
        if not sink.audio_data:
            await channel.send("Nenhum áudio foi gravado.")
            return

        recorded_users = [
            f"<@{user_id}>" for user_id in sink.audio_data.keys()
        ]

        files = [
            File(audio.file, f"{user_id}.{sink.encoding}")
            for user_id, audio in sink.audio_data.items()
        ]

        # Envia os arquivos de áudio para o canal
        try:
            await channel.send(
                f"Gravação finalizada para: {', '.join(recorded_users)}.",
                files=files,
            )
            logger.info(
                f"Arquivos de áudio enviados para o canal {channel.id}"
            )
        except Exception as e:
            logger.error(f"Erro ao enviar arquivos de áudio: {e}")
            await channel.send(f"Erro ao enviar arquivos de áudio: {e}")
