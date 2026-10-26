# Exposição pública do Harpi: plano de segurança

## Veredito

O Harpi não deve receber um subdomínio público no estado atual. Cinco bloqueadores P0 permitem assumir o login de um usuário, controlar guildas de terceiros, ler segredos da imagem ou usar o servidor como proxy para a rede interna. A correção é pequena em escopo e cabe em duas fases antes de criar o registro DNS ou o proxy host.

A auditoria partiu do commit `4e05358` em `main`, rodou o código em um contêiner `harpi-sec-audit` sem portas publicadas e sem rede, e leu a configuração real do Nginx Proxy Manager em `/home/opc/external/nginx/data/database.sqlite`. Os testes de rota usaram `curl` dentro do contêiner.

## Escopo e método

O alvo é a superfície web: `app.py`, `pages/`, `src/panel/`, `src/storage/`, o `Dockerfile`, o `docker-compose.yml` e o proxy. O bot Discord entra apenas onde a fronteira web alcança o bot, como autorização por guilda e o comando `!shutdown`.

Cada controle foi confrontado com três fontes independentes. Repositórios com pelo menos 1.000 estrelas recebem peso 7 na escala de autoridade, padrões como ASVS e RFC recebem peso 8, e documentação oficial de uma ferramenta em uso recebe peso 10. As estrelas foram consultadas na API do GitHub em 2026-10-25, não estimadas. Todo repositório citado como ferramenta ou guia tem pelo menos 5.000 estrelas. ASVS e Quart ficam abaixo desse corte, mas entram como padrão e documentação primária do stack.

## Decisões de projeto

| Tema | Decisão |
| --- | --- |
| Terminologia | O login do painel é "login" e o cookie é "cookie de login". **Session** continua reservado ao estado de playback. |
| Entrada | Allowlist de guildas: The Nosbor's Hand (`734174030701264906`) e o servidor do RPG (`896066642948259960`). Só membro de uma guilda aprovada entra no painel. |
| Operação | Qualquer membro da guilda aprovada opera o player. Não há cargo de DJ nesta fase. |
| URLs | No modo público, só YouTube e CDN. O modo LAN pode ampliar por configuração. |
| Rede | NPM e Harpi na rede Docker `harpi-edge`. Sem `ports`, proxy para `harpi-backend:8000`. |
| Login | Cookie `__Host-harpi` com `Secure` e 7 dias absolutos, mais `login_epoch` no SQLite. |
| Domínio e HSTS | Mantém `harpi.smileydroid.com.br`. HSTS sem `includeSubDomains`. |
| Capacidade | Até 10 viewers e 2 guildas. Limites conservadores. |
| Edição da allowlist | `PANEL_GUILD_ALLOWLIST` no `.env`, com restart para aplicar. |
| Logout | Global por usuário via `login_epoch`. |
| Admin do proxy | Interface 81 só via Tailscale (`100.106.27.40`). |
| DNS | Registro.br direto ao NPM, sem Cloudflare. |
| Segredos | `.env` com 0600 fora do build. `cookies.txt` montado como leitura. |
| Alertas e backup | Webhook do Discord em canal privado e backup diário local. |
| Bot | `!shutdown` restrito ao dono. |
| Retenção | 30 dias para viewers e connection_events. |
| Aceite | Checklist, testes automatizados e scan externo de portas. Sem pentest contratado nesta fase. |

## Achados

### P0-1. A imagem Docker carrega segredos e dados pessoais

O `Dockerfile` copia o diretório inteiro com `COPY . /app`, e o `Dockerfile.dockerignore` só exclui oito caminhos. Ele não exclui `.env`, `.env.bak`, `.env.bak-redirect`, `cookies.txt`, `spam.log`, `discord.log`, `data/`, `.git`, `.scratch` ou `.opencode`. A imagem local `harpi-backend`, construída em dezembro, contém `/app/.env` com 236 bytes e `/app/cookies.txt` com 2.901 bytes, confirmado por `docker run --rm --entrypoint sh harpi-backend -c 'ls -l /app/.env /app/cookies.txt'`.

O impacto é direto. Quem obtém a imagem obtém o token do Discord, o cookie mestre da conta YouTube, o cliente OAuth, o banco de viewers e os logs. O diretório de trabalho também tem 4,1 MB de `spam.log` e 9,6 MB de `discord.log` que entram no build.[^dockersecrets][^owaspsecrets][^gitleaks]

Correção: ampliar `Dockerfile.dockerignore` para excluir `.env*`, `cookies.txt`, `*.log`, `data/`, `.git/`, `.scratch/`, `.opencode/`, `.coverage`, `coverage.json`, `__pycache__/`, `mutants/`, `tests/` e `docs/`. Construir a partir de um contexto limpo ou usar `RUN --mount=type=secret` para o que precisar existir no build. Rodar `trivy image --scanners secret` e `gitleaks detect` na imagem e no histórico antes de publicar. Rotacionar o token do Discord e o cookie do YouTube, porque a imagem antiga já existe no host.

