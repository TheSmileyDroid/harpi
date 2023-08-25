from typing import Dict, Sequence
import requests

from threading import Semaphore

my_key = "107292054666352856189$0f7323502b44841407accd18f7474445bdf4638695455a120e1dee5cb9e1b8ef"

auth_header = {"authorization": f"Key {my_key}"}

TMessage = Dict[str, str]
TMessages = Sequence[TMessage]

semaphore = Semaphore(1)


def complete(
    messages: TMessages,
    temperature: float = 0.7,
    top_p: float = 0.95,
    repetition_penalty: float = 2.0,
) -> str:
    request_data = {
        "messages": messages,
        "do_sample": True,
        "temperature": temperature,
        "top_p": top_p,
        "repetition_penalty": repetition_penalty,
    }

    url = "https://chat.maritaca.ai/api/chat/inference"

    auth_header = {"authorization": f"Key {my_key}"}

    semaphore.acquire()
    response = requests.post(url=url, json=request_data, headers=auth_header)

    while True:
        response = requests.post(url=url, json=request_data, headers=auth_header)
        if response.status_code == 429:
            time.sleep(5)
        else:
            break

    semaphore.release()
    
    if response.ok:
        data = response.json()
        print(data["answer"])
        return data["answer"]

    else:
        print(response.status_code)
        print(response.content)
        response.raise_for_status()
        raise Exception("Erro desconhecido")


if __name__ == "__main__":
    print(
        complete(
            [
                {"role": "system", "content": "Você é um bot de Discord"},
                {"role": "user", "content": "Tudo bom?"},
            ]
        )
    )
