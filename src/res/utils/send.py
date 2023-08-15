import logging
from typing import Optional, List
from discord import Embed, Color
from discord.ext import commands


class Message:
    def __init__(self, ctx: commands.Context, content: Optional[str] = None):
        self.ctx = ctx
        self.content = content

    async def send(self, **kwargs):
        if self.content:
            # Split into chunks of 1999 characters long
            for chunk in self._chunks(self.content, 1999):
                await self.ctx.send(chunk, **kwargs)

    # SRP: A separate method to split the content into chunks
    @staticmethod
    def _chunks(content, size):
        # For item i in a range that is a length of content
        for i in range(0, len(content), size):
            # Create an index range for content of size
            yield content[i : i + size]


class EmbeddedMessage(Message):
    def __init__(self, ctx: commands.Context, embed: Embed):
        super().__init__(ctx)
        self.embed = embed

    async def send(self, **kwargs):
        # Check if embed exists
        if self.embed:
            if len(self.embed.fields) == 0:
                logging.warning("Embed has no fields")
                await super().send(**kwargs)
            # Split into chunks of 20 fields
            for chunk in self._chunks(self.embed.fields, 20):
                new_embed = Embed(
                    title=self.embed.title,
                    description=self.embed.description,
                    color=self.embed.color or Color.blue(),
                )
                if self.embed.footer:
                    new_embed.set_footer(
                        text=self.embed.footer.text,
                        icon_url=self.embed.footer.icon_url,
                    )
                for field in chunk:
                    new_embed.add_field(
                        name=field.name, value=field.value, inline=field.inline
                    )
                await self.ctx.send(embed=new_embed, **kwargs)
        else:
            logging.debug("Embed doesn't exist")
            await super().send(**kwargs)

    # OCP: The `_chunks` method from parent class has been overridden (extended) to support different objects
    @staticmethod
    def _chunks(content: List, size):
        # For item i in a range that is a length of content
        for i in range(0, len(content), size):
            # Create an index range for content of size
            yield content[i : i + size]
