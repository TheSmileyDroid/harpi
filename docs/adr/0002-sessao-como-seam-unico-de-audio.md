# Sessão como seam único de áudio

`PlaybackSession` é a dona única do áudio de uma guild — fila, camadas e conexão de voz — e todo verbo de playback (painel e comandos do Discord) passa por ela, cruzando o loop do bot apenas pelo bridge `run_on_bot_loop`. Substituiu os serviços legados de fila e conexão de voz; a API JSON de música morreu por isso (ver ADR-0001).

**Status**: accepted

**Consequences**: Quart e o bot rodam em loops diferentes — chamar a sessão de um handler sem `run_on_bot_loop` trava; código novo de áudio entra na sessão, nunca em serviço paralelo.
