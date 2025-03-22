import asyncio
import os
import pathlib

from browser_use import Agent, Browser, BrowserConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, SecretStr

api_key = os.getenv("GEMINI_API_KEY")


config = BrowserConfig(headless=True, disable_security=True)

deletion_tasks: list[asyncio.Task] = []


class Answer(BaseModel):
    answer: str


async def _delete_file(file: str):
    await asyncio.sleep(300)
    pathlib.Path(file).unlink(missing_ok=True)


async def ask(question: str) -> Answer:
    """A função ask é responsável por fazer uma pergunta ao agente Navegador.
    O agente Navegador é um agente que pode navegar na web livremente e responder perguntas.
    Ele consegue acessar informações em tempo real e gerar respostas com base nessas informações.

    Parameters
    ----------
    question : str
        A pergunta que você deseja fazer ao agente Navegador.
        O agente Navegador irá gerar uma resposta com base nessa pergunta.

    Returns
    -------
    str
        A resposta gerada pelo agente Navegador.
        Se o agente Navegador não conseguir encontrar uma resposta, ele retornará uma mensagem padrão.
    """
    browser = Browser(config=config)

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        api_key=SecretStr(os.getenv("GEMINI_API_KEY") or ""),
    )

    agent = Agent(
        task=question
        + "\n\nPrefira utilizar de informações de dentro de sites e não confie apenas no google",
        llm=llm,
        use_vision=True,
        browser=browser,
    )

    history = await agent.run()

    result = history.final_result()

    if result:
        return Answer(
            answer=result,
        )
    else:
        return Answer(
            answer="Desculpe, não consegui encontrar uma resposta para sua pergunta.",
        )


async def main():
    answer = await ask("What is the capital of France?")
    print(answer)


if __name__ == "__main__":
    asyncio.run(main())
