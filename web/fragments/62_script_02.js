// Sidebar Toggle Helper for Mobile
function toggleSidebar(){
  const s = document.getElementById('appSidebar');
  const b = document.getElementById('sidebarBackdrop');
  if(!s) return;
  s.classList.toggle('open');
  if(b) b.classList.toggle('open');
}
// Keyboard shortcuts
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    const q = document.getElementById('q');
    if (q && document.activeElement === q) { q.value = ''; renderFeed(); }
    ['artOverlay', 'blurbOverlay', 'calDocOverlay', 'ideaOverlay'].forEach(id => closeModal(id));
    if (typeof exitTvFull === 'function') exitTvFull();
  }
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    if (typeof cmdkOpen === 'function') cmdkOpen();
  }
});

/* the rail's own collapse toggle — the state lives on <body> and is remembered
   per browser, so the icon rail comes back the way you left it */
function toggleRail(){
  const on=document.body.classList.toggle('dl2-rail-collapsed');
  const b=document.getElementById('railToggle');
  if(b) b.setAttribute('aria-expanded', on?'false':'true');
  try{ localStorage.setItem('dl2_rail', on?'1':'0'); }catch(e){}
}
try{
  if(localStorage.getItem('dl2_rail')==='1'){
    document.body.classList.add('dl2-rail-collapsed');
    document.getElementById('railToggle').setAttribute('aria-expanded','false');
  }
}catch(e){}

let DATA = null;
let _LOADING = false;
let _ART_GEN = 0;
let UI = {topic:'all', asset:'all', kind:'all', view:'feed', repSym:null, repLang:'en', repSections:null, onlyBookmarked:false,
          /* ideas tab: TradingView-style sort + badge filters */
          ideasSym:null, ideasSort:'popular', ideasKind:'all', ideasTf:'all',
          /* ETF board: family filter + free-text search */
          etfGroup:'all', etfQ:''};
let TVW = {sym:null, tf:'60'};    /* نمودار لایو: دارایی و تایم‌فریم فعال */
let TV_MOUNT_RETRY = null;        /* mounting a hidden widget sizes it to zero */
let LIVE = {};            /* sym -> {price, change_24h, src} from /api/live */

const FA_TOPIC = {regulation:'مقررات',institutional:'نهادی',etf:'ای‌تی‌اف',macro:'کلان',security:'امنیت',
  analysis:'تحلیل',defi:'دیفای',market:'بازار',tech:'فناوری',general:'عمومی'};
const FA_ASSET = {}, ASSET_ICONS = {};
/* The registry stores the names the operator typed, and for the majors that is
   still the English word (fa:"Bitcoin"). The interface reads Persian, so a name
   with no Persian letter in it falls back to the built-in label below — the data
   itself is never rewritten, and a custom asset keeps whatever was entered. */
const ASSET_FA_FALLBACK={BTC:'بیت‌کوین',ETH:'اتریوم',BNB:'بایننس‌کوین',SOL:'سولانا',XRP:'ریپل',
  ADA:'کاردانو',DOGE:'دوج‌کوین',LINK:'چین‌لینک',XAU:'طلا',XAG:'نقره',WTI:'نفت WTI',
  DXY:'دلار DXY',SPX:'اس‌اند‌پی ۵۰۰',VIX:'شاخص ترس VIX'};
const isAsciiName = w => !/[^\x00-\x7F]/.test(String(w||''));

/* Chart palette — mirrors the :root tokens above (SVG presentation attributes
   must use concrete colours, var() only works in style=""). */
const C = {
  price:'#6C97DC', priceTxt:'#DCE6F4',
  ema20:'#5FA8D3', ema50:'#E8A23C', ema200:'#8D99AB',
  band:'rgba(95,168,211,.08)', bandLine:'rgba(95,168,211,.22)',
  grid:'#1D2432', axis:'#8D99AB',
  sup:'#2EBD77', res:'#EE6A58',
  rsi:'#93B6E8',
  up:'rgba(46,189,119,.5)', down:'rgba(238,106,88,.5)',
  vol:'rgba(95,168,211,.28)',
  cup:'#2EBD77', cdn:'#EE6A58'
};

/* importance order for the top strip and every asset list */
const ASSET_ORDER = ['BTC','ETH','BNB','SOL','XRP','ADA','DOGE','LINK','XAU','XAG','WTI','DXY','SPX','VIX'];
const IMPORTANCE = {};
ASSET_ORDER.forEach((s,i)=>IMPORTANCE[s]=i);
function importance(sym){ return IMPORTANCE[sym]!=null ? IMPORTANCE[sym] : 900+String(sym).length; }
function orderedAssets(){
  if(!DATA) return [];
  /* a partial payload (the news channel arrives before /api/data) must not
     throw here — these three reads used to assume config was already set */
  const cfgAssets=(DATA.config&&DATA.config.assets)||[], aMeta=DATA.assets_meta||{};
  const custom=Object.keys(aMeta).filter(s=>aMeta[s]&&aMeta[s].custom&&cfgAssets.includes(s));
  return cfgAssets.slice().sort((a,b)=>importance(a)-importance(b))
    .concat(custom.filter(s=>!cfgAssets.includes(s)));
}

function initMeta(){
  if(!DATA) return;
  for(const [k,v] of Object.entries(DATA.assets_meta||{})){
    FA_ASSET[k]=(v.fa&&!isAsciiName(v.fa))?v.fa:(ASSET_FA_FALLBACK[k]||v.fa||k);
    ASSET_ICONS[k]=v.icon;
  }
}
function toFa(n){ return String(n==null?'':n).replace(/\d/g,d=>'۰۱۲۳۴۵۶۷۸۹'[d]); }
/* ══ MARKUP SAFETY — the single gate between upstream strings and the DOM ══
   One helper, `esc()`, used to do three different jobs, and it did the third
   one badly: it escaped ' as \' so that a value could be dropped inside a JS
   string that lives in an attribute (`onclick="fn('…')"`). That promise holds
   for a quote and fails for a backslash — a feed id of `a\'` closes the string
   and the rest of the attribute becomes script. Escaping is also the wrong
   answer for a URL: `href="${esc('javascript:…')}"` is escaped and still
   executes, because the HTML parser decodes character references *before* the
   URL is interpreted.

   The jobs are now separate and each call site says which one it means:
     · esc(v)   text and attribute values — no quotes-as-JS trick
     · attr(v)  same thing, named for the attribute position it sits in
     · jsArg(v) a value about to sit inside a JS string in an attribute;
                emits a real JSON literal, then attribute-escapes that
     · safeUrl(v) a URL from a feed; returns '' unless the resolved scheme is
                allowed (no javascript:, no data:text/html)
   `Sanitizer.sanitize` stays available for the day a component *wants*
   upstream markup instead of rebuilding it — nothing in the app asks for that
   today, and the reason is worth keeping written down. */
