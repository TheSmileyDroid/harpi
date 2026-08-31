---
name: htmx-panel
description: "HTMX panel patterns for Harpi, distilled from the official htmx essays. Use when editing pages/, templates/, or anything htmx: fragment handlers, hx-* attributes, hx-target/hx-swap, polling or SSE status refresh, panel scripting or hyperscript, view transitions. Also use when a panel behavior should exist on the web surface and you are deciding how the server answers."
---

# HTMX panel patterns

Harpi's panel is a hypermedia-driven app: the server owns the state, the browser renders HTML. These patterns come from the official htmx essays, mapped to Quart + Jinja + jinja2-fragments. Each names its source. The "known debt" section lists where the panel does not follow them yet.

## The patterns

**Template fragments, not fragment files.** Every fragment is a named `{% block %}` inside the page's own template. One file holds all HTML for a feature, which keeps Locality of Behaviour true. The Quart equivalent of the essay's `_fragments` helper is `render_block("pages/music.html", "block-name", ...)` from `jinja2_fragments.quart`.
Source: <https://htmx.org/essays/template-fragments/>

**Block dispatch through one handler.** A single action handler serves the full page or the targeted block, branching on one explicit discriminator. One source of truth for context-building: full-page render and fragment render can never drift apart. Do not create parallel fragment endpoints.
Source: <https://github.com/spookylukey/django-htmx-patterns/blob/master/inline_partials.rst>

**UI-shaped endpoints.** Hypermedia endpoints serve this UI and nothing else. Specialize them freely: return exactly the HTML the swap needs, with no JSON layer and no general-purpose API shape. Refactoring them breaks nothing but your own templates.
Source: <https://htmx.org/essays/10-tips-for-ssr-hda-apps/>

**HTML responses, never JSON to interpret.** The server responds with hypermedia; `hx-target` and `hx-swap` decide where it lands. Application state stays on the server so the client stays dumb and refactorable. If a handler starts returning JSON for the panel to reason about, the design has left the hypermedia model.
Source: <https://htmx.org/essays/hypermedia-driven-applications/>

**Script is enhancement only.** Hyperscript or JS may animate, focus, or polish. It must not hold client state or decide playback behavior; htmx events trigger server actions. Client state duplicating server state is the classic SPA failure this stack exists to avoid.
Source: <https://htmx.org/essays/hypermedia-friendly-scripting/>

**Spend the complexity budget on attributes.** Declarative `hx-*` attributes are cheap; script lines are expensive. Declarative polling (`hx-trigger="every 2s"`) over hand-rolled refresh loops. Before adding any script, ask whether an attribute or a server-side branch does the job.
Source: <https://htmx.org/essays/complexity-budget/>

**Server pushes state, client declares interest.** Status refresh is polling or SSE, never a custom JS status loop. Polling (`hx-trigger="every Ns"`) is fine to start. SSE (`hx-ext="sse"` plus a Quart SSE blueprint) is the upgrade path when pollers multiply.
Source: <https://htmx.org/essays/10-tips-for-ssr-hda-apps/>

**Escaped HTML everywhere.** htmx swaps raw HTML, so the XSS surface equals classic server-side rendering. Jinja auto-escapes; `|safe` is banned unless the content is server-generated and reviewed. Never echo user input into `hx-` attributes. State changes are POST, never GET.
Source: <https://htmx.org/essays/web-security-basics-with-htmx/>

**View transitions are free polish.** htmx can drive the View Transitions API on swaps (`htmx.config.globalViewTransitions = true` in layout.html, plus `@view-transition` CSS). No JS state, fits the model. Optional, but prefer it over scripted animations.
Source: <https://htmx.org/essays/view-transitions/>

**Web components: not here.** The repo uses hyperscript for the rare scripting needs. Web components are the essays' alternative extension path; mixing both pays two framework costs for one job.
Source: <https://htmx.org/essays/webcomponents-work-great/>

**Server-side strengths are the point.** The server may cache, precompute, and hold state between requests; the client never re-derives it. The guild cache in `pages/music.py` (`get_guilds`) is the local example: fetched once on the bot loop, reused by every render.
Source: <https://htmx.org/essays/10-tips-for-ssr-hda-apps/>

**Refactor endpoints aggressively.** Hypermedia endpoints have no external clients, so reshaping them is routine maintenance, not a migration. The dispatch in `pages/music.py` has been rewritten (query param, then handler-named blocks, then `HX-Target`) without any consumer noticing.
Source: <https://htmx.org/essays/10-tips-for-ssr-hda-apps/>

**Direct data access, sparingly.** There is no client store here, but the rule still translates: do not repeat expensive calls (status sampling, guild fetches) more than once per request — build the context dict once and pass it down.
Source: <https://htmx.org/essays/10-tips-for-ssr-hda-apps/>

**Avoid modals.** Prefer inline regions and swaps over pop-up flows. Guild and channel selection stay inline on the music page; if a choice needs its own screen-shaped surface, that is a smell the flow is too big.
Source: <https://htmx.org/essays/10-tips-for-ssr-hda-apps/>

**Accept good-enough UX.** The add-by-URL-or-search input is fine as it is. Do not build search-as-you-type, autocomplete, or optimistic UI without a concrete reason; each one buys client state.
Source: <https://htmx.org/essays/10-tips-for-ssr-hda-apps/>

**Islands of interactivity.** The sanctioned place for richer widgets: a small region with its own script inside an otherwise hypermedia page. For this panel the realistic candidate is drag-and-drop queue reordering (SortableJS-style), added only when actually wanted.
Source: <https://htmx.org/essays/10-tips-for-ssr-hda-apps/>

**The scripted escape hatch.** Hyperscript was removed from the repo, but scripting small enhancements (vanilla JS or Alpine, inline, hypermedia-first) remains sanctioned when `hx-*` attributes cannot express the behavior. Script must enhance, never own state — see the complexity-budget pattern above for the cost accounting.
Source: <https://htmx.org/essays/10-tips-for-ssr-hda-apps/>

## Known debt (audit of the current panel)

Fix these when touching the file they live in; do not sweep them speculatively.

- None currently. The 2024 audit items were cleared: block dispatch branches on the `HX-Target` header through the `_TARGET_BLOCKS` id→block mapping in `pages/music.py` (renaming an id is a one-place edit in that dict plus the template), fragment responses are gated on `HX-Request`, the three music-page pollers were consolidated into one `status_panels` wrapper poller, the unused `_hyperscript.min.js` load was dropped, htmx 2.0.4 is vendored at `static/js/htmx.min.js`, and view transitions drive cross-document navigation only (`@view-transition`/`::view-transition-*` fade CSS in `static/css/input.css`; the htmx `globalViewTransitions` config is banned because it fades the whole page on every 2s poll swap). SSE remains the documented upgrade path if pollers multiply again.

Time-dependent panel regressions (pollers eating user input, whole-screen fades) are gated by `tests/test_panel_time_dependent_ui.py`: poller swap regions must not contain live form controls unless `hx-preserve`d, and global view transitions must stay off.

Accepted by the maintainer's audit: `/status` returns a bare fragment rather than a full page on direct navigation.
