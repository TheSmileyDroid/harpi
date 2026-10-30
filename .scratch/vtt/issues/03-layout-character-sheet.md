# Layout de Character e Sheet

Type: grilling
Status: resolved
Blocked by: 02

## Question

Onde Character e Sheet vivem no vault, e como a ficha ganha dono e aprovação?

Decidir:

- uma nota por personagem com o bloco `harpi-sheet`, ou duas notas (Character e Sheet) ligadas por wikilink.
- caminhos em `Harpi/Campaigns/<slug>/` para personagens, fichas, mapas e snapshots.
- frontmatter mínimo: tipo, campanha, personagem, dono, status, rev.
- ciclo `pendente -> ativo -> arquivado`, quem aprova e o que aparece no vault antes da aprovação.
- jogador cria do zero; narrador cria ficha de NPC e pode anexar ficha a Character existente.
- como o link é resolvido quando o narrador move a nota no Obsidian.

Resolução: layout de arquivos, frontmatter e fluxo de aprovação.

## Answer

Character e Sheet são notas separadas. Character guarda identidade e lore, Sheet guarda o estado jogável, e o vínculo mora só no Sheet. O app escreve apenas em `Harpi/Campaigns/<slug>/`, então uma ficha pode apontar para uma nota que já existe no vault sem que essa nota seja tocada.

### Árvore de arquivos

```text
Harpi/Campaigns/paratheos/
├── config.md
├── characters/
│   └── <Nome>.md
├── sheets/
│   └── <Nome>.md
├── scenes/
└── tables/
```

- `config.md` fica na raiz da campanha, como decidido em "Esquema da ficha".
- `characters/` e `sheets/` são pastas irmãs por tipo, não uma pasta por personagem.
- `scenes/` guarda as cenas e `tables/` os snapshots de mesa. O conteúdo das duas é decidido em "Modelo de Table e Scene" e "Ops do vault", aqui só se fixa o nome.
- O nome do arquivo é o nome de batismo. Mudança de nome na ficção não renomeia arquivo.
- `<slug>` é minúsculo, imutável e igual em três lugares: pasta, `harpi-campanha` e a config. Paratheos usa `paratheos`.
- Nada é copiado para a campanha. Imagens e notas do mundo continuam onde estão e são referenciadas.

### Frontmatter do Character

```yaml
---
tipo: personagem
harpi-id: chr_k3m9
harpi-campanha: paratheos
harpi-status: ativo
harpi-rev: 4
aliases: []
tags:
  - personagem
---
```

| Chave | Quem escreve | Valor |
|---|---|---|
| `tipo` | app, na criação | sempre `personagem` |
| `harpi-id` | app, uma vez | imutável, prefixo `chr_` |
| `harpi-campanha` | app | slug da campanha |
| `harpi-status` | app | espelho do status do Sheet |
| `harpi-rev` | app, a cada escrita | inteiro crescente |
| `aliases`, `tags` | app e Obsidian | convenção do vault, preservados |

Character não tem dono. A lore pertence à campanha, e quem edita é o narrador.

### Frontmatter do Sheet

```yaml
---
tipo: ficha
harpi-id: sht_p2x7
harpi-campanha: paratheos
harpi-character: "[[IR1S]]"
harpi-character-id: chr_ab12
harpi-owner: "284712345678901234"
harpi-owner-name: leandro
harpi-status: ativo
harpi-rev: 9
harpi-review-note: ""
---
```

| Chave | Quem escreve | Valor |
|---|---|---|
| `tipo` | app, na criação | sempre `ficha` |
| `harpi-id` | app, uma vez | imutável, prefixo `sht_` |
| `harpi-campanha` | app | slug da campanha |
| `harpi-character` | app | wikilink para o Character, por nome ou caminho |
| `harpi-character-id` | app | id do Character, ausente quando o alvo é uma nota do vault sem id |
| `harpi-owner` | app | snowflake do Discord, a verdade do dono |
| `harpi-owner-name` | app, a cada escrita | nome de exibição derivado, nunca editado à mão |
| `harpi-status` | app | `pendente`, `ativo` ou `arquivado` |
| `harpi-rev` | app, a cada escrita | inteiro crescente |
| `harpi-review-note` | app, na recusa | texto do narrador, vazio significa sem pendência |

