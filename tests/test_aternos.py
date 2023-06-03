import unittest
from unittest.mock import patch, MagicMock
from python_aternos import atclient, atserver
from src.modules.utils.aternos import Aternos


class TestAternos(unittest.TestCase):
    def setUp(self):
        self.aternos = Aternos()

    @patch.object(atclient.Client, 'login')
    def test_login(self, mock_login):
        self.aternos.client.login('Multisomatico', 'georgeorwell')
        mock_login.assert_called_once_with('Multisomatico', 'georgeorwell')

    @patch.object(atclient.AternosAccount, 'list_servers')
    def test_list_servers(self, mock_list_servers):
        mock_server = MagicMock(spec=atserver.AternosServer)
        mock_list_servers.return_value = [mock_server]
        result = self.aternos.list_servers()
        self.assertEqual(result, [mock_server])
        mock_list_servers.assert_called_once_with(True)

    @patch.object(atclient.AternosAccount, 'list_servers')
    def test_get_server(self, mock_list_servers):
        mock_server = MagicMock(spec=atserver.AternosServer)
        mock_server.subdomain = 'Warlordii'
        mock_list_servers.return_value = [mock_server]
        result = self.aternos.get_server('Warlordii')
        self.assertEqual(result.subdomain, 'Warlordii')
        self.assertEqual(result, mock_server)
        mock_list_servers.assert_called_once_with(True)
