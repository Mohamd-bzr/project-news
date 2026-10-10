/* ── the official TradingView Advanced Chart widget (free, key-less) ─────── */
const TV_SYMBOL={
  BTC:'BINANCE:BTCUSDT', ETH:'BINANCE:ETHUSDT', BNB:'BINANCE:BNBUSDT',
  SOL:'BINANCE:SOLUSDT', XRP:'BINANCE:XRPUSDT', ADA:'BINANCE:ADAUSDT',
  DOGE:'BINANCE:DOGEUSDT', LINK:'BINANCE:LINKUSDT',
  XAU:'OANDA:XAUUSD', XAG:'OANDA:XAGUSD', WTI:'TVC:USOIL',
  DXY:'TVC:DXY', SPX:'FOREXCOM:SPXUSD', VIX:'TVC:VIX'
};
const TV_INTERVAL={'5':'5','60':'60','4h':'240','1d':'D'};
function tvSymbolFor(sym){
  const s=String(sym||'').toUpperCase();
  if(TV_SYMBOL[s]) return TV_SYMBOL[s];
  const m=((DATA&&DATA.assets_meta&&DATA.assets_meta[s])||{});
  const y=String(m.yahoo||'').toUpperCase().trim();
  if(!y) return s;
  if(m.is_crypto||/-USD$/.test(y)) return 'BINANCE:'+y.replace(/-USD.*$/,'')+'USDT';
  return y;                            /* stocks and futures keep their ticker */
}
let TV_STAMP='';                       /* sym|tf|size the mounted widget serves */
let TV_FALLBACK_TIMER=null;
let TV_PING=null;                      /* the clock slot that watches for the iframe */
/* ── leaving a view must actually release it ─────────────────────────────
   The TradingView embed builds an iframe, a websocket to its own backend and a
   layout listener inside that frame; the fallback chart above builds a canvas
   and its own resize observer. Switching tabs used to leave both alive — a
   widget nobody can see, and the report tab paid for it on every visit. */
function tvTeardown(){
  if(TV_PING){ Clock.off(TV_PING); TV_PING=null; }
  if(TV_MOUNT_RETRY){ clearTimeout(TV_MOUNT_RETRY); TV_MOUNT_RETRY=null; }
  if(TV_FALLBACK_TIMER){ clearTimeout(TV_FALLBACK_TIMER); TV_FALLBACK_TIMER=null; }
  TV_STAMP='';
  const host=document.getElementById('tvholder');
  if(host) host.innerHTML='';
  const tag=document.getElementById('tvLiveTag');
  if(tag) tag.innerHTML='';
  const fail=document.getElementById('tvfail');
  if(fail) fail.style.display='none';
  if(document.body.classList.contains('tv-full')){
    document.body.classList.remove('tv-full');
    const box=document.getElementById('chartBox');
    if(box) box.classList.remove('tvfull');
    const b=document.getElementById('tvFullBtn');
    if(b){ b.classList.remove('on'); b.innerHTML='⛶ بزرگ‌نمایی'; }
  }
}
/* What leaving a view releases, and what it deliberately keeps.

   The TradingView embed goes: it is an iframe with its own connection to its
   own backend, it is the single most expensive thing this page can hold, and
   showView() re-mounts it from scratch on the way back in.

   The windowed grids keep their rows: those rows are a few dozen nodes, and
   they *are* the reader's scroll position. */
function teardownView(prev){
  if(prev==='reports') tvTeardown();
}
/* the page may be closed from any view, including the one holding the embed */
if(typeof window!=='undefined'&&window.addEventListener)
  window.addEventListener('pagehide', function(){ try{ tvTeardown(); }catch(e){} });
