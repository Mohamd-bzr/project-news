/* ══ COMMAND PALETTE — Ctrl/Cmd+K ══════════════════════════════════════════
   One field over the whole product: every view, every covered asset (jumping
   straight to its report) and the handful of actions worth a shortcut. ↑ ↓
   move, Enter runs, Esc closes, a click outside closes. */
(function(){
  const VIEWS=[
    ['feed','جریان زندهٔ اخبار','news'],
    ['reports','تحلیل و گزارش‌ها','chart'],
    ['channel','ایده‌های محتوا','coins'],
    ['ideas','ایده‌های تریدینگ‌ویو','bulb'],
    ['calendar','تقویم اقتصادی','calendar'],
    ['etf','نرخ زندهٔ ETF','bank'],
    ['archive','آرشیو هوشمند','archive'],
    ['bookmarks','نشان‌شده‌ها','star'],
    ['monitor','سلامت منابع','pulse'],
    ['alerts','پیام‌رسان تلگرام','send'],
    ['settings','تنظیمات داشبورد','gear'],
    ['sources','مدیریت منابع خبری','rss'],
    ['assets','مدیریت دارایی‌ها','coins']
  ];
  let ITEMS=[], SEL=0;

  function build(){
    const q=(document.getElementById('cmdkQ').value||'').trim().toLowerCase();
    const out=[];
    VIEWS.forEach(v=>out.push({ label:v[1], kind:'بخش', icon:v[2],
      run:function(){ showView(v[0]); } }));
    try{
      (orderedAssets()||[]).forEach(function(sym){
        const meta=((DATA&&DATA.assets_meta)||{})[sym]||{};
        out.push({ label:(meta.fa?meta.fa+' ('+sym+')':sym), kind:'گزارش', icon:'file',
          run:function(){ showView('reports'); if(typeof pickReport==='function') pickReport(sym); } });
      });
    }catch(e){}
    out.push({ label:'Refresh now', kind:'کار', icon:'refresh', run:function(){ doRefresh(); } });
    out.push({ label:'پاک‌کردن فیلترهای خبر', kind:'کار', icon:'filter', run:function(){ resetFeedFilters(); } });
    out.push({ label:'جمع و باز کردن نوار کناری', kind:'کار', icon:'panel', run:function(){ toggleRail(); } });
    const list=q?out.filter(function(it){ return (it.label+' '+it.kind).toLowerCase().indexOf(q)>=0; }):out;
    return list.slice(0,40);
  }
  function paint(){
    const box=document.getElementById('cmdkList');
    box.innerHTML=ITEMS.length?ITEMS.map(function(it,i){
      return '<button class="cmdk-item'+(i===SEL?' sel':'')+'" role="option" data-i="'+i+'">'+
        ic(it.icon)+'<span>'+esc(it.label)+'</span><span class="cmdk-kind">'+esc(it.kind)+'</span></button>';
    }).join(''):'<div class="cmdk-empty">چیزی با این عبارت پیدا نشد.</div>';
    const c=document.getElementById('cmdkCount');
    if(c) c.textContent=toFa(ITEMS.length)+' نتیجه';
    box.querySelectorAll('.cmdk-item').forEach(function(el){
      el.addEventListener('click', function(){ run(+el.getAttribute('data-i')); });
    });
  }
  function refresh(){ ITEMS=build(); if(SEL>=ITEMS.length) SEL=0; paint(); }
  function move(d){
    if(!ITEMS.length) return;
    SEL=(SEL+d+ITEMS.length)%ITEMS.length;
    paint();
    const el=document.querySelector('.cmdk-item.sel');
    if(el&&el.scrollIntoView) el.scrollIntoView({block:'nearest'});
  }
  function run(i){
    const it=ITEMS[i]; if(!it) return;
    close();
    try{ it.run(); }catch(e){}
  }
  function open(){
    const w=document.getElementById('cmdk'); if(!w) return;
    w.classList.add('open');
    document.getElementById('cmdkQ').value='';
    SEL=0; refresh();
    setTimeout(function(){ document.getElementById('cmdkQ').focus(); }, 30);
  }
  function close(){ const w=document.getElementById('cmdk'); if(w) w.classList.remove('open'); }

  window.cmdkOpen=open;   const field=document.getElementById('cmdkQ');
  if(field){
    field.addEventListener('input', function(){ SEL=0; refresh(); });
    field.addEventListener('keydown', function(e){
      if(e.key==='ArrowDown'){ e.preventDefault(); move(1); }
      else if(e.key==='ArrowUp'){ e.preventDefault(); move(-1); }
      else if(e.key==='Enter'){ e.preventDefault(); run(SEL); }
      else if(e.key==='Escape'){ e.preventDefault(); close(); }
    });
  }
  const wrap=document.getElementById('cmdk');
  if(wrap) wrap.addEventListener('mousedown', function(e){ if(e.target===wrap) close(); });
})();
