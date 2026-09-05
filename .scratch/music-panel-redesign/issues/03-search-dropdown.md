# 03: Busca com dropdown overlay

**What to build:** Digitar na busca única abre um **overlay dropdown** sob o input: cada linha mostra thumb, título, uploader, duração e botões `QUEUE`/`LAYER` direto na linha. Fecha com Esc, clique fora ou nova busca. Teclado: ↑/↓ navega, Enter seleciona. URL colada é detectada e vai direto à fila sem abrir dropdown.

**Blocked by:** 01 (thumbnails no domínio), 02 (busca no topo, painel antigo removido).

**Status:** done

- [x] Resultados aparecem como overlay (não empurram conteúdo); competem visualmente com o design amber (hud-panel, corner brackets).
- [x] Linha: thumb + título + uploader + duração + botões QUEUE/LAYER explícitos (paridade com o Discord).
- [x] Fecha com Esc e clique fora; abre de novo ao buscar.
- [x] ↑/↓ + Enter selecionam uma linha.
- [x] URL colada: sem dropdown, vai direto à fila.
- [x] Dropdown não morre com os pollers de 2s (hx-preserve ou re-render estável).
- [x] Ações da linha mantêm o comportamento existente (add → fila; add_layer → layer) com toast de confirmação quando existir.
- [x] Testes: render das linhas, URL detection, fechamento; `make check` verde.
