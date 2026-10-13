#!/usr/bin/env python3
"""
tools/fa_build/ingest_term_reply.py
===================================
Ingests user feedback on core term candidate cards and generates or updates
data/fa/core_terms.tsv.

Supported reply line forms:
  "<n>: <Persian text>"  -> overrides preferred Persian term (status: user_override)
  "<n> skip" / "<n>: skip" -> skips the term from enforcement (status: skipped)
  "<n> ok" / "<n>: ok"     -> accepts recommended default explicitly (status: approved)

Cards not mentioned in reply retain their recommended default translation with
status "approved".

TSV columns:
  en\tfa_preferred\tbad_variants\tcontext_rule\tstatus\tsource
"""
import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_CANDIDATES = REPO / "data" / "fa" / "core_terms_candidates.json"
DEFAULT_OUTPUT_TSV = REPO / "data" / "fa" / "core_terms.tsv"

LINE_PATTERN = re.compile(
    r"^\s*(\d+)\s*(?:[:\-]\s*|\s+)(.+?)\s*$",
    re.IGNORECASE
)

def parse_line(line: str):
    """
    Parses a single reply line.
    Returns:
      (card_id, "custom", persian_text)
      (card_id, "skip", "")
      (card_id, "default", "")
      or None if line cannot be parsed.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    m = LINE_PATTERN.match(line)
    if not m:
        return None

    card_id = int(m.group(1))
    rest = m.group(2).strip()

    rest_lower = rest.lower()
    if rest_lower == "skip":
        return (card_id, "skip", "")
    if rest_lower in ("ok", "default"):
        return (card_id, "default", "")

    # Custom Persian text
    return (card_id, "custom", rest)

def parse_replies(text: str) -> dict:
    """
    Parses multi-line user response.
    Returns: dict of card_id -> (action, custom_text)
    """
    replies = {}
    for line_no, raw_line in enumerate(text.splitlines(), 1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parsed = parse_line(stripped)
        if parsed is None:
            print(f"[WARN] Line {line_no} malformed and ignored: {raw_line!r}", file=sys.stderr)
            continue
        card_id, action, custom_text = parsed
        replies[card_id] = (action, custom_text)
    return replies

def load_candidates(path=None):
    candidates_path = Path(path) if path else DEFAULT_CANDIDATES
    with open(candidates_path, "r", encoding="utf-8") as f:
        return json.load(f)

def apply_term_replies(replies: dict, candidates_path=None, output_tsv_path=None):
    """
    Applies user replies to candidates and writes to data/fa/core_terms.tsv.
    """
    candidates = load_candidates(candidates_path)
    output_path = Path(output_tsv_path) if output_tsv_path else DEFAULT_OUTPUT_TSV

    rows = []
    for c in candidates:
        cid = c["id"]
        en = c["en"]
        rec = c["recommended"]
        ctx = c.get("context_rule", "")
        variants = [v["term"] for v in c.get("variants", [])]

        if cid in replies:
            action, custom_text = replies[cid]
            if action == "skip":
                fa_preferred = ""
                status = "skipped"
            elif action == "custom":
                fa_preferred = custom_text
                status = "user_override"
            else:  # default / ok
                fa_preferred = rec
                status = "approved"
        else:
            # Not mentioned -> pending (never enforced)
            fa_preferred = ""
            status = "pending"

        # Bad variants are other known variants only if preferred is set
        if fa_preferred:
            bad = [v for v in variants if v != fa_preferred and v]
            bad_str = "|".join(bad)
        else:
            bad_str = ""

        rows.append({
            "en": en,
            "fa_preferred": fa_preferred,
            "bad_variants": bad_str,
            "context_rule": ctx,
            "status": status,
            "source": "audit:mohmd_news"
        })

    # Write output TSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["en", "fa_preferred", "bad_variants", "context_rule", "status", "source"],
            delimiter="\t"
        )
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)

def main():
    if len(sys.argv) > 1:
        reply_file = Path(sys.argv[1])
        text = reply_file.read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    replies = parse_replies(text)
    count = apply_term_replies(replies)
    print(f"Successfully processed {count} core terms into {DEFAULT_OUTPUT_TSV}.")

if __name__ == "__main__":
    main()
