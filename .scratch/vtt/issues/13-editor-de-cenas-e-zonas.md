# Editor de cenas e zonas

Type: prototype
Status: resolved
Blocked by: 05, 10

## Question

Como o narrador cria e edita uma cena fora da mesa?

O ticket "Modelo de Table e Scene" delegou a lista de cenas e o editor de zonas para a UX da mesa; a UX da mesa fechou a lista e o revelar, não o editor.

Decidir:

- lista de cenas da campanha e criação de cena nova.
- escolha da imagem: picker do índice do vault, embed ou upload em `assets/`.
- grid: célula em pixels da imagem, offset e visibilidade.
- zonas: desenhar retângulos por célula, vários retângulos numa zona em L, rótulo, `revealed` inicial e `fog_outside`.
- o que o editor mostra da névoa e dos tokens vivos quando a cena está numa Table aberta.
- salvar o molde em `scenes/<slug>.json` com escrita atômica e `blueprint_hash`, e reimportar por hash.

Resolução: protótipo navegável e decisão de UX.

## Answer

Protótipo navegável em [index.html](../prototypes/13/index.html), com [README](../prototypes/13/README.md). Arquivo autocontido, tokens do `DESIGN.md`, dados de exemplo. Nada em `src/`, `pages/`, `web/`, `app.py` ou `tests/` foi alterado.

### 1. Onde o editor mora

- A página Cenas tem duas telas: **galeria** e **editor**. A galeria abre por padrão; o cartão de uma cena abre o editor.
- A galeria é uma grade de cartões: miniatura do mapa, nome, origem (`imagem` ou `desenhada`), número de áreas, estado de salvo e selo **em mesa**. O último cartão cria uma cena.
- O editor é a variante A, **bancada**: palco com barra de ferramentas à esquerda, faixa da sala selecionada embaixo e inspetor à direita (mapa, grid, salas, salvar). B e C ficam no arquivo como registro da comparação.
- O rail mantém a lista curta de cenas para trocar sem voltar à galeria.
- Nova cena: nome vira slug do arquivo e a cena nasce com uma das duas origens, **imagem** ou **desenho**.

### 2. Imagem

- **Origem imagem**: picker do índice do vault, com pastas e miniaturas, como primeira opção.
- Upload em `Harpi/Campaigns/<slug>/assets/` é a segunda opção; a cena aponta para a cópia dentro da campanha.
- **Embed fica fora do M1**: exige allowlist de host, cache no servidor e um caminho que não é do vault. O protótipo mostra a aba apenas como comparação.
- A imagem original do vault não é copiada, movida nem renomeada. O caminho é relativo à raiz do vault, como no ticket 05.

### 3. Mapa desenhado

- **Origem desenho**: a cena nasce sem imagem externa. As salas desenhadas formam o mapa e a névoa ao mesmo tempo: **sala = zona**.
- Ferramenta **Sala**: arrastar um retângulo no grid cria uma sala. Sobrepor um pouco uma sala existente junta o pedaço na mesma sala; encostar sem sobrepor cria outra sala. É a mesma regra do Dungeon Scrawl: o merge só acontece com sobreposição.
- A geometria é normalizada em retângulos sem sobreposição; o contorno desenhado é a união das células, sem linha interna e sem cor dobrada.
- Ferramenta **Apagar**: arrastar corta só as células tocadas. Pode abrir uma porta, um buraco ou dividir a sala; o que sobra continua sendo a mesma sala no M1. **Desfazer** (`Ctrl+Z`/`Cmd+Z`) restaura o estado anterior.
- Clique seleciona; clique no vazio desmarca; duplo clique foca o nome; `Delete` exclui a sala. Atalhos: `V` selecionar, `R` sala, `E` apagar, `S` salvar.
- Cada sala tem um **rótulo**, que é o nome que aparece no mapa e na lista. Não há nota separada por sala no M1; o nome carrega a identificação ("Sala do culto").
- O save de uma cena desenhada gera `Harpi/Campaigns/<slug>/assets/<slug>-map.svg` e mantém `image.path` apontando para esse SVG, então `image_path` continua obrigatório e o pipeline de token, zoom e névoa não muda.
- Sem pincel, textura, hachura, raio de canto ou estilos. Isso é editor de arte e fica para o M2.

### 4. Grid e névoa

- `cell_px`, `offset_x`, `offset_y` e `visible` como no ticket 05. O encaixe é sempre em célula inteira no M1; não há meio-célula nem desenho livre.
- `revealed` do molde é o estado inicial. `fog_outside` é por cena.
- No editor, sala oculta tem contorno tracejado e rótulo "oculta". O jogador não vê contorno, nome nem hachura de sala não revelada, como o ticket 10 fixa.

### 5. Cena numa Table aberta

- O editor **não desenha** névoa nem tokens vivos. Mostra o mapa preparado e uma faixa: "Em uso na mesa · N tokens · X de Y áreas reveladas agora", com atalho para a Mesa.
- Motivo: preparo e condução são momentos distintos. A mesa é a superfície de jogo; o editor é onde se prepara.
- Salvar grava só o arquivo. A mesa avisa que a cena mudou no disco e o narrador aperta **Recarregar cena** quando quiser aplicar. É uma recarga explícita, não edição ao vivo.
- **Emenda ao ticket 05**: o "sem hot reload" passa a ser "sem edição ao vivo; o narrador pode recarregar a cena explicitamente na Mesa". A semântica da recarga é a reimportação por hash já definida no 05: zona com o mesmo `id` mantém o `revealed` vivo, zona nova nasce `false`, zona removida perde a névoa, tokens da Table ficam intactos, e o turno aberto é encerrado como em qualquer troca de cena.

### 6. Salvar, hash e conflito

- Escrita atômica: arquivo temporário `.harpi-tmp-*`, `flush`, `fsync`, `os.replace`; o arquivo nunca é renomeado.
- `blueprint_hash` calculado sobre o JSON canônico do molde e gravado no SQLite. O pedido de save carrega o hash de base.
- Se o arquivo mudou no disco, o save é recusado com **conflito**: o narrador reimporta do disco ou sobrescreve de propósito. Nada é sobrescrito em silêncio.
- Mudar o nome da cena não renomeia o arquivo. O slug é escolhido na criação.

### 7. Consequências para a spec

- Rotas: `/c/<slug>/cenas` (galeria) e `/c/<slug>/cenas/<scene>` (editor), dentro da casca B do ticket 10.
- `scenes.source` novo: `image` | `sketch`. `image_path` continua obrigatório; em `sketch` aponta para o SVG gerado em `assets/`.
- `zones[].label` é o nome da sala; o modelo de `rects` e `revealed` do ticket 05 não muda.
- A Mesa ganha o aviso de versão nova da cena e a ação **Recarregar cena**.
- Glossário: **Sala** é a zona de névoa desenhada; **Origem da cena** é imagem ou desenho.
- O protótipo é descartável e fica em `.scratch/vtt/prototypes/13/`. Não vira código de produção.

### 8. O que o protótipo não prova

- Não prova escrita atômica real, sha256 real, SQLite, SSE, recarga na mesa nem autorização. Prova a UX e o modelo de interação.
- O índice do vault, o upload e o embed são simulados; o desenho é renderizado no cliente.
- O contorno tracejado e o contraste da névoa podem pedir ajuste sobre a imagem real do vault.
