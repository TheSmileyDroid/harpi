# 13: Turno e rodada

**What to build:** A mesa tem um turno aberto por vez e uma rodada que fecha quando o último token público age. O jogador encerra o próprio turno; o narrador conduz qualquer um.

**Blocked by:** 12 — Mesa: abrir, tokens e névoa.

**Status:** ready-for-agent

- [ ] No máximo um turno aberto por mesa e um turno por token por rodada.
- [ ] O narrador abre o turno de qualquer participante pendente; o jogador do turno passa ou encerra o próprio.
- [ ] Passar para quem já agiu responde 422; encerrar sem passar deixa a mesa sem turno.
- [ ] O último pendente encerra a rodada, `round` sobe e todos voltam a pendente; o narrador abre a próxima.
- [ ] Token oculto não participa; token criado no meio entra pendente; token que entra em zona revelada entra pendente; token removido tem o turno encerrado.
- [ ] Fechar a mesa encerra o turno e a rodada; reabrir começa uma rodada nova.
- [ ] O `N` para passar e o `Esc` funcionam sem disparar com o cursor num campo.
- [ ] `make check` verde.
