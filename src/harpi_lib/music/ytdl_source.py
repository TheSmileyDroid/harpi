"""Audio source that streams from YouTube via yt-dlp and FFmpeg."""

from __future__ import annotations

import asyncio
import threading
import uuid
from typing import Any, NoReturn, override

import discord

from src.harpi_lib.music import stream_probe, ytmusic
from src.harpi_lib.music.ffmpeg_source import FFmpegPCMAudio, ffmpeg_options
from src.harpi_lib.music.ytmusic import YTMusicData

BYTES_PER_SECOND = 48000 * 2 * 2


class UniqueAudioSource(discord.PCMVolumeTransformer):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.id: str = str(uuid.uuid4())


class YoutubeDLSource(UniqueAudioSource):
    """Audio source that streams from YouTube via yt-dlp and FFmpeg."""

    def __init__(
        self, source: discord.AudioSource, data: dict[str, Any], **kwargs: Any
    ) -> None:
        super().__init__(original=source, **kwargs)

        self.data: dict[str, str | int] = data

        self.title: str = data.get("title", "Unknown Title")
        self.url: str = data.get("url", "Unknown URL")

        self._position_bytes: int = 0
        self._position_lock: threading.Lock = threading.Lock()
        self._seek_lock: threading.Lock = threading.Lock()

    @override
    def read(self) -> bytes:
        data = super().read()
        with self._position_lock:
            self._position_bytes += len(data)
        return data

    def position_seconds(self) -> float:
        with self._position_lock:
            return self._position_bytes / BYTES_PER_SECOND

    def seek(self, position: float) -> None:
        """Seek to an absolute position in seconds."""
        position = max(0.0, position)
        with self._seek_lock:
            original_seek = getattr(self.original, "seek", None)
            if callable(original_seek):
                original_seek(position)
            with self._position_lock:
                self._position_bytes = int(position * BYTES_PER_SECOND)

    @override
    def cleanup(self) -> None:
        """Forward cleanup to the underlying FFmpeg process."""
        original_cleanup = getattr(self.original, "cleanup", None)
        if callable(original_cleanup):
            original_cleanup()

    @classmethod
    async def from_music_data(
        cls,
        musicdata: YTMusicData,
        volume: float = 0.3,
    ) -> YoutubeDLSource:
        """Create a YoutubeDLSource instance from a YTMusicData.

        Reuses the formats already extracted at search time when possible
        (avoiding a redundant, easily-throttled second extraction) and
        bounds the fallback extraction with a timeout.  The selected
        stream is then duration-validated and probed for playability and
        silence before playback, so an unreachable, audio-less, or silent
        track is rejected up front.
        """
        info, stream_url = await cls._pick_stream(musicdata)
        data = dict(info)
        data["url"] = musicdata.get_url()
        return cls(
            FFmpegPCMAudio(
                source=stream_url,
                options=ffmpeg_options["options"],
                before_options=ffmpeg_options["before_options"],
            ),
            data=data,
            volume=volume,
        )

    @staticmethod
    def _validate_duration(info: dict[str, Any]) -> None:
        """Reject tracks whose duration is known to be zero or negative."""
        duration = info.get("duration")
        if duration is None:
            return
        try:
            duration = float(duration)
        except (TypeError, ValueError):
            return
        if duration <= 0:
            raise ValueError("track has no playable duration")

    @staticmethod
    def _reject_unplayable(musicdata: YTMusicData) -> NoReturn:
        raise ValueError(
            f"No playable stream found for URL: {musicdata.get_url()}"
        )

    @classmethod
    async def _probe_or_none(
        cls,
        info: dict[str, Any],
        stream_url: str,
    ) -> tuple[dict[str, Any], str] | None:
        """Validate and probe *stream_url*; None means try another stream."""
        cls._validate_duration(info)
        try:
            await asyncio.to_thread(
                stream_probe.probe_stream_audio, stream_url
            )
        except ValueError as exc:
            if not cls._probe_failure_is_transient(exc):
                raise
            return None
        return info, stream_url

    @classmethod
    async def _pick_stream(
        cls, musicdata: YTMusicData
    ) -> tuple[dict[str, Any], str]:
        """Pick and validate a playable stream for *musicdata*.

        Reuses the formats already extracted at search time, then retries
        with a fresh extraction if that stream cannot be probed.  Reusing
        avoids a redundant, easily-throttled second extraction in the
        common case; the fresh extraction yields a brand-new URL when the
        reused one was rejected by the CDN edge.  The fresh extraction
        happens at most once per call.
        """
        reused = (
            musicdata.video_data
            if isinstance(musicdata.video_data, dict)
            else None
        )
        reused_url = (
            cls._stream_url_from(reused) if reused is not None else None
        )
        if reused is not None and reused_url is not None:
            picked = await cls._probe_or_none(reused, reused_url)
            if picked is not None:
                return picked

        return await cls._probe_fresh_stream(musicdata)

    @classmethod
    async def _probe_fresh_stream(
        cls, musicdata: YTMusicData
    ) -> tuple[dict[str, Any], str]:
        """Extract a fresh stream for *musicdata*, validate and probe it.

        Raises via ``_reject_unplayable`` when the fresh URL is unusable
        or the probe cannot find a playable stream.
        """
        fresh = await cls._extract_fresh(musicdata.get_url())
        fresh_url = cls._select_stream_url(fresh)
        if not isinstance(fresh_url, str) or not fresh_url.startswith((
            "http://",
            "https://",
        )):
            cls._reject_unplayable(musicdata)
        picked = await cls._probe_or_none(fresh, fresh_url)
        if picked is None:
            cls._reject_unplayable(musicdata)
        return picked

    @staticmethod
    def _stream_url_from(info: dict[str, Any] | None) -> str | None:
        """Select a reused stream URL, or None to force a fresh extraction.

        Flat search entries carry no usable ``formats`` list, so a top-level
        URL is never trusted here; only real extracted formats are reused.
        """
        if not isinstance(info, dict):
            return None
        formats = info.get("formats")
        if not isinstance(formats, list) or not formats:
            return None
        return YoutubeDLSource._select_stream_url(info)

    @classmethod
    async def _extract_fresh(cls, url: str) -> dict[str, Any]:
        """Extract yt-dlp info with a timeout on the single ytdl worker."""
        loop = asyncio.get_running_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(
                ytmusic._YTDL_SERIAL_EXECUTOR, cls._extract_info, url
            ),
            timeout=ytmusic.YT_EXTRACT_TIMEOUT,
        )

    @staticmethod
    def _probe_failure_is_transient(exc: Exception) -> bool:
        """True when a failed probe may succeed on a fresh stream URL.

        Silence and a missing ffmpeg are properties of the track or the
        deployment, not of the connection, so they are never transient;
        everything else (rejected stream, unreadable stream, timeout) can
        be.
        """
        return not isinstance(
            exc,
            (
                stream_probe.ProbeSilenceError,
                stream_probe.ProbeEnvironmentError,
            ),
        )

    @staticmethod
    def _extract_info(url: str) -> dict[str, Any]:
        """Extract yt-dlp info for *url* and unwrap playlist/search entries to the first video."""
        data = ytmusic.ytdl.extract_info(url, download=False)
        if not isinstance(data, dict):
            raise ValueError("Invalid data from ytdl: expected dict")
        info: dict[str, Any] = dict(data)
        if "entries" in info:
            first = next(iter(info["entries"]), None)
            if not isinstance(first, dict):
                raise ValueError("Invalid data from ytdl: expected dict entry")
            info = dict(first)
        return info

    @classmethod
    def _select_stream_url(cls, data: dict[str, Any] | None) -> str | None:
        """Pick the best playable stream URL without any network access.

        Prefers audio-only formats, then ``m4a``, then the highest bitrate.
        Returns None when nothing usable is found.
        """
        if not isinstance(data, dict):
            return None
        formats = data.get("formats")
        if isinstance(formats, list) and formats:
            return cls._best_stream_url(formats)
        url = data.get("url")
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            return url
        return None

    @classmethod
    def _best_stream_url(cls, formats: list[Any]) -> str | None:
        candidates = [f for f in formats if cls._is_streamable_format(f)]
        if not candidates:
            return None
        best = min(candidates, key=cls._stream_score)
        url = best.get("url")
        return url if isinstance(url, str) else None

    @staticmethod
    def _is_streamable_format(f: Any) -> bool:
        """True if *f* is a dict with an http(s) URL carrying audio."""
        url = f.get("url") if isinstance(f, dict) else None
        return (
            isinstance(url, str)
            and url.startswith(("http://", "https://"))
            and YoutubeDLSource._is_usable_audio_format(f)
        )

    @staticmethod
    def _format_bitrate(f: dict[str, Any]) -> float:
        for key in ("abr", "tbr"):
            value = f.get(key)
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return 0.0

    @classmethod
    def _stream_score(cls, f: dict[str, Any]) -> tuple[int, int, float]:
        return (
            not cls._is_audio_only_format(f),
            f.get("ext") != "m4a",
            -cls._format_bitrate(f),
        )

    @staticmethod
    def _is_usable_audio_format(f: dict[str, Any]) -> bool:
        """True if *f* carries an audio stream (muxed or audio-only)."""
        acodec = f.get("acodec")
        return isinstance(acodec, str) and bool(acodec) and acodec != "none"

    @staticmethod
    def _is_audio_only_format(f: dict[str, Any]) -> bool:
        """True if *f* carries audio but no video."""
        acodec = f.get("acodec")
        vcodec = f.get("vcodec")
        return (
            isinstance(acodec, str)
            and bool(acodec)
            and acodec != "none"
            and (not vcodec or vcodec == "none")
        )
