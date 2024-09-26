from discord.ext import commands


class BasicCog(commands.Cog):
    @commands.command()
    async def ping(self, ctx: commands.Context):
        await ctx.send("Pong!")

    @commands.command()
    async def echo(self, ctx: commands.Context, *, args: str):
        await ctx.send(args)

    @commands.command()
    async def shutdown(self, ctx: commands.Context):
        await ctx.send("Desligando...")
        await ctx.bot.close()
