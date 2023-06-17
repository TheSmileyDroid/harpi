from discord.ext import commands


class Basic(commands.Cog):

    @commands.command()
    async def ping(self, ctx: commands.Context):
        await ctx.send('Pong!')

    @commands.command()
    async def echo(self, ctx: commands.Context, *, args: str):
        await ctx.send(args)


async def setup(bot):
    await bot.add_cog(Basic(bot))
