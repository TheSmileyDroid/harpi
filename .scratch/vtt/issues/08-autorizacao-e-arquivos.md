# Autorização e arquivos

Type: grilling
Status: resolved
Blocked by: 03, 05

## Question

Como o painel autoriza e serve conteúdo de uma campanha?

Decidir:

- papéis: narrador, jogador, pendente; matriz de permissões por rota.
- filtro do SSE por campanha e por papel.
- rota de imagem e mapa do vault: path traversal, allowlist, cache e tamanho.
- servir imagens de `Recursos/anexos` sem copiar.
- rate limit, corpo máximo e CSRF nas rotas novas.
- o que um jogador vê de NPC e de outro PC.
- campanha local no M2 usando a mesma interface de autorização.

Resolução: matriz de permissões, regras de rota e modelo de ameaça.

## Answer

A autorização é por campanha e resolvida no SQLite. O papel não é um campo gravado: sai da combinação entre a linha em `members` e o status do Sheet, com o Sheet como verdade, como o ticket 03 fixou. Quem não é narrador recebe um recorte de mesa só, idêntico para jogador, pendente e espectador. O narrador recebe o recorte completo. A névoa é recurso de jogo, não fronteira de segurança.

### 1. Papéis

| Papel | Como o servidor reconhece |
|---|---|
| **Narrador** | `campaigns.narrator_id` é o snowflake do usuário. Co-narrador fica fora do M1. |
| **Jogador** | Linha em `members` e Sheet `ativo` desse usuário na campanha. |
| **Pendente** | Linha em `members` e nenhum Sheet `ativo`. Na prática, o Sheet do par está `pendente` ou `arquivado`. |
| **Espectador** | Não é membro e `tables.spectators = 1` na Table que ele abriu. Só existe dentro de uma Table aberta. |
| **Sem acesso** | Nenhuma das anteriores. Recebe 404 em rota de campanha. |

- Nenhuma coluna de papel. `members` guarda só `(campaign_slug, user_id, display_name, joined_at)`, como no ticket 05. Aprovar o Sheet muda o papel do usuário sem escrever em `members`.
- **Pendente** é o papel da pessoa e **ficha pendente** é o status do arquivo. O glossário do ticket 12 precisa registrar os dois termos separados.
- Ficha `arquivado` rebaixa o membro para o comportamento de pendente. Ele lê a própria ficha em somente leitura, não age na mesa, sai do elenco e do seletor de token. Desarquivar devolve o papel de jogador.
- Um membro com Sheet `pendente` mais um Sheet `arquivado` continua pendente, porque o arquivado não conta em nenhum dos dois sentidos.
- Acesso exige também a guild da campanha. O servidor confere `campaigns.guild_id` contra `user_guilds` do usuário, lista que o login regrava a cada entrada (`pages/auth.py:114-146`). Sair da guild derruba o acesso no login seguinte e a linha em `members` fica guardada para quando ele voltar.
- A autorização nunca abre arquivo do vault para decidir permissão. Status e dono do Sheet vêm de colunas espelhadas em `sheet_files` (ticket 04), escritas quando o sync aceita ou grava a ficha.

### 2. Entrada na campanha

- Convite e criação de campanha são M2 e continuam fora. No M1 a Paratheos é semeada na migração com `narrator_id` do narrador e `guild_id` da guild.
- Jogador sem linha em `members` vê a tela de entrada com "criar personagem". Criar Character e Sheet insere a linha em `members`, grava `approvals` como `pending` e nasce `pendente` nos dois arquivos, como o ticket 03 descreve.
- Aprovar é ato do narrador, grava `ativo` nos dois arquivos e muda o papel do usuário. Recusar mantém `pendente` e preenche `harpi-review-note`, que só o dono e o narrador leem.
- NPC criado pelo narrador nasce `ativo` e não passa por fila. O Sheet do NPC é opcional.
- Um Character tem no máximo um Sheet em `pendente` ou `ativo`, já decidido no ticket 03. A rota de criação recusa o segundo com 409.

