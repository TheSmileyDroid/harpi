import discord
from harpi import Harpi
import pytest_asyncio
import discord.ext.test as dpytest


@pytest_asyncio.fixture
async def bot():
    bot: Harpi = Harpi(command_prefix=Harpi.prefix,
                       intents=discord.Intents.all())
    await bot._async_setup_hook()

    dpytest.configure(bot)
    return bot
