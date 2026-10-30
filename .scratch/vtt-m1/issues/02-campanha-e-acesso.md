# 02: Campanha e acesso

**What to build:** A Paratheos existe semeada e cada pessoa vê a campanha com o papel que tem: narrador, jogador, pendente ou espectador. O servidor decide o papel pelo Sheet e pela guild, nunca por uma coluna. Sem vault, as rotas de ficha respondem 503 e a mesa continua.

**Blocked by:** 01 — Casca e rotas. Precisa também da mudança do ticket 11 (`HARPI_VAULT_PATH`) commitada.

**Status:** resolved

- [x] A migração semeia `paratheos` com narrador e guild vindos de `HARPI_NARRATOR_ID` e `HARPI_GUILD_ID`, documentados no `.env.example`.
- [x] `GET /api/campaigns` e `GET /api/campaigns/<slug>` devolvem a campanha, o papel e a Table aberta, que é `null` até a mesa existir; fora do escopo é 404.
- [x] O papel sai de `members` mais o status do Sheet; aprovar ou arquivar muda o papel sem escrever em `members`.
- [x] A guild da campanha é conferida em toda rota; sair da guild derruba o acesso no login seguinte.
- [x] Sem vault, ficha, elenco, card e asset respondem 503 `vault_unavailable`; mesa, stream e rolagem seguem.
- [x] `POST`, `PATCH` e `DELETE` sem JSON e same-origin respondem 403.
- [x] Contrato regenerado e `make check` verde.
