/* ═══════════════════════════════════════════════════════════════════════════
   PWA BRIDGE — the page half of the offline-first layer
   ═══════════════════════════════════════════════════════════════════════════
   The dashboard keeps its state in memory (DATA / ECON) and, until now, only
   localStorage — 5 MB, synchronous, and on this profile already carrying the
   bookmarks of a year of terminals. This block moves the cache to IndexedDB
   (`MohmdNewsDB`, see web/storage_engine.js) and does four things:

     1. captures every JSON answer the page receives (articles, reports,
        calendar, article bodies) into the database, cloned off the response so
        the render path is never blocked or slowed;
     2. serves a feed and an article body back from the cache when the network
        is gone — the swap happens inside the existing renderers, so nothing
        downstream had to change;
     3. mirrors the starred list into a `bookmarks` store with full snapshots,
        and restores it when localStorage is empty;
     4. answers the feed search box from the full-text index when the live
        filter finds nothing — 2 000 cached articles are searched by posting
        list, not by walking the DOM.

   Everything here is additive: if IndexedDB, the worker or the engine is
   missing, the dashboard behaves exactly as it did before and the telemetry
   capsule simply says so.
   ═══════════════════════════════════════════════════════════════════════════ */
(function(){
'use strict';

/* the maquette is a self-contained demo file: it must not register a worker or
   write into a database that would then leak into the next design review */
if(window.__MAQUETTE__){
  /* say so in the same capsule rather than leaving a dash hanging there */
  const item=document.getElementById('pwaItem'), txt=document.getElementById('pwaTxt'), dot=document.getElementById('pwaDot');
  if(txt) txt.textContent='Cache off (demo)';
  if(item){ item.setAttribute('data-mode','warn'); item.title='ماکت تک‌فایل: بدون سرور، بدون حافظهٔ آفلاین'; }
  if(dot) dot.className='pwa-dot is-idle';
  return;
}

const PWA_LABEL={boot:'Starting…', online:'Online (Synced)', syncing:'Syncing…',
                 offline:'Offline (Cache Mode)', error:'Storage Off'};
const PWA_STATE={mode:'boot', counts:null, sw:null, pruned:false, last:null};
const CACHE_PATHS=[['/api/data','data'],['/api/report/','report'],
                   ['/api/econ','econ'],['/api/article/','article']];

let SE_ENGINE=null, SE_OPEN=null, SEARCH_TOKEN=0;

function el(id){ return document.getElementById(id); }
function fa(n){ try{ return toFa(n); }catch(e){ return String(n); } }
function supported(){ return typeof indexedDB!=='undefined' && typeof window.StorageEngine==='function'; }

/* one engine per page; open() is idempotent, and a failure is remembered as
   "no cache" rather than retried on every call */
function engine(){
  if(SE_ENGINE) return SE_ENGINE;
  if(!supported()) return null;
  try{ SE_ENGINE=new StorageEngine(); }catch(e){ SE_ENGINE=null; }
  return SE_ENGINE;
}
function ready(){
  const eng=engine();
  if(!eng) return Promise.resolve(null);
  if(!SE_OPEN) SE_OPEN=eng.open().then(function(){ return eng; }).catch(function(e){
    console.warn('MohmdNewsDB unavailable:', e); return null;
  });
  return SE_OPEN;
}

/* ── status indicator ──────────────────────────────────────────────────── */
function status(mode, note){
  PWA_STATE.mode=mode;
  const item=el('pwaItem'), txt=el('pwaTxt'), dot=el('pwaDot');
  if(txt) txt.textContent=PWA_LABEL[mode]||mode;
  if(item){ item.setAttribute('data-mode', mode); item.title=tooltip(note); }
  if(dot) dot.className='pwa-dot '+(mode==='online'?'is-on':(mode==='offline'?'is-off':'is-idle'));
}
function tooltip(note){
  if(note) return note;
  const c=PWA_STATE.counts;
  const head = PWA_STATE.mode==='offline' ? 'حالت آفلاین: فید، گزارش‌ها و تقویم از حافظهٔ محلی خوانده می‌شوند'
            : PWA_STATE.mode==='error'  ? 'ذخیره‌سازی آفلاین در این مرورگر فعال نشد (فید کار می‌کند)'
            : 'همگام با سرور · ذخیره‌سازی آفلاین فعال';
  if(!c) return head;
  return head+' · '+fa(c.articles)+' خبر، '+fa(c.reports)+' گزارش، '+fa(c.calendar)+' رویداد، '
         +fa(c.terms)+' ترم نمایه‌سازی';
}
function refreshCounts(eng){
  const e=eng||engine();
  if(!e) return;
  e.stats().then(function(s){
    PWA_STATE.counts=s;
    const item=el('pwaItem'); if(item) item.title=tooltip();
  }).catch(function(){});
}

/* ── capture every JSON answer into the database ───────────────────────── */
function kindOf(url){
  if(typeof url!=='string' || url.charAt(0)!=='/') return null;
  for(let i=0;i<CACHE_PATHS.length;i++)
    if(url.indexOf(CACHE_PATHS[i][0])===0) return CACHE_PATHS[i][1];
  return null;
}
/* `/api/report/BTC?lang=fa` → "BTC", `/api/article/ab12` → "ab12". The index
   here was the bug that made every report land under the literal key
   "report" — invisible in the UI, which is exactly why it needed the browser
   check rather than a unit test. */
function pathArg(url){ return String(url).split('?')[0].split('/')[3] || ''; }
/* the calendar endpoint returns a WEEK OBJECT ({events, source, range}), not a
   list — concat'ing it directly threw and the cache silently stayed empty */
function calEvents(cal){
  if(!cal) return [];
  if(Array.isArray(cal)) return cal;
  return Array.isArray(cal.events)?cal.events:[];
}
function capture(kind, url, res){
  /* off the critical path on purpose: the caller already has its response */
  Promise.resolve().then(function(){
    return ready().then(function(eng){
      if(!eng || !res) return null;
      return res.json().then(function(json){ return {eng:eng, json:json}; });
    });
  }).then(function(ctx){
    if(!ctx) return null;
    const eng=ctx.eng, json=ctx.json;
    if(kind==='data'){
      const list=(json.articles||[]).concat(json.archive||[]);
      if(!list.length) return null;
      return eng.putArticles(list).then(function(){
        /* the small payload fields are stored so an offline boot gets the same
           toolbar, chips and asset names as a live one. Market prices are
           deliberately NOT kept here: stale quotes dressed as live ones are
           worse than no quotes — the worker's own /api/data cache covers the
           "show me the last snapshot" case, under the cache-mode indicator. */
        return eng.putMeta('data_meta', {
          ts: Date.now(),
          kind_labels: json.kind_labels || {}, kind_counts: json.kind_counts || {},
          topic_counts: json.topic_counts || {}, asset_counts: json.asset_counts || {},
          topics_meta: json.topics_meta || {}, assets_meta: json.assets_meta || {},
          config: json.config || null, rules: json.rules || null, stats: json.stats || null,
          server_time_fa: json.server_time_fa || '', interval_fa: json.interval_fa || ''
        });
      }).then(function(){
        /* bounded cache, one prune per page load — the retention window and the
           profile cap both live in the engine */
        if(PWA_STATE.pruned) return null;
        PWA_STATE.pruned=true;
        return eng.prune();
      }).then(function(){ refreshCounts(eng); });
    }
    if(kind==='report') return eng.putReport(pathArg(url), json).then(function(){ refreshCounts(eng); });
    if(kind==='econ'){
      const ev=calEvents(json.calendar).concat(calEvents(json.calendar_next));
      return Promise.resolve(ev.length?eng.putCalendar(ev):null)
        .then(function(){ return eng.putMeta('econ', {ts:Date.now(), data:json}); })
        .then(function(){ refreshCounts(eng); });
    }
    if(kind==='article') return eng.putMeta('body:'+pathArg(url), {ts:Date.now(), data:json});
    return null;
  }).catch(function(e){ /* a cache write may never break a request */ });
}

/* Wraps the global fetch. Installed while the document is still parsing, so the
   very first /api/data of the session is already captured. */
function wireFetch(){
  if(window.__pwaFetchWired || typeof window.fetch!=='function') return;
  window.__pwaFetchWired=true;
  const orig=window.fetch.bind(window);
  window.fetch=function(input, init){
    const url=(typeof input==='string')?input:((input&&input.url)||'');
    const method=String((init&&init.method)||(input&&input.method)||'GET').toUpperCase();
    const kind=kindOf(url);
    return orig(input, init).then(function(res){
      /* a worker-served answer is a cache answer: `X-MOHMD-Cache: hit` is set
         by sw.js, and treating it as a fresh sync would be the one lie this
         indicator must not tell */
      let mark='', fromCache=false;
      try{
        mark=res&&res.headers?String(res.headers.get('X-MOHMD-Cache')||''):'';
        fromCache=mark==='hit';
      }catch(e){}
      if(kind && method==='GET' && mark==='miss'){
        /* a worker that answered "I have nothing" is a failed request as far as
           the cache layer is concerned — but if it ever returns a response
           instead of failing, serve the local copy now */
        return fallback(kind, url).then(function(res2){ return res2||res; });
      }
      if(kind || url.indexOf('/api/')===0){
        PWA_STATE.last={ts:Date.now(), ok:!!(res&&res.ok)&&!fromCache, cache:fromCache, url:url};
        /* the payload request is remembered separately: by the time loadData()
           resolves, renderAll() has fired its own requests and the single
           "last request" slot would belong to one of those instead — which is
           how the offline boot ended up re-rendering instead of just saying
           that the data it already has is old */
        if(kind==='data') PWA_STATE.lastData=PWA_STATE.last;
      }
      if(fromCache) status('offline');
      if(kind && method==='GET' && res && res.ok){
        try{ capture(kind, url, res.clone()); }catch(e){}
      }
      return res;
    }, function(err){
      PWA_STATE.last={ts:Date.now(), ok:false, url:url};
      if(kind) return fallback(kind, url).then(function(res){ if(res) return res; throw err; });
      throw err;
    });
  };
}

/* Serve a request the network could not: the worker covers the whole-payload
   case, this covers the exact shapes the UI asks for by symbol / by id. */
function jres(data){
  return new Response(JSON.stringify(data), {status:200,
    headers:{'Content-Type':'application/json','X-MOHMD-Cache':'hit'}});
}
function fallback(kind, url){
  return ready().then(function(eng){
    if(!eng) return null;
    if(kind==='report') return eng.getReport(pathArg(url)).then(function(d){ return d?jres(d):null; });
    if(kind==='econ') return eng.getMeta('econ').then(function(m){
      if(m&&m.data) return jres(m.data);
      /* without the snapshot, rebuild the shape the renderer expects: it reads
         ECON.calendar.events, not a bare list */
      return eng.getCalendar().then(function(ev){
        return (ev&&ev.length)?jres({calendar:{events:ev, source:'local cache'}, offline:true}):null;
      });
    });
    if(kind==='article'){
      return eng.getMeta('body:'+pathArg(url)).then(function(m){ return (m&&m.data)?jres(m.data):null; });
    }
    return null;                       /* /api/data is rebuilt by hydrate() */
  }).then(function(res){ if(res) status('offline'); return res; })
    .catch(function(){ return null; });
}

/* ── offline boot: rebuild the feed from the cache ─────────────────────── */
function hydrate(){
  return ready().then(function(eng){
    if(!eng) return false;
    return Promise.all([eng.getArticles({limit:400}), eng.getMeta('data_meta')]).then(function(pair){
      const rows=pair[0], meta=pair[1];
      if(!rows.length) return false;
      if(!DATA) DATA={};
      DATA.articles=rows;
      DATA.archive=DATA.archive||[];
      DATA.offline=true;
      if(meta){
        /* the live payload's small fields, as captured with the last sync */
        DATA.kind_labels=DATA.kind_labels||meta.kind_labels||{};
        DATA.kind_counts=meta.kind_counts||{};
        DATA.topic_counts=meta.topic_counts||{};
        DATA.asset_counts=meta.asset_counts||{};
        DATA.topics_meta=DATA.topics_meta||meta.topics_meta||{};
        DATA.assets_meta=meta.assets_meta||{};
        DATA.config=DATA.config||meta.config;
        DATA.rules=meta.rules||null;
        DATA.stats=DATA.stats||meta.stats||null;
      }
      try{ if(typeof initMeta==='function') initMeta(); }catch(e){}
      if(DATA.stats) DATA.stats.cycle_running=false;
      /* renderAll() expects the whole payload (market, sources, macro…); the
         offline path re-runs only what the feed itself needs. Without this the
         source select stayed empty — and an empty select means its value is
         "", which the feed filter reads as "show only articles with no
         source": a silently blank feed (found in the browser, not in a test). */
      try{
        if(typeof renderSrcSel==='function') renderSrcSel();
        if(typeof renderKindSel==='function') renderKindSel();
        renderFeed();
      }catch(e){ console.warn('offline feed render:', e); }
      try{ toast('حالت آفلاین — فید از حافظهٔ محلی ('+fa(rows.length)+' خبر)'); }catch(e){}
      refreshCounts(eng);
      return true;
    });
  }).catch(function(){ return false; });
}

/* ── the search box falls back to the full-text index ──────────────────────
   The live filter only ever sees the current window. When it comes up empty
   and the query is a real word, the index is consulted instead: 2 000 cached
   articles ranked by posting lists, not by re-scanning the rendered cards. */
function cacheSearch(q){
  return ready().then(function(eng){
    if(!eng) return null;
    const token=++SEARCH_TOKEN;
    return eng.search(q, {limit:60}).then(function(res){
      if(!res || token!==SEARCH_TOKEN) return null;
      const box=el('q');
      if(!box || (box.value||'').trim()!==q) return null;   /* query moved on */
      const grid=el('newsGrid');
      /* "the live filter found nothing" is read from the feed itself, not from
         an empty child list: a virtualised grid always has its spacer and its
         layer in it, and asking the DOM whether it is empty would have made
         this fallback fire on a perfectly good feed */
      const blank=el('feedEmpty');
      const feedEmpty=(blank&&blank.style.display!=='none')||
                      (VS.feed?VS.feed.items.length===0:false);
      if(!grid || !feedEmpty || !res.articles.length) return null;
      vsGrid('feed','newsGrid',VS_OPTS_FEED, res.articles, res.articles.map(cardHTML).join(''));
      const cnt=el('feedCount');
      if(cnt) cnt.textContent=fa(res.articles.length)+' خبر · از حافظهٔ محلی ('+fa(res.took)+'ms)';
      const empty=el('feedEmpty');
      if(empty){ empty.style.display='block';
        empty.textContent='در فید زنده نبود — این نتایج از نمایهٔ محلی ('+fa(PWA_STATE.counts?PWA_STATE.counts.articles:0)+' خبر) خوانده شد'; }
      return res;
    });
  }).catch(function(){ return null; });
}

/* ── alert notifications through the worker when it is available ──────────
   A notification raised by the page dies with the tab; one raised by the
   registration survives a focus change, shows the icon, and is tappable. */
function wirePush(){
  if(window.__pwaPushWired || typeof window.arPush!=='function') return;
  window.__pwaPushWired=true;
  const orig=window.arPush;
  window.arPush=function(name, body){
    try{
      const reg=PWA_STATE.sw;
      if(reg && reg.showNotification && typeof Notification!=='undefined' && Notification.permission==='granted'){
        reg.showNotification(String(name||'MOHMD NEWS'), {body:String(body||''), tag:'mohmd-alert',
          lang:'fa', dir:'rtl', icon:'/icons/icon-192.png', badge:'/icons/icon-192.png', data:{url:'/'}});
        return true;
      }
    }catch(e){ /* fall through to the in-page path */ }
    return orig.apply(this, arguments);
  };
}

/* ── bookmarks: snapshots in the database, ids in localStorage ─────────── */
function mirrorBookmarks(){
  return ready().then(function(eng){
    if(!eng) return null;
    return eng.syncBookmarks(getBookmarks(), getBmarkMeta());
  }).catch(function(){ return null; });
}
function restoreBookmarks(){
  return ready().then(function(eng){
    if(!eng) return null;
    if(getBookmarks().length) return mirrorBookmarks();
    return eng.listBookmarks().then(function(rows){
      if(!rows.length) return null;
      const ids=[], meta={};
      rows.forEach(function(r){ ids.push(r.id); meta[r.id]=r; });
      try{ localStorage.setItem(BM_KEY, JSON.stringify(ids)); }catch(e){}
      try{ localStorage.setItem(BM_META_KEY, JSON.stringify(meta)); }catch(e){}
      try{ renderChips(); renderFeed(); renderBookmarks(); }catch(e){}
      return ids.length;
    });
  }).catch(function(){ return null; });
}

/* ── service worker ────────────────────────────────────────────────────── */
function registerWorker(){
  if(!('serviceWorker' in navigator)) return;
  if(location.protocol!=='http:' && location.protocol!=='https:') return;
  navigator.serviceWorker.register('/sw.js', {scope:'/'}).then(function(reg){
    PWA_STATE.sw=reg;
    const take=function(){
      if(reg.waiting && navigator.serviceWorker.controller){
        reg.waiting.postMessage({type:'SKIP_WAITING'});
        try{ toast('نسخهٔ جدید داشبورد فعال شد'); }catch(e){}
      }
    };
    take();
    if(reg.addEventListener) reg.addEventListener('updatefound', take);
    try{ navigator.serviceWorker.addEventListener('controllerchange', take); }catch(e){}
  }).catch(function(e){ console.warn('service worker:', e); });
  navigator.serviceWorker.addEventListener('message', function(ev){
    const d=ev.data||{};
    if(d.type==='SW_OFFLINE_TICK'){ status('offline'); markStaleCycle(); }
    if(d.type==='PONG'){
      /* the worker answers whether it has been serving from its caches; a
         response that arrived before this listener existed is covered here */
      if(d.lastCacheHit){ status('offline'); markStaleCycle(); }
      if(d.failures&&d.failures.length) console.warn('shell precache failures:', d.failures);
    }
    if(d.type==='SW_SHELL_PRIMED'){
      if(d.failures&&d.failures.length) console.warn('shell precache failures:', d.failures);
      else console.info('offline shell rebuilt (worker '+d.version+')');
    }
    if(d.type==='SW_SHELL_OK') console.info('offline shell present (worker '+d.version+')');
  });
}

/* ── boot ──────────────────────────────────────────────────────────────── */
function wireApp(){
  if(typeof window.loadData==='function' && !window.__pwaLoadWired){
    window.__pwaLoadWired=true;
    const orig=window.loadData;
    window.loadData=function(){
      return Promise.resolve(orig.apply(this, arguments)).then(function(r){
        const last=PWA_STATE.lastData||PWA_STATE.last;
        if(last && last.ok===false && !last.cache){
          return hydrate().then(function(hit){
            /* the feed is now local: say that where the cycle status lives */
            const ct2=el('cycleTxt'); if(ct2&&hit) ct2.textContent='حالت آفلاین — فید از حافظهٔ محلی';
            const cd2=el('cycleDot'); if(cd2&&hit) cd2.className='dot err';
            status(hit?'offline':'error', hit?null:'اتصال به سرور نیست و حافظهٔ محلی هم خالی است');
            return r;
          });
        }
        if(last && last.cache){
          /* the payload is real but old: say so where the cycle status is
             shown, or the cached "cycle running" text reads as live */
          const ct=el('cycleTxt');
          if(ct) ct.textContent='حالت آفلاین — داده ذخیرهشدهٔ آخر';
          const cd=el('cycleDot');
          if(cd){ cd.className='dot err'; cd.title='اتصال به سرور نیست — این داده ذخیره‌شدهٔ آخرین همگام‌سازی است'; }
          status('offline');
        } else {
          status(navigator.onLine?'online':'offline');
        }
        return r;
      });
    };
  }
  if(typeof window.toggleBookmark==='function' && !window.__pwaBmWired){
    window.__pwaBmWired=true;
    const orig=window.toggleBookmark;
    window.toggleBookmark=function(){ const r=orig.apply(this, arguments); mirrorBookmarks(); return r; };
    if(typeof window.clearBookmarks==='function'){
      const oc=window.clearBookmarks;
      window.clearBookmarks=function(){ const r=oc.apply(this, arguments); mirrorBookmarks(); return r; };
    }
  }
  if(typeof window.renderFeed==='function' && !window.__pwaFeedWired){
    window.__pwaFeedWired=true;
    const orig=window.renderFeed;
    window.renderFeed=function(){
      const r=orig.apply(this, arguments);
      try{
        const box=el('q');
        const q=box?String(box.value||'').trim():'';
        const grid=el('newsGrid');
        if(q.length>=2 && grid && !grid.children.length) cacheSearch(q);
      }catch(e){}
      return r;
    };
  }
  wirePush();
}

/* If the offline shell is missing (evicted, or cleared by another worker on
   this origin) the worker is asked to rebuild it while the server is up — the
   page is the only party that knows whether it is online. */
function ensureShell(){
  if(!('serviceWorker' in navigator) || !('caches' in window)) return;
  /* the worker owns the cache name — the page only asks it to check */
  const ask=function(w){ if(w&&w.postMessage) w.postMessage({type:'ENSURE_SHELL'}); };
  ask(navigator.serviceWorker.controller);
  if(navigator.serviceWorker.ready){
    navigator.serviceWorker.ready.then(function(reg){ ask(reg.active); }).catch(function(){});
  }
}

/* "the numbers on screen are real but old" — said where the cycle status is,
   because a cached payload still carries the last live cycle line */
function markStaleCycle(txt){
  try{
    const t=el('cycleTxt');
    if(t) t.textContent=txt||'حالت آفلاین — داده ذخیره‌شدهٔ آخر';
    const d=el('cycleDot');
    if(d){ d.className='dot err'; d.title='اتصال به سرور نیست — این دادهٔ آخرین همگام‌سازی است'; }
  }catch(e){}
}
function pingWorker(){
  const ctrl=navigator.serviceWorker&&navigator.serviceWorker.controller;
  if(ctrl&&ctrl.postMessage) ctrl.postMessage({type:'PING'});
}

function boot(){
  if(!supported()){ status('error', 'این مرورگر IndexedDB ندارد — فید بدون حافظهٔ آفلاین کار می‌کند');
    const item=el('pwaItem'); if(item) item.setAttribute('data-off','1'); return; }
  ensureShell();
  ready().then(function(eng){
    if(!eng){ status('error'); return; }
    status(navigator.onLine?'online':'offline');
    restoreBookmarks();
    refreshCounts(eng);
  });
  registerWorker();
  pingWorker();
  try{ if(navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(function(){}); }catch(e){}
  window.addEventListener('online', function(){ status('syncing'); });
  window.addEventListener('offline', function(){ status('offline'); });
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', wireApp);
  else wireApp();
}

/* fetch capture is installed synchronously (the first poll may already be in
   flight); everything that patches the dashboard's own functions waits for the
   script blocks above to have defined them */
wireFetch();
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', boot);
else boot();

/* a small read-only surface for the console, the tests and future views */
window.MohmdCache={
  engine:engine, open:ready, status:function(){ return PWA_STATE; },
  search:function(q, opts){ return ready().then(function(e){ return e?e.search(q, opts||{}):null; }); },
  stats:function(){ return ready().then(function(e){ return e?e.stats():null; }); },
  articles:function(opts){ return ready().then(function(e){ return e?e.getArticles(opts||{}):[]; }); },
  report:function(sym){ return ready().then(function(e){ return e?e.getReport(sym):null; }); },
  calendar:function(opts){ return ready().then(function(e){ return e?e.getCalendar(opts||{}):[]; }); },
  bookmarks:function(){ return ready().then(function(e){ return e?e.listBookmarks():[]; }); },
  prune:function(opts){ return ready().then(function(e){ return e?e.prune(opts||{}):0; }); },
  clear:function(store){ return ready().then(function(e){ return e?e.clear(store):[]; }); }
};
})();

/* Service worker: registerWorker() above is the only registration. A second
   one for '/static/sw.js' used to live here — that path is now a tombstone that
   unregisters itself, and registering it again on every load was pure noise. */
