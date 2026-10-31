# 04: Ficha: leitura

**What to build:** Abrir uma ficha mostra o estado jogável inteiro — aspectos, perícias na escada, estresse, consequências, extras e inventário — e a página Ficha serve para ler fora da cena. YAML quebrado vira somente leitura com erro visível.

**Blocked by:** 02 — Campanha e acesso.

**Status:** resolved

- [x] O parser lê o bloco `harpi-sheet` e o `harpi-campaign`, valida rank na escada, perícia duplicada, trilhas e slots.
- [x] YAML inválido deixa a ficha somente leitura, com erro visível; o app não sobrescreve o bloco.
- [x] Dono e narrador recebem a ficha inteira; outro jogador recebe só o card público.
- [x] A página Ficha mostra aspectos, perícias por degrau, caixas, consequências, extras e inventário; arquivado é somente leitura e pendente lê e edita a própria, com banner.
- [x] Chaves desconhecidas não são descartadas pelo parser.
- [x] Contrato regenerado e `make check` verde.
