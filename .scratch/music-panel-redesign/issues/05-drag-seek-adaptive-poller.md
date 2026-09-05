# 05: Arrastar o seek + poller adaptativo

**What to build:** A barra de progresso aceita arrastar: durante o arrasto, a barra mostra o **preview** do tempo-alvo (sem tocar no backend); ao soltar, um único seek absoluto é aplicado. O poller do transport fica adaptativo: ~500ms enquanto toca (barra fluida), 2s quando pausado.

**Blocked by:** 04 (seek absoluto e barra clicável já existem).

**Status:** done

- [x] Arrastar mostra preview do tempo-alvo (estilo `01:23 / 04:05`) sem chamadas de seek durante o arrasto.
- [x] Soltar dispara exatamente um seek absoluto (nada de seek contínuo — seek reinicia o FFmpeg e a regra é música não morre enquanto toca).
- [x] Poller do transport: ~500ms tocando, 2s pausado; troca de intervalo não derruba o poller nem trips o global indicator (regra de poller silencioso do design.md).
- [x] Teste Playwright de poller × controles interativos continua verde; novos testes cobrem o seek-no-soltar.
- [x] `make check` verde.
