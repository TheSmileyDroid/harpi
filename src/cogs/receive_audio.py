"""Módulo para gravar áudio dos canais de voz do Discord."""

import asyncio
import discord
from discord.ext import commands
from typing import Any, Optional
import tempfile
import os
import logging

logger = logging.getLogger(__name__)

class ReceiveAudioCog(commands.Cog):
    """Cog responsável pela gravação de áudio dos canais de voz."""

    def __init__(self, bot: commands.Bot) -> None:
        """Inicializa o cog de gravação de áudio.

        Args:
            bot: Bot do Discord ao qual este cog será anexado.
        """
        self.bot = bot
        self.connections: dict[int, discord.VoiceClient] = {}
        self.audio_dir = "audio"
        os.makedirs(self.audio_dir, exist_ok=True)
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

    async def process_audio(self, audio_data: bytes) -> str:
        """Process audio data and return text."""
        # Save audio to temporary WAV file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            wavfile.write(temp_wav.name, 16000, audio_data)

        # Convert WAV to text using a different approach (e.g., Whisper)
        # This is a placeholder - you'll need to implement the actual transcription logic
        text = "Transcription not implemented yet"

        return text

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
                discord.sinks.WaveSink(),
                self.once_done,
                ctx.channel,
                sync_start=True,
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
        self, sink: discord.sinks.WaveSink, channel: discord.TextChannel, *args: Any
    ) -> None:
        """Callback chamado quando a gravação é finalizada.

        Args:
            sink: Sink contendo os dados de áudio gravados.
            channel: Canal de texto onde a mensagem será enviada.
            args: Argumentos adicionais.
        """
        assert isinstance(sink, discord.sinks.WaveSink), "O sink deve ser do tipo WaveSink"
        assert isinstance(channel, discord.TextChannel), (
            "O canal deve ser do tipo TextChannel"
        )
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

        # Iniciar mensagem de status
        status_message = await channel.send(
            f"🔄 Processando áudio de {len(sink.audio_data)} usuários..."
        )

        # Cria arquivos para envio
        files = []
        for user_id, audio in sink.audio_data.items():
            assert isinstance(audio, discord.sinks.AudioData), (
                "O objeto de áudio deve ser do tipo AudioData"
            )
            assert isinstance(audio.file, io.BytesIO), (
                "O arquivo de áudio deve ser do tipo BytesIO"
            )

            # Faz uma cópia do arquivo para transcrição, já que vamos usar a posição original para envio
            current_pos = audio.file.tell()
            audio.file.seek(0)
            audio_copy = io.BytesIO(audio.file.read())
            audio.file.seek(current_pos)

            # Prepara o arquivo para envio
            files.append(discord.File(audio.file, f"{user_id}.wav"))

        # Envia os arquivos de áudio
        try:
            await channel.send(
                f"Gravação finalizada para: {', '.join(recorded_users)}.",
                files=files,
            )

            # Atualiza mensagem de status
            await status_message.edit(
                content="📄 Arquivos de áudio enviados! Iniciando transcrição em tempo real..."
            )

            # Inicia transcrições em tempo real para cada arquivo
            transcription_tasks = []
            for user_id, audio in sink.audio_data.items():
                # Cria uma cópia do arquivo para transcrição
                audio_copy = io.BytesIO()
                audio.file.seek(0)
                audio_copy.write(audio.file.read())
                audio_copy.seek(0)

                # Adiciona a tarefa de transcrição à lista
                task = asyncio.create_task(
                    self.process_audio(audio_copy.read())
                )
                transcription_tasks.append(task)

            # Aguarda todas as transcrições terminarem
            await asyncio.gather(*transcription_tasks)

            # Atualiza a mensagem de status para concluído
            await status_message.edit(
                content="✅ Processamento de áudio concluído!"
            )

            logger.info(
                f"Arquivos de áudio e transcrições enviados para o canal {channel.id}"
            )
        except Exception as e:
            logger.error(f"Erro ao processar áudio: {e}")
            await status_message.edit(
                content=f"❌ Erro ao processar áudio: {e}"
            )


if __name__ == "__main__":
    """Testa a funcionalidade de transcrição com um arquivo de áudio existente."""
    import argparse
    import asyncio
    import pathlib

    # Configura o parser de argumentos para permitir testar com diferentes arquivos
    parser = argparse.ArgumentParser(
        description="Testa a transcrição de áudio"
    )
    parser.add_argument(
        "--arquivo",
        type=str,
        default=".voice_recordings/439894995890208768.wav",
        help="Caminho para o arquivo de áudio a ser transcrito",
    )

    args = parser.parse_args()

    # Configura o logger para exibir mensagens durante o teste
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Define uma função para testar a transcrição
    async def test_transcription(
        audio_path: str,
    ) -> None:
        """Testa a transcrição de um arquivo de áudio.

        Args:
            audio_path: Caminho para o arquivo de áudio.
        """
        # Verifica se o arquivo existe
        audio_file_path = pathlib.Path(audio_path)
        if not audio_file_path.exists():
            print(f"❌ Erro: O arquivo {audio_path} não existe.")
            return

        print(f"🎯 Testando transcrição do arquivo: {audio_path}")

        try:
            # Abre o arquivo como BytesIO para simular o processamento real
            with open(audio_file_path, "rb") as f:
                audio_data = io.BytesIO(f.read())

            # Processa o áudio
            text = await ReceiveAudioCog(None).process_audio(audio_data.read())

            # Exibe a transcrição completa
            print("\n📝 Transcrição completa:")
            print(f'"{text}"')

            # Se não houver transcrição, exibe uma mensagem
            if not text:
                print("❗ Nenhum texto foi reconhecido no áudio.")

        except Exception as e:
            print(f"❌ Erro durante a transcrição: {str(e)}")
            import traceback

            traceback.print_exc()

    # Executa o teste
    try:
        asyncio.run(
            test_transcription(args.arquivo)
        )
    except KeyboardInterrupt:
        print("\n⚠️ Teste interrompido pelo usuário.")
    except Exception as e:
        print(f"❌ Erro inesperado: {str(e)}")
        import traceback

        traceback.print_exc()
