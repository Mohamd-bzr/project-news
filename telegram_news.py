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
    {"handle": "newscitypro", "title": "News city pro", "type": "telegram"},
    {"handle": "iribnews", "title": "خبرگزاری صدا و سیما", "type": "bale"},
]

def get_sources(extra_sources=None, deleted_sources=None) -> list[dict]:
    """Combine default SOURCES with any configured extra sources, excluding deleted."""
    disabled = {str(d).lower().strip().lstrip("@") for d in (deleted_sources or [])}
    items = []
    seen = set()
    for s in SOURCES:
        h = s["handle"].lower()
        if h not in disabled:
            seen.add(h)
            items.append({
                "handle": s["handle"],
                "title": s.get("title") or s["handle"],
                "type": s.get("type", "telegram"),
                "url": s.get("url") or f"https://t.me/{s['handle']}",
            })
    for s in (extra_sources or []):
        if isinstance(s, dict) and s.get("handle"):
            h = str(s["handle"]).strip().lstrip("@")
            stype = (s.get("type") or "telegram").lower().strip()
            if h.lower() not in seen and h.lower() not in disabled:
                seen.add(h.lower())
                url = s.get("url") or (f"https://ble.ir/s/{h}" if stype == "bale" else f"https://t.me/{h}")
                items.append({"handle": h, "title": s.get("title") or h, "type": stype, "url": url})
    return items

TTL_SECONDS = 300        # how long one channel's posts stay fresh in memory
MAX_POSTS = 60           # retain and display up to 60 posts per channel
MAX_TEXT_CHARS = 4000    # a post longer than this is truncated with a trailing …

#: Telegram's own username shape (5–32 chars, may not end in _) — also the
#: guard that keeps a caller-supplied handle from becoming part of a URL.
HANDLE_RE = re.compile(r"^[A-Za-z0-9_-]{2,64}$")

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


BALE_FORBIDDEN_PATTERN = re.compile(
    r"(?<![\w؀-ۿ‌])"
    r"(ویدیو(?:[‌\s]?[ه|ی|های|هایی|ها|یی|ئی]*)?|"
    r"ویدئو(?:[‌\s]?[ه|ی|های|هایی|ها|یی|ئی]*)?|"
    r"شهبازی|"
    r"پادکست(?:[‌\s]?[ه|ی|های|هایی|ها]*)?|"
    r"پست\s+امروز|"
    r"پست(?:[‌\s]?[ه|ی|های|هایی|ها|ی]*)?|"
    r"ویس(?:[‌\s]?[ه|ی|های|هایی|ها|ی]*)?)"
    r"(?![\w؀-ۿ‌])",
    re.IGNORECASE
)


def has_bale_forbidden_words(title: str, text: str) -> tuple[bool, str]:
    """Check if title or text contains forbidden keywords for Bale news dispatching.

    Forbidden: ویدیو, شهبازی, پادکست, پست, پست امروز, ویس (with common Persian suffixes).
    Uses unicode boundaries to avoid false positives on 'سرویس', 'سوئیس', 'بن‌بست'.
    """
    full = f"{title or ''}\n{text or ''}"
    m = BALE_FORBIDDEN_PATTERN.search(full)
    if m:
        return True, m.group(0).strip()
    return False, ""



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


def _clean_bale_text(node, handle: str) -> str:
    """Clean text from Bale message node, decoding emoji and dropping self links, quotes, and reactions."""
    if node is None:
        return ""
    clone = BeautifulSoup(str(node), "html.parser")
    # Decompose reactions, meta info, previews, dates, views, and thumbnails
    for junk in clone.find_all(class_=re.compile(
        r"Reactions_|reaction|Info_|Preview_|NarrowBubble_senderInfo|Thumbnail_|MediaIcon_|date|view", re.I
    )):
        junk.decompose()
    for br in clone.find_all("br"):
        br.replace_with("\n")
    for img in clone.find_all("img", class_="emoji"):
        cp = img.get("data-codepoints")
        if cp:
            try:
                ch = "".join(chr(int(c, 16)) for c in cp.split("-"))
                img.replace_with(ch)
            except Exception:
                img.replace_with(" ")
        else:
            img.replace_with(" ")
    self_links = {f"https://ble.ir/{handle}".lower(), f"https://ble.ir/{handle}/".lower(),
                  f"https://ble.ir/s/{handle}".lower(), f"https://ble.ir/s/{handle}/".lower()}
    for a in clone.find_all("a", href=True):
        label = a.get_text(" ", strip=True)
        href = a["href"].strip()
        if href.lower() in self_links or f"@{handle.lower()}" == label.lower():
            a.decompose()
        elif href.startswith(("http://", "https://")):
            a.replace_with(f"{label} ({href})" if label and label != href else href)
        else:
            a.replace_with(label)
    lines = [ln.strip() for ln in clone.get_text().split("\n")]
    out, blanks = [], 0
    for ln in lines:
        cleaned_symbols = re.sub(r"[\d۰-۹\s.,]+", "", ln)
        if ln and not cleaned_symbols:
            continue
        blanks = blanks + 1 if not ln else 0
        if blanks <= 1:
            out.append(ln)
    return "\n".join(out).strip()


