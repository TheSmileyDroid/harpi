# Spec: VTT do Harpi — marco 1

Marco 1 do VTT: uma campanha Paratheos já configurada, uma Table por campanha presa a um canal de texto, Scene com tokens, névoa por zona e rodada de turnos, log de dados espelhado entre painel e Discord, e fichas Fate criadas pelos jogadores e sincronizadas com o vault.

Este documento consolida as decisões dos tickets [01](issues/01-decisoes-do-grilling.md) a [11](issues/11-ops-do-vault.md) e [13](issues/13-editor-de-cenas-e-zonas.md). Onde um ticket posterior corrigiu um anterior, vale a correção e ela está registrada em `## Reconciliações`. O glossário canônico vive no `CONTEXT.md`, com [versão em português](glossario.md); os ADRs 0010 a 0014 vivem em `docs/adr/`.

## 1. Escopo

### Entregue no M1

- Campanha `paratheos` semeada na migração, com narrador e guild fixos. Sem criação de campanha nem convite.
- Tela de entrada do membro sem ficha ativa, com criação de Character e Sheet pelo painel e fila de aprovação do narrador.
- Character e Sheet como notas no vault, sync de três vias com o Obsidian e o Syncthing, conflito explícito e backup por escrita.
- Card público de personagem e elenco revelado, com ficha completa restrita ao dono e ao narrador.
- Mesa: Table aberta pelo narrador, escolha de Scene, tokens arrastáveis, névoa por zona, rodada com um turno por token público.
- Stream dedicado por Table em SSE, com delta absoluto, keyframe, quem está na mesa e cotas próprias.
- Log de rolagens: `4dF` e o restante do parser, no painel e no canal, com a mensagem do Discord antes da linha.
- Galeria e editor de cenas: origem imagem ou desenho, sala = zona, salvar atômico com hash e recarga explícita na Mesa.
- Casca B do painel: rail de 14rem, páginas por campanha, gaveta de ficha, celular e teclado.

### Fora do M1

| Trabalho | Marco |
|---|---|
| Campanha local sem vault, criação de campanha e convites | M2 |
| Atlas em Canvas, viewer somente leitura e navegação de mapas aninhados | M2 |
| Editor de Atlas no Harpi e plugin do Obsidian | M3 |
| Wiki dos jogadores, manifesto e editor de notas | M3 |
| Editor de arte de mapa (pincel, textura, hachura, estilos) | M3 |
| Co-narrador | depois do M3 |
| Embed de imagem remota na cena | depois do M1, sem data |
| 5e, grid d20, paredes, luzes e linha de visão | fora |
| Voz própria, chat de texto próprio e importação de PDF ou HTML | fora |
| Integração com Foundry, Roll20 ou `.atlasmap` | fora |

## 2. Base fixa

- Discord OAuth com allowlist de guild; um processo Quart mais discord.py; SQLite com migrações ordenadas; SSE existente para música.
- Escritas no vault confinadas a `Harpi/Campaigns/<slug>/`.
- Interface em português, código, contrato e docs do repo em inglês.
- `src/panel/schemas.py` continua sendo a fonte do contrato; `make contract` gera OpenAPI, tipos TypeScript e validadores.
- A API de música, o `GuildSampler`, o `STREAM_SLOTS` de música e o `after_request` de `pages/api.py` não mudam. As rotas novas não entram no blueprint `api`.

## 3. Modelo de domínio

- **Campaign**: narrador, membros, guild e uma origem de conteúdo (`vault` ou `local`). Identificada por slug imutável, minúsculo, igual em três lugares: pasta, bloco `harpi-campaign` e SQLite.
- **Character**: nota de identidade e lore. **Sheet**: estado jogável, no máximo um `pendente` ou `ativo` por Character. **PC** é Character com Sheet cujo dono é jogador; **NPC** é todo o resto.
- **Table**: sessão viva de uma campanha presa a um canal de texto. Uma aberta por campanha e uma por canal, garantidas por índice.
- **Scene**: mapa preparado, imagem ou desenho, grid, zonas e névoa inicial. Vive como molde no vault; a cópia viva está no SQLite.
- **Token**: peça na mesa, por Table e por Scene. **Zona** é a unidade de névoa. **Turno** é a vez de um token; **rodada** é uma passagem por todos os tokens públicos da cena.
- **Rolagem**: uma avaliação aceita de expressão de dados numa Table aberta, uma linha em `rolls`, com texto congelado.

## 4. Armazenamento

### 4.1 Vault

```text
Harpi/Campaigns/paratheos/
├── config.md
├── characters/<Nome>.md
├── sheets/<Nome>.md
├── assets/<nome>.<ext>
├── assets/<slug>-map.svg
├── scenes/<slug>.json
└── tables/<table-id>.json
```

- `config.md` é editado no Obsidian e é a única fonte da configuração da campanha. O app lê e recarrega pela varredura de 60 s; nunca escreve.
- `characters/` e `sheets/` são pastas irmãs por tipo. O nome do arquivo é o nome de batismo e não muda quando o nome da ficção muda.
- `assets/` guarda upload de imagem e o SVG de cena desenhada. O nome do upload é o `sha256` do conteúdo mais a extensão.
- `scenes/<slug>.json` é o molde autoral: imagem, grid, zonas e `revealed` inicial, sem tokens. O `source` (`image` ou `sketch`) também viaja no molde, porque o arquivo é a origem da reimportação.
- `tables/<table-id>.json` é o snapshot da mesa: cena corrente com névoa, tokens, rodada e turno. Escrito a cada 60 s, em mudança estrutural com debounce de 2 s, e no fechamento.
- Imagem citada por uma cena nunca é copiada, movida nem redimensionada. O caminho é relativo à raiz do vault.
- O app nunca renomeia, move nem apaga arquivo. Sobrescrever de forma atômica é permitido.
- Bind mount: `/vault` somente leitura e `/vault/Harpi` leitura e escrita, com `user: "1000:1000"`. `HARPI_VAULT_PATH=/vault` no container; o caminho do host fica em `HARPI_VAULT_HOST_PATH`.
- Vault ausente ou raiz inexistente: rotas de ficha, elenco, card e asset respondem 503 `vault_unavailable`. Table, stream, turno e rolagem continuam, porque vivem no SQLite.

