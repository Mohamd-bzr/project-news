#!/usr/bin/env python3
"""
gates.py — the pytest failure-SET gate (stdlib only, offline).
==============================================================
Replaces "the count must stay 12" bookkeeping, which hides swaps: a new
failure plus a fixed one keeps the count green. This gate compares the SET
of failing test ids against tests/BASELINE_FAILURES.txt and fails on any
id that is not listed there.

Usage:
    .venv/Scripts/python.exe tools/gates.py [extra pytest args...]

Exit codes:
    0  every failing id is in the baseline (report fixed ones as info)
    1  NEW failing id(s) outside the baseline — investigate before adding
    2  gate misfired (baseline missing, pytest crashed / collected nothing)
"""
import os
import re
import subprocess
import sys
from pathlib import Path

# Windows console encoding safeguard
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = REPO / "tests" / "BASELINE_FAILURES.txt"

# short summary line: `FAILED <nodeid> - <reason...>` (or `ERROR <nodeid>`)
_FAILED_RE = re.compile(r"^(?:FAILED|ERROR) (.+?)(?: - .*)?$")
_SUMMARY_RE = re.compile(r"^((?:\d+ failed|\d+ passed)[^\n]*)", re.M)
_U_ESCAPED = re.compile(r"\\u([0-9a-fA-F]{4})|\\U([0-9a-fA-F]{8})")


def _normalize_nodeid(nodeid):
    """Decode the \\uXXXX escaping pytest applies to non-ASCII nodeids in the
    short summary, so ids compare equal to the readable baseline file."""
    return _U_ESCAPED.sub(
        lambda m: chr(int(m.group(1) or m.group(2), 16)), nodeid)


def parse_baseline(text):
    """Baseline ids: the first TAB-field of every non-comment line."""
    ids = set()
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            ids.add(_normalize_nodeid(line.split("\t", 1)[0].strip()))
    return ids


def parse_failures(pytest_output):
    """Nodeids from a `-q --tb=no -rf` short summary.

    The nodeid ends at the first ' - ' on the line. Our parameter ids never
    contain ' - ' (they use '-<fixture>-' without spaces), and a mis-parse
    would surface as a bogus NEW id — loud, never silent.
    """
    ids = []
    for line in pytest_output.splitlines():
        m = _FAILED_RE.match(line)
        if m:
            ids.append(_normalize_nodeid(m.group(1).strip()))
    return ids


def evaluate(pytest_output, baseline_text):
    """Pure decision: (new_ids, fixed_ids, summary_line, n_actual_failed)."""
    actual = set(parse_failures(pytest_output))
    baseline = parse_baseline(baseline_text)
    m = _SUMMARY_RE.search(pytest_output)
    summary = m.group(1) if m else "(no pytest summary line found)"
    return sorted(actual - baseline), sorted(baseline - actual), summary, len(actual)


def run_pytest(extra_args):
    cmd = [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no", "-rf"] \
        + list(extra_args)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, env=env)
    out = proc.stdout.decode("utf-8", "replace") + "\n" \
        + proc.stderr.decode("utf-8", "replace")
    return proc.returncode, out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    baseline_path = DEFAULT_BASELINE
    if "--baseline" in argv:
        i = argv.index("--baseline")
        baseline_path = Path(argv[i + 1])
        del argv[i:i + 2]
    if not baseline_path.exists():
        print(f"gates: baseline file missing: {baseline_path}", file=sys.stderr)
        return 2
    rc, out = run_pytest(argv)
    if rc not in (0, 1):     # 2=interrupted 3=internal error 4=usage 5=no tests
        print(f"gates: pytest misfired (rc={rc}); output tail:")
        print("\n".join(out.splitlines()[-30:]))
        return 2
    new, fixed, summary, n_actual = evaluate(
        out, baseline_path.read_text(encoding="utf-8"))
    n_base = len(parse_baseline(baseline_path.read_text(encoding="utf-8")))
    print(f"gates: pytest -> {summary}")
    print(f"gates: failing ids: actual={n_actual} baseline={n_base} "
          f"new={len(new)} fixed={len(fixed)}")
    for tid in new:
        print(f"gates: NEW FAILURE  {tid}")
    for tid in fixed:
        print(f"gates: now passing {tid}  (trim it from {baseline_path.name})")
    if new:
        print("gates: FAIL — a test id outside the baseline is failing.")
        print("gates: fix it, or add it to the baseline only after review.")
        return 1
    print("gates: ok — no new failing test ids.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
