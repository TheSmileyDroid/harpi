from typing import Dict, List, Literal
import requests

from threading import Semaphore

# Coloque aqui a sua chave de API (ex: "10035481...").
my_key = "107292054666352856189$0f7323502b44841407accd18f7474445bdf4638695455a120e1dee5cb9e1b8ef"

auth_header = {
    "authorization": f"Key {my_key}"
}

RoleC = Literal["system"] | Literal["user"] | Literal["assistant"]
Role = Literal["role"]
Content = Literal["content"]
ContentC = str
Message = Dict[Role | Content, RoleC | ContentC]
Messages = List[Message]

semaphore = Semaphore(1)


def complete(
        messages: Messages,
        temperature: float = 0.7,
        top_p: float = 0.95,
        repetition_penalty: float = 1.0,

) -> str:
    request_data = {
        "messages": messages,
        "do_sample": True,
        'max_tokens': 200,
        "temperature": temperature,
        "top_p": top_p,
    }

    url = "https://chat.maritaca.ai/api/chat/inference"

    auth_header = {
        "authorization": f"Key {my_key}"
    }

    semaphore.acquire()
    response = requests.post(
        url=url,
        json=request_data,
        headers=auth_header
    )
    semaphore.release()

    if response.status_code == 429:
        raise Exception("(rate limited, tente novamente em breve)")

    elif response.ok:
        data = response.json()
        print(data["answer"])
        return data["answer"]

    else:
        print(response.status_code)
        print(response.content)
        response.raise_for_status()
        raise Exception("Erro desconhecido")


if __name__ == "__main__":
    print(complete([
        {"role": "system", "content": "Você é um bot de Discord"},
        {"role": "user", "content": "Tudo bom?"},
    ]))
