# Limites do SSE para a mesa

Type: research
Status: resolved
Ticket: [06 Limites do SSE para a mesa](../issues/06-limites-do-sse.md)
Bancada: [06-bench](06-bench/) (scripts locais, fakes, sem rede, sem bot)

## Resposta curta

O SSE aguenta o download a 10 Hz com folga. Uma Table com 8 jogadores e um
stream dedicado custa 12,6 KiB/s e 0,75% de um core em deltas, ou 114 KiB/s e
1,0% em snapshots completos (medido). Não é preciso WebSocket por capacidade.

O sampler atual não serve como fonte a 10 Hz: ele faz poll de 0,5 s do estado
de música e o stream entrega posição a cada 5 s. Baixar o tick para 0,1 s
custaria cerca de 22% de um core só nas escritas de presença no SQLite, antes
de qualquer frame de mesa. A Table precisa de um broadcaster próprio, em
memória, separado do `GuildSampler`.

O gargalo real é o upload. Cada movimento por POST custa 0,7 a 1,6 ms de
servidor, e o NPM em produção limita `/api/` a 60 req/min por IP (1 req/s,
burst 10). A 10 Hz são 600 req/min, dez vezes o limite. Ou sobe o limite do
endpoint de movimentos, ou o cliente coalesce para 1 Hz ou menos, ou o upload
vai por WebSocket. O download pode ficar em SSE nos três casos.

## O que o código faz hoje

- **Sampler**: um `GuildSampler` por guild, poll de `POLL_SECONDS = 0.5`
  (`src/panel/sampler.py:16`), rodando enquanto houver assinante
  (`sampler.py:68-81`). Publica `status` só quando algo além de `progress`
  muda, e `position` quando o progresso salta 1 s ou mais
  (`sampler.py:105-126`). O valor de posição é atualizado a cada poll, mesmo
  sem publicar (`sampler.py:110-113`).
- **Fila por conexão**: `QUEUE_LIMIT = 32` (`sampler.py:18`), uma fila por
  assinante (`sampler.py:69`). Quando enche, `_publish` descarta o frame mais
  antigo e enfileira o novo, sem marcador de lacuna (`sampler.py:128-132`).
- **Tick de entrega**: `TICK_SECONDS = 5.0` (`pages/events.py:49`). A cada
  tick cada stream manda `position` (`events.py:138-142`) e `heartbeat`
  (`events.py:143`). O cliente avança o tempo localmente entre amostras
  (`web/src/lib/playback-clock.ts:12-24`).
- **Custo por iteração do stream**: `_steady_frames` chama
  `_current_allowed` a cada volta (`events.py:197`), que faz
  `state.user_guild_ids` e portanto um SELECT no registro
  (`src/panel/state.py:154-160`). `_reload_frame` faz `stat` de dois assets
  (`events.py:42-45`, `56-65`). No tick, `state.presence` faz um `touch`
  (três escritas com commit) e duas leituras (`state.py:217-233`,
  `src/storage/registry.py:130-171`).
- **Slots**: 5 streams por usuário, 20 por guild
  (`src/panel/rate_limit.py:13-14`); acima disso a rota responde 429 com
  `Retry-After: 30` (`events.py:243-251`). O alerta de crescimento dispara
  com 15 streams vivos (`src/alerts.py:43`).
- **Reconexão**: o cliente fecha e reconecta com backoff 1 s, 2 s, 4 s até
  30 s (`web/src/lib/sse.ts:11-13`, `42-48`), zera a contagem no `open`
  (`sse.ts:140-143`) e derruba o stream após 15 s sem nenhum frame
  (`sse.ts:13`, `105-111`). Não há `id:` nem `Last-Event-ID`; o resync é o
  snapshot de abertura (`events.py:87-99`).
- **Um processo**: o sampler e os slots são dicionários de módulo
  (`sampler.py:142-150`, `events.py:51`). O deploy roda um worker:
  `uvicorn.run` sem `workers` (`src/__main__.py:53-59`) e CMD sem
  `--workers` (`Dockerfile:49`). O ADR 0009 registra que o sampler é estado
  local de processo (`docs/adr/0009-panel-live-updates.md:63-64`).
- **Edge**: `proxy_buffering off` e `proxy_read_timeout 1h`
  (`deploy/npm/harpi-advanced.conf:1-5`), então SSE flui. O mesmo arquivo
  aplica `limit_req zone=harpi_api burst=10 nodelay` em `/api/`
  (`harpi-advanced.conf:22-30`), e a zona é `rate=60r/m` por IP
  (`deploy/npm/harpi-rate-limits-http.conf:1-2`). Não há headers de
  `Upgrade` para WebSocket nesse location.

