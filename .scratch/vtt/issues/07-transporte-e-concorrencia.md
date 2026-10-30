# Transporte e concorrência da mesa

Type: grilling
Status: resolved
Blocked by: 06

## Question

Qual transporte, cadência e formato de frame a mesa usa?

Decidir:

- SSE dedicado ou WebSocket.
- frame completo ou delta.
- frequência de posição, névoa e turno.
- commit do drag ao soltar.
- ordem e backpressure.
- reconexão e estado inicial.
- quantos viewers por Table e o que fazer no limite.

Resolução: decisão e ADR.

## Answer

SSE dedicado por Table no download, POST em lote no upload, delta absoluto com janela de revisão por assinante, coalescência a 10 Hz por Table e commit no fim do drag. WebSocket fica fora do M1. Base numérica: [Limites do SSE para a mesa](06-limites-do-sse.md).

### Transporte

- `GET /api/tables/<table_id>/events`, `text/event-stream`, blueprint próprio (`pages/tables.py`). Não passa por `pages/events.py`, pelo `GuildSampler` nem pelo tick de 5 s: `POLL_SECONDS = 0.5` e `TICK_SECONDS = 5.0` são caros demais como fonte da mesa (`src/panel/sampler.py:16`, `pages/events.py:49`).
- `TableBroadcaster` em memória, um por Table, em `src/panel/table_stream.py`, no molde do `GuildSampler`: nasce no primeiro assinante, morre com o último. O SQLite é a verdade viva (ticket 05); o broadcaster mantém a cópia em memória que alimenta os frames, nunca o contrário.
- Uma conexão por viewer, sem multiplexação. O cliente reaproveita o `EventSource` atual (`web/src/lib/sse.ts`), com backoff 1→30 s e watchdog de 15 s.
- Autenticação continua o `guard_api` (`app.py:248-259`). O blueprint não pode ser o `api`: o `after_request` de `pages/api.py:48-61` acorda o sampler de música em todo POST.

### Frames

Nomes com ponto, para não colidir com os frames de música (`status`, `position`, `heartbeat`).

| Evento | Conteúdo | Quando |
|---|---|---|
| `table.snapshot` | `stream_rev`, `table_id`, recorte da cena, quem está na mesa, drags ativos | abertura, troca de cena, keyframe de 5 s |
| `table.delta` | `from_stream_rev`, `stream_rev`, `scene_id`, entidades mudadas com estado absoluto, `removed` | na mudança, coalescido a 10 Hz |
| `table.viewers` | lista de quem está na mesa | entrada ou saída de viewer |
| `table.drag` | token, ator, início ou fim | começo, drop, queda, troca de cena |
| `sheet.changed` | `sheet_id`, `character_id`, `rev`, estado | mudança aceita de ficha |
| `table.roll` | definido no ticket 09 | rolagem aceita |
| `heartbeat` | vazio | 5 s |
| `table.closed` | motivo | fim da Table (gatilho no ticket 05) |

- O delta carrega o estado absoluto de cada entidade mudada, por `id`. Campos de token, zona e turno são os do schema do ticket 05. Este ticket fixa envelope, `stream_rev`, cadência, recorte e entrega.
- Snapshot custa ~1453 B com 8 tokens e o delta ~153 B por token na bancada do 06.
- Troca de cena manda `table.snapshot`, nunca um delta que substitua a cena.
- Rolagem é evento append-only e não entra na conflação de estado.

### Revisão, janela e recorte por assinante

- O contador do stream é o `stream_rev`, por Table, +1 por mudança aceita (movimento, névoa, turno) e em memória. Ele é separado dos revs de CAS do ticket 05 (`tables.rev`, `tokens.rev`, `scenes.rev`), que continuam valendo para edição estrutural.
- Cada delta leva `from_stream_rev` e `stream_rev`. O cliente aplica quando `from_stream_rev` bate com o `stream_rev` local, senão fecha e reconecta para pegar snapshot.
- O broadcaster guarda as últimas 512 mudanças por Table, o que cobre 5 s no pior caso de 8 arrastando a 10 Hz, e monta o delta de cada assinante a partir do `stream_rev` que ele já tem. Um viewer lento recebe um delta maior, nunca um buraco. Janela vencida vira snapshot.
- O `+1` contínuo não serve: a coalescência junta várias mudanças num frame. `from_stream_rev` torna a verificação exata com 8 arrastando.
- O frame é filtrado por assinante, com as regras de visibilidade do ticket 05: jogador não recebe token `visible: false`, token em zona não revelada, nem token fora de zona quando `fog_outside` é `true`. O narrador recebe tudo.
- Quando um token sai do recorte (ficou invisível ou foi removido), o delta leva `removed: [token_id]` para o cliente apagar. Entrada no recorte vem como entidade completa.
- Keyframe de 5 s reseta a janela e cobre cliente com estado corrompido.

