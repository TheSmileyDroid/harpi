# 06: Volume slider

**What to build:** O volume do Transport vira um range slider estilizado na estética amber (trilha fina, mesma linguagem visual da barra de progresso), substituindo o input numérico. O texto de volume repetido no now playing é removido.

**Blocked by:** 02 (layout no lugar definitivo).

**Status:** done

- [x] Transport tem um slider de volume (0–2, passo fino) que aplica `set_volume` ao interagir (debounce/throttle para não fustigar o endpoint ao arrastar).
- [x] Slider segue o design system (amber, trilha fina, corner bracket no foco).
- [x] Slider sobrevive ao poller de 2s sem ser destruído no meio do arrasto (mesmo padrão de hx-preserve dos forms atuais).
- [x] Texto de volume no now playing removido.
- [x] Testes: set de volume pelo slider, sobrevivência ao poller; `make check` verde.
