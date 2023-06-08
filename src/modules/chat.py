from discord.ext import commands
from src.modules.utils.aichat import AIChat
from src.modules.utils.guild import guild_data


class Chat(commands.Cog):

    @commands.command()
    async def chat(self, ctx: commands.Context, *, message: str):
        """Converse com o bot."""
        chat: AIChat = guild_data.chat(ctx)
        response = chat.chat(ctx, message)
        await ctx.send(response)

    @commands.command()
    async def clearchat(self, ctx: commands.Context):
        """Limpe o chat."""
        chat: AIChat = guild_data.chat(ctx)
        chat.clear()
        await ctx.send('Chat limpo!')


async def setup(bot):
    await bot.add_cog(Chat(bot))
