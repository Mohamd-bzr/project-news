# -*- coding: utf-8 -*-
"""One-shot patch: the economic-calendar view reads in English (the event
explainer modal stays Persian). Run once, then delete nothing — it is idempotent
because every pair is asserted to appear exactly once."""
import io, sys

P = 'dashboard_html.py'
src = io.open(P, encoding='utf-8', newline='').read()

def R(s):
    return s.replace('\n', '\r\n')

pairs = []

pairs.append((R("""function faDayBox(isoDay){
  /* «یکشنبه ۲۷ سپتامبر» — Persian weekday and Persian month name over the
     Gregorian date the release data actually carries (fa-IR-u-ca-gregory),
     because an economic calendar is read against the Western release week. */
  try{
    const d=new Date(isoDay+'T12:00:00Z');
    return esc(d.toLocaleDateString('fa-IR-u-ca-gregory',{weekday:'long',month:'short',day:'numeric',timeZone:'UTC'}));
  }catch(e){ return esc(isoDay); }
}"""), R("""function faDayBox(isoDay){
  /* the economic calendar reads in English, over the Western release week */
  try{
    const d=new Date(isoDay+'T12:00:00Z');
    return esc(d.toLocaleDateString('en-GB',{weekday:'long',month:'short',day:'numeric',timeZone:'UTC'}));
  }catch(e){ return esc(isoDay); }
}""")))

pairs.append((R("""function shortDay(isoDay){
  /* one Persian weekday letter + the day number, the way an Iranian calendar
     app labels a date cell (ی ۲۷) — used by the day strip and the glance table */
  const d=new Date(isoDay+'T12:00:00Z');
  let dow='';
  try{ dow=d.toLocaleDateString('fa-IR-u-ca-gregory',{weekday:'narrow',timeZone:'UTC'}); }catch(e){ dow=''; }
  return {dow:dow, num:toFa(d.getUTCDate())};
}"""), R("""function shortDay(isoDay){
  /* day-strip cell: one weekday letter over the day number (M 21) */
  const d=new Date(isoDay+'T12:00:00Z');
  let dow='';
  try{ dow=d.toLocaleDateString('en-GB',{weekday:'narrow',timeZone:'UTC'}); }catch(e){ dow=''; }
  return {dow:dow, num:String(d.getUTCDate())};
}""")))

pairs.append((R("""function calCountdown(ts, withSeconds){
  /* a countdown reads as a sentence in Persian, never as "1d 21h 51m" */
  let s=Math.round(ts-Date.now()/1000);
  if(s<0) s=0;
  const d=Math.floor(s/86400); s%=86400;
  const h=Math.floor(s/3600); s%=3600;
  const m=Math.floor(s/60), sec=s%60;
  if(d) return `${toFa(d)} روز و ${toFa(h)} ساعت`;
  if(h) return `${toFa(h)} ساعت و ${toFa(m)} دقیقه`;
  if(withSeconds) return `${toFa(m)} دقیقه و ${toFa(sec)} ثانیه`;
  return `${toFa(m)} دقیقه`;
}"""), R("""function calCountdown(ts, withSeconds){
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
}""")))

pairs.append((R("""    if(kind==='dow')  f=new Intl.DateTimeFormat('fa-IR-u-ca-gregory',{timeZone:zone,weekday:'short'});
    if(kind==='full') f=new Intl.DateTimeFormat('fa-IR-u-ca-gregory',{timeZone:zone,weekday:'short',month:'short',day:'numeric'});"""),
              R("""    if(kind==='dow')  f=new Intl.DateTimeFormat('en-GB',{timeZone:zone,weekday:'short'});
    if(kind==='full') f=new Intl.DateTimeFormat('en-GB',{timeZone:zone,weekday:'short',month:'short',day:'numeric'});""")))

pairs.append((R("""  if(src) src.textContent='منبع: '+((ECON.calendar&&ECON.calendar.source)||'—')+
    ' · زمان‌ها به وقت '+tz;"""),
              R("""  if(src) src.textContent='Source: '+((ECON.calendar&&ECON.calendar.source)||'—')+
    ' · times in '+tz;""")))

# ── table header, day header, empty states, row labels ──────────────────────
pairs.append((R("""  const head='<div class="cal-th">'+
    '<span>زمان</span><span>ارز</span><span>اهمیت</span><span>رویداد</span>'+
    '<span style="text-align:end">واقعی</span><span style="text-align:end">پیش‌بینی</span>'+
    '<span style="text-align:end">قبلی</span><span></span></div>';"""),
              R("""  const head='<div class="cal-th">'+
    '<span>Time</span><span>Ccy</span><span>Impact</span><span>Event</span>'+
    '<span style="text-align:end">Actual</span><span style="text-align:end">Forecast</span>'+
    '<span style="text-align:end">Previous</span><span></span></div>';""")))

