import urllib.request
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
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/114.0',  # noqa
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'pt-BR,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Content-Type': 'application/json',
            'Origin': 'http://huirui.work',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Referer': 'http://huirui.work/',
        }

        json_data = {
            "prompt": prompt,
            "options": {"parentMessageId": parentMessageId},
            "systemMessage": systemMessage,
            "temperature": temperature,
            "top_p": top_p,
        }

        url = "http://43.153.7.56:8080/api/chat-process"

        data = json.dumps(json_data).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers)
        response = urllib.request.urlopen(req)
        content = response.read().decode()

        return Completion.__load_json(content)

    @classmethod
    def __load_json(cls, content) -> dict:
        split = content.rsplit("\n", 1)[1]
        to_json = json.loads(split)
        return to_json
