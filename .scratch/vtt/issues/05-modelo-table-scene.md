# Modelo de Table e Scene

Type: grilling
Status: resolved

## Question

Qual é o estado de uma Table e de uma Scene, e onde ele persiste?

Decidir:

- uma Table ativa por campanha e uma por canal; o que acontece ao abrir a segunda.
- tabelas SQLite: campaigns, members, tables, scenes, tokens, turns, rolls, approvals.
- JSON da Scene: imagem, grid, zonas (retângulos), névoa por zona, tokens.
- token: posição, tamanho, rótulo, dono, link para Character, cor, visível.
- turno livre, quem avança, quem encerra.
- snapshot ao fechar e restauração após restart.
- o que é estado vivo (SQLite) e o que é arquivo (JSON).
- como o aligner salva `Harpi/Campaigns/<slug>/maps/<scene>.json`.

Resolução: schema, JSON de exemplo, ciclo de vida e regras de concorrência.

## Answer

SQLite é a verdade viva da Table e da Scene durante a sessão. O vault guarda dois artefatos diferentes: o molde autoral da cena em `scenes/` e o snapshot da mesa em `tables/`. Uma Table aberta por campanha e uma por canal, garantidas por índice único parcial. A rodada é um ciclo de turnos, um turno por token da cena, com passe só para quem ainda não agiu.

Mapa dentro de mapa, com cenas localizáveis num mapa maior, é o Atlas do M2. O M1 não tem relação pai/filho entre cenas nem pino de cena. O caminho `maps/<scene>.json` que aparecia na pergunta foi corrigido para `scenes/<slug>.json` e `tables/<table-id>.json`, como já fixavam o ticket 03 e o mapa.

### 1. O que é estado vivo e o que é arquivo

| Onde | Guarda | Quem escreve |
|---|---|---|
| SQLite (`HARPI_DB_PATH`, o mesmo banco do painel) | campanhas, membros, mesas, cópia viva das cenas, tokens, turnos, rolagens, aprovações | app |
| `Harpi/Campaigns/<slug>/scenes/<scene>.json` | molde da cena: imagem, grid, zonas, névoa inicial. Sem tokens | app, quando o narrador salva a cena |
| `Harpi/Campaigns/<slug>/tables/<table-id>.json` | snapshot do estado vivo: cena corrente com névoa, tokens, turno e rodada | app, periódico e no fechamento |
| imagem citada pela cena | o arquivo original onde ele já está, inclusive `Recursos/anexos` | ninguém copia |

- A cena é preparada antes da sessão e vive no vault. O narrador pode ter várias cenas prontas e escolher uma para a Table ativa. A escolhida vira o mapa.
- Trocar de cena com a Table aberta carrega outra cena. Os tokens são por Table e por cena, então voltar a uma cena anterior devolve os tokens e a névoa dela.
- O app nunca renomeia, move nem apaga arquivo. Sobrescrever o snapshot de forma atômica é permitido; apagar não.
- O molde não tem tokens. Token só existe na mesa. Para repetir um combate, o narrador coloca os tokens de novo; para preparar o mapa, basta imagem, grid e zonas.

### 2. Atlas e mapa dentro de mapa

Fica fora do M1 e já está em Out of scope do mapa: Atlas em Canvas e navegação de mapas aninhados são marco 2, com viewer somente leitura no M2 e editor no M3. O schema da cena não tem `parent_scene_id`, nem `atlas_id`, nem pino. O único mapa do M1 é a imagem da cena ativa.

### 3. Ciclo da Table

`tables.status` é `open` ou `closed`.