Aceite: `docker run --rm IMAGE ls /app/.env /app/cookies.txt` falha, o scanner de segredos não encontra nada, e os segredos antigos foram invalidados.

### P0-2. O contêiner publica a porta 8000 e monta o repositório com escrita

O `docker-compose.yml` publica `8000:8000`, o que vincula a aplicação em todas as interfaces do host. O comando sobe o Uvicorn em `0.0.0.0`. O mesmo arquivo monta `./:/app` com leitura e escrita, então um RCE na aplicação escreve no repositório do host, incluindo `.env`, `cookies.txt` e `.git/hooks`.

Hoje a porta 8000 escuta em `127.0.0.1` pelo processo `python -m src`, não em `0.0.0.0`. O compose, porém, publica `8000:8000` e sobe o Uvicorn em `0.0.0.0`; quando o contêiner sobe, a porta fica pública e o acesso direto por HTTP ignora TLS, HSTS, rate limit e qualquer header do proxy. A entrada antiga do proxy aponta para `172.17.0.1:8000`, ou seja, para a porta publicada no host, não para o contêiner.[^cisdocker][^dockerbench][^dockercompose]

Correção: remover `ports`, colocar Nginx Proxy Manager e Harpi na rede Docker `harpi-edge` e apontar o proxy para `harpi-backend:8000`. Montar apenas `data/`, um diretório de trabalho gravável e `cookies.txt` como leitura, nunca o repositório inteiro. Manter `--host 0.0.0.0` dentro do contêiner é aceitável quando não há publicação no host. O firewall do host deve permitir 80 e 443 e bloquear 8000.

Aceite: `ss -tlnp | grep 8000` não retorna nada no host, o proxy alcança `harpi-backend:8000` pelo nome, e `curl http://IP_PUBLICO:8000/` expira.

### P0-3. Qualquer usuário autenticado controla todas as guildas do bot

O login busca as guildas do usuário, mas usa o resultado apenas para exigir uma interseção não vazia com as guildas do bot. O conjunto de guildas do usuário é descartado em `pages/auth.py:69-71`. O login guarda `user_id`, `username` e `display_name`, mas não guarda as guildas permitidas em `pages/auth.py:101-109`.

A checagem de acesso em `src/panel/state.py:29-30` pergunta apenas se o bot está na guilda. `pages/api.py:98-101` lista todas as guildas do bot, e `pages/api.py:117-131` conecta em qualquer guilda visível. Os endpoints de seleção e transporte seguem o mesmo caminho. Não existe verificação por usuário em nenhuma rota.

O resultado é que um membro de uma guilda compartilhada vê nomes de canais e guildas de todos os servidores do bot, conecta o bot em qualquer canal, enfileira URLs e desconecta o playback de terceiros. Isso é A01 Broken Access Control e viola o controle cross-tenant do ASVS 8.4.1.[^asvs8][^authzcs][^top10a01][^wstg]

Correção: criar `PANEL_GUILD_ALLOWLIST` em `src/config.py`, com `734174030701264906,896066642948259960` como valor inicial. No login, calcular a interseção entre as guildas do usuário, a allowlist e as guildas do bot. Negar o login quando a interseção for vazia. Persistir as guildas permitidas por usuário no SQLite do registry, renovadas no login. Criar uma checagem única, por exemplo `actor_can_access(actor, guild_id)`, e usá-la em `list_guilds`, `read_channels`, `connect`, `selection` e em todo endpoint que resolva guilda. Filtrar a lista de guildas pelo ator. A decisão é só membership, sem cargo de DJ. Adicionar teste de negação cruzada: usuário da guilda A recebe 404 ou 403 na guilda B.

Aceite: dois usuários de guildas diferentes não enxergam nem controlam a guilda um do outro, com teste automatizado cobrindo `GET /api/guilds`, `GET /api/guilds/{id}/channels` e `POST /api/connect`.

### P0-4. O cookie de login não tem Secure, vive 30 dias e não pode ser revogado

`app.py:36-38` define `HttpOnly`, `SameSite=Lax` e 30 dias. Não define `SESSION_COOKIE_SECURE`, não troca o nome padrão `session`, não define limite absoluto e não guarda estado no servidor. O padrão do Quart é `SESSION_COOKIE_SECURE=False`, `PERMANENT_SESSION_LIFETIME=31 dias`, `SESSION_REFRESH_EACH_REQUEST=True` e `TRUSTED_HOSTS=None`.

