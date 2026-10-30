# Esquema da ficha

Type: grilling
Status: resolved

## Question

Qual é a forma exata do bloco `harpi-sheet` e da nota de config da campanha?

O bloco precisa cobrir: aspectos (conceito, problema, +3), perícias na escada de Paratheos, façanhas, trilhas de estresse, consequências, recarga, pontos de destino, extras (Noética, EGO, runas) e inventário linkado a notas de item.

Decidir:

- rank de perícia é número (`+4`) ou rótulo (`Ótimo`) no YAML, e como a config gera o outro.
- estresse é lista de caixas, contador ou lista de booleanos.
- consequências são slots fixos (Leve +2, Moderada +4, Severa +6) com texto e marcação.
- extras são lista tipada ou mapa por tipo.
- inventário guarda wikilink, quantidade e notas.
- a nota `config.md` define perícias, escada, trilhas, slots, recarga e extras.
- o parser de notas do vault lê títulos e tabelas das notas `tipo: personagem` e degrada para nome mais resumo.
- o que é público no card e o que é só do narrador.

Resolução: um exemplo completo de ficha de PC, um de NPC, um de config, e as regras de parse e validação.

## Answer

O estado mecânico vive num bloco YAML cercado por `` ```harpi-sheet ``. A perícia guarda rank numérico. O estresse guarda caixas com valor e marcação. A consequência guarda slot com severidade, valor e texto. Extras são uma lista com `kind`. Aspectos são uma lista rotulada, com o padrão Fate como default. Inventário guarda link, quantidade e nota.

### Bloco `harpi-sheet`

````markdown
```harpi-sheet
refresh: 7
fate_points: 3
aspects:
  - label: Conceito
    text: "A Máquina Fria da Innovation"
  - label: Problema
    text: "Programada para recapturar IR1S"
  - label: Aspecto
    text: "Conectada à Rede Local de Beta"
  - label: Aspecto
    text: "Fantasma na Rede da Innovation"
  - label: Aspecto
    text: "Confusa sobre seu trabalho"
skills:
  - name: Hackear
    rank: 4
  - name: Atirar
    rank: 3
  - name: Luta
    rank: 2
stunts:
  - name: "Escudo Indestrutível"
    text: "Gasta 1 ponto de destino para tornar um objeto na mesma zona indestrutível até o fim da cena."
    refresh_cost: 0
stress:
  - track: Físico
    boxes:
      - value: 1
        checked: false
      - value: 2
        checked: false
      - value: 3
        checked: true
  - track: Mental
    boxes:
      - value: 1
        checked: false
      - value: 2
        checked: false
consequences:
  - severity: Leve
    value: 2
    text: "Casco rachado"
  - severity: Moderada
    value: 4
    text: ""
  - severity: Severa
    value: 6
    text: ""
extras:
  - kind: Noética
    name: Constructo
    text: "Corpo artificial conectado à rede."
    cost: 0
inventory:
  - item: "[[Espada de Lancelot]]"
    qty: 1
    note: "Relíquia"
```
````

### Regras do bloco

- `skills` lista apenas perícias com rank maior ou igual a 1. Perícia ausente vale 0. Duplicata é erro. O rank precisa existir na escada da config.
- `stress` usa as trilhas da config. Cada caixa tem `value` e `checked`. Um extra pode adicionar caixa; nesse caso o valor fica explícito. A interface impede marcar mais caixas do que existem.
- `consequences` usa os slots da config. `severity` é a chave, `value` é o valor exibido, `text` vazio significa slot livre. Preencher o texto ocupa o slot; limpar libera.
- `extras` é uma lista aberta com `kind` vindo da config (`Noética`, `EGO`, `Runa`), mais `name`, `text` e `cost` opcional. O app exibe, não interpreta a mecânica.
- `aspects` é uma lista de `{label, text}`. O default é o padrão Fate: `Conceito`, `Problema` e três `Aspecto`. A config pode renomear; a de Paratheos pode usar `Função`, `Falha`, `Identidade`, `Conexão`, `Ambiguidade` sem mudar o schema.
- `inventory` guarda `{item, qty, note}`. `item` é wikilink para uma nota do vault. Link morto aparece como texto.
- `refresh` e `fate_points` são inteiros. `fate_points` não tem teto, porque a mesa ganha pontos durante a sessão.
- `stunts` guarda `{name, text, refresh_cost}`. O app exibe o custo, não recalcula a recarga.
- Chaves desconhecidas são preservadas na escrita. O app só escreve o bloco, nunca a prosa em volta.
- YAML inválido deixa a ficha em modo somente leitura com erro visível. O app nunca sobrescreve um bloco que não conseguiu parsear.

### Bloco `harpi-campaign`

````markdown
```harpi-campaign
name: Paratheos
system: fate
ladder:
  - {rank: 4, label: Ótimo}
  - {rank: 3, label: Bom}
  - {rank: 2, label: Razoável}
  - {rank: 1, label: Regular}
  - {rank: 0, label: Medíocre}
  - {rank: -1, label: Ruim}
  - {rank: -2, label: Terrível}
skills:
  - Arte
  - Atletismo
  - Atirar
  - Comunicação
  - Conhecimento
  - Contatos
  - Crime
  - Empatia
  - Enganar
  - Furtividade
  - Investigação
  - Luta
  - Manipulação de Fluxos
  - Ofício
  - Percepção
  - Pilotagem
  - Provocar
  - Recursos
  - Vigor
  - Vontade
aspects:
  - Conceito
  - Problema
  - Aspecto
  - Aspecto
  - Aspecto
stress:
  - {track: Físico, boxes: [1, 2, 3]}
  - {track: Mental, boxes: [1, 2]}
consequences:
  - {severity: Leve, value: 2}
  - {severity: Moderada, value: 4}
  - {severity: Severa, value: 6}
refresh: 7
extras:
  - Noética
  - EGO
  - Runa
```
````

A config fica em `Harpi/Campaigns/<slug>/config.md`, editada no Obsidian no M1. O caminho exato e o ciclo de vida ficam no ticket "Layout de Character e Sheet".

### Parser de notas do vault

- Lê as notas `tipo: personagem` sem escrever nelas.
- Reconhece títulos `Aspectos`, `Perícias`, `Façanhas`, `Estresse`, `Consequências`, `Extras` e `Inventário`, com ou sem acento e em qualquer nível de heading.
- Aspectos vêm de bullets `- **Rótulo:** texto`. Rótulos conhecidos do vault são preservados; para o card público, `Função` conta como conceito e `Falha` como problema.
- Perícias vêm de tabela com colunas de nível e lista, no formato `Ótimo (+4)` ou `Good (+3)`, e de bullets `- Good (+3): Physique`.
- Façanhas vêm de bullets sob `Façanhas`.
- Estresse vem de linhas como `- Físico: ☐☐☐` ou `- Physical: ☐☐☐`. `☑` e `■` contam como marcados.
- Consequências vêm de linhas como `- Leve (+2)`, com texto opcional.
- Sem seção reconhecida, a ficha degrada para nome, aliases, imagem e primeiro parágrafo do resumo. Nada é inventado.

### Projeção pública

- Dono da ficha vê e edita a ficha completa.
- Outro jogador vê o card público: nome, imagem, conceito e resumo.
- Jogador vê de NPC o mesmo card público.
- Narrador vê e edita a ficha completa de qualquer Character.

### Fora deste ticket

- Caminhos, frontmatter, status e aprovação: ticket "Layout de Character e Sheet".
- Merge e revisão: ticket "Sync do vault".
- Renderização na mesa: ticket "UX da mesa no painel".
