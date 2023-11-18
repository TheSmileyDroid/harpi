import logging
from typing import Optional
from discord.ext import commands
import time
from maritalk import MariTalk

logger = logging.getLogger(__name__)


class AIChat:
    def __init__(self: "AIChat") -> None:
        self.temp = 0.8
        self.top_p = 0.4
        self.system = "Data atual: " + time.strftime("%d/%m/%Y") + "\n"
        f = open("src/res/utils/chat_mem.txt", "r")
        for line in f:
            self.system += line
        f.close()
        self.chat_mem: str = self.system
        self.reset()
        self.model = MariTalk(
            key="107292054666352856189$76fe16ed7a38e5625753ce3f80a0f1c612af23454474db10d613b7c8a824b05a"
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
        if ctx is not None:
            self.chat_mem += ctx.author.name + ":" + prompt.strip() + "\n\n" + "Harpi: "

        else:
            self.chat_mem += "smileydroid" + ":" + prompt + "\n\n" + "Harpi:"

        answer = self.model.generate(
            self.chat_mem,
            chat_mode=False,
            stopping_tokens=["\n\n"],
            temperature=self.temp,
            top_p=self.top_p,
        )

        logger.info(answer)
        if answer is None:
            raise ValueError("Could not generate text")
        logger.info(len(answer))

        self.chat_mem += answer.removesuffix("\n").removesuffix("\n") + "\n\n"

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

        return answer.removesuffix("\n").removesuffix("\n")

    def get_mem(self):
        return self.chat_mem

    def set_mem(self, mem):
        self.chat_mem = mem

    def clear(self):
        self.reset()
