# 10: Retire the old panel

**What to build:** The old panel and its transport are gone and the repo carries one interface. This is the contract step of the cutover, and it is the only ticket where main would notice a regression, so it merges last with every gate green.

**Blocked by:** 05, 09

**Status:** ready-for-agent

- [ ] htmx, the Jinja panel templates, the fragments dependency, and all HX plumbing are removed
- [ ] Template-oriented tests are removed or rewritten at the API seam; no test asserts a deleted surface
- [ ] The template-oriented gates go with the template tree, and no other gate is lowered to compensate
- [ ] Frontend and API gates stay green, and the bot-surface tests are unedited and green
- [ ] The repo is clean of stale references to the removed transport
