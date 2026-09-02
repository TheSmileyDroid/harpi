# Taste and judgment calls

## The maintainer's intent

TheSmileyDroid likes simplicity and abstraction, and tests ambitious ideas in the domain — audio, dice, music. Plumbing and machinery stay minimal: when an agent could reuse an existing library or pattern or build its own, reuse wins; reinventing needs explicit human sign-off, like any other rule broken here.

## Rules

- The name is the documentation. If a name does not explain, fix the name.
- Templates over copied code. The copy-paste gate means it.
- An invariant lives in the name, not in a comment.
- A comment references a doc or explains a why. It never narrates the how. Docstrings that render real documentation (command help, API contracts) stay.
- An HTMX block names its target; a page keeps its actions near.
- Find the real constraint, then build the smallest thing that makes correct behavior obvious.
- If a rule here fights the task in front of you, say so loudly and get a human sign-off before breaking it.
