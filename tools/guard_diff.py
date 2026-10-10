#!/usr/bin/env python3
"""Diff-size guard: a change that deletes too much, or strays outside its plan, fails.

Agents on this repo have a specific, repeating failure mode: they "helpfully"
reformat or regenerate a file they were only asked to touch in one place. The
result reads as thousands of deleted lines and the real change is unreviewable.

This gate reads `git diff --numstat` against a base ref (default `main`, i.e.
the worktree vs main, staged + unstaged) and fails when either:

  * any single file deletes more than --max-del lines (default 80), or
  * a changed file is not under one of the --allow paths (when given).

Usage:
    python tools/guard_diff.py                       # worktree vs main
    python tools/guard_diff.py --base HEAD~1
    python tools/guard_diff.py --staged              # index vs base
    python tools/guard_diff.py --allow app.py,tests/ --max-del 20

Exit codes: 0 clean, 1 violation, 2 could not run (bad ref, not a repo).
"""
from __future__ import annotations

import argparse
import subprocess
import sys

DEFAULT_MAX_DEL = 80


def _git(args: list[str]) -> tuple[int, bytes, str]:
    """Run git, returning (returncode, raw stdout, decoded stderr)."""
    proc = subprocess.run(["git", *args], capture_output=True)
    return proc.returncode, proc.stdout, proc.stderr.decode("utf-8", "replace")


def parse_numstat_z(data: bytes) -> list[tuple[str, int, int, bool]]:
    """(path, added, deleted, is_binary) from a NUL-terminated --numstat dump.

    Renames arrive as `0\t0\t\0<old>\0<new>\0`; the row is reported under the
    NEW path so an allow-list entry for the destination matches a plain move.
    """
    rows = []
    chunks = data.decode("utf-8", "replace").split("\0")
    i = 0
    while i < len(chunks):
        head = chunks[i]
        i += 1
        if not head:
            continue
        parts = head.split("\t")
        if len(parts) < 3:
            continue
        added_s, deleted_s, path = parts[0], parts[1], "\t".join(parts[2:])
        binary = added_s == "-" or deleted_s == "-"
        if not path and i < len(chunks):
            # rename: skip the old path, keep the destination
            i += 1
            path = chunks[i] if i < len(chunks) else "(renamed)"
            i += 1
        rows.append((path,
                    0 if binary else int(added_s),
                    0 if binary else int(deleted_s),
                    binary))
    return rows


def covered(path: str, allow: list[str]) -> bool:
    """A path is allowed when it equals, or sits under, any allow entry."""
    if not allow:
        return True
    for entry in allow:
        entry = entry.replace("\\", "/").strip("/")
        p = path.replace("\\", "/")
        if p == entry or p.startswith(entry + "/"):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="main",
                    help="ref the diff is taken against (default: main)")
    ap.add_argument("--max-del", type=int, default=DEFAULT_MAX_DEL,
                    help=f"max deleted lines per file (default: {DEFAULT_MAX_DEL})")
    ap.add_argument("--allow", default="",
                    help="comma-separated path prefixes that may be touched")
    ap.add_argument("--staged", action="store_true",
                    help="inspect the index instead of the working tree")
    ap.add_argument("--quiet", action="store_true",
                    help="print only violations")
    args = ap.parse_args(argv)

    if _git(["rev-parse", "--is-inside-work-tree"])[0] != 0:
        print("guard_diff: not inside a git working tree", file=sys.stderr)
        return 2

    diff_args = ["diff", "--numstat", "-z", "--no-color"]
    if args.staged:
        diff_args.append("--cached")
    diff_args.append(args.base)
    code, out, err = _git(diff_args)
    if code != 0:
        print(f"guard_diff: `git {' '.join(diff_args)}` failed:\n{err.strip()}",
              file=sys.stderr)
        return 2

    rows = parse_numstat_z(out)
    allow = [a for a in (p.strip() for p in args.allow.split(",")) if a]

    if not rows:
        if not args.quiet:
            print(f"guard_diff: no changes against {args.base} - nothing to guard")
        return 0

    violations: list[str] = []
    if not args.quiet:
        print(f"guard_diff: {len(rows)} changed file(s) against {args.base} "
              f"(max {args.max_del} deleted lines per file)")
    for path, added, deleted, binary in sorted(rows):
        flags = []
        if deleted > args.max_del:
            flags.append(f"DELETES {deleted} > {args.max_del}")
        if not covered(path, allow):
            flags.append("OUTSIDE --allow")
        if flags:
            violations.append(f"  {path}: {'; '.join(flags)}")
        if not args.quiet or flags:
            kind = "binary" if binary else f"+{added}/-{deleted}"
            print(f"  {kind:>12}  {path}")

    if violations:
        print("\nguard_diff FAILED - unplanned or oversized deletion:")
        for v in violations:
            print(v)
        print("\nSmallest-change rule: revert the file, or pass --allow/--max-del "
              "deliberately if the big diff IS the task.")
        return 1

    if not args.quiet:
        print("guard_diff: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
