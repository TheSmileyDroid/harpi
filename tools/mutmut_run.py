"""Run mutmut with mutant names that match this repo's `src.*` layout.

mutmut assumes the directory it mutates is the import root: it strips
`src.` from generated mutant names (get_mutant_name) and rejects
`src.`-prefixed trampoline hits (record_trampoline_hit).  This repo
imports everything as `src.*`, so a stripped name never matches the
trampoline prefix (`orig.__module__` is `src.bot_state`, not
`bot_state`) and every mutant would silently run the original code.

This shim keeps the full module path in mutant names and records hits
without the `src.` guard, so names agree across stats collection, test
selection, and mutant activation.  Mutants still execute and tests must
still fail to kill them; only the naming is corrected.

Usage (see the mutants target in the Makefile):
    uv run python tools/mutmut_run.py run
"""

import inspect

import mutmut
import mutmut.__main__ as mutmut_main


def _get_mutant_name(relative_source_path, mutant_method_name):
    module_name = str(relative_source_path)
    module_name = module_name[: -len(relative_source_path.suffix)]
    module_name = module_name.replace("\\", ".").replace("/", ".")
    mutant_name = f"{module_name}.{mutant_method_name}"
    return mutant_name.replace(".__init__.", ".")


def _record_trampoline_hit(name):
    max_depth = getattr(mutmut.config, "max_stack_depth", -1)
    if max_depth != -1:
        f = inspect.currentframe()
        c = max_depth
        while c and f:
            filename = f.f_code.co_filename
            if (
                "pytest" in filename
                or "hammett" in filename
                or "unittest" in filename
            ):
                break
            f = f.f_back
            c = c - 1
        if not c:
            return
    mutmut._stats.add(name)


# Deliberate runtime monkeypatch of mutmut internals; ty cannot model
# rebinding def'd module attributes, so the assignments are suppressed.
mutmut_main.get_mutant_name = _get_mutant_name  # ty: ignore[invalid-assignment]
mutmut_main.record_trampoline_hit = _record_trampoline_hit  # ty: ignore[invalid-assignment]

if __name__ == "__main__":
    mutmut_main.cli()