- **Abrir**: só o narrador abre, escolhendo campanha, canal de texto e cena. A Table nasce `open`, `round = 1`, sem turno aberto.
- **Segunda Table**: os índices únicos parciais em `campaign_slug` e em `channel_id` quando `status='open'` barram. O app devolve `409 table_already_open` com id, nome e canal da Table ativa. Nada fecha sozinho. O narrador fecha a ativa e abre a outra.
- **Uma por canal**: um canal pode acumular Tables fechadas, mas só uma aberta. O índice é global no canal, então duas campanhas no mesmo canal também colidem.
- **Fechar**: encerra o turno aberto, fecha a rodada corrente, grava o snapshot e só então marca `closed`. Se o snapshot falhar, a Table continua `open` e o erro aparece; um `closed` sem snapshot não existe.
- **Reabrir**: só o narrador. Table `closed` restaura o snapshot e volta a `open`. Se o snapshot estiver inválido ou ausente, abre do SQLite com aviso, sem apagar nada.
- **Crash**: a Table fica `open`. No boot, o SQLite está mais novo que qualquer snapshot periódico e é ele que vale. O narrador retoma ou fecha a Table órfã. Não há restauração automática de snapshot sobre estado vivo.
- **Jogador**: entra e vê a Table ativa; não abre, não fecha, não reabre. A matriz de rotas fica no ticket "Autorização e arquivos".

### 4. Schema SQLite

Uma migração nova depois das existentes, no mesmo banco do painel. O número fica para a implementação, para não colidir com a migração do sync do vault. Timestamps em segundos epoch; booleanos em `INTEGER` com `CHECK (x IN (0,1))`; ids opacos com prefixo. Campanha usa o slug como chave, igual ao `harpi-campanha`.

