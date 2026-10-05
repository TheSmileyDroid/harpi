# 06: Mobile — collapse to one column, keep the identity

**What to build:** At narrow widths every new component degrades to a single column with reduced chrome and the design language intact: action strips wrap to full-width segments, right-hand metadata columns collapse under the row title, brackets and tokens behave the same. Density collapses; the language doesn't switch off.

**Blocked by:** 03, 04 (the components being collapsed).

**Status:** done

- [x] Music and home pages render one column at mobile width with no horizontal scroll.
- [x] Action strips and metadata columns degrade legibly (no truncation dead-ends).
- [x] Status chip, transport bar, and header keep their identity at mobile width.
- [x] Playwriter loop at mobile viewport (`make dev` running): screenshots of both pages, plus one landscape-ish tablet width for the two-column grid.
