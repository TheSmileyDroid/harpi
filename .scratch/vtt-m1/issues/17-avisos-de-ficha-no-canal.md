# 17: Avisos de ficha no canal

**What to build:** Quando uma ficha entra em conflito, some do disco ou fica inválida, o canal da mesa recebe um aviso com o nome, os campos e o link. Resolver edita a mensagem, sem repostar.

**Blocked by:** 08 — Sync: merge e conflitos; 12 — Mesa: abrir, tokens e névoa.

**Status:** ready-for-agent

- [ ] Uma mensagem por ficha em conflito, mencionando dono da ficha e narrador, com nome, campos e link do painel.
- [ ] Uma mensagem por ficha `ausente` e uma por `invalido`, uma vez cada; merge silencioso não gera mensagem.
- [ ] Resolver edita a mensagem para "resolvido por <nome>"; cinco campos em conflito geram uma mensagem, não cinco.
- [ ] Sem mesa aberta no canal, nada é postado e o aviso aparece só no painel.
- [ ] `make check` verde.
