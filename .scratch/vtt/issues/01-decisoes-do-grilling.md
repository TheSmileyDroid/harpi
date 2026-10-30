# Decisões do grilling

Type: grilling
Status: resolved

## Question

Qual modelo de domínio e qual escopo o grilling fechou para o marco 1 do VTT?

## Answer

Destino: spec implementável do M1. O M1 entrega uma campanha Paratheos já configurada, Table presa a um canal de texto, Scene com tokens, névoa por zona e turno livre, log de dados espelhado e fichas Fate criadas pelos jogadores e sincronizadas com o vault.

### Campanha e acesso

- Campaign é uma entidade com narrador, membros e uma origem de conteúdo: `vault` ou `local`.
- Uma guild pode ter várias campanhas. A Table pertence à Campaign, não à guild.
- Uma Table ativa por campanha e uma Table por canal de texto.
- Autenticação continua Discord OAuth com allowlist de guild. Não há convidados fora da guild no M1.
- Narrador convida jogadores da guild. Co-narrador fica fora do M1.

### Personagens e fichas

- Character é a nota de identidade e lore (`tipo: personagem` no vault).
- Sheet é o estado jogável, no máximo um por Character, com bloco YAML cercado por `` ```harpi-sheet `` e frontmatter de identidade, campanha, dono e revisão.
- PC é Character com Sheet cujo dono é um jogador. NPC é todo o resto.
- Jogador vê e edita a própria ficha completa; vê de outros PCs apenas o card público; vê de NPC apenas nome, imagem, conceito e resumo público.
- Narrador vê e edita qualquer ficha.
- Jogador cria Character e Sheet do zero pela interface; o narrador aprova.
- Narrador também cria fichas de NPC e pode anexar ficha a um Character que já existe no vault.
- Sync com o vault é nos dois sentidos, com merge por campo e contador de revisão; conflito no mesmo campo pede decisão.
- Escritas do app ficam confinadas a `Harpi/Campaigns/<slug>/`.

### Mesa e cena

- Scene é uma imagem de mapa com grid opcional, zonas, tokens, névoa e ordem de turno.
- Névoa é por zona, revelada pelo narrador. Sem linha de visão, paredes ou luzes.
- Cada jogador move o próprio token; o narrador move qualquer token, inclusive NPC.
- Ordem de turno é livre; o narrador avança e o jogador atual pode encerrar o próprio turno.
- Rolagens no painel e no Discord entram no mesmo log; `4dF` já é suportado pelo parser.

### Conteúdo e mapas

- Vault e local são implementações de um ContentStore. O M1 só usa vault; campanha local fica para o M2.
- Atlas é autoria em Canvas (`.canvas`), viewer somente leitura no M2, editor no Harpi no M3, plugin do Obsidian depois.
- Wiki é manifesto em nota, markdown puro, sem Dataview nem Bases, no M3.
- O M1 não inclui Atlas, wiki, campanha local, criação de campanha, convites nem plugin.

### Vocabulário

- Table, Scene, Campaign, Character, Sheet, Atlas, Content source, Narrator, Player, PC, NPC, Public card.
