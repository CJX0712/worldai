# Author: 晨星
"""One-command verification: unit tests -> E2E -> P0 emoji gate.
Fully offline: no API key, no network, no model file required.
Usage: python scripts/verify.py"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STEPS = [
    ("unit tests (pytest)", [sys.executable, "-B", "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"]),
    ("end-to-end (scripts/e2e.py)", [sys.executable, "-B", "scripts/e2e.py"]),
    ("P0 emoji gate (tools/scan_emoji.py)", [sys.executable, "-B", "tools/scan_emoji.py", "."]),
]


def main() -> int:
    results: list[tuple[str, bool]] = []
    for name, cmd in STEPS:
        print(f"\n=== {name} ===")
        proc = subprocess.run(cmd, cwd=ROOT)
        results.append((name, proc.returncode == 0))
        if proc.returncode != 0:
            break  # fail fast: later steps assume earlier ones pass
    print("\n=== verify summary ===")
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    all_ok = all(ok for _, ok in results) and len(results) == len(STEPS)
    print(f"verify: {'ALL GREEN' if all_ok else 'FAILED'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
