# 06: Criação e aprovação

**What to build:** Um jogador cria o próprio par Character/Sheet e espera a aprovação do narrador. Aprovar muda o papel na hora; recusar devolve com a nota. O narrador cria NPC direto, sem fila.

**Blocked by:** 05 — Ficha: escrita.

**Status:** ready-for-agent

- [ ] Criar personagem grava Character e Sheet `pendente`, cria a linha em `members` e a entrada `pending` em `approvals`.
- [ ] O dono lê e edita a ficha pendente; outros jogadores não veem nada; o narrador vê na fila.
- [ ] Aprovar grava `ativo` nos dois arquivos e só então fecha a linha; falha no vault deixa `pending` e erro visível.
- [ ] Recusar mantém `pendente` e grava a nota; reenviar limpa a nota.
- [ ] Segundo Sheet `pendente` ou `ativo` responde 409.
- [ ] NPC nasce `ativo` e não passa pela fila; Sheet de NPC é opcional.
- [ ] Arquivar tira do elenco e do card e rebaixa o papel; desarquivar devolve.
- [ ] `make check` verde.