function mountTVChart(force){
  const host=document.getElementById('tvholder'), rep=window.__rep;
  if(!host||!rep) return;
  /* The widget measures its container once, at mount. Doing that while the
     reports tab is still hidden sizes the iframe to nothing and it never
     re-measures — which is why the chart used to come back tiny. Wait for the
     tab instead of mounting blind. Do NOT test offsetParent here: inside the
     fullscreen panel the ancestor is position:fixed and offsetParent is null
     for every element in the subtree, which would block exactly the case we
     just resized for. A real box is what we need. */
  const hr = host.getBoundingClientRect();
  if(!(hr.width > 4 && hr.height > 4)){
    if(TV_MOUNT_RETRY) clearTimeout(TV_MOUNT_RETRY);
    TV_MOUNT_RETRY=setTimeout(()=>mountTVChart(true),200);
    return;
  }
  if(TV_MOUNT_RETRY){ clearTimeout(TV_MOUNT_RETRY); TV_MOUNT_RETRY=null; }
  const sym=rep.symbol||'';
  const stamp=sym+'|'+TVW.tf+'|'+(document.body.classList.contains('tv-full')?'full':'inline');
  if(!force&&TV_STAMP===stamp&&host.querySelector('iframe')) return;
  TV_STAMP=stamp;
  const fail=document.getElementById('tvfail'); if(fail) fail.style.display='none';
  host.innerHTML='<div class="tradingview-widget-container" style="block-size:100%">'
    +'<div class="tradingview-widget-container__widget" style="block-size:100%"></div></div>';
  const box=host.querySelector('.tradingview-widget-container__widget');
  const conf={
    autosize:true, symbol:tvSymbolFor(sym), interval:TV_INTERVAL[TVW.tf]||'60',
    timezone:'Asia/Tehran', theme:(document.documentElement.getAttribute('data-theme')==='light'?'light':'dark'), style:'1', locale:'en',
    /* the widget ships a cool blue-black; the app is midnight navy with an
       electric-blue accent, and the hole it used to punch in the palette was
       the loudest thing on the report tab. Same depth, same hairline colour. */
    backgroundColor:(document.documentElement.getAttribute('data-theme')==='light'?'rgba(252,253,255,1)':'rgba(12,17,28,1)'), gridColor:(document.documentElement.getAttribute('data-theme')==='light'?'rgba(20,32,46,0.08)':'rgba(160,180,210,0.07)'),
    fontColor:'#AFB9C8',
    hide_side_toolbar:false, allow_symbol_change:true, withdateranges:true,
    save_image:true, hide_volume:false, support_host:'https://www.tradingview.com'
  };
  const sc=document.createElement('script');
  sc.type='text/javascript'; sc.async=true;
  sc.src='https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
  sc.innerHTML=JSON.stringify(conf);
  sc.onerror=()=>showTvFail();                      /* blocked / offline */
  box.appendChild(sc);
  /* the live pill lights up only once the widget has really mounted */
  let tries=0;
  const ping=Clock.every(500, ()=>{
    if(TV_PING!==ping) return;                 /* a newer mount owns the slot */
    const tag=document.getElementById('tvLiveTag');
    if(host.querySelector('iframe')){
      Clock.off(ping); TV_PING=null;
      if(tag) tag.innerHTML='<span class="live-dot"></span>لایو';
      return;
    }
    if(++tries>26){ Clock.off(ping); TV_PING=null; }
  }, {label:'tv-ping'});
  TV_PING=ping;
  if(TV_FALLBACK_TIMER) clearTimeout(TV_FALLBACK_TIMER);
  TV_FALLBACK_TIMER=setTimeout(()=>{
    if(TV_STAMP!==stamp) return;
    if(!host.querySelector('iframe')) showTvFail();
  }, 15000);
}
/* the widget could not mount: blocked, offline, or simply slow. Say exactly
   that, and point at the chart on TradingView — there is no second chart in
   the app to quietly substitute. */
