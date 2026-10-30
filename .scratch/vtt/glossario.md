# Glossário do VTT em português

Leitura em português dos termos de VTT do [`CONTEXT.md`](../../CONTEXT.md). O `CONTEXT.md` é a fonte canônica, em inglês; este arquivo é o espelho para conversa e interface. Nomes de campo, tabela, rota e código continuam em inglês. Termos do painel de música (Session, Viewer, Snowflake, Link) continuam só no `CONTEXT.md`.

## Campanha e conteúdo

**Campanha**:
Um grupo de jogo preso a uma guild do Discord, com narrador, membros e uma origem de conteúdo. O slug é imutável e aparece em três lugares: a pasta no vault, o bloco `harpi-campaign` e o SQLite.
_Evite_: guild (uma guild pode ter várias campanhas), jogo, mesa (a mesa é a Table)

**Origem do conteúdo**:
Onde ficam as fichas da campanha: `vault` (notas em `Harpi/Campaigns/<slug>/`) ou `local` (SQLite, M2). O M1 só entrega `vault`.
_Evite_: backend, armazenamento, provedor

**Atlas**:
O mapa do mundo autoral, com mapas aninhados, guardado como Canvas do Obsidian. Viewer somente leitura no M2, editor no M3. Não é o mapa de uma Table.
_Evite_: mapa do mundo, mapa da campanha

## Personagens e fichas

**Personagem**:
A nota de identidade e lore de uma pessoa da ficção (`tipo: personagem`), com id `chr_` estável quando o app cria a nota. A lore pertence à campanha e não tem dono.
_Evite_: ficha (o estado jogável), token (a peça no mapa), NPC (um papel)

**Ficha**:
O estado jogável de um Personagem: uma nota com bloco cercado `harpi-sheet`, duas seções de prosa, um dono e um status. Um Personagem tem no máximo uma ficha pendente ou ativa. UI: Ficha.
_Evite_: personagem, card, ficha de mecânica

**PC**:
Um Personagem cuja ficha é de um jogador.

**NPC**:
Todo Personagem que não é PC. Criado pelo narrador, nasce ativo e fica visível para os jogadores quando é revelado.

**Card público**:
O que um jogador vê de outro personagem: nome, retrato, conceito e resumo. A ficha nunca sai do servidor para quem não é o dono nem o narrador.
_Evite_: preview, perfil

**Personagem revelado**:
Um NPC que entrou no elenco visível, por ação do narrador ou quando o primeiro token dele cai numa zona revelada. Continua no elenco depois que o token sai da cena.
_Evite_: descoberto, liberado, visível

**Conflito de ficha**:
O mesmo campo mudou no painel e no vault desde a última versão que o app aceitou. O arquivo fica intocado e a ficha vira somente leitura até cada campo receber uma decisão. Uma ficha é `ok`, `conflito`, `ausente`, `invalido` ou `desconhecido`.
_Evite_: erro de merge, divergência, sujo

## Mesa

**Mesa** (Table):
A mesa em jogo: a cena, os tokens, a névoa e os turnos de uma campanha, presa a um canal de texto. Só uma aberta por campanha e por canal. UI: Mesa.
_Evite_: sessão (essa é a de música), sala, jogo

**Cena**:
Um mapa preparado: imagem ou desenho, grid, zonas nomeadas e névoa inicial, guardado em `scenes/` e carregado numa Table.
_Evite_: mapa (palavra da interface para a cena renderizada), encontro, nível

**Origem da cena**:
De onde vem a imagem da cena: `image` (imagem do vault ou asset enviado) ou `sketch` (salas desenhadas no editor e salvas como SVG nos assets da campanha). UI: Origem da cena.
_Evite_: modo, tipo, estilo

**Molde da cena**:
O arquivo autoral da cena em `scenes/`, com imagem, grid, zonas e névoa inicial, sem tokens.
_Evite_: template, definição

**Snapshot da mesa**:
A cópia periódica do estado vivo em `tables/`: cena corrente com névoa, tokens, rodada e turno. Rede de segurança para perda do banco, nunca uma segunda verdade.
_Evite_: save, backup de estado, arquivo de persistência

**Zona**:
Uma área nomeada da cena: união de retângulos inteiros em células, revelada ou oculta de uma vez. Numa cena desenhada, a sala é a zona: as salas formam o mapa e a névoa ao mesmo tempo. UI: área na galeria e nos resumos; sala no desenho.
_Evite_: sala (fora do desenho), retângulo, máscara

