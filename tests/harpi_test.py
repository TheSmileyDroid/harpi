import glob
import os
import discord
from harpi import Harpi
import pytest
import pytest_asyncio
import discord.ext.test as dpytest


@pytest_asyncio.fixture
async def bot():
    bot: Harpi = Harpi(command_prefix=Harpi.prefix,
                       intents=discord.Intents.all())
    await bot._async_setup_hook()
    await bot.load_extension('src.modules.tts')
    await bot.load_extension('src.modules.music')
    await bot.load_extension('src.modules.basic')
    dpytest.configure(bot)
    return bot


@pytest.mark.asyncio
async def test_ping(bot):
    await dpytest.message('-ping')
    assert dpytest.verify().message().content('Pong!')


@pytest.mark.asyncio
async def test_echo(bot):
    await dpytest.message('-echo test teste')
    assert dpytest.verify().message().content('test teste')


@pytest_asyncio.fixture(autouse=True)
async def cleanup():
    yield
    await dpytest.empty_queue()


def pytest_sessionfinish(session, exitstatus):
    """ Code to execute after all tests. """

    # dat files are created when using attachements
    print("\n-------------------------\nClean dpytest_*.dat files")
    fileList = glob.glob('./dpytest_*.dat')
    for filePath in fileList:
        try:
            os.remove(filePath)
        except Exception:
            print("Error while deleting file : ", filePath)
