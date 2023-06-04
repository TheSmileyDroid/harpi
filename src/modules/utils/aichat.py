from gpt4free import you


class AIChat:
    def __init__(self):
        self.chat_mem = []
        self.reset()

    def reset(self):
        self.chat_mem = []
        text = ''
        f = open('src/modules/utils/chat_mem.txt', 'r')
        for line in f:
            text += line
        f.close()
        self.chat_mem.append(
            {
                "question": text,
                "answer": "OK"})

    def chat(self, prompt: str, include_links: bool = False) -> str:
        res, links = self.get_response(prompt)
        if include_links:
            res += "\nLinks:"
            for link in links:
                res += f"\n{link.encode().decode('unicode_escape')}"
        return res

    def get_response(self, prompt: str) -> tuple[str, list[str]]:
        response = you.Completion.create(
            prompt=prompt,
            chat=self.chat_mem)

        if "Unable to fetch the response, Please try again." in response.text:
            for i in range(4):
                response = you.Completion.create(
                    prompt=prompt,
                    chat=self.chat_mem)
                if "Unable to fetch the response, Please try again." not in response.text:  # noqa: E501
                    break

        if "Unable to fetch the response, Please try again." in response.text:
            raise Exception(response.text)

        self.chat_mem.append({"question": prompt, "answer": response.text})

        return response.text.encode().decode('unicode_escape'), response.links

    def clear(self):
        self.reset()
