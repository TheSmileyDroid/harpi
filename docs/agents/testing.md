# Testing and the gates

## The whole gate

`make format` then `make check`: ruff, ty, djlint, pytest with coverage, the CRAP gate, copy-paste detection, prettier, vulture. One command, exit 0 means done.

## Test rules

- Backend behavior changes ship with focused tests for that behavior.
- Tests are deterministic: no network, no sleeps. A test that needs a timeout to pass is wrong.
- Use fakes, not mocks.

## The CRAP gate

Fails any function whose complexity times its missing coverage exceeds 8 (the bar for AI-written code; the human bar is 6). Complex code needs tests, tested code stays simple. Both count.

## Higher-stakes gates

Touching core audio or dice logic: also run `make mutants` and triage the survivors before calling it done.

## When a gate fails

Fix the cause or delete the dead thing it found. Lowering a threshold, adding an ignore, or writing a test that asserts nothing to make it pass are all worse than leaving it red and saying so.
