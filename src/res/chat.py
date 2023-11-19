from discord.ext import commands

from src.res.utils.send import Message

from .utils.aichat import AIChat
from .utils.guild import guild_data


class ChatCog(commands.Cog):
    @commands.command()
    async def chat(self, ctx: commands.Context, *, args: str):
        """Converse com o bot."""
        async with ctx.typing():
            chat: AIChat = guild_data.chat(ctx)
            response = await chat.get_response(args, ctx)
            if response == "":
                response = "Não sei o que responder!"
            await ctx.send(response)

    @commands.command()
    async def clearchat(self, ctx: commands.Context):
        """Limpe o chat."""
        chat: AIChat = guild_data.chat(ctx)
        chat.clear()
        await ctx.send("Chat limpo!")

    @commands.command()
    async def settemp(self, ctx: commands.Context, temp: float):
        """Defina a temperatura do chat."""
        chat: AIChat = guild_data.chat(ctx)
        chat.set_temp(temp)
        await ctx.send(f"Temperatura definida para {temp}!")

    @commands.command()
    async def settopp(self, ctx: commands.Context, top_p: float):
        """Defina o top_p do chat."""
        chat: AIChat = guild_data.chat(ctx)
        chat.set_top_p(top_p)
        await ctx.send(f"Top_p definido para {top_p}!")

    @commands.command()
    async def gettemp(self, ctx: commands.Context):
        """Obtenha a temperatura do chat."""
        chat: AIChat = guild_data.chat(ctx)
        temp = chat.get_temp()
        await ctx.send(f"Temperatura atual: {temp}!")

    @commands.command()
    async def gettopp(self, ctx: commands.Context):
        """Obtenha o top_p do chat."""
        chat: AIChat = guild_data.chat(ctx)
        top_p = chat.get_top_p()
        await ctx.send(f"Top_p atual: {top_p}!")

    @commands.command()
    async def getmem(self, ctx: commands.Context):
        """Obtenha a memória do chat."""
        chat: AIChat = guild_data.chat(ctx)
        mem = chat.chat_mem
        await Message(ctx, f"Memória atual: {mem}!").send()


async def setup(bot):
    await bot.add_cog(ChatCog(bot))
