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
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/114.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'pt-BR,en-US;q=0.7,en;q=0.3',
            # 'Accept-Encoding': 'gzip, deflate',
            'Content-Type': 'application/json',
            'Origin': 'http://aiassist.art',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Referer': 'http://aiassist.art/',
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

        return Completion.__load_json(content)

    @classmethod
    def __load_json(cls, content) -> dict:
        split = content.rsplit("\n", 1)[1]
        to_json = json.loads(split)
        return to_json
