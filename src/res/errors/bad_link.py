class BadLink(Exception):
    def __init__(self, link):
        self.link = link

    def __str__(self):
        return f"Link inválido: {self.link}"
