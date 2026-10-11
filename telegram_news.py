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


def fetch_source(handle: str, refresh: bool = False) -> dict:
    """One source: ``{handle, title, url, ok, error, fetched_at, posts}``.

    A network or parse failure is reported INSIDE the payload (ok=False) rather
    than raised, so the section keeps the other channels alive.
    """
    handle = (handle or "").strip().lstrip("@")
    src = next((s for s in SOURCES if s["handle"].lower() == handle.lower()), None)
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


def fetch_all(refresh: bool = False) -> list[dict]:
    """Every source in SOURCES, each failing independently."""
    return [fetch_source(s["handle"], refresh=refresh) for s in SOURCES]