### 4.2 SQLite

O banco do painel (`HARPI_DB_PATH`), em WAL, `foreign_keys=ON`, `busy_timeout=5000`. Uma migração nova depois das existentes; o número fica para a implementação. Timestamps em segundos epoch, booleanos em `INTEGER` com `CHECK (x IN (0,1))`, ids opacos com prefixo.

- SQLite é a verdade viva durante a sessão. O snapshot é rede de segurança para perda do banco, não fonte concorrente.
- Crash deixa a Table `open`. No boot vale o SQLite; o narrador retoma ou fecha a Table órfã. Nenhuma restauração automática de snapshot sobre estado vivo.

## 5. Esquema SQLite consolidado

Este esquema já inclui as emendas dos tickets 04, 07, 08, 09 e 13. `sheet_conflicts.id` é acréscimo desta spec, porque a rota de resolução endereça o conflito por id.

```sql
CREATE TABLE campaigns (
    slug TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    narrator_id TEXT NOT NULL,
    system TEXT NOT NULL DEFAULT 'fate',
    content_source TEXT NOT NULL DEFAULT 'vault'
        CHECK (content_source IN ('vault', 'local')),
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

CREATE TABLE sheet_files (
    path TEXT PRIMARY KEY,
    harpi_id TEXT NOT NULL,
    campaign TEXT NOT NULL REFERENCES campaigns(slug) ON DELETE CASCADE,
    rev INTEGER NOT NULL DEFAULT 0,
    hash TEXT NOT NULL,
    last_text TEXT NOT NULL,
    base_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pendente'
        CHECK (status IN ('pendente', 'ativo', 'arquivado')),
    owner_id TEXT,
    state TEXT NOT NULL DEFAULT 'ok'
        CHECK (state IN ('ok', 'conflito', 'ausente', 'invalido', 'desconhecido')),
    updated_at INTEGER NOT NULL
);

CREATE INDEX sheet_files_by_campaign ON sheet_files (campaign, state);
CREATE INDEX sheet_files_by_harpi_id ON sheet_files (harpi_id);
CREATE INDEX sheet_files_by_owner ON sheet_files (campaign, owner_id, status);

CREATE TABLE sheet_conflicts (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL REFERENCES sheet_files(path) ON DELETE CASCADE,
    field_path TEXT NOT NULL,
    base TEXT,
    ours TEXT,
    theirs TEXT,
    created_at INTEGER NOT NULL,
    resolved_at INTEGER,
    resolved_by TEXT
);

CREATE TABLE character_visibility (
    campaign_slug TEXT NOT NULL REFERENCES campaigns(slug) ON DELETE CASCADE,
    character_id TEXT NOT NULL,
    revealed_at INTEGER NOT NULL,
    revealed_by TEXT NOT NULL,
    PRIMARY KEY (campaign_slug, character_id)
);

CREATE TABLE tables (
    id TEXT PRIMARY KEY,
    campaign_slug TEXT NOT NULL REFERENCES campaigns(slug) ON DELETE CASCADE,
    channel_id TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open', 'closed')),
    current_scene_id TEXT REFERENCES scenes(id) ON DELETE SET NULL,
    round INTEGER NOT NULL DEFAULT 1 CHECK (round >= 1),
    spectators INTEGER NOT NULL DEFAULT 0 CHECK (spectators IN (0, 1)),
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
    source TEXT NOT NULL DEFAULT 'image' CHECK (source IN ('image', 'sketch')),
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
    scene_label TEXT NOT NULL DEFAULT '',
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

A migração semeia `campaigns` com a linha da Paratheos (`narrator_id` do narrador, `guild_id` da guild, `content_source = 'vault'`).

## 6. Ficha

### 6.1 Bloco `harpi-sheet`

O estado mecânico vive num bloco YAML cercado por ` ```harpi-sheet `, com `refresh`, `fate_points`, `aspects`, `skills`, `stunts`, `stress`, `consequences`, `extras` e `inventory`. O exemplo completo está no [ticket 02](issues/02-esquema-da-ficha.md).

Regras normativas:

- `skills` lista só perícia com rank maior ou igual a 1; ausente vale 0; duplicata é erro; o rank precisa existir na escada da config.
- `stress` usa as trilhas da config; cada caixa tem `value` e `checked`; a interface não deixa marcar mais caixas do que existem.
- `consequences` usa os slots da config; `severity` é a chave; texto vazio libera o slot.
- `extras` é lista aberta com `kind` vindo da config; o app exibe, não interpreta a mecânica.
- `aspects` é lista `{label, text}`, default `Conceito`, `Problema` e três `Aspecto`; a config pode renomear.
- `inventory` é `{item, qty, note}`, com `item` em wikilink; link morto aparece como texto.
- `refresh` e `fate_points` são inteiros; `fate_points` não tem teto.
- `stunts` é `{name, text, refresh_cost}`; o app exibe o custo e não recalcula a recarga.
- Chaves desconhecidas são preservadas na escrita.
- YAML inválido deixa a ficha somente leitura, com erro visível. O app nunca sobrescreve bloco que não parseou.

### 6.2 `harpi-campaign`

`config.md` define nome, sistema, escada, perícias, rótulos de aspecto, trilhas de estresse, slots de consequência, recarga e `extras`. O bloco completo está no [ticket 02](issues/02-esquema-da-ficha.md). A escada não entra na mensagem de rolagem no M1: a rolagem precisa funcionar com o vault fora.

### 6.3 Frontmatter

Character: `tipo: personagem`, `harpi-id` (`chr_`), `harpi-campanha`, `harpi-status`, `harpi-rev`, mais `aliases` e `tags` da convenção do vault.

Sheet: `tipo: ficha`, `harpi-id` (`sht_`), `harpi-campanha`, `harpi-character`, `harpi-character-id` (ausente quando o alvo é nota externa sem id), `harpi-owner` (snowflake, verdade do dono), `harpi-owner-name` (derivado), `harpi-status`, `harpi-rev`, `harpi-review-note`.

