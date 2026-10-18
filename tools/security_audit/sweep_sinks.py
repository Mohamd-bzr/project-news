#!/usr/bin/env python3
"""
tools/fa_build/audit/sweep_sinks.py
===================================
Comprehensive sweep of URL sinks (href, src, .href =, window.open, location =, formaction, action=)
across web/, web/fragments/, and dashboard_html.py.
"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parents[3]

PATTERNS = [
    ("href_attr", re.compile(r'href\s*=\s*["\']?([^"\'>\s]+)', re.I)),
    ("href_template", re.compile(r'href\s*=\s*["\']?\$\{([^}]+)\}', re.I)),
    ("href_concat", re.compile(r'href\s*=\s*["\']?\s*\+\s*([^+"\'>]+)', re.I)),
    ("src_attr", re.compile(r'src\s*=\s*["\']?([^"\'>\s]+)', re.I)),
    ("src_template", re.compile(r'src\s*=\s*["\']?\$\{([^}]+)\}', re.I)),
    ("src_concat", re.compile(r'src\s*=\s*["\']?\s*\+\s*([^+"\'>]+)', re.I)),
    ("dot_href", re.compile(r'\.href\s*=\s*([^;]+)', re.I)),
    ("window_open", re.compile(r'window\.open\s*\(([^)]+)\)', re.I)),
    ("location", re.compile(r'location(?:\.href)?\s*=\s*([^;]+)', re.I)),
    ("action", re.compile(r'action\s*=\s*["\']?([^"\'>\s]+)', re.I)),
]

def scan_file(filepath):
    lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
    hits = []
    for idx, line in enumerate(lines, 1):
        # Ignore static svg icons, stylesheets, font preloads, manifest
        if any(ignore in line for ignore in ['<use href="#i-', 'rel="stylesheet"', 'rel="manifest"', 'rel="icon"', 'rel="apple-touch-icon"', '.woff2', '<script src="']):
            continue
        for name, pat in PATTERNS:
            m = pat.search(line)
            if m:
                hits.append((idx, line.strip(), name, m.group(0)))
                break
    return hits

def main():
    targets = sorted(list((REPO / "web").glob("*.js")) + list((REPO / "web" / "fragments").glob("*")) + [REPO / "dashboard_html.py"])
    all_hits = []
    for t in targets:
        if not t.is_file():
            continue
        h = scan_file(t)
        if h:
            all_hits.append((t.relative_to(REPO).as_posix(), h))

    for path, hits in all_hits:
        print(f"\n=== {path} ({len(hits)} hits) ===")
        for line_num, line_text, kind, matched in hits:
            print(f"  Line {line_num:4d} [{kind}]: {line_text[:120]}")

if __name__ == "__main__":
    main()
