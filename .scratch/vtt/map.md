# VTT do Harpi: spec do M1

Type: wayfinder:map
Status: open

## Destination

Uma spec implementável do marco 1 do VTT do Harpi: uma campanha Paratheos já configurada, Table por campanha presa a um canal de texto, Scene com tokens, névoa por zona e ordem de turno livre, log de dados espelhado entre painel e Discord, e fichas Fate criadas pelos jogadores e sincronizadas com o vault. Entregável: `spec.md`, glossário no `CONTEXT.md` e ADRs, pronto para virar issues de implementação.

## Notes

- Domínio: Fate Core adaptado para Paratheos. Dados de Fate (`4dF`) já funcionam em `src/harpi_lib/math/parser.py`.
- Idioma: interface em português, código, contrato e docs do repo em inglês. Este tracker fica em português.
- Base fixa: Discord OAuth com allowlist de guild; um processo Quart + discord.py; SSE existente; SQLite com migrações; escritas no vault confinadas a `Harpi/Campaigns/<slug>/`.
- Atlas é autoria em Canvas (`.canvas`), viewer somente leitura no M2, editor no Harpi no M3, plugin do Obsidian depois.
- Wiki é manifesto em nota, markdown puro, sem Dataview nem Bases, no M3.
- Consultar: `CONTEXT.md`, `docs/agents/architecture.md`, `docs/agents/panel.md`, `docs/agents/testing.md`, `DESIGN.md`.
- Skills: grilling + domain-modeling nos tickets de decisão; research no ticket de pesquisa; prototype no ticket de UX.

## Decisions so far

- [Decisões do grilling](issues/01-decisoes-do-grilling.md): modelo de Campaign, Character, Sheet, Table, Scene e Content source, com o escopo do M1.
- [Limites do SSE para a mesa](issues/06-limites-do-sse.md): SSE dedicado por Table aguenta 10 Hz com folga; o sampler global e o limite de 60 req/min do NPM no upload são os gargalos; WebSocket só se o upload a 10 Hz for requisito.
- [Esquema da ficha](issues/02-esquema-da-ficha.md): bloco `harpi-sheet` com rank numérico, caixas de estresse, slots de consequência, extras com `kind`, aspectos rotulados no padrão Fate e inventário com quantidade; `harpi-campaign` define escada, perícias, trilhas, slots, recarga e extras.
- [Layout de Character e Sheet](issues/03-layout-character-sheet.md): Character e Sheet em notas separadas sob `Harpi/Campaigns/<slug>/`, ids estáveis no frontmatter, vínculo apenas do Sheet para o Character, e ciclo `pendente`/`ativo`/`arquivado` com o Sheet como verdade.
- [Sync do vault](issues/04-sync-do-vault.md): hash sha256 como verdade da mudança, watcher inotify com varredura de segurança, merge de três vias por campo com identidade por rótulo, conflito explícito que deixa o disco intacto, escrita atômica com CAS e backup fora do vault.
- [Modelo de Table e Scene](issues/05-modelo-table-scene.md): SQLite é a verdade viva; `scenes/` guarda o molde sem tokens e `tables/<table-id>.json` o snapshot; uma Table aberta por campanha e por canal; rodada com um turno por token e passe só para quem ainda não agiu.
- [Transporte e concorrência da mesa](issues/07-transporte-e-concorrencia.md): SSE dedicado por Table com broadcaster em memória e frames recortados por viewer; delta absoluto com `stream_rev` e keyframe de 5 s, coalescido a 10 Hz; movimento por POST em lote com commit no drop; cota própria de 16 viewers por Table.
- [Autorização e arquivos](issues/08-autorizacao-e-arquivos.md): quatro papéis derivados de `members` mais status do Sheet, sem coluna de papel; espectador opt-in por Table; dois recortes de stream no lugar do filtro por viewer; névoa fora do modelo de ameaça; assets resolvidos por recurso, sem caminho de cliente, com upload em `assets/`; personagem revelado em SQLite.
- [Rolagens espelhadas](issues/09-rolagens-espelhadas.md): uma linha em `rolls` por avaliação, com `text` congelado no formato do parser e id `rol_` mais ULID; o painel posta a mensagem no canal antes de gravar, e falha do Discord não grava; sem vínculo com token, sem rolagem secreta e sem expurgo.
- [UX da mesa no painel](issues/10-ux-da-mesa.md): casca B com rail de 14rem e páginas por campanha em `/c/<slug>/`; mesa em duas colunas, ficha em gaveta, revelar por clique na zona, sala oculta invisível para o jogador, turno só com token público, token de 36px arrastável e focável, mapa rolável com zoom no celular; pendente entra por faixa na Mesa.
- [Ops do vault e backup](issues/11-ops-do-vault.md): vault em `/vault:ro` com `/vault/Harpi:rw`, uid 1000 fixado, `HARPI_VAULT_PATH` em `src/config.py`, backups de ficha em `data/vault-backups` com 20 por arquivo, `.harpi-tmp-*` fora do Syncthing e checklist de host.
- [Editor de cenas e zonas](issues/13-editor-de-cenas-e-zonas.md): galeria de cartões e bancada A; origem imagem (índice do vault, upload; embed fora) ou desenho (sala = zona, merge só por sobreposição, borracha corta células); o editor não mostra estado vivo, só aviso e resumo; salvar atômico com hash e recarga explícita na Mesa.
- [Spec, glossário e ADRs do M1](issues/12-spec-glossario-adrs.md): [`spec.md`](spec.md) consolidado em 15 seções, com esquema SQLite emendado, rotas, estados, checklist jogável e riscos; glossário do VTT no `CONTEXT.md`, com espelho em português em [`glossario.md`](glossario.md); ADRs 0010 a 0014 em `docs/adr/`.

## Not yet specified

_Nada. O caminho até o destino está limpo: a spec, o glossário e os ADRs estão escritos e commitados. A implementação do M1 vira issues a partir de [`spec.md`](spec.md) §15, fora deste mapa._

## Out of scope

- Atlas em Canvas e navegação de mapas aninhados: marco 2.
- Wiki dos jogadores, manifesto e editor de notas: marco 3.
- Campanha local sem vault, criação de campanha e convites: marco 2.
- Editor de Atlas no Harpi e plugin do Obsidian: marco 3.
- Editor de arte de mapa no Harpi (pincel, textura, hachura, estilos): o M1 tem retângulo, sala e apagar.
- 5e, grid d20, paredes, luzes e linha de visão.
- Voz própria, chat de texto próprio e importação de PDF/HTML antigos.
- Integração com Foundry, Roll20 ou `.atlasmap`.
