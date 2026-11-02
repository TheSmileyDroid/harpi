from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

import tools.check_report as mod
from tools.check_report import (
    Finding,
    Gate,
    Result,
    accept,
    clone_fingerprint,
    parse_contract_diff,
    parse_crap,
    parse_eslint,
    parse_jscpd,
    parse_knip,
    parse_prettier,
    parse_pytest,
    parse_ruff,
    parse_ruff_format,
    parse_svelte,
    parse_ty,
    parse_vitest,
    parse_vulture,
    render,
    select,
)

RUFF_LOG = """\
src/a.py:10:5: F401 `os` imported but unused
src/b.py:2:1: E402 Module level import not at top of file
Found 2 errors.
"""

TY_LOG = """\
src/a.py:4:12: error[invalid-return-type] Return type does not match
Found 1 diagnostic
"""

VULTURE_LOG = "src/a.py:7: unused function 'helper' (60% confidence)\n"

CRAP_LOG = """\
src/a.py:10 run CRAP=12.0 (comp=4, cov=0.25)
1 function(s) over CRAP 8
"""

PYTEST_LOG = """\
Required test coverage of 70% reached. Total coverage: 95.02%
1721 passed, 3 warnings in 19.31s
"""

JUNIT = """\
<testsuites>
  <testsuite name="pytest" tests="3" failures="1">
    <testcase classname="tests.test_a" name="test_ok" />
    <testcase classname="tests.test_a" name="test_bad">
      <failure message="assert 1 == 2">traceback</failure>
    </testcase>
  </testsuite>
</testsuites>
"""

SVELTE_LOG = """\
/mnt/work/web/src/App.svelte:12:3
Error: Cannot find name 'x'. (ts)
svelte-check found 1 error and 2 warnings
"""


def test_parse_ruff_counts_findings():
    summary, findings = parse_ruff(RUFF_LOG, Path())
    assert summary == "2 issues"
    assert [finding.where for finding in findings] == [
        "src/a.py:10",
        "src/b.py:2",
    ]
    assert findings[0].message.startswith("F401")


def test_parse_ruff_clean():
    assert parse_ruff("All checks passed!\n", Path()) == ("clean", [])


def test_parse_ty_reads_concise_lines():
    summary, findings = parse_ty(TY_LOG, Path())
    assert summary == "1 error"
    assert findings[0].where == "src/a.py:4"


def test_parse_vulture_and_crap():
    assert parse_vulture(VULTURE_LOG, Path())[0] == "1 dead name"
    summary, findings = parse_crap(CRAP_LOG, Path())
    assert summary == "1 function over CRAP 8"
    assert findings[0].where == "src/a.py:10 run"


def test_parse_ruff_format_lists_files():
    summary, findings = parse_ruff_format(
        "Would reformat: src/a.py\n1 file would be reformatted\n", Path()
    )
    assert summary == "1 file(s) would reformat"
    assert findings[0].where == "src/a.py"


def test_parse_ruff_format_clean_counts_formatted():
    summary, findings = parse_ruff_format(
        "164 files already formatted\n", Path()
    )
    assert summary == "164 files formatted"
    assert findings == []


def test_parse_prettier():
    summary, findings = parse_prettier("[warn] web/src/a.ts\n", Path())
    assert summary == "1 file(s) not formatted"
    assert findings[0].where == "web/src/a.ts"


def test_parse_contract_fails_only_with_a_diff():
    assert parse_contract_diff("", Path()) == ("no diff", [])
    summary, findings = parse_contract_diff(
        "M\tweb/src/lib/contract/a.ts\n", Path()
    )
    assert summary == "1 generated file(s) differ"
    assert findings[0].message.startswith("regenerate")


def test_parse_pytest_reads_junit_failure(tmp_path):
    (tmp_path / "pytest.xml").write_text(JUNIT)
    summary, findings = parse_pytest(PYTEST_LOG, tmp_path)
    assert summary == "1721 passed · coverage 95.02%"
    assert [finding.where for finding in findings] == [
        "tests/test_a.py::test_bad"
    ]
    assert findings[0].message == "assert 1 == 2"