- `harpi-id`, `harpi-campanha` e `harpi-owner` são do app; edição à mão é ignorada e corrigida na escrita seguinte, com aviso.
- `harpi-status` aceito à mão quando a transição é legal (`ativo` para `arquivado` e a volta); transição ilegal é corrigida com aviso.
- O Character não tem dono; o vínculo mora só no Sheet.

### 6.4 Prosa

O Sheet ganha `## História` e `## Anotações`, as duas seções de prosa que o app escreve. Fora delas, do bloco e das chaves `harpi-*`, o arquivo continua byte a byte. Cada seção é um campo do merge de três vias.

O jogador edita a prosa do próprio Character só quando a nota foi criada pelo app e o Sheet dele aponta para ela. Character que é nota externa do vault continua exclusivo do narrador. O card público lê o resumo direto; aprovação cobre a mecânica, não a lore.

O editor de prosa é Wordgard montado só nas seções que o app possui, com schema enxuto, markdown canônico e upload de imagem.

### 6.5 Ciclo

- Jogador cria Character e Sheet juntos: os dois nascem `pendente`, `harpi-rev: 1`, e o par já existe no vault. O dono lê e edita; outros jogadores não veem nada; o narrador vê na fila.
- Aprovar grava `ativo` nos dois arquivos na mesma transação e depois a linha em `approvals`. Se a gravação no vault falhar, a linha fica `pending` e o erro aparece.
- Recusar mantém `pendente` e preenche `harpi-review-note`; o reenvio limpa a nota.
- NPC nasce `ativo` e não passa por fila. O Sheet do NPC é opcional.
- `arquivado` sai do elenco, do card público, do seletor de token e da mesa; a ficha fica somente leitura. Token que já está na cena permanece até o narrador remover. Desarquivar volta para `ativo`.
- Um Character tem no máximo um Sheet em `pendente` ou `ativo`; a rota de criação recusa o segundo com 409.

### 6.6 Projeção pública

- Dono da ficha e narrador veem a ficha completa.
- Outro jogador vê o card público: nome, imagem, conceito e resumo. De NPC, o mesmo card, e só depois de revelado.
- Elenco mostra personagens revelados: PCs `ativo` sempre; NPCs a partir da revelação. Personagem revelado não volta a esconder sozinho. Ficha `pendente` de outro jogador não aparece, nem o nome.

### 6.7 Sync com o vault

Uma fila por arquivo, coalescendo por 300 ms. Escrita atômica com `.harpi-tmp-<pid>`, `flush`, `fsync`, `os.replace`, precedida de backup em `data/vault-backups/<slug>/<harpi-id>/<rev>-<timestamp>.md`, retenção de 20 por arquivo.

- A verdade da mudança é o `sha256` do arquivo. `harpi-rev` é carimbo da última escrita do app, nunca detector.
- Observer inotify em `Harpi/Campaigns/` com debounce de 500 ms, mais varredura completa no boot e a cada 60 s comparando `mtime` e tamanho.
- Allowlist: só `characters/*.md` e `sheets/*.md`. Ficam de fora `scenes/`, `tables/`, `config.md`, dotfiles, dotdirs, `*.tmp`, `~syncthing~*` e `*.sync-conflict-*`.
- Merge de três vias com base na última versão aceita, identidade de item por rótulo, patch cirúrgico e CAS de até 3 tentativas. O arquivo só é reescrito nas chaves `tipo`, `harpi-*`, no bloco e nas duas seções de prosa.
- Mesmo campo mudado dos dois lados vira conflito naquele campo; o disco fica intocado e a ficha fica somente leitura até a decisão. A decisão é por campo: `usar do vault`, `usar do painel` e, em campo de texto, `manter os dois`.
- Conflito vive só no SQLite; nenhum marcador é escrito no arquivo.
- `YAML` lido e escrito em modo round-trip com `ruamel.yaml`, fim de linha preservado.
- Não há trava nem arquivo de lock no vault.
- `*.sync-conflict-*` do Syncthing é ignorado e fica no disco para o narrador resolver no Obsidian. O app nunca escolhe a versão verdadeira.
- Arquivo apagado: estado `ausente`, snapshot continua servindo leitura, `restaurar` regrava `last_text` com rev novo e backup. O app nunca restaura sozinho.
- Rename é detectado pelo mesmo `harpi-id` e só atualiza `path`. Id editado à mão vira `ausente` mais `desconhecido`; dois arquivos com o mesmo id ficam ambos intocados, com duplicata sinalizada.

## 7. Mesa

### 7.1 Ciclo da Table

- Só o narrador abre, escolhendo campanha, canal e cena. Nasce `open`, `round = 1`, sem turno aberto.
- Segunda Table aberta na campanha ou no canal é `409 table_already_open`, com id, nome e canal da ativa. Nada fecha sozinho.
- Fechar encerra o turno e a rodada, grava o snapshot e só então marca `closed`. `closed` sem snapshot não existe.
- Reabrir restaura o snapshot e volta a `open` sem turno. Snapshot inválido ou ausente: abre do SQLite com aviso, sem apagar nada.
- Trocar de cena encerra o turno aberto, carrega a nova e os tokens dela; a névoa e os tokens da cena anterior ficam guardados.
- Cena alterada no disco não entra ao vivo. A Mesa mostra o aviso de versão nova e o narrador aperta **Recarregar cena**. A recarga reimporta por hash: zona com o mesmo `id` mantém `revealed` vivo, zona nova nasce `false`, zona removida perde a névoa, tokens da Table ficam intactos e o turno aberto é encerrado.

### 7.2 Token

- `x` e `y` são o canto superior esquerdo em células, float; `w` e `h` em células, inteiro maior que zero, default 1x1; cor `#rrggbb` minúsculo; `visible: false` esconde do jogador e o narrador continua vendo.
- Retrato vem do Character linkado; o token não tem campo de imagem.
- Jogador move o token do próprio Sheet; o narrador move qualquer token.
- Jogador não vê token `visible: false`, token cujo centro cai em zona não revelada, nem token fora de zona quando `fog_outside = true`.
- `x`/`y` não finitos ou fora do mapa, ou `w`/`h` passando da borda, é `422`. O servidor não corrige posição em silêncio.
- Remover token apaga a linha; `turns` e `rolls` guardam cópia de `label` e `character_id`.

