# 08: Sync: merge e conflitos

**What to build:** Quando o painel e o Obsidian mudam a mesma ficha, o merge é por campo e por rótulo. Campo mexido dos dois lados vira conflito visível, o disco fica intocado e a ficha vira somente leitura até a decisão.

**Blocked by:** 07 — Sync: mudanças entram.

**Status:** resolved

- [x] O merge de três vias usa a última versão aceita como base e identifica item por rótulo, nunca por posição.
- [x] Só o vault mudou: aceita. Só o painel mudou: grava. Nenhum mudou: nada. Mesmo valor nos dois: aceita. Valores diferentes: conflito no campo.
- [x] O conflito mostra base, vault e painel e oferece usar do vault, usar do painel e, em texto, manter os dois.
- [x] Manter os dois cria um item novo com o rótulo repetido; nunca concatena.
- [x] Resolver grava uma vez, com rev novo e backup, e volta para `ok`.
- [x] Arquivo ausente oferece restaurar ou esquecer; o app nunca restaura sozinho.
- [x] Enquanto houver conflito, a ficha é somente leitura, inclusive para o dono.
- [x] `make check` verde.