## Medições

Máquina: aarch64, Neoverse-N1, 4 vCPUs, Python 3.13.2, Quart 0.54.0,
uvicorn 0.28.1. Tudo em loopback, sem TLS, sem autenticação, sem bot e sem
chamadas de rede. Medianas de 3 execuções de 8 s, quando não indicado.

### Tamanho dos frames

Payload SSE completo, incluindo `event:` e `data:` e o JSON, antes do
chunked framing do HTTP. Script: [frame_sizes.py](06-bench/frame_sizes.py).

| Frame | Bytes | Custo de encode |
| --- | ---: | ---: |
| `position` (progress) | 43 | 7,7 µs |
| `heartbeat` | 27 | 5,6 µs |
| delta de 1 token (ids ULID, x/y) | 153 | 5,6 µs |
| snapshot de mesa, 8 tokens com metadados | 1453 | 40,2 µs |
| snapshot compacto, 8 tokens (id, x, y) | ~630 no fanout |  |
| `status` de música, 5 na fila | 1601 | 58,9 µs |
| `presence` com 8 viewers | 1359 | 77,3 µs |

O payload de posição atual tem 19 B (`{"progress": 123.4}`), o que confere
com os ~20 B citados no ADR 0009 (`docs/adr/0009-panel-live-updates.md:58-59`).
O frame completo tem 43 B por causa do `event:` e do `data:`.

### SSE dedicado a 10 Hz

Servidor Quart + uvicorn real, um `Response` em streaming por conexão, um
frame de delta a cada 100 ms. Scripts: [sse_server.py](06-bench/sse_server.py),
[sse_bench.py](06-bench/sse_bench.py). Bytes contados no socket, incluindo
headers HTTP e chunked framing.

| Clientes | Frames | Bytes/frame | Total | CPU do servidor |
| ---: | ---: | ---: | ---: | ---: |
| 8 | 640 em 8 s (80/s) | 162 | 12,6 KiB/s | 0,75% de um core (94 µs/frame) |
| 32 | 2560 em 8 s (320/s) | 162 | 50,5 KiB/s | 2,50% de um core |
| 8, snapshot 1453 B | 640 em 8 s | 1463 | 114 KiB/s | 1,00% de um core |

Conexões ociosas custam 22,4 kB de RSS cada (delta com 64 conexões
abertas, sem tráfego). Oito conexões custam ~180 kB.

### Pior caso: 8 jogadores arrastando ao mesmo tempo

8 leitores SSE e 8 movers a 10 Hz, cada movimento publica um snapshot
compacto para todos os leitores, fila limitada a 32 como no sampler. Scripts:
[fanout_server.py](06-bench/fanout_server.py),
[fanout_bench.py](06-bench/fanout_bench.py).

| Leitores | Movers | Posts | Frames | Tráfego | CPU |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 8 | 0 | 0 | 8 (abertura) | 0,76 KiB/s | 0,25% |
| 8 | 1 | 80 em 8 s | 648 | 47,6 KiB/s | 1,62% |
| 8 | 8 | 640 em 8 s | 5128 | 394 KiB/s | 7,00% |
| 32 | 8 | 640 em 8 s | 20428 | 1,50 MiB/s | 13,25% |

Ou seja: a mesa inteira arrastando tokens a 10 Hz, com fanout para todos,
cabe em 7% de um core e 3,1 Mbit/s. O benchmark não inclui autenticação,
commit no SQLite nem TLS.

### Polling e POST de movimento

Script: [sse_bench.py](06-bench/sse_bench.py), modos `poll` e `move`. O POST
de movimento grava uma linha no SQLite com commit por requisição.

| Cenário | Requisições | Bytes/req | Tráfego | CPU |
| --- | ---: | ---: | ---: | ---: |
| Polling 10 Hz, 8 clientes | 640 em 8 s | 1471 | 115 KiB/s | 3,88% |
| Polling 1 Hz, 8 clientes | 64 em 8 s | 1471 | 11,5 KiB/s | ~0,5% (amostra curta) |
| POST move 10 Hz, 1 cliente | 80 em 8 s | 256 | 2,5 KiB/s | 1,62% (1,6 ms/req) |
| POST move 10 Hz, 8 clientes | 640 em 8 s | 256 | 20 KiB/s | 5,25% (0,66 ms/req) |