O contêiner confirma o resultado. `GET /api/auth/discord` devolve `Set-Cookie: session=...; HttpOnly; Path=/; SameSite=Lax`, sem `Secure`. O cookie é assinado, mas não criptografado, e contém `authenticated`, `user_id` e `username`. O logout chama `session.clear()`, que limpa o navegador, mas não invalida uma cópia roubada do cookie. Com renovação a cada requisição, um login ativo nunca expira enquanto for usado.

Há dois agravantes. O domínio pai `smileydroid.com.br` tem outros subdomínios, e um cookie chamado `session` sem prefixo `__Host-` pode ser plantado por um subdomínio irmão. Um cookie de login sem `Secure` também trafega em HTTP se alguém alcançar a porta 8000.[^sesscs][^asvs7][^wstgcookies][^quartdocs]

Correção: definir `SESSION_COOKIE_NAME="__Host-harpi"`, `SESSION_COOKIE_SECURE=True`, `SESSION_COOKIE_SAMESITE="Lax"`, `SESSION_COOKIE_PATH="/"`, `PERMANENT_SESSION_LIFETIME=timedelta(days=7)` e `TRUSTED_HOSTS={"harpi.smileydroid.com.br"}`. Adicionar a migração `0002_login_epoch.sql` com `ALTER TABLE users ADD COLUMN login_epoch INTEGER NOT NULL DEFAULT 0` e a tabela `user_guilds(user_id, guild_id, seen_at)`. Guardar `issued_at` e o `login_epoch` por usuário, verificar os dois em cada requisição e incrementar o epoch no logout. As chaves de configuração do Quart continuam com o prefixo `SESSION_COOKIE_*`, porque são a API do framework. Limpar o cookie de login antes de `_establish_session` e emitir um cookie novo no login. Em desenvolvimento local, condicionar `Secure` e o prefixo a uma flag de ambiente.

Aceite: `Set-Cookie` mostra `__Host-harpi`, `Secure`, `HttpOnly`, `SameSite=Lax` e `Path=/`. Um cookie antigo deixa de valer após o logout. Um login com mais de sete dias é rejeitado. Um `Host: evil.example` recebe 400.

### P0-5. O Harpi busca qualquer URL informada pelo usuário

`src/harpi_lib/music/ytmusic.py:164-190` aceita qualquer `http://` ou `https://` com um ponto no host e entrega a URL ao `yt-dlp`. `src/harpi_lib/music/ytdl_source.py:280-292` chama `extract_info` nessa URL. `pages/api.py:179-186` expõe isso em `/api/search`, e `pages/api.py:214-227` em `/api/queue`. O `ffmpeg` também busca a URL de stream escolhida em `src/harpi_lib/music/stream_probe.py`.

O teste no contêiner comprova a busca. Com `internal.test` apontando para `127.0.0.1`, o `yt-dlp` fez `GET / HTTP/1.1` no servidor local antes de rejeitar o conteúdo como não suportado. O mesmo caminho alcança `http://169.254.169.254.nip.io/`, `http://router.local/`, serviços na rede Docker e qualquer host que resolva para IP privado. Um redirecionamento de um host público para um IP interno também passa, porque não há checagem do IP resolvido.[^ssrfcs][^asvs13][^ytdlp][^ytdlpadv]

Correção: no modo público, aceitar apenas URLs do YouTube e do CDN, com `allowed_extractors` restrito a `youtube`, `youtube:tab` e `youtube:search`. O modo LAN pode ampliar a lista por configuração. Resolver o DNS antes da chamada, rejeitar loopback, RFC1918, link-local, multicast e o endereço de metadados, e repetir a checagem depois de cada redirecionamento. Desligar o extrator genérico. Aplicar uma política de egress no host ou na rede Docker que bloqueie `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `169.254.0.0/16` e `::1`. Limitar duração, tamanho e quantidade de itens de playlist.

Aceite: `POST /api/queue` com `http://internal.test:9099/` retorna 400, o contêiner não alcança `169.254.169.254` nem `172.17.0.1`, e uma URL normal do YouTube continua funcionando.

### P1-1. Não há limite de requisições, corpo ou conexões

O proxy não tem `limit_req`. A aplicação não tem middleware de quota. O Quart aceita 16 MB de corpo por padrão. O stream SSE em `pages/events.py` não limita conexões por usuário. O executor do `yt-dlp` tem um worker, mas a fila de espera não tem teto. Cada busca ou fila consome CPU, rede e cota do YouTube.

O impacto é negação de serviço e custo. Um único cliente abre dezenas de SSE, dispara buscas em paralelo e enche a fila do executor. Um corpo de 16 MB por requisição também pressiona memória.[^api4][^nginxlimit][^npmadv][^fail2ban]

