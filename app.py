"""O executável do bot."""

from __future__ import annotations

import asyncio
import logging
import os

import discord
import discord.ext
import discord.ext.commands
import discord.ext.commands as cd
from fastapi import APIRouter, FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import src
import src.routers
import src.routers.guild
import src.routers.music
from src.cogs.basic import BasicCog
from src.cogs.dice_cog import DiceCog
from src.cogs.music import MusicCog
from src.cogs.tts import TTSCog

terminal_logger = logging.StreamHandler()
# noinspection SpellCheckingInspection
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
    style="%",
    filename="discord.log",
)
logging.getLogger().addHandler(terminal_logger)

background_tasks = set()


def get_token() -> str:
    """Obtém o token do bot.

    Raises:
        ValueError: Se o token não estiver definido.

    Returns:
        str: O token do bot.

    """
    token = os.getenv("DISCORD_TOKEN")

    if token:
        return token

    raise ValueError


async def main() -> cd.Bot:
    """Start the bot.

    Returns
    -------
    cd.Bot
        Bot instance

    """
    intents = discord.Intents.all()

    client = cd.Bot(command_prefix="-", intents=intents)

    await client.add_cog(TTSCog())
    await client.add_cog(MusicCog())
    await client.add_cog(BasicCog())
    await client.add_cog(DiceCog(client))

    task = asyncio.create_task(client.start(get_token()))

    background_tasks.add(task)

    task.add_done_callback(background_tasks.remove)

    return client


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201, D103
    client = await main()
    app.state.bot = client
    yield
    client.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api", tags=["api"])


@api_router.get("/status")
async def bot_status() -> dict[str, str]:
    """Check the bot's status via a FastAPI endpoint.

    Returns
    -------
    dict[str, str]
        Status.

    """
    bot: discord.ext.commands.Bot | None = app.state.bot
    return {"status": "online" if bot.is_ready() else "offline"}


api_router.include_router(src.routers.music.router)
api_router.include_router(src.routers.guild.router)

app.include_router(api_router)

app.mount(
    "/",
    StaticFiles(directory="frontend/build", html=True),
    name="static",
)
