# 01: Casca e rotas

**What to build:** O painel ganha a casca B e as rotas por campanha, com a página de música intacta. O rail mostra campanha, páginas e o estado do link; abaixo de 56rem ele vira faixa no topo. As páginas existem como placeholders navegáveis e o build estático serve link direto.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [x] `/` renderiza a página de música atual, sem rail nem dock de VTT.
- [x] `/c/paratheos/mesa`, `/personagens`, `/ficha` e `/cenas` renderizam a casca com a página ativa marcada.
- [x] O rail mostra wordmark, campanha, páginas e link; abaixo de 56rem vira faixa no topo.
- [x] O build de produção serve `/c/...` direto, sem 404.
- [x] `DESIGN.md` ganha a seção de navegação e `make check` passa.
