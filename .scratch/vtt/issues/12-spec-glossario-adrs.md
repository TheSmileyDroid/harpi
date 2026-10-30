# Spec, glossário e ADRs do M1

Type: task
Status: resolved
Blocked by: 02, 03, 04, 05, 07, 08, 09, 10, 11, 13

## Question

Consolidar as decisões em `spec.md`, atualizar `CONTEXT.md` e escrever os ADRs do M1.

Inclui:

- spec do M1 com escopo, fluxos, rotas, esquema, estados e critérios de aceite.
- glossário: Table, Scene, Campaign, Character, Sheet, Atlas, Content source, Narrator, Player, PC, NPC, Public card.
- ADRs: armazenamento por campanha, sync do vault, transporte da mesa, autorização por campanha, formato da ficha.
- checklist de aceite jogável: abrir Table, carregar Scene, mover token, revelar zona, rolar `4dF`, editar ficha, salvar no vault, reiniciar e retomar.
- riscos e o que fica para M2 e M3.

Resolução: spec e docs commitados.

## Answer

Entregues quatro artefatos:

- [`.scratch/vtt/spec.md`](../spec.md): spec do M1 em 15 seções — escopo, base fixa, modelo de domínio, armazenamento, esquema SQLite emendado, ficha, mesa, editor de cenas, rotas, estados, painel, critérios de aceite, riscos, M2/M3 e ordem de implementação em 9 fatias.
- `CONTEXT.md`: quatro seções novas no glossário (Campaign content, Characters and sheets, Table, Access), cobrindo os 12 termos do ticket mais os que os tickets 03, 07, 08, 09, 10 e 13 pediram para registrar.
- [`.scratch/vtt/glossario.md`](../glossario.md): espelho em português do glossário de VTT, para conversa e interface, com os rótulos finais (Narrador, Na mesa, Áreas, Origem da cena).
- `docs/adr/0010` a `0014`: Table live transport; Campaign state lives in SQLite with authored and snapshot copies in the vault; Sheet sync with the vault by hash and three-way merge; Campaign authorization derived from sheets with two stream cutouts; Fate sheet as a fenced YAML block plus campaign config.

### Consolidado sem redecidir

- Esquema SQLite com as emendas já fechadas: `tables.spectators`, `character_visibility`, `rolls.scene_label`, `scenes.source`, `sheet_files.status` e `owner_id`, e `campaigns.content_source`.
- Reconciliações registradas na spec: movimento sem CAS e último drop vence (07 sobre 05); dois recortes de stream, jogador e narrador (08 sobre 07); participante do turno é o token público (10 sobre 05); recarga explícita de cena e cena desenhada em SVG (13 sobre 05); prosa do Sheet e do Character do app (08 sobre 02, 03 e 04).
- Checklist jogável com os oito passos pedidos: abrir Table, carregar Scene, mover token, revelar zona, rolar `4dF`, editar ficha, salvar no vault, reiniciar e retomar.

### Lacunas preenchidas

- Nomes das rotas que os tickets citaram sem batizar: abrir, fechar e reabrir Table; recarregar cena; cobrir zona (`hide`); `PATCH` de token.
- `GET /api/campaigns/<slug>` devolve a Table aberta, porque nenhum ticket dizia como o jogador descobre o id da mesa.
- `sheet_conflicts.id`, que a rota `POST .../conflicts/<id>/resolve` exigia e a tabela do ticket 04 não tinha.
- SVG de cena desenhada como exceção ao allowlist de raster: gerado pelo servidor, servido só pela rota do mapa, com `nosniff` e CSP de sandbox.
- `source` no JSON do molde, além da coluna, para a reimportação do disco não perder a distinção entre imagem e desenho.

### Pendente

- `DESIGN.md` ainda precisa das três seções que o ticket 10 apontou (navegação, Table map, mesa sem o dock da música). Ficou como fatia 9 da ordem de implementação, fora do escopo deste ticket.

### Fora deste commit

- As mudanças do ticket 11 em `src/config.py`, `docker-compose.yml`, `.env.example` e `tests/test_config.py` seguem não commitadas e não entraram neste commit.