O polling a 10 Hz custa 5 vezes mais CPU e 9 vezes mais bytes que o SSE em
delta, porque cada resposta carrega a tabela inteira e os headers HTTP.
O POST de movimento com um commit por requisição custa 1,6 ms sozinho, na
mesma ordem do `touch` de presença medido abaixo.

### SQLite por tick

`SqliteRegistry` real contra um banco temporário, com as migrações do repo.
Script: [presence_bench.py](06-bench/presence_bench.py).

| Operação | Custo |
| --- | ---: |
| `touch` (3 upserts + commit) | 2,4 a 2,6 ms |
| `viewers` (join + limit 50) | 0,24 ms |
| `last_connection` | 0,13 ms |
| `presence()` completo | 2,7 a 2,9 ms |
| `user_guild_ids` | 0,135 ms |

Consequência: `presence()` a cada 5 s por stream custa 0,44% de um core com
8 streams, o que é aceitável. Se `TICK_SECONDS` caísse para 0,1 s, seriam 80
chamadas por segundo, 22% de um core, mais 1,1% em `user_guild_ids`, só para
manter o stream de música respirando. Não é o caminho.

## Comparação

| Dimensão | SSE dedicado por Table | WebSocket | Polling 10 Hz |
| --- | --- | --- | --- |
| Conexões, 8 jogadores | 8 | 8 | 8 keep-alive |
| Download, 8 jogadores | 12,6 KiB/s em delta, 114 KiB/s em snapshot | mesma ordem; header de 2 a 6 B contra ~9 B de chunk | 115 KiB/s |
| CPU do servidor | 0,75% em delta, 1,0% em snapshot | não medido; mesma ordem do SSE | 3,9% |
| Upload de movimento | POST separado, 1 req por movimento | mesmo socket, sem req por mensagem | POST separado |
| Limite do edge | 60 req/min por IP em `/api/`, bloqueia 10 Hz | 1 handshake por conexão, não limitado por mensagem | 60 req/min, bloqueia |
| Reconexão | nativa do browser + backoff atual | manual | manual |
| Resync | snapshot na abertura | snapshot na abertura | cada resposta é o estado |
| Custo de implementação | rota SSE + broadcaster | rota WS + cliente de reconexão/resync + Upgrade no NPM | rota GET + cliente de polling |
| Dependências | nenhuma nova | `websockets` e `wsproto` já estão no `pyproject.toml` | nenhuma nova |

O WebSocket não foi medido. O caminho ASGI por mensagem é o mesmo do SSE, e a
diferença de header é de poucos bytes. A vantagem dele está no upload sem
limite por requisição e na conexão única, não em vazão.

## Recomendação

1. **SSE dedicado por Table** para o download, uma conexão por jogador. Não
   passar frames de mesa pelo `GuildSampler` nem pelo `_steady_frames`: o
   tick de 5 s faz escrita de presença por stream e a fonte é o estado de
   música, não a mesa.
2. **Broadcaster em memória por Table**, no mesmo processo, no molde do
   `GuildSampler`. Cada assinante guarda o último estado, não uma fila
   profunda: posições são absolutas, então conflacionar é correto e um
   cliente lento só perde estados intermediários. Fila de 32 a 10 Hz dá 3,2 s
   de atraso antes de descartar; para posição, 1 slot basta.
3. **Frames**: snapshot completo na abertura e a cada 5 s (keyframe), delta
   com posições absolutas e `rev` monotônico no meio. O cliente que vê
   `rev` fora de sequência refaz o snapshot. `heartbeat` a cada 5 s para o
   watchdog de 15 s continuar valendo.
4. **Cadência**: enviar na mudança, coalescido a no máximo 10 Hz por Table,
   não por token. O custo medido é 0,75% de um core para 8 leitores.
5. **Upload**: POST em lote para `/api/tables/<id>/moves`, coalescido a no
   máximo 10 Hz por jogador, com commit no fim do drag e snapshot periódico,
   não a cada movimento. O limite de 60 req/min do NPM precisa de uma zona
   própria para esse caminho (por exemplo 600 r/m, burst 30), senão o
   arrasto toma 429 depois do burst de 10 e ainda derruba as outras chamadas
   do mesmo IP. Se mexer no edge não for aceitável, o upload fica em 1 Hz
   com interpolação no cliente, e a diferença de UX vira decisão do ticket
   07.
