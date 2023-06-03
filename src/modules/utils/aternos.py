from python_aternos import atclient, atserver


class Aternos:
    def __init__(self):
        self.client = atclient.Client()
        self.account = self.client.account
        self.client.login('Multisomatico', 'georgeorwell')
        print('Logged in')
        for server in self.list_servers():
            server.fetch()
            print('Server', server.subdomain, server.status)

    def list_servers(self) -> list[atserver.AternosServer]:
        return self.account.list_servers(False)

    def get_server(self, server_name: str) -> atserver.AternosServer:
        for server in self.list_servers():
            if server.subdomain == server_name:
                return server
        raise Exception('Server not found')

    def list_players(self, server_name: str) -> list[str]:
        server = self.get_server(server_name)
        return server.players_list

    def start_server(self, server_name: str) -> None:
        server = self.get_server(server_name)
        server.start()
