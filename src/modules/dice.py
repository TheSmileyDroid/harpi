import random
from discord.ext import commands


class Dice(commands.Cog):

    @commands.command()
    async def roll(self, ctx: commands.Context, *, dice: str):
        number, sides = dice.split('d')
        number = int(number)
        sides = int(sides)
        if number > 100:
            await ctx.send('Você não pode rolar mais de 100 dados')
            return
        if sides > 100:
            await ctx.send('Você não pode rolar dados com mais de 100 lados')
            return
        if number < 1:
            await ctx.send('Você não pode rolar menos de 1 dado')
            return
        if sides < 1:
            await ctx.send('Você não pode rolar dados com menos de 1 lado')
            return
        rolls = [str(random.randint(1, sides)) for _ in range(number)]
        await ctx.send(', '.join(rolls))


async def setup(bot):
    await bot.add_cog(Dice(bot))
