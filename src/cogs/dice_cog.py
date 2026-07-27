"""RPG Dice Cog module."""

from typing import Dict, List

from discord import Message
from discord.ext.commands import Bot, Cog, command
from discord.ext.commands.context import Context
from loguru import logger

from src.harpi_lib.math.parser import DiceParser, RollResult


class DiceCog(Cog):
    """Cog for handling dice."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        if message.author == self.bot.user:
            return
        parser = DiceParser()
        if not parser.is_valid_dice_string(message.content):
            return
        response = parser.roll(message.content)
        await message.reply(response)

    @command(
        name="d", aliases=["dado", "rolar", "roll", "r", "math", "calc", "m"]
    )
    async def roll(self, ctx: Context, *, args: str) -> None:
        """Roll dice (e.g., 2d6 or 1d20+5)."""
        parser = DiceParser()
        response = parser.roll(args)
        await ctx.reply(response)

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
            await ctx.reply(f"Erro ao executar simulação: {str(e)}")

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

        # Top 5 most common results
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
