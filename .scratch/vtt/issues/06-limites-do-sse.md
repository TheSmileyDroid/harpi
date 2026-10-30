# Limites do SSE para a mesa

Type: research
Status: resolved

## Question

O SSE e o sampler atuais aguentam updates de posição de token a cerca de 10 Hz com uma mesa de 5 a 8 jogadores, ou o VTT precisa de WebSocket?

Levantar:

- custo do sampler atual: poll de 0.5 s, tick de 5 s, filas limitadas, slots por usuário e por guild.
- custo de um frame de mesa a 10 Hz com 8 clientes.
- comportamento do Quart e uvicorn com uma conexão SSE por jogador.
- reconexão e resync.
- comparar SSE dedicado, WebSocket e polling.
- medir ou estimar com o código real; citar arquivos e números.

Resolução: nota de pesquisa com números e recomendação, sem alterar código de produção.

## Answer

SSE aguenta o download a 10 Hz. Uma Table de 8 jogadores com stream dedicado custa 12,6 KiB/s e 0,75% de um core em deltas, ou 114 KiB/s e 1,0% em snapshots completos. O sampler atual não serve de fonte: poll de 0,5 s, tick de 5 s, e baixar o tick para 0,1 s custaria ~22% de um core com 8 streams só nas escritas de presença no SQLite.

O gargalo é o upload. 10 Hz de POST são 600 req/min por IP, mas o NPM limita `/api/` a 60 req/min (burst 10), e cada POST com commit custa 0,7 a 1,6 ms. Decisão: SSE dedicado por Table, broadcaster em memória, deltas absolutos com `rev`, snapshot na abertura, persistência no fim do drag, e uma zona própria no NPM para o endpoint de movimentos ou coalescência para 1 Hz. WebSocket não é necessário por capacidade; fica como opção se o upload a 10 Hz for requisito e o limite do edge não puder mudar.

Números, comparação e ressalvas: [research/06-realtime.md](../research/06-realtime.md).
