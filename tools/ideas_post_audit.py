"""tools/ideas_post_audit.py — Audit tool for Content Ideas post composition v2.

Reads up to 200 stored English-source ideas from a read-only connection to the DB.
Never writes to the DB. Never sends any message.
Evaluates structure conformity, number provenance, Persian quality, Latin runs,
and checks the release Quality Gate.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure parent directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ideas_post
import translate


def audit_ideas(db_path: str, max_items: int = 200) -> Dict[str, Any]:
    uri = f"file:{Path(db_path).resolve().as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    cur = con.cursor()

    # Query recent articles with English title and Persian translation
    query = """
    SELECT a.id, a.title, a.title_fa, a.summary, a.summary_fa, a.link, b.payload
    FROM articles a
    LEFT JOIN bodies b ON a.id = b.id
    WHERE a.title IS NOT NULL AND a.title != ''
      AND a.title_fa IS NOT NULL AND a.title_fa != ''
      AND a.summary_fa IS NOT NULL AND a.summary_fa != ''
    ORDER BY a.published_ts DESC
    LIMIT ?
    """
    rows = cur.execute(query, (max_items * 2,)).fetchall()
    con.close()

    total_candidates = len(rows)
    rendered_items: List[Dict[str, Any]] = []
    skipped_reasons: Dict[str, int] = {}

    for row in rows:
        aid, title_en, title_fa, summary_en, summary_fa, link, payload_json = row
        # English source check: title_en should have latin letters
        if not any(c.isascii() and c.isalpha() for c in (title_en or "")):
            continue

        item = {
            "id": aid,
            "title": title_en,
            "title_fa": title_fa,
            "summary": summary_en,
            "summary_fa": summary_fa,
            "link": link,
        }
        if payload_json:
            try:
                body_dict = json.loads(payload_json)
                if isinstance(body_dict, dict) and body_dict.get("paragraphs"):
                    item["paragraphs"] = body_dict["paragraphs"]
            except Exception:
                pass

        res = ideas_post.compose_post(item)
        if res is None:
            # Classify skip reason
            if not translate.is_persian(title_fa):
                reason = "non-persian title"
            elif len(summary_fa.split()) < 5:
                reason = "short summary / few sentences"
            else:
                reason = "insufficient usable sentences (<2 blocks)"
            skipped_reasons[reason] = skipped_reasons.get(reason, 0) + 1
            continue

        rendered_items.append({
            "item": item,
            "output": res,
        })
        if len(rendered_items) >= max_items:
            break

    # Analysis
    structure_passes = 0
    provenance_passes = 0
    url_count = 0
    latin_run_blocks = 0
    func_word_endings = 0
    lengths: List[int] = []

    for entry in rendered_items:
        out = entry["output"]
        title = out["title"]
        blocks = out["blocks"]
        text = out["text"]
        lengths.append(len(text))

        # Check URLs
        if ideas_post._has_url(text):
            url_count += 1

        # Check Structure
        has_structure_err = False
        if not (2 <= len(blocks) <= 5):
            has_structure_err = True
        if len(title) > 110:
            has_structure_err = True
        if len(text) > 1500:
            has_structure_err = True

        prev_em = None
        for b in blocks:
            em = b[:2].strip()
            if em not in ideas_post.PALETTE_EMOJIS:
                has_structure_err = True
            if em == prev_em:
                has_structure_err = True
            prev_em = em

            # Check Latin run
            if translate.longest_latin_run(b) >= 4:
                latin_run_blocks += 1

            # Check function word ending
            clean = b.rstrip(".,:؛!؟ ")
            last_w = clean.split()[-1] if clean.split() else ""
            if last_w in ideas_post.FUNCTION_WORDS:
                func_word_endings += 1
                has_structure_err = True

        if not has_structure_err:
            structure_passes += 1

        # Check provenance
        all_src = f"{entry['item']['title_fa']} {entry['item']['summary_fa']}"
        body_p = entry['item'].get("paragraphs")
        if body_p:
            if isinstance(body_p, list):
                all_src += " " + " ".join(str(p) for p in body_p)
            elif isinstance(body_p, str):
                all_src += " " + body_p
        src_nums = ideas_post.extract_numbers(all_src)
        prov_ok = True
        for b in blocks:
            b_nums = ideas_post.extract_numbers(b)
            if not b_nums.issubset(src_nums):
                prov_ok = False
                break
        if prov_ok:
            provenance_passes += 1

    n_rendered = len(rendered_items)
    structure_pass_rate = (structure_passes / n_rendered * 100) if n_rendered else 0.0
    provenance_rate = (provenance_passes / n_rendered * 100) if n_rendered else 0.0

    lengths.sort()
    min_len = lengths[0] if lengths else 0
    max_len = lengths[-1] if lengths else 0
    med_len = lengths[len(lengths) // 2] if lengths else 0
    p90_len = lengths[int(len(lengths) * 0.9)] if lengths else 0

    passed_gate = (
        n_rendered >= 100
        and structure_pass_rate >= 95.0
        and provenance_rate == 100.0
        and url_count == 0
    )

    return {
        "candidates": total_candidates,
        "rendered": n_rendered,
        "skipped": skipped_reasons,
        "structure_passes": structure_passes,
        "structure_pass_rate": structure_pass_rate,
        "provenance_passes": provenance_passes,
        "provenance_rate": provenance_rate,
        "url_count": url_count,
        "latin_run_blocks": latin_run_blocks,
        "func_word_endings": func_word_endings,
        "length_stats": {
            "min": min_len,
            "median": med_len,
            "p90": p90_len,
            "max": max_len,
        },
        "quality_gate": passed_gate,
        "samples": rendered_items[:12],
    }


def main():
    parser = argparse.ArgumentParser(description="Audit ideas post composition v2 on stored ideas.")
    parser.add_argument("--db", default=r"E:\freebuff\.mohmd_news.db", help="Path to SQLite DB")
    parser.add_argument("--count", type=int, default=200, help="Max items to render")
    args = parser.parse_args()

    res = audit_ideas(args.db, max_items=args.count)

    print("=" * 60)
    print("IDEAS POST V2 AUDIT REPORT")
    print("=" * 60)
    print(f"Items rendered:            {res['rendered']}")
    print(f"Items skipped by reason:   {res['skipped']}")
    print(f"Structure pass rate:       {res['structure_pass_rate']:.1f}% ({res['structure_passes']}/{res['rendered']})")
    print(f"Number provenance rate:    {res['provenance_rate']:.1f}% ({res['provenance_passes']}/{res['rendered']})")
    print(f"Blocks with Latin run >=4: {res['latin_run_blocks']}")
    print(f"Function word endings:     {res['func_word_endings']}")
    print(f"URLs in output:            {res['url_count']}")
    lstats = res["length_stats"]
    print(f"Length distribution:       min={lstats['min']}, med={lstats['median']}, p90={lstats['p90']}, max={lstats['max']}")
    print("-" * 60)
    gate_str = "PASSED" if res["quality_gate"] else "FAILED"
    print(f"QUALITY GATE (>=95% structure, 100% provenance, 0 URLs, >=100 items): {gate_str}")
    print("=" * 60)

    print("\n12 REAL SAMPLES (Title + Blocks):")
    print("=" * 60)
    for idx, s in enumerate(res["samples"], 1):
        print(f"--- SAMPLE {idx} (ID: {s['item']['id']}) ---")
        print(s["output"]["text"])
        print()

    if not res["quality_gate"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
