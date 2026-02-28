import asyncio
from dataclasses import dataclass
from typing import cast

import discord
from discord import Embed, Member, VoiceChannel
from discord.ext.commands import Cog, Context, command

from src.harpi_lib.harpi_bot import HarpiBot
from src.harpi_lib.music.soundboard import SoundboardController
from src.harpi_lib.audio.test_tone_source import (
    MultiFrequencyTestSource,
    TestToneSource,
)


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    duration_ms: int = 0


class TestCog(Cog):
    def __init__(self, bot: HarpiBot) -> None:
        self.bot = bot
        self.api = bot.api

    async def _get_voice_context(
        self, ctx: Context
    ) -> tuple[discord.Guild, VoiceChannel, Member]:
        member = cast(Member, ctx.author)
        if not member.voice or not member.voice.channel:
            raise RuntimeError("You must be in a voice channel to run tests")
        voice_channel = member.voice.channel
        if not isinstance(voice_channel, VoiceChannel):
            raise RuntimeError("Invalid voice channel type")
        guild = ctx.guild
        if not guild:
            raise RuntimeError("This command must be used in a server")
        return guild, voice_channel, member

    @command("test_audio")
    async def test_audio(self, ctx: Context) -> None:
        """Run comprehensive audio tests on the bot."""
        results: list[TestResult] = []

        async with ctx.typing():
            try:
                guild, voice_channel, _ = await self._get_voice_context(ctx)
            except RuntimeError as e:
                await ctx.send(f"❌ {e}")
                return

            _ = await ctx.send("🔌 Connecting to voice channel...")
            try:
                guild_config = await self.api.connect_to_voice(
                    guild.id, voice_channel.id, ctx
                )
                results.append(
                    TestResult(
                        name="Voice Connection",
                        passed=True,
                        message=f"Connected to {voice_channel.name}",
                    )
                )
            except Exception as e:
                results.append(
                    TestResult(
                        name="Voice Connection",
                        passed=False,
                        message=str(e),
                    )
                )
                await self._send_results(ctx, results)
                return

            controller = guild_config.controller

            await asyncio.sleep(0.5)

            result = await self._test_layers(controller)
            results.append(result)

            await asyncio.sleep(0.5)

            result = await self._test_queue(controller)
            results.append(result)

            await asyncio.sleep(0.5)

            result = await self._test_tts(controller)
            results.append(result)

            await asyncio.sleep(0.5)

            result = await self._test_button_sounds(controller)
            results.append(result)

            await asyncio.sleep(0.5)

            result = await self._test_multiple_sources(controller)
            results.append(result)

            await asyncio.sleep(0.5)

            result = await self._test_cleanup(controller)
            results.append(result)

            try:
                await self.api.disconnect_voice(guild.id)
                results.append(
                    TestResult(
                        name="Disconnect",
                        passed=True,
                        message="Successfully disconnected",
                    )
                )
            except Exception as e:
                results.append(
                    TestResult(
                        name="Disconnect",
                        passed=False,
                        message=str(e),
                    )
                )

        await self._send_results(ctx, results)

    async def _test_layers(
        self, controller: SoundboardController
    ) -> TestResult:
        try:
            source = TestToneSource(
                frequency=440, duration_ms=500, name="Layer Test"
            )
            layer_id = controller.add_layer(source)

            if not layer_id or len(layer_id) == 0:
                return TestResult(
                    name="Layer Management",
                    passed=False,
                    message="add_layer did not return a valid ID",
                )

            sounds = controller.get_playing_sounds()
            layer_sounds = [s for t, s in sounds if t == "track"]

            if len(layer_sounds) != 1:
                return TestResult(
                    name="Layer Management",
                    passed=False,
                    message=f"Expected 1 layer, found {len(layer_sounds)}",
                )

            if layer_sounds[0] != source:
                return TestResult(
                    name="Layer Management",
                    passed=False,
                    message="Layer source mismatch",
                )

            controller.remove_layer(layer_id)
            sounds = controller.get_playing_sounds()
            layer_sounds = [s for t, s in sounds if t == "track"]

            if len(layer_sounds) != 0:
                return TestResult(
                    name="Layer Management",
                    passed=False,
                    message="Layer was not removed",
                )

            return TestResult(
                name="Layer Management",
                passed=True,
                message="Add/remove layers working correctly",
            )
        except Exception as e:
            return TestResult(
                name="Layer Management",
                passed=False,
                message=f"Exception: {e}",
            )

    async def _test_queue(
        self, controller: SoundboardController
    ) -> TestResult:
        try:
            source1 = TestToneSource(
                frequency=523, duration_ms=300, name="Queue Test 1"
            )
            source2 = TestToneSource(
                frequency=659, duration_ms=300, name="Queue Test 2"
            )

            controller.add_to_queue(source1)
            controller.add_to_queue(source2)

            sounds = controller.get_playing_sounds()
            queue_sounds = [s for t, s in sounds if t == "queue"]

            if len(queue_sounds) != 1:
                return TestResult(
                    name="Queue Management",
                    passed=False,
                    message=f"Expected 1 playing queue item, found {len(queue_sounds)}",
                )

            controller._on_track_finished(source1)
            sounds = controller.get_playing_sounds()
            queue_sounds = [s for t, s in sounds if t == "queue"]

            if len(queue_sounds) != 1 or queue_sounds[0] != source2:
                return TestResult(
                    name="Queue Management",
                    passed=False,
                    message="Queue did not advance to next track",
                )

            controller.clear_queue()
            sounds = controller.get_playing_sounds()
            queue_sounds = [s for t, s in sounds if t == "queue"]

            if len(queue_sounds) != 0:
                return TestResult(
                    name="Queue Management",
                    passed=False,
                    message="Queue was not cleared",
                )

            return TestResult(
                name="Queue Management",
                passed=True,
                message="Queue add/advance/clear working correctly",
            )
        except Exception as e:
            return TestResult(
                name="Queue Management",
                passed=False,
                message=f"Exception: {e}",
            )

    async def _test_tts(self, controller: SoundboardController) -> TestResult:
        try:
            source = TestToneSource(
                frequency=330, duration_ms=400, name="TTS Test"
            )

            controller.set_tts_track(source)

            sounds = controller.get_playing_sounds()
            tts_sounds = [s for t, s in sounds if t == "tts"]

            if len(tts_sounds) != 1:
                return TestResult(
                    name="TTS Track",
                    passed=False,
                    message=f"Expected 1 TTS track, found {len(tts_sounds)}",
                )

            if tts_sounds[0] != source:
                return TestResult(
                    name="TTS Track",
                    passed=False,
                    message="TTS source mismatch",
                )

            controller.set_tts_track(None)
            sounds = controller.get_playing_sounds()
            tts_sounds = [s for t, s in sounds if t == "tts"]

            if len(tts_sounds) != 0:
                return TestResult(
                    name="TTS Track",
                    passed=False,
                    message="TTS track was not cleared",
                )

            return TestResult(
                name="TTS Track",
                passed=True,
                message="TTS set/clear working correctly",
            )
        except Exception as e:
            return TestResult(
                name="TTS Track",
                passed=False,
                message=f"Exception: {e}",
            )

    async def _test_button_sounds(
        self, controller: SoundboardController
    ) -> TestResult:
        try:
            source = TestToneSource(
                frequency=880, duration_ms=300, name="Button Test"
            )

            button_id = controller.add_button_sound(source)

            if not button_id or len(button_id) == 0:
                return TestResult(
                    name="Button Sounds",
                    passed=False,
                    message="add_button_sound did not return a valid ID",
                )

            sounds = controller.get_playing_sounds()
            button_sounds = [s for t, s in sounds if t == "button"]

            if len(button_sounds) != 1:
                return TestResult(
                    name="Button Sounds",
                    passed=False,
                    message=f"Expected 1 button sound, found {len(button_sounds)}",
                )

            controller.remove_button_sound(button_id)
            sounds = controller.get_playing_sounds()
            button_sounds = [s for t, s in sounds if t == "button"]

            if len(button_sounds) != 0:
                return TestResult(
                    name="Button Sounds",
                    passed=False,
                    message="Button sound was not removed",
                )

            return TestResult(
                name="Button Sounds",
                passed=True,
                message="Button sound add/remove working correctly",
            )
        except Exception as e:
            return TestResult(
                name="Button Sounds",
                passed=False,
                message=f"Exception: {e}",
            )

    async def _test_multiple_sources(
        self, controller: SoundboardController
    ) -> TestResult:
        try:
            layer_source = TestToneSource(
                frequency=440, duration_ms=500, name="Multi Layer"
            )
            queue_source = TestToneSource(
                frequency=523, duration_ms=500, name="Multi Queue"
            )
            tts_source = TestToneSource(
                frequency=659, duration_ms=500, name="Multi TTS"
            )
            button_source = TestToneSource(
                frequency=784, duration_ms=500, name="Multi Button"
            )

            layer_id = controller.add_layer(layer_source)
            controller.add_to_queue(queue_source)
            controller.set_tts_track(tts_source)
            button_id = controller.add_button_sound(button_source)

            sounds = controller.get_playing_sounds()
            types_found = {t for t, _ in sounds}

            expected_types = {"track", "queue", "tts", "button"}
            if types_found != expected_types:
                return TestResult(
                    name="Multiple Sources",
                    passed=False,
                    message=f"Expected {expected_types}, found {types_found}",
                )

            controller.remove_layer(layer_id)
            controller.clear_queue()
            controller.set_tts_track(None)
            controller.remove_button_sound(button_id)

            sounds = controller.get_playing_sounds()
            if len(sounds) != 0:
                return TestResult(
                    name="Multiple Sources",
                    passed=False,
                    message=f"Expected 0 sounds after cleanup, found {len(sounds)}",
                )

            return TestResult(
                name="Multiple Sources",
                passed=True,
                message="All 4 source types play simultaneously",
            )
        except Exception as e:
            return TestResult(
                name="Multiple Sources",
                passed=False,
                message=f"Exception: {e}",
            )

    async def _test_cleanup(
        self, controller: SoundboardController
    ) -> TestResult:
        try:
            for freq in [261, 329, 392]:
                source = TestToneSource(
                    frequency=freq,
                    duration_ms=500,
                    name=f"Cleanup Test {freq}",
                )
                controller.add_layer(source)

            for freq in [523, 659]:
                source = TestToneSource(
                    frequency=freq,
                    duration_ms=500,
                    name=f"Cleanup Queue {freq}",
                )
                controller.add_to_queue(source)

            controller.set_tts_track(
                TestToneSource(
                    frequency=784, duration_ms=500, name="Cleanup TTS"
                )
            )

            controller.add_button_sound(
                TestToneSource(
                    frequency=880, duration_ms=500, name="Cleanup Button"
                )
            )

            sounds = controller.get_playing_sounds()
            if len(sounds) < 4:
                return TestResult(
                    name="Cleanup All",
                    passed=False,
                    message=f"Expected at least 4 sources before cleanup, found {len(sounds)}",
                )

            controller.cleanup_all()

            sounds = controller.get_playing_sounds()
            if len(sounds) != 0:
                return TestResult(
                    name="Cleanup All",
                    passed=False,
                    message=f"Expected 0 sources after cleanup, found {len(sounds)}",
                )

            return TestResult(
                name="Cleanup All",
                passed=True,
                message="All sources cleaned up successfully",
            )
        except Exception as e:
            return TestResult(
                name="Cleanup All",
                passed=False,
                message=f"Exception: {e}",
            )

    async def _send_results(
        self, ctx: Context, results: list[TestResult]
    ) -> None:
        passed = sum(1 for r in results if r.passed)
        total = len(results)

        embed = Embed(
            title="🧪 Audio Test Results",
            description=f"**{passed}/{total} tests passed**",
            color=0x00FF00 if passed == total else 0xFFAA00,
        )

        for result in results:
            status = "✅" if result.passed else "❌"
            embed.add_field(
                name=f"{status} {result.name}",
                value=result.message,
                inline=False,
            )

        await ctx.send(embed=embed)


async def setup(bot: HarpiBot) -> None:
    await bot.add_cog(TestCog(bot))
