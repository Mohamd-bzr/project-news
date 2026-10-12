#!/usr/bin/env python3
"""
FA data collection — SOURCES.md generator (Phase 1 provenance)
===============================================================
Reads the _stats_*.json written by fetch_entities.py / fetch_terms.py /
fetch_wordfreq.py, plus a hand-maintained SKIPPED list, and writes
data/fa/SOURCES.md: one block per artifact with retrieval date, license,
row counts, notes, and a deterministic 20-row sample of each TSV.

Standalone only; pure stdlib; no network.
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fa_norm import DATA_FA, sample_rows

# Sources considered but deliberately NOT used (recorded per the spec).
SKIPPED = [
    ("Dehkhoda dictionary", "proprietary/copyright-unknown — not openly licensed"),
    ("scraped news sites", "only acceptable for counts, none needed beyond the "
                           "project's own feeds; robots/politeness risk"),
    ("OPUS corpora", "no verified openly-licensed EN<->FA parallel corpus of "
                     "financial terms fit for glossary extraction"),
    ("Tatoeba", "CC BY but sentence-level example data, no domain glossary "
                "value beyond what Wiktionary already provides"),
    ("vendor/persian-crypto-words list.txt", "FA-only list: cannot form "
                                             "EN->FA pairs (pairs come from "
                                             "crypto_names.txt)"),
]


def block_for(artifact):
    stats_file = DATA_FA / ("_stats_" + artifact.split(".")[0] + ".json")
    if not stats_file.exists():
        return f"## {artifact}\n\n**not built yet** (run the fetch script).\n"
    import json
    stats = json.loads(stats_file.read_text(encoding="utf-8"))
    lines = [f"## {artifact}", "",
             f"- rows: **{stats['rows']}**",
             f"- built: {date.today().isoformat()}"]
    for s in stats["sources"]:
        lines.append(f"- source: {s['name']} — {s.get('license', '?')} — "
                     f"{s['url']}")
        if s.get("detail"):
            lines.append(f"  - detail: {s['detail']}")
    for n in stats.get("notes", []):
        lines.append(f"- note: {n}")
    tsv = DATA_FA / artifact
    if tsv.exists():
        header, sample = sample_rows(tsv, 20)
        lines += ["", "### 20-row sample (deterministic md5 ordering)", "",
                  "```", header.replace("\t", " | ")]
        lines += [ln.replace("\t", " | ") for ln in sample]
        lines += ["```"]
    lines.append("")
    return "\n".join(lines)


def main():
    parts = [
        "# data/fa/SOURCES.md — provenance for the Phase-1 FA data bundle",
        "",
        "Built by the standalone scripts in `tools/fa_build/` (network lives "
        "there only; nothing in this directory is imported by the app at "
        "runtime). Raw downloads cached under `var/fa_raw/` (gitignored). "
        "License rule: openly-licensed sources only.",
        "",
    ]
    for artifact in ("entities.tsv", "terms.tsv", "fa_wordfreq.tsv"):
        parts.append(block_for(artifact))
    parts += ["## Considered but skipped", ""]
    parts += [f"- **{n}** — {why}" for n, why in SKIPPED]
    parts.append("")
    (DATA_FA / "SOURCES.md").write_text("\r\n".join(parts), encoding="utf-8",
                                        newline="")
    print(f"[report] wrote {DATA_FA / 'SOURCES.md'}")


if __name__ == "__main__":
    main()
