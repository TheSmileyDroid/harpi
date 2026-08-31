class NothingFoundError(Exception):
    """Raised when a search query finds no video."""

    def __init__(self, query: str) -> None:
        self.query = query
        super().__init__(
            f"Não foi possível encontrar nenhum vídeo para {query}.",
        )
