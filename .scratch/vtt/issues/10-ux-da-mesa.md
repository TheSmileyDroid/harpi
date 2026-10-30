# UX da mesa no painel

Type: prototype
Status: resolved
Blocked by: 05, 07

## Question

Como a mesa aparece e se comporta no painel?

Decidir:

- router e páginas: Table, Personagens, Ficha.
- visão do narrador e visão do jogador.
- arrastar token, revelar zona, avançar turno.
- painel de ficha durante a cena.
- entrada do jogador na campanha.
- celular e teclado.
- linguagem visual do `DESIGN.md`.

Resolução: protótipo navegável e decisão de UX.

## Answer

Casca B, protótipo navegável em [index.html](../prototypes/10/index.html), com [README](../prototypes/10/README.md). Arquivo autocontido, tokens copiados de `web/src/app.css`, dados de exemplo. Nada em `src/`, `pages/`, `web/`, `app.py` ou `tests/` foi alterado. As cascas A e C ficam no arquivo como registro da comparação.

### 1. Casca e router

- Rail fixo de 14rem à esquerda: wordmark, campanha, páginas (MESA · PERSONAGENS · FICHA), lista de cenas, quem está na mesa com papel e estado do link. O conteúdo à direita tem a barra da mesa, o papel e o link.
- Rotas por campanha: `/c/<slug>/mesa`, `/c/<slug>/personagens`, `/c/<slug>/ficha`. `/` segue a página de música. O M1 resolve `paratheos` pelo seed; o M2 acrescenta o parâmetro de campanha sem mudar a forma da URL.
- A mesa é uma página de duas colunas dentro do conteúdo: mapa largo e coluna de 20rem com turno, rolagem, log e condução. A página de música não ganha rail nem dock de VTT.
- O rail usa as chaves de instrumento: item ativo em sand com grão, 3px; cena atual com lâmpada quadrada; quem está na mesa com papel. Abaixo de 56rem o rail vira faixa no topo e o conteúdo ocupa a largura. `DESIGN.md` precisa de uma seção de navegação, porque hoje diz que o painel não tem nav.

### 2. Papéis

Uma página só, com controles que aparecem por papel. O recorte de dados já vem do servidor (ticket 08); a UI esconde o que o papel não pode fazer e o servidor responde 403, 404, 409 ou 422 se a ação for forçada.

- **Narrador**: vê todos os tokens e as zonas ocultas em névoa translúcida, clica na zona para revelar ou cobrir, abre a ficha de qualquer token pela linha do turno, troca de cena e adiciona token no painel Condução.
- **Jogador**: só o recorte de jogador. Zona oculta não é desenhada, então o layout da sala não vaza. Arrasta o próprio token, passa e encerra o próprio turno, abre a própria ficha.
- **Pendente**: vê a mesa no recorte de jogador com faixa no topo, "Sua ficha está pendente" e as chaves Ver ficha e Como entrar. Não move, não rola, não conduz.
- **Espectador**: só Mesa. Personagens e Ficha respondem 404 de escopo, como no ticket 08.

### 3. Mapa, token e névoa

- O mapa cabe na largura no desktop, com grid desenhado. O narrador vê o mapa inteiro e as zonas ocultas numa névoa tracejada e clicável. Para o jogador, sala não revelada não é desenhada: sem contorno, sem hachura, sem nome, só o chão escuro. Ocultar não deixa o layout vazado. Zona revelada mostra o nome para os dois papéis, mas só o narrador clica para cobrir.
- Token é um quadrado de 3px, não círculo. Cor por tipo: PC em sand, NPC em oxide, token do jogador com anel amber. Retrato do Character quando existir, senão iniciais. Rótulo em placard abaixo do token, escondido no celular.
- O token tem no mínimo 2.25rem (36px) de alvo, centrado na célula, e não encolhe com o zoom. Hover mostra borda oxide, elevação de 2px e cursor de arrastar; sem hover, o token do jogador mantém o anel amber. Token de outro jogador não muda o cursor.
- Arrastar: pointer capture, preview local e commit no drop, como o ticket 07 fixa. Enquanto outro jogador arrasta, o token leva contorno tracejado oxide com o nome por 3 s, o drag marker do ticket 07, sem bloquear.
- **Revelar zona**: clique na própria zona no mapa, com atualização otimista. A confirmação chega no `table.delta`; o contorno oxide cobre o intervalo. A lista do painel Condução fica só como estado, sem botões de revelar.
- **Avançar turno**: cada participante pendente tem uma chave de seta (→), que chama aquele participante para o turno sem marcar ninguém como já agiu; a ordem continua livre. Passar e Encerrar marcam quem agiu e abrem o próximo, com o atalho `N` para passar. A rodada fecha quando o último pendente age e o narrador abre a seguinte; ninguém começa sozinho.
- Só token público participa do turno, para narrador e jogador. Oculto por `visible: false` ou por zona não revelada fica fora da lista, da contagem e do rodízio; ao revelar a zona, ele entra pendente na rodada corrente. Se o turno aberto era de um token que acabou de ficar oculto, o painel mostra "Aguardando" até alguém passar.
- Zoom com −, ＋ e Enquadrar no cabeçalho da cena. No celular, célula mínima de 32px e mapa rolável para os lados, sem exigir pinch.

