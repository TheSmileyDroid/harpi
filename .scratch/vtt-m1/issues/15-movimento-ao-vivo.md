# 15: Movimento ao vivo

**What to build:** Arrastar um token mostra o preview local e chega ao outro lado enquanto o dedo anda, sem travar a mesa. O commit é no soltar e o último soltar vence.

**Blocked by:** 14 — Stream da mesa.

**Status:** ready-for-agent

- [ ] O cliente manda lote para `/moves` com `drag_id` e `final`, mantendo um POST em voo por arraste.
- [ ] O servidor aceita na ordem, incrementa `stream_rev` e `tokens.rev`, e transmite estado absoluto; o caminho de movimento não responde 409.
- [ ] O commit acontece no soltar, a cada 5 s durante o arraste e no `pagehide`.
- [ ] Jogador move só o token do próprio Sheet; narrador move qualquer um; posição fora do mapa é 422.
- [ ] O token entra no Tab; as setas movem uma célula e Shift mais setas movem cinco; Enter abre a ficha.
- [ ] O balde de 600/min responde 429; o cliente cai para 1 Hz por 30 s e volta sem perder o destino.
- [ ] O arraste alheio mostra a marca de 3 s, sem bloquear ninguém.
- [ ] Dois navegadores convergem; `make check` verde.