```sql
CREATE TABLE campaigns (
    slug TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    narrator_id TEXT NOT NULL,
    system TEXT NOT NULL DEFAULT 'fate',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE members (
    campaign_slug TEXT NOT NULL REFERENCES campaigns(slug) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    display_name TEXT,
    joined_at INTEGER NOT NULL,
    PRIMARY KEY (campaign_slug, user_id)
);

CREATE TABLE tables (
    id TEXT PRIMARY KEY,
    campaign_slug TEXT NOT NULL REFERENCES campaigns(slug) ON DELETE CASCADE,
    channel_id TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open', 'closed')),
    current_scene_id TEXT REFERENCES scenes(id) ON DELETE SET NULL,
    round INTEGER NOT NULL DEFAULT 1 CHECK (round >= 1),
    rev INTEGER NOT NULL DEFAULT 1,
    opened_by TEXT NOT NULL,
    opened_at INTEGER NOT NULL,
    closed_by TEXT,
    closed_at INTEGER,
    snapshot_path TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE UNIQUE INDEX tables_one_open_per_campaign
    ON tables (campaign_slug) WHERE status = 'open';

CREATE UNIQUE INDEX tables_one_open_per_channel
    ON tables (channel_id) WHERE status = 'open';

CREATE TABLE scenes (
    id TEXT PRIMARY KEY,
    campaign_slug TEXT NOT NULL REFERENCES campaigns(slug) ON DELETE CASCADE,
    name TEXT NOT NULL,
    blueprint_path TEXT NOT NULL,
    blueprint_hash TEXT NOT NULL,
    image_path TEXT NOT NULL,
    image_width INTEGER NOT NULL CHECK (image_width > 0),
    image_height INTEGER NOT NULL CHECK (image_height > 0),
    grid_json TEXT NOT NULL,
    zones_json TEXT NOT NULL,
    fog_outside INTEGER NOT NULL DEFAULT 0 CHECK (fog_outside IN (0, 1)),
    rev INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    UNIQUE (campaign_slug, blueprint_path)
);

CREATE TABLE tokens (
    id TEXT PRIMARY KEY,
    table_id TEXT NOT NULL REFERENCES tables(id) ON DELETE CASCADE,
    scene_id TEXT NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    character_id TEXT,
    label TEXT NOT NULL,
    owner_id TEXT,
    x REAL NOT NULL,
    y REAL NOT NULL,
    w INTEGER NOT NULL DEFAULT 1 CHECK (w > 0),
    h INTEGER NOT NULL DEFAULT 1 CHECK (h > 0),
    color TEXT NOT NULL,
    visible INTEGER NOT NULL DEFAULT 1 CHECK (visible IN (0, 1)),
    rev INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE INDEX tokens_by_table_scene ON tokens (table_id, scene_id);
CREATE INDEX tokens_by_owner ON tokens (table_id, owner_id);

CREATE TABLE turns (
    id TEXT PRIMARY KEY,
    table_id TEXT NOT NULL REFERENCES tables(id) ON DELETE CASCADE,
    scene_id TEXT NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    round INTEGER NOT NULL CHECK (round >= 1),
    token_id TEXT REFERENCES tokens(id) ON DELETE SET NULL,
    character_id TEXT,
    label TEXT NOT NULL,
    started_at INTEGER NOT NULL,
    ended_at INTEGER,
    started_by TEXT NOT NULL,
    ended_by TEXT,
    CHECK (ended_at IS NULL OR ended_at >= started_at)
);

CREATE UNIQUE INDEX turns_one_open_per_table
    ON turns (table_id) WHERE ended_at IS NULL;

CREATE UNIQUE INDEX turns_one_per_token_round
    ON turns (table_id, scene_id, token_id, round)
    WHERE token_id IS NOT NULL;

CREATE INDEX turns_by_table_round ON turns (table_id, round, started_at);

CREATE TABLE rolls (
    id TEXT PRIMARY KEY,
    table_id TEXT NOT NULL REFERENCES tables(id) ON DELETE CASCADE,
    scene_id TEXT REFERENCES scenes(id) ON DELETE SET NULL,
    turn_id TEXT REFERENCES turns(id) ON DELETE SET NULL,
    actor_id TEXT,
    actor_label TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('panel', 'discord')),
    expression TEXT NOT NULL,
    total INTEGER NOT NULL,
    dice_json TEXT NOT NULL,
    text TEXT NOT NULL,
    discord_message_id TEXT,
    created_at INTEGER NOT NULL
);

CREATE UNIQUE INDEX rolls_one_per_discord_message
    ON rolls (discord_message_id)
    WHERE discord_message_id IS NOT NULL;

CREATE INDEX rolls_by_table ON rolls (table_id, created_at, id);

CREATE TABLE approvals (
    id TEXT PRIMARY KEY,
    campaign_slug TEXT NOT NULL REFERENCES campaigns(slug) ON DELETE CASCADE,
    sheet_path TEXT NOT NULL,
    sheet_id TEXT,
    character_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')),
    note TEXT NOT NULL DEFAULT '',
    requested_by TEXT NOT NULL,
    requested_at INTEGER NOT NULL,
    decided_by TEXT,
    decided_at INTEGER
);

CREATE UNIQUE INDEX approvals_one_pending_per_sheet
    ON approvals (campaign_slug, sheet_path)
    WHERE status = 'pending';

CREATE INDEX approvals_by_campaign_status
    ON approvals (campaign_slug, status, requested_at);
```

- `members` guarda só jogadores. O narrador é `campaigns.narrator_id`. Co-narrador fica fora do M1.
- `campaigns` tem uma linha semeada para `paratheos`; criação de campanha é M2.
- `scenes` é a cópia viva do molde. `grid_json` e `zones_json` são lidos e gravados inteiros; o resto é normalizado.
- `tokens` não tem FK para o vault. `character_id` e `owner_id` são referências lógicas; o Character pode ser uma nota do vault sem id, e aí o token usa só `label`.
- `rolls` e `approvals` são SQLite puro; o snapshot não os carrega. O formato e a retenção das rolagens ficam no ticket "Rolagens espelhadas".
- `approvals` é fila e auditoria. O `harpi-status` do Sheet continua sendo a verdade, como no ticket 03. Aprovar grava os dois arquivos e depois a linha; se a gravação no vault falhar, a linha fica `pending` e o erro aparece.

### 5. Molde da cena

`Harpi/Campaigns/paratheos/scenes/cripta.json`:

