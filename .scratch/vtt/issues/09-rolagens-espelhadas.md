# Rolagens espelhadas

Type: grilling
Status: resolved
Blocked by: 05

## Question

Como uma rolagem entra no log da Table e aparece nos dois lados?

Decidir:

- Table presa ao canal: rolagem no canal entra na campanha.
- rolagem no painel vira mensagem no canal.
- formato da mensagem e do log: `4dF`, resultado, autor, cena.
- deduplicação e ordem.
- rolagens fora do canal ou antes da Table abrir.
- quem pode rolar o quê.
- retenção do log.

Resolução: protocolo, formato e regras de borda.

## Answer

Rolagem é uma linha em `rolls`, escrita uma vez, com o texto congelado. O Discord é o canal da mesa e o painel espelha. As duas superfícies produzem a mesma linha e a mesma mensagem, sem token, sem rolagem secreta e sem expurgo.

### 1. O que é uma rolagem

Uma **rolagem** é uma avaliação aceita de uma expressão de dados dentro de uma Table aberta. Erro de parser (`1d0`), expressão sem dado (`2+2`) e `!monte` não são rolagem.

- **Canal**: expressão solta (`4dF`) e o comando `!d` (aliases `!dado`, `!rolar`, `!roll`, `!r`, `!math`, `!calc`, `!m`, `src/cogs/dice_cog.py:27-34`) gravam quando o `channel_id` é de uma Table `open`. Fora disso o bot responde como hoje e não grava: outro canal, DM, guild sem campanha, Table fechada, antes de abrir.
- **Painel**: a mesma expressão do canal, sem prefixo. `N#` grava N linhas e uma mensagem, como no canal. Expressão sem dado é `422 no_dice`.
- **Bots e webhook**: ignorados. O listener hoje responde a qualquer autor que não seja o próprio bot (`dice_cog.py:17-25`); passa a sair cedo em `message.author.bot`, que também cobre webhook.
- **Repetição `N#`**: uma linha por avaliação. `3#d20+5` grava três linhas, e só a primeira guarda o `discord_message_id`; as outras ficam NULL. A dedupe consulta a mensagem uma vez e o índice único do ticket 05 continua valendo. Limite de 10 repetições.
- **Limites da expressão**: até 120 caracteres, até 20 dados por grupo, resultado inteiro. `1d6/2` é `422 non_integer_result`, porque `rolls.total` é INTEGER no ticket 05. Acima do limite é `422 too_many_dice` ou `422 expression_too_long`.

### 2. Autor, papel e vínculo

| Superfície | Quem rola |
|---|---|
| Painel | narrador e jogador. Pendente e espectador recebem 403 `forbidden` |
| Discord | quem consegue escrever no canal da Table |

- Fora da campanha, Table de outra campanha ou id inexistente é **404**, como no ticket 08. Table fechada no painel é **409 `table_closed`**.
- No canal, rolagem de quem não tem linha em `members` grava com `actor_id` NULL e `actor_label` do nome de exibição. O canal é a mesa e a permissão do Discord é o portão. Rolagem de membro grava o snowflake.
- **Sem vínculo com token.** `actor_label` é sempre quem rolou. O narrador rola como narrador, inclusive quando a rolagem é para um NPC.
- `turn_id` é preenchido quando o turno aberto pertence a um token da cena corrente cujo `owner_id` bate com o autor. É contexto, não permissão: rolar não exige o turno.
- Consequência: não existe rolagem secreta. Toda rolagem do painel vira mensagem pública no canal, então esconder a mesma linha do recorte de jogador seria teatro. `table.roll` vai para os dois recortes do ticket 08, bit a bit igual.

### 3. Caminho do painel

`POST /api/tables/<table_id>/rolls`, corpo `{"expression": "4dF+2"}`, guarda CSRF e limite de corpo do ticket 08.

1. Resolve acesso, confere `status = 'open'`, valida a expressão e avalia.
2. Posta a mensagem no canal pelo loop do bot (`run_on_bot_loop`, `src/bot_state.py:33`).
3. Insere as linhas já com o id da mensagem do bot.
4. Publica `table.roll` por linha.
5. Responde `200 {"rolls": [...]}`.

Falha do Discord dá **502 `discord_unavailable`** e nada é gravado nem transmitido. Log e canal nunca discordam, sem coluna de entrega e sem retry. Se a Table fechar entre a conferência e o POST, a rolagem ainda entra: a mensagem já está no canal e o log precisa refletir o canal.

