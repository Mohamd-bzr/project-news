#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from fa_postedit import lexicon, post_edit
from fa_postedit import _replace_latin_in_span, _is_protected_latin_span, _LATIN_SPAN_RE

def get_entity_rows():
    pack = json.load(open(REPO / "data" / "fa" / "review_pack_40.json", encoding="utf-8"))
    lex = lexicon()
    entity_rows = []
    for r in pack:
        raw = r["raw"]
        # Check if _replace_latin actually modified anything in raw
        def _sub_span(m):
            span = m.group(0)
            if _is_protected_latin_span(span, lex):
                return span
            return _replace_latin_in_span(span, lex)
        after_latin = _LATIN_SPAN_RE.sub(_sub_span, raw)
        if after_latin != raw:
            entity_rows.append(r)
    print(f"Entity rows in review_pack_40: {len(entity_rows)}")
    for r in entity_rows:
        print(f"{r['en']} | {r['raw']} | {r['post_highlighted']}")

if __name__ == "__main__":
    get_entity_rows()
