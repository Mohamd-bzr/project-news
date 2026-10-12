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
    const safeTitle = esc(p.title || '(بدون تیتر)');
    const safeUrl = esc(p.url);
    const safeHandle = esc(src.handle);
    const safeText = esc(text);

    return '<article class="ncard" data-id="' + esc(src.handle + '/' + p.id) + '">' +
      '<div class="body">' +
        '<div class="row1">' +
          '<span class="badge b-asset">@' + safeHandle + '</span>' +
          (p.media ? '<span class="badge b-viral">📎 ' + esc(p.media) + '</span>' : '') +
          '<span class="badge b-pending" id="st-' + esc(p.id) + '" style="display:none"></span>' +
        '</div>' +
        '<div class="ttl">' + safeTitle + '</div>' +
        (text ? '<div class="summ">' + safeText + (p.text && p.text.length > 420 ? '…' : '') + '</div>' : '') +
        '<div class="row2">' +
          '<span class="src">' + esc(src.title || src.handle) + '</span>' +
          '<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">' +
            '<button class="b-card-act" type="button" data-act="send-bale" title="ارسال به پیام‌رسان بله (بدون ذکر منبع و لینک)">📤 بله</button>' +
            '<button class="b-card-act" type="button" data-act="send-tg" title="ارسال به پیام‌رسان تلگرام (بدون ذکر منبع و لینک)">📤 تلگرام</button>' +
            '<a class="b-card-act link" href="' + safeUrl + '" target="_blank" rel="noopener" title="مشاهدهٔ پست در تلگرام">🔗 پست</a>' +
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
      host.innerHTML = '<div class="cb-empty">کانالی تنظیم نشده است — از دکمه «افزودن کانال» یک کانال اضافه کنید.</div>';
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

    // Bind send action buttons
    host.querySelectorAll('article.ncard').forEach(art => {
      const id = art.getAttribute('data-id');
      const slash = (id || '').indexOf('/');
      if (slash < 0) return;
      const handle = id.slice(0, slash);
      const postId = id.slice(slash + 1);
      const src = sources.find(s => s.handle === handle);
      const post = src ? (src.posts || []).find(p => String(p.id) === postId) : null;
      if (!post) return;

      const btnBale = art.querySelector('[data-act="send-bale"]');
      if (btnBale) {
        btnBale.addEventListener('click', (e) => {
          e.stopPropagation();
          sendPost(post, 'bale', btnBale);
        });
      }
      const btnTg = art.querySelector('[data-act="send-tg"]');
      if (btnTg) {
        btnTg.addEventListener('click', (e) => {
          e.stopPropagation();
          sendPost(post, 'telegram', btnTg);
        });
      }
    });
  }

  async function sendPost(post, platform, btn) {
    const notify = (msg) => { if (typeof toast === 'function') toast(msg); };
    const pName = platform === 'telegram' ? 'تلگرام' : 'بله';
    const oldHtml = btn ? btn.innerHTML : '';
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner sm"></span>';
    }
    try {
      notify('در حال ارسال خبر به ' + pName + ' (بدون ذکر سورس و لینک)...');
      const r = await fetch('/api/telegram_news/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: post.title || '',
          text: post.text || '',
          platform: platform
        })
      });
      const j = await r.json();
      if (j && j.ok) {
        notify('✅ خبر با موفقیت به ' + pName + ' ارسال شد');
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = '✓ ارسال شد';
          btn.classList.add('sent');
        }
      } else {
        notify('❌ ارسال ناموفق: ' + ((j && j.error) || 'خطا در ارتباط'));
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = oldHtml;
        }
      }
    } catch (e) {
      notify('❌ خطای ارتباط: ' + e.message);
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = oldHtml;
      }
    }
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
    mount: function () { if (!S.data) load(false); else render(); },
    refresh: function () { load(true); },
    pick: function (handle) {
      S.picked = (S.picked === handle) ? null : handle;
      render();
    },
    toggleAddBox: function () {
      const box = el('tgNewsAddBox');
      if (box) box.style.display = box.style.display === 'none' ? 'block' : 'none';
    },
    testChannel: async function () {
      const inp = el('inpTgChannelHandle');
      const res = el('tgChannelTestResult');
      const handle = (inp ? inp.value : '').trim().replace(/^@/, '');
      if (!handle) {
        if (typeof toast === 'function') toast('ابتدا آیدی کانال را وارد کنید');
        return;
      }
      if (res) {
        res.style.display = 'block';
        res.innerHTML = '<span class="spinner sm"></span> در حال بررسی ارتباط با کانال @' + esc(handle) + '...';
      }
      try {
        const r = await fetch('/api/telegram_news/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ handle: handle })
        });
        const j = await r.json();
        if (res) {
          if (j && j.ok) {
            res.innerHTML = '<span style="color:var(--up);">✅ کانال «' + esc(j.title || handle) + '» عمومی است و ' + fa(j.count) + ' پست با موفقیت دریافت شد.</span>';
          } else {
            res.innerHTML = '<span style="color:var(--dn);">❌ خطا: ' + esc((j && j.error) || 'کانال در دسترس نیست') + '</span>';
          }
        }
      } catch (e) {
        if (res) res.innerHTML = '<span style="color:var(--dn);">❌ خطای اتصال به سرور: ' + esc(e.message) + '</span>';
      }
    },
    saveChannel: async function () {
      const inpH = el('inpTgChannelHandle');
      const inpT = el('inpTgChannelTitle');
      const handle = (inpH ? inpH.value : '').trim().replace(/^@/, '');
      const title = (inpT ? inpT.value : '').trim();
      if (!handle) {
        if (typeof toast === 'function') toast('آیدی کانال را وارد کنید');
        return;
      }
      try {
        const r = await fetch('/api/telegram_news/sources', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ handle: handle, title: title })
        });
        const j = await r.json();
        if (j && j.ok) {
          if (typeof toast === 'function') toast('✅ کانال با موفقیت افزوده شد');
          if (inpH) inpH.value = '';
          if (inpT) inpT.value = '';
          const res = el('tgChannelTestResult');
          if (res) res.style.display = 'none';
          const box = el('tgNewsAddBox');
          if (box) box.style.display = 'none';
          load(true);
        } else {
          if (typeof toast === 'function') toast('❌ خطا: ' + ((j && j.error) || 'افزودن ناموفق بود'));
        }
      } catch (e) {
        if (typeof toast === 'function') toast('❌ خطای ارتباط: ' + e.message);
      }
    }
  };
})();

window.TgNews = TgNews;
