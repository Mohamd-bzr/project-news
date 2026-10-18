#!/usr/bin/env python3
"""
tools/fa_build/audit/discover_and_fetch_native.py
=================================================
Discovers and fetches expanded Persian RSS feeds from economic, technology,
and general news outlets:
  - Probes tgju.org (<link rel="alternate" ...>) on homepage and /news
  - Fetches category feeds for Persian outlets (target >= 1500 items)
  - Enforces 1.2s delay between requests (<= 1 req/sec)
  - Counts only: never stores article text on disk
  - Groups crypto terms by lemma:
      1. «ارز دیجیتال» + «ارزهای دیجیتال»
      2. «رمزارز» + «رمزارزها»
      3. «کریپتو»
      4. «دارایی دیجیتال»
  - Computes counts and shares WITH and WITHOUT arzdigital
  - Checks owner's 60% rule on general outlets
"""
import re
import sys
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 FreebuffAudit/2.0"
}

FA_LETTER = r"[\u0600-\u06ff\u200c]"

def make_wt_pattern(term):
    escaped = re.escape(term.strip()).replace(r"\ ", r"[ \u200c]+")
    pat = rf"(?<!{FA_LETTER}){escaped}(?:\u200c?(?:ها|های|ی|ای|را|ام))?(?!{FA_LETTER})"
    return re.compile(pat)

def fetch_url(url, timeout=12):
    time.sleep(1.2)  # Strictly enforce 1 req / second
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:
        print(f"  [ERROR] {url}: {e}", file=sys.stderr)
        return None

def find_tgju_rss():
    print("Checking tgju.org homepage and /news for RSS link...", file=sys.stderr)
    for probe_url in ("https://www.tgju.org/", "https://www.tgju.org/news"):
        html_bytes = fetch_url(probe_url)
        if not html_bytes:
            continue
        html = html_bytes.decode("utf-8", errors="replace")
        m = re.search(r'<link[^>]+rel=["\']alternate["\'][^>]+type=["\']application/rss\+xml["\'][^>]+href=["\']([^"\']+)["\']', html, re.I)
        if not m:
            m = re.search(r'<link[^>]+type=["\']application/rss\+xml["\'][^>]+href=["\']([^"\']+)["\']', html, re.I)
        if m:
            href = m.group(1)
            if href.startswith("/"):
                href = "https://www.tgju.org" + href
            return href
        m_links = re.findall(r'href=["\']([^"\']*(?:rss|feed)[^"\']*)["\']', html, re.I)
        for link in m_links:
            if "feed" in link.lower() or "rss" in link.lower():
                if link.startswith("/"):
                    link = "https://www.tgju.org" + link
                return link
    return None

def extract_items_text(xml_bytes):
    if not xml_bytes:
        return []
    root = None
    for enc in ("utf-8", "windows-1256", "iso-8859-1"):
        try:
            root = ET.fromstring(xml_bytes.decode(enc, errors="replace").encode("utf-8"))
            break
        except Exception:
            pass
    if root is None:
        return []

    texts = []
    for item in root.iter("item"):
        t = item.findtext("title") or ""
        d = item.findtext("description") or ""
        texts.append(f"{t} {d}")
    if not texts:
        for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
            t = entry.findtext("{http://www.w3.org/2005/Atom}title") or ""
            s = entry.findtext("{http://www.w3.org/2005/Atom}summary") or ""
            c = entry.findtext("{http://www.w3.org/2005/Atom}content") or ""
            texts.append(f"{t} {s} {c}")
    return texts

