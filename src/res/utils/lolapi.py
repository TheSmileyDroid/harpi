from abc import ABC, abstractmethod
import requests
import random

class ILolApi(ABC):
    @abstractmethod
    def get_champion_by_number(self, champion_number: int) -> dict:
        pass

    @abstractmethod
    def get_champion_by_name(self, champion_name: str) -> dict:
        pass

    @abstractmethod
    def get_champion_by_id(self, champion_id: int) -> dict:
        pass

    @abstractmethod
    def get_item_by_number(self, item_number: int) -> dict:
        pass

    @abstractmethod
    def get_item_by_name(self, item_name: str) -> dict:
        pass

    @abstractmethod
    def get_item_by_id(self, item_id: int) -> dict:
        pass

    @abstractmethod
    def random_champion(self) -> dict:
        pass

    @abstractmethod
    def random_item(self) -> dict:
        pass

    @abstractmethod
    def random_champion_build(self) -> dict:
        pass

class LolApi(ILolApi):
    def __init__(self):
        versions: list[str] = requests.get('https://ddragon.leagueoflegends.com/api/versions.json').json()
        self.version = versions[0]
        self.champions: dict = requests.get(f'http://ddragon.leagueoflegends.com/cdn/{self.version}/data/pt_BR/champion.json').json()['data']
        self.champions_list: list[dict] = list(self.champions.values())
        self.items: dict = requests.get(f'http://ddragon.leagueoflegends.com/cdn/{self.version}/data/pt_BR/item.json').json()['data']
        self.items_list: list[dict] = list(self.items.values())

    def get_champion_by_number(self, champion_number: int) -> dict:
        return self.champions_list[champion_number]

    def get_champion_by_name(self, champion_name: str) -> dict:
        for champion in self.champions_list:
            if champion['name'] == champion_name:
                return champion

    def get_champion_by_id(self, champion_id: str) -> dict:
        return self.champions[champion_id]

    def get_item_by_number(self, item_number: int) -> dict:
        return self.items_list[item_number]

    def get_item_by_name(self, item_name: str) -> dict:
        for item in self.items_list:
            if item['name'] == item_name:
                return item

    def get_item_by_id(self, item_id: str) -> dict:
        return self.items[item_id]

    def random_champion(self) -> dict:
        return random.choice(self.champions_list)

    def random_item(self) -> dict:
        return random.choice(self.items_list)

    def random_champion_build(self) -> dict:
        champion = self.random_champion()
        items = []
        for i in range(6):
            items.append(self.random_item())
        return {
            'champion': champion,
            'items': items
        }

