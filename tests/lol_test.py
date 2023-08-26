from src.res.utils.lolapi import LolApi


def test_get_champion():
    api = LolApi()

    champion = api.get_champion_by_number(0)

    assert champion["id"] == "Aatrox"
    assert champion["title"] == "a Espada Darkin"

def test_get_champion_by_name():
    api = LolApi()

    champion = api.get_champion_by_name("Aatrox")

    assert champion["id"] == "Aatrox"
    assert champion["title"] == "a Espada Darkin"

def test_get_champion_by_id():
    api = LolApi()

    champion = api.get_champion_by_id("Aatrox")

    assert champion["id"] == "Aatrox"
    assert champion["title"] == "a Espada Darkin"

def test_get_item():
    api = LolApi()

    item = api.get_item_by_number(0)

    assert item["name"] == "Botas"
    assert item["plaintext"] == "Aumenta levemente a Velocidade de Movimento"

def test_get_item_by_name():
    api = LolApi()

    item = api.get_item_by_name("Botas")

    assert item["name"] == "Botas"
    assert item["plaintext"] == "Aumenta levemente a Velocidade de Movimento"

def test_get_item_by_id():
    api = LolApi()

    item = api.get_item_by_id("1001")

    assert item["name"] == "Botas"
    assert item["plaintext"] == "Aumenta levemente a Velocidade de Movimento"