function showTvFail(msg){
  const fail=document.getElementById('tvfail');
  if(!fail) return;
  fail.style.display='block';
  const sym=(window.__rep&&window.__rep.symbol)||'';
  const url='https://www.tradingview.com/chart/?symbol='+encodeURIComponent(tvSymbolFor(sym));
  fail.innerHTML=(msg||'نمودار تریدینگ‌ویو بارگذاری نشد (اینترنت یا تاخیر ویجت).')+
    ` <a class="mlink" href="${url}" target="_blank" rel="noopener">باز کردن در تریدینگ‌ویو</a>`;
}
/* «⛶ بزرگ‌نمایی»: the panel leaves the grid and fills the viewport */
function toggleTvFull(){
  const box=document.getElementById('chartBox'); if(!box) return;
  const on=box.classList.toggle('tvfull');
  document.body.classList.toggle('tv-full', on);
  const b=document.getElementById('tvFullBtn');
  if(b){ b.innerHTML=on?'🗗 بستن تمام‌صفحه':'⛶ بزرگ‌نمایی'; b.classList.toggle('on', on); }
  if(on&&window.__rep) mountTVChart(true);
  setTimeout(()=>{ try{ window.dispatchEvent(new Event('resize')); }catch(e){} }, 80);
}
function exitTvFull(){
  const box=document.getElementById('chartBox');
  if(box&&box.classList.contains('tvfull')) toggleTvFull();
}
/* ── report helpers ───────────────────────────────────────────────────────── */
/* one citation row: number, Persian title, English original, source, date,
   time and credibility. The row itself opens the article. */
function citeHTML(it, fa){
  const link=it.link||'';
  const inner=`<span class="idx">${toFa(it.index_fa||it.index||'')}</span>
    <span class="ct-body">
      <span class="ct-t">${esc(it.title_fa||it.title_en||'')}</span>
      ${it.title_fa?`<span class="ct-en">${esc(it.title_en||'')}</span>`:''}
      <span class="ct-meta">
        <span class="ct-src">${esc(it.source||'')}</span>
        ${it.date_fa?`<span>${ic('calendar')} ${esc(it.date_fa)}</span>`:''}
        ${it.time_fa?`<span>${ic('clock')} ${esc(it.time_fa)}</span>`:''}
        ${it.credibility_fa?`<span class="ct-cred">${ic('check')} ${esc(it.credibility_fa)}</span>`:''}
      </span>
      ${(!fa&&it.why_en)?`<span class="why" dir="ltr">${esc(it.why_en)}</span>`:''}
    </span>`;
  return link
    ? `<a class="cite" href="${attr(safeUrl(link))}" target="_blank" rel="noopener">${inner}<span class="ct-go">↗</span></a>`
    : `<div class="cite">${inner}<span></span></div>`;
}
/* the sources button: one click opens the list for that section */
function toggleCites(btn){
  const box=btn.closest('.cites'); if(!box) return;
  const open=box.classList.toggle('open');
  btn.setAttribute('aria-expanded', open?'true':'false');
  const a=btn.querySelector('.cb-a');
  if(a) a.textContent=open?'بستن منابع':'نمایش منابع';
}
/* ══ FILTER MODEL 3 — the shared toolbar ═══════════════════════════════════
   Every view now shows ONE line: the filter button with a live count of what
   is switched on, those filters as removable chips, and the result count.
   The sheet that drops out of the button holds every control. Nothing here
   changes what a filter *does* — the same selects and chip containers drive
   the same renderers, they are just not in the reader's face until asked. */
