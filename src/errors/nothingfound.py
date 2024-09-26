"""Erro gerado quando nenhum vídeo for encontrado."""


class NothingFoundError(Exception):
    """Erro gerado quando nenhum vídeo for encontrado."""

    def __init__(self, query: str) -> None:
        """Cria uma instância de NothingFound.

        Args:
            query (str): A string representing the search query.

        """
        self.query = query
        super().__init__(
            f"Não foi possível encontrar nenhum vídeo para {query}.",
        )
