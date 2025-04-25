"""Módulo responsável por fazer o download de músicas do Youtube."""

from __future__ import annotations

import asyncio
import io
import logging
import shlex
import subprocess  # noqa: S404
import time
from typing import IO, Any, cast

import discord
import yt_dlp
from discord.opus import Encoder
from requests import get

from src.errors.bad_link import BadLink
from src.errors.nothingfound import NothingFoundError

logger = logging.getLogger(__name__)


yt_dlp.utils.bug_reports_message = lambda: logger.warning(
    "Please report this issue",
)

ytdl_format_options = {
    "format": "140",
    "outtmpl": ".audios/%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": False,
    "extract_flat": True,
    "verbose": True,
    "no_warnings": False,
    "default_search": "auto_warning",
    "concurrent-fragments": 8,
    "flat-playlist": True,
    "cookiefile": "cookies.txt",
}

ffmpeg_options: dict[str, Any] = {
    "options": "-vn",
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)


class AudioSourceTracked(discord.AudioSource):
    def __init__(self, source: discord.AudioSource) -> None:
        self._source = source
        self.count_20ms = 0

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

        self.data = data

        self.title = data.get("title")
        self.url = data.get("url")

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
        if data is None:
            raise BadLink(musicdata.get_url())
        if "entries" in data:
            data = data["entries"][0]

        # Use the URL directly for streaming instead of downloading the file
        return cls(
            FFmpegPCMAudio(
                source=data["url"],
                **ffmpeg_options,
            ),
            data=data,
            volume=volume,
        )


def search(arg: str) -> dict[str, Any]:
    """Pesquisa no Youtube e retorna a informação da música.

    Args:
        arg (str): A string representing the search query.

    Raises:
        NothingFoundError: If no music is found.

    Returns:
        dict[str, Any]: A dictionary containing the information of the music.

    """
    _start_time = time.time()

    try:
        get(arg, timeout=5)
    except Exception:  # noqa: BLE001
        video = ytdl.extract_info(
            f"ytsearch:{arg}",
            download=True,
            process=False,
        )
    else:
        video = ytdl.extract_info(arg, download=True, process=False)
    if video is None:
        raise NothingFoundError(arg)
    logger.info(
        f"Searched for {arg} in {time.time() - _start_time} seconds.",
    )
    return video


class YTMusicData:
    """Classe responsável por armazenar informações sobre uma música."""

    def __init__(self, video: dict[str, Any]) -> None:
        """Cria uma instância de YTMusicData.

        Args:
            video (dict[str, Any]):
                A dictionary containing the information of the music.

        """
        self._title: str = video.get("title", "Unknown")
        self._url: str = video.get(
            "url",
            video.get("original_url", "Unknown"),
        )
        self._video: dict[str, Any] = video
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
        if "entries" in result:
            logger.info(
                f"Found {result['entries']} results.",
            )
            return [cls(video) for video in result["entries"]]
        video = result
        return [cls(video)]

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
        return self._video.get("artist", "Unknown")

    @property
    def artist(self) -> str:
        """Retorna o artista da música.

        Returns:
            str: The artist of the music.

        """
        return self._video.get("artist", "Unknown")

    def get_thumbnail(self) -> str:
        """Retorna a URL da imagem de capa da música.

        Returns:
            str: The URL of the thumbnail.

        """
        return self._video.get("thumbnail", "Unknown")

    @property
    def thumbnail(self) -> str:
        """Retorna a URL da imagem de capa da música.

        Returns:
            str: The URL of the thumbnail.

        """
        return self._video.get("thumbnail", "Unknown")

    @property
    def duration(self) -> int:
        """Retorna a duração da música.

        Returns:
            int: The duration of the music.

        """
        return self._video.get("duration", 0)


class FFmpegPCMAudio(discord.AudioSource):
    """Classe responsável por fazer o streaming de áudio via FFmpeg."""

    def __init__(
        self,
        source: str | io.BufferedIOBase,
        *,
        executable: str = "ffmpeg",
        pipe: bool = False,
        stderr: io.TextIOWrapper | None = None,
        before_options: str | None = None,
        options: str | None = None,
    ) -> None:
        """Cria uma instância de FFmpegPCMAudio.

        Args:
            source (str | io.BufferedIOBase): A URL ou arquivo de áudio
            executable (str, optional): O executável a ser usado.
            Defaults to "ffmpeg".
            pipe (bool, optional): Se o áudio deve ser enviado via pipe.
            Defaults to False.
            stderr (io.TextIOWrapper | None, optional): O stderr a ser usado.
            Defaults to None.
            before_options (str | None, optional): Opções antes do input.
            Defaults to None.
            options (str | None, optional): Opções adicionais.
            Defaults to None.

        Raises:
            discord.ClientException: Se o executável não for encontrado.

        """
        stdin = None if not pipe else source
        args: list[str] = [executable]
        if isinstance(before_options, str):
            args.extend(shlex.split(before_options))
        args.extend(("-i", cast("str", "-" if pipe else source)))
        args.extend((
            "-f",
            "s16le",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-loglevel",
            "warning",
        ))
        args.extend((
            "-reconnect",
            "1",
            "-reconnect_streamed",
            "1",
            "-reconnect_delay_max",
            "5",
        ))
        if isinstance(options, str):
            args.extend(shlex.split(options))
        args.append("pipe:1")

        logger.debug(f"FFmpegPCMAudio command: {' '.join(args)}")

        try:
            self._process = subprocess.Popen(  # noqa: S603
                args,
                stdin=cast("IO", stdin) if pipe else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=stderr or subprocess.PIPE,
            )
        except FileNotFoundError:
            raise discord.ClientException(
                executable + " was not found.",
            ) from None
        except subprocess.SubprocessError as exc:
            msg = f"Popen failed: {exc.__class__.__name__}: {exc}"
            raise discord.ClientException(
                msg,
            ) from exc

    def read(self) -> bytes:
        """Read 20ms worth of audio.

        Returns:
            bytes: A bytes like object that represents the PCM data.

        """
        if self._process is None:
            return b""

        ret = b""
        # Lê apenas o tamanho exato de um frame
        try:
            ret = self._process.stdout.read(Encoder.FRAME_SIZE)  # type: ignore
            if len(ret) != Encoder.FRAME_SIZE:
                return b""
        except (OSError, ValueError):
            self.cleanup()
            return b""

        return ret

    def cleanup(self) -> None:
        """Clean up the process."""
        proc = getattr(self, "_process", None)
        if proc is None:
            return

        try:
            proc.kill()
            if proc.poll() is None:
                proc.communicate()
        except Exception:  # noqa: BLE001
            pass

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
