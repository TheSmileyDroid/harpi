# Protótipo: UX da mesa no painel

Artefato descartável do ticket [UX da mesa no painel](../issues/10-ux-da-mesa.md). Não é produção: nada em `src/`, `pages/`, `web/` ou `app.py` foi tocado.

## Abrir

- Direto do disco: abra `index.html` no navegador.
- Ou sirva a pasta: `python3 -m http.server 8765` dentro de `.scratch/vtt/prototypes/10` e abra `http://localhost:8765/`.

## Navegar

- Barra inferior: `←` e `→` trocam a casca; NARRADOR, JOGADOR, PENDENTE e ESPECTADOR trocam o papel simulado.
- Parâmetros de URL: `?variant=A|B|C`, `?role=narrator|player|pending|spectator`, `?page=table|chars|sheet`, `?drawer=ir1s|sela|corvo|sac|vex`.
- Teclado: `N` passa o turno, `D` foca a rolagem, `Esc` fecha gaveta, setas trocam a variante. Token focado: setas movem uma célula, `Shift` mais setas movem cinco, `Enter` abre a ficha.

## O que dá para fazer

- Arrastar o token do próprio jogador (o narrador arrasta qualquer um) e ver a posição mudar no mapa.
- Clicar numa zona como narrador para revelar ou cobrir a névoa, e trocar de papel para ver o recorte do jogador.
- Passar, encerrar e abrir turno, com a rodada fechando quando todos agiram.
- Rolar `4dF`, `4dF+2` ou `3#d20+5`: a linha entra no log com a etiqueta de origem e o aviso de espelhamento.
- Abrir a ficha em gaveta durante a cena, marcar estresse e consequência, e ver a página Ficha inteira.
- Ver o pendente entrando pela faixa da Mesa e pelo fluxo de três passos em Personagens.
- Ver o espectador levando 404 em Personagens e Ficha.
- Testar 403 e 422: pendente tentando rolar, expressão inválida.

## As três cascas

- **B, rail de campanha:** rail fixo com páginas, cenas, quem está na mesa e link, mapa ao lado da coluna de turno, rolagem e log. Vencedora e padrão.
- **A, faixa de superfícies:** nav band no topo, sem rail.
- **C, mesa de condução:** mapa em tela cheia com dock de turno e rolagem.

A e C ficam no arquivo como registro da comparação. A decisão registrada no ticket usa só B.

## O que é falso

- Sem rede, sem SQLite, sem SSE: o estado vive na memória da página e zera ao recarregar.
- O mapa é um SVG de exemplo com as zonas do ticket 05, não a imagem real da cripta.
- O arrasto não faz POST; o commit é local. A gaveta, o log e a rolagem são simulações.
- A ficha usa dados de exemplo em português; o bloco `harpi-sheet` real não é lido.
