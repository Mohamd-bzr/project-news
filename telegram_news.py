#!/usr/bin/env python3
"""
Telegram News — public-channel reader for the dashboard's «اخبار تلگرامی» section
=================================================================================
Reads the PUBLIC web preview of a Telegram channel (https://t.me/s/<handle>) —
the same page anyone sees in a browser without logging in — and returns the
newest posts as plain dicts the dashboard can render.

Deliberate limits:

  * public channels only. There is no login, no invite link and no attempt to
    reach a private channel; a handle whose preview is not public simply comes
    back with ok=False and an error string. Nothing here bypasses an access
    control, and nothing ever posts to Telegram — this reader is read-only.
  * one page per read (~20 newest posts). Older posts would need pagination
    (``?before=<id>``); nothing in the product needs it yet.
  * every source fails independently: one dead channel never blanks the whole
    section.

Adding a source is one line in SOURCES — that list is the whole registry.

Usage from the app:
    import telegram_news
    telegram_news.fetch_all()                  # every source, cached
    telegram_news.fetch_source("newscitypro")  # one source, cached
"""
from __future__ import annotations

import re
import time

import requests
from bs4 import BeautifulSoup

#: The registry. Add a channel by adding a line — the endpoint reads this list
#: and nothing else. ``handle`` is the public @username (letters, digits, _).
SOURCES = [
    {"handle": "newscitypro", "title": "News city pro"},
]

def get_sources(extra_sources=None) -> list[dict]:
    """Combine default SOURCES with any configured extra sources."""
    items = list(SOURCES)
    seen = {s["handle"].lower() for s in items}
    for s in (extra_sources or []):
        if isinstance(s, dict) and s.get("handle"):
            h = str(s["handle"]).strip().lstrip("@")
            if h.lower() not in seen:
                seen.add(h.lower())
                items.append({"handle": h, "title": s.get("title") or h})
    return items

TTL_SECONDS = 300        # how long one channel's posts stay fresh in memory
MAX_POSTS = 20           # what one t.me/s/ page returns
MAX_TEXT_CHARS = 2000    # a post longer than this is truncated with a trailing …

#: Telegram's own username shape (5–32 chars, may not end in _) — also the
#: guard that keeps a caller-supplied handle from becoming part of a URL.
HANDLE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,31}$")

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept-Language": "fa,en;q=0.8",
}

# handle -> (fetched_at, payload). Same shape as app.ETF_QUOTES_CACHE: a module
# cache so a dashboard refresh does not re-download a 130 kB page per poll.
_CACHE: dict[str, tuple[float, dict]] = {}

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _plain_text(node, handle: str) -> str:
    """Plain text of one message body: ``<br>`` becomes a newline, block quotes
    get their own lines, links keep their visible shape plus the target, and a
    link back to the channel itself (the «🔥 @handle» footer every post carries)
    is dropped as noise. Entities are already decoded by BeautifulSoup."""
    if node is None:
        return ""
    clone = BeautifulSoup(str(node), "html.parser")
    self_links = {f"https://t.me/{handle}".lower(),
                  f"https://t.me/{handle}/".lower()}
    for br in clone.find_all("br"):
        br.replace_with("\n")
    for bq in clone.find_all("blockquote"):
        bq.replace_with("\n" + bq.get_text(" ", strip=True) + "\n")
    for a in clone.find_all("a", href=True):
        label = a.get_text(" ", strip=True)
        href = a["href"].strip()
        if href.lower() in self_links:
            a.replace_with("")
        elif href.startswith(("http://", "https://")):
            a.replace_with(f"{label} ({href})" if label else href)
        else:
            a.replace_with(label)
    lines = [ln.strip() for ln in clone.get_text().split("\n")]
    out, blanks = [], 0
    for ln in lines:
        blanks = blanks + 1 if not ln else 0
        if blanks <= 1:                      # collapse runs of blank lines
            out.append(ln)
    return "\n".join(out).strip()


def _first_line(text: str, limit: int = 160) -> str:
    """The headline a card can show: the first non-empty line, capped."""
    for ln in text.split("\n"):
        if ln.strip():
            return ln.strip()[:limit]
    return ""