Duplo clique não vira duplicata: o botão fica travado enquanto o POST está em voo e não há chave de idempotência. Dois cliques depois da resposta são duas rolagens de verdade.

### 4. Caminho do canal

No thread do bot, `on_message` resolve a Table por `tables.channel_id` com `status = 'open'`. Sem Table, nada muda. Com Table, avalia, atravessa para o loop do Quart, confere acesso e cena, insere, publica `table.roll` e devolve o texto para o `message.reply`.

- **Por que atravessar**: o `Database` guarda uma única conexão `aiosqlite` aberta no loop do Quart (`src/storage/database.py:14-32`) e o bot roda em outro loop e outra thread (`src/discord_bot.py:53-75`). O broadcaster do ticket 07 também é memória do processo no loop do Quart. O caminho precisa de um `run_on_panel_loop`, espelho do `run_on_bot_loop`, para não usar a conexão fora do loop dela.
- **Dedupe**: confere `discord_message_id` antes de inserir; `rolls_one_per_discord_message` (ticket 05) é a rede. Reprocessar a mesma mensagem não faz nada.
- **Resposta**: continua `message.reply`, agora com a linha espelhada da seção 5.

### 5. Formato

`text` guarda o corpo congelado, exatamente como o parser imprime hoje (`src/harpi_lib/math/parser.py:279-309`), incluindo `**n**` no dado máximo, `~~n~~` no descartado e o espaço fino de zero do Fate (`parser.py:25`):

```
` 1 ` ⟵ [-, 0, +, +] 4dF
```

A mensagem compõe autor e cena em volta do corpo:

```
**IR1S** · Cripta — ` 1 ` ⟵ [-, 0, +, +] 4dF
```

- Sem nome da escada. A escada vive no `harpi-campaign` do vault (ticket 02) e a rolagem precisa funcionar com o vault fora (ticket 08, §7). O painel pode decorar a leitura com a escada no ticket 10, sem tocar no log.
- Sem menção `<@id>`, para não pingar. O nome de exibição vai em negrito.
- Cena ausente (`current_scene_id` NULL depois de a cena ser apagada): o segmento ` · Cena` some.
- Com `N#`, o cabeçalho aparece uma vez, um corpo por linha e `Max:` no fim quando N > 1. `Max:` é renderizado das linhas, não gravado.
- A linha do painel usa a mesma composição. As duas superfícies leem igual.

`dice_json` guarda o detalhe de uma avaliação:

```json
{
  "index": 2,
  "of": 3,
  "expression": "d20+5",
  "groups": [
    {"notation": "d20", "values": [14], "kept": null, "total": 14}
  ]
}
```

`values` são as faces cruas (-1, 0, +1 no `dF`), `kept` é `null` ou a máscara booleana do `kh`/`kl`, e o `total` da linha é o valor da expressão.

### 6. Ordem, id e dedupe

- Id `rol_` mais ULID, gerado em ordem dentro da mesma mensagem. `created_at` é epoch em segundos (ticket 05), então `(created_at, id)` vira ordem total, como o ticket 07 fixou, e o índice `rolls_by_table (table_id, created_at, id)` já serve de cursor.
- `created_at` é o instante da aceitação, escrito uma vez.
- `discord_message_id` é a mensagem que carrega a expressão: a do autor numa rolagem de canal, a do bot numa rolagem de painel.
- Duas mensagens diferentes nunca deduplicam entre si, mesmo com a mesma expressão. O log é o registro do que aconteceu.
- Cliente deduplica por `id` entre a resposta do POST e o `table.roll`.

### 7. Rotas e evento

| Rota | Papel | Regra |
|---|---|---|
| `POST /api/tables/<id>/rolls` | narrador, jogador | `{expression}`; 200 `{rolls}`; 403, 404, 409 `table_closed`, 422, 502 |
| `GET /api/tables/<id>/rolls?after=<roll_id>&limit=50` | narrador, jogador, pendente, espectador com a Table aberta | ordem crescente, `limit` 1 a 200 (default 50), cursor `(created_at, id)`; membro lê também com a Table fechada; cursor desconhecido é 422 `bad_cursor` |