Chaves desconhecidas e prosa em volta são preservadas, como já vale para o bloco `harpi-sheet`.

### Ciclo de status

- Jogador cria Character e Sheet juntos. Os dois nascem `pendente`, `harpi-owner` é o próprio jogador, `harpi-rev: 1`.
- Antes da aprovação o par já existe no vault. O dono vê e edita a própria ficha, outros jogadores não veem nada dela, o narrador vê na fila de aprovação.
- Aprovação é ato do narrador. Co-narrador fica fora do M1.
- Aprovar grava `ativo` nos dois arquivos na mesma transação. O status do Sheet é a verdade e o do Character é espelho.
- Recusar mantém `pendente` e preenche `harpi-review-note`. O dono corrige e reenvia, e o reenvio limpa a nota.
- NPC criado pelo narrador nasce `ativo` e não passa por fila. O Sheet do NPC é opcional e, quando criado, também nasce `ativo`.
- `arquivado` sai do elenco, do card público e do seletor de token, e a ficha vira somente leitura. Token que já está numa cena permanece nela até o narrador remover. Desarquivar é voltar para `ativo`.
- Um Character tem no máximo um Sheet em `pendente` ou `ativo`. Sheet arquivado não conta, então é possível criar outro depois.

### Anexar ficha a um Character que já está no vault

Character tem duas origens: criado pelo app em `characters/`, ou uma nota `tipo: personagem` que já existe em qualquer pasta do vault.

- O narrador escolhe uma nota `tipo: personagem` do vault, inclusive fora de `Harpi/Campaigns/`.
- O app cria apenas `Harpi/Campaigns/<slug>/sheets/<Nome>.md`, com `harpi-character: "[[Nome da nota]]"` e sem `harpi-character-id`.
- A nota do vault não é movida, copiada nem editada. Nome, imagem, conceito e resumo do card público vêm dela pela leitura do parser de notas do vault.
- O status do par mora no Sheet, porque é o único arquivo do par dentro da campanha.
- Se a nota do vault for renomeada, o vínculo se refaz pelo nome novo ou por um alias. Se for apagada, o Sheet fica órfão.

### Resolução do vínculo

1. `harpi-character-id`, quando presente, resolve contra `characters/` da campanha.
2. Sem id, o alvo do wikilink resolve por nome de arquivo exato e depois por alias, em todo o vault.
3. Ambiguidade ou alvo ausente deixa o Sheet órfão: a ficha continua editável, mostra um chip de personagem não encontrado e entra na fila do narrador. O app nunca apaga a ficha.
4. Quando a resolução por nome encontra o arquivo em outro caminho, a próxima escrita do Sheet reescreve o wikilink para o caminho atual. O app não reescreve na hora em que o watcher vê o movimento e não renomeia nem move arquivo nenhum.

### O que o app nunca faz

- Escrever fora de `Harpi/Campaigns/<slug>/`.
- Adicionar frontmatter a nota do vault que ele não criou.
- Renomear ou mover arquivo.
- Criar segundo Sheet enquanto existir um `pendente` ou `ativo` para o mesmo Character.
- Apagar Sheet. Arquivar é o fim de linha.

### Fica para outros tickets

- Semântica de `harpi-rev`, merge e conflito: "Sync do vault".
- Matriz de permissões por rota, inclusive o que a fila de aprovação expõe: "Autorização e arquivos".
- Conteúdo de `scenes/` e `tables/`: "Modelo de Table e Scene" e "Ops do vault".
- Retrato enviado pelo jogador, cache e limite de imagem: névoa do mapa.
- `ficha` como termo do glossário: "Spec, glossário e ADRs".
