from io import BytesIO
from pathlib import Path

import discord
import discord.ext.commands as commands
from gtts import gTTS

from src.HarpiLib.music_helpers import (
    AlreadyPlaying,
    guild,
    voice_client,
)
from src.HarpiLib.musicdata.ytmusicdata import (
    AudioSourceTracked,
    FFmpegPCMAudio,
)


async def say(ctx: commands.Context, text: str) -> None:
    voice: discord.VoiceClient = await voice_client(ctx)
    if voice.is_playing():
        raise AlreadyPlaying("Já estou reproduzindo algo")
    fp = BytesIO()
    tts = gTTS(text=text, lang="pt", tld="com.br")
    tts.write_to_fp(fp)
    Path.mkdir(Path(".audios"), exist_ok=True, parents=True)
    tts.save(f".audios/{guild(ctx).id}.mp3")
    fp.seek(0)
    voice.play(
        AudioSourceTracked(FFmpegPCMAudio(fp, pipe=True)),
    )
