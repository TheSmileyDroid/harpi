"""CRAP gate: per-function cyclomatic complexity x coverage. Ref: https://testing.googleblog.com/2011/02/code-coverage-goal-and-crap-score.html"""

import argparse
import json
import sys
from pathlib import Path

from radon.complexity import cc_visit

DEFAULT_FAIL_OVER = 8

SCAN_ROOTS = ("src", "pages")
SCAN_FILES = ("app.py",)


def crap_score(complexity: int, coverage: float) -> float:
    return complexity**2 * (1 - coverage) ** 3 + complexity


def function_crap(
    block, executed: frozenset[int], missing: frozenset[int]
) -> tuple[str, float, int, float]:
    lines = executed | missing
    total = sum(
        1 for line in range(block.lineno, block.endline + 1) if line in lines
    )
    covered = total - sum(
        1 for line in range(block.lineno, block.endline + 1) if line in missing
    )
    coverage = covered / total if total else 1.0
    name = block.name
    if getattr(block, "classname", None):
        name = f"{block.classname}.{block.name}"
    return (
        name,
        crap_score(block.complexity, coverage),
        block.complexity,
        coverage,
    )


def violations(
    coverage_report: dict, fail_over: float = DEFAULT_FAIL_OVER
) -> list[tuple[str, int, str, float, int, float]]:
    found: list[tuple[str, int, str, float, int, float]] = []
    files = coverage_report["files"]
    for root in SCAN_ROOTS:
        for path in sorted(Path(root).rglob("*.py")):
            key = str(path)
            if key not in files:
                continue
            found.extend(_violations_for_file(key, files[key], fail_over))
    for path in SCAN_FILES:
        if path in files:
            found.extend(_violations_for_file(path, files[path], fail_over))
    return sorted(found, key=lambda v: v[3], reverse=True)


def _violations_for_file(path: str, file_data: dict, fail_over: float):
    executed = frozenset(file_data["executed_lines"])
    missing = frozenset(file_data["missing_lines"])
    blocks = cc_visit(Path(path).read_text(encoding="utf-8"))
    for block in blocks:
        name, crap, complexity, coverage = function_crap(
            block, executed, missing
        )
        if crap > fail_over:
            yield (path, block.lineno, name, crap, complexity, coverage)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("coverage_json", type=Path)
    parser.add_argument("--fail-over", type=float, default=DEFAULT_FAIL_OVER)
    args = parser.parse_args()
    try:
        report = json.loads(args.coverage_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(
            f"cannot read coverage report {args.coverage_json}: {error}",
            file=sys.stderr,
        )
        return 2
    bad = violations(report, args.fail_over)
    for path, lineno, name, crap, complexity, coverage in bad:
        print(
            f"{path}:{lineno} {name} CRAP={crap:.1f} (comp={complexity}, cov={coverage:.2f})"
        )
    if bad:
        print(f"{len(bad)} function(s) over CRAP {args.fail_over:g}")
        return 1
    print(f"clean: no function over CRAP {args.fail_over:g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
