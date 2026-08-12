# Remoção da API JSON de música

O painel opera por fragmentos HTMX que falam com a sessão via `run_on_bot_loop`; a API JSON de música de controle/status ficou sem nenhum consumidor. Decidimos removê-la — endpoints de controle/status e o endpoint combinado deprecated, junto dos modelos de request correspondentes — mantendo o read-model, os modelos de resposta e o endpoint de adicionar música: não existem duas superfícies HTTP paralelas para o mesmo verbo, e o painel é todo HTMX.

**Status**: accepted

**Considered Options**: manter a API JSON como superfície alternativa ao HTMX — rejeitado: duplicaria o caminho de playback e nenhum consumidor existia.

**Consequences**: qualquer novo consumidor HTTP de música nasce como fragmento HTMX; o conhecimento dos dados do painel vive na doc da gramática de dados do painel.