### 7.3 Zonas e névoa

- Zona é um conjunto de retângulos inteiros em células, com no mínimo um; vários retângulos fazem sala em L.
- Zonas podem se sobrepor: um ponto está revelado se estiver em pelo menos uma zona revelada.
- `fog_outside` é por cena. `false` deixa visível o que está fora de qualquer zona; `true` cobre o mapa inteiro e mostra só dentro de zona revelada.
- O narrador revela ou cobre clicando na zona no mapa. O jogador não vê contorno, nome nem hachura de zona oculta.
- A névoa é recurso de jogo, não fronteira de segurança: quem tem acesso à Table baixa o PNG inteiro. Ver ADR 0013.

### 7.4 Turno e rodada

- Participante é todo token **público** da cena ativa. Token oculto não abre turno, não entra na contagem e não fecha rodada, nem para o narrador.
- Um turno por token por rodada; no máximo um turno aberto por Table.
- O narrador abre o turno de qualquer participante pendente. O jogador do turno pode passar para qualquer pendente ou encerrar o próprio turno.
- Passar para quem já agiu é `422`. Encerrar sem passar deixa a Table sem turno; o narrador escolhe o próximo.
- Quando o último pendente encerra, a rodada fecha, `round` sobe e todos voltam a pendente. O narrador abre a rodada nova; ninguém começa sozinho.
- Token criado no meio da rodada entra pendente. Token removido deixa de ser participante; turno aberto dele é encerrado.
- Fechar a Table encerra turno e rodada; reabrir começa rodada nova, sem turno atual.

### 7.5 Rolagem

- Canal: expressão solta e `!d` gravam quando o canal é de uma Table `open`. Fora disso o bot responde como hoje e não grava.
- Painel: mesma expressão, sem prefixo. Pendente e espectador recebem 403; Table fechada é `409 table_closed`.
- Bots e webhooks são ignorados. `N#` grava N linhas e uma mensagem, limite de 10 repetições.
- Até 120 caracteres por expressão, até 20 dados por grupo, resultado inteiro. `1d6/2` é `422 non_integer_result`.
- Sem vínculo com token. `turn_id` é preenchido só quando o turno aberto é de um token do autor; é contexto, não permissão.
- Caminho do painel: valida e avalia, posta a mensagem no canal pelo loop do bot, insere as linhas já com o id da mensagem, publica `table.roll` e responde. Falha do Discord é `502 discord_unavailable` e nada é gravado nem transmitido.
- Caminho do canal: avalia, atravessa para o loop do Quart, confere acesso e cena, deduplica por `discord_message_id`, insere, publica e responde com `message.reply`.
- Texto congelado no formato do parser: `` ` 1 ` ⟵ [-, 0, +, +] 4dF ``. A mensagem compõe `**Autor** · Cena — <corpo>`, sem menção e sem nome de escada. Cena ausente remove o segmento.
- Id `rol_` mais ULID, na ordem da mensagem. Ordem total por `(created_at, id)`. Sem expurgo; as linhas morrem com a Table por cascata.
- Log só no SQLite; o snapshot não carrega rolagens e não há exportação para o vault no M1.

### 7.6 Stream da Table

`GET /api/tables/<id>/events`, `text/event-stream`, em `pages/tables.py`. Não passa pelo `GuildSampler`, pelo tick de 5 s nem pelo `after_request` do blueprint `api`.

| Evento | Conteúdo | Quando |
|---|---|---|
| `table.snapshot` | `stream_rev`, `table_id`, cena recortada, quem está na mesa, drags ativos | abertura, troca de cena, recarga, keyframe de 5 s |
| `table.delta` | `from_stream_rev`, `stream_rev`, `scene_id`, entidades com estado absoluto, `removed` | na mudança, coalescido a 10 Hz |
| `table.viewers` | quem está na mesa | entrada ou saída de viewer |
| `table.drag` | token, ator, início ou fim | começo, drop, queda, troca de cena |
| `sheet.changed` | `sheet_id`, `character_id`, `rev`, `state` | mudança aceita de ficha |
| `table.roll` | DTO completo da rolagem | rolagem aceita |
| `heartbeat` | vazio | 5 s |
| `table.closed` | motivo | fim da Table |

- Broadcaster em memória, um por Table, em `src/panel/table_stream.py`, no molde do `GuildSampler`: nasce no primeiro assinante e morre com o último. Nunca vira fonte de verdade.
- `stream_rev` é por Table, +1 por mudança aceita, separado dos revs de CAS e não persistido. Cada delta leva `from_stream_rev`; divergência fecha e reconecta.
- Janela de 512 mudanças por Table; viewer lento recebe delta maior, nunca buraco; janela vencida vira snapshot.
- Keyframe de 5 s e heartbeat de 5 s. Sem tick fixo: mesa parada só gera heartbeat.
- Duas classes por assinante: slot de estado (último `stream_rev`) e fila de eventos append-only de 32. Fila cheia fecha o stream; o cliente reconecta, pega snapshot e recupera o log por `GET /rolls`.
- Toda conexão abre com `table.snapshot`, já recortado, adotado sem checar `stream_rev`. Sem `Last-Event-ID` nem replay.
- Backoff 1, 2, 4 até 30 s e watchdog de 15 s, como `web/src/lib/sse.ts`. `visibilitychange` e `online` forçam reconexão.
- Cotas próprias: 16 streams por Table, 2 por usuário, contador separado do `STREAM_SLOTS` de música e fora do alerta de crescimento. Limite responde 429 com `Retry-After: 30`.
- A lista de quem está na mesa é memória do broadcaster: nome de exibição e papel (narrador, jogador, pendente, espectador), nunca snowflake.
- Um worker. Broadcaster, `stream_rev`, janelas e slots são estado local de processo; mais de um worker exige bus compartilhado.

## 8. Editor de cenas

### 8.1 Telas

