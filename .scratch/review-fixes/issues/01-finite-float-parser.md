# 01: One finite-float parser for both surfaces

**What to build:** Seek and volume inputs on both surfaces go through one shared parser in the domain layer. A non-finite number (NaN, infinity) is rejected with consistent, user-facing behavior whether it arrives from a Discord command or a panel action. Each surface formats its own error message; the parse-and-reject logic exists once.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] The three near-identical parse routines collapse into one shared finite-float helper owned by the domain layer; no command or page hand-rolls the try-float-reject-non-finite shape anymore.
- [ ] A Discord seek command with a non-finite number is rejected with a clear error reply (tested at the command level with a fake message).
- [ ] A Discord volume command behaves the same way, through the same helper.
- [ ] A panel seek or volume action with a non-finite number is rejected through the same helper (tested at the page-handler level).
- [ ] The helper's name says what it does without a comment.
- [ ] `make format` then `make check` passes.
