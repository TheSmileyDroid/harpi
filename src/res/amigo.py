import random
from discord.ext import commands

amigos = {
    "nickguita": "Nicolas",
    "ReiNato": "Renato",
    "smileydroid": "Sorriso",
    "peppog_ay": "Café",
    "lucas.gl": "Lucas",
    "kamilalinda": "Cap",
    "kasemiro": "Gukase",
    "mrparanoico66": "Cadu",
    "arcadia1689": "Arcádia",
    "xorupinguento": "Eike",
    "notoryetz": "Rafa",
}


def check_if_is_me(ctx: commands.Context):
    return ctx.author.id == 439894995890208768


def check_if_is_member(ctx: commands.Context):
    return ctx.author.name in amigos.keys()


class AmigoCog(commands.Cog):
    @commands.command()
    @commands.dm_only()
    @commands.check(check_if_is_member)
    async def amigo(self, ctx: commands.Context):
        random.seed("manda desce")
        shuffled_list = [x for x in amigos.keys()]
        shuffled_list.sort()
        random.shuffle(shuffled_list)
        user = ctx.author.name
        index = shuffled_list.index(user)
        await ctx.send(f"Amigo: {amigos[shuffled_list[index+1]]}")

    @commands.command()
    @commands.check(check_if_is_member)
    async def lista_de_amigos(self, ctx: commands.Context):
        await ctx.send("Lista de amigos: " + ", ".join(amigos.values()))

    @commands.command()
    @commands.check(check_if_is_me)
    async def lista_de_amigos_secreta(self, ctx: commands.Context):
        random.seed("amigo2022")
        shuffled_list = [x for x in amigos.keys()]
        shuffled_list.sort()
        random.shuffle(shuffled_list)
        await ctx.send(
            f"Lista de amigos: {', '.join([amigos[x] for x in shuffled_list])}"
        )