function tbCloseAll(except){
  document.querySelectorAll('.fsheet.open').forEach(s=>{ if(s!==except) s.classList.remove('open'); });
  document.querySelectorAll('.tb-btn[aria-expanded="true"]').forEach(b=>{
    const s=b.getAttribute('aria-controls')&&document.getElementById(b.getAttribute('aria-controls'));
    if(!s||s!==except) b.setAttribute('aria-expanded','false');
  });
}
function tbToggle(id){
  const sheet=document.getElementById(id); if(!sheet) return;
  const open=!sheet.classList.contains('open');
  tbCloseAll(open?sheet:null);
  sheet.classList.toggle('open', open);
  const bar=sheet.closest('.tb');
  const btn=bar?bar.querySelector('.tb-btn'):null;
  if(btn) btn.setAttribute('aria-expanded', open?'true':'false');
  if(open){
    /* the sheet must fit the room left *below its button*, not a fixed slice of
       the viewport — otherwise the footer (and “clear all”) sits off-screen on
       short windows. */
    if(bar){
      try{
        const r=bar.getBoundingClientRect();
        const room=Math.max(240, Math.min(window.innerHeight-r.bottom-18, Math.round(window.innerHeight*0.72)));
        sheet.style.maxBlockSize=room+'px';
      }catch(e){}
    }
    const f=sheet.querySelector('input[type=text],input:not([type])');
    if(f){ try{ f.focus({preventScroll:true}); }catch(e){} }
  }
}
function tbClose(id){ const s=document.getElementById(id); if(s) s.classList.remove('open'); }
/* Clicking outside or pressing Esc puts the page back to its quiet state.
   The hit is remembered in the CAPTURE phase on purpose: a click inside the
   sheet can delete the very node it landed on (setAssetFilter re-renders the
   chip grid), so by the time the event bubbles to the document the target is
   detached and closest('.tb') is null — which used to close the sheet on every
   single filter toggle. Detached targets are ignored for the same reason. */
let TB_HIT = false;
document.addEventListener('click', e=>{
  const t=e.target;
  TB_HIT = !!(t && t.closest && t.closest('.tb'));
}, true);
document.addEventListener('click', e=>{
  const t=e.target;
  if(TB_HIT || (t && t.isConnected === false)) return;
  tbCloseAll(null);
});
document.addEventListener('keydown', e=>{ if(e.key==='Escape') tbCloseAll(null); });
/* a resize re-flows the page under an open sheet; put it away rather than leave
   it pointing at a button that has moved */
window.addEventListener('resize', ()=>tbCloseAll(null));
function tbChipHTML(label, act){
  return `<button class="tb-chip" title="حذف این فیلتر" onclick="${act}">${label}<span class="x">✕</span></button>`;
}
/* items = [[label, onclick], …]; assetChip is an optional non-removable chip */
function tbPaint(badgeId, liveId, btnId, items, assetChip, lang){
  /* the calendar's toolbar reads in English, the rest of the app in Persian */
  const en = lang === 'en';
  const badge=document.getElementById(badgeId), live=document.getElementById(liveId), btn=document.getElementById(btnId);
  if(badge){ const n=en?String(items.length):toFa(items.length); badge.textContent=n; badge.setAttribute('data-n', String(items.length)); }
  if(btn) btn.classList.toggle('on', items.length>0);
  if(!live) return;
  let h = assetChip || '';
  h += items.slice(0,4).map(it=>tbChipHTML(it[0], it[1])).join('');
  if(items.length>4) h += `<span class="tb-chip more">+${en?String(items.length-4):toFa(items.length-4)} ${en?'more filters':'فیلتر دیگر'}</span>`;
  live.innerHTML = h;
}
function valOf(id){ const el=document.getElementById(id); return el?el.value:''; }
function txtOf(sel){
  const el=document.querySelector(sel); if(!el) return '';
  const o=el.options?el.options[el.selectedIndex]:null;
  return String((o&&o.textContent)||el.value||'').trim();
}
function faAssetName(sym){
  const m=((typeof DATA!=='undefined'&&DATA&&DATA.assets_meta)||{})[sym]||{};
  const v=m.fa;
  return (v&&!isAsciiName(v))?v:(ASSET_FA_FALLBACK[sym]||v||sym);
}
/* topics arrive from the feed in English; the map above carries the Persian
   name for every one the scraper emits */
