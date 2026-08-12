# Harpi

Bot do Discord (música, dados, TTS) com painel web HTMX servido pelo Quart no mesmo processo.

## Language

**Sessão**:
O estado de playback de uma guild — fila, camadas e conexão de voz — com um dono único por guild.
_Avoid_: player, gerenciador de áudio

**Fila**:
A sequência de faixas que a sessão toca em ordem.
_Avoid_: playlist

**Camada**:
Áudio de fundo tocado em paralelo à fila, sob o mesmo controle da sessão.
_Avoid_: som ambiente, música de fundo

**Painel**:
A interface web (Quart + HTMX) que observa e controla o bot.
_Avoid_: frontend, UI

**Read-model**:
A projeção do estado da sessão em dados de resposta consumidos pelo painel.
_Avoid_: status API, endpoint de status

**Projeção**:
A transformação de dados do read-model em contexto de template do painel.
_Avoid_: serialização, mapping
