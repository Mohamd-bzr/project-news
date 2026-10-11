/* ═══════════════════════════════════════════════════════════════════════════
   MOHMD NEWS — «اخبار تلگرامی» (public Telegram channels, read-only)

   The client half of the board that lists the newest posts of the channels in
   telegram_news.SOURCES. The server does the fetching and the parsing; this
   file only draws what /api/telegram_news answers and lets the operator pick a
   channel or force a refresh. Nothing here posts to Telegram.

   Same contract as web/channel.js: reach the global esc/toFa through window,
   escape every string that came off the network, and show a missing number as
   «—» instead of guessing one.
   ═══════════════════════════════════════════════════════════════════════════ */
'use strict';

const TgNews = (function () {
  const S = { data: null, busy: false, picked: null };

  const el = (id) => document.getElementById(id);
  const fa = (n) => (typeof toFa === 'function' ? toFa(n) : String(n));
  /* Reach the global ``esc`` through ``window`` — a local binding named ``esc``
     would shadow it and recurse until the stack dies. */
  const escFallback = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const esc = (s) => (typeof window.esc === 'function' ? window.esc(s) : escFallback(s));

  /* ISO → «۱۴۰۴/۰۷/۲۰ — ۱۲:۳۷» ; an empty timestamp is an explicit gap. */
  function faWhen(iso) {
    const t = String(iso || '').replace('T', ' ').slice(0, 16);
    return t ? fa(t) : '—';
  }

  function faViews(v) {
    return (v == null ? '—' : fa(v)) + ' بازدید';
  }

  function postCard(p, src) {
    const text = String(p.text || '').slice(0, 420);
    return '<article class="ncard" data-id="' + esc(src.handle + '/' + p.id) + '">' +
      '<div class="body">' +
        '<div class="row1">' +
          '<span class="badge b-asset">@' + esc(src.handle) + '</span>' +
          (p.media ? '<span class="badge b-viral">📎 ' + esc(p.media) + '</span>' : '') +
        '</div>' +
        '<div class="ttl">' + esc(p.title || '(بدون تیتر)') + '</div>' +
        (text ? '<div class="summ">' + esc(text) + (p.text && p.text.length > 420 ? '…' : '') + '</div>' : '') +
        '<div class="row2">' +
          '<span class="src">' + esc(src.title || src.handle) + '</span>' +
          '<div style="display:flex;align-items:center;gap:6px;">' +
            '<a class="b-card-act link" href="' + esc(p.url) + '" target="_blank" rel="noopener" title="مشاهدهٔ پست در تلگرام">🔗 پست</a>' +
            '<span class="dt">' + faWhen(p.time) + '</span>' +
          '</div>' +
        '</div>' +
        '<div class="rank">' + faViews(p.views) + '</div>' +
      '</div>' +
    '</article>';
  }

  function renderChips() {
    const host = el('tgNewsChips');
    if (!host) return;
    const sources = (S.data || {}).sources || [];
    host.innerHTML = sources.map(s =>
      '<button class="chip' + (S.picked === s.handle ? ' on' : '') + '" type="button" ' +
      'onclick="TgNews.pick(\'' + esc(s.handle) + '\')" ' +
      'title="' + esc(s.url) + '">@' + esc(s.handle) +
      ' <span class="n">' + fa((s.posts || []).length) + '</span></button>').join('');
  }

  function render() {
    const host = el('tgNewsList');
    if (!host) return;
    const sources = (S.data || {}).sources || [];
    const rail = el('cntTgNews');
    if (rail) {
      const total = sources.reduce((n, s) => n + (s.posts || []).length, 0);
      rail.textContent = fa(total);
      rail.style.display = total ? '' : 'none';
    }
    const count = el('tgNewsCount');
    if (count) count.textContent = fa(sources.length) + ' کانال';

    renderChips();

    if (!sources.length) {
      host.innerHTML = '<div class="cb-empty">کانالی تنظیم نشده است — برای افزودن، یک خط به SOURCES در telegram_news.py اضافه کن.</div>';
      return;
    }
    const shown = S.picked
      ? sources.filter(s => s.handle === S.picked)
      : sources;

    const cards = [];
    shown.forEach(s => {
      if (s.ok === false) {
        cards.push('<div class="cb-empty">@' + esc(s.handle) + ' جواب نداد: ' + esc(s.error || 'خطای ناشناخته') + '</div>');
        return;
      }
      (s.posts || []).forEach(p => cards.push(postCard(p, s)));
    });
    host.innerHTML = cards.length
      ? cards.join('')
      : '<div class="cb-empty">پستی برای نمایش نیست.</div>';
  }

  async function load(force) {
    if (S.busy) return;
    S.busy = true;
    const host = el('tgNewsList');
    try {
      const r = await fetch('/api/telegram_news' + (force ? '?refresh=1' : ''));
      const j = await r.json();
      if (!j || j.ok === false) throw new Error((j && j.error) || ('HTTP ' + r.status));
      S.data = j;
      render();
    } catch (e) {
      console.error('TgNews.load:', e);
      if (host) host.innerHTML = '<div class="cb-empty">دریافت پست‌ها ممکن نشد — ' + esc(e.message || e) + '</div>';
    } finally {
      S.busy = false;
    }
  }

  return {
    /* called by showView('tgnews') — fetch once, then just re-render */
    mount: function () { if (!S.data) load(false); else render(); },
    refresh: function () { load(true); },
    pick: function (handle) {
      S.picked = (S.picked === handle) ? null : handle;   /* second tap = all */
      render();
    },
  };
})();

window.TgNews = TgNews;
