"""social_signals.py — what the audience is actually watching, right now.

The content studio needs a demand signal: not "is this news true" (the corpus
and its credibility score already answer that) but "does anyone care". This
module is that half, built from three sources that answered keyless from this
host (verified 2026-09-29):

  * **YouTube search** — ``youtube.com/results`` ships the whole result set as
    ``ytInitialData``, including view counts and a relative publish age. Views
    over age gives **views per hour**, which is the closest thing to the
    ranking signal a public endpoint can hand you. A free Data API key is used
    instead when one is configured.
  * **Telegram channel previews** — ``t.me/s/<channel>`` renders the last posts
    with their view counts. For a Persian-speaking financial audience this is
    the most honest reach proxy available, and it needs no login.
  * **Reddit** — RSS for the subreddits, with upvote/comments resolved through
    the Arctic-Shift archive by ``reddit_scores`` (already in this project).

Instagram is deliberately absent: every keyless path redirects to a login wall
and its oEmbed needs an app token, so the only honest source is the official
Graph API — used here *only* when a token is configured, and only for the
account's own insights (a feedback loop, not surveillance of others).

Everything is cached with a last-good value (``.content_studio_cache.json``), so
a blocked or rate-limited upstream degrades to a stale reading with its
provider named, never to an exception in a request handler. Run
``python social_signals.py`` to refresh everything once and print a status
table.
"""

from __future__ import annotations

import json
import os
import queue
import re
import threading
import time

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 20
CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          ".content_studio_cache.json")
HIST_MAX = 240
HIST_MIN_GAP = 600

# A starter list of demand sources, all editable from the settings tab. Kept
# small on purpose: every channel is a request per refresh, and a long list is
# how a scraper gets rate-limited.
DEFAULT_TELEGRAM_CHANNELS = [
    ("akhbarefori", "خبر فوری"),
    ("bourse24", "بورس ۲۴"),
    ("eghtesadonline", "اقتصاد آنلاین"),
    ("donya_eqtesad", "دنیای اقتصاد"),
    ("TehranStockExchange", "بورس تهران"),
]
DEFAULT_REDDIT_SUBS = ["wallstreetbets", "CryptoCurrency", "investing", "economics", "gold"]
DEFAULT_YT_QUERIES_FA = ["قیمت طلا", "قیمت دلار", "قیمت بیت کوین", "بورس تهران", "قیمت نفت"]
DEFAULT_YT_QUERIES_EN = ["gold price today", "bitcoin price", "oil price", "fed rate decision"]

# filter codes for youtube search (verified): video-only, and this-week
_YT_FILTER_VIDEO = "EgIQAQ%3D%3D"
_YT_FILTER_WEEK = "CAISBAgCEAE%3D"


# ─────────────────────────── text/telemetry parsing ───────────────────────────

