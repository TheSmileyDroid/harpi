import os
from src.modules.utils import aiassist
from discord.ext import commands
import poe

models = {
    'claude-v1': 'a2_2',
    'claude-instant': 'a2',
    'claude-instant-100k': 'a2_100k',
    'sage': 'capybara',
    'gpt-4': 'beaver',
    'gpt-3.5-turbo': 'chinchilla',
}


class AIChat:
    def __init__(self):
        self.chat_mem = []
        self.deepai_mem = []
        self.parent_id = None
        self.temp = 0.8
        self.top_p = 1
        self.poe_token = os.environ.get('POE_TOKEN')
        self.system = ''
        f = open('src/modules/utils/chat_mem.txt', 'r')
        for line in f:
            self.system += line
        f.close()
        self.reset()

    def reset(self):
        self.chat_mem = []
        self.deepai_mem = []
        self.parent_id = None
        self.system = ''
        f = open('src/modules/utils/chat_mem.txt', 'r')
        for line in f:
            self.system += line
        f.close()

    def chat(self,
             ctx: commands.Context,
             prompt: str) -> str:
        prompt = ctx.author.name + ": " + prompt
        res = self.get_response(prompt)

        return res

    def set_temp(self, temp: float):
        self.temp = temp

    def set_top_p(self, top_p: float):
        self.top_p = top_p

    def get_temp(self) -> float:
        return self.temp

    def get_top_p(self) -> float:
        return self.top_p

    def get_response_aiassist(self, prompt: str) -> str:
        req = aiassist.Completion.create(
            prompt=prompt,
            systemMessage=self.system,
            parentMessageId=self.parent_id,
            temperature=self.temp,
            top_p=self.top_p,
        )
        self.parent_id = req["parentMessageId"]
        return req["text"]

    def get_response_poe(self, prompt: str) -> str:
        client = poe.Client(self.poe_token)
        poe_system = 'system: your response will be rendered in a discord message, include language hints when returning code like: ```py ...```, and use * or ** or > to create highlights ||\n ' + self.system  # noqa
        for req in client.send_message(chatbot=models['sage'], message=poe_system+prompt, with_chat_break=False):  # noqa
            pass
        return req["text"]

    def get_response(self, prompt: str) -> str:
        return self.get_response_aiassist(prompt)

    def clear(self):
        self.reset()
