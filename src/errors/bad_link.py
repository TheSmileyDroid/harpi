"""Módulo responsável por gerar erros relacionados a links inválidos."""


class BadLink(Exception):
    """Erro gerado quando o link fornecido não é válido."""

    def __init__(self, link) -> None:
        self.link = link

    def __str__(self) -> str:
        return f"Link inválido: {self.link}"
