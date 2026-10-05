/* ═══════════════════════════════════════════════════════════════════════════
   FREEBUFF — VIRAL SUGGESTIONS (the gold/coin page tab)

   The server gates every story through the page's lanes, then ranks what
   passed by *viral potential* — market shock, wallet impact, the retellable
   angle, real social demand, freshness — with every factor kept. This view
   renders those suggestions: which story, how likely to travel, and why.
   Nothing is generated here; the operator picks and writes their own post.
   ═══════════════════════════════════════════════════════════════════════════ */
'use strict';

const Channel = (function () {
  const VIRAL_FACTORS = [
    ['shock', 'شوک بازار'], ['pocket', 'جیب مخاطب'], ['novelty', 'زاویهٔ چشمگیر'],
    ['demand', 'تقاضای اجتماعی'], ['freshness', 'تازگی'],
  ];
  const SORTS = [
    ['viral', 'بیشترین احتمال وایرال'], ['fresh', 'تازه‌ترین'], ['fit', 'بیشترین تناسب با پیج'],
  ];

  const S = {
    feed: null,
    busy: false,
    lane: 'all',       // 'all' | badge label
    sort: 'viral',
    search: '',
  };

  const el = (id) => document.getElementById(id);
  const fa = (n) => (typeof toFa === 'function' ? toFa(n) : String(n));
  /* The page defines a global ``esc``. The local name must not *shadow* it:
     testing ``typeof esc`` from inside a binding called ``esc`` finds this
     helper itself and recurses until the stack dies. Reach for the global
     through ``window`` and keep the fallback under another name. */
  const escFallback = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const esc = (s) => (typeof window.esc === 'function' ? window.esc(s) : escFallback(s));

  function num(v, digits) {
    if (v === null || v === undefined || v === '' || isNaN(Number(v))) return '—';
    const d = digits === undefined ? 1 : digits;
    return fa(Number(v).toLocaleString('en-US',
      { minimumFractionDigits: d, maximumFractionDigits: d }));
  }

  function agoText(hours) {
    const h = Number(hours);
    if (!isFinite(h)) return '—';
    if (h < 1) return fa(Math.round(h * 60)) + ' دقیقه پیش';
    if (h < 48) return fa(Math.round(h)) + ' ساعت پیش';
    return fa(Math.round(h / 24)) + ' روز پیش';
  }

  function bar(label, value) {
    const pct = Math.max(0, Math.min(1, Number(value) || 0)) * 100;
    return '<div class="cb-factor-bar">' +
      '<span class="k">' + esc(label) + '</span>' +
      '<span class="meter"><i style="inline-size:' + pct.toFixed(1) + '%"></i></span>' +
      '<span class="v">' + fa(pct.toFixed(0)) + '٪</span></div>';
  }

  function laneClass(badge) {
    const b = String(badge || '');
    if (b.indexOf('طلا') >= 0) return 'cb-lane-gold';
    if (b.indexOf('داخلی') >= 0) return 'cb-lane-dom';
    if (b.indexOf('جهانی') >= 0) return 'cb-lane-glob';
    return 'cb-lane-fx';
  }

  function laneChips() {
    const feed = S.feed || {};
    const lanes = feed.lanes || {};
    const keys = Object.keys(lanes);
    const chips = ['<button type="button" class="cb-chip' + (S.lane === 'all' ? ' active' : '') +
      '" onclick="Channel.setLane(\'all\')">همه <b>' + fa((feed.items || []).length) + '</b></button>'];
    keys.forEach(function (k) {
      chips.push('<button type="button" class="cb-chip' + (S.lane === k ? ' active' : '') +
        '" onclick="Channel.setLane(' + JSON.stringify(k).replace(/"/g, '&quot;') + ')">' +
        esc(k) + ' <b>' + fa(lanes[k]) + '</b></button>');
    });
    return chips.join('');
  }

  function visible() {
    const items = ((S.feed || {}).items || []).slice();
    const q = S.search.trim().toLowerCase();
    const out = items.filter(function (it) {
      if (S.lane !== 'all' && it.badge !== S.lane) return false;
      if (!q) return true;
      return ((it.title_fa || '') + ' ' + (it.title || '') + ' ' +
              (it.source || '') + ' ' + (it.bucket_label || '')).toLowerCase().indexOf(q) >= 0;
    });
    if (S.sort === 'fresh') {
      out.sort(function (a, b) { return (a.age_hours || 9e9) - (b.age_hours || 9e9); });
    } else if (S.sort === 'fit') {
      out.sort(function (a, b) { return (b.fit || 0) - (a.fit || 0); });
    } /* 'viral' keeps the server's rank order */
    return out;
  }

  function viralBadge(it) {
    const v = Math.max(0, Math.min(100, Number(it.viral) || 0));
    const cls = v >= 65 ? 'hot' : (v >= 45 ? 'warm' : 'cool');
    return '<div class="cb-viral ' + cls + '" title="امتیاز احتمال وایرال">' +
      '<span class="cb-viral-val">' + fa(v.toFixed(0)) + '</span>' +
      '<span class="cb-viral-lbl">احتمال وایرال</span></div>';
  }

  function itemCard(it, rank) {
    const vf = it.viral_factors || {};
    const nums = it.numbers || [];
    const laneCls = laneClass(it.badge);
    const rankCls = rank === 1 ? 'rank-1' : (rank === 2 ? 'rank-2' : (rank === 3 ? 'rank-3' : ''));

    const chips = (it.buckets ? Object.keys(it.buckets) : []).map(function (b) {
      const meta = (((S.feed || {}).profile || {}).buckets || {})[b] || {};
      return '<span class="cb-bkt" title="کلیدواژه: ' + esc((it.buckets[b] || []).join('، ')) + '">' +
        (meta.emoji || '•') + ' ' + esc(meta.label || b) + '</span>';
    }).join('');

    const numberStrip = nums.length
      ? '<div class="cb-numbers">' + nums.slice(0, 8).map(function (n) {
          return '<span class="cb-num">' + fa(n) + '</span>'; }).join('') + '</div>'
      : '';

    const whys = (it.viral_why || []).map(function (w) {
      return '<span class="cb-why-item">' + esc(w) + '</span>';
    }).join('');

    return '<article class="cb-item ' + rankCls + '" data-id="' + esc(it.id || '') + '">' +
      '<div class="cb-item-top">' +
        '<div class="cb-item-head">' +
          '<span class="cb-rank">#' + fa(rank) + '</span>' +
          '<h4>' + esc(it.title_fa || it.title || '') + '</h4>' +
        '</div>' +
        viralBadge(it) +
      '</div>' +

      '<div class="cb-meta">' +
        '<span class="cb-lane ' + laneCls + '">' + (it.emoji || '📊') + ' ' + esc(it.badge || '') + '</span>' +
        '<span class="badge sm">' + esc(it.source || 'منبع اصلی') + '</span>' +
        '<span class="badge sm">⏱️ ' + agoText(it.age_hours) + '</span>' +
        '<span class="badge sm" style="color:var(--cu-txt)">🛡️ ' + fa(Math.round((it.credibility || 0) * 100)) + '٪</span>' +
        '<span class="badge sm">تناسب پیج: ' + fa(Number(it.fit || 0).toFixed(0)) + '</span>' +
        chips +
      '</div>' +

      (whys ? '<div class="cb-why">' + whys + '</div>' : '') +
      numberStrip +
      '<div class="cb-factors">' + VIRAL_FACTORS.map(function (p) { return bar(p[1], vf[p[0]]); }).join('') + '</div>' +

      '<div class="cb-foot">' +
        '<button type="button" class="btn sm ghost" onclick="Channel.openSource(' + jsArg(it.id) + ')">خواندن خبر</button>' +
        (it.link
          ? '<a class="btn sm ghost" href="' + esc(it.link) + '" target="_blank" rel="noopener noreferrer">خبر اصلی ↗</a>'
          : '<span class="cb-nolink">بدون لینک</span>') +
      '</div>' +
    '</article>';
  }

  function renderKPIs() {
    const feed = S.feed || {};
    const items = feed.items || [];
    const rej = feed.rejected || {};

    const set = function (id, v) { const n = el(id); if (n) n.textContent = v; };
    set('cbCount', fa(items.length));
    set('cbCorpus', 'از ' + fa((feed.status || {}).corpus || 0) + ' خبر اسکن شد');
    set('cbTop', items.length ? fa(Number(items[0].viral || 0).toFixed(0)) : '—');
    set('cbTopSub', items.length
      ? 'بالاترین وایرال: ' + esc((items[0].title_fa || items[0].title || '').slice(0, 44))
      : 'خبری متناسب پیدا نشد');
    set('cbRejected', fa((rej.off_profile || 0) + (rej.no_bucket || 0) + (rej.low_credibility || 0)));
    set('cbRejectedSub', fa(rej.off_profile || 0) + ' خارج از موضوع · ' +
                        fa(rej.no_bucket || 0) + ' بی‌ربط · ' +
                        fa(rej.low_credibility || 0) + ' کم‌اعتبار');

    const lanes = el('cbLanes');
    if (lanes) lanes.innerHTML = laneChips();

    const sortSel = el('cbSort');
    if (sortSel && sortSel.value !== S.sort) sortSel.value = S.sort;

    const stamp = el('cbStamp');
    if (stamp && feed.generated_ts) {
      stamp.textContent = 'به‌روزرسانی ' + agoText((Date.now() / 1000 - feed.generated_ts) / 3600);
    }

    /* the rail count, the same way the feed and bookmark tabs do it: the badge
       is hidden while it is zero so the rail does not shout at an empty tab */
    const rail = el('cntChannel');
    if (rail) {
      rail.textContent = fa(items.length);
      rail.style.display = items.length ? '' : 'none';
    }
  }

  function render() {
    const host = el('cbList');
    if (!host) return;
    const list = visible();
    const total = ((S.feed || {}).items || []).length;
    const res = el('cbResults');
    if (res) res.textContent = 'نمایش ' + fa(list.length) + ' پیشنهاد از ' + fa(total);

    if (!list.length) {
      const empty = (S.feed || {}).items || [];
      host.innerHTML = '<div class="cb-empty">' +
        '<div style="font-size:30px;margin-bottom:8px">🔥</div>' +
        '<div style="font-weight:700">' +
          (empty.length ? 'پیشنهادی در این دسته نیست' : 'فعلاً خبری با پتانسیل وایرال برای این پیج نیست') +
        '</div>' +
        '<div style="font-size:12px;color:var(--ink-4);margin-top:6px;line-height:1.9">' +
          (empty.length
            ? 'دستهٔ دیگری را انتخاب کنید یا جستجو را پاک کنید.'
            : 'منابع فعلی بیشتر کریپتو و بازار جهانی می‌دهند؛ افزودن منابع فارسی طلا و ارز در «مدیریت منابع» این تب را پر می‌کند.') +
        '</div></div>';
      return;
    }
    host.innerHTML = list.map(function (it, i) { return itemCard(it, i + 1); }).join('');
  }

  async function load(force) {
    if (S.busy) return;
    S.busy = true;
    const host = el('cbList');
    if (host && !S.feed) host.innerHTML = '<div class="cb-empty"><span class="spinner"></span> در حال غربال اخبار…</div>';
    try {
      const r = await fetch('/api/channel/feed?limit=48' + (force ? '&refresh=1' : ''));
      const j = await r.json();
      if (!j || j.ok === false) throw new Error((j && j.error) || ('HTTP ' + r.status));
      S.feed = j;
      renderKPIs();
      render();
    } catch (e) {
      if (host) host.innerHTML = '<div class="cb-empty">دریافت فهرست ناموفق بود: ' +
        esc(e && e.message || '') + '</div>';
    }
    S.busy = false;
  }

  function setLane(v) { S.lane = v; renderKPIs(); render(); }
  function setSort(v) { S.sort = v || 'viral'; render(); }
  function setSearch(v) { S.search = v || ''; render(); }

  function openSource(id) {
    if (typeof openArticle === 'function') openArticle(id);
    else if (typeof toast === 'function') toast('خوانندهٔ خبر در این نسخه در دسترس نیست.');
  }

  async function mount() {
    if (!S.feed) await load(false);
    else { renderKPIs(); render(); }
  }

  async function refresh() {
    if (typeof toast === 'function') toast('در حال غربال دوبارهٔ اخبار…');
    S.feed = null;
    await load(true);
  }

  return {
    mount: mount, refresh: refresh, setLane: setLane, setSort: setSort,
    setSearch: setSearch, openSource: openSource, _s: S,
  };
})();
window.Channel = Channel;
