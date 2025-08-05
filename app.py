"""O executável do bot."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import cast

import discord
import discord.ext
import discord.ext.commands
import discord.ext.commands as cd
from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
)
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer

import src
import src.routers
import src.routers.cogs
import src.routers.guild
import src.routers.system
from models.status import IStatus
from src.cogs.ai import AiCog
from src.cogs.basic import BasicCog
from src.cogs.dice_cog import DiceCog
from src.cogs.music import MusicCog
from src.cogs.tts import TTSCog
from src.services.cog_manager import cog_manager
from src.websocket import manager as websocketmanager

_ = load_dotenv()

terminal_logger = logging.StreamHandler()
# noinspection SpellCheckingInspection
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
    style="%",
    filename="discord.log",
)
logging.getLogger().addHandler(terminal_logger)

background_tasks: set[asyncio.Task[None]] = set()


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

    # Available cog classes mapped by name
    available_cogs = {
        "TTSCog": TTSCog,
        "MusicCog": lambda: MusicCog(client),
        "BasicCog": BasicCog,
        "DiceCog": lambda: DiceCog(client),
        "AiCog": lambda: AiCog(client),
    }

    # Load cogs based on configuration
    for cog_name, cog_class in available_cogs.items():
        if cog_manager.is_cog_enabled(cog_name):
            try:
                # Create cog instance
                if callable(cog_class) and not isinstance(cog_class, type):
                    # Lambda function - call it to get instance
                    cog_instance = cog_class()
                else:
                    # Regular class - instantiate it
                    cog_instance = cog_class()
                
                await client.add_cog(cog_instance)
                
                # Update cog information in configuration
                cog_manager.update_cog_info(cog_name, cog_instance)
                
                logging.getLogger(__name__).info(f"Loaded cog: {cog_name}")
            except Exception as e:
                logging.getLogger(__name__).error(f"Failed to load cog {cog_name}: {e}")

    task = asyncio.create_task(client.start(get_token()))

    background_tasks.add(task)

    task.add_done_callback(background_tasks.remove)

    return client


@asynccontextmanager
async def lifespan(_app: FastAPI):  # noqa: ANN201
    client = await main()
    _app.state.bot = client  # type: ignore  # noqa: PGH003
    yield
    await client.close()  # type: ignore  # noqa: PGH003


app = FastAPI(lifespan=lifespan)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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


@api_router.get("/status")
async def bot_status() -> IStatus:
    """Check the bot's status via a FastAPI endpoint.

    Returns
    -------
    IStatus
        Status.

    """
    bot = cast(discord.ext.commands.Bot | None, app.state.bot)
    return IStatus.model_validate(
        {
            "status": "online" if bot and bot.is_ready() else "offline",
        }
    )


app.include_router(
    src.routers.guild.router,
    prefix="/api/guilds",
    tags=["guilds"],
)

app.include_router(
    src.routers.system.router,
    prefix="/api/system",
    tags=["system"],
)

app.include_router(
    src.routers.cogs.router,
    prefix="/api/cogs",
    tags=["cogs"],
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
            message = await websocket.receive_text()
            # Processar as mensagens recebidas usando o manipulador de mensagens
            await websocketmanager.handle_message(websocket, message)
    except (WebSocketDisconnect, WebSocketException):
        websocketmanager.disconnect(websocket)


@app.get("/{path:path}")
def serve_static(path: str) -> FileResponse:
    """
    Use index.html for all requests without an existing file.
    """
    print(f"Request for path: {path}")
    if path and (Path("frontend/dist") / path).exists():
        return FileResponse(Path("frontend/dist") / path)
    return FileResponse(path=Path("frontend/dist") / "index.html")
