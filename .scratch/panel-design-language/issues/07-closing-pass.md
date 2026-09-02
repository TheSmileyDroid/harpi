# 07: Closing pass — conformance gates and visual review pack

**What to build:** The whole migration lands green and reviewable: `make format` then `make check` exit 0 on the final tree, and a review pack of desktop + mobile captures of every page is produced so the maintainer can judge fidelity against the reference images (the taste call is human; the mechanical violations were already caught in-loop).

**Blocked by:** 05, 06.

**Status:** ready-for-agent

- [ ] `make format` and `make check` exit 0 with no skipped or lowered gates.
- [ ] Review pack saved: desktop and mobile captures of home, music (idle and playing), and the offline state.
- [ ] Each capture shot at the same viewport sizes so the maintainer can compare against `references/` side by side.
- [ ] Any known deviations from the design doc are listed explicitly in the ticket comments rather than left silent.
