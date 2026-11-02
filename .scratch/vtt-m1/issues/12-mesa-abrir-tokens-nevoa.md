# 12: Mesa: abrir, tokens e névoa

**What to build:** O narrador abre a mesa no canal com uma cena; jogadores entram e veem só o recorte deles. Tokens aparecem no mapa, a névoa esconde zonas e a ficha abre em gaveta durante a cena.

**Blocked by:** 02 — Campanha e acesso; 03 — Personagens e cards; 10 — Cenas: molde e galeria.

**Status:** resolved

- [x] Só o narrador abre, com campanha, canal e cena; a segunda mesa na campanha ou no canal responde 409 com id, nome e canal da ativa.
- [x] Fechar grava o snapshot e só então marca `closed`; reabrir restaura o snapshot ou abre do SQLite com aviso.
- [x] Token guarda posição em células, tamanho, rótulo, dono, Personagem, cor e visibilidade; o narrador cria, posiciona e remove tokens.
- [x] O recorte de jogador esconde token invisível, token em zona oculta e token fora de zona quando `fog_outside` está ligado; o narrador vê tudo.
- [x] Revelar e cobrir zona por clique; o token que entra em zona revelada aparece na cena e revela o NPC na primeira vez.
- [x] Recarregar a cena reimporta por hash: zona com o mesmo `id` mantém a névoa viva, zona nova nasce oculta e zona removida perde a névoa.
- [x] O mapa serve a cena corrente, inclusive o SVG de cena desenhada; a gaveta de ficha, a faixa de pendente e a visão de espectador funcionam.
- [x] A galeria marca a cena em uso; a mesa funciona no celular, com mapa rolável e zoom, e o teclado alcança tokens e zonas.
- [x] `make check` verde.
