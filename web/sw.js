/* ═══════════════════════════════════════════════════════════════════════════
   MOHMD NEWS — SERVICE WORKER  (served at /sw.js, scope /)

   The terminal must open on a plane, in a dealing room with the proxy down, or
   while the scraper cycle is mid-flight. This worker is the half of that
   promise the page cannot make on its own: the shell is precached, the last
   good answer of every JSON endpoint is kept, and a navigation that cannot
   reach Flask still boots the dashboard.

   Strategies, deliberately different per class of request:

     navigations      network-first (4 s), then the precached shell. A stale
                      shell is harmless — the JSON behind it is what carries
                      the news, and it is versioned separately.
     /api/* GET       network-first with NO timeout race: serving a cached
                      /api/data while the network is merely slow is exactly the
                      "feed stuck on old news" bug this project already fought.
                      Cache is consulted only when the request actually fails.
     /api/stream      never touched. It is an SSE stream; buffering it would
                      freeze the live ticker behind a response that never ends.
     shell assets     stale-while-revalidate: instant boot, fresh next time.
     cross-origin     stale-while-revalidate (fonts, the chart library, the
                      TradingView embed). Opaque responses are cacheable.

   Cache names carry a version so `activate` can drop everything from an older
   build in one pass. Bump SW_VERSION with any shell-affecting change.
   ═══════════════════════════════════════════════════════════════════════════ */
'use strict';

const SW_VERSION = 'v13';        /* v9: dropped the daily-print route from the shell (shell changed) */
const SHELL_CACHE = 'mohmd-shell-' + SW_VERSION;
const API_CACHE = 'mohmd-api-' + SW_VERSION;
const EXT_CACHE = 'mohmd-ext-' + SW_VERSION;

const SHELL = [
  '/',
  '/manifest.webmanifest',
  '/storage-engine.js',
  '/channel.js',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  /* self-hosted letterforms — the offline boot renders in the real brand
     font, not the system fallback */
  '/fonts/Vazirmatn-var.woff2',
  '/fonts/IBMPlexMono-Regular.woff2',
  '/fonts/IBMPlexMono-SemiBold.woff2',
  '/fonts/IBMPlexMono-Bold.woff2',
  '/fonts/IBMPlexSans-Regular.woff2',
  '/fonts/IBMPlexSans-SemiBold.woff2',
  '/fonts/IBMPlexSans-Bold.woff2'
];

const API_MAX = 80;        /* newest endpoint answers kept */
const EXT_MAX = 40;        /* newest third-party assets kept */
const NAV_TIMEOUT = 4000;  /* ms before a navigation falls back to the shell */

/* Chrome ignores HTTP cache headers for the worker script and revalidates at
   most every 24 h, so the version constant above plus skipWaiting is the real
   update mechanism: a new build installs, takes over, and drops old caches. */

let SHELL_FAILURES = [];
/* when this worker last answered a request from a cache instead of the network.
   The page asks for it on boot (PING) so the "this data is old" label does not
   depend on a message that may have been sent before the listener existed. */
let LAST_CACHE_HIT = 0;

/* Precache the shell. Deliberately one URL at a time instead of addAll(): a
   single 404 (a renamed icon) would abort addAll() and leave the terminal with
   no worker at all, while here the three URLs that do exist still land and the
   failure is recorded for the page to report. */
async function primeShell(force) {
  const cache = await caches.open(SHELL_CACHE);
  const failures = [];
  for (const url of SHELL) {
    try {
      if (!force && await cache.match(url)) continue;
      await cache.add(new Request(url, { cache: 'reload' }));
    } catch (e) {
      failures.push(url + ': ' + e);
      console.warn('[sw] shell precache failed for', url, e);
    }
  }
  SHELL_FAILURES = failures;
  return failures;
}

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    await primeShell(true).catch(() => {});
    self.skipWaiting();
  })());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keep = [SHELL_CACHE, API_CACHE, EXT_CACHE];
    const names = await caches.keys();
    await Promise.all(names.map(n => (keep.includes(n) ? null : caches.delete(n))));
    await trim(API_CACHE, API_MAX);
    await trim(EXT_CACHE, EXT_MAX);
    /* Self-healing: a browser profile can evict a cache under storage
       pressure, and a second worker on the same origin (the preview harness
       registers one under /static/) may clear caches it does not recognise.
       Whichever happened, the shell is what makes the terminal openable, so it
       is re-primed whenever it comes up incomplete. */
    const shell = await caches.open(SHELL_CACHE);
    if (!await shell.match('/')) await primeShell(true).catch(() => {});
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;                     /* settings, alerts, refresh */
  let url;
  try { url = new URL(req.url); } catch (e) { return; }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return;

  const sameOrigin = url.origin === self.location.origin;

  if (!sameOrigin) { event.respondWith(staleWhileRevalidate(req, EXT_CACHE)); return; }

  if (url.pathname === '/api/stream' || url.pathname === '/api/stream/prices') {
    return;                                             /* SSE: hands off */
  }

  if (url.pathname.startsWith('/api/')) {
    /* the image proxy sets its own long-lived cache headers and its payloads
       are far bigger than the JSON this cache is sized for */
    if (url.pathname.startsWith('/api/proxy-image')) return;
    event.respondWith(networkFirst(req, API_CACHE, API_MAX));
    return;
  }

  if (req.mode === 'navigate') { event.respondWith(navigateFirst(req)); return; }

  event.respondWith(staleWhileRevalidate(req, SHELL_CACHE));
});

/* ── strategies ─────────────────────────────────────────────────────────── */

