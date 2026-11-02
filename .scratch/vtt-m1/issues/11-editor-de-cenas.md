# 11: Editor de cenas

**What to build:** O narrador desenha o mapa e a névoa no mesmo gesto: sala desenhada é zona. Ele cria salas, corta com a borracha, ajusta grid e rótulos e salva o molde com o SVG gerado.

**Blocked by:** 10 — Cenas: molde e galeria.

**Status:** resolved

- [x] Arrastar com a ferramenta Sala cria uma sala; sobrepor parcialmente junta na mesma sala e encostar cria outra.
- [x] Apagar corta só as células tocadas e pode abrir porta, buraco ou dividir a sala; desfazer restaura o estado anterior.
- [x] Clique seleciona, clique no vazio desmarca, duplo clique foca o nome e Delete exclui; V, R, E e S funcionam.
- [x] O inspetor edita célula, offset, grid visível, rótulo, `revealed` inicial e `fog_outside`.
- [x] Salvar cena desenhada grava o SVG em `assets/` e mantém `image_path` apontando para ele.
- [x] O editor não desenha névoa nem tokens vivos; mostra o resumo de uso e o atalho para a Mesa.
- [x] Reabrir restaura o desenho; hash velho é conflito; o celular desenha e o teclado funciona.
- [x] `make check` verde.
