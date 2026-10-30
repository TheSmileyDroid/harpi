# Ops do vault e backup

Type: task
Status: resolved
Blocked by: 04

## Question

O que precisa existir no host e no container para o Harpi ler e escrever no vault com segurança?

Decidir e executar:

- bind mount do vault no container, read-write só em `Harpi/`.
- `HARPI_VAULT_PATH` em `src/config.py` e `.env.example`.
- backup antes de escrita e retenção.
- Syncthing: conflito, arquivo temporário, permissões.
- disco e memória com 122 MB de vault.
- checklist de verificação no host.

Resolução: checklist e configuração aplicada, ou handoff preciso.

## Answer

O vault entra no container em duas camadas: `/vault` somente leitura e `/vault/Harpi` leitura e escrita. O app já limita a escrita a `Harpi/Campaigns/<slug>/` por código, e o mount impede que um bug escreva no resto do vault. `HARPI_VAULT_PATH=/vault` é o caminho que o app lê. O caminho do host fica em `HARPI_VAULT_HOST_PATH`, porque o compose não pode derivar um do outro.

### Aplicado

- `docker-compose.yml` monta `"${HARPI_VAULT_HOST_PATH:?set HARPI_VAULT_HOST_PATH}:/vault:ro"` e `".../Harpi:/vault/Harpi:rw"`. O compose falha se a variável não existir, em vez de criar uma pasta vazia em silêncio.
- `docker-compose.yml` fixa `user: "1000:1000"`. O host tem `opc` 1000:1000, o vault é `opc:opc`, e o usuário `harpi` da imagem também é 1000. Escrever no vault não depende de ACL.
- `src/config.py` ganhou `Settings.vault_path`, lido de `HARPI_VAULT_PATH`, com string vazia virando `None`.
- `.env.example` lista as duas variáveis, separando o caminho do app do caminho do host.
- `.env` do host recebeu `HARPI_VAULT_HOST_PATH="/home/opc/external/sync/backup paratheos"`. O arquivo não é versionado.
- `/home/opc/external/sync/backup paratheos/Harpi` criado como `opc:opc 755`. A árvore `Campaigns/<slug>/` fica para o app criar.
- `data/vault-backups` criado como `opc:opc 755`, no bind `./data`, fora do vault e do Syncthing.

Verificação no container: `/vault/index.md` é legível, escrita em `/vault` responde `Read-only file system`, e escrita em `/vault/Harpi/.probe` sai como `1000:1000 644`.

### Backup e retenção

- Antes de sobrescrever uma ficha, o escritor do ticket 04 grava a versão anterior em `data/vault-backups/<slug>/<harpi-id>/<rev>-<timestamp>.md`, com retenção de 20 por arquivo.
- No container o caminho é `/app/data/vault-backups`. O escritor resolve a raiz por `Path(settings.db_path).parent / "vault-backups"`, não por caminho relativo ao cwd, que é `/work`.
- O bind `./data` sobrevive a recriação do container. O diretório fica fora do vault, então não entra no Syncthing e não aparece na campanha do Obsidian.
- O backup diário do SQLite continua em `/work/backups`, com 7 cópias, como `src/panel/backup.py` já faz.
- Não há snapshot do vault inteiro no M1. A cópia fora do host é o Syncthing, com 8 dispositivos, e o trashcan guarda 30 dias. O `data` e o vault estão no mesmo `/dev/sdb1`, então o backup de ficha protege contra erro do app e remoção acidental, não contra falha do disco.

### Syncthing

- A pasta `Sync` cobre `~/external/sync` em sendreceive, watcher com atraso de 10 s, varredura de 3600 s, trashcan de 30 dias e `maxConflicts=10`.
- `.stignore` na raiz do Sync ganhou `(?d).harpi-tmp-*`. O escritor precisa do temporário na mesma pasta para o `os.replace` atômico, e o ignore evita que um processo morto no meio da escrita propague um arquivo parcial.
- O app já ignora `*.sync-conflict-*`, `~syncthing~*`, dotfiles e dotdirs. Arquivo de conflito do Syncthing fica no disco para o narrador resolver no Obsidian. O app nunca escolhe qual versão é a verdadeira.
- Permissões: pastas 755, arquivos 644, dono 1000. `ignorePerms=false`, então o modo viaja entre dispositivos. `sendOwnership=false`, então cada peer usa o próprio usuário. Rodar o Syncthing com outro uid no host exige ACL ou mudança no mount.

### Disco e memória

- O vault mede 69 MB, não 122 MB. São 521 arquivos, 66 MB em `Recursos/anexos`, zero symlinks.
- `/home/opc/external` tem 59 GB livres. `/` tem 6.0 GB livres e está em 84% de uso, mas o vault e o `data` não ficam nele.
- O host tem 23.7 GB de RAM e cerca de 4.1 GB disponíveis. O container tem limite de 1 GB e usava 110.7 MiB.
- A retenção de 20 por ficha guarda poucos KB por arquivo. Não há ação de disco no M1.

### Checklist no host

```bash
VAULT="/home/opc/external/sync/backup paratheos"
stat -c '%u:%g %a %n' "$VAULT" "$VAULT/Harpi" data/vault-backups
docker inspect harpi-backend --format '{{range .Mounts}}{{.Destination}} rw={{.RW}} {{.Source}}{{"\n"}}{{end}}'
docker exec harpi-backend printenv HARPI_VAULT_PATH
docker exec harpi-backend sh -c 'head -c 40 /vault/index.md; touch /vault/Harpi/.probe && rm /vault/Harpi/.probe'
docker exec harpi-backend sh -c 'touch /vault/.probe'
find "$VAULT" \( -name '*.sync-conflict-*' -o -name '~syncthing~*' -o -name '.harpi-tmp-*' \) -print
du -sh "$VAULT"
df -h /home/opc/external
free -m
docker stats --no-stream harpi-backend
```

Esperado: dono 1000:1000 e modo 755, `/vault` com `rw=false`, `/vault/Harpi` com `rw=true`, `HARPI_VAULT_PATH=/vault`, leitura do `index.md`, escrita no `Harpi` aceita, escrita na raiz recusada, nenhum conflito nem temporário na listagem, e os números de disco e memória acima.

### O que só o humano pode fazer

- Manter o Syncthing rodando e resolver qualquer `*.sync-conflict-*` no Obsidian. O app não adota nem apaga esses arquivos.
- Se o uid ou gid de `opc` mudar, atualizar `user:` no `docker-compose.yml` e ajustar o dono de `Harpi`. Fora isso, a escrita falha sem causa visível.
- Se o vault mudar de lugar no host, atualizar `HARPI_VAULT_HOST_PATH` no `.env`.
- Uma cópia local independente do disco do vault não está no M1. Hoje a cópia fora do host são os peers do Syncthing.

A leitura da raiz e o 503 `vault_unavailable` continuam no ticket 08. Este ticket só entrega a configuração de host e container.