def main():
    tgju_rss = find_tgju_rss()
    print(f"TGJU discovered RSS: {tgju_rss}", file=sys.stderr)

    # Expanded list of feeds across outlets targeting >= 1500 items
    FEEDS = [
        # 1. Donya-e-Eqtesad
        ("donya-eqtesad:main", "https://donya-e-eqtesad.com/rss"),

        # 2. EghtesadOnline (General Economic & Markets)
        ("eghtesadonline:main", "https://www.eghtesadonline.com/rss"),
        ("eghtesadonline:gold_curr", "https://www.eghtesadonline.com/rss/tp/4"),
        ("eghtesadonline:bourse", "https://www.eghtesadonline.com/rss/tp/3"),
        ("eghtesadonline:energy", "https://www.eghtesadonline.com/rss/tp/9"),
        ("eghtesadonline:banking", "https://www.eghtesadonline.com/rss/tp/7"),
        ("eghtesadonline:industry", "https://www.eghtesadonline.com/rss/tp/2"),

        # 3. Tejaratnews (Economy, Bourse, Macro, Tech, Industry)
        ("tejaratnews:main", "https://tejaratnews.com/feed/"),
        ("tejaratnews:bourse", "https://tejaratnews.com/category/%d8%a8%d9%88%d8%b1%d8%b3/feed"),
        ("tejaratnews:macro", "https://tejaratnews.com/category/%d8%a7%d9%82%d8%aa%d8%b5%d8%a7%d8%af-%da%a9%d9%84%d8%a7%d9%86/feed"),
        ("tejaratnews:tech", "https://tejaratnews.com/category/%d8%aa%da%a9%d9%86%d9%88%d9%84%d9%88%da%98%db%8c/feed"),
        ("tejaratnews:industry", "https://tejaratnews.com/category/%d8%b5%d9%86%d8%b9%d8%aa/feed"),

        # 4. Tabnak
        ("tabnak:latest", "https://www.tabnak.ir/fa/rss/allnews"),
        ("tabnak:economy", "https://www.tabnak.ir/fa/rss/2"),
        ("tabnak:politics", "https://www.tabnak.ir/fa/rss/1"),

        # 5. Asriran (General & Economic)
        ("asriran:latest", "https://www.asriran.com/fa/rss/allnews"),
        ("asriran:economy", "https://www.asriran.com/fa/rss/2"),
        ("asriran:politics", "https://www.asriran.com/fa/rss/1"),
        ("asriran:social", "https://www.asriran.com/fa/rss/3"),

        # 6. Khabaronline
        ("khabaronline:main", "https://www.khabaronline.ir/rss"),
        ("khabaronline:economy", "https://www.khabaronline.ir/rss/tp/20"),
        ("khabaronline:tech", "https://www.khabaronline.ir/rss/tp/10"),

        # 6. ISNA
        ("isna:main", "https://www.isna.ir/rss"),
        ("isna:economy", "https://www.isna.ir/rss/tp/14"),
        ("isna:energy", "https://www.isna.ir/rss/tp/14/energy"),
        ("isna:tech", "https://www.isna.ir/rss/tp/9"),

        # 7. MehrNews
        ("mehrnews:main", "https://www.mehrnews.com/rss"),
        ("mehrnews:economy", "https://www.mehrnews.com/rss/tp/25"),
        ("mehrnews:tech", "https://www.mehrnews.com/rss/tp/6"),
        ("mehrnews:intl", "https://www.mehrnews.com/rss/tp/7"),

        # 8. IRNA
        ("irna:main", "https://www.irna.ir/rss"),
        ("irna:economy", "https://www.irna.ir/rss/tp/20"),
        ("irna:tech", "https://www.irna.ir/rss/tp/28"),

        # 9. Digiato (Technology)
        ("digiato:main", "https://digiato.com/feed"),

        # 10. Arzdigital (Crypto Specialist)
        ("arzdigital:main", "https://arzdigital.com/feed/"),
        ("arzdigital:news", "https://arzdigital.com/category/news/feed/"),
    ]

    if tgju_rss:
        FEEDS.insert(0, ("tgju:main", tgju_rss))

    # Grouped by Lemma
    LEMMAS = {
        "ارز دیجیتال": [
            "ارز دیجیتال",
            "ارزهای دیجیتال",
            "ارز دیجیتالی",
            "ارزهای دیجیتالی",
        ],
        "رمزارز": [
            "رمزارز",
            "رمز ارز",
            "رمزارزها",
            "رمز ارزها",
        ],
        "کریپتو": [
            "کریپتو",
            "کریپتوکارنسی",
        ],
        "دارایی دیجیتال": [
            "دارایی دیجیتال",
            "دارایی‌های دیجیتال",
            "دارایی های دیجیتال",
        ],
    }

    lemma_patterns = {
        lemma: [make_wt_pattern(term) for term in terms]
        for lemma, terms in LEMMAS.items()
    }

    GENERAL_TERMS = [
        "بازدهی", "بازده", "افزایش نرخ بهره", "حمایت", "پشتیبانی",
        "نگهداری", "حضانت", "عرضه اولیه", "استیکینگ", "بازار صعودی",
        "بازار گاوی", "اوپک", "اوپک پلاس", "اشباع فروش", "شاخص دلار",
        "نفت برنت", "برنت", "پولبک", "شکست", "پیش‌بینی"
    ]
    gen_patterns = {t: make_wt_pattern(t) for t in GENERAL_TERMS}

    # Tracking
    feed_results = {}
    failed_feeds = []
    total_items = 0

    print(f"Beginning fetch of {len(FEEDS)} feeds with 1.2s delay between requests...", file=sys.stderr)

    for tag, url in FEEDS:
        outlet_name = tag.split(":")[0]
        data = fetch_url(url)
        if not data:
            failed_feeds.append(tag)
            continue
        items = extract_items_text(data)
        if not items:
            failed_feeds.append(tag)
            continue

        item_count = len(items)
        total_items += item_count
        combined_text = "\n".join(items)

        counts = {}
        for lemma, pats in lemma_patterns.items():
            cnt = sum(len(p.findall(combined_text)) for p in pats)
            counts[lemma] = cnt

        g_counts = {}
        for term, pat in gen_patterns.items():
            g_counts[term] = len(pat.findall(combined_text))

        feed_results[tag] = {
            "outlet": outlet_name,
            "items": item_count,
            "counts": counts,
            "gen_counts": g_counts,
        }
        print(f"  [OK] {tag:24s}: {item_count:3d} items", file=sys.stderr)

    print("\n" + "=" * 70)
    print(f"SAMPLE COLLECTION SUMMARY")
    print(f"Total RSS items scanned: {total_items}")
    print(f"Feeds successfully fetched: {len(feed_results)} / {len(FEEDS)}")
    print(f"Failed feeds: {len(failed_feeds)} ({', '.join(failed_feeds)})")
    print("=" * 70)

    # Aggregate by outlet
    outlet_items = defaultdict(int)
    outlet_lemma_counts = defaultdict(lambda: defaultdict(int))
    outlet_gen_counts = defaultdict(lambda: defaultdict(int))

    for tag, res in feed_results.items():
        out = res["outlet"]
        outlet_items[out] += res["items"]
        for lemma, cnt in res["counts"].items():
            outlet_lemma_counts[out][lemma] += cnt
        for term, cnt in res["gen_counts"].items():
            outlet_gen_counts[out][term] += cnt

    # Table breakdown
    outlets = sorted(outlet_items.keys())
    print("\n=== PER-OUTLET LEMMA COUNTS ===")
    header = f"{'Lemma':20s} | " + " | ".join(f"{o[:9]:>9s}" for o in outlets) + " | Total"
    print(header)
    print("-" * len(header))
    for lemma in LEMMAS:
        row_str = f"{lemma:20s} | "
        row_str += " | ".join(f"{outlet_lemma_counts[o][lemma]:9d}" for o in outlets)
        tot = sum(outlet_lemma_counts[o][lemma] for o in outlets)
        row_str += f" | {tot:5d}"
        print(row_str)

    # 1. With Arzdigital (ALL Outlets)
    total_with = {lemma: sum(outlet_lemma_counts[o][lemma] for o in outlets) for lemma in LEMMAS}
    sum_with = sum(total_with.values())

    # 2. Without Arzdigital (GENERAL Outlets only)
    gen_outlets = [o for o in outlets if o != "arzdigital"]
    total_without = {lemma: sum(outlet_lemma_counts[o][lemma] for o in gen_outlets) for lemma in LEMMAS}
    sum_without = sum(total_without.values())
    gen_items = sum(outlet_items[o] for o in gen_outlets)

    print("\n=== CRYPTOCURRENCY LEMMA SHARES ===")
    print(f"{'Lemma':20s} | With Arzdigital ({sum_with} mentions, {total_items} items) | Without Arzdigital ({sum_without} mentions, {gen_items} items)")
    print("-" * 85)
    for lemma in sorted(LEMMAS.keys(), key=lambda l: -total_without[l]):
        cnt_w = total_with[lemma]
        sh_w = (cnt_w / sum_with * 100) if sum_with else 0
        cnt_wo = total_without[lemma]
        sh_wo = (cnt_wo / sum_without * 100) if sum_without else 0
        print(f"{lemma:20s} | {cnt_w:5d} ({sh_w:5.1f}%)                         | {cnt_wo:5d} ({sh_wo:5.1f}%)")

    # Evaluation of 60% rule
    print("\n=== OWNER'S 60% RULE EVALUATION (GENERAL OUTLETS) ===")
    print(f"Total mentions in general outlets: {sum_without}")
    if sum_without >= 100:
        top_lemma, top_cnt = max(total_without.items(), key=lambda x: x[1])
        top_share = top_cnt / sum_without * 100
        print(f"Top lemma: «{top_lemma}» with {top_cnt}/{sum_without} ({top_share:.1f}%)")
        if top_share >= 60.0:
            print(f"Verdict: PASS 60% threshold ({top_share:.1f}% >= 60.0%) -> Can be recommended as default.")
        else:
            print(f"Verdict: BELOW 60% threshold ({top_share:.1f}% < 60.0%) -> Leave `cryptocurrency` PENDING.")
    else:
        print(f"Verdict: FEWER than 100 mentions ({sum_without} < 100) -> Leave `cryptocurrency` PENDING.")

    # Save outlet_gen_counts and outlet_items to JSON for mine_core_terms.py
    import json
    from pathlib import Path
    REPO = Path(__file__).resolve().parents[3]
    out_file = REPO / "tools" / "fa_build" / "audit" / "native_outlet_counts.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "items_per_outlet": dict(outlet_items),
            "gen_counts": {o: dict(c) for o, c in outlet_gen_counts.items()},
            "lemma_counts": {o: dict(c) for o, c in outlet_lemma_counts.items()},
        }, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
