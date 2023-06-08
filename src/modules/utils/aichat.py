from src.modules.utils import aiassist
from src.modules.utils import pierangelo
from discord.ext import commands


class AIChat:
    def __init__(self):
        self.chat_mem = []
        self.deepai_mem = []
        self.parent_id = None
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

        if res.startswith("Harpi: "):
            res = res[7:]
        return res

    def get_response_aiassist(self, prompt: str) -> str:
        print(prompt)
        req = aiassist.Completion.create(
            prompt=prompt,
            systemMessage=self.system,
            parentMessageId=self.parent_id,
            temperature=1)
        self.parent_id = req["parentMessageId"]
        return req["text"]

    def get_response_pierangelo(self, prompt: str) -> str:
        self.chat_mem.append({'role': 'user', 'text': prompt})
        response = pierangelo._create_completion(
            'gpt-4', self.chat_mem, True, self.system)
        answer = ''
        for message in response:
            answer += str(message)
        self.chat_mem.append({'role': 'assistant', 'text': answer})
        return answer

    def get_response(self, prompt: str) -> str:
        return self.get_response_aiassist(prompt)

    def clear(self):
        self.reset()
