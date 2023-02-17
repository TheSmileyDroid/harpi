import random
from discord.ext import commands


class Dice(commands.Cog):

    @commands.command(name='d', aliases=['dado', 'rolar', 'roll', 'r'])
    async def roll(self, ctx, *, dice: str):
        try:
            rolls, limit = map(int, dice.split('d'))
        except Exception:
            return await ctx.send('Formato inválido')
        if rolls > 100:
            return await ctx.send('Máximo de 100 dados')
        if limit > 400:
            return await ctx.send('Máximo de 400 lados')
        result: list = [random.randint(1, limit) for _ in range(rolls)]
        text = ', '.join(map(str, result))
        text += f' = **{sum(result)}**'
        await ctx.send(text)


async def setup(bot):
    await bot.add_cog(Dice(bot))
