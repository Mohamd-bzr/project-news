/* ═══════════════════════════════════════════════════════════════════════════
   FREEBUFF — MERGED SUGGESTIONS TAB (was: content studio + channel board)

   One view, one job: show the news the engine picked for the page. No factor
   bars, no scores, no explanation chrome — title, summary, source, time,
   original link. The ranking lives entirely on the server (channel_profile).
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

  function agoText(hours) {
    const h = Number(hours);
    if (!isFinite(h)) return '—';
    if (h < 1) return fa(Math.round(h * 60)) + ' دقیقه پیش';
    if (h < 48) return fa(Math.round(h)) + ' ساعت پیش';
    return fa(Math.round(h / 24)) + ' روز پیش';
  }

  function itemCard(it) {
    const title = it.title_fa || it.title || '';
    const summary = (it.summary_fa || '').trim();
    const open = it.id ? ' onclick="Channel.openSource(' + jsArg(it.id) + ')"' : '';
    return '<article class="cb-item" data-id="' + esc(it.id || '') + '">' +
      '<h4 class="cb-title" style="cursor:pointer"' + open + '>' + esc(title) + '</h4>' +
      (summary ? '<p class="cb-sum">' + esc(summary) + '</p>' : '') +
      '<div class="cb-meta" style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">' +
        '<span class="badge sm">' + esc(it.source || 'منبع اصلی') + '</span>' +
        '<span class="badge sm">⏱️ ' + agoText(it.age_hours) + '</span>' +
        (it.link
          ? '<a class="btn sm ghost" href="' + esc(it.link) + '" target="_blank" rel="noopener noreferrer">خبر اصلی ↗</a>'
          : '') +
      '</div>' +
    '</article>';
  }

  function render() {
    const host = el('cbList');
    if (!host) return;
    const items = (S.feed || {}).items || [];

    /* the rail badge, the same way the feed tab does it */
    const rail = el('cntChannel');
    if (rail) {
      rail.textContent = fa(items.length);
      rail.style.display = items.length ? '' : 'none';
    }

    if (!items.length) {
      host.innerHTML = '<div class="cb-empty">فعلاً خبری برای نشان دادن نیست.</div>';
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

  function openSource(id) {
    if (typeof openArticle === 'function') openArticle(id);
  }

  return { mount: mount, load: load, openSource: openSource, _s: S };
})();
window.Channel = Channel;
