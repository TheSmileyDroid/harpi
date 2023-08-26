from src.res.utils.lolapi import LolApi
from discord.ext import commands


class Lol(commands.Cog):
    @commands.command()
    async def champion(self, ctx, champion_name):
        api = LolApi()

        champion = api.get_champion_by_name(champion_name)

        await ctx.send(f'{champion["name"]} - {champion["title"]}')

    @commands.command()
    async def item(self, ctx, item_name):
        api = LolApi()

        item = api.get_item_by_name(item_name)

        await ctx.send(f'{item["name"]} - {item["plaintext"]}')

    @commands.command()
    async def random_champion(self, ctx):
        api = LolApi()

        champion = api.random_champion()

        await ctx.send(f'{champion["name"]} - {champion["title"]}')

    @commands.command()
    async def random_item(self, ctx):
        api = LolApi()

        item = api.random_item()

        await ctx.send(f'{item["name"]} - {item["plaintext"]}')

    @commands.command()
    async def random_champion_build(self, ctx):
        api = LolApi()

        build = api.random_champion_build()

        await ctx.send(f'{build["champion"]["name"]} - {build["champion"]["title"]}' + \
            f'\n{build["item1"]["name"]}' + \
            f'\n{build["item2"]["name"]}' + \
            f'\n{build["item3"]["name"]}' + \
            f'\n{build["item4"]["name"]}' + \
            f'\n{build["item5"]["name"]}' + \
            f'\n{build["item6"]["name"]}')