def test_parse_pytest_without_report_still_summarizes(tmp_path):
    summary, findings = parse_pytest(PYTEST_LOG, tmp_path)
    assert summary == "1721 passed · coverage 95.02%"
    assert findings == []


def test_parse_svelte_pairs_file_and_message():
    summary, findings = parse_svelte(SVELTE_LOG, Path())
    assert summary == "1 error · 2 warnings"
    assert findings[0].where == "/mnt/work/web/src/App.svelte:12"
    assert findings[0].message == "Cannot find name 'x'."


def test_parse_eslint_groups_messages(tmp_path):
    (tmp_path / "eslint.json").write_text(
        json.dumps([
            {
                "filePath": "/w/a.ts",
                "messages": [
                    {"line": 3, "ruleId": "no-unused-vars", "message": "x"}
                ],
            }
        ])
    )
    summary, findings = parse_eslint("", tmp_path)
    assert summary == "1 problem"
    assert findings[0].where == "/w/a.ts:3"


def test_parse_knip_reads_issue_rows(tmp_path):
    (tmp_path / "knip.json").write_text(
        json.dumps({
            "issues": [
                {
                    "file": "src/a.ts",
                    "exports": [{"name": "gone", "line": 9}],
                }
            ]
        })
    )
    summary, findings = parse_knip("", tmp_path)
    assert summary == "1 issue"
    assert findings[0].where == "src/a.ts:9"
    assert findings[0].message == "exports gone"


def test_parse_vitest_reads_coverage_summary(tmp_path, monkeypatch):
    summary_file = tmp_path / "coverage-summary.json"
    summary_file.write_text(json.dumps({"total": {"lines": {"pct": 91.08}}}))
    monkeypatch.setattr(mod, "VITEST_SUMMARY", summary_file)
    summary, _ = parse_vitest(
        "Tests  262 passed (262)\n % Coverage report from v8\n", tmp_path
    )
    assert summary == "262 passed · lines 91.08%"


def clone(fragment, first, second, lines=10):
    return {
        "fragment": fragment,
        "lines": lines,
        "firstFile": {"name": first, "start": 1},
        "secondFile": {"name": second, "start": 2},
    }


def test_clone_fingerprint_ignores_indent_and_blank_lines():
    assert clone_fingerprint("a = 1\n  b = 2") == clone_fingerprint(
        "  a = 1\n\nb = 2\n"
    )
    assert clone_fingerprint("a = 1") != clone_fingerprint("a = 2")


def test_parse_jscpd_reports_only_new_clones(tmp_path, monkeypatch):
    known = clone("known", "src/a.py", "src/a.py")
    new = clone("fresh", "src/b.py", "src/b.py")
    write_jscpd(tmp_path, [known, new])
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps({
            "version": 1,
            "accept": [
                {
                    "fingerprint": clone_fingerprint("known"),
                    "lines": 10,
                    "where": "src/a.py:1 ↔ src/a.py:2",
                    "reason": "triaged",
                }
            ],
        })
    )
    monkeypatch.setattr(mod, "BASELINE", baseline)
    summary, findings = parse_jscpd("", tmp_path)
    assert summary == "2 clones · 1 known · 1 new"
    assert len(findings) == 1
    assert findings[0].where == "src/b.py:1 ↔ src/b.py:2"
    assert clone_fingerprint("fresh") in findings[0].message


def write_jscpd(reports, duplicates):
    directory = reports / "jscpd"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "jscpd-report.json").write_text(
        json.dumps({"duplicates": duplicates})
    )


