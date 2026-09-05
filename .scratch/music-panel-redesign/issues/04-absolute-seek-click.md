# 04: Seek absoluto no clique

**What to build:** Clicar na barra de progresso move a posição da faixa para o ponto clicado. O endpoint passa a aceitar seek **absoluto** (posição-alvo em segundos) em vez do offset relativo ±s. O input numérico de seek some do transport.

**Blocked by:** 02 (transport no lugar definitivo; evita conflito de edição).

**Status:** done

- [x] Endpoint de seek aceita posição absoluta em segundos (rejeita NaN/inf como hoje; também rejeita fora de 0..duração).
- [x] Clicar em qualquer ponto da barra dispara um único seek absoluto para aquele ponto.
- [x] Input numérico de seek removido do transport.
- [x] Paridade com o Discord: o comando de seek continua funcionando (a mudaça é de painel; o backend compartilhado recebe a nova semântica de forma compatível com a superfície de comandos).
- [x] Testes: endpoint absoluto, clamps, validação; testes de seek existentes (`test_music_seek.py`) continuam verdes.
- [x] `make check` verde.
