"""persian_words.py — Persian crypto vocabulary, vendored + wired.

Vocabulary source: https://github.com/mohamadkhalaj/persian-crypto-words
(MIT license, kept verbatim under ``vendor/persian-crypto-words/`` together
with its LICENSE file). The repo ships two lists:

* ``crypto_names.txt`` — coin names as (English, Persian, ticker) triplets.
* ``list.txt`` — free-form trading jargon, mostly Persian, **heavily mixed
  with generic finance words** (بازار، قیمت، دلار، تحلیل، صعود…) that must
  never be allowed to open a topic lane on their own.

How this module turns that into something safe to match against:

* Only the **coin names** become matchable phrases, filtered to lines that
  actually carry Persian script. A Persian name is unambiguous — «ریپل» or
  «پولکادات» cannot mean anything else.
* Meme coins (دوج، شیبا، پپه…) are excluded on purpose: the channel profile
  hard-excludes the meme lane, so their names must not quietly open the
  crypto lane either.
* A short, hand-picked jargon tuple from ``list.txt`` adds the trading words
  that really do mean crypto and nothing else (فاندینگ، لیکویید، نهنگ…).
  Everything generic in that file stays vendor-only.

Matching is plain token n-gram membership over text that was already run
through :func:`channel_profile.normalize` — no regex per word, O(tokens).
"""

from __future__ import annotations

import os
import re
from typing import Dict, List

_VENDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "vendor", "persian-crypto-words")
_FA_RE = re.compile(r"[\u0600-\u06FF]")

# The channel's OFF_PROFILE meme gate is deliberately narrow; these coins
# must not re-enter through the lexicon either.
_MEME_EN = ("doge", "shiba", "pepe", "bonk", "floki", "memecoin", "meme coin")
_MEME_SYM = ("DOGE", "SHIB", "PEPE", "BONK", "FLOKI")

# From list.txt, kept only where the word means crypto and nothing else.
# Generic finance vocabulary from that file (بازار، قیمت، دلار، تحلیل، صعود،
# سقوط، سرمایه…) is deliberately NOT wired — it would misfire on ordinary
# domestic news. Token-launch words (ایردراپ، عرضه اولیه) are excluded too:
# they belong to the off-profile DeFi lane, not to the crypto lane.
# Only market-STRUCTURE terms here: generic words (کیف پول، تراکنش، تریدر،
# هولد…) appear in ordinary gold/FX copy and one hit must not flip a
# story's lane to crypto via the lexicon-evidence rule.
JARGON = (
    "رمزارز", "ارز دیجیتال", "کریپتو", "بلاک چین", "بلاکچین",
    "آلت کوین", "الت کوین", "نهنگ", "فاندینگ", "لیکویید", "لیکوییدیتی",
    "فیوچرز", "ماینینگ", "ماینر", "دامیننس", "مارکت کپ", "هشریت",
)

_phrases: Dict[str, str] = {}          # normalized phrase -> display spelling
_loaded = False


def _fa_lines(path: str) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [ln.strip() for ln in f if ln.strip()]
    except OSError:
        return []


def load() -> Dict[str, str]:
    """normalized phrase -> the vendored Persian spelling it came from."""
    global _loaded
    if _loaded:
        return _phrases

    from channel_profile import normalize   # local: avoids import cycles

    lines = _fa_lines(os.path.join(_VENDOR, "crypto_names.txt"))
    # crypto_names.txt is *mostly* (English, Persian, ticker) but several
    # coins carry no Persian line, so fixed strides desync. Parse as a
    # stream instead: a latin non-ticker line becomes the pending English
    # name, a Persian line is its translation, a short all-caps token closes
    # the record.
    ticker_re = re.compile(r"^[A-Z0-9]{2,8}$")
    pending_en = ""
    last_ticker = ""
    for raw in lines:
        if _FA_RE.search(raw):
            # some records carry no English prose name — «XRP / ریپل / XRP»
            en = pending_en or last_ticker
            if not en:
                continue
            if any(m in en.lower() for m in _MEME_EN):
                pending_en = ""
                continue
            fa = raw.split("(")[0].strip()      # «پالی‌گان (ماتیک سابق)»
            norm = normalize(fa)
            if len(norm.replace(" ", "")) >= 3:
                _phrases.setdefault(norm, fa)
            pending_en = ""
        elif ticker_re.match(raw):
            last_ticker = raw
            if raw in _MEME_SYM:
                pending_en = ""                 # drop the whole record
        else:
            pending_en = raw

    for phrase in JARGON:
        norm = normalize(phrase)
        if norm:
            _phrases.setdefault(norm, phrase)

    _loaded = True
    return _phrases


def crypto_evidence(text_norm: str) -> List[str]:
    """Persian crypto terms present in an already-normalized text.

    Input must come from :func:`channel_profile.normalize` (or be plain
    lowercase Persian) — matching is exact token n-gram membership. Returns
    the vendored spellings, deduped, longest matches first.
    """
    phrases = load()
    if not phrases or not text_norm:
        return []
    toks = str(text_norm).split()
    out: List[str] = []
    # longest first so «بیت کوین کش» wins over its «بیت کوین» prefix
    for n in (3, 2, 1):
        for i in range(len(toks) - n + 1):
            disp = phrases.get(" ".join(toks[i:i + n]))
            if disp and disp not in out:
                out.append(disp)
    return out[:8]
