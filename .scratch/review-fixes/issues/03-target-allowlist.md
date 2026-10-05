# 03: Target validation is an allowlist

**What to build:** The HTMX target validation declares itself as a set of valid target names instead of a dictionary that maps most names to themselves. Unknown targets are rejected; known targets behave exactly as before.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] Target validation is a set of valid names; membership, not identity mapping.
- [x] An unknown target is still rejected (existing page-test behavior unchanged).
- [x] All known targets pass validation exactly as before.
- [x] `make format` then `make check` passes.
