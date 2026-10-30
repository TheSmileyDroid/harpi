# Sync do vault

Type: grilling
Status: resolved
Blocked by: 03

## Question

Como o app e o Obsidian escrevem na mesma ficha sem perder edição?

Decidir:

- watcher do vault (inotify) e debounce.
- `harpi-rev`, hash da última versão lida e merge por campo.
- o que acontece quando o mesmo campo mudou dos dois lados.
- escrita atômica (temp mais rename) e backup antes de sobrescrever.
- arquivo apagado, renomeado ou substituído pelo Syncthing.
- nota aberta no Obsidian com alteração não salva.
- o que o merge preserva: prosa, chaves desconhecidas, ordem.
- como o usuário vê o diff e decide.

Resolução: protocolo, estados de conflito e mensagens.

## Answer

O arquivo tem dois escritores que não se conhecem: o painel e o Obsidian. Editor reescreve a nota inteira a partir do buffer, então o merge existe para o app não perder a marcação feita na mesa quando o autosave do Obsidian grava por cima, e para o app não apagar a edição de fora. A verdade da mudança é o hash do arquivo. `harpi-rev` é só o carimbo da última escrita do app.

### Problema que o protocolo resolve

Sessão ao vivo, ficha aberta no Obsidian do narrador, jogador marcando estresse no painel. O app grava o estresse. Segundos depois o autosave do Obsidian grava a nota inteira com o estresse velho. Sem merge por campo, a marcação some a cada sessão. O mesmo vale para edição feita com o app desligado e sincronizada depois pelo Syncthing.

### Leitura: watcher e detecção

- Observer inotify (`watchdog`) na subárvore `Harpi/Campaigns/` do vault, com debounce de 500 ms por caminho.
- Varredura completa no boot e a cada 60 s, comparando `mtime` e tamanho, para cobrir evento perdido em restart, rename do Syncthing ou bind mount que não entrega evento. Hash só é calculado quando mtime ou tamanho muda.
- Allowlist estreita: só `characters/*.md` e `sheets/*.md`. Ficam de fora `scenes/`, `tables/`, `config.md`, dotfiles, dotdirs, `*.tmp`, `~syncthing~*` e `*.sync-conflict-*`.
- `*.sync-conflict-*` do Syncthing é ignorado e não vira ficha. Duas versões divergentes não podem ser as duas verdade; o narrador vê o aviso e resolve no Obsidian.
- `config.md` não entra no merge: mudança é lida pela varredura de 60 s e recarrega a config da campanha, sem escrita. A escrita à mão no Obsidian é a única fonte, como fixado em "Esquema da ficha".
- A escrita do próprio app volta como evento e é descartada por hash igual ao gravado, sem debounce extra.

### Detecção de mudança

- A verdade é `sha256` do arquivo inteiro na última leitura aceita. Hash igual ao gravado significa "sem mudança" ou "eco da minha escrita". Hash diferente significa mudança externa.
- `harpi-rev` sobe só quando o app escreve, e serve para exibir há quanto tempo o painel mexeu. Edição no Obsidian não incrementa, então rev nunca é usado como detector.
- Comparar mtime e tamanho sozinho não basta: edição que preserva tamanho e a resolução de mtime passa despercebida, e o Syncthing preserva mtime em alguns fluxos.

### Estado guardado no app

Uma migração nova em `src/storage/migrations/`, duas tabelas.

`sheet_files`:

| Coluna | Conteúdo |
|---|---|
| `path` | caminho relativo ao vault, chave do registro |
| `harpi_id` | id do frontmatter, `chr_` ou `sht_` |
| `campaign` | slug |
| `rev` | último rev escrito pelo app |
| `hash` | sha256 da última versão aceita |
| `last_text` | texto integral da última versão aceita |
| `base_json` | bloco e frontmatter já parseados, para o merge de três vias |
| `state` | `ok`, `conflito`, `ausente`, `invalido` ou `desconhecido` |
| `updated_at` | quando o app aceitou a versão |

`sheet_conflicts`: `path`, `field_path`, `base`, `ours`, `theirs`, `created_at`, `resolved_at`, `resolved_by`.

