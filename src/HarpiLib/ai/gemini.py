"""Gemini module"""

from __future__ import annotations

import datetime
import logging
import os
from typing import TYPE_CHECKING

import discord
import discord.ext
import discord.ext.commands
import google.generativeai as genai
from google.protobuf.struct_pb2 import Struct

from src.HarpiLib.ai.base import BaseAi

if TYPE_CHECKING:
    from google.generativeai.types.content_types import (
        ContentsType,
    )
    from google.generativeai.types.generation_types import (
        GenerateContentResponse,
    )

    from src.HarpiLib.ai.tools import AiTools

logger = logging.getLogger("Gemini")

logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


class Gemini(BaseAi):
    def __init__(self) -> None:
        super().__init__()
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(
            "gemini-2.0-flash-exp",
            generation_config={"max_output_tokens": 4000},
            system_instruction=(
                """Você é Harpi, um bot de Discord.
Criado pelo usuário SmileyDroid (Apelidado de Sorriso).
Você está aqui para ajudar com qualquer coisa que te pedirem.
Seja gentil e animado. Extrapole bastante e divirta-se!
Quando for solicitado, você pode chutar alguma resposta próxima da realidade.
Sempre use suas funções, elas são realmente uteis
e podem te ajudar muito.
Tente não formular respostas muito longas,
apenas o suficiente para responder a pergunta.
Porém tente sempre ser o mais completo possível.
Solucione o problema da pessoa, tente, não faça perguntas.
Não há a necessidade de explicar suas funções e ferramentas, quando for necessário
utilizá-las apenas faça. E faça o máximo possível.
"""
            ),
        )
        self.chat = self.model.start_chat()
        self.chat_starting_time = datetime.datetime.now(
            tz=datetime.timezone(datetime.timedelta(hours=-3)),
        )

    def reset_chat(self) -> None:
        """Reset chat session."""
        self.chat = self.model.start_chat()
        self.chat_starting_time = datetime.datetime.now(
            tz=datetime.timezone(datetime.timedelta(hours=-3)),
        )

    @staticmethod
    def _has_function_call(
        response: GenerateContentResponse,
    ) -> bool:
        for part in response.candidates[0].content.parts:
            if part.function_call:
                return True
        return False

    async def _handle_function_calls(
        self,
        response: GenerateContentResponse,
        ctx: discord.ext.commands.Context,
        tools: AiTools,
    ) -> GenerateContentResponse:
        """Handle function calls in the response.

        Returns
        -------
        GenerateContentResponse
            Response with function calls handled.
        """
        try:
            while self._has_function_call(response):
                for part in response.candidates[0].content.parts:
                    if fn := part.function_call:
                        try:
                            result = await tools.call_function(
                                ctx,
                                fn.name,
                                fn.args.items(),
                            )
                        except Exception as e:  # noqa: BLE001
                            logger.error("Error calling function: %s", e)
                            result = str(e)
                        s = Struct()
                        s.update({"result": result})
                        function_response = genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=fn.name,
                                response=s,
                            ),
                        )
                        response = self.chat.send_message(function_response)
                    else:
                        if part.text and len(part.text) > 0:
                            if part.text == "\n":
                                await ctx.send("*Em silêncio*", silent=True)
                            else:
                                await ctx.send(part.text)
        except Exception as e:  # noqa: BLE001
            logger.error(e)
            response = self.chat.send_message(
                f'[Erro: "{e}"]',
            )
        return response

    async def get_response(
        self,
        message: str,
        ctx: discord.ext.commands.Context,
        tools: AiTools,
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
        history = [history async for history in ctx.history(limit=15)]

        content: ContentsType = [
            f"<<<{old_message.created_at} - {old_message.author.display_name}({old_message.author.name})>>>: {old_message.content}"
            for old_message in history
        ] + [
            f"<<<{ctx.message.created_at} - {ctx.author.display_name}({ctx.author.name})>>>: {message}",
        ]

        if reference := ctx.message.reference:
            resolved = reference.resolved
            if isinstance(resolved, discord.Message):
                content.append(
                    f"> <<<{resolved.created_at} - {resolved.author.display_name}({resolved.author.name})>>>: {resolved.content}",
                )

        response: GenerateContentResponse = self.chat.send_message(
            content,
            tools=(tools.get_tools() or []),
        )

        logger.info(response.candidates[0].content.parts)
        response = await self._handle_function_calls(response, ctx, tools)
        return response.text


if __name__ == "__main__":
    ai = Gemini()
