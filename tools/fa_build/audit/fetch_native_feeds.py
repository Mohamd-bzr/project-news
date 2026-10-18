#!/usr/bin/env python3
"""
tools/fa_build/audit/fetch_native_feeds.py
==========================================
Fetches Persian RSS feeds (1 req/sec rate limit), extracts titles + descriptions
in memory, and computes whole-token frequency counts for the cryptocurrency family
and key financial terms. Never stores article text on disk.
"""
import re
import sys
import time
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")

FEEDS = [
    ("donya-eqtesad", "https://donya-e-eqtesad.com/rss"),
    ("eghtesadonline", "https://www.eghtesadonline.com/rss"),
    ("isna", "https://www.isna.ir/rss"),
    ("mehrnews", "https://www.mehrnews.com/rss"),
    ("tejaratnews", "https://tejaratnews.com/feed/"),
    ("arzdigital", "https://arzdigital.com/feed/"),
    ("tgju", "https://www.tgju.org/rss"),
    ("irna", "https://www.irna.ir/rss"),
]

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FreebuffAudit/1.0"
}

FA_LETTER = r"[\u0600-\u06ff\u200c]"

def make_wt_pattern(term):
    escaped = re.escape(term.strip()).replace(r"\ ", r"[ \u200c]+")
    # Whole-token: not preceded by Persian letter/ZWNJ, optional standard suffixes, not followed by Persian letter/ZWNJ
    pat = rf"(?<!{FA_LETTER}){escaped}(?:\u200c?(?:ها|های|ی|ای|را|ام))?(?!{FA_LETTER})"
    return re.compile(pat)

CRYPTO_TERMS = [
    "ارز دیجیتال",
    "ارزهای دیجیتال",
    "رمزارز",
    "رمز ارز",
    "رمزارزها",
    "دارایی دیجیتال",
    "ارز رمزنگاری شده",
    "ارز رمزنگاری‌شده",
    "کریپتو",
]

GENERAL_TERMS = [
    "نرخ بهره",
    "کاهش نرخ بهره",
    "تورم",
    "نفت خام",
    "برنت",
    "اوپک پلاس",
    "اوپک‌پلاس",
    "بانک مرکزی",
    "فدرال رزرو",
    "فدرال‌رزرو",
    "سود تقسیمی",
    "گزارش سود",
    "حمایت",
    "مقاومت",
    "شکست",
]

def fetch_feed(name, url):
    print(f"Fetching {name} ({url})...", file=sys.stderr)
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            content = resp.read()
            return content
    except Exception as e:
        print(f"  [ERROR] {name}: {e}", file=sys.stderr)
        return None