`last_text` existe para devolver a ficha inteira quando o arquivo é apagado. `base_json` sozinho recriaria só o bloco e perderia frontmatter, prosa e imagem. Cada ficha tem poucos KB.

### Escrita

- Uma fila por arquivo, coalescendo edições por 300 ms. Dois cliques em caixas de estresse viram uma escrita. Fichas diferentes não esperam umas pelas outras.
- Escrita atômica: temporário `.harpi-tmp-<pid>` na mesma pasta, `flush`, `fsync`, `os.replace`. Nunca grava direto no arquivo final.
- Antes de sobrescrever, cópia byte a byte da versão anterior em `data/vault-backups/<slug>/<harpi-id>/<rev>-<timestamp>.md`, retenção de 20 por arquivo. Fora do vault, então não entra no Syncthing nem polui a campanha, e sobrevive a alguém apagar a pasta no Obsidian.
- Compare-and-swap: o hash lido no começo da escrita é comparado com o do disco na hora de gravar. Mudou, remergeia e tenta de novo, até 3 vezes. Na terceira falha vira conflito.
- Patch cirúrgico, sem re-serializar a nota. Só as chaves de frontmatter que o app possui e o bloco `harpi-sheet` são trocados no lugar. O resto do arquivo fica byte a byte.
- YAML lido e escrito em modo round-trip (`ruamel.yaml`, dependência nova) para preservar comentário, ordem e citação dentro do bloco. O bloco é reescrito com indentação de 2 espaços, que é a forma do exemplo do ticket 02.
- Fim de linha é preservado como lido. O vault é LF hoje.
- `harpi-rev` gravado é o `rev` guardado mais 1. Um autosave do Obsidian com rev velho é corrigido na escrita seguinte.

### O que o merge preserva

- Prosa antes e depois do bloco, headings, wikilinks, embeds, blocos Dataview.
- Chaves de frontmatter desconhecidas, `aliases`, `tags`, comentários e a ordem em que estão.
- Dentro do bloco: chaves desconhecidas, ordem dos itens e comentários.
- O app nunca escreve fora do bloco e das chaves `tipo`, `harpi-*`.

### Merge de três vias

Base é a última versão aceita (`base_json`), nosso é o que o painel quer gravar, deles é o que está no arquivo agora.

Identidade de item de lista é o rótulo, nunca a posição:

| Lista | Chave |
|---|---|
| `aspects` | `label` mais posição entre rótulos iguais |
| `skills` | `name` |
| `stunts` | `name` |
| `stress` | `track` e `value` da caixa |
| `consequences` | `severity` |
| `extras` | `kind` e `name` |
| `inventory` | `item` |

Inserir ou reordenar no Obsidian não conflita com edição de outro item. Renomear a chave vira remoção mais adição, e só conflita se o outro lado mexeu no mesmo item.

Resultado por campo:

- Só deles mudou: aceita o valor do arquivo, sem conflito. É o caso do narrador ajustando consequência enquanto ninguém toca nela no painel.
- Só nosso mudou: grava o valor do painel.
- Nenhum mudou: nada a fazer.
- Os dois mudaram para valores diferentes: conflito naquele campo, arquivo intocado.
- Os dois mudaram para o mesmo valor: aceita, sem conflito.

Caso de aceitação: narrador insere aspecto novo no topo no Obsidian, jogador reescreve "Fantasma na Rede" no painel. O app casa por rótulo, grava o texto novo e mantém o aspecto inserido. Um conflito de estresse não impede gravar aspecto, porque a decisão é por campo.

### Conflito

- O arquivo no disco não é tocado. O painel mostra chip de conflito, diff lado a lado por campo (base, vault, painel) e botões `usar do vault` e `usar do painel`, mais `manter os dois` em campo de texto.
- `manter os dois` mantém o valor do painel no item original e cria um item novo com o rótulo repetido e o texto do vault. Em `aspects`, um sexto aspecto com o mesmo `label`. Nada é concatenado.
- A ficha fica somente leitura até resolver, inclusive para o dono. Mesa, card público e token continuam no último snapshot aceito.
- Resolver grava o arquivo mesclado de uma vez, com rev novo e backup, e volta para `ok`.
- O narrador vê a fila de conflitos da campanha e resolve por procuração. O dono só resolve a própria ficha.
- Conflito não é escrito no arquivo. Nenhum marcador de conflito em frontmatter, para não invadir o ciclo `pendente`/`ativo`/`arquivado` do ticket 03 e não escrever no arquivo justamente quando o disco deve ficar intacto. O estado vive só no SQLite.

