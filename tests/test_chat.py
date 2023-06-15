import unittest
from src.modules.utils.aichat import AIChat
from unittest.mock import MagicMock


class TestAIChat(unittest.TestCase):

    def setUp(self):
        self.ctx = MagicMock()
        self.ctx.author = MagicMock()
        self.ctx.author.name = 'SmileyDroid'

    def test_chat(self):
        chat = AIChat()
        response = chat.chat(self.ctx, 'Olá')
        print(f'Response: {response}')
        self.assertGreater(len(response), 0)
