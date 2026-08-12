# AGENTS.md — Harpi

Bot do Discord (música, dados, TTS) + painel web HTMX servido pelo Quart no mesmo processo. Python 3.13, uv, pytest.

## Estilo (contrato do repo)

Estas regras não são negociáveis: siga o estilo, não "corrija" o estilo.

- **Nomeia certo.** O nome é a documentação. Se o nome não explica, conserte o nome.
- **Cache L1/L2.** A função tem que caber inteira na cabeça de uma olhada. Precisou pular de função em função pra entender? É bug de design — refatore.
- **Repetiu, virou factory.** 5 linhas repetidas em 2+ lugares viram factory num arquivo de config que gera o código: a config declara os dados, o código itera a config.
- **Template > código copiado.** Loop sobre lista de config substitui N handlers quase idênticos. Adicionar um caso = editar uma lista.
- **Comentário só referencia a DOC.** Explicação vai pra `docs/`/`CONTEXT.md`; no código fica só a referência. Docstring que renderiza doc real (OpenAPI, help do discord, contrato não-óbvio de método) permanece.
- **Ticket = 1 linha.** `TODO(SMI-xx): ...` aponta o tracker, não explica a DOC.
- **Invariante vira nome.** Contrato expresso na assinatura — sufixo `_unlocked` — nunca em comentário.
- Fora: docstring de módulo, banner de seção (`# ===`, `<!-- -->`), comentário-eco (`<!-- Toast Container -->` sobre `id="toast-container"`), why-comment.

## Regras do repo

- **Uma superfície por verbo.** Toda ação de playback passa pela `PlaybackSession` via `run_on_bot_loop` (src/api/deps.py). A API JSON de música morreu por isso (docs/ADR) — não ressuscitar.
- **Loops diferentes.** Quart e bot rodam em loops distintos; discord.py chamado de handler sem `run_on_bot_loop` trava.
- **Painel = HTMX.** Páginas Jinja + fragmentos HTMX polando. Sem API JSON de consumo.
- **Toda rota tem chamador real.** Endpoint órfão = deletar. Stub vivo (com botão na UI) fica com TODO de 1 linha.
- **Contexto do painel.** Um helper projeta o status da sessão; cada página resolve só o que renderiza.
- **Single source of truth.** Loop mode = 1 dicionário junto do enum, importado por painel e cogs. Navegação = loop sobre lista. Nunca 2 cópias da mesma lista.
- Glossário (sessão, fila, camada, painel): `CONTEXT.md`.

## Testes

- **Testa o essencial, do código vivo.** Comportamento externo, sem detalhe de implementação; quando der, escreve o teste antes.
- **Fake é seam, mock é mentira.** Fakes de `tests/conftest.py` são classes reais que substituem o cliente discord. Mock que esconde comportamento não é teste.
- Código morto sai junto com o teste que o pina. Suíte sempre 100% verde.

## Verificação

Terminou: `make format`, depois `make check` (ruff, ty, vulture, pytest, prettier). Não aumente `ignore_names` do vulture pra silenciar código morto.