### Cadência

| O quê | Quando |
|---|---|
| posição de token | na mudança, no máximo 10 Hz por Table, um frame por tick com tudo que está pendente |
| névoa | imediata |
| turno | imediato |
| keyframe | 5 s |
| heartbeat | 5 s |
| quem está na mesa | na mudança |
| commit no SQLite | no drop, a cada 5 s durante o arrasto, no `pagehide` |

- Sem tick fixo: mesa parada não gera frame de estado, só heartbeat.
- 10 Hz por Table, não por token: 8 tokens arrastando juntos continuam 10 frames/s por viewer, abaixo do pior caso medido de 7% de um core.

### Upload e commit

- `POST /api/tables/<table_id>/moves`, JSON com lote de movimentos, `drag_id` do arrasto e `final` no drop.
- O cliente coalesce a 10 Hz e mantém um POST em voo por drag. O próximo destino espera a resposta, então a ordem é a da conexão e o token nunca anda para trás.
- Resposta `200 {stream_rev}`. O estado chega pelo stream: a 10 Hz, devolver o snapshot custaria 14 kB/s por dragger e duas vias de estado.
- O movimento é a exceção ao CAS do ticket 05: o POST não carrega rev esperado e não responde 409, porque posição é amostra viva, não edição concorrente. `tokens.rev` continua subindo a cada movimento aceito. Edição estrutural (cena, névoa, turno, criação e atributos de token) mantém o CAS e o 409 por linha.
- `x`/`y` fora do mapa é `422`, como no ticket 05. O cliente prende o token às bordas durante o arrasto, então o 422 só aparece com cliente adulterado.
- Commit no SQLite no drop, segurança a cada 5 s durante o arrasto e `pagehide` com `keepalive`. O commit de 1,6 ms fica fora do caminho quente (`06-realtime.md`).
- Balde por usuário de 600 movimentos/min, no molde de `SEARCH_BUCKETS` (`pages/api.py:42-45`).
- 429 no meio do drag: o cliente cai para 1 Hz por 30 s, mostra rede limitada, continua mandando o destino e volta a 10 Hz ao fim do `Retry-After`. Nenhum movimento se perde.

### Ordem e backpressure

- Duas classes por assinante: um slot de estado (último `stream_rev` pendente) e uma fila de eventos append-only de 32.
- Estado mais novo substitui o antigo. Evento não é conflacionado.
- Fila de eventos cheia fecha o stream. O cliente reconecta, recebe `table.snapshot` e busca o log pelo endpoint do ticket 09. Nada é descartado em silêncio, ao contrário do `_publish` atual (`src/panel/sampler.py:128-132`).
- Nenhum viewer lento atrasa outro: o fanout é independente por assinante.

### Reconexão e estado inicial

- Toda conexão abre com `table.snapshot`, já filtrado para o viewer e adotado sem checar `stream_rev`. Não há `id:`, `Last-Event-ID` nem buffer de replay.
- Delta com `from_stream_rev` diferente do local fecha e reconecta na hora, sem esperar o backoff.
- Backoff 1, 2, 4 até 30 s e watchdog de 15 s iguais aos do painel (`web/src/lib/sse.ts:11-13`).
- `visibilitychange` e `online` forçam reconexão. O snapshot é o resync.
- O `stream_rev` não é persistido. Depois de restart, o broadcaster nasce vazio, o primeiro snapshot sai do SQLite, que é a verdade viva do ticket 05, e o cliente adota o contador novo.
- O snapshot de abertura carrega só a Table: a cena recortada, tokens visíveis, névoa, turno, quem está na mesa e drags. Log e ficha têm eventos e rotas próprios.