pairs.append((R("""      <span class="c-time">${e.all_day?'تمام روز':esc(tzClock(e.ts))}<small>${esc(e.all_day?'':tzDow(e.ts))}</small></span>"""),
              R("""      <span class="c-time">${e.all_day?'All day':esc(tzClock(e.ts))}<small>${esc(e.all_day?'':tzDow(e.ts))}</small></span>""")))

pairs.append((R("""<span class="c-imp" title="اهمیت ${esc(CAL_IMP_LABEL[e.impact]||e.impact)}">"""),
              R("""<span class="c-imp" title="Impact ${esc(CAL_IMP_LABEL[e.impact]||e.impact)}">""")))

pairs.append((R("""      <button class="cal-info" onclick="openCalDoc(${e._idx})" title="این رویداد چیست و بازار چطور معامله‌اش می‌کند؟"><svg class="ic"><use href="#i-info"/></svg> توضیح</button>"""),
              R("""      <button class="cal-info" onclick="openCalDoc(${e._idx})" title="What this release is — explained in Persian"><svg class="ic"><use href="#i-info"/></svg> توضیح</button>""")))

pairs.append((R("""    box.innerHTML='<div class="empty">فید تقویم همین حالا در دسترس نیست — یک دقیقهٔ دیگر دوباره تلاش کن.</div>';"""),
              R("""    box.innerHTML='<div class="empty">Calendar feed unavailable right now — try again in a minute.</div>';""")))

pairs.append((R("""    box.innerHTML=`<div class="cal-board-h"><span class="d">${faDayBox(selDay)}</span>`+
      `<span class="cal-tz-chip">${esc(tz)}</span>`+
      `<span class="m">${toFa(0)} رویداد</span></div><div class="empty">`+
      (inWindow?'رویدادی با این فیلترها در این روز نیست.'
               :'برای این هفته داده‌ای بارگذاری نشده — این داشبورد هفتهٔ جاری و هفتهٔ بعد را نگه می‌دارد.')+
      `<br><button class="btn ghost sm" style="margin-block-start:14px" onclick="jumpToNextEventDay()">پرش به نزدیک‌ترین روز دارای رویداد ›</button></div>`;"""),
              R("""    box.innerHTML=`<div class="cal-board-h"><span class="d">${faDayBox(selDay)}</span>`+
      `<span class="cal-tz-chip">${esc(tz)}</span>`+
      `<span class="m">0 events</span></div><div class="empty">`+
      (inWindow?'No event on this day with these filters.'
               :'No data loaded for this week — the dashboard keeps the current week and the next.')+
      `<br><button class="btn ghost sm" style="margin-block-start:14px" onclick="jumpToNextEventDay()">Jump to the nearest day with events ›</button></div>`;""")))

pairs.append((R("""        <span class="m">${toFa(evs.length)} رویداد · ${toFa(relDay)} منتشرشده${hiDay?` · ${toFa(hiDay)} پراثر`:''}</span>"""),
              R("""        <span class="m">${evs.length} events · ${relDay} released${hiDay?` · ${hiDay} high impact`:''}</span>""")))

# ── hero ticker text ────────────────────────────────────────────────────────
pairs.append((R("""    if(!next){ cd.textContent='در بازهٔ بارگذاری‌شده رویدادی پیشِ‌رو نیست'; if(tt) tt.textContent='—'; if(rel) rel.style.display='none'; return; }"""),
              R("""    if(!next){ cd.textContent='No upcoming event in the loaded window'; if(tt) tt.textContent='—'; if(rel) rel.style.display='none'; return; }""")))

pairs.append((R("""    if(tt) tt.innerHTML=`<span class="ccy">${esc(next.country||'')}</span><span class="imp">اهمیت ${esc(CAL_IMP_LABEL[next.impact]||next.impact)}</span>${esc(next.title)}`;"""),
              R("""    if(tt) tt.innerHTML=`<span class="ccy">${esc(next.country||'')}</span><span class="imp">Impact ${esc(CAL_IMP_LABEL[next.impact]||next.impact)}</span>${esc(next.title)}`;""")))

