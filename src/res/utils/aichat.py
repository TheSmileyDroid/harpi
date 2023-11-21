import logging
from typing import Optional
from discord.ext import commands
import time
from maritalk import MariTalk

logger = logging.getLogger(__name__)


class AIChat:
    def __init__(self: "AIChat") -> None:
        self.temp = 0.5
        self.top_p = 0.6
        self.system = "Data atual: " + time.strftime("%d/%m/%Y") + "\n"
        f = open("src/res/utils/chat_mem.txt", "r")
        for line in f:
            self.system += line
        f.close()
        self.chat_mem: str = self.system
        self.reset()
        self.model = MariTalk(
            key="108771055631679688191$6d19696e53fbbb3ca42e67760ae448d210db08ed1f32628b534bc8ef5f078aae"
        )

    def reset(self):
        self.deepai_mem = []
        self.system = ""
        f = open("src/res/utils/chat_mem.txt", "r")
        for line in f:
            self.system += line
        f.close()
        self.chat_mem: str = self.system

    def set_temp(self, temp: float):
        if temp < 0.1 or temp > 0.9:
            raise ValueError("Temperature must be between 0.1 and 0.9")
        self.temp = temp

    def set_top_p(self, top_p: float):
        if top_p < 0.1 or top_p > 0.9:
            raise ValueError("Top P must be between 0.1 and 0.9")
        self.top_p = top_p

    def get_temp(self) -> float:
        return self.temp

    def get_top_p(self) -> float:
        return self.top_p

    async def get_response(
        self, prompt: str, ctx: Optional[commands.Context] = None
    ) -> str:
        self.chat_mem += "MENSAGEM\n"

        if ctx is not None:
            self.chat_mem += ctx.author.name + ": " + prompt.strip() + "\n"

        else:
            self.chat_mem += "smileydroid" + ": " + prompt.strip() + "\n"

        answer = self.complete()

        while answer == "":
            answer = self.complete()

        if len(self.chat_mem) > 4000:
            aux = self.chat_mem.removeprefix(self.system).split("\n")
            size = 0
            limit = -1
            for i in range(len(aux), 0, -1):
                size += len(aux[i - 1])
                if size > 4000:
                    limit = i - 1
                    break
            self.chat_mem = self.system + "\n".join(aux[limit:])
        return answer.strip()

    def complete(self):
        answer = self.model.generate(
            self.chat_mem,
            chat_mode=False,
            stopping_tokens=["MENSAGEM"],
            temperature=self.temp,
            top_p=self.top_p,
            max_tokens=2500,
        )

        if not isinstance(answer, str):
            raise ValueError("Could not generate text")

        print(
            "Pensamentos do harpi:"
            + str([line for line in answer.split("\n") if "Harpi:" not in line])
        )

        logger.info(answer)
        logger.info(len(answer))

        lines = answer.removesuffix("MENSAGEM").removesuffix("\n").split("\n")
        answer = ""
        started_answering = False
        for line in lines:
            self.chat_mem += line + "\n"
            if not started_answering:
                if line.startswith("Harpi:"):
                    started_answering = True
                    answer += line.removeprefix("Harpi:").strip() + "\n"
            else:
                answer += line.strip() + "\n"
        return answer

    def get_mem(self):
        return self.chat_mem

    def set_mem(self, mem):
        self.chat_mem = mem

    def clear(self):
        self.reset()
