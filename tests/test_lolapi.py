import pytest
from unittest.mock import MagicMock, patch
from src.res.utils.lolapi import LolApi

versions = [
    "13.22.1",
    "13.21.1",
]

champions = {
    "type": "champion",
    "format": "standAloneComplex",
    "version": "13.22.1",
    "data": {
        "Aatrox": {
            "version": "13.22.1",
            "id": "Aatrox",
            "key": "266",
            "name": "Aatrox",
            "title": "a Espada Darkin",
            "blurb": "Antes defensores honrados de Shurima contra o temido Vazio, Aatrox e seus irmãos acabaram se tornando uma ameaça ainda maior para Runeterra, e a única coisa capaz de derrotá-los foi um tipo de feitiçaria mortal e traiçoeira. Mas após séculos de...",
            "info": {"attack": 8, "defense": 4, "magic": 3, "difficulty": 4},
            "image": {
                "full": "Aatrox.png",
                "sprite": "champion0.png",
                "group": "champion",
                "x": 0,
                "y": 0,
                "w": 48,
                "h": 48,
            },
            "tags": ["Fighter", "Tank"],
            "partype": "Poço de Sangue",
            "stats": {
                "hp": 650,
                "hpperlevel": 114,
                "mp": 0,
                "mpperlevel": 0,
                "movespeed": 345,
                "armor": 38,
                "armorperlevel": 4.45,
                "spellblock": 32,
                "spellblockperlevel": 2.05,
                "attackrange": 175,
                "hpregen": 3,
                "hpregenperlevel": 1,
                "mpregen": 0,
                "mpregenperlevel": 0,
                "crit": 0,
                "critperlevel": 0,
                "attackdamage": 60,
                "attackdamageperlevel": 5,
                "attackspeedperlevel": 2.5,
                "attackspeed": 0.651,
            },
        },
        "Ahri": {
            "version": "13.22.1",
            "id": "Ahri",
            "key": "103",
            "name": "Ahri",
            "title": "a Raposa de Nove Caudas",
            "blurb": "A ligação de Ahri com a magia do mundo espiritual é inata. Ela é uma vastaya com traços de raposa, capaz de manipular as emoções de sua presa e consumir sua essência, devorando também as memórias e as percepções de cada alma absorvida. Outrora uma...",
            "info": {"attack": 3, "defense": 4, "magic": 8, "difficulty": 5},
            "image": {
                "full": "Ahri.png",
                "sprite": "champion0.png",
                "group": "champion",
                "x": 48,
                "y": 0,
                "w": 48,
                "h": 48,
            },
            "tags": ["Mage", "Assassin"],
            "partype": "Mana",
            "stats": {
                "hp": 590,
                "hpperlevel": 96,
                "mp": 418,
                "mpperlevel": 25,
                "movespeed": 330,
                "armor": 21,
                "armorperlevel": 4.7,
                "spellblock": 30,
                "spellblockperlevel": 1.3,
                "attackrange": 550,
                "hpregen": 2.5,
                "hpregenperlevel": 0.6,
                "mpregen": 8,
                "mpregenperlevel": 0.8,
                "crit": 0,
                "critperlevel": 0,
                "attackdamage": 53,
                "attackdamageperlevel": 3,
                "attackspeedperlevel": 2.2,
                "attackspeed": 0.668,
            },
        },
        "Akali": {
            "version": "13.22.1",
            "id": "Akali",
            "key": "84",
            "name": "Akali",
            "title": "a Assassina Renegada",
            "blurb": "Abandonando a Ordem Kinkou e seu título de Punho das Sombras, Akali agora ataca sozinha, pronta para ser a arma mortal que seu povo precisa. Embora ela mantenha tudo o que aprendeu com seu mestre Shen, ela se comprometeu a defender Ionia de seus...",
            "info": {"attack": 5, "defense": 3, "magic": 8, "difficulty": 7},
            "image": {
                "full": "Akali.png",
                "sprite": "champion0.png",
                "group": "champion",
                "x": 96,
                "y": 0,
                "w": 48,
                "h": 48,
            },
            "tags": ["Assassin"],
            "partype": "Energia",
            "stats": {
                "hp": 570,
                "hpperlevel": 119,
                "mp": 200,
                "mpperlevel": 0,
                "movespeed": 345,
                "armor": 23,
                "armorperlevel": 4.7,
                "spellblock": 37,
                "spellblockperlevel": 2.05,
                "attackrange": 125,
                "hpregen": 9,
                "hpregenperlevel": 0.9,
                "mpregen": 50,
                "mpregenperlevel": 0,
                "crit": 0,
                "critperlevel": 0,
                "attackdamage": 62,
                "attackdamageperlevel": 3.3,
                "attackspeedperlevel": 3.2,
                "attackspeed": 0.625,
            },
        },
        "Akshan": {
            "version": "13.22.1",
            "id": "Akshan",
            "key": "166",
            "name": "Akshan",
            "title": "o Sentinela Rebelde",
            "blurb": "Akshan ri da cara do perigo, lutando contra o mal com carisma, determinação e desejo de vingança, mas, estranhamente, sem vestir uma camisa sequer. É extremamente habilidoso na arte do combate furtivo, capaz de sumir da vista dos inimigos e reaparecer...",
            "info": {"attack": 0, "defense": 0, "magic": 0, "difficulty": 0},
            "image": {
                "full": "Akshan.png",
                "sprite": "champion0.png",
                "group": "champion",
                "x": 144,
                "y": 0,
                "w": 48,
                "h": 48,
            },
            "tags": ["Marksman", "Assassin"],
            "partype": "Mana",
            "stats": {
                "hp": 630,
                "hpperlevel": 107,
                "mp": 350,
                "mpperlevel": 40,
                "movespeed": 330,
                "armor": 26,
                "armorperlevel": 4.7,
                "spellblock": 30,
                "spellblockperlevel": 1.3,
                "attackrange": 500,
                "hpregen": 3.75,
                "hpregenperlevel": 0.65,
                "mpregen": 8.2,
                "mpregenperlevel": 0.7,
                "crit": 0,
                "critperlevel": 0,
                "attackdamage": 52,
                "attackdamageperlevel": 3,
                "attackspeedperlevel": 4,
                "attackspeed": 0.638,
            },
        },
    },
}

