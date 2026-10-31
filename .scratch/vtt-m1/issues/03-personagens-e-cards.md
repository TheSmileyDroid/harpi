# 03: Personagens e cards

**What to build:** A página Personagens lista o elenco que o jogador pode ver: PCs ativos e NPCs revelados, cada um com o card público. O narrador vê todos. O retrato vem do vault, sem copiar arquivo.

**Blocked by:** 02 — Campanha e acesso.

**Status:** resolved

- [x] O índice do vault nasce no boot e é atualizado pela varredura de 60 s; nenhuma rota lista diretório.
- [x] O elenco mostra PCs `ativo` e NPCs revelados; ficha pendente de outro jogador não aparece, nem o nome; arquivado sai.
- [x] O card público tem nome, retrato, conceito e resumo, sem campo mecânico.
- [x] O retrato resolve frontmatter e primeiro embed, com allowlist, raiz conferida por `realpath`, cache privado e 404 sem dizer o motivo.
- [x] Personagens renderiza para jogador e narrador; espectador recebe 404.
- [x] Contrato regenerado e `make check` verde.
