#!/usr/bin/env python3
"""
tools/fa_build/audit/inspect_candidates.py
==========================================
Scans all candidates across the 8 domains and shows exact Persian phrases
in translated pairs to identify genuine inconsistency variants.
"""
import sqlite3
import re
import sys
from pathlib import Path
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = Path("E:/freebuff/.mohmd_news.db")

CANDIDATES = [
    # Macro
    ("rate cut", r"\brate cuts?\b"),
    ("rate hike", r"\brate hikes?\b"),
    ("interest rate", r"\binterest rates?\b"),
    ("inflation", r"\binflation\b"),
    ("central bank", r"\bcentral banks?\b"),
    ("monetary policy", r"\bmonetary polic(?:y|ies)\b"),
    ("balance sheet", r"\bbalance sheets?\b"),
    ("yields", r"\b(?:treasury\s+)?yields?\b"),
    ("recession", r"\brecession\b"),
    ("hawkish", r"\bhawkish\b"),
    ("dovish", r"\bdovish\b"),
    ("tightening", r"\btightening\b"),
    # Equities
    ("equities", r"\bequities\b"),
    ("shares", r"\bshares\b"),
    ("dividend", r"\bdividends?\b"),
    ("valuation", r"\bvaluations?\b"),
    ("market cap", r"\bmarket caps?\b|\bmarket capitaliz?ations?\b"),
    ("ipo", r"\bipos?\b"),
    ("buyback", r"\bbuybacks?\b|\bshare buybacks?\b"),
    ("rally", r"\brall(?:y|ies)\b"),
    ("selloff", r"\bselloffs?\b|\bsell-offs?\b"),
    ("bull market", r"\bbull markets?\b"),
    ("bear market", r"\bbear markets?\b"),
    ("correction", r"\bcorrections?\b"),
    ("all-time high", r"\ball-time highs?\b|\bath\b"),
    ("volatility", r"\bvolatilit(?:y|ies)\b"),
    # Forex
    ("forex", r"\bforex\b|\bforeign exchange\b"),
    ("currency", r"\bcurrenc(?:y|ies)\b"),
    ("dollar index", r"\bdollar index\b|\bdxy\b"),
    ("safe haven", r"\bsafe havens?\b"),
    ("spread", r"\bspreads?\b"),
    # Oil & Energy
    ("opec", r"\bopec\b|\bopec\+\b"),
    ("brent", r"\bbrent(?:\s+crude)?\b"),
    ("wti", r"\bwti(?:\s+crude)?\b"),
    ("crude oil", r"\bcrude(?:\s+oil)?\b"),
    ("refinery", r"\brefiner(?:y|ies)\b"),
    ("natural gas", r"\bnatural gas\b"),
    # Tech & AI
    ("chips", r"\bchips?\b"),
    ("guidance", r"\bguidance\b"),
    ("data center", r"\bdata centers?\b"),
    # TA & Smart Money
    ("support", r"\bsupport\b"),
    ("resistance", r"\bresistance\b"),
    ("breakout", r"\bbreakouts?\b"),
    ("rsi", r"\brsi\b"),
    ("macd", r"\bmacd\b"),
    ("moving average", r"\bmoving averages?\b"),
    ("fibonacci", r"\bfibonacci\b"),
    ("oversold", r"\boversold\b"),
    ("pullback", r"\bpullbacks?\b"),
    ("trendline", r"\btrendlines?\b|\btrend lines?\b"),
    ("divergence", r"\bdivergences?\b"),
    # FA
    ("earnings", r"\bearnings\b"),
    ("revenue", r"\brevenues?\b"),
    ("cash flow", r"\bcash flows?\b"),
    # Crypto
    ("etf", r"\betfs?\b"),
    ("halving", r"\bhalvings?\b"),
    ("staking", r"\bstaking\b"),
    ("stablecoin", r"\bstablecoins?\b"),
    ("defi", r"\bdefi\b"),
    ("smart contract", r"\bsmart contracts?\b"),
    ("wallet", r"\bwallets?\b"),
    ("custody", r"\bcustod(?:y|ian|ians)\b"),
    ("ledger", r"\bledgers?\b"),
    ("node", r"\bnodes?\b"),
]

def main():
    con = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    cur = con.cursor()
    articles = cur.execute("SELECT title, title_fa, summary, summary_fa FROM articles").fetchall()
    con.close()

    print(f"Loaded {len(articles)} articles.")

    for term, pat_str in CANDIDATES:
        pat = re.compile(pat_str, re.IGNORECASE)
        matching_pairs = []
        for t, t_fa, s, s_fa in articles:
            if t and t_fa and pat.search(t):
                matching_pairs.append((t, t_fa))
            elif s and s_fa and pat.search(s):
                matching_pairs.append((s, s_fa))
        
        print(f"=== {term} (matches: {len(matching_pairs)}) ===")
        # Print first 3 samples
        for en, fa in matching_pairs[:3]:
            print(f"  EN: {en[:70]}")
            print(f"  FA: {fa[:70]}")

if __name__ == "__main__":
    main()
