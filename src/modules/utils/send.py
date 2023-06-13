from discord.ext import commands


async def send_message(ctx: commands.Context, message: str | None = None, **kwargs):  # noqa: E501
    if message is not None:
        if len(message) > 1999:
            while len(message) > 1999:
                await ctx.send(message[:1999], **kwargs)
                message = message[1999:]
    await ctx.send(message, **kwargs)