- Página Cenas com galeria e editor. A galeria abre por padrão, em grade de cartões: miniatura, nome, origem, número de áreas, estado de salvo e selo **em mesa**. O último cartão cria cena.
- O editor é a bancada: palco, barra de ferramentas à esquerda, faixa da sala selecionada embaixo e inspetor à direita com mapa, grid, salas e salvar.
- O rail mantém a lista curta de cenas para trocar sem voltar à galeria.
- Cena nova: o nome vira slug do arquivo e a cena nasce com origem `image` ou `sketch`.

### 8.2 Origem

- `image`: picker do índice do vault, com pastas e miniaturas, ou upload em `assets/`. A imagem original não é copiada, movida nem renomeada.
- `sketch`: a cena nasce sem imagem externa. Sala desenhada é a zona de névoa; as salas formam o mapa e a névoa ao mesmo tempo.
- Embed de imagem remota fica fora do M1: exige allowlist de host e cache no servidor.

### 8.3 Desenho

- Ferramenta Sala: arrastar retângulo no grid cria sala. Sobrepor parcialmente uma sala existente junta o pedaço na mesma sala; encostar sem sobrepor cria outra. Merge só por sobreposição.
- Geometria normalizada em retângulos sem sobreposição; contorno é a união das células, sem linha interna nem cor dobrada.
- Ferramenta Apagar: arrastar corta só as células tocadas e pode abrir porta, buraco ou dividir a sala; o que sobra continua sendo a mesma sala. Desfazer restaura o estado anterior.
- Clique seleciona, clique no vazio desmarca, duplo clique foca o nome, `Delete` exclui a sala. Atalhos: `V` selecionar, `R` sala, `E` apagar, `S` salvar.
- Cada sala tem rótulo, que é o nome no mapa e na lista.
- Salvar cena desenhada gera `assets/<slug>-map.svg` e mantém `image.path` apontando para ele.
- A miniatura de uma cena desenhada na galeria e no editor é renderizada dos retângulos do molde no cliente. O SVG existe só para a Mesa, servido pela rota do mapa.
- Encaixe sempre em célula inteira. Sem pincel, textura, hachura, raio de canto ou estilo.

### 8.4 Grid e névoa

- `cell_px`, `offset_x`, `offset_y` e `visible`, como no molde. Grid existe sempre: opcional significa `visible: false`.
- `revealed` do molde é o estado inicial; `fog_outside` é por cena.
- No editor, sala oculta tem contorno tracejado e rótulo "oculta".

### 8.5 Cena em uso

- O editor não desenha névoa nem tokens vivos. Mostra o mapa preparado e a faixa "Em uso na mesa · N tokens · X de Y áreas reveladas agora", com atalho para a Mesa.
- Salvar grava só o arquivo. A Mesa avisa e o narrador recarrega explicitamente.
- Escrita atômica com `.harpi-tmp-*`, `flush`, `fsync`, `os.replace`; arquivo nunca renomeado.
- `blueprint_hash` sobre o JSON canônico, gravado no SQLite. O save carrega o hash de base; se o arquivo mudou no disco, o save é recusado com conflito e o narrador reimporta do disco ou sobrescreve de propósito.
- Mudar o nome da cena não renomeia o arquivo.

## 9. Rotas

### 9.1 Páginas

| Rota | Tela |
|---|---|
| `/c/<slug>/mesa` | Mesa |
| `/c/<slug>/personagens` | Personagens, criação e fila do narrador |
| `/c/<slug>/ficha` | Ficha em largura cheia |
| `/c/<slug>/cenas` | Galeria de cenas |
| `/c/<slug>/cenas/<scene>` | Editor de cena |

`/` continua a página de música. O M1 resolve `paratheos` pelo seed; o M2 acrescenta o parâmetro de campanha sem mudar a forma da URL.

### 9.2 API de campanha

Prefixo `/api/campaigns/<slug>`. Rotas com `E` aceitam espectador com a flag ligada; `P` é pendente.

| Rota | Narrador | Jogador | P | E |
|---|---|---|---|---|
| `GET /api/campaigns` | as suas | as suas | as suas | não |
| `GET /api/campaigns/<slug>` | sim | sim | sim | não |
| `GET .../characters` | todos | cards revelados | cards revelados | não |
| `GET .../characters/<id>` | ficha inteira | própria ficha, card alheio | própria ficha, card alheio | não |
| `GET .../characters/<id>/portrait` | sim | se o card é visível | se o card é visível | não |
| `POST .../characters` | qualquer (NPC) | só o próprio par | já criou | não |
| `PATCH .../characters/<id>` | qualquer | só Character criado pelo app que o Sheet dele aponta | idem | não |
| `PATCH .../sheets/<id>` | qualquer | a própria, se não arquivada | a própria, se pendente | não |
| `POST .../sheets/<id>/submit` | não | não | reenviar depois de recusa | não |
| `GET .../approvals` | fila toda | não | não | não |
| `POST .../approvals/<id>` | aprovar ou recusar | não | não | não |
| `GET .../conflicts` | fila da campanha | os próprios | não | não |
| `POST .../conflicts/<id>/resolve` | qualquer | os próprios | não | não |
| `POST .../characters/<id>/reveal` e `.../hide` | sim | não | não | não |
| `GET .../assets/<name>`, `.../images/<name>` | sim | sim | sim | não |
| `POST .../assets` | sim | sim | sim | não |
| `GET .../scenes` | lista | não | não | não |
| `GET .../scenes/<scene>` | molde | não | não | não |
| `POST .../scenes` | criar | não | não | não |
| `PUT .../scenes/<scene>` | salvar | não | não | não |

Jogador, pendente e espectador recebem a cena corrente pelo stream, nunca a lista nem o molde. `GET /api/campaigns/<slug>` devolve a campanha, o papel do usuário e a Table aberta (id, nome, canal), para a Mesa resolver a URL sem que o cliente conheça ids.

`PATCH .../sheets/<id>` carrega os campos que o painel possui e o `base_hash` lido; o servidor faz o merge de três vias e responde o estado aceito ou 409 com os campos em conflito.

### 9.3 API de mesa

Prefixo `/api/tables`.

