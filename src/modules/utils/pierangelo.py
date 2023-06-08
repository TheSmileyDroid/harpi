import requests


url = 'https://chat.pierangelo.info'
model = ['gpt-4', 'gpt-3.5-turbo']
supports_stream = True

models = {
    'gpt-4': {
        'id': 'gpt-4',
        'name': 'GPT-4'
    },
    'gpt-3.5-turbo': {
        'id': 'gpt-3.5-turbo',
        'name': 'GPT-3.5'
    }
}


def _create_completion(model: str, messages: list, stream: bool, system: str, **kwargs):  # noqa E501

    headers = {
        'authority': 'chat.pierangelo.info',
        'accept': '*/*',
        'accept-language': 'en,fr-FR;q=0.9,fr;q=0.8,es-ES;q=0.7,es;q=0.6,en-US;q=0.5,am;q=0.4,de;q=0.3',  # noqa E501
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'origin': 'https://chat.pierangelo.info',
        'pragma': 'no-cache',
        'referer': 'https://chat.pierangelo.info/',
        'sec-ch-ua': '"Google Chrome";v="113", "Chromium";v="113", "Not-A.Brand";v="24"',  # noqa E501
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',  # noqa E501
    }

    json_data = {
        'model': models[model],
        'messages': messages,
        'key': '',
        'prompt': system,
        'temperature': 0.7
    }

    response = requests.post('https://chat.pierangelo.info/api/chat',
                             headers=headers, json=json_data, stream=True)

    for token in response:
        yield (token)