_PROMO_PHRASES = (
    "مطالعه متن کامل",
    "مشاهده متن کامل",
    "متن کامل خبر",
    "متن کامل گزارش",
    "ادامه مطلب",
    "جزئیات بیشتر",
    "لینک خبر",
    "شبکه‌های اجتماعی",
    "شبکههای اجتماعی",
    "شبکه های اجتماعی",
    "دنبال کنید",
    "عضویت در",
    "کانال ما",
    "کانال تلگرام",
    "کانال بله",
    "ما را دنبال",
    "مارا دنبال",
    "به کانال ما",
    "پیوستن به کانال",
    "عضو شوید",
    "نظر شما چیه",
    "نظرات خود را",
    "نظرتون چیه",
    "کامنت بذارید",
    "کامنت بگذارید",
    "واکنش نشان دهید",
    "منبع خبر",
    "منبع:",
    "منبع :",
)


def is_promo_line(line: str, source_title: str = "", source_handle: str = "") -> bool:
    """Check if a line is a promotional footer, social link, reaction or signature."""
    l = line.strip()
    if not l:
        return False
    # Check if after stripping URLs, mentions and symbols nothing remains
    cleaned = re.sub(r"https?://\S+", "", l)
    cleaned = re.sub(r"@\w+", "", cleaned).strip(" \t\n\r()[]{}|/\\:;.,•-–—_~*#")
    if not cleaned:
        return True

    for p in _PROMO_PHRASES:
        if p in l:
            return True

    # Combined messengers or social links
    if ("بله" in l or "ble.ir" in l) and ("تلگرام" in l or "t.me" in l):
        return True
    if any(k in l for k in ("t.me/", "ble.ir/", "eitaa.com/", "rubika.ir/", "instagram.com/", "twitter.com/", "x.com/")):
        return True

    # Channel signature / footer
    if source_handle and source_handle.lower() in l.lower() and len(l) < 60:
        return True
    if source_title and source_title.lower() in l.lower() and len(l) < 60:
        return True

    return False


def clean_for_messenger(title: str, text: str, source_title: str = "", source_handle: str = "") -> tuple[str, str]:
    """Clean a Telegram post for dispatching to messengers (Bale / Telegram).

    Removes all URLs, handles, promo footers, social media links, reaction polls,
    and source/channel signatures, returning (clean_title, clean_body).
    """
    clean_t = str(title or "").strip()
    clean_t = re.sub(r"https?://\S+", "", clean_t)
    clean_t = re.sub(r"@\w+", "", clean_t)
    if source_handle:
        clean_t = re.sub(re.escape(source_handle), "", clean_t, flags=re.IGNORECASE)
    if source_title:
        clean_t = re.sub(re.escape(source_title), "", clean_t, flags=re.IGNORECASE)
    clean_t = clean_t.strip(" \t\n\r-–—:|/•")

    raw_text = str(text or "")
    lines = raw_text.split("\n")
    out = []
    for ln in lines:
        if is_promo_line(ln, source_title, source_handle):
            continue
        c = re.sub(r"https?://\S+", "", ln)
        c = re.sub(r"@\w+", "", c)
        c = re.sub(r"\(\s*\)", "", c)
        c = re.sub(r"\[\s*\]", "", c).strip()
        # Clean broken dangling parens leftover from URLs
        c = re.sub(r"\(\s*$", "", c).strip()
        c = re.sub(r"^\s*\)", "", c).strip()
        if source_handle and len(c) < 50:
            c = re.sub(re.escape(source_handle), "", c, flags=re.IGNORECASE).strip()
        if source_title and len(c) < 50:
            c = re.sub(re.escape(source_title), "", c, flags=re.IGNORECASE).strip()
        if c:
            out.append(c)

    # Strip trailing orphan symbols/emojis
    while out and len(out[-1]) <= 3 and not any(ch.isalnum() for ch in out[-1]):
        out.pop()

    clean_b = "\n\n".join(out).strip()
    if not clean_t and clean_b:
        clean_t = clean_b.split("\n")[0][:160]

    # If body starts with title, strip redundant first line so title is not repeated
    if clean_t and clean_b.startswith(clean_t):
        clean_b = clean_b[len(clean_t):].strip()

    return clean_t, clean_b



