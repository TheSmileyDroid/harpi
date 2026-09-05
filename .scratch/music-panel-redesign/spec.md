# Spec: Redesign dinâmico do painel Music

Painel Music deixa de ser página empilhada estática e vira interface viva: lógica de layout Spotify (conteúdo + side panel + transport fixo), com dropdown, dialogs, toasts e interação real na barra de progresso — tudo na estética amber CRT existente.

## Entendimento compartilhado

### Estrutura (Spotify × Cyberpunk)

- Desktop: grid de 2 colunas — conteúdo principal + `now_playing` à esquerda; **Side panel** (abas `QUEUE | LAYERS`) à direita. Mobile: coluna única (busca → now playing → abas → transport fixo).
- **Transport** fixo embaixo (já existe, mantém controles).
- "00 // LINK" vira linha compacta no topo (guild + canal + connect), com a busca logo abaixo.
- Todo componente novo herda o design system: amber phosphor, `hud-panel`, corner brackets no foco, Rajdhani nos títulos, vermelho só para erro, nunca verde.

### Busca única

- Uma busca só, no topo da página (o painel search antigo e o quick-add da fila morrem).
- Resultados em **overlay dropdown**: fecha com Esc/clique fora/nova busca; efêmero por design.
- Linha do resultado: thumb + título + uploader + duração + botões `QUEUE`/`LAYER` direto na linha (paridade com o Discord: play vs layer é escolha explícita).
- URL colada é detectada e vai direto à fila.
- Teclado: ↑/↓ navega, Enter seleciona.
- Thumbnails vêm do dict cru do yt-dlp que o `YTMusicData` já guarda (sem rede extra, sem cache local — o browser cacheia i.ytimg.com; não há CSP no app).

### Transport

- Barra de progresso **clicável e arrastável**. Preview do tempo-alvo durante o arrasto; **seek absoluto único no soltar** (o seek reinicia o FFmpeg, então seek contínuo é proibido — a regra "música não morre enquanto toca" manda).
- Input numérico de seek (±s relativo) removido.
- Poller adaptativo do transport: ~500ms tocando, 2s pausado.
- Volume vira range slider estilizado (mesma trilha visual do seek); o texto de volume repetido no now playing sai.

### Dinamismo

- **Dialogs** (`<dialog>`): detalhe de camada (slider de volume + remover) e confirmação de ações destrutivas (limpar fila, desconectar).
- **Toasts** amber transitórios para confirmações (adicionado à fila, virou camada, volume, seek aplicado). `panel_error` vermelho persistente permanece como é.
- Thumbs pequenas (40–56px) em busca, fila **e camadas**.

### Fora do escopo

Dashboard `/` fica como está nesta rodada.

## Terminologia (CONTEXT.md)

Termos novos no glossário: **Transport**, **Search results**, **Side panel**, **Toast**. "Player" continua proibido — é Session.