_FA_DIGITS = {ord(c): str(i) for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹")}
_AR_DIGITS = {ord(c): str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")}


def ascii_digits(s: str) -> str:
    """Persian/Arabic-Indic digits -> ASCII, and the Persian separators too."""
    if not s:
        return ""
    return (str(s).translate(_FA_DIGITS).translate(_AR_DIGITS)
            .replace("٬", ",").replace("٫", "."))


_AGE_UNITS = {
    "second": 1 / 3600.0, "sec": 1 / 3600.0, "s": 1 / 3600.0, "ثانیه": 1 / 3600.0,
    "minute": 1 / 60.0, "min": 1 / 60.0, "m": 1 / 60.0, "دقیقه": 1 / 60.0,
    "hour": 1.0, "hr": 1.0, "h": 1.0, "ساعت": 1.0,
    "day": 24.0, "d": 24.0, "روز": 24.0,
    "week": 168.0, "w": 168.0, "هفته": 168.0,
    "month": 730.0, "mo": 730.0, "ماه": 730.0,
    "year": 8760.0, "y": 8760.0, "سال": 8760.0,
}


def parse_age_hours(text: str):
    """'17h ago' / '۲ ساعت پیش' / 'Streamed 3 days ago' -> hours (float) or None."""
    if not text:
        return None
    s = ascii_digits(text).lower().replace("\u200f", "").replace("\u200e", "")
    m = re.search(r"(\d+(?:\.\d+)?)\s*([a-z\u0600-\u06FF]+)", s)
    if not m:
        return None
    try:
        n = float(m.group(1))
    except ValueError:
        return None
    unit = m.group(2).strip()
    if unit not in _AGE_UNITS:
        # the compact forms ('7mo', '2y') and anything unknown
        for key in ("mo", "y", "w", "d", "h", "m", "s"):
            if unit.startswith(key):
                unit = key
                break
    factor = _AGE_UNITS.get(unit)
    if factor is None:
        return None
    return max(0.0, n * factor)


def parse_count(text: str):
    """'2,317 views' / '۲٬۳۱۷ بازدید' / '22.7K' / '1.2M' -> float or None."""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    s = ascii_digits(str(text)).replace(",", "").replace(" ", "")
    m = re.search(r"(\d+(?:\.\d+)?)\s*([kmb])?", s, re.I)
    if not m:
        return None
    try:
        n = float(m.group(1))
    except ValueError:
        return None
    mult = {"k": 1e3, "m": 1e6, "b": 1e9}.get((m.group(2) or "").lower(), 1.0)
    return n * mult


def parse_yt_initial(html: str) -> list:
    """Pull the video list out of a youtube results/feed page.

    Recursive walk rather than a path expression: YouTube moves the renderers
    around between builds, and a path that breaks silently is worse than none.
    """
    if not html:
        return []
    m = re.search(r"(?:var\s+)?ytInitialData\s*=\s*(\{.*?\});", html, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except ValueError:
        return []
    out, seen = [], set()

    def walk(node):
        if isinstance(node, dict):
            for key, kind in (("videoRenderer", "video"), ("reelItemRenderer", "short")):
                if key in node and isinstance(node[key], dict):
                    rec = _yt_record(node[key], kind)
                    if rec and rec["id"] not in seen:
                        seen.add(rec["id"])
                        out.append(rec)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)
    return out


def _runs_text(node) -> str:
    if not isinstance(node, dict):
        return ""
    if node.get("simpleText"):
        return str(node["simpleText"])
    runs = node.get("runs") or []
    return "".join(str(r.get("text", "")) for r in runs if isinstance(r, dict))


def _yt_record(v: dict, kind: str):
    vid = v.get("videoId")
    if not vid:
        return None
    views_raw = _runs_text(v.get("viewCountText")) or _runs_text(v.get("shortViewCountText"))
    age_raw = _runs_text(v.get("publishedTimeText"))
    owner = v.get("ownerText") or v.get("longBylineText") or {}
    owner_runs = owner.get("runs") or [{}]
    channel = str(owner_runs[0].get("text", "")) if owner_runs else ""
    channel_id = None
    try:
        channel_id = (((owner_runs[0].get("navigationEndpoint") or {})
                       .get("browseEndpoint") or {}).get("browseId"))
    except Exception:
        channel_id = None
    views = parse_count(views_raw)
    age = parse_age_hours(age_raw)
    return {
        "id": vid,
        "kind": kind,
        "title": _runs_text(v.get("title")),
        "channel": channel,
        "channel_id": channel_id,
        "views": views,
        "age_hours": age,
        "views_per_hour": (views / age) if (views is not None and age and age > 0.2) else None,
        "duration": _runs_text(v.get("lengthText")),
        "url": f"https://www.youtube.com/watch?v={vid}",
        "raw_age": age_raw,
    }


_TAG_RE = re.compile(r"<[^>]+>")


def _balanced_inner(html: str, tag_class: str) -> str:
    """Inner HTML of the first div carrying `tag_class`, div-depth aware.

    A lazy `(.*?)</div>` stops at the first nested close and silently truncates
    the post text — the exact reason this parser exists instead of a one-liner.
    """
    m = re.search(r'<div[^>]*class="[^"]*' + re.escape(tag_class) + r'[^"]*"[^>]*>', html)
    if not m:
        return ""
    start = m.end()
    depth = 1
    for tok in re.finditer(r"<div\b|</div>", html[start:]):
        if tok.group(0).startswith("</"):
            depth -= 1
            if depth == 0:
                return html[start:start + tok.start()]
        else:
            depth += 1
    return html[start:]


def parse_telegram_channel(html: str, channel: str = "") -> list:
    """Last posts of a public channel: text, views, timestamp.

    Messages are delimited by their own `data-post` attribute: splitting on the
    `tgme_widget_message` class instead cuts at every inner element (bubble,
    text, views) and produces hundreds of fragments with nothing in them.
    """
    if not html:
        return []
    posts = []
    marks = [(m.start(), m.group(1)) for m in re.finditer(r'data-post="([^"]+)"', html)]
    for i, (pos, post_id) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(html)
        block = html[pos:end]
        views = None
        mv = re.search(r'tgme_widget_message_views">([^<]+)<', block)
        if mv:
            views = parse_count(mv.group(1))
        iso = None
        mt = re.search(r'<time datetime="([^"]+)"', block)
        if mt:
            iso = mt.group(1)
        body = _TAG_RE.sub(" ", _balanced_inner(block, "tgme_widget_message_text"))
        body = re.sub(r"\s+", " ", body).strip()
        if not (post_id or body):
            continue
        age_hours = None
        if iso:
            try:
                clean = iso.replace("Z", "+00:00")
                from datetime import datetime, timezone
                dt = datetime.fromisoformat(clean)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                age_hours = max(0.0, (time.time() - dt.timestamp()) / 3600.0)
            except Exception:
                age_hours = None
        posts.append({
            "channel": channel,
            "post_id": post_id,
            "text": body,
            "views": views,
            "age_hours": age_hours,
            "views_per_hour": (views / age_hours) if (views is not None and age_hours and age_hours > 0.2) else None,
            "url": f"https://t.me/{post_id}" if post_id else "",
        })
    return posts


def parse_reddit_feed(xml: str, sub: str = "") -> list:
    """Reddit's RSS: link, title, updated. Scores come from reddit_scores."""
    if not xml:
        return []
    out = []
    for entry in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        link = re.search(r'<link[^>]*href="([^"]+)"', entry)
        title = re.search(r"<title>(.*?)</title>", entry, re.S)
        updated = re.search(r"<updated>(.*?)</updated>", entry, re.S)
        if not (link and title):
            continue
        cleaned = _TAG_RE.sub("", title.group(1))
        cleaned = (cleaned.replace("&amp;", "&").replace("&lt;", "<")
                   .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'"))
        age_hours = None
        if updated:
            try:
                from datetime import datetime, timezone
                dt = datetime.fromisoformat(updated.group(1).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                age_hours = max(0.0, (time.time() - dt.timestamp()) / 3600.0)
            except Exception:
                age_hours = None
        out.append({"sub": sub, "title": cleaned.strip(), "link": link.group(1),
                    "age_hours": age_hours, "score": None, "comments": None,
                    "score_per_hour": None})
    return out


# ─────────────────────────── cache + background refresh ───────────────────────────

_CACHE: dict[str, dict] = {}
_HIST: dict[str, list] = {}
_LOCK = threading.RLock()
_QUEUE: "queue.Queue[str]" = queue.Queue()
_WORKER: threading.Thread | None = None


def _load_cache():
    global _CACHE, _HIST
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as fh:
            blob = json.load(fh)
        if isinstance(blob, dict):
            with _LOCK:
                _CACHE = {k: v for k, v in (blob.get("cache") or {}).items()
                          if isinstance(v, dict)}
                _HIST = {k: v for k, v in (blob.get("hist") or {}).items()
                         if isinstance(v, list)}
    except (OSError, ValueError):
        pass


def _save_cache():
    try:
        tmp = CACHE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"cache": _CACHE, "hist": _HIST, "saved_ts": time.time()},
                      fh, ensure_ascii=False)
        os.replace(tmp, CACHE_PATH)
    except OSError:
        pass


def push_hist(name: str, value, ts: float | None = None):
    if value is None:
        return
    ts = float(ts or time.time())
    with _LOCK:
        series = _HIST.setdefault(name, [])
        if series and abs(series[-1][0] - ts) < HIST_MIN_GAP:
            series[-1] = [ts, value]
        else:
            series.append([ts, value])
        if len(series) > HIST_MAX:
            del series[:-HIST_MAX]


def hist(name: str, limit: int | None = None) -> list:
    with _LOCK:
        series = [list(p) for p in _HIST.get(name, [])]
    return series[-limit:] if limit else series


def hist_change(name: str, seconds: float):
    series = hist(name)
    if len(series) < 2:
        return None, None
    now = series[-1][0]
    inside = [(ts, v) for ts, v in series if now - ts <= seconds and v is not None]
    if len(inside) < 2:
        return None, None
    first, last = inside[0][1], inside[-1][1]
    if not first:
        return None, None
    return (last - first), (last - first) / abs(first) * 100.0


def value(key: str):
    with _LOCK:
        entry = _CACHE.get(key)
    return entry.get("value") if entry else None


def snapshot(key: str) -> dict:
    with _LOCK:
        entry = _CACHE.get(key)
    label, _ttl, _fn, source = SOURCES[key]
    if not entry:
        return {"value": None, "ts": None, "age": None, "error": "never fetched",
                "source": source, "label": label}
    return {"value": entry.get("value"), "ts": entry.get("ts"),
            "age": (time.time() - entry["ts"]) if entry.get("ts") else None,
            "error": entry.get("error"), "source": source, "label": label}


def snapshot_all(force: bool = False) -> dict:
    if force:
        refresh_all()
    return {k: snapshot(k) for k in SOURCES}


def _is_stale(key: str) -> bool:
    with _LOCK:
        entry = _CACHE.get(key)
    if not entry or not entry.get("ts"):
        return True
    return (time.time() - entry["ts"]) >= SOURCES[key][1]


def _schedule(key: str):
    try:
        _QUEUE.put_nowait(key)
    except queue.Full:                                   # pragma: no cover
        pass
    global _WORKER
    if _WORKER is None or not _WORKER.is_alive():
        _WORKER = threading.Thread(target=_worker, name="studio-signals", daemon=True)
        _WORKER.start()


def cached(key: str, *, force: bool = False):
    """Last good value; schedules a background refresh when it went stale."""
    if key not in SOURCES:
        raise KeyError(key)
    if force or _is_stale(key):
        _schedule(key)
    return value(key)


def refresh_all(timeout: float = 180.0) -> bool:
    deadline = time.time() + timeout
    for key in SOURCES:
        if time.time() > deadline:
            return False
        _run(key)
    return True


def _worker():
    while True:
        key = _QUEUE.get()
        if key is None:
            return
        try:
            _run(key)
        except Exception:                                # pragma: no cover
            pass


def _run(key: str):
    _label, _ttl, fn, _source = SOURCES[key]
    try:
        fresh = fn()
        if fresh is None:
            raise RuntimeError("provider returned nothing")
        with _LOCK:
            _CACHE[key] = {"ts": time.time(), "value": fresh, "error": None}
        _save_cache()
    except Exception as exc:
        with _LOCK:
            entry = _CACHE.get(key) or {"value": None, "ts": None}
            entry["error"] = f"{type(exc).__name__}: {exc}"[:200]
            _CACHE[key] = entry
        _save_cache()


_load_cache()


# ─────────────────────────── config helpers ───────────────────────────

def _cfg(config: dict | None) -> dict:
    cfg = ((config or {}).get("content_studio") or {})
    return cfg if isinstance(cfg, dict) else {}


def _list_cfg(cfg: dict, key: str, default):
    raw = cfg.get(key)
    if isinstance(raw, list) and raw:
        out = []
        for item in raw:
            if isinstance(item, str) and item.strip():
                out.append((item.strip(), item.strip()))
            elif isinstance(item, (list, tuple)) and item:
                out.append((str(item[0]).strip(), str(item[1]).strip() if len(item) > 1 else str(item[0])))
        return out or list(default)
    return list(default)


def _get(url, *, params=None, headers=None, expect="text", timeout=TIMEOUT):
    hdrs = {"User-Agent": UA, "Accept-Language": "fa,en;q=0.8"}
    if headers:
        hdrs.update(headers)
    r = requests.get(url, params=params, headers=hdrs, timeout=timeout)
    r.raise_for_status()
    return r.json() if expect == "json" else r.text


# ─────────────────────────── providers ───────────────────────────

_CONFIG: dict = {}


def set_config(config: dict | None):
    """app.py hands the live CONFIG in once per cycle (avoids an import cycle)."""
    global _CONFIG
    _CONFIG = config or {}


def _yt_queries(cfg: dict):
    fa = _list_cfg(cfg, "youtube_queries_fa", [(q, q) for q in DEFAULT_YT_QUERIES_FA])
    en = _list_cfg(cfg, "youtube_queries_en", [(q, q) for q in DEFAULT_YT_QUERIES_EN])
    return [(q, "fa") for q, _l in fa] + [(q, "en") for q, _l in en]


def _yt_api_search(query: str, key: str, max_results: int = 12):
    """Official path when a free Data API key is configured."""
    search = _get("https://www.googleapis.com/youtube/v3/search",
                  params={"part": "snippet", "q": query, "type": "video", "key": key,
                          "maxResults": max_results, "order": "viewCount",
                          "publishedAfter": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                          time.gmtime(time.time() - 7 * 86400))},
                  expect="json", timeout=25)
    ids = [i["id"]["videoId"] for i in (search.get("items") or [])
           if i.get("id", {}).get("videoId")]
    if not ids:
        return []
    stats = _get("https://www.googleapis.com/youtube/v3/videos",
                 params={"part": "statistics,snippet,contentDetails", "id": ",".join(ids[:20]),
                         "key": key}, expect="json", timeout=25)
    out = []
    for item in stats.get("items") or []:
        sn = item.get("snippet") or {}
        st = item.get("statistics") or {}
        views = parse_count(st.get("viewCount"))
        published = sn.get("publishedAt")
        age = None
        if published:
            try:
                from datetime import datetime, timezone
                dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                age = max(0.0, (time.time() - dt.timestamp()) / 3600.0)
            except Exception:
                age = None
        out.append({
            "id": item.get("id"), "kind": "video", "title": sn.get("title") or "",
            "channel": sn.get("channelTitle") or "", "channel_id": sn.get("channelId"),
            "views": views, "age_hours": age,
            "views_per_hour": (views / age) if (views is not None and age and age > 0.2) else None,
            "duration": (item.get("contentDetails") or {}).get("duration") or "",
            "url": f"https://www.youtube.com/watch?v={item.get('id')}",
            "raw_age": published or "",
        })
    return out


def _youtube_engagement(video_id: str):
    """Likes/views via the keyless returnyoutubedislike API (best effort)."""
    try:
        data = _get("https://returnyoutubedislikeapi.com/votes",
                    params={"videoId": video_id}, expect="json", timeout=12)
    except Exception:
        return None
    views = parse_count(data.get("viewCount"))
    likes = parse_count(data.get("likes"))
    return {"views": views, "likes": likes,
            "like_rate": (likes / views * 100.0) if (likes and views) else None,
            "date_created": data.get("dateCreated")}


def fetch_youtube() -> dict:
    cfg = _cfg(_CONFIG)
    key = str(cfg.get("youtube_key") or "").strip()
    out = {"queries": {}, "videos": [], "mode": "data-api" if key else "keyless"}
    errors = []
    for query, lang in _yt_queries(cfg):
        vids = []
        try:
            if key:
                vids = _yt_api_search(query, key)
            if not vids:
                # hl/gl matter more than they look: without them a Persian or
                # English query comes back salted with unrelated-language
                # channels, and the whole board loses its audience signal
                html = _get("https://www.youtube.com/results",
                            params={"search_query": query, "sp": _YT_FILTER_WEEK,
                                    "hl": "fa" if lang == "fa" else "en",
                                    "gl": "IR" if lang == "fa" else "US",
                                    "persist_gl": "1", "persist_hl": "1"},
                            timeout=25)
                vids = parse_yt_initial(html)
        except Exception as exc:
            errors.append(f"{query}: {exc}"[:120])
            continue
        vids = [v for v in vids if v.get("views") is not None][:12]
        for v in vids:
            v["query"], v["lang"] = query, lang
        out["queries"][query] = {"lang": lang, "videos": vids}
        out["videos"].extend(vids)
        best = max([v["views_per_hour"] or 0 for v in vids] or [0])
        push_hist(f"yt:{query}", best)
    # engagement for the handful of videos that matter most this cycle
    top = sorted([v for v in out["videos"] if v.get("views_per_hour")],
                 key=lambda v: -(v["views_per_hour"] or 0))[:4]
    for v in top:
        eng = _youtube_engagement(v["id"])
        if eng:
            v.update({k: val for k, val in eng.items() if val is not None})
            if eng.get("views"):
                v["views"] = eng["views"]
    out["queries"]["_errors"] = {"lang": "", "videos": [], "errors": errors}
    if not out["videos"]:
        raise RuntimeError("; ".join(errors)[:180] or "no videos parsed")
    out["generated_ts"] = time.time()
    return out


def fetch_telegram() -> dict:
    cfg = _cfg(_CONFIG)
    channels = _list_cfg(cfg, "telegram_channels", DEFAULT_TELEGRAM_CHANNELS)
    out = {"channels": [], "posts": [], "errors": []}
    for username, label in channels[:12]:
        try:
            html = _get(f"https://t.me/s/{username}", timeout=20)
            posts = parse_telegram_channel(html, username)
        except Exception as exc:
            out["errors"].append(f"{username}: {exc}"[:120])
            continue
        for p in posts:
            p["label"] = label
        views = [p["views"] for p in posts if p.get("views")]
        out["channels"].append({"channel": username, "label": label, "posts": len(posts),
                                "median_views": sorted(views)[len(views) // 2] if views else None})
        out["posts"].extend(posts)
        rates = [p["views_per_hour"] for p in posts if p.get("views_per_hour")]
        if rates:
            push_hist(f"tg:{username}", sorted(rates)[len(rates) // 2])
    if not out["posts"]:
        raise RuntimeError("; ".join(out["errors"])[:180] or "no telegram posts parsed")
    out["generated_ts"] = time.time()
    return out


def fetch_reddit() -> dict:
    cfg = _cfg(_CONFIG)
    subs = [s for s, _l in _list_cfg(cfg, "reddit_subs", [(s, s) for s in DEFAULT_REDDIT_SUBS])][:10]
    out = {"subs": [], "posts": [], "errors": []}
    for sub in subs:
        try:
            xml = _get(f"https://www.reddit.com/r/{sub}/.rss", timeout=20)
            posts = parse_reddit_feed(xml, sub)
        except Exception as exc:
            out["errors"].append(f"{sub}: {exc}"[:120])
            continue
        out["posts"].extend(posts)
        out["subs"].append({"sub": sub, "posts": len(posts)})
    if not out["posts"]:
        raise RuntimeError("; ".join(out["errors"])[:180] or "no reddit posts parsed")
    try:                       # upvotes come from the archive, with its own cache
        import reddit_scores
        now = time.time()
        # attach_scores gates its fetches on published_ts: a probe without one
        # is skipped as "too old" and the scores silently never arrive
        probe = [{"id": p["link"], "link": p["link"],
                  "published_ts": now - (p.get("age_hours") or 0) * 3600.0}
                 for p in out["posts"]]
        kept, _dropped = reddit_scores.attach_scores(probe, max_age_hours=48)
        scores = {a["link"]: a for a in kept}
        for p in out["posts"]:
            rec = scores.get(p["link"])
            if rec:
                p["score"] = rec.get("reddit_score")
                p["comments"] = rec.get("reddit_comments")
                if p["score"] and p.get("age_hours"):
                    p["score_per_hour"] = p["score"] / max(0.5, p["age_hours"])
    except Exception as exc:
        out["errors"].append(f"scores: {exc}"[:120])
    out["generated_ts"] = time.time()
    return out


def fetch_instagram() -> dict:
    """Own-account insights via the official Graph API — only when configured.

    There is no keyless path: instagram.com answers a login wall to every
    public JSON endpoint, so this provider is opt-in by design and reads only
    the account whose token it is given.
    """
    cfg = _cfg(_CONFIG)
    token = str(cfg.get("instagram_token") or "").strip()
    user_id = str(cfg.get("instagram_user_id") or "").strip()
    if not token or not user_id:
        raise RuntimeError("instagram token/user id not configured")
    data = _get(f"https://graph.facebook.com/v20.0/{user_id}/media",
                params={"fields": "id,caption,media_type,timestamp,permalink,like_count,comments_count",
                        "limit": 12, "access_token": token}, expect="json", timeout=25)
    posts = []
    for item in data.get("data") or []:
        ts = None
        if item.get("timestamp"):
            try:
                from datetime import datetime, timezone
                dt = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
                ts = dt.timestamp()
            except Exception:
                ts = None
        posts.append({"id": item.get("id"), "caption": item.get("caption") or "",
                      "media_type": item.get("media_type"), "permalink": item.get("permalink"),
                      "likes": item.get("like_count"), "comments": item.get("comments_count"),
                      "ts": ts})
    return {"posts": posts, "generated_ts": time.time()}


SOURCES: dict[str, tuple] = {
    # key          label                     ttl    fetcher            source
    "youtube":   ("تقاضای ویدیویی یوتیوب",    1200,  fetch_youtube,     "YouTube"),
    "telegram":  ("کانال‌های تلگرام",          600,   fetch_telegram,    "Telegram"),
    "reddit":    ("نزدیک‌ترین ساب‌ردیت‌ها",     1800,  fetch_reddit,      "Reddit"),
    "instagram": ("اینستاگرام (حساب خودم)",   3600,  fetch_instagram,   "Instagram Graph API"),
}


def warm(config: dict | None = None, force: bool = False):
    set_config(config if config is not None else _CONFIG)
    for key in SOURCES:
        cached(key, force=force)


def all_signals() -> dict:
    return {
        "youtube": value("youtube"),
        "telegram": value("telegram"),
        "reddit": value("reddit"),
        "instagram": value("instagram"),
    }


if __name__ == "__main__":                                # pragma: no cover
    print("refreshing %d providers …" % len(SOURCES))
    refresh_all()
    for key, meta in snapshot_all().items():
        ok = "ok " if meta["value"] else "ERR"
        age = f"{meta['age']:.0f}s" if meta["age"] is not None else "-"
        print(f"  {ok} {key:<10} {meta['label']:<28} age={age:<6} {meta['error'] or ''}")
        val = meta["value"]
        if isinstance(val, dict):
            for field in ("videos", "posts"):
                if isinstance(val.get(field), list):
                    print(f"       {field}: {len(val[field])}")
