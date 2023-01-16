from discord.ext import commands


class Basic(commands.Cog):

    @commands.command()
    async def ping(self, ctx: commands.Context):
        await ctx.send('Pong!')

    @commands.command()
    async def echo(self, ctx: commands.Context, *, message: str):
        await ctx.send(message)


async def setup(bot):
    await bot.add_cog(Basic(bot))