### 3. O que o jogador vê de NPC e de outro PC

- De outro PC, o card público: nome, imagem, conceito e resumo. A ficha completa nunca sai do servidor para quem não é o dono nem o narrador.
- De NPC, o mesmo card público, e só depois de revelado. A ficha de NPC não é legível por jogador em nenhuma rota.
- O elenco da campanha mostra todos os personagens **revelados**: PCs `ativo` sempre, NPCs a partir do momento em que o narrador os revela. Personagem que já apareceu continua no elenco depois que o token sai da cena, para os jogadores lembrarem quem era. Personagem futuro não aparece.
- Ficha `pendente` de outro jogador não aparece no elenco, nem o nome dela. O dono vê a sua marcada como aguardando aprovação.
- Personagem `arquivado` sai do elenco, do card e do seletor de token.

#### Personagem revelado

Nova tabela, no mesmo banco do painel:

```sql
CREATE TABLE character_visibility (
    campaign_slug TEXT NOT NULL REFERENCES campaigns(slug) ON DELETE CASCADE,
    character_id TEXT NOT NULL,
    revealed_at INTEGER NOT NULL,
    revealed_by TEXT NOT NULL,
    PRIMARY KEY (campaign_slug, character_id)
);
```

- `character_id` é o `harpi-id` do Character (`chr_`) quando o app criou a nota. Para Character que é nota externa do vault e não tem id, é o `harpi-id` do Sheet que aponta para ele (`sht_`), o único id estável do par.
- A tabela guarda NPC revelado. PC com Sheet `ativo` é sempre visível, então não precisa de linha e não sai do elenco por flag. Arquivar é o jeito de tirar um PC do elenco.
- Primeira revelação acontece de dois jeitos: o narrador clica em revelar na página do personagem, ou o primeiro token daquele personagem entra numa zona revelada. A segunda é automática e grava `revealed_by = system`.
- Esconder de novo é permitido e remove a linha. Personagem revelado não volta a esconder sozinho quando os tokens saem.
- Token com `visible: false` não revela o personagem, e o card não aparece no elenco enquanto a linha não existir.
- O motivo de ser SQLite e não frontmatter: o app não pode adicionar frontmatter a nota do vault que não criou (ticket 03), então nota externa ficaria sempre escondida.

#### Prosa do Character

- O jogador edita a prosa do próprio Character quando as duas condições valem: a nota foi criada pelo app (tem `harpi-id` e `harpi-campanha` em `characters/`) e o Sheet dele aponta para ela (`harpi-character-id`).
- Character que é nota externa do vault continua exclusivo do narrador. O app nunca edita nota que não criou.
- O narrador edita qualquer Character.
- O card público lê o resumo do Character direto. Edição de prosa do jogador aparece no card sem passar pela aprovação, que aprova a mecânica, não a lore. O narrador modera editando.
- Nada de campo de dono novo no Character. O vínculo vem do Sheet, como o resto.

#### Prosa do Sheet e inventário

- O Sheet ganha duas seções de prosa depois do bloco: `## História` e `## Anotações`. O app passa a escrever nelas, e só nelas. Fora delas e do bloco, o arquivo continua byte a byte, como no ticket 04.
- Inventário continua no bloco `harpi-sheet` (`item`, `qty`, `note`, ticket 02). Adicionar, remover e alterar quantidade é edição do bloco pelo dono ou pelo narrador, sem rota nova.
- Item do inventário é wikilink para nota existente. O painel não cria nota de item no M1, e link morto aparece como texto, como o ticket 02 já fixa.

### 4. Matriz de permissões

`E` = espectador com a flag ligada. `P` = pendente.

