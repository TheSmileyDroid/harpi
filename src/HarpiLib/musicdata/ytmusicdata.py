"""Módulo responsável por fazer o download de músicas do Youtube."""

from __future__ import annotations

import asyncio
import io
import logging
import re
import shlex
import subprocess  # noqa: S404
import time
from typing import IO, Any, cast, override

import discord
import yt_dlp
from discord.opus import Encoder

from src.errors.nothingfound import NothingFoundError

logger = logging.getLogger(__name__)

ytdl_format_options: yt_dlp._Params = {
    "format": "m4a/bestaudio/best",
    "outtmpl": ".audios/%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": False,
    "extract_flat": True,
    "verbose": True,
    "no_warnings": False,
    "default_search": "auto_warning",
    "cookiefile": "cookies.txt",
}

ffmpeg_options = {
    "options": "-vn",
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)


class AudioSourceTracked(discord.AudioSource):
    def __init__(self, source: discord.AudioSource) -> None:
        self._source: discord.AudioSource = source
        self.count_20ms: int = 0

    def read(self) -> bytes:
        data = self._source.read()
        if data:
            self.count_20ms += 1
        return data

    @property
    def progress(self) -> float:
        return self.count_20ms * 0.02  # count_20ms * 20ms


class YoutubeDLSource(discord.PCMVolumeTransformer):
    """Classe responsável por fazer o download de músicas do Youtube."""

    def __init__(
        self,
        source: discord.AudioSource,
        *,
        data: dict[str, Any],
        volume: float = 0.3,
    ) -> None:
        """Cria uma instância de YoutubeDLSource."""
        super().__init__(source, volume)

        self.data: dict[str, str | int] = data

        self.title: str = data.get("title", "Unknown Title")
        self.url: str = data.get("url", "Unknown URL")

    @classmethod
    async def from_music_data(
        cls,
        musicdata: YTMusicData,
        volume: float = 0.3,
    ) -> YoutubeDLSource:
        """Create a YoutubeDLSource instance from a YTMusicData.

        Args:
            musicdata (YTMusicData): Music data to use.
            volume (float, optional): Volume to be set. Defaults to 0.3.

        Raises:
            BadLink: If the link is invalid.

        Returns:
            YoutubeDLSource: The created YoutubeDLSource instance.

        """
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None,
            lambda: ytdl.extract_info(musicdata.get_url(), download=False),
        )

        assert isinstance(data, dict), "Invalid data from ytdl"
        if "entries" in data:
            data = data["entries"][0]
        assert isinstance(data, dict), "Invalid data from ytdl"

        url = data.get("url")
        assert isinstance(url, str), "Invalid URL from ytdl"
        # Use the URL directly for streaming instead of downloading the file
        return cls(
            FFmpegPCMAudio(
                source=url,
                options=ffmpeg_options["options"],
                before_options=ffmpeg_options["before_options"],
            ),
            data=dict(data),
            volume=volume,
        )


def search(arg: str):
    """Pesquisa no Youtube e retorna a informação da música.

    Args:
        arg (str): A string representing the search query.

    Raises:
        NothingFoundError: If no music is found.

    Returns:
        dict[str, Any]: A dictionary containing the information of the music.

    """
    _start_time = time.time()

    URL_REGEX = re.compile(
        r"https?://(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
    )
    video: dict | None = None
    try:
        if not re.match(URL_REGEX, arg):
            video = cast(
                dict[str, str | int],
                cast(
                    object,
                    ytdl.extract_info(
                        f"ytsearch:{arg}",
                        download=True,
                        process=False,
                    ),
                ),
            )
        else:
            video = cast(
                dict[str, str | int],
                cast(
                    object,
                    ytdl.extract_info(arg, download=True, process=False),
                ),
            )
    except Exception as e:
        logger.error(f"Error during search: {e}")
    if not video:
        raise NothingFoundError(arg)
    logger.info(
        f"Searched for {arg} in {time.time() - _start_time} seconds.",
    )
    return video