function faTopic(t){ return FA_TOPIC[t]||t||''; }
function setSel(id,v){ const el=document.getElementById(id); if(el){ el.value=v; renderFeed(); } }
function setCred(v){
  const s=document.getElementById('credSlider'), cv=document.getElementById('credVal');
  if(s) s.value=v;
  if(cv) cv.textContent=toFa(v)+'٪';
  renderFeed();
}
function setQ(v){ const q=document.getElementById('q'); if(q) q.value=v; renderFeed(); }
function renderFeedToolbar(){
  const items=[];
  if(UI.onlyBookmarked) items.push([ic('star')+' نشان‌شده‌ها', "UI.onlyBookmarked=false;renderChips();renderFeed()"]);
  if(UI.asset&&UI.asset!=='all') items.push([assetIc(UI.asset)+' '+faAssetName(UI.asset), "setAssetFilter('"+UI.asset+"')"]);
  if(UI.topic&&UI.topic!=='all') items.push([topicIc(UI.topic)+' '+(FA_TOPIC[UI.topic]||UI.topic), "setTopicFilter('"+UI.topic+"')"]);
  const kind=valOf('kindSel');
  if(kind&&kind!=='all') items.push([ic('book')+' '+(((typeof DATA!=='undefined'&&DATA&&DATA.kind_labels)||{})[kind]||kind), "setSel('kindSel','all')"]);
  const src=valOf('srcSel');
  if(src&&src!=='all') items.push([ic('bank')+' '+esc(src), "setSel('srcSel','all')"]);
  const cred=parseInt(valOf('credSlider')||'0',10)||0;
  if(cred>0) items.push([ic('star')+' اعتبار ≥ '+toFa(cred)+'٪', 'setCred(0)']);
  const sort=valOf('sortSel');
  if(sort&&sort!=='new') items.push(['⇅ '+esc(txtOf('#sortSel')), "setSel('sortSel','new')"]);
  const q=document.getElementById('q');
  if(q&&q.value.trim()) items.push([ic('search')+' «'+esc(q.value.trim().slice(0,16))+'»', "setQ('')"]);
  tbPaint('feedBadge','feedLive','feedBtn',items);
}
function renderIdeasToolbar(){
  const sym=ideasSym();
  const items=[];
  const kind=UI.ideasKind||'all';
  if(kind!=='all') items.push([ic('grid')+' '+esc(txtOf('#ideasKindChips')), "setIdeasKind('all')"]);
  const tf=UI.ideasTf||'all';
  /* the timeframe list is built from the ideas that actually loaded, so the
     select can legitimately have no matching option yet — name the value itself */
  if(tf!=='all') items.push([ic('clock')+' '+esc(txtOf('#ideasTfChips')||tfLabel(tf)), "setIdeasTf('all')"]);
  const srt=UI.ideasSort||'popular';
  if(srt!=='popular') items.push(['⇅ '+esc(txtOf('#ideasSortChips')), "setIdeasSort('popular')"]);
  tbPaint('ideasBadge','ideasLive','ideasBtn',items);
  const cnt=document.getElementById('ideasCount'), c=IDEAS_CACHE[sym];
  if(cnt) cnt.textContent = c ? (c.err ? '—' : (toFa((c.items||[]).length)+' ایده')) : 'در حال خواندن…';
}
function renderEtfToolbar(){
  const nm=document.getElementById('etfBtnName');
  if(nm){ const g=UI.etfGroup||'all'; nm.textContent = g==='all' ? 'همه' : (ETF_GROUP_FA[g]||g); }
  const btn=document.getElementById('etfBtn'); if(btn) btn.classList.toggle('on', (UI.etfGroup||'all')!=='all');
}
/* the calendar keeps all six controls, but only the ones you changed show on
   the line — including the timezone, which is easy to forget you moved */