| Rota | Narrador | Jogador | P | E |
|---|---|---|---|---|
| `GET /api/campaigns` | as suas | as suas | as suas | não |
| `GET /api/campaigns/<slug>` | sim | sim | sim | não |
| `GET /api/campaigns/<slug>/characters` | todos | cards revelados | cards revelados | não |
| `GET .../characters/<id>` | ficha inteira | própria ficha, card alheio | própria ficha, card alheio | não |
| `GET .../characters/<id>/portrait` | sim | se o card é visível | se o card é visível | não |
| `POST /api/campaigns/<slug>/characters` | qualquer (NPC) | só o próprio par | já criou | não |
| `PATCH .../characters/<id>` | qualquer | só Character criado pelo app que o Sheet dele aponta | idem | não |
| `PATCH .../sheets/<id>` | qualquer | a própria, se não arquivada | a própria, se pendente | não |
| `POST .../sheets/<id>/submit` | não | não | reenviar depois de recusa | não |
| `GET .../approvals` | fila toda | não | não | não |
| `POST .../approvals/<id>` | aprovar ou recusar | não | não | não |
| `GET .../conflicts` | fila da campanha | os próprios | não | não |
| `POST .../conflicts/<id>/resolve` | qualquer | os próprios | não | não |
| `POST .../characters/<id>/reveal` e `.../hide` | sim | não | não | não |
| `GET .../assets/<name>`, `.../images/<name>` | sim | sim | sim | não |
| `POST .../assets` (upload) | sim | sim | sim | não |
| `GET /api/tables/<id>/events` | recorte completo | recorte jogador | recorte jogador | recorte jogador |
| `GET /api/tables/<id>/summary` | sim | sim | sim | sim, com a flag |
| `GET /api/tables/<id>/map` | sim | sim | sim | sim |
| `POST /api/tables/<id>/moves` | qualquer token | só o token do próprio Sheet | não | não |
| `POST /api/tables/<id>/turns` | abrir, passar e encerrar qualquer | passar e encerrar o próprio | não | não |
| `POST /api/tables/<id>/scene` | sim | não | não | não |
| `POST /api/tables/<id>/zones/<zone>/reveal` | sim | não | não | não |
| `POST /api/tables/<id>/tokens` e `DELETE .../tokens/<id>` | sim | não | não | não |
| `POST /api/tables/<id>/spectators` | sim | não | não | não |
| abrir, fechar e reabrir Table | sim | não | não | não |
| lista de cenas, blueprint e snapshot | sim | só a cena corrente, pelo stream | idem | idem |

- Jogador move o token cujo `tokens.owner_id` é o dele e cujo `character_id` aponta para o Sheet dele. Token de personagem arquivado não é movível pelo jogador, só pelo narrador.
- Jogador encerra e passa o turno só quando o turno aberto é do token dele. Passar para quem já agiu continua 422, como no ticket 05.
- **404** para falta de escopo: campanha alheia, ficha alheia, Table de outra campanha, id inexistente. **403** para ação negada dentro do escopo: jogador tentando revelar zona, pendente tentando mover token, espectador tentando abrir card. **409** para rev de CAS e segundo Sheet. **422** para payload inválido. A escolha de 404 no escopo evita enumeração de campanhas, fichas e mesas.
- Segurança de log: 403 e 429 já caem no `security_log` por status (`src/security_log.py:32-36`), sem rota nova de auditoria.

### 5. Stream da Table

- `GET /api/tables/<id>/events` exige acesso à Table: membro da campanha, mais o narrador, mais espectador quando `tables.spectators = 1`. Table de outra campanha responde 404 mesmo para quem tem o id.
- **Dois recortes, não um por viewer.** O servidor calcula um recorte de jogador e um de narrador por Table. Todo subscriber que não é narrador recebe o recorte de jogador, bit a bit igual. Isso substitui a linha "frame filtrado por assinante" do ticket 07 e é a reconciliação registrada para o ticket 12.
- O recorte de jogador aplica as regras do ticket 05: sem token `visible: false`, sem token cujo centro cai em zona não revelada, sem token fora de zona quando `fog_outside = true`. O narrador recebe tudo.
- `sheet.changed` é a exceção e continua por assinante: só o dono do Sheet e o narrador recebem o evento. Jogador não recebe evento de ficha alheia, nem de ficha `pendente`, nem o `sheet_id` dela.
- A lista de quem está na mesa (`table.viewers`) é a mesma para todos e mostra nome de exibição e papel (`narrador`, `jogador`, `pendente`, `espectador`), nunca o snowflake. Espectador aparece marcado.
- `table.closed` encerra o stream. Reconectar numa Table fechada responde 404.
- Cotas do ticket 07 valem sem mudança: 16 streams por Table, 2 por usuário, contador próprio. Espectador e pendente contam como viewer.
- A flag de espectador é coluna nova em `tables`:

