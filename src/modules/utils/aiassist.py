from curl_cffi import requests  # type: ignore
import json


class Completion:
    @staticmethod
    def create(
        systemMessage: str = "You are a helpful assistant",
        prompt: str = "",
        parentMessageId: str = "",
        temperature: float = 0.8,
        top_p: float = 0.8,
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

        response = requests.post(
            url, headers=headers, json=json_data, impersonate="chrome101")  # type: ignore
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