- `table.roll` leva o DTO completo: `id`, `table_id`, `scene_id`, `scene_label`, `turn_id`, `actor_id`, `actor_label`, `source`, `expression`, `total`, `dice`, `text`, `discord_message_id`, `created_at`. Um frame por linha, sem `stream_rev` e fora da conflação de estado (ticket 07).
- O snapshot não carrega o log (ticket 07). O painel busca `GET /rolls` ao abrir a Table e depois de cada reconexão, a partir do último id que tem. É a rota de recuperação da fila de 32.
- Buckets por usuário, no molde de `SEARCH_BUCKETS` (`pages/api.py:42-45`): 60/min no POST, 240/min no GET. Corpo de 1 KB no POST, abaixo do limite de 16 KB de `moves` do ticket 08.

### 8. Delta de schema

Uma coluna nova, pelo mesmo motivo que `turns.label` e `rolls.actor_label` são cópias:

```sql
ALTER TABLE rolls ADD COLUMN scene_label TEXT NOT NULL DEFAULT '';
```

`scene_id` é `ON DELETE SET NULL` (ticket 05), então sem a cópia o log perderia o nome da cena quando a cena fosse apagada. Nada mais muda: sem coluna de entrega, sem soft delete, e o índice único de `discord_message_id` fica como está.

### 9. Retenção

Sem expurgo. As linhas vivem enquanto a Table existir e morrem com a campanha, por `ON DELETE CASCADE`. O job diário de `src/panel/retention.py` continua só de presença.

O snapshot não carrega rolagens (ticket 05), então o SQLite é o registro. Ele já entra no backup diário de `src/panel/backup.py`, que copia o banco inteiro pela API de backup do SQLite e guarda 7 cópias. Perder o banco e os backups deixa só as mensagens do Discord, e não há exportação para o vault no M1.

### 10. Bordas

- Table sem cena corrente: rolagem aceita, `scene_id` NULL, `scene_label` vazio, mensagem sem o segmento da cena.
- Canal com Table fechada, DM, guild sem campanha: resposta, sem log.
- Expressão inválida ou com erro: resposta de erro como hoje, sem linha.
- Jogador com Sheet arquivado é pendente e recebe 403.
- Espectador não posta e lê o log só com a Table aberta.
- Rolagem de membro pendente no canal entra, com o snowflake.
- Duas rolagens simultâneas de superfícies diferentes entram as duas, ordenadas por `(created_at, id)`.

### 11. Critérios de aceite

- `4dF` no canal da Table aberta grava uma linha e chega ao painel por `table.roll`.
- Rolagem no painel aparece no canal e no log com o mesmo texto.
- `3#d20+5` grava três linhas e uma mensagem.
- Rolagem em canal sem Table aberta responde e não grava.
- A mesma mensagem processada duas vezes grava uma linha.
- Table fechada recusa o POST com 409 e aceita o GET do membro.
- Reiniciar o painel e reabrir a Table mostra o log pelo `GET /rolls`.

### 12. Reconciliações com tickets fechados

| Ticket | Ajuste |
|---|---|
| 01 | Log de dados espelhado confirmado, com o parser atual e sem escada. |
| 02 | A escada de Paratheos fica fora da mensagem de rolagem no M1. |
| 05 | `rolls` ganha `scene_label`; id `rol_` mais ULID para `(created_at, id)` ordenar; rolagens continuam fora do snapshot. |
| 07 | `table.roll` definido, sem `stream_rev`, um frame por linha; a recuperação da fila de 32 é `GET /rolls`. |
| 08 | Rolagem segue os papéis, os 404/403/409 e o CSRF; a matriz ganha a linha de `GET /rolls`, com membro sempre e espectador só com a Table aberta. |

### 13. Glossário para o ticket 12

- **Rolagem**: uma avaliação aceita de uma expressão de dados numa Table, uma linha em `rolls`, com o texto congelado. Distinta de **expressão de dados**, que é o que o parser aceita.
- **Mensagem de rolagem**: a mensagem do Discord que carrega a rolagem, do autor no canal e do bot no painel.
- **Log de dados**: a lista ordenada por `created_at, id` das rolagens de uma Table.

ADR candidato para o ticket 12, **Rolagem espelhada**: mensagem antes da linha, texto congelado, ULID na ordem, sem expurgo, e painel que depende do Discord estar de pé para rolar. Tem as três características: difícil de reverter depois que existem linhas, surpreendente para quem espera rolar no painel com o Discord fora, e resultado de um trade-off real contra gravar primeiro e tolerar mensagem faltando.

### 14. Fica para outros tickets

- Botão, histórico, chips de dado e celular: ticket 10.
- Spec, glossário e ADR: ticket 12.
- Backup do banco e retenção de cópias ficam com o job existente, sem trabalho novo. Exportar o log para o vault não está no M1.