Correção: definir zonas `limit_req` no `http.conf` customizado do Nginx Proxy Manager e aplicá-las por local. Dimensionar para até 10 viewers e 2 guildas. No proxy, limitar `/api/auth/*` a 10 requisições por minuto por IP e `/api/*` a 60 por minuto por IP, com burst pequeno. Na aplicação, limitar `/api/search` a 20 por minuto por usuário. Definir `client_max_body_size 64k` no host. Na aplicação, definir `MAX_CONTENT_LENGTH=64*1024`, um token bucket por usuário para busca e fila, teto de 5 conexões SSE por usuário e 20 por guilda, e `429` com `Retry-After`. Adicionar `pids_limit: 256`, `mem_limit: 1g` e `cpus` ao compose.

Aceite: 30 buscas em um minuto a partir do mesmo IP retornam 429, um corpo de 1 MB retorna 413, e 100 streams abertos param no teto configurado.

### P1-2. Faltam headers de segurança, CSP e o schema OpenAPI é público

As respostas do contêiner não trazem `Content-Security-Policy`, `Strict-Transport-Security`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` ou `X-Frame-Options`. O header `Server: uvicorn` aparece em todas as respostas. `GET /openapi.json`, `/docs`, `/redocs` e `/scalar` retornam 200 sem autenticação.

O schema lista todas as rotas, modelos e campos, incluindo `ConnectRequest`, `UrlRequest` e `StatusSnapshot`. Isso não vaza segredo, mas reduz o trabalho de quem procura a superfície. A ausência de CSP e `frame-ancestors` permite clickjacking, e a ausência de `nosniff` piora qualquer falha de tipo de conteúdo.[^headerscs][^cspcs][^helmet][^mdnframe]

Correção: adicionar um `after_request` em `app.py` com HSTS, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy`, `X-Frame-Options: DENY` e CSP com `default-src 'self'`, `frame-ancestors 'none'`, `base-uri 'none'`, `object-src 'none'`. O `index.html` tem um script inline do SvelteKit e carrega Google Fonts, então a primeira versão precisa de `script-src 'self' 'unsafe-inline'` e das origens `fonts.googleapis.com` e `fonts.gstatic.com`, ou de fontes hospedadas no próprio domínio. A versão final usa hash do script inline gerado no build.

Desligar a documentação em produção com `QuartSchema(app, openapi_path=None, redoc_ui_path=None, scalar_ui_path=None, swagger_ui_path=None, ...)`. O alvo `make contract` lê `app.extensions["QUART_SCHEMA"].openapi_provider` diretamente, então continua funcionando. Ocultar `Server` com `--no-server-header` no Uvicorn ou `proxy_hide_header Server` e `server_tokens off` no Nginx.

Aceite: `curl -I https://harpi...` mostra os headers, `/openapi.json` retorna 404 ou 401, e um teste de injeção de script inline é bloqueado pela CSP final.

### P1-3. O host e o proxy têm portas e entradas obsoletas

O host escuta em `0.0.0.0:81` (interface administrativa do Nginx Proxy Manager), `0.0.0.0:22` (SSH), `0.0.0.0:111` (rpcbind), `0.0.0.0:8096` (Jellyfin) e várias interfaces em `52082` (qBittorrent). O banco do proxy tem duas entradas para `harpi.smileydroid.com.br`, ambas com `is_deleted=1`, uma apontando para 8050 e outra para 8000. As duas usam o certificado 2, expirado em 2026-09-18 e marcado como removido. Os únicos hosts ativos são `smileydroid.com.br` e `home.smileydroid.com.br`.

O impacto é indireto e grave. Quem entra na interface do proxy reescreve rotas e certificados. Quem entra no qBittorrent ou no Jellyfin alcança a rede e o host. O rpcbind exposto amplia a superfície de NFS. O certificado vencido quebra HTTPS e induz o usuário a aceitar exceção.[^npmrepo][^tlscs][^nginxhandbook][^linuxguide][^nist123]

Correção: firewall permitindo apenas 80 e 443 na interface pública. Mover 81 para o Tailscale (`100.106.27.40`) e 22, 111, 8096 e 52082 para LAN ou VPN. O DNS fica no Registro.br, sem Cloudflare no caminho. Colocar fail2ban na interface do proxy e no SSH. Apagar as duas linhas antigas do Harpi e criar um único proxy host com certificado Let's Encrypt válido, `Force SSL`, HTTP/2, HSTS sem `includeSubDomains`, `Block Common Exploits` e WebSocket. Desligar `server_tokens`.

Aceite: um scan externo vê apenas 80 e 443, a interface do proxy não responde na internet, `curl -I https://harpi...` retorna certificado válido e existe exatamente uma linha de proxy host.

### P1-4. Logs, banco e backups expõem dados

`app.py:27-29` grava DEBUG em `spam.log` sem rotação. O arquivo tem 4,1 MB e cresce. `src/harpi_lib/music/ytmusic.py:28` liga `verbose: True` no `yt-dlp`, que pode imprimir cabeçalhos de requisição no stdout do contêiner. `ytmusic.py:259` registra o termo de busca ou a URL informada. `data/harpi.db` está com modo 644 e contém nomes de usuários e histórico de conexões. Existem `.env.bak` e `.env.bak-redirect` no diretório de trabalho.

