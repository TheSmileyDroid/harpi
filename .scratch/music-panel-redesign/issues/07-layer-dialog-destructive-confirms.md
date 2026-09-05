# 07: Dialogs — detalhe de camada + confirmações destrutivas

**What to build:** Clicar numa camada abre um `<dialog>` de detalhe com slider de volume da camada e botão de remover. Ações destrutivas (limpar fila, desconectar) ganham dialog de confirmação antes de executar. Dialogs estilizados na estética CRT (hud-panel, amber; vermelho só para o destrutivo).

**Blocked by:** 02 (side panel com abas é onde as camadas moram), 06 (reusa o padrão de slider/trilha).

**Status:** done

- [x] Clique na camada abre dialog: slider de volume da camada + remover.
- [x] Slider de camada sobrevive ao poller (mesmo cuidado do volume do transport).
- [x] Limpar fila e desconectar exigem confirmação em dialog antes de executar.
- [x] `<dialog>` nativo com fallback/estilização própria; fecha com Esc e clique fora.
- [x] Acessibilidade básica: foco preso ao dialog aberto, devolvido ao fechar.
- [x] Testes: abrir/fechar dialog, ação executada só após confirmação; `make check` verde.
