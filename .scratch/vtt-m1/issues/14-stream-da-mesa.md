# 14: Stream da mesa

**What to build:** A mesa ao vivo chega por um stream próprio: abertura com snapshot, mudanças por delta, keyframe e roster. Quem cai volta com o estado inteiro, e quem não é narrador recebe o mesmo recorte de jogador.

**Blocked by:** 08 — Sync: merge e conflitos; 12 — Mesa: abrir, tokens e névoa; 13 — Turno e rodada.

**Status:** resolved

- [x] A conexão abre com `table.snapshot` recortado e recebe `table.delta` com `from_stream_rev` e `stream_rev`.
- [x] O broadcaster guarda 512 mudanças, coalesce posição a 10 Hz, manda keyframe e heartbeat de 5 s e não gera frame com a mesa parada.
- [x] Dois recortes, jogador e narrador; `sheet.changed` chega só ao dono e ao narrador.
- [x] O roster mostra nome e papel, nunca snowflake; 16 streams por mesa e 2 por usuário, com 429 e `Retry-After`.
- [x] O cliente reconecta com backoff e watchdog e adota o snapshot; a recuperação do log fica na rolagem.
- [x] Troca e recarga de cena mandam snapshot; `table.closed` encerra o stream.
- [x] O edge ganha a zona de `/api/tables/`; nada passa pelo sampler de música.
- [x] `make check` verde.