async function navigateFirst(req) {
  const cache = await caches.open(SHELL_CACHE);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), NAV_TIMEOUT);
  try {
    const fresh = await fetch(req, { signal: controller.signal });
    /* every successful navigation to the *dashboard* refreshes the shell, so an
       evicted cache is rebuilt by simply using the terminal while the server is
       up. Other documents are pages of their own: storing one under '/' would
       leave the offline shell booting the wrong page, which is exactly what
       happened when a stray click landed on a sub-page. */
    let path = '';
    try { path = new URL(req.url).pathname; } catch (e) {}
    if (fresh && fresh.ok && fresh.type === 'basic' && (path === '/' || path === '/index.html')) {
      await cache.put('/', fresh.clone()).catch(() => {});
    }
    return fresh;
  } catch (e) {
    const shell = (await cache.match('/')) || (await cache.match('/index.html'));
    if (shell) {
      /* tell the page it is running from the shell — the client shows
         "Offline (Cache Mode)" instead of claiming a fresh sync */
      LAST_CACHE_HIT = Date.now();
      notifyClients({ type: 'SW_OFFLINE_TICK' });
      return shell;
    }
    return offlinePage('Terminal shell is not cached yet');
  } finally {
    clearTimeout(timer);
  }
}

async function networkFirst(req, cacheName, max) {
  const cache = await caches.open(cacheName);
  try {
    const fresh = await fetch(req);
    if (fresh && fresh.ok && fresh.status === 200) {
      cache.put(req, fresh.clone()).then(() => trim(cacheName, max)).catch(() => {});
    }
    return fresh;
  } catch (e) {
    const hit = await cache.match(req, { ignoreSearch: false });
    if (hit) {
      LAST_CACHE_HIT = Date.now();
      notifyClients({ type: 'SW_OFFLINE_TICK', url: req.url });
      const headers = new Headers(hit.headers);
      headers.set('X-MOHMD-Cache', 'hit');     /* the client can show cache mode */
      return new Response(hit.body, { status: hit.status, statusText: hit.statusText, headers: headers });
    }
    /* A synthetic 504 would *resolve* the page's fetch with a body it cannot
       use (the report drawer would render an offline stub instead of its own
       IndexedDB copy). Failing like a dead network is the honest answer: the
       page has a cache layer of its own behind this one, and it only runs when
       the request actually rejects. */
    throw new Error('offline: no cached response for ' + req.url);
  }
}

async function staleWhileRevalidate(req, cacheName) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(req);
  const network = fetch(req).then(res => {
    if (res && res.status === 200) cache.put(req, res.clone()).catch(() => {});
    return res;
  }).catch(() => null);
  return hit || (await network) || new Response('', { status: 504, statusText: 'offline' });
}

async function trim(cacheName, max) {
  try {
    const cache = await caches.open(cacheName);
    const keys = await cache.keys();
    if (keys.length <= max) return;
    /* keys() is insertion-ordered, so the surplus at the front is the oldest */
    await Promise.all(keys.slice(0, keys.length - max).map(k => cache.delete(k)));
  } catch (e) { /* a full or evicted cache must not break the handler */ }
}

function notifyClients(msg) {
  self.clients.matchAll({ includeUncontrolled: true }).then(list => {
    list.forEach(c => { try { c.postMessage(msg); } catch (e) {} });
  }).catch(() => {});
}

function offlinePage(text) {
  return new Response(
    '<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8">' +
    '<title>MOHMD NEWS — آفلاین</title>' +
    '<body style="background:#0B0A09;color:#EFE8DD;font:15px/1.7 system-ui;padding:12vh 8vw">' +
    '<h1 style="color:#C8965D;font-size:20px">MOHMD NEWS</h1><p>' + text + '</p>' +
    '<p style="color:#8C8377">یک بار با اتصال باز کنید تا صفحه ذخیره شود.</p></body></html>',
    { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
}

/* ── messages from the page + notification plumbing ─────────────────────── */

self.addEventListener('message', event => {
  const data = event.data || {};
  if (data.type === 'SKIP_WAITING') { self.skipWaiting(); return; }
  if (data.type === 'CLEAR_API_CACHE') {
    caches.delete(API_CACHE).then(() => notifyClients({ type: 'SW_CACHE_CLEARED' }));
    return;
  }
  if (data.type === 'ENSURE_SHELL') {
    /* the page reports; the worker decides. `force` is false, so a shell that
       is already complete costs one cache lookup. */
    (async () => {
      const cache = await caches.open(SHELL_CACHE);
      const have = await cache.match('/');
      if (have) { notifyClients({ type: 'SW_SHELL_OK', version: SW_VERSION }); return; }
      const failures = await primeShell(true).catch(() => ['primeShell threw']);
      notifyClients({ type: 'SW_SHELL_PRIMED', failures: failures, version: SW_VERSION });
    })();
    return;
  }
  if (data.type === 'CACHE_URLS' && Array.isArray(data.urls)) {
    /* used by the page to pin a report or a chart payload for offline reading */
    caches.open(API_CACHE).then(c => Promise.all(
      data.urls.map(u => c.add(new Request(u, { credentials: 'same-origin' })).catch(() => false))));
    return;
  }
  if (data.type === 'PING') {
    event.source && event.source.postMessage(
      { type: 'PONG', version: SW_VERSION, shell: SHELL_CACHE, failures: SHELL_FAILURES,
        lastCacheHit: LAST_CACHE_HIT, caches: { shell: SHELL_CACHE, api: API_CACHE } });
  }
});

/* Alerts raised while the tab is hidden are shown through the worker so they
   survive a focus change and are tappable on mobile. */
self.addEventListener('notificationclick', event => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil((async () => {
    const wins = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const w of wins) {
      if ('focus' in w) { try { await w.focus(); if (target !== '/') w.navigate(target); return; } catch (e) {} }
    }
    if (self.clients.openWindow) await self.clients.openWindow(target);
  })());
});