function renderCalToolbar(){
  const items=[];
  const imp=valOf('calImpact');
  if(imp&&imp!=='all') items.push([ic('target')+' '+esc(txtOf('#calImpact')), "setSelCal('calImpact','all')"]);
  const ccys=[...(CAL.ccys||[])];
  if(ccys.length) items.push([ic('swap')+' '+ccys.map(esc).join(', '), "clearCalCcy();renderCalendar()"]);
  const srt=valOf('calSort');
  if(srt&&srt!=='time') items.push(['⇅ '+esc(txtOf('#calSort')), "setSelCal('calSort','time')"]);
  const tz=valOf('calTz');
  if(tz&&tz!=='Asia/Tehran') items.push([ic('clock')+' '+esc(txtOf('#calTz')), "setSelCal('calTz','Asia/Tehran')"]);
  const q=document.getElementById('calQ');
  if(q&&q.value.trim()) items.push([ic('search')+' «'+esc(q.value.trim().slice(0,16))+'»', "setCalQ('')"]);
  const hp=document.getElementById('calHidePast');
  if(hp&&hp.checked) items.push([ic('eye-off')+' released hidden', 'setCalHidePast(false)']);
  tbPaint('calBadge','calLive','calBtn',items,null,'en');
  /* the result count on the far side of the line — the feed and the ideas tab
     both carry one, the calendar's slot was painted empty */
  const cnt=document.getElementById('calFiltersCount');
  if(cnt){
    const n=(window.__calDayCount||0);
    cnt.innerHTML='<b>'+n+'</b> '+(n===1?'event':'events');
  }
}
function setSelCal(id,v){ const el=document.getElementById(id); if(el){ el.value=v; renderCalendar(); } }
function toggleCalCcy(inp){
  if(!CAL.ccys) CAL.ccys=new Set();
  if(inp.checked) CAL.ccys.add(inp.value); else CAL.ccys.delete(inp.value);
  const lab=inp.closest('.ccy'); if(lab) lab.classList.toggle('on', inp.checked);
  renderCalendar();
}
function clearCalCcy(){
  CAL.ccys=new Set();
  document.querySelectorAll('#calCurChips input[type=checkbox]').forEach(function(i){
    i.checked=false; const l=i.closest('.ccy'); if(l) l.classList.remove('on');
  });
}
function setCalQ(v){ const q=document.getElementById('calQ'); if(q) q.value=v; renderCalendar(); }
function setCalHidePast(v){ const hp=document.getElementById('calHidePast'); if(hp) hp.checked=!!v; renderCalendar(); }
function resetCalFilters(){
  const set=(id,v)=>{ const el=document.getElementById(id); if(el) el.value=v; };
  set('calImpact','all'); set('calSort','time'); set('calTz','Asia/Tehran');
  clearCalCcy();
  const q=document.getElementById('calQ'); if(q) q.value='';
  const hp=document.getElementById('calHidePast'); if(hp) hp.checked=false;
  renderCalendar();
  if(typeof toast==='function') toast('Calendar filters cleared');
}
/* ── filter bar helpers ───────────────────────────────────────────────────── */
function syncFeedReset(){
  const btn=document.getElementById('feedReset'); if(!btn) return;
  const val=id=>{ const el=document.getElementById(id); return el?el.value:''; };
  const q=document.getElementById('q');
  const on=(UI.asset&&UI.asset!=='all')||(UI.topic&&UI.topic!=='all')||UI.onlyBookmarked
    ||val('srcSel')!=='all'||val('kindSel')!=='all'||val('sortSel')!=='new'
    ||(+val('credSlider')||0)>0||!!(q&&q.value.trim());
  btn.hidden=!on;
  if(typeof renderFeedToolbar==='function') renderFeedToolbar();   /* FILTER MODEL 3 toolbar */
}
function resetFeedFilters(){
  UI.asset='all'; UI.topic='all'; UI.onlyBookmarked=false;
  const q=document.getElementById('q'); if(q) q.value='';
  const set=(id,v)=>{ const el=document.getElementById(id); if(el) el.value=v; };
  set('sortSel','new'); set('kindSel','all'); set('srcSel','all'); set('credSlider',0);
  const cv=document.getElementById('credVal'); if(cv) cv.textContent='۰٪';
  renderChips(); renderFeed();
  toast('فیلترها پاک شد');
}
/* jump inside the report pane without moving the whole page */
function jumpRepSec(id){
  const doc=document.getElementById('repDoc'), el=document.getElementById(id);
  if(!doc||!el) return;
  const top=doc.scrollTop+(el.getBoundingClientRect().top-doc.getBoundingClientRect().top)-10;
  try{ doc.scrollTo({top:top, behavior:'smooth'}); }catch(e){ doc.scrollTop=top; }
}
