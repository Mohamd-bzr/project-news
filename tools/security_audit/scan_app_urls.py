import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
lines = Path("app.py").read_text(encoding="utf-8").splitlines()
pat = re.compile(r'["\'](?:link|url|resolved_url|image)["\']\s*:')
for idx, line in enumerate(lines, 1):
    if pat.search(line):
        print(f"{idx}: {line.strip()}")