```sql
ALTER TABLE tables ADD COLUMN spectators INTEGER NOT NULL DEFAULT 0
    CHECK (spectators IN (0, 1));
```

Ligada, qualquer usuário autenticado de guild permitida com acesso à guild da campanha abre `summary`, `map` e `events` daquela Table. Desligada, só membros. Não existe link anônimo nem token de convite.

### 6. Rotas de asset

Nenhuma rota aceita caminho de vault vindo do cliente. O servidor resolve o arquivo pelo banco ou por um índice de nomes.

| Rota | Resolve |
|---|---|
| `GET /api/tables/<id>/map` | `current_scene.image_path`, só a cena corrente da Table |
| `GET /api/campaigns/<slug>/characters/<id>/portrait` | `harpi-portrait`, depois `imagem`/`image` do frontmatter, depois o primeiro embed `![[...]]` do corpo |
| `GET /api/campaigns/<slug>/assets/<name>` | upload do M1 em `Harpi/Campaigns/<slug>/assets/` |
| `GET /api/campaigns/<slug>/images/<name>` | imagem do vault por nome de arquivo, para embed de prosa e picker |
| `POST /api/campaigns/<slug>/assets` | upload novo |

- `image_path` é relativo à raiz do vault e pode apontar para `Recursos/anexos`. O arquivo é servido onde está, sem copiar, mover ou redimensionar, como o ticket 05 fixa.
- `.../images/<name>` e `.../assets/<name>` recebem nome, não caminho: `name` passa por `^[a-z0-9][a-z0-9._-]{0,127}$` para assets e pelo charset do índice para imagens do vault. Sem `/`, sem `\`, sem `..`. A resolução é pelo índice em memória, então um nome que não existe no índice é 404 antes de qualquer `open`.
- Índice do vault: caminho relativo, mtime, tamanho e nome de arquivo, construído no boot e atualizado pela varredura de 60 s do ticket 04. Nome duplicado resolve pelo caminho mais curto, regra do Obsidian. Nada de listagem de diretório.
- Defesa em profundidade mesmo sem caminho no request: `realpath` do alvo precisa continuar sob a raiz do vault, cada componente não pode começar com `.` nem `~`, o alvo precisa ser arquivo regular, e a extensão precisa estar em `png`, `jpg`, `jpeg`, `webp`. Symlink só passa se o `realpath` ficar dentro da raiz. SVG fica fora porque carrega script.
- Imagem acima de 16 MB, ausente, fora da allowlist ou fora da raiz responde 404, sem dizer qual das quatro coisas aconteceu. O maior PNG do vault tem 4 MB.
- Cache: `Cache-Control: private, max-age=60, must-revalidate`, `ETag` do par mtime mais tamanho, `Last-Modified` e 304 em `If-None-Match`. Nunca `public`. `X-Content-Type-Options: nosniff` já vem global de `app.py:103-115`, e o `Content-Type` vem da extensão, nunca do conteúdo.
- O CSP atual já permite `img-src 'self'`, então as rotas funcionam sem afrouxar header. URL remota em `image:` é ignorada. Sem imagem, o card mostra iniciais.

#### Upload

- `POST /api/campaigns/<slug>/assets`, multipart, membro ou narrador, espectador não. Destino exclusivo `Harpi/Campaigns/<slug>/assets/`, que entra na árvore do ticket 03.
- Allowlist `png`, `jpg`, `webp` por sniff dos primeiros bytes, não pelo nome. Teto de 16 MB por arquivo. Re-encoda para remover EXIF antes de gravar.
- Nome é `sha256` do conteúdo mais a extensão. Arquivo com o mesmo hash não é reescrito. O app nunca apaga nem renomeia asset.
- Upload não vira hospedagem: a rota de leitura só serve arquivo que o banco referencia (imagem de cena, retrato, embed em prosa de ficha). Asset órfão fica no disco e não é servido.
- Cota por campanha de 100 MB, somando `assets/`. Acima disso, 413 com mensagem. O vault inteiro tem 69 MB hoje.

### 7. Defesas de borda

**CSRF.** Guard novo nos blueprints de campanha e mesa, no `before_request`: para `POST`, `PATCH` e `DELETE`, exigir `Content-Type: application/json` (ou `multipart/form-data` só na rota de upload) e `Sec-Fetch-Site: same-origin`, aceitando `same-site` apenas quando o `Origin` bater com o host confiável. Sem o header, exigir `Origin` igual ao host. Falha vira 403 `forbidden`. GET não muta. A API de música fica intocada, porque o cookie já é `SameSite=Lax` e mudar todas as rotas existentes não é escopo deste ticket.

**Corpo.** `MAX_CONTENT_LENGTH` global sobe de 64 KB para 16 MB mais 64 KB, porque o Quart aplica o limite antes da rota e o upload precisa passar. Cada rota JSON checa `request.content_length` antes de ler e responde 413: moves 16 KB, escrita de ficha 64 KB, prosa de Character 64 KB, upload 16 MB. No NPM, `client_max_body_size` sobe para `17m` só em `location /api/campaigns/`, e fica `64k` no resto.

**Rate limit.** Buckets por usuário, no molde de `SEARCH_BUCKETS` (`pages/api.py:42-45`):

| Rota | Limite |
|---|---|
| moves | 600/min, já no ticket 07 |
| escrita de ficha e prosa | 60/min |
| leitura de elenco e card | 120/min |
| assets (GET) | 300/min |
| upload | 10/min |
| aprovação e recusa | 30/min |

429 leva `Retry-After` e o painel mostra o estado de rede limitada, como no ticket 07.

**Edge.** Duas locations novas em `deploy/npm/harpi-advanced.conf`, ambas por IP, com `proxy_buffering off` e os timeouts de 1 h que já valem no server: `/api/tables/` com `rate=600r/m burst=30` (ticket 07) e `/api/campaigns/` com `rate=300r/m burst=60`, esta com `client_max_body_size 17m`. O limite de 60 req/min de `/api/` hoje (`deploy/npm/harpi-advanced.conf:26`) não serve para assets nem para o stream.

**Vault ausente.** Enquanto `HARPI_VAULT_PATH` não estiver configurado ou a raiz não existir (ticket 11), rotas de ficha, elenco, card e asset respondem 503 `vault_unavailable`, e o painel mostra banner. Table, stream, turno e rolagem continuam, porque vivem no SQLite. `HARPI_VAULT_PATH` entra em `src/config.py` e a leitura da raiz é feita uma vez no boot, como `WORK_DIR` já é.

### 8. Modelo de ameaça

O que este desenho protege e o que aceita:

- **Protege** ficha alheia, ficha pendente, campanha alheia, cena futura, nota do vault fora do que o card mostra, e escrita fora de `Harpi/Campaigns/<slug>/`.
- **Aceita** que a névoa não é sigilo. Quem tem acesso à Table baixa o PNG inteiro e pode olhar as zonas escondidas. Recorte por viewer destruiria o cache e custaria CPU por request, e a mesa é entre amigos na mesma guild. Fica escrito aqui e no ADR para ninguém tratar névoa como controle de acesso.
- **Aceita** que espectador com a flag ligada vê a mesa, os tokens e os rótulos, sem ficha. A flag é opt-in e o narrador desliga quando quiser.
- **Não protege** contra o próprio jogador copiando o que vê. Não há marca d'água, não há download proibido, não há bloqueio de print.
- **Não protege** contra alguém com acesso ao host ou ao Syncthing. O vault é arquivo comum no disco, e isso é o ticket 11.
- A allowlist de guild continua sendo o portão de entrada, e a guild da campanha é conferida de novo em toda rota. Um login de outra guild permitida não alcança a Paratheos.

### 9. Campanha local no M2

- Um resolvedor único, `CampaignAccess`, sobre SQLite: `campaigns`, `members`, `sheet_files.status` e `sheet_files.owner_id`, `character_visibility`, `tables.spectators`. Nenhuma rota lê o vault para autorizar.
- `campaigns.content_source` (`vault` ou `local`, já no ticket 01) escolhe a implementação de `SheetStore`: arquivos do vault por um lado, linhas SQLite pelo outro. A matriz de permissões e os recortes de stream não mudam, porque não falam de arquivo.
- Campanha local nasce no M2 com as mesmas tabelas e o mesmo `CampaignAccess`. O que muda é quem escreve as linhas de `sheet_files` e se existe `HARPI_VAULT_PATH` para consultar.
- Consequência: nenhuma rota ganha `if vault` ou `if local`. A diferença fica em uma camada abaixo da autorização.

### 10. Reconciliações com tickets fechados

| Ticket | Ajuste |
|---|---|
| 02 | O Sheet ganha `## História` e `## Anotações` como campos de prosa do app. O resto do modelo do bloco fica igual. |
| 03 | Character criado pelo app passa a ter prosa editável pelo jogador dono do Sheet. Character externo continua do narrador. A árvore ganha `assets/`. |
| 04 | Cada seção de prosa é um campo do merge de três vias (base, painel, vault). Fora do bloco e das seções, o patch continua cirúrgico. |
| 05 | `tables` ganha `spectators`. `character_visibility` é tabela nova. `sheet_files` ganha `status` e `owner_id`. |
| 07 | "Frames recortados por viewer" vira dois recortes, jogador e narrador. `sheet.changed` continua por assinante. `stream_rev`, cadência e cotas não mudam. |