O impacto é vazamento de PII, de termos de busca e, no pior caso, de cookies em log. O banco legível por qualquer usuário local do host também é um problema.[^loggingcs][^top10a09][^asvs16]

Correção: rotação e retenção no Loguru, nível INFO em produção, redaction de URL, token e cookie, `verbose=False` e `quiet=True` no `yt-dlp`, log de segurança separado, `chmod 600` no banco, remoção dos backups e limpeza de 30 dias para `viewers` e `connection_events`. O log de segurança registra login, falha de login, logout, negação de acesso, mudança de seleção e erro 5xx, com user id, IP e timestamp UTC, sem corpo de requisição.

Aceite: os logs rotacionam, um grep por `token`, `cookie` e `Authorization` não encontra valor sensível, o banco está em 600 e os backups não existem.

### P2. Itens de operação contínua

O CSRF depende só de `SameSite=Lax`. Todas as mutações são POST, então o risco é baixo, mas falta uma checagem de `Origin` ou `Sec-Fetch-Site` para defesa em profundidade. Adicionar no `before_request` para métodos não seguros, com exceção do callback OAuth.[^csrfcs][^rfc9700][^discordoauth][^oauthcs]

O `Host` não é validado. `curl -H "Host: evil.example"` retorna 200. Definir `TRUSTED_HOSTS` resolve.

O comando `!shutdown` em `src/cogs/basic.py:177-180` não verifica permissão. Qualquer membro de qualquer guilda derruba o bot. Restringir ao ID do dono fecha esse vetor.

A imagem usa tags móveis `oven/bun:1` e `ghcr.io/astral-sh/uv:python3.13-bookworm-slim`. Fixar por digest. Rodar `osv-scanner` e `trivy image` no CI, manter `uv.lock` e `bun.lock` versionados, e habilitar Dependabot ou Renovate.[^osv][^trivy][^scorecard]

Não há monitoramento, alerta nem backup testado. Adicionar webhook do Discord em canal privado para 401, 403, 429, 5xx, crescimento de conexões SSE e uso de disco. Fazer backup diário local do `data/harpi.db` com checkpoint do WAL e testar a restauração. Escrever um runbook de incidente que cubra rotação de `SECRET_KEY`, token do Discord, cookie do YouTube e credenciais do proxy.

## Plano por fases

### Fase 0, antes de criar DNS ou proxy host

1. Corrigir o contexto de build, reconstruir a imagem, rodar scanner de segredos e rotacionar token e cookies.
2. Remover a publicação da porta 8000, montar só dados e cookie em leitura, e colocar proxy e app na mesma rede.
3. Implementar autorização por guilda em todas as rotas e testes de negação cruzada.
4. Endurecer o cookie de login, adicionar `login_epoch`, limite absoluto e `TRUSTED_HOSTS`.
5. Restringir URLs e extratores do `yt-dlp`, validar IP resolvido e aplicar egress deny para redes privadas.

### Fase 1, antes de anunciar o subdomínio

1. Adicionar headers, CSP e desligar OpenAPI e UIs de documentação.
2. Aplicar rate limit no proxy e quotas na aplicação, com corpo máximo de 64 KB.
3. Limpar o proxy, emitir certificado válido, mover 81 para o Tailscale e fechar 22, 111, 8096 e 52082 na interface pública.
4. Configurar rotação de log, redaction, permissão 600 no banco e remoção de backups.
5. Rodar o checklist de verificação abaixo em uma cópia de staging.

### Fase 2, primeira semana no ar

1. Ligar alertas no Discord, backup local e teste de restauração.
2. Rodar `osv-scanner`, `trivy image` e `gitleaks` no CI.
3. Fazer o scan externo e os testes do checklist com OWASP WSTG, cobrindo autenticação, cookie de login, autorização, SSRF e rate limit. Pentest contratado fica fora desta fase.
4. Restringir `!shutdown` ao dono e revisar permissões do bot.
5. Configurar a limpeza de 30 dias para `viewers` e `connection_events`.
6. Repetir o scan de portas e a revisão de proxy host a cada mudança de infraestrutura.

## Gate de liberação

Não criar o registro DNS nem o proxy host enquanto todos os itens abaixo não estiverem marcados.

O checklist com o comando que prova cada item, a evidência a registrar e a ordem de liberação está em [release-gate.md](release-gate.md). O script `deploy/release-gate.sh` automatiza a prova de que o gate está fechado (`--pre`), os testes de liberação (`--release`) e o scan externo de portas (`--ports`).

