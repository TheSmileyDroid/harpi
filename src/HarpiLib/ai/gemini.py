"""Gemini module"""

from __future__ import annotations

import datetime
import logging
import os
from typing import Callable

import google.generativeai as genai

from src.HarpiLib.ai.base import BaseAi


class Gemini(BaseAi):
    def __init__(self) -> None:
        super().__init__()
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(
            "gemini-2.0-flash-exp",
            generation_config={"max_output_tokens": 4000},
            system_instruction="Você é Harpi, um bot de Discord",
        )
        self.chat = self.model.start_chat(
            enable_automatic_function_calling=True,
        )
        self.chat_starting_time = datetime.datetime.now(
            tz=datetime.timezone(datetime.timedelta(hours=-3)),
        )

    def reset_chat(self) -> None:
        """Reset chat session."""
        self.chat = self.model.start_chat(
            enable_automatic_function_calling=True,
        )
        self.chat_starting_time = datetime.datetime.now(
            tz=datetime.timezone(datetime.timedelta(hours=-3)),
        )

    def get_response(
        self,
        message: str,
        tools: list[Callable] | None = None,
    ) -> str:
        """Get response from Gemini AI.

        Parameters
        ----------
        message : str
            User message.

        Returns
        -------
        str
            AI response.

        """

        response = self.chat.send_message(
            message,
            tools=[current_time] + (tools or []),
        )

        for part in response.parts:
            if fn := part.function_call:
                args = ", ".join(
                    f"{key}={val}" for key, val in fn.args.items()
                )
                logging.getLogger("Gemini").info(f"{fn.name}({args})")
        return response.text


def current_time() -> str:
    """Get current time in string format.

    Returns
    -------
    str
        Current time in string format.
    """
    current = datetime.datetime.now(
        tz=datetime.timezone(datetime.timedelta(hours=-3)),
    )
    return current.strftime("%d/%m/%Y %H:%M:%S")


if __name__ == "__main__":
    ai = Gemini()
    print(ai.get_response("Hello!"))  # noqa: T201
    print(ai.get_response("Which time is now? "))  # noqa: T201
