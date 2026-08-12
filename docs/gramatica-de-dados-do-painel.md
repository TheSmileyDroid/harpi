# Gramática de dados do painel

Fonte única de verdade dos dados que o painel renderiza: o que é cada campo,
de onde vem e quem o consome.  O painel é todo HTMX — os fragmentos se
auto-preenchem via polling e nenhuma página resolve dados de música.

## Read-model (src/api/music.py)

Projeção do snapshot da sessão (`SessionStatus`) em dados de resposta.
`get_music_data(guild_id)` cruza o loop do bot via `run_on_bot_loop`; o
`MusicStatusResponse` é o que a sessão expõe ao painel.

| Campo | Origem na sessão |
|---|---|
| `current_music` (title, duration, url, thumbnail, uploader) | faixa atual |
| `progress` (ms) | posição da faixa atual |
| `queue` (title, duration, url, thumbnail, uploader) | fila |
| `layers` (title, id, url, volume) | camadas |
| `is_playing` / `is_paused` | estado do voice client |
| `loop_mode` | modo de loop |
| `volume` | volume mestre |

Sem sessão: `MusicStatusResponse.empty()` (defaults).  Guild desconhecida:
`None`.

## Contexto de fragmento (src/api/panel_context.py)

`project_music_panel(status)` é função pura sobre o read-model — adiciona só o
que é renderização: `current_position` (progress em ms) e
`current_position_formatted` (`M:SS`).  `get_music_panel(guild_id)` faz o
bridge e projeta.  Os fragmentos consomem o mesmo contexto:

| Fragmento | Campos | Poll |
|---|---|---|
| `_music_queue.html` | queue, current_track, paused, guild_id | 3s |
| `_playback_controls.html` | current_track, paused, volume, loop_mode, current_position(_formatted), guild_id | 2s |
| `_music_layers.html` | layers, guild_id | 3s |
| `_server_status.html` | cpu_percent, memory_percent, memory_used, memory_total, bot_connected, bot_latency, guild_count, user_count, music_guilds, queue_total, uptime_formatted | 5s |

## Contexto de página (src/api/panel_context.py)

`PAGE_RESOLVERS` decide o que cada página resolve; `base_context` (nav_items,
bot_connected) é comum.  A página de música recebe o seletor
(guilds, selected_guild_id, selected_channel_id, channels, guild_id,
channel_id) mais os defaults estáticos dos fragmentos — nunca dados de música.

## Seletor de guild/canal

O endpoint `guild_select_channel` aplica **um passo por request**:

- mudança de guild (`guild_id`): salva na sessão e re-renderiza o seletor com
  os canais da guild (não conecta);
- mudança de canal (`channel_id`): conecta usando a guild da sessão e
  re-renderiza o seletor;
- bot não pronto: re-renderiza o seletor com o contexto (503).

`channel_id` da página vem do voice client ativo da guild selecionada
(bot conectado); o seletor mostra o canal conectado e o botão DISCONNECT.