### Concorrência

- O servidor é o serializador do movimento. Aceito na ordem de chegada, `stream_rev` e `tokens.rev` novos, broadcast absoluto. Sem trava e sem 409 no caminho do move.
- O cliente ignora movimento remoto do token que ele mesmo arrasta e usa o preview local até o drop. O último drop vence e todos convergem.
- `table.drag` é aviso, não trava: token, ator e início/fim, renovado por cada movimento aceito, TTL de 3 s, encerrado no drop, no fim do stream e na troca de cena. Não bloqueia ninguém.
- Ficha: `sheet.changed` fino, com `sheet_id`, `character_id`, `rev` e `state` (`ok`, `conflito`, `ausente`, `invalido`, `desconhecido` do ticket 04). O painel busca o card pela rota que o ticket 08 autorizar. Ficha completa nunca entra no stream da mesa.

### Viewers e limite

- `TableStreamSlots` próprio: 16 streams por Table, 2 por usuário, contador separado do `STREAM_SLOTS` de música (`src/panel/rate_limit.py:13-14`) e fora do alerta de crescimento (`src/alerts.py:43`).
- No limite: 429 com `Retry-After: 30`. O painel mostra mesa cheia e tenta de novo em 30 s. O narrador vê a contagem no cabeçalho da Table.
- 16 cobre 8 jogadores com duas abas. O teto é do tamanho da mesa, não da guild, e não cruza com os 20 streams de música.
- A lista de quem está na mesa vem do conjunto de assinantes do broadcaster, em memória, sem `touch` no Registry. É conceito distinto do **Viewer** do painel e ganha termo próprio no glossário.

### Edge

- `location /api/tables/` em `deploy/npm/harpi-advanced.conf`, com zona própria `rate=600r/m burst=30`, mantendo `proxy_buffering off` e os timeouts de 1 h que já valem no server.
- O stream SSE usa a mesma location: é uma requisição por conexão, então 600/min cobre reconexão com folga.
- A zona é por IP. Oito jogadores atrás do mesmo NAT arrastando ao mesmo tempo somam 4800 req/min e tomam 429, o que a queda para 1 Hz absorve sem perder movimento.

### Um processo

Broadcaster, `stream_rev`, janelas e slots são estado local de processo, como o sampler (ADR 0009). O deploy roda um worker (`Dockerfile:49`, `src/__main__.py:53-59`). Múltiplos workers quebram a janela de `stream_rev` e a contagem de viewers, então o dia em que houver mais de um worker exige bus compartilhado, não só uma flag.

### Reconciliação com o ticket 05

O ticket 05 fechou `tables.rev`, `tokens.rev` e `scenes.rev` como revs de CAS e escreveu que "dois movimentos do mesmo token, o segundo perde". Este ticket mantém o CAS para edição estrutural, mas o caminho de movimento a 10 Hz não carrega rev esperado: o segundo movimento vence, porque é a posição mais recente. `tokens.rev` sobe a cada movimento aceito, então o CAS estrutural continua enxergando a linha mais nova. O ticket 12 ajusta essa linha do 05 ao escrever a spec.

### Fora deste ticket

- Schema de cena, token, zonas, turno e persistência: ticket 05.
- Quem pode mover qual token e quem vê qual card: ticket 08.
- Payload, deduplicação e retenção do log: ticket 09.
- Aparência, celular, teclado e visão do narrador: ticket 10.
- ADR e glossário: ticket 12. Conteúdo pronto para o ADR 0010 "Table live transport", com as decisões acima, os números do ticket 06 e a consequência de processo único.

### Glossário para o ticket 12

- **Table stream**: a conexão SSE de uma Table, uma por viewer.
- **Table presence**: quem está com o Table stream aberto, mantido em memória pelo broadcaster. Distinto de **Viewer**.
- **Table stream revision** (`stream_rev`): contador por Table do stream, +1 por mudança aceita, separado dos revs de CAS, não persistido.
- **Table frame**: `table.snapshot` ou `table.delta`, o estado da cena.
- **Token move**: uma mudança de posição aceita, coalescida a no máximo 10 por segundo por jogador.
- **Drag marker**: aviso efêmero de que alguém está com o token, TTL de 3 s, sem bloquear.