itens = {
    "type": "item",
    "version": "13.22.1",
    "basic": {
        "name": "",
        "rune": {"isrune": True, "tier": 1, "type": "red"},
        "gold": {"base": 0, "total": 0, "sell": 0, "purchasable": False},
        "group": "",
        "description": "",
        "colloq": ";",
        "plaintext": "",
        "consumed": False,
        "stacks": 1,
        "depth": 1,
        "consumeOnFull": False,
        "from": [],
        "into": [],
        "specialRecipe": 0,
        "inStore": True,
        "hideFromAll": False,
        "requiredChampion": "",
        "requiredAlly": "",
        "stats": {
            "FlatHPPoolMod": 0,
            "rFlatHPModPerLevel": 0,
            "FlatMPPoolMod": 0,
            "rFlatMPModPerLevel": 0,
            "PercentHPPoolMod": 0,
            "PercentMPPoolMod": 0,
            "FlatHPRegenMod": 0,
            "rFlatHPRegenModPerLevel": 0,
            "PercentHPRegenMod": 0,
            "FlatMPRegenMod": 0,
            "rFlatMPRegenModPerLevel": 0,
            "PercentMPRegenMod": 0,
            "FlatArmorMod": 0,
            "rFlatArmorModPerLevel": 0,
            "PercentArmorMod": 0,
            "rFlatArmorPenetrationMod": 0,
            "rFlatArmorPenetrationModPerLevel": 0,
            "rPercentArmorPenetrationMod": 0,
            "rPercentArmorPenetrationModPerLevel": 0,
            "FlatPhysicalDamageMod": 0,
            "rFlatPhysicalDamageModPerLevel": 0,
            "PercentPhysicalDamageMod": 0,
            "FlatMagicDamageMod": 0,
            "rFlatMagicDamageModPerLevel": 0,
            "PercentMagicDamageMod": 0,
            "FlatMovementSpeedMod": 0,
            "rFlatMovementSpeedModPerLevel": 0,
            "PercentMovementSpeedMod": 0,
            "rPercentMovementSpeedModPerLevel": 0,
            "FlatAttackSpeedMod": 0,
            "PercentAttackSpeedMod": 0,
            "rPercentAttackSpeedModPerLevel": 0,
            "rFlatDodgeMod": 0,
            "rFlatDodgeModPerLevel": 0,
            "PercentDodgeMod": 0,
            "FlatCritChanceMod": 0,
            "rFlatCritChanceModPerLevel": 0,
            "PercentCritChanceMod": 0,
            "FlatCritDamageMod": 0,
            "rFlatCritDamageModPerLevel": 0,
            "PercentCritDamageMod": 0,
            "FlatBlockMod": 0,
            "PercentBlockMod": 0,
            "FlatSpellBlockMod": 0,
            "rFlatSpellBlockModPerLevel": 0,
            "PercentSpellBlockMod": 0,
            "FlatEXPBonus": 0,
            "PercentEXPBonus": 0,
            "rPercentCooldownMod": 0,
            "rPercentCooldownModPerLevel": 0,
            "rFlatTimeDeadMod": 0,
            "rFlatTimeDeadModPerLevel": 0,
            "rPercentTimeDeadMod": 0,
            "rPercentTimeDeadModPerLevel": 0,
            "rFlatGoldPer10Mod": 0,
            "rFlatMagicPenetrationMod": 0,
            "rFlatMagicPenetrationModPerLevel": 0,
            "rPercentMagicPenetrationMod": 0,
            "rPercentMagicPenetrationModPerLevel": 0,
            "FlatEnergyRegenMod": 0,
            "rFlatEnergyRegenModPerLevel": 0,
            "FlatEnergyPoolMod": 0,
            "rFlatEnergyModPerLevel": 0,
            "PercentLifeStealMod": 0,
            "PercentSpellVampMod": 0,
        },
        "tags": [],
        "maps": {"1": True, "8": True, "10": True, "12": True},
    },
    "data": {
        "1001": {
            "name": "Botas",
            "description": "<mainText><stats><attention>25</attention> de Velocidade de Movimento</stats></mainText><br>",
            "colloq": ";boot",
            "plaintext": "Aumenta levemente a Velocidade de Movimento",
            "into": ["3005", "3158", "3117", "3047", "3020", "3006", "3009", "3111"],
            "image": {
                "full": "1001.png",
                "sprite": "item0.png",
                "group": "item",
                "x": 0,
                "y": 0,
                "w": 48,
                "h": 48,
            },
            "gold": {"base": 300, "purchasable": True, "total": 300, "sell": 210},
            "tags": ["Boots"],
            "maps": {"11": True, "12": True, "21": True, "22": False, "30": False},
            "stats": {"FlatMovementSpeedMod": 25},
        },
        "1004": {
            "name": "Amuleto da Fada",
            "description": "<mainText><stats><attention>50%</attention> de Regeneração de Mana base</stats></mainText><br>",
            "colloq": ";",
            "plaintext": "Aumenta levemente a Regeneração de Mana",
            "into": ["3012", "3114", "4642"],
            "image": {
                "full": "1004.png",
                "sprite": "item0.png",
                "group": "item",
                "x": 48,
                "y": 0,
                "w": 48,
                "h": 48,
            },
            "gold": {"base": 250, "purchasable": True, "total": 250, "sell": 175},
            "tags": ["ManaRegen"],
            "maps": {"11": True, "12": True, "21": True, "22": False, "30": False},
            "stats": {},
        },
    },
}


