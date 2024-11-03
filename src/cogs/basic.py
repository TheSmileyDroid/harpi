"""Basic COG."""

from discord.ext import commands


class BasicCog(commands.Cog):
    """Docstring for BasicCog."""

    @commands.command()
    async def ping(self, ctx: commands.Context) -> None:
        """Responde Ping de volta."""
        await ctx.send("Pong!")

    @commands.command()
    async def echo(self, ctx: commands.Context, *, args: str) -> None:
        """Repete a mensagem."""
        await ctx.send(args)

    @commands.command()
    async def shutdown(self, ctx: commands.Context) -> None:
        """Desliga o Harpi."""
        await ctx.send("Desligando...")
        await ctx.bot.close()
