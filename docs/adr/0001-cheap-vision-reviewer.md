# Cheap vision reviewer with a bounded judging scope

Panel work is judged in two parts, split by checkability. Every design-language rule a test can verify becomes a pytest test (TDD: new rules start red); only what pixels uniquely reveal — spacing rhythm, hierarchy, CRT fidelity, the mobile collapse — goes to a **design review** by a cheap vision-capable model (currently Mimo 2.5; the model is a parameter, the role is the decision). The reviewer sees fixed-viewport screenshots (375, 1280) and produces a **verdict**: per-item pass/fail/inapplicable with evidence. The in-repo capture tool (`tools/design_review.py`) serves the panel offline, shoots it, and prints a digest of the UI bytes; the reviewer writes `.scratch/design-review/verdict.json` carrying that digest, and `make check` fails when the verdict is missing, stale against the digest, or failing. On fail: two fix attempts, then the verdict surfaces — the bar never lowers, and a red gate is never silent.

Why a cheap model: the review runs at gate frequency, and cost scales with every `make check`. Determinism comes from the harness — fixed rubric, fixed viewports, fixed verdict schema — so the model only needs to be consistent, and consistency is enforced by the format, not by model strength. The model is forbidden from judging anything the test suite can judge; that boundary is what lets it be cheap.

## Considered options

- **Strong model judges everything** — costs more per run and still re-judges rules a test settles for free; the vision model's judgment adds nothing where `assert` applies.
- **Skill-only enforcement** — a skill the agent is told to run is advisory; advisory review gets skipped. The gate lives in `make check`, where "exit 0 means done" already rules.

## Consequences

- The capture step needs a served panel; the capture script serves one itself so the gate is reproducible by a human or an agent.
- Design rules that later become testable graduate out of the review into tests, shrinking the vision checklist over time.
