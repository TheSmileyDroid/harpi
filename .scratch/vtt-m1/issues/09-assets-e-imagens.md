# 09: Assets e imagens

**What to build:** O narrador e o jogador enviam uma imagem e ela pode virar retrato ou mapa sem sair da campanha. Imagem do vault é servida do lugar onde está, por nome, nunca por caminho do cliente.

**Blocked by:** 03 — Personagens e cards.

**Status:** ready-for-agent

- [ ] Upload aceita PNG, JPG e WebP por sniff, até 16 MB, re-encoda para tirar EXIF e nomeia pelo sha256; mesmo hash não reescreve.
- [ ] A cota de 100 MB por campanha responde 413; asset órfão não é servido.
- [ ] As rotas de asset e de imagem recebem nome, conferem a raiz com `realpath`, exigem arquivo regular e extensão da allowlist; o resto é 404 sem detalhe.
- [ ] Cache é privado, com ETag, Last-Modified e 304.
- [ ] Upload e leitura respeitam os buckets, o CSRF e o limite de corpo; o edge aceita 17 MB só em `/api/campaigns/`.
- [ ] Contrato regenerado e `make check` verde.
