# AGENTS.md — Harpi

Bot do Discord (música, dados, TTS) + painel web HTMX servido pelo Quart no mesmo processo. Python 3.13, uv, pytest.

## Estilo

Estas regras não são negociáveis: siga o estilo, não "corrija" o estilo.

- **Nomeia certo.** O nome é a documentação. Se o nome não explica, conserte o nome.
- **Template > código copiado.**
- **Comentário só referencia a DOC.** no código fica só a referência. Docstring que renderiza doc real (OpenAPI, help do discord) permanece.
- **Invariante vira nome.** Contrato expresso na assinatura — sufixo `_unlocked` — nunca em comentário.
- Fora: docstring de módulo, banner de seção (`# ===`, `<!-- -->`), comentário-eco (`<!-- Toast Container -->` sobre `id="toast-container"`), why-comment.
- **[Locality of Behaviour (LoB)](https://htmx.org/essays/locality-of-behaviour/)** - "The behaviour of a unit of code should be as obvious as possible by looking only at that unit of code"

## Verificação

Terminou: `make format`, depois `make check` (ruff, ty, vulture, pytest, prettier). Não aumente `ignore_names` do vulture pra silenciar código morto.