def test_accept_records_reason_in_baseline(tmp_path, monkeypatch):
    write_jscpd(tmp_path, [clone("fresh", "src/b.py", "src/b.py")])
    baseline = tmp_path / "baseline.json"
    monkeypatch.setattr(mod, "BASELINE", baseline)
    monkeypatch.setattr(mod, "REPORTS", tmp_path)
    monkeypatch.setattr(mod, "LOGS", tmp_path / "logs")
    code = accept(clone_fingerprint("fresh")[:8], "triaged by hand")
    assert code == 0
    entry = json.loads(baseline.read_text())["accept"][0]
    assert entry["reason"] == "triaged by hand"
    assert entry["fingerprint"] == clone_fingerprint("fresh")


def test_accept_refuses_unknown_fingerprint(tmp_path, monkeypatch, capsys):
    write_jscpd(tmp_path, [])
    monkeypatch.setattr(mod, "REPORTS", tmp_path)
    monkeypatch.setattr(mod, "LOGS", tmp_path / "logs")
    assert accept("deadbeef", "reason") == 2
    assert "no clone" in capsys.readouterr().err


def test_result_fails_closed_on_exit_code():
    gate = Gate("ruff", "py", "true", parse_ruff)
    failed = Result(gate, 1, 0.1, "clean", [])
    assert not failed.ok
    assert Result(gate, 0, 0.1, "clean", []).ok


def test_result_can_fail_on_findings():
    gate = Gate(
        "contract", "py", "true", parse_contract_diff, fails_on_findings=True
    )
    assert not Result(gate, 0, 0.1, "1 differ", [Finding("a", "b")]).ok


def test_select_rejects_unknown_gate():
    with pytest.raises(SystemExit):
        select(args(fast=False, only="nope"))


def test_fast_skips_the_deep_gates():
    chosen = select(args(fast=True))
    names = {gate.name for gate in chosen}
    assert {"pytest", "ruff", "eslint"} <= names
    assert names.isdisjoint({"crap", "vulture", "jscpd", "knip"})


def test_render_lists_failures_first():
    ok = Result(Gate("ruff", "py", "true", parse_ruff), 0, 0.1, "clean", [])
    bad = Result(
        Gate("ty", "py", "true", parse_ty, tail=True),
        1,
        0.4,
        "1 error",
        [Finding("src/a.py:4", "invalid-return-type")],
    )
    text = render([ok, bad], 1.0, full=False, label="make check")
    assert "FAILED: ty" in text
    assert "src/a.py:4" in text
    assert "PASS  ruff" in text


def args(fast=False, only="", full=False):
    return argparse.Namespace(fast=fast, only=only, full=full)


def test_baseline_entry_without_reason_does_not_accept(tmp_path, monkeypatch):
    write_jscpd(tmp_path, [clone("fresh", "src/b.py", "src/b.py")])
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps({
            "version": 1,
            "accept": [
                {
                    "fingerprint": clone_fingerprint("fresh"),
                    "lines": 10,
                    "where": "src/b.py:1 ↔ src/b.py:2",
                    "reason": "   ",
                }
            ],
        })
    )
    monkeypatch.setattr(mod, "BASELINE", baseline)
    summary, findings = parse_jscpd("", tmp_path)
    assert summary == "1 clones · 0 known · 1 new"
    assert len(findings) == 1


def test_vitest_ignores_stale_coverage_in_fast_mode(tmp_path, monkeypatch):
    summary_file = tmp_path / "coverage-summary.json"
    summary_file.write_text(json.dumps({"total": {"lines": {"pct": 91.08}}}))
    monkeypatch.setattr(mod, "VITEST_SUMMARY", summary_file)
    summary, _ = parse_vitest("Tests  262 passed (262)\n", tmp_path)
    assert summary == "262 passed"


def test_render_labels_the_fast_profile():
    ok = Result(Gate("ruff", "py", "true", parse_ruff), 0, 0.1, "clean", [])
    text = render([ok], 1.0, full=False, label="make check-fast")
    assert text.splitlines()[0] == "make check-fast · 1 gate · 0 failed · 1s"
