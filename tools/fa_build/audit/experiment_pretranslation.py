#!/usr/bin/env python3
"""
tools/fa_build/audit/experiment_pretranslation.py
=================================================
Feasibility experiment for source-side protection (glossary applied before translation).
Tests 3 protection styles on 30 real English headlines containing 10 finance/crypto terms:
  (a) Alphanumeric placeholder: TERM01, TERM02...
  (b) Bracketed placeholder: [01], [02]...
  (c) Direct Persian injection: preferred Persian term inserted in English source

Evaluates against the real Google endpoint (clients5.google.com/translate_a/t):
  - 1 req/sec rate limit
  - Measures placeholder survival rate per style
  - Evaluates surrounding grammar integrity
  - Prints 20 comparison examples (English | engine | protected)
"""
import re
import sys
import time
import json
import sqlite3
import urllib.request
import urllib.parse
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parents[3]
DB_PATH = Path("E:/freebuff/.mohmd_news.db")

ENDPOINT = "https://clients5.google.com/translate_a/t"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 10 targeted terms with regex and preferred Persian translation
TARGET_TERMS = [
    ("hawkish", re.compile(r"\bhawkish(?:ly)?\b", re.I), "هاوکیش"),
    ("dovish", re.compile(r"\bdovish(?:ly)?\b", re.I), "داویش"),
    ("hedge fund", re.compile(r"\bhedge\s+funds?\b", re.I), "صندوق‌های پوشش ریسک"),
    ("breakout", re.compile(r"\bbreakouts?\b|\bbreaks?\s+out\b|\bbroke\s+out\b", re.I), "شکست صعودی"),
    ("pullback", re.compile(r"\bpullbacks?\b", re.I), "پولبک"),
    ("rate cut", re.compile(r"\brate\s+cuts?\b", re.I), "کاهش نرخ بهره"),
    ("rate hike", re.compile(r"\brate\s+hikes?\b", re.I), "افزایش نرخ بهره"),
    ("safe haven", re.compile(r"\bsafe\s+havens?\b", re.I), "دارایی امن"),
    ("stablecoin", re.compile(r"\bstablecoins?\b", re.I), "استیبل‌کوین"),
    ("order block", re.compile(r"\border\s+blocks?\b", re.I), "اوردر بلاک"),
]

def fetch_translation_batch(texts):
    """Batched GET request to Google translation endpoint with 1 req/sec rate limit."""
    time.sleep(1.2)
    clean = [(t or "").strip()[:500] for t in texts]
    params = [("client", "dict-chrome-ex"), ("sl", "en"), ("tl", "fa")]
    params += [("q", t) for t in clean]
    url = f"{ENDPOINT}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            out = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, str):
                        out.append(item)
                    elif isinstance(item, list) and item and isinstance(item[0], list):
                        out.append("".join(s[0] for s in item if isinstance(s, list) and s and s[0]))
                    elif isinstance(item, list) and item and isinstance(item[0], str):
                        out.append(item[0])
                    else:
                        out.append("")
            return out
    except Exception as e:
        print(f"Translation batch error: {e}", file=sys.stderr)
        return [""] * len(texts)

def select_30_headlines():
    con = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    cur = con.cursor()
    rows = cur.execute("SELECT title, title_fa FROM articles ORDER BY id DESC LIMIT 15000").fetchall()
    con.close()

    selected = []
    seen = set()

    # Find headlines containing target terms where translation has defect or leaves term untranslated
    for term_name, pat, fa_term in TARGET_TERMS:
        term_matches = 0
        for title, title_fa in rows:
            if not title or not title_fa or title in seen:
                continue
            if pat.search(title):
                selected.append({
                    "title": title,
                    "engine_fa": title_fa,
                    "term": term_name,
                    "fa_target": fa_term,
                    "pat": pat,
                })
                seen.add(title)
                term_matches += 1
                if term_matches >= 3:  # 3 headlines per term = 30 total
                    break

    # If some terms had fewer than 3, fill from any target term
    if len(selected) < 30:
        for title, title_fa in rows:
            if title in seen:
                continue
            for term_name, pat, fa_term in TARGET_TERMS:
                if pat.search(title):
                    selected.append({
                        "title": title,
                        "engine_fa": title_fa,
                        "term": term_name,
                        "fa_target": fa_term,
                        "pat": pat,
                    })
                    seen.add(title)
                    break
            if len(selected) >= 30:
                break

    return selected[:30]