- [ ] A imagem não contém `.env`, `cookies.txt`, logs, banco ou `.git`.
- [ ] Token do Discord e cookie do YouTube foram rotacionados depois da última imagem antiga.
- [ ] A porta 8000 não está publicada no host.
- [ ] NPM e Harpi estão na rede `harpi-edge` e o proxy usa `harpi-backend:8000`.
- [ ] A allowlist de guildas está configurada e um login fora dela é negado.
- [ ] A allowlist é editada por `PANEL_GUILD_ALLOWLIST` e exige restart.
- [ ] Um usuário da guilda A recebe 403 ou 404 para a guilda B em todos os endpoints.
- [ ] O cookie de login é `__Host-`, `Secure`, `HttpOnly`, `SameSite=Lax`, com limite absoluto e revogação.
- [ ] O logout invalida todos os dispositivos via `login_epoch`.
- [ ] Os segredos estão em `.env` com 0600 fora do build.
- [ ] URL interna, IP privado e redirecionamento para IP privado são rejeitados.
- [ ] `/openapi.json`, `/docs`, `/redocs` e `/scalar` não respondem em produção.
- [ ] Headers e CSP estão presentes.
- [ ] Rate limit e corpo máximo respondem 429 e 413.
- [ ] O certificado é válido, o proxy host é único e o HSTS está sem `includeSubDomains`.
- [ ] A interface 81 do NPM só responde no Tailscale.
- [ ] SSH, rpcbind, Jellyfin e qBittorrent não respondem na internet.
- [ ] `!shutdown` é owner-only.
- [ ] A retenção de 30 dias está configurada.
- [ ] Alertas no Discord e backup local foram testados.
- [ ] Logs não contêm token, cookie ou senha.
- [ ] Backup e restauração foram testados.

## Verificação

O harness usado nesta auditoria continua disponível no host. Ele não publica portas e não tem rede.

```bash
docker run -d --name harpi-sec-audit --network none \
  -e SECRET_KEY=audit-only-not-a-real-secret-0123456789abcdef \
  -e DISCORD_CLIENT_ID=000000000000000000 \
  -e DISCORD_REDIRECT_URI=http://localhost:8000/api/auth/discord/callback \
  -e HARPI_DB_PATH=/tmp/harpi-audit.db \
  harpi-sec-audit:latest
```

Testes de rota que devem passar depois da Fase 1:

```bash
docker exec harpi-sec-audit sh -c '
curl -s -o /dev/null -w "session=%{http_code}\n" http://127.0.0.1:8000/api/session
curl -s -o /dev/null -w "events=%{http_code}\n" http://127.0.0.1:8000/api/events
curl -s -o /dev/null -w "openapi=%{http_code}\n" http://127.0.0.1:8000/openapi.json
curl -s -o /dev/null -w "docs=%{http_code}\n" http://127.0.0.1:8000/docs
curl -sS -D - -o /dev/null http://127.0.0.1:8000/api/auth/discord | grep -i set-cookie
'
```

Esperado: `session=401`, `events=401`, `openapi=404`, `docs=404`, e o cookie com `__Host-`, `Secure`, `HttpOnly`, `SameSite=Lax`.

Teste de SSRF que deve falhar depois da correção:

```bash
docker exec harpi-sec-audit sh -c '
cd /app && .venv/bin/python - <<"PY"
import yt_dlp
try:
    yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True, "socket_timeout": 5}).extract_info("http://internal.test:9099/", download=False)
    print("FETCHED")
except Exception as e:
    print("BLOCKED", type(e).__name__)
PY
'
```

Esperado: `BLOCKED`, e nenhum `GET /` no servidor local.

Teste de autorização cruzada, com dois usuários de guildas diferentes e o bot conectado, deve retornar 403 ou 404 para a guilda não compartilhada em `GET /api/guilds`, `GET /api/guilds/{id}/channels`, `POST /api/connect` e `POST /api/selection`.

Teste de allowlist: um usuário cujas guildas não cruzam `PANEL_GUILD_ALLOWLIST` recebe `/?auth=denied` e não cria cookie autenticado. O teste unitário de `_admitted_user` cobre a interseção vazia.

Teste de `login_epoch`: fazer logout, reutilizar o cookie anterior e esperar 401 em `GET /api/session`. O epoch no SQLite deve ter sido incrementado.

Teste de rede: `docker network inspect harpi-edge` lista NPM e Harpi, `ss -tlnp` no host não mostra 8000, e o proxy responde por `harpi-backend:8000`.

Teste do admin do proxy: `curl` para `http://IP_PUBLICO:81` expira e `curl http://100.106.27.40:81` responde. O NPM não deve escutar em `0.0.0.0:81`.

Teste de retenção: inserir um viewer e um connection_event com data acima de 30 dias, rodar a limpeza e esperar zero linhas antigas.

Teste do `!shutdown`: um membro comum recebe negação e o dono derruba o bot. O teste unitário cobre a checagem de ID.

