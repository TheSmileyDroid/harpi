# 02: Layout estrutural (grid + side panel)

**What to build:** A página Music vira grid: no desktop, conteúdo principal + now playing na coluna esquerda e um **Side panel** com abas `QUEUE | LAYERS` à direita; no mobile, coluna única (busca → now playing → abas → transport fixo). O "00 // LINK" vira uma linha compacta no topo, com a busca logo abaixo dele. O painel "04 // SEARCH" e o quick-add dentro da fila morrem — a busca passa a ser única e mora no topo (os resultados ainda aparecem inline nesta etapa; o dropdown é outro ticket).

**Blocked by:** None (can start immediately).

**Status:** done

- [x] Desktop: grid de 2 colunas; mobile: coluna única na ordem busca → now playing → abas → transport.
- [x] Side panel com abas `QUEUE | LAYERS` funcionais (troca de aba não perde estado da sessão).
- [x] "00 // LINK" compacto: guild + canal + connect na mesma linha, desconect incluído.
- [x] Só existe uma busca na página, no topo; os dois inputs antigos não existem mais.
- [x] Estética amber CRT preservada (hud-panel, corner brackets, Rajdhani nos títulos).
- [x] Testes de rota atualizados: fragments por HX-Target continuam funcionando, actions de search/add continuam; testes dos blocos removidos atualizados.
- [x] Pollers (status_panels/transport) não destroem controles interativos (teste Playwright existente continua verde).
- [x] `make check` verde.
