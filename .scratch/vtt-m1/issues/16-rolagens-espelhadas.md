# 16: Rolagens espelhadas

**What to build:** Rolar `4dF` no painel posta a mensagem no canal e entra no log; rolar no canal entra no mesmo log. As duas superfícies leem igual e o log sobrevive ao restart.

**Blocked by:** 12 — Mesa: abrir, tokens e névoa; 14 — Stream da mesa.

**Status:** ready-for-agent

- [ ] O painel avalia, posta no canal pelo loop do bot, grava as linhas com o id da mensagem e então publica `table.roll`; falha do Discord é 502 e não grava.
- [ ] Expressão solta e `!d` no canal de uma mesa aberta gravam; fora disso nada muda; bot e webhook são ignorados.
- [ ] `N#` grava N linhas e uma mensagem; a mesma mensagem processada duas vezes grava uma; limites de expressão e dados respondem 422.
- [ ] O texto é congelado no formato do parser; a mensagem leva autor e cena, sem menção e sem escada; `scene_label` sobrevive à remoção da cena.
- [ ] `GET /rolls` pagina por `(created_at, id)` e recupera o log após reconexão e restart.
- [ ] O painel mostra campo e log com etiqueta PAINEL ou DISCORD; a chave trava durante o POST.
- [ ] A ponte `run_on_panel_loop` existe e o bot não usa a conexão SQLite fora do loop dela.
- [ ] `make check` verde.
