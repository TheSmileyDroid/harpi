import itertools
import logging
import subprocess
import time
from typing import Any, Dict, Optional
from discord.opus import Encoder
import io
import shlex
import asyncio
from src.res.errors.bad_link import BadLink
import discord
import yt_dlp


yt_dlp.utils.bug_reports_message = lambda: ""

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

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

logger = logging.getLogger(__name__)


class YoutubeDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.3):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get("title")
        self.url = data.get("url")

    @classmethod
    async def from_music_data(cls, musicdata: "YTMusicData", *, volume=0.3):
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(musicdata.get_url(), download=False)
        )
        if data is None:
            raise BadLink(musicdata.get_url())
        if "entries" in data:
            data = data["entries"][0]
        filename = data["url"] if "url" in data else ytdl.prepare_filename(data)
        return cls(
            FastStartFFmpegPCMAudio(filename, **ffmpeg_options),
            data=data,
            volume=volume,
        )


async def search(arg):
    _start_time = time.time()
    if not arg.startswith("https://") and not arg.startswith("http://"):
        arg = f"ytsearch:{arg}"
    loop = asyncio.get_event_loop()
    video = await loop.run_in_executor(
        None, lambda: ytdl.extract_info(arg, download=False, process=False)
    )

    if video is None:
        raise Exception("Não foi possível encontrar nenhum vídeo.")
    if "entries" in video:
        videoEntries: list[dict[str, Any]] = list(video["entries"])
        video = videoEntries[0]
    logger.info(f"Searched for {arg} in {time.time() - _start_time} seconds.")
    return video


class YTMusicData:
    def __init__(self, title: str, url: str):
        self._title: str = title
        self._url: str = url
        self._source: Optional[YoutubeDLSource] = None

    @classmethod
    async def from_url(cls, url: str) -> list["YTMusicData"]:
        logger.info(f"Searching for {url}")
        result = await search(url)
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


class FastStartFFmpegPCMAudio(discord.FFmpegPCMAudio):
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
        if isinstance(before_options, str):
            before_options = f"{before_options} -analyzeduration 0 -probesize 32"
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
