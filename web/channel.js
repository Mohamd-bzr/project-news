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
  const attr = (s) => (typeof window.attr === 'function' ? window.attr(s) : esc(s));
  const jsArg = (v) => (typeof window.jsArg === 'function' ? window.jsArg(v) : JSON.stringify(String(v == null ? '' : v)).replace(/&/g, '&amp;').replace(/"/g, '&quot;'));

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

  /* the feed's badge tags: bucket -> (emoji, label) */
  const TAGS = {
    gold: ['🟡', 'طلا و فلزات'], coin: ['🪙', 'فلزات'], currency: ['💵', 'ارز و فارکس'],
    global: ['🌍', 'اقتصاد جهان'], crypto: ['₿', 'ارز دیجیتال'], tech: ['🤖', 'فناوری و AI'],
  };

  function agoText(hours) {
    const h = Number(hours);
    if (!isFinite(h)) return '—';
    if (h < 1) return fa(Math.round(h * 60)) + ' دقیقه پیش';
    if (h < 48) return fa(Math.round(h)) + ' ساعت پیش';
    return fa(Math.round(h / 24)) + ' روز پیش';
  }

  function itemCard(it) {
    const title = it.title_fa || it.title || '';
    const summary = (it.summary_fa || it.summary || '').trim();
    const lane = esc(it.primary_bucket || 'tech');
    const tag = TAGS[it.primary_bucket] || ['', it.bucket_label || 'فناوری و AI'];
    const safeId = String(it.id || '').replace(/[^\w-]/g, '');
    const open = it.id ? ' onclick="Channel.openSource(' + jsArg(it.id) + ')"' : '';
    const v = Math.max(0, Math.min(100, Number(it.viral) || 0));
    const vcls = v >= 65 ? 'hot' : (v >= 45 ? 'warm' : 'cool');

    const isBaleSent = Boolean(it.posted_bale);
    const baleBadge = isBaleSent
      ? '<span class="badge b-sent" title="این ایده به کانال بله ارسال شده است">✅ ارسال به بله</span>'
      : '<span class="badge b-pending" title="در صف ارسال خودکار بله">⏳ در صف بله</span>';

    const sendAction = isBaleSent
      ? '<button class="b-card-act sent" type="button" onclick="event.stopPropagation(); Channel.sendSingle(' + jsArg(it.id) + ', \'bale\', this)" title="ارسال دوباره به بله">🔄 ارسال مجدد</button>'
      : '<button class="b-card-act" type="button" onclick="event.stopPropagation(); Channel.sendSingle(' + jsArg(it.id) + ', \'bale\', this)" title="ارسال فوری همین خبر به کانال بله">📤 ارسال به بله</button>';

    const linkAction = it.link
      ? '<a class="b-card-act link" href="' + attr(safeHref(it.link)) + '" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()" title="مشاهده خبر اصلی در وب‌سایت منبع">🔗 منبع خبر</a>'
      : '';

    return '<article class="ncard" data-lane="' + lane + '" data-id="' +
      safeId + '"' + open + ' style="cursor:pointer">' +
      '<div class="body">' +
        '<div class="row1">' +
          '<span class="badge b-viral ' + vcls + '" title="احتمال وایرال">🔥 ' + fa(v.toFixed(0)) + '٪</span>' +
          '<span class="badge b-asset">' + esc(tag[0]) + ' ' + esc(tag[1]) + '</span>' +
          baleBadge +
        '</div>' +
        '<div class="ttl">' + esc(title) + '</div>' +
        (summary ? '<div class="summ">' + esc(summary) + '</div>' : '') +
        '<div class="row2">' +
          '<span class="src">' + esc(it.source || 'منبع اصلی') + '</span>' +
          '<div style="display:flex;align-items:center;gap:6px;">' +
            linkAction +
            sendAction +
            '<span class="dt">' + agoText(it.age_hours) + '</span>' +
          '</div>' +
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
      const r = await fetch('/api/channel/feed?all=1' + (force ? '&refresh=1' : ''));
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
    const btn = el('btnRefreshChannel');
    const oldHtml = btn ? btn.innerHTML : '';
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner sm"></span> <span>در حال غربال...</span>';
    }
    if (typeof toast === 'function') toast('در حال غربال و رتبه‌بندی مجدد ایده‌ها...');
    try {
      await load(true);
      if (typeof toast === 'function') toast('غربال ایده‌ها با موفقیت انجام شد ✓');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = oldHtml;
      }
    }
  }

  /* called immediately when a background scraping cycle finishes */
  async function onCycleUpdate() {
    const panel = el('view-channel');
    const isVisible = panel && panel.classList.contains('active');
    if (isVisible) {
      await load(true);
    } else {
      S.fetchedAt = 0;
    }
  }

  async function pushNow() {
    const btn = el('btnPushBale');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner sm"></span> در حال ارسال...';
    }
    try {
      const r = await fetch('/api/ideas/push-now', { method: 'POST' });
      const j = await r.json();
      if (typeof toast === 'function') {
        toast(j.hint || (j.ok ? 'ارسال ایده‌ها به بله و تلگرام آغاز شد' : 'خطا در ارسال: ' + (j.error || '')));
      }
      setTimeout(() => load(true), 2500);
    } catch (e) {
      if (typeof toast === 'function') toast('خطا در ارتباط با سرور: ' + e.message);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<svg class="ic"><use href="#i-send"/></svg> <span>ارسال فوری به بله</span>';
      }
    }
  }

  async function sendSingle(id, platform, btnEl) {
    if (!id) return;
    const btn = btnEl || (typeof event !== 'undefined' && event && event.currentTarget);
    const oldHtml = btn ? btn.innerHTML : '';
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner sm"></span> در حال ارسال...';
    }
    const notify = (msg) => {
      if (typeof window.toast === 'function') window.toast(msg);
      else if (typeof toast === 'function') toast(msg);
      else alert(msg);
    };
    try {
      notify('در حال ارسال ایده به بله...');
      const r = await fetch('/api/ideas/send-single', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: id, platform: platform || 'bale' })
      });
      const j = await r.json();
      if (j.ok) {
        notify('✅ با موفقیت به بله ارسال شد');
        if (S.feed && S.feed.items) {
          const item = S.feed.items.find(x => x.id === id);
          if (item) item.posted_bale = true;
          render();
        }
      } else {
        notify('❌ ' + (j.error || 'ارسال ناموفق بود'));
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

  async function openDispatchModal() {
    const modal = el('ideasDispatchOverlay');
    const body = el('ideasDispatchBody');
    if (!modal || !body) return;
    modal.classList.add('open');
    body.innerHTML = '<div style="text-align:center;padding:30px;"><span class="spinner"></span> در حال بارگذاری وضعیت پیام‌رسان‌ها...</div>';

    try {
      const r = await fetch('/api/ideas/dispatch-status');
      const j = await r.json();
      if (!j.ok) throw new Error(j.error || 'خطا در دریافت وضعیت');

      const b = j.bale || {};
      const tg = j.telegram || {};
      const bn = j.balenews || {};
      const logs = j.recent_logs || [];

      let html = '<div class="dispatch-modal-content">' +
        '<div class="dispatch-head" style="margin-bottom:16px;">' +
          '<div style="display:flex;align-items:center;gap:10px;">' +
            '<span style="font-size:24px;">📨</span>' +
            '<div>' +
              '<h3 style="margin:0;font-size:16px;color:var(--ink-1);">وضعیت و تاریخچه خبرهای ارسال‌شده</h3>' +
              '<p style="margin:2px 0 0 0;font-size:12px;color:var(--ink-3);">پایش وضعیت ربات‌ها، کانال‌های متصل و گزارش خبرهای ارسال‌شده به بله و تلگرام</p>' +
            '</div>' +
          '</div>' +
        '</div>' +

        '<div class="dispatch-grid">' +
          '<div class="dispatch-card">' +
            '<div class="dh"><strong>ایده‌های محتوایی (بله)</strong>' + (b.configured ? '<span class="status-pill ok">متصل ✅</span>' : '<span class="status-pill err">تنظیم‌نشده ⚠️</span>') + '</div>' +
            '<div class="row"><span>کانال مقصد:</span> <code dir="ltr" style="font-weight:bold;color:var(--accent);">' + esc(b.chat || 'تنظیم نشده') + '</code></div>' +
            '<div class="row"><span>وضعیت:</span> <span>' + (b.configured ? 'آماده ارسال' : 'نیازمند توکن و چت') + '</span></div>' +
            '<div class="row"><span>ارسال‌شده در این تخته:</span> <strong>' + fa(b.posted_count || 0) + ' ایده</strong></div>' +
            '<div class="row"><span>در صف ارسال:</span> <strong>' + fa(b.unsent_count || 0) + ' ایده</strong></div>' +
            '<div style="margin-top:12px;display:flex;gap:8px;">' +
              '<button class="btn sm primary" style="flex:1" onclick="Channel.pushNow(); closeModal(\'ideasDispatchOverlay\');">🚀 ارسال ایده‌های در صف</button>' +
              '<button class="btn sm ghost" onclick="Channel.testBalePing()">🧪 تست اتصال</button>' +
            '</div>' +
          '</div>' +

          '<div class="dispatch-card">' +
            '<div class="dh"><strong>اخبار بله (کانال اختصاصی)</strong>' + (bn.configured ? '<span class="status-pill ok">متصل ✅</span>' : '<span class="status-pill err">تنظیم‌نشده ⚠️</span>') + '</div>' +
            '<div class="row"><span>کانال مقصد:</span> <code dir="ltr" style="font-weight:bold;color:var(--accent);">' + esc(bn.chat || 'تنظیم نشده') + '</code></div>' +
            '<div class="row"><span>وضعیت ربات:</span> <span>' + (bn.configured ? 'آماده ارسال اخبار بله' : 'تنظیم‌نشده') + '</span></div>' +
            '<div style="margin-top:12px;display:flex;gap:8px;">' +
              '<button class="btn sm ghost" style="flex:1" onclick="showView(\'balenews\'); closeModal(\'ideasDispatchOverlay\');">⚙️ رفتن به اخبار بله</button>' +
            '</div>' +
          '</div>' +

          '<div class="dispatch-card">' +
            '<div class="dh"><strong>پیام‌رسان تلگرام</strong>' + (tg.configured ? '<span class="status-pill ok">متصل ✅</span>' : '<span class="status-pill err">تنظیم‌نشده ⚠️</span>') + '</div>' +
            '<div class="row"><span>کانال مقصد:</span> <code dir="ltr" style="font-weight:bold;">' + esc(tg.chat || 'تنظیم نشده') + '</code></div>' +
            '<div class="row"><span>وضعیت ربات:</span> <span>' + (tg.configured ? 'آماده ارسال' : 'تنظیم نشده') + '</span></div>' +
            '<div class="row"><span>ارسال‌شده:</span> <strong>' + fa(tg.posted_count || 0) + ' ایده</strong></div>' +
            '<div class="row"><span>در صف ارسال:</span> <strong>' + fa(tg.unsent_count || 0) + ' ایده</strong></div>' +
          '</div>' +
        '</div>' +

        '<div class="dispatch-logs-section">' +
          '<h4 style="margin:16px 0 8px 0;font-size:13.5px;display:flex;justify-content:space-between;align-items:center;">' +
            '<span>تاریخچه آخرین خبرهای ارسال‌شده (ایده‌ها و اخبار)</span>' +
            '<span style="font-size:12px;color:var(--ink-3);font-weight:normal;">' + fa(logs.length) + ' مورد اخیر</span>' +
          '</h4>' +
          (logs.length ? '<div class="dispatch-table-wrap"><table class="dispatch-table">' +
            '<thead><tr><th>پلتفرم</th><th>تیتر خبر</th><th>زمان ارسال</th><th>لینک</th></tr></thead>' +
            '<tbody>' +
            logs.map(l => {
              const dt = l.posted_ts ? new Date(l.posted_ts * 1000).toLocaleTimeString('fa-IR', {hour: '2-digit', minute:'2-digit'}) : '—';
              const isB = l.platform && l.platform.includes('bale');
              let title = l.title_fa || l.title;
              if (!title && l.article_id) {
                if (String(l.article_id).startsWith('tgnews_')) {
                  const parts = String(l.article_id).split('_');
                  title = 'خبر ارسالی کانال @' + (parts[1] || 'تلگرام/بله');
                } else {
                  title = 'ایده شماره ' + l.article_id;
                }
              }
              title = title || 'بدون تیتر';
              return '<tr>' +
                '<td><span class="badge ' + (isB ? 'b-bale' : 'b-tg') + '">' + (isB ? 'بله' : 'تلگرام') + '</span></td>' +
                '<td class="ttl-col">' + esc(title) + '</td>' +
                '<td class="dt-col">' + dt + '</td>' +
                '<td>' + (l.link ? '<a href="' + attr(safeHref(l.link)) + '" target="_blank" rel="noopener noreferrer" class="link-btn">مشاهده</a>' : '—') + '</td>' +
              '</tr>';
            }).join('') +
            '</tbody></table></div>'
          : '<div style="padding:15px;background:var(--panel-2);border:1px solid var(--rule);border-radius:8px;color:var(--ink-3);font-size:12.5px;text-align:center;">هنوز خبری ثبت نشده است. برای ارسال، دکمه «ارسال فوری به بله» را بزنید.</div>') +
        '</div>' +
      '</div>';

      body.innerHTML = html;
    } catch (e) {
      body.innerHTML = '<div style="padding:20px;color:var(--err);text-align:center;">خطا در دریافت وضعیت: ' + esc(e.message) + '</div>';
    }
  }

  async function testBalePing() {
    try {
      if (typeof toast === 'function') toast('در حال ارسال پیام تست به بله...');
      const r = await fetch('/api/bale/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const j = await r.json();
      if (j.ok) {
        if (typeof toast === 'function') toast('✅ پیام آزمایشی با موفقیت به بله ارسال شد');
      } else {
        if (typeof toast === 'function') toast('❌ خطا: ' + (j.error || 'ارسال نشد'));
      }
    } catch (e) {
      if (typeof toast === 'function') toast('خطای اتصال: ' + e.message);
    }
  }

  function openSource(id) {
    if (!id) return;
    if (typeof window.openArticle === 'function') {
      window.openArticle(id);
    } else if (typeof openArticle === 'function') {
      openArticle(id);
    } else {
      const it = (S.feed && S.feed.items) ? S.feed.items.find(x => x.id === id) : null;
      if (it && it.link) {
        const u = safeHref(it.link);
        if (u !== '#') window.open(u, '_blank', 'noopener,noreferrer');
      }
    }
  }

  function getItem(id) {
    if (!id || !S.feed || !S.feed.items) return null;
    return S.feed.items.find(x => x.id === id) || null;
  }

  return {
    mount: mount,
    refresh: refresh,
    onCycleUpdate: onCycleUpdate,
    openSource: openSource,
    getItem: getItem,
    pushNow: pushNow,
    sendSingle: sendSingle,
    openDispatchModal: openDispatchModal,
    testBalePing: testBalePing,
    _safeHref: safeHref,
    _s: S
  };
})();
window.Channel = Channel;