| Rota | Narrador | Jogador | P | E |
|---|---|---|---|---|
| `GET /api/tables/<id>/summary` | sim | sim | sim | sim, com a flag |
| `GET /api/tables/<id>/map` | sim | sim | sim | sim |
| `GET /api/tables/<id>/events` | recorte completo | recorte jogador | recorte jogador | recorte jogador |
| `POST /api/tables/<id>/moves` | qualquer token | só o token do próprio Sheet | não | não |
| `POST /api/tables/<id>/turns` | abrir, passar e encerrar qualquer | passar e encerrar o próprio | não | não |
| `POST /api/tables/<id>/scene` | trocar cena | não | não | não |
| `POST /api/tables/<id>/scene/reload` | recarregar do disco | não | não | não |
| `POST /api/tables/<id>/zones/<zone>/reveal` e `.../hide` | sim | não | não | não |
| `POST /api/tables/<id>/tokens`, `PATCH .../tokens/<id>`, `DELETE .../tokens/<id>` | sim | não | não | não |
| `POST /api/tables/<id>/spectators` | sim | não | não | não |
| `POST /api/tables` (abrir) | sim | não | não | não |
| `POST /api/tables/<id>/close` e `.../reopen` | sim | não | não | não |
| `POST /api/tables/<id>/rolls` | sim | sim | não | não |
| `GET /api/tables/<id>/rolls?after=<roll_id>&limit=50` | sim | sim | sim | sim, com a Table aberta |

- Corpos: `moves` 16 KB; escrita de ficha e prosa 64 KB; rolagem 1 KB; upload 16 MB. `MAX_CONTENT_LENGTH` global sobe para 16 MB mais 64 KB.
- Buckets por usuário: moves 600/min; escrita de ficha e prosa 60/min; leitura de elenco e card 120/min; assets GET 300/min; upload 10/min; aprovação 30/min; rolagem POST 60/min e GET 240/min.
- Códigos: 404 para falta de escopo, 403 para ação negada dentro do escopo, 409 para CAS e segundo Sheet, 422 para payload inválido, 413 para corpo grande, 429 para cota, 502 para Discord fora, 503 para vault ausente.

### 9.4 Borda

- CSRF: em `POST`, `PATCH` e `DELETE`, exigir `Content-Type: application/json` (ou `multipart/form-data` só no upload) e `Sec-Fetch-Site: same-origin`, aceitando `same-site` quando `Origin` bate com o host confiável; sem header, exigir `Origin` igual ao host. Falha é 403. GET não muta.
- NPM: `/api/tables/` com `rate=600r/m burst=30`; `/api/campaigns/` com `rate=300r/m burst=60` e `client_max_body_size 17m`; `/api/` continua 60/min. `proxy_buffering off` e os timeouts de 1 h.
- Assets: nome por `^[a-z0-9][a-z0-9._-]{0,127}$`; imagem do vault resolvida por índice em memória; `realpath` sob a raiz; cada componente sem `.` ou `~` inicial; arquivo regular; extensão em `png`, `jpg`, `jpeg`, `webp`. Symlink só passa se o `realpath` ficar dentro da raiz. SVG fica fora.
- Imagem acima de 16 MB, ausente, fora da allowlist ou fora da raiz: 404 sem dizer qual.
- O SVG de cena desenhada é gerado pelo servidor a partir das células, não é upload e não entra no índice de imagens nem na rota de assets. Só é servido por `GET /api/tables/<id>/map`, com `Content-Type: image/svg+xml`, `X-Content-Type-Options: nosniff` e `Content-Security-Policy: sandbox`. O allowlist de raster continua valendo para tudo que vem do vault ou do cliente.
- Cache: `private, max-age=60, must-revalidate`, `ETag` de mtime mais tamanho, `Last-Modified`, 304 em `If-None-Match`. Nunca `public`.
- Upload: sniff dos primeiros bytes, re-encode para remover EXIF, nome `sha256` mais extensão, mesmo hash não reescreve. Cota de 100 MB por campanha.
- Rota de leitura só serve arquivo que o banco referencia; asset órfão não é servido.

## 10. Estados

### Ficha

| Estado | Significa | Sai quando |
|---|---|---|
| `ok` | hash e base em dia | qualquer mudança externa ou escrita |
| `conflito` | mesmo campo mudou dos dois lados | decisão campo a campo |
| `ausente` | arquivo sumiu do disco | `restaurar` ou `esquecer` |
| `invalido` | YAML não parseia | arquivo corrigido |
| `desconhecido` | `harpi-id` novo, ausente ou duplicado | narrador adota ou conserta |

### Status da ficha

`pendente`, `ativo`, `arquivado`. O status do Sheet é a verdade; o do Character é espelho.

### Table

`open` ou `closed`. A Table `open` pode estar sem turno. Rodada começa em 1 e sobe quando o último pendente age.

### Papéis

Narrador, jogador (membro com Sheet `ativo`), pendente (membro sem Sheet `ativo`), espectador (fora da campanha, Table com flag), sem acesso (404). Papel não é coluna: sai de `members` mais `sheet_files.status`.

## 11. Painel

- Casca B: rail fixo de 14rem com wordmark, campanha, páginas (MESA · PERSONAGENS · FICHA · CENAS), lista de cenas, quem está na mesa com papel e estado do link. Abaixo de 56rem o rail vira faixa no topo.
- Mesa em duas colunas: mapa largo e coluna de 20rem com turno, rolagem, log e condução. A página de música não ganha rail nem dock de VTT.
- Controles por papel; o recorte de dados vem do servidor e a UI esconde o que o papel não pode fazer. O servidor responde 403, 404, 409 ou 422 se a ação for forçada.
- Mapa cabe na largura no desktop, com grid. Narrador vê zonas ocultas em névoa tracejada e clicável; jogador não vê contorno, hachura nem nome de zona oculta.
- Token é quadrado de 3px, mínimo de 36px de alvo, centrado na célula, que não encolhe com o zoom. PC em sand, NPC em oxide, token do jogador com anel amber. Rótulo em placard, escondido no celular.
- Arrastar com pointer capture, preview local e commit no drop. Enquanto outro arrasta, contorno tracejado oxide com nome por 3 s, sem bloquear.
- Revelar zona por clique, com atualização otimista e confirmação no `table.delta`.
- Turno: seta por participante pendente; passar e encerrar marcam quem agiu. Atalho `N` para passar.
- Rolagem abaixo do turno; log crescente com etiqueta PAINEL ou DISCORD; reconexão recupera por `GET /rolls`; chave travada durante o POST.
- Ficha em gaveta de 28rem no desktop e tela cheia no celular; fecha com Esc, botão ou backdrop. A página Ficha é a mesma composição em largura cheia.
- Celular: mapa rolável com zoom, células de no mínimo 32px, turno, rolagem e log empilhados abaixo do mapa.
- Teclado: `N` passa, `D` foca a rolagem, `Esc` fecha; token entra no Tab, setas movem uma célula, Shift mais setas movem cinco, Enter abre a ficha; zona focável responde a Enter e Espaço. Nenhum atalho dispara com o cursor num campo.
- Nenhuma cor nova. Sand é o que se pressiona, amber é estado e leitura viva, oxide é cautela e drag alheio, hazard é só fault plate. A hachura da névoa usa `rule-strong`.
- `DESIGN.md` ganha a seção de navegação, o componente Table map (grid, zona, névoa, token, drag marker) e a regra de que a mesa não usa o dock da música.