Teste de backup: restaurar o dump em um banco temporário e comparar as contagens de `users`, `viewers` e `connection_events`.

Teste de headers:

```bash
curl -sS -D - -o /dev/null https://harpi.smileydroid.com.br/ | grep -i -E "strict-transport|content-security|x-content-type|referrer-policy|permissions-policy|x-frame"
```

Teste de portas, de fora da rede:

```bash
nmap -Pn -p 22,80,81,111,443,8000,8096,52082 harpi.smileydroid.com.br
```

Esperado: 80 e 443 abertos, o resto filtrado.

## Fontes por controle

Cada linha tem três fontes independentes. A coluna de estrelas foi consultada na API do GitHub.

| Controle | Fonte 1 | Fonte 2 | Fonte 3 |
| --- | --- | --- | --- |
| Autorização multi-tenant | ASVS 5.0 V8.4.1, 3,7k | Authorization Cheat Sheet, 33,7k | OWASP Top 10:2025 A01, 6,4k |
| Login e cookie | Session Management Cheat Sheet, 33,7k | ASVS 5.0 V7, 3,7k | WSTG Cookies Attributes, 10,1k |
| CSRF e OAuth | CSRF Prevention Cheat Sheet, 33,7k | RFC 9700 | Discord OAuth2 docs |
| Headers e CSP | HTTP Headers Cheat Sheet, 33,7k | CSP Cheat Sheet, 33,7k | Helmet, 10,7k |
| TLS e proxy | TLS Cheat Sheet, 33,7k | Nginx Proxy Manager, 34,5k | nginx-admins-handbook, 14,3k |
| Rate limit e DoS | OWASP API4:2023 | nginx limit_req docs | NPM Advanced Configuration |
| SSRF | SSRF Prevention Cheat Sheet, 33,7k | ASVS 5.0 V13.2.4 e V13.2.5, 3,7k | yt-dlp security advisory, 201k |
| Contêiner | CIS Docker Benchmark | Docker Bench, 9,7k | Docker build secrets docs |
| Segredos | Secrets Management Cheat Sheet, 33,7k | Gitleaks, 30,3k | TruffleHog, 28,7k |
| Logs e alerta | Logging Cheat Sheet, 33,7k | OWASP Top 10:2025 A09, 6,4k | Fail2ban, 18,9k |
| Cadeia de suprimentos | OSV-Scanner, 11,3k | Trivy, 38,7k | OpenSSF Scorecard, 5,8k |
| Host | How To Secure A Linux Server, 31,8k | NIST SP 800-123 | Fail2ban, 18,9k |

## Limites

A reachability pública não foi confirmada. O DNS de `harpi.smileydroid.com.br` aponta para `136.248.101.41`, mas conexões a 80 e 443 a partir do próprio host expiram, o que impede distinguir bloqueio de firewall, NAT ou indisponibilidade. O plano assume que o subdomínio será liberado e trata a exposição como nova.

O teste de autorização cruzada foi feito por leitura do fluxo de código, não por execução com dois usuários reais. O contêiner de auditoria não tem token do Discord nem bot conectado, então `GET /api/guilds` e `POST /api/connect` não chegaram ao bot. A falha é demonstrável no código, mas a prova ponta a ponta fica para o ambiente de staging.

O vazamento de cookie pelo `yt-dlp` em modo verbose é um risco, não um evento observado. O teste de SSRF provou a busca de URL interna pelo `yt-dlp`, não o envio de cookie para host atacante.

Não foi executado teste de penetração, varredura de vulnerabilidade da imagem, nem auditoria de configuração do host. O plano lista essas etapas como verificação, não como resultado.

## Referências

