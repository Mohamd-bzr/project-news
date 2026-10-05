#!/usr/bin/env python3
"""Temp read-only helper: inventory classes/ids referenced anywhere in the UI.

Scans the APP_HTML string of dashboard_html.py for `class=` / `id=` attributes
whether they appear in literal markup or inside JS string literals, plus
classList mutations and querySelector selectors.
"""
import collections
import re

src = open("dashboard_html.py", encoding="utf-8").read()
i = src.index("<style>")
j = src.index("</html>")
html = src[i:j]

cls = collections.Counter()
ids = set()


def read_value(s, k):
    """s[k:] starts right after `class=`. Return (value, next_i) honoring quotes/backslash."""
    n = len(s)
    if k >= n:
        return None, n
    backslash = False
    if s[k] == "\\":              # class=\\"x\\" inside a python/JS literal
        backslash = True
        k += 1
    if k >= n or s[k] not in "\"'":
        return None, k
    q = s[k]
    k += 1
    out = []
    while k < n:
        c = s[k]
        if backslash and c == "\\":
            k += 1
            continue
        if c == q:
            break
        out.append(c)
        k += 1
    return "".join(out), k + 1


for attr in ("class=", "id="):
    k = 0
    while True:
        k = html.find(attr, k)
        if k < 0:
            break
        v, k = read_value(html, k + len(attr))
        if v:
            if attr == "id=":
                ids.add(v.strip())
            else:
                for c in v.split():
                    cls[c] += 1

# classList / className / querySelector references in JS
for m in re.finditer(r"(?:classList\.(?:add|remove|toggle)|className\s*=)\s*\(?\s*['\"]([^'\"]+)['\"]", html):
    for c in m.group(1).split():
        cls.setdefault(c, 0)
for m in re.finditer(r"querySelector(?:All)?\(\s*['\"]([^'\"]+)['\"]", html):
    for tok in re.findall(r"\.([A-Za-z_][\w-]*)", m.group(1)):
        cls.setdefault(tok, 0)

# ---- CSS selector inventory (top-level selector heads) ----
style = html[html.index("<style>") + 7:html.index("</style>")]
sel_classes = set()
for m in re.finditer(r"\.([A-Za-z_][\w-]*)", style):
    sel_classes.add(m.group(1))

print("== classes referenced in html/js:", len(cls))
print(" ".join(sorted(cls)))
print()
print("== ids:", len(ids))
print(" ".join(sorted(ids)))
print()
print("== classes styled in CSS but never referenced:", len(sel_classes - set(cls)))
print(" ".join(sorted(sel_classes - set(cls))))
print()
print("== referenced but not styled:", len(set(cls) - sel_classes))
print(" ".join(sorted(set(cls) - sel_classes)))
