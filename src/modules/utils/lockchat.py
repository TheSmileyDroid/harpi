from curl_cffi import requests  # type: ignore
import json
from discord.ext import commands

from threading import Semaphore

semaphore = Semaphore(1)


class Completion:
    @staticmethod
    async def create(
        systemMessage: str = "You are a helpful assistant",
        prompt: str = "",
        messages: list[dict[str, str]] = [],
        temperature: float = 0.7,
        ctx: commands.Context | None = None,
    ):
        payload = {
            "temperature": temperature,
            "messages": messages,
            "model": 'gpt-3.5-turbo',
            "stream": True,
        }
        headers = {
            "user-agent": "ChatX/39 CFNetwork/1408.0.4 Darwin/22.5.0",
        }

        url = "http://supertest.lockchat.app"

        semaphore.acquire()
        response = requests.post(
            url, headers=headers, json=payload)  # type: ignore

        answer = ''

        for token in response.iter_lines():  # type: ignore
            if b'The model: `gpt-4` does not exist' in token:
                print('error, retrying...')
                await Completion.create(messages=messages, temperature=temperature)
            if b"content" in token:
                token = json.loads(token.decode(
                    'utf-8').split('data: ')[1])['choices'][0]['delta'].get('content')
                if token:
                    answer += token

        semaphore.release()

        print(answer)

        return answer


if __name__ == "__main__":
    print(Completion.create(prompt="Hello, how are you?"))
