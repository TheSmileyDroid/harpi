from time import sleep
from curl_cffi import requests
import json
from discord.ext import commands

from threading import Semaphore

semaphore = Semaphore(1)


class Completion:
    @staticmethod
    async def create(
        systemMessage: str = "You are a helpful assistant",
        prompt: str = "",
        parentMessageId: str = "",
        temperature: float = 0.8,
        top_p: float = 0.8,
        ctx: commands.Context | None = None,
    ):
        headers = {
            'Content-Type': 'application/json'
        }

        json_data = {
            "prompt": prompt,
            "options": {"parentMessageId": parentMessageId},
            "systemMessage": systemMessage,
            "temperature": temperature,
            "top_p": top_p,
        }

        url = "http://43.153.7.56:8081/api/chat-process"

        semaphore.acquire()
        response = requests.post(
            url, headers=headers, json=json_data, impersonate="chrome101")  # type: ignore
        if (response.status_code != 200 and ctx is not None):
            await ctx.send("Me desculpe a demora, estou processando sua mensagem!")

        while (response.status_code != 200):
            response = requests.post(
                url, headers=headers, json=json_data, impersonate="chrome101")
            sleep(1)
        semaphore.release()

        print(response.content)

        content = response.content.decode("utf-8", "ignore")

        try:
            return Completion.__load_json(content)
        except json.decoder.JSONDecodeError:
            print(content)
            raise Exception(content)

    @classmethod
    def __load_json(cls, content) -> dict:
        split = content.rsplit("\n", 1)[1]
        to_json = json.loads(split)
        return to_json


if __name__ == "__main__":
    print(Completion.create(prompt="Hello, how are you?"))
