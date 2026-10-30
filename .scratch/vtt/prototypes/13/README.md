# Protótipo: editor de cenas e salas

Artefato descartável do ticket [Editor de cenas e zonas](../issues/13-editor-de-cenas-e-zonas.md). Não é produção: nada em `src/`, `pages/`, `web/`, `app.py` ou `tests/` foi tocado.

## Abrir

- Direto do disco: abra `index.html` no navegador.
- Ou sirva a pasta: `python3 -m http.server 8766` dentro de `.scratch/vtt/prototypes/13` e abra `http://localhost:8766/`.

## Navegar

- A página inicial é a galeria de Cenas. Clique num cartão para abrir o editor.
- Barra inferior: `←` e `→` trocam a variante. `Fora da mesa` e `Mesa aberta` ligam o aviso de cena em uso. `Zerar` recomeça.
- URL: `?variant=A|B|C`, `?scene=cripta|patio|porto`, `?table=open`, `?page=editor`.
- A variante A é a vencedora. B e C ficam como registro da comparação.

## Cena em uso na mesa

- O editor não desenha névoa nem tokens da sessão. Mostra o mapa preparado e uma faixa com quantos tokens e áreas reveladas existem na mesa agora.
- Salvar grava o arquivo. A mudança entra na mesa quando o narrador recarregar a cena por lá.

## Mexer no mapa

- **Selecionar** (padrão): clique numa sala. O nome e a névoa aparecem na faixa embaixo do mapa.
- **Sala**: arraste no grid. Cada arrasto cria uma sala; se **sobrepuser** um pouco uma sala existente, vira parte dela. Encostar sem sobrepor cria outra sala, como no Dungeon Scrawl. A geometria é reorganizada em retângulos sem sobreposição, então nada fica com cor dobrada. Dois arrastos sobrepostos fazem uma sala em L com um contorno só.
- **Apagar**: arraste sobre a área. A borracha corta só as células que você passou, como no Dungeon Scrawl. Pode abrir um buraco ou dividir a sala; o que sobra continua sendo a mesma sala.
- **Desfazer**: seta curva na barra ou `Ctrl+Z`/`Cmd+Z`.
- Clique numa sala vazia para desmarcar. `Delete` apaga a sala selecionada. Duplo clique numa sala foca o nome.
- Teclado: `V` selecionar, `R` sala, `E` apagar, `Esc` desmarca, `S` salva.

## Origem do mapa

- **Imagem**: escolhe uma imagem do vault ou envia para `assets/`. O embed aparece no protótipo só como comparação; ficou fora do M1.
- **Desenho**: a cena nasce vazia; as salas desenhadas formam o mapa e a névoa ao mesmo tempo. O save grava o SVG em `assets/<slug>-map.svg`.

## O que dá para fazer

- Escolher, criar e trocar cenas na galeria e na lista do rail.
- Criar uma cena com imagem ou desenhando.
- Editar nome, névoa inicial, grid e `fog_outside`.
- Salvar com a sequência de escrita atômica simulada e o hash.
- Ver o aviso de cena em uso e o resumo da mesa.
- Simular edição externa do arquivo e ver o conflito por hash.

## As três variantes

- **A, bancada:** palco com ferramentas à esquerda, faixa da sala selecionada embaixo e inspetor à direita. Vencedora e padrão.
- **B, passo a passo:** faixa de cenas, quatro passos e um assunto por vez ao lado do palco.
- **C, quadro de salas:** palco largo com dock de salvar e salas como cartões.

## O que é falso

- Sem rede, sem SQLite, sem SSE, sem escrita real: tudo vive na memória da página e zera ao recarregar.
- O hash é um djb2/FNV de mentira com cara de sha256; a escrita atômica é uma lista de passos, não um `os.replace`.
- O mapa de exemplo é um SVG fixo; no modo desenho ele é gerado pelas salas só na simulação do save.
- Upload não lê o arquivo, o embed não busca a URL, e o índice do vault é uma lista fixa.
- A vista viva usa tokens e névoa de exemplo; não prova o recorte do servidor nem o SSE.
