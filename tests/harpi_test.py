import discord
from src.harpi import Harpi
import pytest
from src.modules.basic import Basic
from discord.ext.commands import Context


@pytest.fixture
def bot() -> Harpi:
    bot: Harpi = Harpi(command_prefix=Harpi.prefix,
                       intents=discord.Intents.all())
    return bot


@pytest.mark.asyncio
async def test_ping(bot: Harpi):
    cog: Basic = Basic(bot)
    fake_ctx: Context = Context()
    message = await cog.ping.invoke(fake_ctx)
