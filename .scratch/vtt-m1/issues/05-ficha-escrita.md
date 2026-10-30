# 05: Ficha: escrita

**What to build:** Editar a ficha grava no vault de forma atômica, deixa backup e nunca perde prosa, comentário ou chave que o app não conhece. Se o arquivo mudou desde a leitura, o save é recusado com conflito.

**Blocked by:** 04 — Ficha: leitura.

**Status:** ready-for-agent

- [ ] A escrita usa temporário na mesma pasta, `flush`, `fsync` e `os.replace`; o arquivo final nunca é escrito direto.
- [ ] Antes de sobrescrever, a versão anterior vai para `data/vault-backups/<slug>/<harpi-id>/`, com 20 por arquivo.
- [ ] O patch troca só `tipo`, `harpi-*`, o bloco e as seções `## História` e `## Anotações`; o resto fica byte a byte.
- [ ] Marcar estresse, editar aspecto, consequência, extra e inventário grava e recarrega com o valor novo.
- [ ] A prosa do Sheet é editada só nas duas seções do app, com markdown canônico.
- [ ] `base_hash` velho responde 409, sem tocar no disco.
- [ ] YAML inválido continua somente leitura e nunca é sobrescrito.
- [ ] `make check` verde.