6. **WebSocket** só se o upload a 10 Hz for requisito e o limite do edge não
   puder mudar, ou se uma conexão única for preferida. A capacidade não
   exige. O custo é reimplementar reconexão/resync no cliente e habilitar
   `Upgrade` no NPM, que hoje só tem `proxy_http_version 1.1`
   (`deploy/npm/harpi-advanced.conf:22-30`).
7. **Polling a 10 Hz**: descartado. Custa 5 vezes mais CPU, 9 vezes mais
   bytes e esbarra no mesmo limite de 60 req/min.

## Riscos e ressalvas

- **Um processo**: broadcaster, `STREAM_SLOTS` e sampler são estado local.
  Múltiplos workers quebram contagem de slots e fanout. O deploy atual roda
  um worker (`Dockerfile:49`, `src/__main__.py:53-59`). O ADR 0009 já prevê
  um bus compartilhado se isso mudar (`docs/adr/0009-panel-live-updates.md:63-64`).
- **Teto por guild**: 20 streams por guild (`rate_limit.py:14`). Oito
  jogadores com painel e mesa abertos são 16, ainda cabe. Uma segunda aba com
  painel e mesa acrescenta 16, então 32 streams e doze recebem 429. O alerta
  de crescimento dispara em 15 (`src/alerts.py:43`), então uma mesa cheia com
  o painel aberto já alerta. Uma cota própria por Table, ou um teto maior
  para o stream da mesa, evita o cruzamento com o stream de música.
- **NAT**: o limite do NPM é por `$binary_remote_addr`. Jogadores atrás do
  mesmo IP dividem os 60 req/min, e reconexões e refetch de `/api/status`
  competem com os movimentos.
- **HTTP/1.1**: o browser limita 6 conexões por origem. Duas `EventSource`
  por aba deixam margem para 3 abas. Com HTTP/2 o teto é bem maior, mas o
  protocolo do edge não está fixado na config do repo.
- **Descarte silencioso**: `_publish` descarta o frame mais antigo sem
  marcar lacuna (`sampler.py:128-132`). Para deltas de mesa, `rev` ou
  conflação resolvem. Sem isso, um delta final descartado deixa o token
  parado até o próximo movimento.
- **Números de bancada**: loopback, sem TLS, sem autenticação, sem
  `guard_api` e sem o bot. Cada POST real ainda paga o SELECT de
  `login_epoch` em `guard_api` (`app.py:238-259`). Um POST de movimento sob
  o blueprint `api` ainda acordaria o sampler de música
  (`pages/api.py:48-61`), então a rota da mesa deve ficar em blueprint
  próprio.
- **Commit por movimento**: 1,6 ms por POST sozinho, 0,66 ms por POST quando
  oito clientes concorrem, 5,25% de um core no total. Commitar no fim do drag,
  como o ticket 07 já propõe, tira esse custo do caminho quente.

## Fontes

Código e configuração:

- `pages/events.py`
- `src/panel/sampler.py`
- `src/panel/rate_limit.py`
- `src/panel/schemas.py`
- `src/panel/state.py`
- `src/storage/registry.py`
- `src/storage/database.py`
- `src/alerts.py`
- `src/__main__.py`
- `app.py`
- `pages/api.py`
- `web/src/lib/sse.ts`
- `web/src/lib/playback-clock.ts`
- `docs/adr/0009-panel-live-updates.md`
- `docs/agents/architecture.md`
- `docs/agents/panel.md`
- `Dockerfile`
- `deploy/npm/harpi-advanced.conf`
- `deploy/npm/harpi-rate-limits-http.conf`

Bancada local, sem rede:

- [06-bench/frame_sizes.py](06-bench/frame_sizes.py)
- [06-bench/sse_server.py](06-bench/sse_server.py)
- [06-bench/sse_bench.py](06-bench/sse_bench.py)
- [06-bench/fanout_server.py](06-bench/fanout_server.py)
- [06-bench/fanout_bench.py](06-bench/fanout_bench.py)
- [06-bench/presence_bench.py](06-bench/presence_bench.py)

Comandos:

```
PYTHONPATH=. .venv/bin/python .scratch/vtt/research/06-bench/frame_sizes.py
.venv/bin/python .scratch/vtt/research/06-bench/sse_bench.py all
.venv/bin/python .scratch/vtt/research/06-bench/fanout_bench.py
PYTHONPATH=. .venv/bin/python .scratch/vtt/research/06-bench/presence_bench.py
```
