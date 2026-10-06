/* ═══════════════════════════════════════════════════════════════════════════
   FREEBUFF — «ایده‌های محتوا» (merged tab; was: content studio + channel)

   The board re-uses the news feed's own card (.ncard) and its badge tags, so
   both surfaces read as one product: text-only cards, the virality
   probability chip and the lane tag on every card. The ranking internals
   never reach this file (the API ships display fields alone).
   ═══════════════════════════════════════════════════════════════════════════ */
'use strict';

const Channel = (function () {
  const S = { feed: null, fetchedAt: 0, busy: false };

  const el = (id) => document.getElementById(id);
  const fa = (n) => (typeof toFa === 'function' ? toFa(n) : String(n));
  /* Reach for the global ``esc`` through ``window`` — a local binding named
     ``esc`` would shadow it and recurse until the stack dies. */
  const escFallback = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const esc = (s) => (typeof window.esc === 'function' ? window.esc(s) : escFallback(s));

  /* the feed's badge tags: bucket -> (emoji, label) */
  const TAGS = {
    gold: ['🟡', 'طلا'], coin: ['🪙', 'سکه'], currency: ['💵', 'ارز'],
    global: ['🌍', 'جهانی'], crypto: ['₿', 'کریپتو'],
  };

  function agoText(hours) {
    const h = Number(hours);
    if (!isFinite(h)) return '—';
    if (h < 1) return fa(Math.round(h * 60)) + ' دقیقه پیش';
    if (h < 48) return fa(Math.round(h)) + ' ساعت پیش';
    return fa(Math.round(h / 24)) + ' روز پیش';
  }

  function itemCard(it, i) {
    const title = it.title_fa || it.title || '';
    const summary = (it.summary_fa || it.summary || '').trim();
    const lane = esc(it.primary_bucket || 'global');
    /* mono rank takes Latin digits: IBM Plex Mono has no Persian set */
    const rank = String(i + 1).padStart(2, '0');
    const tag = TAGS[it.primary_bucket] || ['', it.bucket_label || 'ایده'];
    const open = it.id ? ' onclick="Channel.openSource(' + jsArg(it.id) + ')"' : '';
    const v = Math.max(0, Math.min(100, Number(it.viral) || 0));
    const vcls = v >= 65 ? 'hot' : (v >= 45 ? 'warm' : 'cool');

    return '<article class="ncard" data-lane="' + lane + '" data-id="' +
      esc(it.id || '') + '"' + open + '>' +
      '<div class="body">' +
        '<div class="row1">' +
          '<span class="badge b-viral ' + vcls + '" title="احتمال وایرال">🔥 ' + fa(v.toFixed(0)) + '٪</span>' +
          '<span class="badge b-asset">' + esc(tag[0]) + ' ' + esc(tag[1]) + '</span>' +
        '</div>' +
        '<div class="ttl">' + esc(title) + '</div>' +
        (summary ? '<div class="summ">' + esc(summary) + '</div>' : '') +
        '<div class="row2">' +
          '<span class="src">' + esc(it.source || 'منبع اصلی') + '</span>' +
          '<span class="dt">' + agoText(it.age_hours) + '</span>' +
          '<span class="rank" aria-hidden="true">' + rank + '</span>' +
        '</div>' +
      '</div>' +
    '</article>';
  }

  function render() {
    const host = el('cbList');
    if (!host) return;
    const items = (S.feed || {}).items || [];

    const rail = el('cntChannel');
    if (rail) {
      rail.textContent = fa(items.length);
      rail.style.display = items.length ? '' : 'none';
    }
    const count = el('cbCount');
    if (count) count.textContent = fa(items.length) + ' ایده';

    if (!items.length) {
      host.innerHTML = '<div class="cb-empty">فعلاً ایده‌ای برای نشان دادن نیست — بعد از چرخهٔ بعدی خبرها دوباره بررسی می‌شود.</div>';
      return;
    }
    host.innerHTML = items.map(itemCard).join('');
  }

  async function load(force) {
    if (S.busy) return;
    S.busy = true;
    try {
      const r = await fetch('/api/channel/feed?limit=48' + (force ? '&refresh=1' : ''));
      const j = await r.json();
      if (!j || j.ok === false) throw new Error((j && j.error) || ('HTTP ' + r.status));
      S.feed = j;
      S.fetchedAt = Date.now();
      render();
    } catch (e) {
      const host = el('cbList');
      if (host) host.innerHTML = '<div class="cb-empty">دریافت خبرها ناموفق بود: ' +
        esc(e && e.message || '') + '</div>';
    }
    S.busy = false;
  }

  /* every visit to the tab refetches if the last fetch is older than a minute */
  async function mount() {
    if (!S.feed || (Date.now() - S.fetchedAt) > 60000) await load(false);
    else render();
  }

  async function refresh() {
    await load(true);
  }

  function openSource(id) {
    if (typeof openArticle === 'function') openArticle(id);
  }

  return { mount: mount, refresh: refresh, openSource: openSource, _s: S };
})();
window.Channel = Channel;