```json
{
  "version": 1,
  "kind": "scene",
  "id": "scn_7f3a",
  "name": "Cripta",
  "campaign": "paratheos",
  "image": {
    "path": "Recursos/anexos/cripta.png",
    "width_px": 3000,
    "height_px": 2000
  },
  "grid": {
    "cell_px": 100,
    "offset_x": 0,
    "offset_y": 0,
    "visible": true
  },
  "fog_outside": false,
  "zones": [
    {
      "id": "zon_a1",
      "label": "Sala principal",
      "rects": [
        {"x": 4, "y": 3, "w": 6, "h": 4},
        {"x": 4, "y": 7, "w": 2, "h": 3}
      ],
      "revealed": false
    },
    {
      "id": "zon_b2",
      "label": "Banheiro",
      "rects": [
        {"x": 12, "y": 7, "w": 2, "h": 2}
      ],
      "revealed": true
    }
  ]
}
```

- `version` e `kind` permitem recusar arquivo de formato errado.
- `image.path` é relativo à raiz do vault. A imagem não é copiada, movida nem redimensionada. `width_px` e `height_px` são os naturais; o cliente escala.
- `grid` existe sempre. Grid opcional do ticket 01 significa `visible: false`, nunca ausência de grid, para coordenada não mudar de significado. `cell_px` é o lado da célula em pixels da imagem; `offset_x` e `offset_y` deslocam o grid.
- `fog_outside` é por cena. `false` (default) deixa visível o que está fora de qualquer zona; `true` cobre o mapa inteiro e só mostra dentro de zona revelada.
- `zones[].rects` tem no mínimo um retângulo inteiro em células. Vários retângulos fazem uma sala em L sem editor de polígono. Zonas podem se sobrepor: um ponto está revelado se estiver em pelo menos uma zona revelada.
- `revealed` no molde é o estado inicial. Depois que a cena entra numa Table, a névoa viva mora em `scenes.zones_json` no SQLite.
- O molde não tem `tokens`. Token é da Table.
- O arquivo é gravado de forma atômica (temp, `flush`, `fsync`, `os.replace`) e nunca renomeado. Mudar o nome da cena não renomeia o arquivo.
- Reimportar um molde alterado compara `blueprint_hash`: zona com o mesmo `id` mantém o `revealed` vivo, zona nova nasce `false`, zona removida perde a névoa. Sem hot reload; a mudança entra na próxima carga da cena.
- Imagem ausente vira placeholder; allowlist, path traversal e cache são do ticket "Autorização e arquivos".

### 6. Snapshot da Table

`Harpi/Campaigns/paratheos/tables/tbl_9c2e.json`, escrito enquanto a mesa está aberta:

```json
{
  "version": 1,
  "kind": "table_snapshot",
  "saved_at": 1760000000,
  "rev": 42,
  "table": {
    "id": "tbl_9c2e",
    "campaign": "paratheos",
    "channel_id": "123456789012345678",
    "name": "Sessão 12",
    "status": "open",
    "round": 3,
    "current_scene_id": "scn_7f3a"
  },
  "scene": {
    "id": "scn_7f3a",
    "name": "Cripta",
    "blueprint_path": "Harpi/Campaigns/paratheos/scenes/cripta.json",
    "blueprint_hash": "sha256:9f2c...",
    "image": {
      "path": "Recursos/anexos/cripta.png",
      "width_px": 3000,
      "height_px": 2000
    },
    "grid": {
      "cell_px": 100,
      "offset_x": 0,
      "offset_y": 0,
      "visible": true
    },
    "fog_outside": false,
    "zones": [
      {
        "id": "zon_a1",
        "label": "Sala principal",
        "rects": [
          {"x": 4, "y": 3, "w": 6, "h": 4},
          {"x": 4, "y": 7, "w": 2, "h": 3}
        ],
        "revealed": true
      },
      {
        "id": "zon_b2",
        "label": "Banheiro",
        "rects": [
          {"x": 12, "y": 7, "w": 2, "h": 2}
        ],
        "revealed": false
      }
    ]
  },
  "tokens": [
    {
      "id": "tok_a1",
      "character_id": "chr_k3m9",
      "label": "IR1S",
      "owner_id": "284712345678901234",
      "x": 6.5,
      "y": 5.0,
      "w": 1,
      "h": 1,
      "color": "#4f8cff",
      "visible": true
    },
    {
      "id": "tok_b2",
      "character_id": null,
      "label": "Goblin 1",
      "owner_id": null,
      "x": 8.0,
      "y": 4.0,
      "w": 1,
      "h": 1,
      "color": "#c0392b",
      "visible": true
    }
  ],
  "turn": {
    "id": "trn_55",
    "round": 3,
    "token_id": "tok_a1",
    "character_id": "chr_k3m9",
    "label": "IR1S",
    "started_at": 1759999900
  }
}
```