## 12. Critérios de aceite

### 12.1 Checklist jogável

1. **Abrir Table.** O narrador abre a Mesa, escolhe a cena Cripta e o canal da sessão. A Table nasce `open`, rodada 1, sem turno. Uma segunda Table na mesma campanha responde 409 e mostra o nome e o canal da ativa.
2. **Carregar Scene.** A cena carrega com imagem, grid e áreas. O narrador vê as áreas ocultas tracejadas; um jogador vê só o chão escuro e nenhum contorno. O jogador entra, e a lista de quem está na mesa mostra os dois com papel.
3. **Mover token.** O jogador arrasta o próprio token. O preview é local, o commit acontece no drop, e o token aparece na posição nova na tela do narrador sem recarregar. Arrastar token alheio não move nada.
4. **Revelar zona.** O narrador clica na Sala principal. A névoa sai para os dois, o nome da sala aparece, e o token que estava dentro dela entra pendente na rodada corrente.
5. **Rolar `4dF`.** O jogador rola no painel e a mensagem `**Nome** · Cripta — ... 4dF` chega ao canal antes de a linha aparecer no log. `4dF` digitado no canal entra no mesmo log. Com o Discord fora, o painel responde 502 e não grava.
6. **Editar ficha.** O jogador marca uma caixa de estresse e muda um aspecto. A alteração chega ao narrador por `sheet.changed`, e o card público não expõe a ficha.
7. **Salvar no vault.** A escrita é atômica, deixa backup em `data/vault-backups/` e o arquivo no vault mostra o bloco novo com a prosa em volta intacta. Editar a mesma consequência no Obsidian e no painel gera conflito, disco intocado e ficha somente leitura até a decisão por campo.
8. **Reiniciar e retomar.** Reiniciar o processo mantém a Table `open`, os tokens, a névoa, a rodada e o log pelo SQLite; o stream reconecta e recebe snapshot com `stream_rev` novo. Aprovar uma ficha pendente antes do restart continua `ativo` depois.

### 12.2 Por área

