# Review fixes: panel truthfulness, shared parsing, deterministic tests

Status: ready-for-agent

## Problem Statement

The panel can show a guild list that no longer matches reality: after the bot joins a new guild or reconnects, the page keeps serving a list captured the first time it was asked. Bot state must explain itself, and a panel that lies about which guilds exist breaks that promise. Separately, the codebase carries three near-identical copies of a float-parsing routine, one unreachable guard, a mapping that is really an allowlist, an inference about skipped tracks that no test pins, and one test that relies on a timed sleep, which violates the repo rule that tests are deterministic and make the suite flaky on slow machines.

## Solution

The panel fetches the guild list fresh on every request, so what it displays always reflects the bot's actual connections. The redundant guard goes away. One shared finite-float parser serves both surfaces (Discord commands and panel actions) with consistent error messages. The allowlist declares itself as a set of valid targets, not a self-mapping dictionary. The skipped-tracks inference is pinned by a test so it can't silently rot. The seek-serialization test proves queue-jumping is impossible through causally ordered assertions, with no timing dependence.

## User Stories

1. As a panel user, I want the guild list to show every guild the bot is currently connected to, so that I never moderate a guild the bot has already left or miss one it just joined.
2. As a panel user, I want the guild list to be correct immediately after the bot reconnects, so that a network blip doesn't leave me staring at a stale roster.
3. As a panel user, I want the guild list to be correct the first time I open the panel after the bot boots, so that I don't need to refresh to see my guild.
4. As a maintainer, I want the panel to re-evaluate the guild list on each request rather than caching it forever, so that the "bot state explains itself" invariant holds on the web surface too.
5. As a maintainer, I want no unreachable guard clauses in the panel code, so that readers don't waste time reasoning about code paths that cannot happen.
6. As a maintainer, I want one shared routine for parsing finite floats, so that a fix to float handling (like rejecting NaN or infinity) lands everywhere at once.
7. As a Discord user, I want seek and volume commands to reject non-finite numbers with the same clear error message style the panel uses, so that both surfaces feel like one product.
8. As a panel user, I want seek and volume fields to reject non-finite numbers with the same clear error message, so that both surfaces feel like one product.
9. As a maintainer, I want the HTMX target allowlist expressed as a set of valid names, so that adding or removing a target block is a one-line, intention-revealing change.
10. As a maintainer, I want the skipped-tracks inference (a session left idle right after an add means every queued track was skipped) pinned by a test, so that a future change to play semantics cannot silently produce false "all tracks skipped" warnings.
11. As a panel user, I want to trust the skipped-tracks warning, so that I don't re-queue music that is actually still playing.
12. As a maintainer, I want the seek-serialization test to pass without wall-clock timing, so that CI is stable regardless of machine speed or load.
13. As a maintainer, I want the queue-jump property (a second seek may not reach the underlying source while the first holds the lock) proven exactly, so that refactors of the seek path are genuinely guarded, not accidentally green.
14. As a future contributor, I want domain terms in the code to match the glossary (Session, Session manager, Audio controller, Probe), so that I can navigate the audio pipeline by name.
15. As a maintainer, I want each fix to arrive with a focused, deterministic test, so that the CRAP gate and the no-sleep rule stay honest.

## Implementation Decisions

- The panel's guild listing is computed per request from the live bot handle. The module-level cache and its `None` sentinel are removed entirely; there is no TTL or epoch machinery because the list is cheap to compute and polling is seconds apart.
- The bot handle lookup keeps its assert-based contract; the now-unreachable falsy branch following it is deleted.
- A single shared helper parses a string into a finite float and reports failure; the Discord command surface and the panel action surface both call it. Error wording stays user-facing and identical in spirit across surfaces; each surface formats its own message. The helper lives in the domain layer, consistent with the rule that cogs and pages stay thin (parse, delegate, format).
- The HTMX target validation becomes a set of valid target names. Membership, not identity mapping, is the concept.
- The skipped-tracks inference keeps its current semantics and its docstring explaining why; only its test coverage is at stake here.
- The seek-serialization test replaces timing with causality: the fake underlying source records whether it ever observed a second seek while the first was still blocked, and the test asserts the flag is false after both threads join. The sleep and the mid-test assertion are removed. The fake source is test-local; no production hook is added.
- All glossary terms from CONTEXT.md are used as-is in code, tests, and messages. No ADR is written for the probe retry policy (reversible, readable in code).

## Testing Decisions

- Good tests here assert external behavior only: what a command replies, what a panel fragment renders, what the session state reports. Implementation details like private helpers are tested only through their public surfaces.
- Four existing seams, no new ones:
  - Panel page handlers with a fake bot (prior art: the existing music page tests) cover per-request guild listing and the removed dead branch, including a scenario where the bot's guild set changes between requests.
  - Cog command level with fake message objects (prior art: the existing music cog tests) cover the shared finite-float parser through command error replies for both seek and volume.
  - Panel-to-session integration (prior art: the existing panel session integration tests) pins the skipped-tracks inference: tracks skipped produces the warning; a genuinely playing session does not.
  - Test-local fake audio sources (prior art: the existing seek tests) cover the rewritten serialization test.
- Tests stay deterministic: no network, no sleeps, no wall-clock assumptions. The no-sleep rule is now enforced by review finding, and the rewritten seek test is the reference example.

## Out of Scope

- Any change to the probe retry or time-budget policy.
- Any change to play, pause, skip, seek, queue, or layer behavior beyond parsing and message consistency.
- Caching or performance work on the guild listing beyond removing the stale cache.
- New panel features, new pages, or new Discord commands.
- ADRs for any decision in this spec.
- The review's template/CSS findings (there were none).

## Further Notes

- This spec came out of a two-axis code review of the working tree against HEAD; the Spec axis was skipped, so all findings here are standards-driven.
- The domain glossary now lives in CONTEXT.md at the repo root; Session, Session manager, Audio controller, Probe, and Source chain are defined there and should be used verbatim.
- After implementation, run the full gate (`make format` then `make check`); the seek change touches core audio logic, so `make mutants` also applies and survivors must be triaged.
