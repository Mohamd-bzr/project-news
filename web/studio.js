/* ═══════════════════════════════════════════════════════════════════════════
   FREEBUFF — CONTENT STUDIO (Redesigned 2026 Standard)

   The server ranks the corpus and drafts the copy; this client presents it,
   provides deep filtering (format, asset, demand, search, sorting), and turns
   a draft into things a person can actually publish: a caption to copy,
   slides exported as PNG, a printable deck, and an explicit, confirmed send to
   Telegram.
   ═══════════════════════════════════════════════════════════════════════════ */
'use strict';

const Studio = (function () {
  const FACTORS = [
    ['credibility', 'اعتبار'], ['coverage', 'پوشش'], ['audience', 'مخاطب'],
    ['freshness', 'تازگی'], ['youtube', 'یوتیوب'], ['telegram', 'تلگرام'],
    ['reddit', 'ردیت'],
  ];
  const SLIDE_W = 1080, SLIDE_H = 1350;

  const S = {
    feed: null,
    providers: [],
    busy: false,
    draft: null,
    draftId: 0,
    draftLoadingId: null,
    tab: 'text',
    pending: null,
    filters: {
      search: '',
      format: 'all',      // 'all', 'carousel', 'video', 'text'
      asset: 'all',       // 'all', 'BTC', 'ETH', 'SOL', 'XAU', 'WTI', 'DXY', etc.
      sortBy: 'score',    // 'score', 'heat', 'credibility', 'age'
      demandOnly: false,  // boolean
    }
  };

  const fa = (n) => (typeof toFa === 'function' ? toFa(n) : String(n));
  const el = (id) => document.getElementById(id);

  function num(v, digits) {
    if (v === null || v === undefined || v === '' || isNaN(Number(v))) return '—';
    const d = digits === undefined ? 1 : digits;
    return fa(Number(v).toLocaleString('en-US',
      { minimumFractionDigits: d, maximumFractionDigits: d }));
  }

  function agoText(seconds) {
    if (seconds === null || seconds === undefined) return '—';
    const s = Math.max(0, Math.round(seconds));
    if (s < 90) return fa(s) + ' ثانیه پیش';
    if (s < 5400) return fa(Math.round(s / 60)) + ' دقیقه پیش';
    return fa(Math.round(s / 3600)) + ' ساعت پیش';
  }

  function bar(label, value) {
    const pct = Math.max(0, Math.min(1, Number(value) || 0)) * 100;
    return '<div class="st-factor-bar">' +
      '<span class="k">' + esc(label) + '</span>' +
      '<span class="meter"><i style="inline-size:' + pct.toFixed(1) + '%"></i></span>' +
      '<span class="v">' + fa(pct.toFixed(0)) + '٪</span></div>';
  }

  function heatItems(item) {
    const h = item.heat || {};
    const bits = [];
    if (h.youtube_vph && Number(h.youtube_vph) > 0) {
      bits.push('<span class="st-heat-item yt">▶️ یوتیوب: ' + num(h.youtube_vph, 0) + ' باز/ساعت</span>');
    }
    if (h.telegram_vph && Number(h.telegram_vph) > 0) {
      const relTxt = (h.telegram_rel && h.telegram_rel > 1.05) ? ' (×' + fa(Number(h.telegram_rel).toFixed(1)) + ')' : '';
      bits.push('<span class="st-heat-item tg">✈️ تلگرام: ' + num(h.telegram_vph, 0) + ' باز/ساعت' + relTxt + '</span>');
    }
    if (h.reddit_sph && Number(h.reddit_sph) > 0) {
      bits.push('<span class="st-heat-item rd">💬 ردیت: ' + num(h.reddit_sph, 1) + ' رای/ساعت</span>');
    }
    return bits;
  }

  function formatBadge(fmt) {
    const best = (fmt && fmt.best) || 'text';
    const label = (fmt && fmt.best_label) || 'پست متنی / تلگرام';
    let cls = 'st-fmt-text';
    let icon = '✍️';
    if (best === 'carousel') {
      cls = 'st-fmt-carousel';
      icon = '📑';
    } else if (best === 'video') {
      cls = 'st-fmt-video';
      icon = '🎬';
    }
    return '<span class="st-fmt-tag ' + cls + '">' + icon + ' ' + esc(label) + '</span>';
  }

  function getFilteredItems() {
    const feed = S.feed || {};
    let items = (feed.items || []).slice();
    const f = S.filters;

    // Search filter
    if (f.search && f.search.trim()) {
      const q = f.search.trim().toLowerCase();
      items = items.filter(function (it) {
        const title = ((it.title_fa || '') + ' ' + (it.title || '') + ' ' + (it.source || '')).toLowerCase();
        const assets = (it.assets || []).join(' ').toLowerCase();
        return title.includes(q) || assets.includes(q);
      });
    }

    // Format filter
    if (f.format && f.format !== 'all') {
      items = items.filter(function (it) {
        return (it.format && it.format.best) === f.format;
      });
    }

    // Asset filter
    if (f.asset && f.asset !== 'all') {
      items = items.filter(function (it) {
        return (it.assets || []).includes(f.asset);
      });
    }

    // Demand only filter
    if (f.demandOnly) {
      items = items.filter(function (it) {
        const h = it.heat || {};
        return (Number(h.youtube_vph) > 0 || Number(h.telegram_vph) > 0 || Number(h.reddit_sph) > 0);
      });
    }

    // Sorting
    if (f.sortBy === 'heat') {
      items.sort(function (a, b) {
        const ha = ((a.factors && (a.factors.youtube || 0) + (a.factors.telegram || 0) + (a.factors.reddit || 0)) || 0);
        const hb = ((b.factors && (b.factors.youtube || 0) + (b.factors.telegram || 0) + (b.factors.reddit || 0)) || 0);
        return hb - ha;
      });
    } else if (f.sortBy === 'credibility') {
      items.sort(function (a, b) {
        return (b.credibility || 0) - (a.credibility || 0);
      });
    } else if (f.sortBy === 'age') {
      items.sort(function (a, b) {
        return (a.age_hours || 0) - (b.age_hours || 0);
      });
    } else {
      // Default: composite score
      items.sort(function (a, b) {
        return (b.score || 0) - (a.score || 0);
      });
    }

    return items;
  }

  function itemCard(item, rank) {
    const f = item.factors || {};
    const fmt = item.format || {};
    const sig = item.signals || {};
    const yt = sig.youtube || {};
    const tg = sig.telegram || {};
    const rd = sig.reddit || {};
    const facts = [];
    if (yt.url && safeUrl(yt.url)) {
      facts.push('<a href="' + esc(safeUrl(yt.url)) + '" target="_blank" rel="noopener noreferrer">' +
                 '📺 یوتیوب: ' + esc((yt.title || '').slice(0, 70)) + ' (' + num(yt.views, 0) + ' بازدید)</a>');
    }
    if (tg.text) facts.push('✈️ تلگرام [@' + esc(tg.channel || '') + ']: ' + esc(tg.text.slice(0, 90)));
    if (rd.title) facts.push('💬 ردیت (r/' + esc(rd.sub || '') + '): ' + esc(rd.title.slice(0, 80)));

    const rankCls = rank === 1 ? 'rank-1' : (rank === 2 ? 'rank-2' : (rank === 3 ? 'rank-3' : ''));
    const isDrafting = (S.draftLoadingId === item.id);
    const heatChips = heatItems(item);

    return '<article class="st-item ' + rankCls + '" data-id="' + esc(item.id || '') + '">' +
      '<div class="st-item-top">' +
        '<div class="st-item-rank-title">' +
          '<span class="st-rank-badge" title="رتبه #' + fa(rank) + '">' + fa(rank) + '</span>' +
          '<h4>' + esc(item.title_fa || item.title || '') + '</h4>' +
        '</div>' +
        '<div class="st-item-score-pill" title="امتیاز ترکیبی">' +
          '<span class="st-score-val">' + fa(Number(item.score || 0).toFixed(1)) + '</span>' +
          '<span class="st-score-lbl">امتیاز تولید</span>' +
        '</div>' +
      '</div>' +

      '<div class="st-meta-row">' +
        formatBadge(fmt) +
        '<span class="badge sm">' + esc(item.source || 'منبع اصلی') + '</span>' +
        '<span class="badge sm" style="color:var(--cu-txt);font-weight:600">🛡️ اعتبار ' + fa(((item.credibility || 0) * 100).toFixed(0)) + '٪</span>' +
        '<span class="badge sm">⏱️ ' + agoText((item.age_hours || 0) * 3600) + '</span>' +
        (item.assets || []).map(function (a) { return '<span class="badge sm b-asset">' + esc(a) + '</span>'; }).join('') +
        (item.repeat ? '<span class="badge sm" style="border-color:var(--warn);color:var(--warn)">⚠️ قبلاً منتشر شده</span>' : '') +
      '</div>' +

      (heatChips.length
        ? '<div class="st-heat-strip">' + heatChips.join('') + '</div>'
        : '<div style="font-size:11px;color:var(--ink-4);margin:6px 0">ℹ️ سیگنال شبکه اجتماعی مستقیمی ثبت نشده (بر اساس پوشش و تازگی رتبه‌بندی شده)</div>') +

      '<div class="st-factors-summary">' +
        FACTORS.slice(0, 4).map(function (p) { return bar(p[1], f[p[0]]); }).join('') +
      '</div>' +

      (facts.length
        ? '<details style="margin-top:8px;font-size:11px;color:var(--ink-3)"><summary style="cursor:pointer;color:var(--cu-txt)">🔍 شاهدهای تقاضا (' +
          fa(facts.length) + ' مورد)</summary><div style="margin-top:6px;line-height:1.8">' + facts.join('<br>') + '</div></details>'
        : '') +

      '<div class="st-item-footer">' +
        '<div style="font-size:11.5px;color:var(--ink-3)">💡 ' + esc(fmt.why || '') + '</div>' +
        '<div style="display:flex;gap:8px;align-items:center">' +
          '<button type="button" class="btn sm on st-draft-btn ' + (isDrafting ? 'loading' : '') + '" ' +
            'onclick="Studio.draft(' + jsArg(item.id) + ')">' +
            (isDrafting
              ? '<span class="spinner" style="width:14px;height:14px"></span> در حال نگارش...'
              : '<svg class="ic"><use href="#i-bulb"/></svg> <span>ساخت پیش‌نویس (AI)</span>') +
          '</button>' +
          '<button type="button" class="btn sm ghost" title="کارت خبر آمادهٔ انتشار — PNG ۱۰۸۰×۱۳۵۰" ' +
            'onclick="Studio.openCard(' + jsArg(item.id) + ')">' +
            '<svg class="ic"><use href="#i-file"/></svg> کارت تصویری</button>' +
          (item.link && safeUrl(item.link)
            ? '<a class="btn sm ghost" href="' + esc(safeUrl(item.link)) + '" target="_blank" rel="noopener noreferrer">' +
              '<svg class="ic"><use href="#i-external"/></svg> خبر اصلی</a>'
            : '') +
        '</div>' +
      '</div>' +
    '</article>';
  }

  function updateKPIs() {
    const feed = S.feed || {};
    const items = feed.items || [];
    const countEl = el('kpiStudioCount');
    const corpusEl = el('kpiStudioCorpus');
    const topAssetEl = el('kpiStudioTopAsset');
    const assetHeatEl = el('kpiStudioAssetHeat');
    const sigEl = el('kpiStudioSignals');
    const gateEl = el('kpiStudioGate');

    if (countEl) countEl.textContent = fa(items.length);
    if (corpusEl) corpusEl.textContent = 'از میان ' + fa(feed.corpus || 0) + ' خبر بررسی شده';

    // Find top asset
    const assetCounts = {};
    items.forEach(function (it) {
      (it.assets || []).forEach(function (a) {
        assetCounts[a] = (assetCounts[a] || 0) + (it.score || 1);
      });
    });
    let topA = 'BTC';
    let maxA = 0;
    Object.keys(assetCounts).forEach(function (k) {
      if (assetCounts[k] > maxA) { maxA = assetCounts[k]; topA = k; }
    });
    if (topAssetEl) topAssetEl.textContent = topA;
    if (assetHeatEl) assetHeatEl.textContent = 'بیشترین تمرکز سوژه‌های داغ';

    // Gate
    const gateVal = ((feed.status || {}).gate || 0.6) * 100;
    if (gateEl) gateEl.textContent = fa(gateVal.toFixed(0)) + '٪';

    // Providers
    const provs = S.providers || [];
    const readyProvs = provs.filter(function (p) { return p.ready && !p.error; });
    if (sigEl) {
      sigEl.textContent = fa(readyProvs.length) + ' / ' + fa(provs.length) + ' منبع';
    }
  }

  function renderFeed() {
    const host = el('stList');
    if (!host) return;

    const filtered = getFilteredItems();
    const totalCount = ((S.feed || {}).items || []).length;

    const resCountEl = el('stResultsCount');
    if (resCountEl) {
      resCountEl.textContent = 'نمایش ' + fa(filtered.length) + ' سوژه از ' + fa(totalCount);
    }

    if (!filtered.length) {
      host.innerHTML = '<div class="st-empty">' +
        '<div style="font-size:32px;margin-bottom:8px">🔍</div>' +
        '<div style="font-size:14px;color:var(--ink-2);font-weight:600">سوژه‌ای با فیلترهای انتخابی یافت نشد</div>' +
        '<div style="font-size:12px;color:var(--ink-4);margin-top:4px">می‌توانید فیلترها را پاک کنید یا کلمه دیگری جستجو نمایید.</div>' +
        '<button type="button" class="btn sm ghost" style="margin-top:12px" onclick="Studio.clearFilters()">پاک کردن فیلترها</button>' +
        '</div>';
      return;
    }

    host.innerHTML = filtered.map(function (it, i) { return itemCard(it, i + 1); }).join('');
  }

  function renderProviders() {
    const host = el('stProv');
    if (!host) return;
    host.innerHTML = (S.providers || []).map(function (p) {
      const age = p.age === null || p.age === undefined ? null : Math.round(p.age);
      const cls = p.error ? (p.ready ? 'old' : 'bad') : '';
      const title = p.error ? ('آخرین خطا: ' + p.error) : (p.ready ? 'داده دریافت شده' : 'هنوز داده‌ای نیست');
      return '<span class="' + cls + '" title="' + esc(title) + '">' + esc(p.label || p.key) +
             (age === null ? '' : ' · ' + agoText(age)) + '</span>';
    }).join('');
  }

  async function load(force) {
    if (S.busy) return;
    S.busy = true;
    const host = el('stList');
    if (host && !S.feed) {
      host.innerHTML = '<div class="st-empty"><span class="spinner"></span> در حال رتبه‌بندی هوشمند اخبار…</div>';
    }
    try {
      const r = await fetch('/api/studio/feed?limit=40' + (force ? '&refresh=1' : ''));
      const j = await r.json();
      if (!j || j.ok === false) throw new Error((j && j.error) || ('HTTP ' + r.status));
      S.feed = j;
      S.providers = j.providers || [];
      updateKPIs();
      renderFeed();
      renderProviders();
      const stamp = el('stStamp');
      if (stamp) {
        stamp.textContent = 'به‌روزرسانی ' + agoText(j.generated_ts ? Date.now() / 1000 - j.generated_ts : null);
      }
    } catch (e) {
      if (host) host.innerHTML = '<div class="st-note">دریافت فهرست ناموفق بود: ' + esc(e && e.message || '') + '</div>';
    }
    S.busy = false;
  }

  /* ── Filter Controls ─────────────────────────────────────────────────────── */
  function setFilter(key, val) {
    S.filters[key] = val;
    if (key === 'format') {
      document.querySelectorAll('.st-format-btn[data-fmt]').forEach(function (btn) {
        const isAct = btn.getAttribute('data-fmt') === val;
        btn.classList.toggle('active', isAct);
      });
    }
    renderFeed();
  }

  function toggleDemandOnly() {
    S.filters.demandOnly = !S.filters.demandOnly;
    const btn = el('stDemandToggle');
    if (btn) btn.classList.toggle('active', S.filters.demandOnly);
    renderFeed();
  }

  function clearFilters() {
    S.filters = {
      search: '',
      format: 'all',
      asset: 'all',
      sortBy: 'score',
      demandOnly: false,
    };
    const sInput = el('stSearchInput');
    if (sInput) sInput.value = '';
    const aSelect = el('stAssetSelect');
    if (aSelect) aSelect.value = 'all';
    const sSelect = el('stSortSelect');
    if (sSelect) sSelect.value = 'score';
    const dBtn = el('stDemandToggle');
    if (dBtn) dBtn.classList.remove('active');
    document.querySelectorAll('.st-format-btn[data-fmt]').forEach(function (btn) {
      btn.classList.toggle('active', btn.getAttribute('data-fmt') === 'all');
    });
    renderFeed();
  }

  function toggleConfig() {
    const details = el('stCfgDetails');
    if (details) {
      details.open = !details.open;
      if (details.open) details.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  function closeDraft() {
    S.draft = null;
    S.draftId = 0;
    const host = el('stDetail');
    if (host) host.innerHTML = '';
  }

  /* ── slide rendering ────────────────────────────────────────────────────── */
  const BODY_FONT = 'Tahoma, "Segoe UI", "Iranian Sans", sans-serif';

  function wrap(text, perLine) {
    const words = String(text || '').split(/\s+/).filter(Boolean);
    const lines = [];
    let line = '';
    words.forEach(function (w) {
      if ((line + ' ' + w).trim().length > perLine) { if (line) lines.push(line.trim()); line = w; }
      else line = (line + ' ' + w).trim();
    });
    if (line) lines.push(line.trim());
    return lines;
  }

  function esc4xml(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&apos;');
  }

  function slideSvg(slide, index, total, meta) {
    const title = String((slide && slide.title) || '').trim();
    const body = String((slide && slide.body) || '').trim();
    const titleLines = wrap(title, 24).slice(0, 3);
    const bodyLines = wrap(body, body.length > 260 ? 40 : 30).slice(0, 12);
    const pad = 84;
    let y = 300;
    let t = '';
    titleLines.forEach(function (line) {
      t += '<text x="' + (SLIDE_W - pad) + '" y="' + y + '" text-anchor="end" direction="rtl" ' +
           'font-size="76" font-weight="700" fill="#EFE8DD">' + esc4xml(line) + '</text>';
      y += 96;
    });
    y += 40;
    bodyLines.forEach(function (line) {
      t += '<text x="' + (SLIDE_W - pad) + '" y="' + y + '" text-anchor="end" direction="rtl" ' +
           'font-size="46" fill="#CFC6B8">' + esc4xml(line) + '</text>';
      y += 66;
    });
    const footer = esc4xml((meta.source || '') + ' · اعتبار ' +
      fa(((meta.credibility || 0) * 100).toFixed(0)) + '٪ — این محتوا توصیهٔ سرمایه‌گذاری نیست');
    return '<svg xmlns="http://www.w3.org/2000/svg" width="' + SLIDE_W + '" height="' + SLIDE_H + '" ' +
      'viewBox="0 0 ' + SLIDE_W + ' ' + SLIDE_H + '">' +
      '<rect width="' + SLIDE_W + '" height="' + SLIDE_H + '" fill="#0B0A09"/>' +
      '<rect x="' + pad + '" y="' + pad + '" width="' + (SLIDE_W - pad * 2) + '" height="' + (SLIDE_H - pad * 2) +
        '" fill="none" stroke="rgba(236,224,206,.18)" stroke-width="2"/>' +
      '<rect x="' + pad + '" y="' + pad + '" width="10" height="160" fill="#C8965D"/>' +
      '<text x="' + (SLIDE_W - pad) + '" y="' + (pad + 62) + '" text-anchor="end" direction="rtl" ' +
        'font-size="34" fill="#C8965D" font-family="' + BODY_FONT + '">FREEBUFF STUDIO</text>' +
      '<text x="' + pad + '" y="' + (SLIDE_H - pad - 90) + '" text-anchor="start" direction="rtl" ' +
        'font-size="34" fill="#918779" font-family="' + BODY_FONT + '">' + fa(index) + ' / ' + fa(total) + '</text>' +
      '<text x="' + (SLIDE_W - pad) + '" y="' + (SLIDE_H - pad - 90) + '" text-anchor="end" direction="rtl" ' +
        'font-size="30" fill="#918779" font-family="' + BODY_FONT + '">' + footer + '</text>' +
      '<g font-family="' + BODY_FONT + '">' + t + '</g>' +
    '</svg>';
  }

  function svgToPng(svg, scale) {
    return new Promise(function (resolve, reject) {
      const img = new Image();
      img.onload = function () {
        const canvas = document.createElement('canvas');
        canvas.width = SLIDE_W * (scale || 1);
        canvas.height = SLIDE_H * (scale || 1);
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#0B0A09';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        try { resolve(canvas.toDataURL('image/png')); }
        catch (e) { reject(e); }
      };
      img.onerror = function () { reject(new Error('تصویرسازی اسلاید ناموفق بود')); };
      img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
    });
  }

  function download(name, dataUrl) {
    const a = document.createElement('a');
    a.href = dataUrl;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  function draftSlides() {
    const d = (S.draft && S.draft.draft) || {};
    const slides = d.slides || [];
    if (slides.length) return slides;
    return [{ title: (S.draft && S.draft.title) || 'خبر', body: d.caption || '' }];
  }

  function slideMeta() {
    const d = S.draft || {};
    return { source: d.source || '', credibility: d.credibility || 0,
    openCard: openCard,
  };
  }

  function renderSlides() {
    const host = el('stSlides');
    if (!host) return;
    const slides = draftSlides();
    host.innerHTML = slides.map(function (s, i) {
      return '<div class="st-slide-card">' +
        '<div>' +
          '<div class="st-slide-top-bar"></div>' +
          '<div class="st-slide-h">' + esc(s.title || '') + '</div>' +
          '<div class="st-slide-p">' + esc(s.body || '') + '</div>' +
        '</div>' +
        '<div class="st-slide-bottom">' +
          '<span>اسلاید ' + fa(i + 1) + ' از ' + fa(slides.length) + '</span>' +
          '<button type="button" class="btn xs ghost" style="padding:2px 8px;font-size:10px" onclick="Studio.png(' + i + ')">' +
            '⬇️ دانلود PNG</button>' +
        '</div>' +
      '</div>';
    }).join('');
  }

  function renderDraft() {
    const host = el('stDetail');
    if (!host) return;
    const wrap = S.draft;
    if (!wrap) { host.innerHTML = ''; return; }
    const d = wrap.draft || {};
    const isAi = (d.method === 'ai');
    const method = isAi
      ? '🤖 هوش مصنوعی (OpenRouter)'
      : 'قالب‌محور از متن خبر';
    const scenes = (d.scenes || []).map(function (sc) {
      return '<li style="margin-bottom:12px"><b>⏱️ ' + esc(sc.sec || '') + ' ثانیه</b> — <span style="line-height:1.8">' + esc(sc.narration || '') + '</span>' +
             (sc.on_screen ? '<div style="font-size:11px;color:var(--cu-txt);margin-top:4px">🎬 تصویر روی صفحه: ' + esc(sc.on_screen) + '</div>' : '') + '</li>';
    }).join('');
    const tags = (d.hashtags || []).map(function (t) { return esc(t); }).join(' ');

    host.innerHTML =
      '<div class="st-workspace" id="stWorkspace">' +
        '<div class="st-workspace-head">' +
          '<div class="st-workspace-title">' +
            '<span style="font-size:1.2em">⚡</span>' +
            '<span>میز کار تولید محتوا: ' + esc(wrap.title || wrap.article_id || '') + '</span>' +
            '<span class="badge sm" style="background:var(--cu-wash);color:var(--cu-txt);border-color:var(--cu-line)">' + esc(method) + '</span>' +
            '<span class="badge sm">امتیاز ' + fa(Number(wrap.score || 0).toFixed(1)) + '</span>' +
          '</div>' +
          '<button type="button" class="btn sm ghost" onclick="Studio.closeDraft()" title="بستن میز کار">' +
            '<svg class="ic"><use href="#i-x"/></svg> <span>بستن</span>' +
          '</button>' +
        '</div>' +

        (d.ai_error ? '<div class="st-note">⚠️ ' + esc(d.ai_error) + '</div>' : '') +

        '<div class="st-tabs-modern" role="tablist">' +
          [
            ['text', '📝 متن و کپشن'],
            ['carousel', '🎨 اسلایدهای کاروسل (' + fa(draftSlides().length) + ')'],
            ['script', '🎬 سناریوی ویدیو'],
            ['telegram', '🚀 ارسال به تلگرام'],
            ['bale', '💬 ارسال به بله']
          ].map(function (pair) {
            const k = pair[0], label = pair[1];
            return '<button type="button" role="tab" class="st-tab-btn' + (S.tab === k ? ' on' : '') +
              '" aria-selected="' + (S.tab === k ? 'true' : 'false') +
              '" onclick="Studio.pane(' + jsArg(k) + ')">' + label + '</button>';
          }).join('') +
        '</div>' +

        /* Tab 1: Text / Caption */
        '<div class="st-pane-box" id="stPaneText" ' + (S.tab === 'text' ? '' : 'hidden') + '>' +
          '<label style="font-size:12px;color:var(--ink-3);display:block;margin-bottom:6px">کپشن اینستاگرام / متن تلگرام (قابل ویرایش مستقیم):</label>' +
          '<textarea class="st-caption-editor" id="stCaption" oninput="Studio.onCaptionChange(this.value)">' + esc(d.caption || '') + '</textarea>' +
          (tags ? '<div class="st-tags" style="margin-top:8px"><b>هشتگ‌ها:</b> ' + tags + '</div>' : '') +
          '<div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px;flex-wrap:wrap;gap:8px">' +
            '<div style="display:flex;gap:8px">' +
              '<button type="button" class="btn sm on" onclick="Studio.copy(' + "'stCaption'" + ')">' +
                '<svg class="ic"><use href="#i-copy"/></svg> کپی متن کامل</button>' +
              '<button type="button" class="btn sm ghost" onclick="Studio.deck()">' +
                '<svg class="ic"><use href="#i-file"/></svg> چاپ / PDF</button>' +
            '</div>' +
            '<div style="font-size:11px;color:var(--ink-4)" id="stCharCount">' +
              fa((d.caption || '').length) + ' کاراکتر · ' + fa((d.caption || '').split(/\s+/).filter(Boolean).length) + ' کلمه' +
            '</div>' +
          '</div>' +
        '</div>' +

        /* Tab 2: Carousel */
        '<div class="st-pane-box" id="stPaneCarousel" ' + (S.tab === 'carousel' ? '' : 'hidden') + '>' +
          '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">' +
            '<span style="font-size:12px;color:var(--ink-2)">پیش‌نمایش اسلایدهای کاروسل (آماده برای اینستاگرام و لینکدین):</span>' +
            '<div style="display:flex;gap:8px">' +
              '<button type="button" class="btn sm on" onclick="Studio.pngAll()">' +
                '<svg class="ic"><use href="#i-drop"/></svg> دانلود همه اسلایدها (ZIP/PNG)</button>' +
              '<button type="button" class="btn sm ghost" onclick="Studio.deck()">' +
                '<svg class="ic"><use href="#i-file"/></svg> چاپ به PDF</button>' +
            '</div>' +
          '</div>' +
          '<div class="st-slides-grid" id="stSlides"></div>' +
        '</div>' +

        /* Tab 3: Video Script */
        '<div class="st-pane-box" id="stPaneScript" ' + (S.tab === 'script' ? '' : 'hidden') + '>' +
          '<div style="font-size:12px;color:var(--ink-2);margin-bottom:10px">سناریوی ثانیه‌به‌ثانیه ویدیو برای ریلز، تیک‌تاک و شورتز:</div>' +
          '<ol class="st-script">' + (scenes || '<li>اسکریپتی تولید نشد.</li>') + '</ol>' +
          '<div class="st-actions">' +
            '<button type="button" class="btn sm on" onclick="Studio.copy(' + "'stScript'" + ')">' +
              '<svg class="ic"><use href="#i-copy"/></svg> کپی اسکریپت ویدیو</button>' +
          '</div>' +
          '<pre class="st-pre" id="stScript" hidden>' +
            esc((d.scenes || []).map(function (s) { return s.sec + ' ثانیه — گوینده: ' + s.narration + (s.on_screen ? ' (تصویر: ' + s.on_screen + ')' : ''); }).join('\n')) + '</pre>' +
        '</div>' +

        /* Tab 4: Telegram Publish */
        '<div class="st-pane-box" id="stPaneTelegram" ' + (S.tab === 'telegram' ? '' : 'hidden') + '>' +
          '<div style="font-size:12px;color:var(--ink-2);margin-bottom:10px">ارسال مستقیم متن و اسلایدها به کانال تلگرام تنظیم شده:</div>' +
          '<div id="stPublish"></div>' +
          '<div class="st-actions">' +
            '<button type="button" class="btn sm on" onclick="Studio.publish(false, \'telegram\')">' +
              '<svg class="ic"><use href="#i-send"/></svg> بررسی پیش‌نمایش و تایید ارسال به تلگرام</button>' +
          '</div>' +
        '</div>' +

        /* Tab 5: Bale Publish */
        '<div class="st-pane-box" id="stPaneBale" ' + (S.tab === 'bale' ? '' : 'hidden') + '>' +
          '<div style="font-size:12px;color:var(--ink-2);margin-bottom:10px">ارسال مستقیم متن به کانال یا گروه پیام‌رسان بله:</div>' +
          '<div id="stPublishBale"></div>' +
          '<div class="st-actions">' +
            '<button type="button" class="btn sm on" onclick="Studio.publish(false, \'bale\')">' +
              '<span style="margin-left:4px">💬</span> بررسی پیش‌نمایش و تایید ارسال به بله</button>' +
          '</div>' +
        '</div>' +

      '</div>';

    renderSlides();
    const ws = el('stWorkspace');
    if (ws) ws.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  async function draft(articleId) {
    if (!articleId || S.draftLoadingId) return;
    S.draftLoadingId = articleId;
    renderFeed(); // updates button to spinner
    try {
      const r = await fetch('/api/studio/draft', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ article_id: articleId }),
      });
      const j = await r.json();
      if (!j || j.ok === false) throw new Error((j && j.error) || ('HTTP ' + r.status));
      S.draft = j;
      S.draftId = j.id || 0;
      S.tab = 'text';
      renderDraft();
      if (typeof toast === 'function') toast('پیش‌نویس محتوا با موفقیت آماده شد');
    } catch (e) {
      if (typeof toast === 'function') toast('خطا در ساخت پیش‌نویس: ' + (e && e.message || ''));
    }
    S.draftLoadingId = null;
    renderFeed(); // resets button state
  }

  function pane(which) {
    S.tab = which;
    ['text', 'carousel', 'script', 'telegram', 'bale'].forEach(function (k) {
      const map = { text: 'stPaneText', carousel: 'stPaneCarousel', script: 'stPaneScript', telegram: 'stPaneTelegram', bale: 'stPaneBale' };
      const node = el(map[k]);
      if (node) node.hidden = (k !== which);
    });
    document.querySelectorAll('#stWorkspace .st-tab-btn').forEach(function (b) {
      const isAct = b.textContent.includes({ text: 'متن', carousel: 'کاروسل', script: 'ویدیو', telegram: 'تلگرام', bale: 'بله' }[which]);
      b.classList.toggle('on', isAct);
      b.setAttribute('aria-selected', isAct ? 'true' : 'false');
    });
    if (which === 'telegram' || which === 'bale') {
      publish(false, which); // trigger dry-run preview
    }
  }

  function onCaptionChange(val) {
    if (S.draft && S.draft.draft) {
      S.draft.draft.caption = val;
    }
    const cc = el('stCharCount');
    if (cc) {
      cc.textContent = fa(val.length) + ' کاراکتر · ' + fa(val.split(/\s+/).filter(Boolean).length) + ' کلمه';
    }
  }

  function copy(id) {
    const node = el(id);
    if (!node || !navigator.clipboard) return;
    const text = node.value || node.textContent || '';
    navigator.clipboard.writeText(text).then(function () {
      if (typeof toast === 'function') toast('متن با موفقیت در کلیپ‌بورد کپی شد');
    }).catch(function () {
      if (typeof toast === 'function') toast('متن کپی شد');
    });
  }

  async function png(index) {
    try {
      const slides = draftSlides();
      const svg = slideSvg(slides[index] || {}, index + 1, slides.length, slideMeta());
      download('freebuff-slide-' + (index + 1) + '.png', await svgToPng(svg, 1));
      if (typeof toast === 'function') toast('تصویر اسلاید ' + fa(index + 1) + ' دانلود شد');
    } catch (e) {
      if (typeof toast === 'function') toast('خروجی PNG ناموفق بود');
    }
  }

  async function pngAll() {
    const slides = draftSlides();
    if (typeof toast === 'function') toast('در حال دانلود ' + fa(slides.length) + ' اسلاید...');
    for (let i = 0; i < slides.length; i++) {
      await png(i);
      await new Promise(function (r) { setTimeout(r, 300); });
    }
  }

  function deck() {
    const slides = draftSlides();
    const meta = slideMeta();
    const html = slides.map(function (s, i) {
      return '<section class="deck-slide"><div class="deck-k">FREEBUFF STUDIO</div>' +
        '<h2>' + esc(s.title || '') + '</h2><p>' + esc(s.body || '') + '</p>' +
        '<div class="deck-f">' + esc(meta.source) + ' · اسلاید ' + fa(i + 1) + ' از ' + fa(slides.length) +
        ' — این محتوا توصیهٔ سرمایه‌گذاری نیست</div></section>';
    }).join('');
    const w = window.open('', '_blank');
    if (!w) { if (typeof toast === 'function') toast('پنجرهٔ چاپ باز نشد'); return; }
    w.document.write('<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">' +
      '<title>FREEBUFF — Slides</title><style>' +
      '@page{size:1080px 1350px;margin:0}body{margin:0;background:#0B0A09;font-family:Tahoma,sans-serif}' +
      '.deck-slide{width:1080px;height:1350px;box-sizing:border-box;padding:84px;color:#EFE8DD;' +
      'page-break-after:always;display:flex;flex-direction:column;justify-content:center}' +
      '.deck-k{color:#C8965D;font-size:34px;margin-bottom:40px}' +
      '.deck-slide h2{font-size:72px;line-height:1.3;margin:0 0 32px}' +
      '.deck-slide p{font-size:46px;line-height:1.6;color:#CFC6B8;margin:0}' +
      '.deck-f{position:absolute;bottom:60px;color:#918779;font-size:28px}' +
      '</style></head><body>' + html + '</body></html>');
    w.document.close();
    setTimeout(function () { try { w.print(); } catch (e) { } }, 400);
  }

  async function publish(confirmSend, channel) {
    channel = channel || (S.tab === 'bale' ? 'bale' : 'telegram');
    const isBale = (channel === 'bale');
    const hostId = isBale ? 'stPublishBale' : 'stPublish';
    const endpoint = isBale ? '/api/studio/publish/bale' : '/api/studio/publish/telegram';
    const channelName = isBale ? 'پیام‌رسان بله' : 'کانال تلگرام';

    const d = (S.draft && S.draft.draft) || {};
    const text = (d.caption || '') +
      (d.hashtags && d.hashtags.length ? '\n\n' + d.hashtags.join(' ') : '');
    let photos = [];
    if (!isBale) {
      if (S.pending && S.pending.photos) {
        photos = S.pending.photos;
      } else if (confirmSend) {
        const slides = draftSlides().slice(0, 3);
        for (let i = 0; i < slides.length; i++) {
          try { photos.push(await svgToPng(slideSvg(slides[i], i + 1, slides.length, slideMeta()), 1)); }
          catch (e) { }
        }
      }
    }
    const body = { text: text, photos: photos, content_id: S.draftId, confirm: !!confirmSend };
    try {
      const r = await fetch(endpoint, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      });
      const j = await r.json();
      const host = el(hostId);
      if (!j || j.ok === false) {
        if (host) host.innerHTML = '<div class="st-note" style="border-color:var(--dn-line);color:var(--dn)">❌ ' + esc((j && j.hint) || (j && j.error) || 'ارسال ناموفق بود') + '</div>';
        return;
      }
      if (j.dry_run) {
        S.pending = { photos: photos };
        if (host) {
          host.innerHTML = '<div class="st-note" style="background:var(--bg-deep);border:1px solid var(--rule);color:var(--ink-1)">' +
            '<div style="font-weight:700;margin-bottom:6px">📋 پیش‌نمایش ارسال به ' + channelName + ' (تایید نهایی):</div>' +
            '<div>تعداد کاراکتر متن: ' + fa(j.text_chars || 0) + (j.images ? ' · تعداد تصاویر اسلاید: ' + fa(j.images) : '') + '</div>' +
            '<div class="st-preview" style="margin:8px 0;max-height:120px;overflow-y:auto">' + esc((j.preview || '').slice(0, 400)) + '</div>' +
            '<button type="button" class="btn sm on" onclick="Studio.publish(true, \'' + channel + '\')">' +
              '<svg class="ic"><use href="#i-send"/></svg> تایید و ارسال نهایی به ' + channelName + '</button>' +
            '</div>';
        }
        return;
      }
      S.pending = null;
      if (host) host.innerHTML = '<div class="st-note" style="border-color:var(--up-line);color:var(--up)">✅ ' + (j.ok_all ? 'محتوا با موفقیت به ' + channelName + ' ارسال شد.' : 'ارسال انجام شد اما برخی بخش‌ها خطا داد.') + '</div>';
      if (typeof toast === 'function') toast('محتوا به ' + channelName + ' ارسال شد');
    } catch (e) {
      const host = el(hostId);
      if (host) host.innerHTML = '<div class="st-note" style="border-color:var(--dn-line);color:var(--dn)">ارتباط برقرار نشد: ' + esc(e && e.message || '') + '</div>';
    }
  }

  async function loadConfig() {
    try {
      const r = await fetch('/api/studio/config');
      const j = await r.json();
      if (!j || !j.ok || !j.config) return;
      const cfg = j.config;
      const gate = el('stGate'), tg = el('stTg'), auto = el('stAuto');
      if (gate && cfg.credibility_gate != null) gate.value = cfg.credibility_gate;
      if (tg && cfg.telegram_channels) {
        tg.value = Array.isArray(cfg.telegram_channels) ? cfg.telegram_channels.join(', ') : cfg.telegram_channels;
      }
      if (auto && cfg.auto_post) {
        auto.checked = !!cfg.auto_post.telegram;
      }
    } catch (e) { }
  }

  async function config(values) {
    try {
      const r = await fetch('/api/studio/config', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      const j = await r.json();
      if (typeof toast === 'function') toast(j && j.ok ? 'تنظیمات با موفقیت ذخیره شد' : 'ذخیره نشد');
      return j;
    } catch (e) {
      if (typeof toast === 'function') toast('ذخیرهٔ تنظیمات ناموفق بود');
      return null;
    }
  }

  function saveConfig() {
    const gate = el('stGate'), tg = el('stTg'), yt = el('stYtKey'),
          igTok = el('stIgToken'), igId = el('stIgId'), auto = el('stAuto');
    const values = {};
    if (gate && gate.value !== '') values.credibility_gate = gate.value;
    if (tg) values.telegram_channels = tg.value;
    if (yt && yt.value) values.youtube_key = yt.value;
    if (igTok && igTok.value) values.instagram_token = igTok.value;
    if (igId && igId.value) values.instagram_user_id = igId.value;
    if (auto) values.auto_post = { telegram: !!auto.checked, require_confirm: false };
    return config(values).then(function (res) {
      if (res && res.ok) load(true);
    });
  }

  async function autoPostNow() {
    if (typeof toast === 'function') toast('در حال ارسال بهترین خبر به تلگرام...');
    try {
      const r = await fetch('/api/studio/autopost/now', { method: 'POST' });
      const j = await r.json();
      if (j && j.ok) {
        if (typeof toast === 'function') toast('✅ خبر «' + (j.title || '').slice(0, 30) + '» به تلگرام ارسال شد');
      } else {
        if (typeof toast === 'function') toast('❌ خطا در ارسال: ' + ((j && j.error) || 'نامشخص'));
      }
    } catch (e) {
      if (typeof toast === 'function') toast('❌ ارتباط با سرور برقرار نشد');
    }
  }

  async function mount() {
    loadConfig();
    if (!S.feed) await load(false);
    else { renderFeed(); renderProviders(); updateKPIs(); }
  }

  async function refresh() {
    if (typeof toast === 'function') toast('در حال تازه‌سازی سیگنال‌های زنده...');
    try { await fetch('/api/studio/signals/refresh', { method: 'POST' }); } catch (e) { }
    S.feed = null;
    await load(true);
  }

  function openCard(id) {
    window.open('/api/studio/card?aid=' + encodeURIComponent(id), '_blank');
  }

  return {
    mount: mount,
    refresh: refresh,
    draft: draft,
    pane: pane,
    copy: copy,
    png: png,
    pngAll: pngAll,
    deck: deck,
    publish: publish,
    saveConfig: saveConfig,
    autoPostNow: autoPostNow,
    setFilter: setFilter,
    toggleDemandOnly: toggleDemandOnly,
    clearFilters: clearFilters,
    toggleConfig: toggleConfig,
    closeDraft: closeDraft,
    onCaptionChange: onCaptionChange,
    _s: S
  };
})();
window.Studio = Studio;
