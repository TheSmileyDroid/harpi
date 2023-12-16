import logging
import subprocess
from typing import Any, Dict, Optional
from discord.opus import Encoder
import io
import shlex
import asyncio
from src.res.errors.bad_link import BadLink
import discord
import yt_dlp as youtube_dl
from requests import get

from ..interfaces.imusicdata import IMusicData

youtube_dl.utils.bug_reports_message = lambda: ""

ytdl_format_options = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": False,
    "extract_flat": True,
    "nocheckcertificate": True,
    "ignoreerrors": True,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",
}

ffmpeg_options: Dict[str, Any] = {
    "options": "-vn",
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

logger = logging.getLogger(__name__)


class YoutubeDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.3):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get("title")
        self.url = data.get("url")

    @classmethod
    async def from_music_data(
        cls,
        musicdata: IMusicData,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        volume=0.3,
    ):
        _loop: asyncio.AbstractEventLoop = loop or asyncio.get_event_loop()
        data: Any | dict[str, Any] = await _loop.run_in_executor(
            None,
            lambda: ytdl.extract_info(musicdata.get_url(), download=False),
        )
        if data is None:
            raise BadLink(musicdata.get_url())
        if "entries" in data:
            data = data["entries"][0]
        filename = data["url"] if "url" in data else ytdl.prepare_filename(data)
        return cls(
            discord.FFmpegPCMAudio(filename, **ffmpeg_options),
            data=data,
            volume=volume,
        )


def search(arg):
    with ytdl:
        try:
            get(arg)
        except Exception:
            video = ytdl.extract_info(f"ytsearch:{arg}", download=False)
            if video is None:
                raise Exception("Não foi possível encontrar nenhum vídeo.")
            if "entries" in video:
                video = video["entries"][0]
        else:
            video = ytdl.extract_info(arg, download=False)

    return video


class YTMusicData(IMusicData):
    def __init__(self, title: str, url: str):
        self._title: str = title
        self._url: str = url

    @classmethod
    def from_url(cls, url: str) -> list["YTMusicData"]:
        logger.info(f"Searching for {url}")
        result = search(url)
        if result is None:
            raise BadLink(url)
        if "entries" in result:
            return [cls(video["title"], video["url"]) for video in result["entries"]]
        video = result
        if "original_url" in video.keys():
            return [cls(video["title"], video["original_url"])]
        else:
            return [cls(video["title"], video["url"])]

    def get_title(self) -> str:
        return self._title

    def get_url(self) -> str:
        return self._url

    def get_artist(self) -> str:
        return "Unknown"

    async def get_source(self) -> YoutubeDLSource:
        return await YoutubeDLSource.from_music_data(self)  # type: ignore


class FFmpegPCMAudio(discord.AudioSource):
    def __init__(
        self,
        source,
        *,
        executable="ffmpeg",
        pipe=False,
        stderr=None,
        before_options=None,
        options=None,
    ):
        stdin = None if not pipe else source
        args = [executable]
        if isinstance(before_options, str):
            args.extend(shlex.split(before_options))
        args.append("-i")
        args.append("-" if pipe else source)
        args.extend(("-f", "s16le", "-ar", "48000", "-ac", "2", "-loglevel", "warning"))
        if isinstance(options, str):
            args.extend(shlex.split(options))
        args.append("pipe:1")
        self._process = None
        try:
            self._process = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=stderr,
            )
            self._stdout = io.BytesIO(self._process.communicate(input=stdin)[0])
        except FileNotFoundError:
            raise discord.ClientException(executable + " was not found.") from None
        except subprocess.SubprocessError as exc:
            raise discord.ClientException(
                "Popen failed: {0.__class__.__name__}: {0}".format(exc)
            ) from exc

    def read(self):
        ret = self._stdout.read(Encoder.FRAME_SIZE)
        if len(ret) != Encoder.FRAME_SIZE:
            return b""
        return ret

    def cleanup(self):
        proc = self._process
        if proc is None:
            return
        proc.kill()
        if proc.poll() is None:
            proc.communicate()

        self._process = None
