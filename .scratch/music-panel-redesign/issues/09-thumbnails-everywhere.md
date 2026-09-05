# 09: Thumbs na UI toda

**What to build:** Thumbnails visíveis: 40–56px nas linhas de busca, fila e camadas; **arte quadrada** grande no topo do now playing (título/uploader/duração abaixo dela). Thumbs 16:9 nativas exibidas como quadrado via crop (`object-fit: cover`).

**Blocked by:** 01 (thumbnail no domínio/payload), 02 (layout e abas no lugar).

**Status:** done

- [x] Linhas de busca, fila e camadas mostram thumb pequena à esquerda (40–56px).
- [x] Now playing mostra arte quadrada grande no topo, com metadados abaixo.
- [x] Crop quadrado sem distorção (`object-fit: cover`); placeholder discreto quando não há thumb.
- [x] Imagens carregam sem quebrar o poller (swaps de 2s não recarregam/re-piscam as imagens sem motivo).
- [x] Estética preservada: thumbs com borda/tratamento hud-panel, não "coladas".
- [x] Testes: presença das thumbs nos fragments, placeholder sem thumb; `make check` verde.
