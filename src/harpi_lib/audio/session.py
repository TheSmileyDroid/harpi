"""PlaybackSession — one deep module holding a guild's playback state.

A session owns everything a single guild's audio needs: the voice client,
the :class:`AudioController`, the :class:`MixerSource`, and the mixer's
end-of-track observer wiring.  Later slices add the queue, the current
track, the loop mode, the volume, the background layers, and the TTS track;
the session is the seam the cogs, routes, and tests cross.

Threading contract
------------------
The bot's event loop is the single writer for all session state.  Every
session verb must therefore run on the **bot's** loop; verbs that touch
discord.py's async voice APIs (``leave``, and later the queue and volume
verbs) are async, while ``start`` and ``cleanup`` are synchronous but still
bot-loop-bound.  The mixer itself is an exception by design:
``MixerSource.read()`` runs on discord.py's voice-sending thread, and its
``queue_end`` / ``track_end`` observers fire from that same thread.  Those
callbacks must never touch session state directly — they marshal work back
onto the bot's event loop (``asyncio.run_coroutine_threadsafe`` /
``call_soon_threadsafe``) before mutating anything.  Anything else that
needs a session (the web panel, the cogs) reaches it through the
:class:`SessionManager` and the ``run_on_bot_loop`` bridge, never by
calling into the controller or mixer directly.
"""

from __future__ import annotations

from dataclasses import dataclass

import discord

from src.harpi_lib.audio.controller import AudioController
from src.harpi_lib.audio.mixer import MixerSource


@dataclass(frozen=True)
class SessionStatus:
    """Immutable snapshot of a session's state, safe to pass across threads.

    The snapshot is produced on the bot's event loop (sampled from the
    voice client) and is immutable, so once built it can be handed to
    any reader — the panel JSON, the HTMX fragments, the server status,
    the chat ``list`` command.  Later slices add the current track, the
    queue, the layers, the progress, the loop mode, and the volume.
    """

    guild_id: int
    connected: bool
    is_playing: bool
    is_paused: bool


class PlaybackSession:
    """All playback state and behaviour for a single guild.

    The controller and the mixer are internal seams: nothing outside the
    session touches them.  State is read through :attr:`status` and
    changed through the session's verbs (``start``, ``cleanup``,
    ``leave``).
    """

    def __init__(
        self,
        guild_id: int,
        voice_client: discord.VoiceClient,
    ) -> None:
        self._guild_id = guild_id
        self._voice_client = voice_client

        self._controller = AudioController()
        self._mixer = MixerSource(self._controller)
        self._wire_mixer_observers()

    def _wire_mixer_observers(self) -> None:
        """Hook the mixer's end-of-track events to the session's own handlers."""
        self._mixer.add_observer("queue_end", self._on_queue_end)
        self._mixer.add_observer("track_end", self._on_track_end)

    # --- End-of-track handlers (fired from the voice-sending thread) ---

    def _on_queue_end(self) -> None:
        """The current queue track finished reading.

        The controller already cleared and cleaned the finished source.
        Later slices advance the queue here, marshalling back onto the
        bot's event loop as the threading contract requires.
        """

    def _on_track_end(self, to_remove: list[discord.AudioSource]) -> None:
        """A background layer finished reading.

        The controller already removed and cleaned the finished sources.
        Later slices keep the layer bookkeeping here, marshalling back
        onto the bot's event loop as the threading contract requires.
        """

    # --- Public API ---

    @property
    def guild_id(self) -> int:
        return self._guild_id

    @property
    def status(self) -> SessionStatus:
        """Snapshot of this session's state; read from the bot's event loop.

        Sampling the voice client from any other thread races against the
        bot loop, the session's single writer.  Panel readers cross the
        loop via the ``run_on_bot_loop`` bridge; the immutable snapshot
        is safe to hand around once built.
        """
        voice_client = self._voice_client
        return SessionStatus(
            guild_id=self._guild_id,
            connected=voice_client.is_connected(),
            is_playing=voice_client.is_playing(),
            is_paused=voice_client.is_paused(),
        )

    def start(self) -> None:
        """Begin streaming the mixer to the voice client."""
        self._voice_client.play(self._mixer)

    def cleanup(self) -> None:
        """Release the controller's sources and shut down the mixer.

        Does not touch the voice client; callers that want to leave the
        channel use :meth:`leave`.
        """
        self._controller.cleanup_all()
        self._mixer.cleanup()

    async def leave(self) -> None:
        """Disconnect the voice client if it is still connected."""
        voice_client = self._voice_client
        if voice_client.is_connected():
            await voice_client.disconnect()