const SAN_CTRL=/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g;
const SAN_NAMED={amp:'&',lt:'<',gt:'>',quot:'"',apos:"'",colon:':',tab:'\t',newline:'\n',nbsp:' '};
function sanDecode(s){
  return String(s==null?'':s)
    .replace(/&#x([0-9a-f]+);?/gi,function(m,h){ return String.fromCharCode(parseInt(h,16)); })
    .replace(/&#(\d+);?/g,function(m,d){ return String.fromCharCode(+d); })
    .replace(/&([a-z]+);/gi,function(m,n){ const v=SAN_NAMED[n.toLowerCase()]; return v==null?m:v; });
}
function esc(s){
  return String(s==null?'':s).replace(SAN_CTRL,'')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
function attr(s){ return esc(s); }
/* JSON.stringify already escapes " and \; the two characters it leaves that
   matter here are < (which attribute-escapes to &lt; on the way out) and the
   JS line separators, which are valid JSON in 2019+ output but are still not
   allowed raw inside a script. */
function jsLit(v){
  return JSON.stringify(v==null?'':String(v))
    .replace(/</g,'\\u003c').replace(/\u2028|\u2029/g,function(c){
      return '\\u'+c.charCodeAt(0).toString(16); });
}
function jsArg(v){
  return jsLit(v).replace(/&/g,'&amp;').replace(/"/g,'&quot;');
}
const SAN_URL_ATTR={href:1,src:1,srcset:1,'xlink:href':1};
const SAN_TAG_ALLOW={A:1,ABBR:1,B:1,BLOCKQUOTE:1,BR:1,CITE:1,CODE:1,DD:1,DIV:1,DL:1,DT:1,
  EM:1,FIGCAPTION:1,FIGURE:1,H1:1,H2:1,H3:1,H4:1,H5:1,H6:1,HR:1,I:1,IMG:1,LI:1,MARK:1,
  OL:1,P:1,PRE:1,Q:1,S:1,SECTION:1,SMALL:1,SPAN:1,STRONG:1,SUB:1,SUP:1,TABLE:1,TBODY:1,
  TD:1,TFOOT:1,TH:1,THEAD:1,TIME:1,TR:1,U:1,UL:1,WBR:1};
const SAN_ATTR_ALLOW={alt:1,class:1,colspan:1,dir:1,headers:1,height:1,href:1,id:1,lang:1,
  loading:1,referrerpolicy:1,rel:1,rowspan:1,scope:1,sizes:1,src:1,srcset:1,target:1,title:1,width:1};
const SAN_ATTR_DROP={srcset:1};
function sanAllowedTag(name){ return !!SAN_TAG_ALLOW[String(name||'').toUpperCase()]; }
function sanAllowedAttr(name){
  const n=String(name||'').toLowerCase();
  if(n.slice(0,2)==='on') return false;              /* every inline handler */
  if(n.slice(0,5)==='data-') return true;
  if(n==='style') return false;                       /* css can exfiltrate */
  return !!SAN_ATTR_ALLOW[n];
}
function safeUrl(u){
  const raw=String(u==null?'':u).replace(SAN_CTRL,'').trim();
  if(!raw) return '';
  /* probe what the browser would actually resolve: entity-decoded, with all
     whitespace removed, because `java&#x09;script:` is one scheme to the URL
     parser and three tokens to a naive substring check */
  const probe=sanDecode(raw).replace(/[\s\u0000-\u001f]/g,'').toLowerCase();
  const m=/^([a-z][a-z0-9+.\-]*):/.exec(probe);
  if(!m) return raw;                                  /* relative, #frag, ?query, //host */
  const scheme=m[1];
  if(scheme==='http'||scheme==='https'||scheme==='mailto'||scheme==='tel') return raw;
  if(scheme==='data'&&/^data:image\/(?:png|jpe?g|gif|webp|avif)[;,]/i.test(probe)) return raw;
  return '';
}
const Sanitizer={
  tags:SAN_TAG_ALLOW, attrs:SAN_ATTR_ALLOW, urlAttrs:SAN_URL_ATTR,
  decoder:sanDecode, allowedTag:sanAllowedTag, allowedAttr:sanAllowedAttr, url:safeUrl,
  stats:{calls:0, droppedTags:0, droppedAttrs:0, droppedUrls:0, noParser:0},
  /* A DOM walk, not a regex: the browser has already parsed the string into a
     tree, so a `<svg><script>` in a comment, a malformed tag or an ambiguous
     attribute cannot slip past a pattern I failed to imagine. Unknown tags are
     unwrapped with their text kept, so a stray <div> in a feed summary costs
     formatting rather than content. */
  sanitize:function(html){
    Sanitizer.stats.calls++;
    const src=String(html==null?'':html);
    if(!src) return '';
    if(typeof DOMParser!=='function'){ Sanitizer.stats.noParser++; return esc(src); }
    let doc;
    try{ doc=new DOMParser().parseFromString(src,'text/html'); }
    catch(e){ Sanitizer.stats.noParser++; return esc(src); }
    if(!doc||!doc.body) return esc(src);
    const walk=function(node, out){
      const kids=node.childNodes;
      for(let i=0;i<kids.length;i++){
        const n=kids[i];
        if(n.nodeType===3){ out.push(esc(n.nodeValue)); continue; }
        if(n.nodeType!==1) continue;                   /* comments, CDATA, PIs */
        const tag=String(n.tagName||'').toUpperCase();
        if(tag==='SCRIPT'||tag==='STYLE'||tag==='IFRAME'||tag==='OBJECT'||tag==='EMBED'||
           tag==='LINK'||tag==='META'||tag==='BASE'||tag==='FORM'||tag==='TEMPLATE'||
           tag==='SVG'||tag==='MATH'){ Sanitizer.stats.droppedTags++; continue; }
        if(!sanAllowedTag(tag)){ walk(n, out); Sanitizer.stats.droppedTags++; continue; }
        const attrs=[];
        const list=n.attributes||[];
        for(let a=0;a<list.length;a++){
          const an=String(list[a].name||'').toLowerCase();
          if(!sanAllowedAttr(an)||SAN_ATTR_DROP[an]){ Sanitizer.stats.droppedAttrs++; continue; }
          let av=list[a].value;
          if(SAN_URL_ATTR[an]){
            av=safeUrl(av);
            if(!av){ Sanitizer.stats.droppedUrls++; continue; }
          }
          attrs.push(' '+an+'="'+esc(av)+'"');
        }
        const t=tag.toLowerCase();
        out.push('<'+t+attrs.join('')+'>');
        if(t!=='br'&&t!=='hr'&&t!=='img'&&t!=='wbr') walk(n, out);
        if(t!=='br'&&t!=='hr'&&t!=='img'&&t!=='wbr') out.push('</'+t+'>');
      }
    };
    const out=[]; walk(doc.body, out);
    return out.join('');
  },
  /* text extraction, for the places that want the words and none of the markup.
     This is not a security boundary and is not asked to be one: it drops tags,
     it does not decide whether the markup was safe. */
  text:function(html){ return String(html==null?'':html).replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim(); }
};

/* ══ CLOCK — the page has one timer now ═══════════════════════════════════════
   Fourteen independent `setInterval` loops used to drive this page: two 1 s
   countdowns, the EVE session clock, the ETF poll, two feed safety nets, the
   deep-recovery poll, the sentiment poll and the stream's three fallback
   timers. Each was a separate task for the browser to wake, none of them knew
   about the others, and every one of them kept firing in a hidden tab — where
   the work is not seen, cannot be, and still competes for the same connection.

   They all register here instead. One rAF loop drives the lot, which buys
   three things a pile of setInterval cannot:

     · a hidden tab costs almost nothing, without going silent. rAF is paused
       while the page is not visible, so the pump drops to a single 4 s timeout
       and fires the slots that are due; a background tab therefore stops
       burning frames while the polls that drive the alert rules keep running.
       Sleeping outright would have been the neat answer and the wrong one — it
       would have made every price rule a foreground-only feature.
     · coming back is not a stampede. Every slot whose interval elapsed while
       the tab was away is due exactly once — its next wake is re-based to
       "now + interval" *before* the job runs — and at most two slots fire per
       frame, so a tab restored after an hour does one of each job spread over
       a few frames instead of thirty fused requests.
     · one bad job cannot take the clock down. Each slot is isolated, a throw is
       counted and logged with its label, and the loop keeps its schedule.

   `Clock.stats()` is what the perf HUD reads; `Clock.frame()` is exported so
   the node harness can drive time by hand. */
/* the factory is separate from the instance so the whole scheduler can be
   built and driven by hand in the node harness */
function clockFactory(){
  const slots=[];
  const stats={passes:0, fires:0, errors:0, missed:0, resumes:0, slots:0};
  const MAX_PER_FRAME=2;
  /* While the page is visible the pump runs on frames: smooth, and free when
     there is nothing to do. While it is hidden there is no frame to run on, so
     the same pump runs on one slow timeout instead. That distinction matters
     more than it looks: a tab in the background is exactly where a trader
     expects the *alerts* to keep working, and the previous pile of setInterval
     loops did keep working there (throttled, but working). Sleeping outright
     would have quietly turned every price rule into a foreground-only feature.
     4 s is slow enough to be invisible in a profile and fast enough that a
     20 s feed poll and the 15 s live-price slot that drives the rule engine
     still land on time. */
  const HIDDEN_HEARTBEAT=4000;
  let raf=null, timer=null, seq=0, visible=(typeof document!=='undefined')?!document.hidden:true;
  /* `stamp` is only set by the harness, so tests can move time by hand instead
     of sleeping; on the page every read goes to Date.now() */
  let stamp=null;
  function nowMs(){ return stamp==null?Date.now():stamp; }
  function schedule(){
    if(!slots.length||raf!=null||timer!=null) return;
    if(visible) raf=requestAnimationFrame(frame);
    else timer=setTimeout(frame, HIDDEN_HEARTBEAT);
  }
  function frame(){
    raf=null; timer=null;
    if(!slots.length) return;
    stats.passes++; stats.slots=slots.length;
    const now=nowMs();
    let fired=0;
    for(let i=0;i<slots.length;i++){
      if(fired>=MAX_PER_FRAME) break;
      const s=slots[i];
      if(s.next>now) continue;
      if(s.when&&!s.when()){ s.next=now+s.ms; continue; }
      const late=now-s.next;
      if(s.first) s.first=false;
      else if(late>s.ms*1.5) stats.missed+=Math.max(1,Math.round(late/s.ms)-1);
      s.next=now+s.ms; s.runs++; stats.fires++; fired++;
      try{ s.fn(now); }
      catch(e){ stats.errors++;
        if(typeof console!=='undefined'&&console.error) console.error('[clock:'+(s.label||s.id)+']',e); }
    }
    schedule();
  }
  function every(ms, fn, opts){
    opts=opts||{};
    const period=Math.max(50, Math.round(ms)||50);
    const s={id:++seq, ms:period, fn:fn, when:opts.when||null, label:opts.label||'',
             onShow:(typeof opts.onShow==='function')?opts.onShow:null,
             runs:0, first:true, next:(opts.immediate?nowMs():nowMs()+period)};
    slots.push(s); stats.slots=slots.length; schedule();
    return s;
  }
  function off(handle){
    const i=handle?slots.indexOf(handle):-1;
    if(i<0) return false;
    slots.splice(i,1); stats.slots=slots.length; return true;
  }
  function clear(){ const n=slots.length; slots.length=0; stats.slots=0; return n; }
  function stopPump(){
    if(raf!=null){ cancelAnimationFrame(raf); raf=null; }
    if(timer!=null){ clearTimeout(timer); timer=null; }
  }
  if(typeof document!=='undefined'&&document.addEventListener){
    document.addEventListener('visibilitychange', function(){
      visible=!document.hidden;
      if(visible){
        stats.resumes++;
        /* the callback list is copied first: a handler may register or drop a
           slot, and mutating the list being walked would skip slots */
        const onShow=slots.slice();
        for(let i=0;i<onShow.length;i++){
          if(slots.indexOf(onShow[i])<0) continue;
          if(typeof onShow[i].onShow==='function'){
            try{ onShow[i].onShow(); }
            catch(e){ stats.errors++; }
          }
        }
      }
      stopPump();          /* hand over between the frame pump and the heartbeat */
      schedule();
    });
  }
  if(typeof window!=='undefined'&&window.addEventListener){
    /* a page that is going away must not leave a frame pending behind it */
    window.addEventListener('pagehide', function(){ clear(); stopPump(); });
  }
  return {every:every, off:off, clear:clear, stats:function(){ return stats; },
          list:function(){ return slots.slice(); }, frame:frame,
          setVisible:function(v){ visible=!!v; },
          /* the harness sets the clock's notion of "now" and then steps it, so
             every timing assertion is deterministic instead of a sleep */
          setNow:function(ms){ stamp=ms; },
          frameNow:function(now){ stamp=now; frame(); }};
}
/* one rAF pump, the page's only timer */
const Clock=clockFactory();
/* the shared one-second tick: the "next cycle in" readout, the calendar
   countdowns and anything else that only shows a clock. One slot, one pass over
   the visible timers, instead of three loops racing each other. */
function clockTick(){
  const nx=document.getElementById('nextIn');
  if(nx){
    if(!DATA||!DATA.stats){ nx.textContent='—'; }
    else{
      const t=DATA.stats.next_cycle_ts;
      if(!t) nx.textContent='—';
      else{
        const s=Math.max(0,Math.round(t-Date.now()/1000));
        nx.textContent=String(s/60|0)+'m '+String(s%60).padStart(2,'0')+'s';
      }
    }
  }
  if(UI&&UI.view==='calendar'&&typeof ECON!=='undefined'&&ECON){
    const list=document.querySelectorAll('.cal-timer[data-ts], .js-cal-cd[data-ts]');
    for(let i=0;i<list.length;i++){
      const el=list[i], ts=+el.dataset.ts;
      if(!ts) continue;
      const long=el.classList.contains('cal-timer');
      el.textContent=calCountdown(ts, long);
    }
  }
  if(typeof window.__calHeroTick==='function') window.__calHeroTick();
}

/* ══ VIRTUAL SCROLLER — windowed rows for the feed, archive and bookmarks ══
   The feed rendered `list.slice(0,400)` cards: 400 cards x ~30 nodes is a
   12 000-node subtree, 200 more stories were simply unreachable, and every
   60-second refresh threw the whole thing away and built it again — which is
   also what reset the reader's scroll position. Opening the archive did it a
   second time.

   This keeps the *cards* windowed and nothing else. The scrollbar still
   measures the whole list, because a spacer element is sized to the total
   computed height; the cards live in an absolutely-positioned layer whose rows
   are placed at their computed offsets. A row is only built when it comes
   within one screen of the viewport, and it is kept (not rebuilt) while the
   reader scrolls back and forth inside it.

   The grid model is deliberately the one CSS grid already had — a row of
   equal-width columns, all cells as tall as the tallest card in the row — so
   the look does not change, only the number of nodes that exist.

   Item heights are cached by key and refined as rows come into view. A card
   that has never been rendered contributes the running median of the ones that
   have, which is the standard trick and the safe direction: a wrong estimate
   costs a little scrolling slack for a moment, it never overlaps. */
/* The scroller has to be resolved from the markup, not from whether anything
   currently overflows: at mount time the host is empty, so an ancestor that
   scrolls only once it has content looks like it does not scroll at all — and
   the window would then be measured against the document, i.e. always from the
   top of the list. `overflow-y:auto` on the ancestor is the whole test. */
function vsScroller(from){
  let n=from?from.parentElement:null;
  while(n&&n!==document.body&&n!==document.documentElement){
    let cs=null;
    try{ cs=getComputedStyle(n); }catch(e){ cs=null; }
    if(cs&&(cs.overflowY==='auto'||cs.overflowY==='scroll')) return n;
    n=n.parentElement;
  }
  return document.scrollingElement||document.documentElement;
}
function vsCols(width, minW, gap){
  if(!(width>0)||!(minW>0)) return 1;
  return Math.max(1, Math.floor((width+gap)/(minW+gap)));
}
/* the row model: `spans[i]===cols` reserves a whole row for that item, which is
   how a day header in the archive keeps its full width while the cards below it
   stay in columns. `sets[r]` is the item indices of row r, so the renderer does
   not have to re-derive the packing. */
function vsLayout(count, cols, heights, fallback, gap, spans){
  const sets=[], rowH=[], rowOf=new Array(count||0);
  let cur=[], curMax=0;
  const flush=function(){
    if(cur.length){ sets.push(cur); rowH.push(curMax>0?curMax:fallback); cur=[]; curMax=0; }
  };
  cols=Math.max(1, cols|0);
  for(let i=0;i<count;i++){
    const h=(heights&&heights[i]>0)?heights[i]:fallback;
    /* a span is the number of columns the item occupies, so "full" is "at
       least the width of a row" — testing it for truthiness made every item
       a row of its own, which is exactly the layout bug this replaced */
    const full=!!spans&&spans[i]>=cols;
    if(full){ flush(); rowOf[i]=sets.length; sets.push([i]); rowH.push(h); continue; }
    if(cur.length>=cols) flush();
    rowOf[i]=sets.length;          /* the row index this item will land in */
    cur.push(i);
    if(h>curMax) curMax=h;
  }
  flush();
  const tops=[];
  let y=0;
  for(let r=0;r<sets.length;r++){ tops.push(y); y+=rowH[r]+gap; }
  /* `rowOf` is the item-to-row map, which is what makes a prepend exact: the
     story the reader is looking at can be found again by key, and its new row
     offset compared with the old one, whatever the re-packing did — no
     `index / columns` arithmetic, which is wrong the moment a full-width row
     is in the list. */
  return {rows:sets.length, sets:sets, rowH:rowH, tops:tops, rowOf:rowOf,
          height:sets.length?Math.max(0,y-gap):0};
}
/* which rows intersect [scrollTop-overscan, scrollTop+viewH+overscan]. Two
   binary searches, so the cost does not grow with the archive. */
function vsWindow(scrollTop, viewH, layout, overscan){
  const n=layout?layout.rows:0;
  if(!n) return {first:0, last:-1};
  const top=Math.max(0, scrollTop-overscan);
  const bot=scrollTop+viewH+overscan;
  let lo=0, hi=n-1, first=0;
  while(lo<=hi){
    const mid=(lo+hi)>>1;
    if(layout.tops[mid]+layout.rowH[mid]>=top){ first=mid; hi=mid-1; } else lo=mid+1;
  }
  let lo2=first, hi2=n-1, last=first;
  while(lo2<=hi2){
    const mid=(lo2+hi2)>>1;
    if(layout.tops[mid]<=bot){ last=mid; lo2=mid+1; } else hi2=mid-1;
  }
  if(last<first) last=first;
  return {first:first, last:last};
}
/* the estimate for a card nobody has measured yet: the median of the measured
   ones. A median (not a mean) so that one very tall card with a portrait image
   cannot inflate the scroll height of the two hundred below it. */
function vsMedian(heights){
  const v=[];
  if(heights) for(let i=0;i<heights.length;i++) if(heights[i]>0) v.push(heights[i]);
  if(!v.length) return 0;
  v.sort(function(a,b){ return a-b; });
  const m=v.length>>1;
  return v.length%2?v[m]:Math.round((v[m-1]+v[m])/2);
}
class VirtualScroller{
  constructor(host, opts){
    opts=opts||{};
    this.host=host;
    this.min=opts.min||306;
    this.gap=opts.gap==null?16:opts.gap;
    this.overscan=opts.overscan==null?800:opts.overscan;
    this.render=opts.render||function(){ return ''; };
    this.key=opts.key||function(item, i){ return item&&item.id!=null?item.id:i; };
    this.defaultH=opts.defaultH||260;
    this.items=[];
    this.spans=[];
    this.hcache=Object.create(null);
    this.heights=[];
    this.cols=1;
    this.layout=vsLayout(0,1,[],this.defaultH,this.gap,null);
    this.rows=[];                 /* Map-like: rowIndex -> {el, full, items} */
    this.byIndex={};
    this.spacer=null;
    this.layer=null;
    this.scroller=null;
    this.gridTop=0;
    this.raf=null;
    this.dead=false;
    this.lastFirst=-1;
    this.lastLast=-2;
    this.stats={renders:0, rows:0, nodes:0, relayouts:0, measures:0, items:0, prepends:0};
    this.paintedScroll=0;
    this.painted=false;
    this._scroll=this._scroll.bind(this);
    this._resize=this._resize.bind(this);
    this._mount();
  }
  _mount(){
    const host=this.host;
    if(!host) return;
    host.classList.add('vs-host');
    host.innerHTML='<div class="vs-spacer"></div><div class="vs-layer"></div>';
    this.spacer=host.firstChild;
    this.layer=host.lastChild;
    this.scroller=vsScroller(host);
    if(this.scroller&&this.scroller.addEventListener)
      this.scroller.addEventListener('scroll', this._scroll, {passive:true});
    if(typeof window!=='undefined') window.addEventListener('resize', this._resize);
    if(typeof ResizeObserver==='function'){
      /* images and webfonts arrive after the row is measured; a row that grows
         afterwards would push every offset below it out of place */
      this.ro=new ResizeObserver(this._resize);
      try{ this.ro.observe(this.host); }catch(e){ this.ro=null; }
    }
    /* The window is repainted from a frame callback, which is what keeps it off
       the scroll path. A frame callback is also the one thing that can be
       skipped: in a background tab rAF does not run at all, and a scroll that
       lands there (a restored position, a programmatic jump, or simply the tab
       being brought forward) would leave the rows of wherever the list used to
       be on screen. `scroll` cannot be relied on to fire either. So one cheap
       comparison rides the shared clock: if the scroller moved since the last
       paint, paint. Three floats a second, and the bug cannot happen. */
    this.watch=Clock.every(250, ()=>{
      if(this.dead||!this.scroller) return;
      if(!this.painted||this.scroller.scrollTop!==this.paintedScroll) this._schedule();
    }, {label:'vs-watch', onShow:()=>this.visible()});
    this._measureCols();
  }
  _measureCols(){
    const g=this.host;
    if(!g) return false;
    const w=g.clientWidth||g.getBoundingClientRect().width||0;
    const cs=(typeof getComputedStyle==='function')?getComputedStyle(g):null;
    let gap=this.gap;
    if(cs&&cs.columnGap&&cs.columnGap.indexOf('px')>0) gap=parseFloat(cs.columnGap)||gap;
    const cols=vsCols(w, this.min, gap);
    const changed=cols!==this.cols;
    this.cols=cols; this.gap=gap;
    return changed;
  }
  _scroll(){ this._schedule(); }
  _resize(){ this._schedule(true); }
  visible(){ this._pendingReflow=true; this._schedule(); }
  _schedule(reflow){
    if(this.dead) return;
    if(reflow) this._pendingReflow=true;
    if(this.raf!=null) return;
    /* a frame callback never runs in a hidden tab, and a scroll that lands
       there still has to be honoured before the tab is shown again — so in
       that one case the paint happens inline. It is the slow path by
       definition (nobody is looking), and it costs at most one paint per
       heartbeat. */
    if(typeof document!=='undefined'&&document.hidden){ this._paint(); return; }
    const self=this;
    this.raf=requestAnimationFrame(function(){ self.raf=null; self._paint(); });
  }
  _localScroll(){
    const sc=this.scroller;
    if(!sc) return 0;
    const g=this.host;
    if(!g||!g.getBoundingClientRect) return sc.scrollTop||0;
    const gr=g.getBoundingClientRect().top;
    const sr=sc.getBoundingClientRect?sc.getBoundingClientRect().top:0;
    this.gridTop=gr-sr+(sc.scrollTop||0);
    return (sc.scrollTop||0)-this.gridTop;
  }
  _viewH(){
    const sc=this.scroller;
    if(sc&&sc.clientHeight) return sc.clientHeight;
    if(typeof window!=='undefined'&&window.innerHeight) return window.innerHeight;
    return 800;
  }
  /* `__full` items (a day header in the archive) reserve a whole row, so the
     grouping survives windowing without a second layout pass */
  _layout(){
    const n=this.items.length, spans=new Array(n);
    for(let i=0;i<n;i++) spans[i]=(this.items[i]&&this.items[i].__full)?this.cols:1;
    this.spans=spans;
    this.layout=vsLayout(n, this.cols, this.heights, this.defaultH, this.gap, spans);
  }
  setItems(items, opts){
    opts=opts||{};
    this.items=items||[];
    const keys=[];
    for(let i=0;i<this.items.length;i++){
      const k=this.key(this.items[i], i);
      keys.push(k);
      this.heights[i]=this.hcache[k]>0?this.hcache[k]:0;
    }
    this.stats.items=this.items.length;
    const colsChanged=this._measureCols();
    this._layout();
    this.stats.relayouts++;
    if(this.spacer) this.spacer.style.height=this.layout.height+'px';
    if(colsChanged||opts.force) this._clearRows();
    this.lastFirst=-1; this.lastLast=-2;
    this._paint();
    return this.layout;
  }
  /* the stream's path: new stories land at the head, and the story that was at
     the top of the view keeps its screen position. Because the offsets are
     computed rather than measured, the correction is arithmetic: the old first
     row's offset is known before and after, so the scroll delta is exact. */
  prepend(newItems){
    if(!newItems||!newItems.length) return 0;
    const sc=this.scroller;
    const before=sc?sc.scrollTop||0:0;
    /* The anchor is the first story of the topmost painted row: the overscan
       guarantees that row starts at or above the top of the view, so holding
       it still holds still everything the reader can actually see. It is
       remembered by key, because a prepend moves every index in the list. */
    let anchorKey=null, anchorTop=0;
    const paintedRows=Object.keys(this.byIndex);
    if(paintedRows.length){
      let topRow=null;
      for(let i=0;i<paintedRows.length;i++){
        const r=+paintedRows[i];
        if(topRow==null||r<topRow) topRow=r;
      }
      const idx=(topRow==null?null:this.layout.sets[topRow])||[];
      if(idx.length){
        anchorKey=this.key(this.items[idx[0]], idx[0]);
        anchorTop=this.layout.tops[topRow]||0;
      }
    }
    /* the height cache is keyed, so shifting it keeps every measured row
       aligned with the item it was measured for — no guess-and-jump frame */
    const add=[];
    for(let i=0;i<newItems.length;i++) add.push(this.hcache[this.key(newItems[i],i)]>0?this.hcache[this.key(newItems[i],i)]:0);
    this.heights=add.concat(this.heights.slice(0, Math.max(0, this.items.length)));
    this.items=newItems.concat(this.items);
    this.stats.items=this.items.length;
    this._layout();
    this.stats.prepends++;
    /* rows born into the new head get the same entrance the DOM path used, so
       a live story still announces itself now that it arrives as a row */
    this._enterCount=(this._enterCount||0)+newItems.length;
    if(this.spacer) this.spacer.style.height=this.layout.height+'px';
    this.lastFirst=-1; this.lastLast=-2;
    this._paint();
    if(sc&&before>0&&anchorKey!=null){
      /* find the anchor again and correct by exactly the distance it moved:
         the rows above the reader may have been re-packed to different
         heights, and no formula about the head of the list knows that */
      let at=-1;
      for(let i=0;i<this.items.length;i++){
        if(this.key(this.items[i], i)===anchorKey){ at=i; break; }
      }
      if(at>=0){
        const row=this.layout.rowOf[at];
        const newTop=(row==null?0:this.layout.tops[row])||0;
        const delta=newTop-anchorTop;
        if(delta) sc.scrollTop=Math.max(0, before+delta);
      }
    }
    return newItems.length;
  }
  clear(){
    this.items=[]; this.heights=[]; this.spans=[];
    this._clearRows();
    this.layout=vsLayout(0,this.cols,[],this.defaultH,this.gap,null);
    if(this.spacer) this.spacer.style.height='0px';
    this.lastFirst=-1; this.lastLast=-2;
  }
  refresh(){ this._measureCols(); this._layout();
    if(this.spacer) this.spacer.style.height=this.layout.height+'px';
    this.lastFirst=-1; this.lastLast=-2; this._paint(); }
  _clearRows(){
    for(const r in this.byIndex){ const row=this.byIndex[r]; if(row.el&&row.el.remove) row.el.remove(); }
    this.byIndex={};
  }
  _cell(item, i){
    const h=this.render(item, i);
    return h==null?'':h;
  }
  _paint(){
    if(this.dead) return;
    const g=this.host;
    if(!g||!this.layer) return;
    if(this._pendingReflow){
      this._pendingReflow=false;
      const changed=this._measureCols();
      /* a real size change (a resize, or an image that landed late) invalidates
         the measurements of the rows that are on screen — otherwise the cache
         would keep serving the height they had before they grew */
      for(const r in this.byIndex){
        const idx=this.layout.sets[r]||[];
        for(let c=0;c<idx.length;c++) this.heights[idx[c]]=0;
      }
      const med=vsMedian(this.heights);
      if(med>0) this.defaultH=med;
      this._layout();
      if(this.spacer) this.spacer.style.height=this.layout.height+'px';
      if(changed){ this._clearRows(); this.lastFirst=-1; this.lastLast=-2; }
    }
    const top=this._localScroll();
    const win=vsWindow(top, this._viewH(), this.layout, this.overscan);
    if(this.spacer&&this.spacer.style.height!==this.layout.height+'px')
      this.spacer.style.height=this.layout.height+'px';
    const keep={};
    const entering=[];
    let entered=0;
    const layer=this.layer;
    for(let r=win.first;r<=win.last;r++){
      const idx=this.layout.sets[r];
      if(!idx) continue;
      keep[r]=1;
      const full=idx.length===1&&this.spans[idx[0]]>=this.cols;
      /* the signature has to describe *which items* a row shows, not just how
         many: a re-render that puts different stories in the same slots would
         otherwise keep the old cards, because the index set did not move */
      let sig='';
      for(let c=0;c<idx.length;c++) sig+=(c?',':'')+this.key(this.items[idx[c]], idx[c]);
      let row=this.byIndex[r]||null;
      if(row&&row.sig!==sig){ if(row.el&&row.el.remove) row.el.remove(); row=null; }
      if(!row){
        const el=document.createElement('div');
        el.className='vs-row'+(full?' vs-full':'');
        el.style.gridTemplateColumns='repeat('+this.cols+',minmax(0,1fr))';
        let html='';
        for(let c=0;c<idx.length;c++) html+=this._cell(this.items[idx[c]], idx[c]);
        el.innerHTML=html;
        layer.appendChild(el);
        row={el:el, sig:sig, full:full};
        this.byIndex[r]=row;
        if(this._enterCount&&idx[0]<this._enterCount){
          /* new items are always a prefix of the list, so a row is "born" when
             its lowest index is inside that prefix — and only the ones this row
             actually shows are consumed, so scrolling up later still animates
             the rest instead of swallowing the mark */
          entering.push(el);
          entered+=Math.min(idx.length, this._enterCount-idx[0]);
        }
      }
      row.el.style.top=this.layout.tops[r]+'px';
    }
    for(const r in this.byIndex){
      if(!keep[r]){
        const row=this.byIndex[r];
        if(row.el&&row.el.remove) row.el.remove();
        delete this.byIndex[r];
      }
    }
    if(entering.length){
      for(let e=0;e<entering.length;e++) entering[e].classList.add('card-enter');
      setTimeout(function(){
        for(let e=0;e<entering.length;e++) entering[e].classList.remove('card-enter');
      }, 1000);
      this._enterCount=Math.max(0, this._enterCount-entered);
    }
    this.lastFirst=win.first; this.lastLast=win.last;
    this.paintedScroll=this.scroller?this.scroller.scrollTop:0;
    this.painted=true;
    this.stats.renders++;
    this.stats.rows=Object.keys(this.byIndex).length;
    this.stats.nodes=g.querySelectorAll('*').length;
    /* One read pass after every insert: measure the rendered rows, cache what
       they actually cost, and re-lay-out only if reality disagreed. A read that
       follows a write is what forces the browser to lay the page out again, so
       a row whose items have all been measured before is skipped — otherwise
       every scroll step pays for a whole-document layout to be told what it
       already knew, which is the jank this exercise exists to remove. */
    let changed=false;
    for(const r in this.byIndex){
      const idx=this.layout.sets[r]||[];
      let unknown=false;
      for(let c=0;c<idx.length;c++){ if(!(this.heights[idx[c]]>0)){ unknown=true; break; } }
      if(!unknown) continue;
      const row=this.byIndex[r];
      const h=row.el.offsetHeight||0;
      if(!(h>0)) continue;
      for(let c=0;c<idx.length;c++){
        const i=idx[c];
        const k=this.key(this.items[i], i);
        this.stats.measures++;
        if(this.hcache[k]!==h){ this.hcache[k]=h; }
        if(this.heights[i]!==h){ this.heights[i]=h; changed=true; }
      }
    }
    if(changed){
      const med=vsMedian(this.heights);
      if(med>0) this.defaultH=med;
      this._layout();
      if(this.spacer) this.spacer.style.height=this.layout.height+'px';
      for(const r in this.byIndex){
        const row=this.byIndex[r];
        if(this.layout.tops[r]!=null) row.el.style.top=this.layout.tops[r]+'px';
      }
      this.stats.relayouts++;
    }
  }
  destroy(){
    this.dead=true;
    if(this.watch) Clock.off(this.watch);
    if(this.raf!=null){ cancelAnimationFrame(this.raf); this.raf=null; }
    if(this.scroller&&this.scroller.removeEventListener)
      this.scroller.removeEventListener('scroll', this._scroll);
    if(typeof window!=='undefined') window.removeEventListener('resize', this._resize);
    if(this.ro){ try{ this.ro.disconnect(); }catch(e){} this.ro=null; }
    this.byIndex={};
    if(this.host){
      this.host.classList.remove('vs-host');
      this.host.innerHTML='';
    }
    this.spacer=null; this.layer=null; this.items=[];
  }
  /* what the perf HUD shows */
  report(){
    return {items:this.stats.items, rows:this.stats.rows, cols:this.cols,
            nodes:this.stats.nodes, renders:this.stats.renders,
            height:this.layout.height, relayouts:this.stats.relayouts};
  }
}
/* ── the three windowed grids ─────────────────────────────────────────────
   One instance per host, created on first render and reused for the life of
   the page: creating it is what empties the host, so it must never happen
   twice for the same element. */
const VS={feed:null, archive:null, bmark:null};
const VS_OPTS_FEED={min:306, gap:16, defaultH:280, overscan:900, render:cardHTML,
  key:function(a){ return a&&a.__sk!=null?('sk'+a.__sk):(a&&a.id!=null?a.id:''); }};
const VS_OPTS_BMARK={min:306, gap:16, defaultH:280, overscan:900, render:cardHTML,
  key:function(a){ return a&&a.id!=null?a.id:''; }};
const VS_OPTS_ARCHIVE={min:280, gap:14, defaultH:300, overscan:1000,
  key:function(it,i){ return it&&it.__full?('day:'+it.__day):(it&&it.id!=null?it.id:i); },
  render:function(it){
    if(it&&it.__full)
      return '<div class="calday archday"><div class="calday-h">'+
        '<span class="calday-title">'+ic('calendar')+' '+esc(it.__day)+'</span>'+
        '<span class="calday-meta">'+toFa(it.n)+' خبر آرشیوشده</span></div></div>';
    return cardHTML(it);
  }};
function vsFor(which, hostId, opts){
  const g=document.getElementById(hostId);
  if(!g) return null;
  if(!VS[which]){
    try{ VS[which]=new VirtualScroller(g, opts); }
    catch(e){ if(typeof console!=='undefined'&&console.error) console.error('vs:'+which, e); return null; }
  }
  return VS[which];
}
function vsGrid(which, hostId, opts, items, fallbackHTML){
  const vs=vsFor(which, hostId, opts);
  if(vs){ vs.setItems(items); return true; }
  const g=document.getElementById(hostId);
  if(g&&fallbackHTML!=null) g.innerHTML=fallbackHTML;
  return false;
}
function vsReleaseAll(){
  ['feed','archive','bmark'].forEach(function(k){
    if(VS[k]){ VS[k].destroy(); VS[k]=null; }
  });
}
/* ── perf HUD ──────────────────────────────────────────────────────────────
   Numbers, not adjectives. Every claim in the benchmark table is produced by
   this panel on the live page: how many nodes the document actually holds,
   how many rows each grid is willing to keep, and what the clock did. */
/* one icon helper for generated markup — every pictogram is an SVG <use> into
   the sprite at the top of <body>, never a font glyph */
function ic(name, cls){ return '<svg class="ic'+(cls?' '+cls:'')+'" aria-hidden="true"><use href="#i-'+name+'"/></svg>'; }
/* asset and topic marks: the registry used to carry an emoji per asset, which
   put pictographs in the middle of an otherwise drawn interface. The mark is
   now derived from the instrument itself (coin / ingot / barrel / FX / index),
   so a newly added asset gets a real icon with no data migration. */
const ASSET_IC={BTC:'coin',ETH:'coin',BNB:'coin',SOL:'coin',XRP:'coin',ADA:'coin',DOGE:'coin',LINK:'coin',
                XAU:'ingot',XAG:'ingot',WTI:'drop',DXY:'swap',SPX:'chart',VIX:'pulse'};
function assetIcName(sym){
  const s=String(sym||'').toUpperCase();
  if(ASSET_IC[s]) return ASSET_IC[s];
  const meta=((typeof DATA!=='undefined'&&DATA&&DATA.assets_meta)||{})[s]||{};
  if(meta.coingecko) return 'coin';
  if(meta.yahoo&&/=F$/.test(String(meta.yahoo))) return 'drop';
  return 'chart';
}
function assetIc(sym, cls){ return ic(assetIcName(sym), cls); }
const TOPIC_IC={regulation:'lock',institutional:'bank',etf:'coins',macro:'globe',security:'shield',
                analysis:'chart',defi:'grid',market:'pulse',tech:'cpu',general:'news'};
function topicIc(t, cls){ return ic(TOPIC_IC[t]||'tag', cls); }
function num(v,nd){ return Number(v).toLocaleString('en-US',{minimumFractionDigits:nd||0,maximumFractionDigits:nd||0}); }
function fmtPrice(v){ if(v==null) return '—';
  if(v>=1000) return '$'+num(v,0);
  if(v>=10) return '$'+num(v,2); if(v>=1) return '$'+num(v,3); return '$'+num(v,4); }
function fmtIran(iso){ if(!iso) return '—'; try{ return toFa(new Date(iso).toLocaleTimeString('fa-IR',{hour:'2-digit',minute:'2-digit'})); }catch(e){ return '—'; } }
/* the telemetry line is English: same clock, Latin digits */
function fmtEng(iso){ if(!iso) return '—'; try{ return new Date(iso).toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'}); }catch(e){ return '—'; } }
/* storage keys carry the app name — migrate once from the pre-rebrand keys so
   bookmarks saved before the rename are never lost */
const BM_KEY='mohmd_bmarks', BM_META_KEY='mohmd_bmark_meta';
(function migrateBmarkKeys(){
  try{
    const pairs=[[BM_KEY,'hermes_bmarks'],[BM_META_KEY,'hermes_bmark_meta']];
    for(const [nu,old] of pairs){
      if(localStorage.getItem(nu)==null && localStorage.getItem(old)!=null){
        localStorage.setItem(nu, localStorage.getItem(old));
        localStorage.removeItem(old);
      }
    }
  }catch(e){}
})();
function getBookmarks(){ try{ return JSON.parse(localStorage.getItem(BM_KEY)||'[]'); }catch(e){ return []; } }
function isBookmarked(id){ return getBookmarks().includes(id); }
/* a bookmark keeps a snapshot of the story so the Bookmarks tab still renders
   it after the article has aged out of the live window */
function getBmarkMeta(){ try{ return JSON.parse(localStorage.getItem(BM_META_KEY)||'{}'); }catch(e){ return {}; } }
function findArticle(id){
  const pools=[DATA.articles||[], DATA.archive||[]];
  for(const p of pools){ for(const a of p){ if(a.id===id) return a; } }
  if (window.Channel && typeof window.Channel.getItem === 'function') {
    const it = window.Channel.getItem(id);
    if (it) return (it.article || it);
  }
  return null;
}
function snapshot(a){
  const keys=['id','title','title_fa','source','source_kind','link','image','published_str','published_ts',
              'datetime_fa','age_fa','credibility','topic','topic_fa','topic_icon','assets','summary','summary_fa'];
  const o={}; for(const k of keys) if(a[k]!=null) o[k]=a[k];
  o.saved_at=Math.floor(Date.now()/1000);
  return o;
}
function toggleBookmark(id, ev){
  if(ev) ev.stopPropagation();
  let b = getBookmarks();
  const meta = getBmarkMeta();
  if(b.includes(id)){ b = b.filter(x=>x!==id); delete meta[id]; toast('از نشان‌شده‌ها حذف شد'); }
  else { b.push(id); const a=findArticle(id); if(a) meta[id]=snapshot(a); toast('⭐ به نشان‌شده‌ها اضافه شد'); }
  try{ localStorage.setItem(BM_KEY, JSON.stringify(b)); }catch(e){}
  try{ localStorage.setItem(BM_META_KEY, JSON.stringify(meta)); }catch(e){}
  renderChips();
  renderFeed();
  renderBookmarks();
}
function clearBookmarks(){
  if(!getBookmarks().length) return toast('نشان‌شده‌ای وجود ندارد');
  if(!confirm('همهٔ نشان‌شده‌ها پاک شوند؟')) return;
  try{ localStorage.removeItem(BM_KEY); localStorage.removeItem(BM_META_KEY); }catch(e){}
  renderChips(); renderFeed(); renderBookmarks();
  toast('نشان‌شده‌ها پاک شد');
}

/* ── Jalali (برای برچسب محور نمودار) ── */
function g2j(gy,gm,gd){
  const gdm=[0,31,59,90,120,151,181,212,243,273,304,334];
  let gy2 = gm>2 ? gy+1 : gy;
  let days = 355666 + (365*gy) + Math.floor((gy2+3)/4) - Math.floor((gy2+99)/100) + Math.floor((gy2+399)/400) + gd + gdm[gm-1];
  let jy = -1595 + 33*Math.floor(days/12053); days %= 12053;
  jy += 4*Math.floor(days/1461); days %= 1461;
  if(days>365){ jy += Math.floor((days-1)/365); days = (days-1)%365; }
  let jm, jd;
  if(days<186){ jm = 1+Math.floor(days/31); jd = 1+(days%31); }
  else { jm = 7+Math.floor((days-186)/30); jd = 1+((days-186)%30); }
  return [jy,jm,jd];
}
const JM=['فروردین','اردیبهشت','خرداد','تیر','مرداد','شهریور','مهر','آبان','آذر','دی','بهمن','اسفند'];
function faDateFromIso(s){ if(!s) return ''; const p=s.split('-'); if(p.length<3) return s;
  const [jy,jm,jd]=g2j(+p[0],+p[1],+p[2]); return toFa(jd)+' '+JM[jm-1]; }

/* ── views ── */
function showView(v, skipPick){
  const prev=UI.view;
  UI.view=v;
  document.querySelectorAll('.tab').forEach(t=>{t.classList.toggle('active',t.dataset.view===v); t.setAttribute('aria-selected', t.dataset.view===v?'true':'false');});
  document.querySelectorAll('.view').forEach(s=>s.classList.toggle('active',s.id==='view-'+v));
  ['ibSettings','ibSources','ibAssets'].forEach(id=>{
    const b=document.getElementById(id);
    if(b) b.classList.toggle('on', b.id==='ibSettings'&&v==='settings' || b.id==='ibSources'&&v==='sources' || b.id==='ibAssets'&&v==='assets');
  });
  /* releases happen on the way out, not on the way back in */
  if(prev&&prev!==v) teardownView(prev);
  /* the grids measure themselves, and a hidden element measures zero: a grid
     whose view was switched away from is re-measured the moment it is visible */
  if(v==='feed'&&VS.feed) VS.feed.refresh();
  if(v==='archive'&&VS.archive) VS.archive.refresh();
  if(v==='bookmarks'&&VS.bmark) VS.bmark.refresh();

  if(v==='reports'&&DATA&&!skipPick){
    const ordered=orderedAssets().filter(s=>true);
    if(!UI.repSym||!ordered.includes(UI.repSym)) UI.repSym=ordered[0];
    pickReport(UI.repSym, true);   // pickReport calls showView(..., skipPick)
  }
  if(v==='assets') renderAssetTable();
  if(v==='channel'&&window.Channel) window.Channel.mount();
  if(v==='monitor') loadMonitor();
  if(v==='calendar'){ if(ECON) renderCalendar(); else loadCalendar(); }
  if(v==='alerts') initAlerts();
  if(UI.view==='archive'){ renderArchive(); return; }
  if(UI.view==='bookmarks'){ renderBookmarks(); return; }
  if(v==='etf'){ if(!(window.__ETFQ&&Object.keys(window.__ETFQ).length)) pollEtf(); renderEtfLive('etfLive2'); }
  if(v==='ideas') loadIdeas();
  if(v==='reports'){
    /* coming back to the tab: the widget may have been mounted while hidden
       (or never mounted at all) — give it a viewport to measure */
    setTimeout(()=>{
      try{
        if(!document.querySelector('#tvholder iframe')) mountTVChart(true);
        else window.dispatchEvent(new Event('resize'));
      }catch(e){}
    }, 150);
  }
}

async function loadData(){
  if(_LOADING) return;
  _LOADING = true;
  try{
    const r = await fetch('/api/data');
    if(!r.ok) throw new Error(r.status);
    DATA = await r.json();
    initMeta(); renderAll();
    if(window.Channel && typeof window.Channel.onCycleUpdate === 'function') window.Channel.onCycleUpdate();
  }catch(e){
    console.error('loadData:', e);            /* never swallow silently — the
        banner alone hides which renderer broke (it did: the maquette's
        synchronous mock used to fail here with an empty feed and no trace) */
    const ct=document.getElementById('cycleTxt');
    if(ct) ct.textContent='خطای اتصال به سرور';
  }finally{
    _LOADING = false;
  }
}
/* poll /api/data every 60s so newly-cycled news appears without reload */
/* ── timers that stand down while the stream is alive ──────────────────────
   These two used to be the feed's clock. Now the `news` channel delivers new
   articles the moment the scrape lands, so the timers are only a safety net
   for the case where no stream (ws or sse) could be established at all. */
Clock.every(60000, ()=>{ if(Stream.state!=='live'&&(!DATA||!DATA.stats||!DATA.stats.cycle_running)) loadData(); }, {label:'feed-net-60s'});
/* While a cycle is running the feed is polled too: the server publishes the
   fresh articles as soon as the scrape lands (before translation/reports),
   so waiting for cycle_running to go false used to hide them for minutes. */
Clock.every(20000, ()=>{ if(Stream.state!=='live'&&DATA&&DATA.stats&&DATA.stats.cycle_running) loadData(); }, {label:'feed-net-20s'});
/* ── DL2 phase 2/5: live price ticker under the topbar ────────────────────
   Compact marquee: every asset in the board, the whole series rendered twice
   so the CSS slide can loop seamlessly. The scroll duration scales with the
   number of symbols (about 3s each) so adding an asset never makes it crawl. */
/* infinite marquee (2026-09-26): one chip per asset, then the series repeated
   until a single pass is wider than the bar, rendered as two identical halves.
   CSS slides the track exactly -50%, so the loop restarts on an identical
   frame — no jump and no cut-off end, however few assets are enabled. The
   duration follows the real pixel width, so the speed never changes. */
function tickerChipsHTML(){
  const out=[];
  (typeof orderedAssets==='function'?orderedAssets():[]).forEach(sym=>{
    const m=(DATA.market||{})[sym]||{};
    const lv=(typeof liveOf==='function')?liveOf(sym):null;
    const price=(lv&&lv.price!=null)?lv.price:m.price;
    if(price==null) return;
    const chg=(lv&&lv.change_24h!=null)?lv.change_24h:m.change_24h;
    const cls=chg==null?'':(chg>=0?'up':'dn');
    const arrow=chg==null?'':(chg>=0?'▲':'▼');
    /* data-sym: the handle the stream's micro-updates use to find this chip's
       .p / .c nodes without re-rendering the marquee on every tick */
    out.push(`<span class="tk ${cls}" data-sym="${esc(sym)}" title="${esc(sym)}"><span class="s">${esc(sym)}</span>`+
      `<span class="p">${fmtPrice(price)}</span>`+
      (chg==null?'':`<span class="c">${arrow}${Math.abs(chg).toFixed(2)}%</span>`)+
      (m.stale?'<span class="st" title="قیمت کهنه"></span>':'')+`</span>`);
  });
  /* the unit ends on its separator so repeating it keeps the rhythm even */
  return out.length ? out.join('<span class="sep">◆</span>')+'<span class="sep">◆</span>' : '';
}
function renderTicker(){
  const bar=document.getElementById('tickerBar');
  if(!bar||!DATA) return;
  const unit=tickerChipsHTML();
  if(!unit){ bar.innerHTML=''; return; }
  bar.innerHTML=`<div class="tk-half">${unit}</div>`;      /* measure one pass */
  const probe=bar.firstElementChild;
  const unitW=probe?probe.getBoundingClientRect().width:0;
  const viewW=Math.max(bar.clientWidth||0, document.documentElement.clientWidth||0, 320);
  const reps=(unitW>1)?Math.max(1, Math.ceil(viewW/unitW)+1):1;
  const half=unit.repeat(reps);
  const dur=Math.max(36, Math.min(220, Math.round(((unitW*reps)||600)/52)));
  bar.innerHTML=`<div class="tk-track" style="--tk-dur:${dur}s">`+
    `<div class="tk-half">${half}</div>`+
    `<div class="tk-half" aria-hidden="true">${half}</div></div>`;
}
/* ── اخبار منتخب: twenty selected stories, four per row, one page at a time ──
   Was three text boxes above a grid of full-colour cards. Three problems with
   that: the top of the page looked poorer than what sat under it, three cards
   is not a section, and the top three by credibility barely move between two
   payloads — so the same three stories sat at the top of the page all day.
   Now twenty are picked and the row walks through them a page at a time. It is
   pausable by hand, and it stops by itself while the pointer or the keyboard is
   inside it: a carousel that moves under a reading eye is the one thing a
   carousel must never do. */
const LEAD_POOL=20, LEAD_PER=4, LEAD_ROTATE_MS=10000, LEAD_MIN_CRED=0.55;
const LEAD={pool:[], page:0, paused:false, hover:false, built:false};
const LEAD_REDUCE=(typeof matchMedia==='function')?matchMedia('(prefers-reduced-motion: reduce)'):null;

function leadTs(a){ const t=(a&&a.published_ts)||0; return t>1e12?Math.floor(t/1000):t; }
/* credibility first, freshness as the tie-breaker: a 0.80 story from an hour
   ago outranks a 0.75 one from this morning, and yesterday's tail never buys
   its way in on age alone */
function leadScore(a, now){
  const cred=Math.max(0, Math.min(1, (+(a&&a.credibility))||0));
  const hours=Math.max(0, ((now||0)-leadTs(a))/3600);
  return cred*100 + Math.max(0, 1-hours/24)*15;
}
/* the twenty: the best story per asset first, then the rest by score, so four
   cards in one row are never four takes on the same coin */
function leadPick(arts, now){
  const sorted=(arts||[]).filter(a=>a&&a.id&&((+a.credibility)||0)>=LEAD_MIN_CRED)
    .slice().sort((a,b)=>leadScore(b,now)-leadScore(a,now)||leadTs(b)-leadTs(a));
  const out=[], seen={};
  for(const a of sorted){
    const key=(a.assets&&a.assets[0])||a.topic||a.source||'?';
    if(seen[key]) continue;
    seen[key]=1; out.push(a);
    if(out.length>=LEAD_POOL) return out;
  }
  for(const a of sorted){
    if(out.indexOf(a)<0) out.push(a);
    if(out.length>=LEAD_POOL) break;
  }
  return out;
}
function leadPages(pool){ return Math.max(1, Math.ceil((((pool||[]).length)||0)/LEAD_PER)); }
function leadWindow(pool, page){
  const n=(pool||[]).length; if(!n) return [];
  const pages=leadPages(pool), p=((((Math.round(page)||0)%pages)+pages)%pages);
  return pool.slice(p*LEAD_PER, p*LEAD_PER+LEAD_PER);
}
/* the banner slot the stylesheet already had (`.lead-card .thumb`, 21:9) but
   no renderer ever filled: the most credible stories ran as text-only boxes
   directly above a grid of full-colour thumbnails */
function leadCardHTML(a){
  /* the sanitised URL is the only URL that reaches the markup — including the
     proxy fallback, which used to be built from the raw feed string */
  const img0=safeUrl(a.image);
  const img = img0
    ? `<div class="thumb"><img src="${attr(img0)}" alt="" loading="eager" referrerpolicy="no-referrer" data-orig="${attr(img0)}" onerror="if(!this.dataset.tried){this.dataset.tried='1';this.src='/api/proxy-image?url='+encodeURIComponent(this.dataset.orig);}else{this.remove()}"></div>`
    : '';
  const assets=(a.assets||[]).slice(0,2);
  return `<article class="lead-card" data-id="${attr(a.id)}" role="button" tabindex="0"
      aria-label="${esc(a.title_fa||a.title)}" onclick="openArticle(${jsArg(a.id)})"
      onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();openArticle(${jsArg(a.id)})}">
      <div class="lead-rail"></div>
      ${img}
      <div class="body">
        <div class="row1">${assets.map(s=>`<span class="badge b-asset">${assetIc(s)}${FA_ASSET[s]||s}</span>`).join('')}
          <span class="badge b-topic">${topicIc(a.topic)} ${FA_TOPIC[a.topic]||''}</span></div>
        <div class="lead-ttl">${esc(a.title_fa||a.title)}</div>
        <div class="row2"><span class="src">${esc(a.source)}</span><span class="dt">${esc(a.datetime_fa||'')}</span>
          <button class="del-btn" onclick="hideNews(${jsArg(a.id)}, event)" title="حذف این خبر از داشبورد" aria-label="حذف خبر">${ic('trash')}</button></div>
      </div></article>`;
}
/* the head doubles as the WCAG "pause, stop, hide" control an auto-rotating
   row needs: without a visible stop, rotation for more than five seconds is a
   failure on its own */
function leadHeadHTML(pool, page){
  const pages=leadPages(pool), lab=`<span class="lead-lab">${ic('star')} اخبار منتخب</span>`+
    `<span class="lead-count">${toFa(pool.length)} خبر برتر</span>`;
  if(pages<2) return `<div class="lead-head">${lab}</div>`;
  let dots='';
  for(let i=0;i<pages;i++)
    dots+=`<button class="lead-dot${i===page?' on':''}" aria-label="صفحهٔ ${toFa(i+1)} از ${toFa(pages)}" aria-current="${i===page?'true':'false'}" onclick="leadGo(${i})"></button>`;
  return `<div class="lead-head">${lab}
    <div class="lead-nav">
      <button class="lead-btn" onclick="leadStep(-1)" title="صفحهٔ قبلی" aria-label="صفحهٔ قبلی اخبار منتخب">${ic('chev-right')}</button>
      <span class="lead-dots">${dots}</span>
      <span class="lead-pos">${toFa(page+1)} / ${toFa(pages)}</span>
      <button class="lead-btn" id="leadPlay" onclick="leadToggle()" aria-pressed="${LEAD.paused?'true':'false'}"
        title="${LEAD.paused?'شروع چرخش اخبار منتخب':'توقف چرخش اخبار منتخب'}">${ic(LEAD.paused?'play':'pause')}</button>
      <button class="lead-btn" onclick="leadStep(1)" title="صفحهٔ بعدی" aria-label="صفحهٔ بعدی اخبار منتخب">${ic('chev-left')}</button>
    </div></div>`;
}
function paintLead(animate){
  const box=document.getElementById('leadRow'); if(!box) return;
  const pool=LEAD.pool;
  if(!pool.length){ box.innerHTML=''; box.hidden=true; return; }
  if(box.hidden) box.hidden=false;
  /* the inner grid is the only node replaced, and the fade-in class is on it
     when it is created — so a page change is one animation, not a swap plus a
     timer waiting to start one */
  box.innerHTML=leadHeadHTML(pool, LEAD.page)+
    `<div class="lead-cards${animate?' lead-in':''}" id="leadCards">`+
    leadWindow(pool, LEAD.page).map(leadCardHTML).join('')+`</div>`;
}
function leadGo(p){
  const pages=leadPages(LEAD.pool);
  LEAD.page=((((Math.round(p)||0)%pages)+pages)%pages);
  paintLead(true);
}
function leadStep(d){ leadGo(LEAD.page+(d||1)); }
function leadToggle(){ LEAD.paused=!LEAD.paused; paintLead(false); }
function initLead(){
  if(LEAD.built) return;
  const box=document.getElementById('leadRow');
  if(!box||!box.addEventListener) return;
  LEAD.built=true;
  const enter=()=>{ LEAD.hover=true; }, leave=()=>{ LEAD.hover=false; };
  box.addEventListener('mouseenter',enter); box.addEventListener('mouseleave',leave);
  box.addEventListener('focusin',enter);    box.addEventListener('focusout',leave);
}
function renderLead(){
  const box=document.getElementById('leadRow');
  if(!box||!DATA) return;
  const wasOn=leadWindow(LEAD.pool, LEAD.page)[0];
  LEAD.pool=leadPick(DATA.articles||[], Math.floor(Date.now()/1000));
  /* a new payload reshuffles the twenty: stay with the story the reader was
     looking at instead of snapping back to page one every sixty seconds */
  if(wasOn){
    const at=LEAD.pool.map(a=>a.id).indexOf(wasOn.id);
    if(at>=0) LEAD.page=Math.floor(at/LEAD_PER);
  }
  if(LEAD.page>=leadPages(LEAD.pool)) LEAD.page=0;
  initLead();
  paintLead(false);
}
/* one slot on the single clock, and every reason not to fire lives in its
   `when`: another tab's worth of rotation is work nobody asked for */
Clock.every(LEAD_ROTATE_MS, ()=>{ if(leadPages(LEAD.pool)>1) leadStep(1); }, {
  label:'lead-rotate',
  when:()=>{
    if(typeof UI==='undefined'||UI.view!=='feed') return false;
    if(LEAD.paused||LEAD.hover||document.hidden) return false;
    if(LEAD_REDUCE&&LEAD_REDUCE.matches) return false;   /* motion is optional; readability is not */
    const ov=document.getElementById('artOverlay');
    return !(ov&&ov.classList&&ov.classList.contains('open'));
  }
});
function renderAll(){
  window.__MACRO=DATA.macro||[];
  renderChips(); renderSrcSel(); renderKindSel(); renderFeed();
  renderTicker(); renderLead(); dl2AfterFeed();
  renderSources(); renderSettings(); renderStats(); renderAssetTable(); renderArchive(); renderBookmarks();
  arTick();           /* alert rules see the new headline list on the next slot */
  paintFng(); paintHygiene();
  /* opening the reports tab before the first payload lands used to leave it
     empty forever — the tab needs DATA to pick an asset, so it retries here */
  if(UI.view==='reports'&&!window.__rep&&!window.__repPending)
    pickReport(UI.repSym||orderedAssets()[0], true);
  if(UI.view==='monitor') loadMonitor();
  if(UI.view==='calendar'&&ECON) renderCalendar();
}
/* ── bookmarks tab ── */
function renderBookmarks(){
  const g=document.getElementById('bmarkGrid'), empty=document.getElementById('bmarkEmpty'),
        cnt=document.getElementById('cntBmarks'), sum=document.getElementById('bmarkSummary');
  if(!g) return;
  const ids=getBookmarks(), meta=getBmarkMeta();
  const items=[];
  for(const id of ids.slice().reverse()){                 /* newest bookmark first */
    const a=findArticle(id)||meta[id];
    if(a) items.push(a);
  }
  if(sum) sum.textContent=`${toFa(items.length)} نشان‌شده · ${toFa(ids.length)} شناسه · ذخیره‌شده در همین مرورگر`;
  if(cnt){ if(ids.length){ cnt.style.display='inline-block'; cnt.textContent=toFa(ids.length); } else cnt.style.display='none'; }
  empty.style.display=items.length?'none':'block';
  vsGrid('bmark','bmarkGrid',VS_OPTS_BMARK, items, items.map(cardHTML).join(''));
}
/* ── archive tab ── */
function renderArchive(){
  const g=document.getElementById('archGrid'), empty=document.getElementById('archEmpty'),
        cnt=document.getElementById('cntArchive'), sum=document.getElementById('archSummary');
  if(!g) return;
  const list=DATA.archive||[];
  if(sum) sum.textContent=`${toFa(list.length)} خبر آرشیوشده (کل: ${toFa(DATA.archive_total||list.length)}) · خارج از پنجرهٔ فعال`; 
  if(cnt){ if(list.length){cnt.style.display='inline-block'; cnt.textContent=toFa(list.length);} else cnt.style.display='none'; }
  empty.style.display=list.length?'none':'block';
  /* day-grouped boxed layout — same visual language as the calendar */
  const byDay={}; const days=[];
  for(const a of list){
    const d=(a.datetime_fa||'').split('،')[0]||'قدیمی‌تر';
    if(!byDay[d]){ byDay[d]=[]; days.push(d); }
    byDay[d].push(a);
  }
  /* the day header is a full-row item, so windowing cannot lose the grouping:
     whichever rows are on screen, each one carries its own header */
  const flat=[];
  for(const day of days){
    flat.push({__full:true, __day:day, n:byDay[day].length});
    for(const a of byDay[day]) flat.push(a);
  }
  vsGrid('archive','archGrid',VS_OPTS_ARCHIVE, flat, days.map(day=>{
    const items=byDay[day];
    return `<div class="calday archday">
      <div class="calday-h"><span class="calday-title">${ic('calendar')} ${esc(day)}</span>
        <span class="calday-meta">${toFa(items.length)} خبر آرشیوشده</span></div>
      <div class="archgrid">${items.map(cardHTML).join('')}</div>
    </div>`;
  }).join(''));
}
/* ── source health monitor ── */
let MON=null;
async function loadMonitor(){
  try{
    const r=await fetch('/api/monitor'); const d=await r.json();
    MON=d.monitor; renderMonitor();
  }catch(e){}
}
let recTimer=null;
async function recoverAll(){
  const b=document.getElementById('recoverBtn');
  if(b.disabled) return;
  b.disabled=true;
  try{ await fetch('/api/recover',{method:'POST'}); }
  catch(e){ b.disabled=false; toast('بازیابی شروع نشد'); return; }
  toast('بازیابی عمیق شروع شد — بیش از ۶۰ روش برای هر فید خراب');
  Clock.off(recTimer);
  recTimer=Clock.every(2000, async ()=>{
    const b=document.getElementById('recoverBtn');
    if(!b) return;
    try{
      const r=await fetch('/api/recover/status'); const j=await r.json();
      if(!j.running){
        Clock.off(recTimer); b.disabled=false;
        b.innerHTML=ic('refresh')+' بازیابی همهٔ فیدهای خراب';
        if(j.total) toast(`بازیابی تمام شد — ${toFa(j.fixed)} از ${toFa(j.total)} فید برگشت · ${toFa(j.attempts)} روش امتحان شد`);
        loadMonitor();
        return;
      }
      b.innerHTML=ic('refresh')+` در حال بازیابی… فید ${toFa(j.done||0)} از ${toFa(j.total||0)} · ${toFa(j.attempts||0)} روش · ${toFa(j.fixed||0)} ترمیم‌شده`;
      if((j.attempts||0)%6===0) loadMonitor();      /* refresh rows live */
    }catch(e){}
  },2000);
  setTimeout(loadMonitor, 4000);
}
function renderMonitor(){
  if(!MON) return;
  document.getElementById('monSummary').textContent=`${toFa(MON.ok)} از ${toFa(MON.total)} فید سالم · ${toFa(MON.broken)} خراب`;
  const nb=document.getElementById('cntBroken');
  if(MON.broken>0){ nb.style.display='inline-block'; nb.textContent=MON.broken; nb.style.background='var(--dn)'; nb.style.color='#fff'; }
  else nb.style.display='none';
  const rows=[...MON.rows].sort((a,b)=>(a.ok-b.ok)||(b.count-a.count));
  let html='';
  for(const r of rows){
    if(r.ok&&!r.recovered) continue;                 /* healthy & untouched: skip in monitor */
    const st=r.ok?(r.recovered?`<span class="ok">${ic('check')} بازیابی‌شده</span>`:`<span class="ok">${ic('check')} سالم</span>`)
                 :`<span class="bad">${ic('x')} خراب</span>`;
    const reason=r.ok?'':`<div style="color:var(--cu-txt);margin-block-start:3px">${ic('warn')} علت: ${esc(r.reason_fa||r.detail||'نامعلوم')}</div>`;
    const rec=(r.recovery||[]);
    const shown=rec.slice(0,8);
    const path=rec.length?`<div style="color:var(--ink-3);font-size:10.5px;margin-block-start:2px">بازیابی: ${toFa(rec.length)} روش امتحان شد — ${shown.map(esc).join(' → ')}${rec.length>8?` … (+${toFa(rec.length-8)} روش دیگر)`:''}${r.mirror?' (آینه)':''}${r.ok?' · آخرین موفقیت: '+esc(shown[shown.length-1]||''):''}</div>`:'';
    const hist=(r.hist&&r.hist.length)?`<div style="display:flex;align-items:center;gap:6px;margin-block-start:3px;color:var(--ink-4);font-size:10.5px">۳۰ چرخهٔ آخر: ${histSvg(r.hist)}</div>`:'';
    html+=`<div class="monrow">
      <div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap">
        <span><b>${esc(r.name)}</b> <span style="color:var(--ink-4);font-size:10px">${esc(r.kind_fa||'')}</span></span>
        <span style="font-size:11px">${st}${r.count?` · ${toFa(r.count)} خبر`:''}${r.checked_fa?` · در ${esc(r.checked_fa)}`:''}</span>
      </div>
      ${reason}${path}${hist}
    </div>`;
  }
  document.getElementById('monList').innerHTML=html||'<div class="empty">همهٔ منابع سالماند — فیدی برای ترمیم نیست.</div>';
}
function renderStats(){
  const s=DATA.stats;
  document.getElementById('lastUpd').textContent = fmtEng(s.last_update);
  const d=document.getElementById('cycleDot'), t=document.getElementById('cycleTxt');
  d.className='dot'+(s.cycle_running?' busy':(s.last_error?' err':''));
  /* the cycle pill reads in English — it sits inside the English telemetry line */
  t.textContent = s.cycle_running?'cycle running — fetching & translating':(s.cycles_run? ('cycle #'+s.cycles_run+' done · every '+Math.round(DATA.config.interval/60)+'m'):'starting…');
  document.getElementById('cntFeed').textContent = toFa(DATA.articles.length);
  document.getElementById('cntSrc').textContent = toFa(DATA.sources.filter(x=>x.enabled).length);
  document.getElementById('ruleAge').textContent = DATA.rules.max_age_hours;
  document.getElementById('setAgeInfo').textContent = toFa(DATA.rules.max_age_hours);
  const rb=document.getElementById('refreshBtn'); rb.disabled=!!s.cycle_running;
  rb.innerHTML = s.cycle_running?(ic('clock')+' Refreshing…'):(ic('refresh')+' Refresh');
  const cs = s.cycle_stats||{};
  if(cs.total!=null) document.getElementById('cycleTxt').title =
     `خبر معتبر: ${toFa(cs.total)} | ردشده: ${toFa(cs.rejected)} (قدیمی‌تر از ${toFa(cs.max_age_hours)} ساعت: ${toFa(cs.stale_rejected)}) | فید سالم: ${toFa(cs.feeds_ok)} از ${toFa(cs.feeds_total)}`;
}
/* the cycle countdown and every calendar countdown run on one slot now; see
   clockTick() next to the Clock itself */
Clock.every(1000, clockTick, {label:'clock-tick', immediate:true});

/* ── live prices (free APIs, polled every 15s) ── */
async function pollLive(){
  try{
    const r=await fetch('/api/live'); const d=await r.json();
    if(d.ok&&d.prices){ LIVE=d.prices; if(d.fng&&d.fng.now!=null) window.__FNG=d.fng; paintLive(); paintFng(); arTick(); }
  }catch(e){
    console.error('pollLive:', e);
  }
}
function liveOf(sym){ return LIVE[sym]||null; }
function paintLive(){
  if(UI.view==='reports'&&window.__rep){ updateChartLive(); }
}
/* green/red flash on a price element whose value moved */
function flash(el, dir){ if(!el||!dir) return; el.classList.remove('flash-up','flash-dn'); void el.offsetWidth;
  el.classList.add(dir>0?'flash-up':'flash-dn'); }
/* pollLive() is no longer on a timer of its own: StreamManager calls it only
   while no stream is alive, and stops the moment one connects (2026-09-28). */

/* ── assets strip — deleted.
   The per-asset price cards duplicated the ticker and pushed the first headline
   down the page. Live prices still paint the ticker, the report head and the
   asset table. */
function histSvg(arr){
  if(!arr||!arr.length) return '';
  const W=arr.length*4;
  return `<svg class="histsvg" viewBox="0 0 ${W} 20" preserveAspectRatio="none" role="img" aria-label="health history">`+
    arr.map((v,i)=>`<rect x="${i*4}" y="${v?4:12}" width="3" height="${v?12:4}" fill="${v?'var(--up)':'var(--dn)'}"/>`).join('')+`</svg>`;
}

/* ── sources management (restored: this function and toggleSrc were lost when
   the old chart engine was cut out of the file) ──────────────────────────── */
function renderSources(){
  const list=DATA.sources||[];
  const cnt=document.getElementById('srcCount');
  if(cnt) cnt.textContent=toFa(list.filter(s=>s.enabled).length)+' فعال از '+toFa(list.length);
  const groups={};
  for(const s of list){ (groups[s.kind_fa]=groups[s.kind_fa]||[]).push(s); }
  let html='';
  for(const kind of Object.keys(groups)){
    const items=groups[kind];
    const on=items.filter(x=>x.enabled).length;
    html+=`<div class="kindgroup">
      <div class="kh"><span>${esc(kind)}</span><span style="font-size:11px;color:var(--ink-3)">${toFa(on)}/${toFa(items.length)} فعال</span></div>
      <div class="kb">${items.map(s=>`
        <div class="srcrow">
          <label class="switch"><input type="checkbox" ${s.enabled?'checked':''} aria-label="فعال یا خاموش کردن ${esc(s.name)}" onchange="toggleSrc(${jsArg(s.key)},this.checked)"><span class="slider"></span></label>
          <span class="nm">${esc(s.name)}</span>
          <span class="trust">اعتماد ${toFa(Math.round(s.trust*100))}٪</span>
          <span class="url ltr" title="${esc(s.url||'')}">${esc(s.url||'')}</span>
          <span class="ltr ${s.last_ok===false?'bad':'ok'}" style="font-size:10.5px">${s.last_count==null?'—':(s.last_ok?ic('check')+' '+toFa(s.last_count)+' خبر':ic('x')+' قطع')}</span>
          ${s.type==='custom'?`<button class="btn ghost sm" onclick="removeSrc(${jsArg(s.key)})">حذف</button>`:''}
        </div>`).join('')}</div></div>`;
  }
  const box=document.getElementById('srcList');
  if(box) box.innerHTML=html||'<div class="empty">منبعی فعال نیست.</div>';
}
async function toggleSrc(key,on){
  try{
    await postSettings({source_updates:{[key]:on}});
    toast('منبع بروزرسانی شد — در چرخهٔ بعدی اعمال می‌شود');
  }catch(e){
    toast('خطا در بروزرسانی منبع');
  }
}

/* ── chips ── */
function renderChips(){
  /* the news channel can beat the first /api/data payload: render from what
     is really there instead of trusting a half-built DATA */
  if(!DATA) return;
  const topicsMeta=DATA.topics_meta||{}, assetsMeta=DATA.assets_meta||{};
  const cfgAssets=(DATA.config&&DATA.config.assets)||[];
  const tc=DATA.topic_counts||{};
  const bmarks=getBookmarks();
  const wl=typeof FreebuffWatchlist!=='undefined'?FreebuffWatchlist.get():[];
  let th=`<button class="chip ${UI.topic==='all'&&!UI.onlyBookmarked&&!UI.onlyWatchlist?'on':''}" aria-pressed="${UI.topic==='all'&&!UI.onlyBookmarked&&!UI.onlyWatchlist}" onclick="UI.onlyBookmarked=false;UI.onlyWatchlist=false;UI.topic='all';renderChips();renderFeed()">همه موضوعات <span class="n">${toFa(DATA.articles.length)}</span></button>`;
  if(wl.length){
    th+=`<button class="chip chip-watchlist ${UI.onlyWatchlist?'on':''}" onclick="UI.onlyWatchlist=!UI.onlyWatchlist;UI.onlyBookmarked=false;renderChips();renderFeed()" title="فیلتر اخبار دارایی‌های واچ‌لیست اختصاصی">${ic('star')} ⭐ واچ‌لیست من <span class="n">${toFa(wl.length)}</span></button>`;
  }
  if(bmarks.length){
    th+=`<button class="chip ${UI.onlyBookmarked?'on':''}" onclick="UI.onlyBookmarked=!UI.onlyBookmarked;UI.onlyWatchlist=false;renderChips();renderFeed()">${ic('star')} نشان‌شده‌ها <span class="n">${toFa(bmarks.length)}</span></button>`;
  }
  for(const t of Object.keys(topicsMeta)){
    const n=tc[t]||0; if(!n) continue;
    const tact=UI.topic===t&&!UI.onlyBookmarked&&!UI.onlyWatchlist;
    th+=`<button class="chip ${tact?'on':''}" aria-pressed="${tact}" onclick="setTopicFilter(${jsArg(t)})">${topicIc(t)} ${esc(faTopic(t))} <span class="n">${toFa(n)}</span></button>`;
  }
  document.getElementById('topicChips').innerHTML=th;

  const ac=DATA.asset_counts||{};
  let ah=`<button class="chip ${UI.asset==='all'?'on':''}" aria-pressed="${UI.asset==='all'}" onclick="UI.asset='all';UI.onlyBookmarked=false;UI.onlyWatchlist=false;renderChips();renderFeed()">همه دارایی‌ها</button>`;
  ah+=`<button class="chip" onclick="FreebuffWatchlist.openModal()" style="border-style:dashed;color:#f59e0b" title="ویرایش دارایی‌های واچ‌لیست">⚙️ تنظیم واچ‌لیست</button>`;
  for(const sym of orderedAssets()){
    if(cfgAssets.length&&!cfgAssets.includes(sym)) continue;
    const meta=assetsMeta[sym]||{};
    const aact=UI.asset===sym;
    ah+=`<button class="chip ${aact?'on':''}" aria-pressed="${aact}" onclick="setAssetFilter(${jsArg(sym)})">${assetIc(sym)} ${esc(faAssetName(sym))} <span class="n">${toFa(ac[sym]||0)}</span></button>`;
  }
  document.getElementById('assetChips').innerHTML=ah;
}
/* asset & topic chips are toggles: clicking the active one clears the filter */
function setAssetFilter(sym){ UI.asset = (UI.asset===sym) ? 'all' : sym; UI.onlyBookmarked=false; UI.onlyWatchlist=false; renderChips(); renderFeed(); }
function setTopicFilter(t){ UI.topic = (UI.topic===t) ? 'all' : t; UI.onlyBookmarked=false; UI.onlyWatchlist=false; renderChips(); renderFeed(); }
function renderSrcSel(){
  const sel=document.getElementById('srcSel'), cur=sel.value;
  const srcs=[...new Set(DATA.articles.map(a=>a.source))].sort();
  sel.innerHTML=`<option value="all">همه منابع</option>`+srcs.map(s=>`<option value="${esc(s)}">${esc(s)}</option>`).join('');
  if(srcs.includes(cur)) sel.value=cur;
}
function renderKindSel(){
  const sel=document.getElementById('kindSel'), cur=sel.value;
  const labels=DATA.kind_labels||{}, counts=DATA.kind_counts||{};
  let html='<option value="all">همه دسته‌های منبع</option>';
  for(const [k,fa] of Object.entries(labels)){
    if(!counts[k]) continue;
    html+=`<option value="${k}">${fa} (${toFa(counts[k])})</option>`;
  }
  sel.innerHTML=html;
  if([...sel.options].some(o=>o.value===cur)) sel.value=cur;
}

/* ── feed ── */
function renderFeed(){
  if (!DATA || !DATA.articles) return;
  const rawQ=(document.getElementById('q').value||'').trim().toLowerCase();
  const src=document.getElementById('srcSel').value;
  const kind=document.getElementById('kindSel').value;
  const minC=+document.getElementById('credSlider').value/100;
  const sort=document.getElementById('sortSel').value;
  const sent=document.getElementById('sentSel')?document.getElementById('sentSel').value:'all';
  const tr=document.getElementById('timeRangeSel')?document.getElementById('timeRangeSel').value:'all';
  const wl=typeof FreebuffWatchlist!=='undefined'?FreebuffWatchlist.get():[];

  const tsOf=a=>{ const t=a.published_ts||0; return t>1e12?Math.floor(t/1000):t; };
  const nowSec=Date.now()/1000;

  let list=DATA.articles.filter(a=>{
    if(UI.onlyBookmarked && !isBookmarked(a.id)) return false;
    if(UI.onlyWatchlist && !wl.some(s=>(a.assets||[]).includes(s))) return false;
    if(UI.topic!=='all'&&a.topic!==UI.topic) return false;
    if(UI.asset!=='all'&&!(a.assets||[]).includes(UI.asset)) return false;
    if(src!=='all'&&a.source!==src) return false;
    if(kind!=='all'&&a.source_kind!==kind) return false;
    if(a.credibility<minC) return false;

    // Time range filter
    if(tr!=='all'){
      const maxAgeH=parseFloat(tr);
      if(!isNaN(maxAgeH)){
        const pts=tsOf(a);
        if(pts && (nowSec - pts) > (maxAgeH * 3600)) return false;
      }
    }

    // Sentiment filter
    if(sent!=='all'){
      const txt=((a.title||'')+' '+(a.title_fa||'')+' '+(a.summary||'')+' '+(a.summary_fa||'')).toLowerCase();
      const isBull = /bull|rise|gain|surge|rally|jump|soar|high|buy|breakout|صعود|رشد|افزایش|جهش/i.test(txt);
      const isBear = /bear|drop|fall|plunge|crash|sink|dip|slide|low|sell|down|سقوط|افت|کاهش|ریزش/i.test(txt);
      if(sent==='bullish'&&!isBull) return false;
      if(sent==='bearish'&&!isBear) return false;
      if(sent==='neutral'&&(isBull||isBear)) return false;
    }

    // Advanced search with quotes, negation, and field prefixes
    if(rawQ){
      const fullText=((a.title||'')+' '+(a.title_fa||'')+' '+(a.summary_fa||'')+' '+(a.summary||'')+' '+(a.source||'')+' '+(a.assets||[]).join(' ')).toLowerCase();
      // Negation: -keyword
      const negs = (rawQ.match(/-\b[\w\u0600-\u06ff]+\b/g) || []).map(t=>t.slice(1));
      for(const nt of negs){ if(fullText.includes(nt)) return false; }
      // Source prefix: src:name or source:name
      const srcM = rawQ.match(/(?:src|source):([\w\u0600-\u06ff]+)/);
      if(srcM && !(a.source||'').toLowerCase().includes(srcM[1])) return false;
      // Asset prefix: asset:sym
      const astM = rawQ.match(/asset:([\w]+)/);
      if(astM && !(a.assets||[]).map(x=>x.toLowerCase()).includes(astM[1])) return false;

      let cleanQ = rawQ.replace(/-\b[\w\u0600-\u06ff]+\b/g, '').replace(/(?:src|source|asset):[\w\u0600-\u06ff]+/g, '').trim();
      if(cleanQ){
        const exactMatches = cleanQ.match(/"([^"]+)"/g);
        if(exactMatches){
          for(const em of exactMatches){
            const phrase = em.slice(1, -1).trim();
            if(phrase && !fullText.includes(phrase)) return false;
            cleanQ = cleanQ.replace(em, '').trim();
          }
        }
        if(cleanQ && !fullText.includes(cleanQ)) return false;
      }
    }
    return true;
  });

  if(sort==='new') list.sort((a,b)=>tsOf(b)-tsOf(a)||String(a.source).localeCompare(String(b.source)));
  else if(sort==='cred') list.sort((a,b)=>b.credibility-a.credibility||tsOf(b)-tsOf(a));
  else if(sort==='src') list.sort((a,b)=>a.source.localeCompare(b.source)||tsOf(b)-tsOf(a));
  document.getElementById('feedEmpty').style.display=list.length?'none':'block';
  document.getElementById('feedCount').textContent = toFa(list.length)+' خبر';
  vsGrid('feed','newsGrid',VS_OPTS_FEED, list, list.map(cardHTML).join(''));
  if(typeof syncFeedReset==='function') syncFeedReset();
}


function credBadge(c){
  const pct=Math.round(c*100), cls=pct>=75?'hi':(pct>=55?'mid':'low');
  return `<span class="cred ${cls}" title="امتیاز اعتبار محتوایی: ${toFa(pct)}٪"><span class="bar"><i style="width:${pct}%"></i></span><span>${pct}%</span></span>`;
}
function credChip(c){
  const pct=Math.round(c*100), cls=pct>=75?'hi':(pct>=55?'mid':'low');
  return `<span class="cred ${cls} cred-chip" title="امتیاز اعتبار محتوایی: ${toFa(pct)}٪">${toFa(pct)}٪</span>`;
}
function cardHTML(a){
  if(!a) return '';
  /* the loading skeleton rides the same window as the cards, so the first
     paint does not have to build and then throw away a full grid */
  if(a.__sk!=null) return '<div class="skcard skeleton"></div>';
  const _as=(a.assets||[]);
  const chips=_as.slice(0,2).map(s=>`<span class="badge b-asset">${assetIc(s)}${FA_ASSET[s]||s}</span>`).join('')
    + (_as.length>2?`<span class="badge more">+${toFa(_as.length-2)}</span>`:'');
  const tp=a.topic_fa?`<span class="badge b-topic">${topicIc(a.topic)} ${FA_TOPIC[a.topic]||a.topic_fa}</span>`:'';
  /* a headline can arrive on the news channel before the first /api/data
     payload has landed, and this renderer used to reach straight into DATA
     for the source-kind labels — one early story was enough to throw inside
     the paint and leave the window half-built */
  const kindLabels=(typeof DATA!=='undefined'&&DATA&&DATA.kind_labels)||{};
  const kd=kindLabels[a.source_kind]?`<span class="badge b-kind">${esc(kindLabels[a.source_kind])}</span>`:'';
  const sc=(a.source_kind==='social'&&a.reddit_score!=null)?`<span class="badge b-kind" title="آپ‌ووت زندهٔ ردیت">▲ ${toFa(a.reddit_score)}</span>`:'';
  const faTitle = a.title_fa || a.title;
  const enTitle = a.title_fa ? `<div class="ttl-en">${esc(a.title)}</div>` : '';
  const summ = a.summary_fa || a.summary || '';
  const img = a.image
    ? `<img src="${attr(safeUrl(a.image))}" alt="" loading="lazy" referrerpolicy="no-referrer" data-orig="${attr(a.image)}" onerror="if(!this.dataset.tried){this.dataset.tried='1';this.src='/api/proxy-image?url='+encodeURIComponent(this.dataset.orig);}else{this.replaceWith(Object.assign(document.createElement('div'),{className:'noimg',innerHTML:ic('news')}))}">`
    : '';
  const thumb = `<div class="thumb">${img || '<div class="noimg">'+ic('news')+'</div>'}${credChip(a.credibility)}</div>`;
  const bmarked = isBookmarked(a.id);
  const starBtn = `<button class="star-btn ${bmarked?'on':''}" onclick="toggleBookmark(${jsArg(a.id)}, event)" title="${bmarked?'حذف از نشان‌شده‌ها':'نشان کردن این خبر'}" aria-label="نشان کردن">${ic('star')}</button>`;
  const delBtn = `<button class="del-btn" onclick="hideNews(${jsArg(a.id)}, event)" title="حذف این خبر از داشبورد" aria-label="حذف خبر">${ic('trash')}</button>`;
  return `<div class="ncard" data-id="${attr(a.id)}" role="button" tabindex="0" aria-label="${esc(faTitle)} — ${esc(a.source)}" onclick="openArticle(${jsArg(a.id)})" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();openArticle(${jsArg(a.id)})}">
    ${thumb}
    <div class="body">
      <div class="row1">${tp}${kd}${sc}${chips}</div>
      <div class="ttl">${isNew(a)?'<span class="newdot newdot-inline" title="خبر تازه"></span>':''}${esc(faTitle)}</div>
      ${summ?`<div class="summ">${esc(summ)}</div>`:''}
      <div class="row2">
        <span class="src">${esc(a.source)}</span>
        <span class="dt" title="${esc(a.published_str||'')}">${esc(a.datetime_fa||'')}</span>
        ${starBtn}${delBtn}
      </div>
      <div style="display:flex;gap:6px;margin-top:6px;flex-wrap:wrap">
        <button class="btn ghost sm blurb-btn" onclick="event.stopPropagation();openBlurb(${jsArg(a.id)})" aria-label="توضیحات خبر">${ic('list')} توضیحات خبر</button>
      </div>
    </div>
  </div>`;
}

/* ── delete a news item ──────────────────────────────────────────────────────
   One click removes the story from every view and remembers it: the id is kept
   server-side, so the next scrape of the same link cannot bring it back. The
   list is not lost — Settings shows the count and can restore all of it. */
async function hideNews(id, ev){
  if(ev){ ev.stopPropagation(); ev.preventDefault(); }
  if(!id) return;
  if(typeof confirm==='function' && !confirm('این خبر از داشبورد حذف شود؟\n(از تنظیمات می‌توانی همهٔ حذف‌شده‌ها را برگردانی)')) return;
  const gone=document.querySelectorAll('[data-id="'+id+'"]');
  gone.forEach(el=>el.style.opacity='.35');
  try{
    const r=await fetch('/api/article/hide',{method:'POST',headers:{'Content-Type':'application/json'},
                                           body:JSON.stringify({id:id})});
    const d=await r.json();
    if(!d.ok) throw new Error(d.error||'failed');
    toast('خبر حذف شد — از تنظیمات قابل بازگردانی است');
    await loadData();
  }catch(e){
    gone.forEach(el=>el.style.opacity='');
    toast('حذف نشد — دوباره تلاش کن');
  }
}
/* the hygiene switches (feed sheet + settings) write the same config keys */
async function saveHygiene(){
  const box=document.getElementById('fHideSocial'), num=document.getElementById('fMinChars');
  const sBox=document.getElementById('setHideSocial'), sNum=document.getElementById('setMinChars');
  const gate=document.getElementById('fSocialGate'), sm=document.getElementById('fSocialMin');
  const hide_social = box?box.checked:(sBox?sBox.checked:false);
  const min_chars = parseInt((num?num.value:(sNum?sNum.value:120))||'0',10)||0;
  const gate_on = gate?gate.checked:false;
  const min_score = parseInt((sm?sm.value:2000)||'0',10)||0;
  if(box) box.checked=hide_social;
  if(num) num.value=min_chars;
  if(sBox) sBox.checked=hide_social;
  if(sNum) sNum.value=min_chars;
  if(sm) sm.value=min_score;
  try{
    await postSettings({news_min_chars:min_chars, news_hide_social:hide_social,
                        social_score_filter:gate_on, social_score_min:min_score});
    toast(gate_on?('حداقل لایک اجتماعی: '+toFa(min_score)+' آپ‌ووت')
                 :('فیلتر لایک اجتماعی خاموش است · '+(hide_social?'خبرهای اجتماعی حذف شد':'حداقل '+toFa(min_chars)+' کاراکتر')));
    loadData();
  }catch(e){ toast('ذخیره نشد — دوباره تلاش کن'); }
}
/* the toolbar/settings controls read their state from the saved config */
function paintHygiene(){
  const cfg=(DATA&&DATA.config)||{};
  const hide=!!cfg.news_hide_social, min=(cfg.news_min_chars==null?120:cfg.news_min_chars);
  const gate=!!cfg.social_score_filter, smin=(cfg.social_score_min==null?2000:cfg.social_score_min);
  [['fHideSocial','fMinChars'],['setHideSocial','setMinChars']].forEach(function(p){
    const b=document.getElementById(p[0]), n=document.getElementById(p[1]);
    if(b) b.checked=hide;
    if(n&&document.activeElement!==n) n.value=min;
  });
  const gateEl=document.getElementById('fSocialGate'), sminEl=document.getElementById('fSocialMin');
  if(gateEl) gateEl.checked=gate;
  if(sminEl&&document.activeElement!==sminEl) sminEl.value=smin;
  const info=document.getElementById('hiddenInfo');
  if(info) info.textContent=toFa((DATA&&DATA.hidden_count)||0);
  const btn=document.getElementById('hiddenRestore');
  if(btn) btn.disabled=!((DATA&&DATA.hidden_count)||0);
}
function restoreHidden(){
  if(typeof confirm==='function' && !confirm('همهٔ خبرهای حذف‌شده برگردند؟')) return;
  fetch('/api/article/restore',{method:'POST'}).then(r=>r.json()).then(d=>{
    if(d&&d.ok){ toast('بازگردانی شد: '+toFa(d.restored||0)+' خبر'); loadData(); }
    else toast('بازگردانی نشد');
  }).catch(()=>toast('خطای شبکه در بازگردانی'));
}

/* ── article modal ── */
async function openArticle(id, fa){
  window._activeArtId = id;
  const ov=document.getElementById('artOverlay'); ov.classList.add('open');
  const b=document.getElementById('artBody');
  const url='/api/article/'+id+(fa?'?fa=1':'');
  const waitTxt=fa?'🇮🇷 در حال ترجمهٔ متن به فارسی…':'📝 متن کامل در حال آماده‌سازی…';
  const spinBox=`<div style="display:flex;align-items:center;gap:10px;color:var(--ink-3);font-size:12.5px;padding:6px 0"><span class="spinner"></span><span id="artLoadTxt">${waitTxt}</span></div>`;
  /* paint what we already have instantly — the full text is extracted
     OFF-THREAD server-side and answered with pending:true, so we poll
     instead of blocking the modal for 8-15s */
  try{
    const quick=findArticle(id)||getBmarkMeta()[id];
    if(quick){
      b.innerHTML=`
        <h2>${esc(quick.title_fa||quick.title)}</h2>
        ${quick.title_fa?`<div class="h2en">${esc(quick.title)}</div>`:''}
        <div class="mmeta">
          <span>📰 ${esc(quick.source||'')}</span>
          ${quick.datetime_fa?`<span>🗓 ${esc(quick.datetime_fa)}</span>`:''}
          ${quick.credibility!=null?credBadge(quick.credibility):''}
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-block:2px 6px">
          ${fa?`<button class="btn sm ghost" onclick="openArticle(${jsArg(id)})">🇬🇧 نمایش متن اصلی</button>`
              :`<button class="btn sm on" onclick="openArticle(${jsArg(id)},true)">🇮🇷 ترجمهٔ فارسی متن</button>`}
        </div>
        ${quick.summary_fa||quick.summary?`<div class="msec"><h4>📄 خلاصه</h4><p class="fa">${esc(quick.summary_fa||quick.summary)}</p></div>`:''}
        <div class="msec"><h4>📝 متن کامل خبر</h4>${spinBox}</div>`;
    } else {
      b.innerHTML='<div class="empty" style="padding:30px;text-align:center">'+spinBox+'</div>';
    }
  }catch(e){ b.innerHTML='<div class="empty" style="padding:30px;text-align:center">'+spinBox+'</div>'; }
  const gen = ++_ART_GEN;
  let tries=0;
  const poll=async()=>{
    if (_ART_GEN !== gen) return;
    let d;
    try{ d=await (await fetch(url)).json(); }
    catch(e){
      if (_ART_GEN !== gen) return;
      b.innerHTML='<div class="empty">خطا در دریافت خبر</div>'; return;
    }
    if (_ART_GEN !== gen) return;
    const hasParas = (fa && Array.isArray(d.content_fa) && d.content_fa.length) || (d.content && Array.isArray(d.content.paragraphs) && d.content.paragraphs.length);
    if(d.pending && !hasParas && tries++<20){
      const t=document.getElementById('artLoadTxt');
      if(t) t.textContent=waitTxt+' ('+toFa(tries)+')';
      setTimeout(poll,1000); return;
    }
    render(d);
  };
  const render=(d)=>{
    try{
    const flags=(d.flags||[]).length?`<div class="flags">⚠️ پرچم‌های اعتبارسنجی: ${d.flags.map(esc).join(' — ')}</div>`:'';
    const rel=(d.related||[]).map(x=>`<a class="relrow" href="javascript:void(0)" onclick="openArticle(${jsArg(x.id)});event.stopPropagation()"><span class="reltitle">${esc(x.title)}</span><span class="relsrc">${esc(x.source)}</span>${x.full?`<span class="relfull" title="متن کامل این خبر آماده است">${ic('file')} متن کامل</span>`:''}<span class="relgo">↗</span></a>`).join('');
    const assets=(d.assets||[]).map(s=>`<span class="badge b-asset">${esc(FA_ASSET[s]||s)}</span>`).join(' ');
    const c=d.content||{};
    /* ?fa=1: the server returns content_fa once the background translation
       lands; until then it answers pending and the poll re-renders with it */
    const paras = (fa && Array.isArray(d.content_fa) && d.content_fa.length)
      ? d.content_fa : (c.paragraphs||[]);
    const searchUrl='https://www.google.com/search?q='+encodeURIComponent('"'+d.title+'" '+d.source);
    /* the chip under the heading used to read "۰ کلمه · ۰ پاراگراف" which made a
       blocked publisher look like a broken page; say what actually happened and
       put the publisher's link where the text would be */
    const statusChip = paras.length
      ? `${toFa(c.word_count||0)} کلمه · ${toFa(paras.length)} پاراگراف`
      : '';
    const shortNoteHtml = (c.word_count<60) && paras.length
      ? (/^reddit/.test(c.via||'')
          ? `<div style="font-size:11px;color:var(--ink-3);margin-top:8px">ℹ️ این پست ردیت تصویری/لینکی است و متن کاملی در خودِ پست ندارد؛ همین چند سطر و نظرات بحث از همانجاست. لینک اصلی را باز کنید.</div>`
          : '')
      : '';
    const bodyHtml = paras.length
      ? paras.map(p=>`<p class="${fa && Array.isArray(d.content_fa) && d.content_fa.length ? 'fa' : 'en'}">${esc(p)}</p>`).join('')
      : (d.summary_full
          ? `<p class="en" style="font-size:14px;line-height:1.8">${esc(d.summary_full)}</p>`
          : `<div class="nobody">
               <div class="nobody-cta">
                 <a class="btn ghost sm" href="${attr(safeUrl((c&&c.resolved_url)||d.link))}" target="_blank" rel="noopener">🔗 مشاهده در ${esc(d.source)}</a>
                 <a class="btn ghost sm" href="${searchUrl}" target="_blank" rel="noopener">🔍 جستجوی متن خبر</a>
               </div>
             </div>`);
    const relNote = paras.length
      ? `${toFa((d.related||[]).length)} خبر هم‌موضوع`
      : 'اخبار مرتبط هم‌موضوع';
    b.innerHTML=`
      <div class="row1" style="display:flex;gap:6px;flex-wrap:wrap">
        <span class="badge b-topic">${topicIc(d.topic)} ${esc(FA_TOPIC[d.topic]||'')}</span>${assets}
        ${(DATA.kind_labels||{})[d.source_kind]?`<span class="badge b-kind">${DATA.kind_labels[d.source_kind]}</span>`:''}
      </div>
      <h2>${esc(d.title_fa||d.title)}</h2>
      ${d.title_fa?`<div class="h2en">${esc(d.title)}</div>`:''}
      <div class="mmeta">
        <span>📰 ${esc(d.source)}${d.via?(' · از طریق '+esc(d.via)):''}</span>
        <span>✍️ ${esc(d.author||'—')}</span>
        <span>🗓 ${esc(d.datetime_fa||d.published_str||'')}</span>
        ${credBadge(d.credibility)}
      </div>
      ${flags}
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-block:0 10px">
        ${fa?`<button class="btn sm ghost" onclick="openArticle(${jsArg(id)})">🇬🇧 نمایش متن اصلی (English)</button>`
            :`<button class="btn sm on" onclick="openArticle(${jsArg(id)},true)">🇮🇷 ترجمهٔ فارسی متن کامل</button>`}
      </div>
      ${(d.summary_full_fa||d.summary_full)?`<div class="msec"><h4>📄 خلاصه (فارسی)</h4><p class="fa">${esc(d.summary_full_fa||'')}</p>
        ${!d.summary_full_fa&&d.summary_full?`<p class="en" style="font-size:12px;color:var(--ink-3)">${esc(d.summary_full)}</p>`:''}
        <h4 style="margin-top:10px">📄 Original summary</h4><p class="en" style="font-size:12px;color:var(--ink-3)">${esc(d.summary_full||'—')}</p></div>`:''}
      <div class="msec">
        <h4><span>📝 متن خبر</span>
          <span style="font-size:10.5px;color:var(--ink-3)">${statusChip}</span></h4>
        <div class="scroll">${bodyHtml}</div>
        ${shortNoteHtml}
      </div>
      <a class="mlink" href="${attr(safeUrl((c&&c.resolved_url)||d.link))}" target="_blank" rel="noopener">🔗 مشاهده در ${esc(d.source)}</a>
      ${rel?`<div class="msec rel" style="margin-top:12px"><h4>🧩 اخبار مرتبط <span style="font-size:10.5px;color:var(--ink-3);font-weight:400">${relNote}</span></h4>${rel}</div>`:''}`;
    }catch(e){ b.innerHTML='<div class="empty">خطا در دریافت خبر</div>'; }
  };
  poll();
}
function closeModal(id){
  const el=document.getElementById(id);
  if(el) el.classList.remove('open');
}

/* ── reports ── */
function renderRepChips(){
  const list=orderedAssets();
  document.getElementById('repChips').innerHTML=list.map(s=>{
    const m=DATA.assets_meta[s]||{};
    return `<button class="chip ${UI.repSym===s?'on':''}" onclick="pickReport(${jsArg(s)})">${assetIc(s)} ${esc(faAssetName(s))}</button>`;
  }).join('');
  const n=document.getElementById('repChipsN');
  if(n) n.textContent='· '+toFa(list.length)+' دارایی';
  const nm=document.getElementById('repBtnName');
  if(nm&&UI.repSym) nm.textContent=faAssetName(UI.repSym);
}
/* the toolbar button names the open report; the picker itself lives in the sheet */
function setRepBtnName(sym){
  const nm=document.getElementById('repBtnName');
  if(nm) nm.textContent=faAssetName(sym);
}
function pickReport(sym, keepLang){
  UI.repSym=sym; if(!keepLang) UI.repLang='en';
  showView('reports', true);   // skipPick: never call back into pickReport
  renderRepChips();
  setRepBtnName(sym);
  if(typeof tbClose==='function') tbClose('repSheet');   /* pick → the sheet has done its job */
  const box=document.getElementById('repBox');
  box.innerHTML=`<div class="empty" style="display:flex;align-items:center;justify-content:center;gap:10px;padding:44px 0"><span class="spinner"></span>${UI.repLang==='fa'?'🇮🇷 در حال ترجمهٔ گزارش به فارسی…':'⏳ در حال ساخت گزارش…'}</div>`;
  const url='/api/report/'+sym+(UI.repLang==='fa'?'?lang=fa':'');
  window.__repPending=sym;
  fetch(url).then(r=>r.json()).then(rep=>{
    window.__repPending=null;
    if(rep.error){ box.innerHTML=`<div class="empty">خطا در تولید گزارش: ${esc(rep.error)}</div>`; return; }
    UI.repSections=rep.sections;
    const fa = UI.repLang==='fa';
    const mv = (rep.sections.find(s=>s[0]==='meta')||[null,{}])[1];
    const mm = (DATA&&DATA.assets_meta&&DATA.assets_meta[rep.symbol])||{};
    const lv0 = liveOf(rep.symbol);
    const p0 = (lv0&&lv0.price!=null)?lv0.price:mv.price;
    const c0 = (lv0&&lv0.change_24h!=null)?lv0.change_24h:mv.change_24h;
    const toc=[];                 /* section jump chips: a long report stops being a scroll hunt */
    let doc='';
    for(const [kind,val] of rep.sections){
      if(kind==='meta') continue;               /* the hero carries it now */
      if(kind==='h'){
        const id='repsec-'+(toc.length+1);
        const label=fa?(val.fa||val.en):val.en;
        toc.push({id:id, label:label});
        doc+=`<h3 id="${id}" class="rep-sec">${esc(label)}</h3>`;
      }
      else if(kind==='p'){
        const t = fa ? (val.fa || val.en) : val.en;
        doc+=`<p class="${fa?'fa':'en'}">${mdLite(t)}</p>`;
        if(fa && !val.fa) doc+=`<p class="fa" style="color:var(--warn);font-size:11px">ترجمه این بخش در دسترس نبود؛ متن انگلیسی نمایش داده شد.</p>`;
      }
      else if(kind==='cites'){
        const items=val.items||[];
        if(!items.length) continue;
        /* the sources sit behind one button — closed by default, so the report
           reads as analysis, not as a bibliography */
        doc+=`<section class="cites">
          <button class="cites-btn" onclick="toggleCites(this)" aria-expanded="false">
            <span class="cb-ic">${ic('bookmark')}</span>
            <span class="cb-t">منابع این بخش</span>
            <span class="cb-n">${toFa(items.length)} خبر</span>
            <span class="cb-a">نمایش منابع</span>
          </button>
          <div class="cites-body">
            <div class="cites-list">${items.map(it=>citeHTML(it,fa)).join('')}</div>
          </div>
        </section>`;
      }
    }
    box.innerHTML=`<div class="rep-shell">
      <header class="rep-hero">
        <div class="rh-main">
          <span class="rh-icon" aria-hidden="true">${assetIc(rep.symbol||sym)}</span>
          <div style="min-inline-size:0">
            <h2>${esc(fa?(mv.title_fa||mv.title):(mv.title||mm.fa||rep.symbol))} <span class="rh-sym ltr">${esc(rep.symbol||sym)}</span></h2>
            <div class="rh-sub">
              <span>${ic('clock')} ${esc(fa?(mv.asof_fa||mv.asof):(mv.asof||''))}</span>
              <span>${ic('news')} ${toFa(mv.news_used||0)} خبر استنادشده از ${toFa((mv.sources_used||[]).length)} منبع</span>
            </div>
          </div>
        </div>
        <div class="rh-side">
          <div class="ch-price">
            <span class="p" id="chartLivePrice">${fmtPrice(p0)}</span>
            <span class="c ${c0==null?'':(c0>=0?'up':'dn')}" id="chartLiveChg">${c0==null?'':((c0>=0?'▲ +':'▼ ')+num(c0,2)+'%')}</span>
          </div>
          <div class="rh-actions">
            <button class="btn ghost sm" onclick="copyReport()" title="فقط متن تحلیل کپی می‌شود">${ic('copy')} کپی متن</button>
            <button class="btn ${fa?'on':'ghost'} sm" onclick="toggleLang(${jsArg(sym)},'fa')">ترجمهٔ فارسی</button>
            <button class="btn ${fa?'ghost':'on'} sm" onclick="toggleLang(${jsArg(sym)},'en')">English</button>
          </div>
        </div>
      </header>
      <div class="rep-layout">
        <section class="rep-doc" id="repDoc" tabindex="0" aria-label="متن گزارش تحلیلی">
          ${toc.length>1?`<nav class="rep-toc" aria-label="پرش به بخش‌ها">${toc.map(t=>`<button onclick="jumpRepSec(${jsArg(t.id)})">${esc(t.label)}</button>`).join('')}</nav>`:''}
          ${doc}
        </section>
        <aside class="rep-side" id="chartCol">
          <div id="chartBoxHost"></div>
          <div class="chartbox repfng" id="repFng"></div>
        </aside>
      </div>
    </div>`;
    window.__rep = rep;
    /* the document is one language at a time; the stylesheet keys the heading
       and the section-chip row off this so an English report reads LTR and a
       Persian one stays RTL (see .rep-doc[data-lang]) */
    const docEl=document.getElementById('repDoc');
    if(docEl) docEl.setAttribute('data-lang', fa?'fa':'en');
    renderChartInto(rep);
    loadRepFng(rep.symbol||sym);
  }).catch(()=>{ window.__repPending=null; box.innerHTML='<div class="empty">خطا در دریافت گزارش</div>'; });
}
/* the chart column: the panel plus the Fear & Greed box under it, so a
   timeframe change never wipes the gauge out of the page */
function renderChartInto(rep){
  const host=document.getElementById('chartBoxHost');
  if(!host||!rep) return;
  host.innerHTML=renderChartPanel(rep.chart);
  afterChartRender();
}
/* the panel is the widget — there is nothing else to mount, and it does not
   depend on the server having candle history for the asset */
function afterChartRender(){
  const rep=window.__rep; if(!rep) return;
  if(rep.symbol!==TVW.sym) TVW.sym=rep.symbol;
  mountTVChart(true);
}
function toggleLang(sym,lang){
  if(UI.repLang===lang) return;
  UI.repLang=lang; pickReport(sym,true);
}
function mdLite(t){ return esc(t).replace(/\*\*(.+?)\*\*/g,'<b>$1</b>'); }
/* «کپی متن» = analysis prose only (headings + paragraphs). No citation boxes,
   no links — exactly what the user asked for. */
function reportText(rep, fa){
  let out='';
  for(const [kind,val] of (rep.sections||[])){
    if(kind==='meta'){ out+=`# ${fa?(val.title_fa||val.title):val.title}\n`; out+=`${fa?(val.asof_fa||val.asof):val.asof} | ${val.price}\n`; }
    else if(kind==='h') out+=`\n## ${fa?val.fa:val.en}\n`;
    else if(kind==='p') out+=(fa?(val.fa||val.en):val.en)+'\n';
    /* kind==='cites' → never copied */
  }
  return out.replace(/\n{3,}/g,'\n\n').trim()+'\n';
}
function copyReport(){
  const fa=UI.repLang==='fa';
  navigator.clipboard.writeText(reportText(window.__rep||{sections:[]}, fa))
    .then(()=>toast('متن تحلیل کپی شد ✓'));
}

/* ── chart panel — TradingView and nothing else ───────────────────────────
   The old panel carried a second, hand-drawn chart with Bollinger bands, EMAs,
   support/resistance and an RSI/MACD pane. It is gone: two charts meant two
   sources of truth for the same asset, and the drawn one needed the server's
   price history before it could show anything at all. What remains is the
   official TradingView embed — real candles, its own intervals, indicators and
   drawing tools — plus a link out for when the embed is blocked. */
function renderChartPanel(c){
  const s=((c&&c.sym)||TVW.sym||'').toUpperCase();
  return `<div class="chartbox" id="chartBox">
    <div class="chart-head">
      <h3>${ic('chart')} نمودار ${assetIc(s)} ${esc(faAssetName(s))}
        <span class="ch-sym ltr">${esc(s)}</span></h3>
      <span class="chart-live" id="tvLiveTag">${ic('clock')} در حال اتصال…</span>
      <div class="chart-tools">
        <a class="btn ghost sm" href="https://www.tradingview.com/chart/?symbol=${encodeURIComponent(tvSymbolFor(s))}"
           target="_blank" rel="noopener">${ic('external')} باز کردن در تریدینگ‌ویو</a>
        <button class="btn ghost sm" id="tvFullBtn" onclick="toggleTvFull()">${ic('expand')} بزرگ‌نمایی</button>
      </div>
    </div>
    <div class="tvwrap" id="tvwrap"><div id="tvholder"></div></div>
    <div class="tvfail" id="tvfail" style="display:none"></div>
  </div>`;
}
/* merge the live quote into the chart head + last point of the price line */
function updateChartLive(){
  /* the widget streams its own candles; what this keeps live is the quote line
     above the panel and the connection pill next to its title */
  const rep=window.__rep; if(!rep) return;
  const lv=liveOf(rep.symbol), tag=document.getElementById('tvLiveTag');
  const p=document.getElementById('chartLivePrice'), chg=document.getElementById('chartLiveChg');
  if(lv&&lv.price!=null&&p){
    const prev=+p.dataset.v||((rep.chart&&rep.chart.price)||null);
    p.textContent=fmtPrice(lv.price);
    if(prev!=null) flash(p, lv.price-prev);
    p.dataset.v=lv.price;
    if(chg&&lv.change_24h!=null){ chg.textContent=(lv.change_24h>=0?'▲ +':'▼ ')+num(lv.change_24h,2)+'%'; chg.className='c '+(lv.change_24h>=0?'up':'dn'); }
  }
  if(!tag) return;
  if(document.querySelector('#tvholder iframe')) tag.innerHTML='<span class="live-dot"></span>لایو';
  else if(!lv) tag.textContent='قیمت لحظه‌ای در دسترس نیست';
}
async function removeSrc(key){ await postSettings({remove_sources:[key]}); toast('منبع حذف شد'); loadData(); }
async function addSource(){
  const name=document.getElementById('newSrcName').value.trim();
  const rss=document.getElementById('newSrcUrl').value.trim();
  if(!name||!rss.startsWith('http')){ toast('نام و آدرس RSS معتبر وارد کنید'); return; }
  await postSettings({add_source:{name,rss}});
  document.getElementById('newSrcName').value=''; document.getElementById('newSrcUrl').value='';
  toast('منبع اضافه شد — در چرخه بعدی خوانده می‌شود'); loadData();
}

/* ── assets manager ── */
function renderAssetTable(){
  const box=document.getElementById('assetTableBox'); if(!box||!DATA) return;
  let rows='';
  for(const sym of orderedAssets()){
    const m=DATA.assets_meta[sym]||{};
    const d=(DATA.market||{})[sym]||{};
    const lv=liveOf(sym);
    const price=lv?lv.price:d.price;
    rows+=`<tr data-sym="${esc(sym)}">
      <td>${assetIc(sym)} ${esc(faAssetName(sym))}</td>
      <td>${esc(m.name||'')}</td>
      <td class="ltr">${esc(m.yahoo||'—')}</td>
      <td class="ltr">${esc(m.coingecko||'—')}</td>
      <td class="ltr"><span class="p">${fmtPrice(price)}</span>${lv?' <span class="live-dot"></span>':''}${m.custom&&d.price==null&&!lv?' <span style="color:var(--cu-hi);font-size:10px" title="نماد Yahoo برای این دارایی داده نداد — آن را اصلاح کن (مثلاً LINK-USD)">'+ic('warn')+'</span>':''}</td>
      <td class="ltr">${toFa(DATA.asset_counts[sym]||0)}</td>
      <td>${m.custom?`<button class="btn ghost sm" onclick="removeAsset(${jsArg(sym)})">حذف</button>`:'<span style="font-size:10px;color:var(--ink-3)">پیش‌فرض</span>'}</td>
    </tr>`;
  }
  box.innerHTML=`<table class="asset-table">
    <thead><tr><th>دارایی</th><th>نام</th><th>نماد Yahoo</th><th>CoinGecko</th><th>قیمت</th><th>خبر</th><th></th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}
async function addAsset(){
  const payload={add_asset:{
    symbol:document.getElementById('naSym').value.trim(),
    fa:document.getElementById('naFa').value.trim(),
    name:document.getElementById('naName').value.trim(),
    yahoo:document.getElementById('naYahoo').value.trim(),
    coingecko:document.getElementById('naCg').value.trim(),
    keywords:document.getElementById('naKw').value.trim()
  }};
  if(!payload.add_asset.symbol||!payload.add_asset.yahoo){ toast('نماد و نماد Yahoo لازم است'); return; }
  await postSettings(payload);
  ['naSym','naFa','naName','naYahoo','naCg','naKw'].forEach(i=>document.getElementById(i).value='');
  toast('دارایی اضافه شد — با بروزرسانی بعدی قیمت و خبر آن می‌آید');
  await loadData(); doRefresh();
}
async function removeAsset(sym){
  await postSettings({remove_assets:[sym]});
  toast('دارایی حذف شد'); await loadData();
}

/* ── settings ── */
function renderSettings(){
  const c=DATA.config;
  document.getElementById('setInterval').value=String(c.interval);
  document.getElementById('setAge').value=String(DATA.rules.max_age_hours);
  document.getElementById('setAutoRep').checked=!!c.auto_reports;
  document.getElementById('assetToggles').innerHTML=orderedAssets().map(s=>{
    const m=DATA.assets_meta[s]||{};
    const on=c.assets.includes(s);
    return `<button class="chip ${on?'on':''}" data-sym="${s}" onclick="this.classList.toggle('on')">${assetIc(s)} ${esc(faAssetName(s))}</button>`;
  }).join('');
}
async function saveSettings(){
  const assets=[...document.querySelectorAll('#assetToggles .chip.on')].map(b=>b.dataset.sym);
  if(!assets.length){ toast('حداقل یک دارایی انتخاب کنید'); return; }
  await postSettings({interval:+document.getElementById('setInterval').value,
                      report_max_age_hours:+document.getElementById('setAge').value,
                      assets, auto_reports:document.getElementById('setAutoRep').checked,
                      news_min_chars:parseInt((document.getElementById('setMinChars')||{}).value||'0',10)||0,
                      news_hide_social:!!((document.getElementById('setHideSocial')||{}).checked)});
  toast('تنظیمات ذخیره شد ✓'); loadData();
}
async function postSettings(payload){
  const r=await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  return r.json();
}

/* ── refresh / toast ── */
async function doRefresh(){
  const rb=document.getElementById('refreshBtn'); rb.disabled=true; rb.innerHTML=ic('clock')+' ارسال درخواست…';
  try{ await fetch('/api/refresh',{method:'POST'}); toast('چرخه بروزرسانی شروع شد'); }
  finally{ setTimeout(()=>{rb.disabled=false;rb.innerHTML=ic('refresh')+' Refresh';},1500); }
}
function toast(msg){
  const t=document.getElementById('toast'); t.textContent=msg; t.style.display='block';
  clearTimeout(t._h); t._h=setTimeout(()=>t.style.display='none',2600);
}
document.addEventListener('keydown',e=>{ if(e.key==='Escape'){ closeModal('artOverlay'); closeModal('blurbOverlay'); closeModal('calDocOverlay'); } });
document.getElementById('ibSources').onclick=()=>showView('sources');
document.getElementById('ibAssets').onclick=()=>showView('assets');

/* ═══════════ economic calendar & market context (/api/econ) ═══════════ */
let ECON=null, ECON_AT=0;
async function loadCalendar(){
  try{
    const r=await fetch('/api/econ'); const d=await r.json();
    ECON=d; ECON_AT=Date.now();   }catch(e){ renderCalendar(); }
}
const FA_DAY={'Saturday':'شنبه','Sunday':'یکشنبه','Monday':'دوشنبه','Tuesday':'سه‌شنبه','Wednesday':'چهارشنبه','Thursday':'پنجشنبه','Friday':'جمعه'};
const FA_MONTH={'Farvardin':'فروردین','Ordibehesht':'اردیبهشت','Khordad':'خرداد','Tir':'تیر','Mordad':'مرداد','Shahrivar':'شهریور','Mehr':'مهر','Aban':'آبان','Azar':'آذر','Dey':'دی','Bahman':'بهمن','Esfand':'اسفند'};
function isoOf(d){ return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'); }
function todayIso(){ return isoOf(new Date()); }
/* The selected day is the single source of truth: the day strip, the board and
   both side widgets all derive from it, so nothing can disagree about which
   day is on screen. Weeks move by moving the day. */
let CAL = {day:null};
function shiftCalWeek(n){ CAL.day=addDays(CAL.day||tzNow(),7*n); renderCalendar(); }
function gotoCalToday(){ CAL.day=tzNow(); renderCalendar(); }
function jumpToNextEventDay(){
  const days=[...new Set((window.__calPool||[]).map(e=>e._day))].sort();
  if(!days.length) return;
  CAL.day = days.find(d=>d>=tzNow()) || days[days.length-1];
  renderCalendar();
}
function faDayBox(isoDay){
  /* the economic calendar reads in English, over the Western release week */
  try{
    const d=new Date(isoDay+'T12:00:00Z');
    return esc(d.toLocaleDateString('en-GB',{weekday:'long',month:'short',day:'numeric',timeZone:'UTC'}));
  }catch(e){ return esc(isoDay); }
}
/* ── timezone handling ────────────────────────────────────────────────────
   The server sends every row with an exact UTC epoch (`ts`) and the UTC clock
   in `time_str`. Both are re-formatted here for whichever zone the reader
   picked, so switching the selector moves every time — and the day buckets —
   together. Formatters are memoised because a week is 300+ rows. */
const TZ_FMT={};
function tzFmt(zone,kind){
  const k=zone+'|'+kind;
  if(TZ_FMT[k]) return TZ_FMT[k];
  let f=null;
  try{
    if(kind==='day')  f=new Intl.DateTimeFormat('en-CA',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit'});
    if(kind==='time') f=new Intl.DateTimeFormat('en-GB',{timeZone:zone,hour:'2-digit',minute:'2-digit',hour12:false});
    if(kind==='dow')  f=new Intl.DateTimeFormat('en-GB',{timeZone:zone,weekday:'short'});
    if(kind==='full') f=new Intl.DateTimeFormat('en-GB',{timeZone:zone,weekday:'short',month:'short',day:'numeric'});
  }catch(e){ f=null; }
  TZ_FMT[k]=f;
  return f;
}
function calTz(){ const s=document.getElementById('calTz'); return (s&&s.value)||'Asia/Tehran'; }
function tzDay(ts){ const z=calTz(), f=tzFmt(z,'day'), d=new Date(ts*1000);
  return f?f.format(d):d.toISOString().slice(0,10); }
/* same zone, but written the way the rest of the calendar reads its dates */
function tzDayFa(ts){ const f=tzFmt(calTz(),'full'), d=new Date(ts*1000);
  return f?f.format(d):tzDay(ts); }
function tzClock(ts){ const z=calTz(), f=tzFmt(z,'time'), d=new Date(ts*1000);
  const t=f?f.format(d):d.toISOString().slice(11,16);
  return t==='24:00'?'00:00':t; }
function tzDow(ts){ const f=tzFmt(calTz(),'dow'), d=new Date(ts*1000); return f?f.format(d):''; }
function tzNow(){ return tzDay(Date.now()/1000); }
function addDays(isoDay,n){
  const t=Date.parse(isoDay+'T00:00:00Z')+n*86400000;
  return new Date(t).toISOString().slice(0,10);
}
function shortDay(isoDay){
  /* day-strip cell: one weekday letter over the day number (M 21) */
  const d=new Date(isoDay+'T12:00:00Z');
  let dow='';
  try{ dow=d.toLocaleDateString('en-GB',{weekday:'narrow',timeZone:'UTC'}); }catch(e){ dow=''; }
  return {dow:dow, num:String(d.getUTCDate())};
}
function monOf(isoDay){
  const d=new Date(isoDay+'T00:00:00Z');
  const off=(d.getUTCDay()+6)%7;          /* Monday-first week, like the server */
  return addDays(isoDay,-off);
}
function calCountdown(ts, withSeconds){
  /* the calendar is English: compact terminal countdowns (1d 21h / 21h 51m) */
  let s=Math.round(ts-Date.now()/1000);
  if(s<0) s=0;
  const d=Math.floor(s/86400); s%=86400;
  const h=Math.floor(s/3600); s%=3600;
  const m=Math.floor(s/60), sec=s%60;
  const two=n=>String(n).padStart(2,'0');
  if(d) return d+'d '+two(h)+'h';
  if(h) return h+'h '+two(m)+'m';
  return m+'m '+two(withSeconds?sec:0)+'s';
}
function impClass(v){ return v==='High'?'h':(v==='Medium'?'m':(v==='Holiday'?'hol':'l')); }
function impRank(v){ return v==='High'?0:(v==='Medium'?1:(v==='Low'?2:3)); }
const CAL_IMP_LABEL={High:'High',Medium:'Medium',Low:'Low',Holiday:'Holiday'};
/* the event explainer stays Persian — that is the part meant to be read */
const CAL_IMP_FA={High:'بالا',Medium:'متوسط',Low:'کم',Holiday:'تعطیل'};
/* the sessions rail names its cities in the server's English config — shown in Persian */
/* market sessions read in English too (the names come off the server config) */
const SESSION_FA={'Sydney':'Sydney','Tokyo':'Tokyo','London':'London','New York':'New York','Frankfurt':'Frankfurt','Shanghai':'Shanghai','Hong Kong':'Hong Kong'};
function renderCalendar(){
  const box=document.getElementById('calDays'), cd=document.getElementById('calCountdown');
  if(!box) return;
  if(!ECON){ box.innerHTML='<div class="empty">Loading the calendar…</div>'; return; }
  window.__ECON_FA=ECON.fng_fa||{};
  if(ECON.fng&&ECON.fng.now!=null) window.__FNG=ECON.fng;

  /* pool both loaded weeks (deduped) — the server sends exact UTC epochs, and
     every derived value below (day bucketing, clock, sorting) follows the
     timezone selector, never the UTC clock printed by the server */
  const tz=calTz();
  const pool=[], seen={};
  [ECON.calendar, ECON.calendar_next].forEach(function(src){
    ((src&&src.events)||[]).forEach(function(e){
      const k=e.ts+'|'+e.title+'|'+(e.country||'');
      if(seen[k]) return; seen[k]=1;
      e._day=tzDay(e.ts); e._released=!!(e.actual||e.past);
      e._key = (e.ts||0) + '_' + (e.title||'').replace(/[^a-zA-Z0-9]/g,'').slice(0,20);
      pool.push(e);
    });
  });
  pool.sort((a,b)=>a.ts-b.ts);
  window.__calPool=pool;

  if(!CAL.day) CAL.day=tzNow();
  const selDay=CAL.day, today=tzNow();
  /* only the two weeks the server actually loaded can be shown — say so instead
     of rendering a silent empty day */
  const todayBtn=document.getElementById('calBtnToday');
  if(todayBtn) todayBtn.classList.toggle('on', selDay===today);

  const impSel=document.getElementById('calImpact'), ccyBox=document.getElementById('calCurChips'),
        sSel=document.getElementById('calSort'), hp=document.getElementById('calHidePast'),
        qEl=document.getElementById('calQ');
  /* Currency is a multi-select: USD *and* EUR *and* JPY can be on at once, so
     the old single-value dropdown became a row of tick-boxes. Rebuilt only when
     the currency list present in the data actually changes. */
  if(!CAL.ccys) CAL.ccys=new Set();
  const ccys=[...new Set(pool.map(e=>e.country).filter(Boolean))].sort();
  if(ccyBox && ccyBox.dataset.keys!==ccys.join('|')){
    ccyBox.dataset.keys=ccys.join('|');
    ccyBox.innerHTML=ccys.map(c=>`<label class="ccy${CAL.ccys.has(c)?' on':''}">
        <input type="checkbox" value="${esc(c)}"${CAL.ccys.has(c)?' checked':''} onchange="toggleCalCcy(this)">
        <span>${esc(c)}</span></label>`).join('');
  }
  const impVal=impSel?impSel.value:'all', ccySet=CAL.ccys,
        srtVal=sSel?sSel.value:'time', hideRel=!!(hp&&hp.checked),
        q=(qEl?qEl.value:'').trim().toLowerCase();
  /* the toolbar is painted further down, once the day's rows have actually
     been filtered — its count is the number the reader is looking at */

  /* ── the week strip: 7 day boxes from the Monday of the selected week ── */
  const mon=monOf(selDay);
  const week=[]; for(let i=0;i<7;i++) week.push(addDays(mon,i));
  const byDay={}; pool.forEach(e=>{ (byDay[e._day]=byDay[e._day]||[]).push(e); });
  const strip=document.getElementById('calStrip');
  if(strip){
    strip.innerHTML=week.map(function(d){
      const evs=byDay[d]||[], hi=evs.filter(e=>e.impact==='High').length,
            md=evs.filter(e=>e.impact==='Medium').length;
      const s=shortDay(d);
      const dots='<span class="dots">'+
        (hi?`<i class="h"></i>${hi>1?`<i class="h"></i>`:''}`:(md?'<i class="m"></i>':''))+
        (evs.length?'<i></i>':'<i></i>')+'</span>';
      return `<button class="cal-day ${d===selDay?'on':''} ${d===today?'today':''} ${evs.length?'':'empty'}"
        role="tab" aria-selected="${d===selDay}" onclick="CAL.day='${d}';renderCalendar()">
        <span class="dow">${s.dow}</span><span class="dd">${s.num}</span>
        <span class="n">${evs.length}${hi?` · ${hi} high`:''}</span>${dots}</button>`;
    }).join('');
  }
  const wl=document.getElementById('calWeekLab');
  if(wl){
    const f=d=>{const x=new Date(d+'T12:00:00Z');
      return x.toLocaleDateString('en-GB',{month:'short',day:'numeric',timeZone:'UTC'});};
    wl.textContent=f(mon)+' – '+f(addDays(mon,6));
    wl.classList.toggle('is-now', week.indexOf(today)>=0);
  }
  const src=document.getElementById('calSrc');
  if(src) src.textContent='Source: '+((ECON.calendar&&ECON.calendar.source)||'—')+
    ' · times in '+tz;

  /* ── the day's rows: filter → sort → table ── */
  let evs=(byDay[selDay]||[]).slice();
  if(impVal==='High')        evs=evs.filter(e=>e.impact==='High');
  else if(impVal==='Medium') evs=evs.filter(e=>e.impact==='High'||e.impact==='Medium');
  else if(impVal==='Low')    evs=evs.filter(e=>e.impact!=='Holiday');
  if(ccySet&&ccySet.size) evs=evs.filter(e=>ccySet.has(e.country));
  if(hideRel) evs=evs.filter(e=>!e._released);
  if(q) evs=evs.filter(e=>(e.title+' '+(e.indicator||'')+' '+(e.country||'')).toLowerCase().indexOf(q)>=0);
  const releasedFirst=(a,b)=>(b._released?1:0)-(a._released?1:0)||a.ts-b.ts;
  if(srtVal==='impact') evs.sort((a,b)=>impRank(a.impact)-impRank(b.impact)||a.ts-b.ts);
  else if(srtVal==='released') evs.sort(releasedFirst);
  else evs.sort((a,b)=>a.ts-b.ts);
  window.__calDayCount=evs.length;
  if(typeof renderCalToolbar==='function') renderCalToolbar();   /* FILTER MODEL 3 toolbar */

  const rowHTML=function(e){
    const cls='cal-tr is-'+(e.impact==='Holiday'?'hol':impClass(e.impact))+
              (e._released?' released':' pending')+(e.past&&!e._released?' faded':'');
    const nums=e._released
      ? `<span class="c-num c-act ${e.better===1?'good':(e.better===-1?'bad':'')}"><b>${esc(e.actual_fmt||'—')}</b>${
           e.surprise!==null&&e.surprise!==undefined?`<span class="c-sur ${e.better===1?'good':(e.better===-1?'bad':'')}">${esc(e.surprise_fmt)}</span>`:''}</span>`
      : `<span class="c-num c-act sched">—</span>`;
    const blank=v=>!v||v==='—';
    const fcNum=`<span class="c-num c-fc${blank(e.forecast_fmt)?' sched':''}">${esc(e.forecast_fmt||'—')}</span>`;
    const pvNum=`<span class="c-num c-pv${blank(e.previous_fmt)?' sched':''}">${esc(e.previous_fmt||'—')}</span>`;
    const timer=!e._released
      ? `<span class="cal-timer" data-ts="${e.ts}">${calCountdown(e.ts,true)}</span>` : '';
    return `<div class="${cls}" data-ts="${e.ts}" data-key="${esc(e._key||'')}">
      <span class="c-time">${e.all_day?'All day':esc(tzClock(e.ts))}<small>${esc(e.all_day?'':tzDow(e.ts))}</small></span>
      <span class="c-ccy">${esc(e.country||'—')}</span>
      <span class="c-imp" title="Impact ${esc(CAL_IMP_LABEL[e.impact]||e.impact)}"><i class="imp-dot ${impClass(e.impact)}"></i><b class="imp-lab">${esc(CAL_IMP_LABEL[e.impact]||e.impact)}</b></span>
      <span class="c-ev"><span class="t">${esc(e.title)}</span>${
        e.period?` <span class="p">(${esc(e.period)})</span>`:''}${
        timer?` ${timer}`:''}${e.indicator&&e.indicator!=='Calendar'?`<span class="d">${esc(e.indicator)}</span>`:''}</span>
      ${nums}${fcNum}${pvNum}
      <button class="cal-info" onclick="openCalDoc(${jsArg(e._key)})" title="What this release is — explained in Persian"><svg class="ic"><use href="#i-info"/></svg> توضیح</button>
    </div>`;
  };
  const hiDay=evs.filter(e=>e.impact==='High').length;
  const relDay=evs.filter(e=>e._released).length;
  const head='<div class="cal-th">'+
    '<span>Time</span><span>Ccy</span><span>Impact</span><span>Event</span>'+
    '<span style="text-align:end">Actual</span><span style="text-align:end">Forecast</span>'+
    '<span style="text-align:end">Previous</span><span></span></div>';
  /* nothing registers a day tick any more — the calendar board is repainted by
     the render that got here, and the countdowns are the shared clock's job */
  if(!pool.length){
    box.innerHTML='<div class="empty">Calendar feed unavailable right now — try again in a minute.</div>';
  } else if(!evs.length){
    const loaded=[...new Set(pool.map(e=>e._day))].sort();
    const inWindow=selDay>=loaded[0]&&selDay<=loaded[loaded.length-1];
    box.innerHTML=`<div class="cal-board-h"><span class="d">${faDayBox(selDay)}</span>`+
      `<span class="cal-tz-chip">${esc(tz)}</span>`+
      `<span class="m">no events</span></div><div class="empty">`+
      (inWindow?'No event on this day with these filters.'
               :'No data loaded for this week — the dashboard keeps the current week and the next.')+
      `<br><button class="btn ghost sm" style="margin-block-start:14px" onclick="jumpToNextEventDay()">Jump to the nearest day with events ›</button></div>`;
  } else {
    box.innerHTML=`<div class="cal-board-h">
        <span class="d">${faDayBox(selDay)}</span>
        <span class="cal-tz-chip">${esc(tz)}</span>
        <span class="m">${evs.length} ${evs.length===1?'event':'events'} · ${relDay} released${hiDay?` · ${hiDay} high impact`:''}</span>
      </div>
      <div class="cal-tbl">${head}${evs.map(rowHTML).join('')}</div>`;
  }

  /* ── hero: next high-impact release + week counters ── */
  const upcoming=pool.filter(e=>e.ts>Date.now()/1000).sort((a,b)=>a.ts-b.ts);
  const hi=upcoming.filter(e=>e.impact==='High');
  const next=hi[0]||upcoming[0];
  const tt=document.getElementById('calHeroTtl');
  const nb=document.getElementById('cntEvents');
  if(nb){ if(hi.length){ nb.style.display='inline-block'; nb.textContent=String(hi.length); } else nb.style.display='none'; }
  const rel=document.getElementById('calReleased');
  window.__calHeroTick=null;
  const tick=function(){
    if(!next){ cd.textContent='No upcoming event in the loaded window'; if(tt) tt.textContent='—'; if(rel) rel.style.display='none'; return; }
    if(tt) tt.innerHTML=`<span class="ccy">${esc(next.country||'')}</span><span class="imp">Impact ${esc(CAL_IMP_LABEL[next.impact]||next.impact)}</span>${esc(next.title)}`;
    if(next.ts<=Date.now()/1000){
      const relRow=pool.filter(e=>e._released&&e.impact==='High').sort((a,b)=>b.ts-a.ts)[0];
      if(rel&&relRow){
        rel.style.display='flex';
        rel.innerHTML=`<span><svg class="ic"><use href="#i-check"/></svg></span> Just released: <b>${esc(relRow.title)}</b> `+
          (relRow.actual_fmt?`<span style="direction:ltr">actual <b>${esc(relRow.actual_fmt)}</b> vs forecast ${esc(relRow.forecast_fmt)}</span>`:'')+
          `<span class="ltr" style="opacity:.75">${esc(tzClock(relRow.ts))} ${esc(tz)}</span>`;
      }
      const after=pool.filter(e=>e.ts>Date.now()/1000&&e.impact==='High').sort((a,b)=>a.ts-b.ts)[0];
      cd.innerHTML=after?('Next high impact in <b>'+calCountdown(after.ts,false)+'</b> — '+esc(after.title))
                        :'No further high-impact event in the loaded window';
      return;
    }
    if(rel) rel.style.display='none';
    const when=tzDay(next.ts)===tzNow()?'today':faDayBox(tzDay(next.ts));   /* tzDay stays ISO: it is the bucket key */
    cd.innerHTML=`in <b>${calCountdown(next.ts,true)}</b> · ${esc(tzClock(next.ts))} ${esc(tz)} · ${esc(when)}`;
  };
  tick();
  /* the hero is a function now, not a timer: clockTick() calls it on the shared
     second, and re-rendering the calendar swaps the function shell */
  window.__calHeroTick=tick;

  const st=document.getElementById('calStats');
  if(st){
    const wk=pool.filter(e=>week.indexOf(e._day)>=0);
    const wkHi=wk.filter(e=>e.impact==='High').length;
    const wkRel=wk.filter(e=>e._released).length;
    const surplus=wk.filter(e=>e.better===1).length, shortf=wk.filter(e=>e.better===-1).length;
    st.innerHTML=[[wk.length,'events', ''],[wkHi,'high','hi'],[wkRel,'released','rel'],
                  [surplus,'beat','rel'],[shortf,'missed','hi']]
      .map(x=>`<span class="cal-stat ${x[2]}"><b>${x[0]}</b><span>${x[1]}</span></span>`).join('');
  }

  renderCalHigh(pool, selDay);
  renderSessions();
  renderEtfLive('etfLive2');
}

/* the high-impact releases OF THE DAY ON THE BOARD — not a second, longer list
   answering a different question. Same day as the table above it. */
function renderCalHigh(pool, day){
  const box=document.getElementById('calHighList'); if(!box) return;
  const lab=document.getElementById('calHighDay');
  if(lab) lab.textContent=faDayBox(day);
  const hi=pool.filter(e=>e._day===day&&e.impact==='High').sort((a,b)=>a.ts-b.ts);
  if(!hi.length){ box.innerHTML='<span class="hint">No high-impact release on this day.</span>'; return; }
  box.innerHTML=hi.map(e=>`<div class="cal-high-row">
      <div class="t">${esc(e.title)}</div>
      <div class="meta"><b class="js-cal-cd" data-ts="${e.ts}">${e._released?'released':calCountdown(e.ts,false)}</b>
        <span>${esc(tzClock(e.ts))} ${esc(calTz())}</span>
        <span>${esc(e.country||'')}</span></div>
      <button class="cal-info" style="margin-block-start:6px" onclick="openCalDoc(${jsArg(e._key)})"><svg class="ic"><use href="#i-info"/></svg> توضیح</button></div>`).join('');
}

/* every countdown on the calendar tab (rows, side rail, hero) is updated by
   clockTick() under the Clock — there used to be a second 1 s loop here */

/* ══ historical price reaction to a release (inside the calendar explainer) ══
   What a print does to the tape, not just what the print was. Per pairing,
   `dir` is the sign the asset takes when the print arrives ABOVE forecast
   (a hot CPI lifts the dollar and pressures bullion and crypto), and a print
   below forecast mirrors it; `typ.sd` / `typ.rel` are the typical surprise in
   absolute and relative terms, and `m15`/`h1` are the typical moves at minute
   15 and 60 — the first leg is front-loaded, because a release travels most of
   its distance in the first quarter hour. There is no live backtest endpoint,
   so every row the model produces is badged «مرجع»: the dates follow the
   indicator's own release cadence and the consensus is taken from this same
   calendar feed where it exists. The figures are a reference model, never a
   measurement of what actually happened. */
const CAL_REACT_RULES=[
  {id:'cpi', label:'شاخص قیمت مصرف‌کننده (تورم)', geos:['US'], cadence:'monthly', unit:'%', dec:1,
   lowerIsBetter:false, typ:{fc:0.3, sd:0.2, rel:0.6},
   match:[/\bcore cpi\b/i, /\bcpi\b/i, /consumer price index/i],
   assets:[{s:'DXY',dir:1,m15:0.22,h1:0.35},{s:'XAU',dir:-1,m15:0.48,h1:0.78},
           {s:'BTC',dir:-1,m15:0.70,h1:1.15},{s:'SPX',dir:-1,m15:0.32,h1:0.55},
           {s:'VIX',dir:1,m15:0.60,h1:0.95}]},
  {id:'ppi', label:'شاخص قیمت تولیدکننده (PPI)', geos:['US'], cadence:'monthly', unit:'%', dec:1,
   lowerIsBetter:false, typ:{fc:0.2, sd:0.2, rel:0.6},
   match:[/\bppi\b/i, /producer price/i],
   assets:[{s:'DXY',dir:1,m15:0.14,h1:0.24},{s:'XAU',dir:-1,m15:0.26,h1:0.42},
           {s:'BTC',dir:-1,m15:0.34,h1:0.62},{s:'SPX',dir:-1,m15:0.20,h1:0.34}]},
  {id:'nfp', label:'اشتغال غیرکشاورزی (NFP)', geos:['US'], cadence:'monthly', unit:'', dec:0,
   lowerIsBetter:false, typ:{fc:150000, sd:30000, rel:0.35},
   match:[/non-?farm payrolls?/i, /\bnfp\b/i],
   assets:[{s:'DXY',dir:1,m15:0.20,h1:0.34},{s:'XAU',dir:-1,m15:0.40,h1:0.72},
           {s:'BTC',dir:-1,m15:0.45,h1:0.85,mixed:true},
           {s:'SPX',dir:1,m15:0.28,h1:0.45,mixed:true}]},
  {id:'adp', label:'اشتغال بخش خصوصی ADP', geos:['US'], cadence:'monthly', unit:'', dec:0,
   lowerIsBetter:false, typ:{fc:120000, sd:25000, rel:0.35},
   match:[/\badp\b/i],
   assets:[{s:'DXY',dir:1,m15:0.10,h1:0.18},{s:'XAU',dir:-1,m15:0.18,h1:0.30},
           {s:'BTC',dir:-1,m15:0.22,h1:0.40}]},
  {id:'fomc', label:'نرخ بهره فدرال رزرو', geos:['US'], cadence:'6w', unit:'%', dec:2,
   lowerIsBetter:false, typ:{fc:0.25, sd:0.25, rel:0},
   match:[/fed(?:eral)? funds rate/i, /fomc/i, /fed (?:interest )?rate decision/i],
   assets:[{s:'DXY',dir:1,m15:0.30,h1:0.52},{s:'XAU',dir:-1,m15:0.62,h1:1.05},
           {s:'BTC',dir:-1,m15:0.95,h1:1.70},{s:'SPX',dir:-1,m15:0.45,h1:0.80},
           {s:'VIX',dir:1,m15:0.70,h1:1.15}]},
  {id:'claims', label:'مدعیان بیکاری هفتگی', geos:['US'], cadence:'weekly', dow:4, unit:'', dec:0,
   lowerIsBetter:true, typ:{fc:220000, sd:12000, rel:0.06},
   match:[/jobless claims/i, /unemployment claims/i],
   assets:[{s:'DXY',dir:-1,m15:0.06,h1:0.12},{s:'XAU',dir:1,m15:0.12,h1:0.22},
           {s:'SPX',dir:1,m15:0.10,h1:0.18,mixed:true},{s:'BTC',dir:1,m15:0.14,h1:0.26,mixed:true}]},
  {id:'crude', label:'ذخایر نفت خام (EIA)', geos:['US'], cadence:'weekly', dow:3, unit:'', dec:1,
   lowerIsBetter:true, typ:{fc:-1500000, sd:1000000, rel:0.6},
   match:[/crude oil inventories/i, /eia crude/i, /petroleum status/i],
   assets:[{s:'WTI',dir:-1,m15:0.85,h1:1.40},{s:'SPX',dir:1,m15:0.08,h1:0.14,mixed:true}]},
  {id:'retail', label:'خرده‌فروشی آمریکا', geos:['US'], cadence:'monthly', unit:'%', dec:1,
   lowerIsBetter:false, typ:{fc:0.3, sd:0.3, rel:0.6},
   match:[/retail sales/i],
   assets:[{s:'DXY',dir:1,m15:0.16,h1:0.28},{s:'SPX',dir:1,m15:0.22,h1:0.38},
           {s:'XAU',dir:-1,m15:0.22,h1:0.36},{s:'BTC',dir:1,m15:0.30,h1:0.55,mixed:true}]},
  {id:'gdp', label:'تولید ناخالص داخلی', geos:['US'], cadence:'quarterly', unit:'%', dec:1,
   lowerIsBetter:false, typ:{fc:2.0, sd:0.4, rel:0.3},
   match:[/\bgdp\b/i, /gross domestic product/i],
   assets:[{s:'DXY',dir:1,m15:0.16,h1:0.30},{s:'SPX',dir:1,m15:0.26,h1:0.44},
           {s:'XAU',dir:-1,m15:0.24,h1:0.40},{s:'BTC',dir:1,m15:0.32,h1:0.58,mixed:true}]},
  {id:'pmi', label:'شاخص مدیران خرید (ISM/PMI)', geos:['US'], cadence:'monthly', unit:'', dec:1,
   lowerIsBetter:false, typ:{fc:50, sd:1.0, rel:0.04},
   match:[/\bism\b/i, /\bpmi\b/i, /manufacturing index/i],
   assets:[{s:'DXY',dir:1,m15:0.14,h1:0.26},{s:'SPX',dir:1,m15:0.24,h1:0.40},
           {s:'XAU',dir:-1,m15:0.20,h1:0.34},{s:'BTC',dir:1,m15:0.28,h1:0.50,mixed:true}]},
  {id:'ecb', label:'نرخ بهره منطقهٔ یورو', geos:['EU'], cadence:'6w', unit:'%', dec:2,
   lowerIsBetter:false, typ:{fc:0.25, sd:0.25, rel:0},
   /* a rate decision only: “ECB Machado Speech” is not a policy surprise */
   match:[/ecb[^|]{0,24}rate decision/i, /ecb[^|]{0,24}(?:deposit|main refinanc)/i,
          /euro(?:pean)? central bank[^|]{0,24}rate/i, /deposit facility rate/i],
   assets:[{s:'DXY',dir:-1,m15:0.20,h1:0.36},{s:'XAU',dir:-1,m15:0.24,h1:0.42},
           {s:'BTC',dir:-1,m15:0.40,h1:0.70},{s:'SPX',dir:-1,m15:0.22,h1:0.38}]}
];
const CAL_REACT_ROWS=4;                 /* releases kept in the sample */
const CAL_REACT_FRONT=.35;              /* share of the move done by minute 15 */
/* kind → the sign the surprise carries in the rule's own direction map */
const CAL_REACT_KIND={pos:{sgn:1, fa:'بیشتر از انتظار'}, neg:{sgn:-1, fa:'کمتر از انتظار'}, flat:{sgn:0, fa:'مطابق انتظار'}};
function calReactRule(e){
  if(!e) return null;
  const hay=(e.title||'')+' '+(e.indicator||'')+' '+(e.category||'');
  for(const r of CAL_REACT_RULES){
    if(r.geos && e.geo && r.geos.indexOf(e.geo)<0) continue;
    if(r.match.some(rx=>rx.test(hay))) return r;
  }
  return null;
}
function calReactHash(s){ let h=0; for(let i=0;i<s.length;i++) h=(h*31+s.charCodeAt(i))|0; return Math.abs(h); }
/* calendar-event → a row of its own (real numbers straight off the feed) */
function calReactLiveRow(ev, rule){
  const kind=ev.surprise==null?'flat':(ev.surprise>0?'pos':(ev.surprise<0?'neg':'flat'));
  const sd=Math.abs(ev.surprise||0);
  const strength=sd?Math.max(.6,Math.min(1.6,.6+.35*(sd/(rule.typ.sd||1)))):0.5;
  return {ts:ev.ts, actual:ev.actual_n, forecast:ev.forecast_n, unit:ev.unit||rule.unit,
          dec:rule.dec, kind:kind, strength:strength, src:'live', title:ev.title||''};
}
/* reference rows: the indicator's own cadence, going back from the event date */
function calReactModelRows(rule, anchorTs, n){
  const out=[], base=new Date(anchorTs*1000);
  const KINDS=['pos','neg','pos','flat'];
  const off=calReactHash(rule.id)%4;
  for(let i=1;i<=n+1 && out.length<n;i++){
    const d=new Date(base.getTime());
    if(rule.cadence==='weekly'){
      d.setUTCDate(d.getUTCDate()-7*i);
      const want=rule.dow==null?3:rule.dow;
      while(d.getUTCDay()!==want) d.setUTCDate(d.getUTCDate()-1);
    } else if(rule.cadence==='monthly'){
      d.setUTCMonth(d.getUTCMonth()-i);
    } else if(rule.cadence==='quarterly'){
      d.setUTCMonth(d.getUTCMonth()-3*i);
    } else {  /* 6w — policy meetings */
      d.setUTCDate(d.getUTCDate()-42*i);
    }
    const ts=Math.floor(d.getTime()/1000);
    if(ts>=anchorTs) continue;
    const kind=KINDS[(i-1+off)%4];
    out.push({ts:ts, kind:kind, src:'model', unit:rule.unit, dec:rule.dec,
              strength:kind==='flat'?0.5:(kind==='pos'?1.0:0.85)});
  }
  return out;
}
function calReactRows(rule, e){
  const pool=[];
  const cal=(typeof ECON!=='undefined'&&ECON)?ECON.calendar:null;
  const events=(cal&&(cal.events||cal))||[];
  (Array.isArray(events)?events:[]).forEach(function(ev){
    if(!ev||ev.ts==null||ev.ts>=e.ts) return;
    if(ev.actual_n==null||ev.forecast_n==null) return;
    const hay=(ev.title||'')+' '+(ev.indicator||'')+' '+(ev.category||'');
    if(ev.geo&&rule.geos&&rule.geos.indexOf(ev.geo)<0) return;
    if(!rule.match.some(rx=>rx.test(hay))) return;
    pool.push(calReactLiveRow(ev,rule));
  });
  pool.sort((a,b)=>b.ts-a.ts);
  const rows=pool.slice(0,CAL_REACT_ROWS);
  const need=CAL_REACT_ROWS-rows.length;
  if(need>0) rows.push(...calReactModelRows(rule, e.ts, need));
  /* numbers for the reference rows: the live consensus when the feed has one,
     otherwise the indicator's typical print — the path is what is modelled */
  const fcBase=(typeof e.forecast_n==='number')?e.forecast_n:(rule.typ.fc||0);
  rows.forEach(function(r){
    if(r.forecast==null) r.forecast=fcBase;
    if(r.actual==null){
      const sgn=CAL_REACT_KIND[r.kind].sgn;
      /* magnitude of the modelled surprise: the rule's absolute floor, or a
         share of the consensus when the series is a different scale (jobless
         claims run in the hundreds of thousands, continuing claims in the
         millions — one fixed delta cannot serve both) */
      const sdEff=Math.max(rule.typ.sd||0, (rule.typ.rel||0)*Math.abs(fcBase||0));
      r.actual=Math.round((r.forecast + sgn*sdEff)*Math.pow(10,rule.dec))/Math.pow(10,rule.dec);
    }
    r.surp=Math.round((r.actual-r.forecast)*Math.pow(10,rule.dec))/Math.pow(10,rule.dec);
    r.react={};
    rule.assets.forEach(function(a){
      const sgn=CAL_REACT_KIND[r.kind].sgn;
      const dir=a.dir||1;
      r.react[a.s]={m15:a.m15*dir*sgn*r.strength, h1:a.h1*dir*sgn*r.strength};
    });
  });
  return rows;
}
function calReactMove(v){ return (v>0?'+':(v<0?'−':''))+toFa(Math.abs(v).toFixed(2))+'٪'; }
/* the calendar feed hands compact strings (“72K”, “-1.5M”, “0.3%”) but the
   parsed numbers are raw — a modelled print has to print the same way */
function calReactFmt(v, dec, unit){
  if(v==null) return '—';
  const a=Math.abs(v);
  if((unit||'').indexOf('%')>=0 || a<1000) return toFa(v.toFixed(dec))+(unit||'');
  if(a>=1e9) return toFa((v/1e9).toFixed(1))+'B';
  if(a>=1e6) return toFa((v/1e6).toFixed(1))+'M';
  return toFa((v/1e3).toFixed(0))+'K';
}
/* ── SVG mini-chart: a zero baseline with one path per release ── */
function calReactSvg(rows, sym, w, h){
  const padX=44, padY=14;
  const vals=rows.map(r=>(r.react[sym]||{}).h1||0).concat(rows.map(r=>(r.react[sym]||{}).m15||0));
  const max=Math.max(0.2, Math.max.apply(null, vals.map(v=>Math.abs(v))))*1.25;
  const x0=padX, x1=w-padX, midX=x0+(x1-x0)*CAL_REACT_FRONT;
  const yOf=v=>padY+(1-(v+max)/(2*max))*(h-2*padY);
  const zero=yOf(0);
  const parts=[];
  parts.push('<line class="cr-zero" x1="'+x0+'" y1="'+zero+'" x2="'+x1+'" y2="'+zero+'"/>');
  parts.push('<text class="cr-ax" x="'+(x0-6)+'" y="'+(yOf(max)+4)+'">+'+toFa(max.toFixed(1))+'</text>');
  parts.push('<text class="cr-ax" x="'+(x0-6)+'" y="'+(yOf(-max)+4)+'">−'+toFa(max.toFixed(1))+'</text>');
  rows.forEach(function(r, i){
    const p=r.react[sym]||{m15:0,h1:0};
    const cls=p.h1>0?'is-pos':(p.h1<0?'is-neg':'is-flat');
    const d='M'+x0+' '+zero.toFixed(1)+' L'+midX.toFixed(1)+' '+yOf(p.m15).toFixed(1)+' L'+x1+' '+yOf(p.h1).toFixed(1);
    parts.push('<path class="cr-path '+cls+'" d="'+d+'"><title>'+esc(tzDayFa(r.ts))+' — '+esc(CAL_REACT_KIND[r.kind].fa)+' · ۱۵د '+calReactMove(p.m15)+' · ۶۰د '+calReactMove(p.h1)+'</title></path>');
    parts.push('<circle class="cr-dot '+cls+'" cx="'+x1+'" cy="'+yOf(p.h1).toFixed(1)+'" r="2.6"><title>'+esc(calReactMove(p.h1))+'</title></circle>');
  });
  parts.push('<text class="cr-ax is-x" x="'+x0+'" y="'+(h-3)+'">انتشار</text>');
  parts.push('<text class="cr-ax is-x" x="'+midX+'" y="'+(h-3)+'" text-anchor="middle">+۱۵د</text>');
  parts.push('<text class="cr-ax is-x" x="'+x1+'" y="'+(h-3)+'" text-anchor="end">+۶۰د</text>');
  return '<svg class="cr-svg" viewBox="0 0 '+w+' '+h+'" role="img" aria-label="مسیر واکنش '
    +esc(faAssetName(sym))+' در ۶۰ دقیقهٔ پس از '+toFa(rows.length)+' انتشار اخیر">'+parts.join('')+'</svg>';
}
/* ── summary of the sample ──
   Deliberately NOT a win-rate: every path here is produced by the same rule
   that would be measured, so a hit-rate would just restate the rule. What is
   worth stating is the rule itself (real desk knowledge), the size of the
   modelled move, and how the sample splits. */
function calReactStats(rule, rows, sym){
  const a=rule.assets.filter(x=>x.s===sym)[0]||{dir:1};
  const pos=rows.filter(r=>r.kind==='pos').length, neg=rows.filter(r=>r.kind==='neg').length;
  const flat=rows.filter(r=>r.kind==='flat').length;
  const dirRows=rows.filter(r=>r.kind!=='flat');
  const avg=fn=>dirRows.length?dirRows.reduce(function(s,r){ return s+(fn(r.react[sym]||{})||0); },0)/dirRows.length:0;
  const name=faAssetName(sym);
  const bias=a.dir>0?'بالا':'پایین';
  let rule_txt='قاعدهٔ مرجع برای '+name+': غافلگیری مثبت (بالاتر از انتظار) این شاخص آن را '+bias+' می‌برد';
  if(a.mixed) rule_txt+=' — اما این واکنش دووجهی است و سمت آن به جزء دیگر همان روز (بازده اوراق یا نرخ ارز) بستگی دارد';
  if(rule.lowerIsBetter) rule_txt+='؛ برای این شاخص «کمتر از انتظار» جهت را برمی‌گرداند';
  rule_txt+='.  ';
  return {pos:pos, neg:neg, flat:flat, mixed:!!a.mixed, bias:bias,
    avg15:avg(function(p){ return p.m15; }), avg60:avg(function(p){ return p.h1; }),
    rule_txt:rule_txt};
}
function calReactTable(rule, rows){
  const head='<div class="cr-tr cr-th"><span>تاریخ</span><span>واقعی</span><span>پیش‌بینی</span><span>غافلگیری</span><span>۱۵ دقیقه</span><span>۶۰ دقیقه</span><span></span></div>';
  const body=rows.map(function(r){
    const sym=window.__calReact.sym;
    const p=r.react[sym]||{m15:0,h1:0};
    const fmt=v=>esc(calReactFmt(v, rule.dec, r.unit||rule.unit));
    const cls=r.kind==='pos'?'pos':(r.kind==='neg'?'neg':'flat');
    return '<div class="cr-tr">'
      +'<span class="cr-d">'+esc(tzDayFa(r.ts))+'</span>'
      +'<span class="cr-n" dir="ltr">'+fmt(r.actual)+'</span>'
      +'<span class="cr-n" dir="ltr">'+fmt(r.forecast)+'</span>'
      +'<span class="cr-sur is-'+cls+'">'+((r.surp>0?'+':(r.surp<0?'−':''))+esc(calReactFmt(Math.abs(r.surp||0), rule.dec, r.unit||rule.unit)))+' '+CAL_REACT_KIND[r.kind].fa+'</span>'
      +'<span class="cr-n '+(p.m15>0?'pos':(p.m15<0?'neg':''))+'">'+calReactMove(p.m15)+'</span>'
      +'<span class="cr-n '+(p.h1>0?'pos':(p.h1<0?'neg':''))+'">'+calReactMove(p.h1)+'</span>'
      +'<span class="cr-src '+(r.src==='live'?'is-live':'')+'">'+(r.src==='live'?'زنده':'مرجع')+'</span>'
    +'</div>';
  }).join('');
  return '<div class="cr-tbl" role="table" aria-label="واکنش قیمت در چهار انتشار اخیر">'+head+body+'</div>';
}
function calReactInner(rule, rows){
  const st=window.__calReact, a=rule.assets.filter(x=>x.s===st.sym)[0]||rule.assets[0];
  const stat=calReactStats(rule, rows, st.sym);
  const live=rows.filter(r=>r.src==='live').length;
  const chips=rule.assets.map(function(x){
    const sel=x.s===st.sym;
    return '<button type="button" class="cr-chip'+(sel?' on':'')+'" data-react-asset="'+x.s+'" aria-pressed="'+(sel?'true':'false')+'">'
      +esc(x.s)+(x.mixed?' <i class="cr-mx" title="واکنش دووجهی">±</i>':'')+'</button>';
  }).join('');
  return '<div class="cr-chips" role="group" aria-label="دارایی مرتبط">'+chips+'</div>'
    +'<div class="cr-chart">'+calReactSvg(rows, st.sym, 520, 150)+'</div>'
    +'<div class="cr-capline"><span>مسیر قیمت '+esc(faAssetName(st.sym))+' پس از هر انتشار (خط صفر = لحظهٔ انتشار)</span>'
      +(live?('<span class="cr-live">'+toFa(live)+' رديف با عدد منتشرشدهٔ همین تقویم</span>'):'<span class="cr-live is-ref">آرشیو مرجع مدل‌شده</span>')+'</div>'
    +calReactTable(rule, rows)
    +'<p class="cr-stat'+(stat.mixed?' is-mixed':'')+'">'+esc(stat.rule_txt)
      +' <span class="cr-counts">نمونهٔ '+toFa(rows.length)+' انتشار: '+toFa(stat.pos)+' بیشتر از انتظار · '+toFa(stat.neg)+' کمتر از انتظار · '+toFa(stat.flat)+' مطابق انتظار — میانگین مدل‌شدهٔ '+esc(faAssetName(st.sym))+' در ۱۵ دقیقه '+calReactMove(stat.avg15)+' و در ۶۰ دقیقه '+calReactMove(stat.avg60)+'</span></p>';
}
function calReactHTML(e){
  const rule=calReactRule(e);
  if(!rule){
    return '<section class="cal-react is-none"><div class="cr-hd"><h4>واکنش تاریخی قیمت</h4></div>'
      +'<p class="hint">برای این رویداد آرشیو واکنشی ثبت نشده است — ماژول واکنش فقط برای شاخص‌های پرتکرار و پرتأثیر (تورم آمریکا، اشتغال، نرخ بهرهٔ فدرال، ذخایر نفت خام، خرده‌فروشی، GDP، PMI، نرخ بهرهٔ ECB) داده دارد.</p></section>';
  }
  return '<details class="cal-react" open>'
    +'<summary class="cr-hd"><h4>واکنش تاریخی قیمت</h4><span class="cr-rule">'+esc(rule.label)+'</span>'
      +'<span class="cr-badge">آرشیو مرجع · '+toFa(CAL_REACT_ROWS)+' انتشار اخیر</span></summary>'
    +'<div id="calReactBody"></div>'
    +'<p class="hint cr-foot">جهت واکنش هر دارایی از قاعدهٔ رفتاری همان شاخص می‌آید (تورم داغ‌تر ⇒ دلار بالا، طلا و کریپتو و سهام پایین) و اندازهٔ حرکت، میانگین تیپیکال یک‌ساعتهٔ همان جفت‌ارز است. بک‌تست زندهٔ ریز‌داده در دسترس نیست، پس ردیف‌های «مرجع» با آهنگ انتشار همان شاخص و قیمت انتظاری همین تقویم ساخته می‌شوند؛ ردیف‌هایی که تقویم واقعاً مقدار منتشرشده دارد «زنده» نشان می‌شوند. این اعداد سیگنال معاملاتی نیستند.</p></details>';
}
function initCalReact(e){
  const body=document.getElementById('calDocBody');
  if(!body||!body.__crWired){
    if(body){
      body.__crWired=1;
      body.addEventListener('click', function(ev){
        const b=ev.target.closest('[data-react-asset]');
        if(!b) return;
        window.__calReact.sym=b.getAttribute('data-react-asset');
        paintCalReact();
      });
    }
  }
  window.__calReact={rule:calReactRule(e), e:e, sym:null};
  const rule=window.__calReact.rule;
  if(!rule) return;
  /* default asset: the one the desk would watch first (the rule lists them in
     priority order), kept across events while it stays relevant */
  const keep=window.__calReactSym;
  window.__calReact.sym=(keep&&rule.assets.some(x=>x.s===keep))?keep:rule.assets[0].s;
  paintCalReact();
}
function paintCalReact(){
  const st=window.__calReact;
  const box=document.getElementById('calReactBody');
  if(!box||!st||!st.rule) return;
  window.__calReactSym=st.sym;
  const rows=calReactRows(st.rule, st.e);
  box.innerHTML=calReactInner(st.rule, rows);
}
/* ── "Explain" card: what the release is, in plain English ───────────────
   Four sections per event — what it is, how it is measured, why it matters,
   how the market trades it — written by calendar_data.event_doc() on the
   server (deterministic, offline, no model). The card also repeats the row's
   own numbers: actual against forecast with the surprise, and the source. */
function openCalDoc(key){
  const e=(window.__calPool||[]).find(x => x._key === key); if(!e) return;
  const ov=document.getElementById('calDocOverlay'), b=document.getElementById('calDocBody');
  if(!ov||!b) return;
  const num=function(label,val,cls){
    return `<div class="cal-doc-num ${cls||''}"><span>${label}</span><b>${esc(val||'—')}</b></div>`;
  };
  /* Persian, and short: two lines written from the event's own fields. The
     longer English primer is still on the row (`doc_sections`) for anything that
     needs it, but this is what the modal shows. */
  const secs=(e.doc_fa_sections&&e.doc_fa_sections.length)?e.doc_fa_sections:(e.doc_sections||[]);
  const sections=secs.map(s=>
    `<div class="cal-doc-sec"><h4>${esc(s.h)}</h4><p>${esc(s.p)}</p></div>`).join('');
  b.innerHTML=`
    <div class="cal-doc-ttl">${esc(e.title)}${e.period?` <span style="color:var(--ink-3);font-weight:700">(${esc(e.period)})</span>`:''}</div>
    <div class="cal-doc-sub">${esc(e.category?'دستهٔ '+e.category:'رویداد اقتصادی')} · منتشرکننده: ${esc(e.geo_name||e.country||'کشور منتشرکننده')}${e.all_day?' · رویداد تمام‌روز':''}</div>
    <div class="cal-doc-meta">
      <span class="cal-doc-chip"><i class="imp-dot ${impClass(e.impact)}"></i> اهمیت ${esc(CAL_IMP_FA[e.impact]||e.impact)}</span>
      <span class="cal-doc-chip">${esc(e.country||'')}</span>
      <span class="cal-doc-chip">${esc(tzDayFa(e.ts))} · ${esc(e.all_day?'تمام روز':tzClock(e.ts))} ${esc(calTz())}</span>
      ${tzDay(e.ts)!==e.day||calTz()!=='UTC'?`<span class="cal-doc-chip">UTC ${esc(e.time_str||'')}</span>`:''}
      ${e.impact?`<span class="cal-doc-chip imp is-${impClass(e.impact)}">اهمیت ${esc(CAL_IMP_FA[e.impact]||'')}</span>`:''}
      <span class="cal-doc-chip">${esc(e.geo_name||'')}${e.geo_name&&e.country?` (${esc(e.country)})`:''}</span>
      <span class="cal-doc-chip">${esc(e.indicator&&e.indicator!=='Calendar'?e.indicator:'انتشار اقتصادی')}</span>
    </div>
    <div class="cal-doc-nums">
      ${num('مقدار واقعی', e._released?(e.actual_fmt||'—'):'منتشر نشده', e.better===1?'good':(e.better===-1?'bad':''))}
      ${num('پیش‌بینی', e.forecast_fmt)}
      ${num('مقدار قبلی', e.previous_fmt+(e.revision?` (بازنگری ${e.revision})`:''))}
      ${num('غافلگیری', e.surprise_fmt||'—', e.better===1?'good':(e.better===-1?'bad':''))}
    </div>
    ${sections}
    ${calReactHTML(e)}
    <div class="cal-doc-foot">
      <span class="hint">توضیح رویداد به‌صورت محلی از نام، دسته و اهمیت رویداد ساخته می‌شود — قاعده‌محور و بدون مدل زبانی. توصیهٔ سرمایه‌گذاری نیست.</span>
    </div>`;
  initCalReact(e);          /* fills #calReactBody and wires the asset chips */
  ov.classList.add('open');
}
/* ── market sessions ── */
function renderSessions(){
  const box=document.getElementById('sessionsBox'); if(!box||!ECON) return;
  const ss=ECON.sessions||[];
  if(!ss.length){ box.innerHTML='<span class="hint">Sessions unavailable right now.</span>'; return; }
  box.innerHTML=ss.map(s=>{
    const st=s.open?'Open':'Closed';
    const h=Math.floor(s.mins_to_change/60), m=s.mins_to_change%60;
    const to=(s.open?'closes in ':'opens in ')+h+'h '+String(m).padStart(2,'0')+'m';
    return `<div class="session ${s.open?'on':'off'}">
      <span class="ic">${ic('globe')}</span>
      <span class="lbl">${esc(SESSION_FA[s.label]||s.label)}</span>
      <span class="dot" title="${st}"></span>
      <span class="state">${st}</span>
      <span class="eta">${to}</span>
    </div>`;
  }).join('')
  +`<div class="hint" style="margin-block-start:8px">Weekly schedule, times in UTC — the clock refreshes every minute.</div>`;
  /* the session clock is re-armed on every calendar render, so the previous
     slot has to be released first — Clock.off on a handle that was never
     registered is a no-op, which is what makes this safe to call each time */
  Clock.off(window.__sessTick);
  window.__sessTick=Clock.every(60000, ()=>{ if(UI.view==='calendar'&&ECON) renderSessions(); }, {label:'sessions'});
}
/* ── TradingView ideas tab: per-asset filter, chart image, text, permalink ──
   Every card points at the permalink the API resolved. The old build linked to
   /idea/<numeric id>/ which returns 404 — that is why nothing ever opened — so
   the server now returns the real chart_url (and s3 chart thumbnail) instead.
   Thumbnails go through the local image proxy so hotlink rules never blank a
   card; if an image still fails it is hidden and the card keeps image-less
   layout with title, text and link. */
const IDEAS_CACHE={};               // sym -> {items, url, ts}
const IDEAS_TTL=15*60*1000;         // 15 min client-side cache
let IDEAS_SEQ=0;
const IDEA_FA={};                   // "sym|id" -> {title_fa, paragraphs}
/* TradingView's own ideas page labels, kept in Persian: Popular is the site's
   default feed, Editors' picks is its badge filter, and timeframe/market tags
   come straight off each card. */
const IDEAS_SORTS=[['popular','🔥 محبوب‌ترین'],['recent','🕒 جدیدترین'],['followers','👥 پرطرفدارترین نویسنده']];
const IDEAS_KINDS=[['all','همه ایده‌ها'],['picked','⭐ منتخب سردبیر'],['education','📚 آموزشی'],['video','🎬 ویدیو']];
const TF_LABEL={'1':'1m','3':'3m','5':'5m','15':'15m','30':'30m','45':'45m','60':'1H','120':'2H','180':'3H','240':'4H','1D':'روزانه','1W':'هفتگی','1M':'1M','3M':'3M','6M':'6M','12M':'12M'};
function tfLabel(v){ v=String(v==null?'':v); return TF_LABEL[v]||v; }
function fmtCount(n){ n=+n||0; if(n>=1e6) return (n/1e6).toFixed(1).replace(/\.0$/,'')+'M';
  if(n>=1e3) return (n/1e3).toFixed(1).replace(/\.0$/,'')+'K'; return String(n); }
function ideasSym(){ return UI.ideasSym || orderedAssets()[0] || 'BTC'; }
function setIdeasAsset(sym){ if(UI.ideasSym===sym) return; UI.ideasSym=sym; loadIdeas(); }
/* the setters also sync their <select> — otherwise the toolbar chip (which
   reads the select's selected option for its label) would keep naming the old
   value after a programmatic change such as “clear all”. */
function setIdeasSort(v){
  UI.ideasSort=v;
  const el=document.getElementById('ideasSortChips'); if(el&&el.value!==v) el.value=v;
  renderIdeas();
}
function setIdeasKind(v){
  UI.ideasKind=v;
  const el=document.getElementById('ideasKindChips'); if(el&&el.value!==v) el.value=v;
  renderIdeas();
}
function setIdeasTf(v){
  UI.ideasTf=v;
  const el=document.getElementById('ideasTfChips'); if(el&&el.value!==v) el.value=v;
  renderIdeas();
}
function renderIdeasChips(){
  const box=document.getElementById('ideasChips'); if(!box||typeof DATA==='undefined'||!DATA) return;
  const cur=ideasSym();
  box.innerHTML=orderedAssets().map(s=>{
    const m=(DATA.assets_meta||{})[s]||{};
    const on=cur===s;
    return `<button class="chip ${on?'on':''}" aria-pressed="${on}" onclick="setIdeasAsset(${jsArg(s)})">${assetIc(s)} ${esc(faAssetName(s))}</button>`;
  }).join('');
  /* sort + kind are selects now — the option lists stay the same */
  const sc=document.getElementById('ideasSortChips');
  if(sc){
    const s=UI.ideasSort||'popular';
    sc.innerHTML=IDEAS_SORTS.map(([v,t])=>`<option value="${v}"${s===v?' selected':''}>${t}</option>`).join('');
  }
  const kc=document.getElementById('ideasKindChips');
  if(kc){
    const k=UI.ideasKind||'all';
    kc.innerHTML=IDEAS_KINDS.map(([v,t])=>`<option value="${v}"${k===v?' selected':''}>${t}</option>`).join('');
  }
}
/* the timeframe lane is built from the ideas actually loaded, like the market
   tags TradingView shows on its cards — hidden when everything is one frame */
function renderIdeasTfChips(){
  const bar=document.getElementById('ideasTfBar'), box=document.getElementById('ideasTfChips');
  if(!bar||!box) return;
  const cached=IDEAS_CACHE[ideasSym()];
  const tfs=[...new Set(((cached&&cached.items)||[]).map(x=>String(x.interval||'')).filter(Boolean))];
  let cur=UI.ideasTf||'all';
  /* a frame that this asset has no ideas for would filter the list to nothing
     while the select showed “همه” — drop the filter instead of lying */
  if(cur!=='all'&&!tfs.includes(cur)){ UI.ideasTf='all'; cur='all'; }
  if(!tfs.length){ bar.style.display='none'; return; }
  bar.style.display='';
  box.innerHTML=`<option value="all"${cur==='all'?' selected':''}>همه</option>`+
    tfs.map(t=>`<option value="${esc(t)}"${cur===t?' selected':''}>${esc(tfLabel(t))}</option>`).join('');
}
function ideasFiltered(){
  const cached=IDEAS_CACHE[ideasSym()];
  let list=((cached&&cached.items)||[]).slice();
  const kind=UI.ideasKind||'all';
  if(kind==='picked') list=list.filter(x=>x.picked);
  else if(kind==='education') list=list.filter(x=>x.education);
  else if(kind==='video') list=list.filter(x=>x.video);
  const tf=UI.ideasTf||'all';
  if(tf!=='all') list=list.filter(x=>String(x.interval||'')===String(tf));
  const s=UI.ideasSort||'popular';
  const pop=x=>(x.likes||0)*3+(x.comments||0)*2+Math.log10((x.followers||0)+1)*4+(x.picked?6:0)+(x.hot?4:0);
  if(s==='recent') list.sort((a,b)=>(b.ts||0)-(a.ts||0));
  else if(s==='followers') list.sort((a,b)=>((b.followers||0)-(a.followers||0))||((b.likes||0)-(a.likes||0))||((b.ts||0)-(a.ts||0)));
  else list.sort((a,b)=>(pop(b)-pop(a))||((b.ts||0)-(a.ts||0)));
  return list;
}
/* badge chips only — the timeframe now sits on the chart image itself */
function ideaBadges(x){
  const b=[];
  if(x.picked) b.push(`<span class="badge b-topic">${ic('star')} منتخب سردبیر</span>`);
  if(x.hot)    b.push(`<span class="badge b-topic">${ic('fire')} داغ</span>`);
  if(x.education) b.push(`<span class="badge b-topic">${ic('book')} آموزشی</span>`);
  if(x.video)  b.push(`<span class="badge b-topic">${ic('film')} ویدیو</span>`);
  return b.join(' ');
}
/* the card TradingView itself would render: chart image on top with the
   direction and timeframe over it, then the thesis, then the author and the
   permalink. The proxy ladder is unchanged (hotlink 403 → local proxy). */
function ideaCardHTML(x){
  const dir=x.symbol_dir||'';
  const dcls=dir==='Long'?'up':dir==='Short'?'dn':'';
  const dlabel=dir==='Long'?'▲ لانگ':dir==='Short'?'▼ شورت':(dir?(dir==='Neutral'?'خنثی':dir):'ایده بدون جهت');
  const link=attr(safeUrl(x.link||'https://www.tradingview.com/ideas/'));
  const open=`openIdeaModal(${jsArg(x.asset||ideasSym())},${jsArg(x.id)})`;
  const when=x.iso?faDateFromIso(String(x.iso).slice(0,10)):'';
  const snippet=x.snippet||'', body=x.body||'';
  const more=body.length>snippet.length+40?`<button class="idea-more-btn" onclick="${open}">${ic('book')} متن کامل + ترجمهٔ فارسی</button>`:'';
  const reach=(x.followers>0)?` · ${toFa(fmtCount(x.followers))} دنبال‌کننده`:'';
  const thumb=x.image
    ? `<button class="idea-thumb" onclick="${open}" tabindex="-1" aria-hidden="true">
         <img loading="lazy" decoding="async" alt="" src="${attr(safeUrl(x.image))}" referrerpolicy="no-referrer" data-orig="${attr(x.image)}" onerror="if(!this.dataset.tried){this.dataset.tried='1';this.src='/api/proxy-image?url='+encodeURIComponent(this.dataset.orig);}else{this.closest('.idea-thumb').classList.add('noimg')}">
         ${x.interval?`<span class="idea-tf">${esc(tfLabel(x.interval))}</span>`:''}
       </button>`
    : '';
  return `<article class="idea-card">
    ${thumb}
    <div class="idea-body">
      <div class="idea-top">
        <span class="dir ${dcls}">${dlabel}</span>
        ${x.symbol?`<span class="idea-sym ltr">${esc(x.symbol)}</span>`:''}
        ${(!x.image&&x.interval)?`<span class="badge b-kind ltr">${esc(tfLabel(x.interval))}</span>`:''}
        ${when?`<span class="idea-when">${esc(when)}</span>`:''}
      </div>
      <h4 class="idea-ttl"><a href="javascript:void(0)" onclick="${open}">${esc(x.title)}</a></h4>
      ${snippet?`<p class="idea-txt">${esc(snippet)}</p>`:''}
      ${ideaBadges(x)?`<div class="idea-badges">${ideaBadges(x)}</div>`:''}
      <div class="idea-foot">
        <span class="author">${ic('users')} ${esc(x.user||'—')}${x.user_pro?' '+ic('star'):''}${reach}</span>
        <span class="eng">${ic('heart')} ${toFa(x.likes||0)} · ${ic('comment')} ${toFa(x.comments||0)}${x.views?(' · '+ic('eye')+' '+toFa(fmtCount(x.views))):''}</span>
      </div>
      <div class="idea-cta">
        ${more}
        <a class="idea-link" href="${link}" target="_blank" rel="noopener">تریدینگ‌ویو ${ic('external')}</a>
      </div>
    </div>
  </article>`;
}
function renderIdeas(){
  const grid=document.getElementById('ideasGrid'); if(!grid) return;
  const sym=ideasSym(), cached=IDEAS_CACHE[sym];
  const summary=document.getElementById('ideasSummary');
  const allLink=document.getElementById('ideasAllLink');
  if(cached&&cached.url&&allLink) allLink.href=cached.url;
  renderIdeasTfChips();
  if(typeof renderIdeasToolbar==='function') renderIdeasToolbar();   /* FILTER MODEL 3 toolbar */
  if(!cached){
    grid.innerHTML=`<div class="empty"><span class="spinner"></span> در حال دریافت ایده‌های ${esc(sym)}…</div>`;
    if(summary) summary.textContent='در حال خواندن…';
    return;
  }
  if(cached.err==='not_available'){
    grid.innerHTML='<div class="empty">این بخش در این نسخه فعال نیست — ایده‌های تریدینگ‌ویو فقط در داشبورد اصلی خوانده می‌شوند.</div>';
    if(summary) summary.textContent='—';
    return;
  }
  if(!cached.items.length){
    grid.innerHTML='<div class="empty">برای این دارایی ایده‌ای پیدا نشد — یک دارایی دیگر را انتخاب کنید یا آخرین ایده‌ها را در تریدینگ‌ویو ببینید.</div>';
    if(summary) summary.textContent=toFa(0)+' ایده';
    return;
  }
  const list=ideasFiltered();
  if(!list.length){
    grid.innerHTML='<div class="empty">با این فیلتر ایده‌ای نیست — «نوع ایده» یا تایم‌فریم را به «همه» برگردان.</div>';
  } else {
    grid.innerHTML=list.map(ideaCardHTML).join('');
  }
  const longs=list.filter(x=>x.symbol_dir==='Long').length;
  const shorts=list.filter(x=>x.symbol_dir==='Short').length;
  if(summary) summary.textContent=`${toFa(list.length)} از ${toFa(cached.items.length)} ایدهٔ ${esc(sym)} · ${toFa(longs)} لانگ · ${toFa(shorts)} شورت`;
}
async function loadIdeas(force){
  const sym=ideasSym();
  renderIdeasChips();
  const cached=IDEAS_CACHE[sym];
  if(cached&&!force&&Date.now()-cached.ts<IDEAS_TTL){ renderIdeas(); return; }
  renderIdeas();
  const seq=++IDEAS_SEQ;
  try{
    const d=await (await fetch('/api/ideas?sym='+encodeURIComponent(sym)+'&limit=30')).json();
    if(seq!==IDEAS_SEQ) return;                      /* a newer chip won the race */
    IDEAS_CACHE[sym]={items:(d&&d.items)||[], url:(d&&d.url)||'', ts:Date.now(),
                      err:(d&&d.ok===false)?(d.error||'error'):null};
  }catch(e){
    if(seq!==IDEAS_SEQ) return;
    IDEAS_CACHE[sym]={items:[], url:'', ts:Date.now(), err:'network'};
  }
  if(UI.view==='ideas') renderIdeas();
}
/* ── idea modal: chart + full text + Persian translation (like a news item) ── */
function findIdea(sym,id){
  const c=IDEAS_CACHE[sym];
  return c?((c.items||[]).find(x=>String(x.id)===String(id))||null):null;
}
function openIdeaModal(sym,id){
  const x=findIdea(sym,id); if(!x) return;
  const ov=document.getElementById('ideaOverlay'); if(!ov) return;
  ov.classList.add('open');
  renderIdeaModal(sym,x,false);
}
function renderIdeaModal(sym,x,faMode){
  const b=document.getElementById('ideaBody'); if(!b||!x) return;
  const fa=IDEA_FA[sym+'|'+x.id];
  const dir=x.symbol_dir||'';
  const dcls=dir==='Long'?'up':dir==='Short'?'dn':'';
  const dlabel=dir==='Long'?'▲ لانگ':dir==='Short'?'▼ شورت':(dir?(dir==='Neutral'?'خنثی':dir):'ایده بدون جهت');
  const raw=(x.body||x.snippet||'').split(/\n{2,}/).map(p=>p.trim()).filter(Boolean);
  const bodyHtml = (faMode&&fa&&fa.paragraphs&&fa.paragraphs.length)
    ? fa.paragraphs.map(p=>`<p class="fa">${esc(p)}</p>`).join('')
    : (raw.length?raw.map(p=>`<p class="en">${esc(p)}</p>`).join('')
       : '<p style="color:var(--ink-3)">متن کامل این ایده در صفحهٔ تریدینگ‌ویو است.</p>');
  const titleShown=(faMode&&fa&&fa.title_fa)?fa.title_fa:x.title;
  const faBtn = faMode
    ? `<button class="btn ghost sm" onclick="renderIdeaModal(${jsArg(sym)},findIdea(${jsArg(sym)},${jsArg(x.id)}),false)">↩️ نمایش متن اصلی</button>`
    : (fa?`<button class="btn sm" onclick="renderIdeaModal(${jsArg(sym)},findIdea(${jsArg(sym)},${jsArg(x.id)}),true)">🇮🇷 نمایش ترجمهٔ فارسی</button>`
       : `<button class="btn sm" id="ideaFaBtn" onclick="ideaToFa(${jsArg(sym)},${jsArg(x.id)})">🇮🇷 ترجمهٔ فارسی متن کامل</button>`);
  b.innerHTML=`
    <div class="row1" style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
      <span class="dir ${dcls}" style="font-weight:800">${dlabel}</span>${ideaBadges(x)}
    </div>
    <h2>${esc(titleShown||'')}</h2>
    ${(faMode&&fa&&fa.title_fa)?`<div class="h2en">${esc(x.title)}</div>`:''}
    <div class="mmeta">
      <span>✍️ ${esc(x.user||'—')}</span>
      ${(x.followers>0)?`<span>👥 ${toFa(fmtCount(x.followers))} دنبال‌کننده</span>`:''}
      ${x.symbol?`<span class="ltr">${esc(x.symbol)}</span>`:''}
      ${x.iso?`<span>🗓 ${esc(faDateFromIso(String(x.iso).slice(0,10)))}</span>`:''}
      <span class="ltr">❤ ${toFa(x.likes||0)} · 💬 ${toFa(x.comments||0)}</span>
    </div>
    ${x.image?`<a href="${attr(safeUrl(x.link))}" target="_blank" rel="noopener" style="display:block;margin:10px 0 4px"><img class="idea-big" src="${attr(safeUrl(x.image))}" referrerpolicy="no-referrer" alt="" onerror="this.style.display='none'"></a>`:''}
    <div class="msec">
      <h4>${faMode?'📝 ترجمهٔ فارسی متن ایده':'📝 متن کامل ایده'}</h4>
      ${bodyHtml}
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:14px">
        ${faBtn}
        <a class="mlink" href="${attr(safeUrl(x.link))}" target="_blank" rel="noopener">🔗 مشاهده در تریدینگ‌ویو</a>
      </div>
    </div>`;
}
async function ideaToFa(sym,id){
  const key=sym+'|'+id;
  const x=findIdea(sym,id);
  if(IDEA_FA[key]){ renderIdeaModal(sym,x,true); return; }
  const btn=document.getElementById('ideaFaBtn');
  const setTxt=t=>{ if(btn) btn.innerHTML=t; };
  setTxt('<span class="spinner"></span> در حال ترجمه…');
  let tries=0;
  const poll=async()=>{
    let d;
    try{ d=await (await fetch('/api/ideas/translate?sym='+encodeURIComponent(sym)+'&id='+encodeURIComponent(id))).json(); }
    catch(e){ setTxt('⚠️ خطا در ترجمه — دوباره بزن'); return; }
    if(d.ok&&d.pending&&tries++<25){
      setTxt('<span class="spinner"></span> در حال ترجمه… ('+toFa(tries)+')');
      setTimeout(poll,1500); return;
    }
    if(d.ok&&!d.pending){
      IDEA_FA[key]={title_fa:d.title_fa||'', paragraphs:d.paragraphs||[]};
      renderIdeaModal(sym,findIdea(sym,id),true); return;
    }
    setTxt('⚠️ ترجمه در دسترس نیست');
  };
  poll();
}
/* ── live ETF rate board: every quoted fund, boxed per family ───────────── */
const ETF_GROUP_FA={Bitcoin:'بیت‌کوین', 'BTC futures':'فیوچرز بیت‌کوین', Leveraged:'اهرمی و معکوس',
  Ethereum:'اتریوم', Solana:'سولانا', XRP:'ریپل (XRP)', 'Crypto blends':'ترکیبی کریپتو',
  'Crypto equity':'سهام کریپتو', Commodities:'کالاها', Markets:'بازارها', Other:'سایر'};
const ETF_GROUP_ORDER=['Bitcoin','BTC futures','Leveraged','Ethereum','Solana','XRP','Crypto blends','Crypto equity','Commodities','Markets','Other'];
function setEtfGroup(g){
  UI.etfGroup=g;
  if(typeof renderEtfToolbar==='function') renderEtfToolbar();
  if(typeof tbClose==='function') tbClose('etfSheet');
  renderEtfLive('etfLive2');
}
function etfCardHTML(s,x){
  const ch=(x&&x.change_pct!=null)?x.change_pct:null;
  const cls=ch==null?'':(ch>=0?'up':'dn');
  const st=(x&&x.market_state)||'';
  const open=!!st&&!['CLOSED','PRE','PREPRE','POST','POSTPOST'].includes(st);
  return `<div class="etfcard">
    <div class="etfcard-top"><span class="tk">${esc(s)}</span><span class="ms ${open?'live':''}">${st?(open?'باز':'بسته'):'—'}</span></div>
    <div class="nm" title="${esc((x&&x.name)||s)}">${esc((x&&x.name)||s)}</div>
    <div class="prc">${(x&&x.price!=null)?'$'+num(x.price,2):'—'}</div>
    <div class="chg ${cls}">${ch==null?'—':((ch>=0?'▲ +':'▼ ')+num(ch,2)+'%')}</div>
  </div>`;
}
function renderEtfGroupChips(){
  const box=document.getElementById('etfGroupChips'); if(!box) return;
  const q=window.__ETFQ||{};
  const counts={};
  Object.keys(q).forEach(s=>{ const g=(q[s]&&q[s].group)||'Other'; counts[g]=(counts[g]||0)+1; });
  const cur=UI.etfGroup||'all';
  if(typeof renderEtfToolbar==='function') renderEtfToolbar();
  let h=`<button class="chip ${cur==='all'?'on':''}" onclick="setEtfGroup('all')">همه <span class="n">${toFa(Object.keys(q).length)}</span></button>`;
  ETF_GROUP_ORDER.filter(g=>counts[g]).forEach(g=>{
    h+=`<button class="chip ${cur===g?'on':''}" onclick="setEtfGroup(${jsArg(g)})">${ETF_GROUP_FA[g]||g} <span class="n">${toFa(counts[g])}</span></button>`;
  });
  box.innerHTML=h;
}
function renderEtfLive(targetId){
  const box=document.getElementById(targetId||'etfLive2'); if(!box) return;
  const q=window.__ETFQ||{};
  const all=Object.keys(q);
  const sum=document.getElementById('etfSummary');
  renderEtfGroupChips();
  if(!all.length){
    box.innerHTML='<div class="empty">نرخ زندهٔ صندوق‌ها هم‌اکنون در دسترس نیست — تلاش بعدی یک دقیقهٔ دیگر.</div>';
    if(sum) sum.textContent='—';
    return;
  }
  const grp=UI.etfGroup||'all';
  const needle=(UI.etfQ||'').trim().toLowerCase();
  const syms=all.filter(s=>{
    if(grp!=='all'&&((q[s]&&q[s].group)||'Other')!==grp) return false;
    if(!needle) return true;
    return s.toLowerCase().includes(needle)||String((q[s]&&q[s].name)||'').toLowerCase().includes(needle);
  });
  if(!syms.length){
    box.innerHTML='<div class="empty">صندوقی با این فیلتر پیدا نشد.</div>';
    if(sum) sum.textContent=`۰ از ${toFa(all.length)} صندوق`;
    return;
  }
  const groups={};
  syms.slice().sort().forEach(s=>{ const g=(q[s]&&q[s].group)||'Other'; (groups[g]=groups[g]||[]).push(s); });
  /* known groups in a fixed order, then anything the API adds later — a new
     family must never silently drop out of the board */
  const order=ETF_GROUP_ORDER.filter(g=>groups[g])
    .concat(Object.keys(groups).filter(g=>!ETF_GROUP_ORDER.includes(g)).sort());
  box.innerHTML=order.map(g=>
    `<section class="etfgroup"><h4 class="etfgroup-t">${ETF_GROUP_FA[g]||g}<span class="n">${toFa(groups[g].length)} صندوق</span></h4>`+
    `<div class="etfgrid">${groups[g].map(s=>etfCardHTML(s,q[s])).join('')}</div></section>`).join('');
  if(sum){
    const ups=syms.filter(s=>((q[s]||{}).change_pct||0)>=0).length;
    sum.textContent=`${toFa(syms.length)}${(grp==='all'&&!needle)?'':' از '+toFa(all.length)} صندوق · ${toFa(ups)} مثبت · ${toFa(syms.length-ups)} منفی`;
  }
}
async function pollEtf(){
  try{ const d=await (await fetch('/api/etf')).json();
    if(d.ok&&d.quotes&&Object.keys(d.quotes).length){ window.__ETFQ=d.quotes; renderEtfLive('etfLive2'); }
  }catch(e){}
}
pollEtf(); Clock.every(60000, pollEtf, {label:'etf-poll'});
/* ── DL2 step 1: "new since last visit" + page-load skeleton ──────────────
   The baseline is frozen at boot so the markers do not blink out when the
   60s poll re-renders the feed; localStorage is updated for the next visit. */
const DL2_SEEN_KEY='dl2_last_seen';
let DL2_BASELINE=0;
function dl2LastSeen(){ try{ return +(localStorage.getItem(DL2_SEEN_KEY)||0); }catch(e){ return 0; } }
function dl2MarkSeen(){ try{ localStorage.setItem(DL2_SEEN_KEY, String(Math.floor(Date.now()/1000))); }catch(e){} }
function tsOf(a){ const t=(a&&a.published_ts)||0; return t>1e12?Math.floor(t/1000):t; }
function isNew(a){ return DL2_BASELINE>0 && tsOf(a)>DL2_BASELINE; }
function dl2Skeleton(n){
  const g=document.getElementById('newsGrid');
  if(!g||(typeof DATA!=='undefined'&&DATA)) return;
  const sk=[]; for(let i=0;i<(n||6);i++) sk.push({__sk:i});
  if(vsGrid('feed','newsGrid',VS_OPTS_FEED, sk, null)) return;
  let h=''; for(let i=0;i<(n||6);i++) h+='<div class="skcard skeleton"></div>';
  g.innerHTML=h;
}
function dl2AfterFeed(){
  if(typeof DATA==='undefined'||!DATA) return;
  const host=document.getElementById('feedCount');
  if(!host||!host.parentNode) return;
  const n=(DATA.articles||[]).filter(isNew).length;
  let b=document.getElementById('feedNewBadge');
  if(!b){
    b=document.createElement('span'); b.id='feedNewBadge';
    host.parentNode.insertBefore(b, host.nextSibling);
  }
  b.innerHTML = n ? '<span class="newdot"></span>'+toFa(n)+' تازه' : '';
}
DL2_BASELINE=dl2LastSeen();

/* ── DL2 step 2: accessibility — modal focus trap + keyboard nav for the rail
   Small, self-contained, and additive: it only listens, it never rewrites the
   DOM the rest of the app builds. */
(function(){
  try{
    let lastFocus=null;
    function visibleOverlay(){
      return document.querySelector('.overlay.open');
    }
    function focusables(root){
      return [...root.querySelectorAll(
        'a[href],button:not([disabled]),input:not([disabled]),select,textarea,'+
        '[tabindex]:not([tabindex="-1"])')].filter(el=>el.offsetParent!==null||el===document.activeElement);
    }
    document.addEventListener('keydown',function(e){
      const ov=visibleOverlay();
      if(!ov) return;
      if(e.key==='Escape'){ e.preventDefault(); ov.classList.remove('open');
        if(lastFocus&&lastFocus.focus) lastFocus.focus(); lastFocus=null; return; }
      if(e.key==='Tab'){
        const f=focusables(ov);
        if(!f.length){ e.preventDefault(); return; }
        const first=f[0], last=f[f.length-1];
        if(e.shiftKey&&document.activeElement===first){ e.preventDefault(); last.focus(); }
        else if(!e.shiftKey&&document.activeElement===last){ e.preventDefault(); first.focus(); }
      }
    },true);
    /* remember what had focus before a modal opened, so Esc returns the user there */
    document.addEventListener('click',function(e){
      const opener=e.target&&e.target.closest?e.target.closest('.ncard,.lead-card,[data-modal-opener]'):null;
      if(opener) lastFocus=opener;
    },true);
    /* modal role/aria for screen readers */
    document.querySelectorAll('.overlay').forEach(function(ov){
      ov.setAttribute('role','dialog'); ov.setAttribute('aria-modal','true');
    });
    /* roving focus + Arrow/Home/End inside the tab rail */
    const rail=document.getElementById('appSidebar');
    if(rail){
      rail.addEventListener('keydown',function(e){
        const items=[...rail.querySelectorAll('.nav-item')];
        const i=items.indexOf(document.activeElement);
        if(i<0) return;
        let j=null;
        if(e.key==='ArrowDown'||e.key==='ArrowLeft') j=Math.min(items.length-1,i+1);
        else if(e.key==='ArrowUp'||e.key==='ArrowRight') j=Math.max(0,i-1);
        else if(e.key==='Home') j=0;
        else if(e.key==='End') j=items.length-1;
        if(j===null) return;
        e.preventDefault();
        items.forEach((el,k)=>el.setAttribute('tabindex',k===j?'0':'-1'));
        items[j].focus();
      });
    }
  }catch(e){ /* progressive enhancement only — never break the dashboard */ }
})();

/* ── Fear & Greed — one per-asset gauge under the report chart ────────────
   The standalone tab was removed on request; each asset report now carries its
   own reading (scored from that asset's last-24 h headlines) right under the
   chart, with the global alternative.me index kept as a reference line. */
const FNG_LABELS={'Extreme Fear':'ترس شدید','Fear':'ترس','Neutral':'خنثی','Greed':'طمع','Extreme Greed':'طمع شدید'};
function fngColor(v){ /* concrete hex: SVG presentation attributes cannot use var() */
    return v>=75?'#EE6A58':v>=55?'#8FB4E8':v>=45?'#8A93A6':'#2EBD77'; }
function fngFaLabel(label){ return (window.__ECON_FA&&window.__ECON_FA[label])||FNG_LABELS[label]||label||''; }
function fngGauge(v,label){
  /* 0=fear(green) … 100=greed(red) — 270° arc like the old dial */
  const col=fngColor(v);
  const dash=`<circle cx="30" cy="30" r="25" fill="none" stroke="${col}" stroke-width="7"
    stroke-dasharray="${(169.6*v/100).toFixed(1)} 169.6" transform="rotate(135 30 30)" stroke-linecap="round"/>`;
  return [dash,col,fngFaLabel(label)];
}
function paintFng(){ refreshRepFngGlobal(); }
function refreshRepFngGlobal(){
  const el=document.getElementById('repFngGlobal'); if(!el) return;
  const g=window.__FNG||{};
  el.innerHTML = g.now==null ? 'شاخص کل بازار کریپتو موقتاً در دسترس نیست.'
    : `🌐 شاخص کل بازار کریپتو: <b style="color:${fngColor(g.now)}">${toFa(g.now)}</b> · ${esc(fngFaLabel(g.label))}`;
}
function loadRepFng(sym){
  const host=document.getElementById('repFng'); if(!host) return;
  const meta=(typeof DATA!=='undefined'&&DATA&&DATA.assets_meta&&DATA.assets_meta[sym])||{};
  host.innerHTML=`<h3>😱 شاخص ترس و طمع — ${esc(meta.fa||sym)} <span class="ltr" style="font-size:11px;color:var(--ink-4)">${esc(sym)}</span></h3>
    <div class="rf-row"><span class="spinner"></span><span style="font-size:12px;color:var(--ink-4)">در حال محاسبه از خبرهای ۲۴ ساعت گذشته…</span></div>`;
  fetch('/api/fng/'+encodeURIComponent(sym)).then(r=>r.json()).then(d=>{
    const h=document.getElementById('repFng'); if(!h) return;
    if(!d||!d.ok){ h.insertAdjacentHTML('beforeend','<div class="empty">داده ترس و طمع این دارایی در دسترس نیست.</div>'); return; }
    renderRepFng(sym,d);
  }).catch(()=>{});
}
function renderRepFng(sym,d){
  const host=document.getElementById('repFng'); if(!host) return;
  const meta=(typeof DATA!=='undefined'&&DATA&&DATA.assets_meta&&DATA.assets_meta[sym])||{};
  const v=(d.now==null?50:d.now), cls=fngColor(v), lab=fngFaLabel(d.label);
  const gauge=fngGauge(v,d.label)[0];
  host.innerHTML=`<h3>😱 شاخص ترس و طمع — ${esc(meta.fa||sym)} <span class="ltr" style="font-size:11px;color:var(--ink-4)">${esc(sym)}</span></h3>
    <div class="rf-row">
      <svg viewBox="0 0 60 60" role="img" aria-label="Fear and Greed ${v}" style="inline-size:88px;block-size:88px;flex:0 0 auto">
        <circle cx="30" cy="30" r="25" fill="none" stroke="var(--rule-2)" stroke-width="7"/>${gauge}</svg>
      <div style="flex:1 1 auto;min-inline-size:0">
        <div class="rf-score" style="color:${cls}">${toFa(v)}<span> / ۱۰۰</span></div>
        <div class="rf-lab" style="color:${cls}">${esc(lab)}</div>
        <div class="rf-bar" role="progressbar" aria-valuenow="${v}" aria-valuemin="0" aria-valuemax="100"><i style="inline-size:${v}%;background:${cls}"></i></div>
        <div class="rf-src">ساخته‌شده از <b>${toFa(d.count||0)}</b> خبر ${esc(meta.fa||sym)} در ۲۴ ساعت گذشته — <b style="color:var(--up)">${toFa(d.pos||0)} صعودی</b> · <b style="color:var(--dn)">${toFa(d.neg||0)} نزولی</b> · باقی بی‌طرف.</div>
      </div>
    </div>
    <div class="rf-scale"><span>۰ ترس شدید</span><span>۵۰ خنثی</span><span>۱۰۰ طمع شدید</span></div>
    <div class="rf-glob" id="repFngGlobal"></div>`;
  refreshRepFngGlobal();
}

/* ── short Persian explainer per news (بند کوتاه درباره خبر) ── */
async function openBlurb(id){
  const ov=document.getElementById('blurbOverlay'); ov.classList.add('open');
  const b=document.getElementById('blurbBody');
  b.innerHTML='<div class="spinner"></div>';
  try{
    const d=await (await fetch('/api/article/'+id)).json();
    b.innerHTML=`
      <h2 style="font-size:15.5px;line-height:1.9">${esc(d.title_fa||d.title)}</h2>
      ${d.title_fa?`<div class="h2en">${esc(d.title)}</div>`:''}
      <div class="mmeta">
        <span>📰 ${esc(d.source)}</span>
        <span>🗓 ${esc(d.datetime_fa||'')}</span>
        ${credBadge(d.credibility)}
      </div>
      <div class="msec" style="border-inline-start:3px solid var(--cu)">
        <h4 style="margin-bottom:6px">💡 این خبر چیست؟</h4>
        <p style="font-size:13.5px;line-height:2.15;margin:0">${esc(d.blurb_fa||'توضیحی برای این خبر ساخته نشد — خلاصه را در مودال اصلی ببینید.')}</p>
      </div>
      <button class="btn sm" style="margin-top:4px" onclick="closeModal('blurbOverlay');openArticle(${jsArg(id)})">📄 متن کامل خبر</button>`;
  }catch(e){ b.innerHTML='<div class="empty">خطا در دریافت توضیحات</div>'; }
}

/* ═══════════ telegram digest settings ═══════════ */
const TG_TPL_DEFAULT='<b>{title}</b>\n\n{summary_blocks}{key_point}{link_line}';
function tgPayload(){
  return {telegram:{
    token: document.getElementById('tgToken').value.trim(),
    chat: document.getElementById('tgChat').value.trim(),
    gateway: document.getElementById('tgGateway') ? document.getElementById('tgGateway').value.trim() : '',
    proxy: document.getElementById('tgProxy') ? document.getElementById('tgProxy').value.trim() : '',
    enabled: document.getElementById('tgEnabled').checked,
    min_credibility: parseFloat(document.getElementById('tgMinCred').value)||0.75,
    max_items: parseInt(document.getElementById('tgMaxItems').value)||10,
    max_age_hours: parseFloat(document.getElementById('tgMaxAge').value)||6,
    asset_filter: document.getElementById('tgAssets').value.split(',').map(x=>x.trim().toUpperCase()).filter(Boolean),
    quiet_hours: document.getElementById('tgQuiet').checked,
    send_ideas: document.getElementById('tgIdeas') ? document.getElementById('tgIdeas').checked : true,
    send_digest: document.getElementById('tgDigest') ? document.getElementById('tgDigest').checked : false,
    include_link: document.getElementById('tgLink').checked,
    link_on_own_line: document.getElementById('tgLinkLine').checked,
    include_summary: document.getElementById('tgSummary').checked,
    hashtags: document.getElementById('tgHashtags').checked,
    emoji: document.getElementById('tgEmoji').checked,
    show_stars: document.getElementById('tgStars').checked,
    silent: document.getElementById('tgSilent').checked,
    pin: document.getElementById('tgPin').checked,
    language: document.getElementById('tgLang').value,
    template: document.getElementById('tgTemplate').value.trim()
  }};
}
/* ═══════════ smart alert rules — condition engine + dispatch ═══════════
   A rule is `[when…] logic → [actions]`. Conditions read three independent
   sources (live prices, calendar releases, the news feed); evaluation is pure
   (`arRuleEval(rule, ctx)`), so it is testable, and the tick that calls it is
   deferred so it never sits in the render path of a poll or a news cycle. */
const AR_KEY='mohmd_alert_rules_v1';
const AR_LOG_MAX=60;
const AR={rules:[], log:[], edit:null, pending:null, rt:{}, ctx:null, lastRun:0};
const AR_OPS={gt:'بزرگ‌تر از', gte:'بزرگ‌تر یا مساوی', lt:'کوچک‌تر از', lte:'کوچک‌تر یا مساوی', eq:'برابر با', contains:'شامل'};
const AR_OP_SYM={gt:'>', gte:'≥', lt:'<', lte:'≤', eq:'=', contains:'⊃'};
const AR_KINDS={price:'قیمت لحظه‌ای', change:'تغییر ۲۴ ساعته', event:'رویداد تقویم اقتصادی', news:'تیتر خبر'};
const AR_IMPACTS={all:'همهٔ سطوح', High:'فقط High', Medium:'فقط Medium'};
const AR_TPL_DEFAULT='🚨 <b>{name}</b>\n{body}\n🕒 {time}';
function arOp(a, op, b){
  if(op==='contains') return String(a==null?'':a).toLowerCase().indexOf(String(b==null?'':b).toLowerCase())>=0;
  const v=Number(a), w=Number(b);
  if(a==null||b===''||b==null||isNaN(v)||isNaN(w)) return false;
  if(op==='gt') return v>w;
  if(op==='gte') return v>=w;
  if(op==='lt') return v<w;
  if(op==='lte') return v<=w;
  if(op==='eq') return Math.abs(v-w)<=Math.abs(w||1)*1e-9;
  return false;
}
function arFmtVal(h){
  if(!h) return '';
  if(h.art) return String(h.art.title_fa||h.art.title||'');
  if(h.ev) return String(h.ev.title||'')+' '+(h.ev.actual_fmt||'');
  const v=Number(h.value);
  if(h.unit==='change') return toFa(v.toFixed(2))+'٪';
  if(isNaN(v)) return String(h.value);
  return toFa(Math.abs(v)>=1000?v.toFixed(0):(Math.abs(v)<1?v.toFixed(4):v.toFixed(2)));
}
function arCondText(c){
  if(!c||!AR_KINDS[c.kind]) return '—';
  if(c.kind==='price'||c.kind==='change'){
    const unit=c.kind==='change'?'٪':' ';
    return (c.kind==='price'?'قیمت ':'تغییر ۲۴ساعتهٔ ')+String(c.sym||'')+' '+(AR_OP_SYM[c.op]||'?')
      +(c.op==='contains'?' "'+String(c.value==null?'':c.value)+'"':' '+toFa(String(c.value==null?'':c.value))+unit);
  }
  if(c.kind==='event') return 'رویداد اقتصادی منتشر شده ('+(AR_IMPACTS[c.impact||'all']||'')+')';
  const terms=(c.terms||[]).filter(Boolean);
  return 'تیتر شامل '+(terms.length?'«'+terms.join('» یا «')+'»':'هر خبر')
    +(Number(c.minCred||0)>0?' با اعتبار ≥ '+toFa(Math.round(Number(c.minCred)*100))+'٪':'')
    +(Number(c.within||0)>0?' در '+toFa(Number(c.within))+' دقیقهٔ اخیر':'');
}
/* one condition against one snapshot; `false` = no, `null` = no data to say,
   an object = matched (and it carries what to print in the notification) */
function arCondOk(c, ctx){
  if(!c) return false;
  if(c.kind==='price'||c.kind==='change'){
    const p=((ctx&&ctx.prices)||{})[c.sym];
    const v=p?(c.kind==='price'?p.price:p.change_24h):null;
    if(v==null) return null;
    if(!arOp(v, c.op, c.value)) return false;
    return {sym:c.sym, value:v, unit:c.kind==='change'?'change':'price',
            label:(c.kind==='price'?'قیمت '+c.sym:'تغییر ۲۴ساعتهٔ '+c.sym)};
  }
  if(c.kind==='event'){
    const ev=((ctx&&ctx.events)||[]).filter(function(e){
      if(c.impact&&c.impact!=='all'&&e.impact!==c.impact) return false;
      return e.past && (e.actual_n!=null || e.actual);
    })[0];
    if(!ev) return false;
    return {sym:null, value:ev.actual_fmt||'', ev:ev, label:'رویداد '+String(ev.title||'')};
  }
  if(c.kind==='news'){
    const terms=(c.terms||[]).map(function(t){ return String(t||'').trim().toLowerCase(); }).filter(Boolean);
    const minCred=Number(c.minCred||0), within=Number(c.within||0)*60;
    const hit=((ctx&&ctx.news)||[]).filter(function(a){
      if((a.credibility||0)<minCred) return false;
      if(within && (ctx.now-(a.published_ts||0))>within) return false;
      if(!terms.length) return true;
      const t=((a.title||'')+' '+(a.title_fa||'')+' '+(a.summary||'')+' '+(a.summary_fa||'')).toLowerCase();
      return terms.some(function(x){ return t.indexOf(x)>=0; });
    })[0];
    if(!hit) return false;
    return {sym:(hit.assets||[])[0]||null, value:hit.title_fa||hit.title||'', art:hit, label:'خبر'+(hit.assets&&hit.assets.length?' '+hit.assets.join('/'):'')};
  }
  return false;
}
function arRuleEval(rule, ctx){
  const conds=((rule&&rule.when)||[]).filter(function(c){ return c&&AR_KINDS[c.kind]; });
  if(!conds.length) return {ok:false, hits:[], misses:[]};
  const hits=[], misses=[];
  conds.forEach(function(c){
    const r=arCondOk(c, ctx);
    if(r&&r!==true) hits.push(r); else misses.push(c);
  });
  return {ok:(rule.logic==='or')?hits.length>0:hits.length===conds.length, hits:hits, misses:misses};
}
function arValidate(rule, silent){
  const bad=function(msg){ if(!silent && typeof arHint==='function') arHint(msg, true); return msg; };
  if(!String(rule.name||'').trim()) return bad('نام قانون را بنویس');
  const conds=(rule.when||[]).filter(function(c){ return c&&AR_KINDS[c.kind]; });
  if(!conds.length) return bad('حداقل یک شرط لازم است');
  for(const c of conds){
    if((c.kind==='price'||c.kind==='change') && !c.sym) return bad('دارایی شرط قیمت انتخاب نشده');
    if(c.kind==='news' && !(c.terms||[]).filter(Boolean).length && !Number(c.minCred||0))
      return bad('برای شرط خبر حداقل یک کلیدواژه یا حد اعتبار لازم است');
  }
  const acts=rule.actions||{};
  if(!acts.toast && !acts.tone && !acts.tg && !acts.push) return bad('حداقل یک اقدام انتخاب کن');
  if(acts.tg && !rule.template) rule.template=AR_TPL_DEFAULT;
  if(!silent && typeof arHint==='function') arHint('');
  return '';
}
/* ── persistence (per browser, like the bookmarks) ─────────────────────── */
function arLoad(){
  try{
    const d=JSON.parse(localStorage.getItem(AR_KEY)||'{}');
    AR.rules=Array.isArray(d.rules)?d.rules:[];
    AR.log=Array.isArray(d.log)?d.log:[];
  }catch(e){ AR.rules=[]; AR.log=[]; }
  AR.rules.forEach(function(r){ if(r.enabled===undefined) r.enabled=true; });
}
function arStore(){
  try{ localStorage.setItem(AR_KEY, JSON.stringify({rules:AR.rules, log:AR.log.slice(0,AR_LOG_MAX), v:1})); }catch(e){}
}
function arNewId(){ return 'ar_'+Date.now().toString(36)+Math.random().toString(36).slice(2,6); }
/* ── actions: sticky toast, squawk tone, telegram webhook ─────────────── */
function arNotify(title, body, level){
  const box=document.getElementById('alertStack');
  if(!box) return null;
  const el=document.createElement('div');
  el.className='alert-card'+(level==='warn'?' is-warn':'');
  el.setAttribute('role','alert');
  el.innerHTML='<div class="al-hd"><span class="al-ic">'+ic(level==='warn'?'warn':'bell')+'</span>'
    +'<b>'+esc(title)+'</b>'
    +'<button type="button" class="al-x" aria-label="بستن هشدار">'+ic('x')+'</button></div>'
    +'<div class="al-bd">'+esc(body||'')+'</div>'
    +'<div class="al-ft"><span>'+esc(tzClock(Math.floor(Date.now()/1000)))+' '+esc(calTz())+'</span><span class="al-tag">هشدار هوشمند</span></div>';
  el.querySelector('.al-x').onclick=function(){ arDismiss(el); };
  box.insertBefore(el, box.firstChild);
  /* keep the newest five only, so a chatty rule cannot bury the dashboard */
  while(box.children.length>5) box.removeChild(box.lastChild);
  return el;
}
function arDismiss(el){
  if(!el) return;
  el.classList.add('is-out');
  setTimeout(function(){ if(el.parentNode) el.parentNode.removeChild(el); }, 160);
}
function arSquawk(){
  try{
    const AC=window.AudioContext||window.webkitAudioContext;
    if(!AC) return;
    if(!AR.ac) AR.ac=new AC();
    const ac=AR.ac;
    if(ac.state==='suspended'&&ac.resume) ac.resume();
    const t0=ac.currentTime;
    [[880,0],[1174.7,0.17]].forEach(function(p){
      const o=ac.createOscillator(), g=ac.createGain();
      o.type='square'; o.frequency.value=p[0];
      g.gain.setValueAtTime(0.0001, t0+p[1]);
      g.gain.exponentialRampToValueAtTime(0.08, t0+p[1]+0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, t0+p[1]+0.15);
      o.connect(g); g.connect(ac.destination);
      o.start(t0+p[1]); o.stop(t0+p[1]+0.17);
    });
  }catch(e){ /* audio is a nicety — a blocked context must never break a rule */ }
}
/* browsers only allow audio after a real gesture, so arm it on the first one */
function arArmTone(){
  if(AR.armed||!AR.rules.length) return;
  AR.armed=1;
  const unlock=function(){
    try{
      const AC=window.AudioContext||window.webkitAudioContext;
      if(AC){ if(!AR.ac) AR.ac=new AC(); if(AR.ac.state==='suspended'&&AR.ac.resume) AR.ac.resume(); }
    }catch(e){}
    document.removeEventListener('click', unlock);
    document.removeEventListener('keydown', unlock);
  };
  document.addEventListener('click', unlock);
  document.addEventListener('keydown', unlock);
}
function arRenderTpl(rule, res){
  const body=res.hits.map(function(h){ return '• '+h.label+(h.art?'':' — '+arFmtVal(h)); }).join('\n');
  const now=Math.floor(Date.now()/1000);
  const first=res.hits[0]||{};
  return String(rule.template||AR_TPL_DEFAULT)
    .replace(/\{name\}/g, esc(rule.name||''))
    .replace(/\{body\}/g, esc(body))
    .replace(/\{time\}/g, esc(tzClock(now)+' '+calTz()))
    .replace(/\{sym\}/g, esc(first.sym||''))
    .replace(/\{value\}/g, esc(arFmtVal(first)))
    .replace(/\{logic\}/g, rule.logic==='or'?'OR':'AND');
}
async function arSendTelegram(rule, res){
  try{
    const r=await fetch('/api/telegram/send',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text:arRenderTpl(rule,res)})});
    const d=await r.json();
    if(!d.ok) arNotify('ارسال تلگرام ناموفق بود', String(d.error||''), 'warn');
    return !!d.ok;
  }catch(e){ return false; }
}
async function arSendBale(rule, res){
  try{
    const r=await fetch('/api/bale/send',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text:arRenderTpl(rule,res)})});
    const d=await r.json();
    if(!d.ok) arNotify('ارسال به بله ناموفق بود', String(d.error||''), 'warn');
    return !!d.ok;
  }catch(e){ return false; }
}
/* real desktop push, on top of the in-page stack. Permission is only ever asked
   from a gesture (saving a rule with this action on); without it the card in the
   stack is still the answer — an alert must never be lost silently. */
function arPush(ruleName, body){
  try{
    if(typeof Notification==='undefined') return false;
    if(Notification.permission!=='granted') return false;
    const n=new Notification(String(ruleName||'MOHMD NEWS'), {body:String(body||''), tag:'mohmd-alert', lang:'fa'});
    setTimeout(function(){ try{ n.close(); }catch(e){} }, 60000);
    return true;
  }catch(e){ return false; }
}
function arAskNotify(){
  try{
    if(typeof Notification==='undefined'||Notification.permission!=='default') return;
    Notification.requestPermission();
  }catch(e){}
}
function arDispatch(rule, res){
  const acts=rule.actions||{};
  const body=res.hits.map(function(h){ return h.label+(h.art?' — '+(h.art.title_fa||h.art.title||''):' — '+arFmtVal(h)); }).join(' · ');
  const entry={ts:Date.now(), name:rule.name||'هشدار', body:body, hits:res.hits.length};
  if(acts.toast) arNotify(rule.name||'هشدار', body);
  if(acts.push && !arPush(rule.name||'هشدار', body) && !acts.toast)
    arNotify(rule.name||'هشدار', body+' — نوتیفیکیشن مرورگر در دسترس نیست، اینجا نشان داده شد', 'warn');
  if(acts.tone) arSquawk();
  if(acts.tg) arSendTelegram(rule, res);
  if(acts.bale) arSendBale(rule, res);
  AR.log.unshift(entry);
  AR.log=AR.log.slice(0,AR_LOG_MAX);
}
/* ── the loop: build a snapshot, run every enabled rule, dispatch ──────── */
function arBuildCtx(){
  const now=Math.floor(Date.now()/1000);
  const evs=[];
  const cal=(typeof ECON!=='undefined'&&ECON)?ECON.calendar:null;
  const events=(cal&&(cal.events||cal))||[];
  (Array.isArray(events)?events:[]).forEach(function(e){
    if(!e||e.ts==null) return;
    if(!e.past&&!(e.actual_n!=null||e.actual)) return;
    if(e.actual_n==null&&!e.actual) return;      /* only releases that printed */
    evs.push(e);
  });
  evs.sort(function(a,b){ return (b.ts||0)-(a.ts||0); });
  const news=((typeof DATA!=='undefined'&&DATA&&DATA.articles)||[]);
  return {prices:(typeof LIVE!=='undefined'&&LIVE)||{}, events:evs, news:news, now:now};
}
function arEvaluate(ctxIn){
  const ctx=ctxIn||arBuildCtx();
  AR.ctx=ctx; AR.lastRun=Date.now();
  const fired=[];
  AR.rules.forEach(function(rule){
    if(rule.enabled===false) return;
    const res=arRuleEval(rule, ctx);
    if(!res.ok) return;
    const sig=res.hits.map(function(h){
      return h.art?('a:'+h.art.id):(h.ev?('e:'+h.ev.ts+'|'+h.ev.title):('p:'+(h.sym||'')+'|'+(Number(h.value)||0).toFixed(4)));
    }).join('~');
    const rt=AR.rt[rule.id]||{};
    /* `|| 30` would turn an explicit 0 (fire on every tick) back into 30 min */
    const cool=Math.max(0, Number(rule.cooldown==null?30:rule.cooldown))*60*1000;
    /* Two different rhythms, deliberately:
       · a threshold/event rule is a *state* — once it fires it stays quiet for
         its cooldown even if the reading keeps wiggling (otherwise “WTI > 100”
         would shout on every 15s tick while the price drifts);
       · a headline is an *event* — the same article never fires the same rule
         twice, however long the rule runs. */
    if(rt.at && (Date.now()-rt.at)<cool) return;
    if(rt.sig===sig && res.hits.some(function(h){ return !!h.art; })) return;
    AR.rt[rule.id]={sig:sig, at:Date.now()};
    rule.fired=(rule.fired||0)+1; rule.last=Date.now();
    fired.push(rule);
    arDispatch(rule, res);
  });
  if(fired.length){ arStore(); arRenderList(); arRenderLog(); }
  arSummary();
  return fired;
}
/* coalesced tick — called from the price poll and the news cycle, runs on the
   next frame-ish slot so a slow rule can never delay a render */
function arTick(){
  if(AR.pending) return;
  AR.pending=setTimeout(function(){
    AR.pending=null;
    try{ arEvaluate(); }catch(e){ console.error('alertTick:', e); }
  }, 400);
}

/* ── builder UI: one row per condition, fields per kind ───────────────── */
function arBlankCond(){ return {kind:'price', sym:(orderedAssets()[0]||'BTC'), op:'gt', value:''}; }
function arFields(c){
  if(c.kind==='price'||c.kind==='change'){
    const syms=orderedAssets();
    return '<select class="ar-sym" aria-label="دارایی">'+syms.map(function(s){
        return '<option value="'+esc(s)+'"'+(c.sym===s?' selected':'')+'>'+esc(s)+'</option>'; }).join('')+'</select>'
      +'<select class="ar-op" aria-label="عملگر">'+Object.keys(AR_OPS).filter(function(k){ return k!=='contains'; }).map(function(k){
        return '<option value="'+k+'"'+(c.op===k?' selected':'')+'>'+AR_OP_SYM[k]+' '+AR_OPS[k]+'</option>'; }).join('')+'</select>'
      +'<input class="ar-val" type="text" inputmode="decimal" style="direction:ltr;text-align:left" placeholder="'
        +(c.kind==='change'?'-3':'100')+'" value="'+esc(String(c.value==null?'':c.value))+'" aria-label="مقدار">'
      +(c.kind==='change'?'<span class="ar-unit">درصد</span>':'<span class="ar-unit">دلار/واحد</span>');
  }
  if(c.kind==='event'){
    return '<select class="ar-impact" aria-label="سطح اهمیت">'+Object.keys(AR_IMPACTS).map(function(k){
      return '<option value="'+k+'"'+((c.impact||'all')===k?' selected':'')+'>'+AR_IMPACTS[k]+'</option>'; }).join('')+'</select>'
      +'<span class="ar-unit">رقم منتشرشده در تقویم</span>';
  }
  /* every value that reaches esc() is stringified first: esc() is the page's
     `.replace()`-based escaper, and a bare number would throw in it */
  return '<input class="ar-terms" type="text" placeholder="Hormuz, Emergency" style="direction:ltr;text-align:left" value="'
      +esc((c.terms||[]).join(', '))+'" aria-label="کلیدواژه‌ها">'
    +'<span class="ar-unit">اعتبار ≥</span>'
    +'<input class="ar-cred" type="text" inputmode="numeric" style="width:74px;direction:ltr;text-align:left" value="'
      +esc(String(c.minCred!=null?Math.round(c.minCred*100):85))+'" aria-label="حداقل اعتبار درصد"><span class="ar-unit">٪</span>'
    +'<input class="ar-within" type="text" inputmode="numeric" style="width:74px;direction:ltr;text-align:left" value="'
      +esc(String(c.within!=null?c.within:240))+'" aria-label="پنجرهٔ زمانی دقیقه"><span class="ar-unit">دقیقهٔ اخیر</span>';
}
function arRenderConds(list){
  const box=document.getElementById('arConds'); if(!box) return;
  const conds=(list&&list.length)?list:[arBlankCond()];
  box.innerHTML=conds.map(function(c,i){
    return '<div class="ar-cond" data-i="'+i+'">'
      +'<span class="ar-idx">'+toFa(i+1)+'</span>'
      +'<select class="ar-kind" aria-label="نوع شرط">'+Object.keys(AR_KINDS).map(function(k){
        return '<option value="'+k+'"'+(c.kind===k?' selected':'')+'>'+AR_KINDS[k]+'</option>'; }).join('')+'</select>'
      +'<span class="ar-fields">'+arFields(c)+'</span>'
      +'<button type="button" class="ar-del" aria-label="حذف شرط">'+ic('trash')+'</button>'
    +'</div>';
  }).join('');
}
function arReadConds(){
  const rows=[].slice.call(document.querySelectorAll('#arConds .ar-cond'));
  return rows.map(function(row){
    const val=function(sel){ const el=row.querySelector(sel); return el?el.value:''; };
    const kind=val('.ar-kind');
    if(kind==='price'||kind==='change') return {kind:kind, sym:val('.ar-sym'), op:val('.ar-op'), value:val('.ar-val').trim()};
    if(kind==='event') return {kind:kind, impact:val('.ar-impact')};
    return {kind:'news', terms:val('.ar-terms').split(',').map(function(s){ return s.trim(); }).filter(Boolean),
            minCred:(parseFloat(val('.ar-cred'))||0)/100, within:parseFloat(val('.ar-within'))||0};
  });
}
function arReadForm(){
  const num=function(id,d){ const v=parseFloat((document.getElementById(id)||{}).value); return isNaN(v)?d:v; };
  return {
    id:AR.edit||arNewId(),
    name:(document.getElementById('arName').value||'').trim(),
    enabled:true,
    logic:document.getElementById('arLogic').value,
    cooldown:num('arCooldown',30),
    when:arReadConds(),
    actions:{toast:document.getElementById('arActToast').checked,
             tone:document.getElementById('arActTone').checked,
             tg:document.getElementById('arActTg').checked,
             bale:document.getElementById('arActBale')?document.getElementById('arActBale').checked:false,
             push:document.getElementById('arActPush').checked},
    template:(document.getElementById('arTemplate').value||'').trim()||AR_TPL_DEFAULT,
    created:Date.now(), fired:0, last:0
  };
}
function arHint(msg, bad){
  const h=document.getElementById('arHint'); if(!h) return;
  h.textContent=msg||'';
  h.classList.toggle('is-bad', !!bad);
  h.classList.toggle('is-ok', !!msg && !bad);
}
function arLogicHint(){
  const l=document.getElementById('arLogic');
  const h=document.getElementById('arLogicHint');
  if(h) h.textContent=l&&l.value==='or'?'با OR: برقرار شدن یک شرط برای اجرای قانون کافی است.':'با AND: همهٔ شرطها باید هم‌زمان برقرار شوند.';
}
function arAddCond(){
  const list=arReadConds(); list.push(arBlankCond()); arRenderConds(list);
}
function arClearForm(){
  AR.edit=null;
  document.getElementById('arName').value='';
  document.getElementById('arLogic').value='and';
  document.getElementById('arCooldown').value='30';
  document.getElementById('arActToast').checked=true;
  document.getElementById('arActTone').checked=false;
  document.getElementById('arActTg').checked=false;
  if(document.getElementById('arActBale')) document.getElementById('arActBale').checked=false;
  document.getElementById('arActPush').checked=false;
  document.getElementById('arTemplate').value=AR_TPL_DEFAULT;
  document.getElementById('arSaveBtn').innerHTML=ic('save')+' ذخیرهٔ قانون';
  arRenderConds([arBlankCond()]); arLogicHint();
}
function arSave(){
  const rule=arReadForm();
  if(arValidate(rule)) return;
  if(AR.edit){
    const i=AR.rules.map(function(r){ return r.id; }).indexOf(AR.edit);
    if(i>=0){
      const old=AR.rules[i];
      rule.id=old.id; rule.created=old.created||rule.created;
      rule.fired=old.fired||0; rule.last=old.last||0; rule.enabled=old.enabled!==false;
      AR.rules[i]=rule;
    } else AR.rules.unshift(rule);
  } else AR.rules.unshift(rule);
  delete AR.rt[rule.id];
  if(rule.actions&&rule.actions.push) arAskNotify();   /* a user gesture may ask once */
  arStore(); arArmTone(); arClearForm(); arRenderList(); arSummary();
  arHint('قانون «'+(rule.name||'')+'» ذخیره شد ✓');
  toast('قانون هشدار ذخیره شد ✓');
}
function arEditRule(id){
  const rule=AR.rules.filter(function(r){ return r.id===id; })[0];
  if(!rule) return;
  AR.edit=id;
  document.getElementById('arName').value=rule.name||'';
  document.getElementById('arLogic').value=rule.logic||'and';
  document.getElementById('arCooldown').value=rule.cooldown!=null?rule.cooldown:30;
  const a=rule.actions||{};
  document.getElementById('arActToast').checked=!!a.toast;
  document.getElementById('arActTone').checked=!!a.tone;
  document.getElementById('arActTg').checked=!!a.tg;
  if(document.getElementById('arActBale')) document.getElementById('arActBale').checked=!!a.bale;
  document.getElementById('arActPush').checked=!!a.push;
  document.getElementById('arTemplate').value=rule.template||AR_TPL_DEFAULT;
  document.getElementById('arSaveBtn').innerHTML=ic('check')+' به‌روزرسانی قانون';
  arRenderConds((rule.when||[]).length?rule.when:[arBlankCond()]);
  arLogicHint();
  const panel=document.getElementById('arPanel');
  if(panel&&panel.scrollIntoView) panel.scrollIntoView({block:'start', behavior:'smooth'});
}
function arToggle(id, on){
  const rule=AR.rules.filter(function(r){ return r.id===id; })[0];
  if(!rule) return;
  rule.enabled=!!on; arStore(); arRenderList(); arSummary();
  toast(on?'قانون فعال شد':'قانون غیرفعال شد');
}
function arDelete(id){
  const rule=AR.rules.filter(function(r){ return r.id===id; })[0];
  if(!rule) return;
  AR.rules=AR.rules.filter(function(r){ return r.id!==id; });
  delete AR.rt[id];
  if(AR.edit===id) arClearForm();
  arStore(); arRenderList(); arSummary();
  toast('قانون حذف شد');
}
function arTestNow(){
  const rule=arReadForm();
  if(arValidate(rule)) return;
  const ctx=arBuildCtx(); AR.ctx=ctx;
  const lines=(rule.when||[]).map(function(c){
    const r=arCondOk(c, ctx);
    return arCondText(c)+' → '+(r===null?'داده در دسترس نیست':(r?'برقرار':'برقرار نیست'));
  });
  const res=arRuleEval(rule, ctx);
  lines.push(res.ok?('نتیجه: قانون برقرار است ('+toFa(res.hits.length)+' شرط)') : 'نتیجه: برقرار نیست');
  if(res.ok) arNotify('اجرای آزمایشی: '+(rule.name||''), res.hits.map(function(h){ return h.label+' — '+arFmtVal(h); }).join(' · '), 'warn');
  arHint(lines.join('\n'));
}
function arRenderList(){
  const box=document.getElementById('arList'); if(!box) return;
  if(!AR.rules.length){
    box.innerHTML='<div class="empty">هنوز قانونی ساخته نشده — با فرم بالا یکی بساز؛ مثلاً «نفت بالای ۱۰۰» یا «تیتر شامل Hormuz با اعتبار بالای ۸۵٪».</div>';
    return;
  }
  box.innerHTML=AR.rules.map(function(r){
    const a=r.actions||{};
    const acts=[a.toast?'توست':null, a.tone?'آهنگ':null, a.tg?'تلگرام':null, a.push?'نوتیفیکیشن':null].filter(Boolean).join(' · ')||'—';
    return '<div class="ar-item'+(r.enabled===false?' is-off':'')+'" data-id="'+esc(r.id)+'">'
      +'<div class="ar-item-hd">'
        +'<label class="switch ar-sw"><input type="checkbox" data-ar-toggle aria-label="فعال/غیرفعال"'
          +(r.enabled===false?'':' checked')+'><span class="slider"></span></label>'
        +'<b>'+esc(r.name||'هشدار')+'</b>'
        +'<span class="ar-tag">'+(r.logic==='or'?'OR':'AND')+' · '+toFa((r.when||[]).length)+' شرط</span>'
        +'<span class="ar-meta">'+toFa(r.fired||0)+' اجرا'
          +(r.last?(' · آخرین '+esc(tzClock(Math.floor(r.last/1000)))):'')+' · هر '+toFa(r.cooldown!=null?r.cooldown:30)+' دقیقه</span>'
        +'<span class="ar-item-btns">'
          +'<button type="button" class="btn ghost sm" data-ar-edit>'+ic('pen')+' ویرایش</button>'
          +'<button type="button" class="btn ghost sm" data-ar-del>'+ic('trash')+' حذف</button></span>'
      +'</div>'
      +'<div class="ar-item-body">'+esc((r.when||[]).map(arCondText).join(r.logic==='or'?' — یا — ':' و '))+'</div>'
      +'<div class="ar-item-acts"><span>اقدام: '+esc(acts)+'</span>'
        +(a.tg?'<span class="ar-tpl">قالب: '+esc((r.template||'').slice(0,60))+'</span>':'')+'</div>'
    +'</div>';
  }).join('');
}
function arRenderLog(){
  const box=document.getElementById('arLog'); if(!box) return;
  if(!AR.log.length){ box.innerHTML='<div class="empty">هنوز قانونی اجرا نشده است.</div>'; return; }
  box.innerHTML=AR.log.slice(0,20).map(function(e){
    const d=new Date(e.ts);
    return '<div class="ar-lrow"><span class="ar-lt">'+esc(tzClock(Math.floor(e.ts/1000)))+'</span>'
      +'<span class="ar-ld">'+esc(String(d.getFullYear())+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'))+'</span>'
      +'<b>'+esc(e.name||'')+'</b>'
      +'<span class="ar-lb">'+esc(e.body||'')+'</span></div>';
  }).join('');
}
function arSummary(){
  const el=document.getElementById('arSummary'); if(!el) return;
  const on=AR.rules.filter(function(r){ return r.enabled!==false; }).length;
  el.textContent=toFa(AR.rules.length)+' قانون ('+toFa(on)+' فعال) · '+toFa(AR.log.length)+' اجرا'
    +(AR.lastRun?(' · آخرین ارزیابی '+esc(tzClock(Math.floor(AR.lastRun/1000)))):'');
}
function arInitUI(){
  const panel=document.getElementById('arPanel');
  if(!panel) return;
  if(!AR.loaded){ AR.loaded=1; arLoad(); }
  const conds=document.getElementById('arConds');
  if(!AR.wired){
    AR.wired=1;
    conds.addEventListener('change', function(ev){
      const k=ev.target.closest('.ar-kind');
      if(!k) return;
      const row=ev.target.closest('.ar-cond');
      const list=arReadConds();
      /* fields differ per kind, so that row restarts from a blank one */
      list[+row.dataset.i]=Object.assign(arBlankCond(), {kind:k.value});
      arRenderConds(list);
    });
    conds.addEventListener('click', function(ev){
      const d=ev.target.closest('.ar-del');
      if(!d) return;
      const list=arReadConds();
      list.splice(+d.closest('.ar-cond').dataset.i, 1);
      arRenderConds(list.length?list:[]);
    });
    const list=document.getElementById('arList');
    list.addEventListener('click', function(ev){
      const item=ev.target.closest('.ar-item');
      if(!item) return;
      if(ev.target.closest('[data-ar-edit]')) arEditRule(item.dataset.id);
      else if(ev.target.closest('[data-ar-del]')) arDelete(item.dataset.id);
    });
    list.addEventListener('change', function(ev){
      const t=ev.target.closest('[data-ar-toggle]');
      if(!t) return;
      arToggle(t.closest('.ar-item').dataset.id, t.checked);
    });
    document.getElementById('arLogic').addEventListener('change', arLogicHint);
    arArmTone();
  }
  if(!conds.querySelector('.ar-cond')) arRenderConds([]);
  if(!document.getElementById('arTemplate').value) document.getElementById('arTemplate').value=AR_TPL_DEFAULT;
  arLogicHint(); arRenderList(); arRenderLog(); arSummary();
  window.__arDebug={AR:AR, condOk:arCondOk, ruleEval:arRuleEval, evaluate:arEvaluate, ctx:arBuildCtx};
}

function initAlerts(){
  const tg=(DATA&&DATA.config&&DATA.config.telegram)||{};
  const tk=document.getElementById('tgToken'), tc=document.getElementById('tgChat');
  if(tg.token && (!tk.value || tk.value.length < 5)) tk.value=tg.token;
  if(tg.chat && !tc.value) tc.value=tg.chat;
  const tgw=document.getElementById('tgGateway');
  if(tgw && !tgw.value) tgw.value=tg.gateway||'';
  const tgp=document.getElementById('tgProxy');
  if(tgp && !tgp.value) tgp.value=tg.proxy||'';
  const tgi=document.getElementById('tgIdeas');
  if(tgi) tgi.checked = tg.send_ideas!==false;
  const tgd=document.getElementById('tgDigest');
  if(tgd) tgd.checked = tg.send_digest===true;
  document.getElementById('tgEnabled').checked = tg.enabled!==false;
  document.getElementById('tgMinCred').value = tg.min_credibility!=null?tg.min_credibility:0.70;
  document.getElementById('tgMaxItems').value = tg.max_items||10;
  document.getElementById('tgMaxAge').value = tg.max_age_hours||24;
  document.getElementById('tgAssets').value = (tg.asset_filter||[]).join(', ');
  document.getElementById('tgQuiet').checked = tg.quiet_hours!==false;
  document.getElementById('tgLink').checked = tg.include_link!==false;
  document.getElementById('tgLinkLine').checked = !!tg.link_on_own_line;
  document.getElementById('tgSummary').checked = tg.include_summary!==false;
  document.getElementById('tgHashtags').checked = tg.hashtags!==false;
  document.getElementById('tgEmoji').checked = tg.emoji!==false;
  document.getElementById('tgStars').checked = tg.show_stars!==false;
  document.getElementById('tgSilent').checked = !!tg.silent;
  document.getElementById('tgPin').checked = !!tg.pin;
  document.getElementById('tgLang').value = tg.language||'fa';
  document.getElementById('tgTemplate').value = tg.template||TG_TPL_DEFAULT;
  initBale();
  arInitUI();                    /* the smart-alert builder lives in this view */
}

function toggleTokenVisibility(){
  const tk = document.getElementById('tgToken');
  if(!tk) return;
  tk.type = tk.type === 'password' ? 'text' : 'password';
}

async function detectTelegramChat(){
  const token = document.getElementById('tgToken').value.trim();
  const btn = document.getElementById('btnDetectChat');
  const box = document.getElementById('detectedChatsBox');
  if(!token){
    toast('ابتدا توکن ربات تلگرام را وارد کنید');
    return;
  }
  if(btn) btn.textContent = '⏳ در حال بررسی...';
  try {
    const r = await fetch('/api/telegram/get-chat-id', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({token})
    });
    const d = await r.json();
    if(!d.ok){
      toast('✗ خطا: ' + (d.error || 'ارتباط برقرار نشد'));
      if(box){
        box.style.display = 'block';
        box.innerHTML = `<div style="background:rgba(235,87,87,0.12);padding:10px 14px;border-radius:8px;border:1px solid var(--dn,#eb5757);color:var(--dn,#eb5757);font-size:0.85rem">✗ ${esc(d.error || 'خطا در بررسی توکن')}</div>`;
      }
      return;
    }
    if(d.chats && d.chats.length > 0){
      const latest = d.chats[d.chats.length - 1];
      document.getElementById('tgChat').value = latest.id;
      toast('✓ چت شناسایی شد: ' + (latest.title || latest.id));
      if(box){
        box.style.display = 'block';
        /* chat titles/usernames are REMOTE-CONTROLLED text (any Telegram user
           can name a chat) — everything here goes through esc() */
        let html = '<div style="background:var(--bg2,#1c2128);padding:10px 14px;border-radius:8px;border:1px solid var(--border,#30363d);font-size:0.85rem">';
        html += `<div style="color:var(--up,#2ecc71);margin-bottom:8px">✓ ربات @${esc(d.bot_username || '')} متصل است. چت‌های شناسایی‌شده:</div>`;
        d.chats.forEach((c, ci) => {
          const cid = String(c.id == null ? '' : c.id);
          html += `<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.06)">
            <span><b>${esc(c.title || '')}</b> <span style="opacity:0.7">(${esc(c.type || '')})</span> <code style="direction:ltr;display:inline-block">${esc(cid)}</code></span>
            <button class="btn sm" type="button" data-chatpick="${esc(cid)}">انتخاب</button>
          </div>`;
        });
        html += '</div>';
        box.innerHTML = html;
        box.querySelectorAll('[data-chatpick]').forEach(b => {
          b.addEventListener('click', () => {
            document.getElementById('tgChat').value = b.getAttribute('data-chatpick');
            toast('شناسه چت انتخاب شد');
          });
        });
      }
    } else {
      toast('ربات متصل است اما پیامی دریافت نکرده است');
      if(box){
        box.style.display = 'block';
        box.innerHTML = `<div style="background:rgba(243,156,18,0.12);padding:10px 14px;border-radius:8px;border:1px solid var(--warn,#f39c12);color:var(--warn,#f39c12);font-size:0.85rem">
          ⚠️ ${esc(d.hint || 'پیامی در ربات یافت نشد.')}
        </div>`;
      }
    }
  } catch(e) {
    toast('خطای اتصال به سرور: ' + e);
  } finally {
    if(btn) btn.textContent = '🔍 تشخیص خودکار چت';
  }
}

async function saveTelegram(){
  const p=tgPayload();
  if(!p.telegram.token||!p.telegram.chat){ toast('توکن و شناسهٔ چت را وارد کنید'); return; }
  const r=await postSettings(p);
  if(r&&r.ok){
    toast('همه تنظیمات تلگرام ذخیره شد ✓');
    if(r.config && r.config.telegram && DATA && DATA.config){
      DATA.config.telegram = r.config.telegram;
    }
  } else {
    toast('خطا در ذخیره تنظیمات');
  }
}

async function testTelegram(){
  const token=document.getElementById('tgToken').value.trim(), chat=document.getElementById('tgChat').value.trim();
  if(!token||!chat){ toast('توکن و شناسهٔ چت را وارد کنید'); return; }
  toast('در حال ارسال پیام تست به تلگرام...');
  const r=await fetch('/api/telegram/test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,chat})});
  const d=await r.json();
  if(d.ok){
    toast('✓ پیام تست با موفقیت ارسال شد — تلگرام خود را چک کنید');
  } else {
    toast('✗ ارسال نشد: ' + (d.error || 'خطای نامشخص'));
  }
}

async function sendNowTelegram(){
  toast('در حال ارسال خلاصه خبرها به تلگرام...');
  const r=await fetch('/api/telegram/send-now',{method:'POST'});
  const d=await r.json();
  if(d.ok){
    toast(`✓ خلاصه ارسال شد (${toFa(d.sent||0)} خبر)`);
  } else {
    toast('✗ ارسال نشد: ' + (d.error || 'خطای نامشخص'));
  }
}

async function previewTelegram(){
  /* server renders with saved config but never sends */
  await saveTelegram();
  const r=await fetch('/api/telegram/preview',{method:'POST'});
  const d=await r.json();
  const box=document.getElementById('tgPreview');
  box.style.display='block';
  box.textContent = d.ok ? d.text.replace(/<[^>]+>/g,'') : ('خطا: '+(d.error||''));
}

/* ═══════════ Bale Messenger Settings ═══════════ */
const BALE_TPL_DEFAULT='**{title}**\n\n{summary_blocks}{key_point}{link_line}';

function switchMessengerTab(type){
  const tgPanel = document.getElementById('panel-messenger-tg');
  const balePanel = document.getElementById('panel-messenger-bale');
  const tgBtn = document.getElementById('subtab-btn-tg');
  const baleBtn = document.getElementById('subtab-btn-bale');
  if(type === 'bale'){
    if(tgPanel) tgPanel.style.display = 'none';
    if(balePanel) balePanel.style.display = 'block';
    if(tgBtn){ tgBtn.classList.remove('btn'); tgBtn.classList.add('btn', 'ghost'); }
    if(baleBtn){ baleBtn.classList.remove('ghost'); }
  } else {
    if(tgPanel) tgPanel.style.display = 'block';
    if(balePanel) balePanel.style.display = 'none';
    if(tgBtn){ tgBtn.classList.remove('ghost'); }
    if(baleBtn){ baleBtn.classList.remove('btn'); baleBtn.classList.add('btn', 'ghost'); }
  }
}

function balePayload(){
  return {bale:{
    token: document.getElementById('baleToken').value.trim(),
    chat: document.getElementById('baleChat').value.trim(),
    enabled: document.getElementById('baleEnabled').checked,
    min_credibility: parseFloat(document.getElementById('baleMinCred').value)||0.70,
    max_items: parseInt(document.getElementById('baleMaxItems').value)||10,
    max_age_hours: parseFloat(document.getElementById('baleMaxAge').value)||24,
    asset_filter: document.getElementById('baleAssets').value.split(',').map(x=>x.trim().toUpperCase()).filter(Boolean),
    quiet_hours: document.getElementById('baleQuiet').checked,
    send_ideas: document.getElementById('baleIdeas') ? document.getElementById('baleIdeas').checked : true,
    send_digest: document.getElementById('baleDigest') ? document.getElementById('baleDigest').checked : false,
    link_shortener: {
      provider: document.getElementById('lsEnabled') && !document.getElementById('lsEnabled').checked ? 'none' : (document.getElementById('lsProvider') ? document.getElementById('lsProvider').value : 'auto'),
      api_key: document.getElementById('lsApiKey') ? document.getElementById('lsApiKey').value.trim() : '',
      custom_endpoint: document.getElementById('lsCustom') ? document.getElementById('lsCustom').value.trim() : ''
    },
    include_link: document.getElementById('baleLink').checked,
    include_summary: document.getElementById('baleSummary').checked,
    hashtags: document.getElementById('baleHashtags').checked,
    emoji: document.getElementById('baleEmoji').checked,
    show_stars: document.getElementById('baleStars').checked,
    silent: document.getElementById('baleSilent').checked,
    language: document.getElementById('baleLang').value,
    template: document.getElementById('baleTemplate').value.trim()
  }};
}

function initBale(){
  const bale=(DATA&&DATA.config&&DATA.config.bale)||{};
  const tk=document.getElementById('baleToken'), tc=document.getElementById('baleChat');
  if(tk && bale.token && (!tk.value || tk.value.length < 5)) tk.value = bale.token;
  if(tc && bale.chat && !tc.value) tc.value = bale.chat;
  const be = document.getElementById('baleEnabled');
  if(be) be.checked = bale.enabled!==false;
  const bmc = document.getElementById('baleMinCred');
  if(bmc) bmc.value = bale.min_credibility!=null?bale.min_credibility:0.70;
  const bmi = document.getElementById('baleMaxItems');
  if(bmi) bmi.value = bale.max_items||10;
  const bma = document.getElementById('baleMaxAge');
  if(bma) bma.value = bale.max_age_hours||24;
  const bas = document.getElementById('baleAssets');
  if(bas) bas.value = (bale.asset_filter||[]).join(', ');
  const bq = document.getElementById('baleQuiet');
  if(bq) bq.checked = bale.quiet_hours!==false;
  const bIdeas = document.getElementById('baleIdeas');
  if(bIdeas) bIdeas.checked = bale.send_ideas!==false;
  const bDigest = document.getElementById('baleDigest');
  if(bDigest) bDigest.checked = bale.send_digest===true;
  const lsC = (DATA && DATA.config && DATA.config.link_shortener) || {};
  const lsp = document.getElementById('lsProvider');
  if(lsp) lsp.value = lsC.provider || 'auto';
  const lsk = document.getElementById('lsApiKey');
  if(lsk && !lsk.value && lsC.api_key) lsk.value = lsC.api_key;
  const lsc = document.getElementById('lsCustom');
  if(lsc && !lsc.value && lsC.custom_endpoint) lsc.value = lsC.custom_endpoint;
  const lse = document.getElementById('lsEnabled');
  if(lse) lse.checked = (lsC.provider || 'auto') !== 'none';
  const bl = document.getElementById('baleLink');
  if(bl) bl.checked = bale.include_link!==false;
  const bs = document.getElementById('baleSummary');
  if(bs) bs.checked = bale.include_summary!==false;
  const bh = document.getElementById('baleHashtags');
  if(bh) bh.checked = bale.hashtags!==false;
  const bem = document.getElementById('baleEmoji');
  if(bem) bem.checked = bale.emoji!==false;
  const bst = document.getElementById('baleStars');
  if(bst) bst.checked = bale.show_stars!==false;
  const bsl = document.getElementById('baleSilent');
  if(bsl) bsl.checked = !!bale.silent;
  const bla = document.getElementById('baleLang');
  if(bla) bla.value = bale.language||'fa';
  const bt = document.getElementById('baleTemplate');
  if(bt) bt.value = bale.template||BALE_TPL_DEFAULT;
}

function toggleBaleTokenVisibility(){
  const tk = document.getElementById('baleToken');
  if(!tk) return;
  tk.type = tk.type === 'password' ? 'text' : 'password';
}

async function detectBaleChat(){
  const token = document.getElementById('baleToken').value.trim();
  const btn = document.getElementById('btnDetectBaleChat');
  const box = document.getElementById('detectedBaleChatsBox');
  if(!token){
    toast('ابتدا توکن ربات بله را وارد کنید');
    return;
  }
  if(btn) btn.textContent = '⏳ در حال بررسی...';
  try {
    const r = await fetch('/api/bale/get-chat-id', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({token})
    });
    const d = await r.json();
    if(!d.ok){
      toast('✗ خطا: ' + (d.error || 'ارتباط برقرار نشد'));
      if(box){
        box.style.display = 'block';
        box.innerHTML = `<div style="background:rgba(235,87,87,0.12);padding:10px 14px;border-radius:8px;border:1px solid var(--dn,#eb5757);color:var(--dn,#eb5757);font-size:0.85rem">✗ ${d.error || 'خطا در بررسی توکن بله'}</div>`;
      }
      return;
    }
    if(d.chats && d.chats.length > 0){
      const latest = d.chats[d.chats.length - 1];
      document.getElementById('baleChat').value = latest.id;
      toast(`✓ چت بله شناسایی شد: ${latest.title} (${latest.id})`);
      if(box){
        box.style.display = 'block';
        let html = '<div style="background:var(--bg2,#1c2128);padding:10px 14px;border-radius:8px;border:1px solid var(--border,#30363d);font-size:0.85rem">';
        html += `<div style="color:var(--up,#2ecc71);margin-bottom:8px">✓ ربات @${d.bot_username || ''} در بله متصل است. چت‌های شناسایی‌شده:</div>`;
        d.chats.forEach(c => {
          html += `<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.06)">
            <span><b>${c.title}</b> <span style="opacity:0.7">(${c.type})</span> <code style="direction:ltr;display:inline-block">${c.id}</code></span>
            <button class="btn sm" type="button" onclick="document.getElementById('baleChat').value='${c.id}';toast('شناسه چت بله انتخاب شد');">انتخاب</button>
          </div>`;
        });
        html += '</div>';
        box.innerHTML = html;
      }
    } else {
      toast('ربات بله متصل است اما پیامی دریافت نکرده است');
      if(box){
        box.style.display = 'block';
        box.innerHTML = `<div style="background:rgba(243,156,18,0.12);padding:10px 14px;border-radius:8px;border:1px solid var(--warn,#f39c12);color:var(--warn,#f39c12);font-size:0.85rem">
          ⚠️ ${d.hint || 'پیامی در ربات بله یافت نشد.'}
        </div>`;
      }
    }
  } catch(e) {
    toast('خطای اتصال به سرور: ' + e);
  } finally {
    if(btn) btn.textContent = '🔍 تشخیص خودکار چت';
  }
}

async function saveBale(){
  const p=balePayload();
  if(!p.bale.token||!p.bale.chat){ toast('توکن و شناسهٔ چت بله را وارد کنید'); return; }
  const r=await postSettings(p);
  if(r&&r.ok){
    toast('همه تنظیمات پیام‌رسان بله ذخیره شد ✓');
    if(r.config && r.config.bale && DATA && DATA.config){
      DATA.config.bale = r.config.bale;
    }
  } else {
    toast('خطا در ذخیره تنظیمات بله');
  }
}

async function pushIdeasNow(){
  toast('در حال ارسال همهٔ ایده‌های نارسیده… چند دقیقه طول می‌کشد');
  const r=await fetch('/api/ideas/push-now',{method:'POST',headers:{'Content-Type':'application/json'}});
  const d=await r.json().catch(()=>({}));
  if(d.ok){ toast(d.already_running ? 'یک پوش در حال اجراست — صبر کن تمام شود' : 'ارسال آغاز شد ✓ بعداً چک کن'); }
  else{ toast('خطا در شروع ارسال'); }
}

async function testBale(){
  const token=document.getElementById('baleToken').value.trim(), chat=document.getElementById('baleChat').value.trim();
  if(!token||!chat){ toast('توکن و شناسهٔ چت بله را وارد کنید'); return; }
  toast('در حال ارسال پیام تست به پیام‌رسان بله...');
  const r=await fetch('/api/bale/test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,chat})});
  const d=await r.json();
  if(d.ok){
    toast('✓ پیام تست با موفقیت به بله ارسال شد — اپلیکیشن بله را چک کنید');
  } else {
    toast('✗ ارسال نشد: ' + (d.error || 'خطای نامشخص'));
  }
}

async function sendNowBale(){
  toast('در حال ارسال خلاصه خبرها به بله...');
  const r=await fetch('/api/bale/send-now',{method:'POST'});
  const d=await r.json();
  if(d.ok){
    toast(`✓ خلاصه ارسال شد (${toFa(d.sent||0)} خبر)`);
  } else {
    toast('✗ ارسال نشد: ' + (d.error || 'خطای نامشخص'));
  }
}

async function previewBale(){
  await saveBale();
  const r=await fetch('/api/bale/preview',{method:'POST'});
  const d=await r.json();
  const box=document.getElementById('balePreview');
  if(box){
    box.style.display='block';
    box.textContent = d.ok ? d.text : ('خطا: '+(d.error||''));
  }
}

loadData();
pollLive();
dl2Skeleton(6);
setTimeout(function(){ dl2MarkSeen(); }, 15000);

/* ═══════════════════════════════════════════════════════════════════════════
   STREAM MANAGER — one connection, three channels, no polling while it works
   ═══════════════════════════════════════════════════════════════════════════
   Replaces the hand-rolled `connectSSE()` that stood here, and the timers it
   leaned on: prices every 15s, the feed every 60s, a 120s safety net, and every
   one of those refreshes re-rendered a whole component (the ticker rebuilt its
   markup on each tick, the feed replaced #newsGrid — taking the reader's scroll
   position with it).

     transport   WebSocket → SSE → HTTP polling, in that order. A WebSocket is
                 used when the server advertises one (/api/stream/info); this
                 deployment pushes over SSE, which needs no upgrade and no
                 dependency, and the client is written so pointing a proxy at a
                 ws endpoint is the only change required to move to it.
     contract    one socket, three channels routed by event name:
                   prices   → tick frames, applied as micro-updates
                   news     → newly ingested articles, prepended
                   calendar → a release that just landed, flashed in place
     backoff     1s · 2s · 5s · 10s · 20s · 30s … capped at 30s, with jitter so
                 N tabs started together do not reconnect in lockstep. Polling
                 is only started while no transport is alive, and stopped again
                 the moment one connects.
     DOM         one requestAnimationFrame per batch. Only the `.p` / `.c` nodes
                 whose value actually moved are written and flashed: an
                 unchanged symbol costs zero layout work.
     feed        new headlines are inserted above the list and the scroll offset
                 is corrected by exactly the height that was added.
   ═══════════════════════════════════════════════════════════════════════════ */
const SM_BACKOFF=[1000,2000,5000,10000,20000,30000];
const SM_CHANNELS=['prices','news','calendar'];
/* server event name → channel. The server emits `init`, `update` and `prices`
   today (see app.py `_sse_broadcast`) and `calendar` for releases; the extra
   spellings are accepted so a new server event cannot silently vanish. */
const SM_WIRE={prices:'prices', tick:'prices', quote:'prices',
               update:'news', news:'news', init:'news',
               calendar:'calendar', release:'calendar', econ:'calendar'};
const SM_POLL={prices:15000, data:120000, calendar:300000};

/* 1s, 2s, 5s, 10s, 20s, 30s, 30s… with up to 25% jitter */
function smBackoff(attempt){
  const i=Math.max(0, Math.min(SM_BACKOFF.length-1, (parseInt(attempt,10)||1)-1));
  const base=SM_BACKOFF[i];
  return base + Math.floor(Math.random()*Math.min(500, Math.round(base/4)));
}
function smRouteEvent(name){
  return SM_WIRE[String(name==null?'':name).toLowerCase()]||null;
}
/* What actually changed since the previous frame — the whole reason the DOM
   update can be cheap: symbols that did not move produce no entries at all. */
function smPriceDiff(prev, next, fields){
  const keys=fields||['price','change_24h'], out=[];
  const prevMap=prev||{}, nextMap=next||{};
  Object.keys(nextMap).forEach(function(sym){
    const a=prevMap[sym]||{}, b=nextMap[sym]||{}, moved=[];
    keys.forEach(function(f){
      if(b[f]==null) return;
      if(a[f]==null||Number(a[f])!==Number(b[f])) moved.push(f);
    });
    if(!moved.length) return;
    out.push({sym:sym, price:b.price, change:b.change_24h, moved:moved,
              dir:(a.change_24h==null||b.change_24h==null)?0:(b.change_24h>a.change_24h?1:(b.change_24h<a.change_24h?-1:0)),
              dirPrice:(a.price==null||b.price==null)?0:(b.price>a.price?1:(b.price<a.price?-1:0))});
  });
  return out;
}
/* Newest-first merge that neither duplicates nor reorders: the stream and a
   /api/data refresh can both deliver the same story. */
function smMergeNews(existing, incoming, limit){
  const seen={}, merged=[];
  (incoming||[]).forEach(function(a){ if(a&&a.id&&!seen[a.id]){ seen[a.id]=1; merged.push(a); } });
  const fresh=merged.slice();
  (existing||[]).forEach(function(a){ if(a&&a.id&&!seen[a.id]){ seen[a.id]=1; merged.push(a); } });
  merged.sort(function(x,y){ return (y.published_ts||0)-(x.published_ts||0); });
  return {list:(limit?merged.slice(0,limit):merged), fresh:fresh};
}
/* Scroll anchoring, by reference point rather than by height.

   The obvious version (add the height the list grew by) is wrong here: the feed
   is a multi-column grid, so inserting one card repacks the columns and the
   total height can even shrink. What must stay fixed is the element the reader
   is looking at, so the anchor is that element's viewport position: whatever it
   moved down by is exactly what scrollTop has to move down by. */
function smAnchorScroll(prevTop, prevAnchorTop, nextAnchorTop){
  const shift=(Number(nextAnchorTop)||0)-(Number(prevAnchorTop)||0);
  return Math.max(0, (Number(prevTop)||0) + shift);
}
/* Is the feed narrowed right now? A new card prepended into a filtered list can
   be a card that does not belong there, so in that case the renderer is used
   instead of the incremental path (rare, and it keeps the two honest). */
function smFeedFiltered(){
  try{
    const q=(document.getElementById('q').value||'').trim();
    const src=document.getElementById('srcSel').value, kind=document.getElementById('kindSel').value;
    const minC=+document.getElementById('credSlider').value/100;
    return !!(q||(src&&src!=='all')||(kind&&kind!=='all')||minC>0||
              UI.topic!=='all'||UI.asset!=='all'||UI.onlyBookmarked||UI.onlyWatchlist);
  }catch(e){ return true; }
}
function smChangeText(chg){ return (chg>=0?'▲':'▼')+Math.abs(Number(chg)).toFixed(2)+'%'; }
/* The feed scrolls inside `main.app-main`, not the document — anchoring against
   document.scrollingElement silently does nothing (the page itself does not
   scroll at all in this shell), which is how a prepend ends up throwing the
   reader to a different story. Walk up to whatever actually scrolls. */
/* The card the reader is actually looking at, not the first card in the list:
   in a multi-column grid the first card stays in the first row when something
   is inserted before it (it only slides sideways), while the cards below it
   move down a whole row. Anchoring on the topmost *visible* card is therefore
   the only choice that reflects what the eye is following. */
function smPickAnchor(grid, scroller){
  if(!grid||!scroller) return null;
  const top=scroller.getBoundingClientRect().top;
  const kids=grid.children;
  for(let i=0;i<kids.length;i++){
    const r=kids[i].getBoundingClientRect();
    if(r.bottom>top+1) return kids[i];
  }
  return null;
}
function smScroller(from){
  let n=from||document.getElementById('newsGrid');
  while(n&&n!==document.body){
    let cs=null;
    try{ cs=getComputedStyle(n); }catch(e){ cs=null; }
    if(cs&&(cs.overflowY==='auto'||cs.overflowY==='scroll')&&n.scrollHeight>n.clientHeight) return n;
    n=n.parentElement;
  }
  return document.scrollingElement||document.documentElement;
}

/* ── DOM micro-updates ──────────────────────────────────────────────────────
   The price index is built from the markup, not from the data: any element that
   carries `data-sym` (ticker chips, asset table rows) and holds a `.p` and/or
   `.c` child becomes a hit target. That keeps this layer independent of the
   renderers — a new component gets live ticks the moment it declares its symbol. */
let SM_INDEX={}, SM_INDEX_SIZE=0;
function smIndexPrices(root){
  const idx={}, nodes=(root||document).querySelectorAll('[data-sym]');
  for(let i=0;i<nodes.length;i++){
    const sym=nodes[i].getAttribute('data-sym');
    if(!sym) continue;
    const p=nodes[i].querySelector('.p'), c=nodes[i].querySelector('.c');
    if(!p&&!c) continue;
    const slot=idx[sym]||(idx[sym]={p:[], c:[]});
    if(p) slot.p.push(p);
    if(c) slot.c.push(c);
  }
  SM_INDEX=idx;
  SM_INDEX_SIZE=nodes.length;
  return idx;
}
function smPaintPrices(diff){
  if(!diff||!diff.length) return 0;
  if(!SM_INDEX_SIZE) smIndexPrices(document);
  let touched=0;
  diff.forEach(function(t){
    const slot=SM_INDEX[t.sym];
    if(!slot) return;
    slot.p.forEach(function(el){
      const txt=fmtPrice(t.price);
      if(el.textContent===txt) return;
      el.textContent=txt; touched++;
      if(t.dirPrice) flash(el, t.dirPrice);
    });
    slot.c.forEach(function(el){
      if(t.change==null) return;
      const txt=smChangeText(t.change);
      if(el.textContent===txt) return;
      el.textContent=txt; touched++;
      const host=el.parentElement;
      if(host){ host.classList.remove('up','dn'); host.classList.add(t.change>=0?'up':'dn'); }
      if(t.dir) flash(el, t.dir);
    });
  });
  return touched;
}
function smPrependNews(list){
  const grid=document.getElementById('newsGrid');
  const vs=VS.feed;
  if(!grid||!list||!list.length) return 0;
  const seen={};
  /* the identity of what is already on screen comes from the window's own
     item list when it is virtualised — the DOM only holds a few rows, so
     reading ids out of it would re-admit a story that is merely scrolled off */
  if(vs) vs.items.forEach(function(a){ if(a&&a.id) seen[a.id]=1; });
  else [].forEach.call(grid.children, function(n){ const id=n.getAttribute('data-id'); if(id) seen[id]=1; });
  const fresh=list.filter(function(a){ return a&&a.id&&!seen[a.id]; });
  if(!fresh.length) return 0;
  /* windowed path (see below): the head of the list grows and the rows are re-placed from
     the computed offsets, so the reader's position is corrected by arithmetic
     rather than by a DOM probe — which is exact even when the inserted cards
     change the height of the very row the reader is looking at */
  if(vs){ vs.prepend(fresh); return fresh.length; }
  const scroller=smScroller(grid);
  const wasEmpty=!grid.children.length;
  const anchor=smPickAnchor(grid, scroller);                 /* the story at the top of the view */
  const anchorTop=anchor?anchor.getBoundingClientRect().top:0;
  grid.insertAdjacentHTML('afterbegin', fresh.map(cardHTML).join(''));
  const added=Array.prototype.slice.call(grid.children, 0, fresh.length);
  added.forEach(function(el){ el.classList.add('card-enter'); });
  /* only correct the scroll when the reader has scrolled: at the top of the
     list the new cards should simply be there */
  if(anchor&&!wasEmpty&&scroller.scrollTop>0){
    const next=smAnchorScroll(scroller.scrollTop, anchorTop, anchor.getBoundingClientRect().top);
    if(next!==scroller.scrollTop) scroller.scrollTop=next;
  }
  setTimeout(function(){ added.forEach(function(el){ el.classList.remove('card-enter'); }); }, 1000);
  return fresh.length;
}
function smFlashEvent(item){
  if(!item) return false;
  const q=function(s){ return String(s==null?'':s).replace(/"/g,'\\"'); };
  /* the calendar board renders rows as .cal-tr (dashboard's own markup); the
     epoch second is the fallback selector when the keys differ */
  /* the server's key first, the epoch second as the fallback: a release frame
     has to land on its own row without the client rebuilding the calendar */
  let row=item.key?document.querySelector('.cal-tr[data-key="'+q(item.key)+'"]'):null;
  if(!row&&item.ts!=null) row=document.querySelector('.cal-tr[data-ts="'+q(item.ts)+'"]');
  if(!row) return false;
  /* the board's own vocabulary (pending/released), plus a transient marker for
     the one row that changed while the reader was watching */
  row.classList.remove('pending');
  row.classList.add('released','just-released');
  flash(row, (item.better==null?0:item.better)>=0?1:-1);
  setTimeout(function(){ row.classList.remove('just-released'); }, 10000);
  const cell=row.querySelector('.c-num.c-act');
  if(cell&&item.actual_fmt&&cell.textContent!==String(item.actual_fmt)){
    cell.textContent=String(item.actual_fmt);
    cell.classList.remove('sched');
    flash(cell,1);
  }
  return true;
}

/* ── the manager ───────────────────────────────────────────────────────── */
class StreamManager{
  constructor(opts){
    opts=opts||{};
    this.handlers={};
    SM_CHANNELS.forEach((c)=>{ this.handlers[c]=[]; });
    this.info=opts.info||null;      /* /api/stream/info, asked once per connect */
    this.state='idle';              /* idle | connecting | live | reconnecting | polling | stopped */
    this.transport=null;            /* 'ws' | 'sse' | 'poll' */
    this.attempt=0;
    this.socket=null; this.es=null;
    this.timers={};
    this.queue={prices:null, news:[], calendar:[]};
    this.raf=null;
    this.prevPrices={};
    this.announced={};
    this.lastTick=0;
    this.counters={prices:0, news:0, calendar:0, reconnects:0, polls:0, dom:0};
  }
  /* Any channel may be subscribed to, not only the three data ones: `status`
     is emitted here too, and a lazy map means a new channel cannot be silently
     dropped by a missing initialiser (that bug cost a status pill that never
     painted while every other handler worked). */
  on(channel, fn){
    if(!fn) return this;
    if(!this.handlers[channel]) this.handlers[channel]=[];
    this.handlers[channel].push(fn);
    return this;
  }
  emit(channel, payload){
    (this.handlers[channel]||[]).forEach(function(fn){
      try{ fn(payload); }catch(e){ console.error('stream handler '+channel+':', e); }
    });
  }
  /* one probe per connect: the client must not guess a transport */
  probe(){
    return fetch('/api/stream/info',{cache:'no-store'})
      .then(function(r){ return r.ok?r.json():null; })
      .catch(function(){ return null; });
  }
  start(){
    if(this.state==='live'||this.state==='connecting') return this;
    /* the maquette is a single demo file opened from a disk with a stubbed
       fetch: it has no server to stream from, so it says so instead of
       retrying a socket that cannot exist */
    if(window.__MAQUETTE__){ this.state='demo'; smPaintStatus({state:'demo'}); return this; }
    this.state='connecting';
    const self=this;
    const go=function(){
      const info=self.info||{};
      const wantWs=(info.ws||window.__SM_FORCE_WS)&&typeof WebSocket==='function'&&!window.__SM_NO_WS;
      if(wantWs) self.openWs(info.ws||((location.protocol==='https:'?'wss://':'ws://')+location.host+'/api/ws'));
      else self.openSse(info.sse||'/api/stream');
    };
    if(this.info) go();
    else this.probe().then(function(info){ self.info=info; go(); });
    return this;
  }
  stop(){
    this.state='stopped';
    /* the fallback pollers are clock slots now, not browser timers: leaving
       them behind would keep polling a transport that is already closed */
    Object.keys(this.timers).forEach((k)=>{ Clock.off(this.timers[k]); });
    this.timers={};
    try{ if(this.socket) this.socket.close(); }catch(e){}
    try{ if(this.es) this.es.close(); }catch(e){}
    this.socket=null; this.es=null;
    return this;
  }
  alive(transport){
    this.transport=transport;
    this.state='live';
    this.attempt=0;
    this.stopPolling();
    /* a pending reconnect must not fire once the stream is back, or a healthy
       terminal reconnects on top of itself and the counters lie */
    if(this.timers.reconnect){ clearTimeout(this.timers.reconnect); delete this.timers.reconnect; }
    this.emit('status', {state:'live', transport:transport, attempt:0});
  }
  fail(transport){
    this.counters.reconnects++;
    try{ if(this.socket) this.socket.close(); }catch(e){}
    try{ if(this.es) this.es.close(); }catch(e){}
    this.socket=null; this.es=null;
    /* a ws that this server cannot serve is not a failure of the terminal: the
       same push model is available one line down, so step down immediately
       instead of waiting out the backoff for a transport that will never work */
    if(transport==='ws'&&!this.triedSse){ this.triedSse=true; this.openSse((this.info&&this.info.sse)||'/api/stream'); return; }
    this.startPolling();
    const delay=smBackoff(this.attempt+1);
    this.attempt++;
    this.emit('status', {state:'reconnecting', transport:this.transport, retryIn:delay, attempt:this.attempt});
    const self=this;
    clearTimeout(this.timers.reconnect);
    this.timers.reconnect=setTimeout(function(){ self.start(); }, delay);
  }
  openWs(url){
    const self=this;
    let sock;
    try{ sock=new WebSocket(url); }catch(e){ this.fail('ws'); return; }
    this.transport='ws'; this.socket=sock;
    sock.onopen=function(){ self.triedSse=false; self.alive('ws'); };
    sock.onmessage=function(ev){ self.ingest(ev.data); };
    sock.onerror=function(){ try{ sock.close(); }catch(e){} };
    sock.onclose=function(){ if(self.state!=='stopped') self.fail('ws'); };
  }
  openSse(url){
    if(typeof EventSource!=='function'){ this.startPolling(); return; }
    const self=this;
    this.transport='sse';
    const es=new EventSource(url);
    this.es=es;
    es.onopen=function(){ self.alive('sse'); };
    es.onmessage=function(ev){ self.ingest(ev.data, 'message'); };
    Object.keys(SM_WIRE).forEach(function(name){
      es.addEventListener(name, function(ev){ self.ingest(ev.data, name); });
    });
    es.onerror=function(){ if(self.state!=='stopped') self.fail('sse'); };
  }
  /* Accepts either a wire frame ({event, data}) or a bare SSE payload, and
     either an already-parsed object or JSON text. */
  ingest(raw, eventName){
    let frame=raw, name=eventName;
    /* tolerate either order — (payload, event) is what an SSE listener passes,
       (event, payload) is what a hand-built frame looks like */
    if(typeof frame==='string'&&name&&typeof name==='object'){ const t=frame; frame=name; name=t; }
    if(typeof frame==='string'){
      try{ frame=JSON.parse(frame); }catch(e){ return; }
      if(frame&&typeof frame==='object'&&(frame.event||frame.channel)){
        name=frame.event||frame.channel;
        frame=frame.data||frame.payload||frame;
      }
    }
    if(frame&&typeof frame==='object'&&frame.type&&!name) name=frame.type;
    const channel=smRouteEvent(name)||(frame&&smRouteEvent(frame.event))||null;
    if(!channel) return null;
    this.lastTick=Date.now();
    this.counters[channel]++;
    if(channel==='prices'){ this.queue.prices=frame; this.schedule(); }
    else if(channel==='news'){ this.queueNews(frame); }
    else { this.queue.calendar.push(frame); this.schedule(); }
    return channel;
  }
  queueNews(frame){
    if(!frame) return;
    const list=frame.articles||frame.items||(frame.id?[frame]:[]);
    const fresh=[];
    const self=this;
    list.forEach(function(a){ if(a&&a.id&&!self.announced[a.id]){ self.announced[a.id]=1; fresh.push(a); } });
    if(!fresh.length) return;
    this.queue.news=this.queue.news.concat(fresh);
    this.schedule();
  }
  schedule(){
    if(this.raf) return;
    const self=this;
    const run=function(){ self.raf=null; self.flush(); };
    this.raf=(typeof requestAnimationFrame==='function')?requestAnimationFrame(run):setTimeout(run, 16);
  }
  flush(){
    if(this.queue.prices){
      const next=this.queue.prices;
      const diff=smPriceDiff(this.prevPrices, next);
      this.prevPrices=next;
      if(diff.length){
        this.counters.dom+=smPaintPrices(diff);
        this.emit('prices', {prices:next, diff:diff});
      }
    }
    if(this.queue.news.length){
      const fresh=this.queue.news.slice();
      this.queue.news=[];
      const added=smPrependNews(fresh);
      this.emit('news', {fresh:fresh, prepended:added});
      if(window.Channel && typeof window.Channel.onCycleUpdate === 'function') window.Channel.onCycleUpdate();
    }
    if(this.queue.calendar.length){
      const items=this.queue.calendar.slice();
      this.queue.calendar=[];
      const self=this;
      items.forEach(function(item){ self.emit('calendar', item); });
    }
  }
  /* Polling is a fallback, never a parallel track: it starts only when no
     transport is alive and is cleared the moment one connects. */
  startPolling(){
    if(this.state==='polling') return;
    this.state='polling';
    this.emit('status', {state:'polling', transport:'poll', attempt:this.attempt});
    const self=this;
    const rates=(this.info&&this.info.poll_seconds)||SM_POLL;
    if(!this.timers.prices&&typeof pollLive==='function'){
      this.timers.prices=Clock.every((rates.prices||SM_POLL.prices)*1000, function(){ self.counters.polls++; pollLive(); }, {label:'stream-poll-prices'});
    }
    if(!this.timers.data&&typeof loadData==='function'){
      this.timers.data=Clock.every((rates.data||120)*1000, function(){ self.counters.polls++; loadData(); }, {label:'stream-poll-data'});
    }
    if(!this.timers.calendar&&typeof loadCalendar==='function'){
      this.timers.calendar=Clock.every((rates.calendar||300)*1000, function(){
        self.counters.polls++;
        if(typeof UI!=='undefined'&&UI.view==='calendar') loadCalendar();
      }, {label:'stream-poll-calendar'});
    }
  }
  stopPolling(){
    ['prices','data','calendar'].forEach((k)=>{ if(this.timers[k]){ Clock.off(this.timers[k]); delete this.timers[k]; } });
  }
  stats(){
    return {state:this.state, transport:this.transport, attempt:this.attempt,
            age:this.lastTick?Math.round((Date.now()-this.lastTick)/1000):null,
            counters:Object.assign({}, this.counters)};
  }
}

/* ── wiring ─────────────────────────────────────────────────────────────── */
function smPaintStatus(st){
  const item=document.getElementById('smItem'), dot=document.getElementById('smDot'), txt=document.getElementById('smTxt');
  if(!item) return;
  const label=st.state==='live'?(st.transport==='ws'?'WebSocket':'SSE live')
            : st.state==='polling'?'Polling fallback'
            : st.state==='reconnecting'?('Reconnect in '+Math.round((st.retryIn||0)/1000)+'s')
            : st.state==='demo'?'Demo (offline)'
            : st.state;
  item.dataset.mode=st.state==='live'?'online':(st.state==='polling'||st.state==='demo'?'warn':'offline');
  if(txt) txt.textContent=label;
  if(dot) dot.className='pwa-dot '+(st.state==='live'?'is-on':(st.state==='polling'?'is-idle':'is-off'));
  item.title='کانال‌های زنده: قیمت، خبر، تقویم — '+(st.transport||'—')+
             (st.attempt?(' · تلاش '+toFa(st.attempt)):'')+' · پوش‌ها: '+toFa((Stream.counters&&Stream.counters.prices)||0);
}
const Stream=new StreamManager();
Stream.on('prices', function(p){
  LIVE=p.prices||LIVE;
  if(typeof paintLive==='function') paintLive();   /* an open report head */
  if(typeof paintFng==='function') paintFng();
  if(typeof arTick==='function') arTick();         /* alert rules see the tick */
  /* the pill counts frames; refresh its tooltip without repainting the label */
  const item=document.getElementById('smItem');
  if(item&&Stream.transport) item.title='کانال‌های زنده: قیمت، خبر، تقویم — '+Stream.transport+
    ' · فریم‌های قیمت: '+toFa(Stream.counters.prices)+' · به‌روزرسانی DOM: '+toFa(Stream.counters.dom);
});
Stream.on('news', function(p){
  const fresh=p.fresh||[];
  if(!fresh.length) return;
  if(!DATA) DATA={};
  const merged=smMergeNews(DATA.articles||[], fresh);
  DATA.articles=merged.list;
  if(typeof smFeedFiltered==='function'&&smFeedFiltered()){
    /* a filter is on: the incremental path would insert a card the filter
       excludes, so the renderer does it (correct beats cheap) */
    if(typeof renderFeed==='function') renderFeed();
  } else {
    /* unfiltered path did not re-render — publish the new total here.
       (renderFeed writes the FILTERED count; writing the raw total
       unconditionally used to overwrite it.) */
    const cnt=document.getElementById('feedCount');
    if(cnt) cnt.textContent=toFa(DATA.articles.length)+' خبر';
  }
  const empty=document.getElementById('feedEmpty');
  if(empty&&DATA.articles.length) empty.style.display='none';
  if(typeof renderChips==='function') renderChips();
  if(typeof toast==='function'&&p.prepended) toast('خبر جدید — '+toFa(p.prepended)+' مورد');
});
Stream.on('calendar', function(item){
  const flashed=smFlashEvent(item);
  /* the released value has to survive the next render of the board */
  try{
    if(typeof ECON!=='undefined'&&ECON&&ECON.calendar&&ECON.calendar.events){
      [ECON.calendar, ECON.calendar_next].forEach(function(src){
        ((src&&src.events)||[]).forEach(function(e){
          const ek=(e.ts||0)+'_'+String(e.title||'').replace(/[^a-zA-Z0-9]/g,'').slice(0,20);
          if((item.key&&ek===item.key)||(e.ts===item.ts&&e.title===item.title)){
            e.actual=item.actual; e.actual_fmt=item.actual_fmt||e.actual_fmt; e.past=true; e.released=true;
          }
        });
      });
    }
  }catch(e){}
  if(typeof toast==='function'){
    toast((item.impact==='High'?'⚠️ ':'') + (item.country?('['+item.country+'] '):'')+(item.title||'')+' — '+(item.actual_fmt||item.actual||'')+
          (flashed?'':' (رویداد در نمای تقویم نیست)'));
  }
  if(typeof arTick==='function') arTick();
});
Stream.on('status', smPaintStatus);
Stream.start();
window.Stream=Stream;
window.SM=Stream;
