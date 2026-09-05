# 01: Thumbnails no domínio (prefactor)

**What to build:** O `YTMusicData` expõe a URL de thumbnail de cada faixa, e o painel (status, fila, busca) já a recebe serializada. Nada muda visualmente ainda — esta é a prefatoração que destrava as thumbs na UI.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] `YTMusicData` tem uma propriedade de thumbnail que escolhe a melhor thumb razoável (resolução média, ~320–480px) da lista do dict yt-dlp; fallback seguro quando a lista vier vazia.
- [x] Queue, now playing, search results e layers carregam a thumbnail no payload serializado.
- [x] Testes cobrem: escolha de resolução, fallback sem thumbnails, presença no payload.
- [x] `make check` verde.
