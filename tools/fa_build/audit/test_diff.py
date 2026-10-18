#!/usr/bin/env python3
import difflib
import re
import sys
sys.stdout.reconfigure(encoding="utf-8")

def highlight_diff(raw, post):
    # Split into tokens (words + separators)
    # Using regex to capture both words and punctuation/spaces
    r_toks = re.findall(r"\S+|\s+", raw)
    p_toks = re.findall(r"\S+|\s+", post)
    
    matcher = difflib.SequenceMatcher(None, r_toks, p_toks)
    out = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            out.extend(p_toks[j1:j2])
        elif tag in ("replace", "insert"):
            chunk = "".join(p_toks[j1:j2])
            out.append(f"⟦{chunk}⟧")
    return "".join(out)

# Test examples
print(highlight_diff("قیمت Ethereum بالا رفت", "قیمت اتریوم بالا رفت"))
print(highlight_diff("اضافه می کند", "اضافه می‌کند"))
print(highlight_diff("بیت کوین خرید", "بیت‌کوین خرید"))
