from discord.ext import commands
from discord import Color, Colour, Embed


async def send_message(ctx: commands.Context, message: str | None = None, **kwargs):  # noqa: E501
    if message is not None:
        if len(message) > 1999:
            while len(message) > 1999:
                await ctx.send(message[:1999], **kwargs)
                message = message[1999:]
            await ctx.send(message, **kwargs)
            return
    if 'embed' in kwargs:
        embed = kwargs['embed']
        if isinstance(embed, Embed):
            if len(embed.fields) > 20:
                while len(embed.fields) > 20:
                    color: Colour | None = embed.colour
                    if color is None:
                        color = Color.blue()
                    newembed = Embed(
                        title=embed.title,
                        description=embed.description,
                        color=color)
                    for field in embed.fields[:20]:
                        newembed.add_field(
                            name=field.name,
                            value=field.value,
                            inline=field.inline)
                    newembed.set_footer(text=embed.footer.text)
                    await ctx.send(embed=newembed)
                    for _ in range(20):
                        embed.remove_field(0)
                await ctx.send(embed=embed)
                return
    await ctx.send(**kwargs)
