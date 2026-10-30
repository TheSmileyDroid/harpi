# VTT do Harpi — M1 em construção

Tickets de implementação do marco 1. O plano e as decisões estão em [`../vtt/spec.md`](../vtt/spec.md), com o glossário em [`../vtt/glossario.md`](../vtt/glossario.md) e o mapa em [`../vtt/map.md`](../vtt/map.md).

Os tickets estão numerados na ordem de dependência. Trabalhe a fronteira: qualquer ticket cujos bloqueadores estejam fechados pode começar. Todos começam `ready-for-agent`.

## Antes do 02

A mudança do ticket 11 em `src/config.py`, `.env.example`, `docker-compose.yml` e `tests/test_config.py` precisa estar commitada. O 02 acrescenta `HARPI_NARRATOR_ID` e `HARPI_GUILD_ID` no mesmo lugar.
