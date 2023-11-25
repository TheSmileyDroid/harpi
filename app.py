import logging
import os
from time import sleep

import discord
from src.bot.harpi import Harpi
from src.bot.iharpi import IHarpi
import src.res  # noqa: F401

from flask import Flask, request
from threading import Thread

from src.robsons.hub import bp as hub_bp

terminalLogger = logging.StreamHandler()
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
    style="%",
    filename="discord.log",
)
logging.getLogger().addHandler(terminalLogger)


def run_bot(bot: IHarpi) -> None:
    token: str = str(os.getenv("DISCORD_ID"))
    bot.run(token, log_level=logging.FATAL)


def create_bot() -> Harpi:
    intents = discord.Intents.all()
    bot = Harpi(command_prefix=Harpi.prefix, intents=intents)
    return bot


app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["TESTING"] = True


app.register_blueprint(hub_bp)


@app.context_processor
def context_processor():
    def base_url():
        return request.base_url

    return dict(base_url=base_url)


def run_flask():
    app.run(debug=True, port=5000)


if __name__ == "__main__":
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    sleep(1)
    # run_bot(bot=create_bot())
