#!/usr/bin/env python3
"""
FA data collection — fa_wordfreq.tsv (Phase 1, deliverable c)
==============================================================
Persian word frequencies from two license-clean corpora:

  1. fa.wikipedia official dump (CC BY-SA 4.0) — downloaded once to
     var/fa_raw/ (gitignored, resumable via HTTP Range), parsed in streaming
     fashion (xml.etree iterparse + bz2), namespace 0 only, redirects and
     disambiguation-free main text. Markup stripped crudely but deterministically
     (templates, refs, tables, categories, file links) — documented, not fancy.
  2. the project's own Persian feeds (title_fa + summary_fa of `articles`), DB
     opened read-only. Counts only.

Output: word, wiki_count, feed_count, total — sorted by total desc, kept only
where total >= 2 (or the word appears in the feeds at all). The pruned tail is
the Phase-5 model's raw material decision, not this file's problem.

Standalone only; never imported by app.py. Pure stdlib.
"""
import bz2
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fa_norm import BASE, DATA_FA, RAW_DIR, fa_words, write_stats, write_tsv

DUMP_URL = ("https://dumps.wikimedia.org/fawiki/latest/"
            "fawiki-latest-pages-articles.xml.bz2")
DUMP_FILE = RAW_DIR / "fawiki-pages-articles.xml.bz2"
DB_FILE = BASE / ".mohmd_news.db"

MIN_TOTAL = 2

# crude, deterministic markup stripping (order matters)
_RE_COMMENT = re.compile(r"<!--.*?-->", re.S)
_RE_REF = re.compile(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", re.S)
_RE_TAG = re.compile(r"</?[a-zA-Z][^>]*>")
_RE_TABLE = re.compile(r"\{\|.*?\|\}", re.S)
_RE_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")      # innermost-first, repeated
_RE_FILE = re.compile(r"\[\[(?:فایل|پرونده|Image|File|رده|Category):[^\]]*\]\]",
                      re.I)
_RE_LINK = re.compile(r"\[\[([^\]|]+)\|([^\]]+)\]\]")   # pipe text wins
_RE_SIMPLELINK = re.compile(r"\[\[([^\]]+)\]\]")
_RE_URL = re.compile(r"https?://\S+|www\.\S+")

_TAG_RE = re.compile(r"<[^>]+>")


def strip_markup(text):
    """Deterministic crude wikitext -> plain-ish text."""
    text = _RE_COMMENT.sub(" ", text)
    text = _RE_REF.sub(" ", text)
    text = _RE_TABLE.sub(" ", text)
    while True:
        new = _RE_TEMPLATE.sub(" ", text)
        if new == text:
            break
        text = new
    text = _RE_FILE.sub(" ", text)
    text = _RE_LINK.sub(r"\2", text)
    text = _RE_SIMPLELINK.sub(r"\1", text)
    text = _RE_URL.sub(" ", text)
    text = _RE_TAG.sub(" ", text)
    return text


def count_dump():
    """Stream the fa.wikipedia dump; return Counter of normalized words."""
    if not DUMP_FILE.exists():
        from fa_norm import download
        print(f"[wordfreq] downloading dump -> {DUMP_FILE} ...")
        size = download(DUMP_URL, DUMP_FILE, timeout=600)
        print(f"[wordfreq] dump bytes={size}")
    counts = Counter()
    pages = kept = 0
    with bz2.open(DUMP_FILE, "rb") as fh:
        for _ev, el in ET.iterparse(fh, events=("end",)):
            tag = el.tag.rsplit("}", 1)[-1]
            if tag != "page":
                continue
            pages += 1
            if pages % 100000 == 0:
                print(f"  ... pages={pages} kept={kept} vocab={len(counts)}")
            ns = title = text = None
            for sub in el:
                st = sub.tag.rsplit("}", 1)[-1]
                if st == "ns":
                    ns = (sub.text or "").strip()
                elif st == "title":
                    title = sub.text or ""
                elif st == "revision":
                    for s2 in sub:
                        if s2.tag.rsplit("}", 1)[-1] == "text":
                            text = s2.text or ""
            el.clear()
            if ns != "0" or not text or text.lstrip().upper().startswith("#REDIRECT"):
                continue
            kept += 1
            body = strip_markup(text)
            for w in fa_words(body):
                w = w.strip("‌-ـ")
                if len(w) >= 2 and any("\u0600" <= c <= "\u06FF" for c in w):
                    counts[w] += 1
    print(f"[wordfreq] dump done pages={pages} kept={kept} vocab={len(counts)}")
    return counts


def count_feeds():
    """Project's own Persian feeds (title_fa, summary_fa) — read-only DB."""
    counts = Counter()
    try:
        con = sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True)
        rows = con.execute(
            "SELECT title_fa, summary_fa FROM articles "
            "WHERE title_fa IS NOT NULL OR summary_fa IS NOT NULL"
        ).fetchall()
        con.close()
    except sqlite3.Error as e:
        print(f"  [warn] feeds DB unavailable: {e}")
        return counts
    for title_fa, summary_fa in rows:
        for w in fa_words(title_fa or "") + fa_words(summary_fa or ""):
            w = w.strip("‌-ـ")
            if len(w) >= 2 and any("\u0600" <= c <= "\u06FF" for c in w):
                counts[w] += 1
    print(f"[wordfreq] feeds rows={len(rows)} vocab={len(counts)}")
    return counts


def main():
    print("[wordfreq] fa.wikipedia dump + project feeds -> fa_wordfreq.tsv")
    wiki = count_dump()
    feed = count_feeds()

    vocab = set(wiki) | set(feed)
    rows = []
    for w in vocab:
        wc, fc = wiki.get(w, 0), feed.get(w, 0)
        total = wc + fc
        if total >= MIN_TOTAL or fc >= 1:
            rows.append([w, wc, fc, total])
    rows.sort(key=lambda r: (-r[3], r[0]))

    out = DATA_FA / "fa_wordfreq.tsv"
    write_tsv(out, ["word", "wiki_count", "feed_count", "total"], rows)

    sources = [
        {"name": "fa.wikipedia dump (CC BY-SA 4.0)",
         "url": DUMP_URL,
         "license": "CC BY-SA 4.0",
         "detail": "namespace 0, redirects skipped, crude deterministic markup "
                   "strip; words len>=2, Persian script only"},
        {"name": "project feeds (own data)",
         "url": ".mohmd_news.db articles.title_fa/summary_fa",
         "license": "n/a (own data)",
         "detail": f"vocabulary={len(feed)}"},
    ]
    size_mb = out.stat().st_size / 1e6
    write_stats("wordfreq", "fa_wordfreq.tsv", len(rows), sources,
                notes=[f"pruned: kept rows with total>={MIN_TOTAL} or feed>=1; "
                       f"file={size_mb:.1f}MB; vocab_kept={len(rows)} "
                       f"vocab_total={len(vocab)}"])
    print(f"[wordfreq] wrote {out} rows={len(rows)} size={size_mb:.1f}MB "
          f"pruned={len(vocab) - len(rows)}")


if __name__ == "__main__":
    main()
