#!/usr/bin/env python3
"""
MOHMD NEWS Database Layer — Lightweight SQLite with WAL mode
============================================================
Persists articles and archive across server restarts so the dashboard
is instantly populated at boot without waiting for the first 3.5-min cycle.
Zero external dependencies (uses standard library sqlite3).
"""

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


def get_connection():
    conn = sqlite3.connect(str(DB_FILE), timeout=15)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 10000;")
    conn.row_factory = sqlite3.Row
    return conn


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
        conn.commit()


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
                title_fa = CASE WHEN excluded.title_fa != '' THEN excluded.title_fa ELSE articles.title_fa END,
                summary_fa = CASE WHEN excluded.summary_fa != '' THEN excluded.summary_fa ELSE articles.summary_fa END,
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

    with get_connection() as conn:
        recent_rows = conn.execute("""
            SELECT * FROM articles
            WHERE published_ts >= ?
            ORDER BY published_ts DESC, credibility DESC
            LIMIT 600;
        """, (cutoff,)).fetchall()

        archive_rows = conn.execute("""
            SELECT * FROM articles
            WHERE published_ts < ?
            ORDER BY published_ts DESC
            LIMIT ?;
        """, (cutoff, archive_cap)).fetchall()

    recent = [_row_to_article(r, now) for r in recent_rows]
    archive = [_row_to_article(r, now) for r in archive_rows]
    return recent, archive
