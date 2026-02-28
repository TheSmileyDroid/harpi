"""Error raised when no video is found."""


class NothingFoundError(Exception):
    """Error raised when no video is found for a search query."""

    def __init__(self, query: str) -> None:
        """Create a NothingFoundError instance.

        Args:
            query (str): A string representing the search query.

        """
        self.query = query
        super().__init__(
            f"Não foi possível encontrar nenhum vídeo para {query}.",
        )
