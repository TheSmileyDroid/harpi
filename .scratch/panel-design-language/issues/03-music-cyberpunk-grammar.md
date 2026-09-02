# 03: Cyberpunk grammar on the music surface

**What to build:** The music page speaks the secondary grammar: queue rows carry metadata (status, duration) in a right-hand column; cards get boxed TVA titles and a segmented action strip along their bottom edge; the transport bar conforms to the new tokens with the playing row bracketed. Verified live: `make dev` with the test bot plays a real track while screenshots and computed-style checks run.

**Blocked by:** 02 (bracket on the playing row).

**Status:** ready-for-agent

- [ ] Queue rows show a right-hand metadata column; row title truncates without breaking layout.
- [ ] Music cards use double borders, boxed titles, and a bottom-edge segmented action strip.
- [ ] Transport bar uses the new tokens; paused reads dim amber; errors use only `alert` tokens.
- [ ] Quart-client tests assert the queue/transport markup carries the new structure.
- [ ] Playwriter loop with the test bot playing: screenshot before/after, computed-style check on tokens and fonts, mobile-width sanity look.
- [ ] `make format` and `make check` exit 0.