pairs.append((R("""        rel.innerHTML=`<span><svg class="ic"><use href="#i-check"/></svg></span> همین حالا منتشر شد: <b>${esc(relRow.title)}</b> `+
          (relRow.actual_fmt?`<span style="direction:ltr">واقعی <b>${esc(relRow.actual_fmt)}</b> در برابر پیش‌بینی ${esc(relRow.forecast_fmt)}</span>`:'')+"""),
              R("""        rel.innerHTML=`<span><svg class="ic"><use href="#i-check"/></svg></span> Just released: <b>${esc(relRow.title)}</b> `+
          (relRow.actual_fmt?`<span style="direction:ltr">actual <b>${esc(relRow.actual_fmt)}</b> vs forecast ${esc(relRow.forecast_fmt)}</span>`:'')+""")))

pairs.append((R("""      cd.innerHTML=after?('رویداد پراثر بعدی تا <b>'+calCountdown(after.ts,false)+'</b> دیگر — '+esc(after.title))
                        :'رویداد پراثر دیگری در بازهٔ بارگذاری‌شده نمانده';"""),
              R("""      cd.innerHTML=after?('Next high impact in <b>'+calCountdown(after.ts,false)+'</b> — '+esc(after.title))
                        :'No further high-impact event in the loaded window';""")))

pairs.append((R("""    const when=tzDay(next.ts)===tzNow()?'امروز':faDayBox(tzDay(next.ts));   /* tzDay stays ISO: it is the bucket key */
    cd.innerHTML=`تا <b>${calCountdown(next.ts,true)}</b> دیگر · ${esc(tzClock(next.ts))} ${esc(tz)} · ${esc(when)}`;"""),
              R("""    const when=tzDay(next.ts)===tzNow()?'today':faDayBox(tzDay(next.ts));   /* tzDay stays ISO: it is the bucket key */
    cd.innerHTML=`in <b>${calCountdown(next.ts,true)}</b> · ${esc(tzClock(next.ts))} ${esc(tz)} · ${esc(when)}`;""")))

# ── week counters ───────────────────────────────────────────────────────────
pairs.append((R("""    st.innerHTML=[[wk.length,'رویداد', ''],[wkHi,'پراثر','hi'],[wkRel,'منتشرشده','rel'],
                  [surplus,'بهتر از پیش‌بینی','rel'],[shortf,'بدتر از پیش‌بینی','hi']]
      .map(x=>`<span class="cal-stat ${x[2]}"><b>${toFa(x[0])}</b><span>${x[1]}</span></span>`).join('');"""),
              R("""    st.innerHTML=[[wk.length,'events', ''],[wkHi,'high','hi'],[wkRel,'released','rel'],
                  [surplus,'beat','rel'],[shortf,'missed','hi']]
      .map(x=>`<span class="cal-stat ${x[2]}"><b>${x[0]}</b><span>${x[1]}</span></span>`).join('');""")))

# ── sessions rail: English ─────────────────────────────────────────────────
pairs.append((R("""  if(!ss.length){ box.innerHTML='<span class="hint">سشن‌ها موقتاً در دسترس نیستند.</span>'; return; }
  box.innerHTML=ss.map(s=>{
    const st=s.open?'باز':'بسته';
    const h=Math.floor(s.mins_to_change/60), m=s.mins_to_change%60;
    const to=(s.open?'بستن در ':'بازشدن در ')+toFa(h)+' ساعت و '+toFa(String(m).padStart(2,'0'))+' دقیقه';"""),
              R("""  if(!ss.length){ box.innerHTML='<span class="hint">Sessions unavailable right now.</span>'; return; }
  box.innerHTML=ss.map(s=>{
    const st=s.open?'Open':'Closed';
    const h=Math.floor(s.mins_to_change/60), m=s.mins_to_change%60;
    const to=(s.open?'closes in ':'opens in ')+h+'h '+String(m).padStart(2,'0')+'m';""")))

pairs.append((R("""  +`<div class="hint" style="margin-block-start:8px">برنامهٔ هفتگی به وقت UTC — ساعت زنده هر دقیقه به‌روز می‌شود.</div>`;"""),
              R("""  +`<div class="hint" style="margin-block-start:8px">Weekly schedule, times in UTC — the clock refreshes every minute.</div>`;""")))

# ── remove the week-at-a-glance panel and its renderer ─────────────────────
pairs.append((R("""  renderCalGlance(pool,week,today);
  renderCalHigh(upcoming);"""),
              R("""  renderCalHigh(pool, selDay);""")))

