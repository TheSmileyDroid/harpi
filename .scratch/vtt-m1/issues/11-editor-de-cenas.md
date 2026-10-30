# 11: Editor de cenas

**What to build:** O narrador desenha o mapa e a névoa no mesmo gesto: sala desenhada é zona. Ele cria salas, corta com a borracha, ajusta grid e rótulos e salva o molde com o SVG gerado.

**Blocked by:** 10 — Cenas: molde e galeria.

**Status:** ready-for-agent

- [ ] Arrastar com a ferramenta Sala cria uma sala; sobrepor parcialmente junta na mesma sala e encostar cria outra.
- [ ] Apagar corta só as células tocadas e pode abrir porta, buraco ou dividir a sala; desfazer restaura o estado anterior.
- [ ] Clique seleciona, clique no vazio desmarca, duplo clique foca o nome e Delete exclui; V, R, E e S funcionam.
- [ ] O inspetor edita célula, offset, grid visível, rótulo, `revealed` inicial e `fog_outside`.
- [ ] Salvar cena desenhada grava o SVG em `assets/` e mantém `image_path` apontando para ele.
- [ ] O editor não desenha névoa nem tokens vivos; mostra o resumo de uso e o atalho para a Mesa.
- [ ] Reabrir restaura o desenho; hash velho é conflito; o celular desenha e o teclado funciona.
- [ ] `make check` verde.
