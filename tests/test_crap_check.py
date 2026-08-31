from types import SimpleNamespace

import pytest

from tools.crap_check import crap_score, function_crap, violations


def block(name, lineno, endline, complexity, classname=None):
    return SimpleNamespace(
        name=name,
        lineno=lineno,
        endline=endline,
        complexity=complexity,
        classname=classname,
    )


def test_crap_score_fully_covered_is_complexity():
    assert crap_score(5, 1.0) == 5


def test_crap_score_uncovered_is_comp_squared_plus_comp():
    assert crap_score(3, 0.0) == 3**2 + 3


def test_function_crap_partial_coverage():
    name, crap, _complexity, coverage = function_crap(
        block("fn", 10, 20, 4),
        frozenset(range(10, 16)),
        frozenset(range(16, 21)),
    )
    assert name == "fn"
    assert coverage == pytest.approx(6 / 11)
    assert crap == pytest.approx(4**2 * (5 / 11) ** 3 + 4)


def test_function_crap_zero_statements_counts_as_covered():
    name, crap, _complexity, coverage = function_crap(
        block("empty", 1, 5, 1), frozenset(), frozenset()
    )
    assert name == "empty"
    assert coverage == pytest.approx(1.0)
    assert crap == 1


def test_function_crap_names_methods_with_class():
    name, _, _, _ = function_crap(
        block("run", 2, 3, 2, classname="Bot"), frozenset({2, 3}), frozenset()
    )
    assert name == "Bot.run"


def make_report(executed, missing):
    return {
        "files": {
            "sample.py": {
                "executed_lines": sorted(executed),
                "missing_lines": sorted(missing),
            }
        }
    }


def test_violations_sorted_worst_first(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sample.py").write_text("x = 1\n")
    worst = block("worst", 1, 5, 10)
    mild = block("mild", 6, 8, 9)
    import tools.crap_check as mod

    monkeypatch.setattr(mod, "cc_visit", lambda source: [mild, worst])
    monkeypatch.setattr(mod, "SCAN_ROOTS", ())
    monkeypatch.setattr(mod, "SCAN_FILES", ("sample.py",))
    bad = violations(make_report(range(1, 9), ()), fail_over=8)
    assert [entry[2] for entry in bad] == ["worst", "mild"]
    assert bad[0][3] == 10


def test_violations_respect_threshold(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sample.py").write_text("x = 1\n")
    import tools.crap_check as mod

    monkeypatch.setattr(mod, "cc_visit", lambda source: [block("fn", 1, 5, 3)])
    monkeypatch.setattr(mod, "SCAN_ROOTS", ())
    monkeypatch.setattr(mod, "SCAN_FILES", ("sample.py",))
    assert violations(make_report(range(1, 6), ()), fail_over=8) == []
