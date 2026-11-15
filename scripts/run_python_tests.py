"""Minimal dependency-free runner for the integration tests.

The test functions intentionally use plain assertions; this runner supplies
only the temporary-path fixture needed by two adapter tests.
"""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import tempfile
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for runtime in ("earthsync_runtime", "aquasense_runtime", "terralens_runtime"):
    sys.path.insert(0, str(ROOT / "modules" / runtime))


def main() -> int:
    passed = 0
    failures: list[tuple[str, BaseException]] = []
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot import {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name, function in inspect.getmembers(module, inspect.isfunction):
            if not name.startswith("test_"):
                continue
            try:
                parameters = inspect.signature(function).parameters
                if parameters:
                    if tuple(parameters) != ("tmp_path",):
                        raise RuntimeError(f"Unsupported test fixture(s): {tuple(parameters)}")
                    with tempfile.TemporaryDirectory(prefix="orbitill-test-") as directory:
                        function(Path(directory))
                else:
                    function()
                print(f"PASS {path.name}::{name}")
                passed += 1
            except BaseException as exc:
                print(f"FAIL {path.name}::{name}: {exc}")
                failures.append((f"{path.name}::{name}", exc))
    print(f"\n{passed} passed, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
