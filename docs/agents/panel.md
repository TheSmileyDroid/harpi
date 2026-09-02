# Panel and HTMX work

Commands and panel are one feature on two surfaces. Fixing one is not fixing the feature. Before calling music work done, walk this list:

- **Surfaces.** play, pause, skip, seek, queue and layers are reachable from both a `MusicCog` command and a `pages/music.py` action. If you added one, check the other.
- **Reverse states.** If you added a way in, add the way out. Connect needs disconnect. Loop on needs loop off. A one-way door is a bug.
- **Both loops.** Panel code that touches discord.py internals goes through `run_on_bot_loop`, never calls the coroutine directly. See [architecture.md](architecture.md).
- **Templates.** Panel behavior lives next to its markup (LoB): the block the HTMX request targets, the handler that serves it, in `pages/` and `templates/pages/` together.

## Before writing panel patterns

Before writing fragment handlers, `hx-*` attributes, polling, or panel scripting, read `.opencode/skills/htmx-panel/SKILL.md`: the official htmx essay patterns mapped to this stack, plus the known debt list.
