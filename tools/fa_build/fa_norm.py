#!/usr/bin/env python3
"""
Shared helpers for the Phase-1 data builders (tools/fa_build only).
====================================================================
Pure stdlib, no network at import, never imported by app.py.

Normalization contract (applied to EVERY Persian value and every English key
before it lands in data/fa/*):
  * NFC,
  * Arabic yeh/kaf -> Persian yeh/kaf (U+06CC / U+06A9), alef maksura -> yeh,
  * tatweel stripped,
  * ZWNJ: no space around it, runs collapsed, trimmed at both ends,
  * whitespace collapsed, trimmed,
  * English keys additionally lowercased.
"""
import hashlib
import json
import re
import shutil
import unicodedata
import urllib.request
from pathlib import Path

ZWNJ = "\u200c"
BASE = Path(__file__).resolve().parents[2]
DATA_FA = BASE / "data" / "fa"
RAW_DIR = BASE / "var" / "fa_raw"

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) mohmd-news-fa-build/1.0 "
       "(offline lexicon build; no telemetry)")

# Persian letters only: basic block minus Arabic punctuation/digits, plus the
# extended Persian letters (پ چ ژ گ ک ی ...), with ZWNJ allowed inside tokens.
# NOTE: a naive [\u0600-\u06FF] would swallow the Arabic comma/question mark
# (U+060C/U+061F) and Arabic-Indic digits, gluing punctuation onto words.
_FA_TOKEN_RE = re.compile(
    r"[\u0621-\u063A\u0641-\u064A\u066E-\u06D3\u200c]+")


def norm_fa(s: str) -> str:
    """Normalize a Persian label/value. Idempotent."""
    s = unicodedata.normalize("NFC", s or "")
    s = s.replace("\u064a", "\u06cc")            # Arabic yeh -> Persian yeh
    s = s.replace("\u0649", "\u06cc")            # alef maksura -> Persian yeh
    s = s.replace("\u0643", "\u06a9")            # Arabic kaf -> Persian kaf
    s = s.replace("\u0640", "")                  # tatweel
    s = re.sub(r" *\u200c *", ZWNJ, s)           # no space around ZWNJ
    s = re.sub(ZWNJ + "{2,}", ZWNJ, s)           # collapse ZWNJ runs
    s = re.sub(r" {2,}", " ", s)                 # collapse spaces
    return s.strip(" " + ZWNJ + "\t\r\n")


def norm_en(s: str) -> str:
    """Normalize an English key: NFC, collapsed whitespace, trimmed, lower."""
    s = unicodedata.normalize("NFC", s or "")
    return re.sub(r"\s+", " ", s).strip().lower()


def fa_words(text: str):
    """Normalized Persian word tokens of a text (ZWNJ kept inside tokens)."""
    return [norm_fa(w) for w in _FA_TOKEN_RE.findall(text or "")]


def write_tsv(path, header, rows):
    """Write a sorted-by-caller TSV with LF endings (git policy normalizes)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(header) + "\n")
        for r in rows:
            f.write("\t".join("" if c is None else str(c) for c in r) + "\n")


def write_stats(name, artifact, rows, sources, notes=None):
    """Record provenance for fa_report.py: data/fa/_stats_<name>.json."""
    DATA_FA.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact": artifact,
        "rows": rows,
        "sources": sources,           # [{name, url, license, detail}]
        "notes": notes or [],
    }
    p = DATA_FA / f"_stats_{name}.json"
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                 encoding="utf-8", newline="\n")
    return p


def http_get_json(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": _UA,
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def http_get_text(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def download(url, dest, timeout=120):
    """Resumable download (Range) into var/fa_raw/. Returns byte size.

    1 request per call; callers pace themselves (>=1 req/s).
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    existing = dest.stat().st_size if dest.exists() else 0
    headers = {"User-Agent": _UA}
    if existing:
        headers["Range"] = f"bytes={existing}-"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resume = (r.status == 206 and existing)
        mode = "ab" if resume else "wb"
        with open(dest, mode) as f:
            shutil.copyfileobj(r, f, length=1 << 20)
    return dest.stat().st_size


def sample_rows(path, n=20):
    """Deterministic pseudo-random sample: n rows ordered by md5(row|name)."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    body = [ln for ln in lines[1:] if ln.strip()]
    key = Path(path).name
    ranked = sorted(body, key=lambda ln: hashlib.md5((key + "|" + ln).encode())
                    .hexdigest())
    return lines[0], ranked[:n]