def parse_bale_channel_page(html: str, handle: str) -> list[dict]:
    """The newest-first posts of one ``ble.ir/s/<handle>`` page.

    Bale lays the page's messages window out OLDEST-first, so the
    collected rows are reversed before returning.
    """
    soup = BeautifulSoup(html, "html.parser")
    posts: list[dict] = []
    wrappers = soup.find_all(lambda tag: tag.name == "div" and (
        tag.get("data-sid") or (tag.get("class") and any("messageWrapper" in c for c in tag.get("class", [])))
    ))
    for wrap in wrappers[:MAX_POSTS]:
        wrap_copy = BeautifulSoup(str(wrap), "html.parser")

        sid = wrap_copy.find("div", attrs={"data-sid": True})
        sid_val = sid.get("data-sid") if sid else (wrap.get("data-sid") or "")
        msg_id = sid_val.split("-")[-1] if "-" in sid_val else (sid_val or f"{len(posts)+1}")

        time_el = wrap_copy.find(class_=re.compile(r"Info_date|date", re.I))
        when = time_el.get_text(strip=True) if time_el else ""

        views_el = wrap_copy.find(class_=re.compile(r"Info_ViewWrapper|Info_Text", re.I))
        views_text = views_el.get_text(strip=True) if views_el else ""

        media = None
        for kind in ("video", "photo", "document", "animation", "audio", "file"):
            if wrap_copy.find(class_=re.compile(rf"{kind}", re.I)):
                media = kind
                break

        # Strip reactions, metadata, and link preview cards from wrap_copy
        for junk in list(wrap_copy.find_all(class_=re.compile(
            r"Reactions_|reaction|Info_|LinkPreview|NarrowBubble_senderInfo|Thumbnail_|MediaIcon_|date|view", re.I
        ))):
            if not hasattr(junk, "attrs") or junk.attrs is None:
                continue
            classes = junk.get("class") or []
            # Keep text preview / headline blocks intact
            if not any("TextPreview" in c or "Text_text" in c for c in classes):
                junk.decompose()

        # Collect all text elements within the message (headline, preview, captions, body paragraphs)
        collected_parts = []
        for cand in wrap_copy.find_all(class_=re.compile(r"Text_text|Video_caption|Photo_caption|TextPreview")):
            cleaned = _clean_bale_text(cand, handle)
            if cleaned and cleaned not in collected_parts:
                if not any(cleaned in existing for existing in collected_parts):
                    collected_parts.append(cleaned)

        text = "\n\n".join(collected_parts).strip()
        if not text:
            text = _clean_bale_text(wrap_copy.find(class_=re.compile(r"Text_text")), handle)
        if not text and not media:
            continue

        posts.append({
            "id": msg_id,
            "url": f"https://ble.ir/s/{handle}",
            "title": _first_line(text),
            "text": text[:MAX_TEXT_CHARS],
            "time": when,
            "views": _parse_views(views_text),
            "media": media,
        })
    posts.reverse()
    return posts


def fetch_source(handle: str, refresh: bool = False, sources: list[dict] | None = None) -> dict:
    """One source: ``{handle, title, type, url, ok, error, fetched_at, posts}``.

    Supports both Telegram and Bale channels.
    """
    handle = (handle or "").strip().lstrip("@")
    reg = sources if sources is not None else SOURCES
    src = next((s for s in reg if s["handle"].lower() == handle.lower()), None)
    stype = (src.get("type") if src else "telegram") or "telegram"
    default_url = f"https://ble.ir/s/{handle}" if stype == "bale" else f"https://t.me/{handle}"
    out = {"handle": handle,
           "title": src["title"] if src else handle,
           "type": stype,
           "url": src.get("url") if src else default_url,
           "ok": False, "error": "", "fetched_at": 0.0, "posts": []}
    if not HANDLE_RE.match(handle):
        out["error"] = "invalid_handle"
        return out

    cache_key = f"{stype}:{handle.lower()}"
    now = time.time()
    if not refresh:
        hit = _CACHE.get(cache_key)
        if hit and now - hit[0] < TTL_SECONDS:
            return hit[1]

    fetch_url = f"https://ble.ir/s/{handle}" if stype == "bale" else f"https://t.me/s/{handle}"
    fresh_posts = []
    try:
        r = requests.get(fetch_url, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        if stype == "bale":
            fresh_posts = parse_bale_channel_page(r.text, handle)
        else:
            fresh_posts = parse_channel_page(r.text, handle)
        if fresh_posts:
            try:
                import database
                database.save_channel_posts(handle, fresh_posts, chan_type=stype, max_keep=MAX_POSTS)
            except Exception:
                pass
    except Exception as e:                  # one dead channel, not a dead section
        out["error"] = f"{type(e).__name__}: {e}"[:200]

    stored_posts = []
    try:
        import database
        stored_posts = database.get_channel_posts(handle, limit=MAX_POSTS)
    except Exception:
        pass

    final_posts = stored_posts if stored_posts else fresh_posts
    if final_posts:
        out.update(ok=True, fetched_at=now, posts=final_posts)
        _CACHE[cache_key] = (now, out)
        return out
    elif out["error"]:
        return out
    else:
        out.update(ok=True, fetched_at=now, posts=[])
        _CACHE[cache_key] = (now, out)
        return out


def fetch_all(refresh: bool = False, extra_sources: list[dict] | None = None, deleted_sources: list[str] | None = None) -> list[dict]:
    """Every source in SOURCES (and any extra_sources), excluding deleted_sources."""
    reg = get_sources(extra_sources, deleted_sources)
    return [fetch_source(s["handle"], refresh=refresh, sources=reg) for s in reg]
