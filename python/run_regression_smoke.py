#!/usr/bin/env python3
"""Run dependency-free smoke tests for the DIFTCL helper.

This runner is intentionally stdlib-only so it works in Codex containers,
Claude code-execution environments, and simple local Python installs.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "python" / "diftcl_citation_audit.py"
DEFAULT_CASES = ROOT / "tests" / "fixtures" / "regression_cases.json"


def get_path(data: Any, dotted: str) -> Any:
    current = data
    for part in dotted.split("."):
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current[part]
        else:
            raise KeyError(f"Cannot descend into {part!r} for {dotted!r}")
    return current


def run_case(case: dict[str, Any], verbose: bool) -> tuple[bool, str]:
    script = ROOT / "python" / case["script"] if case.get("script") else HELPER
    cmd = [sys.executable, str(script), *case["args"]]
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=case.get("timeout", 30),
    )
    if result.returncode != 0:
        return False, f"{case['id']}: exit {result.returncode}\nSTDERR:\n{result.stderr}"
    output = result.stdout
    for expected in case.get("contains", []):
        if expected not in output:
            return False, f"{case['id']}: missing text {expected!r}\nOUTPUT:\n{output}"
    if case.get("json_checks"):
        try:
            data = json.loads(output)
        except json.JSONDecodeError as exc:
            return False, f"{case['id']}: expected JSON output: {exc}\nOUTPUT:\n{output}"
        for path, expected in case["json_checks"]:
            actual = get_path(data, path)
            if actual != expected:
                return False, f"{case['id']}: {path} expected {expected!r}, got {actual!r}"
    if verbose:
        print(f"PASS {case['id']}")
    return True, f"{case['id']}: ok"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", default=str(DEFAULT_CASES), help="Regression cases JSON file")
    parser.add_argument("--verbose", action="store_true", help="Print each passing case")
    args = parser.parse_args()

    cases_path = Path(args.cases)
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    for case in cases:
        ok, message = run_case(case, args.verbose)
        if not ok:
            failures.append(message)

    if failures:
        print(f"DIFTCL regression smoke failed: {len(failures)} failure(s)", file=sys.stderr)
        for failure in failures:
            print("", file=sys.stderr)
            print(failure, file=sys.stderr)
        return 1

    print(f"DIFTCL regression smoke passed: {len(cases)} case(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
