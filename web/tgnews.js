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
  const S = { data: null, busy: false, picked: { telegram: null, bale: null } };

  const el = (id) => document.getElementById(id);
  const fa = (n) => (typeof toFa === 'function' ? toFa(n) : String(n));
  /* Reach the global ``esc`` through ``window`` — a local binding named ``esc``
     would shadow it and recurse until the stack dies. */
  const escFallback = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const esc = (s) => (typeof window.esc === 'function' ? window.esc(s) : escFallback(s));
  const attr = (s) => (typeof window.attr === 'function' ? window.attr(s) : esc(s));
  const jsArg = (v) => (typeof window.jsArg === 'function' ? window.jsArg(v) : JSON.stringify(String(v == null ? '' : v)));

  function safeHref(u) {
    const raw = String(u == null ? '' : u).replace(/[\u0000-\u001f\u007f-\u009f]/g, '').trim();
    if (!raw) return '#';
    const dec = (typeof window.sanDecode === 'function' ? window.sanDecode(raw) : raw);
    const probe = dec.replace(/[\s\u0000-\u001f\u007f-\u009f]/g, '').toLowerCase();
    const m = /^([a-z][a-z0-9+.\-]*):/.exec(probe);
    if (!m) return '#';
    const scheme = m[1];
    if (scheme === 'http' || scheme === 'https') return raw;
    return '#';
  }

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
    const safeUrl = attr(safeHref(esc(p.url)));
    const safeHandle = esc(src.handle);
    const safeText = esc(text);
    const isBaleChan = (src.type === 'bale');
    const chanBadge = isBaleChan
      ? '<span class="badge" style="background:rgba(46,189,133,0.15);color:var(--up);border:1px solid rgba(46,189,133,0.3);">🟢 @' + safeHandle + '</span>'
      : '<span class="badge b-asset">🔵 @' + safeHandle + '</span>';

    const isBale = Boolean(p.posted_bale);
    const isTg = Boolean(p.posted_telegram);

    const baleBadge = isBale
      ? '<span class="badge b-sent" title="ارسال شده به بله">✅ بله</span>'
      : '<span class="badge b-pending" title="در صف ارسال خودکار بله">⏳ در صف بله</span>';

    const tgBadge = isTg
      ? '<span class="badge b-sent" title="ارسال شده به تلگرام">✅ تلگرام</span>'
      : '<span class="badge b-pending" title="در صف ارسال خودکار تلگرام">⏳ در صف تلگرام</span>';

    const baleBtn = isBale
      ? '<button class="b-card-act sent" type="button" data-act="send-bale" title="ارسال دوباره به بله (بدون ذکر منبع و لینک)">🔄 بله</button>'
      : '<button class="b-card-act" type="button" data-act="send-bale" title="ارسال به پیام‌رسان بله (بدون ذکر منبع و لینک)">📤 بله</button>';

    const tgBtn = isTg
      ? '<button class="b-card-act sent" type="button" data-act="send-tg" title="ارسال دوباره به تلگرام (بدون ذکر منبع و لینک)">🔄 تلگرام</button>'
      : '<button class="b-card-act" type="button" data-act="send-tg" title="ارسال به پیام‌رسان تلگرام (بدون ذکر منبع و لینک)">📤 تلگرام</button>';

    const postLinkTitle = isBaleChan ? 'مشاهدهٔ پست در بله' : 'مشاهدهٔ پست در تلگرام';

    return '<article class="ncard" data-id="' + esc(src.handle + '/' + p.id) + '">' +
      '<div class="body">' +
        '<div class="row1">' +
          chanBadge +
          (p.media ? '<span class="badge b-viral">📎 ' + esc(p.media) + '</span>' : '') +
          baleBadge +
          tgBadge +
        '</div>' +
        '<div class="ttl">' + safeTitle + '</div>' +
        (text ? '<div class="summ">' + safeText + (p.text && p.text.length > 420 ? '…' : '') + '</div>' : '') +
        '<div class="row2">' +
          '<span class="src">' + esc(src.title || src.handle) + '</span>' +
          '<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">' +
            baleBtn +
            tgBtn +
            '<a class="b-card-act link" href="' + safeUrl + '" target="_blank" rel="noopener noreferrer" title="' + esc(postLinkTitle) + '">🔗 پست</a>' +
            '<span class="dt">' + faWhen(p.time) + '</span>' +
          '</div>' +
        '</div>' +
        '<div class="rank">' + faViews(p.views) + '</div>' +
      '</div>' +
    '</article>';
  }

  function renderView(platform) {
    const isBale = (platform === 'bale');
    const hostId = isBale ? 'baleNewsList' : 'tgNewsList';
    const chipsId = isBale ? 'baleNewsChips' : 'tgNewsChips';
    const manageId = isBale ? 'baleNewsManageList' : 'tgNewsManageList';
    const railId = isBale ? 'cntBaleNews' : 'cntTgNews';
    const countId = isBale ? 'baleNewsCount' : 'tgNewsCount';

    const host = el(hostId);
    const chipsHost = el(chipsId);
    const manageHost = el(manageId);
    const rail = el(railId);
    const count = el(countId);

    const allSources = (S.data || {}).sources || [];
    const sources = allSources.filter(s => isBale ? (s.type === 'bale') : ((s.type || 'telegram') !== 'bale'));

    if (rail) {
      const total = sources.reduce((n, s) => n + (s.posts || []).length, 0);
      rail.textContent = fa(total);
      rail.style.display = total ? '' : 'none';
    }
    if (count) count.textContent = fa(sources.length) + ' کانال';
    const destEl = el(isBale ? 'baleDestStatus' : 'tgDestStatus');
    if (destEl) {
      const destChat = isBale ? (S.data && S.data.bale_chat) : (S.data && S.data.telegram_chat);
      if (destChat) {
        destEl.innerHTML = (isBale ? '🟢' : '🔵') + ' ارسال به چت مقصد: <strong>' + esc(destChat) + '</strong>';
      } else {
        destEl.innerHTML = '';
      }
    }

    const picked = S.picked[platform];

    if (chipsHost) {
      chipsHost.innerHTML = sources.map(s => {
        const icon = isBale ? '🟢 ' : '🔵 ';
        return '<button class="chip' + (picked === s.handle ? ' on' : '') + '" type="button" ' +
          'onclick="TgNews.pick(' + jsArg(s.handle) + ',' + jsArg(platform) + ')" ' +
          'title="' + esc(s.url) + '">' +
          icon + '@' + esc(s.handle) +
          ' <span class="n">' + fa((s.posts || []).length) + '</span>' +
          '<span class="chip-del" onclick="event.stopPropagation();TgNews.deleteChannel(' + jsArg(s.handle) + ')" title="حذف این کانال" aria-label="حذف">×</span>' +
          '</button>';
      }).join('');
    }

    if (manageHost) {
      if (!sources.length) {
        manageHost.innerHTML = '<span style="font-size:12px;color:var(--ink-3);">هیچ کانالی در این بخش ثبت نشده است.</span>';
      } else {
        const pLabel = isBale ? 'بله' : 'تلگرام';
        manageHost.innerHTML = '<span style="font-size:12px;color:var(--ink-2);font-weight:600;">کانال‌های ثبت‌شده ' + pLabel + ':</span> ' +
          sources.map(s => {
            const icon = isBale ? '🟢' : '🔵';
            return '<span style="display:inline-flex;align-items:center;gap:6px;background:var(--wash);border:1px solid var(--rule);border-radius:var(--r1);padding:3px 8px;font-size:12px;">' +
              icon + ' <strong>@' + esc(s.handle) + '</strong>' +
              '<button type="button" class="btn sm ghost" style="padding:1px 6px;height:22px;color:var(--dn);font-size:11px;" onclick="TgNews.deleteChannel(' + jsArg(s.handle) + ')" title="حذف کانال">🗑️ حذف</button>' +
              '</span>';
          }).join(' ');
      }
    }

    if (!host) return;

    if (!sources.length) {
      const pName = isBale ? 'بله' : 'تلگرام';
      host.innerHTML = '<div class="cb-empty">کانال ' + pName + ' تنظیم نشده است — از دکمه «افزودن کانال» یک کانال اضافه کنید.</div>';
      return;
    }

    const shown = picked
      ? sources.filter(s => s.handle === picked)
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
          sendPost(post, src, 'bale', btnBale);
        });
      }
      const btnTg = art.querySelector('[data-act="send-tg"]');
      if (btnTg) {
        btnTg.addEventListener('click', (e) => {
          e.stopPropagation();
          sendPost(post, src, 'telegram', btnTg);
        });
      }
    });
  }

  function render() {
    renderView('telegram');
    renderView('bale');
  }

  async function sendPost(post, src, platform, btn) {
    const notify = (msg) => { if (typeof toast === 'function') toast(msg); };
    const pName = platform === 'telegram' ? 'تلگرام' : 'بله';
    const oldHtml = btn ? btn.innerHTML : '';
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner sm"></span>';
    }
    try {
      notify('در حال ارسال خبر به ' + pName + ' (بدون ذکر سورس و لینک)...');
      const postId = (src && src.handle ? src.handle + '_' : '') + (post.id || '');
      const r = await fetch('/api/telegram_news/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          post_id: postId,
          handle: (src && src.handle) || '',
          source_title: (src && src.title) || '',
          title: post.title || '',
          text: post.text || '',
          platform: platform,
          from_view: (src && src.type === 'bale') ? 'balenews' : 'tgnews',
          source_type: (src && src.type) || 'telegram'
        })
      });
      const j = await r.json();
      if (j && j.ok) {
        notify('✅ خبر با موفقیت به ' + pName + ' ارسال شد');
        if (platform === 'telegram') {
          post.posted_telegram = true;
        } else {
          post.posted_bale = true;
        }
        render();
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
    try {
      const r = await fetch('/api/telegram_news' + (force ? '?refresh=1' : ''));
      const j = await r.json();
      if (!j || j.ok === false) throw new Error((j && j.error) || ('HTTP ' + r.status));
      S.data = j;
      render();
    } catch (e) {
      console.error('TgNews.load:', e);
      ['tgNewsList', 'baleNewsList'].forEach(id => {
        const h = el(id);
        if (h) h.innerHTML = '<div class="cb-empty">دریافت پست‌ها ممکن نشد — ' + esc(e.message || e) + '</div>';
      });
    } finally {
      S.busy = false;
    }
  }

  async function loadBaleNewsBotConfig() {
    try {
      const r = await fetch('/api/balenews/config');
      const j = await r.json();
      if (j && j.ok) {
        const inpT = el('inpBaleNewsBotToken');
        const inpC = el('inpBaleNewsBotChat');
        const lbl = el('lblBaleDestChat');
        if (inpT && j.has_token) inpT.value = j.token;
        if (inpC) inpC.value = j.chat || '';
        if (lbl) lbl.textContent = j.chat || 'تنظیم‌نشده';
      }
    } catch (e) {
      console.warn('loadBaleNewsBotConfig:', e);
    }
  }

  return {
    mount: function (platform) {
      if (!S.data) load(false);
      else render();
      if (platform === 'bale') loadBaleNewsBotConfig();
    },
    refresh: function () { load(true); },
    pick: function (handle, platform) {
      const p = platform || 'telegram';
      S.picked[p] = (S.picked[p] === handle) ? null : handle;
      render();
    },
    toggleAddBox: function (platform) {
      const boxId = (platform === 'bale') ? 'baleNewsAddBox' : 'tgNewsAddBox';
      const box = el(boxId);
      if (box) box.style.display = box.style.display === 'none' ? 'block' : 'none';
    },
    testChannel: async function (platform) {
      const isB = (platform === 'bale');
      const inpHId = isB ? 'inpBaleChannelHandle' : 'inpTgChannelHandle';
      const resId = isB ? 'baleChannelTestResult' : 'tgChannelTestResult';
      const inp = el(inpHId);
      const res = el(resId);
      let handle = (inp ? inp.value : '').trim().replace(/^@/, '');
      let cType = isB ? 'bale' : 'telegram';
      if (handle.indexOf('ble.ir') >= 0) cType = 'bale';
      handle = handle.replace(/^https?:\/\/(?:ble\.ir|t\.me)\//i, '').replace(/^\/+|\/+$/g, '').replace(/^@/, '');
      if (!handle) {
        if (typeof toast === 'function') toast('ابتدا آیدی کانال را وارد کنید');
        return;
      }
      const platformName = cType === 'bale' ? 'بله' : 'تلگرام';
      if (res) {
        res.style.display = 'block';
        res.innerHTML = '<span class="spinner sm"></span> در حال بررسی ارتباط با کانال @' + esc(handle) + ' در ' + platformName + '...';
      }
      try {
        const r = await fetch('/api/telegram_news/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ handle: handle, type: cType })
        });
        const j = await r.json();
        if (res) {
          if (j && j.ok) {
            res.innerHTML = '<span style="color:var(--up);">✅ کانال «' + esc(j.title || handle) + '» (' + platformName + ') عمومی است و ' + fa(j.count) + ' پست با موفقیت دریافت شد.</span>';
          } else {
            res.innerHTML = '<span style="color:var(--dn);">❌ خطا: ' + esc((j && j.error) || 'کانال در دسترس نیست') + '</span>';
          }
        }
      } catch (e) {
        if (res) res.innerHTML = '<span style="color:var(--dn);">❌ خطای اتصال به سرور: ' + esc(e.message) + '</span>';
      }
    },
    saveChannel: async function (platform) {
      const isB = (platform === 'bale');
      const inpHId = isB ? 'inpBaleChannelHandle' : 'inpTgChannelHandle';
      const inpTId = isB ? 'inpBaleChannelTitle' : 'inpTgChannelTitle';
      const resId = isB ? 'baleChannelTestResult' : 'tgChannelTestResult';
      const boxId = isB ? 'baleNewsAddBox' : 'tgNewsAddBox';

      const inpH = el(inpHId);
      const inpT = el(inpTId);
      let handle = (inpH ? inpH.value : '').trim().replace(/^@/, '');
      let cType = isB ? 'bale' : 'telegram';
      if (handle.indexOf('ble.ir') >= 0) cType = 'bale';
      handle = handle.replace(/^https?:\/\/(?:ble\.ir|t\.me)\//i, '').replace(/^\/+|\/+$/g, '').replace(/^@/, '');
      const title = (inpT ? inpT.value : '').trim();
      if (!handle) {
        if (typeof toast === 'function') toast('آیدی کانال را وارد کنید');
        return;
      }
      try {
        const r = await fetch('/api/telegram_news/sources', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ handle: handle, title: title, type: cType })
        });
        const j = await r.json();
        if (j && j.ok) {
          if (typeof toast === 'function') toast('✅ کانال با موفقیت افزوده شد');
          if (inpH) inpH.value = '';
          if (inpT) inpT.value = '';
          const res = el(resId);
          if (res) res.style.display = 'none';
          const box = el(boxId);
          if (box) box.style.display = 'none';
          load(true);
        } else {
          if (typeof toast === 'function') toast('❌ خطا: ' + ((j && j.error) || 'افزودن ناموفق بود'));
        }
      } catch (e) {
        if (typeof toast === 'function') toast('❌ خطای ارتباط: ' + e.message);
      }
    },
    deleteChannel: async function (handle) {
      if (!handle) return;
      if (!confirm('آیا از حذف کانال @' + handle + ' از بخش اخبار اطمینان دارید؟')) return;
      try {
        const r = await fetch('/api/telegram_news/sources/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ handle: handle })
        });
        const j = await r.json();
        if (j && j.ok) {
          if (typeof toast === 'function') toast('✅ کانال @' + handle + ' با موفقیت حذف شد');
          if (S.picked.telegram === handle) S.picked.telegram = null;
          if (S.picked.bale === handle) S.picked.bale = null;
          load(true);
        } else {
          if (typeof toast === 'function') toast('❌ حذف ناموفق: ' + ((j && j.error) || 'خطا در عملیات'));
        }
      } catch (e) {
        if (typeof toast === 'function') toast('❌ خطای ارتباط: ' + e.message);
      }
    },
    toggleBaleTokenEye: function () {
      const inp = el('inpBaleNewsBotToken');
      if (inp) inp.type = (inp.type === 'password') ? 'text' : 'password';
    },
    saveBaleNewsBot: async function () {
      const inpT = el('inpBaleNewsBotToken');
      const inpC = el('inpBaleNewsBotChat');
      const status = el('baleNewsBotStatusMsg');
      const token = (inpT ? inpT.value : '').trim();
      const chat = (inpC ? inpC.value : '').trim();
      if (status) status.innerHTML = '<span class="spinner sm"></span> در حال ذخیره...';
      try {
        const r = await fetch('/api/balenews/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: token, chat: chat })
        });
        const j = await r.json();
        if (j && j.ok) {
          if (typeof toast === 'function') toast('✅ تنظیمات ربات اخبار بله ذخیره شد');
          if (status) status.innerHTML = '<span style="color:var(--up);">✅ ذخیره شد</span>';
          const lbl = el('lblBaleDestChat');
          if (lbl) lbl.textContent = chat || 'تنظیم‌نشده';
        } else {
          if (status) status.innerHTML = '<span style="color:var(--dn);">❌ خطا: ' + esc((j && j.error) || 'خطا در ذخیره') + '</span>';
        }
      } catch (e) {
        if (status) status.innerHTML = '<span style="color:var(--dn);">❌ خطا: ' + esc(e.message) + '</span>';
      }
    },
    testBaleNewsBot: async function () {
      const inpT = el('inpBaleNewsBotToken');
      const inpC = el('inpBaleNewsBotChat');
      const status = el('baleNewsBotStatusMsg');
      const token = (inpT ? inpT.value : '').trim();
      const chat = (inpC ? inpC.value : '').trim();
      if (status) status.innerHTML = '<span class="spinner sm"></span> در حال ارسال پیام تست...';
      try {
        const r = await fetch('/api/balenews/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: token, chat: chat })
        });
        const j = await r.json();
        if (j && j.ok) {
          if (status) status.innerHTML = '<span style="color:var(--up);">✅ پیام تست با موفقیت ارسال شد</span>';
          if (typeof toast === 'function') toast('✅ پیام تست به کانال بله ارسال شد');
        } else {
          if (status) status.innerHTML = '<span style="color:var(--dn);">❌ خطا: ' + esc((j && j.error) || 'ارسال نشد') + '</span>';
        }
      } catch (e) {
        if (status) status.innerHTML = '<span style="color:var(--dn);">❌ خطای ارتباط: ' + esc(e.message) + '</span>';
      }
    },
    detectBaleNewsChat: async function () {
      const inpT = el('inpBaleNewsBotToken');
      const box = el('baleNewsDetectedChats');
      const token = (inpT ? inpT.value : '').trim();
      if (box) {
        box.style.display = 'block';
        box.innerHTML = '<span class="spinner sm"></span> در حال بررسی کانال‌ها و چت‌های فعال ربات بله...';
      }
      try {
        const r = await fetch('/api/bale/get-chat-id', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: token })
        });
        const j = await r.json();
        if (!j || !j.ok) {
          if (box) box.innerHTML = '<span style="color:var(--dn);">❌ خطا: ' + esc((j && j.error) || 'عدم امکان دریافت اطلاعات ربات') + '</span>';
          return;
        }
        const chats = j.chats || [];
        if (!chats.length) {
          const hint = j.hint || 'ربات متصل شد اما چت فعالی ثبت نشده است. ربات را به کانال اضافه کرده و یک پیام بفرستید، سپس مجدداً روی دکمه تشخیص خودکار کلیک کنید.';
          if (box) box.innerHTML = '<div style="color:var(--ink-2);line-height:1.6;">ℹ️ ' + esc(hint) + '</div>';
          return;
        }
        let html = '<div style="font-weight:600;margin-bottom:8px;color:var(--ink-1);">کانال‌ها و چت‌های فعال متصل به ربات: (روی کانال مقصد کلیک کنید)</div>';
        html += '<div style="display:flex;flex-direction:column;gap:6px;">';
        chats.forEach(function (c) {
          const isChan = (c.type === 'channel');
          const typeIcon = isChan ? '📢' : '👤';
          const typeLabel = isChan ? 'کانال' : 'چت خصوصی';
          const title = c.title || (c.first_name ? (c.first_name + ' ' + (c.last_name || '')).trim() : '') || 'بدون نام';
          const u = c.username ? ('@' + c.username) : '';
          const cid = String(c.id);
          html += '<div style="display:flex;align-items:center;justify-content:space-between;padding:8px 10px;background:var(--panel);border:1px solid var(--rule);border-radius:var(--r1);gap:8px;flex-wrap:wrap;">';
          html += '<div><strong>' + typeIcon + ' ' + esc(typeLabel) + ':</strong> ' + esc(title) + ' ' + (u ? '<span style="color:var(--ink-3);font-size:11px;">(' + esc(u) + ')</span>' : '') + ' — <code style="font-size:11px;direction:ltr;display:inline-block;">' + esc(cid) + '</code></div>';
          html += '<button type="button" class="btn sm" onclick="TgNews.selectDetectedChat(' + jsArg(cid) + ')">✓ انتخاب این مقصد</button>';
          html += '</div>';
        });
        html += '</div>';
        if (box) box.innerHTML = html;
      } catch (e) {
        if (box) box.innerHTML = '<span style="color:var(--dn);">❌ خطا: ' + esc(e.message) + '</span>';
      }
    },
    selectDetectedChat: function (chatId) {
      const inpC = el('inpBaleNewsBotChat');
      if (inpC) inpC.value = chatId;
      TgNews.saveBaleNewsBot();
      const box = el('baleNewsDetectedChats');
      if (box) box.style.display = 'none';
      if (typeof toast === 'function') toast('✅ کانال مقصد با موفقیت انتخاب و ذخیره شد: ' + chatId);
    },
    toggleBaleSettings: function () {
      const d = el('baleNewsSettingsDetails');
      if (d) d.open = !d.open;
    },
    loadBaleNewsBotConfig: loadBaleNewsBotConfig,
    _safeHref: safeHref
  };
})();

window.TgNews = TgNews;
