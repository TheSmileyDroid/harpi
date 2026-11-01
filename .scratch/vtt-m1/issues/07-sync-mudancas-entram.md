# 07: Sync: mudanças entram

**What to build:** Editar uma ficha no Obsidian ou receber uma mudança pelo Syncthing aparece no painel sem sobrescrever nada. O hash do arquivo é a verdade da mudança.

**Blocked by:** 05 — Ficha: escrita.

**Status:** resolved

- [x] O watcher cobre `Harpi/Campaigns/` com debounce de 500 ms e a varredura de boot e de 60 s compara `mtime` e tamanho.
- [x] Só `characters/*.md` e `sheets/*.md` entram; `config.md` é lido e recarregado, nunca escrito.
- [x] `scenes/`, `tables/`, dotfiles, `*.tmp`, `~syncthing~*` e `*.sync-conflict-*` são ignorados.
- [x] O eco da escrita do app é descartado por hash igual.
- [x] Edição externa é aceita e aparece na ficha; os estados `ok`, `ausente`, `invalido` e `desconhecido` são registrados.
- [x] Rename pelo mesmo `harpi-id` só troca o caminho; id duplicado é sinalizado e ninguém é escolhido sozinho.
- [x] Testes com vault temporário e `make check` verde.
