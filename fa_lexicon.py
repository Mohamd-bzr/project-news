#!/usr/bin/env python3
"""
fa_lexicon — lazy, read-only loader for the data/fa lexicon bundle (Phase 2)
============================================================================
Pure stdlib. Never imports `app`. No network. No writes. No new threads.

What it loads (all from the Phase-1 bundle, committed at data/fa/):
  * entities.tsv + terms.tsv  -> EN key -> Persian rendering candidates with
    confidence, kind and source (small: ~5k rows, eager on first use).
  * fa_wordfreq.tsv           -> Persian word -> counts (large: ~785k rows;
    loaded ONLY on explicit demand via load_wordfreq(), with a count
    threshold that keeps the runtime slice small).

Contract with callers:
  * fa_for() returns None when the key is missing or AMBIGUOUS — it never
    guesses and never fabricates a rendering.
  * Within one rendering family (typography variants like space-vs-ZWNJ are
    one family), the representative is chosen deterministically:
    ZWNJ form > higher confidence > shorter > lexicographic.
"""
import csv
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data" / "fa"
ZWNJ = "\u200c"


def canon_fa(fa):
    """Family key for AMBIGUITY grouping in fa_for(): every spelling variant
    of the same phrase (space / ZWNJ / joined) counts as one family."""
    return (fa or "").replace(ZWNJ, "").replace(" ", "")


def canon_sep(fa):
    """TYPOGRAPHY-only key: space and ZWNJ are the same separator; word
    boundaries are PRESERVED. «بیت کوین» == «بیت‌کوین», but «رمز ارز» (two
    words) != «رمزارز» (one word) — joining/splitting words is a human
    decision (REVIEW.md), never an automatic one."""
    s = (fa or "").replace(ZWNJ, " ")
    s = re.sub(r" {2,}", " ", s).strip(" ")
    return s.replace(" ", ZWNJ)


def norm_en_key(s):
    """EN lookup key: collapsed whitespace, trimmed, lowercased."""
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