class YTMusicData:
    """Classe responsável por armazenar informações sobre uma música."""

    def __init__(self, video: dict[str, str | int]) -> None:
        """Cria uma instância de YTMusicData.

        Args:
            video (dict[str, Any]):
                A dictionary containing the information of the music.

        """
        self._title: str = cast(str, video.get("title", "Unknown"))
        self._url: str = cast(
            str,
            video.get(
                "url",
                cast(str, video.get("original_url", "Unknown")),
            ),
        )
        self._video: dict[str, str | int] = video
        self._source: YoutubeDLSource | None = None

    @classmethod
    async def from_url(cls, url: str) -> list[YTMusicData]:
        """Cria uma instância de YTMusicData a partir de uma URL.

        Args:
            url (str): A string representing the URL.

        Returns:
            list[YTMusicData]: A list of YTMusicData instances.

        """
        logger.info(f"Searching for {url}")
        result = search(url)
        if result.get("entries"):
            logger.info(
                f"Found {result.get('entries')} results.",
            )
            return [
                cls(dict(cast(dict[str, str | int], video)))
                for video in cast(list, result.get("entries"))
            ]
        video = result
        return cast(
            list[YTMusicData], [cls(dict(cast(dict[str, str | int], video)))]
        )

    def get_title(self) -> str:
        """Retorna o título da música.

        Returns:
            str: The title of the music.

        """
        return self._title

    def get_metadata(self, key: str):  # noqa: ANN201
        return self._video.get(key, None)

    @property
    def title(self) -> str:
        """Retorna o título da música.

        Returns:
            str: The title of the music.

        """
        return self._title

    def get_url(self) -> str:
        """Retorna a URL da música.

        Returns:
            str: The URL of the music.

        """
        return self._url

    @property
    def url(self) -> str:
        """Retorna a URL da música.

        Returns:
            str: The URL of the music.

        """
        return self._url

    def get_artist(self) -> str:
        """Retorna o artista da música.

        Returns:
            str: The artist of the music.

        """
        return cast(str, self._video.get("artist", "Unknown"))

    @property
    def artist(self) -> str:
        """Retorna o artista da música.

        Returns:
            str: The artist of the music.

        """
        return cast(str, self._video.get("artist", "Unknown"))

    def get_thumbnail(self) -> str:
        """Retorna a URL da imagem de capa da música.

        Returns:
            str: The URL of the thumbnail.

        """
        return cast(str, self._video.get("thumbnail", "Unknown"))

    @property
    def thumbnail(self) -> str:
        """Retorna a URL da imagem de capa da música.

        Returns:
            str: The URL of the thumbnail.

        """
        return cast(str, self._video.get("thumbnail", "Unknown"))

    @property
    def duration(self) -> int:
        """Retorna a duração da música.

        Returns:
            int: The duration of the music.

        """
        return cast(int, self._video.get("duration", 0))