- Enquanto aberta, a Table grava o snapshot a cada 60 s e em mudança estrutural (trocar cena, criar ou remover token, revelar zona, virar rodada), com debounce de 2 s. Só um escritor por Table.
- Fechar grava na hora. O snapshot de fechamento tem `table.status: "closed"` e `turn: null`, porque o turno aberto é encerrado antes. O snapshot periódico de mesa aberta pode ter turno.
- O snapshot carrega todos os tokens, inclusive `visible: false`, e a névoa corrente. Não carrega rolagens, aprovações nem o log completo de turnos: isso é SQLite e não é backup de banco.
- Restaurar uma Table `closed` valida `version`, `kind`, id da Table e campanha, repõe a cena corrente, a névoa, os tokens daquela cena e a rodada, e volta para `open` sem turno. Tokens de outras cenas da mesma Table ficam intactos.
- Se o snapshot não validar, a Table abre do SQLite com aviso. O arquivo inválido fica no disco; o app não apaga nem corrige por conta própria.
- Crash não usa snapshot: a Table continua `open` e o boot serve o SQLite. O snapshot periódico é rede de segurança para perda do banco, não fonte de verdade concorrente.

### 7. Token

Tabela `tokens`; os campos são exatamente os do ticket.

| Campo | Regra |
|---|---|
| `id` | `tok_`, gerado uma vez |
| `table_id`, `scene_id` | token pertence à Table e à cena; trocar de cena não move token de cena |
| `character_id` | opcional; `chr_` quando o Character tem id no vault. Nota externa sem id usa só `label` |
| `label` | nome exibido; default é o nome do Character |
| `owner_id` | snowflake do jogador dono; `null` para NPC e marcador |
| `x`, `y` | canto superior esquerdo em células, float; `3.5` é metade da quarta célula |
| `w`, `h` | tamanho em células, inteiro maior que zero; default 1x1 |
| `color` | `#rrggbb` minúsculo; o painel escolhe da paleta |
| `visible` | `false` esconde do jogador; o narrador continua vendo |

- Retrato do token vem do Character linkado. Não existe campo de imagem no token.
- Jogador move o próprio token; narrador move qualquer token, inclusive NPC. A persistência do movimento é no fim do drag, como no ticket 06.
- Jogador não vê token com `visible: false`, token cujo centro cai em zona não revelada, nem token fora de todas as zonas quando `fog_outside` é `true`. O narrador vê todos.
- `x`/`y` precisam ser finitos e dentro do mapa; `w`/`h` não podem passar da borda. Fora disso é `422`; o servidor não corrige posição em silêncio.
- Remover token apaga a linha. `turns` e `rolls` guardam `label` e `character_id` em cópia, então o log continua legível. Não há soft delete no M1.
- Token de personagem arquivado permanece na cena até o narrador remover, como já dizia o ticket 03.

### 8. Turno e rodada