def run_experiment():
    headlines = select_30_headlines()
    print(f"Selected {len(headlines)} real headlines covering all 10 target terms.\n")

    # Prepare 3 variations for each headline:
    # (a) Alphanumeric: TERM01, TERM02...
    # (b) Bracketed: [01], [02]...
    # (c) Direct Persian: inserted directly
    for i, h in enumerate(headlines, 1):
        h["ph_alpha"] = f"PHX{i:02d}"
        h["ph_bracket"] = f"[{i:02d}]"

        # Apply substitutions
        h["text_alpha"] = h["pat"].sub(h["ph_alpha"], h["title"], count=1)
        h["text_bracket"] = h["pat"].sub(h["ph_bracket"], h["title"], count=1)
        h["text_direct"] = h["pat"].sub(h["fa_target"], h["title"], count=1)

    # Translate batches (batches of 10)
    batch_size = 10
    res_alpha = []
    res_bracket = []
    res_direct = []

    print("Translating Style (a) Alphanumeric tokens...")
    for b in range(0, len(headlines), batch_size):
        chunk = [h["text_alpha"] for h in headlines[b:b+batch_size]]
        res_alpha.extend(fetch_translation_batch(chunk))

    print("Translating Style (b) Bracketed tokens...")
    for b in range(0, len(headlines), batch_size):
        chunk = [h["text_bracket"] for h in headlines[b:b+batch_size]]
        res_bracket.extend(fetch_translation_batch(chunk))

    print("Translating Style (c) Direct Persian injection...")
    for b in range(0, len(headlines), batch_size):
        chunk = [h["text_direct"] for h in headlines[b:b+batch_size]]
        res_direct.extend(fetch_translation_batch(chunk))

    # Evaluate survival and post-processing
    surv_alpha = 0
    surv_bracket = 0
    surv_direct = 0

    grammar_break_alpha = 0
    grammar_break_bracket = 0
    grammar_break_direct = 0

    final_results = []

    for i, h in enumerate(headlines):
        raw_a = res_alpha[i]
        raw_b = res_bracket[i]
        raw_c = res_direct[i]

        # Check survival
        # Style a: PHX01
        has_a = h["ph_alpha"].lower() in raw_a.lower()
        if has_a:
            surv_alpha += 1
            # Replace placeholder with target Persian
            post_a = re.sub(re.escape(h["ph_alpha"]), h["fa_target"], raw_a, flags=re.I)
        else:
            post_a = raw_a

        # Style b: [01] or [۱]
        has_b = h["ph_bracket"] in raw_b or f"[{i:02d}]" in raw_b or f"[{i}]" in raw_b
        # Also check Persian digits inside bracket e.g. [۰۱]
        m_b = re.search(r"\[\s*(?:" + str(i) + rf"|{i:02d}|[۰-۹]+)\s*\]", raw_b)
        if m_b:
            surv_bracket += 1
            post_b = raw_b[:m_b.start()] + h["fa_target"] + raw_b[m_b.end():]
        else:
            post_b = raw_b

        # Style c: direct Persian
        has_c = h["fa_target"] in raw_c
        if has_c:
            surv_direct += 1
        post_c = raw_c

        # Grammar heuristic: check if word order inverted or prepositions damaged
        # In Persian, adjectives follow nouns. If English has "hawkish pause", direct injection might yield
        # "هاوکیش مکث" (English order) instead of "مکث هاوکیش" (Persian order).
        if re.search(rf"{h['fa_target']}\s+(?:مکث|لحن|رویکرد|سیاست)", post_c):
            grammar_break_direct += 1
        if re.search(rf"{h['fa_target']}\s+(?:مکث|لحن|رویکرد|سیاست)", post_a):
            grammar_break_alpha += 1

        final_results.append({
            "title": h["title"],
            "term": h["term"],
            "fa_target": h["fa_target"],
            "engine_fa": h["engine_fa"],
            "post_alpha": post_a,
            "post_bracket": post_b,
            "post_direct": post_c,
            "surv_a": has_a,
            "surv_b": bool(m_b),
            "surv_c": has_c,
        })

    # Output report
    print("\n" + "=" * 70)
    print("SOURCE-SIDE PROTECTION FEASIBILITY RESULTS (N=30 HEADLINES)")
    print("=" * 70)
    print(f"Style (a) Alphanumeric (PHX01): survival = {surv_alpha}/30 ({surv_alpha/30*100:.1f}%), grammar issues = {grammar_break_alpha}/30")
    print(f"Style (b) Bracketed ([01])   : survival = {surv_bracket}/30 ({surv_bracket/30*100:.1f}%), grammar issues = {grammar_break_bracket}/30")
    print(f"Style (c) Direct Persian      : survival = {surv_direct}/30 ({surv_direct/30*100:.1f}%), grammar issues = {grammar_break_direct}/30")

    print("\n" + "=" * 70)
    print("20 BEFORE/AFTER EXAMPLES (ENGLISH | ENGINE | PROTECTED)")
    print("=" * 70)
    for idx, r in enumerate(final_results[:20], 1):
        # Pick best protected output
        best_prot = r["post_bracket"] if r["surv_b"] else (r["post_alpha"] if r["surv_a"] else r["post_direct"])
        print(f"[{idx:02d}] Term: {r['term']} -> {r['fa_target']}")
        print(f"     EN    : {r['title']}")
        print(f"     ENGINE: {r['engine_fa']}")
        print(f"     PROT  : {best_prot}\n")

if __name__ == "__main__":
    run_experiment()
