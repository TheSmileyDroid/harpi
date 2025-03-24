"""Módulo para gravar áudio dos canais de voz do Discord."""

import asyncio
import io
import json
import logging
import os
import wave
import zipfile
from typing import Any, Dict, Optional, cast

import discord
import discord.ext
from discord import File, Message, TextChannel, VoiceClient
from discord.ext import commands
from discord.sinks import WaveSink
from vosk import KaldiRecognizer, Model

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
        self.transcription_messages: Dict[
            str, Message
        ] = {}  # Armazena mensagens para atualização
        self.vosk_model_path = "models/vosk-model-small-pt-0.3"
        self.vosk_zip_path = f"{self.vosk_model_path}.zip"
        self._setup_logger()
        self._setup_vosk_model()

    def _setup_vosk_model(self) -> None:
        """Prepara o modelo Vosk para reconhecimento de fala em português."""
        try:
            # Verifica se o modelo já está extraído
            if not os.path.exists(self.vosk_model_path):
                logger.info(f"Extraindo modelo Vosk de {self.vosk_zip_path}")
                # Cria o diretório models se não existir
                os.makedirs("models", exist_ok=True)

                # Extrai o arquivo zip
                with zipfile.ZipFile(self.vosk_zip_path, "r") as zip_ref:
                    zip_ref.extractall("models")
                logger.info("Modelo Vosk extraído com sucesso")
            else:
                logger.info("Modelo Vosk já existe, pulando extração")
        except Exception as e:
            logger.error(f"Erro ao configurar modelo Vosk: {e}")

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

    async def transcribe_audio(self, audio_file: io.BytesIO) -> str:
        """Transcreve um arquivo de áudio para texto usando o modelo Vosk.

        Args:
            audio_file: Arquivo de áudio a ser transcrito.

        Returns:
            Texto transcrito do áudio.
        """
        try:
            # Carrega o modelo Vosk para português
            model = Model(self.vosk_model_path)

            # Abre o arquivo de áudio
            wf = wave.open(audio_file, "rb")

            # Configura o reconhecedor
            recognizer = KaldiRecognizer(model, wf.getframerate())
            recognizer.SetWords(True)

            # Processa o áudio em chunks
            results = []
            chunk_size = 4000  # tamanho do chunk em bytes

            while True:
                data = wf.readframes(chunk_size)
                if len(data) == 0:
                    break

                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    if "text" in result and result["text"]:
                        results.append(result["text"])

            # Obtém o resultado final
            final_result = json.loads(recognizer.FinalResult())
            if "text" in final_result and final_result["text"]:
                results.append(final_result["text"])

            # Junta todos os resultados
            transcription = " ".join(results)

            return (
                transcription if transcription else "Nenhum texto reconhecido."
            )

        except Exception as e:
            logger.error(f"Erro ao transcrever áudio: {e}")
            return f"Erro na transcrição: {str(e)}"

    async def transcribe_audio_live(
        self, audio_file: io.BytesIO, channel: TextChannel, user_id: str
    ) -> str:
        """Transcreve áudio em tempo real, atualizando uma mensagem no Discord.

        Args:
            audio_file: Arquivo de áudio a ser transcrito.
            channel: Canal onde a mensagem será enviada/atualizada.
            user_id: ID do usuário cujo áudio está sendo transcrito.

        Returns:
            Texto completo transcrito do áudio.
        """
        try:
            # Carrega o modelo Vosk para português
            model = Model(self.vosk_model_path)

            # Abre o arquivo de áudio
            wf = wave.open(audio_file, "rb")

            # Configura o reconhecedor
            recognizer = KaldiRecognizer(model, wf.getframerate())
            recognizer.SetWords(True)

            # Inicia com uma mensagem vazia que será atualizada
            message_key = f"{channel.id}_{user_id}"
            if message_key not in self.transcription_messages:
                initial_message = await channel.send(
                    f"🎤 **Transcrevendo áudio de <@{user_id}>**: _(processando...)_"
                )
                self.transcription_messages[message_key] = initial_message

            # Buffer para acumular a transcrição completa
            full_transcription = ""
            segment_buffer = ""

            # Processa o áudio em chunks
            chunk_size = 4000  # tamanho do chunk em bytes
            update_interval = 0.5  # segundos entre atualizações da mensagem
            last_update = 0
            current_time = 0

            while True:
                data = wf.readframes(chunk_size)
                if len(data) == 0:
                    break

                # Atualiza o tempo atual baseado na taxa de amostragem e tamanho do chunk
                frames_read = (
                    chunk_size / wf.getsampwidth() / wf.getnchannels()
                )
                time_increment = frames_read / wf.getframerate()
                current_time += time_increment

                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    if "text" in result and result["text"]:
                        # Adiciona ao buffer de segmento e à transcrição completa
                        new_text = result["text"]
                        segment_buffer += " " + new_text
                        full_transcription += " " + new_text

                # Atualiza a mensagem periodicamente
                if (
                    current_time - last_update >= update_interval
                    and segment_buffer
                ):
                    message = self.transcription_messages[message_key]
                    await message.edit(
                        content=f"🎤 **Transcrevendo áudio de <@{user_id}>**: {full_transcription.strip()}"
                    )
                    segment_buffer = ""  # Limpa o buffer de segmento
                    last_update = current_time

            # Processa o resultado final
            final_result = json.loads(recognizer.FinalResult())
            if "text" in final_result and final_result["text"]:
                final_text = final_result["text"]
                full_transcription += " " + final_text

            # Atualiza a mensagem uma última vez com o texto completo
            final_transcription = full_transcription.strip()
            if final_transcription:
                message = self.transcription_messages[message_key]
                await message.edit(
                    content=f"🎤 **Transcrição de <@{user_id}>**: {final_transcription}"
                )
            else:
                message = self.transcription_messages[message_key]
                await message.edit(
                    content=f"🎤 **Transcrição de <@{user_id}>**: _(Nenhum texto reconhecido)_"
                )
                final_transcription = "Nenhum texto reconhecido."

            return final_transcription

        except Exception as e:
            logger.error(f"Erro ao transcrever áudio em tempo real: {e}")
            error_message = f"Erro na transcrição em tempo real: {str(e)}"

            # Tenta atualizar a mensagem com o erro
            message_key = f"{channel.id}_{user_id}"
            if message_key in self.transcription_messages:
                message = self.transcription_messages[message_key]
                await message.edit(
                    content=f"🎤 **Erro na transcrição de <@{user_id}>**: {str(e)}"
                )

            return error_message

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
            vc = cast(
                discord.VoiceClient, await ctx.author.voice.channel.connect()
            )
            self.connections[ctx.guild.id] = vc

            # Inicia a gravação
            vc.start_recording(
                WaveSink(),
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
        self, sink: WaveSink, channel: TextChannel, *args: Any
    ) -> None:
        """Callback chamado quando a gravação é finalizada.

        Args:
            sink: Sink contendo os dados de áudio gravados.
            channel: Canal de texto onde a mensagem será enviada.
            args: Argumentos adicionais.
        """
        assert isinstance(sink, WaveSink), "O sink deve ser do tipo WaveSink"
        assert isinstance(channel, TextChannel), (
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
            files.append(File(audio.file, f"{user_id}.{sink.encoding}"))

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
                    self.transcribe_audio_live(audio_copy, channel, user_id)
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
    parser.add_argument(
        "--modelo",
        type=str,
        default="models/vosk-model-small-pt-0.3",
        help="Caminho para o modelo Vosk a ser utilizado",
    )
    parser.add_argument(
        "--chunk_size",
        type=int,
        default=4000,
        help="Tamanho do chunk para processamento de áudio",
    )

    args = parser.parse_args()

    # Configura o logger para exibir mensagens durante o teste
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Define uma função para testar a transcrição
    async def test_transcription(
        audio_path: str, modelo_path: str, chunk_size: int
    ) -> None:
        """Testa a transcrição de um arquivo de áudio.

        Args:
            audio_path: Caminho para o arquivo de áudio.
            modelo_path: Caminho para o modelo Vosk.
            chunk_size: Tamanho do chunk para processamento.
        """
        # Verifica se o arquivo existe
        audio_file_path = pathlib.Path(audio_path)
        if not audio_file_path.exists():
            print(f"❌ Erro: O arquivo {audio_path} não existe.")
            return

        # Verifica se o modelo existe
        modelo_dir_path = pathlib.Path(modelo_path)
        if not modelo_dir_path.exists():
            print(f"❌ Erro: O modelo em {modelo_path} não existe.")
            print(
                "   Você precisa baixar o modelo Vosk para português e extraí-lo para este diretório."
            )
            print(
                "   Download: https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip"
            )
            return

        print(f"🎯 Testando transcrição do arquivo: {audio_path}")
        print(f"🧠 Usando modelo: {modelo_path}")
        print(f"⚙️ Parâmetros: chunk_size={chunk_size}")

        try:
            # Abre o arquivo como BytesIO para simular o processamento real
            with open(audio_file_path, "rb") as f:
                audio_data = io.BytesIO(f.read())

            # Carrega o modelo Vosk
            model = Model(modelo_path)

            # Abre o arquivo de áudio com wave
            audio_data.seek(0)
            wf = wave.open(audio_data, "rb")

            # Exibe informações sobre o arquivo de áudio
            print("\n📊 Informações do arquivo de áudio:")
            print(f"   Canais: {wf.getnchannels()}")
            print(f"   Width: {wf.getsampwidth()}")
            print(f"   Taxa de amostragem: {wf.getframerate()} Hz")
            print(f"   Frames: {wf.getnframes()}")
            print(
                f"   Duração: {wf.getnframes() / wf.getframerate():.2f} segundos"
            )

            # Configura o reconhecedor
            recognizer = KaldiRecognizer(model, wf.getframerate())
            recognizer.SetWords(True)

            # Medição de tempo para análise de performance
            import time

            start_time = time.time()

            # Processa o áudio em chunks
            results = []
            total_audio_processed = 0

            print("\n🔄 Processando áudio...")

            while True:
                data = wf.readframes(chunk_size)
                if len(data) == 0:
                    break

                total_audio_processed += len(data)

                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    if "text" in result and result["text"]:
                        results.append(result["text"])
                        print(f'   ↪ Trecho reconhecido: "{result["text"]}"')

            # Obtém o resultado final
            final_result = json.loads(recognizer.FinalResult())
            if "text" in final_result and final_result["text"]:
                results.append(final_result["text"])
                print(f'   ↪ Trecho final: "{final_result["text"]}"')

            # Calcula o tempo de processamento
            elapsed_time = time.time() - start_time

            # Junta todos os resultados
            transcription = " ".join(results)

            print("\n✅ Transcrição concluída!")
            print(f"⏱️ Tempo de processamento: {elapsed_time:.2f} segundos")
            print(
                f"📈 Velocidade: {total_audio_processed / elapsed_time / 1024:.2f} KB/s"
            )

            # Exibe a transcrição completa
            print("\n📝 Transcrição completa:")
            print(f'"{transcription}"')

            # Se não houver transcrição, exibe uma mensagem
            if not transcription:
                print("❗ Nenhum texto foi reconhecido no áudio.")

            # Verificação de palavras comuns para análise básica de qualidade
            common_words = [
                "eu",
                "você",
                "ele",
                "ela",
                "nós",
                "eles",
                "sim",
                "não",
                "porque",
                "como",
            ]
            words_in_transcript = set(transcription.lower().split())
            common_words_found = words_in_transcript.intersection(common_words)

            print("\n📊 Estatísticas da transcrição:")
            print(f"   Total de palavras: {len(transcription.split())}")
            print(
                f"   Palavras comuns encontradas: {', '.join(common_words_found) if common_words_found else 'nenhuma'}"
            )

        except Exception as e:
            print(f"❌ Erro durante a transcrição: {str(e)}")
            import traceback

            traceback.print_exc()

    # Executa o teste
    try:
        asyncio.run(
            test_transcription(args.arquivo, args.modelo, args.chunk_size)
        )
    except KeyboardInterrupt:
        print("\n⚠️ Teste interrompido pelo usuário.")
    except Exception as e:
        print(f"❌ Erro inesperado: {str(e)}")
        import traceback

        traceback.print_exc()
