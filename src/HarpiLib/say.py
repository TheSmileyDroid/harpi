import io

import discord
import discord.ext.commands as commands
from gtts import gTTS

from src.HarpiLib.music_helpers import (
    AlreadyPlaying,
    voice_client,
)
from src.HarpiLib.musicdata.ytmusicdata import (
    AudioSourceTracked,
    FastStartFFmpegPCMAudio,
)


async def say(ctx: commands.Context, text: str) -> None:
    voice: discord.VoiceClient = await voice_client(ctx)
    if voice.is_playing():
        raise AlreadyPlaying("Já estou reproduzindo algo")
    fp = io.BytesIO()
    tts = gTTS(text=text, lang="pt", tld="com.br")
    tts.write_to_fp(fp)
    fp.seek(0)
    voice.play(
        AudioSourceTracked(FastStartFFmpegPCMAudio(fp, pipe=True)),
    )
