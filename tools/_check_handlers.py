#!/usr/bin/env python3
"""Temporary verifier: every inline handler in the UI must resolve.

Extracts function names from onclick/oninput/onchange handlers in the markup and
checks them against the function definitions in the three script blocks. Also
reports ids referenced by getElementById() calls that the markup never defines.
"""
import re
import sys

src = open("dashboard_html.py", encoding="utf-8").read()
html = src[src.index("<!DOCTYPE html>"):src.index("</html>")] if "<!DOCTYPE html>" in src else src
body = html[html.index("<body>"):]
scripts = re.findall(r"<script[^>]*>(.*?)</script>", body, re.S)
markup = re.sub(r"<script[^>]*>.*?</script>", "", body, flags=re.S)
js = "\n".join(scripts)

# every function/method the JS defines
defined = set(re.findall(r"function\s+([A-Za-z_$][\w$]*)", js))
defined |= set(re.findall(r"(?:window\.|var |let |const )([A-Za-z_$][\w$]*)\s*=\s*(?:function|\(|async)", js))
defined |= set(re.findall(r"([A-Za-z_$][\w$]*)\s*:\s*(?:function|\([^)]*\)\s*=>)", js))
# members of UI/CAL/CHART objects assigned anywhere
obj_members = set(re.findall(r"\b(?:UI|CAL|CHART|TVW|DATA|LIVE)\.([A-Za-z_$][\w$]*)\s*=", js))

missing = set()
calls = re.findall(r'on(?:click|input|change)="([^"]+)"', markup)
for expr in calls:
    for name in re.findall(r"([A-Za-z_$][\w$]*)\s*\(", expr):
        if name in {"if", "return", "event", "this", "document", "window", "String", "Number", "parseInt",
                    "setTimeout", "JSON", "Object", "Array", "Math", "console", "renderFeed"}:
            continue
        if name not in defined and name not in obj_members:
            missing.add(name)

# ids the JS looks up
used_ids = set(re.findall(r"getElementById\(\s*['\"]([^'\"]+)['\"]", js))
markup_ids = set(re.findall(r'id="([^"]+)"', body))
# ids built by JS itself (templates) also count
js_ids = set(re.findall(r"id=[\\\"']([A-Za-z][\w-]*)", js))
ghost_ids = sorted(used_ids - markup_ids - js_ids)

print("markup handlers:", len(calls))
print("unresolved handler functions:", sorted(missing) or "none")
print("getElementById targets with no id anywhere:", ghost_ids or "none")
sys.exit(1 if (missing or ghost_ids) else 0)
