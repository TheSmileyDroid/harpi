"""Error raised for invalid links."""


class BadLink(Exception):
    """Error raised when the provided link is invalid."""

    def __init__(self, link: str) -> None:
        self.link = link

    def __str__(self) -> str:
        return f"Link inválido: {self.link}"
