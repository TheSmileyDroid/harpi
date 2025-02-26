"""O executável do bot."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Literal

import discord
import discord.ext
import discord.ext.commands
import discord.ext.commands as cd
from fastapi import (
    APIRouter,
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
)
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import src
import src.routers
import src.routers.guild
from src.cogs.ai import AiCog
from src.cogs.basic import BasicCog
from src.cogs.dice_cog import DiceCog
from src.cogs.music import MusicCog
from src.cogs.tts import TTSCog
from src.websocket import manager as websocketmanager
from dotenv import load_dotenv

load_dotenv()

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
    await client.add_cog(MusicCog(client))
    await client.add_cog(BasicCog())
    await client.add_cog(DiceCog(client))
    await client.add_cog(AiCog(client))

    task = asyncio.create_task(client.start(get_token()))

    background_tasks.add(task)

    task.add_done_callback(background_tasks.remove)

    return client


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    client = await main()
    app.state.bot = client
    yield
    client.close()  # type: ignore  # noqa: PGH003


app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:5173",
    "https://localhost:5173",
    "http://127.0.0.1:8000",
    "https://127.0.0.1:8000",
    "https://localhost:8000",
    "http://localhost:8000",
]
if os.getenv("DOMAIN"):
    origins.append(os.getenv("DOMAIN") or "")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


api_router = APIRouter(prefix="/api", tags=["api"])


class IStatus(BaseModel):
    """Estado atual do Bot."""

    status: Literal["online", "offline"]


@api_router.get("/status")
async def bot_status() -> IStatus:
    """Check the bot's status via a FastAPI endpoint.

    Returns
    -------
    IStatus
        Status.

    """
    bot: discord.ext.commands.Bot | None = app.state.bot
    return IStatus.model_validate({
        "status": "online" if bot and bot.is_ready() else "offline",
    })


app.include_router(
    src.routers.guild.router,
    prefix="/api/guilds",
    tags=["guilds"],
)

app.include_router(api_router)

if not (Path.cwd() / "frontend" / "dist").exists():
    Path.mkdir((Path.cwd() / "frontend" / "dist"), parents=True)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle the WebSocket connection for a client.

    This function manages the lifecycle of a WebSocket connection. It connects
    the client to the WebSocket manager, continuously listens for incoming
    messages, and ensures proper disconnection in case of an error or when the
    connection is closed.

    Args:
        websocket (WebSocket): The WebSocket connection instance.

    """
    await websocketmanager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, WebSocketException):
        websocketmanager.disconnect(websocket)


app.mount(
    "/",
    StaticFiles(directory="frontend/dist", html=True),
    name="static",
)
