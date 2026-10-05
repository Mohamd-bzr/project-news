/* ═══════════════════════════════════════════════════════════════════════════
   MOHMD NEWS — STORAGE ENGINE (StorageEngine.js)
   Offline-first persistence on top of IndexedDB, replacing the 5 MB / blocking
   localStorage cache that the dashboard used for bookmarks alone.

   One database, `MohmdNewsDB`:

     articles   id            keyed by article id; indexed by ts / topic / assets
     reports    sym           generated intelligence reports, keyed by symbol
     calendar   id            cached multi-week economic events (ts, impact)
     bookmarks  id            starred stories kept as full snapshots
     terms      term          INVERTED INDEX — {term, postings:[[id,w,ts,topic,assets]]}
     meta       k             counters and misc small values

   Search is a posting-list intersection over the `terms` store: the query is
   tokenized, each token is expanded by prefix inside one key range (so "horm"
   finds "hormuz" without a table scan), the postings are merged and scored in
   memory by `seSearch`. Nothing walks the 2 000+ article rows, which is why a
   query costs a handful of key reads instead of a full pass.

   Design rules that matter here (and that the node harness in
   tests/test_storage_engine.py pins down):

     * the pure parts — tokenizer, document terms, merge/score — never touch
       IndexedDB, so they are testable outside a browser;
     * no `await` inside an open transaction (a transaction auto-commits at the
       first await of a non-IDB promise, and the next request then throws
       TransactionInactiveError). Requests are queued, then `tx.oncomplete` is
       awaited once;
     * a write never throws into the dashboard: callers get a rejected promise
       they may ignore, and the UI keeps rendering from memory as before.

   Licensed with the rest of the project; no runtime dependency.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';

  const SE_DB_NAME = 'MohmdNewsDB';
  const SE_DB_VERSION = 1;

  /* Bound the index: a term that appears in every one of 50 000 articles would
     otherwise grow an unbounded posting list. Newest wins, since a relevance
     ranking that surfaces last month's story is not useful anyway. */
  const SE_MAX_POSTINGS = 600;
  const SE_PREFIX_TERMS = 8;      /* prefix expansions considered per query token */
  const SE_HALF_LIFE_MS = 36 * 3600 * 1000;   /* recency decay: 36h to half score */
  const SE_PROFILE_MAX = 4000;    /* articles kept before the oldest are pruned */

  /* Store/index schema — the single source of truth used by onupgradeneeded and
     by the tests, so a new index cannot be added to one and forgotten in the
     other. `keeps` documents the retention contract of each store. */
  const SE_STORES = {
    articles: {
      keyPath: 'id',
      indexes: [
        ['ts', 'ts'],
        ['topic', 'topic'],
        ['assets', 'assets', { multiEntry: true }]
      ],
      keeps: 'newest ' + SE_PROFILE_MAX + ' rows'
    },
    reports: { keyPath: 'sym', indexes: [['ts', 'ts']], keeps: 'one row per symbol' },
    calendar: {
      keyPath: 'id',
      indexes: [['ts', 'ts'], ['impact', 'impact']],
      keeps: 'rolling multi-week window'
    },
    bookmarks: { keyPath: 'id', indexes: [['saved_at', 'saved_at']], keeps: 'until unstarred' },
    terms: { keyPath: 'term', indexes: [['df', 'df']], keeps: 'newest ' + SE_MAX_POSTINGS + ' postings per term' },
    meta: { keyPath: 'k', indexes: [], keeps: 'counters' }
  };

  /* Field boosts: a hit in the headline must outrank the same word buried in a
     summary, and an asset tag is close to a headline because that is how the
     feed is actually addressed ("what moved XAU"). */
  const SE_FIELD_W = { title: 3, assets: 2.5, topic: 1.5, summary: 1, source: 0.4 };

  /* Stopwords in both languages of this terminal. The feed carries English
     headlines with Persian titles, so a tokenizer that removed only one set
     would quietly index "the" and "برای" as if they were signals. */
  const SE_STOP = new Set([
    'the', 'and', 'for', 'with', 'from', 'that', 'this', 'are', 'was', 'were', 'has',
    'have', 'had', 'its', 'into', 'over', 'after', 'before', 'than', 'then', 'but',
    'not', 'you', 'your', 'his', 'her', 'their', 'they', 'them', 'will', 'would',
    'can', 'could', 'may', 'might', 'says', 'said', 'amid', 'more', 'most', 'new',
    'now', 'how', 'why', 'who', 'what', 'when', 'all', 'any', 'out', 'off', 'per',
    'به', 'از', 'در', 'که', 'را', 'با', 'این', 'آن', 'های', 'ها', 'برای', 'بر', 'تا',
    'است', 'بود', 'شد', 'شده', 'می', 'هم', 'یا', 'و', 'همچنین', 'روی', 'بین', 'یک',
    'دو', 'هر', 'اما', 'اگر', 'نیز', 'خود', 'دیگر', 'دارد', 'کرد', 'کند'
  ]);

  /* ── pure helpers ─────────────────────────────────────────────────────── */

  /* Normalize one string into searchable tokens. Persian/Arabic variants are
     folded (ي→ی, ك→ک, diacritics dropped) so "بانك" and "بانک" are one term,
     and Latin text is lower-cased with combining marks stripped, which keeps
     "Crude", "crude" and "Crudé" together. */
  function seTok(text) {
    if (text == null) return [];
    let s = String(text);
    s = s.replace(/[\u064A\u0649]/g, '\u06CC').replace(/\u0643/g, '\u06A9');
    s = s.replace(/[\u064B-\u0652\u0670\u0640]/g, '');       /* harakat + tatweel */
    s = s.replace(/[\u200C\u200F\u200E]/g, ' ');              /* ZWNJ / bidi marks */
    try { s = s.normalize('NFKD').replace(/[\u0300-\u036f]/g, ''); } catch (e) { /* old engines */ }
    s = s.toLowerCase();
    const out = [], seen = Object.create(null);
    const raw = s.split(/[^0-9a-z\u0621-\u06FF]+/);
    for (let i = 0; i < raw.length; i++) {
      const t = raw[i];
      if (t.length < 2) continue;                 /* single letters are noise */
      if (/^[0-9]+$/.test(t) && t.length > 4) continue;  /* stray ids */
      if (SE_STOP.has(t)) continue;
      if (seen[t]) continue;
      seen[t] = 1;
      out.push(t);
    }
    return out;
  }

  /* Accepts epoch seconds, epoch ms or an ISO/parseable date and returns ms. */
  function seTs(v) {
    if (v == null || v === '') return Date.now();
    if (typeof v === 'number') return v > 1e12 ? Math.round(v) : Math.round(v * 1000);
    const n = Number(v);
    if (isFinite(n) && n > 0) return n > 1e12 ? Math.round(n) : Math.round(n * 1000);
    const d = Date.parse(String(v));
    return isNaN(d) ? Date.now() : d;
  }

  function seArr(v) {
    if (v == null) return [];
    if (Array.isArray(v)) return v.filter(Boolean).map(String);
    return String(v).split(/[,|/]+/).map(s => s.trim()).filter(Boolean);
  }

  function seRound(w) { return Math.round(w * 1000) / 1000; }

  /* One article → { rec, terms }. `rec` is the full article as the dashboard
     knows it (cardHTML renders straight from it after an offline restore), plus
     the three normalized fields the indexes are built on. */
  function seDoc(a) {
    a = a || {};
    const rec = Object.assign({}, a);
    rec.id = String(a.id != null ? a.id : (a.link || a.url || ''));
    rec.ts = seTs(a.published_ts != null ? a.published_ts : (a.ts || a.published));
    rec.topic = String(a.topic || '');
    rec.assets = seArr(a.assets);
    rec.title = String(a.title || '');
    rec.summary = String(a.summary || '');
    rec.source = String(a.source || '');

    const terms = Object.create(null);
    const add = (toks, w) => {
      for (let i = 0; i < toks.length; i++) terms[toks[i]] = (terms[toks[i]] || 0) + w;
    };
    add(seTok(rec.title), SE_FIELD_W.title);
    add(seTok(rec.title_fa), SE_FIELD_W.title);
    add(seTok(rec.assets.join(' ')), SE_FIELD_W.assets);
    add(seTok(rec.topic), SE_FIELD_W.topic);
    add(seTok(rec.topic_fa), SE_FIELD_W.topic);
    add(seTok(rec.summary), SE_FIELD_W.summary);
    add(seTok(rec.summary_fa), SE_FIELD_W.summary);
    add(seTok(rec.source), SE_FIELD_W.source);
    return { rec: rec, terms: terms };
  }

  /* Merge + rank. Pure: `parts` are already-fetched posting lists, one per query
     token — [{term, exact, df, postings:[[id,w,ts,topic,assets], …]]}.

     Returns {hits, took, terms, relaxed}. A hit carries `coverage` (how much of
     the query it matched), which is what makes multi-word queries behave: an
     article matching "opec supply" beats one matching "opec" alone, and if
     nothing matches every token the search relaxes to OR instead of returning
     an empty screen. */
  function seSearch(parts, query, opts) {
    const t0 = Date.now();
    opts = opts || {};
    const limit = opts.limit || 30;
    const now = opts.now || Date.now();
    const total = Math.max(1, opts.totalDocs || 1);
    const halfLife = opts.halfLife || SE_HALF_LIFE_MS;
    const since = opts.since ? seTs(opts.since) : 0;
    const asset = opts.asset && opts.asset !== 'all' ? String(opts.asset) : '';
    const topic = opts.topic && opts.topic !== 'all' ? String(opts.topic) : '';

    const usable = (parts || []).filter(p => p && p.postings && p.postings.length);
    if (!usable.length) return { hits: [], took: Date.now() - t0, terms: 0, relaxed: false };

    const byId = new Map();
    for (let i = 0; i < usable.length; i++) {
      const part = usable[i];
      const df = Math.max(1, part.df || part.postings.length);
      /* idf: a token present in every article contributes nothing to the
         ranking, one that appears in three contributes a lot */
      const idf = Math.log(1 + total / (1 + df));
      for (let j = 0; j < part.postings.length; j++) {
        const p = part.postings[j];
        const id = String(p[0]);
        let hit = byId.get(id);
        if (!hit) {
          hit = { id: id, score: 0, matched: 0, ts: p[2] || 0, topic: p[3] || '', assets: p[4] || [] };
          byId.set(id, hit);
        }
        const w = Math.max(0.01, Number(p[1]) || 1);
        hit.matched += 1;
        hit.score += idf * (1 + Math.log(1 + w)) * (part.exact ? 1.6 : 1);
        if (p[2] > hit.ts) hit.ts = p[2];
      }
    }

    const need = opts.any ? 1 : usable.length;
    const hits = [];
    byId.forEach(hit => {
      if (hit.matched < need) return;
      if (since && hit.ts < since) return;
      if (asset && !hit.assets.includes(asset)) return;
      if (topic && hit.topic !== topic) return;
      const coverage = hit.matched / usable.length;
      const recency = Math.pow(0.5, Math.max(0, now - hit.ts) / halfLife);
      hit.coverage = coverage;
      hit.score = hit.score * (0.45 + 0.55 * coverage) * (0.35 + 0.65 * recency);
      hits.push(hit);
    });
    hits.sort((a, b) => b.score - a.score || b.ts - a.ts);
    return {
      hits: hits.slice(0, limit),
      total: hits.length,
      took: Date.now() - t0,
      terms: usable.length,
      relaxed: !!opts.any
    };
  }

  /* ── engine ───────────────────────────────────────────────────────────── */

  class StorageEngine {
    constructor(name) {
      this.name = name || SE_DB_NAME;
      this._db = null;
      this._opening = null;
      this._docCount = 0;
      this.lastError = null;
    }

    /* Promise-based glue. Everything below is queued through these three so no
       method has to invent its own error handling. */
    static _req(r) {
      return new Promise((res, rej) => {
        r.onsuccess = () => res(r.result);
        r.onerror = () => rej(r.error || new Error('idb request failed'));
      });
    }
    static _done(tx) {
      return new Promise((res, rej) => {
        tx.oncomplete = () => res(true);
        tx.onerror = () => rej(tx.error || new Error('idb txn failed'));
        tx.onabort = () => rej(tx.error || new Error('idb txn aborted'));
      });
    }
    available() {
      return typeof indexedDB !== 'undefined' && !!indexedDB;
    }

    open() {
      if (this._db) return Promise.resolve(this._db);
      if (this._opening) return this._opening;
      if (!this.available()) return Promise.reject(new Error('IndexedDB unavailable'));
      this._opening = new Promise((resolve, reject) => {
        const req = indexedDB.open(this.name, SE_DB_VERSION);
        req.onupgradeneeded = ev => {
          const db = req.result;
          Object.keys(SE_STORES).forEach(name => {
            const spec = SE_STORES[name];
            const store = db.objectStoreNames.contains(name)
              ? req.transaction.objectStore(name)
              : db.createObjectStore(name, { keyPath: spec.keyPath });
            (spec.indexes || []).forEach(ix => {
              if (!store.indexNames.contains(ix[0])) {
                store.createIndex(ix[0], ix[1], ix[2] || {});
              }
            });
          });
        };
        req.onsuccess = () => {
          this._db = req.result;
          this._db.onversionchange = () => { try { this._db.close(); } catch (e) {} };
          this._opening = null;
          resolve(this._db);
        };
        req.onerror = () => {
          this._opening = null;
          this.lastError = req.error;
          reject(req.error || new Error('open failed'));
        };
        req.onblocked = () => { /* another tab holds an old version — reported, not fatal */ };
      });
      return this._opening;
    }

    close() {
      if (this._db) { try { this._db.close(); } catch (e) {} this._db = null; }
    }

    /* ── articles ──────────────────────────────────────────────────────── */

    /* Write articles and their postings in a single transaction: an article
       visible in search but missing from the store (or the reverse) is the kind
       of half-state a crash between two transactions would leave behind. */
    async putArticles(list) {
      const docs = (list || []).map(seDoc).filter(d => d.rec.id);
      if (!docs.length) return { articles: 0, terms: 0 };
      const byTerm = new Map();
      docs.forEach(d => {
        Object.keys(d.terms).forEach(term => {
          let arr = byTerm.get(term);
          if (!arr) { arr = []; byTerm.set(term, arr); }
          arr.push([d.rec.id, seRound(d.terms[term]), d.rec.ts, d.rec.topic, d.rec.assets]);
        });
      });

      const db = await this.open();
      await new Promise((resolve, reject) => {
        const tx = db.transaction(['articles', 'terms'], 'readwrite');
        StorageEngine._done(tx).then(resolve, reject);
        const as = tx.objectStore('articles');
        const ts = tx.objectStore('terms');
        docs.forEach(d => as.put(d.rec));
        byTerm.forEach((posts, term) => {
          const get = ts.get(term);
          get.onsuccess = () => {
            const row = get.result || { term: term, df: 0, postings: [] };
            const seen = new Map();
            (row.postings || []).forEach(p => seen.set(String(p[0]), p));
            posts.forEach(p => {
              const old = seen.get(p[0]);
              seen.set(p[0], old
                ? [p[0], Math.max(old[1] || 0, p[1]), p[2] || old[2], p[3] || old[3],
                   (p[4] && p[4].length) ? p[4] : (old[4] || [])]
                : p);
            });
            const merged = Array.from(seen.values()).sort((a, b) => (b[2] || 0) - (a[2] || 0)).slice(0, SE_MAX_POSTINGS);
            /* `df` is the true document count of the term, kept even when the
               posting list is truncated — idf would otherwise over-weight the
               most common words as soon as the cap kicked in */
            ts.put({ term: term, df: Math.max(merged.length, row.df || 0, seen.size), postings: merged });
          };
        });
      });
      this._docCount = await this.count('articles');
      return { articles: docs.length, terms: byTerm.size };
    }

    async count(store) {
      const db = await this.open();
      return new Promise((resolve, reject) => {
        const tx = db.transaction(store, 'readonly');
        StorageEngine._req(tx.objectStore(store).count()).then(resolve, reject);
      });
    }

    /* Newest first, optionally narrowed by the three indexes. */
    async getArticles(opts) {
      opts = opts || {};
      const limit = opts.limit || 200;
      const db = await this.open();
      const store = db.transaction('articles', 'readonly').objectStore('articles');
      let src;
      if (opts.asset && opts.asset !== 'all') src = store.index('assets').getAll(IDBKeyRange.only(String(opts.asset)));
      else if (opts.topic && opts.topic !== 'all') src = store.index('topic').getAll(IDBKeyRange.only(String(opts.topic)));
      else src = store.getAll();
      let rows = await StorageEngine._req(src);
      if (opts.since) {
        const since = seTs(opts.since);
        rows = rows.filter(r => (r.ts || 0) >= since);
      }
      if (opts.q) {
        const q = String(opts.q).toLowerCase();
        rows = rows.filter(r =>
          (String(r.title || '') + ' ' + String(r.summary || '') + ' ' +
           String(r.title_fa || '') + ' ' + String(r.source || '')).toLowerCase().indexOf(q) >= 0);
      }
      rows.sort((a, b) => (b.ts || 0) - (a.ts || 0));
      return rows.slice(0, limit);
    }

    async getArticle(id) {
      const db = await this.open();
      const store = db.transaction('articles', 'readonly').objectStore('articles');
      return StorageEngine._req(store.get(String(id)));
    }

    /* ── full-text search ──────────────────────────────────────────────── */

    /* Terms whose key starts with `prefix`: one key-range cursor. Returning the
       exact token first means a query for "hormuz" is not diluted by unrelated
       words that merely share the first letters. */
    async _termsFor(prefix) {
      const db = await this.open();
      const out = [];
      await new Promise((resolve, reject) => {
        let range;
        try { range = IDBKeyRange.bound(prefix, prefix + '\uffff'); }
        catch (e) { return resolve(); }
        const tx = db.transaction('terms', 'readonly');
        const cur = tx.objectStore('terms').openKeyCursor(range);
        cur.onsuccess = () => {
          const c = cur.result;
          if (!c || out.length >= SE_PREFIX_TERMS) return resolve();
          if (c.key === prefix) out.unshift(c.key); else out.push(c.key);
          c.continue();
        };
        cur.onerror = () => reject(cur.error);
      });
      return out;
    }

    async _rows(store, keys) {
      if (!keys.length) return [];
      const db = await this.open();
      return new Promise((resolve, reject) => {
        const out = [];
        const tx = db.transaction(store, 'readonly');
        StorageEngine._done(tx).then(() => resolve(out), reject);
        const os = tx.objectStore(store);
        keys.forEach(k => {
          const r = os.get(k);
          r.onsuccess = () => { if (r.result) out.push(r.result); };
        });
      });
    }

    /* Full-text query → hydrated articles. `parts` are built from the index,
       `seSearch` decides the order, and only the top hits are read back. */
    async search(q, opts) {
      opts = opts || {};
      const limit = opts.limit || 30;
      if (!this._docCount) this._docCount = await this.count('articles');
      const toks = seTok(q);
      if (!toks.length) return { hits: [], articles: [], took: 0, terms: 0, relaxed: false };

      const parts = [];
      for (let i = 0; i < toks.length; i++) {
        const tok = toks[i];
        const keys = await this._termsFor(tok);
        const rows = await this._rows('terms', keys);
        const seen = new Set(), postings = [];
        let df = 0;
        rows.forEach(row => {
          df += row.df || (row.postings || []).length;
          (row.postings || []).forEach(p => {
            const id = String(p[0]);
            if (seen.has(id)) return;
            seen.add(id);
            postings.push(p);
          });
        });
        parts.push({ term: tok, exact: keys.length > 0 && keys[0] === tok, df: df, postings: postings });
      }

      const base = {
        limit: limit, totalDocs: this._docCount || 1, now: opts.now || Date.now(),
        since: opts.since, asset: opts.asset, topic: opts.topic,
        halfLife: opts.halfLife, any: !!opts.any
      };
      let res = seSearch(parts, q, base);
      /* AND is right for two-or-three-word queries, but a strict AND on a phrase
         nobody wrote returns an empty feed and looks broken — relax once. */
      if (!opts.any && res.hits.length < 3) {
        const loose = seSearch(parts, q, Object.assign({}, base, { any: true }));
        if (loose.hits.length > res.hits.length) res = loose;
      }
      const rows = await this._rows('articles', res.hits.map(h => h.id));
      const byId = new Map(rows.map(r => [String(r.id), r]));
      return {
        hits: res.hits,
        articles: res.hits.map(h => byId.get(h.id)).filter(Boolean),
        total: res.total || res.hits.length,
        took: res.took,
        terms: res.terms,
        relaxed: res.relaxed
      };
    }

    /* ── reports ───────────────────────────────────────────────────────── */

    async putReport(sym, data) {
      const db = await this.open();
      const tx = db.transaction('reports', 'readwrite');
      tx.objectStore('reports').put({ sym: String(sym), ts: Date.now(), data: data });
      return StorageEngine._done(tx);
    }

    async getReport(sym) {
      const db = await this.open();
      const row = await StorageEngine._req(
        db.transaction('reports', 'readonly').objectStore('reports').get(String(sym)));
      return row ? row.data : null;
    }

    async listReports() {
      const db = await this.open();
      const rows = await StorageEngine._req(
        db.transaction('reports', 'readonly').objectStore('reports').getAll());
      return rows.sort((a, b) => (b.ts || 0) - (a.ts || 0)).map(r => ({ sym: r.sym, ts: r.ts }));
    }

    /* ── calendar ──────────────────────────────────────────────────────── */

    async putCalendar(events) {
      const rows = (events || []).map(e => {
        e = e || {};
        /* the calendar feed carries `ts` (epoch seconds) plus `iso`/`day`, but
           no id of its own — one is derived, including the country, because
           the same release name appears for several economies on one day */
        const id = String(e.id != null ? e.id
          : [e.title || e.event || '', e.iso || e.day || '', e.country || ''].join('|'));
        return Object.assign({}, e, {
          id: id,
          ts: seTs(e.ts != null ? e.ts : (e.iso || e.day || e.date)),
          impact: String(e.impact || e.importance || ''),
          country: String(e.country || '')
        });
      }).filter(r => r.id.replace(/\|/g, '').trim().length > 0);
      if (!rows.length) return 0;
      const db = await this.open();
      const tx = db.transaction('calendar', 'readwrite');
      const os = tx.objectStore('calendar');
      rows.forEach(r => os.put(r));
      await StorageEngine._done(tx);
      return rows.length;
    }

    async getCalendar(opts) {
      opts = opts || {};
      const db = await this.open();
      let rows = await StorageEngine._req(
        db.transaction('calendar', 'readonly').objectStore('calendar').getAll());
      if (opts.from) { const f = seTs(opts.from); rows = rows.filter(r => (r.ts || 0) >= f); }
      if (opts.to) { const t = seTs(opts.to); rows = rows.filter(r => (r.ts || 0) <= t); }
      if (opts.impact) rows = rows.filter(r => r.impact === opts.impact);
      return rows.sort((a, b) => (a.ts || 0) - (b.ts || 0));
    }

    /* ── bookmarks (snapshot in the database, ids mirrored to localStorage so
          the existing sync rendering path keeps working unchanged) ───────── */

    async putBookmark(snap) {
      if (!snap || snap.id == null) return false;
      const row = Object.assign({}, snap, { id: String(snap.id) });
      if (!row.saved_at) row.saved_at = Math.floor(Date.now() / 1000);
      const db = await this.open();
      const tx = db.transaction('bookmarks', 'readwrite');
      tx.objectStore('bookmarks').put(row);
      await StorageEngine._done(tx);
      return true;
    }

    async dropBookmark(id) {
      const db = await this.open();
      const tx = db.transaction('bookmarks', 'readwrite');
      tx.objectStore('bookmarks').delete(String(id));
      await StorageEngine._done(tx);
      return true;
    }

    async listBookmarks() {
      const db = await this.open();
      const rows = await StorageEngine._req(
        db.transaction('bookmarks', 'readonly').objectStore('bookmarks').getAll());
      return rows.sort((a, b) => (b.saved_at || 0) - (a.saved_at || 0));
    }

    /* Replace the whole snapshot set in one transaction — used when the starred
       list is edited in one place and the DB must not drift from it. */
    async syncBookmarks(ids, meta) {
      ids = (ids || []).map(String);
      meta = meta || {};
      const db = await this.open();
      const tx = db.transaction('bookmarks', 'readwrite');
      const os = tx.objectStore('bookmarks');
      const keep = new Set(ids);
      os.openCursor().onsuccess = ev => {
        const c = ev.target.result;
        if (!c) return;
        if (!keep.has(String(c.key))) c.delete();
        c.continue();
      };
      ids.forEach(id => {
        const snap = meta[id];
        if (snap) os.put(Object.assign({}, snap, { id: String(id) }));
      });
      await StorageEngine._done(tx);
      return ids.length;
    }

    /* ── meta + housekeeping ───────────────────────────────────────────── */

    async putMeta(k, v) {
      const db = await this.open();
      const tx = db.transaction('meta', 'readwrite');
      tx.objectStore('meta').put({ k: String(k), v: v });
      return StorageEngine._done(tx);
    }

    async getMeta(k) {
      const db = await this.open();
      const row = await StorageEngine._req(
        db.transaction('meta', 'readonly').objectStore('meta').get(String(k)));
      return row ? row.v : null;
    }

    async stats() {
      const out = { db: this.name, version: SE_DB_VERSION, articles: 0, reports: 0, calendar: 0, bookmarks: 0, terms: 0 };
      const names = Object.keys(SE_STORES);
      for (let i = 0; i < names.length; i++) {
        try { out[names[i]] = await this.count(names[i]); } catch (e) { /* store missing → 0 */ }
      }
      if (this._docCount) out.articles = Math.max(out.articles, this._docCount);
      try {
        if (global.navigator && navigator.storage && navigator.storage.estimate) {
          const est = await navigator.storage.estimate();
          out.usage = est.usage; out.quota = est.quota;
          out.persisted = navigator.storage.persisted ? await navigator.storage.persisted() : null;
        }
      } catch (e) { /* no storage estimate in this browser */ }
      return out;
    }

    /* Keep the cache bounded without a background job: drop articles past the
       retention window, then trim the oldest rows over the profile cap. Terms
       are re-derived lazily — an orphan posting is harmless (its id simply does
       not hydrate) whereas a wrong posting list would be a wrong search result. */
    async prune(opts) {
      opts = opts || {};
      const keepDays = opts.keepDays || 21;
      const max = opts.max || SE_PROFILE_MAX;
      const cutoff = Date.now() - keepDays * 24 * 3600 * 1000;
      const db = await this.open();
      let removed = 0;
      await new Promise((resolve, reject) => {
        const tx = db.transaction('articles', 'readwrite');
        StorageEngine._done(tx).then(resolve, reject);
        const os = tx.objectStore('articles');
        const cur = os.index('ts').openCursor(IDBKeyRange.upperBound(cutoff));
        cur.onsuccess = ev => {
          const c = ev.target.result;
          if (!c) return;
          removed += 1;
          c.delete();
          c.continue();
        };
      });
      let n = await this.count('articles');
      if (n > max) {
        await new Promise((resolve, reject) => {
          const tx = db.transaction('articles', 'readwrite');
          StorageEngine._done(tx).then(resolve, reject);
          const cur = tx.objectStore('articles').index('ts').openCursor();
          let left = n - max;
          cur.onsuccess = ev => {
            const c = ev.target.result;
            if (!c || left <= 0) return;
            left -= 1; removed += 1;
            c.delete();
            c.continue();
          };
        });
      }
      this._docCount = await this.count('articles');
      return removed;
    }

    async clear(store) {
      const db = await this.open();
      const names = store ? [store] : Object.keys(SE_STORES);
      for (let i = 0; i < names.length; i++) {
        const tx = db.transaction(names[i], 'readwrite');
        tx.objectStore(names[i]).clear();
        await StorageEngine._done(tx);
      }
      this._docCount = 0;
      return names;
    }
  }

  const SE_API = {
    StorageEngine: StorageEngine,
    SE_DB_NAME: SE_DB_NAME,
    SE_DB_VERSION: SE_DB_VERSION,
    SE_STORES: SE_STORES,
    SE_MAX_POSTINGS: SE_MAX_POSTINGS,
    SE_FIELD_W: SE_FIELD_W,
    seTok: seTok, seTs: seTs, seArr: seArr, seDoc: seDoc, seSearch: seSearch
  };

  Object.keys(SE_API).forEach(k => { global[k] = SE_API[k]; });
  if (typeof module !== 'undefined' && module.exports) module.exports = SE_API;
})(typeof window !== 'undefined' ? window : globalThis);
