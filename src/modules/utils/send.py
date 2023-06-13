from discord.ext import commands


async def send_message(ctx: commands.Context, message: str):
    if len(message) > 1999:
        while len(message) > 1999:
            await ctx.send(message[:1999])
            message = message[1999:]
    await ctx.send(message)