class FFmpegPCMAudio(discord.AudioSource):
    """Classe responsável por fazer o streaming de áudio via FFmpeg com tipagem rigorosa.

    Melhorias aplicadas:
    1. Lazy Loading: O processo só inicia na primeira leitura (economiza recursos).
    2. Deadlock Fix: Stderr é redirecionado para DEVNULL se não fornecido.
    3. Type Hints: Tipagem completa para validação estática (Mypy/Pyright).
    4. Auto-Reconnection: Flags de reconexão aplicadas apenas para URLs HTTP(s).
    """

    def __init__(
        self,
        source: str | io.BufferedIOBase,
        *,
        executable: str = "ffmpeg",
        pipe: bool = False,
        stderr: IO[str] | None = None,
        before_options: str | None = None,
        options: str | None = None,
    ) -> None:
        """Inicializa o FFmpegPCMAudio.

        Args:
            source: URL (str) ou objeto de arquivo (buffer) para leitura.
            executable: Nome ou caminho do executável do ffmpeg.
            pipe: Se True, o source será passado via stdin.
            stderr: Arquivo/Pipe para log de erros.
            before_options: Argumentos do FFmpeg antes do input (-i).
            options: Argumentos do FFmpeg depois do input.
        """
        self.source: str | io.BufferedIOBase = source
        self.executable: str = executable
        self.pipe: bool = pipe
        self.stderr: IO[str] | None = stderr
        self.before_options: str | None = before_options
        self.options: str | None = options

        # O processo é tipado como Popen que retorna bytes no stdout
        self._process: subprocess.Popen[bytes] | None = None

    def _spawn_process(self) -> None:
        """Inicia o subprocesso FFmpeg (Lazy Loading)."""
        args: list[str] = [self.executable]

        # 1. Before Options
        if self.before_options:
            args.extend(shlex.split(self.before_options))

        # 2. Flags de Reconexão (Apenas para URLs HTTP/HTTPS)
        # Evita erro em arquivos locais onde essas flags não existem.
        if isinstance(self.source, str) and self.source.startswith(
            ("http:", "https:")
        ):
            # Verifica se o usuário já não passou essas flags manualmente
            if (
                not self.before_options
                or "-reconnect" not in self.before_options
            ):
                args.extend(
                    [
                        "-reconnect",
                        "1",
                        "-reconnect_streamed",
                        "1",
                        "-reconnect_delay_max",
                        "5",
                    ]
                )

        # 3. Input (-i)
        args.append("-i")
        args.append("-" if self.pipe else str(self.source))

        # 4. Codec Options (Padrão Discord: PCM 16-bit Little Endian, 48kHz, Stereo)
        args.extend(
            [
                "-f",
                "s16le",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-loglevel",
                "warning",
            ]
        )

        # 5. After Options
        if self.options:
            args.extend(shlex.split(self.options))

        # 6. Output Pipe
        args.append("pipe:1")

        logger.debug(f"Iniciando FFmpeg com comando: {shlex.join(args)}")

        # Configuração do Stdin
        # Se pipe=True, usamos self.source como stdin. Se não, usamos DEVNULL.
        # Precisamos garantir que stdin seja um arquivo válido ou None/DEVNULL.
        input_stream: IO[bytes] | int | None = None
        if self.pipe:
            if isinstance(self.source, (str, bytes)):
                # Se source for string mas pipe=True, isso geralmente é erro de uso,
                # a menos que a string seja os dados brutos (o que str não deveria ser).
                # Assumimos aqui que source é um Buffer válido se pipe=True.
                pass
            input_stream = cast(IO[bytes], cast(object, self.source))
        else:
            input_stream = subprocess.DEVNULL  # type: ignore

        try:
            # FIX DEADLOCK: Usar DEVNULL se stderr não for definido pelo usuário.
            # Nunca deixe stderr=subprocess.PIPE sem ler os dados, isso trava o processo.
            stderr_dest = self.stderr if self.stderr else subprocess.DEVNULL

            self._process = subprocess.Popen(
                args,
                stdin=input_stream,
                stdout=subprocess.PIPE,
                stderr=stderr_dest,
            )
        except FileNotFoundError:
            raise discord.ClientException(
                f"Executável '{self.executable}' não foi encontrado."
            ) from None
        except subprocess.SubprocessError as exc:
            raise discord.ClientException(
                f"Falha ao iniciar Popen: {exc}"
            ) from exc

    @override
    def read(self) -> bytes:
        """Lê 20ms de áudio PCM."""
        # Inicialização sob demanda
        if self._process is None:
            self._spawn_process()

        # Verificação de segurança pós-spawn
        if self._process is None or self._process.stdout is None:
            return b""

        ret: bytes = b""
        try:
            # Lê o tamanho exato do frame (geralmente 3840 bytes para estéreo/48k)
            ret = self._process.stdout.read(Encoder.FRAME_SIZE)

            # Se o tamanho lido for menor que o frame, chegamos ao fim do stream ou erro.
            if len(ret) != Encoder.FRAME_SIZE:
                # Opcional: Logar se foi um corte abrupto
                # if len(ret) > 0: logger.warning("Frame incompleto recebido.")
                self.cleanup()
                return b""
        except (OSError, ValueError) as e:
            logger.error(f"Erro ao ler do FFmpeg: {e}")
            self.cleanup()
            return b""

        return ret

    @override
    def cleanup(self) -> None:
        """Encerra o processo de forma limpa."""
        proc = self._process
        if proc is None:
            return

        try:
            # Tenta terminar gentilmente (SIGTERM)
            proc.terminate()
            try:
                # Aguarda brevemente para evitar processos zumbis
                _ = proc.wait(timeout=0.1)
            except subprocess.TimeoutExpired:
                # Se não fechar, mata forçado (SIGKILL)
                proc.kill()
                _ = proc.communicate()
        except Exception:
            # Ignora erros durante o cleanup para não crashar o bot
            pass
        finally:
            self._process = None


class FastStartFFmpegPCMAudio(discord.FFmpegPCMAudio):
    """Classe responsável por fazer o download de músicas do Youtube."""

    def __init__(
        self,
        source: io.BufferedIOBase,
        *,
        executable: str = "ffmpeg",
        pipe: bool = False,
        stderr: io.TextIOWrapper | None = None,
        before_options: str | None = None,
        options: str | None = None,
    ) -> None:
        """Create a FFmpegPCMAudio instance."""
        if isinstance(before_options, str):
            before_options = (
                f"{before_options} -analyzeduration 1000000 -probesize 1000000"
            )
        else:
            before_options = "-analyzeduration 1000000 -probesize 1000000"

        super().__init__(
            source,
            executable=executable,
            pipe=pipe,
            stderr=cast("IO[bytes]", stderr),
            before_options=before_options,
            options=options,
        )
