import subprocess
from typing import Any, Dict
from discord.opus import Encoder
import io
import shlex
import asyncio
from src.modules.errors.bad_link import BadLink
import discord
import yt_dlp as youtube_dl  # type: ignore
from requests import get

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,
    'extract_flat': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options: dict[str, Any] = {
    'options': '-vn',
    'before_options':
    '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


def search(arg):
    with ytdl:
        try:
            get(arg)
        except Exception:
            video = ytdl.extract_info(f"ytsearch:{arg}", download=False)
            if video is None:
                raise Exception("Não foi possível encontrar nenhum vídeo.")
            if 'entries' in video:
                video = video['entries'][0]
        else:
            video = ytdl.extract_info(arg, download=False)

    return video


class MusicData:

    def __init__(self, title, url):
        self.title = title
        self.url = url

    @classmethod
    def from_url(cls, url: str) -> list['MusicData']:
        print(url)
        result = search(url)
        if result is None:
            raise BadLink(url)
        if 'entries' in result:
            return [
                cls(video['title'], video['url'])
                for video in result['entries']
            ]
        video = result
        return [cls(video['title'], video['url'])]


class FFmpegPCMAudio(discord.AudioSource):
    def __init__(self, source, *,
                 executable='ffmpeg',
                 pipe=False,
                 stderr=None,
                 before_options=None,
                 options=None):
        stdin = None if not pipe else source
        args = [executable]
        if isinstance(before_options, str):
            args.extend(shlex.split(before_options))
        args.append('-i')
        args.append('-' if pipe else source)
        args.extend(('-f', 's16le', '-ar', '48000',
                    '-ac', '2', '-loglevel', 'warning'))
        if isinstance(options, str):
            args.extend(shlex.split(options))
        args.append('pipe:1')
        self._process = None
        try:
            self._process = subprocess.Popen(
                args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=stderr)
            self._stdout = io.BytesIO(
                self._process.communicate(input=stdin)[0]
            )
        except FileNotFoundError:
            raise discord.ClientException(
                executable + ' was not found.') from None
        except subprocess.SubprocessError as exc:
            raise discord.ClientException(
                'Popen failed: {0.__class__.__name__}: {0}'
                .format(exc)) from exc

    def read(self):
        ret = self._stdout.read(Encoder.FRAME_SIZE)
        if len(ret) != Encoder.FRAME_SIZE:
            return b''
        return ret

    def cleanup(self):
        proc = self._process
        if proc is None:
            return
        proc.kill()
        if proc.poll() is None:
            proc.communicate()

        self._process = None


class YoutubeDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source: FFmpegPCMAudio, *, data: Dict[str, Any], volume=0.3):
        super().__init__(source, volume)

        self.data: Dict[str, Any] = data

        self.title: str = data.get('title') or 'Unknown'
        self.url: str = data.get('url') or 'Unknown'

    @classmethod
    async def from_music_data(cls,
                              musicdata: MusicData,
                              *,
                              loop=None,
                              volume=0.3):
        loop = loop or asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(musicdata.url, download=False))
        if result is None or result is not dict:
            raise BadLink(musicdata.url)
        data: Dict[str, Any] = result
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if 'url' in data else ytdl.prepare_filename(
            data)
        return cls(FFmpegPCMAudio(
            filename,
            **ffmpeg_options),
            data=data,
            volume=volume)
