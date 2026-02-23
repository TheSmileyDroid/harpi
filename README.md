# Harpi

This is a discord bot made mainly for replacing other bots
in a simplier way with features like:

- Music Player
- Dice Roller
- TTS using external voice

## Running

To run Harpi at local environment you will need to install the
dependencies from the pyproject into your virtual environment.
To do that I recommend you to use the `uv` package manager.

After installing some package manager and installing the dependencies.
You can run the `./run.sh` file in the root to startup the backend of the
bot and run the `./ui/run.sh` to start the svelte frontend. You will need
bun if you and to start the frontend.

To run at prod, or if you have a better understanding of Docker
files, you can start the docker compose file from the root to start
both backend and frontend containers with everything configured.


