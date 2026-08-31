from __future__ import annotations

import argparse
import sys

import uvicorn
from dotenv import load_dotenv
from loguru import logger

from src.config import Settings


def parse_args(settings: Settings) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Harpi Discord Bot")
    parser.add_argument(
        "--host",
        default=settings.host,
        help="Host to bind to (default: 0.0.0.0 or HOST env var)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.port,
        help="Port to bind to (default: 8000 or PORT env var)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=settings.reload,
        help="Enable auto-reload (default: RELOAD env var or false)",
    )
    return parser.parse_args()


def setup_logging() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO")
    logger.add("spam.log", level="DEBUG")


def main() -> None:
    # Load .env first
    if not load_dotenv():
        logger.warning(".env file not found or empty")

    setup_logging()

    settings = Settings.from_env()
    args = parse_args(settings)

    logger.info(
        f"Starting Harpi on {args.host}:{args.port} (reload={args.reload})"
    )

    uvicorn.run(
        "app:asgi_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