def extract_items_text(xml_bytes):
    if not xml_bytes:
        return []
    try:
        root = ET.fromstring(xml_bytes)
    except Exception as e:
        # Some RSS have encoding issues, try decoding with utf-8 or windows-1256
        for enc in ("utf-8", "windows-1256", "iso-8859-1"):
            try:
                root = ET.fromstring(xml_bytes.decode(enc, errors="replace").encode("utf-8"))
                break
            except Exception:
                pass
        else:
            return []

    texts = []
    # RSS 2.0 / Atom
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
    crypto_patterns = {t: make_wt_pattern(t) for t in CRYPTO_TERMS}
    general_patterns = {t: make_wt_pattern(t) for t in GENERAL_TERMS}

    outlet_stats = {}
    failed_outlets = []
    total_items = 0

    for name, url in FEEDS:
        xml_data = fetch_feed(name, url)
        time.sleep(1.2)  # Respect 1 req/sec policy

        if xml_data is None:
            failed_outlets.append(name)
            continue

        items = extract_items_text(xml_data)
        if not items:
            failed_outlets.append(name)
            continue

        item_count = len(items)
        total_items += item_count
        combined_text = "\n".join(items)

        c_counts = {}
        for term, pat in crypto_patterns.items():
            c_counts[term] = len(pat.findall(combined_text))

        g_counts = {}
        for term, pat in general_patterns.items():
            g_counts[term] = len(pat.findall(combined_text))

        outlet_stats[name] = {
            "items": item_count,
            "crypto": c_counts,
            "general": g_counts,
        }

    print("\n" + "=" * 60)
    print(f"AUDIT SUMMARY: {len(outlet_stats)} successful outlets, {len(failed_outlets)} failed outlets")
    print(f"Total RSS items scanned: {total_items}")
    if failed_outlets:
        print(f"Failed outlets: {', '.join(failed_outlets)}")
    print("=" * 60)

    # 1. Cryptocurrency family breakdown
    print("\n=== CRYPTOCURRENCY FAMILY IN NATIVE PERSIAN OUTLETS ===")
    total_crypto = {t: sum(stats["crypto"][t] for stats in outlet_stats.values()) for t in CRYPTO_TERMS}
    # Collapse spelling variants for summary
    # e.g. ارز رمزنگاری شده vs ارز رمزنگاری‌شده
    collapsed_crypto = {
        "ارز دیجیتال": total_crypto["ارز دیجیتال"],
        "ارزهای دیجیتال": total_crypto["ارزهای دیجیتال"],
        "رمزارز": total_crypto["رمزارز"],
        "رمز ارز": total_crypto["رمز ارز"],
        "رمزارزها": total_crypto["رمزارزها"],
        "دارایی دیجیتال": total_crypto["دارایی دیجیتال"],
        "ارز رمزنگاری‌شده": total_crypto["ارز رمزنگاری شده"] + total_crypto["ارز رمزنگاری‌شده"],
        "کریپتو": total_crypto["کریپتو"],
    }
    crypto_sum = sum(collapsed_crypto.values())

    print(f"{'Term':25s} | " + " | ".join(f"{name[:8]:>8s}" for name in outlet_stats.keys()) + " | Total | Share")
    print("-" * (30 + 11 * len(outlet_stats) + 16))
    for term, tot in sorted(collapsed_crypto.items(), key=lambda x: -x[1]):
        per_out = " | ".join(f"{outlet_stats[o]['crypto'].get(term, 0):8d}" for o in outlet_stats.keys())
        share = (tot / crypto_sum * 100) if crypto_sum else 0
        print(f"{term:25s} | {per_out} | {tot:5d} | {share:5.1f}%")
    print(f"Total cryptocurrency mentions: {crypto_sum}")

    # 2. General terms breakdown
    print("\n=== GENERAL FINANCE TERMS IN NATIVE PERSIAN OUTLETS ===")
    collapsed_general = {
        "نرخ بهره": sum(s["general"]["نرخ بهره"] for s in outlet_stats.values()),
        "کاهش نرخ بهره": sum(s["general"]["کاهش نرخ بهره"] for s in outlet_stats.values()),
        "تورم": sum(s["general"]["تورم"] for s in outlet_stats.values()),
        "نفت خام": sum(s["general"]["نفت خام"] for s in outlet_stats.values()),
        "برنت": sum(s["general"]["برنت"] for s in outlet_stats.values()),
        "اوپک پلاس": sum(s["general"]["اوپک پلاس"] + s["general"]["اوپک‌پلاس"] for s in outlet_stats.values()),
        "بانک مرکزی": sum(s["general"]["بانک مرکزی"] for s in outlet_stats.values()),
        "فدرال رزرو": sum(s["general"]["فدرال رزرو"] + s["general"]["فدرال‌رزرو"] for s in outlet_stats.values()),
        "سود تقسیمی": sum(s["general"]["سود تقسیمی"] for s in outlet_stats.values()),
        "گزارش سود": sum(s["general"]["گزارش سود"] for s in outlet_stats.values()),
        "حمایت": sum(s["general"]["حمایت"] for s in outlet_stats.values()),
        "مقاومت": sum(s["general"]["مقاومت"] for s in outlet_stats.values()),
        "شکست": sum(s["general"]["شکست"] for s in outlet_stats.values()),
    }
    for term, tot in sorted(collapsed_general.items(), key=lambda x: -x[1]):
        per_out = " | ".join(f"{outlet_stats[o]['general'].get(term, 0):8d}" for o in outlet_stats.keys())
        print(f"{term:20s} | {per_out} | {tot:5d}")

if __name__ == "__main__":
    main()
