"""Article full-text extraction — the fallback ladder for `/api/article`.

Moved here verbatim from `app.py` (see the phase-3 commit and its
`git diff --color-moved` proof): the JSON-LD and paywall parsers, the Google-News
and publisher resolvers, the Jina / Wayback / Reddit / inline-payload rungs, the
content caches and the warm loop.

`app.py` keeps the routes; this module owns the ladder. The objects it shares with
`app.py` (the caches, their locks, `STATE`, the logger, the outbound `HEADERS`)
stay owned by `app.py` and are attached once through `bind_shared_state` — the same
objects, never copies, so a test that touches `app.CONTENT_CACHE` or `app.STATE`
still steers this code, and the two modules cannot disagree about what is cached
or which lock protects it. `translate_paragraphs` / `save_cache` are the real
imports from `translate`, i.e. the same functions `app.py` holds.
"""
import base64
import json
import re
import threading
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from translate import save_cache, translate_paragraphs

# ---------------------------------------------------------------------------
# State owned by app.py, attached at import time by `bind_shared_state`.
# ---------------------------------------------------------------------------
# Globals rather than parameters, so that the moved code below could stay a
# verbatim move. They are the SAME objects app.py holds — never copies.
STATE = None                  # dict    — articles/archive the warm loop reads
STATE_LOCK = None             # lock    — guards STATE
CONTENT_CACHE = None          # dict    — article id -> extracted body
FA_CONTENT_CACHE = None       # dict    — article id -> Persian paragraphs
_CONTENT_LOCK = None          # lock    — guards CONTENT_CACHE
_FA_CONTENT_LOCK = None       # lock    — guards FA_CONTENT_CACHE
_ART_INFLIGHT = None          # set     — extraction/translation jobs in flight
HEADERS = None                # dict    — outbound request headers
_JINA_KEY = None              # str     — optional Jina Reader key
log = None                    # callable — app.py's logger
_channel_board = None         # callable — idea board, read by the warm loop


def bind_shared_state(shared: dict) -> None:
    """Attach the objects that stay owned by app.py (called once, at import)."""
    globals().update(shared)


# ---------------------------------------------------------------------------
# Full-text extraction
# ---------------------------------------------------------------------------
_JUNK_LINE = (
    "subscribe", "newsletter", "sign up", "sign in", "log in", "cookie",
    "advertisement", "advertise with us", "follow us", "share this", "read more:",
    "read more", "related articles", "terms of service", "privacy policy",
    "all rights reserved", "disclaimer", "download our app", "watch now",
    "click here", "join our", "topics:", "tags:", "منتشر شده در",
)
_MIN_PARA = 60


def _paragraphs_from(node):
    out = []
    for p in node.find_all(["p", "h2", "h3"]):
        txt = p.get_text(" ", strip=True)
        txt = " ".join(txt.split())
        if len(txt) < _MIN_PARA:
            continue
        low = txt.lower()
        if any(j in low for j in _JUNK_LINE) and len(txt) < 220:
            continue
        out.append(txt)
    return out


def _jsonld_body(soup):
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "{}")
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                body = node.get("articleBody")
                if isinstance(body, str) and len(body) > 300:
                    return body
                for v in node.values():
                    if isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(node, list):
                stack.extend(node)
    return None


from urllib.parse import quote_plus, unquote, urlparse


_BLOCKED_HOSTS = ("news.google.", "googleusercontent", "www.google.", "google.com",
                  "bing.com", "duckduckgo.com", "news.yahoo.com", "msn.com",
                  "facebook.com", "twitter.com", "x.com", "instagram.com")
_STOPWORDS = {"the", "a", "an", "of", "to", "in", "on", "for", "and", "as", "at",
              "with", "is", "are", "its", "it", "after", "over", "up", "down", "new",
              "says", "will", "could", "than", "from", "by", "be", "has", "have"}


def _title_tokens(title: str):
    words = re.findall(r"[A-Za-z0-9$%]+", (title or "").lower())
    return [w for w in words if len(w) > 2 and w not in _STOPWORDS]


def _bounded(fn, seconds, *args, **kwargs):
    """Run fn(*args) in a worker thread and give up after `seconds` (→ None).

    The paywall ladder is a *sequence* of tries whose socket timeouts run 15–45s,
    so one hostile host used to hold the article modal open for over a minute.
    Bounding it keeps behaviour identical whenever the ladder finishes in time.
    """
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        return pool.submit(fn, *args, **kwargs).result(timeout=seconds)
    except Exception:
        return None
    finally:
        pool.shutdown(wait=False)


def _looks_like_match(url: str, title: str, publisher: str = "") -> bool:
    """Only accept a search hit that is plausibly *this* story."""
    try:
        parts = urlparse(url)
        host = parts.netloc.lower()
    except Exception:
        return False
    if any(b in host for b in _BLOCKED_HOSTS):
        return False
    tokens = _title_tokens(title)
    if not tokens:
        return False
    # The path is the only thing that can tie a URL to a headline. A bare
    # domain or a section page (`…/symbols/BTCUSD/`, `…/economy-news/`) carries
    # no headline words, and accepting it on a publisher-host match alone used
    # to hand the modal a completely unrelated page as "the article".
    path = unquote(parts.path).lower()
    hits = sum(1 for t in tokens if t.strip("$%") and t.strip("$%") in path)
    # A substantive hit is a real headline word, not a bare ticker — otherwise
    # `…/symbols/btcusd/` matches any story whose headline opens "BTC/USD:".
    strong = sum(1 for t in tokens if len(t) >= 5 and t in path)
    if hits == 0 or strong == 0:
        return False
    slug = re.sub(r"[^a-z0-9]", "", (publisher or "").lower())
    stem = slug[3:] if slug.startswith("the") and len(slug) > 6 else slug
    if len(stem) > 3 and (stem in host.replace("-", "").replace(".", "")):
        return True
    return hits >= max(3, int(len(tokens) * 0.34))