### Estados

| Estado | Significa | Sai quando |
|---|---|---|
| `ok` | hash e base em dia | qualquer mudança externa ou escrita |
| `conflito` | mesmo campo mudou dos dois lados | decisão campo a campo |
| `ausente` | arquivo sumiu do disco | `restaurar` ou `esquecer` |
| `invalido` | YAML não parseia | arquivo corrigido |
| `desconhecido` | `harpi-id` novo, ausente ou duplicado | narrador adota ou conserta |

- `ausente`: o snapshot continua servindo card, token e leitura, tudo somente leitura. `restaurar` regrava `last_text` com rev novo, atômico e com backup. O app nunca restaura sozinho, porque isso desfaz remoção intencional e briga com o Syncthing no meio da sincronização.
- `invalido`: modelo do ticket 02. Somente leitura, erro visível, e o app nunca sobrescreve bloco que não parseou.
- Rename de ficha é detectado pelo mesmo `harpi-id` e só atualiza `path`, sem reescrever nada. O app não renomeia nem move arquivo.
- `harpi-id` editado ou removido à mão: o registro antigo vira `ausente` e o arquivo entra como `desconhecido`, com aviso. Dois arquivos com o mesmo id: o mais antigo por `rev` e hash mantém o vínculo, o outro é sinalizado como duplicata e fica intocado. O app nunca escolhe sozinho qual é o verdadeiro.
- Primeira adoção de ficha que já existia no vault: base é o arquivo como lido, estado `ok`, sem conflito.

### Identidade e status escritos à mão

- `harpi-status` editado à mão é aceito quando a transição é legal: `ativo` para `arquivado` e a volta. O app sincroniza o espelho no Character. O narrador arquiva pelo Obsidian e a ficha sai da mesa.
- Transição ilegal, como `pendente` para `arquivado` sem passar por aprovação, é corrigida com aviso.
- `harpi-id`, `harpi-campanha` e `harpi-owner` são do app. Edição à mão é ignorada e corrigida na escrita seguinte, com aviso no painel.

### Nota aberta no Obsidian com alteração não salva

O app não enxerga o buffer do Obsidian e não tenta adivinhar. O protocolo absorve o pior caso: patch cirúrgico toca só o campo alterado, CAS pega a gravação concorrente, backup guarda o que havia, e o que sobrar de divergência vira conflito visível em vez de perda silenciosa. O painel nunca mantém estado de ficha só em memória. Não existe trava nem arquivo de lock: lock em pasta sincronizada vira lixo quando um dos lados cai.

### Mensagens no Discord

- Uma mensagem por ficha em conflito no canal da Table, mencionando dono e narrador, com o nome da ficha, os campos em conflito e o link do painel.
- Uma mensagem por ficha `ausente` e uma por ficha `invalido`, no mesmo canal, uma vez cada. Sem mensagem para merge silencioso.
- Resolver edita a mensagem para `resolvido por <nome>`, sem repostar. Uma ficha com cinco campos em conflito gera uma mensagem, não cinco.

### Relação com o Character

Cada arquivo do par tem hash, rev e estado próprios. O par não é transação de sync: o Character pode estar `ok` com o Sheet em `conflito`. Aprovação e arquivamento continuam gravando os dois na mesma transação do ticket 03. O status do Sheet é a verdade e o do Character é espelho; o espelho é reescrito na próxima escrita aceita do Character.

### Fica para outros tickets

- Bind mount, `HARPI_VAULT_PATH`, retenção no host e checklist de disco: "Ops do vault e backup".
- Quem vê a fila de conflitos e a ficha somente leitura: "Autorização e arquivos".
- Como o conflito aparece na mesa e o frame que atualiza a ficha: "UX da mesa no painel" e "Transporte e concorrência da mesa".
- Termos `conflito`, `ausente`, `base` e o ADR do sync: "Spec, glossário e ADRs".