def _parse_views(raw: str):
    """'3.44K views' → 3440, '696 views' → 696; anything unreadable → None.
    The UI renders a missing number as «—»; it is never guessed."""
    if not raw:
        return None
    m = re.match(r"([\d]+(?:[.,][\d]+)?)\s*([KMB])?",
                 raw.translate(_DIGITS).strip(), re.I)
    if not m:
        return None
    try:
        num = float(m.group(1).replace(",", "."))
    except ValueError:
        return None
    mult = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}.get(
        (m.group(2) or "").lower(), 1)
    return int(num * mult)


def parse_channel_page(html: str, handle: str) -> list[dict]:
    """The newest-first posts of one ``t.me/s/<handle>`` page.

    Telegram lays the page's ~20-message window out OLDEST-first, so the
    collected rows are reversed before they leave here — callers always get
    the newest post at index 0.

    Pure function — no network — so the tests feed it saved HTML.
    """
    soup = BeautifulSoup(html, "html.parser")
    posts: list[dict] = []
    for wrap in soup.find_all("div", class_="tgme_widget_message_wrap")[:MAX_POSTS]:
        msg = wrap.find("div", class_="tgme_widget_message")
        if msg is None:
            continue
        data_post = msg.get("data-post") or ""
        if "/" not in data_post:
            continue
        _, msg_id = data_post.rsplit("/", 1)

        # a reply quote carries its own .tgme_widget_message_text and sits
        # BEFORE the body — the body is the first text div that is not inside
        # the reply block, otherwise a quoted headline would become the post.
        body = None
        for td in msg.find_all("div", class_="tgme_widget_message_text"):
            if td.find_parent(class_="tgme_widget_message_reply") is None:
                body = td
                break
        text = _plain_text(body, handle)

        media = None
        for kind in ("video", "photo", "document", "animation"):
            if msg.find("div", class_=f"tgme_widget_message_{kind}"):
                media = kind
                break
        if not text and not media:
            continue                        # service msgs (pinned/join) carry neither

        when = ""
        t = msg.find("time", datetime=True)
        if t is not None:
            when = t.get("datetime") or ""
        views_el = msg.find("span", class_="tgme_widget_message_views")
        posts.append({
            "id": msg_id,
            "url": f"https://t.me/{handle}/{msg_id}",
            "title": _first_line(text),
            "text": text[:MAX_TEXT_CHARS],
            "time": when,
            "views": _parse_views(views_el.get_text(" ", strip=True) if views_el else ""),
            "media": media,
        })
    posts.reverse()                     # page is oldest-first; callers want newest first
    return posts


def fetch_source(handle: str, refresh: bool = False, sources: list[dict] | None = None) -> dict:
    """One source: ``{handle, title, url, ok, error, fetched_at, posts}``.

    A network or parse failure is reported INSIDE the payload (ok=False) rather
    than raised, so the section keeps the other channels alive.
    """
    handle = (handle or "").strip().lstrip("@")
    reg = sources if sources is not None else SOURCES
    src = next((s for s in reg if s["handle"].lower() == handle.lower()), None)
    out = {"handle": handle,
           "title": src["title"] if src else handle,
           "url": f"https://t.me/{handle}",
           "ok": False, "error": "", "fetched_at": 0.0, "posts": []}
    if not HANDLE_RE.match(handle):
        out["error"] = "invalid_handle"
        return out

    now = time.time()
    if not refresh:
        hit = _CACHE.get(handle)
        if hit and now - hit[0] < TTL_SECONDS:
            return hit[1]

    try:
        r = requests.get(f"https://t.me/s/{handle}", headers=_HEADERS, timeout=15)
        r.raise_for_status()
        posts = parse_channel_page(r.text, handle)
    except Exception as e:                  # one dead channel, not a dead section
        out["error"] = f"{type(e).__name__}: {e}"[:200]
        return out

    out.update(ok=True, fetched_at=now, posts=posts)
    _CACHE[handle] = (now, out)
    return out


def fetch_all(refresh: bool = False, extra_sources: list[dict] | None = None) -> list[dict]:
    """Every source in SOURCES (and any extra_sources), each failing independently."""
    reg = get_sources(extra_sources)
    return [fetch_source(s["handle"], refresh=refresh, sources=reg) for s in reg]
