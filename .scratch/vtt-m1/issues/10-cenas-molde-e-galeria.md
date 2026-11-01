# 10: Cenas: molde e galeria

**What to build:** A página Cenas lista os mapas preparados em cartões e cria uma cena a partir de uma imagem do vault ou de um upload. O molde vive no vault e o save não sobrescreve em silêncio.

**Blocked by:** 05 — Ficha: escrita; 09 — Assets e imagens.

**Status:** resolved

- [x] A cena nasce com `source` `image` ou `sketch`, imagem, grid, zonas, névoa inicial e slug imutável.
- [x] A galeria mostra miniatura, nome, origem, número de áreas e estado de salvo; o último cartão cria cena.
- [x] Criar, listar e abrir cena são do narrador; jogador e espectador não recebem a lista nem o molde.
- [x] Salvar carrega o `blueprint_hash` de base e recusa com conflito quando o arquivo mudou no disco.
- [x] A escrita é atômica e o arquivo nunca é renomeado; mudar o nome da cena não muda o arquivo.
- [x] Salvar e reabrir o molde preserva zonas e rótulos; o hash de base detecta mudança no disco.
- [x] Contrato regenerado e `make check` verde.
