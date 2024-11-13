"""Módulo responsável por fazer o download de músicas do Youtube."""

from __future__ import annotations

import asyncio
import io
import logging
import shlex
import subprocess  # noqa: S404
import time
from typing import Any

import discord
import yt_dlp
from discord.opus import Encoder

from src.errors.bad_link import BadLink
from src.errors.nothingfound import NothingFoundError

yt_dlp.utils.bug_reports_message = lambda: ""

ytdl_format_options = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "downloader": "aria2c",
    "restrictfilenames": True,
    "noplaylist": False,
    "extract_flat": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": True,
    "quiet": False,
    "no_warnings": False,
    "default_search": "auto_warning",
    "source_address": "0.0.0.0",  # noqa: S104
    "concurrent-fragments": 8,
    "flat-playlist": True,
}

ffmpeg_options: dict[str, Any] = {
    "options": "-vn",
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",  # noqa: E501
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

logger = logging.getLogger(__name__)


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
        filename = (
            data["url"] if "url" in data else ytdl.prepare_filename(data)
        )
        return cls(
            FastStartFFmpegPCMAudio(filename, **ffmpeg_options),
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
    video = ytdl.extract_info(arg, download=False, process=False)
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
        """Cria uma instância de FFmpegPCMAudio.

        Args:
            source (io.BufferedIOBase): A file-like object that reads
            byte data representing raw PCM.
            executable (str, optional): The executable to use.
            Defaults to "ffmpeg".
            pipe (bool, optional): Whether to pipe the audio.
            Defaults to False.
            stderr (io.TextIOWrapper | None, optional): The stderr to use.
            Defaults to None.
            before_options (str | None, optional): The before options to use.
            Defaults to None.
            options (str | None, optional): The options to use.
            Defaults to None.

        Raises:
            discord.ClientException: _description_

        """
        stdin = None if not pipe else source
        args: list[str] = [executable]
        if isinstance(before_options, str):
            args.extend(shlex.split(before_options))
        args.extend(("-i", "-" if pipe else source))
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
        if isinstance(options, str):
            args.extend(shlex.split(options))
        args.append("pipe:1")
        self._process = None
        try:
            self._process = subprocess.Popen(  # noqa: S603
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=stderr,
            )
            self._stdout = io.BytesIO(
                self._process.communicate(input=stdin)[0],
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
            bytes: A bytes like object that represents the PCM or Opus data.

        """
        ret = self._stdout.read(Encoder.FRAME_SIZE)
        if len(ret) != Encoder.FRAME_SIZE:
            return b""
        return ret

    def cleanup(self) -> None:
        """Clean up the process."""
        proc = self._process
        if proc is None:
            return
        proc.kill()
        if proc.poll() is None:
            proc.communicate()

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
        """Create a FFmpegPCMAudio instance.

        Args:
            source (io.BufferedIOBase): The source of the audio.
            executable (str, optional): The executable to use. Defaults to "ffmpeg".
            pipe (bool, optional): Whether to pipe the audio. Defaults to False.
            stderr (io.TextIOWrapper | None, optional): The stderr to use. Defaults to None.
            before_options (str | None, optional): The before options to use. Defaults to None.
            options (str | None, optional): The options to use. Defaults to None.

        """  # noqa: E501
        if isinstance(before_options, str):
            before_options = (
                f"{before_options} -analyzeduration 0 -probesize 32"
            )
        else:
            before_options = "-analyzeduration 0 -probesize 32"

        super().__init__(
            source,
            executable=executable,
            pipe=pipe,
            stderr=stderr,
            before_options=before_options,
            options=options,
        )
