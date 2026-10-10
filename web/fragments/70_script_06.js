


/* ═══════════════════════════════════════════════════════════════════════════
   FREEBUFF EXPANSION SUITE CONTROLLERS
   1. FreebuffWatchlist (واچ‌لیست اختصاصی دارایی‌ها)
   2. FreebuffBookmarks (پشتیبان‌گیری و بازیابی نشان‌شده‌ها)
   3. FreebuffOffline (مدیریت اتصال و وضعیت آفلاین)
   ═══════════════════════════════════════════════════════════════════════════ */


// ── 2. Watchlist Manager ───────────────────────────────────────────────────
const FreebuffWatchlist = (function(){
  const STORAGE_KEY = 'freebuff_watchlist';
  const DEFAULT_SYMS = ['BTC', 'ETH', 'SOL', 'XAU', 'WTI', 'EUR', 'DXY'];

  function get(){
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : DEFAULT_SYMS;
    } catch(e){
      return DEFAULT_SYMS;
    }
  }

  function set(list){
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
      if(typeof renderChips==='function') renderChips();
      if(typeof renderFeed==='function') renderFeed();
    } catch(e){}
  }

  function toggle(sym){
    let cur = get();
    if(cur.includes(sym)){
      cur = cur.filter(s => s !== sym);
    } else {
      cur.push(sym);
    }
    set(cur);
    renderGrid();
  }

  function selectAll(val){
    if(val && typeof orderedAssets==='function'){
      set(orderedAssets());
    } else {
      set([]);
    }
    renderGrid();
  }

  function openModal(){
    renderGrid();
    const ov = document.getElementById('watchlistOverlay');
    if(ov) ov.classList.add('open');
  }

  function renderGrid(){
    const grid = document.getElementById('watchlistGrid');
    if(!grid || typeof orderedAssets!=='function') return;
    const cur = get();
    const assets = orderedAssets();
    grid.innerHTML = assets.map(s => {
      const active = cur.includes(s);
      const name = typeof faAssetName==='function' ? faAssetName(s) : s;
      return `<div class="watchlist-card ${active?'active':''}" onclick="FreebuffWatchlist.toggle('${s}')">
        <span>${typeof assetIc==='function'?assetIc(s):'🪙'} <b>${esc(name)}</b></span>
        <span>${active ? '✅' : '⚪'}</span>
      </div>`;
    }).join('');
  }

  return { get, set, toggle, selectAll, openModal, renderGrid };
})();
window.FreebuffWatchlist = FreebuffWatchlist;

// ── 3. Bookmarks JSON Export/Import ─────────────────────────────────────────
const FreebuffBookmarks = (function(){
  function exportJSON(){
    const bmarks = (typeof getBookmarks==='function' ? getBookmarks() : []);
    const meta = (typeof getBmarkMeta==='function' ? getBmarkMeta() : {});
    const payload = { version: 1, exported_at: new Date().toISOString(), bookmarks: bmarks, metadata: meta };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'freebuff_bookmarks_' + new Date().toISOString().slice(0,10) + '.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    if(typeof toast==='function') toast('فایل پشتیبان نشان‌شده‌ها دانلود شد (' + toFa(bmarks.length) + ' خبر)');
  }

  function importJSON(ev){
    const file = ev.target.files && ev.target.files[0];
    if(!file) return;
    const reader = new FileReader();
    reader.onload = function(e){
      try {
        const data = JSON.parse(e.target.result);
        if(!data || !Array.isArray(data.bookmarks)) throw new Error('فایل نامعتبر است');
        const curBmarks = (typeof getBookmarks==='function' ? getBookmarks() : []);
        const curMeta = (typeof getBmarkMeta==='function' ? getBmarkMeta() : {});
        const mergedBmarks = Array.from(new Set([...curBmarks, ...data.bookmarks]));
        const mergedMeta = Object.assign({}, curMeta, data.metadata || {});
        localStorage.setItem('mohmd_bmarks', JSON.stringify(mergedBmarks));
        localStorage.setItem('mohmd_bmark_meta', JSON.stringify(mergedMeta));
        if(typeof renderBookmarks==='function') renderBookmarks();
        if(typeof renderChips==='function') renderChips();
        if(typeof toast==='function') toast('بازیابی موفق: ' + toFa(mergedBmarks.length) + ' خبر نشان‌شده در مرورگر بارگذاری شد');
      } catch(err){
        if(typeof toast==='function') toast('خطا در خواندن فایل: ' + err.message);
      }
    };
    reader.readAsText(file);
    ev.target.value = '';
  }

  return { exportJSON, importJSON };
})();
window.FreebuffBookmarks = FreebuffBookmarks;

// ── 5. Offline Status & Sync Listener ───────────────────────────────────────
window.addEventListener('offline', function(){
  const pwaTxt = document.getElementById('pwaTxt');
  const pwaItem = document.getElementById('pwaItem');
  if(pwaTxt) pwaTxt.textContent = 'آفلاین (حافظه محلی)';
  if(pwaItem) pwaItem.classList.add('offline-pill-active');
  if(typeof toast==='function') toast('📡 ارتباط اینترنت قطع شد — داشبورد در حالت آفلاین کار می‌کند');
});

window.addEventListener('online', function(){
  const pwaTxt = document.getElementById('pwaTxt');
  const pwaItem = document.getElementById('pwaItem');
  if(pwaTxt) pwaTxt.textContent = 'همگام‌شده';
  if(pwaItem) pwaItem.classList.remove('offline-pill-active');
  if(typeof toast==='function') toast('🟢 اتصال اینترنت برقرار شد — دریافت اطلاعات تازه...');
  if(typeof loadData==='function') loadData();
});