[^asvs8]: OWASP. "ASVS 5.0 V8 Authorization". 2025. https://github.com/OWASP/ASVS/blob/master/5.0/en/0x17-V8-Authorization.md (3.718 estrelas).
[^authzcs]: OWASP. "Authorization Cheat Sheet". https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html (repositório com 33.736 estrelas).
[^top10a01]: OWASP. "A01:2025 Broken Access Control". https://owasp.org/Top10/2025/A01_2025-Broken_Access_Control/ (repositório com 6.379 estrelas).
[^wstg]: OWASP. "Web Security Testing Guide, Authorization Testing". https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/ (10.113 estrelas).
[^sesscs]: OWASP. "Session Management Cheat Sheet". https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html (33.736 estrelas).
[^asvs7]: OWASP. "ASVS 5.0 V7 Session Management". 2025. https://github.com/OWASP/ASVS/blob/master/5.0/en/0x16-V7-Session-Management.md (3.718 estrelas).
[^wstgcookies]: OWASP. "WSTG, Cookies Attributes". https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management/02-Cookies_Attributes (10.113 estrelas).
[^quartdocs]: Pallets. "Quart Configuration". https://quart.palletsprojects.com/en/latest/how_to_guides/configuration/ (3.678 estrelas).
[^csrfcs]: OWASP. "Cross-Site Request Forgery Prevention Cheat Sheet". https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html (33.736 estrelas).
[^rfc9700]: IETF. "RFC 9700, Best Current Practice for OAuth 2.0 Security". 2025. https://www.rfc-editor.org/rfc/rfc9700.html
[^discordoauth]: Discord. "OAuth2". https://docs.discord.com/developers/topics/oauth2
[^oauthcs]: OWASP. "OAuth 2.0 Protocol Cheatsheet". https://cheatsheetseries.owasp.org/cheatsheets/OAuth2_Cheat_Sheet.html (33.736 estrelas).
[^headerscs]: OWASP. "HTTP Security Response Headers Cheat Sheet". https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html (33.736 estrelas).
[^cspcs]: OWASP. "Content Security Policy Cheat Sheet". https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html (33.736 estrelas).
[^helmet]: Helmet. "Help secure Express apps with HTTP headers". https://github.com/helmetjs/helmet (10.739 estrelas).
[^mdnframe]: MDN. "Content-Security-Policy: frame-ancestors". https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors
[^tlscs]: OWASP. "Transport Layer Security Cheat Sheet". https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html (33.736 estrelas).
[^npmrepo]: Nginx Proxy Manager. https://github.com/NginxProxyManager/nginx-proxy-manager (34.529 estrelas).
[^npmadv]: Nginx Proxy Manager. "Advanced Configuration". https://nginxproxymanager.com/advanced-config/.
[^nginxhandbook]: trimstray. "nginx-admins-handbook". https://github.com/trimstray/nginx-admins-handbook (14.334 estrelas).
[^api4]: OWASP. "API4:2023 Unrestricted Resource Consumption". https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/
[^nginxlimit]: nginx. "Module ngx_http_limit_req_module". https://nginx.org/en/docs/http/ngx_http_limit_req_module.html
[^ssrfcs]: OWASP. "Server-Side Request Forgery Prevention Cheat Sheet". https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html (33.736 estrelas).
[^asvs13]: OWASP. "ASVS 5.0 V13 Configuration". 2025. https://github.com/OWASP/ASVS/blob/master/5.0/en/0x22-V13-Configuration.md (3.718 estrelas).
[^ytdlp]: yt-dlp. https://github.com/yt-dlp/yt-dlp (201.871 estrelas).
[^ytdlpadv]: yt-dlp. "Downstream command injection via improper metadata handling". https://github.com/yt-dlp/yt-dlp/security/advisories/GHSA-6v4j-43gg-vj32
[^cisdocker]: Center for Internet Security. "CIS Docker Benchmark". https://www.cisecurity.org/benchmark/docker
[^dockerbench]: Docker. "Docker Bench for Security". https://github.com/docker/docker-bench-security (9.709 estrelas).
[^dockersecrets]: Docker. "Build secrets". https://docs.docker.com/build/building/secrets/.
[^dockercompose]: Docker. "Define services in Docker Compose". https://docs.docker.com/reference/compose-file/services/.
[^owaspsecrets]: OWASP. "Secrets Management Cheat Sheet". https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html (33.736 estrelas).
[^gitleaks]: Gitleaks. https://github.com/gitleaks/gitleaks (30.318 estrelas).
[^trufflehog]: TruffleHog. https://github.com/trufflesecurity/trufflehog (28.698 estrelas).
[^loggingcs]: OWASP. "Logging Cheat Sheet". https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html (33.736 estrelas).
[^top10a09]: OWASP. "A09:2025 Security Logging and Alerting Failures". https://owasp.org/Top10/2025/A09_2025-Security_Logging_and_Alerting_Failures/ (6.379 estrelas).
[^asvs16]: OWASP. "ASVS 5.0 V16 Security Logging and Error Handling". 2025. https://github.com/OWASP/ASVS/blob/master/5.0/en/0x25-V16-Security-Logging-and-Error-Handling.md (3.718 estrelas).
[^fail2ban]: Fail2ban. https://github.com/fail2ban/fail2ban (18.866 estrelas).
[^osv]: Google. "OSV-Scanner". https://github.com/google/osv-scanner (11.264 estrelas).
[^trivy]: Aqua Security. "Trivy". https://github.com/aquasecurity/trivy (38.705 estrelas).
[^scorecard]: OpenSSF. "Scorecard". https://github.com/ossf/scorecard (5.791 estrelas).
[^linuxguide]: imthenachoman. "How To Secure A Linux Server". https://github.com/imthenachoman/How-To-Secure-A-Linux-Server (31.840 estrelas).
[^nist123]: NIST. "SP 800-123, Guide to General Server Security". 2008. https://csrc.nist.gov/pubs/sp/800/123/final