- Participante é todo token da cena ativa. Cada participante age uma vez por rodada; ninguém age duas vezes. Token de cenário (porta, baú) não deve ser token; fica na imagem ou numa zona.
- `turns` registra cada intervalo. Um índice único garante no máximo um turno aberto por Table e um turno por token por rodada.
- A Table começa em `round = 1`, sem turno aberto.
- O narrador abre o turno de qualquer participante pendente. O jogador do turno atual pode passar para qualquer participante que ainda não agiu ou encerrar o próprio turno. O narrador também passa e encerra por qualquer um, inclusive NPC e jogador ausente.
- Passar para quem já agiu é `422`: contraria um turno por personagem.
- Encerrar sem passar deixa a Table sem turno atual; o narrador escolhe o próximo.
- Quando o último participante pendente encerra o turno, a rodada fecha, `round` sobe e todos voltam a ficar pendentes. O narrador abre a rodada nova; ninguém começa sozinho.
- Token criado no meio da rodada entra pendente. Token removido deixa de ser participante; se tinha turno aberto, o turno é encerrado. Trocar de cena encerra o turno aberto e os tokens da cena nova entram pendentes na rodada corrente, sem reiniciar a contagem.
- Fechar a Table encerra o turno e a rodada; reabrir começa uma rodada nova, sem turno atual.
- `turns.label` e `turns.character_id` são cópia para o log sobreviver à remoção do token. `started_by` e `ended_by` guardam o snowflake de quem agiu; o app usa `system` quando fecha sozinho.
- Termos para o glossário: **turno** é a vez de um token; **rodada** é uma passagem por todos os tokens da cena. O ticket 01 chamava de "ordem livre"; a ordem continua livre, mas a rodada agora fecha por contagem.

### 9. Concorrência

- Um processo, SQLite em WAL, `foreign_keys=ON` e `busy_timeout=5000`, como o banco atual. Não há segundo banco.
- Um lock asyncio por Table serializa troca de cena, revelação de zona, turno, rodada, fechamento e snapshot. Movimento de token não precisa do lock da Table.
- CAS por linha: `tables.rev` para cena corrente, turno e rodada; `scenes.rev` para névoa e definição viva; `tokens.rev` para posição, tamanho, cor, rótulo, dono e visibilidade. Toda escrita incrementa o rev da linha.
- O pedido carrega o rev esperado. `UPDATE ... WHERE id = ? AND rev = ?` com zero linhas vira `409` com o estado atual; o cliente reaplica. Movimentos de tokens diferentes não conflitam; dois movimentos do mesmo token, o segundo perde.
- Abrir a segunda Table em paralelo é resolvido pelo índice único parcial; `IntegrityError` vira o mesmo `409 table_already_open`.
- O snapshot lê numa transação consistente, copia para memória e grava o arquivo fora da transação. Se uma mutação entrar durante a gravação, o snapshot fica com o `rev` anterior; o próximo snapshot corrige.
- Não há arquivo de lock no vault, como no ticket 04. Aprovação que grava vault e SQLite não é transação entre sistemas: grava os dois arquivos primeiro, depois a linha; falha no meio deixa `pending` e erro visível.
- Rolar no Discord e no painel pode chegar junto; `discord_message_id` único deduplica a mesma mensagem. A ordem do log é `created_at, id`.
- Formato, cadência e ordem dos frames continuam no ticket "Transporte e concorrência da mesa". Aqui só se fixa o commit no banco e o `409` de rev.

### 10. Fica para outros tickets

- Matriz de permissões por rota, filtro do SSE e allowlist de imagem: "Autorização e arquivos".
- Formato da mensagem de rolagem, deduplicação de borda e retenção: "Rolagens espelhadas".
- Como a lista de cenas, o editor de zonas e o arrastar token aparecem no painel: "UX da mesa no painel".
- Bind mount, `HARPI_VAULT_PATH`, backup e checklist de disco: "Ops do vault e backup".
- Glossário e ADRs: "Spec, glossário e ADRs". Candidatos: ADR do estado da mesa (SQLite vivo, molde em `scenes/`, snapshot em `tables/`), ADR da Table única por campanha/canal e ADR do ciclo de rodada.
- Atlas e mapa dentro de mapa: marco 2, fora do M1.
