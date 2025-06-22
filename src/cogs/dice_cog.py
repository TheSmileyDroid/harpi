"""RPG Dice Cog module."""

from discord import Message
from discord.ext.commands import Bot, Cog, command
from discord.ext.commands.context import Context
from typing import Dict, List
import logging

from src.HarpiLib.math.parser import DiceParser


class DiceCog(Cog):
    """Cog for handling dice."""

    def __init__(self, bot: Bot) -> None:
        """Initialize the cog.

        Args:
            bot (discord.ext.commands.Bot): The bot.

        """
        self.bot = bot
        self.logger = logging.getLogger(__name__)

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        """Listen for messages and roll the dice."""
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
        """Comando para rolar dados.

        Args:
            ctx (Context)
            args (str): String com a quantidade e o tipo de dado a ser rolado
            (ex: 2d6 ou 1d20+5)

        """
        parser = DiceParser()
        response = parser.roll(args)
        await ctx.reply(response)

    @command(name="monte", aliases=["mc", "montecarlo", "simulation", "sim"])
    async def monte_carlo(
        self, ctx: Context, n: int, *, roll_expression: str
    ) -> None:
        """Executa uma simulação Monte Carlo com n iterações de uma expressão de dados.

        Args:
            ctx (Context): Contexto do comando
            n (int): Número de iterações para a simulação
            roll_expression (str): Expressão de dados para simular (ex: 2d6+3)

        """
        assert n > 0, "O número de iterações deve ser positivo"
        assert n <= 10000, "Número máximo de iterações é 10000"

        try:
            results = self._run_monte_carlo_simulation(n, roll_expression)
            response = self._format_monte_carlo_results(
                results, n, roll_expression
            )
            await ctx.reply(response)

        except Exception as e:
            self.logger.error(f"Erro na simulação Monte Carlo: {e}")
            await ctx.reply(f"Erro ao executar simulação: {str(e)}")

    def _run_monte_carlo_simulation(
        self, n: int, roll_expression: str
    ) -> List[int]:
        """Executa a simulação Monte Carlo.

        Args:
            n (int): Número de iterações
            roll_expression (str): Expressão de dados

        Returns:
            List[int]: Lista com os resultados de cada iteração

        """
        parser = DiceParser()
        results: List[int] = []

        for _ in range(n):
            result = parser.roll(roll_expression)
            # Assumindo que o parser retorna um valor numérico ou string com número
            if isinstance(result, str):
                # Extrai apenas o número do resultado se for string
                numeric_result = int(
                    "".join(filter(str.isdigit, result.split()[-1]))
                )
            else:
                numeric_result = int(result)
            results.append(numeric_result)

        return results

    def _format_monte_carlo_results(
        self, results: List[int], n: int, expression: str
    ) -> str:
        """Formata os resultados da simulação Monte Carlo.

        Args:
            results (List[int]): Resultados da simulação
            n (int): Número de iterações
            expression (str): Expressão original

        Returns:
            str: Mensagem formatada com os resultados

        """
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
        """Calcula estatísticas dos resultados.

        Args:
            results (List[int]): Lista de resultados

        Returns:
            Dict: Dicionário com as estatísticas calculadas

        """
        from collections import Counter
        import statistics

        mean = statistics.mean(results)
        median = statistics.median(results)
        std_dev = statistics.stdev(results) if len(results) > 1 else 0.0

        # Top 5 resultados mais comuns
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
