# 08: Toasts amber

**What to build:** O `#toast-container` (que hoje existe vazio no layout) ganha vida: confirmações transitórias em amber aparecem e desaparecem sozinhas — adicionado à fila, virou camada, volume alterado, seek aplicado. Nunca verde. O `panel_error` vermelho persistente permanece exatamente como é.

**Blocked by:** 02 (ações no lugar definitivo).

**Status:** done

- [x] Toast aparece para: add à fila, virar camada, volume alterado, seek aplicado (extensível para outras confirmações).
- [x] Toast some sozinho (alguns segundos); múltiplos toasts empilham sem se sobrescrever.
- [x] Toast é amber, nunca verde; nunca usado para erro (erro segue no panel_error persistente).
- [x] Toast sobrevive/convive com os pollers sem ser apagado por swap alheio.
- [x] Bot offline/falha não vira toast — só confirmações de ação bem-sucedida.
- [x] Testes: toast em sucesso, nenhum toast em erro; `make check` verde.
