from collections.abc import Awaitable, Callable
from typing import Any, Dict, List

from discord import Message
from discord.ext.commands import Bot, Cog, command
from discord.ext.commands.context import Context
from loguru import logger

from src.bot_state import run_on_panel_loop
from src.harpi_lib.math.parser import DiceParser, RollResult
from src.panel import rolls

NO_TABLE_ACCESS = "Você não tem acesso a esta mesa."


class DiceCog(Cog):
    """Cog for handling dice."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        if getattr(message.author, "bot", False):
            return
        if getattr(message, "webhook_id", None):
            return
        if message.author == self.bot.user:
            return
        parser = DiceParser()
        if not parser.is_valid_dice_string(message.content):
            return
        mirrored = await self._mirror(message, message.content)
        if await self._answer(message.reply, mirrored):
            return
        response = parser.roll(message.content)
        await message.reply(response)

    @command(
        name="d", aliases=["dado", "rolar", "roll", "r", "math", "calc", "m"]
    )
    async def roll(self, ctx: Context, *, args: str) -> None:
        """Roll dice (e.g., 2d6 or 1d20+5)."""
        mirrored = await self._mirror(getattr(ctx, "message", None), args)
        if await self._answer(ctx.reply, mirrored):
            return
        parser = DiceParser()
        response = parser.roll(args)
        await ctx.reply(response)

    async def _answer(
        self,
        reply: Callable[[str], Awaitable[Any]],
        mirrored: rolls.ChannelRoll | None,
    ) -> bool:
        if mirrored is None:
            return False
        if mirrored.text is not None:
            await reply(mirrored.text)
        elif mirrored.refused:
            await reply(NO_TABLE_ACCESS)
        return True

    async def _mirror(
        self, message: Message | None, expression: str
    ) -> rolls.ChannelRoll | None:
        if message is None:
            return None
        guild = getattr(message, "guild", None)
        if guild is None:
            return None
        author = message.author
        label = getattr(author, "display_name", None) or author.name
        try:
            return await run_on_panel_loop(
                rolls.channel_roll(
                    channel_id=str(message.channel.id),
                    guild_id=str(guild.id),
                    author_id=str(author.id),
                    author_label=str(label),
                    message_id=str(message.id),
                    expression=expression,
                )
            )
        except Exception:
            return None

    @command(name="monte", aliases=["montecarlo", "simulation"])
    async def monte_carlo(
        self, ctx: Context, n: int, *, roll_expression: str
    ) -> None:
        """Run n iterations of a dice expression and return statistics."""
        assert n > 0, "O número de iterações deve ser positivo"
        assert n <= 10000, "Número máximo de iterações é 10000"

        try:
            results = self._run_monte_carlo_simulation(n, roll_expression)
            response = self._format_monte_carlo_results(
                results, n, roll_expression
            )
            await ctx.reply(response)

        except Exception as e:
            logger.opt(exception=True).error(
                f"Erro na simulação Monte Carlo: {e}"
            )
            await ctx.reply(f"Erro ao executar simulação: {e!s}")

    def _run_monte_carlo_simulation(
        self, n: int, roll_expression: str
    ) -> List[int]:

        results: List[int] = []

        for _ in range(n):
            parser = DiceParser()
            result: RollResult = parser.parse(roll_expression)
            results.append(result.value)

        return results

    def _format_monte_carlo_results(
        self, results: List[int], n: int, expression: str
    ) -> str:
        """Format the Monte Carlo simulation results."""
        stats = self._calculate_statistics(results)

        response_lines = [
            f"🎲 **Simulação Monte Carlo** - {expression}",
            f"📊 **Iterações:** {n:,}",
            f"📈 **Média:** {stats['mean']:.2f}",
            f"📉 **Mediana:** {stats['median']:.2f}",
            f"⬆️ **Máximo:** {stats['max']}",
            f"⬇️ **Mínimo:** {stats['min']}",
            f"📏 **Desvio Padrão:** {stats['std_dev']:.2f}",
            "",
            "**Distribuição dos resultados mais frequentes:**",
        ]

        if isinstance(stats["top_results"], list):
            for value, count in stats["top_results"]:
                percentage = (count / n) * 100
                response_lines.append(
                    f"`{value}`: {count:,} vezes ({percentage:.1f}%)"
                )

        return "\n".join(response_lines)

    def _calculate_statistics(
        self, results: List[int]
    ) -> Dict[str, float | int | List[tuple]]:
        import statistics
        from collections import Counter

        mean = statistics.mean(results)
        median = statistics.median(results)
        std_dev = statistics.stdev(results) if len(results) > 1 else 0.0

        counter = Counter(results)
        top_results = counter.most_common(5)

        return {
            "mean": mean,
            "median": median,
            "max": max(results),
            "min": min(results),
            "std_dev": std_dev,
            "top_results": top_results,
        }