**Névoa**:
O estado de revelação da mesa: quais zonas estão reveladas e se o que está fora de toda zona fica oculto. Zona oculta não é desenhada para o jogador. Recurso de jogo, não fronteira de segurança.
_Evite_: máscara, sombra, visibilidade, escuridão

**Token**:
Uma peça no mapa presa a uma Table e a uma cena: posição em células, tamanho, rótulo, dono e Personagem opcionais, cor e visibilidade. O retrato vem do Personagem linkado.
_Evite_: miniatura, peça, ator, marcador

**Token público**:
Um token que o jogador pode ver: `visible: true`, com o centro numa zona revelada, ou fora de toda zona quando `fog_outside` está desligado. Só token público participa da rodada.
_Evite_: token visível (isso é só um campo), token revelado

**Turno**:
O intervalo em que um token age na rodada corrente. No máximo um aberto por Table.
_Evite_: iniciativa, ordem, ativação

**Rodada**:
Uma passagem pelos tokens públicos da cena corrente. Fecha quando o último token que ainda não agiu encerra o turno, e o narrador abre a próxima.
_Evite_: ciclo, rodada de iniciativa, pendente (isso é um papel)

**Stream da mesa**:
A conexão SSE que uma pessoa com o painel aberto mantém com uma Table.
_Evite_: socket, canal, feed

**Presença na mesa**:
A lista de quem está com o stream da mesa aberto agora, com nome de exibição e papel (`table.viewers`), mantida em memória pelo distribuidor do stream. Nunca o id do Discord. Não é o **Viewer** do painel: esta é por Table. UI: Na mesa.
_Evite_: viewers (o conceito do painel), lista de presença

**Revisão do stream**:
O contador `stream_rev` por Table, mais um por mudança aceita, em memória e nunca persistido. Separado das revisões por linha usadas no controle de conflito.
_Evite_: versão, rev (as revisões de linha)

**Frame da mesa**:
`table.snapshot` ou `table.delta`: o estado da cena como chega ao cliente.
_Evite_: update, payload, tick

**Movimento de token**:
Uma mudança de posição aceita, enviada no máximo 10 vezes por segundo por Table. O último soltar vence.
_Evite_: evento de arraste, posição, delta

**Marca de arraste**:
O aviso temporário de que alguém está arrastando um token, renovado a cada movimento aceito e apagado 3 s depois do último. Nunca bloqueia ninguém.
_Evite_: trava, reserva, seleção

**Rolagem**:
Uma avaliação aceita de uma expressão de dados numa Table aberta: uma linha em `rolls` com o texto congelado como o parser imprimiu.
_Evite_: resultado de dado, teste, arremesso

**Mensagem de rolagem**:
A mensagem do Discord que carrega uma rolagem: a do autor no canal, a do bot quando vem do painel.
_Evite_: post, embed

**Log de dados**:
As rolagens de uma Table ordenadas por `(created_at, id)`. Só no SQLite, recuperadas pela API, nunca pelo snapshot.
_Evite_: histórico, feed

## Acesso

**Narrador**:
Quem consta em `campaigns.narrator_id`, aprova fichas, prepara cenas e conduz a mesa. UI: Narrador.
_Evite_: GM, DM, mestre, dono (dono é o da ficha)

**Jogador**:
Um membro da campanha com ficha `ativo`. UI: Jogador.
_Evite_: usuário, membro (qualquer linha em `members`), participante (um token)

**Pendente**:
Um membro da campanha sem ficha `ativo`. UI: Pendente. Diferente de ficha pendente, que é status de arquivo.
_Evite_: esperando, candidato

**Espectador**:
Um usuário autenticado de uma guild permitida, fora da campanha, que assiste a uma Table com a flag de espectador ligada, sem acesso a fichas. UI: Espectador.
_Evite_: convidado, anônimo, visitante

**Dono da ficha**:
O id do Discord em `harpi-owner`: a verdade de quem joga a ficha. UI: Dono da ficha.
_Evite_: dono (sem qualificar), jogador (papel derivado da ficha)

**Acesso à mesa**:
A condição que abre stream, mapa e resumo de uma Table: ser membro da campanha (o narrador incluso) ou espectador numa Table com a flag ligada.
_Evite_: permissão, concessão