@pytest.fixture
@patch("requests.get")
def lol_api(mock_get):
    mock_versions_response = MagicMock()
    mock_versions_response.json.return_value = versions
    mock_champions_response = MagicMock()
    mock_champions_response.json.return_value = champions
    mock_items_response = MagicMock()
    mock_items_response.json.return_value = itens

    mock_get.side_effect = [
        mock_versions_response,
        mock_champions_response,
        mock_items_response,
    ]

    lol_api = LolApi()

    mock_get.assert_any_call("https://ddragon.leagueoflegends.com/api/versions.json")
    mock_get.assert_any_call(
        "http://ddragon.leagueoflegends.com/cdn/13.22.1/data/pt_BR/champion.json"
    )
    mock_get.assert_any_call(
        "http://ddragon.leagueoflegends.com/cdn/13.22.1/data/pt_BR/item.json"
    )

    return lol_api


def test_get_champion_by_number(lol_api):
    champion = lol_api.get_champion_by_number(0)
    assert champion["name"] == "Aatrox"


def test_get_champion_by_name(lol_api):
    champion = lol_api.get_champion_by_name("Aatrox")
    assert champion["id"] == "Aatrox"


def test_get_champion_by_id(lol_api):
    champion = lol_api.get_champion_by_id("Aatrox")
    assert champion["name"] == "Aatrox"


def test_get_item_by_number(lol_api):
    item = lol_api.get_item_by_number(0)
    assert item["name"] == "Botas"


def test_get_item_by_name(lol_api):
    item = lol_api.get_item_by_name("Botas")
    assert item
    assert item["name"] == "Botas"


def test_get_item_by_id(lol_api):
    item = lol_api.get_item_by_id("1001")
    assert item["name"] == "Botas"


@patch("random.choice")
def test_random_champion(mock_choice, lol_api):
    mock_choice.return_value = {"name": "Aatrox"}
    champion = lol_api.random_champion()
    assert champion["name"] == "Aatrox"


@patch("random.choice")
def test_random_item(mock_choice, lol_api):
    mock_choice.return_value = {"name": "Botas"}
    item = lol_api.random_item()
    assert item["name"] == "Botas"