# ---------------------------------------------------------------------------
# Google News links: ids are encrypted, the page is a JS shell, and Google
# never redirects - so the URL has to be *exchanged*. Every article page
# carries a signature (`data-n-a-sg`) and a timestamp (`data-n-a-ts`); posting
# those to the public batchexecute endpoint returns the publisher's address.
# Free, no key, ~300ms. Hits are cached on disk because an id never changes.
# ---------------------------------------------------------------------------
NEWSLINK_FILE = Path(__file__).parent / ".news_links.json"
_NEWSLINK_CACHE = {}
_NEWSLINK_LOCK = threading.Lock()


def _load_newslinks():
    try:
        if NEWSLINK_FILE.exists():
            data = json.loads(NEWSLINK_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                _NEWSLINK_CACHE.update({k: v for k, v in data.items() if isinstance(v, str)})
    except Exception:
        pass


def _save_newslinks():
    try:
        tmp = NEWSLINK_FILE.with_suffix(".tmp")
        with _NEWSLINK_LOCK:
            snap = dict(_NEWSLINK_CACHE)
        tmp.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
        tmp.replace(NEWSLINK_FILE)
    except Exception:
        pass


def _gn_article_id(url: str):
    m = re.search(r"/articles/([^?/#]+)", url or "")
    return m.group(1) if m else None


def _gn_offline_id(art_id: str):
    """Some (older) ids are base64 of a small protobuf with the URL in clear;
    those need no network round trip at all."""
    if not art_id or not art_id.startswith("CBMi"):
        return None
    try:
        raw = base64.urlsafe_b64decode(art_id + "=" * (-len(art_id) % 4))
        for m in re.finditer(rb"https?://[\x20-\x7e]{10,400}", raw):
            cand = m.group(0).decode("utf-8", "replace")
            cand = re.split(r"[\x00-\x1f]", cand)[0]
            if "news.google.com" not in cand and "." in cand.split("//")[-1][:40]:
                return cand
    except Exception:
        return None
    return None


def decode_google_news_url(art_id: str, timeout: int = 8):
    """Swap an encrypted Google News article id for the publisher URL."""
    if not art_id:
        return None
    try:
        page = requests.get(f"https://news.google.com/rss/articles/{art_id}",
                            headers=HEADERS, timeout=timeout)
        html = page.text or ""
    except Exception:
        return None
    sg = re.search(r'data-n-a-sg="([^"]+)"', html)
    ts = re.search(r'data-n-a-ts="([^"]+)"', html)
    if not (sg and ts):
        return None
    inner = ("[\"garturlreq\",[[\"X\",\"X\",[\"X\",\"X\"],null,null,1,1,"
             "\"US:en\",null,1,null,null,null,null,null,0,1],\"X\",\"X\",1,"
             "[1,1,1],1,1,null,0,0,null,0],\"%s\",%s,\"%s\"]"
             % (art_id, ts.group(1), sg.group(1)))
    payload = json.dumps([[ ["Fbv4je", inner] ]])
    url = None
    for kwargs in ({"params": {"f.req": payload}}, {"data": {"f.req": payload}}):
        if url:
            break
        try:
            r = requests.post("https://news.google.com/_/DotsSplashUi/data/batchexecute",
                              headers=HEADERS, timeout=timeout, **kwargs)
            body = r.text or ""
        except Exception:
            continue
        for part in body.split("\n\n"):
            try:
                rows = json.loads(part)
            except Exception:
                continue
            for row in (rows if isinstance(rows, list) else []):
                if (isinstance(row, list) and len(row) > 2 and row[0] == "wrb.fr"
                        and isinstance(row[2], str)):
                    try:
                        cand = json.loads(row[2])[1]
                    except Exception:
                        continue
                    if isinstance(cand, str) and cand.startswith("http"):
                        url = cand
                        break
        if not url:
            m = re.search(r'"(https?://(?!news\.google\.com)[^"\\]{12,})"', body)
            if m:
                url = m.group(1)
    if not url:
        return None
    url = (url.replace("\\u003d", "=").replace("\\u0026", "&")
              .replace("\\/", "/").strip())
    if not url.startswith("http") or "news.google.com" in url or "google.com/url" in url:
        return None
    return url


def resolve_news_url(url: str, title: str = "", publisher: str = "", timeout: int = 8):
    """Google News wrapper → the publisher's own address (or None).
    Exchange first (exact, fast), then the search-engine lookup, then nothing -
    the caller falls back to the headline it already has."""
    if "news.google.com" not in (url or ""):
        return None
    art_id = _gn_article_id(url)
    if not art_id:
        return None
    with _NEWSLINK_LOCK:
        hit = _NEWSLINK_CACHE.get(art_id)
    if hit:
        return hit
    real = _gn_offline_id(art_id) or decode_google_news_url(art_id, timeout=timeout)
    if not real:
        real = resolve_publisher_url(title, publisher)
    if real:
        with _NEWSLINK_LOCK:
            _NEWSLINK_CACHE[art_id] = real
        _save_newslinks()
    return real


_load_newslinks()


def resolve_publisher_url(title: str, publisher: str = "", timeout: int = 15):
    """
    Google News article ids are encrypted, so `news.google.com/rss/articles/...`
    cannot be unwrapped. We look the headline up on public search engines and
    only accept a hit that plausibly matches this story (host = publisher name,
    or enough headline words inside the URL path).
    """
    if not title:
        return None
    query = f'"{title}"' + (f' {publisher}' if publisher else "")
    candidates = []

    # 1) Bing — result links carry the real URL base64-encoded in `u=a1...`
    try:
        r = requests.get("https://www.bing.com/search", params={"q": query},
                         headers=HEADERS, timeout=timeout)
        for tok in re.findall(r"u=a1([A-Za-z0-9_\-]+)", r.text)[:14]:
            try:
                dec = base64.urlsafe_b64decode(tok + "=" * (-len(tok) % 4))
                dec = dec.decode("utf-8", "replace")
                if dec.startswith("http"):
                    candidates.append(dec)
            except Exception:
                continue
    except Exception as e:
        log(f"  x bing lookup failed: {e}")

    # 2) DuckDuckGo (rate limited, best effort)
    if not candidates:
        for attempt in ("lite", "html"):
            try:
                if attempt == "lite":
                    r = requests.get("https://lite.duckduckgo.com/lite/",
                                     params={"q": query}, headers=HEADERS, timeout=timeout)
                else:
                    r = requests.post("https://html.duckduckgo.com/html/",
                                      data={"q": query}, headers=HEADERS, timeout=timeout)
                got = [unquote(u) for u in re.findall(r"uddg=([^\"&]+)", r.text)]
                candidates.extend(got)
                if got:
                    break
            except Exception:
                continue

    for c in candidates:
        if _looks_like_match(c, title, publisher):
            return c
    return None


# ---------------------------------------------------------------------------
# deep article extraction — when the publisher's page is a JS shell, an IP
# block or a paywall, these relay sources usually still have the full text.
# All free, no keys. Ordered by quality of output.
# ---------------------------------------------------------------------------

def _jina_reader_text(url: str):
    """r.jina.ai renders the page in a headless browser and returns clean
    text/markdown — the single most effective free fix for JS-rendered news
    *and* for hosts that answer 403 to this machine's IP.

    Headers matter more than they should: r.jina.ai sits behind Cloudflare and
    challenges the app's own `HEADERS` UA (and any Chrome-looking one) with a
    403 challenge page, while the crawler UA sails through — measured 3/3 hosts
    that were 403 for every other rung (cryptopotato 576 words, ccn 1168,
    robinhood 342). One retry absorbs the flaky challenge; with MOHMD_JINA_KEY
    set the authenticated route is used instead.
    """
    _hdrs = {"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; "
                           "+http://www.google.com/bot.html)",
             "Accept": "text/plain", "Accept-Language": "en-US,en;q=0.9"}
    if _JINA_KEY:
        _hdrs["Authorization"] = f"Bearer {_JINA_KEY}"
    for attempt in range(2):
        try:
            r = requests.get(f"https://r.jina.ai/{url}", headers=_hdrs, timeout=25)
        except Exception:
            r = None
        if r is not None and r.status_code == 200 and len(r.text) >= 300:
            return r.text
        if r is not None and r.status_code not in (403, 429, 503):
            break
        time.sleep(0.8 * (attempt + 1))
    return None


def _proxy_html(url: str, template: str, timeout: float = 3.0):
    """Fetch the page through a raw XML/HTML proxy (beats IP/UA blocks)."""
    from urllib.parse import quote_plus
    try:
        r = requests.get(template.format(q=quote_plus(url)),
                         headers=HEADERS, timeout=timeout)
        if r.status_code == 200 and len(r.text) > 500:
            return r.text
    except Exception:
        pass
    return None


def _wayback_html(url: str):
    """Closest Wayback Machine snapshot of the article page."""
    try:
        r = requests.get("https://archive.org/wayback/available",
                         params={"url": url}, headers=HEADERS, timeout=8)
        snap = ((r.json() or {}).get("archived_snapshots") or {}).get("closest") or {}
        if snap.get("url"):
            rr = requests.get(snap["url"], headers=HEADERS, timeout=20)
            if rr.status_code == 200 and len(rr.text) > 500:
                return rr.text
    except Exception:
        pass
    return None


def _ua_fetch(url: str, headers: dict):
    """Direct fetch with a crawler UA (Googlebot/Bingbot often see the full
    article on sites that serve browsers a paywall stub)."""
    try:
        r = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        if r.status_code == 200 and len(r.text) > 500:
            return r.text
    except Exception:
        pass
    return None


def _archive_ph_html(url: str):
    """Fetch the latest archive.ph (archive.today) snapshot of a URL.
    archive.ph mirrors often have the full paywalled article text."""
    from urllib.parse import quote_plus
    try:
        # archive.ph returns the latest snapshot page with a redirect
        r = requests.get(
            f"https://archive.ph/newest/{url}",
            headers={**HEADERS, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"},
            timeout=15, allow_redirects=True)
        if r.status_code == 200 and len(r.text) > 500:
            return r.text
    except Exception:
        pass
    return None


def _reddit_session(url: str):
    """GET the page and, when reddit answers with its proof-of-work shell, solve
    it (two rounds) so the session holds the `rdt` cookie. Returns (session,
    last_response)."""
    s = requests.Session()
    s.headers.update(HEADERS)
    r = s.get(url, timeout=15, allow_redirects=True)
    for _ in range(4):
        # ~60 kB is comfortably above the shell and far below any real page
        if r.status_code != 200 or len(r.content) > 60000:
            break
        m = re.search(r'await\(async e=>e\+e\)\("([0-9a-f]{8,})"\)', r.text)
        if not m:
            break
        tok = re.search(r'name="jsc_token" value="([^"]*)"', r.text)
        r = s.get(r.url, params={"solution": m.group(1) * 2,
                                 "js_challenge": "1",
                                 "jsc_token": tok.group(1) if tok else "",
                                 "jsc_orig_r": ""}, timeout=15)
    return s, r


def _reddit_html(url: str):
    """reddit.com hands non-browser clients a tiny JS interstitial (an ~8 kB
    shell whose only job is `<form name="solution">` + a proof-of-work nonce)
    instead of the post. The "work" is the nonce doubled, and reddit normally
    asks for two consecutive rounds before it sets the `rdt` cookie and serves
    the real ~500 kB page — so two extra GETs buy the full post with no browser
    and no third-party relay. Measured: 8407 B challenge → 554 kB post."""
    try:
        s, r = _reddit_session(url)
        if r.status_code == 200 and len(r.text) > 500:
            return r.text
    except Exception:
        pass
    return None


def _looks_like_paragraph(s: str) -> bool:
    """Reject the shapes a body extractor picks up by accident: a bare media URL,
    a line of markup, a run of emoji/labels."""
    if len(s) < _MIN_PARA:
        return False
    if s.startswith(("http://", "https://")) and " " not in s[:80]:
        return False
    letters = sum(1 for c in s if c.isalpha() or c.isspace() or c in ".,;:!?-'\"()[]/&%")
    return letters / len(s) >= 0.75


def _reddit_paras(text: str, prefix: str = "") -> list:
    out = []
    for blk in re.split(r"\n\s*\n", text or ""):
        blk = " ".join(blk.split())
        if not _looks_like_paragraph(blk):
            continue
        out.append((prefix + blk) if prefix else blk)
    return out


def _pullpush_selftext(post_id: str):
    """pullpush.io mirrors reddit submissions — including selftext that moderation
    has since `[removed]`, which the live .json endpoint refuses to hand over."""
    try:
        r = requests.get("https://api.pullpush.io/reddit/search/submission/",
                         params={"ids": post_id}, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            rows = (r.json() or {}).get("data") or []
            if rows and isinstance(rows[0], dict):
                st = rows[0].get("selftext") or ""
                if len(st.split()) >= 30:
                    return st
    except Exception:
        pass
    return ""


def _reddit_external(post: dict, url: str):
    """A link post carries no prose of its own — the article it points at *is*
    the content, so the ladder has to follow it."""
    try:
        if post.get("is_self"):
            return None
        ext = (post.get("url") or "").strip()
        if not ext.startswith(("http://", "https://")):
            return None
        host = urlparse(ext).netloc.lower()
        if "reddit." in host or "redd.it" in host:
            return None
        return ext
    except Exception:
        return None


def _reddit_content(url: str):
    """A reddit post is a shell plus an XHR: the body never ships in the HTML the
    ladder parses, which is why every thread came back as ~22 words of title and
    metadata. The `.json` endpoint (same session, fetched *after* the PoW cookie)
    returns selftext and comment tree directly; pullpush fills the gap where the
    post body was removed."""
    try:
        s, _ = _reddit_session(url)
        j = s.get(url.rstrip("/") + ".json?raw_json=1&limit=12",
                  headers={**HEADERS, "Accept": "application/json"}, timeout=15)
        if j.status_code != 200 or not j.text.lstrip().startswith("["):
            return None
        data = j.json()
        if not isinstance(data, list) or not data:
            return None
        post = (((data[0].get("data") or {}).get("children")) or [{}])[0].get("data") or {}
        paras = _reddit_paras(post.get("selftext") or "")
        wc = sum(len(p.split()) for p in paras)
        if wc < 60:
            m = re.search(r"/comments/([a-z0-9]+)", url)
            archived = _pullpush_selftext(m.group(1)) if m else ""
            got = _reddit_paras(archived)
            if sum(len(p.split()) for p in got) > wc:
                paras = got
                wc = sum(len(p.split()) for p in got)
        # a text-less post (image / link / removed body) is a *discussion*:
        # the thread's comments are the only prose the page has
        if wc < 120 and len(data) > 1:
            for c in ((data[1].get("data") or {}).get("children")) or []:
                if c.get("kind") != "t1":
                    continue
                cd = c.get("data") or {}
                body = (cd.get("body") or "").strip()
                if body in ("[removed]", "[deleted]"):
                    continue
                paras += _reddit_paras(body, prefix=f"u/{cd.get('author') or '?'}: ")
                wc = sum(len(p.split()) for p in paras)
                if wc >= 400 or len(paras) >= 8:
                    break
        if not paras:
            return {"paragraphs": [], "word_count": 0, "partial": False,
                    "title": post.get("title") or "", "site": "reddit",
                    "published": "", "url": url, "resolved_url": url,
                    "external_url": _reddit_external(post, url),
                    "via": "reddit-json-empty"}
        return {"paragraphs": paras[:40], "word_count": wc, "partial": wc < 120,
                "title": post.get("title") or "", "site": "reddit",
                "published": "", "url": url, "resolved_url": url,
                "external_url": _reddit_external(post, url),
                "via": "reddit-json"}
    except Exception:
        return None


def _parse_reader_text(text: str):
    """Parse r.jina.ai output: 'Title: …' header + 'Markdown Content:' body."""
    title = ""
    body = text
    m = re.search(r"^Title:\s*(.+)$", text, re.M)
    if m:
        title = m.group(1).strip()
    m = re.search(r"^Markdown Content:\s*$", text, re.M)
    if m:
        body = text[m.end():]
    # markdown → plain lines, keep prose-looking ones
    lines = []
    for ln in body.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith(("#", "!", ">", "---", "|", "```")):
            continue
        ln = re.sub(r"^([-*+]\s+|\d+\.\s+)", "", ln)          # bullet / numbering
        ln = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", ln)   # ![alt](url) → gone
        ln = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", ln)   # [txt](url) → txt
        ln = re.sub(r"[*_`]{1,3}", "", ln)
        ln = " ".join(ln.split())
        if len(ln) < 55:
            continue
        # a link that survived the strip (nested markdown, bare url in text) is
        # navigation, not prose — the nav bullets of a page used to read as a
        # paragraph of image labels
        if "](" in ln or "![" in ln:
            continue
        letters = sum(1 for c in ln if c.isalpha() or c.isspace())
        if letters / len(ln) < 0.72:
            continue
        low = ln.lower()
        if any(j in low for j in _JUNK_LINE) and len(ln) < 220:
            continue
        lines.append(ln)
    return title, lines


# ---------------------------------------------------------------------------
# Inline app payloads. The page an SPA *serves* is a shell — the article lives
# in the JSON it hydrates from (Next.js `__NEXT_DATA__`, Nuxt/Redux initial
# state, the React flight stream `self.__next_f.push`). Reading the payload
# turns a 28-word stub into the real document with no headless browser, and it
# survives every proxy rung of the ladder because the data ships with the HTML.
# ---------------------------------------------------------------------------
_PAYLOAD_KEYS = (
    "articlebody", "longdescription", "fulldescription", "articletext",
    "bodytext", "articlecontent", "htmlbody", "contenthtml",
)


def _looks_like_prose(s: str) -> bool:
    """True for a string that reads as an article paragraph, not as markup,
    CSS, a label from an i18n table or a URL."""
    if not isinstance(s, str):
        return False
    s = s.strip()
    if len(s) < 200 or len(s.split()) < 30:
        return False
    low = s[:400].lower()
    if any(j in low for j in ("function(", "=>", "window.", "undefined",
                              ".css", ".js", "http://", "https://t")):
        return False
    if s.startswith(("http://", "https://") ) and " " not in s[:60]:
        return False
    sentences = sum(s.count(x) for x in (". ", "? ", "! "))
    ok = sum(1 for c in s if c.isalpha() or c.isspace() or
             c in ".,;:!?-'\"()[]$/&%0123456789%")
    return sentences >= 2 and ok / len(s) >= 0.8


def _iter_strings(node, path=()):
    """Yield (key, string) for every string in a parsed JSON document."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _iter_strings(v, path + (str(k),))
    elif isinstance(node, list):
        for v in node:
            yield from _iter_strings(v, path)
    elif isinstance(node, str):
        yield (path[-1] if path else ""), node


def _payload_candidates(html: str):
    """All string content the inline scripts of the document carry."""
    out = []
    for m in re.finditer(r"<script([^>]*)>(.*?)</script>", html or "", re.S | re.I):
        attrs, body = m.group(1), m.group(2)
        if not body.strip():
            continue
        raw = body.lstrip()
        if "json" in attrs.lower() or "__next_data__" in attrs.lower() or raw[:1] in ("{", "["):
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = None
            if parsed is not None:
                out.extend(_iter_strings(parsed))
                continue
        # React Server flight / Redux / Nuxt: JS, not JSON — pull the string
        # literals out of it (they are JSON-escaped, so json.loads decodes them)
        if any(k in body for k in ("self.__next_f", "__INITIAL_STATE__", "__NUXT__")):
            for sm in re.finditer(r'"((?:[^"\\]|\\.){160,})"', body):
                try:
                    s = json.loads('"' + sm.group(1) + '"')
                except Exception:
                    continue
                if isinstance(s, str):
                    out.append(("", s))
    return out


def _payload_blocks(texts) -> list:
    """Turn chosen payload strings into clean paragraphs."""
    out, seen = [], set()
    for t in texts:
        if not isinstance(t, str):
            continue
        for ln in t.splitlines() or [t]:
            ln = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", ln).strip()
            ln = " ".join(ln.split())
            if not _looks_like_paragraph(ln):
                continue
            k = ln[:120]
            if k in seen:
                continue
            seen.add(k)
            out.append(ln)
    return out


def _payload_paragraphs(html: str) -> list:
    """Salvage the article from the page's own hydration JSON.

    Tier 1 trusts the keys a CMS uses for the article itself (first hit per
    key, so a 'related articles' list of the same field never leaks in). Tier
    2 — only when tier 1 stayed thin — trusts the *shape*: a field repeated
    many times is a block list, otherwise the first prose-looking string.
    """
    cands = _payload_candidates(html)
    if not cands:
        return []
    picked, seen = [], set()
    for key, s in cands:
        k = (key or "").lower()
        if k in _PAYLOAD_KEYS and k not in seen and len(s.strip()) >= _MIN_PARA:
            seen.add(k)
            picked.append(s)
    blocks = _payload_blocks(picked)
    if sum(len(p.split()) for p in blocks) >= 100:
        return blocks

    prose = [((key or "").lower(), s) for key, s in cands if _looks_like_prose(s)]
    if not prose:
        return blocks
    counts = {}
    for k, _ in prose:
        counts[k] = counts.get(k, 0) + 1
    top = max(counts, key=counts.get)
    run = [s for k, s in prose if counts[top] >= 3 and k == top]
    if not run:
        run = [prose[0][1]]
    return _payload_blocks(run) or blocks


def _parse_article_html(html: str, url: str, publisher=None, via="direct"):
    """Full DOM/JSON-LD/app-payload extraction from one HTML document. Adds a
    statistical 'densest <p> container' pass so unknown layouts still yield the
    body. The JSON passes run *before* <script> is decomposed — they used to
    run after it, which silently made the JSON-LD pass dead code."""
    result = {"paragraphs": [], "word_count": 0, "partial": True,
              "title": "", "site": "", "published": "", "url": url,
              "resolved_url": url, "via": via}
    soup = BeautifulSoup(html, "html.parser")

    result["site"] = (soup.find("meta", property="og:site_name") or {}).get("content", "") or ""
    result["title"] = ((soup.find("meta", property="og:title") or {}).get("content")
                      or (soup.title.get_text(strip=True) if soup.title else ""))
    result["published"] = ((soup.find("meta", property="article:published_time") or {})
                           .get("content", "") or "")

    # the JSON passes need the <script> tags, so they run before the strip below
    body = _jsonld_body(soup)
    payload = _payload_paragraphs(html)

    for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                     "iframe", "noscript", "form", "button"]):
        tag.decompose()

    paras = []
    if body:
        paras = [p.strip() for p in body.split("\n") if len(p.strip()) > _MIN_PARA]
    if payload and len("".join(payload)) > len("".join(paras)):
        paras = payload

    if len(paras) < 3:
        for sel in (".entry-content", ".post-content", ".article-content", ".article-body",
                    ".story-body", ".post-body", ".content-body", ".rich-text",
                    "#content", "article", "main"):
            el = soup.select_one(sel)
            if not el:
                continue
            got = _paragraphs_from(el)
            if len("".join(got)) > len("".join(paras)):
                paras = got
            if len(paras) >= 3:
                break

    if len(paras) < 3:
        best = []
        for art in soup.find_all("article"):
            got = _paragraphs_from(art)
            if len("".join(got)) > len("".join(best)):
                best = got
        if best:
            paras = best

    # statistical pass: whichever single parent element holds the most <p> text
    # is almost certainly the article body — works with any class naming
    if len(paras) < 3:
        buckets = {}
        for p in soup.find_all("p"):
            parent = p.parent
            if parent is None or parent.name in ("body", "html", "[document]"):
                continue
            txt = " ".join(p.get_text(" ", strip=True).split())
            if len(txt) < _MIN_PARA:
                continue
            buckets.setdefault(id(parent), [parent, []])[1].append(txt)
        if buckets:
            _, texts = max(buckets.values(), key=lambda v: sum(map(len, v[1])))
            if sum(map(len, texts)) > sum(map(len, paras)):
                paras = texts

    if len(paras) < 2:
        got = _paragraphs_from(soup)
        # never *replace* a real body with nothing: a page whose only prose is
        # JSON-LD / an app payload has no qualifying <p> at all, and the old
        # unconditional overwrite threw the article away
        if sum(map(len, got)) > sum(map(len, paras)):
            paras = got

    # last-resort: the meta description (thin, but beats an empty modal)
    if not paras:
        for prop in ("og:description", "description"):
            m = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            if m and m.get("content"):
                paras = [m["content"].strip()]
                break

    seen, clean = set(), []
    for p in paras:
        k = p[:120]
        if k in seen:
            continue
        seen.add(k)
        clean.append(p)

    result["paragraphs"] = clean[:150]
    result["word_count"] = sum(len(p.split()) for p in result["paragraphs"])
    result["partial"] = result["word_count"] < 120
    return result


def _search_snippet_paragraphs(title, url=None, publisher=None):
    """Extract full content paragraphs from search engine snippets when the publisher blocks scrapers."""
    if not title:
        return []
    paragraphs = []
    seen = set()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    queries = []
    host = urlparse(url).netloc.lower() if url else ""
    clean_host = host.replace("www.", "") if host else ""
    if clean_host and "google" not in clean_host:
        queries.append(f'site:{clean_host} "{title}"')
        words = title.split()[:8]
        if len(words) >= 4:
            queries.append(f'site:{clean_host} "{" ".join(words)}"')
    queries.append(f'"{title}"')
    clean_title = re.sub(r'[\'\"\–\—\-:]', ' ', title)
    queries.append(" ".join(clean_title.split()[:10]))

    for q in queries:
        try:
            r = requests.get("https://www.bing.com/search", params={"q": q}, headers=headers, timeout=5)
            if r.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(r.text, "html.parser")
                for p in soup.select("p, .b_caption p, .b_snippet"):
                    txt = p.get_text(strip=True)
                    txt = re.sub(r'^(?:\d+\s+(?:hours?|days?|mins?|weeks?|months?)\s+ago|[A-Z][a-z]{2}\s+\d+,\s+\d{4})[·\s\-]*(?:[·])?\s*', '', txt)
                    txt = re.sub(r'(?:Read more|More|\.\.\.|…|\[\.\.\.\])\s*$', '', txt).strip()
                    if len(txt) > 35 and txt not in seen:
                        seen.add(txt)
                        paragraphs.append(txt)
        except Exception:
            pass

        try:
            r = requests.post("https://html.duckduckgo.com/html/", data={"q": q}, headers=headers, timeout=5)
            if r.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(r.text, "html.parser")
                for el in soup.select(".result__snippet"):
                    txt = el.get_text(strip=True)
                    txt = re.sub(r'(?:Read more|More|\.\.\.|…|\[\.\.\.\])\s*$', '', txt).strip()
                    if len(txt) > 35 and txt not in seen:
                        seen.add(txt)
                        paragraphs.append(txt)
        except Exception:
            pass

        if len(paragraphs) >= 4:
            break

    return paragraphs


def fetch_article_content(url, title=None, publisher=None):
    """
    Best-effort *complete* article text, through a ladder of 6+ sources:
      direct fetch → news_bypass (paywall hosts) → r.jina.ai (renders JS) →
      2 raw proxies → Wayback Machine snapshot → Google-News redirect resolution → search snippets.
    The best result (most words) wins; stops early once a source returns a
    convincing body (≥250 words).
    """
    if not url or not isinstance(url, str) or not url.startswith(('http://', 'https://')):
        return {
            "paragraphs": [],
            "word_count": 0,
            "partial": True,
            "title": "",
            "url": url or "",
            "method": "none"
        }
    host = (urlparse(url).netloc.lower() if url else "")
    from news_bypass import smart_extract
    _PAYWALL_HOSTS = ("bloomberg.", "wsj.", "ft.com", "reuters.", "marketwatch.",
                      "nytimes.", "washingtonpost.", "seekingalpha.", "economist.",
                      "forbes.", "investing.com", "businessinsider.")

    # 0) resolve Google News encrypted links to the real publisher URL first
    if "news.google.com" in url:
        resolved = resolve_news_url(url, title or "", publisher or "")
        if resolved:
            url = resolved

    # 0b) nothing could unwrap the id:
    if "news.google.com" in url:
        snip_paras = _search_snippet_paragraphs(title, url, publisher)
        if snip_paras:
            wc = sum(len(p.split()) for p in snip_paras)
            return {"paragraphs": snip_paras[:150], "word_count": wc, "partial": wc < 120,
                    "title": title or "", "site": publisher or "", "published": "",
                    "url": url, "resolved_url": None, "via": "google-news-snippets"}
        return {"paragraphs": [], "word_count": 0, "partial": True,
                "title": title or "", "site": publisher or "", "published": "",
                "url": url, "resolved_url": None, "via": "google-news-unresolved",
                "error": "google-news id could not be resolved to a publisher url"}

    best = None

    def _consider(res):
        nonlocal best
        if not res or not res.get("paragraphs"):
            return False
        if best is None or res["word_count"] > best["word_count"]:
            best = res
        return best["word_count"] >= 250          # convincing body → stop

    # 0c) reddit blocks plain clients with a solvable JS interstitial, and its
    #     body lives behind an XHR — the session solves the challenge once and
    #     then reads the .json endpoint (selftext + comments) directly.
    if "reddit." in host:
        rc = _bounded(_reddit_content, 22, url)
        if rc:
            if rc.get("paragraphs") and _consider(rc):
                return best
            # link post with (almost) no prose of its own → the target article
            ext = rc.get("external_url")
            if ext and (best is None or best["word_count"] < 120):
                inner = _bounded(fetch_article_content, 15, ext, title or "", publisher or "")
                if inner and inner.get("paragraphs"):
                    _consider({**inner, "via": "reddit→" + str(inner.get("via"))})
                    if best["word_count"] >= 250:
                        return best
        rh = _bounded(_reddit_html, 14, url)
        if rh:
            res = _parse_article_html(rh, url, publisher, via="reddit-jsc")
            if _consider(res):
                return best

    # 1) paywalled outlet? the tested bypass ladder goes first (bounded — see
    #    _bounded; unbounded it could hold the modal for a minute or more).
    #    bypass_ran stops step 4 from calling the *same* ladder with the same
    #    arguments a second time — it had already timed out once.
    bypass_ran = False
    if any(h in host for h in _PAYWALL_HOSTS):
        bypass_ran = True
        bp = _bounded(smart_extract, 25, url, title or "", publisher or "") or {}
        if bp.get("paragraphs"):
            _consider({**bp, "site": publisher or "", "published": "",
                       "resolved_url": bp.get("resolved_url") or url,
                       "via": "bypass:" + (bp.get("bypass") or "")})

    # 2) direct fetch + full DOM parse
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
        if resp.status_code == 200 and len(resp.text) > 500:
            res = _parse_article_html(resp.text, url, publisher, via="direct")
            res["resolved_url"] = resp.url
            if _consider(res):
                return best
    except Exception:
        pass

    # 2b) trafilatura — the best open-source article extractor (Apache-2.0,
    #     key-less): readability + justext fallbacks built in. One second on
    #     live feeds where the DOM pass returned thin text, so it goes right
    #     before the parallel deep burst and also re-tries the paywall hosts.
    def _trafilatura_rung():
        try:
            import trafilatura
            r = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
            if r.status_code != 200 or len(r.text) < 500:
                return None
            txt = trafilatura.extract(r.text, include_comments=False,
                                      include_tables=False, favor_recall=True,
                                      url=url) or ""
            paras = [p.strip() for p in txt.splitlines() if len(p.strip()) > 40]
            if not paras:
                return None
            wc = sum(len(p.split()) for p in paras)
            return {"paragraphs": paras[:150], "word_count": wc, "partial": wc < 120,
                    "title": title or "", "site": publisher or "", "published": "",
                    "url": url, "resolved_url": url, "via": "trafilatura"}
        except ImportError:
            return None
        except Exception:
            return None

    tr = _bounded(_trafilatura_rung, 16)
    if tr:
        if _consider(tr):
            return best
        # even a thin trafilatura body usually beats nothing; keep it as `best`

    # 3) deep sources — all fetched IN PARALLEL (worst case ≈ slowest source,
    #    not the sum), so a thin article never stalls the modal for minutes
    _GBOT = {**HEADERS, "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"}
    _BBOT = {**HEADERS, "User-Agent": "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"}
    deep_sources = (
        ("snippets",   lambda: "\n\n".join(_search_snippet_paragraphs(title, url, publisher)), "text"),
        ("jina",       lambda: _jina_reader_text(url),            "text"),
        ("allorigins", lambda: _proxy_html(url, "https://api.allorigins.win/raw?url={q}"), "html"),
        ("codetabs",   lambda: _proxy_html(url, "https://api.codetabs.com/v1/proxy?quest={q}"), "html"),
        ("wayback",    lambda: _wayback_html(url),                "html"),
        # many publishers hand the FULL page to search crawlers while giving
        # browsers the paywall stub — two more parallel getters, zero extra wait
        ("googlebot",  lambda: _ua_fetch(url, _GBOT),             "html"),
        ("bingbot",    lambda: _ua_fetch(url, _BBOT),             "html"),
        # archive.ph mirrors often bypass paywalls completely
        ("archiveph",  lambda: _archive_ph_html(url),             "html"),
        # Google webcache (separate from the google-cache in news_bypass)
        ("gcache",     lambda: _proxy_html(url, "https://webcache.googleusercontent.com/search?q=cache:{q}&strip=1", 12.0), "html"),
    )
    deep_results = []

    def _run_deep(item):
        label, getter, kind = item
        try:
            return label, kind, getter()
        except Exception:
            return label, kind, None

    from concurrent.futures import (ThreadPoolExecutor, as_completed,
                                    TimeoutError as FuturesTimeout)
    # as_completed (not pool.map): map() yields in *submission* order, so a fast
    # source that finished in 1s still waited behind a 20s one. Here the first
    # convincing body ends the wait and the stragglers are abandoned.
    #
    # DEEP_BUDGET is a hard ceiling on the whole ladder. Without it the modal
    # blocked for ~10s on sites where the fast sources have already answered
    # "nothing" and the only things still in flight are two raw proxies that
    # hang until their timeout and then return no body at all.
    DEEP_BUDGET = 18
    pool = ThreadPoolExecutor(max_workers=8)
    try:
        futures = [pool.submit(_run_deep, s) for s in deep_sources]
        for fut in as_completed(futures, timeout=DEEP_BUDGET):
            try:
                label, kind, text = fut.result()
            except Exception:
                continue
            if not text:
                continue
            try:
                if kind == "text":
                    jtitle, jparas = _parse_reader_text(text)
                    wc = sum(len(p.split()) for p in jparas)
                    res = {"paragraphs": jparas[:150], "word_count": wc,
                           "partial": wc < 120, "title": jtitle,
                           "site": publisher or "", "published": "",
                           "url": url, "resolved_url": url, "via": label}
                else:
                    res = _parse_article_html(text, url, publisher, via=label)
            except Exception:
                continue
            deep_results.append(res)
            if _consider(res):
                return best          # convincing body — stop waiting on the rest
    except FuturesTimeout:
        pass                         # budget spent — take the best we already have
    finally:
        pool.shutdown(wait=False)
    for res in deep_results:
        if _consider(res):
            return best

    # 4) still thin/empty → the paywall ladder as the final attempt
    #    (only for real paywalled outlets or when we have NOTHING — otherwise
    #    it adds a minute of retries for a page that is simply short)
    paywalled = any(h in host for h in _PAYWALL_HOSTS)
    if not bypass_ran and (best is None or (best["word_count"] < 120 and paywalled)):
        bp = _bounded(smart_extract, 25, url, title or "", publisher or "") or {}
        if bp.get("paragraphs"):
            _consider({**bp, "site": (best or {}).get("site") or publisher or "",
                       "published": (best or {}).get("published", ""),
                       "url": url, "via": "bypass:" + (bp.get("bypass") or "")})

    # 5) Search engine snippet extraction (the ultimate safety net for Cloudflare / JS / bot blocks)
    if best is None or best.get("word_count", 0) < 100:
        snip_paras = _search_snippet_paragraphs(title, url, publisher)
        if snip_paras:
            wc = sum(len(p.split()) for p in snip_paras)
            res = {
                "paragraphs": snip_paras[:150],
                "word_count": wc,
                "partial": wc < 120,
                "title": title or "",
                "site": publisher or "",
                "published": "",
                "url": url,
                "resolved_url": url,
                "via": "search-snippets"
            }
            _consider(res)

    if best:
        best["title"] = best.get("title") or title or ""
        return best
    return {"paragraphs": [], "word_count": 0, "partial": True,
            "title": title or "", "site": publisher or "", "published": "",
            "url": url, "resolved_url": None, "via": "none", "error": "all sources empty"}


THIN_RETRY_SECONDS = 300.0     # lead-only / empty body retry window


def _content_fresh(hit) -> bool:
    """A thin (paywalled/JS-blocked) result is NOT final: it is re-run by the
    background job every few minutes so cached stubs heal themselves. The window
    used to be 30 minutes, which meant a publisher that came back (or a rung that
    started working) was not noticed for half an hour."""
    if not hit:
        return False
    if hit.get("via") == "pending":
        return False
    return not (hit.get("partial") and time.time() - hit.get("_at", 0) > THIN_RETRY_SECONDS)


def _schedule_article(art, priority=False) -> bool:
    """Kick the (up to ~15s) extraction ladder off-thread. Returns True when a
    job was started, False when there is nothing to do."""
    key = art.get("id")
    if not key:
        return False
    with _CONTENT_LOCK:
        hit = CONTENT_CACHE.get(key)
    if key in _ART_INFLIGHT or _content_fresh(hit):
        return False
    if not priority and len(_ART_INFLIGHT) >= 20:          # cap concurrent background jobs
        return False
    _ART_INFLIGHT.add(key)

    def _job():
        try:
            content = fetch_article_content(
                art.get("link"), title=art.get("title"),
                publisher=art.get("source_name") if art.get("via") else None)
            content["_at"] = time.time()
            with _CONTENT_LOCK:
                old = CONTENT_CACHE.get(key)
                if (old and content.get("word_count", 0) <= old.get("word_count", 0)
                        and not content.get("error")):
                    old["_at"] = time.time()
                    content = old
                else:
                    CONTENT_CACHE[key] = content
            if content.get("via") != "pending":
                try:
                    from database import save_body
                    save_body(key, content)
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            _ART_INFLIGHT.discard(key)

    threading.Thread(target=_job, daemon=True).start()
    return True


def _schedule_fa(art, content) -> bool:
    """Translate the extracted body off-thread (one Google round trip ≈ 5s)."""
    aid = art.get("id")
    if not aid:
        return False
    fk = aid + "|fa"
    with _FA_CONTENT_LOCK:
        cached_fa = FA_CONTENT_CACHE.get(fk)
    if fk in _ART_INFLIGHT or cached_fa:
        return False
    paras = (content or {}).get("paragraphs") or []
    if not paras:
        return False
    _ART_INFLIGHT.add(fk)

    def _job():
        try:
            fa = translate_paragraphs(paras[:60])
            save_cache()
            with _FA_CONTENT_LOCK:
                FA_CONTENT_CACHE[fk] = fa
            if fa:
                try:
                    from database import save_body
                    save_body(fk, fa)
                except Exception:
                    pass
        except Exception as e:
            log(f"  x content translation failed: {e}")
        finally:
            _ART_INFLIGHT.discard(fk)

    threading.Thread(target=_job, daemon=True).start()
    return True


def article_content_cached(art, want_fa=False, priority=False):
    """Never blocks the request: returns the cached body when we have one and
    starts the extraction ladder in the background when we do not. The
    returned stub carries `pending: True` so the API can tell the client to
    poll again — that is what removed the 8-15 s spinner on every click."""
    aid = art.get("id")
    if not aid:
        return {
            "paragraphs": [], "word_count": 0, "partial": True,
            "title": "", "site": "", "published": "",
            "url": "", "resolved_url": None, "via": "none",
            "error": "missing_id", "pending": False,
        }
    with _CONTENT_LOCK:
        hit = CONTENT_CACHE.get(aid)
    if _content_fresh(hit):
        return hit
    _schedule_article(art, priority=priority)
    stub = dict(hit) if hit else {
        "paragraphs": [], "word_count": 0, "partial": True,
        "title": art.get("title") or "", "site": "", "published": "",
        "url": art.get("link"), "resolved_url": None, "via": "none",
        "error": None,
    }
    stub["pending"] = True
    return stub


def warm_article_bodies(limit: int = 150):
    """Pre-extract Content Ideas and the newest articles in parallel so opening
    any news card is 100% instant without ever showing a waiting spinner."""
    try:
        from concurrent.futures import ThreadPoolExecutor

        # 1. Warm all Content Ideas first (operator's primary focus)
        board = _channel_board() or {}
        board_items = list(board.get("items") or [])
        board_arts = [i.get("article") or dict(i) for i in board_items if i.get("id") and i.get("link")]

        # 2. Warm newest live articles
        with STATE_LOCK:
            arts = [a for a in (STATE.get("articles") or [])
                    if a.get("id") and a.get("link")]
        arts.sort(key=lambda a: -(a.get("published_ts") or 0))

        candidates = []
        seen = set()
        for a in (board_arts + arts[:limit]):
            aid = a.get("id")
            if aid and aid not in seen:
                seen.add(aid)
                with _CONTENT_LOCK:
                    cached = CONTENT_CACHE.get(aid)
                if not _content_fresh(cached):
                    candidates.append(a)

        def _extract(a):
            try:
                aid = a.get("id")
                content = fetch_article_content(
                    a.get("link"), title=a.get("title"),
                    publisher=a.get("source_name") if a.get("via") else None
                )
                if content and content.get("paragraphs"):
                    content["_at"] = time.time()
                    with _CONTENT_LOCK:
                        CONTENT_CACHE[aid] = content
                    try:
                        from database import save_body
                        save_body(aid, content)
                    except Exception:
                        pass
            except Exception:
                pass

        if candidates:
            with ThreadPoolExecutor(max_workers=10) as executor:
                list(executor.map(_extract, candidates))
    except Exception as e:
        log(f"  x body pre-warm stopped: {e}")