pairs.append((R("""/* week-at-a-glance: how loaded each day is, and where the red flags sit */
function renderCalGlance(pool,week,today){
  const box=document.getElementById('calGlance'); if(!box) return;
  const counts=week.map(d=>({d:d, n:pool.filter(e=>e._day===d).length,
                            hi:pool.filter(e=>e._day===d&&e.impact==='High').length}));
  const max=Math.max(1,...counts.map(c=>c.n));
  box.innerHTML=counts.map(function(c){
    const s=shortDay(c.d);
    return `<div class="cal-glance-row" onclick="CAL.day='${c.d}';renderCalendar()" role="button" tabindex="0">
      <span class="d">${s.dow} ${s.num}${c.d===today?' · امروز':''}</span>
      <span class="bar"><i style="width:${Math.round(c.n/max*100)}%"></i></span>
      <span class="n">${toFa(c.n)}${c.hi?` · ${toFa(c.hi)} پراثر`:''}</span></div>`;
  }).join('')+
  `<div class="hint" style="margin-block-start:8px">برای دیدن آن روز روی ردیف بزن.</div>`;
}

/* the next handful of high-impact releases, each with a live countdown, so the
   tab answers "what is coming?" without hunting through days */
function renderCalHigh(upcoming){
  const box=document.getElementById('calHighList'); if(!box) return;
  const hi=upcoming.filter(e=>e.impact==='High').slice(0,6);
  if(!hi.length){ box.innerHTML='<span class="hint">رویداد پراثری در بازهٔ بارگذاری‌شده نمانده.</span>'; return; }"""),
              R("""/* the high-impact releases OF THE DAY ON THE BOARD — not a second, longer list
   answering a different question. Same day as the table above it. */
function renderCalHigh(pool, day){
  const box=document.getElementById('calHighList'); if(!box) return;
  const lab=document.getElementById('calHighDay');
  if(lab) lab.textContent=faDayBox(day);
  const hi=pool.filter(e=>e._day===day&&e.impact==='High').sort((a,b)=>a.ts-b.ts);
  if(!hi.length){ box.innerHTML='<span class="hint">No high-impact release on this day.</span>'; return; }""")))

pairs.append((R("""      <div class="meta"><b class="js-cal-cd" data-ts="${e.ts}">${calCountdown(e.ts,false)}</b>
        <span>${esc(tzDayFa(e.ts))} · ${esc(tzClock(e.ts))}</span>
        <span>${esc(e.country||'')}</span></div>"""),
              R("""      <div class="meta"><b class="js-cal-cd" data-ts="${e.ts}">${e._released?'released':calCountdown(e.ts,false)}</b>
        <span>${esc(tzClock(e.ts))} ${esc(calTz())}</span>
        <span>${esc(e.country||'')}</span></div>""")))

# ── filter toolbar chip + reset toast ──────────────────────────────────────
pairs.append((R("""  if(hp&&hp.checked) items.push([ic('eye-off')+' پنهان‌کردن منتشرشده‌ها', 'setCalHidePast(false)']);"""),
              R("""  if(hp&&hp.checked) items.push([ic('eye-off')+' released hidden', 'setCalHidePast(false)']);""")))

pairs.append((R("""  if(typeof toast==='function') toast('فیلترهای تقویم پاک شد');"""),
              R("""  if(typeof toast==='function') toast('Calendar filters cleared');""")))

# ── explainer modal keeps Persian labels even though the board is English ──
pairs.append((R("""      <span class="cal-doc-chip"><i class="imp-dot ${impClass(e.impact)}"></i> اهمیت ${esc(CAL_IMP_LABEL[e.impact]||e.impact)}</span>"""),
              R("""      <span class="cal-doc-chip"><i class="imp-dot ${impClass(e.impact)}"></i> اهمیت ${esc(CAL_IMP_FA[e.impact]||e.impact)}</span>""")))

pairs.append((R("""      ${e.impact?`<span class="cal-doc-chip imp is-${impClass(e.impact)}">اهمیت ${esc(CAL_IMP_LABEL[e.impact]||'')}</span>`:''}"""),
              R("""      ${e.impact?`<span class="cal-doc-chip imp is-${impClass(e.impact)}">اهمیت ${esc(CAL_IMP_FA[e.impact]||'')}</span>`:''}""")))

bad = 0
for old, new in pairs:
    n = src.count(old)
    if n != 1:
        print('!! %d occurrences -> %s' % (n, old.split('\r\n')[0][:80]))
        bad += 1
        continue
    src = src.replace(old, new)

io.open(P, 'w', encoding='utf-8', newline='').write(src)
print('applied', len(pairs) - bad, '/', len(pairs))
sys.exit(1 if bad else 0)
