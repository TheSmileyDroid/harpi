# 05: HTMX behavior — loading indicator and silent polling

**What to build:** The panel signals activity without strobing: one subtle global indicator (thin fixed bar or caret, in the new tokens) shows during any HTMX request; buttons that trigger an action show local `hx-indicator` feedback; the 2-second status poll swaps invisibly when nothing changed. No skeletons, no boot animation on appearing fragments.

**Blocked by:** 01 (indicator uses the new tokens).

**Status:** done

- [x] Global indicator element exists, is subtle, and clears when requests finish.
- [x] Every explicit action button declares its own loading feedback.
- [x] Status polling produces no visible change when the state is unchanged.
- [x] No skeleton or entrance animation on polling fragments.
- [x] Quart-client tests assert the indicator element and indicator attributes in rendered pages.
- [x] Playwriter loop (panel running via `make dev`): observe several poll cycles for stillness, then trigger an action and capture the indicator firing.
