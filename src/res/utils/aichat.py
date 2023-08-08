from src.res.utils.models import sabia
from typing import Dict, List, Optional
from discord.ext import commands
import time


TMessage = Dict[str, str]
TMessages = List[TMessage]


class AIChat:
    def __init__(self: "AIChat"):
        self.chat_mem: TMessages = []
        self.temp = 0.8
        self.top_p = 0.8
        self.system = "Data atual: " + time.strftime("%d/%m/%Y") + "\n"
        f = open("src/modules/utils/chat_mem.txt", "r")
        for line in f:
            self.system += line
        f.close()
        self.chat_mem.append({"role": "system", "content": self.system})
        self.reset()

    def reset(self):
        self.chat_mem = []
        self.deepai_mem = []
        self.system = ""
        f = open("src/modules/utils/chat_mem.txt", "r")
        for line in f:
            self.system += line
        f.close()
        self.chat_mem.append({"role": "user", "content": self.system})

    async def chat(self, ctx: Optional[commands.Context], prompt: str) -> str:
        if ctx is not None:
            prompt_with_author = ctx.author.name + ": " + prompt
        else:
            prompt_with_author = "smileydroid" + ": " + prompt

        print(prompt_with_author)

        res = await self.get_response(prompt_with_author, ctx)

        return res

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

    async def get_response_sabia(
        self, prompt: str, ctx: commands.Context | None = None
    ) -> str:
        self.chat_mem.append({"role": "user", "content": prompt})

        answer: str = sabia.complete(
            messages=self.chat_mem,
            temperature=self.temp,
            top_p=self.top_p,
        )

        self.chat_mem.append({"role": "assistant", "content": answer})

        return answer

    async def get_response(
        self, prompt: str, ctx: Optional[commands.Context] = None
    ) -> str:
        return await self.get_response_sabia(prompt, ctx)

    def clear(self):
        self.reset()