- **Campanha e acesso**: membro sem Sheet `ativo` cai na Mesa com faixa de pendência e não move, não rola e não conduz; espectador só vê Mesa; campanha alheia é 404; sair da guild derruba o acesso no login seguinte.
- **Ficha**: segundo Sheet em `pendente` ou `ativo` é 409; YAML inválido deixa somente leitura; chave desconhecida sobrevive à escrita; `harpi-status` ilegal é corrigido com aviso.
- **Aprovação**: aprovar grava os dois arquivos e depois a linha; falha no vault deixa `pending` e erro visível; recusa preenche a nota e o reenvio limpa.
- **Sync**: edição só no Obsidian é aceita sem conflito; só no painel é gravada; mesmo campo nos dois vira conflito; rename só troca `path`; arquivo apagado vira `ausente` e só restaura por ação; `*.sync-conflict-*` é ignorado.
- **Mesa**: um turno aberto por Table; passar para quem já agiu é 422; token oculto não participa; recarga de cena preserva névoa por `id` de zona e encerra o turno; snapshot de fechamento tem `closed` e `turn: null`.
- **Stream**: delta aplicado em ordem pelo `stream_rev`; divergência reconecta; viewer lento recebe delta maior; 17º stream recebe 429; `sheet.changed` só chega ao dono e ao narrador.
- **Rolagem**: `3#d20+5` grava três linhas e uma mensagem; a mesma mensagem processada duas vezes grava uma linha; Table fechada recusa POST com 409 e aceita GET do membro; reiniciar e reabrir mostra o log.
- **Cenas**: sobreposição junta sala, encostar cria outra; apagar corta só as células tocadas; salvar com hash de base velho é recusado; cena desenhada gera SVG e `image.path` aponta para ele.
- **Assets**: upload de PNG com EXIF é re-encodado; mesmo conteúdo não reescreve; nome com `..`, `\` ou `/` é 404; acima de 16 MB é 404; cota de 100 MB responde 413.

## 13. Riscos

| Risco | Efeito | Mitigação no desenho |
|---|---|---|
| Um worker por processo | Broadcaster, `stream_rev` e cotas quebram com mais de um worker | Deploy de um worker, escrito no ADR 0010; escala exige bus compartilhado |
| Limite de 60 req/min do NPM e NAT | Oito jogadores atrás do mesmo IP a 10 Hz tomam 429 | Zona própria de 600/min, queda para 1 Hz por 30 s sem perder movimento |
| Merge de três vias com dois escritores | Campo do mesmo lado perdido em silêncio | Hash como verdade, CAS, backup e conflito por campo; `ruamel` para preservar o arquivo |
| Ficha aberta no Obsidian com alteração não salva | Autosave grava por cima | Patch cirúrgico, CAS e backup; o pior caso vira conflito visível |
| Névoa tratada como sigilo | Jogador baixa o PNG e vê a cena inteira | Modelo de ameaça explícito no ADR 0013; não desenhar zona oculta é UX, não segurança |
| Discord fora | Painel não rola | 502 e nada gravado; log e canal nunca discordam |
| SQLite como cópia viva | Crash ou corrupção do banco | Snapshot periódico em `tables/`, backup diário com 7 cópias |
| Vault em pasta sincronizada | Conflito do Syncthing, temporário propagado | `.harpi-tmp-*` no `.stignore`, allowlist, conflito do Syncthing intocado |
| uid do host mudar | Escrita no vault falha sem causa visível | `user: "1000:1000"` fixo e checklist no ticket 11 |
| Editor de cena crescer | Vira editor de arte e atrasa o M1 | Só retângulo, sala e apagar; pincel e textura no M2 |
| SVG de mapa desenhado | Tamanho e contraste da névoa sobre imagem real | Protótipo só prova a UX; ajuste de contraste fica para a implementação |
| Log de rolagem só no SQLite | Perder banco e backups deixa só o Discord | Backup diário existente; exportação para o vault fica fora do M1 |
| Evento de watcher perdido | Ficha desatualizada no painel | Varredura de 60 s por `mtime` e tamanho |

## 14. M2 e M3

- **M2**: campanha local sobre o mesmo `CampaignAccess` e a mesma matriz de rotas, com `SheetStore` trocado; criação de campanha e convites; Atlas em Canvas com viewer somente leitura; co-narrador se couber.
- **M3**: wiki dos jogadores com manifesto em nota e markdown puro, sem Dataview nem Bases; editor de Atlas no Harpi; plugin do Obsidian; editor de arte de mapa.
- **Depois**: embed de imagem remota com allowlist e cache; WebSocket se o upload a 10 Hz virar requisito e o edge não puder mudar; exportação do log para o vault; segundo worker com bus compartilhado.

## 15. Ordem de implementação

As fatias abaixo viram issues de implementação, na ordem. Cada uma termina com `make format` e `make check` verdes.

1. **Fundação**: migração com `campaigns`, `members`, `sheet_files`, `sheet_conflicts`, `character_visibility`, seed da Paratheos; `CampaignAccess`; leitura de `HARPI_VAULT_PATH` e o 503 `vault_unavailable`.
2. **Ficha e aprovação**: parser do bloco e da config, projeção pública, criação do par, fila de aprovação, `PATCH` de ficha e de prosa.
3. **Sync do vault**: watcher, varredura, merge de três vias, conflito, backup, estados.
4. **Assets e imagens**: índice do vault, rotas de imagem, upload com sniff e cota.
5. **Cenas**: molde, galeria, editor, hash e conflito de save.
6. **Mesa**: tabelas, tokens, zonas, névoa, turno e rodada.
7. **Stream e movimento**: `table_stream`, frames, `stream_rev`, cotas, `moves`.
8. **Rolagens**: parser no painel, espelho no canal, log e `table.roll`.
9. **Painel**: casca B, páginas por campanha, gaveta de ficha, celular, teclado e as seções novas do `DESIGN.md`.

## Reconciliações

| Ticket | Ajuste registrado |
|---|---|
| 07 sobre 05 | Movimento a 10 Hz não carrega rev esperado e não responde 409; o último drop vence. `tokens.rev` continua subindo e o CAS estrutural segue valendo. |
| 08 sobre 07 | "Frames recortados por viewer" viram dois recortes, jogador e narrador; `sheet.changed` continua por assinante. |
| 10 sobre 05 | Participante do turno é o token público da cena; token oculto não abre turno, não conta e não fecha rodada. |
| 13 sobre 05 | "Sem hot reload" vira "sem edição ao vivo, com recarga explícita na Mesa"; entra `scenes.source`, na coluna e no molde, e a cena desenhada aponta para SVG em `assets/`. |
| 13 sobre 08 | O SVG de cena desenhada é gerado pelo servidor e é a exceção ao allowlist de raster: só é servido pela rota do mapa, com `nosniff` e CSP de sandbox. |
| 08 sobre 02, 03, 04 | Sheet ganha `## História` e `## Anotações`; Character do app ganha prosa do jogador; `sheet_files` ganha `status` e `owner_id`; cada seção de prosa é campo do merge. |
| 08 e 09 sobre 05 | `tables.spectators`, `character_visibility` e `rolls.scene_label` entram no schema; `sheet_conflicts` ganha `id` para a rota de resolução. |
| 01 sobre a mesa | "Ordem de turno livre" continua livre, mas a rodada fecha por contagem de participantes. |

Lacunas que esta spec fecha sem contrariar ticket nenhum:

- Nomes das rotas que os tickets citaram sem batizar: `POST /api/tables` (abrir), `POST /api/tables/<id>/close`, `POST /api/tables/<id>/reopen`, `POST /api/tables/<id>/scene/reload`, `POST /api/tables/<id>/zones/<zone>/hide`, `PATCH /api/tables/<id>/tokens/<id>`.
- `GET /api/campaigns/<slug>` passa a devolver a Table aberta, porque nenhum ticket definiu como o jogador descobre o id da mesa.
- `sheet_conflicts.id` existe para a rota `POST .../conflicts/<id>/resolve`.
- `source` entra também no JSON do molde da cena, não só na coluna: sem ele, reimportar um molde do disco perderia a distinção entre imagem e desenho.

## Decisões de origem

- [Decisões do grilling](issues/01-decisoes-do-grilling.md)
- [Esquema da ficha](issues/02-esquema-da-ficha.md)
- [Layout de Character e Sheet](issues/03-layout-character-sheet.md)
- [Sync do vault](issues/04-sync-do-vault.md)
- [Modelo de Table e Scene](issues/05-modelo-table-scene.md)
- [Limites do SSE para a mesa](issues/06-limites-do-sse.md)
- [Transporte e concorrência da mesa](issues/07-transporte-e-concorrencia.md)
- [Autorização e arquivos](issues/08-autorizacao-e-arquivos.md)
- [Rolagens espelhadas](issues/09-rolagens-espelhadas.md)
- [UX da mesa no painel](issues/10-ux-da-mesa.md)
- [Ops do vault e backup](issues/11-ops-do-vault.md)
- [Editor de cenas e zonas](issues/13-editor-de-cenas-e-zonas.md)
