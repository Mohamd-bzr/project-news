#!/usr/bin/env python3
"""
MOHMD NEWS Database Layer — Lightweight SQLite with WAL mode
============================================================
Persists articles and archive across server restarts so the dashboard
is instantly populated at boot without waiting for the first 3.5-min cycle.
Zero external dependencies (uses standard library sqlite3).
"""

import contextlib
import json
import sqlite3
import time
from pathlib import Path

DB_FILE = Path(__file__).parent / ".mohmd_news.db"
_LEGACY_DB_FILE = Path(__file__).parent / ".hermes.db"


def _migrate_legacy_db():
    """One-time rename of the pre-rebrand database file so the history that was
    already collected survives the name change. Safe to leave in place forever."""
    try:
        if _LEGACY_DB_FILE.exists() and not DB_FILE.exists():
            _LEGACY_DB_FILE.rename(DB_FILE)
    except Exception:
        pass


_migrate_legacy_db()


@contextlib.contextmanager
def db_conn():
    conn = sqlite3.connect(str(DB_FILE), timeout=15)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 10000;")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_connection():
    return db_conn()


def init_db():
    """Create tables and indexes if they do not already exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                title_fa TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                summary_fa TEXT DEFAULT '',
                link TEXT,
                base_link TEXT,
                published_ts REAL,
                published_str TEXT,
                author TEXT DEFAULT '',
                source_key TEXT,
                source_name TEXT,
                source_kind TEXT DEFAULT 'crypto',
                source_trust REAL DEFAULT 0.6,
                tier INTEGER DEFAULT 3,
                via TEXT DEFAULT '',
                image TEXT DEFAULT '',
                assets_json TEXT DEFAULT '[]',
                topic TEXT DEFAULT 'general',
                topic_fa TEXT DEFAULT '',
                topic_icon TEXT DEFAULT '',
                credibility REAL DEFAULT 0.5,
                flags_json TEXT DEFAULT '[]',
                created_at REAL
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_art_pub_ts ON articles (published_ts DESC);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_art_created ON articles (created_at DESC);")
        # Full article bodies, extracted ahead of time. They used to live only in
        # the process memory, so every restart threw away thousands of expensive
        # fetches and the reader had to wait again on the first click.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bodies (
                id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                at REAL NOT NULL
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_body_at ON bodies (at DESC);")
        # News the operator deleted by hand. Kept as a list of ids rather than a
        # column on `articles` so a re-scrape of the same story cannot resurrect
        # it — the id is stable, the row is rewritten every cycle.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS hidden_articles (
                id TEXT PRIMARY KEY,
                at REAL NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS news_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                sentiment_score REAL,
                price_at_event REAL,
                price_1h REAL,
                price_4h REAL,
                price_24h REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_events_sym ON news_events (symbol);")
        # ── content studio ────────────────────────────────────────────────
        # What the studio drafted and where it went. Kept so the ranking can
        # penalise repeats (a story already published today is not news again)
        # and so the reply from a real channel can be read back later.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS studio_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id TEXT,
                title TEXT,
                title_key TEXT,
                score REAL,
                factors TEXT,
                format TEXT,
                draft TEXT,
                method TEXT DEFAULT 'template',
                created_ts REAL,
                status TEXT DEFAULT 'draft'
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_studio_content_ts ON studio_content (created_ts DESC);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_studio_content_key ON studio_content (title_key);")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS studio_posted (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id INTEGER,
                platform TEXT NOT NULL,
                ref TEXT,
                posted_ts REAL,
                stats TEXT DEFAULT ''
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_studio_posted_ts ON studio_posted (posted_ts DESC);")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messenger_posted (
                article_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                posted_ts REAL NOT NULL,
                PRIMARY KEY (article_id, platform)
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messenger_posted_ts ON messenger_posted (posted_ts DESC);")
        conn.commit()


def hide_article(aid: str) -> bool:
    """Hide one news item from the dashboard.

    The row stays in `articles` and the id goes on the hidden list — deleting the
    row instead would make "restore" a lie, because nothing would be left to
    restore it from. `load_articles_for_state` filters the list out. Best-effort.
    """
    if not aid:
        return False
    try:
        with get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO hidden_articles (id, at) VALUES (?, ?)",
                         (str(aid), time.time()))
            conn.commit()
        return True
    except Exception:
        return False


def unhide_all() -> int:
    """Bring every deleted news item back into circulation."""
    try:
        with get_connection() as conn:
            n = conn.execute("SELECT COUNT(*) FROM hidden_articles").fetchone()[0]
            conn.execute("DELETE FROM hidden_articles")
            conn.commit()
        return int(n or 0)
    except Exception:
        return 0


def hidden_ids() -> set:
    try:
        with get_connection() as conn:
            return {r[0] for r in conn.execute("SELECT id FROM hidden_articles")}
    except Exception:
        return set()


def save_body(aid: str, payload, cap: int = 700):
    """Persist one extracted article body or its Persian translation
    (`"<id>|fa"`). Best-effort, never raises."""
    if not aid or not payload:
        return
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO bodies (id, payload, at) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET payload = excluded.payload, at = excluded.at;",
                (aid, json.dumps(payload, ensure_ascii=False), time.time()),
            )
            conn.execute(
                "DELETE FROM bodies WHERE id NOT IN "
                "(SELECT id FROM bodies ORDER BY at DESC LIMIT ?);", (cap,)
            )
            conn.commit()
    except Exception:
        pass


def load_bodies(cap: int = 900) -> dict[str, dict]:
    """Newest extracted bodies, ready to merge into the in-memory cache."""
    out: dict[str, dict] = {}
    try:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, payload FROM bodies ORDER BY at DESC LIMIT ?;", (cap,)
            ).fetchall()
    except Exception:
        return out
    for r in rows:
        try:
            out[r["id"]] = json.loads(r["payload"])
        except Exception:
            continue
    return out


def load_bodies_fa(cap: int = 700) -> dict[str, list]:
    """Persian article bodies (`"<id>|fa"`), separately so the caller can put
    them back into the FA cache without touching the raw bodies."""
    return {k: v for k, v in load_bodies(cap).items()
            if k.endswith("|fa") and isinstance(v, list)}


def save_articles(articles: list[dict]):
    """Upsert articles into SQLite."""
    if not articles:
        return
    now = time.time()
    rows = []
    for a in articles:
        aid = a.get("id")
        if not aid:
            continue
        rows.append((
            aid,
            a.get("title") or "",
            a.get("title_fa") or "",
            a.get("summary") or "",
            a.get("summary_fa") or "",
            a.get("link") or "",
            a.get("base_link") or (a.get("link") or "").split("?")[0],
            a.get("published_ts") or 0.0,
            a.get("published_str") or "",
            a.get("author") or "",
            a.get("source_key") or "",
            a.get("source_name") or "",
            a.get("source_kind") or "crypto",
            float(a.get("source_trust") or 0.6),
            int(a.get("tier") or 3),
            a.get("via") or "",
            a.get("image") or "",
            json.dumps(a.get("assets") or [], ensure_ascii=False),
            a.get("topic") or "general",
            a.get("topic_fa") or "",
            a.get("topic_icon") or "",
            float(a.get("credibility") or 0.5),
            json.dumps(a.get("flags") or [], ensure_ascii=False),
            now,
        ))

    with get_connection() as conn:
        conn.executemany("""
            INSERT INTO articles (
                id, title, title_fa, summary, summary_fa, link, base_link,
                published_ts, published_str, author, source_key, source_name,
                source_kind, source_trust, tier, via, image, assets_json,
                topic, topic_fa, topic_icon, credibility, flags_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                title_fa = CASE WHEN excluded.title_fa != '' THEN excluded.title_fa ELSE articles.title_fa END,
                summary_fa = CASE WHEN excluded.summary_fa != '' THEN excluded.summary_fa ELSE articles.summary_fa END,
                link = excluded.link,
                source_key = excluded.source_key,
                source_name = excluded.source_name,
                published_ts = excluded.published_ts,
                source_trust = excluded.source_trust,
                tier = excluded.tier,
                topic = excluded.topic,
                topic_fa = CASE WHEN excluded.topic_fa != '' THEN excluded.topic_fa ELSE articles.topic_fa END,
                image = CASE WHEN excluded.image != '' THEN excluded.image ELSE articles.image END,
                credibility = excluded.credibility,
                flags_json = excluded.flags_json;
        """, rows)
        conn.commit()


def _row_to_article(r: sqlite3.Row, now_ts: float) -> dict:
    pub_ts = r["published_ts"] or 0.0
    age_hours = round((now_ts - pub_ts) / 3600, 1) if pub_ts else None
    try:
        assets = json.loads(r["assets_json"] or "[]")
    except Exception:
        assets = []
    try:
        flags = json.loads(r["flags_json"] or "[]")
    except Exception:
        flags = []

    return {
        "id": r["id"],
        "title": r["title"],
        "title_fa": r["title_fa"],
        "summary": r["summary"],
        "summary_fa": r["summary_fa"],
        "link": r["link"],
        "base_link": r["base_link"],
        "published_ts": pub_ts,
        "published_str": r["published_str"],
        "author": r["author"],
        "source_key": r["source_key"],
        "source_name": r["source_name"],
        "source_kind": r["source_kind"],
        "source_trust": r["source_trust"],
        "tier": r["tier"],
        "via": r["via"],
        "image": r["image"],
        "assets": assets,
        "topic": r["topic"],
        "topic_fa": r["topic_fa"],
        "topic_icon": r["topic_icon"],
        "credibility": r["credibility"],
        "flags": flags,
        "age_hours": age_hours,
    }


def load_articles_for_state(window_seconds: float = 86400.0, archive_cap: int = 1200) -> tuple[list[dict], list[dict]]:
    """
    Returns (recent_articles, archive_articles) ready to hydrate STATE.
    """
    now = time.time()
    cutoff = now - window_seconds
    gone = tuple(hidden_ids())
    # `NOT IN ()` is not valid SQL, so an empty delete-list needs its own query
    sql_recent = """
        SELECT * FROM articles
        WHERE published_ts >= ?%s
        ORDER BY published_ts DESC, credibility DESC
        LIMIT 600;
    """ % (" AND id NOT IN (%s)" % ",".join("?" * len(gone)) if gone else "")
    sql_arch = """
        SELECT * FROM articles
        WHERE published_ts < ?%s
        ORDER BY published_ts DESC
        LIMIT ?;
    """ % (" AND id NOT IN (%s)" % ",".join("?" * len(gone)) if gone else "")

    with get_connection() as conn:
        recent_rows = conn.execute(sql_recent, (cutoff, *gone)).fetchall()
        archive_rows = conn.execute(sql_arch, (cutoff, *gone, archive_cap)).fetchall()

    recent = [_row_to_article(r, now) for r in recent_rows]
    archive = [_row_to_article(r, now) for r in archive_rows]
    return recent, archive


# ── content studio ───────────────────────────────────────────────────────────

def save_studio_content(article_id: str, title: str, title_key: str, score: float,
                        factors: dict, fmt: dict, draft: dict, method: str = "template",
                        status: str = "draft") -> int:
    """Persist one drafted piece. Returns its row id (0 when the write failed)."""
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO studio_content (article_id, title, title_key, score, factors,"
                " format, draft, method, created_ts, status)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (str(article_id or ""), str(title or "")[:400], str(title_key or "")[:200],
                 float(score or 0), json.dumps(factors or {}, ensure_ascii=False),
                 json.dumps(fmt or {}, ensure_ascii=False),
                 json.dumps(draft or {}, ensure_ascii=False), str(method or "template"),
                 time.time(), str(status or "draft")))
            conn.commit()
            return int(cur.lastrowid or 0)
    except Exception:
        return 0


def update_studio_content(row_id: int, **fields) -> bool:
    allowed = {k: v for k, v in fields.items()
               if k in ("draft", "method", "status", "score", "factors", "format")}
    if not row_id or not allowed:
        return False
    for key in ("draft", "factors", "format"):
        if key in allowed and not isinstance(allowed[key], str):
            allowed[key] = json.dumps(allowed[key], ensure_ascii=False)
    try:
        with get_connection() as conn:
            sets = ", ".join(f"{k} = ?" for k in allowed)
            conn.execute(f"UPDATE studio_content SET {sets} WHERE id = ?;",
                         (*allowed.values(), int(row_id)))
            conn.commit()
        return True
    except Exception:
        return False


def studio_content_list(limit: int = 40) -> list[dict]:
    """Newest drafts first, with their posted markers resolved."""
    out: list[dict] = []
    try:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM studio_content ORDER BY created_ts DESC LIMIT ?;", (int(limit),)
            ).fetchall()
            posted = conn.execute(
                "SELECT content_id, platform, ref, posted_ts FROM studio_posted ORDER BY posted_ts DESC LIMIT 200;"
            ).fetchall()
    except Exception:
        return out
    by_content: dict[int, list] = {}
    for p in posted:
        by_content.setdefault(int(p["content_id"] or 0), []).append(
            {"platform": p["platform"], "ref": p["ref"], "posted_ts": p["posted_ts"]})
    for r in rows:
        def _j(raw, fallback):
            try:
                return json.loads(raw) if raw else fallback
            except Exception:
                return fallback
        out.append({
            "id": r["id"], "article_id": r["article_id"], "title": r["title"],
            "title_key": r["title_key"], "score": r["score"],
            "factors": _j(r["factors"], {}), "format": _j(r["format"], {}),
            "draft": _j(r["draft"], {}), "method": r["method"],
            "created_ts": r["created_ts"], "status": r["status"],
            "posted": by_content.get(int(r["id"]), []),
        })
    return out


def mark_studio_posted(content_id: int, platform: str, ref: str = "", stats: str = "") -> bool:
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO studio_posted (content_id, platform, ref, posted_ts, stats)"
                " VALUES (?, ?, ?, ?, ?);",
                (int(content_id or 0), str(platform or ""), str(ref or "")[:200],
                 time.time(), str(stats or "")[:4000]))
            if content_id:
                conn.execute("UPDATE studio_content SET status = 'posted' WHERE id = ?;",
                             (int(content_id),))
            conn.commit()
        return True
    except Exception:
        return False


def studio_recent_keys(hours: float = 48.0) -> set:
    """Ids, article ids and title keys of what was published recently, so the
    ranking can stop pitching the same story twice."""
    keys: set = set()
    try:
        cutoff = time.time() - hours * 3600.0
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT article_id, title_key FROM studio_content"
                " WHERE created_ts >= ? AND status = 'posted';", (cutoff,)).fetchall()
        for r in rows:
            if r["article_id"]:
                keys.add(str(r["article_id"]))
            if r["title_key"]:
                keys.add(str(r["title_key"]))
    except Exception:
        return keys
    return keys


def studio_posted_stats(limit: int = 30) -> list[dict]:
    out = []
    try:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT p.*, c.title FROM studio_posted p"
                " LEFT JOIN studio_content c ON c.id = p.content_id"
                " ORDER BY p.posted_ts DESC LIMIT ?;", (int(limit),)).fetchall()
        out = [{"id": r["id"], "content_id": r["content_id"], "platform": r["platform"],
                "ref": r["ref"], "posted_ts": r["posted_ts"], "stats": r["stats"],
                "title": r["title"]} for r in rows]
    except Exception:
        return []
    return out


def is_messenger_posted(article_id: str, platform: str) -> bool:
    """Check if an article has already been dispatched to a messenger."""
    if not article_id:
        return False
    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM messenger_posted WHERE article_id = ? AND platform = ? LIMIT 1;",
                (str(article_id), str(platform))
            ).fetchone()
            return bool(row)
    except Exception:
        return False


def mark_messenger_posted(article_id: str, platform: str) -> bool:
    """Record an article as dispatched to a messenger."""
    if not article_id:
        return False
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO messenger_posted (article_id, platform, posted_ts) VALUES (?, ?, ?);",
                (str(article_id), str(platform), time.time())
            )
            conn.commit()
            return True
    except Exception:
        return False


def messenger_recent_posted_ids(platform: str, max_age_hours: float = 72.0) -> set:
    """Retrieve set of article IDs dispatched to a messenger within max_age_hours."""
    out = set()
    try:
        cutoff = time.time() - (max_age_hours * 3600.0)
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT article_id FROM messenger_posted WHERE platform = ? AND posted_ts >= ?;",
                (str(platform), cutoff)
            ).fetchall()
            return {str(r["article_id"]) for r in rows if r["article_id"]}
    except Exception:
        return out


def get_messenger_posted_logs(platform: str = None, limit: int = 50) -> list[dict]:
    """Retrieve detailed log of recently dispatched ideas joined with article metadata."""
    out = []
    try:
        with get_connection() as conn:
            if platform:
                query = """
                    SELECT m.article_id, m.platform, m.posted_ts,
                           a.title, a.title_fa, a.link, a.source_name
                    FROM messenger_posted m
                    LEFT JOIN articles a ON a.id = m.article_id
                    WHERE m.platform = ?
                    ORDER BY m.posted_ts DESC
                    LIMIT ?;
                """
                rows = conn.execute(query, (str(platform), int(limit))).fetchall()
            else:
                query = """
                    SELECT m.article_id, m.platform, m.posted_ts,
                           a.title, a.title_fa, a.link, a.source_name
                    FROM messenger_posted m
                    LEFT JOIN articles a ON a.id = m.article_id
                    ORDER BY m.posted_ts DESC
                    LIMIT ?;
                """
                rows = conn.execute(query, (int(limit),)).fetchall()
            for r in rows:
                out.append({
                    "article_id": r["article_id"],
                    "platform": r["platform"],
                    "posted_ts": r["posted_ts"],
                    "title": r["title"] or "",
                    "title_fa": r["title_fa"] or "",
                    "link": r["link"] or "",
                    "source_name": r["source_name"] or "",
                })
    except Exception:
        pass
    return out