### 11. Glossário e ADR para o ticket 12

Termos novos:

- **Narrador**: o `narrator_id` da campanha. Não confundir com **Dono da ficha**.
- **Jogador**: membro com Sheet `ativo`.
- **Pendente**: membro sem Sheet `ativo`. Distinto de **ficha pendente**, que é status de arquivo.
- **Espectador**: usuário sem vínculo com a campanha que assiste a uma Table com `spectators` ligado.
- **Personagem revelado**: NPC que entrou no elenco visível, por ação do narrador ou primeira aparição em zona revelada.
- **Card público**: nome, imagem, conceito e resumo. Já existe no ticket 02.
- **Acesso à Table**: a condição que libera stream, mapa e summary. Membro ou espectador com flag.

ADR candidato, **Autorização por campanha**: papéis derivados do Sheet, dois recortes de stream, névoa fora do modelo de ameaça, assets sem caminho de cliente. Tem as três características que justificam ADR: difícil de reverter, surpreendente para quem espera névoa como sigilo, e resultado de um trade-off real contra o filtro por viewer do ticket 07.

### 12. Fica para outros tickets

- Quem pode rolar e o formato do log: ticket 09.
- Tela de aprovação, editor de prosa, alternância de espectador e visão do narrador: ticket 10. O editor escolhido é **Wordgard** montado só nas seções que o app possui, com schema enxuto e markdown canônico, mais upload de imagem. Isso acrescenta um slice de implementação à spec, não uma rota de autorização nova.
- Bind mount, `HARPI_VAULT_PATH`, retenção e checklist de disco: ticket 11.
- Grade de tokens, parede e linha de visão continuam fora do M1.
