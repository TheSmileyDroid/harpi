import requests

url = "https://chat.maritaca.ai/api/chat/inference"

messages = [
    {"role": "user", "content": "bom dia, esta é a mensagem do usuario"},
    {"role": "assistant", "content": "bom dia, esta é a resposta do assistente"},
    {"role": "user", "content": "Você pode me falar quanto é 25 + 27?"},
]


my_key = "107292054666352856189$0f7323502b44841407accd18f7474445bdf4638695455a120e1dee5cb9e1b8ef"

auth_header = {
    "authorization": f"Key {my_key}"
}

request_data = {
    "messages": messages,
    "do_sample": True,
    'max_tokens': 200,
    "temperature": 0.7,
    "top_p": 0.95,
}


def get_maritalk_response(request_data, headers):
    response = requests.post(
        url,
        json=request_data,
        headers=headers
    )

    if response.status_code == 429:
        print("rate limited, tente novamente em breve")

    elif response.ok:
        data = response.json()
        print(data["answer"])

    else:
        response.raise_for_status()


get_maritalk_response(request_data, auth_header)
