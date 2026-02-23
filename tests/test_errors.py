from src.errors.nothingfound import NothingFoundError
from src.errors.bad_link import BadLink


class TestNothingFoundError:
    def test_creates_with_query(self):
        error = NothingFoundError("test query")
        assert error.query == "test query"

    def test_message_contains_query(self):
        error = NothingFoundError("my search term")
        assert "my search term" in str(error)

    def test_message_in_portuguese(self):
        error = NothingFoundError("video name")
        message = str(error)
        assert "Não foi possível encontrar" in message

    def test_is_exception(self):
        error = NothingFoundError("query")
        assert isinstance(error, Exception)

    def test_can_be_raised_and_caught(self):
        try:
            raise NothingFoundError("test")
        except NothingFoundError as e:
            assert e.query == "test"


class TestBadLink:
    def test_creates_with_link(self):
        error = BadLink("https://invalid.url")
        assert error.link == "https://invalid.url"

    def test_str_representation(self):
        error = BadLink("https://bad.link")
        result = str(error)
        assert "Link inválido" in result
        assert "https://bad.link" in result

    def test_is_exception(self):
        error = BadLink("any link")
        assert isinstance(error, Exception)

    def test_can_be_raised_and_caught(self):
        try:
            raise BadLink("bad_url")
        except BadLink as e:
            assert e.link == "bad_url"

    def test_empty_link(self):
        error = BadLink("")
        assert error.link == ""
        assert "Link inválido" in str(error)
