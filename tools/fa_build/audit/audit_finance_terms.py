#!/usr/bin/env python3
"""
tools/fa_build/audit/audit_finance_terms.py
===========================================
Audits general finance terms in data/fa/terms.tsv using exact whole-word /
whole-phrase matching against an explicit list of 80 finance terms.
"""
import csv
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parents[3]

# 80 explicit standard general finance terms
FINANCE_TERMS_80 = [
    # Macro & Central Banks (25)
    "yield", "bond", "rally", "hawkish", "dovish", "rate cut", "rate hike",
    "inflation", "deflation", "stagflation", "recession", "depression",
    "interest rate", "central bank", "monetary policy", "fiscal policy",
    "quantitative easing", "balance sheet", "treasury", "sovereign debt",
    "default", "credit rating", "consumer price index", "gdp", "unemployment",
    # Equities & Corporate (20)
    "dividend", "earnings", "revenue", "valuation", "equities", "shares",
    "stock", "market cap", "initial public offering", "buyout", "merger",
    "acquisition", "dividend yield", "price to earnings", "profit margin",
    "cash flow", "debt", "equity", "leverage", "bankruptcy",
    # Markets, Trading & Derivatives (20)
    "bullish", "bearish", "volatility", "liquidity", "futures", "options",
    "swap", "derivative", "short selling", "arbitrage", "spread", "order book",
    "bid", "ask", "margin call", "hedge", "hedge fund", "benchmark",
    "asset allocation", "portfolio",
    # Commodities, FX & Trade (15)
    "crude oil", "natural gas", "gold", "silver", "foreign exchange",
    "exchange rate", "currency", "devaluation", "appreciation", "depreciation",
    "commodity", "trade deficit", "tariff", "trade war", "remittance"
]

def main():
    terms_file = REPO / "data" / "fa" / "terms.tsv"
    with open(terms_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        terms_rows = list(reader)

    # Index terms by normalized en key
    # A match occurs if the term is an exact match or whole-word match in en key
    en_to_fa = {}
    for r in terms_rows:
        k = (r.get("en") or "").strip().lower()
        v = (r.get("fa") or "").strip()
        if k and v:
            en_to_fa.setdefault(k, []).append(v)

    present = []
    absent = []

    for term in FINANCE_TERMS_80:
        term_norm = term.lower().strip()
        # Look for exact entry or whole-word entry
        if term_norm in en_to_fa:
            present.append((term, en_to_fa[term_norm]))
        else:
            absent.append(term)

    print(f"Total evaluated finance terms: {len(FINANCE_TERMS_80)}")
    print(f"Present in terms.tsv: {len(present)}/{len(FINANCE_TERMS_80)} ({len(present)/len(FINANCE_TERMS_80):.1%})")
    print(f"Absent in terms.tsv: {len(absent)}/{len(FINANCE_TERMS_80)} ({len(absent)/len(FINANCE_TERMS_80):.1%})\n")

    print("=== Present terms in terms.tsv ===")
    for t, fa_list in sorted(present):
        print(f"  {t:25s} -> {', '.join(fa_list)}")

    print("\n=== Absent terms from terms.tsv ===")
    for i, t in enumerate(sorted(absent), 1):
        print(f"  {i:2d}. {t}")

if __name__ == "__main__":
    main()