class Lexicon:
    """EN->FA lookup over entities.tsv + terms.tsv. Lazy, cached, read-only."""

    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self._en = None                    # dict: en key -> [(fa, conf, kind)]
        self._fa_map = None                # canon(fa) -> (rep, 1, "")

    # -- loading -----------------------------------------------------------
    def _load(self):
        en = {}
        for name, kind in (("entities.tsv", "entity"), ("terms.tsv", "term")):
            path = self.data_dir / name
            if not path.exists():
                continue
            with open(path, encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f, delimiter="\t"):
                    key = norm_en_key(row.get("en"))
                    fa = (row.get("fa") or "").strip()
                    if not key or not fa:
                        continue          # never fabricate a row
                    try:
                        conf = float(row.get("confidence") or 0)
                    except ValueError:
                        conf = 0.0
                    if kind == "entity" and name == "entities.tsv":
                        # entities.tsv has no confidence column: use source
                        conf = 0.85       # Wikidata labels are curated
                    en.setdefault(key, []).append((fa, conf, kind))
        self._en = en
        return en

    @property
    def table(self):
        if self._en is None:
            self._load()
        return self._en

    @property
    def fa_windows(self):
        """canon(fa rendering) -> canonical representative (ZWNJ-preferring).

        Used by fa_postedit to normalize TYPOGRAPHY variants of the same
        Persian phrase («بیت کوین» -> «بیت‌کوین»); genuinely different words
        have different canon keys, so only spelling variants collapse.
        """
        if getattr(self, "_fa_map", None) is None:
            m = {}
            for rows in self.table.values():
                fams = {}
                for fa, conf, kind in rows:
                    fams.setdefault(canon_sep(fa), []).append((fa, conf, kind))
                for fam, members in fams.items():
                    rep = self._representative(members)
                    prev = m.get(fam)
                    if prev is None or self._representative([prev, (rep, 1, "")]) == rep:
                        m[fam] = (rep, 1, "")
            self._fa_map = m
        return self._fa_map

    # -- lookup ------------------------------------------------------------
    @staticmethod
    def _representative(rows):
        """Deterministic pick inside one family (see module docstring)."""
        def sort_key(r):
            fa = r[0]
            return (ZWNJ not in fa, -r[1], len(fa), fa)
        return sorted(rows, key=sort_key)[0][0]

    def _load_latin(self):
        """Loads vetted entity and project-name entries for Latin residue replacement.

        Rules:
          * ONLY entities.tsv + vetted crypto project-names from terms.tsv.
          * Rows with source wiktionary-fa, and any common English words
            (from common_english_stoplist.txt), are NEVER included.
          * Ticker expansions and ETF/ETN are never included.
        """
        stop_path = self.data_dir / "common_english_stoplist.txt"
        stoplist = set()
        if stop_path.exists():
            with open(stop_path, "r", encoding="utf-8") as f:
                for line in f:
                    w = line.strip().lower()
                    if w:
                        stoplist.add(w)

        latin_entries = {}
        # 1. entities.tsv (proper names)
        ent_path = self.data_dir / "entities.tsv"
        if ent_path.exists():
            with open(ent_path, encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f, delimiter="\t"):
                    key = norm_en_key(row.get("en"))
                    fa = (row.get("fa") or "").strip()
                    if not key or not fa or key in stoplist:
                        continue
                    if key in {"etf", "etn"} or any(c.isdigit() or c in ".-" for c in key):
                        continue
                    latin_entries.setdefault(key, []).append((fa, 0.85, "entity"))

        # 2. Vetted crypto project names from terms.tsv
        terms_path = self.data_dir / "terms.tsv"
        if terms_path.exists():
            with open(terms_path, encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f, delimiter="\t"):
                    src = row.get("source") or ""
                    dom = row.get("domain") or ""
                    if dom != "crypto" or "vendor:crypto_names" not in src or "#ticker" in src or "wiktionary-fa" in src:
                        continue
                    try:
                        conf = float(row.get("confidence") or 0)
                    except ValueError:
                        conf = 0.0
                    if conf < 0.8:
                        continue
                    key = norm_en_key(row.get("en"))
                    fa = (row.get("fa") or "").strip()
                    if not key or not fa or key in stoplist:
                        continue
                    if key in {"etf", "etn"} or any(c.isdigit() or c in ".-" for c in key):
                        continue
                    latin_entries.setdefault(key, []).append((fa, conf, "term"))

        # Build unambiguous map
        m = {}
        for key, rows in latin_entries.items():
            fams = {}
            for fa, conf, _kind in rows:
                fams.setdefault(canon_fa(fa), []).append((fa, conf, _kind))
            if len(fams) == 1:
                m[key] = self._representative(next(iter(fams.values())))
        self._latin_table = m
        return m

    @property
    def latin_table(self):
        if getattr(self, "_latin_table", None) is None:
            self._load_latin()
        return self._latin_table

    def latin_fa_for(self, en_key):
        """Vetted Persian rendering for Latin residue replacement, or None."""
        return self.latin_table.get(norm_en_key(en_key))

    def is_exact_entity(self, en_key):
        """True if the EN key is an exact entry in entities.tsv."""
        key = norm_en_key(en_key)
        rows = self.table.get(key)
        return bool(rows and any(r[2] == "entity" for r in rows))

    def fa_for(self, en_key, min_conf=0.8):
        """Persian rendering for an EN key, or None (missing/ambiguous)."""
        rows = self.table.get(norm_en_key(en_key))
        if not rows:
            return None
        rows = [r for r in rows if r[1] >= min_conf] or rows
        fams = {}
        for fa, conf, _kind in rows:
            fams.setdefault(canon_fa(fa), []).append((fa, conf, _kind))
        if len(fams) != 1:
            return None                    # ambiguous: caller keeps original
        return self._representative(next(iter(fams.values())))

    def keys(self):
        return list(self.table)


def load_wordfreq(data_dir=None, min_total=10):
    """Persian word -> (wiki, feed, total). Explicit, thresholded, lazy.

    The full file is ~785k rows; callers outside tests should pass a
    threshold (e.g. min_total=50) so the resident slice stays small.
    Returns {} when the file is absent (never fabricates).
    """
    path = Path(data_dir) if data_dir else DATA_DIR
    path = path / "fa_wordfreq.tsv"
    out = {}
    if not path.exists():
        return out
    with open(path, encoding="utf-8", newline="") as f:
        next(f, None)                     # header
        for row in csv.reader(f, delimiter="\t"):
            if len(row) != 4:
                continue
            word, wiki, feed, total = row
            try:
                total_i = int(total)
            except ValueError:
                continue
            if total_i >= min_total:
                out[word] = (int(wiki), int(feed), total_i)
    return out


_singleton = None


def lexicon():
    """Process-wide lazy singleton (module-internal cache, no app state)."""
    global _singleton
    if _singleton is None:
        _singleton = Lexicon()
    return _singleton
