# Resolução de contexto por página

Cada página do painel resolve apenas o contexto que renderiza, por dispatch: um mapa `PAGE_RESOLVERS` (slice base + slices por página) que a rota de páginas mergeia — dashboard resolve status do servidor e info do bot; a página de música resolve só o seletor de guild/canal; settings nada. Os dados de música (fila, camadas, playback) não são resolvidos no render inicial: os fragmentos se auto-preenchem via polling HTMX. A projeção do estado da sessão em contexto do painel é função pura sobre o read-model, mantendo o seam `run_on_bot_loop` confinado no read-model.

**Status**: accepted

**Considered Options**: resolver tudo em toda página (como antes) — rejeitado: toda página pagava status do servidor (psutil) e dados de música que não usava; contexto lazy manual no WIP — tentado e descartado por ficar quebrado.

**Consequences**: a página de música mostra fila/playback até alguns segundos após o paint (latência do poll, 2-3s); novo dado de página entra como resolver no mapa, não no meio da rota.