### 4. Rolagem e log

- Campo de rolagem na coluna, logo abaixo do turno, para não sair da tela quando o mapa é alto. A mensagem vai ao canal antes da linha no log, como o ticket 09 fixa; falha do Discord aparece em fault plate e nada entra no log.
- Log na coluna, ordem crescente, etiqueta PAINEL ou DISCORD por linha, rolagem para o fim ao abrir. Reconexão recupera por `GET /rolls`.
- A chave fica travada enquanto o POST está em voo; duplo clique não vira duplicata.

### 5. Ficha

- Gaveta lateral de 28rem sobre o mapa no desktop e tela cheia no celular. Fecha com Esc, botão ou clique no backdrop.
- Conteúdo: aspectos, perícias por degrau, caixas de estresse clicáveis, consequências, extras e inventário. Jogador lê e edita a própria; narrador, qualquer uma. Ficha de NPC só o narrador vê, como o ticket 08 fixa.
- A página Ficha é a mesma composição em largura cheia, para edição longa e leitura fora da cena. O narrador ganha seletor de personagem; o jogador vê a própria.
- Pendente lê a própria ficha em somente leitura, com banner de aprovação. Conduzir estresse e consequência de NPC durante a cena é a mesma gaveta do narrador; o jogador continua vendo só o card público.

### 6. Entrada do jogador

- Membro sem ficha ativa cai na Mesa com faixa no topo: "Sua ficha está pendente" ou "Crie seu personagem".
- O fluxo de três passos (criar, enviar, aprovar) vive em Personagens: nome, conceito, envio e fila do narrador. Aprovar muda o papel sem escrever em `members`, como o ticket 08 fixa. O pendente acompanha a mesa enquanto espera.

### 7. Celular e teclado

- Celular: o rail vira faixa no topo com as páginas e o conteúdo ocupa a largura; mapa rola e tem zoom; gaveta ocupa a tela; turno, rolagem e log empilham abaixo do mapa, nunca em gaveta escondida.
- Teclado: `N` passa o turno, `D` foca a rolagem, `Esc` fecha gaveta e diálogos. O token do jogador entra no Tab: setas movem uma célula, Shift mais setas movem cinco, Enter abre a ficha. Zona focável responde a Enter e Espaço. Nenhum atalho global dispara com o cursor num campo.
- Alvos de 40px sobem para 44px em ponteiro grosso, como o `DESIGN.md` já manda.

### 8. Linguagem visual

- Nenhuma cor nova. Sand é o que se pressiona, amber é estado e leitura viva, oxide é cautela e drag de outro jogador, hazard é só fault plate (permissão, expressão inválida, Discord fora).
- A hachura da névoa usa `rule-strong`, não a fita de hazard. Token de NPC em oxide não é alerta.
- Item ativo do rail é chave sand com grão; painéis, bandas e rating seguem o `DESIGN.md`. Nada de pill, círculo, glow ou quarta fonte.
- `DESIGN.md` ganha a seção de navegação, o componente "Table map" (grid, zona, névoa, token, drag marker) e a regra de que a mesa não usa o dock da música.

### 9. Consequências para a spec

- Rotas, páginas e estados entram na spec do ticket 12.
- Reconciliação com o ticket 05: participante do turno é o token público da cena. Token oculto não abre turno, não entra na contagem e não fecha rodada, nem para o narrador.
- O contrato não ganha modelo novo: os DTOs de mesa já vêm dos tickets 05 a 09.
- `DESIGN.md` precisa das três seções acima.
- O protótipo é descartável e fica em `.scratch/vtt/prototypes/10/`. Não vira código de produção.

### 10. O que o protótipo não prova

- Não prova SSE, commit de drag, autorização nem ficha real; prova a UX. Os números continuam com os tickets 06 e 07.
- A imagem da cena é um SVG de exemplo. A imagem real do vault pode pedir ajuste de contraste da névoa.

