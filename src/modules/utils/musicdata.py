import subprocess
from discord.opus import Encoder
import io
import shlex
import asyncio
from src.modules.errors.bad_link import BadLink
import discord
import yt_dlp as youtube_dl

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'options': '-vn',
    'before_options':
    '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class MusicData:

    def __init__(self, title, url):
        self.title = title
        self.url = url

    @classmethod
    def from_url(cls, url):
        with ytdl:
            result = ytdl.extract_info(url, download=False)
        if result is None:
            raise BadLink(url)
        video = result['entries'][0] if 'entries' in result else result
        return cls(video['title'], video['webpage_url'])


class YoutubeDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, volume=0.3):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_music_data(cls,
                              musicdata: MusicData,
                              *,
                              loop=None,
                              volume=0.3):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(musicdata.url, download=False))
        if data is None:
            raise BadLink(musicdata.url)
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if 'url' in data else ytdl.prepare_filename(
            data)
        return cls(discord.FFmpegPCMAudio(
            filename,
            **ffmpeg_options),  # type: ignore
            data=data,
            volume=volume)


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