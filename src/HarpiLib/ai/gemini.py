"""Gemini module"""

from __future__ import annotations

import datetime
import logging
import os
from typing import Callable

import google.generativeai as genai

from src.HarpiLib.ai.base import BaseAi

logger = logging.getLogger("Gemini")

logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)


class Gemini(BaseAi):
    def __init__(self) -> None:
        super().__init__()
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(
            "gemini-2.0-flash-exp",
            generation_config={"max_output_tokens": 4000},
            system_instruction=(
                "Você é Harpi, um bot de Discord. "
                "Criado pelo usuário SmileyDroid (Apelidado de Sorriso). "
                "Você está aqui para ajudar com qualquer coisa que te pedirem."
                "Seja gentil e animado. Extrapole bastante e divirta-se!"
                "Evite dar informações falsas, "
                "pesquise na internet antes de responder!"
                "Sempre use suas funções, elas são realmente uteis "
                "e podem te ajudar muito."
                "Sempre use a função de ver o histórico para saber o contexto da conversa."  # noqa: E501
            ),
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
            tools=(tools or []),
        )

        for part in response.parts:
            if fn := part.function_call:
                args = ", ".join(
                    f"{key}={val}" for key, val in fn.args.items()
                )
                print(f"Calling {fn.name}({args})")  # noqa: T201
                logger.info(f"Calling {fn.name}({args})")
        return response.text


if __name__ == "__main__":
    ai = Gemini()
    print(ai.get_response("Hello!"))  # noqa: T201
    print(ai.get_response("Which time is now? "))  # noqa: T201
