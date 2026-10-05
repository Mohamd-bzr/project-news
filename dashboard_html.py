#!/usr/bin/env python3
"""
Dashboard UI — one self-contained Persian RTL page (plain string, no Jinja).
Kept in its own module so the Flask backend stays readable.
"""

APP_HTML = r"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="MOHMD NEWS — ترمینال هوش بازار: خوشه‌بندی خبرهای منابع آزاد، تلمتری دارایی‌ها، تقویم اقتصادی و گزارش‌های نهادی (آفلاین‌پذیر)">
<meta name="theme-color" content="#0C111C">
<meta name="color-scheme" content="dark">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700;800&family=Vazirmatn:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" type="image/png" href="/icons/icon-192.png">
<link rel="apple-touch-icon" href="/icons/icon-192.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="MOHMD NEWS">
<title>MOHMD NEWS — Market Intelligence</title>
<style>
/* ═══════════════════════════════════════════════════════════════════════════
   MOHMD NEWS — DESIGN LANGUAGE 3 · ENGRAVED INSTRUMENT → DESIGN LANGUAGE 6 "MIDNIGHT TERMINAL"
   Deep midnight navy, cool ink, one electric-blue live accent, saturated market
   green/red. Hairlines instead of card-stacks; Vazirmatn for prose, IBM Plex
   Mono for figures; tabular numbers; RTL logical.
   Token names (--cu, --ink, --panel) stay so the rest of the sheet remaps.
   ═══════════════════════════════════════════════════════════════════════════ */

/* ── 1 · TOKENS ────────────────────────────────────────────────────────────
   The only custom-property block in the file. Nothing below re-declares one. */
:root{
  /* surfaces — midnight navy, deeper than the old slate */
  --bg:#0C111C;
  --bg-deep:#080C15;
  --panel:#121826;
  --panel-2:#171E2B;
  --panel-3:#1D2432;
  --panel-4:#263041;
  --sheet:rgba(18,24,38,.97);
  --wash:rgba(224,236,252,.04);
  --wash-2:rgba(224,236,252,.07);
  --wash-3:rgba(224,236,252,.10);

  /* hairlines — cool steel, never warm ivory */
  --rule:rgba(154,182,224,.11);
  --rule-2:rgba(154,182,224,.06);
  --rule-3:rgba(154,182,224,.22);
  --rule-strong:rgba(154,182,224,.32);

  /* ink ramp — cool paper on midnight navy; --ink-4 stays ≥4.5:1 on --panel-3 */
  --ink-1:#F1F4F9;
  --ink-2:#D2D9E3;
  --ink-3:#AFB9C8;
  --ink-4:#8D99AB;

  /* signature: electric blue (the live wire), applied sparingly */
  --cu:#6C97DC;
  --cu-hi:#93B6E8;
  --cu-2:#4A7BC0;
  --cu-txt:#DCE6F4;
  --cu-wash:rgba(108,151,220,.11);
  --cu-wash-2:rgba(108,151,220,.17);
  --cu-line:rgba(108,151,220,.30);
  --cu-line-2:rgba(108,151,220,.52);

  --up:#2EBD77;
  --up-wash:rgba(46,189,119,.11);
  --up-line:rgba(46,189,119,.30);
  --dn:#EE6A58;
  --dn-wash:rgba(238,106,88,.11);
  --dn-line:rgba(238,106,88,.30);
  --warn:#E8A23C;
  --warn-wash:rgba(232,162,60,.12);
  --info:#5FA8D3;
  --info-wash:rgba(95,168,211,.12);
  --hol:#8A93A8;

  /* type — 16px base, 1.2 dashboard ratio */
  --font-mono:'IBM Plex Mono','Vazirmatn',ui-monospace,monospace;
  --t-xs:11px;   --t-sm:12.5px;--t-md:14px;   --t-lg:15px;
  --t-xl:17px;  --t-2xl:20px;  --t-3xl:clamp(1.4rem, 1.25rem + 0.7vw, 1.75rem);
  --lh-tight:1.25; --lh:1.55; --lh-fa:1.85;
  --measure:68ch;

  /* spacing — 4px scale only */
  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px; --s6:32px; --s7:48px; --s8:64px;

  --r1:4px; --r2:8px; --r3:12px; --r-pill:999px;

  --dur-1:120ms; --dur-2:200ms; --dur-3:320ms;
  --ease:cubic-bezier(.16,1,.3,1);

  --sh-1:0 8px 24px -12px rgba(0,0,0,.55);
  --sh-2:0 24px 56px -20px rgba(0,0,0,.72);
  --inset-hi:inset 0 1px 0 rgba(255,255,255,.04);
  --well:inset 0 1px 0 rgba(0,0,0,.35);

  --doc:#111726;

  --topbar-h:56px;
  --ticker-h:36px;
  --sidebar-w:240px;
  --sidebar-w-rail:64px;
}

/* ── 2 · BASE ───────────────────────────────────────────────────────────── */
*, *::before, *::after{ box-sizing:border-box; }
html, body{
  margin:0; padding:0; height:100%; width:100%;
  background:var(--bg); color:var(--ink-2);
  font-family:'Vazirmatn','IBM Plex Sans',system-ui,-apple-system,'Segoe UI',sans-serif;
  font-size:var(--t-md); line-height:var(--lh); overflow:hidden;
  letter-spacing:0;
  scroll-padding-block-start:96px;
  -webkit-font-smoothing:antialiased; text-rendering:geometricPrecision;
}
/* Persian body copy gets its own leading; Latin UI keeps the tighter one */
p, li, .fa{ line-height:var(--lh-fa); }
h1, h2, h3, h4, h5{ margin:0; color:var(--ink-1); font-weight:700; line-height:var(--lh-tight); letter-spacing:-.012em; }
h1{ font-size:var(--t-xl); font-weight:800; letter-spacing:-.03em; }
h2{ font-size:var(--t-2xl); }
h3{ font-size:var(--t-xl); }
h4{ font-size:var(--t-lg); }
a{ color:var(--cu); text-decoration:none; }
a:hover{ color:var(--cu-hi); }
b, strong{ color:var(--ink-1); font-weight:600; }
small{ font-size:var(--t-xs); }
code, kbd, pre{ font-family:inherit; }
button, input, select, textarea{ font-family:inherit; font-size:inherit; color:inherit; }
button{ cursor:pointer; }
img{ max-width:100%; }
/* figures: one rule for every number in the product */
.num, .ltr, .prc, .chg, .tk .p, .tk .c, .cal-timer, .cal-countdown,
.telem-item b, .tb-badge, .cnt, .cred, .etfcard .prc, .etfcard .chg, .rf-score,
.c-num, .c-time, .cal-stat b, .cal-day .dd, .cal-weeklab, .dow{
  font-variant-numeric:tabular-nums; font-feature-settings:"tnum" 1;
}
.ltr, .num{ direction:ltr; unicode-bidi:isolate; }
.en{ direction:ltr; text-align:left; }
.visually-hidden{
  position:absolute !important; width:1px; height:1px; padding:0; margin:-1px;
  overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; border:0;
}
::selection{ background:var(--cu-wash-2); color:#fff; }

/* scrollbars — hairline, copper on hover */
*{ scrollbar-width:thin; scrollbar-color:rgba(154,182,224,.16) transparent; }
::-webkit-scrollbar{ width:10px; height:10px; }
::-webkit-scrollbar-track{ background:transparent; }
::-webkit-scrollbar-thumb{
  background:rgba(154,182,224,.14); border:3px solid transparent;
  background-clip:padding-box; border-radius:99px;
}
::-webkit-scrollbar-thumb:hover{ background:rgba(200,150,93,.55); background-clip:padding-box; }

/* one focus ring for every control */
:is(a, button, input, select, textarea, [tabindex], [role="tab"]):focus-visible{
  outline:2px solid var(--cu-hi);
  outline-offset:2px;
  border-radius:var(--r1);
}
.skip-link{
  position:absolute; inset-block-start:var(--s2); inset-inline-start:var(--s2);
  z-index:400; padding:var(--s2) var(--s4);
  background:var(--cu); color:#16140A; font-weight:700; border-radius:var(--r2);
  transform:translateY(-200%);
}
.skip-link:focus{ transform:none; }

/* ── 3 · ICONS ──────────────────────────────────────────────────────────────
   One sprite, one size rule. Glyphs are drawn at 24px and inherit colour. */
.ic{ inline-size:1em; block-size:1em; flex:0 0 auto; display:inline-block;
     vertical-align:-.125em; fill:none; stroke:currentColor; stroke-width:1.6;
     stroke-linecap:round; stroke-linejoin:round; }
/* the separator the chrome strings its fields with: a hairline, not a dot */
.vr{ display:inline-block; inline-size:1px; block-size:.82em; flex:0 0 auto;
     background:var(--rule-3); margin-inline:.58em; vertical-align:-.02em; }
.ic-lg{ font-size:19px; }
.ic-xl{ font-size:24px; }

/* ── 4 · FORMS ──────────────────────────────────────────────────────────── */
select, input[type="text"], input[type="password"], input[type="number"], input[type="search"], textarea{
  min-block-size:34px; padding:6px 10px;
  background:var(--panel-2); border:1px solid var(--rule); border-radius:var(--r2);
  color:var(--ink-1); font-size:var(--t-sm); font-weight:500;
  transition:border-color var(--dur-1) var(--ease), background var(--dur-1) var(--ease);
}
select{
  appearance:none; -webkit-appearance:none; cursor:pointer; padding-inline-end:26px;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6' fill='none' stroke='%23E8B84A' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M1 1.5 5 4.8 9 1.5'/%3E%3C/svg%3E");
  background-repeat:no-repeat; background-position:left 10px center; background-size:10px 6px;
}
select option{ background:var(--panel-2); color:var(--ink-1); }
select:hover, input[type="text"]:hover, input[type="password"]:hover, textarea:hover{ border-color:var(--rule-3); }
select:focus, input:focus, textarea:focus{
  outline:none; border-color:var(--cu); background:var(--panel-3);
  box-shadow:0 0 0 3px var(--cu-wash);
}
input::placeholder, textarea::placeholder{ color:var(--ink-4); }
input[type="checkbox"]{ accent-color:var(--cu); inline-size:15px; block-size:15px; cursor:pointer; }
input[type="range"]{
  -webkit-appearance:none; appearance:none; inline-size:100%; block-size:4px;
  background:linear-gradient(90deg, var(--cu-2), var(--cu)); border-radius:2px; outline:none;
}
input[type="range"]::-webkit-slider-thumb{
  -webkit-appearance:none; appearance:none; inline-size:15px; block-size:15px; border-radius:50%;
  background:var(--cu-hi); border:2px solid var(--bg);
  box-shadow:0 0 0 1px var(--cu-2); cursor:pointer;
}
input[type="range"]::-moz-range-thumb{
  inline-size:13px; block-size:13px; border-radius:50%; background:var(--cu-hi);
  border:2px solid var(--bg); cursor:pointer;
}
/* switch — the same shape in settings and in the telegram toggles */
.switch{ position:relative; inline-size:38px; block-size:22px; flex:0 0 auto; }
.switch input{ opacity:0; inline-size:0; block-size:0; position:absolute; }
.slider{
  position:absolute; inset:0; background:var(--panel-4); border:1px solid var(--rule);
  border-radius:var(--r-pill); cursor:pointer; transition:background var(--dur-2) var(--ease);
}
.slider::before{
  content:""; position:absolute; inline-size:15px; block-size:15px; inset-block-start:2px;
  inset-inline-start:3px; border-radius:50%; background:var(--ink-4); transition:transform var(--dur-2) var(--ease), background var(--dur-2);
}
.switch input:checked + .slider{ background:var(--cu-wash-2); border-color:var(--cu-line); }
.switch input:checked + .slider::before{ transform:translateX(-17px); background:var(--cu); }
html[dir="rtl"] .switch input:checked + .slider::before{ transform:translateX(-17px); }
.switch input:focus-visible + .slider{ box-shadow:0 0 0 3px var(--cu-wash); }

/* generic label + field block used across the settings-style views */
.formgrid{ display:grid; grid-template-columns:repeat(auto-fit, minmax(190px,1fr)); gap:var(--s3); align-items:end; }
.formgrid label, .formgrid > div > label{ display:block; margin-block-end:var(--s1); font-size:var(--t-xs); color:var(--ink-3); font-weight:600; }
.formgrid input, .formgrid select{ inline-size:100%; }
.formgrid .ltr-in{ direction:ltr; text-align:left; }
.asset-toggles{ display:flex; flex-wrap:wrap; gap:var(--s1); margin-block-start:var(--s2); }

/* ── 5 · BUTTONS ────────────────────────────────────────────────────────── */
.btn{
  display:inline-flex; align-items:center; gap:var(--s2); min-block-size:40px; padding:8px 16px;
  background:var(--cu); color:#16140A;
  border:1px solid var(--cu-2); border-radius:var(--r2);
  font-size:var(--t-sm); font-weight:700; letter-spacing:0; white-space:nowrap;
  transition:background var(--dur-1) var(--ease), border-color var(--dur-1) var(--ease), color var(--dur-1);
}
.btn:hover{ background:var(--cu-hi); border-color:var(--cu-hi); }
.btn:active{ transform:translateY(1px); }
.btn:disabled{ opacity:.5; cursor:not-allowed; transform:none; }
.btn.ghost{
  background:var(--wash); border-color:var(--rule); color:var(--ink-2); font-weight:600;
}
.btn.ghost:hover{ background:var(--wash-2); border-color:var(--rule-3); color:var(--ink-1); }
.btn.on{ background:var(--cu-wash-2); border-color:var(--cu-line); color:var(--cu-txt); }
.btn.sm{ min-block-size:28px; padding:3px 10px; font-size:var(--t-xs); }
.iconbtn{
  inline-size:40px; block-size:40px; display:grid; place-items:center;
  background:var(--wash); border:1px solid var(--rule); border-radius:var(--r2);
  color:var(--ink-3); font-size:15px;
}
.iconbtn:hover{ background:var(--wash-2); border-color:var(--cu-line); color:var(--cu-hi); }
.iconbtn.on{ background:var(--cu-wash); border-color:var(--cu-line); color:var(--cu-txt); }

/* ── 6 · APP SHELL ──────────────────────────────────────────────────────────
   A fixed-height frame: topbar, engraved ticker, then a two-column body whose
   only scroller is the main pane. */
.stage{
  position:fixed; inset:0; z-index:0; pointer-events:none;
  background:
    radial-gradient(900px 520px at 92% -8%, rgba(232,184,74,.08), transparent 58%),
    radial-gradient(720px 480px at 0% 108%, rgba(77,164,220,.06), transparent 58%),
    var(--bg);
}
.stage::after{
  content:""; position:absolute; inset:0;
  background:radial-gradient(120% 90% at 50% 30%, transparent 42%, rgba(0,0,0,.5));
}
.app-shell{ position:relative; z-index:1; display:flex; flex-direction:column; block-size:100vh; inline-size:100vw; overflow:hidden; }
.app-body{
  display:flex !important; flex:1; min-block-size:0; inline-size:100%;
  position:relative; overflow:hidden; direction:rtl !important;
}

/* ── TOPBAR ─────────────────────────────────────────────────────────────── */
.app-topbar{
  display:flex; align-items:center; justify-content:space-between; gap:var(--s4);
  block-size:var(--topbar-h); flex:0 0 auto; padding-inline:var(--s4);
  background:var(--panel); border-block-end:1px solid var(--rule); z-index:120;
  box-shadow:inset 0 -2px 0 var(--cu);
}
.brand-group{ display:flex; align-items:center; gap:var(--s3); min-inline-size:0; }
.brand-badge{
  inline-size:32px; block-size:32px; flex:0 0 auto; display:grid; place-items:center;
  border-radius:var(--r2); color:var(--cu-hi);
  background:linear-gradient(160deg, rgba(200,150,93,.22), rgba(200,150,93,.05));
  border:1px solid var(--cu-line); box-shadow:var(--inset-hi);
}
.brand-title-wrap{ display:flex; flex-direction:column; min-inline-size:0; }
.brand-title-row{ display:flex; align-items:center; gap:var(--s2); }
.brand-title-row h1{ font-size:var(--t-lg); font-weight:800; letter-spacing:.01em; white-space:nowrap; }
.brand-desc{ font-size:var(--t-xs); color:var(--ink-4); font-weight:500; white-space:nowrap; }
.live-pill{
  display:inline-flex; align-items:center; gap:5px; padding:2px 8px;
  border:1px solid var(--up-line); background:var(--up-wash); color:var(--up);
  border-radius:var(--r-pill); font-size:var(--t-xs); font-weight:700;
}
.dot{ inline-size:6px; block-size:6px; border-radius:50%; background:var(--up); flex:0 0 auto; }
.dot.busy{ background:var(--cu); animation:blink 1s steps(2, end) infinite; }
.dot.err{ background:var(--dn); }
@keyframes blink{ 50%{ opacity:.25; } }
/* telemetry: a bordered strip with hairline dividers, not a pill.
   direction:ltr — the labels are English, so the row has to lay out left to
   right. Inherited RTL reversed the run into "h 24 Window", which reads as
   gibberish in either direction. */
.topbar-telemetry{
  direction:ltr;
  display:flex; align-items:center; gap:var(--s3); padding:5px 12px;
  background:var(--bg-deep); border:1px solid var(--rule); border-radius:var(--r2);
  font-size:var(--t-xs); color:var(--ink-3); white-space:nowrap;
}
.telem-item{ display:flex; align-items:center; gap:4px; }
.telem-item b{ color:var(--ink-1); font-weight:700; }
.telem-divider{ inline-size:1px; block-size:12px; background:var(--rule); }
.topbar-actions{ display:flex; align-items:center; gap:var(--s2); }
.menu-toggle-btn{
  display:none; inline-size:34px; block-size:34px; place-items:center;
  background:var(--wash); border:1px solid var(--rule); border-radius:var(--r2);
  color:var(--ink-2); font-size:17px;
}

/* ── TICKER — an engraved strip ─────────────────────────────────────────────
   Two identical halves slide exactly -50%; every chip carries its own trailing
   gap so a half's width IS the loop offset. Nothing here may add a flex gap. */
.dl2-ticker{
  position:relative; z-index:110; flex:0 0 auto; block-size:var(--ticker-h);
  overflow:hidden; direction:ltr;
  background:var(--bg-deep); border-block-end:1px solid var(--rule);
  box-shadow:inset 0 1px 0 var(--cu-line);
}
.dl2-ticker::before, .dl2-ticker::after{
  content:""; position:absolute; inset-block:0; inline-size:44px; z-index:2; pointer-events:none;
}
.dl2-ticker::before{ inset-inline-start:0; background:linear-gradient(90deg, var(--bg-deep), transparent); }
.dl2-ticker::after{ inset-inline-end:0; background:linear-gradient(270deg, var(--bg-deep), transparent); }
.dl2-ticker .tk-track{
  display:flex; inline-size:max-content; block-size:100%; gap:0; padding:0;
  will-change:transform; animation:tkRoll var(--tk-dur, 60s) linear infinite;
}
.dl2-ticker:hover .tk-track{ animation-play-state:paused; }
@keyframes tkRoll{ from{ transform:translateX(0); } to{ transform:translateX(-50%); } }
.dl2-ticker .tk-half{ display:flex; align-items:center; flex:0 0 auto; block-size:100%; }
.dl2-ticker .tk-half > *{ margin-inline-end:16px; }
.dl2-ticker .tk{ display:inline-flex; align-items:baseline; gap:5px; font-size:var(--t-xs); }
.dl2-ticker .tk .s{ color:var(--cu-txt); font-weight:700; letter-spacing:.03em; }
.dl2-ticker .tk .p{ color:var(--ink-1); font-weight:700; }
.dl2-ticker .tk .c{ font-size:var(--t-xs); font-weight:600; }
.dl2-ticker .tk.up .c{ color:var(--up); }
.dl2-ticker .tk.dn .c{ color:var(--dn); }
.dl2-ticker .tk .st{ inline-size:4px; block-size:4px; border-radius:50%; background:var(--warn); }
/* the separator stayed in the markup; it is a hairline now, not a diamond */
.dl2-ticker .sep{
  inline-size:1px; block-size:12px; background:var(--rule); color:transparent;
  font-size:0; overflow:hidden; align-self:center;
}

/* ── SIDEBAR — the index rail ───────────────────────────────────────────── */
.app-sidebar{
  inline-size:var(--sidebar-w); flex:0 0 auto; block-size:100%; overflow-y:auto; overflow-x:hidden;
  display:flex; flex-direction:column; gap:1px; padding:var(--s4) var(--s2) var(--s3);
  background:var(--panel); border-left:1px solid var(--rule) !important; border-right:none !important; z-index:100;
  transition:inline-size var(--dur-3) var(--ease), transform var(--dur-3) var(--ease);
}
html[dir="ltr"] .app-main{ direction:ltr !important; }
html[dir="rtl"] .app-main{ direction:rtl !important; }
html[dir="ltr"] .app-sidebar{ direction:ltr !important; }
html[dir="rtl"] .app-sidebar{ direction:rtl !important; }
html[dir="ltr"] .app-sidebar .nav-item[aria-selected="true"]::before,
html[dir="ltr"] .app-sidebar .nav-item.active::before{
  right:0; left:auto; border-radius:2px 0 0 2px;
}
.sidebar-section-label, .rail-group-label{
  font-size:var(--t-xs); font-weight:600; color:var(--cu-2); letter-spacing:0;
  text-transform:none; padding:var(--s3) var(--s3) var(--s1);
}
.rail-group{ display:flex; flex-direction:column; gap:1px; }
.rail-group + .rail-group{ margin-block-start:var(--s2); padding-block-start:var(--s2); border-block-start:1px solid var(--rule-2); }
.nav-item{
  position:relative; display:flex; align-items:center; gap:var(--s3); inline-size:100%;
  min-block-size:44px; padding:var(--s2) var(--s3);
  background:transparent; border:0; border-radius:var(--r2);
  color:var(--ink-2); font-size:var(--t-md); font-weight:500; text-align:start;
  transition:background var(--dur-1) var(--ease), color var(--dur-1) var(--ease);
}
.nav-item:hover{ background:var(--wash); color:var(--ink-1); }
.nav-item[aria-selected="true"], .nav-item.active{
  background:var(--cu-wash); color:var(--cu-txt); font-weight:700;
}
.nav-item[aria-selected="true"]::before, .nav-item.active::before{
  content:""; position:absolute; inset-inline-start:0; inset-block:6px;
  inline-size:2px; border-radius:0 2px 2px 0; background:var(--cu);
}
.nav-icon{
  inline-size:22px; block-size:22px; display:grid; place-items:center; flex:0 0 auto;
  color:var(--ink-3); font-size:17px;
}
.nav-item:hover .nav-icon{ color:var(--ink-2); }
.nav-item.active .nav-icon, .nav-item[aria-selected="true"] .nav-icon{ color:var(--cu); }
.nav-text{ flex:1; min-inline-size:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.nav-item .cnt, .nav-badge{
  font-size:var(--t-xs); font-weight:700; color:var(--ink-3);
  background:var(--bg-deep); border:1px solid var(--rule); border-radius:var(--r1);
  padding:1px 6px; margin-inline-start:auto;
}
.nav-item.active .cnt, .nav-item[aria-selected="true"] .cnt{ color:var(--cu-txt); border-color:var(--cu-line); background:transparent; }
.sidebar-footer{ margin-block-start:auto; padding-block-start:var(--s3); border-block-start:1px solid var(--rule-2); display:flex; flex-direction:column; gap:1px; }
.sidebar-backdrop{ display:none; }
/* collapsed rail: icons only, the same CSS hook the markup button toggles */
body.dl2-rail-collapsed .app-sidebar{ inline-size:var(--sidebar-w-rail); padding-inline:var(--s1); }
body.dl2-rail-collapsed .app-sidebar .nav-text,
body.dl2-rail-collapsed .app-sidebar .cnt,
body.dl2-rail-collapsed .app-sidebar .rail-group-label,
body.dl2-rail-collapsed .app-sidebar .sidebar-section-label{ display:none; }
body.dl2-rail-collapsed .app-sidebar .nav-item{ justify-content:center; padding-inline:0; }
.dl2-rail-toggle{
  margin-block-start:var(--s2); align-self:flex-start; inline-size:30px; block-size:30px;
  display:grid; place-items:center; background:transparent; border:1px solid var(--rule);
  border-radius:var(--r2); color:var(--ink-4);
}
.dl2-rail-toggle:hover{ color:var(--cu); border-color:var(--cu-line); background:var(--wash); }
body.dl2-rail-collapsed .dl2-rail-toggle{ align-self:center; }

/* ── MAIN PANE ──────────────────────────────────────────────────────────── */
.app-main{ flex:1; min-inline-size:0; block-size:100%; overflow-y:auto; overflow-x:hidden; display:flex; flex-direction:column; }
.view-container{ flex:1; padding:var(--s5); }
.view{ display:none; }
.view.active{ display:block; animation:viewIn var(--dur-2) var(--ease); }
@keyframes viewIn{ from{ opacity:0; } to{ opacity:1; } }
.grid{ display:grid; gap:var(--s4); }
.empty{
  color:var(--ink-3); text-align:center; padding:var(--s8) var(--s5);
  font-size:var(--t-sm); line-height:var(--lh-fa);
  border:1px dashed var(--rule); border-radius:var(--r3); background:var(--wash);
}
.spinner{
  display:inline-block; inline-size:15px; block-size:15px; margin-inline-end:var(--s2);
  border:1.5px solid var(--rule-3); border-top-color:var(--cu); border-radius:50%;
  animation:spin .7s linear infinite; vertical-align:-2px;
}
.spinner.block{ display:block; inline-size:26px; block-size:26px; margin:var(--s7) auto; }
@keyframes spin{ to{ transform:rotate(360deg); } }
.hint{ font-size:var(--t-sm); color:var(--ink-3); line-height:var(--lh-fa); font-weight:400; }
.panel-sub{ font-size:var(--t-sm); color:var(--ink-3); font-weight:400; }
/* ── 7 · CHIPS, BADGES, CREDIBILITY ──────────────────────────────────────── */
.chip{
  display:inline-flex; align-items:center; gap:5px; min-block-size:30px; padding:4px 11px;
  background:var(--wash); border:1px solid var(--rule); border-radius:var(--r2);
  color:var(--ink-2); font-size:var(--t-sm); font-weight:600;
  transition:background var(--dur-1) var(--ease), border-color var(--dur-1), color var(--dur-1);
}
.chip:hover{ background:var(--wash-2); border-color:var(--rule-3); color:var(--ink-1); }
.chip:active{ transform:translateY(1px); }
.chip.on{ background:var(--cu-wash); border-color:var(--cu-line); color:var(--cu-txt); }
.chip.on:hover{ background:var(--cu-wash-2); border-color:var(--cu); }
.chip .n{ font-size:var(--t-xs); color:var(--ink-4); font-weight:600; }
.chip.on .n{ color:var(--cu-2); }

.badge{
  display:inline-flex; align-items:center; gap:4px; padding:1px 7px;
  border-radius:var(--r1); font-size:var(--t-xs); font-weight:600; white-space:nowrap;
}
.badge .ic{ font-size:11px; }
.b-asset{ background:var(--cu-wash); color:var(--cu-txt); border:1px solid var(--cu-line); }
.b-topic{ background:var(--wash); color:var(--ink-3); border:1px solid var(--rule); }
.b-kind{ background:var(--info-wash); color:var(--info); border:1px solid rgba(127,166,201,.26); }
.badge.more{ background:transparent; border:1px dashed var(--rule-3); color:var(--ink-4); }

.cred{
  display:inline-flex; align-items:center; gap:4px; padding:1px 6px;
  border-radius:var(--r1); font-size:var(--t-xs); font-weight:700; direction:ltr;
  border:1px solid var(--rule); background:var(--bg-deep); color:var(--ink-2);
}
.cred::before{ content:""; inline-size:3px; block-size:11px; border-radius:1px; background:var(--ink-4); }
.cred.hi{ border-color:var(--up-line); color:var(--up); background:var(--up-wash); }
.cred.hi::before{ background:var(--up); }
.cred.mid{ border-color:var(--cu-line); color:var(--cu-txt); background:var(--cu-wash); }
.cred.mid::before{ background:var(--cu); }
.cred.low{ border-color:var(--dn-line); color:var(--dn); background:var(--dn-wash); }
.cred.low::before{ background:var(--dn); }
.cred-chip{ position:absolute; inset-block-end:9px; inset-inline-start:9px; z-index:2; backdrop-filter:blur(3px); }

/* ── 8 · TOOLBAR + FILTER SHEET (one line each, nothing else on screen) ──── */
.tb-wrap{ position:relative; }
.tb{
  position:relative; z-index:40; display:flex; align-items:center; gap:var(--s2); flex-wrap:wrap;
  padding:6px 8px; margin-block-end:var(--s4);
  background:var(--sheet); border:1px solid var(--rule); border-radius:var(--r2);
  box-shadow:var(--inset-hi);
}
.tb-btn{
  display:inline-flex; align-items:center; gap:var(--s2); min-block-size:32px; padding-inline:12px;
  background:var(--wash); border:1px solid var(--rule); border-radius:var(--r2);
  color:var(--ink-2); font-size:var(--t-sm); font-weight:600;
  transition:background var(--dur-1), border-color var(--dur-1), color var(--dur-1);
}
.tb-btn:hover{ background:var(--wash-2); border-color:var(--rule-3); color:var(--ink-1); }
.tb-btn.on, .tb-btn[aria-expanded="true"]{ background:var(--cu-wash); border-color:var(--cu-line); color:var(--cu-txt); }
.tb-caret{ font-size:9px; color:var(--ink-4); }
.tb-badge{
  display:inline-grid; place-items:center; min-inline-size:18px; block-size:18px; padding-inline:5px;
  background:var(--cu); color:#1A1206; border-radius:var(--r1); font-size:var(--t-xs); font-weight:800;
}
.tb-badge[data-n="0"]{ background:var(--wash-2); color:var(--ink-4); }
.tb-live{ display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
.tb-chip{
  display:inline-flex; align-items:center; gap:6px; min-block-size:26px; padding-inline:9px;
  background:var(--cu-wash); border:1px solid var(--cu-line); border-radius:var(--r2);
  color:var(--cu-txt); font-size:var(--t-xs); font-weight:600;
}
.tb-chip:hover{ background:var(--cu-wash-2); }
.tb-chip .x{ font-size:10px; opacity:.75; }
.tb-chip.more{ background:var(--wash); border-color:var(--rule); color:var(--ink-3); cursor:pointer; }
.tb-count{ margin-inline-start:auto; display:inline-flex; align-items:center; gap:6px;
  font-size:var(--t-xs); color:var(--ink-4); white-space:nowrap; }
.tb-count b{ color:var(--ink-1); }
.tb-hint{ font-size:var(--t-xs); color:var(--ink-4); }

.fsheet{
  position:absolute; z-index:60; inset-block-start:calc(100% + 6px); inset-inline-start:0;
  inline-size:min(640px, calc(100vw - 32px)); max-block-size:min(70vh, 620px);
  overflow:auto; overscroll-behavior:contain; padding:var(--s4);
  background:var(--panel-2); border:1px solid var(--rule-3); border-radius:var(--r3);
  box-shadow:var(--sh-1); display:none;
}
.fsheet.open{ display:block; animation:fsIn var(--dur-1) var(--ease); }
@keyframes fsIn{ from{ opacity:0; transform:translateY(-4px); } to{ opacity:1; transform:none; } }
.fsheet-hd{ display:flex; align-items:center; gap:var(--s2); margin-block-end:var(--s3);
  padding-block-end:var(--s3); border-block-end:1px solid var(--rule); }
.fsheet-hd b{ font-size:var(--t-md); color:var(--ink-1); }
.fsheet-x{
  margin-inline-start:auto; inline-size:26px; block-size:26px; display:grid; place-items:center;
  background:transparent; border:1px solid var(--rule); border-radius:var(--r2);
  color:var(--ink-3); font-size:12px;
}
.fsheet-x:hover{ color:var(--ink-1); border-color:var(--cu-line); background:var(--wash); }
.fsec{ padding-block:var(--s3); border-block-start:1px solid var(--rule-2); }
.fsec:first-of-type{ border-block-start:0; padding-block-start:0; }
.fsec-lbl{ display:block; margin-block-end:var(--s2); font-size:var(--t-xs); font-weight:700; color:var(--cu-txt); }
.fsec-lbl .fsec-n{ color:var(--ink-4); font-weight:600; }
.fsec-row{ display:flex; align-items:center; gap:var(--s3); flex-wrap:wrap; }
.fr-inline{ display:inline-flex; align-items:center; gap:6px; font-size:var(--t-xs); color:var(--ink-3); font-weight:600; }
.fgrid{ display:flex; flex-wrap:wrap; gap:6px; }
.fsel{ min-block-size:32px; min-inline-size:170px; border-radius:var(--r2); }
.fsearch{
  display:flex; align-items:center; gap:var(--s2); flex:1 1 240px; min-block-size:34px; padding-inline:10px;
  background:var(--panel-3); border:1px solid var(--rule); border-radius:var(--r2);
}
.fsearch:focus-within{ border-color:var(--cu); box-shadow:0 0 0 3px var(--cu-wash); }
.fsearch input{ flex:1 1 auto; min-inline-size:0; padding:0; border:0; background:transparent; }
.fsearch input:focus{ box-shadow:none; }
.fb-ic{ color:var(--ink-4); display:inline-flex; font-size:14px; }
.fb-kbd{
  font-size:10px; color:var(--ink-4); border:1px solid var(--rule); border-radius:var(--r1);
  padding:0 5px; line-height:16px; direction:ltr;
}
.fb-dot{ inline-size:6px; block-size:6px; border-radius:50%; background:var(--up); }
.fcred{ display:flex; align-items:center; gap:var(--s3); flex:1 1 260px; }
.fcred b{ font-size:var(--t-sm); color:var(--cu-txt); min-inline-size:42px; text-align:center; }
.fsheet-ft{ display:flex; align-items:center; gap:var(--s3); margin-block-start:var(--s3);
  padding-block-start:var(--s3); border-block-start:1px solid var(--rule); }
.fsheet-ft .sp{ margin-inline-start:auto; }
.fclr{
  min-block-size:30px; padding-inline:12px; background:var(--dn-wash); border:1px solid var(--dn-line);
  border-radius:var(--r2); color:var(--dn); font-size:var(--t-xs); font-weight:700;
}
.fclr:hover{ background:rgba(217,106,85,.2); }
.fdone{
  min-block-size:30px; padding-inline:14px; background:var(--cu-wash); border:1px solid var(--cu-line);
  border-radius:var(--r2); color:var(--cu-txt); font-size:var(--t-xs); font-weight:700;
}
.fdone:hover{ background:var(--cu-wash-2); }

/* ── 9 · PANELS ─────────────────────────────────────────────────────────────
   A panel is a bordered surface with a titled header strip; the tab rule under
   the title and the copper tick on its leading edge are the recurring motif. */
.panelbox{
  background:var(--panel); border:1px solid var(--rule); border-radius:var(--r3);
  box-shadow:var(--inset-hi);
  padding:var(--s5); margin-block-end:var(--s4);
}
.panelbox > h3{
  display:flex; align-items:center; gap:var(--s2); flex-wrap:wrap;
  font-size:var(--t-lg); color:var(--ink-1); font-weight:700;
  margin-block-end:var(--s4); padding-block-end:var(--s3);
  border-block-end:1px solid var(--rule);
}
.panelbox > h3::before{ content:""; inline-size:2px; block-size:15px; background:var(--cu); border-radius:1px; }
.panelbox > h4{ display:flex; align-items:center; gap:var(--s2); margin-block:var(--s5) var(--s3); font-size:var(--t-md); color:var(--cu-txt); }
.panelbox .hint{ display:block; }
.setrow{
  display:grid; grid-template-columns:minmax(0,1fr) auto; gap:var(--s4); align-items:center;
  padding-block:var(--s3); border-block-end:1px solid var(--rule-2);
}
.setrow .lbl{ font-size:var(--t-md); font-weight:600; color:var(--ink-1); }
.setrow .hint{ font-size:var(--t-xs); margin-block-start:2px; }
.setrow select[style]{ inline-size:auto !important; min-inline-size:150px; }
.kindgroup{ border:1px solid var(--rule); border-radius:var(--r2); overflow:hidden; margin-block-end:var(--s3); }
.kindgroup .kh{
  display:flex; justify-content:space-between; align-items:center; gap:var(--s2);
  padding:var(--s2) var(--s4); background:var(--bg-deep); font-size:var(--t-sm); font-weight:700;
  color:var(--ink-2); cursor:pointer;
}
.kindgroup .kb{ padding:0 var(--s4); }
.srcrow{
  display:flex; align-items:center; gap:var(--s3); flex-wrap:wrap;
  padding:var(--s2) 2px; border-block-end:1px solid var(--rule-2); font-size:var(--t-sm);
}
.srcrow:last-child{ border-block-end:0; }
.srcrow .nm{ font-weight:600; color:var(--ink-1); min-inline-size:130px; }
.srcrow .url{ flex:1; min-inline-size:180px; color:var(--ink-4); font-size:var(--t-xs); direction:ltr; text-align:left; }
.trust{
  font-size:var(--t-xs); font-weight:600; padding:1px 6px; border-radius:var(--r1);
  background:var(--cu-wash); color:var(--cu-txt); border:1px solid var(--cu-line); direction:ltr;
}
.ok{ color:var(--up); font-weight:700; }
.bad{ color:var(--dn); font-weight:700; }
.monrow{
  display:flex; align-items:center; gap:var(--s3); flex-wrap:wrap;
  padding:var(--s3) var(--s4); margin-block-end:var(--s1);
  background:var(--panel-2); border:1px solid var(--rule-2); border-radius:var(--r2);
  font-size:var(--t-sm);
}
.monrow:hover{ border-color:var(--rule); }
table.asset-table{ inline-size:100%; border-collapse:collapse; font-size:var(--t-sm); }
table.asset-table th{
  padding:var(--s2); font-size:var(--t-xs); font-weight:600; color:var(--ink-3);
  border-block-end:1px solid var(--rule); text-align:start;
}
table.asset-table td{ padding:var(--s2); border-block-end:1px solid var(--rule-2); color:var(--ink-2); text-align:start; }
table.asset-table tr:hover td{ background:var(--wash); }
table.asset-table td.ltr{ color:var(--ink-4); }

/* ── 10 · FEED ──────────────────────────────────────────────────────────────
   The منتخب carousel first (twenty scored stories, four per row, one page at a
   time), then the grid. Cards are rules-bordered with a copper tab that appears
   on hover — no drop shadows and no lift, so a screen of them still reads as a
   table rather than bubbles. */
.lead-row{ display:block; margin-block-end:var(--s4); }
.lead-row[hidden]{ display:none; }   /* the block display above would out-vote the UA rule */
.lead-head{ display:flex; align-items:center; gap:var(--s2); margin-block-end:var(--s3); flex-wrap:wrap; }
.lead-lab{ display:inline-flex; align-items:center; gap:6px; font-size:var(--t-md); font-weight:700; color:var(--ink-2); }
.lead-lab .ic{ color:var(--cu); }
.lead-count{ font-size:var(--t-xs); color:var(--ink-4); }
.lead-nav{ margin-inline-start:auto; display:flex; align-items:center; gap:var(--s1); }
.lead-btn{ inline-size:32px; block-size:32px; display:inline-grid; place-items:center; padding:0;
  font-size:14px; color:var(--ink-3); background:var(--panel); cursor:pointer;
  border:1px solid var(--rule); border-radius:var(--r2); transition:color var(--dur-1), border-color var(--dur-1); }
.lead-btn:hover{ color:var(--ink-1); border-color:var(--cu-line); }
.lead-btn:focus-visible{ outline:1px solid var(--cu-hi); outline-offset:2px; }
.lead-dots{ display:inline-flex; align-items:center; gap:5px; margin-inline:var(--s2); }
.lead-dot{ inline-size:7px; block-size:7px; padding:0; border:0; border-radius:var(--r-pill);
  background:var(--rule-3); cursor:pointer; transition:background var(--dur-1); }
.lead-dot.on{ background:var(--cu); }
.lead-dot:focus-visible{ outline:1px solid var(--cu-hi); outline-offset:2px; }
.lead-pos{ font-size:var(--t-xs); color:var(--ink-4); font-variant-numeric:tabular-nums; }
.lead-cards{ display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:var(--s4); }
.lead-cards.lead-in{ animation:leadIn var(--dur-3) var(--ease); }
@keyframes leadIn{ from{ opacity:.25; transform:translateY(5px); } to{ opacity:1; transform:none; } }
@media (max-width:1180px){ .lead-cards{ grid-template-columns:repeat(2, minmax(0,1fr)); } }
@media (prefers-reduced-motion: reduce){
  .view.active{ animation:none; }
  .lead-cards.lead-in{ animation:none; }
  .dot.busy{ animation:none; }
  .dl2-ticker .tk-track{ animation:none; }
}
.lead-card{
  position:relative; display:flex; flex-direction:column; overflow:hidden; cursor:pointer;
  background:var(--panel); border:1px solid var(--rule); border-radius:var(--r3);
  box-shadow:var(--inset-hi);
  min-block-size:180px; transition:border-color var(--dur-2) var(--ease), background var(--dur-2);
}
.lead-card:hover{ border-color:var(--cu-line); background:var(--panel-2); }
.lead-card:focus-visible{ outline:1px solid var(--cu-hi); outline-offset:2px; }
.lead-rail{ position:absolute; inset-inline-start:0; inset-block:0; inline-size:2px; background:var(--cu); opacity:.75; }
.lead-card .body{ display:flex; flex-direction:column; gap:var(--s2); padding:var(--s5); }
.lead-card .row1{ display:flex; gap:5px; flex-wrap:wrap; align-items:center; }
.lead-card .lead-ttl{ font-size:var(--t-xl); line-height:1.55; font-weight:700; color:var(--ink-1);
  display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }
.lead-card .summ{ color:var(--ink-3); font-size:var(--t-md); line-height:var(--lh-fa);
  display:-webkit-box; -webkit-line-clamp:4; -webkit-box-orient:vertical; overflow:hidden; }
.lead-card .row2{
  display:flex; align-items:center; gap:var(--s3); flex-wrap:wrap; margin-block-start:auto;
  padding-block-start:var(--s3); border-block-start:1px solid var(--rule-2);
  font-size:var(--t-xs); color:var(--ink-4);
}
/* the banner slot the lead card was authored for but never filled: a 21:9
   crop under the copper rail, so the three best-credibility stories read as
   the top of the page instead of as three text boxes sitting above pictures */
.lead-card .thumb{
  position:relative; aspect-ratio:21/9; overflow:hidden; background:var(--panel-3);
  border-block-end:1px solid var(--rule-2);
}
.lead-card .thumb::before{
  content:""; position:absolute; inset:0; pointer-events:none;
  background:linear-gradient(200deg, rgba(56,120,220,.16), rgba(6,11,24,.36));
}
.lead-card .thumb::after{
  content:""; position:absolute; inset:0; pointer-events:none;
  background:linear-gradient(180deg, rgba(6,11,24,0) 55%, rgba(6,11,24,.72) 100%);
}
.lead-card .thumb img{ inline-size:100%; block-size:100%; object-fit:cover; display:block; }

.ngrid{ display:grid; grid-template-columns:repeat(auto-fill, minmax(306px,1fr)); gap:var(--s4); }
.ncard{
  position:relative; display:flex; flex-direction:column; overflow:hidden; cursor:pointer;
  background:var(--panel); border:1px solid var(--rule); border-radius:var(--r3);
  box-shadow:var(--inset-hi);
  transition:border-color var(--dur-2) var(--ease), background var(--dur-2);
}
.ncard::before{
  content:""; position:absolute; inset-inline-start:0; inset-block:0; inline-size:2px;
  background:var(--cu); opacity:0; transition:opacity var(--dur-2) var(--ease);
}
.ncard:hover{ border-color:var(--cu-line); background:var(--panel-2); }
.ncard:hover::before{ opacity:.8; }
.ncard:focus-visible{ outline:1px solid var(--cu-hi); outline-offset:2px; }
.ncard .thumb{ position:relative; inline-size:100%; aspect-ratio:16/9; overflow:hidden; background:var(--panel-3); }
/* ── DL4 · let the picture into the material ──────────────────────────────
   Feed thumbnails arrive saturated: Google-News placeholders, press photos,
   brand colour blocks. Three of them side by side punch primary-coloured
   holes in a warm-graphite interface and the copper stops reading as the one
   accent. One filter chain pulls every image toward the palette (desaturate,
   warm, hold contrast back) and a copper-to-graphite wash sits over it; hover
   and keyboard focus hand most of the colour back, so the picture is still a
   picture when you go to open it. Reduced transparency keeps the wash, the
   filter is what does the work. */
.ncard .thumb img, .lead-card .thumb img{
  filter:grayscale(.42) saturate(1.02) contrast(1.06) brightness(.84) hue-rotate(8deg);
  transition:filter var(--dur-3) var(--ease);
}
.ncard:hover .thumb img, .ncard:focus-visible .thumb img,
.lead-card:hover .thumb img, .lead-card:focus-visible .thumb img{
  filter:grayscale(.08) saturate(1.05) contrast(1.02) brightness(.96) hue-rotate(0deg);
}
.ncard .thumb::before{
  content:""; position:absolute; inset:0; pointer-events:none;
  background:linear-gradient(200deg, rgba(95,140,200,.12), rgba(8,12,21,.38));
}
.ncard .thumb img{ inline-size:100%; block-size:100%; object-fit:cover; display:block; }
.ncard .thumb::after{
  content:""; position:absolute; inset:0; pointer-events:none;
  background:linear-gradient(180deg, rgba(6,11,24,0) 45%, rgba(6,11,24,.88) 100%);
}
.ncard .noimg{
  inline-size:100%; block-size:100%; display:grid; place-items:center;
  color:var(--ink-4); background:
    repeating-linear-gradient(-45deg, rgba(255,255,255,.02) 0 8px, transparent 8px 16px),
    var(--panel-3);
}
.ncard .noimg .ic{ font-size:26px; opacity:.4; }
.ncard .body{ display:flex; flex-direction:column; gap:var(--s2); flex:1; padding:var(--s4); }
.ncard .row1{ display:flex; align-items:center; gap:5px; flex-wrap:wrap; }
.ncard .ttl{ font-size:var(--t-lg); font-weight:700; line-height:1.7; color:var(--ink-1); letter-spacing:0; }
.ncard .ttl-en{ direction:ltr; text-align:left; font-size:var(--t-xs); color:var(--ink-4); line-height:1.6; }
.ncard .summ{
  display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;
  font-size:var(--t-md); line-height:var(--lh-fa); color:var(--ink-3);
}
.ncard .row2{
  display:flex; align-items:center; gap:var(--s2); flex-wrap:wrap; margin-block-start:auto;
  padding-block-start:var(--s3); border-block-start:1px solid var(--rule-2);
  font-size:var(--t-xs); color:var(--ink-4);
}
.src{ color:var(--cu); font-weight:600; }
.ncard .dt{ font-weight:400; }
.star-btn{
  margin-inline-start:auto; background:transparent; border:0; padding:0;
  inline-size:24px; block-size:24px; flex:0 0 auto;
  justify-content:center; align-items:center;
  color:var(--ink-4); font-size:15px; line-height:1; display:inline-flex;
}
.star-btn .ic{ font-size:15px; }
.star-btn:hover{ color:var(--cu-hi); }
.star-btn.on{ color:var(--cu); }
.star-btn.on .ic{ fill:currentColor; }
/* delete one story — quiet until hovered, then oxide. A row can hold both the
   bookmark and the bin, so the star no longer claims the auto margin alone. */
.del-btn{
  background:transparent; border:0; padding:0;
  inline-size:24px; block-size:24px; flex:0 0 auto;
  justify-content:center; align-items:center;
  color:var(--ink-4); font-size:15px; line-height:1; display:inline-flex;
}
.del-btn .ic{ font-size:15px; }
.del-btn:hover{ color:var(--dn); }
.row2 .star-btn{ margin-inline-start:auto; }
.blurb-btn{ align-self:flex-start; margin-block-start:var(--s1); display:none; }

/* The quote-card strip above the views is gone: it duplicated the ticker and
   pushed the first headline down the page. No .acard rules remain. */

/* freshness + skeletons */
.newdot{
  display:inline-block; inline-size:6px; block-size:6px; border-radius:50%;
  background:var(--cu); margin-inline-end:6px; animation:newpulse 2.4s var(--ease) infinite;
}
@keyframes newpulse{ 0%{ box-shadow:0 0 0 0 rgba(200,150,93,.4); } 70%{ box-shadow:0 0 0 7px rgba(200,150,93,0); } 100%{ box-shadow:0 0 0 0 rgba(200,150,93,0); } }
#feedNewBadge{ display:inline-flex; align-items:center; font-size:var(--t-xs); color:var(--cu-txt); margin-inline-start:var(--s2); }
.skcard{ block-size:200px; border:1px solid var(--rule); border-radius:var(--r3); }
.skeleton{ background:linear-gradient(100deg, var(--panel-2) 30%, var(--panel-3) 50%, var(--panel-2) 70%); background-size:220% 100%; animation:shimmer 1.4s linear infinite; }
@keyframes shimmer{ from{ background-position:180% 0; } to{ background-position:-40% 0; } }
.flash-up{ color:var(--up) !important; }
.flash-dn{ color:var(--dn) !important; }

/* ── 11 · MODALS ────────────────────────────────────────────────────────────
   One shell for all four: hairline frame, squared corners, a title strip and a
   square close button. No glow. */
.overlay{
  position:fixed; inset:0; z-index:400; display:none; align-items:center; justify-content:center;
  padding:var(--s5); background:rgba(6,5,4,.76);
  -webkit-backdrop-filter:blur(10px); backdrop-filter:blur(10px);
}
.overlay.open{ display:flex; animation:ovIn var(--dur-2) var(--ease); }
@keyframes ovIn{ from{ opacity:0; } to{ opacity:1; } }
.modal{
  position:relative; inline-size:95%; max-inline-size:860px; max-block-size:90vh; overflow-y:auto;
  padding:var(--s6) var(--s6) var(--s5);
  background:var(--panel); border:1px solid var(--rule-3); border-radius:var(--r3);
  box-shadow:var(--sh-2);
}
.mclose{
  position:absolute; inset-block-start:var(--s4); inset-inline-start:var(--s4);
  inline-size:30px; block-size:30px; display:grid; place-items:center;
  background:var(--wash); border:1px solid var(--rule); border-radius:var(--r2);
  color:var(--ink-3); font-size:13px;
}
.mclose:hover{ background:var(--dn-wash); border-color:var(--dn-line); color:var(--dn); }
.modal h2{ font-size:var(--t-xl); line-height:var(--lh-fa); margin-block:var(--s3) var(--s1); }
.modal h3{ font-size:var(--t-lg); }
.modal h4{ font-size:var(--t-md); }
.modal .h2en{ direction:ltr; text-align:left; font-size:var(--t-sm); color:var(--ink-4); margin-block-end:var(--s3); }
.modal .mmeta{ display:flex; gap:var(--s4); flex-wrap:wrap; align-items:center; font-size:var(--t-xs); color:var(--ink-4); margin-block-end:var(--s4); }
.modal .flags{
  padding:var(--s3); margin-block-end:var(--s4); font-size:var(--t-sm); line-height:var(--lh-fa);
  background:var(--warn-wash); border:1px solid rgba(216,169,63,.3); border-radius:var(--r2); color:#E7C978;
}
.msec{ margin-block-start:var(--s4); padding:var(--s4); background:var(--panel-2); border:1px solid var(--rule-2); border-radius:var(--r2); }
.msec h4{ display:flex; justify-content:space-between; align-items:center; gap:var(--s2);
  color:var(--cu-txt); font-size:var(--t-sm); margin-block-end:var(--s2); }
.msec p{ font-size:var(--t-md); line-height:var(--lh-fa); color:var(--ink-2); margin:0; }
.msec p + p{ margin-block-start:var(--s3); }
.msec .scroll{ max-block-size:320px; overflow-y:auto; overscroll-behavior:contain; padding-inline-end:var(--s1); }
.mlink{ display:inline-flex; align-items:center; gap:6px; margin-block-start:var(--s4); font-size:var(--t-sm); font-weight:700; color:var(--cu-txt); }
.mlink:hover{ color:var(--cu-hi); }
.tradingview-widget-container, .tradingview-widget-container__widget{ inline-size:100%; block-size:100%; }
/* .tvfail lives with the chart panel (theme_v3_c) */

/* related stories inside the article modal */
.rel{ padding-block:var(--s1); }
.rel .relrow{
  display:flex; align-items:baseline; gap:var(--s3); padding:var(--s2) 2px;
  border-block-end:1px solid var(--rule-2);
}
.rel .relrow:last-child{ border-block-end:0; }
.rel .relrow:hover{ background:var(--wash); }
.rel .reltitle{ flex:1; min-inline-size:0; font-size:var(--t-sm); font-weight:600; line-height:1.75; color:var(--ink-1); }
.rel .relsrc{ flex:0 0 auto; font-size:var(--t-xs); font-weight:700; color:var(--cu); direction:ltr; white-space:nowrap; }
.rel .relfull{ flex:0 0 auto; font-size:10px; font-weight:700; color:var(--up);
  border:1px solid var(--up-line); background:var(--up-wash); border-radius:var(--r1); padding:0 5px; }
.rel .relgo{ flex:0 0 auto; color:var(--ink-4); font-size:12px; }
/* a blocked publisher: what happened, and the two things that still work */
.nobody > p{ font-size:var(--t-md); line-height:var(--lh-fa); color:var(--ink-3); margin-block:0 var(--s3); }
.nobody-cta{ display:flex; gap:var(--s3); flex-wrap:wrap; }
.nobody-hint{ font-size:var(--t-xs); color:var(--ink-4); margin-block:var(--s3) 0; line-height:var(--lh); }

/* ── 12 · TOAST ─────────────────────────────────────────────────────────── */
.toast{
  position:fixed; inset-block-end:var(--s5); inset-inline-start:var(--s5); z-index:500;
  display:none; max-inline-size:380px; padding:var(--s3) var(--s4);
  background:var(--panel-3); border:1px solid var(--cu-line); border-radius:var(--r2);
  color:var(--cu-txt); font-size:var(--t-sm); font-weight:600; box-shadow:var(--sh-1);
}
/* ── 13 · REPORTS ───────────────────────────────────────────────────────────
   The reading surface is the product, so it gets the paper treatment: a lighter
   surface than the rest of the app, a 76ch measure, 15px/2.0 body and section
   rules with a copper tick at the start of each heading. */
.rep-shell{ display:flex; flex-direction:column; gap:var(--s4); }
.rep-hero{
  display:grid; grid-template-columns:minmax(0,1fr) auto; gap:var(--s4);
  align-items:center; padding:var(--s4) var(--s5);
  background:var(--panel); border:1px solid var(--rule); border-radius:var(--r3);
}
.rep-hero .rh-main{ display:flex; align-items:center; gap:var(--s4); min-inline-size:0; }
.rep-hero .rh-icon{
  inline-size:40px; block-size:40px; flex:0 0 auto; display:grid; place-items:center;
  background:var(--cu-wash); border:1px solid var(--cu-line); border-radius:var(--r2); color:var(--cu-hi);
}
.rep-hero h2{ display:flex; align-items:center; gap:var(--s2); font-size:var(--t-2xl); color:var(--ink-1); }
.rep-hero .rh-sym{ font-size:var(--t-xs); font-weight:600; color:var(--ink-4); direction:ltr; }
.rep-hero .rh-sub{ display:flex; gap:var(--s4); flex-wrap:wrap; margin-block-start:5px; font-size:var(--t-xs); color:var(--ink-4); }
.rep-hero .rh-side{ display:flex; flex-direction:column; align-items:flex-end; gap:var(--s3); }
.rep-hero .rh-actions{ display:flex; gap:var(--s2); flex-wrap:wrap; justify-content:flex-end; align-items:center; }
.rep-layout{ display:grid; grid-template-columns:minmax(0,1fr) minmax(430px,560px); gap:var(--s4); align-items:start; }
.rep-side{ position:sticky; inset-block-start:calc(var(--topbar-h) + var(--s5)); display:flex; flex-direction:column; gap:var(--s4); }
.rep-doc{
  background:var(--doc);
  border:1px solid var(--rule); border-radius:var(--r3);
  box-shadow:var(--inset-hi);
  padding:var(--s6) var(--s7); min-inline-size:0;
  max-block-size:calc(100vh - 160px); overflow:auto; overscroll-behavior:contain; scrollbar-gutter:stable;
}
.rep-doc h2{ font-size:var(--t-2xl); color:var(--cu-hi); }
.rep-doc h3{
  display:flex; align-items:center; gap:var(--s2);
  font-size:var(--t-xl); color:var(--ink-1);
  margin-block:var(--s7) var(--s4); padding-block-end:var(--s2);
  border-block-end:1px solid var(--rule);
}
.rep-doc h3::before{ content:""; inline-size:3px; block-size:16px; background:var(--cu); border-radius:1px; flex:0 0 auto; }
.rep-doc h3:first-of-type{ margin-block-start:0; }
.rep-doc h4{ font-size:var(--t-lg); color:var(--ink-1); margin-block:var(--s5) var(--s3); }
.rep-doc p{ font-size:var(--t-lg); line-height:2.05; max-inline-size:var(--measure); color:var(--ink-2); margin-block:0 var(--s3); }
.rep-doc p + p{ margin-block-start:var(--s3); }
.rep-doc ul, .rep-doc ol{ padding-inline-start:var(--s5); }
.rep-doc li{ margin-block-end:var(--s1); }
.rep-doc .meta{ display:flex; gap:var(--s4); flex-wrap:wrap; font-size:var(--t-xs); color:var(--ink-4); margin-block-end:var(--s4); }
.rep-doc p.en, .rep-doc .en{ direction:ltr; text-align:left; }
.rep-doc table{ inline-size:100%; }
.rep-doc .rep-toc{
  display:flex; gap:6px; flex-wrap:wrap; margin-block-end:var(--s5); padding-block-end:var(--s3);
  border-block-end:1px solid var(--rule);
}
.rep-toc button{
  min-block-size:28px; padding:3px 11px; background:var(--wash); border:1px solid var(--rule);
  border-radius:var(--r2); color:var(--ink-3); font-size:var(--t-xs); font-weight:600;
}
.rep-toc button:hover{ background:var(--cu-wash); border-color:var(--cu-line); color:var(--cu-txt); }
.rep-sec{ scroll-margin-block-start:var(--s4); }
/* ── DL4 · the report runs in one language at a time ──────────────────────
   The body is English by default and Persian on request, but only the
   paragraphs ever switched direction: the section headings and the chip row
   kept the page's RTL. The result was a left-aligned English paragraph under
   a right-aligned English heading whose leading "1." had been bidi-pushed to
   the far right of the label ("Market Overview .1"). data-lang flips just
   those two elements — the citation boxes stay Persian and keep RTL. */
.rep-doc[data-lang="en"] .rep-sec,
.rep-doc[data-lang="en"] .rep-toc{ direction:ltr; text-align:left; }

/* citations: one disclosure per section, closed by default */
.cites, .rep-doc .cites{ margin-block-start:var(--s4); border:1px solid var(--rule-2); border-radius:var(--r2); overflow:hidden; background:var(--wash); }
.cites-btn{
  inline-size:100%; display:flex; align-items:center; gap:var(--s2); flex-wrap:wrap;
  padding:var(--s3) var(--s4); background:transparent; border:0; color:var(--ink-1);
  font-size:var(--t-sm); font-weight:600; text-align:start;
}
.cites-btn:hover{ background:var(--wash); }
.cites-btn .cb-ic{ color:var(--cu); display:inline-flex; }
.cites-btn .cb-t{ color:var(--cu-txt); }
.cites-btn .cb-n{ font-size:var(--t-xs); color:var(--ink-4); border:1px solid var(--rule); border-radius:var(--r1); padding:0 6px; }
.cites-btn .cb-a{
  margin-inline-start:auto; font-size:var(--t-xs); font-weight:700; color:var(--cu-txt);
  background:var(--cu-wash); border:1px solid var(--cu-line); border-radius:var(--r2); padding:2px 10px;
}
.cites.open .cites-btn{ border-block-end:1px solid var(--rule-2); }
.cites.open .cites-btn .cb-a{ background:transparent; border-color:var(--rule); color:var(--ink-3); }
.cites-body, .rep-doc .cites-body{ display:none; }
.cites.open .cites-body, .rep-doc .cites.open .cites-body{ display:block; }
.cites-list{ padding:var(--s1) var(--s4) var(--s3); max-block-size:min(44vh,380px); overflow:auto; overscroll-behavior:contain; }
.cite, .rep-doc .cite{
  display:grid; grid-template-columns:auto minmax(0,1fr) auto; gap:var(--s3);
  align-items:start; padding:var(--s3) 0; border-block-start:1px dashed var(--rule-2); color:var(--ink-3);
}
.cite:first-child, .rep-doc .cite:first-child{ border-block-start:0; }
.cite:hover, .rep-doc .cite:hover{ background:var(--wash); }
.cite .idx{
  inline-size:22px; block-size:22px; display:flex; align-items:center; justify-content:center;
  font-size:10px; font-weight:800; border-radius:var(--r1);
  background:var(--cu-wash); border:1px solid var(--cu-line); color:var(--cu-txt);
}
.cite .ct-body{ display:flex; flex-direction:column; gap:2px; min-inline-size:0; }
.cite .ct-t{ font-size:var(--t-sm); font-weight:600; line-height:1.8; color:var(--ink-1); }
.cite .ct-en{ direction:ltr; text-align:left; font-size:var(--t-xs); line-height:1.65; color:var(--ink-4); }
.cite .ct-meta{ display:flex; gap:var(--s2); flex-wrap:wrap; margin-block-start:4px; font-size:var(--t-xs); color:var(--ink-4); }
.cite .ct-src{ font-weight:700; color:var(--cu); }
.cite .ct-cred{ color:var(--up); }
.cite .ct-go{ color:var(--ink-4); align-self:center; }
.cite:hover .ct-go{ color:var(--cu-hi); }
.cite .why{ font-size:var(--t-xs); color:var(--ink-4); }
.idea-foot .author{ display:inline-flex; align-items:center; gap:6px; font-size:var(--t-xs); color:var(--ink-3); }
.idea-foot .eng{ display:inline-flex; align-items:center; gap:5px; font-size:var(--t-xs); color:var(--ink-4); }
.idea-foot .ic{ color:var(--cu-2); }

/* fear & greed strip under the report */
.repfng{ display:flex; flex-direction:column; gap:var(--s3); }
.repfng .rf-row{ display:flex; align-items:center; gap:var(--s4); }
.repfng .rf-score{ font-size:32px; font-weight:800; line-height:1.1; color:var(--ink-1); }
.repfng .rf-score span{ font-size:var(--t-xs); color:var(--ink-4); font-weight:500; }
.repfng .rf-lab{ font-size:var(--t-lg); font-weight:700; }
.repfng .rf-bar{ block-size:5px; border-radius:2px; background:var(--bg-deep); overflow:hidden; }
.repfng .rf-bar i{ display:block; block-size:100%; }
.repfng .rf-src{ font-size:var(--t-xs); color:var(--ink-4); line-height:var(--lh); }
.repfng .rf-glob{ padding-block-start:var(--s3); border-block-start:1px solid var(--rule-2); font-size:var(--t-sm); color:var(--ink-3); }
.repfng .rf-scale{ display:flex; justify-content:space-between; font-size:10px; color:var(--ink-4); }

/* chart panel */
.chartbox{
  background:var(--panel); border:1px solid var(--rule); border-radius:var(--r3);
  padding:var(--s4);
}
.rep-side .chartbox:not(.tvfull){ position:static; }
.chartbox h3{ font-size:var(--t-lg); color:var(--ink-1); }
.chart-head{ display:flex; align-items:center; gap:var(--s3); flex-wrap:wrap; margin-block-end:var(--s3);
  padding-block-end:var(--s3); border-block-end:1px solid var(--rule); }
.chart-head h3{ margin:0; }
.chart-head .p{ font-size:var(--t-2xl); font-weight:700; direction:ltr; }
.chart-head .c, .chart-head .chg{ font-size:var(--t-sm); font-weight:700; direction:ltr; }
.chart-head .c.up, .chart-head .chg.up{ color:var(--up); }
.chart-head .c.dn, .chart-head .chg.dn{ color:var(--dn); }
.chart-head .ch-sym{ font-size:var(--t-xs); color:var(--ink-4); direction:ltr; font-weight:500; }
.chart-head h3{ display:inline-flex; align-items:center; gap:var(--s2); }
/* the analytic pane's own head (drawn inside the SVG wrapper) */
.tvhead{ display:flex; align-items:baseline; gap:var(--s3); flex-wrap:wrap; margin-block-end:var(--s2); }
.tvhead .p{ font-size:var(--t-xl); font-weight:700; direction:ltr; color:var(--ink-1); }
.tvhead .chg{ font-size:var(--t-xs); font-weight:700; direction:ltr; }
.tvhead .chg.up{ color:var(--up); }
.tvhead .chg.dn{ color:var(--dn); }
.chartbox .hint{ font-size:var(--t-xs); }
/* the live price block in the report hero */
.ch-price{ display:flex; align-items:baseline; gap:var(--s2); direction:ltr; }
.ch-price .p{ font-size:var(--t-2xl); font-weight:700; color:var(--ink-1); }
.ch-price .c{ font-size:var(--t-sm); font-weight:700; }
.ch-price .c.up{ color:var(--up); }
.ch-price .c.dn{ color:var(--dn); }
.chart-live{
  margin-inline-start:auto; padding:1px 9px; font-size:var(--t-xs); font-weight:700;
  color:var(--up); background:var(--up-wash); border:1px solid var(--up-line); border-radius:var(--r-pill);
}
.chart-tools{ display:flex; gap:6px; flex-wrap:wrap; justify-content:flex-end; margin-block-end:var(--s3); }
.chart-tools .btn, .chart-tools .seg button{ min-block-size:30px; font-size:var(--t-xs); }
.chart-tools .btn{ display:inline-flex; align-items:center; gap:5px; }
#tvFullBtn.on{ background:var(--cu-wash); border-color:var(--cu-line); color:var(--cu-txt); }
/* the TradingView embed fills its holder. Without these two rules the holder is
   a zero-height div, the widget measures 0 and never mounts — which is exactly
   why the chart used to come up empty. */
.tvwrap{ position:relative; block-size:min(52vh, 460px); overflow:hidden;
  background:var(--bg-deep); border:1px solid var(--rule); border-radius:var(--r2); }
.tvwrap > div, .tvwrap iframe, #tvholder{ inline-size:100% !important; block-size:100% !important; }
.tvfail{ margin-block-start:var(--s3); padding:var(--s3); font-size:var(--t-sm); color:var(--warn);
  background:var(--warn-wash); border:1px solid var(--rule); border-radius:var(--r2); }
.tvfail .mlink{ margin-inline-start:6px; }
/* fullscreen chart — the transform chain has to be neutralised or position:fixed
   resolves against the animated .view instead of the screen */
.chartbox.tvfull{
  position:fixed; inset:0; z-index:620; display:flex; flex-direction:column; gap:var(--s3);
  padding:var(--s3) var(--s4) var(--s4); background:var(--bg); border:0; border-radius:0;
}
.chartbox.tvfull .tvwrap{ flex:1 1 auto; block-size:auto; min-block-size:0; }
body.tv-full{ overflow:hidden; }
body.tv-full .app-sidebar, body.tv-full .app-topbar, body.tv-full .dl2-ticker{ visibility:hidden; }
body.tv-full .view, body.tv-full .view.active, body.tv-full .view-container, body.tv-full .app-body{
  transform:none !important; animation:none !important; filter:none !important;
}

/* ── 14 · TRADINGVIEW IDEAS ─────────────────────────────────────────────── */
.tv-hero{
  display:grid; grid-template-columns:minmax(0,1.6fr) minmax(240px,.4fr); gap:var(--s5);
  align-items:center; padding:var(--s5); margin-block-end:var(--s4);
  background:var(--panel); border:1px solid var(--rule); border-radius:var(--r3);
}
.tv-hero .tvh-brand{ display:inline-block; font-size:var(--t-xs); font-weight:700; color:var(--cu); direction:ltr; letter-spacing:.02em; }
.tv-hero h2{ font-size:var(--t-2xl); margin-block:var(--s1) var(--s2); }
.tv-hero p{ margin:0; font-size:var(--t-md); line-height:var(--lh-fa); color:var(--ink-3); }
.tv-hero .tvh-r{ display:flex; flex-direction:column; align-items:flex-end; gap:var(--s2); }
.tv-hero .tvh-note{ font-size:var(--t-xs); color:var(--ink-4); }
.ideas-grid{ display:grid; grid-template-columns:repeat(auto-fill, minmax(330px,1fr)); gap:var(--s4); }
.idea-card{
  display:flex; flex-direction:column; overflow:hidden;
  background:var(--panel); border:1px solid var(--rule); border-radius:var(--r3);
  box-shadow:var(--inset-hi);
  transition:border-color var(--dur-2) var(--ease), background var(--dur-2);
}
.idea-card:hover{ border-color:var(--cu-line); background:var(--panel-2); }
.idea-thumb{ position:relative; display:block; inline-size:100%; aspect-ratio:16/9; background:var(--panel-3); border-block-end:1px solid var(--rule-2); overflow:hidden; }
.idea-thumb::after{ content:""; position:absolute; inset:0; pointer-events:none;
  background:linear-gradient(180deg, rgba(8,7,6,.55), transparent 45%, rgba(8,7,6,.5)); }
/* the timeframe stamps the chart image, the way TradingView draws it; the
   direction label lives in the card body, never on the picture */
.idea-thumb .idea-tf{
  position:absolute; z-index:2; inset-block-start:var(--s2); padding:1px 8px;
  border-radius:var(--r1); background:rgba(8,7,6,.72); font-size:var(--t-xs); font-weight:700;
}
.idea-thumb .idea-tf{ inset-inline-end:var(--s2); direction:ltr; color:var(--ink-2); }
.idea-thumb img{ inline-size:100%; block-size:100%; object-fit:cover; display:block; }
.idea-thumb.noimg{ display:none; }
.idea-body{ display:flex; flex-direction:column; gap:var(--s2); flex:1; padding:var(--s3) var(--s4) var(--s4); }
.idea-top{ display:flex; align-items:center; gap:var(--s2); flex-wrap:wrap; }
.idea-top .dir{ font-size:var(--t-xs); font-weight:800; }
.idea-top .dir.up{ color:var(--up); }
.idea-top .dir.dn{ color:var(--dn); }
.idea-top .idea-sym{ font-size:var(--t-xs); color:var(--ink-3); border:1px solid var(--rule); border-radius:var(--r1); padding:0 6px; direction:ltr; }
.idea-top .idea-tf{ font-size:10.5px; color:var(--ink-4); border:1px solid var(--rule-2); border-radius:var(--r1); padding:0 5px; direction:ltr; }
.idea-top .idea-when{ margin-inline-start:auto; font-size:var(--t-xs); color:var(--ink-4); }
.idea-ttl{ font-size:var(--t-lg); font-weight:700; line-height:1.7; }
.idea-ttl a{ color:var(--ink-1); }
.idea-ttl a:hover{ color:var(--cu-hi); }
.idea-txt{ font-size:var(--t-sm); line-height:var(--lh-fa); color:var(--ink-3);
  display:-webkit-box; -webkit-line-clamp:4; -webkit-box-orient:vertical; overflow:hidden; }
.idea-badges{ display:flex; gap:5px; flex-wrap:wrap; }
.idea-more-btn{
  align-self:flex-start; padding:5px 11px; font-size:var(--t-xs); font-weight:700;
  background:var(--cu-wash); border:1px dashed var(--cu-line); border-radius:var(--r2); color:var(--cu-txt);
}
.idea-more-btn:hover{ background:var(--cu-wash-2); border-style:solid; }
.idea-big{ inline-size:100%; border:1px solid var(--rule); border-radius:var(--r2); display:block; }
.idea-foot{ display:flex; align-items:center; gap:var(--s3); flex-wrap:wrap; margin-block-start:auto; padding-block-start:var(--s3); }
.idea-link{
  display:inline-flex; align-items:center; gap:6px; padding:5px 12px;
  background:var(--cu-wash); border:1px solid var(--cu-line); border-radius:var(--r2);
  color:var(--cu-txt); font-size:var(--t-xs); font-weight:700;
}
.idea-link:hover{ background:var(--cu-wash-2); }
.idea-cta{ margin-inline-start:auto; }

/* ── 15 · ECONOMIC CALENDAR ─────────────────────────────────────────────────
   The tab is English end to end — hero, week navigator, day strip, control
   sheet, side rail and board — which is the decision the code and the
   operator's note both record. English laid out in an inherited RTL container
   comes back mirrored: the week label read "Sept – 27 Sept 21", "Prev week"
   sat on the right with a left chevron, the strip ran Sunday → Monday under a
   Monday-first board, and the hero counted down as "1d 19h in". So the whole
   view is LTR, not just .cal-board; only the event explainer (a modal, outside
   this view) is Persian and it keeps the page direction. */
#view-calendar{ direction:ltr; }
.cal-grid{ display:grid; grid-template-columns:minmax(0,1fr) 330px; gap:var(--s4); align-items:start; }
.cal-main, .cal-side{ display:flex; flex-direction:column; gap:var(--s4); min-inline-size:0; }

/* hero: the next release that can move price */
.cal-hero{
  display:flex; gap:var(--s5); align-items:center; justify-content:space-between; flex-wrap:wrap;
  padding:var(--s4) var(--s5);
  background:linear-gradient(90deg, var(--cu-wash), transparent 85%), var(--panel);
  border:1px solid var(--cu-line); border-radius:var(--r3);
}
.cal-hero-l{ display:flex; flex-direction:column; gap:var(--s2); min-inline-size:0; }
.cal-eyebrow{ font-size:var(--t-xs); font-weight:600; color:var(--cu); }
.cal-hero-ttl{ font-size:var(--t-xl); font-weight:700; color:var(--ink-1); line-height:1.5; }
.cal-hero-ttl .ccy{ display:inline-block; font-size:var(--t-xs); font-weight:700; color:var(--cu-txt); margin-inline-end:7px; }
.cal-hero-ttl .imp{ display:inline-block; padding:1px 7px 2px; margin-inline-end:8px; font-size:10.5px; font-weight:600;
  color:var(--ink-2); background:var(--wash); border:1px solid var(--rule); border-radius:var(--r1); }
.cal-countdown{ display:flex; align-items:center; gap:var(--s2); font-size:var(--t-lg); font-weight:700; color:var(--ink-1); min-block-size:40px; }
.cal-countdown b{ color:var(--cu-hi); }
.js-cal-cd{ color:var(--cu-hi); }
.cal-stats{ display:flex; gap:var(--s2); flex-wrap:wrap; }
.cal-stat{
  display:flex; flex-direction:column; align-items:center; gap:1px; min-inline-size:72px;
  padding:var(--s2) var(--s3); background:var(--bg-deep); border:1px solid var(--rule); border-radius:var(--r2);
}
.cal-stat b{ font-size:var(--t-lg); font-weight:700; color:var(--ink-1); }
.cal-stat span{ font-size:10.5px; font-weight:600; color:var(--ink-4); }
.cal-stat.hi b{ color:var(--dn); }
.cal-stat.rel b{ color:var(--up); }
.cal-released{
  display:flex; align-items:center; gap:var(--s2); flex-wrap:wrap;
  padding:var(--s3) var(--s4); font-size:var(--t-sm); font-weight:600;
  background:var(--up-wash); border:1px solid var(--up-line); border-radius:var(--r2); color:var(--up);
}

/* controls */
.cal-panel{
  display:flex; flex-direction:column; gap:var(--s3); padding:var(--s4);
  background:var(--panel); border:1px solid var(--rule); border-radius:var(--r3);
}
.cal-weekrow{ display:flex; align-items:center; gap:var(--s2); flex-wrap:wrap; }
.cal-weeklab{
  padding:4px 12px; font-size:var(--t-sm); font-weight:700; color:var(--ink-1);
  background:var(--bg-deep); border:1px solid var(--rule); border-radius:var(--r2);
}
.cal-weeklab.is-now{ border-color:var(--cu-line); color:var(--cu-hi); background:var(--cu-wash); }
.cal-src{ margin-inline-start:auto; font-size:var(--t-xs); color:var(--ink-4); direction:ltr; }
.cal-strip{ display:grid; grid-template-columns:repeat(7, minmax(0,1fr)); gap:6px; }
.cal-day{
  display:flex; flex-direction:column; align-items:center; gap:2px; cursor:pointer;
  padding:var(--s2) 4px; background:var(--panel-2); border:1px solid var(--rule); border-radius:var(--r2);
  color:var(--ink-2); transition:border-color var(--dur-1), background var(--dur-1);
}
.cal-day:hover{ border-color:var(--cu-line); background:var(--panel-3); }
.cal-day .dow{ font-size:10.5px; font-weight:600; color:var(--ink-4); }
.cal-day .dd{ font-size:var(--t-lg); font-weight:700; color:var(--ink-1); }
.cal-day .n{ font-size:10px; color:var(--ink-4); font-weight:600; }
.cal-day .dots{ display:flex; gap:2px; align-items:center; block-size:6px; }
.cal-day .dots i{ inline-size:4px; block-size:4px; border-radius:50%; background:var(--ink-4); }
.cal-day .dots i.h{ background:var(--dn); }
.cal-day .dots i.m{ background:var(--cu); }
.cal-day.on{ border-color:var(--cu); background:var(--cu-wash); }
.cal-day.on .dd{ color:var(--cu-hi); }
.cal-day.today .dow{ color:var(--cu-txt); }
.cal-day.empty{ opacity:.55; }
.cal-tz-chip{
  font-size:10.5px; font-weight:700; color:var(--cu-txt); direction:ltr;
  border:1px solid var(--cu-line); border-radius:var(--r1); padding:1px 7px;
}

/* the board — the only LTR island in the view */
.cal-board{ background:var(--panel); border:1px solid var(--rule); border-radius:var(--r3); overflow:hidden; direction:ltr; }
.cal-board-h{
  display:flex; align-items:center; gap:var(--s3); flex-wrap:wrap;
  padding:var(--s3) var(--s4); background:var(--bg-deep); border-block-end:1px solid var(--rule);
}
.cal-board-h .d{ font-size:var(--t-md); font-weight:700; color:var(--ink-1); }
.cal-board-h .m{ margin-inline-start:auto; font-size:var(--t-xs); color:var(--ink-4); direction:ltr; }
.cal-tbl{ display:block; }
.cal-th, .cal-tr{ display:grid; grid-template-columns:68px 84px 82px minmax(0,1fr) 96px 96px 96px 104px; }
.cal-th > *, .cal-tr > *{ padding:8px 10px; border-block-end:1px solid var(--rule-2); min-inline-size:0; }
.cal-tr > *{ align-self:center; }
.cal-th{
  position:sticky; inset-block-start:0; z-index:2;
  background:var(--bg-deep); border-block-end:1px solid var(--rule);
  font-size:10.5px; font-weight:700; color:var(--ink-3);
}
.cal-tr{ align-items:center; font-size:var(--t-sm); color:var(--ink-2); }
.cal-tr:hover{ background:var(--wash); }
.cal-tr.pending{ }                                  /* scheduled, not out yet */
.cal-tr.is-h{ box-shadow:inset 3px 0 0 var(--dn); }
.cal-tr.is-m{ box-shadow:inset 3px 0 0 var(--cu); }
.cal-tr.is-l{ box-shadow:inset 3px 0 0 var(--ink-4); }
.cal-tr.is-hol{ box-shadow:inset 3px 0 0 var(--hol); opacity:.8; }
.cal-tr.faded{ opacity:.55; }
.cal-tr .c-time{ font-weight:700; color:var(--ink-1); direction:ltr; }
.cal-tr .c-time small{ display:block; font-size:10px; color:var(--ink-4); font-weight:500; }
.cal-tr .c-ccy{ font-weight:700; color:var(--ink-1); direction:ltr; }
.cal-tr .c-imp{ display:flex; align-items:center; gap:5px; font-size:10.5px; font-weight:600; color:var(--ink-4); }
.imp-dot{ inline-size:7px; block-size:7px; border-radius:50%; flex:0 0 auto; background:var(--ink-4); }
.imp-dot.h{ background:var(--dn); }
.imp-dot.m{ background:var(--cu); }
.imp-dot.l{ background:var(--ink-4); }
.imp-dot.hol{ background:var(--hol); }
.cal-tr .c-ev{ min-inline-size:0; }
.cal-tr .c-ev .t{ font-weight:600; color:var(--ink-1); }
.cal-tr .c-ev .p{ font-size:10.5px; color:var(--ink-4); }
.cal-tr .c-ev .d{ display:block; margin-block-start:2px; font-size:var(--t-xs); color:var(--ink-4); line-height:1.6; }
.cal-tr .c-num{ direction:ltr; text-align:end; font-weight:600; }
.cal-tr .c-num.sched, .cal-tr .c-fc.sched, .cal-tr .c-pv.sched{ color:var(--ink-4); font-weight:500; }
.cal-tr .c-fc{ color:var(--cu-txt); }
.cal-tr .c-pv{ color:var(--ink-3); }
.cal-tr.released .c-act{ font-weight:700; }
.cal-tr.released .c-act.good b{ color:var(--up); }
.cal-tr.released .c-act.bad b{ color:var(--dn); }
.cal-tr .c-sur{ font-size:10px; font-weight:700; }
.cal-tr .c-sur.good{ color:var(--up); }
.cal-tr .c-sur.bad{ color:var(--dn); }
.cal-info{
  justify-self:end; align-self:center; padding:2px 9px; white-space:nowrap;
  min-block-size:24px; display:inline-flex; align-items:center;
  background:var(--cu-wash); border:1px solid var(--cu-line); border-radius:var(--r1);
  color:var(--cu-txt); font-size:10.5px; font-weight:700;
}
.cal-info:hover{ background:var(--cu-wash-2); }
.cal-timer{
  display:inline-flex; align-items:stretch; gap:3px; padding:2px 4px; direction:ltr;
  background:var(--bg-deep); border:1px solid var(--rule); border-radius:var(--r2);
}
.cal-timer .sg{
  display:inline-flex; flex-direction:column; align-items:center; justify-content:center;
  inline-size:32px; padding:1px 0; background:var(--wash); border-radius:var(--r1);
}
.cal-timer .sg b{ font-size:var(--t-sm); font-weight:700; line-height:1.05; color:var(--ink-1); }
.cal-timer .sg small{ font-size:7px; font-weight:600; color:var(--ink-4); }

/* side rail widgets */
.session{ display:flex; align-items:center; gap:var(--s2); padding:var(--s2) 0; border-block-end:1px solid var(--rule-2); font-size:var(--t-sm); }
.session:last-child{ border-block-end:0; }
.session .dot{ inline-size:6px; block-size:6px; }
.session.on .dot{ background:var(--up); }
.session.off .dot{ background:var(--ink-4); }
.session .state{ font-size:10.5px; font-weight:700; }
.session.on .state{ color:var(--up); }
.session.off .state{ color:var(--ink-4); }
.session .eta{ margin-inline-start:auto; font-size:10.5px; color:var(--ink-4); }
.cal-high-row{ padding:var(--s2) 0; border-block-end:1px solid var(--rule-2); font-size:var(--t-sm); }
.cal-high-row:last-child{ border-block-end:0; }
.cal-high-row .t{ font-weight:600; color:var(--ink-1); }
.cal-high-row .meta{ display:flex; align-items:center; gap:var(--s2); flex-wrap:wrap;
  margin-block-start:3px; font-size:10.5px; color:var(--ink-4); }
.cal-high-row .meta b{ color:var(--cu-txt); }

/* event explainer modal */
.cal-doc-ttl{ font-size:var(--t-xl); font-weight:700; color:var(--ink-1); line-height:1.6; }
.cal-doc-sub{ font-size:var(--t-xs); color:var(--ink-4); margin-block-start:2px; }
.cal-doc-meta{ display:flex; gap:var(--s2); flex-wrap:wrap; margin-block:var(--s3) var(--s1); }
.cal-doc-chip{
  padding:2px 9px; font-size:var(--t-xs); font-weight:600;
  background:var(--wash); border:1px solid var(--rule); border-radius:var(--r1); color:var(--ink-2);
}
.cal-doc-chip.imp{ color:var(--ink-1); }
.cal-doc-chip.imp.is-h{ color:var(--dn); border-color:var(--dn-line); background:var(--dn-wash); }
.cal-doc-chip.imp.is-m{ color:var(--cu-txt); border-color:var(--cu-line); background:var(--cu-wash); }
.cal-doc-chip.imp.is-l{ color:var(--ink-3); }
.cal-doc-chip.imp.is-hol{ color:var(--hol); border-color:var(--rule-3); }
.cal-doc-nums{ display:flex; gap:var(--s2); flex-wrap:wrap; margin-block:var(--s3); }
.cal-doc-num{
  min-inline-size:104px; padding:var(--s3); background:var(--panel-2);
  border:1px solid var(--rule-2); border-radius:var(--r2);
}
.cal-doc-num span{ display:block; font-size:10.5px; font-weight:600; color:var(--ink-4); }
.cal-doc-num b{ font-size:var(--t-lg); font-weight:700; color:var(--ink-1); direction:ltr; }
.cal-doc-num.good b{ color:var(--up); }
.cal-doc-num.bad b{ color:var(--dn); }
.cal-doc-sec{ margin-block:var(--s4); padding-inline-start:var(--s3); border-inline-start:2px solid var(--cu); }
.cal-doc-sec h4{ font-size:var(--t-sm); font-weight:700; color:var(--cu-txt); margin-block-end:var(--s2); }
.cal-doc-sec p{ font-size:var(--t-md); line-height:var(--lh-fa); color:var(--ink-2); margin:0; }
.cal-doc-foot{ display:flex; align-items:center; gap:var(--s3); flex-wrap:wrap; margin-block-start:var(--s4); }

/* ── historical price reaction block inside the explainer modal ──────────────
   A collapsible <details> so the keyboard toggles it for free; everything
   inside keeps the terminal's hairline + tabular-figure language. */
.cal-react{ margin-block:var(--s4) 0; border:1px solid var(--rule); border-radius:var(--r2);
  background:var(--panel-2); overflow:hidden; }
.cal-react.is-none{ padding:var(--s3) var(--s4); }
.cal-react .cr-hd{ display:flex; align-items:center; gap:var(--s2); flex-wrap:wrap;
  padding:var(--s3) var(--s4); cursor:pointer; border-block-end:1px solid var(--rule);
  background:var(--panel-3); }
.cal-react.is-none .cr-hd{ border:0; padding:0 0 var(--s2); background:none; cursor:default; }
.cal-react .cr-hd h4{ margin:0; font-size:var(--t-sm); font-weight:700; color:var(--cu-txt); }
.cal-react .cr-hd::marker{ color:var(--cu); }
.cal-react .cr-hd::-webkit-details-marker{ color:var(--cu); }
.cr-rule{ font-size:var(--t-xs); color:var(--ink-2); }
.cr-badge{ margin-inline-start:auto; font-size:10.5px; color:var(--ink-3);
  border:1px solid var(--rule-3); border-radius:var(--r-pill); padding:2px 8px; background:var(--wash); }
.cal-react > #calReactBody{ padding:var(--s3) var(--s4) var(--s2); }
.cr-chips{ display:flex; gap:5px; flex-wrap:wrap; margin-block-end:var(--s2); }
.cr-chip{ font:inherit; font-size:var(--t-xs); direction:ltr; color:var(--ink-2);
  background:var(--wash); border:1px solid var(--rule); border-radius:var(--r-pill);
  padding:2px 10px; cursor:pointer; font-variant-numeric:tabular-nums; }
.cr-chip:hover{ color:var(--ink-1); border-color:var(--rule-3); }
.cr-chip:focus-visible{ outline:2px solid var(--cu); outline-offset:1px; }
.cr-chip.on{ color:var(--cu-hi); border-color:var(--cu-line); background:var(--cu-wash); }
.cr-mx{ font-style:normal; color:var(--ink-4); }
.cr-chart{ background:var(--bg-deep); border:1px solid var(--rule); border-radius:var(--r2);
  padding:4px 6px; direction:ltr; }
.cr-svg{ display:block; inline-size:100%; block-size:auto; }
.cr-svg .cr-zero{ stroke:var(--rule-3); stroke-width:1; stroke-dasharray:3 3; }
.cr-svg .cr-path{ fill:none; stroke-width:1.6; stroke-linejoin:round; }
.cr-svg .cr-path.is-pos{ stroke:var(--up); }
.cr-svg .cr-path.is-neg{ stroke:var(--dn); }
.cr-svg .cr-path.is-flat{ stroke:var(--ink-4); stroke-dasharray:4 3; }
.cr-svg .cr-dot{ stroke:none; }
.cr-svg .cr-dot.is-pos{ fill:var(--up); } .cr-svg .cr-dot.is-neg{ fill:var(--dn); }
.cr-svg .cr-dot.is-flat{ fill:var(--ink-4); }
.cr-svg .cr-ax{ fill:var(--ink-4); font-size:9px; direction:ltr;
  font-variant-numeric:tabular-nums; }
.cr-svg .cr-ax.is-x{ font-size:8.5px; }
.cr-capline{ display:flex; justify-content:space-between; gap:var(--s3); flex-wrap:wrap;
  margin-block:6px var(--s3); font-size:10.5px; color:var(--ink-3); }
.cr-live{ color:var(--up); }
.cr-live.is-ref{ color:var(--cu); }
.cr-tbl{ display:flex; flex-direction:column; gap:1px; overflow:auto; }
.cr-tr{ display:grid; align-items:center; gap:6px; padding:5px 6px; border-radius:var(--r1);
  grid-template-columns:1.05fr .75fr .75fr 1.5fr .72fr .72fr .5fr; }
.cr-tr:nth-child(even){ background:var(--wash); }
.cr-tr.cr-th{ background:none; border-block-end:1px solid var(--rule); border-radius:0;
  color:var(--ink-4); font-size:10px; padding-block:2px; }
.cr-tr.cr-th span{ font-weight:600; }
.cr-d{ font-size:10.5px; color:var(--ink-3); white-space:nowrap; }
.cr-n{ font-size:var(--t-xs); color:var(--ink-1); font-variant-numeric:tabular-nums; }
.cr-n.pos{ color:var(--up); } .cr-n.neg{ color:var(--dn); }
.cr-sur{ font-size:10.5px; color:var(--ink-3); font-variant-numeric:tabular-nums; }
.cr-sur.is-pos{ color:var(--up); } .cr-sur.is-neg{ color:var(--dn); }
.cr-src{ font-size:9.5px; text-align:center; color:var(--cu); border:1px solid var(--cu-line);
  border-radius:var(--r-pill); background:var(--cu-wash); }
.cr-src.is-live{ color:var(--up); border-color:var(--up-line); background:var(--up-wash); }
.cr-stat{ margin:var(--s3) 0 0; font-size:var(--t-xs); line-height:var(--lh-fa);
  color:var(--ink-2); padding-inline-start:var(--s3); border-inline-start:2px solid var(--cu); }
.cr-stat.is-mixed{ border-inline-start-color:var(--ink-4); }
.cr-counts{ display:block; margin-block-start:3px; color:var(--ink-4); font-size:10.5px;
  font-variant-numeric:tabular-nums; }
.cr-foot{ display:block; margin-block-start:var(--s3); }
@media (max-width:640px){
  .cr-tr{ grid-template-columns:1fr .7fr .7fr .7fr; }
  .cr-tr.cr-th span:nth-child(3), .cr-tr .cr-sur{ display:none; }
  .cr-tr.cr-th span:nth-child(4){ display:block; }
  .cr-tr .cr-d{ grid-column:1 / -1; }
}

/* currency filter (multi-select): one tick-box per currency, so USD *and* EUR
   *and* JPY can be on at the same time; an empty row means "all currencies" */
.ccy-row{ gap:var(--s2); }
.ccy-lbl{ min-inline-size:56px; }
.ccy-list{ display:flex; flex-wrap:wrap; gap:6px; }
.ccy{
  position:relative; display:inline-flex; align-items:center;
  padding:3px 9px; border:1px solid var(--rule); border-radius:var(--r1);
  background:var(--panel-2); color:var(--ink-3); font-size:var(--t-xs); font-weight:700;
  direction:ltr; cursor:pointer;
  transition:border-color var(--dur-1) var(--ease), color var(--dur-1) var(--ease),
             background var(--dur-1) var(--ease);
}
.ccy:hover{ border-color:var(--cu-line); color:var(--ink-2); }
.ccy input{ position:absolute; opacity:0; inline-size:1px; block-size:1px; margin:0; }
.ccy span{ display:inline-flex; align-items:center; gap:5px; }
.ccy span::before{
  content:""; inline-size:9px; block-size:9px; border:1px solid var(--rule-strong);
  border-radius:2px; background:transparent; transition:background var(--dur-1) var(--ease);
}
.ccy.on{ background:var(--cu-wash); border-color:var(--cu); color:var(--cu-txt); }
.ccy.on span::before{ background:var(--cu); border-color:var(--cu); box-shadow:inset 0 0 0 1.5px var(--panel-2); }
.ccy input:focus-visible + span{ outline:2px solid var(--cu-hi); outline-offset:3px; border-radius:2px; }

/* archive day boxes (the archive view reuses this shape) */
.calday{ background:var(--panel); border:1px solid var(--rule); border-radius:var(--r3); overflow:hidden; margin-block-end:var(--s3); }
.calday-h{
  display:flex; justify-content:space-between; align-items:center; gap:var(--s2); flex-wrap:wrap;
  padding:var(--s2) var(--s4); background:var(--bg-deep); border-block-end:1px solid var(--rule); font-size:var(--t-sm);
}
.calday-title{ font-weight:700; color:var(--ink-1); }
.calday-meta{ font-size:var(--t-xs); color:var(--ink-4); }
.archday .calday-h{ background:var(--panel-2); }
/* six news boxes per row, as asked — one track each, no auto-fill guessing */
.archgrid{ display:grid; grid-template-columns:repeat(6, minmax(0,1fr)); gap:var(--s3); padding:var(--s3); }

/* ── 16 · ETF BOARD ─────────────────────────────────────────────────────── */
.etfgroups{ display:flex; flex-direction:column; gap:var(--s4); }
.etfgroup{ padding:var(--s3) var(--s4) var(--s4); background:var(--panel); border:1px solid var(--rule); border-radius:var(--r3); box-shadow:var(--inset-hi); }
.etfgroup-t{ display:flex; align-items:center; gap:var(--s2); margin:0 0 var(--s3); font-size:var(--t-sm); font-weight:700; color:var(--cu-hi); }
.etfgroup-t .n{ font-size:var(--t-xs); font-weight:500; color:var(--ink-4); }
.etfgroup-t::after{ content:""; flex:1; block-size:1px; background:linear-gradient(90deg, var(--cu-line), transparent); }
.etfgrid{ display:grid; grid-template-columns:repeat(auto-fill, minmax(172px,1fr)); gap:var(--s2); }
.etfcard{
  display:flex; flex-direction:column; gap:1px; padding:var(--s3);
  background:var(--panel-2); border:1px solid var(--rule-2); border-radius:var(--r2);
}
.etfcard:hover{ border-color:var(--cu-line); }
.etfcard-top{ display:flex; align-items:center; justify-content:space-between; gap:var(--s2); }
.etfcard .tk{ font-size:var(--t-sm); font-weight:700; direction:ltr; color:var(--ink-1); }
.etfcard .ms{ font-size:10px; padding:0 6px; border:1px solid var(--rule); border-radius:var(--r1); color:var(--ink-4); }
.etfcard .ms.live{ color:var(--up); border-color:var(--up-line); }
.etfcard .nm{ font-size:var(--t-xs); color:var(--ink-4); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.etfcard .prc{ margin-block-start:var(--s1); font-size:var(--t-xl); font-weight:700; direction:ltr; text-align:start; color:var(--ink-1); }
.etfcard .chg{ font-size:var(--t-xs); font-weight:700; direction:ltr; text-align:start; }
.etfcard .chg.up{ color:var(--up); }
.etfcard .chg.dn{ color:var(--dn); }
/* ── 17 · TELEGRAM DIGEST ───────────────────────────────────────────────── */
.tg-toggles{ display:grid; grid-template-columns:repeat(auto-fill, minmax(250px,1fr)); gap:4px var(--s4); }
.tgopt{
  display:flex; align-items:center; gap:var(--s2); padding:var(--s2);
  font-size:var(--t-sm); color:var(--ink-2); border-radius:var(--r2); cursor:pointer;
}
.tgopt:hover{ background:var(--wash); }
.tgopt input{ accent-color:var(--cu); }
.tgopt .ic{ color:var(--cu-2); }
.tg-template{
  inline-size:100%; min-block-size:110px; resize:vertical;
  direction:ltr; text-align:left; font-size:var(--t-xs); line-height:1.9;
  background:var(--bg-deep); border:1px solid var(--rule); border-radius:var(--r2);
  color:var(--ink-1); padding:var(--s3);
}
.tg-vars{ font-size:var(--t-xs); color:var(--ink-4); line-height:var(--lh-fa); margin-block-end:var(--s2); }
.tg-vars code{ color:var(--cu-txt); direction:ltr; display:inline-block; }
.tg-preview{
  display:none; margin-block-start:var(--s3); padding:var(--s3) var(--s4);
  background:var(--bg-deep); border:1px solid var(--rule); border-radius:var(--r2);
  font-size:var(--t-sm); line-height:var(--lh-fa); white-space:pre-wrap; color:var(--ink-2);
}
.tg-preview.on{ display:block; }
.tg-actions{ display:flex; gap:var(--s2); flex-wrap:wrap; align-items:flex-end; }
.settings-note{ margin-block-start:var(--s3); font-size:var(--t-xs); color:var(--ink-4); line-height:var(--lh-fa); }

/* ── 18 · COMMAND PALETTE (Ctrl/Cmd+K) ──────────────────────────────────────
   One field, fuzzy-ish substring match over views, assets and reports, arrow
   keys to move, Enter to go. Nothing else in the app uses these classes. */
.cmdk{
  position:fixed; inset:0; z-index:700; display:none;
  padding-block-start:14vh; padding-inline:var(--s4);
  justify-content:center; align-items:flex-start;
  background:rgba(6,5,4,.7); -webkit-backdrop-filter:blur(8px); backdrop-filter:blur(8px);
}
.cmdk.open{ display:flex; animation:ovIn var(--dur-1) var(--ease); }
.cmdk-box{
  inline-size:100%; max-inline-size:620px; overflow:hidden;
  background:var(--panel-2); border:1px solid var(--rule-3); border-radius:var(--r3);
  box-shadow:var(--sh-2);
}
.cmdk-field{ display:flex; align-items:center; gap:var(--s3); padding:var(--s3) var(--s4); border-block-end:1px solid var(--rule); }
.cmdk-field .ic{ color:var(--cu); font-size:16px; }
.cmdk-field input{
  flex:1; min-inline-size:0; padding:0; border:0; background:transparent;
  font-size:var(--t-lg); color:var(--ink-1);
}
.cmdk-field input:focus{ box-shadow:none; }
.cmdk-field kbd{ font-size:10px; color:var(--ink-4); border:1px solid var(--rule); border-radius:var(--r1); padding:1px 6px; }
.cmdk-list{ max-block-size:min(52vh, 420px); overflow:auto; overscroll-behavior:contain; padding:var(--s1); }
.cmdk-item{
  display:flex; align-items:center; gap:var(--s3); inline-size:100%;
  padding:var(--s2) var(--s3); background:transparent; border:0; border-radius:var(--r2);
  color:var(--ink-2); font-size:var(--t-md); text-align:start;
}
.cmdk-item .ic{ color:var(--ink-4); font-size:15px; }
.cmdk-item .cmdk-kind{ margin-inline-start:auto; font-size:var(--t-xs); color:var(--ink-4); }
.cmdk-item.sel, .cmdk-item:hover{ background:var(--cu-wash); color:var(--cu-txt); }
.cmdk-item.sel .ic, .cmdk-item:hover .ic{ color:var(--cu); }
.cmdk-empty{ padding:var(--s5); text-align:center; color:var(--ink-4); font-size:var(--t-sm); }
.cmdk-foot{
  display:flex; align-items:center; gap:var(--s3); padding:var(--s2) var(--s4);
  border-block-start:1px solid var(--rule); font-size:var(--t-xs); color:var(--ink-4);
}
.cmdk-foot .sp{ margin-inline-start:auto; }

/* ── 19 · ACCESSIBILITY: contrast, motion, touch ─────────────────────────── */
@media (prefers-reduced-motion: reduce){
  *, *::before, *::after{ animation-duration:.001ms !important; animation-iteration-count:1 !important;
    transition-duration:.001ms !important; scroll-behavior:auto !important; }
  .dl2-ticker{ overflow-x:auto; scrollbar-width:none; }
  .dl2-ticker::-webkit-scrollbar{ block-size:0; }
  .dl2-ticker .tk-track{ animation:none; }
}
@media (prefers-reduced-transparency: reduce){
  .app-topbar, .tb, .overlay, .cmdk, .sidebar-backdrop{ background:var(--panel) !important; backdrop-filter:none !important; }
}
@media (pointer: coarse){
  .btn, .chip, .mclose, .star-btn, .del-btn, .cal-info, .tb-btn, .tb-chip, .nav-item{ min-block-size:44px; }
  .tb-btn, .tb-chip{ min-inline-size:44px; }
  /* the 24px card actions below are the desktop floor (WCAG 2.2 SC 2.5.8);
     a finger gets a full 44px target in both axes, not a 24-wide strip */
  .star-btn, .del-btn{ inline-size:44px; block-size:44px; }
  .cal-info{ min-inline-size:44px; }
}

/* ── 20 · PRINT ─────────────────────────────────────────────────────────────
   Printing a report should give paper: chrome out, the document in. */
@media print{
  .app-sidebar, .app-topbar, .dl2-ticker, .assets, .tb, .tb-wrap, .overlay, .toast, .cmdk, .stage{ display:none !important; }
  html, body{ overflow:visible; background:#fff; color:#111; block-size:auto; }
  .app-shell, .app-body, .app-main{ display:block; block-size:auto; overflow:visible; }
  .view-container{ padding:0; }
  .view{ display:none !important; }
  .view.active{ display:block !important; }
  .rep-doc{ max-block-size:none; overflow:visible; border:0; padding:0; background:#fff; color:#111; }
  .rep-doc p, .rep-doc h3, .rep-doc h4{ color:#111; max-inline-size:none; }
  .rep-doc h3{ border-block-end-color:#bbb; }
  .panelbox, .chartbox, .idea-card, .ncard, .lead-card{ border-color:#ccc; background:#fff; }
  .ncard .thumb img, .lead-card .thumb img{ filter:none !important; }
  .ncard .thumb::before, .ncard .thumb::after,
  .lead-card .thumb::before, .lead-card .thumb::after{ display:none !important; }
  .rep-side, .chartbox{ break-inside:avoid; }
}

/* ── 21 · RESPONSIVE ────────────────────────────────────────────────────────
   One ladder, each step doing one thing: give the reading column its width,
   stack the two-column views, fold the wide table, put the rail in a drawer. */
@media (max-width:1400px){
  .rep-layout{ grid-template-columns:minmax(0,1fr) minmax(380px,480px); }
  .rep-doc{ padding:var(--s6); }
  .archgrid{ grid-template-columns:repeat(4, minmax(0,1fr)); }
}
@media (max-width:1240px){
  .rep-layout{ grid-template-columns:minmax(0,1fr) minmax(340px,420px); }
  .topbar-telemetry{ display:none; }
  .cal-grid{ grid-template-columns:minmax(0,1fr) 290px; }
}
@media (max-width:1180px){
  .cal-th, .cal-tr{ grid-template-columns:58px 72px 68px minmax(0,1fr) 84px 84px 84px 92px; }
  .rep-side{ position:static; }
  .rep-doc{ max-block-size:none; overflow:visible; }
  .tv-hero{ grid-template-columns:1fr; }
  .tv-hero .tvh-r{ align-items:flex-start; }
  .archgrid{ grid-template-columns:repeat(3, minmax(0,1fr)); }
}
@media (max-width:1080px){
  .rep-layout{ grid-template-columns:1fr; }
  .rep-side .tvwrap{ block-size:min(56vh,460px); }
}
@media (max-width:980px){
  .cal-grid{ grid-template-columns:1fr; }
  /* one column folds away: previous first, so the event name keeps its room */
  .cal-th, .cal-tr{ grid-template-columns:54px 64px 60px minmax(0,1fr) 76px 76px 82px; }
  .cal-th > *:nth-child(7), .cal-tr > *:nth-child(7){ display:none; }
  .cal-side{ flex-direction:row; flex-wrap:wrap; }
  .cal-side .panelbox{ flex:1 1 260px; margin-block-end:0; }
  .archgrid{ grid-template-columns:repeat(2, minmax(0,1fr)); }
}
@media (max-width:860px){
  .menu-toggle-btn{ display:grid !important; }
  .app-sidebar{
    position:fixed !important; top:0 !important; bottom:0 !important; right:0 !important; left:auto !important; inline-size:266px !important;
    padding-block-start:var(--s5); z-index:200; transform:translateX(100%) !important;
    box-shadow:var(--sh-1); border-left:1px solid var(--rule) !important; border-right:none !important; display:flex !important;
    transition:transform var(--dur-3) var(--ease) !important;
  }
  .app-sidebar.open{ transform:translateX(0) !important; display:flex !important; }
  .sidebar-backdrop{ position:fixed; inset:0; z-index:150; display:none; background:rgba(4,3,2,.6); }
  .sidebar-backdrop.open{ display:block; }
  .view-container{ padding:var(--s4); }
  .ngrid{ grid-template-columns:1fr; }
  .assets{ padding-inline:var(--s4); }
  .lead-cards{ grid-template-columns:1fr; }
}
@media (max-width:780px){
  .cal-th, .cal-tr{ grid-template-columns:50px 58px 46px minmax(0,1fr) 74px 78px; }
  .cal-th > *:nth-child(6), .cal-tr > *:nth-child(6){ display:none; }
  .cal-tr .imp-lab{ display:none; }
  .cal-strip{ grid-template-columns:repeat(4, minmax(0,1fr)); }
  .archgrid{ grid-template-columns:1fr; padding:var(--s2); }
  .idea-thumb{ aspect-ratio:2/1; }
}
@media (max-width:720px){
  /* absolute, not fixed: a .view carries a settled transform, so a fixed sheet
     would be positioned against the view rather than the screen */
  .fsheet{ inset-inline:0; inline-size:auto; max-block-size:min(72vh, 560px); }
  .tb-count{ margin-inline-start:0; }
  .ncard .thumb{ aspect-ratio:2/1; }
  .ncard .summ{ -webkit-line-clamp:2; }
  .rep-doc p{ font-size:var(--t-md); }
  .rep-doc{ padding:var(--s4); }
  .modal{ padding:var(--s4) var(--s4) var(--s4); max-block-size:94vh; }
  .tvwrap{ block-size:min(60vh,420px); }
}
@media (max-width:600px){
  .view-container{ padding:var(--s3); }
  .cal-side{ flex-direction:column; }
  .rep-hero{ grid-template-columns:1fr; }
  .rep-hero .rh-side{ align-items:flex-start; }
  .setrow{ grid-template-columns:1fr; }
  .setrow select[style]{ inline-size:100% !important; }
  .ngrid{ gap:var(--s3); }
  .cal-strip{ grid-template-columns:repeat(3, minmax(0,1fr)); }
  .topbar-telemetry{ display:none; }
  .brand-desc{ display:none; }
}

/* ══════════ smart alert rules — builder, rule list, execution log, stack ══════════
   Same instrument language: hairlines, one copper accent, tabular figures. The
   notification stack is fixed to the inline-end edge so it never covers the rail. */
.ar-builder{ border:1px solid var(--rule); border-radius:var(--r2); background:var(--panel-2);
  padding:var(--s3) var(--s4) var(--s4); }
.ar-top{ display:grid; gap:var(--s3); grid-template-columns:2fr 1.2fr 1fr; margin-block-end:var(--s3); }
.ar-top label, .ar-builder label{ display:block; font-size:10.5px; color:var(--ink-4);
  margin-block-end:3px; }
.ar-top input, .ar-top select{ inline-size:100%; }
.ar-conds{ display:flex; flex-direction:column; gap:6px; }
.ar-cond{ display:grid; grid-template-columns:auto 150px 1fr auto; gap:8px; align-items:center;
  background:var(--panel-3); border:1px solid var(--rule); border-radius:var(--r2);
  padding:7px 9px; }
.ar-idx{ font-variant-numeric:tabular-nums; color:var(--cu); font-size:var(--t-xs);
  inline-size:20px; text-align:center; }
.ar-cond select, .ar-cond input{ font:inherit; font-size:var(--t-xs); color:var(--ink-1);
  background:var(--well); border:1px solid var(--rule-3); border-radius:var(--r1); padding:4px 7px; }
.ar-fields{ display:flex; gap:7px; flex-wrap:wrap; align-items:center; min-inline-size:0; }
.ar-unit{ font-size:10.5px; color:var(--ink-4); }
.ar-del{ background:none; border:1px solid var(--rule); border-radius:var(--r1); color:var(--ink-4);
  cursor:pointer; padding:4px 6px; display:inline-flex; }
.ar-del:hover{ color:var(--dn); border-color:var(--dn-line); background:var(--dn-wash); }
.ar-btns{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-block-start:var(--s3); }
.ar-acts{ display:flex; gap:var(--s3); flex-wrap:wrap; margin-block-start:6px; }
.ar-act{ display:inline-flex; align-items:center; gap:6px; font-size:var(--t-xs); color:var(--ink-2);
  border:1px solid var(--rule); border-radius:var(--r-pill); padding:4px 10px; cursor:pointer;
  background:var(--wash); }
.ar-act:hover{ border-color:var(--rule-3); color:var(--ink-1); }
.ar-act input{ accent-color:var(--cu); }
.ar-act svg{ inline-size:13px; block-size:13px; color:var(--ink-4); }
#arHint{ white-space:pre-line; margin-block-start:var(--s2); min-block-size:1.2em; }
#arHint.is-bad{ color:var(--dn); } #arHint.is-ok{ color:var(--up); }
.ar-list{ display:flex; flex-direction:column; gap:8px; }
.ar-item{ border:1px solid var(--rule); border-radius:var(--r2); background:var(--panel-2);
  padding:var(--s3) var(--s4); }
.ar-item.is-off{ opacity:.55; }
.ar-item-hd{ display:flex; align-items:center; gap:var(--s3); flex-wrap:wrap; }
.ar-item-hd b{ font-size:var(--t-sm); color:var(--ink-1); }
.ar-sw{ margin:0; }
.ar-tag{ font-size:10.5px; color:var(--cu-txt); border:1px solid var(--cu-line);
  background:var(--cu-wash); border-radius:var(--r-pill); padding:1px 8px; }
.ar-meta{ font-size:10.5px; color:var(--ink-4); font-variant-numeric:tabular-nums; }
.ar-item-btns{ margin-inline-start:auto; display:flex; gap:6px; }
.ar-item-body{ margin-block-start:6px; font-size:var(--t-xs); color:var(--ink-2);
  line-height:var(--lh-fa); }
.ar-item-acts{ margin-block-start:5px; display:flex; gap:var(--s3); flex-wrap:wrap;
  font-size:10.5px; color:var(--ink-4); font-variant-numeric:tabular-nums; }
.ar-tpl{ direction:ltr; unicode-bidi:embed; max-inline-size:100%; overflow:hidden;
  text-overflow:ellipsis; white-space:nowrap; }
.ar-log{ display:flex; flex-direction:column; gap:3px; }
.ar-lrow{ display:grid; grid-template-columns:auto auto auto 1fr; gap:10px; align-items:baseline;
  padding:5px 8px; border-radius:var(--r1); font-size:var(--t-xs); }
.ar-lrow:nth-child(even){ background:var(--wash); }
.ar-lt{ color:var(--cu); font-variant-numeric:tabular-nums; direction:ltr; }
.ar-ld{ color:var(--ink-4); font-variant-numeric:tabular-nums; direction:ltr; }
.ar-lrow b{ color:var(--ink-1); font-weight:600; }
.ar-lb{ color:var(--ink-3); }

/* ── notification stack ── */
.alert-stack{ position:fixed; inset-block-start:70px; inset-inline-end:16px; z-index:1200;
  display:flex; flex-direction:column; gap:8px; inline-size:min(340px, 88vw); pointer-events:none; }
.alert-card{ pointer-events:auto; background:var(--panel); border:1px solid var(--cu-line);
  border-inline-start:3px solid var(--cu); border-radius:var(--r2); box-shadow:var(--sh-2);
  padding:9px 11px; }
.alert-card.is-warn{ border-inline-start-color:var(--dn); border-color:var(--dn-line); }
.alert-card.is-out{ opacity:.35; transform:translateX(-8px); }
.al-hd{ display:flex; align-items:center; gap:7px; }
.al-ic{ color:var(--cu); display:inline-flex; }
.alert-card.is-warn .al-ic{ color:var(--dn); }
.al-hd b{ font-size:var(--t-xs); color:var(--ink-1); flex:1; }
.al-x{ background:none; border:0; color:var(--ink-4); cursor:pointer; padding:2px; display:inline-flex; }
.al-x:hover{ color:var(--dn); }
.al-bd{ margin-block-start:4px; font-size:10.5px; color:var(--ink-2); line-height:1.75; }
.al-ft{ margin-block-start:5px; display:flex; justify-content:space-between;
  font-size:9.5px; color:var(--ink-4); font-variant-numeric:tabular-nums; }
.al-tag{ color:var(--cu); }
@media (max-width:820px){
  .ar-top{ grid-template-columns:1fr; }
  .ar-cond{ grid-template-columns:auto 1fr auto; grid-template-areas:'idx kind del' 'fields fields fields'; }
  .ar-idx{ grid-area:idx; } .ar-cond select.ar-kind{ grid-area:kind; }
  .ar-fields{ grid-area:fields; } .ar-del{ grid-area:del; }
  .alert-stack{ inset-inline:10px; inline-size:auto; }
}

/* ── PWA · offline-first status (topbar telemetry) ──────────────────────────
   The rest of the capsule answers "how fresh is the data"; this item answers
   "is there a server behind it". One dot and one word, in the same 10px
   tabular style as its neighbours — no new chrome, no badge. The state comes
   from what the last request actually did, so a reachable network that cannot
   reach Flask still reads as Offline (Cache Mode). */
.pwa-item{ gap:6px; }
.pwa-item b{ color:var(--ink-2); font-size:10px; letter-spacing:.02em; }
.pwa-dot{
  inline-size:7px; block-size:7px; border-radius:50%; flex:0 0 auto;
  background:var(--ink-4); box-shadow:0 0 0 1px rgba(154,182,224,.14) inset;
  transition:background .2s ease, box-shadow .2s ease;
}
.pwa-item[data-mode="online"] .pwa-dot{ background:var(--up); box-shadow:0 0 0 2px rgba(87,177,131,.18); }
.pwa-item[data-mode="offline"] .pwa-dot{ background:var(--dn); box-shadow:0 0 0 2px rgba(217,106,85,.18); }
.pwa-item[data-mode="offline"] b{ color:var(--dn); }
.pwa-item[data-mode="error"] .pwa-dot{ background:var(--dn); }
.pwa-item[data-mode="syncing"] .pwa-dot,
.pwa-item[data-mode="boot"] .pwa-dot{ background:var(--cu); animation:pwaPulse 1.1s ease-in-out infinite; }
@keyframes pwaPulse{ 0%,100%{ opacity:.3; } 50%{ opacity:1; } }
@media (max-width:1080px){ .pwa-item b{ display:none; } }   /* the dot alone carries it */
@media (prefers-reduced-motion:reduce){ .pwa-item .pwa-dot{ animation:none; } }
.pwa-item[data-mode="warn"] .pwa-dot{ background:var(--cu); }

/* ── LIVE STREAM · incremental UI ───────────────────────────────────────────
   A headline that arrives through the stream is inserted above the list. It has
   to be *noticeable* without being a jump: a short height-settled fade, one
   second, no layout animation that would fight the scroll correction. */
@keyframes streamCardIn{
  from{ opacity:0; transform:translateY(-6px); }
  to{ opacity:1; transform:none; }
}
.ncard.card-enter{ animation:streamCardIn .42s cubic-bezier(.22,.61,.36,1) both; }
.ncard.card-enter::before{
  content:''; position:absolute; inset-inline-start:0; inset-block:0; inline-size:2px;
  background:var(--cu); opacity:.65;
}
/* an indicator just released (pushed on the calendar channel): the row keeps a
   copper edge for ten seconds, so the release that moved while you were
   watching is unmistakable on a board of a hundred rows */
.cal-tr.just-released{ box-shadow:inset 2px 0 0 var(--cu); background:rgba(200,150,93,.06); }
.cal-tr.just-released .c-num.c-act b{ color:var(--cu-hi,var(--cu)); }
@media (prefers-reduced-motion:reduce){ .ncard.card-enter{ animation:none; } }

/* ── PHONE (≤768px) ────────────────────────────────────────────────────────
   The narrowest breakpoint in the shell. Three things have to give on a phone:
   the telemetry capsule (the stream and storage pills keep their dots and drop
   their words), the feed's multi-column grid (one story per row), and the
   calendar board's fixed column track (it scrolls sideways instead of
   squeezing the event names into an ellipsis). */
@media (max-width: 768px){
  .topbar-telemetry{ gap:5px; }
  .pwa-item b{ display:none; }
  .telem-divider{ margin-inline:2px; }
  .ngrid{ grid-template-columns:1fr; }
  .cal-scroll{ overflow-x:auto; -webkit-overflow-scrolling:touch; }
  .cal-th, .cal-tr{ min-inline-size:660px; }
  .app-main{ padding-inline:10px; }
}

/* ══ VIRTUALISED GRIDS ══════════════════════════════════════════════════════
   The host keeps the grid's own look — cards still sit in equal columns — but
   it stops being the element that measures the list. A spacer carries the
   total computed height, so the scrollbar stays honest for the whole archive,
   and an absolutely-positioned layer holds only the rows on screen. */
.vs-host{ display:block !important; position:relative; }
/* the spacer carries only the height the scroller measured; it is not given a
   block-size here, so a logical/physical declaration cannot fight the inline
   height the layout sets on it */
.vs-spacer{ inline-size:100%; pointer-events:none; }
.vs-layer{ position:absolute; inset-block-start:0; inset-inline:0; }
.vs-row{ position:absolute; inset-inline:0; display:grid; gap:var(--s4); align-items:stretch; }
.vs-row.vs-full{ grid-template-columns:1fr !important; }
.vs-row > *{ min-inline-size:0; }
/* a day header is its own full-width row now; the day box still wraps a whole
   day in the non-windowed fallback path */
.vs-row.vs-full > .calday.archday{ margin:0; }

/* ══ PERF HUD — the counters the benchmark table quotes, on the live page ══ */
.phud{ position:fixed; inset-block-start:calc(var(--topbar-h) + var(--s3));
  inset-inline-start:var(--s4); z-index:420; inline-size:min(370px,86vw);
  padding:var(--s3) var(--s3) var(--s2); border:1px solid var(--rule-2);
  border-radius:var(--r2); background:var(--panel-2); box-shadow:var(--sh-2);
  color:var(--ink-2); font-size:var(--t-xs); }
.phud-h{ display:flex; align-items:center; justify-content:space-between; gap:var(--s2);
  margin-block-end:var(--s2); padding-block-end:var(--s1); border-block-end:1px solid var(--rule);
  color:var(--cu-txt); font-weight:700; letter-spacing:.02em; }
.phud-x{ all:unset; cursor:pointer; inline-size:18px; block-size:18px; display:grid;
  place-items:center; border-radius:var(--r-pill); color:var(--ink-3); }
.phud-x:hover{ background:var(--wash-2); color:var(--cu-txt); }
.phud-r{ display:flex; align-items:baseline; justify-content:space-between; gap:var(--s3);
  padding-block:2px; border-block-end:1px dashed var(--rule); font-variant-numeric:tabular-nums; }
.phud-r:last-of-type{ border-block-end:0; }
.phud-r b{ color:var(--ink-1); font-weight:700; }
.phud-r em{ color:var(--cu-txt); font-style:normal; font-weight:700; }
.phud-n{ margin-block-start:var(--s2); color:var(--ink-4); font-size:10px;
  line-height:var(--lh-fa); }
/* ══ ON-DEMAND AUDIO READER (News Cards & Reports) ══ */
.audio-read-btn{
  all:unset; cursor:pointer;
  display:inline-flex; align-items:center; justify-content:center;
  width:24px; height:24px; border-radius:var(--r1);
  color:var(--ink-3); transition:all var(--dur-1) var(--ease);
  position:relative;
}
.audio-read-btn:hover{ color:var(--cu-txt); background:var(--wash-2); }
.audio-read-btn.playing{
  color:var(--up); background:rgba(87,177,131,0.15);
  border:1px solid var(--up);
}
.audio-wave{
  display:none; align-items:flex-end; gap:1.5px; height:10px; margin-inline-start:2px;
}
.audio-read-btn.playing .audio-wave,
.audio-rep-btn.playing .audio-wave,
.audio-modal-btn.playing .audio-wave{
  display:inline-flex;
}
.audio-wave span{
  width:2px; height:3px; background:currentColor; border-radius:1px;
  animation:audioWavePulse 0.4s infinite alternate ease-in-out;
}
.audio-wave span:nth-child(1){ animation-delay:0.05s; }
.audio-wave span:nth-child(2){ animation-delay:0.2s; }
.audio-wave span:nth-child(3){ animation-delay:0.1s; }
@keyframes audioWavePulse{
  0%{ height:2px; }
  100%{ height:10px; }
}
.ncard.is-speaking{
  border-color:var(--cu);
  box-shadow:0 0 10px rgba(200, 150, 93, 0.25);
}
.audio-rep-btn.playing,
.audio-modal-btn.playing{
  color:var(--up) !important;
  border-color:var(--up) !important;
  background:rgba(87,177,131,0.12) !important;
}

/* ══ WHALE LIQUIDITY TRACKER ══ */
.whale-hero{
  display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:var(--s4);
  padding:var(--s4); background:var(--panel); border:1px solid var(--rule); border-radius:var(--r3);
  margin-bottom:var(--s4);
}
.whale-kpi{ background:var(--panel-2); border:1px solid var(--rule-2); border-radius:var(--r2); padding:var(--s3); display:flex; flex-direction:column; gap:var(--s1); }
.whale-kpi-title{ font-size:var(--t-xs); color:var(--ink-3); display:flex; justify-content:space-between; align-items:center; }
.whale-kpi-val{ font-size:var(--t-xl); font-weight:700; font-variant-numeric:tabular-nums; direction:ltr; text-align:start; }
.whale-kpi-val.pos{ color:var(--up); }
.whale-kpi-val.neg{ color:var(--dn); }
.whale-netflow-bar{ height:6px; background:var(--bg-deep); border-radius:3px; overflow:hidden; display:flex; margin-top:4px; }
.whale-netflow-fill{ height:100%; transition:width var(--dur-2) var(--ease); }
.whale-netflow-fill.pos{ background:var(--up); }
.whale-netflow-fill.neg{ background:var(--dn); }
.whale-table-wrap{ overflow-x:auto; background:var(--panel); border:1px solid var(--rule); border-radius:var(--r3); }
.whale-table{ width:100%; border-collapse:collapse; text-align:start; font-size:var(--t-sm); }
.whale-table th{ padding:var(--s2) var(--s3); background:var(--bg-deep); color:var(--ink-3); font-size:var(--t-xs); font-weight:600; border-bottom:1px solid var(--rule); }
.whale-table td{ padding:var(--s2) var(--s3); border-bottom:1px solid var(--rule-2); vertical-align:middle; }
.whale-table tr:hover td{ background:var(--wash); }
.wtag{ display:inline-flex; align-items:center; gap:3px; padding:1px 6px; border-radius:var(--r1); font-size:var(--t-xs); font-weight:600; }
.wtag-ultra{ background:rgba(217,106,85,0.2); color:var(--dn); border:1px solid var(--dn); }
.wtag-accum{ background:rgba(87,177,131,0.2); color:var(--up); border:1px solid var(--up); }
.wtag-mint{ background:rgba(200,150,93,0.2); color:var(--cu-txt); border:1px solid var(--cu); }
.wtag-flow{ font-variant-numeric:tabular-nums; direction:ltr; display:inline-block; font-weight:600; }

@media (max-width:860px){ .phud{ inline-size:min(94vw,420px); inset-inline-start:3vw; } }

.tone-up{ color:var(--up); } .tone-dn{ color:var(--dn); } .tone-warn{ color:var(--warn); }
/* ══ CONTENT STUDIO — Redesigned 2026 Standard ══ */
.st-hero{ display:flex; flex-wrap:wrap; justify-content:space-between; align-items:flex-start; gap:var(--s3); margin-bottom:var(--s4); padding-bottom:var(--s3); border-bottom:1px solid var(--rule); }
.st-hero-main{ display:flex; flex-direction:column; gap:4px; }
.st-hero-title{ display:flex; align-items:center; gap:8px; font-size:var(--t-lg); font-weight:800; color:var(--ink-1); margin:0; }
.st-hero-sub{ font-size:var(--t-xs); color:var(--ink-3); margin:0; line-height:var(--lh-fa); }
.st-hero-badge{ font-size:11px; padding:2px 8px; border-radius:var(--r-pill); background:rgba(200,150,93,0.15); color:var(--cu-txt); border:1px solid var(--cu-line); font-weight:600; display:inline-flex; align-items:center; gap:4px; }
.st-hero-actions{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; }

/* KPI Grid */
.st-kpi-grid{ display:grid; grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)); gap:var(--s2) var(--s3); margin-bottom:var(--s4); }
.st-kpi-card{ background:var(--panel-2); border:1px solid var(--rule); border-radius:var(--r2); padding:10px 14px; display:flex; flex-direction:column; gap:4px; transition:border-color 0.2s; }
.st-kpi-card:hover{ border-color:var(--rule-2); }
.st-kpi-label{ font-size:11px; color:var(--ink-4); display:flex; align-items:center; justify-content:space-between; }
.st-kpi-val{ font-size:var(--t-lg); font-weight:800; color:var(--ink-1); font-variant-numeric:tabular-nums; }
.st-kpi-sub{ font-size:10.5px; color:var(--ink-3); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

/* Filter Bar */
.st-filter-panel{ background:var(--bg-deep); border:1px solid var(--rule); border-radius:var(--r3); padding:var(--s3); margin-bottom:var(--s4); display:flex; flex-direction:column; gap:var(--s3); }
.st-filter-row{ display:flex; flex-wrap:wrap; gap:var(--s2) var(--s3); align-items:center; justify-content:space-between; }
.st-format-tabs{ display:flex; flex-wrap:wrap; gap:6px; }
.st-format-btn{ background:var(--panel); border:1px solid var(--rule); color:var(--ink-2); border-radius:var(--r-pill); padding:5px 12px; font:inherit; font-size:var(--t-xs); cursor:pointer; display:inline-flex; align-items:center; gap:6px; transition:all 0.15s ease; }
.st-format-btn:hover{ border-color:var(--rule-2); color:var(--ink-1); }
.st-format-btn.active{ background:var(--cu-wash); border-color:var(--cu-line); color:var(--cu-txt); font-weight:700; box-shadow:0 0 8px rgba(200,150,93,0.18); }
.st-search-box{ position:relative; min-width:220px; flex:1; max-width:340px; }
.st-search-box input{ width:100%; box-sizing:border-box; background:var(--bg); border:1px solid var(--rule); color:var(--ink-1); border-radius:var(--r-pill); padding:6px 30px 6px 12px; font:inherit; font-size:var(--t-xs); }
.st-search-box input:focus{ outline:none; border-color:var(--cu-line); box-shadow:0 0 0 2px var(--cu-wash); }
.st-search-icon{ position:absolute; right:10px; top:50%; transform:translateY(-50%); color:var(--ink-4); pointer-events:none; }
.st-select{ background:var(--bg); border:1px solid var(--rule); color:var(--ink-2); border-radius:var(--r2); padding:5px 10px; font:inherit; font-size:var(--t-xs); cursor:pointer; }
.st-select:focus{ outline:none; border-color:var(--cu-line); }
.st-filter-meta{ font-size:11px; color:var(--ink-4); display:flex; align-items:center; gap:12px; flex-wrap:wrap; }

/* Item Cards */
.st-item{ border:1px solid var(--rule); border-radius:var(--r3); background:var(--panel-2); padding:var(--s4); margin-bottom:var(--s3); transition:transform 0.15s, border-color 0.15s, box-shadow 0.15s; position:relative; overflow:hidden; }
.st-item:hover{ border-color:var(--rule-2); box-shadow:0 4px 14px rgba(0,0,0,0.06); }
.st-item.rank-1{ border-inline-start:4px solid #f59e0b; }
.st-item.rank-2{ border-inline-start:4px solid #94a3b8; }
.st-item.rank-3{ border-inline-start:4px solid #b45309; }
.st-item-top{ display:flex; justify-content:space-between; align-items:flex-start; gap:var(--s3); margin-bottom:8px; }
.st-item-rank-title{ display:flex; align-items:baseline; gap:var(--s2); flex:1; }
.st-rank-badge{ min-width:28px; height:28px; border-radius:var(--r-pill); background:var(--wash); color:var(--ink-3); font-size:12px; font-weight:800; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0; }
.rank-1 .st-rank-badge{ background:#f59e0b; color:#000; box-shadow:0 0 10px rgba(245,158,11,0.35); }
.rank-2 .st-rank-badge{ background:#94a3b8; color:#000; }
.rank-3 .st-rank-badge{ background:#b45309; color:#fff; }
.st-item h4{ margin:0; font-size:var(--t-md); color:var(--ink-1); line-height:var(--lh-fa); font-weight:700; }
.st-item-score-pill{ display:flex; flex-direction:column; align-items:center; padding:4px 10px; background:var(--wash); border:1px solid var(--rule); border-radius:var(--r2); flex-shrink:0; }
.st-score-val{ font-size:1.35rem; font-weight:800; color:var(--cu-txt); font-variant-numeric:tabular-nums; line-height:1; }
.st-score-lbl{ font-size:9.5px; color:var(--ink-4); margin-top:2px; }

.st-meta-row{ display:flex; flex-wrap:wrap; gap:6px; align-items:center; margin:8px 0; }
.st-fmt-tag{ font-size:11px; padding:3px 9px; border-radius:var(--r-pill); font-weight:600; display:inline-flex; align-items:center; gap:5px; }
.st-fmt-carousel{ background:rgba(59,130,246,0.12); color:#60a5fa; border:1px solid rgba(59,130,246,0.3); }
.st-fmt-video{ background:rgba(239,68,68,0.12); color:#f87171; border:1px solid rgba(239,68,68,0.3); }
.st-fmt-text{ background:rgba(16,185,129,0.12); color:#34d399; border:1px solid rgba(16,185,129,0.3); }

/* Heat & Demand Chips */
.st-heat-strip{ display:flex; flex-wrap:wrap; gap:6px; align-items:center; padding:8px 12px; background:var(--bg); border:1px solid var(--rule-2); border-radius:var(--r2); margin:8px 0; font-size:var(--t-xs); }
.st-heat-item{ display:inline-flex; align-items:center; gap:5px; color:var(--ink-2); }
.st-heat-item.yt{ color:#f87171; }
.st-heat-item.tg{ color:#60a5fa; }
.st-heat-item.rd{ color:#fb923c; }

/* Factor Bars */
.st-factors-summary{ margin-top:8px; display:grid; grid-template-columns:repeat(auto-fit, minmax(130px, 1fr)); gap:6px 12px; font-size:11px; }
.st-factor-bar{ display:flex; align-items:center; gap:6px; }
.st-factor-bar .k{ color:var(--ink-4); width:45px; flex-shrink:0; }
.st-factor-bar .meter{ flex:1; height:5px; background:var(--bg-deep); border-radius:3px; overflow:hidden; }
.st-factor-bar .meter i{ display:block; height:100%; border-radius:3px; background:linear-gradient(90deg, var(--cu-2), var(--cu)); }
.st-factor-bar .v{ color:var(--ink-3); font-variant-numeric:tabular-nums; font-size:10px; width:25px; text-align:left; }

/* Item Action Footer */
.st-item-footer{ display:flex; flex-wrap:wrap; gap:var(--s2); align-items:center; justify-content:space-between; margin-top:12px; padding-top:10px; border-top:1px solid var(--rule); }
.st-draft-btn{ display:inline-flex; align-items:center; gap:6px; font-weight:700; transition:all 0.2s; }
.st-draft-btn.loading{ opacity:0.8; pointer-events:none; }
.st-draft-btn.loading svg{ animation:spin 1s linear infinite; }

/* Modern Draft Drawer / Workspace */
.st-workspace{ background:var(--panel); border:1px solid var(--cu-line); border-radius:var(--r3); padding:var(--s4); margin-bottom:var(--s4); box-shadow:0 8px 30px rgba(0,0,0,0.12); position:relative; scroll-margin-top:20px; }
.st-workspace-head{ display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:var(--s3); margin-bottom:var(--s3); padding-bottom:var(--s3); border-bottom:1px solid var(--rule); }
.st-workspace-title{ font-size:var(--t-md); font-weight:800; color:var(--ink-1); margin:0; display:flex; align-items:center; gap:8px; }
.st-tabs-modern{ display:flex; flex-wrap:wrap; gap:6px; margin:var(--s3) 0; }
.st-tab-btn{ background:var(--wash); border:1px solid var(--rule); color:var(--ink-2); border-radius:var(--r-pill); padding:6px 16px; font:inherit; font-size:var(--t-sm); cursor:pointer; display:inline-flex; align-items:center; gap:6px; transition:all 0.15s; }
.st-tab-btn.on{ background:var(--cu-wash); border-color:var(--cu-line); color:var(--cu-txt); font-weight:700; }
.st-pane-box{ background:var(--bg-deep); border:1px solid var(--rule); border-radius:var(--r2); padding:var(--s4); margin-top:var(--s3); }
.st-caption-editor{ width:100%; box-sizing:border-box; background:var(--bg); border:1px solid var(--rule-2); color:var(--ink-1); border-radius:var(--r2); padding:12px; font:inherit; font-size:var(--t-sm); line-height:var(--lh-fa); resize:vertical; min-height:160px; direction:rtl; }
.st-caption-editor:focus{ outline:none; border-color:var(--cu-line); }

/* Slides Grid */
.st-slides-grid{ display:grid; grid-template-columns:repeat(auto-fill, minmax(210px, 1fr)); gap:var(--s3); margin:var(--s3) 0; }
.st-slide-card{ aspect-ratio:4 / 5; background:#0A0F1E; color:#F2F6FC; border:1px solid rgba(154,182,224,.2); border-radius:var(--r2); padding:14px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 4px 12px rgba(0,0,0,0.3); position:relative; overflow:hidden; }
.st-slide-top-bar{ height:3px; width:40px; background:#4C8DFF; border-radius:2px; margin-bottom:8px; }
.st-slide-h{ font-size:13px; font-weight:700; color:#EFE8DD; line-height:1.4; margin-bottom:6px; }
.st-slide-p{ font-size:11px; color:#CFC6B8; line-height:1.5; flex:1; overflow:hidden; }
.st-slide-bottom{ display:flex; justify-content:space-between; font-size:9.5px; color:#918779; margin-top:8px; border-top:1px solid rgba(255,255,255,0.08); padding-top:6px; }

/* Config details */
.st-cfgbox{ border:1px solid var(--rule); border-radius:var(--r2); background:var(--bg-deep); padding:var(--s3) var(--s4); margin-bottom:var(--s4); }
.st-cfgbox summary{ cursor:pointer; color:var(--ink-2); font-size:var(--t-sm); font-weight:600; display:flex; align-items:center; gap:6px; }
.st-cfg{ display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1.2fr); gap:var(--s2) var(--s3); align-items:center; margin-top:var(--s3); }
.st-cfg label{ font-size:var(--t-xs); color:var(--ink-3); }
.st-cfg input[type=text], .st-cfg input[type=password], .st-cfg input[type=number]{ inline-size:100%; box-sizing:border-box; background:var(--bg); border:1px solid var(--rule); color:var(--ink-1); border-radius:var(--r2); padding:8px 10px; font:inherit; font-size:var(--t-sm); }
.st-cfg input:focus{ outline:none; border-color:var(--cu-line); }
.st-cfg .st-check{ grid-column:1 / -1; display:flex; gap:8px; align-items:center; font-size:var(--t-sm); color:var(--ink-2); }

.st-empty{ color:var(--ink-4); font-size:var(--t-sm); padding:var(--s4); text-align:center; }
.st-note{ border:1px solid var(--warn); background:var(--warn-wash); color:var(--ink-1); border-radius:var(--r2); padding:10px 14px; font-size:var(--t-sm); margin-bottom:var(--s3); line-height:var(--lh-fa); }
.st-foot{ margin-top:var(--s4); font-size:var(--t-xs); color:var(--ink-4); line-height:var(--lh-fa); border-top:1px solid var(--rule); padding-top:var(--s3); }

/* ── CHANNEL BOARD · the gold/coin page ─────────────────────────────────
   Reuses the studio's shapes (.btn, .badge, .spinner) and adds only what this
   surface needs: a lane tag, the fit meter and the ready-made card text. */
.cb-hero{ display:flex; flex-wrap:wrap; justify-content:space-between; align-items:flex-start; gap:var(--s3); margin-bottom:var(--s4); padding-bottom:var(--s3); border-bottom:1px solid var(--rule); }
.cb-hero-title{ display:flex; align-items:center; gap:8px; font-size:var(--t-lg); font-weight:800; color:var(--ink-1); margin:0; }
.cb-handle{ font-size:11px; padding:2px 8px; border-radius:var(--r-pill); background:rgba(200,150,93,0.15); color:var(--cu-txt); border:1px solid var(--cu-line); font-weight:600; }
.cb-hero-sub{ font-size:var(--t-xs); color:var(--ink-3); margin:4px 0 0; line-height:var(--lh-fa); }
.cb-kpis{ display:grid; grid-template-columns:repeat(auto-fit, minmax(170px,1fr)); gap:var(--s2) var(--s3); margin-bottom:var(--s3); }
.cb-kpi{ background:var(--panel-2); border:1px solid var(--rule); border-radius:var(--r2); padding:10px 14px; display:flex; flex-direction:column; gap:4px; }
.cb-kpi-lbl{ font-size:11px; color:var(--ink-4); }
.cb-kpi-val{ font-size:var(--t-lg); font-weight:800; color:var(--ink-1); font-variant-numeric:tabular-nums; }
.cb-kpi-sub{ font-size:10.5px; color:var(--ink-3); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.cb-bar{ display:flex; flex-wrap:wrap; gap:var(--s2); align-items:center; justify-content:space-between; background:var(--bg-deep); border:1px solid var(--rule); border-radius:var(--r3); padding:var(--s3); margin-bottom:var(--s3); }
.cb-lanes{ display:flex; flex-wrap:wrap; gap:6px; }
.cb-chip{ background:var(--panel); border:1px solid var(--rule); color:var(--ink-2); border-radius:var(--r-pill); padding:5px 12px; font:inherit; font-size:var(--t-xs); cursor:pointer; display:inline-flex; align-items:center; gap:6px; }
.cb-chip:hover{ border-color:var(--rule-2); color:var(--ink-1); }
.cb-chip.active{ background:var(--cu-wash); border-color:var(--cu-line); color:var(--cu-txt); font-weight:700; }
.cb-chip b{ font-variant-numeric:tabular-nums; opacity:.8; }
.cb-search{ background:var(--bg); border:1px solid var(--rule); color:var(--ink-1); border-radius:var(--r-pill); padding:6px 12px; font:inherit; font-size:var(--t-xs); min-width:220px; }
.cb-item{ border:1px solid var(--rule); border-radius:var(--r3); background:var(--panel-2); padding:var(--s4); margin-bottom:var(--s3); }
.cb-item:hover{ border-color:var(--rule-2); }
.cb-item.rank-1{ border-inline-start:4px solid #f59e0b; }
.cb-item.rank-2{ border-inline-start:4px solid #94a3b8; }
.cb-item.rank-3{ border-inline-start:4px solid #b45309; }
.cb-item-top{ display:flex; justify-content:space-between; align-items:flex-start; gap:var(--s3); margin-bottom:8px; }
.cb-item-head{ display:flex; align-items:baseline; gap:var(--s2); flex:1; min-width:0; }
.cb-item h4{ margin:0; font-size:var(--t-md); color:var(--ink-1); line-height:var(--lh-fa); font-weight:700; }
.cb-rank{ min-width:30px; height:24px; border-radius:var(--r-pill); background:var(--wash); color:var(--ink-3); font-size:11px; font-weight:800; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0; }
.cb-fit{ display:flex; flex-direction:column; align-items:center; padding:4px 10px; background:var(--wash); border:1px solid var(--rule); border-radius:var(--r2); flex-shrink:0; }
.cb-domestic{ display:flex; flex-wrap:wrap; gap:var(--s2); align-items:center; padding:var(--s2) var(--s3); margin-block-end:var(--s3); background:var(--panel); border:1px solid var(--rule); border-radius:var(--r2); }
.cb-dom{ display:inline-flex; align-items:baseline; gap:6px; padding:3px 10px; border-radius:var(--r-pill); background:var(--wash); border:1px solid var(--rule); }
.cb-dom .lbl{ font-size:10.5px; color:var(--ink-4); }
.cb-dom .val{ font-family:var(--font-mono); font-size:var(--t-sm); font-weight:700; color:var(--ink-1); font-variant-numeric:tabular-nums; direction:ltr; }
.cb-dom .chg{ font-family:var(--font-mono); font-size:10px; font-weight:700; font-variant-numeric:tabular-nums; direction:ltr; }
.cb-dom.up .chg{ color:var(--up); }
.cb-dom.dn .chg{ color:var(--dn); }
.cb-dom.stale{ opacity:.6; }
.cb-dom-src{ font-size:10px; color:var(--ink-4); margin-inline-start:auto; }
.cb-viral{ display:flex; flex-direction:column; align-items:center; padding:6px 14px; border-radius:var(--r2); flex-shrink:0; border:1px solid; }
.cb-viral.hot{ background:rgba(238,106,88,.14); border-color:rgba(238,106,88,.4); }
.cb-viral.warm{ background:rgba(232,162,60,.13); border-color:rgba(232,162,60,.38); }
.cb-viral.cool{ background:var(--wash); border-color:var(--rule); }
.cb-viral-val{ font-family:var(--font-mono); font-size:1.5rem; font-weight:800; font-variant-numeric:tabular-nums; line-height:1; }
.cb-viral.hot .cb-viral-val{ color:var(--dn); }
.cb-viral.warm .cb-viral-val{ color:var(--warn); }
.cb-viral.cool .cb-viral-val{ color:var(--ink-3); }
.cb-viral-lbl{ font-size:9.5px; color:var(--ink-4); margin-top:2px; }
.cb-why-item{ display:inline-block; font-size:11px; padding:2px 9px; margin:2px 0 2px 6px; border-radius:var(--r-pill); background:var(--cu-wash); color:var(--cu-txt); border:1px solid var(--cu-line); }
.cb-fit-val{ font-size:1.35rem; font-weight:800; color:var(--cu-txt); font-variant-numeric:tabular-nums; line-height:1; }
.cb-fit-lbl{ font-size:9.5px; color:var(--ink-4); margin-top:2px; }
.cb-meta{ display:flex; flex-wrap:wrap; gap:6px; align-items:center; margin:8px 0; }
.cb-lane{ font-size:11px; padding:3px 9px; border-radius:var(--r-pill); font-weight:700; border:1px solid; }
.cb-lane-gold{ background:rgba(245,158,11,0.12); color:#fbbf24; border-color:rgba(245,158,11,0.35); }
.cb-lane-fx{ background:rgba(16,185,129,0.12); color:#34d399; border-color:rgba(16,185,129,0.3); }
.cb-lane-dom{ background:rgba(59,130,246,0.12); color:#60a5fa; border-color:rgba(59,130,246,0.3); }
.cb-lane-glob{ background:rgba(167,139,250,0.12); color:#a78bfa; border-color:rgba(167,139,250,0.3); }
.cb-bkt{ font-size:10.5px; padding:2px 8px; border-radius:var(--r-pill); background:var(--panel); border:1px solid var(--rule); color:var(--ink-3); cursor:help; }
.cb-why{ font-size:11.5px; color:var(--ink-3); margin:6px 0; line-height:var(--lh-fa); }
.cb-numbers{ display:flex; flex-wrap:wrap; gap:5px; margin:6px 0; }
.cb-num{ font-size:11px; padding:2px 8px; border-radius:var(--r2); background:var(--bg-deep); border:1px solid var(--rule); color:var(--ink-2); font-variant-numeric:tabular-nums; direction:ltr; }
.cb-factors{ display:grid; grid-template-columns:repeat(auto-fit, minmax(130px,1fr)); gap:6px 12px; font-size:11px; margin:8px 0; }
.cb-factor-bar{ display:flex; align-items:center; gap:6px; }
.cb-factor-bar .k{ color:var(--ink-4); width:58px; flex-shrink:0; }
.cb-factor-bar .meter{ flex:1; height:5px; background:var(--bg-deep); border-radius:3px; overflow:hidden; }
.cb-factor-bar .meter i{ display:block; height:100%; border-radius:3px; background:linear-gradient(90deg, var(--cu-2), var(--cu)); }
.cb-factor-bar .v{ color:var(--ink-3); font-variant-numeric:tabular-nums; font-size:10px; width:25px; text-align:left; }
.cb-cap{ margin-top:10px; border:1px solid var(--cu-line); background:var(--bg-deep); border-radius:var(--r2); padding:10px 12px; }
.cb-cap-head{ display:flex; justify-content:space-between; align-items:center; gap:8px; font-size:11px; color:var(--cu-txt); font-weight:700; margin-bottom:6px; }
.cb-cap-text{ margin:0; font-family:var(--font-fa, inherit); font-size:12.5px; line-height:2; color:var(--ink-1); white-space:pre-wrap; word-break:break-word; text-align:right; }
.cb-cap-tags{ margin-top:8px; font-size:11px; color:var(--ink-3); direction:ltr; text-align:left; }
.cb-cap-note{ margin-top:6px; font-size:10px; color:var(--ink-4); }
.cb-foot{ display:flex; flex-wrap:wrap; gap:var(--s2); align-items:center; justify-content:space-between; margin-top:10px; padding-top:10px; border-top:1px solid var(--rule); }
.cb-nolink{ font-size:11px; color:var(--ink-4); }
.cb-empty{ color:var(--ink-3); font-size:var(--t-sm); padding:var(--s5) var(--s4); text-align:center; line-height:var(--lh-fa); }
.cb-foot-note{ margin-top:var(--s4); font-size:var(--t-xs); color:var(--ink-4); line-height:var(--lh-fa); border-top:1px solid var(--rule); padding-top:var(--s3); }

@media (max-width:768px){
  .st-cfg{ grid-template-columns:minmax(0,1fr); }
  .st-filter-row{ flex-direction:column; align-items:stretch; }
  .st-search-box{ max-width:100%; }
}

/* ── Expansion Suite: Reader Mode, Watchlist, Embeds, Offline ── */
.reader-overlay{ position:fixed; inset:0; z-index:2500; background:var(--bg); color:var(--ink-1); display:none; flex-direction:column; overflow-y:auto; scroll-behavior:smooth; }
.reader-overlay.open{ display:flex; }
.reader-progress{ position:fixed; top:0; left:0; right:0; height:4px; background:transparent; z-index:2600; }
.reader-progress-bar{ height:100%; width:0%; background:#3b82f6; box-shadow:0 0 10px rgba(59,130,246,0.6); transition:width 0.1s ease; }
.reader-toolbar{ position:sticky; top:0; z-index:2550; display:flex; align-items:center; justify-content:space-between; padding:10px 24px; background:var(--panel); border-bottom:1px solid var(--rule); backdrop-filter:blur(8px); }
.reader-tools-group{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
.reader-container{ max-width:760px; margin:0 auto; padding:40px 24px 80px 24px; font-size:var(--reader-fs, 16px); line-height:2.1; direction:rtl; text-align:right; }
.reader-title{ font-size:1.75em; font-weight:800; line-height:1.5; margin-bottom:12px; }
.reader-title-en{ font-size:0.9em; color:var(--ink-3); direction:ltr; text-align:right; margin-bottom:16px; }
.reader-meta{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; font-size:0.82em; color:var(--ink-3); margin-bottom:24px; padding-bottom:16px; border-bottom:1px solid var(--rule); }
.reader-content p{ margin-bottom:1.5em; text-align:justify; }
.reader-theme-sepia{ background:#fbf0d9 !important; color:#433422 !important; }
.reader-theme-sepia .reader-toolbar{ background:#f4e4c1 !important; border-color:#dcc29b !important; color:#433422 !important; }
.reader-theme-sepia .reader-title{ color:#2b1f14 !important; }
.reader-theme-sepia .reader-meta{ border-color:#dcc29b !important; color:#6a5338 !important; }
.reader-theme-sepia .btn{ background:#e8d1a7 !important; color:#2b1f14 !important; border-color:#c9ab7b !important; }
.reader-theme-oled{ background:#000000 !important; color:#d4d4d4 !important; }
.reader-theme-oled .reader-toolbar{ background:#0a0a0a !important; border-color:#222222 !important; }
.chip.chip-watchlist{ border-color:#f59e0b !important; color:#f59e0b !important; }
.chip.chip-watchlist.on{ background:#f59e0b !important; color:#000 !important; }
.watchlist-grid{ display:grid; grid-template-columns:repeat(auto-fill, minmax(130px, 1fr)); gap:10px; margin:16px 0; }
.watchlist-card{ display:flex; align-items:center; justify-content:space-between; padding:8px 12px; border-radius:var(--r2); border:1px solid var(--rule); background:var(--panel-2); cursor:pointer; user-select:none; }
.watchlist-card.active{ border-color:#f59e0b; background:rgba(245,158,11,0.12); }
.offline-pill-active{ background:#ef4444 !important; color:#fff !important; font-weight:bold; }

/* ═══════════════════════════════════════════════════════════════════════════
   DL6 · MIDNIGHT TERMINAL — numeric surfaces
   Prices, changes, timers and calendar figures read in IBM Plex Mono with
   tabular figures: a ticking quote can no longer re-flow its row, and the
   terminal reads like an instrument. Prose (Vazirmatn) is untouched.
   ═══════════════════════════════════════════════════════════════════════════ */
.num,
.dl2-ticker .tk .s, .dl2-ticker .tk .p, .dl2-ticker .tk .c,
.chart-head .p, .chart-head .c, .tvhead .p, .ch-price .p, .ch-price .c,
.cal-countdown, .cal-timer .sg b, .cal-timer .sg small, .cal-day .dd,
.cal-tr .c-time, .cal-tr .c-ccy, .cal-tr .c-num,
.whale-kpi-val, .st-kpi-val, .cb-kpi-val,
.cr-n, .cr-sur, .cred-badge{
  font-family:var(--font-mono);
  font-variant-numeric:tabular-nums;
  letter-spacing:0;
}


/* ═══════════════════════════════════════════════════════════════════════════
   DL6.1 · MATTE PAPER + COMPACT
   The accent is desaturated at the token level (paper-matte steel blue) and
   every major box drops one padding step: the terminal reads denser and
   calmer, boxes stop floating a size too large. Prose keeps its measure.
   ═══════════════════════════════════════════════════════════════════════════ */
.panelbox{ padding:var(--s4); }
.lead-card{ min-block-size:148px; }
.lead-card .body{ padding:var(--s4); gap:var(--s1) var(--s2); }
.lead-card .lead-ttl{ font-size:var(--t-lg); line-height:1.6; }
.lead-card .summ{ font-size:var(--t-sm); -webkit-line-clamp:3; }
.ncard .body{ padding:var(--s3) var(--s4) var(--s4); }
.idea-body{ padding:var(--s3); }
.etfgroup{ padding:var(--s3); }
.modal{ padding:var(--s5) var(--s5) var(--s4); }
.rep-doc{ padding:var(--s5) var(--s6); max-block-size:calc(100vh - 150px); }
.rep-doc h2{ font-size:var(--t-xl); }
.rep-doc h3{ font-size:var(--t-lg); margin-block:var(--s6) var(--s3); }
.rep-doc h4{ font-size:var(--t-md); margin-block:var(--s4) var(--s2); }
.rep-doc p{ font-size:var(--t-md); line-height:1.95; }
.ngrid{ grid-template-columns:repeat(auto-fill, minmax(284px,1fr)); gap:var(--s3); }


/* ═══════════════════════════════════════════════════════════════════════════
   DL6.2 · TIGHTER — one more density step: smaller boxes, shorter feed cards
   (21:9 thumbs, 2-line headlines, 2-line summaries), smaller type scale.
   ═══════════════════════════════════════════════════════════════════════════ */
.ngrid{ grid-template-columns:repeat(auto-fill, minmax(264px,1fr)); gap:var(--s3); }
.ncard .thumb{ aspect-ratio:21/9; }
.ncard .body{ padding:var(--s2) var(--s3) var(--s3); }
.ncard .ttl{ font-size:var(--t-md); line-height:1.65;
  display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.ncard .summ{ font-size:var(--t-sm); -webkit-line-clamp:2; }
.lead-card{ min-block-size:128px; }
.lead-card .body{ padding:var(--s3); }
.lead-card .lead-ttl{ font-size:var(--t-md); line-height:1.6; }
.lead-card .summ{ font-size:var(--t-sm); -webkit-line-clamp:2; }
.panelbox{ padding:var(--s3); }
.rep-doc{ padding:var(--s4) var(--s5); }
.modal{ padding:var(--s4) var(--s4) var(--s3); }
.idea-body{ padding:var(--s2) var(--s3) var(--s3); }
.etfgroup{ padding:var(--s2) var(--s3) var(--s3); }

</style>
<!-- offline-first storage layer: IndexedDB (MohmdNewsDB) + inverted-index search.
     Loaded from its own file because the service worker precaches it as a shell
     asset; the offline maquette inlines this exact file at build time. -->
<script src="/storage-engine.js"></script>
<!-- content studio client: ranked stories, draft panes, slide export. Separate
     file so the dashboard string stays readable, precached by the worker. -->
<script src="/studio.js" defer></script>
<!-- channel board client: which stories fit the gold/coin page, and the card
     text each one becomes. Separate file for the same reason as studio.js. -->
<script src="/channel.js" defer></script>
</head>
<body>

<!-- ══ ICON SET — one inline sprite, 24×24, 1.6px stroke, currentColor ══ -->
<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>
<symbol id="i-mark" viewBox="0 0 24 24"><path d="M3 13.5h4L9.5 6l4.5 11 3-7h4"/><circle cx="20" cy="5.5" r="1.6"/></symbol>
<symbol id="i-menu" viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16"/></symbol>
<symbol id="i-refresh" viewBox="0 0 24 24"><path d="M20 12a8 8 0 1 1-2.4-5.7"/><path d="M20 4v4h-4"/></symbol>
<symbol id="i-filter" viewBox="0 0 24 24"><path d="M4 5h16l-6.2 7.2V19L10.2 20.5v-8.3z"/></symbol>
<symbol id="i-search" viewBox="0 0 24 24"><circle cx="11" cy="11" r="6"/><path d="M20 20l-4.4-4.4"/></symbol>
<symbol id="i-x" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></symbol>
<symbol id="i-chevron-down" viewBox="0 0 24 24"><path d="M6 9.5l6 6 6-6"/></symbol>
<symbol id="i-news" viewBox="0 0 24 24"><path d="M4 5.5h11.5v13H6a2 2 0 0 1-2-2z"/><path d="M15.5 8.5H20v8a2 2 0 0 1-2 2h-2.5"/><path d="M7 9h6M7 12h6M7 15h4"/></symbol>
<symbol id="i-chart" viewBox="0 0 24 24"><path d="M4 4v16h16"/><path d="M8 16v-5M12 16V7.5M16 16v-3"/></symbol>
<symbol id="i-bulb" viewBox="0 0 24 24"><path d="M12 3.5a5.5 5.5 0 0 1 3.3 9.9V16H8.7v-2.6A5.5 5.5 0 0 1 12 3.5z"/><path d="M9.5 18.5h5M10.5 21h3"/></symbol>
<symbol id="i-calendar" viewBox="0 0 24 24"><rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/></symbol>
<symbol id="i-bank" viewBox="0 0 24 24"><path d="M4 9.5 12 4.5l8 5"/><path d="M6 11v8M10 11v8M14 11v8M18 11v8"/><path d="M3.5 20.5h17"/></symbol>
<symbol id="i-archive" viewBox="0 0 24 24"><rect x="3.5" y="4.5" width="17" height="5" rx="1.5"/><path d="M5.5 9.5V19a1.5 1.5 0 0 0 1.5 1.5h10A1.5 1.5 0 0 0 18.5 19V9.5"/><path d="M10 14h4"/></symbol>
<symbol id="i-star" viewBox="0 0 24 24"><path d="M12 4.2l2.5 5.2 5.5.8-4 3.9 1 5.6-5-2.8-5 2.8 1-5.6-4-3.9 5.5-.8z"/></symbol>
<symbol id="i-pulse" viewBox="0 0 24 24"><path d="M3 12h4l2.5-6.5 4 13 2.5-6.5H21"/></symbol>
<symbol id="i-send" viewBox="0 0 24 24"><path d="M4.5 12 20 4.5 15 20l-3.6-6.2z"/><path d="M11.4 13.8 20 4.5"/></symbol>
<symbol id="i-gear" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 3.5v2M12 18.5v2M4.5 12h2M17.5 12h2M6.9 6.9l1.4 1.4M15.7 15.7l1.4 1.4M17.1 6.9l-1.4 1.4M8.3 15.7l-1.4 1.4"/></symbol>
<symbol id="i-rss" viewBox="0 0 24 24"><circle cx="6" cy="17.5" r="1.3" fill="currentColor" stroke="none"/><path d="M5.5 12.5A6 6 0 0 1 11.5 18.5"/><path d="M5.5 7.5A11 11 0 0 1 16.5 18.5"/></symbol>
<symbol id="i-coins" viewBox="0 0 24 24"><ellipse cx="9" cy="7" rx="5.2" ry="2.6"/><path d="M3.8 7v4.5c0 1.4 2.3 2.6 5.2 2.6"/><path d="M3.8 11.5V16c0 1.4 2.3 2.6 5.2 2.6"/><ellipse cx="16" cy="15.5" rx="4.6" ry="2.3"/><path d="M11.4 15.5v3c0 1.3 2 2.3 4.6 2.3s4.6-1 4.6-2.3v-3"/></symbol>
<symbol id="i-external" viewBox="0 0 24 24"><path d="M14 4.5h5.5V10"/><path d="M19.5 4.5 11 13"/><path d="M18 14v4.5A1.5 1.5 0 0 1 16.5 20h-11A1.5 1.5 0 0 1 4 18.5v-11A1.5 1.5 0 0 1 5.5 6H10"/></symbol>
<symbol id="i-clock" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/><path d="M12 7.5V12l3 2"/></symbol>
<symbol id="i-tag" viewBox="0 0 24 24"><path d="M12.5 4.5H20v7.5l-8.5 8.5-7.5-7.5z"/><circle cx="16.4" cy="8" r="1.2"/></symbol>
<symbol id="i-link" viewBox="0 0 24 24"><path d="M10.5 13.5a4 4 0 0 0 5.6 0l2.8-2.8a4 4 0 1 0-5.6-5.6l-1.6 1.6"/><path d="M13.5 10.5a4 4 0 0 0-5.6 0l-2.8 2.8a4 4 0 1 0 5.6 5.6l1.6-1.6"/></symbol>
<symbol id="i-moon" viewBox="0 0 24 24"><path d="M20 14.8A8.2 8.2 0 0 1 9.2 4 8.6 8.6 0 1 0 20 14.8z"/></symbol>
<symbol id="i-bell" viewBox="0 0 24 24"><path d="M6.5 16.5V11a5.5 5.5 0 0 1 11 0v5.5l1.5 2.2h-14z"/><path d="M10 20.7a2 2 0 0 0 4 0"/></symbol>
<symbol id="i-bell-off" viewBox="0 0 24 24"><path d="M6.5 16.5V11a5.5 5.5 0 0 1 8.6-4.5"/><path d="M16.9 10.5v6l1.6 2.2h-11"/><path d="M10 20.7a2 2 0 0 0 4 0"/><path d="M4.5 4l15 16"/></symbol>
<symbol id="i-hash" viewBox="0 0 24 24"><path d="M9.5 4 8 20M16 4l-1.5 16M4.5 9.5h15M4 15h15"/></symbol>
<!-- i-grid / i-swap are declared once in the icon batch below: duplicate IDs
     are invalid markup and the browser would silently keep the first one -->
<symbol id="i-eye" viewBox="0 0 24 24"><path d="M2.8 12S6.4 6.6 12 6.6 21.2 12 21.2 12 17.6 17.4 12 17.4 2.8 12 2.8 12z"/><circle cx="12" cy="12" r="2.8"/></symbol>
<symbol id="i-eye-off" viewBox="0 0 24 24"><path d="M4.5 4l15 16"/><path d="M9.7 7.1A9.4 9.4 0 0 1 12 6.8c5.6 0 9.2 5.2 9.2 5.2a17.4 17.4 0 0 1-3.7 4"/><path d="M6.6 8.6A16.6 16.6 0 0 0 2.8 12s3.6 5.4 9.2 5.4a9.6 9.6 0 0 0 3.4-.6"/></symbol>
<symbol id="i-pin" viewBox="0 0 24 24"><path d="M9.5 4.5h5l-.7 5 3.2 3.2H7l3.2-3.2z"/><path d="M12 12.7v7"/></symbol>
<symbol id="i-copy" viewBox="0 0 24 24"><rect x="9" y="9" width="11" height="11" rx="1.6"/><path d="M15 9V5.6A1.6 1.6 0 0 0 13.4 4H5.6A1.6 1.6 0 0 0 4 5.6v7.8A1.6 1.6 0 0 0 5.6 15H9"/></symbol>
<symbol id="i-download" viewBox="0 0 24 24"><path d="M12 4v12M7.5 11.5 12 16l4.5-4.5M4.5 19.5h15"/></symbol>
<symbol id="i-upload" viewBox="0 0 24 24"><path d="M12 16V4M7.5 8.5 12 4l4.5 4.5M4.5 19.5h15"/></symbol>
<symbol id="i-save" viewBox="0 0 24 24"><path d="M5 4.5h11l3.5 3.5V20H5z"/><path d="M8.5 4.5v5h6v-5"/><path d="M8.5 20v-6h7v6"/></symbol>
<symbol id="i-plus" viewBox="0 0 24 24"><path d="M12 5.5v13M5.5 12h13"/></symbol>
<symbol id="i-check" viewBox="0 0 24 24"><path d="M5 12.5 10 17.5 19 7"/></symbol>
<symbol id="i-warn" viewBox="0 0 24 24"><path d="M12 4.5 21 20H3z"/><path d="M12 10v4.4M12 17.2v.3"/></symbol>
<symbol id="i-info" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/><path d="M12 10.6v5.4M12 7.9v.3"/></symbol>
<symbol id="i-file" viewBox="0 0 24 24"><path d="M6.5 3.5h7l4.5 4.5V20h-11.5z"/><path d="M13.5 3.5V8H18"/><path d="M9.5 13h6M9.5 16h4"/></symbol>
<symbol id="i-list" viewBox="0 0 24 24"><rect x="6" y="4.5" width="13" height="16" rx="1.5"/><path d="M9.5 9h6M9.5 12.5h6M9.5 16h3.5"/><path d="M4.5 7v11"/></symbol>
<symbol id="i-book" viewBox="0 0 24 24"><path d="M12 6.6C10.4 5 8.3 4.5 4.8 4.5v12.8c3.5 0 5.6.5 7.2 2.1 1.6-1.6 3.7-2.1 7.2-2.1V4.5c-3.5 0-5.6.5-7.2 2.1z"/><path d="M12 6.6v12.8"/></symbol>
<symbol id="i-users" viewBox="0 0 24 24"><circle cx="9" cy="8.5" r="3"/><path d="M3.6 19.5c0-3 2.4-5 5.4-5s5.4 2 5.4 5"/><path d="M16.4 6.3a3 3 0 0 1 0 5.5M17 14.8c2 .6 3.4 2.3 3.4 4.7"/></symbol>
<symbol id="i-globe" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.4"/><path d="M3.6 12h16.8"/><path d="M12 3.6c2.4 2.6 2.4 14.2 0 16.8-2.4-2.6-2.4-14.2 0-16.8z"/></symbol>
<symbol id="i-target" viewBox="0 0 24 24"><circle cx="12" cy="12" r="7.8"/><circle cx="12" cy="12" r="3.6"/><path d="M12 2.6v3M12 18.4v3M2.6 12h3M18.4 12h3"/></symbol>
<symbol id="i-film" viewBox="0 0 24 24"><rect x="3.5" y="5" width="17" height="14" rx="2"/><path d="M8 5v14M16 5v14M3.5 12h17"/></symbol>
<symbol id="i-trophy" viewBox="0 0 24 24"><path d="M8 4.5h8V8a4 4 0 0 1-8 0z"/><path d="M8 6H5.5v1.8A3 3 0 0 0 8 10.7M16 6h2.5v1.8A3 3 0 0 1 16 10.7"/><path d="M12 12.2v3.6M9 20h6l-.7-4.2H9.7z"/></symbol>
<symbol id="i-heart" viewBox="0 0 24 24"><path d="M12 19.8S5 15.6 5 11a4.2 4.2 0 0 1 7-3 4.2 4.2 0 0 1 7 3c0 4.6-7 8.8-7 8.8z"/></symbol>
<symbol id="i-comment" viewBox="0 0 24 24"><path d="M4.6 6.6a2 2 0 0 1 2-2h10.8a2 2 0 0 1 2 2v6.8a2 2 0 0 1-2 2H10L4.6 19.4z"/></symbol>
<symbol id="i-lock" viewBox="0 0 24 24"><rect x="5" y="10.4" width="14" height="9.6" rx="2"/><path d="M8.6 10.4V8a3.4 3.4 0 0 1 6.8 0v2.4"/></symbol>
<symbol id="i-trash" viewBox="0 0 24 24"><path d="M5 7h14"/><path d="M9.6 7V4.8h4.8V7"/><path d="M6.6 7l1 13h8.8l1-13"/></symbol>
<symbol id="i-panel" viewBox="0 0 24 24"><rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M9.5 4.5v15"/><path d="M15.4 9.6 13 12l2.4 2.4"/></symbol>
<symbol id="i-expand" viewBox="0 0 24 24"><path d="M4 9.2V5.5A1.5 1.5 0 0 1 5.5 4H9.2M14.8 4h3.7A1.5 1.5 0 0 1 20 5.5v3.7M20 14.8v3.7a1.5 1.5 0 0 1-1.5 1.5h-3.7M9.2 20H5.5A1.5 1.5 0 0 1 4 18.5v-3.7"/></symbol>
<symbol id="i-fire" viewBox="0 0 24 24"><path d="M12 3.5c3.2 3.6 5.6 5.7 5.6 9.3a5.6 5.6 0 0 1-11.2 0c0-2 .9-3.2 2.3-4.8"/></symbol>
<symbol id="i-coin" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.2"/><circle cx="12" cy="12" r="3.2"/><path d="M12 3.8v5M12 15.2v5"/></symbol>
<symbol id="i-ingot" viewBox="0 0 24 24"><path d="M7 9h10l3 7.5H4z"/><path d="M9.5 9 8 6h8l-1.5 3"/></symbol>
<symbol id="i-drop" viewBox="0 0 24 24"><path d="M12 4.2c3.4 4 5.4 6.4 5.4 9.2a5.4 5.4 0 0 1-10.8 0c0-2.8 2-5.2 5.4-9.2z"/></symbol>
<symbol id="i-swap" viewBox="0 0 24 24"><path d="M4 8.5h13l-3.2-3.2M20 15.5H7l3.2 3.2"/></symbol>
<symbol id="i-shield" viewBox="0 0 24 24"><path d="M12 3.8 19 6v6c0 4.2-3 7-7 8.4-4-1.4-7-4.2-7-8.4V6z"/><path d="M9.5 12.2 11.4 14l3.3-3.4"/></symbol>
<symbol id="i-cpu" viewBox="0 0 24 24"><rect x="7" y="7" width="10" height="10" rx="1.6"/><path d="M10.5 3.5v3.5M13.5 3.5v3.5M10.5 17v3.5M13.5 17v3.5M3.5 10.5H7M3.5 13.5H7M17 10.5h3.5M17 13.5h3.5"/></symbol>
<symbol id="i-grid" viewBox="0 0 24 24"><rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/></symbol>
<symbol id="i-pen" viewBox="0 0 24 24"><path d="M4.6 19.4l.8-3.3 9.5-9.5a1.6 1.6 0 0 1 2.3 0l1.2 1.2a1.6 1.6 0 0 1 0 2.3l-9.5 9.5z"/><path d="M13.4 7.4l3.2 3.2"/></symbol>
<symbol id="i-undo" viewBox="0 0 24 24"><path d="M9.6 7.4 5.4 11.6l4.2 4.2"/><path d="M5.4 11.6h7.1a5.4 5.4 0 0 1 5.4 5.4v.6"/></symbol>
<symbol id="i-shrink" viewBox="0 0 24 24"><path d="M9.4 4.6V9H5M13.6 9h4.4V4.6M13.6 19.4V15H18M9.4 15H5v4.4"/></symbol>
<symbol id="i-bookmark" viewBox="0 0 24 24"><path d="M7.2 4.6h9.6a1 1 0 0 1 1 1v14.2l-5.8-3.5-5.8 3.5V5.6a1 1 0 0 1 1-1z"/></symbol>
<symbol id="i-chev-left" viewBox="0 0 24 24"><path d="M14.4 6.4 8.8 12l5.6 5.6"/></symbol>
<symbol id="i-chev-right" viewBox="0 0 24 24"><path d="M9.6 6.4 15.2 12l-5.6 5.6"/></symbol>
<symbol id="i-pause" viewBox="0 0 24 24"><path d="M9.6 5.6v12.8M14.4 5.6v12.8"/></symbol>
<symbol id="i-volume" viewBox="0 0 24 24"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/></symbol>
<symbol id="i-mute" viewBox="0 0 24 24"><path d="M11 5L6 9H2v6h4l5 4V5z"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></symbol>
<symbol id="i-whale" viewBox="0 0 24 24"><path d="M3 14c0 3 3 5 7 5s8-1 11-4c-2-1-4-1-6 0-1-3-4-5-8-5-3 0-4 2-4 4z"/><circle cx="7" cy="13" r="1"/><path d="M18 9c1-2 3-3 5-3-1 2-1 4 0 6"/></symbol>
</defs></svg>

<!-- ══ AMBIENT STAGE (a quiet lit backdrop, never animated away) ══ -->
<div class="stage" aria-hidden="true"></div>

<div class="app-shell">

  <!-- ══ INSTITUTIONAL TOPBAR ══ -->
  <header class="app-topbar">
    <div class="brand-group">
      <button class="menu-toggle-btn" id="btnMenu" onclick="toggleSidebar()" aria-label="منوی ناوبری">
        <svg class="ic"><use href="#i-menu"/></svg>
      </button>
      <div class="brand-badge" aria-hidden="true"><svg class="ic ic-lg"><use href="#i-mark"/></svg></div>
      <div class="brand-title-wrap">
        <div class="brand-title-row">
          <h1>MOHMD NEWS</h1>
          <span class="live-pill">
            <span class="dot" id="cycleDot"></span>
            <span id="cycleTxt">زنده</span>
          </span>
        </div>
      </div>
    </div>

    <!-- Telemetry capsule — kept in English (terminal vernacular, next to the
         live cycle pill it belongs to) -->
    <div class="topbar-telemetry" id="cyclePill">
      <div class="telem-item" title="News retention window">
        <span>Window</span><b id="ruleAge">24</b><span>h</span>
      </div>
      <div class="telem-divider"></div>
      <div class="telem-item">
        <span>Next poll</span><b id="nextIn">—</b>
      </div>
      <div class="telem-divider"></div>
      <div class="telem-item">
        <span>Last sync</span><b id="lastUpd">—</b>
      </div>
      <div class="telem-divider"></div>
      <!-- offline-first indicator: Online (Synced) / Offline (Cache Mode). It
           reflects what the last request actually did, not navigator.onLine —
           a WAN that is up but cannot reach Flask is still cache mode. -->
      <div class="telem-item pwa-item" id="pwaItem" data-mode="boot" role="status" aria-live="polite">
        <span class="pwa-dot" id="pwaDot" aria-hidden="true"></span><b id="pwaTxt">…</b>
      </div>
      <div class="telem-divider"></div>
      <!-- live stream health: which transport is carrying prices/news/calendar
           right now (WebSocket, SSE, or the polling fallback) -->
      <div class="telem-item pwa-item" id="smItem" data-mode="boot" role="status" aria-live="off">
        <span class="pwa-dot" id="smDot" aria-hidden="true"></span><b id="smTxt">…</b>
      </div>
      <div class="telem-divider"></div>
    </div>

    <div class="topbar-actions">
      <button class="btn ghost" id="refreshBtn" onclick="doRefresh()">
        <svg class="ic"><use href="#i-refresh"/></svg> <span>Refresh</span>
      </button>
    </div>
  </header>
  <div class="dl2-ticker" id="tickerBar" role="status" aria-live="off" aria-label="قیمت لحظه‌ای دارایی‌ها"></div>

  <!-- ══ APP BODY CONTAINER (Sidebar on RIGHT, Main on LEFT in RTL) ══ -->
  <div class="app-body">

    <!-- ══ RIGHT NAVIGATION SIDEBAR (First flex item = Far Right in RTL) ══ -->
    <aside class="app-sidebar" id="appSidebar" role="tablist" aria-label="ناوبری داشبورد" aria-orientation="vertical">
      <div class="rail-group">
      <div class="rail-group-label">پایش بازار</div>
      <button id="nav-feed" class="tab nav-item active" role="tab" aria-selected="true" aria-controls="view-feed" data-view="feed" onclick="showView('feed')">
        <span class="nav-icon"><svg class="ic"><use href="#i-news"/></svg></span>
        <span class="nav-text">جریان زنده اخبار</span>
        <span class="cnt" id="cntFeed">۰</span>
      </button>
      <button id="nav-reports" class="tab nav-item" role="tab" aria-selected="false" aria-controls="view-reports" data-view="reports" onclick="showView('reports')">
        <span class="nav-icon"><svg class="ic"><use href="#i-chart"/></svg></span>
        <span class="nav-text">تحلیل و گزارش‌ها</span>
      </button>
      <button id="nav-studio" class="tab nav-item" role="tab" aria-selected="false" aria-controls="view-studio" data-view="studio" onclick="showView('studio')">
        <span class="nav-icon"><svg class="ic"><use href="#i-bulb"/></svg></span>
        <span class="nav-text">استودیو محتوا</span>
      </button>
      <button id="nav-channel" class="tab nav-item" role="tab" aria-selected="false" aria-controls="view-channel" data-view="channel" onclick="showView('channel')">
        <span class="nav-icon"><svg class="ic"><use href="#i-coins"/></svg></span>
        <span class="nav-text">کانال طلا و سکه</span>
        <span class="cnt" id="cntChannel" style="display:none">۰</span>
      </button>
      <button id="nav-ideas" class="tab nav-item" role="tab" aria-selected="false" aria-controls="view-ideas" data-view="ideas" onclick="showView('ideas')">
        <span class="nav-icon"><svg class="ic"><use href="#i-bulb"/></svg></span>
        <span class="nav-text">ایده‌های تریدینگ‌ویو</span>
      </button>
      <button id="nav-calendar" class="tab nav-item" role="tab" aria-selected="false" aria-controls="view-calendar" data-view="calendar" onclick="showView('calendar')">
        <span class="nav-icon"><svg class="ic"><use href="#i-calendar"/></svg></span>
        <span class="nav-text">تقویم اقتصادی</span>
        <span class="cnt" id="cntEvents" style="display:none">۰</span>
      </button>
      <button id="nav-etf" class="tab nav-item" role="tab" aria-selected="false" aria-controls="view-etf" data-view="etf" onclick="showView('etf')">
        <span class="nav-icon"><svg class="ic"><use href="#i-bank"/></svg></span>
        <span class="nav-text">نرخ زندهٔ ETF</span>
      </button>
      <button id="nav-whales" class="tab nav-item" role="tab" aria-selected="false" aria-controls="view-whales" data-view="whales" onclick="showView('whales')">
        <span class="nav-icon"><svg class="ic"><use href="#i-whale"/></svg></span>
        <span class="nav-text">ردیاب نهنگ‌ها</span>
        <span class="cnt" id="cntWhales" style="display:none">۰</span>
      </button>
      <button id="nav-archive" class="tab nav-item" role="tab" aria-selected="false" aria-controls="view-archive" data-view="archive" onclick="showView('archive')">
        <span class="nav-icon"><svg class="ic"><use href="#i-archive"/></svg></span>
        <span class="nav-text">آرشیو هوشمند</span>
        <span class="cnt" id="cntArchive" style="display:none">۰</span>
      </button>

      <button id="nav-bookmarks" class="tab nav-item" role="tab" aria-selected="false" aria-controls="view-bookmarks" data-view="bookmarks" onclick="showView('bookmarks')">
        <span class="nav-icon"><svg class="ic"><use href="#i-star"/></svg></span>
        <span class="nav-text">نشان‌شده‌ها</span>
        <span class="cnt" id="cntBmarks" style="display:none">۰</span>
      </button>

      </div>

      <div class="rail-group">
      <div class="rail-group-label">سیستم و سلامت</div>
      <button id="nav-monitor" class="tab nav-item" role="tab" aria-selected="false" aria-controls="view-monitor" data-view="monitor" onclick="showView('monitor')">
        <span class="nav-icon"><svg class="ic"><use href="#i-pulse"/></svg></span>
        <span class="nav-text">سلامت منابع</span>
        <span class="cnt" id="cntBroken" style="display:none">۰</span>
      </button>
      <button id="nav-alerts" class="tab nav-item" role="tab" aria-selected="false" aria-controls="view-alerts" data-view="alerts" onclick="showView('alerts')">
        <span class="nav-icon"><svg class="ic"><use href="#i-send"/></svg></span>
        <span class="nav-text">پیام‌رسان‌ها (تلگرام / بله)</span>
      </button>

      </div>

      <div class="rail-group">
        <div class="rail-group-label">مدیریت و پیکربندی</div>
        <button class="tab nav-item" id="ibSettings" role="tab" aria-selected="false" aria-controls="view-settings" data-view="settings" onclick="showView('settings')">
          <span class="nav-icon"><svg class="ic"><use href="#i-gear"/></svg></span>
          <span class="nav-text">تنظیمات داشبورد</span>
        </button>
        <button class="tab nav-item" id="ibSources" role="tab" aria-selected="false" aria-controls="view-sources" data-view="sources" onclick="showView('sources')">
          <span class="nav-icon"><svg class="ic"><use href="#i-rss"/></svg></span>
          <span class="nav-text">مدیریت منابع خبری</span>
          <span class="cnt" id="cntSrc">۰</span>
        </button>
        <button class="tab nav-item" id="ibAssets" role="tab" aria-selected="false" aria-controls="view-assets" data-view="assets" onclick="showView('assets')">
          <span class="nav-icon"><svg class="ic"><use href="#i-coins"/></svg></span>
          <span class="nav-text">مدیریت دارایی‌ها</span>
        </button>
      </div>

      <div class="sidebar-footer">
        <button class="dl2-rail-toggle" id="railToggle" type="button" aria-expanded="true"
                aria-label="جمع و باز کردن نوار کناری" onclick="toggleRail()">
          <svg class="ic"><use href="#i-panel"/></svg>
        </button>
      </div>
    </aside>

    <!-- ══ MAIN SCROLLABLE CONTENT (Second flex item = Left of Sidebar in RTL) ══ -->
    <main class="app-main" id="main" tabindex="-1">

      <!-- Views Container -->
      <div class="view-container">

        <!-- ══ 1 · LIVE FEED — default view ══ -->
        <section class="view active" id="view-feed" role="tabpanel" aria-labelledby="nav-feed">

          <!-- ── FILTER MODEL 3 — one line, one button ──────────────────────
               The page used to open on three boxes of chrome (search, four
               labelled fields, credibility slider, then two sideways pill
               lanes) before the first headline. Now the view opens on a single
               38px line: “فیلترها” with a live count of what is on, the active
               filters as removable chips, and the result count. Everything
               else — sort, kind, source, credibility, every asset, every
               topic — lives in the sheet that drops out of that button. -->
          <div class="tb-wrap">
            <div class="tb" id="feedTB">
              <button class="tb-btn" id="feedBtn" onclick="tbToggle('feedSheet')"
                      aria-expanded="false" aria-controls="feedSheet">
                <span><svg class="ic"><use href="#i-filter"/></svg> فیلترها</span>
                <span class="tb-badge" id="feedBadge" data-n="0">۰</span>
                <span class="tb-caret">▾</span>
              </button>
              <div class="tb-live" id="feedLive"></div>
              <span class="tb-count"><span class="fb-dot"></span> <b id="feedCount" role="status">—</b></span>

              <div class="fsheet" id="feedSheet" role="dialog" aria-modal="false" aria-label="فیلترهای جریان خبر">
                <div class="fsheet-hd">
                  <b>فیلتر جریان خبر</b>
                  <button class="fsheet-x" onclick="tbClose('feedSheet')" aria-label="بستن پنل فیلتر"><svg class="ic"><use href="#i-x"/></svg></button>
                </div>

                <div class="fsec">                        <span class="fsec-lbl">جستجو</span>
                  <div class="fsec-row">
                    <div class="fsearch">
                      <span class="fb-ic"><svg class="ic"><use href="#i-search"/></svg></span>
                      <label class="visually-hidden" for="q">جستجو</label>
                      <input type="text" id="q" placeholder="جستجو در تیتر، خلاصه و منبع…" oninput="renderFeed()">
                      <kbd class="fb-kbd">ESC</kbd>
                    </div>
                  </div>
                </div>

                <div class="fsec">
                  <span class="fsec-lbl">نمایش و ترتیب</span>
                  <div class="fsec-row">
                    <label class="fr-inline"><span>ترتیب</span>
                      <select id="sortSel" class="fsel" onchange="renderFeed()" aria-label="ترتیب نمایش">
                        <option value="new" selected>جدیدترین</option>
                        <option value="cred">بیشترین اعتبار</option>
                        <option value="src">نام منبع</option>
                      </select></label>
                    <label class="fr-inline"><span>دستهٔ منبع</span>
                      <select id="kindSel" class="fsel" onchange="renderFeed()" aria-label="دسته منبع"></select></label>
                    <label class="fr-inline"><span>منبع</span>
                      <select id="srcSel" class="fsel" onchange="renderFeed()" aria-label="منبع خبری"></select></label>
                  </div>
                  <div class="fsec-row" style="margin-top:8px">
                    <label class="fr-inline"><span>احساسات</span>
                      <select id="sentSel" class="fsel" onchange="renderFeed()" aria-label="احساسات بازار">
                        <option value="all" selected>همه احساسات</option>
                        <option value="bullish">🟢 صعودی (Bullish)</option>
                        <option value="bearish">🔴 نزولی (Bearish)</option>
                        <option value="neutral">⚪ خنثی</option>
                      </select></label>
                    <label class="fr-inline"><span>بازه زمانی</span>
                      <select id="timeRangeSel" class="fsel" onchange="renderFeed()" aria-label="بازه زمانی">
                        <option value="all" selected>همه زمان‌ها</option>
                        <option value="12">۱۲ ساعت گذشته</option>
                        <option value="24">۲۴ ساعت گذشته</option>
                        <option value="48">۴۸ ساعت گذشته</option>
                        <option value="72">۳ روز گذشته</option>
                      </select></label>
                  </div>
                </div>

                <div class="fsec">
                  <span class="fsec-lbl">حداقل اعتبار</span>
                  <div class="fsec-row">
                    <div class="fcred">
                      <input type="range" id="credSlider" min="0" max="90" step="5" value="0" aria-label="حداقل اعتبار"
                             oninput="document.getElementById('credVal').textContent=toFa(this.value)+'٪';renderFeed()">
                      <b id="credVal">۰٪</b>
                    </div>
                  </div>
                </div>

                <div class="fsec">
                  <span class="fsec-lbl">دارایی‌ها <span class="fsec-n" id="assetChipsN"></span></span>
                  <div class="fgrid" id="assetChips"></div>
                </div>

                <div class="fsec">
                  <span class="fsec-lbl">موضوعات <span class="fsec-n" id="topicChipsN"></span></span>
                  <div class="fgrid" id="topicChips"></div>
                </div>

                <!-- news hygiene: these two change what the server pulls at all,
                     so they are saved settings, not view-only filters -->
                <div class="fsec">
                  <span class="fsec-lbl">پاک‌سازی خبرها</span>
                  <div class="fsec-row">
                    <label class="fr-inline" style="cursor:pointer"><input type="checkbox" id="fHideSocial" onchange="saveHygiene()"> خبرهای شبکه‌های اجتماعی نیاید</label>
                    <label class="fr-inline"><span>حداقل طول خبر (کاراکتر)</span>
                      <input type="number" id="fMinChars" min="0" max="2000" step="20" style="width:90px"
                             onchange="saveHygiene()"></label>
                  </div>
                  <div class="fsec-row">
                    <label class="fr-inline" style="cursor:pointer"><input type="checkbox" id="fSocialGate" onchange="saveHygiene()"> حداقل لایک شبکه‌های اجتماعی</label>
                    <label class="fr-inline"><span>حداقل آپ‌ووت (لایک)</span>
                      <input type="number" id="fSocialMin" min="0" max="100000" step="100" style="width:90px"
                             onchange="saveHygiene()"></label>
                  </div>
                  <div class="hint" style="margin-block-start:6px">پست‌های ردیت با آپ‌ووت کمتر از حد تعیین‌شده وارد جریان خبر نمی‌شوند (لایک‌ها از آرشیو زندهٔ ردیت خوانده می‌شوند؛ ۰ = خاموش).</div>
                </div>

                <div class="fsheet-ft">
                  <button class="fclr" id="feedReset" onclick="resetFeedFilters()" title="پاک کردن همه فیلترها" hidden><svg class="ic"><use href="#i-x"/></svg> پاک‌کردن همه</button>
                  <span class="sp"></span>
                  <button class="fdone" onclick="tbClose('feedSheet')">نمایش نتیجه</button>
                </div>
              </div>
            </div>
          </div>

          <div class="lead-row" id="leadRow"></div>
          <div class="ngrid" id="newsGrid"></div>
          <div class="empty" id="feedEmpty" style="display:none">خبری با این فیلترها پیدا نشد — فیلترها را ساده‌تر کن یا بازهٔ خبری را در تنظیمات بزرگ‌تر کن.</div>

        </section>

        <!-- ══ 2 · REPORTS — per-asset generated analysis + live chart ══ -->
        <section class="view" id="view-reports" role="tabpanel" aria-labelledby="nav-reports">
          <!-- the asset row was a 14-pill scroller across the top of the tab;
               it is now one line naming the open report, with the picker in a
               sheet — the same model as the feed and the ideas tab -->
          <div class="tb-wrap">
            <div class="tb" id="repTB">
              <button class="tb-btn" id="repBtn" onclick="tbToggle('repSheet')"
                      aria-expanded="false" aria-controls="repSheet">
                <span><svg class="ic"><use href="#i-file"/></svg> دارایی گزارش:</span>
                <b id="repBtnName">انتخاب کنید</b>
                <span class="tb-caret">▾</span>
              </button>
              <span class="tb-hint" id="repHint">تحلیل کامل، منابع و نمودار هر دارایی</span>
              <div class="fsheet" id="repSheet" role="dialog" aria-modal="false" aria-label="انتخاب دارایی برای گزارش">
                <div class="fsheet-hd">
                  <b>یک دارایی را انتخاب کنید</b>
                  <button class="fsheet-x" onclick="tbClose('repSheet')" aria-label="بستن"><svg class="ic"><use href="#i-x"/></svg></button>
                </div>
                <div class="fsec">
                  <span class="fsec-lbl">دارایی‌ها <span class="fsec-n" id="repChipsN"></span></span>
                  <div class="fgrid" id="repChips"></div>
                </div>
              </div>
            </div>
          </div>
          <div id="repBox"><div class="empty">یکی از دارایی‌ها را انتخاب کنید تا گزارش تحلیلی و نمودار آن ساخته شود.</div></div>
        </section>

        <!-- ══ 3 · TRADINGVIEW IDEAS — chart, full text, Persian translation ══ -->
        <section class="view" id="view-ideas" role="tabpanel" aria-labelledby="nav-ideas">
          <header class="tv-hero">
            <div class="tvh-l">
              <span class="tvh-brand">ایده‌های تریدینگ‌ویو</span>
              <h2>ایده‌های تحلیل‌گران تریدینگ‌ویو</h2>
              <p>هر ایده با تصویر چارت خودِ تریدینگ‌ویو، متن کامل، جهت معامله، تایم‌فریم، آمار تعامل و شمار دنبال‌کننده‌های نویسنده می‌آید — و با یک کلیک به صفحهٔ اصلی ایده در تریدینگ‌ویو باز می‌شود.</p>
            </div>
            <div class="tvh-r">
              <a class="btn ghost sm" id="ideasAllLink" href="https://www.tradingview.com/ideas/" target="_blank" rel="noopener">صفحهٔ ایده‌ها در تریدینگ‌ویو <svg class="ic"><use href="#i-external"/></svg></a>
              <span class="tvh-note" id="ideasSummary">در حال خواندن…</span>
            </div>
          </header>

          <!-- the same filter-bar model as the news feed: labelled selects in
               one row, the asset lane as a horizontally scrolling pill row -->
          <!-- same model as the feed: one line, one button, sheet behind it -->
          <div class="tb-wrap">
            <div class="tb" id="ideasTB">
              <button class="tb-btn" id="ideasBtn" onclick="tbToggle('ideasSheet')"
                      aria-expanded="false" aria-controls="ideasSheet">
                <span><svg class="ic"><use href="#i-filter"/></svg> فیلترها</span>
                <span class="tb-badge" id="ideasBadge" data-n="0">۰</span>
                <span class="tb-caret">▾</span>
              </button>
              <div class="tb-live" id="ideasLive"></div>
              <span class="tb-count" id="ideasCount"></span>

              <div class="fsheet" id="ideasSheet" role="dialog" aria-modal="false" aria-label="فیلترهای ایده‌ها">
                <div class="fsheet-hd">
                  <b>فیلتر ایده‌های تریدینگ‌ویو</b>
                  <button class="fsheet-x" onclick="tbClose('ideasSheet')" aria-label="بستن پنل فیلتر"><svg class="ic"><use href="#i-x"/></svg></button>
                </div>

                <div class="fsec">
                  <span class="fsec-lbl">مرتب‌سازی و نوع</span>
                  <div class="fsec-row">
                    <label class="fr-inline"><span>مرتب‌سازی</span>
                      <select id="ideasSortChips" class="fsel" onchange="setIdeasSort(this.value)" aria-label="مرتب‌سازی ایده‌ها"></select></label>
                    <label class="fr-inline"><span>نوع ایده</span>
                      <select id="ideasKindChips" class="fsel" onchange="setIdeasKind(this.value)" aria-label="نوع ایده"></select></label>
                    <label class="fr-inline" id="ideasTfBar"><span>تایم‌فریم</span>
                      <select id="ideasTfChips" class="fsel" onchange="setIdeasTf(this.value)" aria-label="تایم‌فریم ایده"></select></label>
                  </div>
                </div>

                <div class="fsec">
                  <span class="fsec-lbl">دارایی</span>
                  <div class="fgrid" id="ideasChips"></div>
                </div>

                <div class="fsheet-ft">
                  <button class="fclr" onclick="setIdeasSort('popular');setIdeasKind('all');setIdeasTf('all')"><svg class="ic"><use href="#i-x"/></svg> پاک‌کردن همه</button>
                  <span class="sp"></span>
                  <button class="fdone" onclick="tbClose('ideasSheet')">نمایش نتیجه</button>
                </div>
              </div>
            </div>
          </div>

          <div class="ideas-grid" id="ideasGrid"><div class="empty"><span class="spinner"></span> در حال دریافت ایده‌ها…</div></div>
        </section>

        <!-- ══ 4 · ECONOMIC CALENDAR — hero, week navigator, events board ══ -->
        <section class="view" id="view-calendar" role="tabpanel" aria-labelledby="nav-calendar">
          <div class="cal-grid">
            <div class="cal-main">

              <!-- Hero: the next release that can actually move price -->
              <div class="cal-hero">
                <div class="cal-hero-l">
                  <span class="cal-eyebrow">Next high-impact release</span>
                  <div class="cal-hero-ttl" id="calHeroTtl">Reading the calendar…</div>
                  <div class="cal-countdown" id="calCountdown" role="status" aria-live="polite">—</div>
                </div>
                <div class="cal-stats" id="calStats"></div>
              </div>
              <div id="calReleased" class="cal-released" style="display:none"></div>

              <!-- Controls: week, day strip, filters, timezone -->
              <div class="cal-panel">
                <div class="cal-weekrow">
                  <button class="btn ghost sm" onclick="shiftCalWeek(-1)">‹ Prev week</button>
                  <span class="cal-weeklab" id="calWeekLab">—</span>
                  <button class="btn ghost sm" onclick="shiftCalWeek(1)">Next week ›</button>
                  <button class="btn sm ghost" id="calBtnToday" onclick="gotoCalToday()">Today</button>
                  <span class="cal-src" id="calSrc"></span>
                </div>
                <div class="cal-strip" id="calStrip" role="tablist" aria-label="Days of the week"></div>
                <!-- FILTER MODEL 3 for the calendar too: the six-control row
                     that wrapped onto two lines is now one line + a sheet, with
                     the applied filters (and the timezone, which is easy to
                     forget you changed) visible as removable chips. -->
                <div class="tb-wrap">
                  <div class="tb" id="calTB">
                    <button class="tb-btn" id="calBtn" onclick="tbToggle('calSheet')"
                            aria-expanded="false" aria-controls="calSheet">
                      <span><svg class="ic"><use href="#i-filter"/></svg> Filters</span>
                      <span class="tb-badge" id="calBadge" data-n="0">۰</span>
                      <span class="tb-caret">▾</span>
                    </button>
                    <div class="tb-live" id="calLive"></div>
                    <span class="tb-count" id="calFiltersCount"></span>

                    <div class="fsheet" id="calSheet" role="dialog" aria-modal="false" aria-label="Economic calendar filters">
                      <div class="fsheet-hd">
                        <b>Economic calendar</b>
                        <button class="fsheet-x" onclick="tbClose('calSheet')" aria-label="Close"><svg class="ic"><use href="#i-x"/></svg></button>
                      </div>
                      <div class="fsec">
                        <span class="fsec-lbl">Search</span>
                        <div class="fsec-row">
                          <div class="fsearch">
                            <span class="fb-ic"><svg class="ic"><use href="#i-search"/></svg></span>
                            <input type="text" id="calQ" placeholder="Event or currency — e.g. CPI or USD" oninput="renderCalendar()">
                          </div>
                        </div>
                      </div>
                      <div class="fsec">
                        <span class="fsec-lbl">Show &amp; order</span>
                        <div class="fsec-row">
                          <label class="fr-inline"><span>Impact</span>
                            <select id="calImpact" class="fsel" onchange="renderCalendar()">
                              <option value="all">All levels</option>
                              <option value="High">High only</option>
                              <option value="Medium">Medium &amp; above</option>
                              <option value="Low">Low &amp; above</option>
                            </select></label>
                          <label class="fr-inline"><span>Sort</span>
                            <select id="calSort" class="fsel" onchange="renderCalendar()">
                              <option value="time">Release time</option>
                              <option value="impact">Impact, then time</option>
                              <option value="released">Released first</option>
                            </select></label>
                          <label class="fr-inline"><span>Time zone</span>
                            <select id="calTz" class="fsel" onchange="renderCalendar()">
                              <option value="UTC">UTC</option>
                              <option value="America/New_York">New York</option>
                              <option value="Europe/London">London</option>
                              <option value="Europe/Berlin">Frankfurt</option>
                              <option value="Asia/Tokyo">Tokyo</option>
                              <option value="Asia/Shanghai">Shanghai</option>
                              <option value="Asia/Tehran" selected>Tehran</option>
                              <option value="Australia/Sydney">Sydney</option>
                            </select></label>
                        </div>
                        <!-- Currency is a *multi*-select: USD and EUR and JPY can be ticked
                             together, so it gets a row of checkboxes, not one value -->
                        <div class="fsec-row ccy-row">
                          <span class="fr-inline ccy-lbl">Currency</span>
                          <div class="ccy-list" id="calCurChips" role="group" aria-label="Currency filter"></div>
                        </div>
                      </div>
                      <div class="fsec">
                        <span class="fsec-lbl">Release</span>
                        <div class="fsec-row">
                          <label class="fr-inline" style="cursor:pointer"><input type="checkbox" id="calHidePast" onchange="renderCalendar()"> Hide released events</label>
                        </div>
                      </div>
                      <div class="fsheet-ft">
                        <button class="fclr" onclick="resetCalFilters()"><svg class="ic"><use href="#i-x"/></svg> Clear all</button>
                        <span class="sp"></span>
                        <button class="fdone" onclick="tbClose('calSheet')">Show results</button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Board: one day at a time, table layout -->
              <div class="cal-board" id="calDays"></div>
            </div>

            <aside class="cal-side">
              <div class="panelbox">
                <h3><svg class="ic"><use href="#i-clock"/></svg> Market sessions</h3>
                <div id="sessionsBox" class="hint">…</div>
              </div>
              <div class="panelbox">
                <h3><svg class="ic"><use href="#i-fire"/></svg> High-impact on this day
                  <span class="panel-sub" id="calHighDay">—</span></h3>
                <div id="calHighList">…</div>
              </div>
            </aside>
          </div>
        </section>

        <!-- ══ 5 · LIVE ETF RATES — search + fund-category filter, auto-refresh ══ -->
        <section class="view" id="view-etf" role="tabpanel" aria-labelledby="nav-etf">
          <div class="panelbox">
            <h3><svg class="ic"><use href="#i-chart"/></svg> نرخ زندهٔ ETF
              <span class="hint" id="etfSummary">در حال خواندن…</span>
              <span class="live-pill" style="margin-inline-start:auto"><span class="live-dot"></span> به‌روزرسانی خودکار هر ۶۰ ثانیه</span>
            </h3>
            <!-- search stays on the line (it is the thing you actually use);
                 the group pills move into the sheet -->
            <div class="tb-wrap">
              <div class="tb" id="etfTB">
                <div class="fsearch" style="flex:1 1 260px">
                  <span class="fb-ic"><svg class="ic"><use href="#i-search"/></svg></span>
                  <input type="text" id="etfQ" placeholder="جستجوی نماد یا نام صندوق…" aria-label="جستجوی صندوق" oninput="UI.etfQ=this.value;renderEtfLive('etfLive2')">
                </div>
                <button class="tb-btn" id="etfBtn" onclick="tbToggle('etfSheet')"
                        aria-expanded="false" aria-controls="etfSheet">
                  <span><svg class="ic"><use href="#i-tag"/></svg> دسته</span>
                  <b id="etfBtnName">همه</b>
                  <span class="tb-caret">▾</span>
                </button>
                <div class="fsheet" id="etfSheet" role="dialog" aria-modal="false" aria-label="دسته‌های صندوق">
                  <div class="fsheet-hd">
                    <b>دستهٔ صندوق</b>
                    <button class="fsheet-x" onclick="tbClose('etfSheet')" aria-label="بستن"><svg class="ic"><use href="#i-x"/></svg></button>
                  </div>
                  <div class="fsec">
                    <span class="fsec-lbl">دسته‌ها</span>
                    <div class="fgrid" id="etfGroupChips"></div>
                  </div>
                </div>
              </div>
            </div>
            <div id="etfLive2" class="etfgroups"><div class="empty"><span class="spinner"></span> در حال دریافت نرخ‌های زنده…</div></div>
          </div>
        </section>

<!-- ══ 8 · SMART ARCHIVE — items that aged out of the live window ══ -->
        <section class="view" id="view-archive" role="tabpanel" aria-labelledby="nav-archive">
          <div class="panelbox">
            <h3><svg class="ic"><use href="#i-archive"/></svg> آرشیو هوشمند <span id="archSummary" class="panel-sub">…</span></h3>
            <div id="archGrid" class="grid"></div>
            <div class="empty" id="archEmpty" style="display:none">آرشیو خالی است — با گذر زمان خبرهای قدیمی‌تر از پنجرهٔ فعال اینجا می‌آیند.</div>
          </div>
        </section>

        <!-- ══ 6b · BOOKMARKS — starred stories, kept in this browser ══ -->
        <section class="view" id="view-bookmarks" role="tabpanel" aria-labelledby="nav-bookmarks">
          <div class="panelbox">
            <h3><svg class="ic"><use href="#i-star"/></svg> نشان‌شده‌ها <span id="bmarkSummary" class="panel-sub">…</span>
              <div style="display:flex;gap:8px;margin-inline-start:auto;flex-wrap:wrap">
                <button class="btn ghost sm" onclick="FreebuffBookmarks.exportJSON()" title="ذخیره نشان‌شده‌ها در قالب فایل JSON"><svg class="ic"><use href="#i-download"/></svg> دریافت فایل خروجی (Export)</button>
                <button class="btn ghost sm" onclick="document.getElementById('importBmarkFile').click()" title="بارگذاری فایل نشان‌شده‌ها"><svg class="ic"><use href="#i-upload"/></svg> بازیابی (Import)</button>
                <input type="file" id="importBmarkFile" accept=".json" style="display:none" onchange="FreebuffBookmarks.importJSON(event)">
                <button class="btn ghost sm" onclick="clearBookmarks()"><svg class="ic"><use href="#i-trash"/></svg> پاک‌کردن همه</button>
              </div></h3>
            <div id="bmarkGrid" class="ngrid"></div>
            <div class="empty" id="bmarkEmpty" style="display:none">هنوز خبری نشان نشده — روی ستارهٔ هر کارت خبر بزن تا اینجا ذخیره شود.</div>
          </div>
        </section>

        <!-- ══ 7 · SOURCE HEALTH — status of every feed the scraper polls ══ -->
        <section class="view" id="view-monitor" role="tabpanel" aria-labelledby="nav-monitor">
          <div class="panelbox">
            <h3><svg class="ic"><use href="#i-pulse"/></svg> سلامت منابع — <span id="monSummary" class="panel-sub">…</span>
              <button class="btn" id="recoverBtn" style="margin-inline-start:auto" onclick="recoverAll()">
                <svg class="ic"><use href="#i-refresh"/></svg> بازیابی همهٔ فیدهای خراب</button></h3>
            <div class="hint" style="margin-block-end:12px">
              وضعیت اتصال به همهٔ فیدهای خبری و تلاش‌های بازیابی خودکار هر منبع، اینجا زنده پایش می‌شود.
            </div>
            <div id="monList"></div>
          </div>
        </section>

        <!-- ══ 8 · MESSENGER DIGEST (Telegram / Bale) ══ -->
        <section class="view" id="view-alerts" role="tabpanel" aria-labelledby="nav-alerts">
          <!-- Messenger Switcher Tabs -->
          <div class="tabs-sub" style="display:flex;gap:10px;margin-bottom:16px;">
            <button type="button" class="btn" id="subtab-btn-tg" onclick="switchMessengerTab('tg')" style="flex:1;display:flex;align-items:center;justify-content:center;gap:8px;padding:10px 16px">
              <svg class="ic"><use href="#i-send"/></svg> <b>پیام‌رسان تلگرام (Telegram)</b>
            </button>
            <button type="button" class="btn ghost" id="subtab-btn-bale" onclick="switchMessengerTab('bale')" style="flex:1;display:flex;align-items:center;justify-content:center;gap:8px;padding:10px 16px">
              <span style="font-size:1.1rem">🟢</span> <b>پیام‌رسان بله (Bale)</b>
            </button>
          </div>

          <!-- Telegram Panel -->
          <div class="panelbox" id="panel-messenger-tg">
            <h3><svg class="ic"><use href="#i-send"/></svg> پیام‌رسان تلگرام <span class="hint">— خلاصهٔ خودکار معتبرترین خبرها بعد از هر چرخه</span>
              <button class="btn sm" style="margin-inline-start:auto" onclick="sendNowTelegram()">
                <svg class="ic"><use href="#i-send"/></svg> ارسال خلاصه الآن</button></h3>
            <div class="formgrid">
              <div style="grid-column:1/-1">
                <label>توکن ربات (از BotFather@ در تلگرام)</label>
                <div style="display:flex;gap:8px;align-items:center">
                  <input type="password" id="tgToken" placeholder="123456789:ABC-DEF..." style="direction:ltr;text-align:left;flex:1">
                  <button type="button" class="btn ghost sm" onclick="toggleTokenVisibility()" title="نمایش/مخفی‌سازی توکن">👁️</button>
                </div>
              </div>
              <div style="grid-column:1/-1">
                <label>شناسه چت یا کانال (Chat ID یا آیدی کانال مثل mychannel@)</label>
                <div style="display:flex;gap:8px;align-items:center">
                  <input type="text" id="tgChat" placeholder="-100123456789 یا @mychannel" style="direction:ltr;text-align:left;flex:1">
                  <button type="button" class="btn ghost sm" onclick="detectTelegramChat()" id="btnDetectChat" title="بررسی ربات و استخراج خودکار شناسه‌های چت اخیر">🔍 تشخیص خودکار چت</button>
                </div>
                <div id="detectedChatsBox" style="display:none;margin-top:8px"></div>
                <div class="hint" style="margin-top:6px;font-size:0.8rem;line-height:1.5">
                  💡 <b>راهنمایی:</b> برای چت خصوصی، ابتدا در تلگرام وارد ربات شده و <code>Start/</code> را بزنید سپس روی «تشخیص خودکار» کلیک کنید. برای کانال، ربات را به کانال اضافه کرده و دسترسی ارسال پیام (Admin) به آن بدهید.
                </div>
              </div>
              <div style="grid-column:1/-1;display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:6px">
                <button class="btn" onclick="saveTelegram()">ذخیره همه تنظیمات</button>
                <button class="btn ghost" onclick="testTelegram()">ارسال پیام تست</button>
              </div>
            </div>
            <h4><svg class="ic"><use href="#i-gear"/></svg> تنظیمات ارسال</h4>
            <div class="formgrid">
              <div class="setrow" style="border:none;padding:0">
                <span class="lbl">ارسال خودکار فعال باشد</span>
                <label class="switch"><input type="checkbox" id="tgEnabled"><span class="slider"></span></label>
              </div>
              <div><label>حداقل اعتبار خبر (۰ تا ۱)</label>
                <input type="text" id="tgMinCred" inputmode="decimal" placeholder="0.75" style="direction:ltr;text-align:left"></div>
              <div><label>حداکثر تعداد خبر در هر پیام</label>
                <input type="text" id="tgMaxItems" inputmode="numeric" placeholder="10" style="direction:ltr;text-align:left"></div>
              <div><label>فقط خبرهای تازه‌تر از (ساعت)</label>
                <input type="text" id="tgMaxAge" inputmode="numeric" placeholder="6" style="direction:ltr;text-align:left"></div>
              <div><label>فیلتر دارایی (با کاما، خالی = همه)</label>
                <input type="text" id="tgAssets" placeholder="BTC, ETH, XAU" style="direction:ltr;text-align:left"></div>
              <div><label>زبان پیام</label>
                <select id="tgLang" style="width:100%">
                  <option value="fa">فارسی</option>
                  <option value="en">English</option>
                </select></div>
            </div>
            <h4><svg class="ic"><use href="#i-grid"/></svg> رفتار پیام</h4>
            <div class="tg-toggles">
              <label class="tgopt"><input type="checkbox" id="tgQuiet" checked><svg class="ic"><use href="#i-moon"/></svg><span>سکوت شبانه (۲۳ تا ۸ صبح ارسال نشود)</span></label>
              <label class="tgopt"><input type="checkbox" id="tgLink" checked><svg class="ic"><use href="#i-link"/></svg><span>تیتر به‌صورت هایپرلینک به خبر</span></label>
              <label class="tgopt"><input type="checkbox" id="tgLinkLine"><svg class="ic"><use href="#i-plus"/></svg><span>لینک در خط جدا هم بیاید</span></label>
              <label class="tgopt"><input type="checkbox" id="tgSummary" checked><svg class="ic"><use href="#i-file"/></svg><span>خلاصهٔ فارسی خبر در پیام</span></label>
              <label class="tgopt"><input type="checkbox" id="tgHashtags" checked><svg class="ic"><use href="#i-hash"/></svg><span>هشتگ دارایی‌ها (#BTC #ETH)</span></label>
              <label class="tgopt"><input type="checkbox" id="tgEmoji" checked><svg class="ic"><use href="#i-bell"/></svg><span>ایموجی شروع هر خبر</span></label>
              <label class="tgopt"><input type="checkbox" id="tgStars" checked><svg class="ic"><use href="#i-star"/></svg><span>ستارهٔ اعتبار (تا ۵ ستاره)</span></label>
              <label class="tgopt"><input type="checkbox" id="tgSilent"><svg class="ic"><use href="#i-bell-off"/></svg><span>ارسال بی‌صدا (نوتیف نزند)</span></label>
              <label class="tgopt"><input type="checkbox" id="tgPin"><svg class="ic"><use href="#i-pin"/></svg><span>پیام بعد از ارسال پین شود</span></label>
            </div>
            <h4><svg class="ic"><use href="#i-file"/></svg> قالب پیام</h4>
            <div class="tg-vars">
              متغیرها: <code class="ltr">{index} {title} {summary_fa} {source} {cred} {stars} {assets} {tags} {time_fa} {link_line}</code>
              — قالب خالی = پیش‌فرض
            </div>
            <textarea id="tgTemplate" class="tg-template" rows="5" aria-label="قالب پیام تلگرام"></textarea>
            <div class="tg-actions">
              <button class="btn" onclick="saveTelegram()"><svg class="ic"><use href="#i-save"/></svg> ذخیرهٔ همهٔ تنظیمات</button>
              <button class="btn ghost" onclick="previewTelegram()"><svg class="ic"><use href="#i-eye"/></svg> پیش‌نمایش پیام</button>
            </div>
            <div id="tgPreview" class="tg-preview"></div>
            <div class="hint" style="margin-block-start:10px">بعد از هر چرخه، جمع‌بندی معتبرترین خبرها خودکار به همین چت فرستاده می‌شود.</div>
          </div>

          <!-- Bale Messenger Panel -->
          <div class="panelbox" id="panel-messenger-bale" style="display:none">
            <h3><span>🟢</span> پیام‌رسان بله (Bale) <span class="hint">— خلاصهٔ خودکار خبرها در پیام‌رسان بله (داخلی و بدون نیاز به فیلترشکن)</span>
              <button class="btn sm" style="margin-inline-start:auto" onclick="sendNowBale()">
                <svg class="ic"><use href="#i-send"/></svg> ارسال خلاصه الآن به بله</button></h3>
            <div class="formgrid">
              <div style="grid-column:1/-1">
                <label>توکن ربات بله (از BotFather@ در پیام‌رسان بله)</label>
                <div style="display:flex;gap:8px;align-items:center">
                  <input type="password" id="baleToken" placeholder="123456789:ABC-DEF..." style="direction:ltr;text-align:left;flex:1">
                  <button type="button" class="btn ghost sm" onclick="toggleBaleTokenVisibility()" title="نمایش/مخفی‌سازی توکن">👁️</button>
                </div>
              </div>
              <div style="grid-column:1/-1">
                <label>شناسه چت یا کانال بله (Chat ID یا آیدی کانال مثل mychannel@)</label>
                <div style="display:flex;gap:8px;align-items:center">
                  <input type="text" id="baleChat" placeholder="12345678 یا @mychannel" style="direction:ltr;text-align:left;flex:1">
                  <button type="button" class="btn ghost sm" onclick="detectBaleChat()" id="btnDetectBaleChat" title="بررسی ربات بله و دریافت خودکار شناسه‌های چت اخیر">🔍 تشخیص خودکار چت</button>
                </div>
                <div id="detectedBaleChatsBox" style="display:none;margin-top:8px"></div>
                <div class="hint" style="margin-top:6px;font-size:0.8rem;line-height:1.5">
                  💡 <b>راهنمایی در بله:</b> برای چت خصوصی، در اپلیکیشن بله وارد ربات خود شوید و دکمه <b>شروع (Start)</b> را بزنید سپس روی «تشخیص خودکار» کلیک کنید. برای کانال، ربات را به کانال اضافه کرده و دسترسی مدیریت (ارسال پیام) به آن بدهید.
                </div>
              </div>
              <div style="grid-column:1/-1;display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:6px">
                <button class="btn" onclick="saveBale()">ذخیره تنظیمات بله</button>
                <button class="btn ghost" onclick="testBale()">ارسال پیام تست به بله</button>
              </div>
            </div>
            <h4><svg class="ic"><use href="#i-gear"/></svg> تنظیمات ارسال در بله</h4>
            <div class="formgrid">
              <div class="setrow" style="border:none;padding:0">
                <span class="lbl">ارسال خودکار به بله فعال باشد</span>
                <label class="switch"><input type="checkbox" id="baleEnabled"><span class="slider"></span></label>
              </div>
              <div><label>حداقل اعتبار خبر (۰ تا ۱)</label>
                <input type="text" id="baleMinCred" inputmode="decimal" placeholder="0.70" style="direction:ltr;text-align:left"></div>
              <div><label>حداکثر تعداد خبر در هر پیام</label>
                <input type="text" id="baleMaxItems" inputmode="numeric" placeholder="10" style="direction:ltr;text-align:left"></div>
              <div><label>فقط خبرهای تازه‌تر از (ساعت)</label>
                <input type="text" id="baleMaxAge" inputmode="numeric" placeholder="24" style="direction:ltr;text-align:left"></div>
              <div><label>فیلتر دارایی (با کاما، خالی = همه)</label>
                <input type="text" id="baleAssets" placeholder="BTC, ETH, XAU" style="direction:ltr;text-align:left"></div>
              <div><label>زبان پیام</label>
                <select id="baleLang" style="width:100%">
                  <option value="fa">فارسی</option>
                  <option value="en">English</option>
                </select></div>
            </div>
            <h4><svg class="ic"><use href="#i-grid"/></svg> رفتار پیام در بله</h4>
            <div class="tg-toggles">
              <label class="tgopt"><input type="checkbox" id="baleQuiet" checked><svg class="ic"><use href="#i-moon"/></svg><span>سکوت شبانه (۲۳ تا ۸ صبح ارسال نشود)</span></label>
              <label class="tgopt"><input type="checkbox" id="baleLink" checked><svg class="ic"><use href="#i-link"/></svg><span>درج لینک خبر</span></label>
              <label class="tgopt"><input type="checkbox" id="baleSummary" checked><svg class="ic"><use href="#i-file"/></svg><span>خلاصهٔ فارسی خبر در پیام</span></label>
              <label class="tgopt"><input type="checkbox" id="baleHashtags" checked><svg class="ic"><use href="#i-hash"/></svg><span>هشتگ دارایی‌ها (#BTC #طلا)</span></label>
              <label class="tgopt"><input type="checkbox" id="baleEmoji" checked><svg class="ic"><use href="#i-bell"/></svg><span>ایموجی شروع هر خبر</span></label>
              <label class="tgopt"><input type="checkbox" id="baleStars" checked><svg class="ic"><use href="#i-star"/></svg><span>ستارهٔ اعتبار خبر</span></label>
              <label class="tgopt"><input type="checkbox" id="baleSilent"><svg class="ic"><use href="#i-bell-off"/></svg><span>ارسال بی‌صدا (بدون نوتیفیکیشن)</span></label>
            </div>
            <h4><svg class="ic"><use href="#i-file"/></svg> قالب پیام در بله</h4>
            <div class="tg-vars">
              متغیرها: <code class="ltr">{index} {title} {summary_fa} {source} {cred} {stars} {assets} {tags} {time_fa} {link_line}</code>
              — قالب خالی = پیش‌فرض
            </div>
            <textarea id="baleTemplate" class="tg-template" rows="5" aria-label="قالب پیام بله"></textarea>
            <div class="tg-actions">
              <button class="btn" onclick="saveBale()"><svg class="ic"><use href="#i-save"/></svg> ذخیرهٔ تنظیمات بله</button>
              <button class="btn ghost" onclick="previewBale()"><svg class="ic"><use href="#i-eye"/></svg> پیش‌نمایش پیام بله</button>
            </div>
            <div id="balePreview" class="tg-preview"></div>
            <div class="hint" style="margin-block-start:10px">بعد از هر چرخه خبری، خلاصه معتبرترین اخبار به کانال یا حساب شما در پیام‌رسان بله ارسال می‌شود.</div>
          </div>

          <!-- ══ smart alerts — a rule builder over prices, the calendar and the feed ══ -->
          <div class="panelbox" id="arPanel">
            <h3><svg class="ic"><use href="#i-bell"/></svg> قوانین هشدار هوشمند
              <span class="hint" id="arSummary">…</span>
              <span class="live-pill" style="margin-inline-start:auto">
                <span class="live-dot"></span> ارزیابی روی هر تیک قیمت و هر چرخهٔ خبری
              </span></h3>

            <div class="ar-builder">
              <div class="ar-top">
                <div><label>نام قانون</label>
                  <input type="text" id="arName" placeholder="مثلاً: نفت بالای ۱۰۰ دلار"></div>
                <div><label>منطق شرط‌ها</label>
                  <select id="arLogic">
                    <option value="and">همهٔ شرط‌ها (AND)</option>
                    <option value="or">یکی از شرط‌ها (OR)</option>
                  </select></div>
                <div><label>حداقل فاصلهٔ تکرار (دقیقه)</label>
                  <input type="text" id="arCooldown" inputmode="numeric" value="30" style="direction:ltr;text-align:left"></div>
              </div>
              <div class="ar-conds" id="arConds"></div>
              <div class="ar-btns">
                <button class="btn ghost sm" onclick="arAddCond()"><svg class="ic"><use href="#i-plus"/></svg> افزودن شرط</button>
                <span class="hint" id="arLogicHint"></span>
              </div>
              <h4><svg class="ic"><use href="#i-send"/></svg> اقدام در صورت برقرار شدن</h4>
              <div class="ar-acts">
                <label class="ar-act"><input type="checkbox" id="arActToast" checked><svg class="ic"><use href="#i-bell"/></svg><span>توست چسبان روی داشبورد</span></label>
                <label class="ar-act"><input type="checkbox" id="arActTone"><svg class="ic"><use href="#i-pulse"/></svg><span>آهنگ هشدار (اسکواک)</span></label>
                <label class="ar-act"><input type="checkbox" id="arActTg"><svg class="ic"><use href="#i-send"/></svg><span>ارسال به تلگرام</span></label>
                <label class="ar-act"><input type="checkbox" id="arActBale"><span style="margin-left:4px">🟢</span><span>ارسال به بله</span></label>
                <label class="ar-act"><input type="checkbox" id="arActPush"><svg class="ic"><use href="#i-info"/></svg><span>نوتیفیکیشن مرورگر</span></label>
              </div>
              <div style="margin-block-start:10px"><label>قالب پیام تلگرام (HTML تلگرام)</label>
                <textarea id="arTemplate" rows="3" style="direction:ltr;text-align:left"
                          aria-label="قالب پیام هشدار"></textarea></div>
              <div class="ar-btns">
                <button class="btn" id="arSaveBtn" onclick="arSave()"><svg class="ic"><use href="#i-save"/></svg> ذخیرهٔ قانون</button>
                <button class="btn ghost" onclick="arTestNow()"><svg class="ic"><use href="#i-eye"/></svg> اجرای آزمایشی روی دادهٔ فعلی</button>
                <button class="btn ghost" onclick="arClearForm()">پاک کردن فرم</button>
              </div>
              <div class="hint" id="arHint" role="status"></div>
            </div>

            <h4 style="margin-block-start:18px"><svg class="ic"><use href="#i-list"/></svg> قوانین ثبت‌شده</h4>
            <div id="arList" class="ar-list"></div>
            <h4 style="margin-block-start:18px"><svg class="ic"><use href="#i-clock"/></svg> تاریخچهٔ اجرا</h4>
            <div id="arLog" class="ar-log"></div>
            <div class="hint" style="margin-block-start:10px">
              موتور هشدار در همین مرورگر اجرا می‌شود: روی هر تیک ۱۵ثانیه‌ای قیمت و بعد از هر چرخهٔ خبری،
              با تعویق کوتاه و بیرون از مسیر رندر. توکن تلگرام هرگز به مرورگر نمی‌آید — متن نهایی به
              سرور فرستاده می‌شود و سرور با اعتبار ذخیره‌شده ارسال می‌کند. قوانین در همین مرورگر ذخیره می‌شوند.
            </div>
          </div>
        </section>

        <!-- ══ 9 · ASSETS — add a custom tracked asset, table of covered assets ══ -->
        <section class="view" id="view-assets" role="tabpanel" aria-labelledby="ibAssets">
          <div class="panelbox">
            <h3><svg class="ic"><use href="#i-plus"/></svg> افزودن دارایی دلخواه <span class="hint">— کریپتو، سهام، فلز، شاخص</span></h3>
            <div class="formgrid">
              <div><label>نماد (لاتین)</label><input type="text" id="naSym" placeholder="LINK"></div>
              <div><label>نام فارسی</label><input type="text" id="naFa" placeholder="چین‌لینک"></div>
              <div><label>نام انگلیسی</label><input type="text" id="naName" placeholder="Chainlink"></div>
              <div><label>نماد Yahoo (تاریخچه قیمت)</label><input type="text" id="naYahoo" placeholder="LINK-USD"></div>
              <div><label>شناسه CoinGecko (اختیاری)</label><input type="text" id="naCg" placeholder="chainlink"></div>
              <div><label>کلیدواژه‌های خبری (با کاما)</label><input type="text" id="naKw" placeholder="chainlink, LINK"></div>
              <div><button class="btn" onclick="addAsset()">افزودن دارایی</button></div>
            </div>
            <div class="settings-note">
              نماد Yahoo تاریخچهٔ قیمت و نمودار را می‌سازد (مثلاً LINK-USD، GC=F، AAPL).
            </div>
          </div>
          <div class="panelbox">
            <h3><svg class="ic"><use href="#i-coins"/></svg> دارایی‌های تحت پوشش</h3>
            <div id="assetTableBox"></div>
          </div>
        </section>

        <!-- ══ 10 · SOURCES — the active list and the add-a-feed form ══ -->
        <section class="view" id="view-sources" role="tabpanel" aria-labelledby="ibSources">
          <div class="panelbox">
            <h3><svg class="ic"><use href="#i-rss"/></svg> منابع فعال — <span id="srcCount" class="panel-sub"></span></h3>
            <div id="srcList"></div>
          </div>
          <div class="panelbox">
            <h3><svg class="ic"><use href="#i-plus"/></svg> افزودن منبع RSS جدید</h3>
            <div style="display:flex;gap:8px;flex-wrap:wrap">
              <input type="text" id="newSrcName" placeholder="نام منبع (مثلاً: Wired)" style="flex:1;min-width:150px">
              <input type="text" id="newSrcUrl" placeholder="https://example.com/rss" style="flex:2;min-width:220px;direction:ltr;text-align:left">
              <button class="btn" onclick="addSource()">افزودن</button>
            </div>
          </div>
        </section>

        <!-- ══ 11 · DASHBOARD SETTINGS — cadence, news window, coverage, auto-report ══ -->
        <section class="view" id="view-settings" role="tabpanel" aria-labelledby="ibSettings">
          <div class="panelbox">
            <h3><svg class="ic"><use href="#i-gear"/></svg> <span>تنظیمات داشبورد</span></h3>
            <div class="setrow">
              <div><div class="lbl">تناوب بروزرسانی خودکار</div><div class="hint">پایش و اعتبارسنجی خودکار دوره‌ای</div></div>
              <select id="setInterval" style="width:160px">
                <option value="300">هر ۵ دقیقه</option>
                <option value="900">هر ۱۵ دقیقه</option>
                <option value="1800" selected>هر ۳۰ دقیقه</option>
                <option value="3600">هر ۱ ساعت</option>
                <option value="7200">هر ۲ ساعت</option>
              </select>
            </div>
            <div class="setrow">
              <div><div class="lbl">پنجره خبری (حداکثر سن خبر)</div><div class="hint">خبر قدیمی‌تر از این مقدار وارد داشبورد نمی‌شود</div></div>
              <select id="setAge" style="width:160px">
                <option value="24" selected>۲۴ ساعت (پیش‌فرض)</option>
                <option value="48">۴۸ ساعت</option>
                <option value="72">۷۲ ساعت</option>
                <option value="168">۷ روز</option>
              </select>
            </div>
            <div class="setrow">
              <div><div class="lbl">دارایی‌های تحت پوشش</div><div class="hint">خبر، قیمت و گزارش برای این دارایی‌ها ساخته می‌شود</div></div>
              <div class="asset-toggles" id="assetToggles"></div>
            </div>
            <div class="setrow">
              <div><div class="lbl">تولید خودکار گزارش تحلیلی</div><div class="hint">تولید گزارش نهادی در هر چرخه</div></div>
              <label class="switch"><input type="checkbox" id="setAutoRep" checked><span class="slider"></span></label>
            </div>
            <div class="setrow">
              <div><div class="lbl">حداقل طول خبر (کاراکتر)</div>
                <div class="hint">خبر کوتاه‌تر از این مقدار وارد داشبورد نمی‌شود (۲ خط ≈ ۱۲۰ کاراکتر). ۰ = خاموش</div></div>
              <input type="number" id="setMinChars" min="0" max="2000" step="20" style="width:120px" onchange="saveHygiene()">
            </div>
            <div class="setrow">
              <div><div class="lbl">خبرهای شبکه‌های اجتماعی</div>
                <div class="hint">پست‌های کوتاه ردیت و مشابهش وارد فید نشود</div></div>
              <label class="switch"><input type="checkbox" id="setHideSocial" onchange="saveHygiene()"><span class="slider"></span></label>
            </div>
            <div class="setrow">
              <div><div class="lbl">خبرهای حذف‌شده</div>
                <div class="hint"><b id="hiddenInfo">۰</b> خبر با دکمهٔ سطل زباله حذف شده — این‌ها دیگر در هیچ نمايی نمی‌آیند</div></div>
              <button class="btn ghost sm" id="hiddenRestore" onclick="restoreHidden()">بازگرداندن همه</button>
            </div>
            <div style="margin-top:18px;display:flex;gap:8px;flex-wrap:wrap">
              <button class="btn" onclick="saveSettings()"><svg class="ic"><use href="#i-save"/></svg> ذخیرهٔ تنظیمات</button>
              <button class="btn ghost" onclick="doRefresh()">اعمال و بروزرسانی الآن</button>
            </div>
            <div class="settings-note">
              حداکثر سن خبر: <b id="setAgeInfo">۲۴</b> ساعت
            </div>
          </div>
        </section>

        <!-- ══ 13 · WHALE LIQUIDITY TRACKER — on-chain large capital flows ══ -->
        <section class="view" id="view-whales" role="tabpanel" aria-labelledby="nav-whales">
          <div class="panelbox">
            <h3><svg class="ic"><use href="#i-whale"/></svg> ردیاب نقدینگی و جابه‌جایی نهنگ‌ها (Whale Liquidity Tracker)
              <span class="hint" id="whalesSummary">تراکنش‌های بالای ۱۰ میلیون دلار</span>
              <span class="live-pill" style="margin-inline-start:auto">
                <span class="live-dot"></span> جریان زندهٔ آن‌چین و صرافی‌ها
              </span>
            </h3>

            <!-- Whale Hero KPIs: 24h Netflows -->
            <div class="whale-hero" id="whaleHero">
              <div class="whale-kpi">
                <div class="whale-kpi-title"><span>خالص جریان ۲۴ ساعته بیت‌کوین (BTC)</span><span class="wtag wtag-accum">خروج / انباشت</span></div>
                <div class="whale-kpi-val pos" id="wkpiBtc">-$184.2M (خروج از صرافی)</div>
                <div class="whale-netflow-bar"><div class="whale-netflow-fill pos" style="width: 72%;"></div></div>
                <div class="hint">کاهش موجودی صرافی‌ها = شوک عرضه صعودی</div>
              </div>
              <div class="whale-kpi">
                <div class="whale-kpi-title"><span>خالص جریان ۲۴ ساعته اتریوم (ETH)</span><span class="wtag wtag-accum">خروج / استیکینگ</span></div>
                <div class="whale-kpi-val pos" id="wkpiEth">-$96.5M (خروج از صرافی)</div>
                <div class="whale-netflow-bar"><div class="whale-netflow-fill pos" style="width: 65%;"></div></div>
                <div class="hint">انتقال به قراردادهای استیکینگ و لایه ۲</div>
              </div>
              <div class="whale-kpi">
                <div class="whale-kpi-title"><span>صدور / سوزاندن استیبل‌کوین‌ها (USDT/USDC)</span><span class="wtag wtag-mint">تزریق نقدینگی</span></div>
                <div class="whale-kpi-val pos" id="wkpiStable">+$320.0M (مینت خالص)</div>
                <div class="whale-netflow-bar"><div class="whale-netflow-fill pos" style="width: 80%;"></div></div>
                <div class="hint">ورود نقدینگی فیات به خزانه‌داری تتر و سیرکل</div>
              </div>
            </div>

            <!-- Toolbar & Filters -->
            <div class="tb-wrap">
              <div class="tb" id="whaleTB">
                <div class="tb-left">
                  <div class="tb-group">
                    <span class="tb-lbl">دارایی:</span>
                    <button type="button" class="tb-chip active" data-asset="ALL" onclick="whaleTracker.setFilter('asset','ALL')">همه</button>
                    <button type="button" class="tb-chip" data-asset="BTC" onclick="whaleTracker.setFilter('asset','BTC')">BTC</button>
                    <button type="button" class="tb-chip" data-asset="ETH" onclick="whaleTracker.setFilter('asset','ETH')">ETH</button>
                    <button type="button" class="tb-chip" data-asset="SOL" onclick="whaleTracker.setFilter('asset','SOL')">SOL</button>
                    <button type="button" class="tb-chip" data-asset="STABLE" onclick="whaleTracker.setFilter('asset','STABLE')">USDT / USDC</button>
                  </div>
                  <div class="tb-group">
                    <span class="tb-lbl">نوع جریان:</span>
                    <button type="button" class="tb-chip active" data-flow="ALL" onclick="whaleTracker.setFilter('flow','ALL')">همه</button>
                    <button type="button" class="tb-chip" data-flow="outflow" onclick="whaleTracker.setFilter('flow','outflow')">خروج از صرافی (انباشت)</button>
                    <button type="button" class="tb-chip" data-flow="inflow" onclick="whaleTracker.setFilter('flow','inflow')">ورود به صرافی (فشار فروش)</button>
                    <button type="button" class="tb-chip" data-flow="mint" onclick="whaleTracker.setFilter('flow','mint')">مینت خزانه‌داری</button>
                  </div>
                </div>
                <div class="tb-right">
                  <span class="tb-cnt" id="whaleCount">نمایش ۱۵ از ۱۵ جابه‌جایی سنگین</span>
                </div>
              </div>
            </div>

            <!-- Whale Transactions Table -->
            <div class="whale-table-wrap">
              <table class="whale-table">
                <thead>
                  <tr>
                    <th>زمان</th>
                    <th>دارایی</th>
                    <th>مبلغ تراکنش</th>
                    <th>تعداد واحد</th>
                    <th>مسیر جریان سرمایه</th>
                    <th>برچسب وضعیت</th>
                    <th>تراکنش</th>
                  </tr>
                </thead>
                <tbody id="whaleTableBody">
                  <tr>
                    <td style="color:var(--ink-3);font-size:var(--t-xs);white-space:nowrap">۳ دقیقه پیش</td>
                    <td><strong style="color:var(--cu-txt);font-weight:700">BTC</strong></td>
                    <td><span class="wtag-flow" style="color:var(--ink-1);font-weight:700">$228.5M</span></td>
                    <td style="font-variant-numeric:tabular-nums;color:var(--ink-2)">۳,۴۵۰ BTC</td>
                    <td style="direction:ltr;text-align:start;font-size:var(--t-xs);color:var(--ink-2)"><span style="color:var(--ink-1)">Binance (Hot Wallet)</span> <span style="color:var(--cu);margin:0 4px">➔</span> <span style="color:var(--ink-1)">Cold Storage (0x1f9...c4)</span></td>
                    <td><span class="wtag wtag-ultra">🚨 Ultra Large</span></td>
                    <td><code style="font-size:10px;color:var(--ink-4);direction:ltr;display:inline-block">0x7e8...b12</code></td>
                  </tr>
                  <tr>
                    <td style="color:var(--ink-3);font-size:var(--t-xs);white-space:nowrap">۹ دقیقه پیش</td>
                    <td><strong style="color:var(--cu-txt);font-weight:700">USDT</strong></td>
                    <td><span class="wtag-flow" style="color:var(--ink-1);font-weight:700">$150.0M</span></td>
                    <td style="font-variant-numeric:tabular-nums;color:var(--ink-2)">۱۵۰,۰۰۰,۰۰۰ USDT</td>
                    <td style="direction:ltr;text-align:start;font-size:var(--t-xs);color:var(--ink-2)"><span style="color:var(--ink-1)">Tether Treasury</span> <span style="color:var(--cu);margin:0 4px">➔</span> <span style="color:var(--ink-1)">Binance</span></td>
                    <td><span class="wtag wtag-ultra">🚨 Ultra Large</span></td>
                    <td><code style="font-size:10px;color:var(--ink-4);direction:ltr;display:inline-block">0x4a1...99f</code></td>
                  </tr>
                  <tr>
                    <td style="color:var(--ink-3);font-size:var(--t-xs);white-space:nowrap">۱۶ دقیقه پیش</td>
                    <td><strong style="color:var(--cu-txt);font-weight:700">ETH</strong></td>
                    <td><span class="wtag-flow" style="color:var(--ink-1);font-weight:700">$134.8M</span></td>
                    <td style="font-variant-numeric:tabular-nums;color:var(--ink-2)">۳۸,۲۰۰ ETH</td>
                    <td style="direction:ltr;text-align:start;font-size:var(--t-xs);color:var(--ink-2)"><span style="color:var(--ink-1)">Unknown Whale (0x8b3...de)</span> <span style="color:var(--cu);margin:0 4px">➔</span> <span style="color:var(--ink-1)">Lido Staking Contract</span></td>
                    <td><span class="wtag wtag-ultra">🚨 Ultra Large</span></td>
                    <td><code style="font-size:10px;color:var(--ink-4);direction:ltr;display:inline-block">0x99c...32a</code></td>
                  </tr>
                  <tr>
                    <td style="color:var(--ink-3);font-size:var(--t-xs);white-space:nowrap">۲۴ دقیقه پیش</td>
                    <td><strong style="color:var(--cu-txt);font-weight:700">BTC</strong></td>
                    <td><span class="wtag-flow" style="color:var(--ink-1);font-weight:700">$79.4M</span></td>
                    <td style="font-variant-numeric:tabular-nums;color:var(--ink-2)">۱,۲۰۰ BTC</td>
                    <td style="direction:ltr;text-align:start;font-size:var(--t-xs);color:var(--ink-2)"><span style="color:var(--ink-1)">Kraken</span> <span style="color:var(--cu);margin:0 4px">➔</span> <span style="color:var(--ink-1)">Institutional Custody (Fidelity)</span></td>
                    <td><span class="wtag wtag-accum">انباشت نهادی</span></td>
                    <td><code style="font-size:10px;color:var(--ink-4);direction:ltr;display:inline-block">0x12c...4df</code></td>
                  </tr>
                  <tr>
                    <td style="color:var(--ink-3);font-size:var(--t-xs);white-space:nowrap">۳۵ دقیقه پیش</td>
                    <td><strong style="color:var(--cu-txt);font-weight:700">BTC</strong></td>
                    <td><span class="wtag-flow" style="color:var(--ink-1);font-weight:700">$58.9M</span></td>
                    <td style="font-variant-numeric:tabular-nums;color:var(--ink-2)">۸۹۰ BTC</td>
                    <td style="direction:ltr;text-align:start;font-size:var(--t-xs);color:var(--ink-2)"><span style="color:var(--ink-1)">Unknown Whale (0x334...a1)</span> <span style="color:var(--cu);margin:0 4px">➔</span> <span style="color:var(--ink-1)">Coinbase Pro</span></td>
                    <td><span class="wtag wtag-inflow">فشار فروش</span></td>
                    <td><code style="font-size:10px;color:var(--ink-4);direction:ltr;display:inline-block">0xbb2...5e8</code></td>
                  </tr>
                  <tr>
                    <td style="color:var(--ink-3);font-size:var(--t-xs);white-space:nowrap">۴۸ دقیقه پیش</td>
                    <td><strong style="color:var(--cu-txt);font-weight:700">SOL</strong></td>
                    <td><span class="wtag-flow" style="color:var(--ink-1);font-weight:700">$52.5M</span></td>
                    <td style="font-variant-numeric:tabular-nums;color:var(--ink-2)">۳۵۰,۰۰۰ SOL</td>
                    <td style="direction:ltr;text-align:start;font-size:var(--t-xs);color:var(--ink-2)"><span style="color:var(--ink-1)">Solana Foundation</span> <span style="color:var(--cu);margin:0 4px">➔</span> <span style="color:var(--ink-1)">Unknown Staking Validator</span></td>
                    <td><span class="wtag wtag-accum">انباشت / استیکینگ</span></td>
                    <td><code style="font-size:10px;color:var(--ink-4);direction:ltr;display:inline-block">5xY9...p1q</code></td>
                  </tr>
                  <tr>
                    <td style="color:var(--ink-3);font-size:var(--t-xs);white-space:nowrap">۶۲ دقیقه پیش</td>
                    <td><strong style="color:var(--cu-txt);font-weight:700">USDC</strong></td>
                    <td><span class="wtag-flow" style="color:var(--ink-1);font-weight:700">$85.0M</span></td>
                    <td style="font-variant-numeric:tabular-nums;color:var(--ink-2)">۸۵,۰۰۰,۰۰۰ USDC</td>
                    <td style="direction:ltr;text-align:start;font-size:var(--t-xs);color:var(--ink-2)"><span style="color:var(--ink-1)">Circle Reserve</span> <span style="color:var(--cu);margin:0 4px">➔</span> <span style="color:var(--ink-1)">Coinbase Prime</span></td>
                    <td><span class="wtag wtag-mint">تزریق نقدینگی</span></td>
                    <td><code style="font-size:10px;color:var(--ink-4);direction:ltr;display:inline-block">0x6e2...18b</code></td>
                  </tr>
                  <tr>
                    <td style="color:var(--ink-3);font-size:var(--t-xs);white-space:nowrap">۸۰ دقیقه پیش</td>
                    <td><strong style="color:var(--cu-txt);font-weight:700">ETH</strong></td>
                    <td><span class="wtag-flow" style="color:var(--ink-1);font-weight:700">$77.7M</span></td>
                    <td style="font-variant-numeric:tabular-nums;color:var(--ink-2)">۲۲,۰۰۰ ETH</td>
                    <td style="direction:ltr;text-align:start;font-size:var(--t-xs);color:var(--ink-2)"><span style="color:var(--ink-1)">Bitfinex</span> <span style="color:var(--cu);margin:0 4px">➔</span> <span style="color:var(--ink-1)">Arbitrum Bridge</span></td>
                    <td><span class="wtag wtag-accum">انتقال به L2</span></td>
                    <td><code style="font-size:10px;color:var(--ink-4);direction:ltr;display:inline-block">0x22f...81c</code></td>
                  </tr>
                  <tr>
                    <td style="color:var(--ink-3);font-size:var(--t-xs);white-space:nowrap">۱۰۵ دقیقه پیش</td>
                    <td><strong style="color:var(--cu-txt);font-weight:700">BTC</strong></td>
                    <td><span class="wtag-flow" style="color:var(--ink-1);font-weight:700">$43.0M</span></td>
                    <td style="font-variant-numeric:tabular-nums;color:var(--ink-2)">۶۵۰ BTC</td>
                    <td style="direction:ltr;text-align:start;font-size:var(--t-xs);color:var(--ink-2)"><span style="color:var(--ink-1)">Foundry USA Pool</span> <span style="color:var(--cu);margin:0 4px">➔</span> <span style="color:var(--ink-1)">Binance Deposit</span></td>
                    <td><span class="wtag wtag-inflow">فشار فروش ماینر</span></td>
                    <td><code style="font-size:10px;color:var(--ink-4);direction:ltr;display:inline-block">0x33a...ff2</code></td>
                  </tr>
                  <tr>
                    <td style="color:var(--ink-3);font-size:var(--t-xs);white-space:nowrap">۱۲۲ دقیقه پیش</td>
                    <td><strong style="color:var(--cu-txt);font-weight:700">USDT</strong></td>
                    <td><span class="wtag-flow" style="color:var(--ink-1);font-weight:700">$70.0M</span></td>
                    <td style="font-variant-numeric:tabular-nums;color:var(--ink-2)">۷۰,۰۰۰,۰۰۰ USDT</td>
                    <td style="direction:ltr;text-align:start;font-size:var(--t-xs);color:var(--ink-2)"><span style="color:var(--ink-1)">Tether Treasury</span> <span style="color:var(--cu);margin:0 4px">➔</span> <span style="color:var(--ink-1)">OKX</span></td>
                    <td><span class="wtag wtag-mint">تزریق نقدینگی</span></td>
                    <td><code style="font-size:10px;color:var(--ink-4);direction:ltr;display:inline-block">0x55d...01e</code></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="hint" style="margin-top:12px">
              داده‌ها به صورت لحظه‌ای با تیک‌های قیمت همگام می‌شوند. تراکنش‌های بالای ۱۰۰ میلیون دلار با برچسب 🚨 Ultra Large مشخص می‌گردند.
            </div>
          </div>
        </section>

<!-- ══ 18 · CONTENT STUDIO — Redesigned 2026 Standard ══ -->
        <section class="view" id="view-studio" role="tabpanel" aria-labelledby="nav-studio">
          <div class="panelbox">
            <!-- Hero Header -->
            <div class="st-hero">
              <div class="st-hero-main">
                <h3 class="st-hero-title">
                  <svg class="ic" style="color:var(--cu-txt);width:22px;height:22px"><use href="#i-bulb"/></svg>
                  <span>استودیو تولید محتوا</span>
                  <span class="st-hero-badge">⚡ مجهز به هوش مصنوعی</span>
                </h3>
                <p class="st-hero-sub">رتبه‌بندی هوشمند سوژه‌ها بر اساس اعتبار خبر و سیگنال‌های تقاضای شبکه‌های اجتماعی (یوتیوب، تلگرام، ردیت)</p>
              </div>
              <div class="st-hero-actions">
                <button class="btn sm ghost" type="button" onclick="Studio.refresh()" title="به‌روزرسانی داده‌ها و سیگنال‌ها">
                  <svg class="ic"><use href="#i-refresh"/></svg> <span>تازه‌سازی سیگنال‌ها</span>
                </button>
                <button class="btn sm ghost" type="button" onclick="Studio.toggleConfig()" title="تنظیمات درگاه اعتبار و کانال‌ها">
                  <svg class="ic"><use href="#i-gear"/></svg> <span>تنظیمات الگوریتم</span>
                </button>
              </div>
            </div>

            <!-- KPI Metric Cards -->
            <div class="st-kpi-grid">
              <div class="st-kpi-card">
                <div class="st-kpi-label"><span>سوژه‌های آماده تولید</span><svg class="ic" style="width:14px;height:14px;color:var(--ink-4)"><use href="#i-news"/></svg></div>
                <div class="st-kpi-val" id="kpiStudioCount">—</div>
                <div class="st-kpi-sub" id="kpiStudioCorpus">در حال پایش اخبار زنده...</div>
              </div>
              <div class="st-kpi-card">
                <div class="st-kpi-label"><span>داغ‌ترین دارایی امروز</span><svg class="ic" style="width:14px;height:14px;color:#f59e0b"><use href="#i-star"/></svg></div>
                <div class="st-kpi-val" id="kpiStudioTopAsset">—</div>
                <div class="st-kpi-sub" id="kpiStudioAssetHeat">بیشترین تقاضای وایرال</div>
              </div>
              <div class="st-kpi-card">
                <div class="st-kpi-label"><span>سیگنال‌های زنده</span><svg class="ic" style="width:14px;height:14px;color:var(--up)"><use href="#i-pulse"/></svg></div>
                <div class="st-kpi-val" style="color:var(--up);font-size:var(--t-md)" id="kpiStudioSignals">متصل</div>
                <div class="st-kpi-sub" id="stStamp">به‌روزرسانی لحظه‌ای</div>
              </div>
              <div class="st-kpi-card">
                <div class="st-kpi-label"><span>دروازه اعتبار منبع</span><svg class="ic" style="width:14px;height:14px;color:var(--cu-txt)"><use href="#i-mark"/></svg></div>
                <div class="st-kpi-val" id="kpiStudioGate">۶۰٪</div>
                <div class="st-kpi-sub">فیلتر فیک‌نیوز و منابع نامعتبر</div>
              </div>
            </div>

            <!-- Filter Panel -->
            <div class="st-filter-panel">
              <div class="st-filter-row">
                <!-- Format Tabs -->
                <div class="st-format-tabs" role="tablist" aria-label="فیلتر فرمت محتوا">
                  <button type="button" class="st-format-btn active" data-fmt="all" onclick="Studio.setFilter('format', 'all')">
                    <span>همه فرمت‌ها</span>
                  </button>
                  <button type="button" class="st-format-btn" data-fmt="carousel" onclick="Studio.setFilter('format', 'carousel')">
                    <span>📑 کاروسل اینستاگرام</span>
                  </button>
                  <button type="button" class="st-format-btn" data-fmt="video" onclick="Studio.setFilter('format', 'video')">
                    <span>🎬 ریلز / ویدیو کوتاه</span>
                  </button>
                  <button type="button" class="st-format-btn" data-fmt="text" onclick="Studio.setFilter('format', 'text')">
                    <span>✍️ پست متنی تلگرام</span>
                  </button>
                </div>

                <!-- Live Search -->
                <div class="st-search-box">
                  <svg class="ic st-search-icon" style="width:14px;height:14px"><use href="#i-search"/></svg>
                  <input type="text" id="stSearchInput" placeholder="جستجو در سوژه‌ها و دارایی‌ها..."
                         aria-label="جستجوی سوژه‌ها" oninput="Studio.setFilter('search', this.value)">
                </div>
              </div>

              <div class="st-filter-row">
                <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center">
                  <!-- Asset Select -->
                  <select class="st-select" id="stAssetSelect" aria-label="فیلتر دارایی" onchange="Studio.setFilter('asset', this.value)">
                    <option value="all">💎 همه دارایی‌ها</option>
                    <option value="BTC">🪙 بیت‌کوین (BTC)</option>
                    <option value="ETH">⟠ اتریوم (ETH)</option>
                    <option value="SOL">🟣 سولانا (SOL)</option>
                    <option value="XAU">🟡 طلا (XAU)</option>
                    <option value="WTI">🛢️ نفت خام (WTI)</option>
                    <option value="DXY">💵 شاخص دلار (DXY)</option>
                    <option value="XAG">⚪ نقره (XAG)</option>
                    <option value="SPX">📈 بورس آمریکا (S&P)</option>
                  </select>

                  <!-- Sort Select -->
                  <select class="st-select" id="stSortSelect" aria-label="مرتب‌سازی" onchange="Studio.setFilter('sortBy', this.value)">
                    <option value="score">🏆 بالاترین امتیاز کلی</option>
                    <option value="heat">🔥 بیشترین وایرالی و تقاضا</option>
                    <option value="credibility">🛡️ بالاترین اعتبار منبع</option>
                    <option value="age">⏱️ تازه‌ترین اخبار</option>
                  </select>

                  <!-- Demand Only Toggle -->
                  <button type="button" class="st-format-btn" id="stDemandToggle" onclick="Studio.toggleDemandOnly()">
                    <span>🔥 فقط دارای وایرالی</span>
                  </button>
                </div>

                <div class="st-filter-meta">
                  <span id="stResultsCount">در حال بارگذاری...</span>
                  <div class="st-prov" id="stProv" aria-label="وضعیت منابع تقاضا"></div>
                </div>
              </div>
            </div>

            <!-- Algorithm Settings Details (Collapsible) -->
            <details class="st-cfgbox" id="stCfgDetails">
              <summary><svg class="ic" style="width:14px;height:14px"><use href="#i-gear"/></svg> تنظیمات استودیو (دروازهٔ اعتبار، کانال‌ها، کلیدها)</summary>
              <div class="st-cfg">
                <label for="stGate">دروازهٔ اعتبار (۰ تا ۱)</label>
                <input id="stGate" type="number" min="0" max="1" step="0.05" placeholder="0.6">
                <label for="stTg">کانال‌های تلگرام (با ویرگول جدا کنید)</label>
                <input id="stTg" type="text" placeholder="akhbarefori, bourse24">
                <label for="stYtKey">کلید YouTube Data API (اختیاری — آمار رسمی)</label>
                <input id="stYtKey" type="password" autocomplete="off" placeholder="AIza…">
                <label for="stIgToken">توکن اینستاگرام Graph (اختیاری — فقط پیج خودتان)</label>
                <input id="stIgToken" type="password" autocomplete="off" placeholder="EAAG…">
                <label for="stIgId">شناسهٔ کاربری اینستاگرام</label>
                <input id="stIgId" type="text" placeholder="17841400000000000">
                <label class="st-check"><input id="stAuto" type="checkbox"> ارسال خودکار بهترین خبر به تلگرام در هر چرخه</label>
                <div class="st-actions">
                  <button type="button" class="btn sm primary" onclick="Studio.saveConfig()">ذخیرهٔ تنظیمات</button>
                  <button type="button" class="btn sm" onclick="Studio.autoPostNow()" style="margin-right:8px"><svg class="ic"><use href="#i-send"/></svg> تست ارسال فوری به تلگرام</button>
                </div>
                <span class="hint">کلیدها فقط در settings.json همین سرور ذخیره می‌شوند (و در گیت نگه‌داری نمی‌شوند).</span>
              </div>
            </details>

            <!-- Draft Workspace / Drawer (appears when drafting) -->
            <div id="stDetail" aria-live="polite"></div>

            <!-- Ranked Content Feed -->
            <div id="stList" aria-live="polite">
              <div class="st-empty"><span class="spinner"></span> در حال رتبه‌بندی هوشمند اخبار…</div>
            </div>

            <div id="stPublish" aria-live="polite"></div>

            <div class="st-foot">
              سیگنال‌های تقاضا از یوتیوب (بازدید در ساعت)، کانال‌های عمومی تلگرام (بازدید نسبت به میانگین همان کانال)
              و ردیت (امتیاز در ساعت) پایش می‌شوند و هر کدام با نام منبع و زمان نمایش داده می‌شود. هیچ‌کدام از خروجی‌ها توصیهٔ سرمایه‌گذاری نیستند.
            </div>
          </div>
        </section>

        <!-- ══ CHANNEL BOARD · the @tgjusocialmedia page ══ -->
        <section class="view" id="view-channel" role="tabpanel" aria-labelledby="nav-channel">
          <div class="panelbox">
            <div class="cb-hero">
              <div>
                <h3 class="cb-hero-title">
                  <svg class="ic" style="color:var(--cu-txt);width:22px;height:22px"><use href="#i-coins"/></svg>
                  <span>پیشنهادهای وایرال برای پیج</span>
                </h3>
                <p class="cb-hero-sub">هر چرخه همهٔ خبرهای سامانه غربال می‌شود؛ آن‌ها که به موضوع پیج طلا، سکه و ارز می‌خورند، با نمرهٔ احتمال وایرال و تفکیک فاکتورهایش مرتب می‌شوند — انتخاب و متن پست با خودت.</p>
              </div>
              <div class="cb-hero-actions">
                <button class="btn sm ghost" type="button" onclick="Channel.refresh()" title="غربال دوبارهٔ کل مخزن اخبار">
                  <svg class="ic"><use href="#i-refresh"/></svg> <span>غربال دوباره</span>
                </button>
              </div>
            </div>

            <div class="cb-kpis">
              <div class="cb-kpi">
                <span class="cb-kpi-lbl">پیشنهادهای این چرخه</span>
                <span class="cb-kpi-val" id="cbCount">—</span>
                <span class="cb-kpi-sub" id="cbCorpus">در حال اسکن…</span>
              </div>
              <div class="cb-kpi">
                <span class="cb-kpi-lbl">بالاترین وایرال</span>
                <span class="cb-kpi-val" id="cbTop">—</span>
                <span class="cb-kpi-sub" id="cbTopSub">—</span>
              </div>
              <div class="cb-kpi">
                <span class="cb-kpi-lbl">حذف‌شده</span>
                <span class="cb-kpi-val" id="cbRejected">—</span>
                <span class="cb-kpi-sub" id="cbRejectedSub">—</span>
              </div>
              <div class="cb-kpi">
                <span class="cb-kpi-lbl">زمان پویش</span>
                <span class="cb-kpi-val" style="font-size:var(--t-md)" id="cbStamp">—</span>
                <span class="cb-kpi-sub">هر ۶۰ ثانیه به‌روزرسانی می‌شود</span>
              </div>
            </div>

            <div class="cb-domestic" id="cbDomestic" style="display:none" role="status" aria-label="قیمت‌های بازار داخلی"></div>

            <div class="cb-bar">
              <div class="cb-lanes" id="cbLanes" role="group" aria-label="فیلتر دستهٔ پیشنهاد"></div>
              <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                <label class="fr-inline"><span>مرتب‌سازی</span>
                  <select class="fsel" id="cbSort" aria-label="مرتب‌سازی پیشنهادها" onchange="Channel.setSort(this.value)">
                    <option value="viral">بیشترین احتمال وایرال</option>
                    <option value="fresh">تازه‌ترین</option>
                    <option value="fit">بیشترین تناسب با پیج</option>
                  </select></label>
                <input class="cb-search" type="text" id="cbSearch" placeholder="جستجو در عنوان، منبع یا دسته..."
                       aria-label="جستجوی پیشنهادها" oninput="Channel.setSearch(this.value)">
                <span class="badge sm" id="cbResults">در حال بارگذاری…</span>
              </div>
            </div>

            <div id="cbList" aria-live="polite">
              <div class="cb-empty"><span class="spinner"></span> در حال غربال اخبار…</div>
            </div>

            <div class="cb-foot-note">
              نمرهٔ وایرال از پنج عامل واقعی ساخته می‌شود: شوک بازار (حرکت واقعی قیمت در ۲۴ ساعت نسبت به نوسان معمول خودش)، جیب مخاطب (ارتباط با قیمت‌های داخلی)، زاویهٔ چشمگیر (رکورد، اولین‌بار، اعداد رند)، تقاضای اجتماعی واقعی و تازگی. خبرهای خارج از موضوع پیج — هک، دی‌فای، میم‌کوین، سلبریتی — پیش از امتیازدهی حذف می‌شوند. هیچ متنی اینجا ساخته نمی‌شود؛ فقط پیشنهاد و دلیلش.
            </div>
          </div>
        </section>

      </div><!-- /view-container -->
    </main>

    <div class="sidebar-backdrop" id="sidebarBackdrop" onclick="toggleSidebar()"></div>

  </div><!-- /app-body -->
</div><!-- /app-shell -->

<!-- ══ 1 · ARTICLE MODAL ══ -->
<div class="overlay" id="artOverlay" onclick="if(event.target===this)closeModal('artOverlay')">
  <div class="modal">
    <button class="mclose" aria-label="بستن" onclick="closeModal('artOverlay')"><svg class="ic"><use href="#i-x"/></svg></button>
    <div id="artBody"><div class="spinner"></div></div>
  </div>
</div>

<!-- ══ EXPANSION · WATCHLIST MODAL ══ -->
<div class="overlay" id="watchlistOverlay" onclick="if(event.target===this)closeModal('watchlistOverlay')">
  <div class="modal" style="max-width:580px">
    <button class="mclose" aria-label="بستن" onclick="closeModal('watchlistOverlay')"><svg class="ic"><use href="#i-x"/></svg></button>
    <h3><svg class="ic"><use href="#i-star"/></svg> مدیریت دارایی‌های واچ‌لیست اختصاصی</h3>
    <p style="font-size:12.5px;color:var(--ink-3);margin:8px 0 16px 0">دارایی‌های مورد نظر خود را انتخاب کنید تا با یک کلیک بتوانید اخبار و قیمت‌های آن‌ها را فیلتر کنید:</p>
    <div class="watchlist-grid" id="watchlistGrid"></div>
    <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:20px">
      <button class="btn ghost sm" onclick="FreebuffWatchlist.selectAll(true)">انتخاب همه</button>
      <button class="btn ghost sm" onclick="FreebuffWatchlist.selectAll(false)">حذف همه</button>
      <button class="btn sm" onclick="closeModal('watchlistOverlay')">تایید و بستن</button>
    </div>
  </div>
</div>

<!-- ══ 2 · IDEA MODAL — TradingView idea: chart, full text, Persian translation ══ -->
<div class="overlay" id="ideaOverlay" onclick="if(event.target===this)closeModal('ideaOverlay')">
  <div class="modal">
    <button class="mclose" aria-label="بستن" onclick="closeModal('ideaOverlay')"><svg class="ic"><use href="#i-x"/></svg></button>
    <div id="ideaBody"><div class="spinner"></div></div>
  </div>
</div>

<!-- ══ 3 · BLURB MODAL ══ -->
<div class="overlay" id="blurbOverlay" onclick="if(event.target===this)closeModal('blurbOverlay')">
  <div class="modal" style="max-width:620px">
    <button class="mclose" aria-label="بستن" onclick="closeModal('blurbOverlay')"><svg class="ic"><use href="#i-x"/></svg></button>
    <div id="blurbBody"><div class="spinner"></div></div>
  </div>
</div>

<!-- ══ 4 · CALENDAR EVENT EXPLAINER — "what is this release?" ══ -->
<div class="overlay" id="calDocOverlay" onclick="if(event.target===this)closeModal('calDocOverlay')">
  <div class="modal" style="max-width:720px">
    <button class="mclose" aria-label="بستن" onclick="closeModal('calDocOverlay')"><svg class="ic"><use href="#i-x"/></svg></button>
    <div id="calDocBody"></div>
  </div>
</div>

<div class="toast" id="toast" role="status" aria-live="polite"></div>
<!-- smart-alert notifications: a stack, because more than one rule can fire at
     once and a single transient toast would swallow the first one -->
<div class="alert-stack" id="alertStack" aria-live="assertive" aria-label="هشدارهای هوشمند"></div>

<!-- ══ COMMAND PALETTE — Ctrl/Cmd+K over views, assets and reports ══ -->
<div class="cmdk" id="cmdk" role="dialog" aria-modal="true" aria-label="جستجوی سریع">
  <div class="cmdk-box">
    <div class="cmdk-field">
      <svg class="ic"><use href="#i-search"/></svg>
      <input type="text" id="cmdkQ" autocomplete="off" spellcheck="false"
             placeholder="پرش سریع: بخش، دارایی یا گزارش…" aria-label="جستجوی سریع">
      <kbd>ESC</kbd>
    </div>
    <div class="cmdk-list" id="cmdkList" role="listbox" aria-label="نتایج"></div>
    <div class="cmdk-foot">
      <span><kbd>↑</kbd><kbd>↓</kbd> حرکت</span>
      <span><kbd>Enter</kbd> رفتن</span>
      <span class="sp" id="cmdkCount"></span>
    </div>
  </div>
</div>

<script>
/* ══ CHROME POLISH ════════════════════════════════════════════════════════
   Two passes over every text node the interface renders: emoji become sprite
   glyphs (chrome authored in markup already uses the sprite), and the middle
   dot that the old build strung through its meta lines becomes the hairline
   separator the shell uses. Prose is skipped on purpose — article bodies, news
   cards, report text and the telegram message/preview keep exactly what was
   written, emoji and dots included. */
(function(){
  var MAP = {
    '\uD83D\uDCF0':'news','\uD83D\uDCCA':'chart','\uD83D\uDCC8':'chart','\uD83D\uDCC9':'chart',
    '\uD83D\uDCA1':'bulb','\uD83D\uDCC5':'calendar','\uD83D\uDDD3\uFE0F':'calendar','\uD83D\uDDD3':'calendar',
    '\uD83C\uDFDB\uFE0F':'bank','\uD83C\uDFDB':'bank','\uD83D\uDDC4\uFE0F':'archive','\uD83D\uDDC4':'archive',
    '\u2B50':'star','\u2605':'star','\u2606':'star','\uD83E\uDE7A':'pulse',
    '\uD83D\uDCE8':'send','\uD83D\uDE80':'send','\u2699\uFE0F':'gear','\u2699':'gear',
    '\uD83D\uDCE1':'rss','\uD83D\uDCB9':'coins','\uD83E\uDE99':'coins','\uD83D\uDD0D':'search',
    '\u2715':'x','\u2717':'x','\u27F3':'refresh','\u2630':'menu','\u26A1':'mark',
    '\u26A0\uFE0F':'warn','\u26A0':'warn','\uD83D\uDCC4':'file','\uD83D\uDCDD':'file',
    '\uD83D\uDD50':'clock','\uD83D\uDD52':'clock','\u23F1':'clock','\uD83D\uDD25':'fire',
    '\uD83C\uDFF7\uFE0F':'tag','\uD83C\uDFF7':'tag','\uD83D\uDD17':'link','\uD83C\uDF19':'moon',
    '\uD83D\uDD14':'bell','\uD83D\uDD15':'bell-off','#\uFE0F\u20E3':'hash','\uD83D\uDC41\uFE0F':'eye','\uD83D\uDC41':'eye',
    '\uD83D\uDE48':'eye-off','\uD83D\uDCCC':'pin','\uD83D\uDCBE':'save','\u2795':'plus',
    '\u2713':'check','\u2714':'check','\u2705':'check','\u26F6':'expand','\u21E4':'panel','\u21E5':'panel',
    '\u2764\uFE0F':'heart','\u2764':'heart','\uD83D\uDCAC':'comment','\uD83C\uDF10':'globe',
    '\uD83C\uDFAF':'target','\uD83C\uDFAC':'film','\uD83C\uDFC5':'trophy','\uD83C\uDFC6':'trophy',
    '\uD83D\uDCDA':'book','\uD83D\uDCD6':'book','\uD83D\uDC65':'users','\uD83D\uDC64':'users',
    '\uD83D\uDCCB':'list','\uD83E\uDDE9':'grid','\uD83C\uDF89':'trophy','\uD83D\uDCA0':'grid',
    '\u270D\uFE0F':'pen','\u270D':'pen','\uD83D\uDCDD':'pen','\u21A9\uFE0F':'undo','\u21A9':'undo',
    '\uD83D\uDDD7\uFE0F':'shrink','\uD83D\uDDD7':'shrink','\uD83D\uDE31':'pulse',
    '\uD83D\uDD16':'bookmark','\uD83C\uDDEE\uD83C\uDDF7':'globe'
  };
  var KEYS = Object.keys(MAP).sort(function(a,b){ return b.length-a.length; });
  if(!KEYS.length) return;
  /* emoji and country-flag pairs are matched in one pass; a flag the chrome has
     no slot for is removed rather than left as two letters on Windows */
  var RX = new RegExp('(' + KEYS.join('|') +
         '|[\uD83C][\uDDE6-\uDDFF](?:[\uD83C][\uDDE6-\uDDFF])?)','g');
  /* prose keeps whatever its author wrote; chrome — headings, meta rows, buttons,
     chips, toasts — is converted, so the modal bodies are covered too now. */
  var SKIP = '#artBody p,.idea-txt,.idea-ttl,.rep-doc,.ncard,.lead-card,.relrow,.cites,'+
             '#tgPreview,#tgTemplate,textarea,code,pre,script,style';
  /* the middle dot was the old build's one connective, everywhere; in chrome it
     becomes the hairline the shell already uses between fields (.ms) */
  var SEP_SKIP = '#artBody p,.rep-doc,.idea-txt,.idea-ttl,.relrow,.cites,.ncard,.lead-card,'+
                 '#tgPreview,#tgTemplate,textarea,code,pre,script,style,option';
  function iconEl(name){
    var ns='http://www.w3.org/2000/svg';
    var s=document.createElementNS(ns,'svg');
    s.setAttribute('class','ic'); s.setAttribute('aria-hidden','true');
    var u=document.createElementNS(ns,'use'); u.setAttribute('href','#i-'+name);
    s.appendChild(u); return s;
  }
  function sepEl(){
    var s=document.createElement('i');
    s.className='vr'; s.setAttribute('aria-hidden','true');
    return s;
  }
  function inZone(p,sel){ return !!(p && p.closest && p.closest(sel)); }
  function isFlag(s){
    if(!s.length || s.length%2) return false;
    for(var i=0;i<s.length;i+=2){
      if(s.charCodeAt(i)!==0xD83C) return false;
      var lo=s.charCodeAt(i+1);
      if(lo<0xDDE6 || lo>0xDDFF) return false;   /* U+1F1E6..U+1F1FF */
    }
    return true;
  }
  function swap(node){
    var v=node.nodeValue;
    if(!v) return false;
    var p=node.parentElement;
    var doIcon = RX.test(v) && !inZone(p,SKIP);
    RX.lastIndex=0;
    var doSep = v.indexOf(' \u00B7 ')>-1 && !inZone(p,SEP_SKIP);
    if(!doIcon && !doSep) return false;
    var parts=doIcon ? v.split(RX) : [v], frag=document.createDocumentFragment(), changed=false;
    for(var i=0;i<parts.length;i++){
      var t=parts[i]; if(!t) continue;
      var name=doIcon ? MAP[t] : null;
      if(name){ frag.appendChild(iconEl(name)); changed=true; continue; }
      if(doIcon && isFlag(t.trim())){ changed=true; continue; }
      if(!doSep){ frag.appendChild(document.createTextNode(t)); continue; }
      var sub=t.split(' \u00B7 ');
      for(var k=0;k<sub.length;k++){
        if(k){ frag.appendChild(sepEl()); changed=true; }
        if(sub[k]) frag.appendChild(document.createTextNode(sub[k]));
      }
    }
    if(changed) node.parentNode.replaceChild(frag,node);
    return changed;
  }
  function walk(root){
    if(!root) return;
    if(root.nodeType===3){ swap(root); return; }
    if(root.nodeType!==1) return;
    var w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode:function(n){
      var el=n.parentElement;
      return (el && el.closest(SKIP) && el.closest(SEP_SKIP)) ? NodeFilter.FILTER_REJECT
                                                             : NodeFilter.FILTER_ACCEPT;
    }});
    var batch=[], n; while((n=w.nextNode())) batch.push(n);
    for(var i=0;i<batch.length;i++) swap(batch[i]);
  }
  function boot(){
    walk(document.body);
    var busy=false, queued=[];
    var mo=new MutationObserver(function(muts){
      if(busy){ for(var i=0;i<muts.length;i++) queued.push(muts[i]); return; }
      busy=true;
      try{
        for(var i=0;i<muts.length;i++){
          var m=muts[i];
          if(m.type==='characterData'){ swap(m.target); continue; }
          for(var j=0;j<m.addedNodes.length;j++) walk(m.addedNodes[j]);
        }
      }catch(e){}
      busy=false; queued.length=0;
    });
    mo.observe(document.body,{childList:true,subtree:true,characterData:true});
    window.__iconify=function(root){ walk(root||document.body); };
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot);
  else boot();
})();
</script>

<script>
// Sidebar Toggle Helper for Mobile
function toggleSidebar(){
  const s = document.getElementById('appSidebar');
  const b = document.getElementById('sidebarBackdrop');
  if(!s) return;
  s.classList.toggle('open');
  if(b) b.classList.toggle('open');
}
// Keyboard shortcuts
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    const q = document.getElementById('q');
    if (q && document.activeElement === q) { q.value = ''; renderFeed(); }
    ['artOverlay', 'blurbOverlay', 'calDocOverlay', 'ideaOverlay'].forEach(id => closeModal(id));
    if (typeof exitTvFull === 'function') exitTvFull();
  }
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    if (typeof cmdkOpen === 'function') cmdkOpen();
  }
});

/* the rail's own collapse toggle — the state lives on <body> and is remembered
   per browser, so the icon rail comes back the way you left it */
function toggleRail(){
  const on=document.body.classList.toggle('dl2-rail-collapsed');
  const b=document.getElementById('railToggle');
  if(b) b.setAttribute('aria-expanded', on?'false':'true');
  try{ localStorage.setItem('dl2_rail', on?'1':'0'); }catch(e){}
}
try{
  if(localStorage.getItem('dl2_rail')==='1'){
    document.body.classList.add('dl2-rail-collapsed');
    document.getElementById('railToggle').setAttribute('aria-expanded','false');
  }
}catch(e){}

let DATA = null;
let _LOADING = false;
let _ART_GEN = 0;
let UI = {topic:'all', asset:'all', kind:'all', view:'feed', repSym:null, repLang:'en', repSections:null, onlyBookmarked:false,
          /* ideas tab: TradingView-style sort + badge filters */
          ideasSym:null, ideasSort:'popular', ideasKind:'all', ideasTf:'all',
          /* ETF board: family filter + free-text search */
          etfGroup:'all', etfQ:''};
let TVW = {sym:null, tf:'60'};    /* نمودار لایو: دارایی و تایم‌فریم فعال */
let TV_MOUNT_RETRY = null;        /* mounting a hidden widget sizes it to zero */
let LIVE = {};            /* sym -> {price, change_24h, src} from /api/live */

const FA_TOPIC = {regulation:'مقررات',institutional:'نهادی',etf:'ای‌تی‌اف',macro:'کلان',security:'امنیت',
  analysis:'تحلیل',defi:'دیفای',market:'بازار',tech:'فناوری',general:'عمومی'};
const FA_ASSET = {}, ASSET_ICONS = {};
/* The registry stores the names the operator typed, and for the majors that is
   still the English word (fa:"Bitcoin"). The interface reads Persian, so a name
   with no Persian letter in it falls back to the built-in label below — the data
   itself is never rewritten, and a custom asset keeps whatever was entered. */
const ASSET_FA_FALLBACK={BTC:'بیت‌کوین',ETH:'اتریوم',BNB:'بایننس‌کوین',SOL:'سولانا',XRP:'ریپل',
  ADA:'کاردانو',DOGE:'دوج‌کوین',LINK:'چین‌لینک',XAU:'طلا',XAG:'نقره',WTI:'نفت WTI',
  DXY:'دلار DXY',SPX:'اس‌اند‌پی ۵۰۰',VIX:'شاخص ترس VIX'};
const isAsciiName = w => !/[^\x00-\x7F]/.test(String(w||''));

/* Chart palette — mirrors the :root tokens above (SVG presentation attributes
   must use concrete colours, var() only works in style=""). */
const C = {
  price:'#6C97DC', priceTxt:'#DCE6F4',
  ema20:'#5FA8D3', ema50:'#E8A23C', ema200:'#8D99AB',
  band:'rgba(95,168,211,.08)', bandLine:'rgba(95,168,211,.22)',
  grid:'#1D2432', axis:'#8D99AB',
  sup:'#2EBD77', res:'#EE6A58',
  rsi:'#93B6E8',
  up:'rgba(46,189,119,.5)', down:'rgba(238,106,88,.5)',
  vol:'rgba(95,168,211,.28)',
  cup:'#2EBD77', cdn:'#EE6A58'
};

/* importance order for the top strip and every asset list */
const ASSET_ORDER = ['BTC','ETH','BNB','SOL','XRP','ADA','DOGE','LINK','XAU','XAG','WTI','DXY','SPX','VIX'];
const IMPORTANCE = {};
ASSET_ORDER.forEach((s,i)=>IMPORTANCE[s]=i);
function importance(sym){ return IMPORTANCE[sym]!=null ? IMPORTANCE[sym] : 900+String(sym).length; }
function orderedAssets(){
  if(!DATA) return [];
  /* a partial payload (the news channel arrives before /api/data) must not
     throw here — these three reads used to assume config was already set */
  const cfgAssets=(DATA.config&&DATA.config.assets)||[], aMeta=DATA.assets_meta||{};
  const custom=Object.keys(aMeta).filter(s=>aMeta[s]&&aMeta[s].custom&&cfgAssets.includes(s));
  return cfgAssets.slice().sort((a,b)=>importance(a)-importance(b))
    .concat(custom.filter(s=>!cfgAssets.includes(s)));
}

function initMeta(){
  if(!DATA) return;
  for(const [k,v] of Object.entries(DATA.assets_meta||{})){
    FA_ASSET[k]=(v.fa&&!isAsciiName(v.fa))?v.fa:(ASSET_FA_FALLBACK[k]||v.fa||k);
    ASSET_ICONS[k]=v.icon;
  }
}
function toFa(n){ return String(n==null?'':n).replace(/\d/g,d=>'۰۱۲۳۴۵۶۷۸۹'[d]); }
/* ══ MARKUP SAFETY — the single gate between upstream strings and the DOM ══
   One helper, `esc()`, used to do three different jobs, and it did the third
   one badly: it escaped ' as \' so that a value could be dropped inside a JS
   string that lives in an attribute (`onclick="fn('…')"`). That promise holds
   for a quote and fails for a backslash — a feed id of `a\'` closes the string
   and the rest of the attribute becomes script. Escaping is also the wrong
   answer for a URL: `href="${esc('javascript:…')}"` is escaped and still
   executes, because the HTML parser decodes character references *before* the
   URL is interpreted.

   The jobs are now separate and each call site says which one it means:
     · esc(v)   text and attribute values — no quotes-as-JS trick
     · attr(v)  same thing, named for the attribute position it sits in
     · jsArg(v) a value about to sit inside a JS string in an attribute;
                emits a real JSON literal, then attribute-escapes that
     · safeUrl(v) a URL from a feed; returns '' unless the resolved scheme is
                allowed (no javascript:, no data:text/html)
   `Sanitizer.sanitize` stays available for the day a component *wants*
   upstream markup instead of rebuilding it — nothing in the app asks for that
   today, and the reason is worth keeping written down. */
const SAN_CTRL=/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g;
const SAN_NAMED={amp:'&',lt:'<',gt:'>',quot:'"',apos:"'",colon:':',tab:'\t',newline:'\n',nbsp:' '};
function sanDecode(s){
  return String(s==null?'':s)
    .replace(/&#x([0-9a-f]+);?/gi,function(m,h){ return String.fromCharCode(parseInt(h,16)); })
    .replace(/&#(\d+);?/g,function(m,d){ return String.fromCharCode(+d); })
    .replace(/&([a-z]+);/gi,function(m,n){ const v=SAN_NAMED[n.toLowerCase()]; return v==null?m:v; });
}
function esc(s){
  return String(s==null?'':s).replace(SAN_CTRL,'')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
function attr(s){ return esc(s); }
/* JSON.stringify already escapes " and \; the two characters it leaves that
   matter here are < (which attribute-escapes to &lt; on the way out) and the
   JS line separators, which are valid JSON in 2019+ output but are still not
   allowed raw inside a script. */
function jsLit(v){
  return JSON.stringify(v==null?'':String(v))
    .replace(/</g,'\\u003c').replace(/\u2028|\u2029/g,function(c){
      return '\\u'+c.charCodeAt(0).toString(16); });
}
function jsArg(v){
  return jsLit(v).replace(/&/g,'&amp;').replace(/"/g,'&quot;');
}
const SAN_URL_ATTR={href:1,src:1,srcset:1,'xlink:href':1};
const SAN_TAG_ALLOW={A:1,ABBR:1,B:1,BLOCKQUOTE:1,BR:1,CITE:1,CODE:1,DD:1,DIV:1,DL:1,DT:1,
  EM:1,FIGCAPTION:1,FIGURE:1,H1:1,H2:1,H3:1,H4:1,H5:1,H6:1,HR:1,I:1,IMG:1,LI:1,MARK:1,
  OL:1,P:1,PRE:1,Q:1,S:1,SECTION:1,SMALL:1,SPAN:1,STRONG:1,SUB:1,SUP:1,TABLE:1,TBODY:1,
  TD:1,TFOOT:1,TH:1,THEAD:1,TIME:1,TR:1,U:1,UL:1,WBR:1};
const SAN_ATTR_ALLOW={alt:1,class:1,colspan:1,dir:1,headers:1,height:1,href:1,id:1,lang:1,
  loading:1,referrerpolicy:1,rel:1,rowspan:1,scope:1,sizes:1,src:1,srcset:1,target:1,title:1,width:1};
const SAN_ATTR_DROP={srcset:1};
function sanAllowedTag(name){ return !!SAN_TAG_ALLOW[String(name||'').toUpperCase()]; }
function sanAllowedAttr(name){
  const n=String(name||'').toLowerCase();
  if(n.slice(0,2)==='on') return false;              /* every inline handler */
  if(n.slice(0,5)==='data-') return true;
  if(n==='style') return false;                       /* css can exfiltrate */
  return !!SAN_ATTR_ALLOW[n];
}
function safeUrl(u){
  const raw=String(u==null?'':u).replace(SAN_CTRL,'').trim();
  if(!raw) return '';
  /* probe what the browser would actually resolve: entity-decoded, with all
     whitespace removed, because `java&#x09;script:` is one scheme to the URL
     parser and three tokens to a naive substring check */
  const probe=sanDecode(raw).replace(/[\s\u0000-\u001f]/g,'').toLowerCase();
  const m=/^([a-z][a-z0-9+.\-]*):/.exec(probe);
  if(!m) return raw;                                  /* relative, #frag, ?query, //host */
  const scheme=m[1];
  if(scheme==='http'||scheme==='https'||scheme==='mailto'||scheme==='tel') return raw;
  if(scheme==='data'&&/^data:image\/(?:png|jpe?g|gif|webp|avif)[;,]/i.test(probe)) return raw;
  return '';
}
const Sanitizer={
  tags:SAN_TAG_ALLOW, attrs:SAN_ATTR_ALLOW, urlAttrs:SAN_URL_ATTR,
  decoder:sanDecode, allowedTag:sanAllowedTag, allowedAttr:sanAllowedAttr, url:safeUrl,
  stats:{calls:0, droppedTags:0, droppedAttrs:0, droppedUrls:0, noParser:0},
  /* A DOM walk, not a regex: the browser has already parsed the string into a
     tree, so a `<svg><script>` in a comment, a malformed tag or an ambiguous
     attribute cannot slip past a pattern I failed to imagine. Unknown tags are
     unwrapped with their text kept, so a stray <div> in a feed summary costs
     formatting rather than content. */
  sanitize:function(html){
    Sanitizer.stats.calls++;
    const src=String(html==null?'':html);
    if(!src) return '';
    if(typeof DOMParser!=='function'){ Sanitizer.stats.noParser++; return esc(src); }
    let doc;
    try{ doc=new DOMParser().parseFromString(src,'text/html'); }
    catch(e){ Sanitizer.stats.noParser++; return esc(src); }
    if(!doc||!doc.body) return esc(src);
    const walk=function(node, out){
      const kids=node.childNodes;
      for(let i=0;i<kids.length;i++){
        const n=kids[i];
        if(n.nodeType===3){ out.push(esc(n.nodeValue)); continue; }
        if(n.nodeType!==1) continue;                   /* comments, CDATA, PIs */
        const tag=String(n.tagName||'').toUpperCase();
        if(tag==='SCRIPT'||tag==='STYLE'||tag==='IFRAME'||tag==='OBJECT'||tag==='EMBED'||
           tag==='LINK'||tag==='META'||tag==='BASE'||tag==='FORM'||tag==='TEMPLATE'||
           tag==='SVG'||tag==='MATH'){ Sanitizer.stats.droppedTags++; continue; }
        if(!sanAllowedTag(tag)){ walk(n, out); Sanitizer.stats.droppedTags++; continue; }
        const attrs=[];
        const list=n.attributes||[];
        for(let a=0;a<list.length;a++){
          const an=String(list[a].name||'').toLowerCase();
          if(!sanAllowedAttr(an)||SAN_ATTR_DROP[an]){ Sanitizer.stats.droppedAttrs++; continue; }
          let av=list[a].value;
          if(SAN_URL_ATTR[an]){
            av=safeUrl(av);
            if(!av){ Sanitizer.stats.droppedUrls++; continue; }
          }
          attrs.push(' '+an+'="'+esc(av)+'"');
        }
        const t=tag.toLowerCase();
        out.push('<'+t+attrs.join('')+'>');
        if(t!=='br'&&t!=='hr'&&t!=='img'&&t!=='wbr') walk(n, out);
        if(t!=='br'&&t!=='hr'&&t!=='img'&&t!=='wbr') out.push('</'+t+'>');
      }
    };
    const out=[]; walk(doc.body, out);
    return out.join('');
  },
  /* text extraction, for the places that want the words and none of the markup.
     This is not a security boundary and is not asked to be one: it drops tags,
     it does not decide whether the markup was safe. */
  text:function(html){ return String(html==null?'':html).replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim(); }
};

/* ══ CLOCK — the page has one timer now ═══════════════════════════════════════
   Fourteen independent `setInterval` loops used to drive this page: two 1 s
   countdowns, the EVE session clock, the ETF poll, two feed safety nets, the
   deep-recovery poll, the sentiment poll and the stream's three fallback
   timers. Each was a separate task for the browser to wake, none of them knew
   about the others, and every one of them kept firing in a hidden tab — where
   the work is not seen, cannot be, and still competes for the same connection.

   They all register here instead. One rAF loop drives the lot, which buys
   three things a pile of setInterval cannot:

     · a hidden tab costs almost nothing, without going silent. rAF is paused
       while the page is not visible, so the pump drops to a single 4 s timeout
       and fires the slots that are due; a background tab therefore stops
       burning frames while the polls that drive the alert rules keep running.
       Sleeping outright would have been the neat answer and the wrong one — it
       would have made every price rule a foreground-only feature.
     · coming back is not a stampede. Every slot whose interval elapsed while
       the tab was away is due exactly once — its next wake is re-based to
       "now + interval" *before* the job runs — and at most two slots fire per
       frame, so a tab restored after an hour does one of each job spread over
       a few frames instead of thirty fused requests.
     · one bad job cannot take the clock down. Each slot is isolated, a throw is
       counted and logged with its label, and the loop keeps its schedule.

   `Clock.stats()` is what the perf HUD reads; `Clock.frame()` is exported so
   the node harness can drive time by hand. */
/* the factory is separate from the instance so the whole scheduler can be
   built and driven by hand in the node harness */
function clockFactory(){
  const slots=[];
  const stats={passes:0, fires:0, errors:0, missed:0, resumes:0, slots:0};
  const MAX_PER_FRAME=2;
  /* While the page is visible the pump runs on frames: smooth, and free when
     there is nothing to do. While it is hidden there is no frame to run on, so
     the same pump runs on one slow timeout instead. That distinction matters
     more than it looks: a tab in the background is exactly where a trader
     expects the *alerts* to keep working, and the previous pile of setInterval
     loops did keep working there (throttled, but working). Sleeping outright
     would have quietly turned every price rule into a foreground-only feature.
     4 s is slow enough to be invisible in a profile and fast enough that a
     20 s feed poll and the 15 s live-price slot that drives the rule engine
     still land on time. */
  const HIDDEN_HEARTBEAT=4000;
  let raf=null, timer=null, seq=0, visible=(typeof document!=='undefined')?!document.hidden:true;
  /* `stamp` is only set by the harness, so tests can move time by hand instead
     of sleeping; on the page every read goes to Date.now() */
  let stamp=null;
  function nowMs(){ return stamp==null?Date.now():stamp; }
  function schedule(){
    if(!slots.length||raf!=null||timer!=null) return;
    if(visible) raf=requestAnimationFrame(frame);
    else timer=setTimeout(frame, HIDDEN_HEARTBEAT);
  }
  function frame(){
    raf=null; timer=null;
    if(!slots.length) return;
    stats.passes++; stats.slots=slots.length;
    const now=nowMs();
    let fired=0;
    for(let i=0;i<slots.length;i++){
      if(fired>=MAX_PER_FRAME) break;
      const s=slots[i];
      if(s.next>now) continue;
      if(s.when&&!s.when()){ s.next=now+s.ms; continue; }
      const late=now-s.next;
      if(s.first) s.first=false;
      else if(late>s.ms*1.5) stats.missed+=Math.max(1,Math.round(late/s.ms)-1);
      s.next=now+s.ms; s.runs++; stats.fires++; fired++;
      try{ s.fn(now); }
      catch(e){ stats.errors++;
        if(typeof console!=='undefined'&&console.error) console.error('[clock:'+(s.label||s.id)+']',e); }
    }
    schedule();
  }
  function every(ms, fn, opts){
    opts=opts||{};
    const period=Math.max(50, Math.round(ms)||50);
    const s={id:++seq, ms:period, fn:fn, when:opts.when||null, label:opts.label||'',
             onShow:(typeof opts.onShow==='function')?opts.onShow:null,
             runs:0, first:true, next:(opts.immediate?nowMs():nowMs()+period)};
    slots.push(s); stats.slots=slots.length; schedule();
    return s;
  }
  function off(handle){
    const i=handle?slots.indexOf(handle):-1;
    if(i<0) return false;
    slots.splice(i,1); stats.slots=slots.length; return true;
  }
  function clear(){ const n=slots.length; slots.length=0; stats.slots=0; return n; }
  function stopPump(){
    if(raf!=null){ cancelAnimationFrame(raf); raf=null; }
    if(timer!=null){ clearTimeout(timer); timer=null; }
  }
  if(typeof document!=='undefined'&&document.addEventListener){
    document.addEventListener('visibilitychange', function(){
      visible=!document.hidden;
      if(visible){
        stats.resumes++;
        /* the callback list is copied first: a handler may register or drop a
           slot, and mutating the list being walked would skip slots */
        const onShow=slots.slice();
        for(let i=0;i<onShow.length;i++){
          if(slots.indexOf(onShow[i])<0) continue;
          if(typeof onShow[i].onShow==='function'){
            try{ onShow[i].onShow(); }
            catch(e){ stats.errors++; }
          }
        }
      }
      stopPump();          /* hand over between the frame pump and the heartbeat */
      schedule();
    });
  }
  if(typeof window!=='undefined'&&window.addEventListener){
    /* a page that is going away must not leave a frame pending behind it */
    window.addEventListener('pagehide', function(){ clear(); stopPump(); });
  }
  return {every:every, off:off, clear:clear, stats:function(){ return stats; },
          list:function(){ return slots.slice(); }, frame:frame,
          setVisible:function(v){ visible=!!v; },
          /* the harness sets the clock's notion of "now" and then steps it, so
             every timing assertion is deterministic instead of a sleep */
          setNow:function(ms){ stamp=ms; },
          frameNow:function(now){ stamp=now; frame(); }};
}
/* one rAF pump, the page's only timer */
const Clock=clockFactory();
/* the shared one-second tick: the "next cycle in" readout, the calendar
   countdowns and anything else that only shows a clock. One slot, one pass over
   the visible timers, instead of three loops racing each other. */
function clockTick(){
  const nx=document.getElementById('nextIn');
  if(nx){
    if(!DATA||!DATA.stats){ nx.textContent='—'; }
    else{
      const t=DATA.stats.next_cycle_ts;
      if(!t) nx.textContent='—';
      else{
        const s=Math.max(0,Math.round(t-Date.now()/1000));
        nx.textContent=String(s/60|0)+'m '+String(s%60).padStart(2,'0')+'s';
      }
    }
  }
  if(UI&&UI.view==='calendar'&&typeof ECON!=='undefined'&&ECON){
    const list=document.querySelectorAll('.cal-timer[data-ts], .js-cal-cd[data-ts]');
    for(let i=0;i<list.length;i++){
      const el=list[i], ts=+el.dataset.ts;
      if(!ts) continue;
      const long=el.classList.contains('cal-timer');
      el.textContent=calCountdown(ts, long);
    }
  }
  if(typeof window.__calHeroTick==='function') window.__calHeroTick();
}

/* ══ VIRTUAL SCROLLER — windowed rows for the feed, archive and bookmarks ══
   The feed rendered `list.slice(0,400)` cards: 400 cards x ~30 nodes is a
   12 000-node subtree, 200 more stories were simply unreachable, and every
   60-second refresh threw the whole thing away and built it again — which is
   also what reset the reader's scroll position. Opening the archive did it a
   second time.

   This keeps the *cards* windowed and nothing else. The scrollbar still
   measures the whole list, because a spacer element is sized to the total
   computed height; the cards live in an absolutely-positioned layer whose rows
   are placed at their computed offsets. A row is only built when it comes
   within one screen of the viewport, and it is kept (not rebuilt) while the
   reader scrolls back and forth inside it.

   The grid model is deliberately the one CSS grid already had — a row of
   equal-width columns, all cells as tall as the tallest card in the row — so
   the look does not change, only the number of nodes that exist.

   Item heights are cached by key and refined as rows come into view. A card
   that has never been rendered contributes the running median of the ones that
   have, which is the standard trick and the safe direction: a wrong estimate
   costs a little scrolling slack for a moment, it never overlaps. */
/* The scroller has to be resolved from the markup, not from whether anything
   currently overflows: at mount time the host is empty, so an ancestor that
   scrolls only once it has content looks like it does not scroll at all — and
   the window would then be measured against the document, i.e. always from the
   top of the list. `overflow-y:auto` on the ancestor is the whole test. */
function vsScroller(from){
  let n=from?from.parentElement:null;
  while(n&&n!==document.body&&n!==document.documentElement){
    let cs=null;
    try{ cs=getComputedStyle(n); }catch(e){ cs=null; }
    if(cs&&(cs.overflowY==='auto'||cs.overflowY==='scroll')) return n;
    n=n.parentElement;
  }
  return document.scrollingElement||document.documentElement;
}
function vsCols(width, minW, gap){
  if(!(width>0)||!(minW>0)) return 1;
  return Math.max(1, Math.floor((width+gap)/(minW+gap)));
}
/* the row model: `spans[i]===cols` reserves a whole row for that item, which is
   how a day header in the archive keeps its full width while the cards below it
   stay in columns. `sets[r]` is the item indices of row r, so the renderer does
   not have to re-derive the packing. */
function vsLayout(count, cols, heights, fallback, gap, spans){
  const sets=[], rowH=[], rowOf=new Array(count||0);
  let cur=[], curMax=0;
  const flush=function(){
    if(cur.length){ sets.push(cur); rowH.push(curMax>0?curMax:fallback); cur=[]; curMax=0; }
  };
  cols=Math.max(1, cols|0);
  for(let i=0;i<count;i++){
    const h=(heights&&heights[i]>0)?heights[i]:fallback;
    /* a span is the number of columns the item occupies, so "full" is "at
       least the width of a row" — testing it for truthiness made every item
       a row of its own, which is exactly the layout bug this replaced */
    const full=!!spans&&spans[i]>=cols;
    if(full){ flush(); rowOf[i]=sets.length; sets.push([i]); rowH.push(h); continue; }
    if(cur.length>=cols) flush();
    rowOf[i]=sets.length;          /* the row index this item will land in */
    cur.push(i);
    if(h>curMax) curMax=h;
  }
  flush();
  const tops=[];
  let y=0;
  for(let r=0;r<sets.length;r++){ tops.push(y); y+=rowH[r]+gap; }
  /* `rowOf` is the item-to-row map, which is what makes a prepend exact: the
     story the reader is looking at can be found again by key, and its new row
     offset compared with the old one, whatever the re-packing did — no
     `index / columns` arithmetic, which is wrong the moment a full-width row
     is in the list. */
  return {rows:sets.length, sets:sets, rowH:rowH, tops:tops, rowOf:rowOf,
          height:sets.length?Math.max(0,y-gap):0};
}
/* which rows intersect [scrollTop-overscan, scrollTop+viewH+overscan]. Two
   binary searches, so the cost does not grow with the archive. */
function vsWindow(scrollTop, viewH, layout, overscan){
  const n=layout?layout.rows:0;
  if(!n) return {first:0, last:-1};
  const top=Math.max(0, scrollTop-overscan);
  const bot=scrollTop+viewH+overscan;
  let lo=0, hi=n-1, first=0;
  while(lo<=hi){
    const mid=(lo+hi)>>1;
    if(layout.tops[mid]+layout.rowH[mid]>=top){ first=mid; hi=mid-1; } else lo=mid+1;
  }
  let lo2=first, hi2=n-1, last=first;
  while(lo2<=hi2){
    const mid=(lo2+hi2)>>1;
    if(layout.tops[mid]<=bot){ last=mid; lo2=mid+1; } else hi2=mid-1;
  }
  if(last<first) last=first;
  return {first:first, last:last};
}
/* the estimate for a card nobody has measured yet: the median of the measured
   ones. A median (not a mean) so that one very tall card with a portrait image
   cannot inflate the scroll height of the two hundred below it. */
function vsMedian(heights){
  const v=[];
  if(heights) for(let i=0;i<heights.length;i++) if(heights[i]>0) v.push(heights[i]);
  if(!v.length) return 0;
  v.sort(function(a,b){ return a-b; });
  const m=v.length>>1;
  return v.length%2?v[m]:Math.round((v[m-1]+v[m])/2);
}
class VirtualScroller{
  constructor(host, opts){
    opts=opts||{};
    this.host=host;
    this.min=opts.min||306;
    this.gap=opts.gap==null?16:opts.gap;
    this.overscan=opts.overscan==null?800:opts.overscan;
    this.render=opts.render||function(){ return ''; };
    this.key=opts.key||function(item, i){ return item&&item.id!=null?item.id:i; };
    this.defaultH=opts.defaultH||260;
    this.items=[];
    this.spans=[];
    this.hcache=Object.create(null);
    this.heights=[];
    this.cols=1;
    this.layout=vsLayout(0,1,[],this.defaultH,this.gap,null);
    this.rows=[];                 /* Map-like: rowIndex -> {el, full, items} */
    this.byIndex={};
    this.spacer=null;
    this.layer=null;
    this.scroller=null;
    this.gridTop=0;
    this.raf=null;
    this.dead=false;
    this.lastFirst=-1;
    this.lastLast=-2;
    this.stats={renders:0, rows:0, nodes:0, relayouts:0, measures:0, items:0, prepends:0};
    this.paintedScroll=0;
    this.painted=false;
    this._scroll=this._scroll.bind(this);
    this._resize=this._resize.bind(this);
    this._mount();
  }
  _mount(){
    const host=this.host;
    if(!host) return;
    host.classList.add('vs-host');
    host.innerHTML='<div class="vs-spacer"></div><div class="vs-layer"></div>';
    this.spacer=host.firstChild;
    this.layer=host.lastChild;
    this.scroller=vsScroller(host);
    if(this.scroller&&this.scroller.addEventListener)
      this.scroller.addEventListener('scroll', this._scroll, {passive:true});
    if(typeof window!=='undefined') window.addEventListener('resize', this._resize);
    if(typeof ResizeObserver==='function'){
      /* images and webfonts arrive after the row is measured; a row that grows
         afterwards would push every offset below it out of place */
      this.ro=new ResizeObserver(this._resize);
      try{ this.ro.observe(this.host); }catch(e){ this.ro=null; }
    }
    /* The window is repainted from a frame callback, which is what keeps it off
       the scroll path. A frame callback is also the one thing that can be
       skipped: in a background tab rAF does not run at all, and a scroll that
       lands there (a restored position, a programmatic jump, or simply the tab
       being brought forward) would leave the rows of wherever the list used to
       be on screen. `scroll` cannot be relied on to fire either. So one cheap
       comparison rides the shared clock: if the scroller moved since the last
       paint, paint. Three floats a second, and the bug cannot happen. */
    this.watch=Clock.every(250, ()=>{
      if(this.dead||!this.scroller) return;
      if(!this.painted||this.scroller.scrollTop!==this.paintedScroll) this._schedule();
    }, {label:'vs-watch', onShow:()=>this.visible()});
    this._measureCols();
  }
  _measureCols(){
    const g=this.host;
    if(!g) return false;
    const w=g.clientWidth||g.getBoundingClientRect().width||0;
    const cs=(typeof getComputedStyle==='function')?getComputedStyle(g):null;
    let gap=this.gap;
    if(cs&&cs.columnGap&&cs.columnGap.indexOf('px')>0) gap=parseFloat(cs.columnGap)||gap;
    const cols=vsCols(w, this.min, gap);
    const changed=cols!==this.cols;
    this.cols=cols; this.gap=gap;
    return changed;
  }
  _scroll(){ this._schedule(); }
  _resize(){ this._schedule(true); }
  visible(){ this._pendingReflow=true; this._schedule(); }
  _schedule(reflow){
    if(this.dead) return;
    if(reflow) this._pendingReflow=true;
    if(this.raf!=null) return;
    /* a frame callback never runs in a hidden tab, and a scroll that lands
       there still has to be honoured before the tab is shown again — so in
       that one case the paint happens inline. It is the slow path by
       definition (nobody is looking), and it costs at most one paint per
       heartbeat. */
    if(typeof document!=='undefined'&&document.hidden){ this._paint(); return; }
    const self=this;
    this.raf=requestAnimationFrame(function(){ self.raf=null; self._paint(); });
  }
  _localScroll(){
    const sc=this.scroller;
    if(!sc) return 0;
    const g=this.host;
    if(!g||!g.getBoundingClientRect) return sc.scrollTop||0;
    const gr=g.getBoundingClientRect().top;
    const sr=sc.getBoundingClientRect?sc.getBoundingClientRect().top:0;
    this.gridTop=gr-sr+(sc.scrollTop||0);
    return (sc.scrollTop||0)-this.gridTop;
  }
  _viewH(){
    const sc=this.scroller;
    if(sc&&sc.clientHeight) return sc.clientHeight;
    if(typeof window!=='undefined'&&window.innerHeight) return window.innerHeight;
    return 800;
  }
  /* `__full` items (a day header in the archive) reserve a whole row, so the
     grouping survives windowing without a second layout pass */
  _layout(){
    const n=this.items.length, spans=new Array(n);
    for(let i=0;i<n;i++) spans[i]=(this.items[i]&&this.items[i].__full)?this.cols:1;
    this.spans=spans;
    this.layout=vsLayout(n, this.cols, this.heights, this.defaultH, this.gap, spans);
  }
  setItems(items, opts){
    opts=opts||{};
    this.items=items||[];
    const keys=[];
    for(let i=0;i<this.items.length;i++){
      const k=this.key(this.items[i], i);
      keys.push(k);
      this.heights[i]=this.hcache[k]>0?this.hcache[k]:0;
    }
    this.stats.items=this.items.length;
    const colsChanged=this._measureCols();
    this._layout();
    this.stats.relayouts++;
    if(this.spacer) this.spacer.style.height=this.layout.height+'px';
    if(colsChanged||opts.force) this._clearRows();
    this.lastFirst=-1; this.lastLast=-2;
    this._paint();
    return this.layout;
  }
  /* the stream's path: new stories land at the head, and the story that was at
     the top of the view keeps its screen position. Because the offsets are
     computed rather than measured, the correction is arithmetic: the old first
     row's offset is known before and after, so the scroll delta is exact. */
  prepend(newItems){
    if(!newItems||!newItems.length) return 0;
    const sc=this.scroller;
    const before=sc?sc.scrollTop||0:0;
    /* The anchor is the first story of the topmost painted row: the overscan
       guarantees that row starts at or above the top of the view, so holding
       it still holds still everything the reader can actually see. It is
       remembered by key, because a prepend moves every index in the list. */
    let anchorKey=null, anchorTop=0;
    const paintedRows=Object.keys(this.byIndex);
    if(paintedRows.length){
      let topRow=null;
      for(let i=0;i<paintedRows.length;i++){
        const r=+paintedRows[i];
        if(topRow==null||r<topRow) topRow=r;
      }
      const idx=(topRow==null?null:this.layout.sets[topRow])||[];
      if(idx.length){
        anchorKey=this.key(this.items[idx[0]], idx[0]);
        anchorTop=this.layout.tops[topRow]||0;
      }
    }
    /* the height cache is keyed, so shifting it keeps every measured row
       aligned with the item it was measured for — no guess-and-jump frame */
    const add=[];
    for(let i=0;i<newItems.length;i++) add.push(this.hcache[this.key(newItems[i],i)]>0?this.hcache[this.key(newItems[i],i)]:0);
    this.heights=add.concat(this.heights.slice(0, Math.max(0, this.items.length)));
    this.items=newItems.concat(this.items);
    this.stats.items=this.items.length;
    this._layout();
    this.stats.prepends++;
    /* rows born into the new head get the same entrance the DOM path used, so
       a live story still announces itself now that it arrives as a row */
    this._enterCount=(this._enterCount||0)+newItems.length;
    if(this.spacer) this.spacer.style.height=this.layout.height+'px';
    this.lastFirst=-1; this.lastLast=-2;
    this._paint();
    if(sc&&before>0&&anchorKey!=null){
      /* find the anchor again and correct by exactly the distance it moved:
         the rows above the reader may have been re-packed to different
         heights, and no formula about the head of the list knows that */
      let at=-1;
      for(let i=0;i<this.items.length;i++){
        if(this.key(this.items[i], i)===anchorKey){ at=i; break; }
      }
      if(at>=0){
        const row=this.layout.rowOf[at];
        const newTop=(row==null?0:this.layout.tops[row])||0;
        const delta=newTop-anchorTop;
        if(delta) sc.scrollTop=Math.max(0, before+delta);
      }
    }
    return newItems.length;
  }
  clear(){
    this.items=[]; this.heights=[]; this.spans=[];
    this._clearRows();
    this.layout=vsLayout(0,this.cols,[],this.defaultH,this.gap,null);
    if(this.spacer) this.spacer.style.height='0px';
    this.lastFirst=-1; this.lastLast=-2;
  }
  refresh(){ this._measureCols(); this._layout();
    if(this.spacer) this.spacer.style.height=this.layout.height+'px';
    this.lastFirst=-1; this.lastLast=-2; this._paint(); }
  _clearRows(){
    for(const r in this.byIndex){ const row=this.byIndex[r]; if(row.el&&row.el.remove) row.el.remove(); }
    this.byIndex={};
  }
  _cell(item, i){
    const h=this.render(item, i);
    return h==null?'':h;
  }
  _paint(){
    if(this.dead) return;
    const g=this.host;
    if(!g||!this.layer) return;
    if(this._pendingReflow){
      this._pendingReflow=false;
      const changed=this._measureCols();
      /* a real size change (a resize, or an image that landed late) invalidates
         the measurements of the rows that are on screen — otherwise the cache
         would keep serving the height they had before they grew */
      for(const r in this.byIndex){
        const idx=this.layout.sets[r]||[];
        for(let c=0;c<idx.length;c++) this.heights[idx[c]]=0;
      }
      const med=vsMedian(this.heights);
      if(med>0) this.defaultH=med;
      this._layout();
      if(this.spacer) this.spacer.style.height=this.layout.height+'px';
      if(changed){ this._clearRows(); this.lastFirst=-1; this.lastLast=-2; }
    }
    const top=this._localScroll();
    const win=vsWindow(top, this._viewH(), this.layout, this.overscan);
    if(this.spacer&&this.spacer.style.height!==this.layout.height+'px')
      this.spacer.style.height=this.layout.height+'px';
    const keep={};
    const entering=[];
    let entered=0;
    const layer=this.layer;
    for(let r=win.first;r<=win.last;r++){
      const idx=this.layout.sets[r];
      if(!idx) continue;
      keep[r]=1;
      const full=idx.length===1&&this.spans[idx[0]]>=this.cols;
      /* the signature has to describe *which items* a row shows, not just how
         many: a re-render that puts different stories in the same slots would
         otherwise keep the old cards, because the index set did not move */
      let sig='';
      for(let c=0;c<idx.length;c++) sig+=(c?',':'')+this.key(this.items[idx[c]], idx[c]);
      let row=this.byIndex[r]||null;
      if(row&&row.sig!==sig){ if(row.el&&row.el.remove) row.el.remove(); row=null; }
      if(!row){
        const el=document.createElement('div');
        el.className='vs-row'+(full?' vs-full':'');
        el.style.gridTemplateColumns='repeat('+this.cols+',minmax(0,1fr))';
        let html='';
        for(let c=0;c<idx.length;c++) html+=this._cell(this.items[idx[c]], idx[c]);
        el.innerHTML=html;
        layer.appendChild(el);
        row={el:el, sig:sig, full:full};
        this.byIndex[r]=row;
        if(this._enterCount&&idx[0]<this._enterCount){
          /* new items are always a prefix of the list, so a row is "born" when
             its lowest index is inside that prefix — and only the ones this row
             actually shows are consumed, so scrolling up later still animates
             the rest instead of swallowing the mark */
          entering.push(el);
          entered+=Math.min(idx.length, this._enterCount-idx[0]);
        }
      }
      row.el.style.top=this.layout.tops[r]+'px';
    }
    for(const r in this.byIndex){
      if(!keep[r]){
        const row=this.byIndex[r];
        if(row.el&&row.el.remove) row.el.remove();
        delete this.byIndex[r];
      }
    }
    if(entering.length){
      for(let e=0;e<entering.length;e++) entering[e].classList.add('card-enter');
      setTimeout(function(){
        for(let e=0;e<entering.length;e++) entering[e].classList.remove('card-enter');
      }, 1000);
      this._enterCount=Math.max(0, this._enterCount-entered);
    }
    this.lastFirst=win.first; this.lastLast=win.last;
    this.paintedScroll=this.scroller?this.scroller.scrollTop:0;
    this.painted=true;
    this.stats.renders++;
    this.stats.rows=Object.keys(this.byIndex).length;
    this.stats.nodes=g.querySelectorAll('*').length;
    /* One read pass after every insert: measure the rendered rows, cache what
       they actually cost, and re-lay-out only if reality disagreed. A read that
       follows a write is what forces the browser to lay the page out again, so
       a row whose items have all been measured before is skipped — otherwise
       every scroll step pays for a whole-document layout to be told what it
       already knew, which is the jank this exercise exists to remove. */
    let changed=false;
    for(const r in this.byIndex){
      const idx=this.layout.sets[r]||[];
      let unknown=false;
      for(let c=0;c<idx.length;c++){ if(!(this.heights[idx[c]]>0)){ unknown=true; break; } }
      if(!unknown) continue;
      const row=this.byIndex[r];
      const h=row.el.offsetHeight||0;
      if(!(h>0)) continue;
      for(let c=0;c<idx.length;c++){
        const i=idx[c];
        const k=this.key(this.items[i], i);
        this.stats.measures++;
        if(this.hcache[k]!==h){ this.hcache[k]=h; }
        if(this.heights[i]!==h){ this.heights[i]=h; changed=true; }
      }
    }
    if(changed){
      const med=vsMedian(this.heights);
      if(med>0) this.defaultH=med;
      this._layout();
      if(this.spacer) this.spacer.style.height=this.layout.height+'px';
      for(const r in this.byIndex){
        const row=this.byIndex[r];
        if(this.layout.tops[r]!=null) row.el.style.top=this.layout.tops[r]+'px';
      }
      this.stats.relayouts++;
    }
  }
  destroy(){
    this.dead=true;
    if(this.watch) Clock.off(this.watch);
    if(this.raf!=null){ cancelAnimationFrame(this.raf); this.raf=null; }
    if(this.scroller&&this.scroller.removeEventListener)
      this.scroller.removeEventListener('scroll', this._scroll);
    if(typeof window!=='undefined') window.removeEventListener('resize', this._resize);
    if(this.ro){ try{ this.ro.disconnect(); }catch(e){} this.ro=null; }
    this.byIndex={};
    if(this.host){
      this.host.classList.remove('vs-host');
      this.host.innerHTML='';
    }
    this.spacer=null; this.layer=null; this.items=[];
  }
  /* what the perf HUD shows */
  report(){
    return {items:this.stats.items, rows:this.stats.rows, cols:this.cols,
            nodes:this.stats.nodes, renders:this.stats.renders,
            height:this.layout.height, relayouts:this.stats.relayouts};
  }
}
/* ── the three windowed grids ─────────────────────────────────────────────
   One instance per host, created on first render and reused for the life of
   the page: creating it is what empties the host, so it must never happen
   twice for the same element. */
const VS={feed:null, archive:null, bmark:null};
const VS_OPTS_FEED={min:306, gap:16, defaultH:280, overscan:900, render:cardHTML,
  key:function(a){ return a&&a.__sk!=null?('sk'+a.__sk):(a&&a.id!=null?a.id:''); }};
const VS_OPTS_BMARK={min:306, gap:16, defaultH:280, overscan:900, render:cardHTML,
  key:function(a){ return a&&a.id!=null?a.id:''; }};
const VS_OPTS_ARCHIVE={min:280, gap:14, defaultH:300, overscan:1000,
  key:function(it,i){ return it&&it.__full?('day:'+it.__day):(it&&it.id!=null?it.id:i); },
  render:function(it){
    if(it&&it.__full)
      return '<div class="calday archday"><div class="calday-h">'+
        '<span class="calday-title">'+ic('calendar')+' '+esc(it.__day)+'</span>'+
        '<span class="calday-meta">'+toFa(it.n)+' خبر آرشیوشده</span></div></div>';
    return cardHTML(it);
  }};
function vsFor(which, hostId, opts){
  const g=document.getElementById(hostId);
  if(!g) return null;
  if(!VS[which]){
    try{ VS[which]=new VirtualScroller(g, opts); }
    catch(e){ if(typeof console!=='undefined'&&console.error) console.error('vs:'+which, e); return null; }
  }
  return VS[which];
}
function vsGrid(which, hostId, opts, items, fallbackHTML){
  const vs=vsFor(which, hostId, opts);
  if(vs){ vs.setItems(items); return true; }
  const g=document.getElementById(hostId);
  if(g&&fallbackHTML!=null) g.innerHTML=fallbackHTML;
  return false;
}
function vsReleaseAll(){
  ['feed','archive','bmark'].forEach(function(k){
    if(VS[k]){ VS[k].destroy(); VS[k]=null; }
  });
}
/* ── perf HUD ──────────────────────────────────────────────────────────────
   Numbers, not adjectives. Every claim in the benchmark table is produced by
   this panel on the live page: how many nodes the document actually holds,
   how many rows each grid is willing to keep, and what the clock did. */
/* one icon helper for generated markup — every pictogram is an SVG <use> into
   the sprite at the top of <body>, never a font glyph */
function ic(name, cls){ return '<svg class="ic'+(cls?' '+cls:'')+'" aria-hidden="true"><use href="#i-'+name+'"/></svg>'; }
/* asset and topic marks: the registry used to carry an emoji per asset, which
   put pictographs in the middle of an otherwise drawn interface. The mark is
   now derived from the instrument itself (coin / ingot / barrel / FX / index),
   so a newly added asset gets a real icon with no data migration. */
const ASSET_IC={BTC:'coin',ETH:'coin',BNB:'coin',SOL:'coin',XRP:'coin',ADA:'coin',DOGE:'coin',LINK:'coin',
                XAU:'ingot',XAG:'ingot',WTI:'drop',DXY:'swap',SPX:'chart',VIX:'pulse'};
function assetIcName(sym){
  const s=String(sym||'').toUpperCase();
  if(ASSET_IC[s]) return ASSET_IC[s];
  const meta=((typeof DATA!=='undefined'&&DATA&&DATA.assets_meta)||{})[s]||{};
  if(meta.coingecko) return 'coin';
  if(meta.yahoo&&/=F$/.test(String(meta.yahoo))) return 'drop';
  return 'chart';
}
function assetIc(sym, cls){ return ic(assetIcName(sym), cls); }
const TOPIC_IC={regulation:'lock',institutional:'bank',etf:'coins',macro:'globe',security:'shield',
                analysis:'chart',defi:'grid',market:'pulse',tech:'cpu',general:'news'};
function topicIc(t, cls){ return ic(TOPIC_IC[t]||'tag', cls); }
function num(v,nd){ return Number(v).toLocaleString('en-US',{minimumFractionDigits:nd||0,maximumFractionDigits:nd||0}); }
function fmtPrice(v){ if(v==null) return '—';
  if(v>=1000) return '$'+num(v,0);
  if(v>=10) return '$'+num(v,2); if(v>=1) return '$'+num(v,3); return '$'+num(v,4); }
function fmtIran(iso){ if(!iso) return '—'; try{ return toFa(new Date(iso).toLocaleTimeString('fa-IR',{hour:'2-digit',minute:'2-digit'})); }catch(e){ return '—'; } }
/* the telemetry line is English: same clock, Latin digits */
function fmtEng(iso){ if(!iso) return '—'; try{ return new Date(iso).toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'}); }catch(e){ return '—'; } }
/* storage keys carry the app name — migrate once from the pre-rebrand keys so
   bookmarks saved before the rename are never lost */
const BM_KEY='mohmd_bmarks', BM_META_KEY='mohmd_bmark_meta';
(function migrateBmarkKeys(){
  try{
    const pairs=[[BM_KEY,'hermes_bmarks'],[BM_META_KEY,'hermes_bmark_meta']];
    for(const [nu,old] of pairs){
      if(localStorage.getItem(nu)==null && localStorage.getItem(old)!=null){
        localStorage.setItem(nu, localStorage.getItem(old));
        localStorage.removeItem(old);
      }
    }
  }catch(e){}
})();
function getBookmarks(){ try{ return JSON.parse(localStorage.getItem(BM_KEY)||'[]'); }catch(e){ return []; } }
function isBookmarked(id){ return getBookmarks().includes(id); }
/* a bookmark keeps a snapshot of the story so the Bookmarks tab still renders
   it after the article has aged out of the live window */
function getBmarkMeta(){ try{ return JSON.parse(localStorage.getItem(BM_META_KEY)||'{}'); }catch(e){ return {}; } }
function findArticle(id){
  const pools=[DATA.articles||[], DATA.archive||[]];
  for(const p of pools){ for(const a of p){ if(a.id===id) return a; } }
  return null;
}
function snapshot(a){
  const keys=['id','title','title_fa','source','source_kind','link','image','published_str','published_ts',
              'datetime_fa','age_fa','credibility','topic','topic_fa','topic_icon','assets','summary','summary_fa'];
  const o={}; for(const k of keys) if(a[k]!=null) o[k]=a[k];
  o.saved_at=Math.floor(Date.now()/1000);
  return o;
}
function toggleBookmark(id, ev){
  if(ev) ev.stopPropagation();
  let b = getBookmarks();
  const meta = getBmarkMeta();
  if(b.includes(id)){ b = b.filter(x=>x!==id); delete meta[id]; toast('از نشان‌شده‌ها حذف شد'); }
  else { b.push(id); const a=findArticle(id); if(a) meta[id]=snapshot(a); toast('⭐ به نشان‌شده‌ها اضافه شد'); }
  try{ localStorage.setItem(BM_KEY, JSON.stringify(b)); }catch(e){}
  try{ localStorage.setItem(BM_META_KEY, JSON.stringify(meta)); }catch(e){}
  renderChips();
  renderFeed();
  renderBookmarks();
}
function clearBookmarks(){
  if(!getBookmarks().length) return toast('نشان‌شده‌ای وجود ندارد');
  if(!confirm('همهٔ نشان‌شده‌ها پاک شوند؟')) return;
  try{ localStorage.removeItem(BM_KEY); localStorage.removeItem(BM_META_KEY); }catch(e){}
  renderChips(); renderFeed(); renderBookmarks();
  toast('نشان‌شده‌ها پاک شد');
}

/* ── Jalali (برای برچسب محور نمودار) ── */
function g2j(gy,gm,gd){
  const gdm=[0,31,59,90,120,151,181,212,243,273,304,334];
  let gy2 = gm>2 ? gy+1 : gy;
  let days = 355666 + (365*gy) + Math.floor((gy2+3)/4) - Math.floor((gy2+99)/100) + Math.floor((gy2+399)/400) + gd + gdm[gm-1];
  let jy = -1595 + 33*Math.floor(days/12053); days %= 12053;
  jy += 4*Math.floor(days/1461); days %= 1461;
  if(days>365){ jy += Math.floor((days-1)/365); days = (days-1)%365; }
  let jm, jd;
  if(days<186){ jm = 1+Math.floor(days/31); jd = 1+(days%31); }
  else { jm = 7+Math.floor((days-186)/30); jd = 1+((days-186)%30); }
  return [jy,jm,jd];
}
const JM=['فروردین','اردیبهشت','خرداد','تیر','مرداد','شهریور','مهر','آبان','آذر','دی','بهمن','اسفند'];
function faDateFromIso(s){ if(!s) return ''; const p=s.split('-'); if(p.length<3) return s;
  const [jy,jm,jd]=g2j(+p[0],+p[1],+p[2]); return toFa(jd)+' '+JM[jm-1]; }

/* ── views ── */
function showView(v, skipPick){
  const prev=UI.view;
  UI.view=v;
  document.querySelectorAll('.tab').forEach(t=>{t.classList.toggle('active',t.dataset.view===v); t.setAttribute('aria-selected', t.dataset.view===v?'true':'false');});
  document.querySelectorAll('.view').forEach(s=>s.classList.toggle('active',s.id==='view-'+v));
  ['ibSettings','ibSources','ibAssets'].forEach(id=>{
    const b=document.getElementById(id);
    if(b) b.classList.toggle('on', b.id==='ibSettings'&&v==='settings' || b.id==='ibSources'&&v==='sources' || b.id==='ibAssets'&&v==='assets');
  });
  /* releases happen on the way out, not on the way back in */
  if(prev&&prev!==v) teardownView(prev);
  /* the grids measure themselves, and a hidden element measures zero: a grid
     whose view was switched away from is re-measured the moment it is visible */
  if(v==='feed'&&VS.feed) VS.feed.refresh();
  if(v==='archive'&&VS.archive) VS.archive.refresh();
  if(v==='bookmarks'&&VS.bmark) VS.bmark.refresh();

  if(v==='reports'&&DATA&&!skipPick){
    const ordered=orderedAssets().filter(s=>true);
    if(!UI.repSym||!ordered.includes(UI.repSym)) UI.repSym=ordered[0];
    pickReport(UI.repSym, true);   // pickReport calls showView(..., skipPick)
  }
  if(v==='assets') renderAssetTable();
  /* the studio module lives in web/studio.js and may still be loading: guard it */
  if(v==='studio'&&window.Studio) window.Studio.mount();
  if(v==='channel'&&window.Channel) window.Channel.mount();
  if(v==='monitor') loadMonitor();
  if(v==='calendar'){ if(ECON) renderCalendar(); else loadCalendar(); }
  if(v==='alerts') initAlerts();
  if(UI.view==='archive'){ renderArchive(); return; }
  if(UI.view==='bookmarks'){ renderBookmarks(); return; }
  if(v==='etf'){ if(!(window.__ETFQ&&Object.keys(window.__ETFQ).length)) pollEtf(); renderEtfLive('etfLive2'); }
  if(v==='whales'){
    if(window.whaleTracker) window.whaleTracker.render();
    else if(typeof WhaleTracker!=='undefined'){
      window.whaleTracker = new WhaleTracker();
      window.whaleTracker.render();
    }
  }
  if(v==='ideas') loadIdeas();
  if(v==='reports'){
    /* coming back to the tab: the widget may have been mounted while hidden
       (or never mounted at all) — give it a viewport to measure */
    setTimeout(()=>{
      try{
        if(!document.querySelector('#tvholder iframe')) mountTVChart(true);
        else window.dispatchEvent(new Event('resize'));
      }catch(e){}
    }, 150);
  }
}
function gotoView(v){ showView(v); }

async function loadData(){
  if(_LOADING) return;
  _LOADING = true;
  try{
    const r = await fetch('/api/data');
    if(!r.ok) throw new Error(r.status);
    DATA = await r.json();
    initMeta(); renderAll();
  }catch(e){
    console.error('loadData:', e);            /* never swallow silently — the
        banner alone hides which renderer broke (it did: the maquette's
        synchronous mock used to fail here with an empty feed and no trace) */
    const ct=document.getElementById('cycleTxt');
    if(ct) ct.textContent='خطای اتصال به سرور';
  }finally{
    _LOADING = false;
  }
}
/* poll /api/data every 60s so newly-cycled news appears without reload */
/* ── timers that stand down while the stream is alive ──────────────────────
   These two used to be the feed's clock. Now the `news` channel delivers new
   articles the moment the scrape lands, so the timers are only a safety net
   for the case where no stream (ws or sse) could be established at all. */
Clock.every(60000, ()=>{ if(Stream.state!=='live'&&(!DATA||!DATA.stats||!DATA.stats.cycle_running)) loadData(); }, {label:'feed-net-60s'});
/* While a cycle is running the feed is polled too: the server publishes the
   fresh articles as soon as the scrape lands (before translation/reports),
   so waiting for cycle_running to go false used to hide them for minutes. */
Clock.every(20000, ()=>{ if(Stream.state!=='live'&&DATA&&DATA.stats&&DATA.stats.cycle_running) loadData(); }, {label:'feed-net-20s'});
/* ── DL2 phase 2/5: live price ticker under the topbar ────────────────────
   Compact marquee: every asset in the board, the whole series rendered twice
   so the CSS slide can loop seamlessly. The scroll duration scales with the
   number of symbols (about 3s each) so adding an asset never makes it crawl. */
/* infinite marquee (2026-09-26): one chip per asset, then the series repeated
   until a single pass is wider than the bar, rendered as two identical halves.
   CSS slides the track exactly -50%, so the loop restarts on an identical
   frame — no jump and no cut-off end, however few assets are enabled. The
   duration follows the real pixel width, so the speed never changes. */
function tickerChipsHTML(){
  const out=[];
  (typeof orderedAssets==='function'?orderedAssets():[]).forEach(sym=>{
    const m=(DATA.market||{})[sym]||{};
    const lv=(typeof liveOf==='function')?liveOf(sym):null;
    const price=(lv&&lv.price!=null)?lv.price:m.price;
    if(price==null) return;
    const chg=(lv&&lv.change_24h!=null)?lv.change_24h:m.change_24h;
    const cls=chg==null?'':(chg>=0?'up':'dn');
    const arrow=chg==null?'':(chg>=0?'▲':'▼');
    /* data-sym: the handle the stream's micro-updates use to find this chip's
       .p / .c nodes without re-rendering the marquee on every tick */
    out.push(`<span class="tk ${cls}" data-sym="${esc(sym)}" title="${esc(sym)}"><span class="s">${esc(sym)}</span>`+
      `<span class="p">${fmtPrice(price)}</span>`+
      (chg==null?'':`<span class="c">${arrow}${Math.abs(chg).toFixed(2)}%</span>`)+
      (m.stale?'<span class="st" title="قیمت کهنه"></span>':'')+`</span>`);
  });
  /* the unit ends on its separator so repeating it keeps the rhythm even */
  return out.length ? out.join('<span class="sep">◆</span>')+'<span class="sep">◆</span>' : '';
}
function renderTicker(){
  const bar=document.getElementById('tickerBar');
  if(!bar||!DATA) return;
  const unit=tickerChipsHTML();
  if(!unit){ bar.innerHTML=''; return; }
  bar.innerHTML=`<div class="tk-half">${unit}</div>`;      /* measure one pass */
  const probe=bar.firstElementChild;
  const unitW=probe?probe.getBoundingClientRect().width:0;
  const viewW=Math.max(bar.clientWidth||0, document.documentElement.clientWidth||0, 320);
  const reps=(unitW>1)?Math.max(1, Math.ceil(viewW/unitW)+1):1;
  const half=unit.repeat(reps);
  const dur=Math.max(36, Math.min(220, Math.round(((unitW*reps)||600)/52)));
  bar.innerHTML=`<div class="tk-track" style="--tk-dur:${dur}s">`+
    `<div class="tk-half">${half}</div>`+
    `<div class="tk-half" aria-hidden="true">${half}</div></div>`;
}
/* ── اخبار منتخب: twenty selected stories, four per row, one page at a time ──
   Was three text boxes above a grid of full-colour cards. Three problems with
   that: the top of the page looked poorer than what sat under it, three cards
   is not a section, and the top three by credibility barely move between two
   payloads — so the same three stories sat at the top of the page all day.
   Now twenty are picked and the row walks through them a page at a time. It is
   pausable by hand, and it stops by itself while the pointer or the keyboard is
   inside it: a carousel that moves under a reading eye is the one thing a
   carousel must never do. */
const LEAD_POOL=20, LEAD_PER=4, LEAD_ROTATE_MS=10000, LEAD_MIN_CRED=0.55;
const LEAD={pool:[], page:0, paused:false, hover:false, built:false};
const LEAD_REDUCE=(typeof matchMedia==='function')?matchMedia('(prefers-reduced-motion: reduce)'):null;

function leadTs(a){ const t=(a&&a.published_ts)||0; return t>1e12?Math.floor(t/1000):t; }
/* credibility first, freshness as the tie-breaker: a 0.80 story from an hour
   ago outranks a 0.75 one from this morning, and yesterday's tail never buys
   its way in on age alone */
function leadScore(a, now){
  const cred=Math.max(0, Math.min(1, (+(a&&a.credibility))||0));
  const hours=Math.max(0, ((now||0)-leadTs(a))/3600);
  return cred*100 + Math.max(0, 1-hours/24)*15;
}
/* the twenty: the best story per asset first, then the rest by score, so four
   cards in one row are never four takes on the same coin */
function leadPick(arts, now){
  const sorted=(arts||[]).filter(a=>a&&a.id&&((+a.credibility)||0)>=LEAD_MIN_CRED)
    .slice().sort((a,b)=>leadScore(b,now)-leadScore(a,now)||leadTs(b)-leadTs(a));
  const out=[], seen={};
  for(const a of sorted){
    const key=(a.assets&&a.assets[0])||a.topic||a.source||'?';
    if(seen[key]) continue;
    seen[key]=1; out.push(a);
    if(out.length>=LEAD_POOL) return out;
  }
  for(const a of sorted){
    if(out.indexOf(a)<0) out.push(a);
    if(out.length>=LEAD_POOL) break;
  }
  return out;
}
function leadPages(pool){ return Math.max(1, Math.ceil((((pool||[]).length)||0)/LEAD_PER)); }
function leadWindow(pool, page){
  const n=(pool||[]).length; if(!n) return [];
  const pages=leadPages(pool), p=((((Math.round(page)||0)%pages)+pages)%pages);
  return pool.slice(p*LEAD_PER, p*LEAD_PER+LEAD_PER);
}
/* the banner slot the stylesheet already had (`.lead-card .thumb`, 21:9) but
   no renderer ever filled: the most credible stories ran as text-only boxes
   directly above a grid of full-colour thumbnails */
function leadCardHTML(a){
  /* the sanitised URL is the only URL that reaches the markup — including the
     proxy fallback, which used to be built from the raw feed string */
  const img0=safeUrl(a.image);
  const img = img0
    ? `<div class="thumb"><img src="${attr(img0)}" alt="" loading="eager" referrerpolicy="no-referrer" data-orig="${attr(img0)}" onerror="if(!this.dataset.tried){this.dataset.tried='1';this.src='/api/proxy-image?url='+encodeURIComponent(this.dataset.orig);}else{this.remove()}"></div>`
    : '';
  const assets=(a.assets||[]).slice(0,2);
  return `<article class="lead-card" data-id="${attr(a.id)}" role="button" tabindex="0"
      aria-label="${esc(a.title_fa||a.title)}" onclick="openArticle(${jsArg(a.id)})"
      onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();openArticle(${jsArg(a.id)})}">
      <div class="lead-rail"></div>
      ${img}
      <div class="body">
        <div class="row1">${assets.map(s=>`<span class="badge b-asset">${assetIc(s)}${FA_ASSET[s]||s}</span>`).join('')}
          <span class="badge b-topic">${topicIc(a.topic)} ${FA_TOPIC[a.topic]||''}</span></div>
        <div class="lead-ttl">${esc(a.title_fa||a.title)}</div>
        <div class="row2"><span class="src">${esc(a.source)}</span><span class="dt">${esc(a.datetime_fa||'')}</span>
          <button class="del-btn" onclick="hideNews(${jsArg(a.id)}, event)" title="حذف این خبر از داشبورد" aria-label="حذف خبر">${ic('trash')}</button></div>
      </div></article>`;
}
/* the head doubles as the WCAG "pause, stop, hide" control an auto-rotating
   row needs: without a visible stop, rotation for more than five seconds is a
   failure on its own */
function leadHeadHTML(pool, page){
  const pages=leadPages(pool), lab=`<span class="lead-lab">${ic('star')} اخبار منتخب</span>`+
    `<span class="lead-count">${toFa(pool.length)} خبر برتر</span>`;
  if(pages<2) return `<div class="lead-head">${lab}</div>`;
  let dots='';
  for(let i=0;i<pages;i++)
    dots+=`<button class="lead-dot${i===page?' on':''}" aria-label="صفحهٔ ${toFa(i+1)} از ${toFa(pages)}" aria-current="${i===page?'true':'false'}" onclick="leadGo(${i})"></button>`;
  return `<div class="lead-head">${lab}
    <div class="lead-nav">
      <button class="lead-btn" onclick="leadStep(-1)" title="صفحهٔ قبلی" aria-label="صفحهٔ قبلی اخبار منتخب">${ic('chev-right')}</button>
      <span class="lead-dots">${dots}</span>
      <span class="lead-pos">${toFa(page+1)} / ${toFa(pages)}</span>
      <button class="lead-btn" id="leadPlay" onclick="leadToggle()" aria-pressed="${LEAD.paused?'true':'false'}"
        title="${LEAD.paused?'شروع چرخش اخبار منتخب':'توقف چرخش اخبار منتخب'}">${ic(LEAD.paused?'play':'pause')}</button>
      <button class="lead-btn" onclick="leadStep(1)" title="صفحهٔ بعدی" aria-label="صفحهٔ بعدی اخبار منتخب">${ic('chev-left')}</button>
    </div></div>`;
}
function paintLead(animate){
  const box=document.getElementById('leadRow'); if(!box) return;
  const pool=LEAD.pool;
  if(!pool.length){ box.innerHTML=''; box.hidden=true; return; }
  if(box.hidden) box.hidden=false;
  /* the inner grid is the only node replaced, and the fade-in class is on it
     when it is created — so a page change is one animation, not a swap plus a
     timer waiting to start one */
  box.innerHTML=leadHeadHTML(pool, LEAD.page)+
    `<div class="lead-cards${animate?' lead-in':''}" id="leadCards">`+
    leadWindow(pool, LEAD.page).map(leadCardHTML).join('')+`</div>`;
}
function leadGo(p){
  const pages=leadPages(LEAD.pool);
  LEAD.page=((((Math.round(p)||0)%pages)+pages)%pages);
  paintLead(true);
}
function leadStep(d){ leadGo(LEAD.page+(d||1)); }
function leadToggle(){ LEAD.paused=!LEAD.paused; paintLead(false); }
function initLead(){
  if(LEAD.built) return;
  const box=document.getElementById('leadRow');
  if(!box||!box.addEventListener) return;
  LEAD.built=true;
  const enter=()=>{ LEAD.hover=true; }, leave=()=>{ LEAD.hover=false; };
  box.addEventListener('mouseenter',enter); box.addEventListener('mouseleave',leave);
  box.addEventListener('focusin',enter);    box.addEventListener('focusout',leave);
}
function renderLead(){
  const box=document.getElementById('leadRow');
  if(!box||!DATA) return;
  const wasOn=leadWindow(LEAD.pool, LEAD.page)[0];
  LEAD.pool=leadPick(DATA.articles||[], Math.floor(Date.now()/1000));
  /* a new payload reshuffles the twenty: stay with the story the reader was
     looking at instead of snapping back to page one every sixty seconds */
  if(wasOn){
    const at=LEAD.pool.map(a=>a.id).indexOf(wasOn.id);
    if(at>=0) LEAD.page=Math.floor(at/LEAD_PER);
  }
  if(LEAD.page>=leadPages(LEAD.pool)) LEAD.page=0;
  initLead();
  paintLead(false);
}
/* one slot on the single clock, and every reason not to fire lives in its
   `when`: another tab's worth of rotation is work nobody asked for */
Clock.every(LEAD_ROTATE_MS, ()=>{ if(leadPages(LEAD.pool)>1) leadStep(1); }, {
  label:'lead-rotate',
  when:()=>{
    if(typeof UI==='undefined'||UI.view!=='feed') return false;
    if(LEAD.paused||LEAD.hover||document.hidden) return false;
    if(LEAD_REDUCE&&LEAD_REDUCE.matches) return false;   /* motion is optional; readability is not */
    const ov=document.getElementById('artOverlay');
    return !(ov&&ov.classList&&ov.classList.contains('open'));
  }
});
function renderAll(){
  window.__MACRO=DATA.macro||[];
  renderChips(); renderSrcSel(); renderKindSel(); renderFeed();
  renderTicker(); renderLead(); dl2AfterFeed();
  renderSources(); renderSettings(); renderStats(); renderAssetTable(); renderArchive(); renderBookmarks();
  arTick();           /* alert rules see the new headline list on the next slot */
  paintFng(); paintHygiene();
  /* opening the reports tab before the first payload lands used to leave it
     empty forever — the tab needs DATA to pick an asset, so it retries here */
  if(UI.view==='reports'&&!window.__rep&&!window.__repPending)
    pickReport(UI.repSym||orderedAssets()[0], true);
  if(UI.view==='monitor') loadMonitor();
  if(UI.view==='calendar'&&ECON) renderCalendar();
  if(UI.view==='whales'&&window.whaleTracker) window.whaleTracker.render();
}
/* ── bookmarks tab ── */
function renderBookmarks(){
  const g=document.getElementById('bmarkGrid'), empty=document.getElementById('bmarkEmpty'),
        cnt=document.getElementById('cntBmarks'), sum=document.getElementById('bmarkSummary');
  if(!g) return;
  const ids=getBookmarks(), meta=getBmarkMeta();
  const items=[];
  for(const id of ids.slice().reverse()){                 /* newest bookmark first */
    const a=findArticle(id)||meta[id];
    if(a) items.push(a);
  }
  if(sum) sum.textContent=`${toFa(items.length)} نشان‌شده · ${toFa(ids.length)} شناسه · ذخیره‌شده در همین مرورگر`;
  if(cnt){ if(ids.length){ cnt.style.display='inline-block'; cnt.textContent=toFa(ids.length); } else cnt.style.display='none'; }
  empty.style.display=items.length?'none':'block';
  vsGrid('bmark','bmarkGrid',VS_OPTS_BMARK, items, items.map(cardHTML).join(''));
}
/* ── archive tab ── */
function renderArchive(){
  const g=document.getElementById('archGrid'), empty=document.getElementById('archEmpty'),
        cnt=document.getElementById('cntArchive'), sum=document.getElementById('archSummary');
  if(!g) return;
  const list=DATA.archive||[];
  if(sum) sum.textContent=`${toFa(list.length)} خبر آرشیوشده (کل: ${toFa(DATA.archive_total||list.length)}) · خارج از پنجرهٔ فعال`; 
  if(cnt){ if(list.length){cnt.style.display='inline-block'; cnt.textContent=toFa(list.length);} else cnt.style.display='none'; }
  empty.style.display=list.length?'none':'block';
  /* day-grouped boxed layout — same visual language as the calendar */
  const byDay={}; const days=[];
  for(const a of list){
    const d=(a.datetime_fa||'').split('،')[0]||'قدیمی‌تر';
    if(!byDay[d]){ byDay[d]=[]; days.push(d); }
    byDay[d].push(a);
  }
  /* the day header is a full-row item, so windowing cannot lose the grouping:
     whichever rows are on screen, each one carries its own header */
  const flat=[];
  for(const day of days){
    flat.push({__full:true, __day:day, n:byDay[day].length});
    for(const a of byDay[day]) flat.push(a);
  }
  vsGrid('archive','archGrid',VS_OPTS_ARCHIVE, flat, days.map(day=>{
    const items=byDay[day];
    return `<div class="calday archday">
      <div class="calday-h"><span class="calday-title">${ic('calendar')} ${esc(day)}</span>
        <span class="calday-meta">${toFa(items.length)} خبر آرشیوشده</span></div>
      <div class="archgrid">${items.map(cardHTML).join('')}</div>
    </div>`;
  }).join(''));
}
/* ── source health monitor ── */
let MON=null;
async function loadMonitor(){
  try{
    const r=await fetch('/api/monitor'); const d=await r.json();
    MON=d.monitor; renderMonitor();
  }catch(e){}
}
let recTimer=null;
async function recoverAll(){
  const b=document.getElementById('recoverBtn');
  if(b.disabled) return;
  b.disabled=true;
  try{ await fetch('/api/recover',{method:'POST'}); }
  catch(e){ b.disabled=false; toast('بازیابی شروع نشد'); return; }
  toast('بازیابی عمیق شروع شد — بیش از ۶۰ روش برای هر فید خراب');
  Clock.off(recTimer);
  recTimer=Clock.every(2000, async ()=>{
    const b=document.getElementById('recoverBtn');
    if(!b) return;
    try{
      const r=await fetch('/api/recover/status'); const j=await r.json();
      if(!j.running){
        Clock.off(recTimer); b.disabled=false;
        b.innerHTML=ic('refresh')+' بازیابی همهٔ فیدهای خراب';
        if(j.total) toast(`بازیابی تمام شد — ${toFa(j.fixed)} از ${toFa(j.total)} فید برگشت · ${toFa(j.attempts)} روش امتحان شد`);
        loadMonitor();
        return;
      }
      b.innerHTML=ic('refresh')+` در حال بازیابی… فید ${toFa(j.done||0)} از ${toFa(j.total||0)} · ${toFa(j.attempts||0)} روش · ${toFa(j.fixed||0)} ترمیم‌شده`;
      if((j.attempts||0)%6===0) loadMonitor();      /* refresh rows live */
    }catch(e){}
  },2000);
  setTimeout(loadMonitor, 4000);
}
function renderMonitor(){
  if(!MON) return;
  document.getElementById('monSummary').textContent=`${toFa(MON.ok)} از ${toFa(MON.total)} فید سالم · ${toFa(MON.broken)} خراب`;
  const nb=document.getElementById('cntBroken');
  if(MON.broken>0){ nb.style.display='inline-block'; nb.textContent=MON.broken; nb.style.background='var(--dn)'; nb.style.color='#fff'; }
  else nb.style.display='none';
  const rows=[...MON.rows].sort((a,b)=>(a.ok-b.ok)||(b.count-a.count));
  let html='';
  for(const r of rows){
    if(r.ok&&!r.recovered) continue;                 /* healthy & untouched: skip in monitor */
    const st=r.ok?(r.recovered?`<span class="ok">${ic('check')} بازیابی‌شده</span>`:`<span class="ok">${ic('check')} سالم</span>`)
                 :`<span class="bad">${ic('x')} خراب</span>`;
    const reason=r.ok?'':`<div style="color:var(--cu-txt);margin-block-start:3px">${ic('warn')} علت: ${esc(r.reason_fa||r.detail||'نامعلوم')}</div>`;
    const rec=(r.recovery||[]);
    const shown=rec.slice(0,8);
    const path=rec.length?`<div style="color:var(--ink-3);font-size:10.5px;margin-block-start:2px">بازیابی: ${toFa(rec.length)} روش امتحان شد — ${shown.map(esc).join(' → ')}${rec.length>8?` … (+${toFa(rec.length-8)} روش دیگر)`:''}${r.mirror?' (آینه)':''}${r.ok?' · آخرین موفقیت: '+esc(shown[shown.length-1]||''):''}</div>`:'';
    const hist=(r.hist&&r.hist.length)?`<div style="display:flex;align-items:center;gap:6px;margin-block-start:3px;color:var(--ink-4);font-size:10.5px">۳۰ چرخهٔ آخر: ${histSvg(r.hist)}</div>`:'';
    html+=`<div class="monrow">
      <div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap">
        <span><b>${esc(r.name)}</b> <span style="color:var(--ink-4);font-size:10px">${esc(r.kind_fa||'')}</span></span>
        <span style="font-size:11px">${st}${r.count?` · ${toFa(r.count)} خبر`:''}${r.checked_fa?` · در ${esc(r.checked_fa)}`:''}</span>
      </div>
      ${reason}${path}${hist}
    </div>`;
  }
  document.getElementById('monList').innerHTML=html||'<div class="empty">همهٔ منابع سالماند — فیدی برای ترمیم نیست.</div>';
}
function renderStats(){
  const s=DATA.stats;
  document.getElementById('lastUpd').textContent = fmtEng(s.last_update);
  const d=document.getElementById('cycleDot'), t=document.getElementById('cycleTxt');
  d.className='dot'+(s.cycle_running?' busy':(s.last_error?' err':''));
  /* the cycle pill reads in English — it sits inside the English telemetry line */
  t.textContent = s.cycle_running?'cycle running — fetching & translating':(s.cycles_run? ('cycle #'+s.cycles_run+' done · every '+Math.round(DATA.config.interval/60)+'m'):'starting…');
  document.getElementById('cntFeed').textContent = toFa(DATA.articles.length);
  document.getElementById('cntSrc').textContent = toFa(DATA.sources.filter(x=>x.enabled).length);
  document.getElementById('ruleAge').textContent = DATA.rules.max_age_hours;
  document.getElementById('setAgeInfo').textContent = toFa(DATA.rules.max_age_hours);
  const rb=document.getElementById('refreshBtn'); rb.disabled=!!s.cycle_running;
  rb.innerHTML = s.cycle_running?(ic('clock')+' Refreshing…'):(ic('refresh')+' Refresh');
  const cs = s.cycle_stats||{};
  if(cs.total!=null) document.getElementById('cycleTxt').title =
     `خبر معتبر: ${toFa(cs.total)} | ردشده: ${toFa(cs.rejected)} (قدیمی‌تر از ${toFa(cs.max_age_hours)} ساعت: ${toFa(cs.stale_rejected)}) | فید سالم: ${toFa(cs.feeds_ok)} از ${toFa(cs.feeds_total)}`;
}
/* the cycle countdown and every calendar countdown run on one slot now; see
   clockTick() next to the Clock itself */
Clock.every(1000, clockTick, {label:'clock-tick', immediate:true});

/* ── live prices (free APIs, polled every 15s) ── */
async function pollLive(){
  try{
    const r=await fetch('/api/live'); const d=await r.json();
    if(d.ok&&d.prices){ LIVE=d.prices; if(d.fng&&d.fng.now!=null) window.__FNG=d.fng; paintLive(); paintFng(); arTick(); }
  }catch(e){
    console.error('pollLive:', e);
  }
}
function liveOf(sym){ return LIVE[sym]||null; }
function paintLive(){
  if(UI.view==='reports'&&window.__rep){ updateChartLive(); }
}
/* green/red flash on a price element whose value moved */
function flash(el, dir){ if(!el||!dir) return; el.classList.remove('flash-up','flash-dn'); void el.offsetWidth;
  el.classList.add(dir>0?'flash-up':'flash-dn'); }
/* pollLive() is no longer on a timer of its own: StreamManager calls it only
   while no stream is alive, and stops the moment one connects (2026-09-28). */

/* ── assets strip — deleted.
   The per-asset price cards duplicated the ticker and pushed the first headline
   down the page. Live prices still paint the ticker, the report head and the
   asset table. */
function histSvg(arr){
  if(!arr||!arr.length) return '';
  const W=arr.length*4;
  return `<svg class="histsvg" viewBox="0 0 ${W} 20" preserveAspectRatio="none" role="img" aria-label="health history">`+
    arr.map((v,i)=>`<rect x="${i*4}" y="${v?4:12}" width="3" height="${v?12:4}" fill="${v?'var(--up)':'var(--dn)'}"/>`).join('')+`</svg>`;
}

/* ── sources management (restored: this function and toggleSrc were lost when
   the old chart engine was cut out of the file) ──────────────────────────── */
function renderSources(){
  const list=DATA.sources||[];
  const cnt=document.getElementById('srcCount');
  if(cnt) cnt.textContent=toFa(list.filter(s=>s.enabled).length)+' فعال از '+toFa(list.length);
  const groups={};
  for(const s of list){ (groups[s.kind_fa]=groups[s.kind_fa]||[]).push(s); }
  let html='';
  for(const kind of Object.keys(groups)){
    const items=groups[kind];
    const on=items.filter(x=>x.enabled).length;
    html+=`<div class="kindgroup">
      <div class="kh"><span>${esc(kind)}</span><span style="font-size:11px;color:var(--ink-3)">${toFa(on)}/${toFa(items.length)} فعال</span></div>
      <div class="kb">${items.map(s=>`
        <div class="srcrow">
          <label class="switch"><input type="checkbox" ${s.enabled?'checked':''} aria-label="فعال یا خاموش کردن ${esc(s.name)}" onchange="toggleSrc(${jsArg(s.key)},this.checked)"><span class="slider"></span></label>
          <span class="nm">${esc(s.name)}</span>
          <span class="trust">اعتماد ${toFa(Math.round(s.trust*100))}٪</span>
          <span class="url ltr" title="${esc(s.url||'')}">${esc(s.url||'')}</span>
          <span class="ltr ${s.last_ok===false?'bad':'ok'}" style="font-size:10.5px">${s.last_count==null?'—':(s.last_ok?ic('check')+' '+toFa(s.last_count)+' خبر':ic('x')+' قطع')}</span>
          ${s.type==='custom'?`<button class="btn ghost sm" onclick="removeSrc(${jsArg(s.key)})">حذف</button>`:''}
        </div>`).join('')}</div></div>`;
  }
  const box=document.getElementById('srcList');
  if(box) box.innerHTML=html||'<div class="empty">منبعی فعال نیست.</div>';
}
async function toggleSrc(key,on){
  try{
    await postSettings({source_updates:{[key]:on}});
    toast('منبع بروزرسانی شد — در چرخهٔ بعدی اعمال می‌شود');
  }catch(e){
    toast('خطا در بروزرسانی منبع');
  }
}

/* ── chips ── */
function renderChips(){
  /* the news channel can beat the first /api/data payload: render from what
     is really there instead of trusting a half-built DATA */
  if(!DATA) return;
  const topicsMeta=DATA.topics_meta||{}, assetsMeta=DATA.assets_meta||{};
  const cfgAssets=(DATA.config&&DATA.config.assets)||[];
  const tc=DATA.topic_counts||{};
  const bmarks=getBookmarks();
  const wl=typeof FreebuffWatchlist!=='undefined'?FreebuffWatchlist.get():[];
  let th=`<button class="chip ${UI.topic==='all'&&!UI.onlyBookmarked&&!UI.onlyWatchlist?'on':''}" aria-pressed="${UI.topic==='all'&&!UI.onlyBookmarked&&!UI.onlyWatchlist}" onclick="UI.onlyBookmarked=false;UI.onlyWatchlist=false;UI.topic='all';renderChips();renderFeed()">همه موضوعات <span class="n">${toFa(DATA.articles.length)}</span></button>`;
  if(wl.length){
    th+=`<button class="chip chip-watchlist ${UI.onlyWatchlist?'on':''}" onclick="UI.onlyWatchlist=!UI.onlyWatchlist;UI.onlyBookmarked=false;renderChips();renderFeed()" title="فیلتر اخبار دارایی‌های واچ‌لیست اختصاصی">${ic('star')} ⭐ واچ‌لیست من <span class="n">${toFa(wl.length)}</span></button>`;
  }
  if(bmarks.length){
    th+=`<button class="chip ${UI.onlyBookmarked?'on':''}" onclick="UI.onlyBookmarked=!UI.onlyBookmarked;UI.onlyWatchlist=false;renderChips();renderFeed()">${ic('star')} نشان‌شده‌ها <span class="n">${toFa(bmarks.length)}</span></button>`;
  }
  for(const t of Object.keys(topicsMeta)){
    const n=tc[t]||0; if(!n) continue;
    const tact=UI.topic===t&&!UI.onlyBookmarked&&!UI.onlyWatchlist;
    th+=`<button class="chip ${tact?'on':''}" aria-pressed="${tact}" onclick="setTopicFilter(${jsArg(t)})">${topicIc(t)} ${esc(faTopic(t))} <span class="n">${toFa(n)}</span></button>`;
  }
  document.getElementById('topicChips').innerHTML=th;

  const ac=DATA.asset_counts||{};
  let ah=`<button class="chip ${UI.asset==='all'?'on':''}" aria-pressed="${UI.asset==='all'}" onclick="UI.asset='all';UI.onlyBookmarked=false;UI.onlyWatchlist=false;renderChips();renderFeed()">همه دارایی‌ها</button>`;
  ah+=`<button class="chip" onclick="FreebuffWatchlist.openModal()" style="border-style:dashed;color:#f59e0b" title="ویرایش دارایی‌های واچ‌لیست">⚙️ تنظیم واچ‌لیست</button>`;
  for(const sym of orderedAssets()){
    if(cfgAssets.length&&!cfgAssets.includes(sym)) continue;
    const meta=assetsMeta[sym]||{};
    const aact=UI.asset===sym;
    ah+=`<button class="chip ${aact?'on':''}" aria-pressed="${aact}" onclick="setAssetFilter(${jsArg(sym)})">${assetIc(sym)} ${esc(faAssetName(sym))} <span class="n">${toFa(ac[sym]||0)}</span></button>`;
  }
  document.getElementById('assetChips').innerHTML=ah;
}
/* asset & topic chips are toggles: clicking the active one clears the filter */
function setAssetFilter(sym){ UI.asset = (UI.asset===sym) ? 'all' : sym; UI.onlyBookmarked=false; UI.onlyWatchlist=false; renderChips(); renderFeed(); }
function setTopicFilter(t){ UI.topic = (UI.topic===t) ? 'all' : t; UI.onlyBookmarked=false; UI.onlyWatchlist=false; renderChips(); renderFeed(); }
function renderSrcSel(){
  const sel=document.getElementById('srcSel'), cur=sel.value;
  const srcs=[...new Set(DATA.articles.map(a=>a.source))].sort();
  sel.innerHTML=`<option value="all">همه منابع</option>`+srcs.map(s=>`<option value="${esc(s)}">${esc(s)}</option>`).join('');
  if(srcs.includes(cur)) sel.value=cur;
}
function renderKindSel(){
  const sel=document.getElementById('kindSel'), cur=sel.value;
  const labels=DATA.kind_labels||{}, counts=DATA.kind_counts||{};
  let html='<option value="all">همه دسته‌های منبع</option>';
  for(const [k,fa] of Object.entries(labels)){
    if(!counts[k]) continue;
    html+=`<option value="${k}">${fa} (${toFa(counts[k])})</option>`;
  }
  sel.innerHTML=html;
  if([...sel.options].some(o=>o.value===cur)) sel.value=cur;
}

/* ── feed ── */
function renderFeed(){
  if (!DATA || !DATA.articles) return;
  const rawQ=(document.getElementById('q').value||'').trim().toLowerCase();
  const src=document.getElementById('srcSel').value;
  const kind=document.getElementById('kindSel').value;
  const minC=+document.getElementById('credSlider').value/100;
  const sort=document.getElementById('sortSel').value;
  const sent=document.getElementById('sentSel')?document.getElementById('sentSel').value:'all';
  const tr=document.getElementById('timeRangeSel')?document.getElementById('timeRangeSel').value:'all';
  const wl=typeof FreebuffWatchlist!=='undefined'?FreebuffWatchlist.get():[];

  const tsOf=a=>{ const t=a.published_ts||0; return t>1e12?Math.floor(t/1000):t; };
  const nowSec=Date.now()/1000;

  let list=DATA.articles.filter(a=>{
    if(UI.onlyBookmarked && !isBookmarked(a.id)) return false;
    if(UI.onlyWatchlist && !wl.some(s=>(a.assets||[]).includes(s))) return false;
    if(UI.topic!=='all'&&a.topic!==UI.topic) return false;
    if(UI.asset!=='all'&&!(a.assets||[]).includes(UI.asset)) return false;
    if(src!=='all'&&a.source!==src) return false;
    if(kind!=='all'&&a.source_kind!==kind) return false;
    if(a.credibility<minC) return false;

    // Time range filter
    if(tr!=='all'){
      const maxAgeH=parseFloat(tr);
      if(!isNaN(maxAgeH)){
        const pts=tsOf(a);
        if(pts && (nowSec - pts) > (maxAgeH * 3600)) return false;
      }
    }

    // Sentiment filter
    if(sent!=='all'){
      const txt=((a.title||'')+' '+(a.title_fa||'')+' '+(a.summary||'')+' '+(a.summary_fa||'')).toLowerCase();
      const isBull = /bull|rise|gain|surge|rally|jump|soar|high|buy|breakout|صعود|رشد|افزایش|جهش/i.test(txt);
      const isBear = /bear|drop|fall|plunge|crash|sink|dip|slide|low|sell|down|سقوط|افت|کاهش|ریزش/i.test(txt);
      if(sent==='bullish'&&!isBull) return false;
      if(sent==='bearish'&&!isBear) return false;
      if(sent==='neutral'&&(isBull||isBear)) return false;
    }

    // Advanced search with quotes, negation, and field prefixes
    if(rawQ){
      const fullText=((a.title||'')+' '+(a.title_fa||'')+' '+(a.summary_fa||'')+' '+(a.summary||'')+' '+(a.source||'')+' '+(a.assets||[]).join(' ')).toLowerCase();
      // Negation: -keyword
      const negs = (rawQ.match(/-\b[\w\u0600-\u06ff]+\b/g) || []).map(t=>t.slice(1));
      for(const nt of negs){ if(fullText.includes(nt)) return false; }
      // Source prefix: src:name or source:name
      const srcM = rawQ.match(/(?:src|source):([\w\u0600-\u06ff]+)/);
      if(srcM && !(a.source||'').toLowerCase().includes(srcM[1])) return false;
      // Asset prefix: asset:sym
      const astM = rawQ.match(/asset:([\w]+)/);
      if(astM && !(a.assets||[]).map(x=>x.toLowerCase()).includes(astM[1])) return false;

      let cleanQ = rawQ.replace(/-\b[\w\u0600-\u06ff]+\b/g, '').replace(/(?:src|source|asset):[\w\u0600-\u06ff]+/g, '').trim();
      if(cleanQ){
        const exactMatches = cleanQ.match(/"([^"]+)"/g);
        if(exactMatches){
          for(const em of exactMatches){
            const phrase = em.slice(1, -1).trim();
            if(phrase && !fullText.includes(phrase)) return false;
            cleanQ = cleanQ.replace(em, '').trim();
          }
        }
        if(cleanQ && !fullText.includes(cleanQ)) return false;
      }
    }
    return true;
  });

  if(sort==='new') list.sort((a,b)=>tsOf(b)-tsOf(a)||String(a.source).localeCompare(String(b.source)));
  else if(sort==='cred') list.sort((a,b)=>b.credibility-a.credibility||tsOf(b)-tsOf(a));
  else if(sort==='src') list.sort((a,b)=>a.source.localeCompare(b.source)||tsOf(b)-tsOf(a));
  document.getElementById('feedEmpty').style.display=list.length?'none':'block';
  document.getElementById('feedCount').textContent = toFa(list.length)+' خبر';
  vsGrid('feed','newsGrid',VS_OPTS_FEED, list, list.map(cardHTML).join(''));
  if(typeof syncFeedReset==='function') syncFeedReset();
}


function credBadge(c){
  const pct=Math.round(c*100), cls=pct>=75?'hi':(pct>=55?'mid':'low');
  return `<span class="cred ${cls}" title="امتیاز اعتبار محتوایی: ${toFa(pct)}٪"><span class="bar"><i style="width:${pct}%"></i></span><span>${pct}%</span></span>`;
}
function credChip(c){
  const pct=Math.round(c*100), cls=pct>=75?'hi':(pct>=55?'mid':'low');
  return `<span class="cred ${cls} cred-chip" title="امتیاز اعتبار محتوایی: ${toFa(pct)}٪">${toFa(pct)}٪</span>`;
}
function cardHTML(a){
  if(!a) return '';
  /* the loading skeleton rides the same window as the cards, so the first
     paint does not have to build and then throw away a full grid */
  if(a.__sk!=null) return '<div class="skcard skeleton"></div>';
  const _as=(a.assets||[]);
  const chips=_as.slice(0,2).map(s=>`<span class="badge b-asset">${assetIc(s)}${FA_ASSET[s]||s}</span>`).join('')
    + (_as.length>2?`<span class="badge more">+${toFa(_as.length-2)}</span>`:'');
  const tp=a.topic_fa?`<span class="badge b-topic">${topicIc(a.topic)} ${FA_TOPIC[a.topic]||a.topic_fa}</span>`:'';
  /* a headline can arrive on the news channel before the first /api/data
     payload has landed, and this renderer used to reach straight into DATA
     for the source-kind labels — one early story was enough to throw inside
     the paint and leave the window half-built */
  const kindLabels=(typeof DATA!=='undefined'&&DATA&&DATA.kind_labels)||{};
  const kd=kindLabels[a.source_kind]?`<span class="badge b-kind">${esc(kindLabels[a.source_kind])}</span>`:'';
  const sc=(a.source_kind==='social'&&a.reddit_score!=null)?`<span class="badge b-kind" title="آپ‌ووت زندهٔ ردیت">▲ ${toFa(a.reddit_score)}</span>`:'';
  const faTitle = a.title_fa || a.title;
  const enTitle = a.title_fa ? `<div class="ttl-en">${esc(a.title)}</div>` : '';
  const summ = a.summary_fa || a.summary || '';
  const img = a.image
    ? `<img src="${attr(safeUrl(a.image))}" alt="" loading="lazy" referrerpolicy="no-referrer" data-orig="${attr(a.image)}" onerror="if(!this.dataset.tried){this.dataset.tried='1';this.src='/api/proxy-image?url='+encodeURIComponent(this.dataset.orig);}else{this.replaceWith(Object.assign(document.createElement('div'),{className:'noimg',innerHTML:ic('news')}))}">`
    : '';
  const thumb = `<div class="thumb">${img || '<div class="noimg">'+ic('news')+'</div>'}${credChip(a.credibility)}</div>`;
  const bmarked = isBookmarked(a.id);
  const starBtn = `<button class="star-btn ${bmarked?'on':''}" onclick="toggleBookmark(${jsArg(a.id)}, event)" title="${bmarked?'حذف از نشان‌شده‌ها':'نشان کردن این خبر'}" aria-label="نشان کردن">${ic('star')}</button>`;
  const delBtn = `<button class="del-btn" onclick="hideNews(${jsArg(a.id)}, event)" title="حذف این خبر از داشبورد" aria-label="حذف خبر">${ic('trash')}</button>`;
  return `<div class="ncard" data-id="${attr(a.id)}" role="button" tabindex="0" aria-label="${esc(faTitle)} — ${esc(a.source)}" onclick="openArticle(${jsArg(a.id)})" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();openArticle(${jsArg(a.id)})}">
    ${thumb}
    <div class="body">
      <div class="row1">${tp}${kd}${sc}${chips}</div>
      <div class="ttl">${isNew(a)?'<span class="newdot newdot-inline" title="خبر تازه"></span>':''}${esc(faTitle)}</div>
      ${summ?`<div class="summ">${esc(summ)}</div>`:''}
      <div class="row2">
        <span class="src">${esc(a.source)}</span>
        <span class="dt" title="${esc(a.published_str||'')}">${esc(a.datetime_fa||'')}</span>
        ${starBtn}${delBtn}
      </div>
      <div style="display:flex;gap:6px;margin-top:6px;flex-wrap:wrap">
        <button class="btn ghost sm blurb-btn" onclick="event.stopPropagation();openBlurb(${jsArg(a.id)})" aria-label="توضیحات خبر">${ic('list')} توضیحات خبر</button>
      </div>
    </div>
  </div>`;
}

/* ── delete a news item ──────────────────────────────────────────────────────
   One click removes the story from every view and remembers it: the id is kept
   server-side, so the next scrape of the same link cannot bring it back. The
   list is not lost — Settings shows the count and can restore all of it. */
async function hideNews(id, ev){
  if(ev){ ev.stopPropagation(); ev.preventDefault(); }
  if(!id) return;
  if(typeof confirm==='function' && !confirm('این خبر از داشبورد حذف شود؟\n(از تنظیمات می‌توانی همهٔ حذف‌شده‌ها را برگردانی)')) return;
  const gone=document.querySelectorAll('[data-id="'+id+'"]');
  gone.forEach(el=>el.style.opacity='.35');
  try{
    const r=await fetch('/api/article/hide',{method:'POST',headers:{'Content-Type':'application/json'},
                                           body:JSON.stringify({id:id})});
    const d=await r.json();
    if(!d.ok) throw new Error(d.error||'failed');
    toast('خبر حذف شد — از تنظیمات قابل بازگردانی است');
    await loadData();
  }catch(e){
    gone.forEach(el=>el.style.opacity='');
    toast('حذف نشد — دوباره تلاش کن');
  }
}
/* the hygiene switches (feed sheet + settings) write the same config keys */
async function saveHygiene(){
  const box=document.getElementById('fHideSocial'), num=document.getElementById('fMinChars');
  const sBox=document.getElementById('setHideSocial'), sNum=document.getElementById('setMinChars');
  const gate=document.getElementById('fSocialGate'), sm=document.getElementById('fSocialMin');
  const hide_social = box?box.checked:(sBox?sBox.checked:false);
  const min_chars = parseInt((num?num.value:(sNum?sNum.value:120))||'0',10)||0;
  const gate_on = gate?gate.checked:false;
  const min_score = parseInt((sm?sm.value:2000)||'0',10)||0;
  if(box) box.checked=hide_social;
  if(num) num.value=min_chars;
  if(sBox) sBox.checked=hide_social;
  if(sNum) sNum.value=min_chars;
  if(sm) sm.value=min_score;
  try{
    await postSettings({news_min_chars:min_chars, news_hide_social:hide_social,
                        social_score_filter:gate_on, social_score_min:min_score});
    toast(gate_on?('حداقل لایک اجتماعی: '+toFa(min_score)+' آپ‌ووت')
                 :('فیلتر لایک اجتماعی خاموش است · '+(hide_social?'خبرهای اجتماعی حذف شد':'حداقل '+toFa(min_chars)+' کاراکتر')));
    loadData();
  }catch(e){ toast('ذخیره نشد — دوباره تلاش کن'); }
}
/* the toolbar/settings controls read their state from the saved config */
function paintHygiene(){
  const cfg=(DATA&&DATA.config)||{};
  const hide=!!cfg.news_hide_social, min=(cfg.news_min_chars==null?120:cfg.news_min_chars);
  const gate=!!cfg.social_score_filter, smin=(cfg.social_score_min==null?2000:cfg.social_score_min);
  [['fHideSocial','fMinChars'],['setHideSocial','setMinChars']].forEach(function(p){
    const b=document.getElementById(p[0]), n=document.getElementById(p[1]);
    if(b) b.checked=hide;
    if(n&&document.activeElement!==n) n.value=min;
  });
  const gateEl=document.getElementById('fSocialGate'), sminEl=document.getElementById('fSocialMin');
  if(gateEl) gateEl.checked=gate;
  if(sminEl&&document.activeElement!==sminEl) sminEl.value=smin;
  const info=document.getElementById('hiddenInfo');
  if(info) info.textContent=toFa((DATA&&DATA.hidden_count)||0);
  const btn=document.getElementById('hiddenRestore');
  if(btn) btn.disabled=!((DATA&&DATA.hidden_count)||0);
}
function restoreHidden(){
  if(typeof confirm==='function' && !confirm('همهٔ خبرهای حذف‌شده برگردند؟')) return;
  fetch('/api/article/restore',{method:'POST'}).then(r=>r.json()).then(d=>{
    if(d&&d.ok){ toast('بازگردانی شد: '+toFa(d.restored||0)+' خبر'); loadData(); }
    else toast('بازگردانی نشد');
  }).catch(()=>toast('خطای شبکه در بازگردانی'));
}

/* ── article modal ── */
async function openArticle(id, fa){
  window._activeArtId = id;
  const ov=document.getElementById('artOverlay'); ov.classList.add('open');
  const b=document.getElementById('artBody');
  const url='/api/article/'+id+(fa?'?fa=1':'');
  const waitTxt=fa?'🇮🇷 در حال ترجمهٔ متن به فارسی…':'📝 متن کامل در حال آماده‌سازی…';
  const spinBox=`<div style="display:flex;align-items:center;gap:10px;color:var(--ink-3);font-size:12.5px;padding:6px 0"><span class="spinner"></span><span id="artLoadTxt">${waitTxt}</span></div>`;
  /* paint what we already have instantly — the full text is extracted
     OFF-THREAD server-side and answered with pending:true, so we poll
     instead of blocking the modal for 8-15s */
  try{
    const quick=findArticle(id)||getBmarkMeta()[id];
    if(quick){
      b.innerHTML=`
        <h2>${esc(quick.title_fa||quick.title)}</h2>
        ${quick.title_fa?`<div class="h2en">${esc(quick.title)}</div>`:''}
        <div class="mmeta">
          <span>📰 ${esc(quick.source||'')}</span>
          ${quick.datetime_fa?`<span>🗓 ${esc(quick.datetime_fa)}</span>`:''}
          ${quick.credibility!=null?credBadge(quick.credibility):''}
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-block:2px 6px">
          ${fa?`<button class="btn sm ghost" onclick="openArticle(${jsArg(id)})">🇬🇧 نمایش متن اصلی</button>`
              :`<button class="btn sm on" onclick="openArticle(${jsArg(id)},true)">🇮🇷 ترجمهٔ فارسی متن</button>`}
        </div>
        ${quick.summary_fa||quick.summary?`<div class="msec"><h4>📄 خلاصه</h4><p class="fa">${esc(quick.summary_fa||quick.summary)}</p></div>`:''}
        <div class="msec"><h4>📝 متن کامل خبر</h4>${spinBox}</div>`;
    } else {
      b.innerHTML='<div class="empty" style="padding:30px;text-align:center">'+spinBox+'</div>';
    }
  }catch(e){ b.innerHTML='<div class="empty" style="padding:30px;text-align:center">'+spinBox+'</div>'; }
  const gen = ++_ART_GEN;
  let tries=0;
  const poll=async()=>{
    if (_ART_GEN !== gen) return;
    let d;
    try{ d=await (await fetch(url)).json(); }
    catch(e){
      if (_ART_GEN !== gen) return;
      b.innerHTML='<div class="empty">خطا در دریافت خبر</div>'; return;
    }
    if (_ART_GEN !== gen) return;
    if(d.pending && tries++<20){
      const t=document.getElementById('artLoadTxt');
      if(t) t.textContent=waitTxt+' ('+toFa(tries)+')';
      setTimeout(poll,1200); return;
    }
    render(d);
  };
  const render=(d)=>{
    try{
    const flags=(d.flags||[]).length?`<div class="flags">⚠️ پرچم‌های اعتبارسنجی: ${d.flags.map(esc).join(' — ')}</div>`:'';
    const rel=(d.related||[]).map(x=>`<a class="relrow" href="javascript:void(0)" onclick="openArticle(${jsArg(x.id)});event.stopPropagation()"><span class="reltitle">${esc(x.title)}</span><span class="relsrc">${esc(x.source)}</span>${x.full?`<span class="relfull" title="متن کامل این خبر آماده است">${ic('file')} متن کامل</span>`:''}<span class="relgo">↗</span></a>`).join('');
    const assets=(d.assets||[]).map(s=>`<span class="badge b-asset">${esc(FA_ASSET[s]||s)}</span>`).join(' ');
    const c=d.content||{};
    /* ?fa=1: the server returns content_fa once the background translation
       lands; until then it answers pending and the poll re-renders with it */
    const paras = (fa && Array.isArray(d.content_fa) && d.content_fa.length)
      ? d.content_fa : (c.paragraphs||[]);
    const searchUrl='https://www.google.com/search?q='+encodeURIComponent('"'+d.title+'" '+d.source);
    /* the chip under the heading used to read "۰ کلمه · ۰ پاراگراف" which made a
       blocked publisher look like a broken page; say what actually happened and
       put the publisher's link where the text would be */
    const statusChip = paras.length
      ? `${toFa(c.word_count||0)} کلمه · ${toFa(paras.length)} پاراگراف`
      : '';
    const shortNoteHtml = (c.word_count<60) && paras.length
      ? (/^reddit/.test(c.via||'')
          ? `<div style="font-size:11px;color:var(--ink-3);margin-top:8px">ℹ️ این پست ردیت تصویری/لینکی است و متن کاملی در خودِ پست ندارد؛ همین چند سطر و نظرات بحث از همانجاست. لینک اصلی را باز کنید.</div>`
          : '')
      : '';
    const bodyHtml = paras.length
      ? paras.map(p=>`<p class="${fa && Array.isArray(d.content_fa) && d.content_fa.length ? 'fa' : 'en'}">${esc(p)}</p>`).join('')
      : (d.summary_full
          ? `<p class="en" style="font-size:14px;line-height:1.8">${esc(d.summary_full)}</p>`
          : `<div class="nobody">
               <div class="nobody-cta">
                 <a class="btn ghost sm" href="${attr(safeUrl((c&&c.resolved_url)||d.link))}" target="_blank" rel="noopener">🔗 مشاهده در ${esc(d.source)}</a>
                 <a class="btn ghost sm" href="${searchUrl}" target="_blank" rel="noopener">🔍 جستجوی متن خبر</a>
               </div>
             </div>`);
    const relNote = paras.length
      ? `${toFa((d.related||[]).length)} خبر هم‌موضوع`
      : 'اخبار مرتبط هم‌موضوع';
    b.innerHTML=`
      <div class="row1" style="display:flex;gap:6px;flex-wrap:wrap">
        <span class="badge b-topic">${topicIc(d.topic)} ${esc(FA_TOPIC[d.topic]||'')}</span>${assets}
        ${(DATA.kind_labels||{})[d.source_kind]?`<span class="badge b-kind">${DATA.kind_labels[d.source_kind]}</span>`:''}
      </div>
      <h2>${esc(d.title_fa||d.title)}</h2>
      ${d.title_fa?`<div class="h2en">${esc(d.title)}</div>`:''}
      <div class="mmeta">
        <span>📰 ${esc(d.source)}${d.via?(' · از طریق '+esc(d.via)):''}</span>
        <span>✍️ ${esc(d.author||'—')}</span>
        <span>🗓 ${esc(d.datetime_fa||d.published_str||'')}</span>
        ${credBadge(d.credibility)}
      </div>
      ${flags}
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-block:0 10px">
        ${fa?`<button class="btn sm ghost" onclick="openArticle(${jsArg(id)})">🇬🇧 نمایش متن اصلی (English)</button>`
            :`<button class="btn sm on" onclick="openArticle(${jsArg(id)},true)">🇮🇷 ترجمهٔ فارسی متن کامل</button>`}
      </div>
      ${(d.summary_full_fa||d.summary_full)?`<div class="msec"><h4>📄 خلاصه (فارسی)</h4><p class="fa">${esc(d.summary_full_fa||'')}</p>
        ${!d.summary_full_fa&&d.summary_full?`<p class="en" style="font-size:12px;color:var(--ink-3)">${esc(d.summary_full)}</p>`:''}
        <h4 style="margin-top:10px">📄 Original summary</h4><p class="en" style="font-size:12px;color:var(--ink-3)">${esc(d.summary_full||'—')}</p></div>`:''}
      <div class="msec">
        <h4><span>📝 متن خبر</span>
          <span style="font-size:10.5px;color:var(--ink-3)">${statusChip}</span></h4>
        <div class="scroll">${bodyHtml}</div>
        ${shortNoteHtml}
      </div>
      <a class="mlink" href="${attr(safeUrl((c&&c.resolved_url)||d.link))}" target="_blank" rel="noopener">🔗 مشاهده در ${esc(d.source)}</a>
      ${rel?`<div class="msec rel" style="margin-top:12px"><h4>🧩 اخبار مرتبط <span style="font-size:10.5px;color:var(--ink-3);font-weight:400">${relNote}</span></h4>${rel}</div>`:''}`;
    }catch(e){ b.innerHTML='<div class="empty">خطا در دریافت خبر</div>'; }
  };
  poll();
}
function closeModal(id){
  const el=document.getElementById(id);
  if(el) el.classList.remove('open');
}

/* ── reports ── */
function renderRepChips(){
  const list=orderedAssets();
  document.getElementById('repChips').innerHTML=list.map(s=>{
    const m=DATA.assets_meta[s]||{};
    return `<button class="chip ${UI.repSym===s?'on':''}" onclick="pickReport(${jsArg(s)})">${assetIc(s)} ${esc(faAssetName(s))}</button>`;
  }).join('');
  const n=document.getElementById('repChipsN');
  if(n) n.textContent='· '+toFa(list.length)+' دارایی';
  const nm=document.getElementById('repBtnName');
  if(nm&&UI.repSym) nm.textContent=faAssetName(UI.repSym);
}
/* the toolbar button names the open report; the picker itself lives in the sheet */
function setRepBtnName(sym){
  const nm=document.getElementById('repBtnName');
  if(nm) nm.textContent=faAssetName(sym);
}
function pickReport(sym, keepLang){
  UI.repSym=sym; if(!keepLang) UI.repLang='en';
  showView('reports', true);   // skipPick: never call back into pickReport
  renderRepChips();
  setRepBtnName(sym);
  if(typeof tbClose==='function') tbClose('repSheet');   /* pick → the sheet has done its job */
  const box=document.getElementById('repBox');
  box.innerHTML=`<div class="empty" style="display:flex;align-items:center;justify-content:center;gap:10px;padding:44px 0"><span class="spinner"></span>${UI.repLang==='fa'?'🇮🇷 در حال ترجمهٔ گزارش به فارسی…':'⏳ در حال ساخت گزارش…'}</div>`;
  const url='/api/report/'+sym+(UI.repLang==='fa'?'?lang=fa':'');
  window.__repPending=sym;
  fetch(url).then(r=>r.json()).then(rep=>{
    window.__repPending=null;
    if(rep.error){ box.innerHTML=`<div class="empty">خطا در تولید گزارش: ${esc(rep.error)}</div>`; return; }
    UI.repSections=rep.sections;
    const fa = UI.repLang==='fa';
    const mv = (rep.sections.find(s=>s[0]==='meta')||[null,{}])[1];
    const mm = (DATA&&DATA.assets_meta&&DATA.assets_meta[rep.symbol])||{};
    const lv0 = liveOf(rep.symbol);
    const p0 = (lv0&&lv0.price!=null)?lv0.price:mv.price;
    const c0 = (lv0&&lv0.change_24h!=null)?lv0.change_24h:mv.change_24h;
    const toc=[];                 /* section jump chips: a long report stops being a scroll hunt */
    let doc='';
    for(const [kind,val] of rep.sections){
      if(kind==='meta') continue;               /* the hero carries it now */
      if(kind==='h'){
        const id='repsec-'+(toc.length+1);
        const label=fa?(val.fa||val.en):val.en;
        toc.push({id:id, label:label});
        doc+=`<h3 id="${id}" class="rep-sec">${esc(label)}</h3>`;
      }
      else if(kind==='p'){
        const t = fa ? (val.fa || val.en) : val.en;
        doc+=`<p class="${fa?'fa':'en'}">${mdLite(t)}</p>`;
        if(fa && !val.fa) doc+=`<p class="fa" style="color:var(--warn);font-size:11px">ترجمه این بخش در دسترس نبود؛ متن انگلیسی نمایش داده شد.</p>`;
      }
      else if(kind==='cites'){
        const items=val.items||[];
        if(!items.length) continue;
        /* the sources sit behind one button — closed by default, so the report
           reads as analysis, not as a bibliography */
        doc+=`<section class="cites">
          <button class="cites-btn" onclick="toggleCites(this)" aria-expanded="false">
            <span class="cb-ic">${ic('bookmark')}</span>
            <span class="cb-t">منابع این بخش</span>
            <span class="cb-n">${toFa(items.length)} خبر</span>
            <span class="cb-a">نمایش منابع</span>
          </button>
          <div class="cites-body">
            <div class="cites-list">${items.map(it=>citeHTML(it,fa)).join('')}</div>
          </div>
        </section>`;
      }
    }
    box.innerHTML=`<div class="rep-shell">
      <header class="rep-hero">
        <div class="rh-main">
          <span class="rh-icon" aria-hidden="true">${assetIc(rep.symbol||sym)}</span>
          <div style="min-inline-size:0">
            <h2>${esc(fa?(mv.title_fa||mv.title):(mv.title||mm.fa||rep.symbol))} <span class="rh-sym ltr">${esc(rep.symbol||sym)}</span></h2>
            <div class="rh-sub">
              <span>${ic('clock')} ${esc(fa?(mv.asof_fa||mv.asof):(mv.asof||''))}</span>
              <span>${ic('news')} ${toFa(mv.news_used||0)} خبر استنادشده از ${toFa((mv.sources_used||[]).length)} منبع</span>
            </div>
          </div>
        </div>
        <div class="rh-side">
          <div class="ch-price">
            <span class="p" id="chartLivePrice">${fmtPrice(p0)}</span>
            <span class="c ${c0==null?'':(c0>=0?'up':'dn')}" id="chartLiveChg">${c0==null?'':((c0>=0?'▲ +':'▼ ')+num(c0,2)+'%')}</span>
          </div>
          <div class="rh-actions">
            <button class="btn ghost sm" onclick="copyReport()" title="فقط متن تحلیل کپی می‌شود">${ic('copy')} کپی متن</button>
            <button class="btn ${fa?'on':'ghost'} sm" onclick="toggleLang(${jsArg(sym)},'fa')">ترجمهٔ فارسی</button>
            <button class="btn ${fa?'ghost':'on'} sm" onclick="toggleLang(${jsArg(sym)},'en')">English</button>
          </div>
        </div>
      </header>
      <div class="rep-layout">
        <section class="rep-doc" id="repDoc" tabindex="0" aria-label="متن گزارش تحلیلی">
          ${toc.length>1?`<nav class="rep-toc" aria-label="پرش به بخش‌ها">${toc.map(t=>`<button onclick="jumpRepSec(${jsArg(t.id)})">${esc(t.label)}</button>`).join('')}</nav>`:''}
          ${doc}
        </section>
        <aside class="rep-side" id="chartCol">
          <div id="chartBoxHost"></div>
          <div class="chartbox repfng" id="repFng"></div>
        </aside>
      </div>
    </div>`;
    window.__rep = rep;
    /* the document is one language at a time; the stylesheet keys the heading
       and the section-chip row off this so an English report reads LTR and a
       Persian one stays RTL (see .rep-doc[data-lang]) */
    const docEl=document.getElementById('repDoc');
    if(docEl) docEl.setAttribute('data-lang', fa?'fa':'en');
    renderChartInto(rep);
    loadRepFng(rep.symbol||sym);
  }).catch(()=>{ window.__repPending=null; box.innerHTML='<div class="empty">خطا در دریافت گزارش</div>'; });
}
/* the chart column: the panel plus the Fear & Greed box under it, so a
   timeframe change never wipes the gauge out of the page */
function renderChartInto(rep){
  const host=document.getElementById('chartBoxHost');
  if(!host||!rep) return;
  host.innerHTML=renderChartPanel(rep.chart);
  afterChartRender();
}
/* the panel is the widget — there is nothing else to mount, and it does not
   depend on the server having candle history for the asset */
function afterChartRender(){
  const rep=window.__rep; if(!rep) return;
  if(rep.symbol!==TVW.sym) TVW.sym=rep.symbol;
  mountTVChart(true);
}
function toggleLang(sym,lang){
  if(UI.repLang===lang) return;
  UI.repLang=lang; pickReport(sym,true);
}
function mdLite(t){ return esc(t).replace(/\*\*(.+?)\*\*/g,'<b>$1</b>'); }
/* «کپی متن» = analysis prose only (headings + paragraphs). No citation boxes,
   no links — exactly what the user asked for. */
function reportText(rep, fa){
  let out='';
  for(const [kind,val] of (rep.sections||[])){
    if(kind==='meta'){ out+=`# ${fa?(val.title_fa||val.title):val.title}\n`; out+=`${fa?(val.asof_fa||val.asof):val.asof} | ${val.price}\n`; }
    else if(kind==='h') out+=`\n## ${fa?val.fa:val.en}\n`;
    else if(kind==='p') out+=(fa?(val.fa||val.en):val.en)+'\n';
    /* kind==='cites' → never copied */
  }
  return out.replace(/\n{3,}/g,'\n\n').trim()+'\n';
}
function copyReport(){
  const fa=UI.repLang==='fa';
  navigator.clipboard.writeText(reportText(window.__rep||{sections:[]}, fa))
    .then(()=>toast('متن تحلیل کپی شد ✓'));
}

/* ── chart panel — TradingView and nothing else ───────────────────────────
   The old panel carried a second, hand-drawn chart with Bollinger bands, EMAs,
   support/resistance and an RSI/MACD pane. It is gone: two charts meant two
   sources of truth for the same asset, and the drawn one needed the server's
   price history before it could show anything at all. What remains is the
   official TradingView embed — real candles, its own intervals, indicators and
   drawing tools — plus a link out for when the embed is blocked. */
function renderChartPanel(c){
  const s=((c&&c.sym)||TVW.sym||'').toUpperCase();
  return `<div class="chartbox" id="chartBox">
    <div class="chart-head">
      <h3>${ic('chart')} نمودار ${assetIc(s)} ${esc(faAssetName(s))}
        <span class="ch-sym ltr">${esc(s)}</span></h3>
      <span class="chart-live" id="tvLiveTag">${ic('clock')} در حال اتصال…</span>
      <div class="chart-tools">
        <a class="btn ghost sm" href="https://www.tradingview.com/chart/?symbol=${encodeURIComponent(tvSymbolFor(s))}"
           target="_blank" rel="noopener">${ic('external')} باز کردن در تریدینگ‌ویو</a>
        <button class="btn ghost sm" id="tvFullBtn" onclick="toggleTvFull()">${ic('expand')} بزرگ‌نمایی</button>
      </div>
    </div>
    <div class="tvwrap" id="tvwrap"><div id="tvholder"></div></div>
    <div class="tvfail" id="tvfail" style="display:none"></div>
  </div>`;
}
/* merge the live quote into the chart head + last point of the price line */
function updateChartLive(){
  /* the widget streams its own candles; what this keeps live is the quote line
     above the panel and the connection pill next to its title */
  const rep=window.__rep; if(!rep) return;
  const lv=liveOf(rep.symbol), tag=document.getElementById('tvLiveTag');
  const p=document.getElementById('chartLivePrice'), chg=document.getElementById('chartLiveChg');
  if(lv&&lv.price!=null&&p){
    const prev=+p.dataset.v||((rep.chart&&rep.chart.price)||null);
    p.textContent=fmtPrice(lv.price);
    if(prev!=null) flash(p, lv.price-prev);
    p.dataset.v=lv.price;
    if(chg&&lv.change_24h!=null){ chg.textContent=(lv.change_24h>=0?'▲ +':'▼ ')+num(lv.change_24h,2)+'%'; chg.className='c '+(lv.change_24h>=0?'up':'dn'); }
  }
  if(!tag) return;
  if(document.querySelector('#tvholder iframe')) tag.innerHTML='<span class="live-dot"></span>لایو';
  else if(!lv) tag.textContent='قیمت لحظه‌ای در دسترس نیست';
}
async function removeSrc(key){ await postSettings({remove_sources:[key]}); toast('منبع حذف شد'); loadData(); }
async function addSource(){
  const name=document.getElementById('newSrcName').value.trim();
  const rss=document.getElementById('newSrcUrl').value.trim();
  if(!name||!rss.startsWith('http')){ toast('نام و آدرس RSS معتبر وارد کنید'); return; }
  await postSettings({add_source:{name,rss}});
  document.getElementById('newSrcName').value=''; document.getElementById('newSrcUrl').value='';
  toast('منبع اضافه شد — در چرخه بعدی خوانده می‌شود'); loadData();
}

/* ── assets manager ── */
function renderAssetTable(){
  const box=document.getElementById('assetTableBox'); if(!box||!DATA) return;
  let rows='';
  for(const sym of orderedAssets()){
    const m=DATA.assets_meta[sym]||{};
    const d=(DATA.market||{})[sym]||{};
    const lv=liveOf(sym);
    const price=lv?lv.price:d.price;
    rows+=`<tr data-sym="${esc(sym)}">
      <td>${assetIc(sym)} ${esc(faAssetName(sym))}</td>
      <td>${esc(m.name||'')}</td>
      <td class="ltr">${esc(m.yahoo||'—')}</td>
      <td class="ltr">${esc(m.coingecko||'—')}</td>
      <td class="ltr"><span class="p">${fmtPrice(price)}</span>${lv?' <span class="live-dot"></span>':''}${m.custom&&d.price==null&&!lv?' <span style="color:var(--cu-hi);font-size:10px" title="نماد Yahoo برای این دارایی داده نداد — آن را اصلاح کن (مثلاً LINK-USD)">'+ic('warn')+'</span>':''}</td>
      <td class="ltr">${toFa(DATA.asset_counts[sym]||0)}</td>
      <td>${m.custom?`<button class="btn ghost sm" onclick="removeAsset(${jsArg(sym)})">حذف</button>`:'<span style="font-size:10px;color:var(--ink-3)">پیش‌فرض</span>'}</td>
    </tr>`;
  }
  box.innerHTML=`<table class="asset-table">
    <thead><tr><th>دارایی</th><th>نام</th><th>نماد Yahoo</th><th>CoinGecko</th><th>قیمت</th><th>خبر</th><th></th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}
async function addAsset(){
  const payload={add_asset:{
    symbol:document.getElementById('naSym').value.trim(),
    fa:document.getElementById('naFa').value.trim(),
    name:document.getElementById('naName').value.trim(),
    yahoo:document.getElementById('naYahoo').value.trim(),
    coingecko:document.getElementById('naCg').value.trim(),
    keywords:document.getElementById('naKw').value.trim()
  }};
  if(!payload.add_asset.symbol||!payload.add_asset.yahoo){ toast('نماد و نماد Yahoo لازم است'); return; }
  await postSettings(payload);
  ['naSym','naFa','naName','naYahoo','naCg','naKw'].forEach(i=>document.getElementById(i).value='');
  toast('دارایی اضافه شد — با بروزرسانی بعدی قیمت و خبر آن می‌آید');
  await loadData(); doRefresh();
}
async function removeAsset(sym){
  await postSettings({remove_assets:[sym]});
  toast('دارایی حذف شد'); await loadData();
}

/* ── settings ── */
function renderSettings(){
  const c=DATA.config;
  document.getElementById('setInterval').value=String(c.interval);
  document.getElementById('setAge').value=String(DATA.rules.max_age_hours);
  document.getElementById('setAutoRep').checked=!!c.auto_reports;
  document.getElementById('assetToggles').innerHTML=orderedAssets().map(s=>{
    const m=DATA.assets_meta[s]||{};
    const on=c.assets.includes(s);
    return `<button class="chip ${on?'on':''}" data-sym="${s}" onclick="this.classList.toggle('on')">${assetIc(s)} ${esc(faAssetName(s))}</button>`;
  }).join('');
}
async function saveSettings(){
  const assets=[...document.querySelectorAll('#assetToggles .chip.on')].map(b=>b.dataset.sym);
  if(!assets.length){ toast('حداقل یک دارایی انتخاب کنید'); return; }
  await postSettings({interval:+document.getElementById('setInterval').value,
                      report_max_age_hours:+document.getElementById('setAge').value,
                      assets, auto_reports:document.getElementById('setAutoRep').checked,
                      news_min_chars:parseInt((document.getElementById('setMinChars')||{}).value||'0',10)||0,
                      news_hide_social:!!((document.getElementById('setHideSocial')||{}).checked)});
  toast('تنظیمات ذخیره شد ✓'); loadData();
}
async function postSettings(payload){
  const r=await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  return r.json();
}

/* ── refresh / toast ── */
async function doRefresh(){
  const rb=document.getElementById('refreshBtn'); rb.disabled=true; rb.innerHTML=ic('clock')+' ارسال درخواست…';
  try{ await fetch('/api/refresh',{method:'POST'}); toast('چرخه بروزرسانی شروع شد'); }
  finally{ setTimeout(()=>{rb.disabled=false;rb.innerHTML=ic('refresh')+' Refresh';},1500); }
}
function toast(msg){
  const t=document.getElementById('toast'); t.textContent=msg; t.style.display='block';
  clearTimeout(t._h); t._h=setTimeout(()=>t.style.display='none',2600);
}
document.addEventListener('keydown',e=>{ if(e.key==='Escape'){ closeModal('artOverlay'); closeModal('blurbOverlay'); closeModal('calDocOverlay'); } });
document.getElementById('ibSources').onclick=()=>showView('sources');
document.getElementById('ibAssets').onclick=()=>showView('assets');

/* ═══════════ economic calendar & market context (/api/econ) ═══════════ */
let ECON=null, ECON_AT=0;
async function loadCalendar(){
  try{
    const r=await fetch('/api/econ'); const d=await r.json();
    ECON=d; ECON_AT=Date.now(); window.__MACRO=d.macro||[]; renderCalendar();
  }catch(e){ renderCalendar(); }
}
const FA_DAY={'Saturday':'شنبه','Sunday':'یکشنبه','Monday':'دوشنبه','Tuesday':'سه‌شنبه','Wednesday':'چهارشنبه','Thursday':'پنجشنبه','Friday':'جمعه'};
const FA_MONTH={'Farvardin':'فروردین','Ordibehesht':'اردیبهشت','Khordad':'خرداد','Tir':'تیر','Mordad':'مرداد','Shahrivar':'شهریور','Mehr':'مهر','Aban':'آبان','Azar':'آذر','Dey':'دی','Bahman':'بهمن','Esfand':'اسفند'};
function isoOf(d){ return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'); }
function todayIso(){ return isoOf(new Date()); }
/* The selected day is the single source of truth: the day strip, the board and
   both side widgets all derive from it, so nothing can disagree about which
   day is on screen. Weeks move by moving the day. */
let CAL = {day:null};
function shiftCalWeek(n){ CAL.day=addDays(CAL.day||tzNow(),7*n); renderCalendar(); }
function gotoCalToday(){ CAL.day=tzNow(); renderCalendar(); }
function jumpToNextEventDay(){
  const days=[...new Set((window.__calPool||[]).map(e=>e._day))].sort();
  if(!days.length) return;
  CAL.day = days.find(d=>d>=tzNow()) || days[days.length-1];
  renderCalendar();
}
function faDayBox(isoDay){
  /* the economic calendar reads in English, over the Western release week */
  try{
    const d=new Date(isoDay+'T12:00:00Z');
    return esc(d.toLocaleDateString('en-GB',{weekday:'long',month:'short',day:'numeric',timeZone:'UTC'}));
  }catch(e){ return esc(isoDay); }
}
/* ── timezone handling ────────────────────────────────────────────────────
   The server sends every row with an exact UTC epoch (`ts`) and the UTC clock
   in `time_str`. Both are re-formatted here for whichever zone the reader
   picked, so switching the selector moves every time — and the day buckets —
   together. Formatters are memoised because a week is 300+ rows. */
const TZ_FMT={};
function tzFmt(zone,kind){
  const k=zone+'|'+kind;
  if(TZ_FMT[k]) return TZ_FMT[k];
  let f=null;
  try{
    if(kind==='day')  f=new Intl.DateTimeFormat('en-CA',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit'});
    if(kind==='time') f=new Intl.DateTimeFormat('en-GB',{timeZone:zone,hour:'2-digit',minute:'2-digit',hour12:false});
    if(kind==='dow')  f=new Intl.DateTimeFormat('en-GB',{timeZone:zone,weekday:'short'});
    if(kind==='full') f=new Intl.DateTimeFormat('en-GB',{timeZone:zone,weekday:'short',month:'short',day:'numeric'});
  }catch(e){ f=null; }
  TZ_FMT[k]=f;
  return f;
}
function calTz(){ const s=document.getElementById('calTz'); return (s&&s.value)||'Asia/Tehran'; }
function tzDay(ts){ const z=calTz(), f=tzFmt(z,'day'), d=new Date(ts*1000);
  return f?f.format(d):d.toISOString().slice(0,10); }
/* same zone, but written the way the rest of the calendar reads its dates */
function tzDayFa(ts){ const f=tzFmt(calTz(),'full'), d=new Date(ts*1000);
  return f?f.format(d):tzDay(ts); }
function tzClock(ts){ const z=calTz(), f=tzFmt(z,'time'), d=new Date(ts*1000);
  const t=f?f.format(d):d.toISOString().slice(11,16);
  return t==='24:00'?'00:00':t; }
function tzDow(ts){ const f=tzFmt(calTz(),'dow'), d=new Date(ts*1000); return f?f.format(d):''; }
function tzNow(){ return tzDay(Date.now()/1000); }
function addDays(isoDay,n){
  const t=Date.parse(isoDay+'T00:00:00Z')+n*86400000;
  return new Date(t).toISOString().slice(0,10);
}
function shortDay(isoDay){
  /* day-strip cell: one weekday letter over the day number (M 21) */
  const d=new Date(isoDay+'T12:00:00Z');
  let dow='';
  try{ dow=d.toLocaleDateString('en-GB',{weekday:'narrow',timeZone:'UTC'}); }catch(e){ dow=''; }
  return {dow:dow, num:String(d.getUTCDate())};
}
function monOf(isoDay){
  const d=new Date(isoDay+'T00:00:00Z');
  const off=(d.getUTCDay()+6)%7;          /* Monday-first week, like the server */
  return addDays(isoDay,-off);
}
function calCountdown(ts, withSeconds){
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
}
function impClass(v){ return v==='High'?'h':(v==='Medium'?'m':(v==='Holiday'?'hol':'l')); }
function impRank(v){ return v==='High'?0:(v==='Medium'?1:(v==='Low'?2:3)); }
const CAL_IMP_LABEL={High:'High',Medium:'Medium',Low:'Low',Holiday:'Holiday'};
/* the event explainer stays Persian — that is the part meant to be read */
const CAL_IMP_FA={High:'بالا',Medium:'متوسط',Low:'کم',Holiday:'تعطیل'};
/* the sessions rail names its cities in the server's English config — shown in Persian */
/* market sessions read in English too (the names come off the server config) */
const SESSION_FA={'Sydney':'Sydney','Tokyo':'Tokyo','London':'London','New York':'New York','Frankfurt':'Frankfurt','Shanghai':'Shanghai','Hong Kong':'Hong Kong'};
function renderCalendar(){
  const box=document.getElementById('calDays'), cd=document.getElementById('calCountdown');
  if(!box) return;
  if(!ECON){ box.innerHTML='<div class="empty">Loading the calendar…</div>'; return; }
  window.__ECON_FA=ECON.fng_fa||{};
  if(ECON.fng&&ECON.fng.now!=null) window.__FNG=ECON.fng;

  /* pool both loaded weeks (deduped) — the server sends exact UTC epochs, and
     every derived value below (day bucketing, clock, sorting) follows the
     timezone selector, never the UTC clock printed by the server */
  const tz=calTz();
  const pool=[], seen={};
  [ECON.calendar, ECON.calendar_next].forEach(function(src){
    ((src&&src.events)||[]).forEach(function(e){
      const k=e.ts+'|'+e.title+'|'+(e.country||'');
      if(seen[k]) return; seen[k]=1;
      e._day=tzDay(e.ts); e._released=!!(e.actual||e.past);
      e._key = (e.ts||0) + '_' + (e.title||'').replace(/[^a-zA-Z0-9]/g,'').slice(0,20);
      pool.push(e);
    });
  });
  pool.sort((a,b)=>a.ts-b.ts);
  window.__calPool=pool;

  if(!CAL.day) CAL.day=tzNow();
  const selDay=CAL.day, today=tzNow();
  /* only the two weeks the server actually loaded can be shown — say so instead
     of rendering a silent empty day */
  const todayBtn=document.getElementById('calBtnToday');
  if(todayBtn) todayBtn.classList.toggle('on', selDay===today);

  const impSel=document.getElementById('calImpact'), ccyBox=document.getElementById('calCurChips'),
        sSel=document.getElementById('calSort'), hp=document.getElementById('calHidePast'),
        qEl=document.getElementById('calQ');
  /* Currency is a multi-select: USD *and* EUR *and* JPY can be on at once, so
     the old single-value dropdown became a row of tick-boxes. Rebuilt only when
     the currency list present in the data actually changes. */
  if(!CAL.ccys) CAL.ccys=new Set();
  const ccys=[...new Set(pool.map(e=>e.country).filter(Boolean))].sort();
  if(ccyBox && ccyBox.dataset.keys!==ccys.join('|')){
    ccyBox.dataset.keys=ccys.join('|');
    ccyBox.innerHTML=ccys.map(c=>`<label class="ccy${CAL.ccys.has(c)?' on':''}">
        <input type="checkbox" value="${esc(c)}"${CAL.ccys.has(c)?' checked':''} onchange="toggleCalCcy(this)">
        <span>${esc(c)}</span></label>`).join('');
  }
  const impVal=impSel?impSel.value:'all', ccySet=CAL.ccys,
        srtVal=sSel?sSel.value:'time', hideRel=!!(hp&&hp.checked),
        q=(qEl?qEl.value:'').trim().toLowerCase();
  /* the toolbar is painted further down, once the day's rows have actually
     been filtered — its count is the number the reader is looking at */

  /* ── the week strip: 7 day boxes from the Monday of the selected week ── */
  const mon=monOf(selDay);
  const week=[]; for(let i=0;i<7;i++) week.push(addDays(mon,i));
  const byDay={}; pool.forEach(e=>{ (byDay[e._day]=byDay[e._day]||[]).push(e); });
  const strip=document.getElementById('calStrip');
  if(strip){
    strip.innerHTML=week.map(function(d){
      const evs=byDay[d]||[], hi=evs.filter(e=>e.impact==='High').length,
            md=evs.filter(e=>e.impact==='Medium').length;
      const s=shortDay(d);
      const dots='<span class="dots">'+
        (hi?`<i class="h"></i>${hi>1?`<i class="h"></i>`:''}`:(md?'<i class="m"></i>':''))+
        (evs.length?'<i></i>':'<i></i>')+'</span>';
      return `<button class="cal-day ${d===selDay?'on':''} ${d===today?'today':''} ${evs.length?'':'empty'}"
        role="tab" aria-selected="${d===selDay}" onclick="CAL.day='${d}';renderCalendar()">
        <span class="dow">${s.dow}</span><span class="dd">${s.num}</span>
        <span class="n">${evs.length}${hi?` · ${hi} high`:''}</span>${dots}</button>`;
    }).join('');
  }
  const wl=document.getElementById('calWeekLab');
  if(wl){
    const f=d=>{const x=new Date(d+'T12:00:00Z');
      return x.toLocaleDateString('en-GB',{month:'short',day:'numeric',timeZone:'UTC'});};
    wl.textContent=f(mon)+' – '+f(addDays(mon,6));
    wl.classList.toggle('is-now', week.indexOf(today)>=0);
  }
  const src=document.getElementById('calSrc');
  if(src) src.textContent='Source: '+((ECON.calendar&&ECON.calendar.source)||'—')+
    ' · times in '+tz;

  /* ── the day's rows: filter → sort → table ── */
  let evs=(byDay[selDay]||[]).slice();
  if(impVal==='High')        evs=evs.filter(e=>e.impact==='High');
  else if(impVal==='Medium') evs=evs.filter(e=>e.impact==='High'||e.impact==='Medium');
  else if(impVal==='Low')    evs=evs.filter(e=>e.impact!=='Holiday');
  if(ccySet&&ccySet.size) evs=evs.filter(e=>ccySet.has(e.country));
  if(hideRel) evs=evs.filter(e=>!e._released);
  if(q) evs=evs.filter(e=>(e.title+' '+(e.indicator||'')+' '+(e.country||'')).toLowerCase().indexOf(q)>=0);
  const releasedFirst=(a,b)=>(b._released?1:0)-(a._released?1:0)||a.ts-b.ts;
  if(srtVal==='impact') evs.sort((a,b)=>impRank(a.impact)-impRank(b.impact)||a.ts-b.ts);
  else if(srtVal==='released') evs.sort(releasedFirst);
  else evs.sort((a,b)=>a.ts-b.ts);
  window.__calDayCount=evs.length;
  if(typeof renderCalToolbar==='function') renderCalToolbar();   /* FILTER MODEL 3 toolbar */

  const rowHTML=function(e){
    const cls='cal-tr is-'+(e.impact==='Holiday'?'hol':impClass(e.impact))+
              (e._released?' released':' pending')+(e.past&&!e._released?' faded':'');
    const nums=e._released
      ? `<span class="c-num c-act ${e.better===1?'good':(e.better===-1?'bad':'')}"><b>${esc(e.actual_fmt||'—')}</b>${
           e.surprise!==null&&e.surprise!==undefined?`<span class="c-sur ${e.better===1?'good':(e.better===-1?'bad':'')}">${esc(e.surprise_fmt)}</span>`:''}</span>`
      : `<span class="c-num c-act sched">—</span>`;
    const blank=v=>!v||v==='—';
    const fcNum=`<span class="c-num c-fc${blank(e.forecast_fmt)?' sched':''}">${esc(e.forecast_fmt||'—')}</span>`;
    const pvNum=`<span class="c-num c-pv${blank(e.previous_fmt)?' sched':''}">${esc(e.previous_fmt||'—')}</span>`;
    const timer=!e._released
      ? `<span class="cal-timer" data-ts="${e.ts}">${calCountdown(e.ts,true)}</span>` : '';
    return `<div class="${cls}" data-ts="${e.ts}" data-key="${esc(e._key||'')}">
      <span class="c-time">${e.all_day?'All day':esc(tzClock(e.ts))}<small>${esc(e.all_day?'':tzDow(e.ts))}</small></span>
      <span class="c-ccy">${esc(e.country||'—')}</span>
      <span class="c-imp" title="Impact ${esc(CAL_IMP_LABEL[e.impact]||e.impact)}"><i class="imp-dot ${impClass(e.impact)}"></i><b class="imp-lab">${esc(CAL_IMP_LABEL[e.impact]||e.impact)}</b></span>
      <span class="c-ev"><span class="t">${esc(e.title)}</span>${
        e.period?` <span class="p">(${esc(e.period)})</span>`:''}${
        timer?` ${timer}`:''}${e.indicator&&e.indicator!=='Calendar'?`<span class="d">${esc(e.indicator)}</span>`:''}</span>
      ${nums}${fcNum}${pvNum}
      <button class="cal-info" onclick="openCalDoc(${jsArg(e._key)})" title="What this release is — explained in Persian"><svg class="ic"><use href="#i-info"/></svg> توضیح</button>
    </div>`;
  };
  const hiDay=evs.filter(e=>e.impact==='High').length;
  const relDay=evs.filter(e=>e._released).length;
  const head='<div class="cal-th">'+
    '<span>Time</span><span>Ccy</span><span>Impact</span><span>Event</span>'+
    '<span style="text-align:end">Actual</span><span style="text-align:end">Forecast</span>'+
    '<span style="text-align:end">Previous</span><span></span></div>';
  /* nothing registers a day tick any more — the calendar board is repainted by
     the render that got here, and the countdowns are the shared clock's job */
  if(!pool.length){
    box.innerHTML='<div class="empty">Calendar feed unavailable right now — try again in a minute.</div>';
  } else if(!evs.length){
    const loaded=[...new Set(pool.map(e=>e._day))].sort();
    const inWindow=selDay>=loaded[0]&&selDay<=loaded[loaded.length-1];
    box.innerHTML=`<div class="cal-board-h"><span class="d">${faDayBox(selDay)}</span>`+
      `<span class="cal-tz-chip">${esc(tz)}</span>`+
      `<span class="m">no events</span></div><div class="empty">`+
      (inWindow?'No event on this day with these filters.'
               :'No data loaded for this week — the dashboard keeps the current week and the next.')+
      `<br><button class="btn ghost sm" style="margin-block-start:14px" onclick="jumpToNextEventDay()">Jump to the nearest day with events ›</button></div>`;
  } else {
    box.innerHTML=`<div class="cal-board-h">
        <span class="d">${faDayBox(selDay)}</span>
        <span class="cal-tz-chip">${esc(tz)}</span>
        <span class="m">${evs.length} ${evs.length===1?'event':'events'} · ${relDay} released${hiDay?` · ${hiDay} high impact`:''}</span>
      </div>
      <div class="cal-tbl">${head}${evs.map(rowHTML).join('')}</div>`;
  }

  /* ── hero: next high-impact release + week counters ── */
  const upcoming=pool.filter(e=>e.ts>Date.now()/1000).sort((a,b)=>a.ts-b.ts);
  const hi=upcoming.filter(e=>e.impact==='High');
  const next=hi[0]||upcoming[0];
  const tt=document.getElementById('calHeroTtl');
  const nb=document.getElementById('cntEvents');
  if(nb){ if(hi.length){ nb.style.display='inline-block'; nb.textContent=String(hi.length); } else nb.style.display='none'; }
  const rel=document.getElementById('calReleased');
  window.__calHeroTick=null;
  const tick=function(){
    if(!next){ cd.textContent='No upcoming event in the loaded window'; if(tt) tt.textContent='—'; if(rel) rel.style.display='none'; return; }
    if(tt) tt.innerHTML=`<span class="ccy">${esc(next.country||'')}</span><span class="imp">Impact ${esc(CAL_IMP_LABEL[next.impact]||next.impact)}</span>${esc(next.title)}`;
    if(next.ts<=Date.now()/1000){
      const relRow=pool.filter(e=>e._released&&e.impact==='High').sort((a,b)=>b.ts-a.ts)[0];
      if(rel&&relRow){
        rel.style.display='flex';
        rel.innerHTML=`<span><svg class="ic"><use href="#i-check"/></svg></span> Just released: <b>${esc(relRow.title)}</b> `+
          (relRow.actual_fmt?`<span style="direction:ltr">actual <b>${esc(relRow.actual_fmt)}</b> vs forecast ${esc(relRow.forecast_fmt)}</span>`:'')+
          `<span class="ltr" style="opacity:.75">${esc(tzClock(relRow.ts))} ${esc(tz)}</span>`;
      }
      const after=pool.filter(e=>e.ts>Date.now()/1000&&e.impact==='High').sort((a,b)=>a.ts-b.ts)[0];
      cd.innerHTML=after?('Next high impact in <b>'+calCountdown(after.ts,false)+'</b> — '+esc(after.title))
                        :'No further high-impact event in the loaded window';
      return;
    }
    if(rel) rel.style.display='none';
    const when=tzDay(next.ts)===tzNow()?'today':faDayBox(tzDay(next.ts));   /* tzDay stays ISO: it is the bucket key */
    cd.innerHTML=`in <b>${calCountdown(next.ts,true)}</b> · ${esc(tzClock(next.ts))} ${esc(tz)} · ${esc(when)}`;
  };
  tick();
  /* the hero is a function now, not a timer: clockTick() calls it on the shared
     second, and re-rendering the calendar swaps the function shell */
  window.__calHeroTick=tick;

  const st=document.getElementById('calStats');
  if(st){
    const wk=pool.filter(e=>week.indexOf(e._day)>=0);
    const wkHi=wk.filter(e=>e.impact==='High').length;
    const wkRel=wk.filter(e=>e._released).length;
    const surplus=wk.filter(e=>e.better===1).length, shortf=wk.filter(e=>e.better===-1).length;
    st.innerHTML=[[wk.length,'events', ''],[wkHi,'high','hi'],[wkRel,'released','rel'],
                  [surplus,'beat','rel'],[shortf,'missed','hi']]
      .map(x=>`<span class="cal-stat ${x[2]}"><b>${x[0]}</b><span>${x[1]}</span></span>`).join('');
  }

  renderCalHigh(pool, selDay);
  renderSessions();
  renderEtfLive('etfLive2');
}

/* the high-impact releases OF THE DAY ON THE BOARD — not a second, longer list
   answering a different question. Same day as the table above it. */
function renderCalHigh(pool, day){
  const box=document.getElementById('calHighList'); if(!box) return;
  const lab=document.getElementById('calHighDay');
  if(lab) lab.textContent=faDayBox(day);
  const hi=pool.filter(e=>e._day===day&&e.impact==='High').sort((a,b)=>a.ts-b.ts);
  if(!hi.length){ box.innerHTML='<span class="hint">No high-impact release on this day.</span>'; return; }
  box.innerHTML=hi.map(e=>`<div class="cal-high-row">
      <div class="t">${esc(e.title)}</div>
      <div class="meta"><b class="js-cal-cd" data-ts="${e.ts}">${e._released?'released':calCountdown(e.ts,false)}</b>
        <span>${esc(tzClock(e.ts))} ${esc(calTz())}</span>
        <span>${esc(e.country||'')}</span></div>
      <button class="cal-info" style="margin-block-start:6px" onclick="openCalDoc(${jsArg(e._key)})"><svg class="ic"><use href="#i-info"/></svg> توضیح</button></div>`).join('');
}

/* every countdown on the calendar tab (rows, side rail, hero) is updated by
   clockTick() under the Clock — there used to be a second 1 s loop here */

/* ══ historical price reaction to a release (inside the calendar explainer) ══
   What a print does to the tape, not just what the print was. Per pairing,
   `dir` is the sign the asset takes when the print arrives ABOVE forecast
   (a hot CPI lifts the dollar and pressures bullion and crypto), and a print
   below forecast mirrors it; `typ.sd` / `typ.rel` are the typical surprise in
   absolute and relative terms, and `m15`/`h1` are the typical moves at minute
   15 and 60 — the first leg is front-loaded, because a release travels most of
   its distance in the first quarter hour. There is no live backtest endpoint,
   so every row the model produces is badged «مرجع»: the dates follow the
   indicator's own release cadence and the consensus is taken from this same
   calendar feed where it exists. The figures are a reference model, never a
   measurement of what actually happened. */
const CAL_REACT_RULES=[
  {id:'cpi', label:'شاخص قیمت مصرف‌کننده (تورم)', geos:['US'], cadence:'monthly', unit:'%', dec:1,
   lowerIsBetter:false, typ:{fc:0.3, sd:0.2, rel:0.6},
   match:[/\bcore cpi\b/i, /\bcpi\b/i, /consumer price index/i],
   assets:[{s:'DXY',dir:1,m15:0.22,h1:0.35},{s:'XAU',dir:-1,m15:0.48,h1:0.78},
           {s:'BTC',dir:-1,m15:0.70,h1:1.15},{s:'SPX',dir:-1,m15:0.32,h1:0.55},
           {s:'VIX',dir:1,m15:0.60,h1:0.95}]},
  {id:'ppi', label:'شاخص قیمت تولیدکننده (PPI)', geos:['US'], cadence:'monthly', unit:'%', dec:1,
   lowerIsBetter:false, typ:{fc:0.2, sd:0.2, rel:0.6},
   match:[/\bppi\b/i, /producer price/i],
   assets:[{s:'DXY',dir:1,m15:0.14,h1:0.24},{s:'XAU',dir:-1,m15:0.26,h1:0.42},
           {s:'BTC',dir:-1,m15:0.34,h1:0.62},{s:'SPX',dir:-1,m15:0.20,h1:0.34}]},
  {id:'nfp', label:'اشتغال غیرکشاورزی (NFP)', geos:['US'], cadence:'monthly', unit:'', dec:0,
   lowerIsBetter:false, typ:{fc:150000, sd:30000, rel:0.35},
   match:[/non-?farm payrolls?/i, /\bnfp\b/i],
   assets:[{s:'DXY',dir:1,m15:0.20,h1:0.34},{s:'XAU',dir:-1,m15:0.40,h1:0.72},
           {s:'BTC',dir:-1,m15:0.45,h1:0.85,mixed:true},
           {s:'SPX',dir:1,m15:0.28,h1:0.45,mixed:true}]},
  {id:'adp', label:'اشتغال بخش خصوصی ADP', geos:['US'], cadence:'monthly', unit:'', dec:0,
   lowerIsBetter:false, typ:{fc:120000, sd:25000, rel:0.35},
   match:[/\badp\b/i],
   assets:[{s:'DXY',dir:1,m15:0.10,h1:0.18},{s:'XAU',dir:-1,m15:0.18,h1:0.30},
           {s:'BTC',dir:-1,m15:0.22,h1:0.40}]},
  {id:'fomc', label:'نرخ بهره فدرال رزرو', geos:['US'], cadence:'6w', unit:'%', dec:2,
   lowerIsBetter:false, typ:{fc:0.25, sd:0.25, rel:0},
   match:[/fed(?:eral)? funds rate/i, /fomc/i, /fed (?:interest )?rate decision/i],
   assets:[{s:'DXY',dir:1,m15:0.30,h1:0.52},{s:'XAU',dir:-1,m15:0.62,h1:1.05},
           {s:'BTC',dir:-1,m15:0.95,h1:1.70},{s:'SPX',dir:-1,m15:0.45,h1:0.80},
           {s:'VIX',dir:1,m15:0.70,h1:1.15}]},
  {id:'claims', label:'مدعیان بیکاری هفتگی', geos:['US'], cadence:'weekly', dow:4, unit:'', dec:0,
   lowerIsBetter:true, typ:{fc:220000, sd:12000, rel:0.06},
   match:[/jobless claims/i, /unemployment claims/i],
   assets:[{s:'DXY',dir:-1,m15:0.06,h1:0.12},{s:'XAU',dir:1,m15:0.12,h1:0.22},
           {s:'SPX',dir:1,m15:0.10,h1:0.18,mixed:true},{s:'BTC',dir:1,m15:0.14,h1:0.26,mixed:true}]},
  {id:'crude', label:'ذخایر نفت خام (EIA)', geos:['US'], cadence:'weekly', dow:3, unit:'', dec:1,
   lowerIsBetter:true, typ:{fc:-1500000, sd:1000000, rel:0.6},
   match:[/crude oil inventories/i, /eia crude/i, /petroleum status/i],
   assets:[{s:'WTI',dir:-1,m15:0.85,h1:1.40},{s:'SPX',dir:1,m15:0.08,h1:0.14,mixed:true}]},
  {id:'retail', label:'خرده‌فروشی آمریکا', geos:['US'], cadence:'monthly', unit:'%', dec:1,
   lowerIsBetter:false, typ:{fc:0.3, sd:0.3, rel:0.6},
   match:[/retail sales/i],
   assets:[{s:'DXY',dir:1,m15:0.16,h1:0.28},{s:'SPX',dir:1,m15:0.22,h1:0.38},
           {s:'XAU',dir:-1,m15:0.22,h1:0.36},{s:'BTC',dir:1,m15:0.30,h1:0.55,mixed:true}]},
  {id:'gdp', label:'تولید ناخالص داخلی', geos:['US'], cadence:'quarterly', unit:'%', dec:1,
   lowerIsBetter:false, typ:{fc:2.0, sd:0.4, rel:0.3},
   match:[/\bgdp\b/i, /gross domestic product/i],
   assets:[{s:'DXY',dir:1,m15:0.16,h1:0.30},{s:'SPX',dir:1,m15:0.26,h1:0.44},
           {s:'XAU',dir:-1,m15:0.24,h1:0.40},{s:'BTC',dir:1,m15:0.32,h1:0.58,mixed:true}]},
  {id:'pmi', label:'شاخص مدیران خرید (ISM/PMI)', geos:['US'], cadence:'monthly', unit:'', dec:1,
   lowerIsBetter:false, typ:{fc:50, sd:1.0, rel:0.04},
   match:[/\bism\b/i, /\bpmi\b/i, /manufacturing index/i],
   assets:[{s:'DXY',dir:1,m15:0.14,h1:0.26},{s:'SPX',dir:1,m15:0.24,h1:0.40},
           {s:'XAU',dir:-1,m15:0.20,h1:0.34},{s:'BTC',dir:1,m15:0.28,h1:0.50,mixed:true}]},
  {id:'ecb', label:'نرخ بهره منطقهٔ یورو', geos:['EU'], cadence:'6w', unit:'%', dec:2,
   lowerIsBetter:false, typ:{fc:0.25, sd:0.25, rel:0},
   /* a rate decision only: “ECB Machado Speech” is not a policy surprise */
   match:[/ecb[^|]{0,24}rate decision/i, /ecb[^|]{0,24}(?:deposit|main refinanc)/i,
          /euro(?:pean)? central bank[^|]{0,24}rate/i, /deposit facility rate/i],
   assets:[{s:'DXY',dir:-1,m15:0.20,h1:0.36},{s:'XAU',dir:-1,m15:0.24,h1:0.42},
           {s:'BTC',dir:-1,m15:0.40,h1:0.70},{s:'SPX',dir:-1,m15:0.22,h1:0.38}]}
];
const CAL_REACT_ROWS=4;                 /* releases kept in the sample */
const CAL_REACT_FRONT=.35;              /* share of the move done by minute 15 */
/* kind → the sign the surprise carries in the rule's own direction map */
const CAL_REACT_KIND={pos:{sgn:1, fa:'بیشتر از انتظار'}, neg:{sgn:-1, fa:'کمتر از انتظار'}, flat:{sgn:0, fa:'مطابق انتظار'}};
function calReactRule(e){
  if(!e) return null;
  const hay=(e.title||'')+' '+(e.indicator||'')+' '+(e.category||'');
  for(const r of CAL_REACT_RULES){
    if(r.geos && e.geo && r.geos.indexOf(e.geo)<0) continue;
    if(r.match.some(rx=>rx.test(hay))) return r;
  }
  return null;
}
function calReactHash(s){ let h=0; for(let i=0;i<s.length;i++) h=(h*31+s.charCodeAt(i))|0; return Math.abs(h); }
/* calendar-event → a row of its own (real numbers straight off the feed) */
function calReactLiveRow(ev, rule){
  const kind=ev.surprise==null?'flat':(ev.surprise>0?'pos':(ev.surprise<0?'neg':'flat'));
  const sd=Math.abs(ev.surprise||0);
  const strength=sd?Math.max(.6,Math.min(1.6,.6+.35*(sd/(rule.typ.sd||1)))):0.5;
  return {ts:ev.ts, actual:ev.actual_n, forecast:ev.forecast_n, unit:ev.unit||rule.unit,
          dec:rule.dec, kind:kind, strength:strength, src:'live', title:ev.title||''};
}
/* reference rows: the indicator's own cadence, going back from the event date */
function calReactModelRows(rule, anchorTs, n){
  const out=[], base=new Date(anchorTs*1000);
  const KINDS=['pos','neg','pos','flat'];
  const off=calReactHash(rule.id)%4;
  for(let i=1;i<=n+1 && out.length<n;i++){
    const d=new Date(base.getTime());
    if(rule.cadence==='weekly'){
      d.setUTCDate(d.getUTCDate()-7*i);
      const want=rule.dow==null?3:rule.dow;
      while(d.getUTCDay()!==want) d.setUTCDate(d.getUTCDate()-1);
    } else if(rule.cadence==='monthly'){
      d.setUTCMonth(d.getUTCMonth()-i);
    } else if(rule.cadence==='quarterly'){
      d.setUTCMonth(d.getUTCMonth()-3*i);
    } else {  /* 6w — policy meetings */
      d.setUTCDate(d.getUTCDate()-42*i);
    }
    const ts=Math.floor(d.getTime()/1000);
    if(ts>=anchorTs) continue;
    const kind=KINDS[(i-1+off)%4];
    out.push({ts:ts, kind:kind, src:'model', unit:rule.unit, dec:rule.dec,
              strength:kind==='flat'?0.5:(kind==='pos'?1.0:0.85)});
  }
  return out;
}
function calReactRows(rule, e){
  const pool=[];
  const cal=(typeof ECON!=='undefined'&&ECON)?ECON.calendar:null;
  const events=(cal&&(cal.events||cal))||[];
  (Array.isArray(events)?events:[]).forEach(function(ev){
    if(!ev||ev.ts==null||ev.ts>=e.ts) return;
    if(ev.actual_n==null||ev.forecast_n==null) return;
    const hay=(ev.title||'')+' '+(ev.indicator||'')+' '+(ev.category||'');
    if(ev.geo&&rule.geos&&rule.geos.indexOf(ev.geo)<0) return;
    if(!rule.match.some(rx=>rx.test(hay))) return;
    pool.push(calReactLiveRow(ev,rule));
  });
  pool.sort((a,b)=>b.ts-a.ts);
  const rows=pool.slice(0,CAL_REACT_ROWS);
  const need=CAL_REACT_ROWS-rows.length;
  if(need>0) rows.push(...calReactModelRows(rule, e.ts, need));
  /* numbers for the reference rows: the live consensus when the feed has one,
     otherwise the indicator's typical print — the path is what is modelled */
  const fcBase=(typeof e.forecast_n==='number')?e.forecast_n:(rule.typ.fc||0);
  rows.forEach(function(r){
    if(r.forecast==null) r.forecast=fcBase;
    if(r.actual==null){
      const sgn=CAL_REACT_KIND[r.kind].sgn;
      /* magnitude of the modelled surprise: the rule's absolute floor, or a
         share of the consensus when the series is a different scale (jobless
         claims run in the hundreds of thousands, continuing claims in the
         millions — one fixed delta cannot serve both) */
      const sdEff=Math.max(rule.typ.sd||0, (rule.typ.rel||0)*Math.abs(fcBase||0));
      r.actual=Math.round((r.forecast + sgn*sdEff)*Math.pow(10,rule.dec))/Math.pow(10,rule.dec);
    }
    r.surp=Math.round((r.actual-r.forecast)*Math.pow(10,rule.dec))/Math.pow(10,rule.dec);
    r.react={};
    rule.assets.forEach(function(a){
      const sgn=CAL_REACT_KIND[r.kind].sgn;
      const dir=a.dir||1;
      r.react[a.s]={m15:a.m15*dir*sgn*r.strength, h1:a.h1*dir*sgn*r.strength};
    });
  });
  return rows;
}
function calReactMove(v){ return (v>0?'+':(v<0?'−':''))+toFa(Math.abs(v).toFixed(2))+'٪'; }
/* the calendar feed hands compact strings (“72K”, “-1.5M”, “0.3%”) but the
   parsed numbers are raw — a modelled print has to print the same way */
function calReactFmt(v, dec, unit){
  if(v==null) return '—';
  const a=Math.abs(v);
  if((unit||'').indexOf('%')>=0 || a<1000) return toFa(v.toFixed(dec))+(unit||'');
  if(a>=1e9) return toFa((v/1e9).toFixed(1))+'B';
  if(a>=1e6) return toFa((v/1e6).toFixed(1))+'M';
  return toFa((v/1e3).toFixed(0))+'K';
}
/* ── SVG mini-chart: a zero baseline with one path per release ── */
function calReactSvg(rows, sym, w, h){
  const padX=44, padY=14;
  const vals=rows.map(r=>(r.react[sym]||{}).h1||0).concat(rows.map(r=>(r.react[sym]||{}).m15||0));
  const max=Math.max(0.2, Math.max.apply(null, vals.map(v=>Math.abs(v))))*1.25;
  const x0=padX, x1=w-padX, midX=x0+(x1-x0)*CAL_REACT_FRONT;
  const yOf=v=>padY+(1-(v+max)/(2*max))*(h-2*padY);
  const zero=yOf(0);
  const parts=[];
  parts.push('<line class="cr-zero" x1="'+x0+'" y1="'+zero+'" x2="'+x1+'" y2="'+zero+'"/>');
  parts.push('<text class="cr-ax" x="'+(x0-6)+'" y="'+(yOf(max)+4)+'">+'+toFa(max.toFixed(1))+'</text>');
  parts.push('<text class="cr-ax" x="'+(x0-6)+'" y="'+(yOf(-max)+4)+'">−'+toFa(max.toFixed(1))+'</text>');
  rows.forEach(function(r, i){
    const p=r.react[sym]||{m15:0,h1:0};
    const cls=p.h1>0?'is-pos':(p.h1<0?'is-neg':'is-flat');
    const d='M'+x0+' '+zero.toFixed(1)+' L'+midX.toFixed(1)+' '+yOf(p.m15).toFixed(1)+' L'+x1+' '+yOf(p.h1).toFixed(1);
    parts.push('<path class="cr-path '+cls+'" d="'+d+'"><title>'+esc(tzDayFa(r.ts))+' — '+esc(CAL_REACT_KIND[r.kind].fa)+' · ۱۵د '+calReactMove(p.m15)+' · ۶۰د '+calReactMove(p.h1)+'</title></path>');
    parts.push('<circle class="cr-dot '+cls+'" cx="'+x1+'" cy="'+yOf(p.h1).toFixed(1)+'" r="2.6"><title>'+esc(calReactMove(p.h1))+'</title></circle>');
  });
  parts.push('<text class="cr-ax is-x" x="'+x0+'" y="'+(h-3)+'">انتشار</text>');
  parts.push('<text class="cr-ax is-x" x="'+midX+'" y="'+(h-3)+'" text-anchor="middle">+۱۵د</text>');
  parts.push('<text class="cr-ax is-x" x="'+x1+'" y="'+(h-3)+'" text-anchor="end">+۶۰د</text>');
  return '<svg class="cr-svg" viewBox="0 0 '+w+' '+h+'" role="img" aria-label="مسیر واکنش '
    +esc(faAssetName(sym))+' در ۶۰ دقیقهٔ پس از '+toFa(rows.length)+' انتشار اخیر">'+parts.join('')+'</svg>';
}
/* ── summary of the sample ──
   Deliberately NOT a win-rate: every path here is produced by the same rule
   that would be measured, so a hit-rate would just restate the rule. What is
   worth stating is the rule itself (real desk knowledge), the size of the
   modelled move, and how the sample splits. */
function calReactStats(rule, rows, sym){
  const a=rule.assets.filter(x=>x.s===sym)[0]||{dir:1};
  const pos=rows.filter(r=>r.kind==='pos').length, neg=rows.filter(r=>r.kind==='neg').length;
  const flat=rows.filter(r=>r.kind==='flat').length;
  const dirRows=rows.filter(r=>r.kind!=='flat');
  const avg=fn=>dirRows.length?dirRows.reduce(function(s,r){ return s+(fn(r.react[sym]||{})||0); },0)/dirRows.length:0;
  const name=faAssetName(sym);
  const bias=a.dir>0?'بالا':'پایین';
  let rule_txt='قاعدهٔ مرجع برای '+name+': غافلگیری مثبت (بالاتر از انتظار) این شاخص آن را '+bias+' می‌برد';
  if(a.mixed) rule_txt+=' — اما این واکنش دووجهی است و سمت آن به جزء دیگر همان روز (بازده اوراق یا نرخ ارز) بستگی دارد';
  if(rule.lowerIsBetter) rule_txt+='؛ برای این شاخص «کمتر از انتظار» جهت را برمی‌گرداند';
  rule_txt+='.  ';
  return {pos:pos, neg:neg, flat:flat, mixed:!!a.mixed, bias:bias,
    avg15:avg(function(p){ return p.m15; }), avg60:avg(function(p){ return p.h1; }),
    rule_txt:rule_txt};
}
function calReactTable(rule, rows){
  const head='<div class="cr-tr cr-th"><span>تاریخ</span><span>واقعی</span><span>پیش‌بینی</span><span>غافلگیری</span><span>۱۵ دقیقه</span><span>۶۰ دقیقه</span><span></span></div>';
  const body=rows.map(function(r){
    const sym=window.__calReact.sym;
    const p=r.react[sym]||{m15:0,h1:0};
    const fmt=v=>esc(calReactFmt(v, rule.dec, r.unit||rule.unit));
    const cls=r.kind==='pos'?'pos':(r.kind==='neg'?'neg':'flat');
    return '<div class="cr-tr">'
      +'<span class="cr-d">'+esc(tzDayFa(r.ts))+'</span>'
      +'<span class="cr-n" dir="ltr">'+fmt(r.actual)+'</span>'
      +'<span class="cr-n" dir="ltr">'+fmt(r.forecast)+'</span>'
      +'<span class="cr-sur is-'+cls+'">'+((r.surp>0?'+':(r.surp<0?'−':''))+esc(calReactFmt(Math.abs(r.surp||0), rule.dec, r.unit||rule.unit)))+' '+CAL_REACT_KIND[r.kind].fa+'</span>'
      +'<span class="cr-n '+(p.m15>0?'pos':(p.m15<0?'neg':''))+'">'+calReactMove(p.m15)+'</span>'
      +'<span class="cr-n '+(p.h1>0?'pos':(p.h1<0?'neg':''))+'">'+calReactMove(p.h1)+'</span>'
      +'<span class="cr-src '+(r.src==='live'?'is-live':'')+'">'+(r.src==='live'?'زنده':'مرجع')+'</span>'
    +'</div>';
  }).join('');
  return '<div class="cr-tbl" role="table" aria-label="واکنش قیمت در چهار انتشار اخیر">'+head+body+'</div>';
}
function calReactInner(rule, rows){
  const st=window.__calReact, a=rule.assets.filter(x=>x.s===st.sym)[0]||rule.assets[0];
  const stat=calReactStats(rule, rows, st.sym);
  const live=rows.filter(r=>r.src==='live').length;
  const chips=rule.assets.map(function(x){
    const sel=x.s===st.sym;
    return '<button type="button" class="cr-chip'+(sel?' on':'')+'" data-react-asset="'+x.s+'" aria-pressed="'+(sel?'true':'false')+'">'
      +esc(x.s)+(x.mixed?' <i class="cr-mx" title="واکنش دووجهی">±</i>':'')+'</button>';
  }).join('');
  return '<div class="cr-chips" role="group" aria-label="دارایی مرتبط">'+chips+'</div>'
    +'<div class="cr-chart">'+calReactSvg(rows, st.sym, 520, 150)+'</div>'
    +'<div class="cr-capline"><span>مسیر قیمت '+esc(faAssetName(st.sym))+' پس از هر انتشار (خط صفر = لحظهٔ انتشار)</span>'
      +(live?('<span class="cr-live">'+toFa(live)+' رديف با عدد منتشرشدهٔ همین تقویم</span>'):'<span class="cr-live is-ref">آرشیو مرجع مدل‌شده</span>')+'</div>'
    +calReactTable(rule, rows)
    +'<p class="cr-stat'+(stat.mixed?' is-mixed':'')+'">'+esc(stat.rule_txt)
      +' <span class="cr-counts">نمونهٔ '+toFa(rows.length)+' انتشار: '+toFa(stat.pos)+' بیشتر از انتظار · '+toFa(stat.neg)+' کمتر از انتظار · '+toFa(stat.flat)+' مطابق انتظار — میانگین مدل‌شدهٔ '+esc(faAssetName(st.sym))+' در ۱۵ دقیقه '+calReactMove(stat.avg15)+' و در ۶۰ دقیقه '+calReactMove(stat.avg60)+'</span></p>';
}
function calReactHTML(e){
  const rule=calReactRule(e);
  if(!rule){
    return '<section class="cal-react is-none"><div class="cr-hd"><h4>واکنش تاریخی قیمت</h4></div>'
      +'<p class="hint">برای این رویداد آرشیو واکنشی ثبت نشده است — ماژول واکنش فقط برای شاخص‌های پرتکرار و پرتأثیر (تورم آمریکا، اشتغال، نرخ بهرهٔ فدرال، ذخایر نفت خام، خرده‌فروشی، GDP، PMI، نرخ بهرهٔ ECB) داده دارد.</p></section>';
  }
  return '<details class="cal-react" open>'
    +'<summary class="cr-hd"><h4>واکنش تاریخی قیمت</h4><span class="cr-rule">'+esc(rule.label)+'</span>'
      +'<span class="cr-badge">آرشیو مرجع · '+toFa(CAL_REACT_ROWS)+' انتشار اخیر</span></summary>'
    +'<div id="calReactBody"></div>'
    +'<p class="hint cr-foot">جهت واکنش هر دارایی از قاعدهٔ رفتاری همان شاخص می‌آید (تورم داغ‌تر ⇒ دلار بالا، طلا و کریپتو و سهام پایین) و اندازهٔ حرکت، میانگین تیپیکال یک‌ساعتهٔ همان جفت‌ارز است. بک‌تست زندهٔ ریز‌داده در دسترس نیست، پس ردیف‌های «مرجع» با آهنگ انتشار همان شاخص و قیمت انتظاری همین تقویم ساخته می‌شوند؛ ردیف‌هایی که تقویم واقعاً مقدار منتشرشده دارد «زنده» نشان می‌شوند. این اعداد سیگنال معاملاتی نیستند.</p></details>';
}
function initCalReact(e){
  const body=document.getElementById('calDocBody');
  if(!body||!body.__crWired){
    if(body){
      body.__crWired=1;
      body.addEventListener('click', function(ev){
        const b=ev.target.closest('[data-react-asset]');
        if(!b) return;
        window.__calReact.sym=b.getAttribute('data-react-asset');
        paintCalReact();
      });
    }
  }
  window.__calReact={rule:calReactRule(e), e:e, sym:null};
  const rule=window.__calReact.rule;
  if(!rule) return;
  /* default asset: the one the desk would watch first (the rule lists them in
     priority order), kept across events while it stays relevant */
  const keep=window.__calReactSym;
  window.__calReact.sym=(keep&&rule.assets.some(x=>x.s===keep))?keep:rule.assets[0].s;
  paintCalReact();
}
function paintCalReact(){
  const st=window.__calReact;
  const box=document.getElementById('calReactBody');
  if(!box||!st||!st.rule) return;
  window.__calReactSym=st.sym;
  const rows=calReactRows(st.rule, st.e);
  box.innerHTML=calReactInner(st.rule, rows);
}
/* ── "Explain" card: what the release is, in plain English ───────────────
   Four sections per event — what it is, how it is measured, why it matters,
   how the market trades it — written by calendar_data.event_doc() on the
   server (deterministic, offline, no model). The card also repeats the row's
   own numbers: actual against forecast with the surprise, and the source. */
function openCalDoc(key){
  const e=(window.__calPool||[]).find(x => x._key === key); if(!e) return;
  const ov=document.getElementById('calDocOverlay'), b=document.getElementById('calDocBody');
  if(!ov||!b) return;
  const num=function(label,val,cls){
    return `<div class="cal-doc-num ${cls||''}"><span>${label}</span><b>${esc(val||'—')}</b></div>`;
  };
  /* Persian, and short: two lines written from the event's own fields. The
     longer English primer is still on the row (`doc_sections`) for anything that
     needs it, but this is what the modal shows. */
  const secs=(e.doc_fa_sections&&e.doc_fa_sections.length)?e.doc_fa_sections:(e.doc_sections||[]);
  const sections=secs.map(s=>
    `<div class="cal-doc-sec"><h4>${esc(s.h)}</h4><p>${esc(s.p)}</p></div>`).join('');
  b.innerHTML=`
    <div class="cal-doc-ttl">${esc(e.title)}${e.period?` <span style="color:var(--ink-3);font-weight:700">(${esc(e.period)})</span>`:''}</div>
    <div class="cal-doc-sub">${esc(e.category?'دستهٔ '+e.category:'رویداد اقتصادی')} · منتشرکننده: ${esc(e.geo_name||e.country||'کشور منتشرکننده')}${e.all_day?' · رویداد تمام‌روز':''}</div>
    <div class="cal-doc-meta">
      <span class="cal-doc-chip"><i class="imp-dot ${impClass(e.impact)}"></i> اهمیت ${esc(CAL_IMP_FA[e.impact]||e.impact)}</span>
      <span class="cal-doc-chip">${esc(e.country||'')}</span>
      <span class="cal-doc-chip">${esc(tzDayFa(e.ts))} · ${esc(e.all_day?'تمام روز':tzClock(e.ts))} ${esc(calTz())}</span>
      ${tzDay(e.ts)!==e.day||calTz()!=='UTC'?`<span class="cal-doc-chip">UTC ${esc(e.time_str||'')}</span>`:''}
      ${e.impact?`<span class="cal-doc-chip imp is-${impClass(e.impact)}">اهمیت ${esc(CAL_IMP_FA[e.impact]||'')}</span>`:''}
      <span class="cal-doc-chip">${esc(e.geo_name||'')}${e.geo_name&&e.country?` (${esc(e.country)})`:''}</span>
      <span class="cal-doc-chip">${esc(e.indicator&&e.indicator!=='Calendar'?e.indicator:'انتشار اقتصادی')}</span>
    </div>
    <div class="cal-doc-nums">
      ${num('مقدار واقعی', e._released?(e.actual_fmt||'—'):'منتشر نشده', e.better===1?'good':(e.better===-1?'bad':''))}
      ${num('پیش‌بینی', e.forecast_fmt)}
      ${num('مقدار قبلی', e.previous_fmt+(e.revision?` (بازنگری ${e.revision})`:''))}
      ${num('غافلگیری', e.surprise_fmt||'—', e.better===1?'good':(e.better===-1?'bad':''))}
    </div>
    ${sections}
    ${calReactHTML(e)}
    <div class="cal-doc-foot">
      <span class="hint">توضیح رویداد به‌صورت محلی از نام، دسته و اهمیت رویداد ساخته می‌شود — قاعده‌محور و بدون مدل زبانی. توصیهٔ سرمایه‌گذاری نیست.</span>
    </div>`;
  initCalReact(e);          /* fills #calReactBody and wires the asset chips */
  ov.classList.add('open');
}
/* ── market sessions ── */
function renderSessions(){
  const box=document.getElementById('sessionsBox'); if(!box||!ECON) return;
  const ss=ECON.sessions||[];
  if(!ss.length){ box.innerHTML='<span class="hint">Sessions unavailable right now.</span>'; return; }
  box.innerHTML=ss.map(s=>{
    const st=s.open?'Open':'Closed';
    const h=Math.floor(s.mins_to_change/60), m=s.mins_to_change%60;
    const to=(s.open?'closes in ':'opens in ')+h+'h '+String(m).padStart(2,'0')+'m';
    return `<div class="session ${s.open?'on':'off'}">
      <span class="ic">${ic('globe')}</span>
      <span class="lbl">${esc(SESSION_FA[s.label]||s.label)}</span>
      <span class="dot" title="${st}"></span>
      <span class="state">${st}</span>
      <span class="eta">${to}</span>
    </div>`;
  }).join('')
  +`<div class="hint" style="margin-block-start:8px">Weekly schedule, times in UTC — the clock refreshes every minute.</div>`;
  /* the session clock is re-armed on every calendar render, so the previous
     slot has to be released first — Clock.off on a handle that was never
     registered is a no-op, which is what makes this safe to call each time */
  Clock.off(window.__sessTick);
  window.__sessTick=Clock.every(60000, ()=>{ if(UI.view==='calendar'&&ECON) renderSessions(); }, {label:'sessions'});
}
/* ── TradingView ideas tab: per-asset filter, chart image, text, permalink ──
   Every card points at the permalink the API resolved. The old build linked to
   /idea/<numeric id>/ which returns 404 — that is why nothing ever opened — so
   the server now returns the real chart_url (and s3 chart thumbnail) instead.
   Thumbnails go through the local image proxy so hotlink rules never blank a
   card; if an image still fails it is hidden and the card keeps image-less
   layout with title, text and link. */
const IDEAS_CACHE={};               // sym -> {items, url, ts}
const IDEAS_TTL=15*60*1000;         // 15 min client-side cache
let IDEAS_SEQ=0;
const IDEA_FA={};                   // "sym|id" -> {title_fa, paragraphs}
/* TradingView's own ideas page labels, kept in Persian: Popular is the site's
   default feed, Editors' picks is its badge filter, and timeframe/market tags
   come straight off each card. */
const IDEAS_SORTS=[['popular','🔥 محبوب‌ترین'],['recent','🕒 جدیدترین'],['followers','👥 پرطرفدارترین نویسنده']];
const IDEAS_KINDS=[['all','همه ایده‌ها'],['picked','⭐ منتخب سردبیر'],['education','📚 آموزشی'],['video','🎬 ویدیو']];
const TF_LABEL={'1':'1m','3':'3m','5':'5m','15':'15m','30':'30m','45':'45m','60':'1H','120':'2H','180':'3H','240':'4H','1D':'روزانه','1W':'هفتگی','1M':'1M','3M':'3M','6M':'6M','12M':'12M'};
function tfLabel(v){ v=String(v==null?'':v); return TF_LABEL[v]||v; }
function fmtCount(n){ n=+n||0; if(n>=1e6) return (n/1e6).toFixed(1).replace(/\.0$/,'')+'M';
  if(n>=1e3) return (n/1e3).toFixed(1).replace(/\.0$/,'')+'K'; return String(n); }
function ideasSym(){ return UI.ideasSym || orderedAssets()[0] || 'BTC'; }
function setIdeasAsset(sym){ if(UI.ideasSym===sym) return; UI.ideasSym=sym; loadIdeas(); }
/* the setters also sync their <select> — otherwise the toolbar chip (which
   reads the select's selected option for its label) would keep naming the old
   value after a programmatic change such as “clear all”. */
function setIdeasSort(v){
  UI.ideasSort=v;
  const el=document.getElementById('ideasSortChips'); if(el&&el.value!==v) el.value=v;
  renderIdeas();
}
function setIdeasKind(v){
  UI.ideasKind=v;
  const el=document.getElementById('ideasKindChips'); if(el&&el.value!==v) el.value=v;
  renderIdeas();
}
function setIdeasTf(v){
  UI.ideasTf=v;
  const el=document.getElementById('ideasTfChips'); if(el&&el.value!==v) el.value=v;
  renderIdeas();
}
function renderIdeasChips(){
  const box=document.getElementById('ideasChips'); if(!box||typeof DATA==='undefined'||!DATA) return;
  const cur=ideasSym();
  box.innerHTML=orderedAssets().map(s=>{
    const m=(DATA.assets_meta||{})[s]||{};
    const on=cur===s;
    return `<button class="chip ${on?'on':''}" aria-pressed="${on}" onclick="setIdeasAsset(${jsArg(s)})">${assetIc(s)} ${esc(faAssetName(s))}</button>`;
  }).join('');
  /* sort + kind are selects now — the option lists stay the same */
  const sc=document.getElementById('ideasSortChips');
  if(sc){
    const s=UI.ideasSort||'popular';
    sc.innerHTML=IDEAS_SORTS.map(([v,t])=>`<option value="${v}"${s===v?' selected':''}>${t}</option>`).join('');
  }
  const kc=document.getElementById('ideasKindChips');
  if(kc){
    const k=UI.ideasKind||'all';
    kc.innerHTML=IDEAS_KINDS.map(([v,t])=>`<option value="${v}"${k===v?' selected':''}>${t}</option>`).join('');
  }
}
/* the timeframe lane is built from the ideas actually loaded, like the market
   tags TradingView shows on its cards — hidden when everything is one frame */
function renderIdeasTfChips(){
  const bar=document.getElementById('ideasTfBar'), box=document.getElementById('ideasTfChips');
  if(!bar||!box) return;
  const cached=IDEAS_CACHE[ideasSym()];
  const tfs=[...new Set(((cached&&cached.items)||[]).map(x=>String(x.interval||'')).filter(Boolean))];
  let cur=UI.ideasTf||'all';
  /* a frame that this asset has no ideas for would filter the list to nothing
     while the select showed “همه” — drop the filter instead of lying */
  if(cur!=='all'&&!tfs.includes(cur)){ UI.ideasTf='all'; cur='all'; }
  if(!tfs.length){ bar.style.display='none'; return; }
  bar.style.display='';
  box.innerHTML=`<option value="all"${cur==='all'?' selected':''}>همه</option>`+
    tfs.map(t=>`<option value="${esc(t)}"${cur===t?' selected':''}>${esc(tfLabel(t))}</option>`).join('');
}
function ideasFiltered(){
  const cached=IDEAS_CACHE[ideasSym()];
  let list=((cached&&cached.items)||[]).slice();
  const kind=UI.ideasKind||'all';
  if(kind==='picked') list=list.filter(x=>x.picked);
  else if(kind==='education') list=list.filter(x=>x.education);
  else if(kind==='video') list=list.filter(x=>x.video);
  const tf=UI.ideasTf||'all';
  if(tf!=='all') list=list.filter(x=>String(x.interval||'')===String(tf));
  const s=UI.ideasSort||'popular';
  const pop=x=>(x.likes||0)*3+(x.comments||0)*2+Math.log10((x.followers||0)+1)*4+(x.picked?6:0)+(x.hot?4:0);
  if(s==='recent') list.sort((a,b)=>(b.ts||0)-(a.ts||0));
  else if(s==='followers') list.sort((a,b)=>((b.followers||0)-(a.followers||0))||((b.likes||0)-(a.likes||0))||((b.ts||0)-(a.ts||0)));
  else list.sort((a,b)=>(pop(b)-pop(a))||((b.ts||0)-(a.ts||0)));
  return list;
}
/* badge chips only — the timeframe now sits on the chart image itself */
function ideaBadges(x){
  const b=[];
  if(x.picked) b.push(`<span class="badge b-topic">${ic('star')} منتخب سردبیر</span>`);
  if(x.hot)    b.push(`<span class="badge b-topic">${ic('fire')} داغ</span>`);
  if(x.education) b.push(`<span class="badge b-topic">${ic('book')} آموزشی</span>`);
  if(x.video)  b.push(`<span class="badge b-topic">${ic('film')} ویدیو</span>`);
  return b.join(' ');
}
/* the card TradingView itself would render: chart image on top with the
   direction and timeframe over it, then the thesis, then the author and the
   permalink. The proxy ladder is unchanged (hotlink 403 → local proxy). */
function ideaCardHTML(x){
  const dir=x.symbol_dir||'';
  const dcls=dir==='Long'?'up':dir==='Short'?'dn':'';
  const dlabel=dir==='Long'?'▲ لانگ':dir==='Short'?'▼ شورت':(dir?(dir==='Neutral'?'خنثی':dir):'ایده بدون جهت');
  const link=esc(x.link||'https://www.tradingview.com/ideas/');
  const open=`openIdeaModal(${jsArg(x.asset||ideasSym())},${jsArg(x.id)})`;
  const when=x.iso?faDateFromIso(String(x.iso).slice(0,10)):'';
  const snippet=x.snippet||'', body=x.body||'';
  const more=body.length>snippet.length+40?`<button class="idea-more-btn" onclick="${open}">${ic('book')} متن کامل + ترجمهٔ فارسی</button>`:'';
  const reach=(x.followers>0)?` · ${toFa(fmtCount(x.followers))} دنبال‌کننده`:'';
  const thumb=x.image
    ? `<button class="idea-thumb" onclick="${open}" tabindex="-1" aria-hidden="true">
         <img loading="lazy" decoding="async" alt="" src="${attr(safeUrl(x.image))}" referrerpolicy="no-referrer" data-orig="${attr(x.image)}" onerror="if(!this.dataset.tried){this.dataset.tried='1';this.src='/api/proxy-image?url='+encodeURIComponent(this.dataset.orig);}else{this.closest('.idea-thumb').classList.add('noimg')}">
         ${x.interval?`<span class="idea-tf">${esc(tfLabel(x.interval))}</span>`:''}
       </button>`
    : '';
  return `<article class="idea-card">
    ${thumb}
    <div class="idea-body">
      <div class="idea-top">
        <span class="dir ${dcls}">${dlabel}</span>
        ${x.symbol?`<span class="idea-sym ltr">${esc(x.symbol)}</span>`:''}
        ${(!x.image&&x.interval)?`<span class="badge b-kind ltr">${esc(tfLabel(x.interval))}</span>`:''}
        ${when?`<span class="idea-when">${esc(when)}</span>`:''}
      </div>
      <h4 class="idea-ttl"><a href="javascript:void(0)" onclick="${open}">${esc(x.title)}</a></h4>
      ${snippet?`<p class="idea-txt">${esc(snippet)}</p>`:''}
      ${ideaBadges(x)?`<div class="idea-badges">${ideaBadges(x)}</div>`:''}
      <div class="idea-foot">
        <span class="author">${ic('users')} ${esc(x.user||'—')}${x.user_pro?' '+ic('star'):''}${reach}</span>
        <span class="eng">${ic('heart')} ${toFa(x.likes||0)} · ${ic('comment')} ${toFa(x.comments||0)}${x.views?(' · '+ic('eye')+' '+toFa(fmtCount(x.views))):''}</span>
      </div>
      <div class="idea-cta">
        ${more}
        <a class="idea-link" href="${link}" target="_blank" rel="noopener">تریدینگ‌ویو ${ic('external')}</a>
      </div>
    </div>
  </article>`;
}
function renderIdeas(){
  const grid=document.getElementById('ideasGrid'); if(!grid) return;
  const sym=ideasSym(), cached=IDEAS_CACHE[sym];
  const summary=document.getElementById('ideasSummary');
  const allLink=document.getElementById('ideasAllLink');
  if(cached&&cached.url&&allLink) allLink.href=cached.url;
  renderIdeasTfChips();
  if(typeof renderIdeasToolbar==='function') renderIdeasToolbar();   /* FILTER MODEL 3 toolbar */
  if(!cached){
    grid.innerHTML=`<div class="empty"><span class="spinner"></span> در حال دریافت ایده‌های ${esc(sym)}…</div>`;
    if(summary) summary.textContent='در حال خواندن…';
    return;
  }
  if(cached.err==='not_available'){
    grid.innerHTML='<div class="empty">این بخش در این نسخه فعال نیست — ایده‌های تریدینگ‌ویو فقط در داشبورد اصلی خوانده می‌شوند.</div>';
    if(summary) summary.textContent='—';
    return;
  }
  if(!cached.items.length){
    grid.innerHTML='<div class="empty">برای این دارایی ایده‌ای پیدا نشد — یک دارایی دیگر را انتخاب کنید یا آخرین ایده‌ها را در تریدینگ‌ویو ببینید.</div>';
    if(summary) summary.textContent=toFa(0)+' ایده';
    return;
  }
  const list=ideasFiltered();
  if(!list.length){
    grid.innerHTML='<div class="empty">با این فیلتر ایده‌ای نیست — «نوع ایده» یا تایم‌فریم را به «همه» برگردان.</div>';
  } else {
    grid.innerHTML=list.map(ideaCardHTML).join('');
  }
  const longs=list.filter(x=>x.symbol_dir==='Long').length;
  const shorts=list.filter(x=>x.symbol_dir==='Short').length;
  if(summary) summary.textContent=`${toFa(list.length)} از ${toFa(cached.items.length)} ایدهٔ ${esc(sym)} · ${toFa(longs)} لانگ · ${toFa(shorts)} شورت`;
}
async function loadIdeas(force){
  const sym=ideasSym();
  renderIdeasChips();
  const cached=IDEAS_CACHE[sym];
  if(cached&&!force&&Date.now()-cached.ts<IDEAS_TTL){ renderIdeas(); return; }
  renderIdeas();
  const seq=++IDEAS_SEQ;
  try{
    const d=await (await fetch('/api/ideas?sym='+encodeURIComponent(sym)+'&limit=30')).json();
    if(seq!==IDEAS_SEQ) return;                      /* a newer chip won the race */
    IDEAS_CACHE[sym]={items:(d&&d.items)||[], url:(d&&d.url)||'', ts:Date.now(),
                      err:(d&&d.ok===false)?(d.error||'error'):null};
  }catch(e){
    if(seq!==IDEAS_SEQ) return;
    IDEAS_CACHE[sym]={items:[], url:'', ts:Date.now(), err:'network'};
  }
  if(UI.view==='ideas') renderIdeas();
}
/* ── idea modal: chart + full text + Persian translation (like a news item) ── */
function findIdea(sym,id){
  const c=IDEAS_CACHE[sym];
  return c?((c.items||[]).find(x=>String(x.id)===String(id))||null):null;
}
function openIdeaModal(sym,id){
  const x=findIdea(sym,id); if(!x) return;
  const ov=document.getElementById('ideaOverlay'); if(!ov) return;
  ov.classList.add('open');
  renderIdeaModal(sym,x,false);
}
function renderIdeaModal(sym,x,faMode){
  const b=document.getElementById('ideaBody'); if(!b||!x) return;
  const fa=IDEA_FA[sym+'|'+x.id];
  const dir=x.symbol_dir||'';
  const dcls=dir==='Long'?'up':dir==='Short'?'dn':'';
  const dlabel=dir==='Long'?'▲ لانگ':dir==='Short'?'▼ شورت':(dir?(dir==='Neutral'?'خنثی':dir):'ایده بدون جهت');
  const raw=(x.body||x.snippet||'').split(/\n{2,}/).map(p=>p.trim()).filter(Boolean);
  const bodyHtml = (faMode&&fa&&fa.paragraphs&&fa.paragraphs.length)
    ? fa.paragraphs.map(p=>`<p class="fa">${esc(p)}</p>`).join('')
    : (raw.length?raw.map(p=>`<p class="en">${esc(p)}</p>`).join('')
       : '<p style="color:var(--ink-3)">متن کامل این ایده در صفحهٔ تریدینگ‌ویو است.</p>');
  const titleShown=(faMode&&fa&&fa.title_fa)?fa.title_fa:x.title;
  const faBtn = faMode
    ? `<button class="btn ghost sm" onclick="renderIdeaModal(${jsArg(sym)},findIdea(${jsArg(sym)},${jsArg(x.id)}),false)">↩️ نمایش متن اصلی</button>`
    : (fa?`<button class="btn sm" onclick="renderIdeaModal(${jsArg(sym)},findIdea(${jsArg(sym)},${jsArg(x.id)}),true)">🇮🇷 نمایش ترجمهٔ فارسی</button>`
       : `<button class="btn sm" id="ideaFaBtn" onclick="ideaToFa(${jsArg(sym)},${jsArg(x.id)})">🇮🇷 ترجمهٔ فارسی متن کامل</button>`);
  b.innerHTML=`
    <div class="row1" style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
      <span class="dir ${dcls}" style="font-weight:800">${dlabel}</span>${ideaBadges(x)}
    </div>
    <h2>${esc(titleShown||'')}</h2>
    ${(faMode&&fa&&fa.title_fa)?`<div class="h2en">${esc(x.title)}</div>`:''}
    <div class="mmeta">
      <span>✍️ ${esc(x.user||'—')}</span>
      ${(x.followers>0)?`<span>👥 ${toFa(fmtCount(x.followers))} دنبال‌کننده</span>`:''}
      ${x.symbol?`<span class="ltr">${esc(x.symbol)}</span>`:''}
      ${x.iso?`<span>🗓 ${esc(faDateFromIso(String(x.iso).slice(0,10)))}</span>`:''}
      <span class="ltr">❤ ${toFa(x.likes||0)} · 💬 ${toFa(x.comments||0)}</span>
    </div>
    ${x.image?`<a href="${attr(safeUrl(x.link))}" target="_blank" rel="noopener" style="display:block;margin:10px 0 4px"><img class="idea-big" src="${attr(safeUrl(x.image))}" referrerpolicy="no-referrer" alt="" onerror="this.style.display='none'"></a>`:''}
    <div class="msec">
      <h4>${faMode?'📝 ترجمهٔ فارسی متن ایده':'📝 متن کامل ایده'}</h4>
      ${bodyHtml}
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:14px">
        ${faBtn}
        <a class="mlink" href="${attr(safeUrl(x.link))}" target="_blank" rel="noopener">🔗 مشاهده در تریدینگ‌ویو</a>
      </div>
    </div>`;
}
async function ideaToFa(sym,id){
  const key=sym+'|'+id;
  const x=findIdea(sym,id);
  if(IDEA_FA[key]){ renderIdeaModal(sym,x,true); return; }
  const btn=document.getElementById('ideaFaBtn');
  const setTxt=t=>{ if(btn) btn.innerHTML=t; };
  setTxt('<span class="spinner"></span> در حال ترجمه…');
  let tries=0;
  const poll=async()=>{
    let d;
    try{ d=await (await fetch('/api/ideas/translate?sym='+encodeURIComponent(sym)+'&id='+encodeURIComponent(id))).json(); }
    catch(e){ setTxt('⚠️ خطا در ترجمه — دوباره بزن'); return; }
    if(d.ok&&d.pending&&tries++<25){
      setTxt('<span class="spinner"></span> در حال ترجمه… ('+toFa(tries)+')');
      setTimeout(poll,1500); return;
    }
    if(d.ok&&!d.pending){
      IDEA_FA[key]={title_fa:d.title_fa||'', paragraphs:d.paragraphs||[]};
      renderIdeaModal(sym,findIdea(sym,id),true); return;
    }
    setTxt('⚠️ ترجمه در دسترس نیست');
  };
  poll();
}
/* ── live ETF rate board: every quoted fund, boxed per family ───────────── */
const ETF_GROUP_FA={Bitcoin:'بیت‌کوین', 'BTC futures':'فیوچرز بیت‌کوین', Leveraged:'اهرمی و معکوس',
  Ethereum:'اتریوم', Solana:'سولانا', XRP:'ریپل (XRP)', 'Crypto blends':'ترکیبی کریپتو',
  'Crypto equity':'سهام کریپتو', Commodities:'کالاها', Markets:'بازارها', Other:'سایر'};
const ETF_GROUP_ORDER=['Bitcoin','BTC futures','Leveraged','Ethereum','Solana','XRP','Crypto blends','Crypto equity','Commodities','Markets','Other'];
function setEtfGroup(g){
  UI.etfGroup=g;
  if(typeof renderEtfToolbar==='function') renderEtfToolbar();
  if(typeof tbClose==='function') tbClose('etfSheet');
  renderEtfLive('etfLive2');
}
function etfCardHTML(s,x){
  const ch=(x&&x.change_pct!=null)?x.change_pct:null;
  const cls=ch==null?'':(ch>=0?'up':'dn');
  const st=(x&&x.market_state)||'';
  const open=!!st&&!['CLOSED','PRE','PREPRE','POST','POSTPOST'].includes(st);
  return `<div class="etfcard">
    <div class="etfcard-top"><span class="tk">${esc(s)}</span><span class="ms ${open?'live':''}">${st?(open?'باز':'بسته'):'—'}</span></div>
    <div class="nm" title="${esc((x&&x.name)||s)}">${esc((x&&x.name)||s)}</div>
    <div class="prc">${(x&&x.price!=null)?'$'+num(x.price,2):'—'}</div>
    <div class="chg ${cls}">${ch==null?'—':((ch>=0?'▲ +':'▼ ')+num(ch,2)+'%')}</div>
  </div>`;
}
function renderEtfGroupChips(){
  const box=document.getElementById('etfGroupChips'); if(!box) return;
  const q=window.__ETFQ||{};
  const counts={};
  Object.keys(q).forEach(s=>{ const g=(q[s]&&q[s].group)||'Other'; counts[g]=(counts[g]||0)+1; });
  const cur=UI.etfGroup||'all';
  if(typeof renderEtfToolbar==='function') renderEtfToolbar();
  let h=`<button class="chip ${cur==='all'?'on':''}" onclick="setEtfGroup('all')">همه <span class="n">${toFa(Object.keys(q).length)}</span></button>`;
  ETF_GROUP_ORDER.filter(g=>counts[g]).forEach(g=>{
    h+=`<button class="chip ${cur===g?'on':''}" onclick="setEtfGroup(${jsArg(g)})">${ETF_GROUP_FA[g]||g} <span class="n">${toFa(counts[g])}</span></button>`;
  });
  box.innerHTML=h;
}
function renderEtfLive(targetId){
  const box=document.getElementById(targetId||'etfLive2'); if(!box) return;
  const q=window.__ETFQ||{};
  const all=Object.keys(q);
  const sum=document.getElementById('etfSummary');
  renderEtfGroupChips();
  if(!all.length){
    box.innerHTML='<div class="empty">نرخ زندهٔ صندوق‌ها هم‌اکنون در دسترس نیست — تلاش بعدی یک دقیقهٔ دیگر.</div>';
    if(sum) sum.textContent='—';
    return;
  }
  const grp=UI.etfGroup||'all';
  const needle=(UI.etfQ||'').trim().toLowerCase();
  const syms=all.filter(s=>{
    if(grp!=='all'&&((q[s]&&q[s].group)||'Other')!==grp) return false;
    if(!needle) return true;
    return s.toLowerCase().includes(needle)||String((q[s]&&q[s].name)||'').toLowerCase().includes(needle);
  });
  if(!syms.length){
    box.innerHTML='<div class="empty">صندوقی با این فیلتر پیدا نشد.</div>';
    if(sum) sum.textContent=`۰ از ${toFa(all.length)} صندوق`;
    return;
  }
  const groups={};
  syms.slice().sort().forEach(s=>{ const g=(q[s]&&q[s].group)||'Other'; (groups[g]=groups[g]||[]).push(s); });
  /* known groups in a fixed order, then anything the API adds later — a new
     family must never silently drop out of the board */
  const order=ETF_GROUP_ORDER.filter(g=>groups[g])
    .concat(Object.keys(groups).filter(g=>!ETF_GROUP_ORDER.includes(g)).sort());
  box.innerHTML=order.map(g=>
    `<section class="etfgroup"><h4 class="etfgroup-t">${ETF_GROUP_FA[g]||g}<span class="n">${toFa(groups[g].length)} صندوق</span></h4>`+
    `<div class="etfgrid">${groups[g].map(s=>etfCardHTML(s,q[s])).join('')}</div></section>`).join('');
  if(sum){
    const ups=syms.filter(s=>((q[s]||{}).change_pct||0)>=0).length;
    sum.textContent=`${toFa(syms.length)}${(grp==='all'&&!needle)?'':' از '+toFa(all.length)} صندوق · ${toFa(ups)} مثبت · ${toFa(syms.length-ups)} منفی`;
  }
}
async function pollEtf(){
  try{ const d=await (await fetch('/api/etf')).json();
    if(d.ok&&d.quotes&&Object.keys(d.quotes).length){ window.__ETFQ=d.quotes; renderEtfLive('etfLive2'); }
  }catch(e){}
}
pollEtf(); Clock.every(60000, pollEtf, {label:'etf-poll'});
/* ── DL2 step 1: "new since last visit" + page-load skeleton ──────────────
   The baseline is frozen at boot so the markers do not blink out when the
   60s poll re-renders the feed; localStorage is updated for the next visit. */
const DL2_SEEN_KEY='dl2_last_seen';
let DL2_BASELINE=0;
function dl2LastSeen(){ try{ return +(localStorage.getItem(DL2_SEEN_KEY)||0); }catch(e){ return 0; } }
function dl2MarkSeen(){ try{ localStorage.setItem(DL2_SEEN_KEY, String(Math.floor(Date.now()/1000))); }catch(e){} }
function tsOf(a){ const t=(a&&a.published_ts)||0; return t>1e12?Math.floor(t/1000):t; }
function isNew(a){ return DL2_BASELINE>0 && tsOf(a)>DL2_BASELINE; }
function dl2Skeleton(n){
  const g=document.getElementById('newsGrid');
  if(!g||(typeof DATA!=='undefined'&&DATA)) return;
  const sk=[]; for(let i=0;i<(n||6);i++) sk.push({__sk:i});
  if(vsGrid('feed','newsGrid',VS_OPTS_FEED, sk, null)) return;
  let h=''; for(let i=0;i<(n||6);i++) h+='<div class="skcard skeleton"></div>';
  g.innerHTML=h;
}
function dl2AfterFeed(){
  if(typeof DATA==='undefined'||!DATA) return;
  const host=document.getElementById('feedCount');
  if(!host||!host.parentNode) return;
  const n=(DATA.articles||[]).filter(isNew).length;
  let b=document.getElementById('feedNewBadge');
  if(!b){
    b=document.createElement('span'); b.id='feedNewBadge';
    host.parentNode.insertBefore(b, host.nextSibling);
  }
  b.innerHTML = n ? '<span class="newdot"></span>'+toFa(n)+' تازه' : '';
}
DL2_BASELINE=dl2LastSeen();

/* ── DL2 step 2: accessibility — modal focus trap + keyboard nav for the rail
   Small, self-contained, and additive: it only listens, it never rewrites the
   DOM the rest of the app builds. */
(function(){
  try{
    let lastFocus=null;
    function visibleOverlay(){
      return document.querySelector('.overlay.open');
    }
    function focusables(root){
      return [...root.querySelectorAll(
        'a[href],button:not([disabled]),input:not([disabled]),select,textarea,'+
        '[tabindex]:not([tabindex="-1"])')].filter(el=>el.offsetParent!==null||el===document.activeElement);
    }
    document.addEventListener('keydown',function(e){
      const ov=visibleOverlay();
      if(!ov) return;
      if(e.key==='Escape'){ e.preventDefault(); ov.classList.remove('open');
        if(lastFocus&&lastFocus.focus) lastFocus.focus(); lastFocus=null; return; }
      if(e.key==='Tab'){
        const f=focusables(ov);
        if(!f.length){ e.preventDefault(); return; }
        const first=f[0], last=f[f.length-1];
        if(e.shiftKey&&document.activeElement===first){ e.preventDefault(); last.focus(); }
        else if(!e.shiftKey&&document.activeElement===last){ e.preventDefault(); first.focus(); }
      }
    },true);
    /* remember what had focus before a modal opened, so Esc returns the user there */
    document.addEventListener('click',function(e){
      const opener=e.target&&e.target.closest?e.target.closest('.ncard,.lead-card,[data-modal-opener]'):null;
      if(opener) lastFocus=opener;
    },true);
    /* modal role/aria for screen readers */
    document.querySelectorAll('.overlay').forEach(function(ov){
      ov.setAttribute('role','dialog'); ov.setAttribute('aria-modal','true');
    });
    /* roving focus + Arrow/Home/End inside the tab rail */
    const rail=document.getElementById('appSidebar');
    if(rail){
      rail.addEventListener('keydown',function(e){
        const items=[...rail.querySelectorAll('.nav-item')];
        const i=items.indexOf(document.activeElement);
        if(i<0) return;
        let j=null;
        if(e.key==='ArrowDown'||e.key==='ArrowLeft') j=Math.min(items.length-1,i+1);
        else if(e.key==='ArrowUp'||e.key==='ArrowRight') j=Math.max(0,i-1);
        else if(e.key==='Home') j=0;
        else if(e.key==='End') j=items.length-1;
        if(j===null) return;
        e.preventDefault();
        items.forEach((el,k)=>el.setAttribute('tabindex',k===j?'0':'-1'));
        items[j].focus();
      });
    }
  }catch(e){ /* progressive enhancement only — never break the dashboard */ }
})();

/* ── Fear & Greed — one per-asset gauge under the report chart ────────────
   The standalone tab was removed on request; each asset report now carries its
   own reading (scored from that asset's last-24 h headlines) right under the
   chart, with the global alternative.me index kept as a reference line. */
const FNG_LABELS={'Extreme Fear':'ترس شدید','Fear':'ترس','Neutral':'خنثی','Greed':'طمع','Extreme Greed':'طمع شدید'};
function fngColor(v){ return v>=75?'var(--dn)':v>=55?'var(--cu-hi)':v>=45?'var(--ink-3)':'var(--up)'; }
function fngFaLabel(label){ return (window.__ECON_FA&&window.__ECON_FA[label])||FNG_LABELS[label]||label||''; }
function fngGauge(v,label){
  /* 0=fear(green) … 100=greed(red) — 270° arc like the old dial */
  const col=fngColor(v);
  const dash=`<circle cx="30" cy="30" r="25" fill="none" stroke="${col}" stroke-width="7"
    stroke-dasharray="${(169.6*v/100).toFixed(1)} 169.6" transform="rotate(135 30 30)" stroke-linecap="round"/>`;
  return [dash,col,fngFaLabel(label)];
}
function paintFng(){ refreshRepFngGlobal(); }
function refreshRepFngGlobal(){
  const el=document.getElementById('repFngGlobal'); if(!el) return;
  const g=window.__FNG||{};
  el.innerHTML = g.now==null ? 'شاخص کل بازار کریپتو موقتاً در دسترس نیست.'
    : `🌐 شاخص کل بازار کریپتو: <b style="color:${fngColor(g.now)}">${toFa(g.now)}</b> · ${esc(fngFaLabel(g.label))}`;
}
function loadRepFng(sym){
  const host=document.getElementById('repFng'); if(!host) return;
  const meta=(typeof DATA!=='undefined'&&DATA&&DATA.assets_meta&&DATA.assets_meta[sym])||{};
  host.innerHTML=`<h3>😱 شاخص ترس و طمع — ${esc(meta.fa||sym)} <span class="ltr" style="font-size:11px;color:var(--ink-4)">${esc(sym)}</span></h3>
    <div class="rf-row"><span class="spinner"></span><span style="font-size:12px;color:var(--ink-4)">در حال محاسبه از خبرهای ۲۴ ساعت گذشته…</span></div>`;
  fetch('/api/fng/'+encodeURIComponent(sym)).then(r=>r.json()).then(d=>{
    const h=document.getElementById('repFng'); if(!h) return;
    if(!d||!d.ok){ h.insertAdjacentHTML('beforeend','<div class="empty">داده ترس و طمع این دارایی در دسترس نیست.</div>'); return; }
    renderRepFng(sym,d);
  }).catch(()=>{});
}
function renderRepFng(sym,d){
  const host=document.getElementById('repFng'); if(!host) return;
  const meta=(typeof DATA!=='undefined'&&DATA&&DATA.assets_meta&&DATA.assets_meta[sym])||{};
  const v=(d.now==null?50:d.now), cls=fngColor(v), lab=fngFaLabel(d.label);
  const gauge=fngGauge(v,d.label)[0];
  host.innerHTML=`<h3>😱 شاخص ترس و طمع — ${esc(meta.fa||sym)} <span class="ltr" style="font-size:11px;color:var(--ink-4)">${esc(sym)}</span></h3>
    <div class="rf-row">
      <svg viewBox="0 0 60 60" role="img" aria-label="Fear and Greed ${v}" style="inline-size:88px;block-size:88px;flex:0 0 auto">
        <circle cx="30" cy="30" r="25" fill="none" stroke="var(--rule-2)" stroke-width="7"/>${gauge}</svg>
      <div style="flex:1 1 auto;min-inline-size:0">
        <div class="rf-score" style="color:${cls}">${toFa(v)}<span> / ۱۰۰</span></div>
        <div class="rf-lab" style="color:${cls}">${esc(lab)}</div>
        <div class="rf-bar" role="progressbar" aria-valuenow="${v}" aria-valuemin="0" aria-valuemax="100"><i style="inline-size:${v}%;background:${cls}"></i></div>
        <div class="rf-src">ساخته‌شده از <b>${toFa(d.count||0)}</b> خبر ${esc(meta.fa||sym)} در ۲۴ ساعت گذشته — <b style="color:var(--up)">${toFa(d.pos||0)} صعودی</b> · <b style="color:var(--dn)">${toFa(d.neg||0)} نزولی</b> · باقی بی‌طرف.</div>
      </div>
    </div>
    <div class="rf-scale"><span>۰ ترس شدید</span><span>۵۰ خنثی</span><span>۱۰۰ طمع شدید</span></div>
    <div class="rf-glob" id="repFngGlobal"></div>`;
  refreshRepFngGlobal();
}

/* ── short Persian explainer per news (بند کوتاه درباره خبر) ── */
async function openBlurb(id){
  const ov=document.getElementById('blurbOverlay'); ov.classList.add('open');
  const b=document.getElementById('blurbBody');
  b.innerHTML='<div class="spinner"></div>';
  try{
    const d=await (await fetch('/api/article/'+id)).json();
    b.innerHTML=`
      <h2 style="font-size:15.5px;line-height:1.9">${esc(d.title_fa||d.title)}</h2>
      ${d.title_fa?`<div class="h2en">${esc(d.title)}</div>`:''}
      <div class="mmeta">
        <span>📰 ${esc(d.source)}</span>
        <span>🗓 ${esc(d.datetime_fa||'')}</span>
        ${credBadge(d.credibility)}
      </div>
      <div class="msec" style="border-inline-start:3px solid var(--cu)">
        <h4 style="margin-bottom:6px">💡 این خبر چیست؟</h4>
        <p style="font-size:13.5px;line-height:2.15;margin:0">${esc(d.blurb_fa||'توضیحی برای این خبر ساخته نشد — خلاصه را در مودال اصلی ببینید.')}</p>
      </div>
      <button class="btn sm" style="margin-top:4px" onclick="closeModal('blurbOverlay');openArticle(${jsArg(id)})">📄 متن کامل خبر</button>`;
  }catch(e){ b.innerHTML='<div class="empty">خطا در دریافت توضیحات</div>'; }
}

/* ═══════════ telegram digest settings ═══════════ */
const TG_TPL_DEFAULT='🏅 <b>{index}. {title}</b>\n{summary_fa}\n📰 {source} · ⭐ {cred}% {stars} · {assets}\n🕒 {time_fa}\n{link_line}';
function tgPayload(){
  return {telegram:{
    token: document.getElementById('tgToken').value.trim(),
    chat: document.getElementById('tgChat').value.trim(),
    enabled: document.getElementById('tgEnabled').checked,
    min_credibility: parseFloat(document.getElementById('tgMinCred').value)||0.75,
    max_items: parseInt(document.getElementById('tgMaxItems').value)||10,
    max_age_hours: parseFloat(document.getElementById('tgMaxAge').value)||6,
    asset_filter: document.getElementById('tgAssets').value.split(',').map(x=>x.trim().toUpperCase()).filter(Boolean),
    quiet_hours: document.getElementById('tgQuiet').checked,
    include_link: document.getElementById('tgLink').checked,
    link_on_own_line: document.getElementById('tgLinkLine').checked,
    include_summary: document.getElementById('tgSummary').checked,
    hashtags: document.getElementById('tgHashtags').checked,
    emoji: document.getElementById('tgEmoji').checked,
    show_stars: document.getElementById('tgStars').checked,
    silent: document.getElementById('tgSilent').checked,
    pin: document.getElementById('tgPin').checked,
    language: document.getElementById('tgLang').value,
    template: document.getElementById('tgTemplate').value.trim()
  }};
}
/* ═══════════ smart alert rules — condition engine + dispatch ═══════════
   A rule is `[when…] logic → [actions]`. Conditions read three independent
   sources (live prices, calendar releases, the news feed); evaluation is pure
   (`arRuleEval(rule, ctx)`), so it is testable, and the tick that calls it is
   deferred so it never sits in the render path of a poll or a news cycle. */
const AR_KEY='mohmd_alert_rules_v1';
const AR_LOG_MAX=60;
const AR={rules:[], log:[], edit:null, pending:null, rt:{}, ctx:null, lastRun:0};
const AR_OPS={gt:'بزرگ‌تر از', gte:'بزرگ‌تر یا مساوی', lt:'کوچک‌تر از', lte:'کوچک‌تر یا مساوی', eq:'برابر با', contains:'شامل'};
const AR_OP_SYM={gt:'>', gte:'≥', lt:'<', lte:'≤', eq:'=', contains:'⊃'};
const AR_KINDS={price:'قیمت لحظه‌ای', change:'تغییر ۲۴ ساعته', event:'رویداد تقویم اقتصادی', news:'تیتر خبر'};
const AR_IMPACTS={all:'همهٔ سطوح', High:'فقط High', Medium:'فقط Medium'};
const AR_TPL_DEFAULT='🚨 <b>{name}</b>\n{body}\n🕒 {time}';
function arOp(a, op, b){
  if(op==='contains') return String(a==null?'':a).toLowerCase().indexOf(String(b==null?'':b).toLowerCase())>=0;
  const v=Number(a), w=Number(b);
  if(a==null||b===''||b==null||isNaN(v)||isNaN(w)) return false;
  if(op==='gt') return v>w;
  if(op==='gte') return v>=w;
  if(op==='lt') return v<w;
  if(op==='lte') return v<=w;
  if(op==='eq') return Math.abs(v-w)<=Math.abs(w||1)*1e-9;
  return false;
}
function arFmtVal(h){
  if(!h) return '';
  if(h.art) return String(h.art.title_fa||h.art.title||'');
  if(h.ev) return String(h.ev.title||'')+' '+(h.ev.actual_fmt||'');
  const v=Number(h.value);
  if(h.unit==='change') return toFa(v.toFixed(2))+'٪';
  if(isNaN(v)) return String(h.value);
  return toFa(Math.abs(v)>=1000?v.toFixed(0):(Math.abs(v)<1?v.toFixed(4):v.toFixed(2)));
}
function arCondText(c){
  if(!c||!AR_KINDS[c.kind]) return '—';
  if(c.kind==='price'||c.kind==='change'){
    const unit=c.kind==='change'?'٪':' ';
    return (c.kind==='price'?'قیمت ':'تغییر ۲۴ساعتهٔ ')+String(c.sym||'')+' '+(AR_OP_SYM[c.op]||'?')
      +(c.op==='contains'?' "'+String(c.value==null?'':c.value)+'"':' '+toFa(String(c.value==null?'':c.value))+unit);
  }
  if(c.kind==='event') return 'رویداد اقتصادی منتشر شده ('+(AR_IMPACTS[c.impact||'all']||'')+')';
  const terms=(c.terms||[]).filter(Boolean);
  return 'تیتر شامل '+(terms.length?'«'+terms.join('» یا «')+'»':'هر خبر')
    +(Number(c.minCred||0)>0?' با اعتبار ≥ '+toFa(Math.round(Number(c.minCred)*100))+'٪':'')
    +(Number(c.within||0)>0?' در '+toFa(Number(c.within))+' دقیقهٔ اخیر':'');
}
/* one condition against one snapshot; `false` = no, `null` = no data to say,
   an object = matched (and it carries what to print in the notification) */
function arCondOk(c, ctx){
  if(!c) return false;
  if(c.kind==='price'||c.kind==='change'){
    const p=((ctx&&ctx.prices)||{})[c.sym];
    const v=p?(c.kind==='price'?p.price:p.change_24h):null;
    if(v==null) return null;
    if(!arOp(v, c.op, c.value)) return false;
    return {sym:c.sym, value:v, unit:c.kind==='change'?'change':'price',
            label:(c.kind==='price'?'قیمت '+c.sym:'تغییر ۲۴ساعتهٔ '+c.sym)};
  }
  if(c.kind==='event'){
    const ev=((ctx&&ctx.events)||[]).filter(function(e){
      if(c.impact&&c.impact!=='all'&&e.impact!==c.impact) return false;
      return e.past && (e.actual_n!=null || e.actual);
    })[0];
    if(!ev) return false;
    return {sym:null, value:ev.actual_fmt||'', ev:ev, label:'رویداد '+String(ev.title||'')};
  }
  if(c.kind==='news'){
    const terms=(c.terms||[]).map(function(t){ return String(t||'').trim().toLowerCase(); }).filter(Boolean);
    const minCred=Number(c.minCred||0), within=Number(c.within||0)*60;
    const hit=((ctx&&ctx.news)||[]).filter(function(a){
      if((a.credibility||0)<minCred) return false;
      if(within && (ctx.now-(a.published_ts||0))>within) return false;
      if(!terms.length) return true;
      const t=((a.title||'')+' '+(a.title_fa||'')+' '+(a.summary||'')+' '+(a.summary_fa||'')).toLowerCase();
      return terms.some(function(x){ return t.indexOf(x)>=0; });
    })[0];
    if(!hit) return false;
    return {sym:(hit.assets||[])[0]||null, value:hit.title_fa||hit.title||'', art:hit, label:'خبر'+(hit.assets&&hit.assets.length?' '+hit.assets.join('/'):'')};
  }
  return false;
}
function arRuleEval(rule, ctx){
  const conds=((rule&&rule.when)||[]).filter(function(c){ return c&&AR_KINDS[c.kind]; });
  if(!conds.length) return {ok:false, hits:[], misses:[]};
  const hits=[], misses=[];
  conds.forEach(function(c){
    const r=arCondOk(c, ctx);
    if(r&&r!==true) hits.push(r); else misses.push(c);
  });
  return {ok:(rule.logic==='or')?hits.length>0:hits.length===conds.length, hits:hits, misses:misses};
}
function arValidate(rule, silent){
  const bad=function(msg){ if(!silent && typeof arHint==='function') arHint(msg, true); return msg; };
  if(!String(rule.name||'').trim()) return bad('نام قانون را بنویس');
  const conds=(rule.when||[]).filter(function(c){ return c&&AR_KINDS[c.kind]; });
  if(!conds.length) return bad('حداقل یک شرط لازم است');
  for(const c of conds){
    if((c.kind==='price'||c.kind==='change') && !c.sym) return bad('دارایی شرط قیمت انتخاب نشده');
    if(c.kind==='news' && !(c.terms||[]).filter(Boolean).length && !Number(c.minCred||0))
      return bad('برای شرط خبر حداقل یک کلیدواژه یا حد اعتبار لازم است');
  }
  const acts=rule.actions||{};
  if(!acts.toast && !acts.tone && !acts.tg && !acts.push) return bad('حداقل یک اقدام انتخاب کن');
  if(acts.tg && !rule.template) rule.template=AR_TPL_DEFAULT;
  if(!silent && typeof arHint==='function') arHint('');
  return '';
}
/* ── persistence (per browser, like the bookmarks) ─────────────────────── */
function arLoad(){
  try{
    const d=JSON.parse(localStorage.getItem(AR_KEY)||'{}');
    AR.rules=Array.isArray(d.rules)?d.rules:[];
    AR.log=Array.isArray(d.log)?d.log:[];
  }catch(e){ AR.rules=[]; AR.log=[]; }
  AR.rules.forEach(function(r){ if(r.enabled===undefined) r.enabled=true; });
}
function arStore(){
  try{ localStorage.setItem(AR_KEY, JSON.stringify({rules:AR.rules, log:AR.log.slice(0,AR_LOG_MAX), v:1})); }catch(e){}
}
function arNewId(){ return 'ar_'+Date.now().toString(36)+Math.random().toString(36).slice(2,6); }
/* ── actions: sticky toast, squawk tone, telegram webhook ─────────────── */
function arNotify(title, body, level){
  const box=document.getElementById('alertStack');
  if(!box) return null;
  const el=document.createElement('div');
  el.className='alert-card'+(level==='warn'?' is-warn':'');
  el.setAttribute('role','alert');
  el.innerHTML='<div class="al-hd"><span class="al-ic">'+ic(level==='warn'?'warn':'bell')+'</span>'
    +'<b>'+esc(title)+'</b>'
    +'<button type="button" class="al-x" aria-label="بستن هشدار">'+ic('x')+'</button></div>'
    +'<div class="al-bd">'+esc(body||'')+'</div>'
    +'<div class="al-ft"><span>'+esc(tzClock(Math.floor(Date.now()/1000)))+' '+esc(calTz())+'</span><span class="al-tag">هشدار هوشمند</span></div>';
  el.querySelector('.al-x').onclick=function(){ arDismiss(el); };
  box.insertBefore(el, box.firstChild);
  /* keep the newest five only, so a chatty rule cannot bury the dashboard */
  while(box.children.length>5) box.removeChild(box.lastChild);
  return el;
}
function arDismiss(el){
  if(!el) return;
  el.classList.add('is-out');
  setTimeout(function(){ if(el.parentNode) el.parentNode.removeChild(el); }, 160);
}
function arSquawk(){
  try{
    const AC=window.AudioContext||window.webkitAudioContext;
    if(!AC) return;
    if(!AR.ac) AR.ac=new AC();
    const ac=AR.ac;
    if(ac.state==='suspended'&&ac.resume) ac.resume();
    const t0=ac.currentTime;
    [[880,0],[1174.7,0.17]].forEach(function(p){
      const o=ac.createOscillator(), g=ac.createGain();
      o.type='square'; o.frequency.value=p[0];
      g.gain.setValueAtTime(0.0001, t0+p[1]);
      g.gain.exponentialRampToValueAtTime(0.08, t0+p[1]+0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, t0+p[1]+0.15);
      o.connect(g); g.connect(ac.destination);
      o.start(t0+p[1]); o.stop(t0+p[1]+0.17);
    });
  }catch(e){ /* audio is a nicety — a blocked context must never break a rule */ }
}
/* browsers only allow audio after a real gesture, so arm it on the first one */
function arArmTone(){
  if(AR.armed||!AR.rules.length) return;
  AR.armed=1;
  const unlock=function(){
    try{
      const AC=window.AudioContext||window.webkitAudioContext;
      if(AC){ if(!AR.ac) AR.ac=new AC(); if(AR.ac.state==='suspended'&&AR.ac.resume) AR.ac.resume(); }
    }catch(e){}
    document.removeEventListener('click', unlock);
    document.removeEventListener('keydown', unlock);
  };
  document.addEventListener('click', unlock);
  document.addEventListener('keydown', unlock);
}
function arRenderTpl(rule, res){
  const body=res.hits.map(function(h){ return '• '+h.label+(h.art?'':' — '+arFmtVal(h)); }).join('\n');
  const now=Math.floor(Date.now()/1000);
  const first=res.hits[0]||{};
  return String(rule.template||AR_TPL_DEFAULT)
    .replace(/\{name\}/g, esc(rule.name||''))
    .replace(/\{body\}/g, esc(body))
    .replace(/\{time\}/g, esc(tzClock(now)+' '+calTz()))
    .replace(/\{sym\}/g, esc(first.sym||''))
    .replace(/\{value\}/g, esc(arFmtVal(first)))
    .replace(/\{logic\}/g, rule.logic==='or'?'OR':'AND');
}
async function arSendTelegram(rule, res){
  try{
    const r=await fetch('/api/telegram/send',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text:arRenderTpl(rule,res)})});
    const d=await r.json();
    if(!d.ok) arNotify('ارسال تلگرام ناموفق بود', String(d.error||''), 'warn');
    return !!d.ok;
  }catch(e){ return false; }
}
async function arSendBale(rule, res){
  try{
    const r=await fetch('/api/bale/send',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text:arRenderTpl(rule,res)})});
    const d=await r.json();
    if(!d.ok) arNotify('ارسال به بله ناموفق بود', String(d.error||''), 'warn');
    return !!d.ok;
  }catch(e){ return false; }
}
/* real desktop push, on top of the in-page stack. Permission is only ever asked
   from a gesture (saving a rule with this action on); without it the card in the
   stack is still the answer — an alert must never be lost silently. */
function arPush(ruleName, body){
  try{
    if(typeof Notification==='undefined') return false;
    if(Notification.permission!=='granted') return false;
    const n=new Notification(String(ruleName||'MOHMD NEWS'), {body:String(body||''), tag:'mohmd-alert', lang:'fa'});
    setTimeout(function(){ try{ n.close(); }catch(e){} }, 60000);
    return true;
  }catch(e){ return false; }
}
function arAskNotify(){
  try{
    if(typeof Notification==='undefined'||Notification.permission!=='default') return;
    Notification.requestPermission();
  }catch(e){}
}
function arDispatch(rule, res){
  const acts=rule.actions||{};
  const body=res.hits.map(function(h){ return h.label+(h.art?' — '+(h.art.title_fa||h.art.title||''):' — '+arFmtVal(h)); }).join(' · ');
  const entry={ts:Date.now(), name:rule.name||'هشدار', body:body, hits:res.hits.length};
  if(acts.toast) arNotify(rule.name||'هشدار', body);
  if(acts.push && !arPush(rule.name||'هشدار', body) && !acts.toast)
    arNotify(rule.name||'هشدار', body+' — نوتیفیکیشن مرورگر در دسترس نیست، اینجا نشان داده شد', 'warn');
  if(acts.tone) arSquawk();
  if(acts.tg) arSendTelegram(rule, res);
  if(acts.bale) arSendBale(rule, res);
  AR.log.unshift(entry);
  AR.log=AR.log.slice(0,AR_LOG_MAX);
}
/* ── the loop: build a snapshot, run every enabled rule, dispatch ──────── */
function arBuildCtx(){
  const now=Math.floor(Date.now()/1000);
  const evs=[];
  const cal=(typeof ECON!=='undefined'&&ECON)?ECON.calendar:null;
  const events=(cal&&(cal.events||cal))||[];
  (Array.isArray(events)?events:[]).forEach(function(e){
    if(!e||e.ts==null) return;
    if(!e.past&&!(e.actual_n!=null||e.actual)) return;
    if(e.actual_n==null&&!e.actual) return;      /* only releases that printed */
    evs.push(e);
  });
  evs.sort(function(a,b){ return (b.ts||0)-(a.ts||0); });
  const news=((typeof DATA!=='undefined'&&DATA&&DATA.articles)||[]);
  return {prices:(typeof LIVE!=='undefined'&&LIVE)||{}, events:evs, news:news, now:now};
}
function arEvaluate(ctxIn){
  const ctx=ctxIn||arBuildCtx();
  AR.ctx=ctx; AR.lastRun=Date.now();
  const fired=[];
  AR.rules.forEach(function(rule){
    if(rule.enabled===false) return;
    const res=arRuleEval(rule, ctx);
    if(!res.ok) return;
    const sig=res.hits.map(function(h){
      return h.art?('a:'+h.art.id):(h.ev?('e:'+h.ev.ts+'|'+h.ev.title):('p:'+(h.sym||'')+'|'+(Number(h.value)||0).toFixed(4)));
    }).join('~');
    const rt=AR.rt[rule.id]||{};
    /* `|| 30` would turn an explicit 0 (fire on every tick) back into 30 min */
    const cool=Math.max(0, Number(rule.cooldown==null?30:rule.cooldown))*60*1000;
    /* Two different rhythms, deliberately:
       · a threshold/event rule is a *state* — once it fires it stays quiet for
         its cooldown even if the reading keeps wiggling (otherwise “WTI > 100”
         would shout on every 15s tick while the price drifts);
       · a headline is an *event* — the same article never fires the same rule
         twice, however long the rule runs. */
    if(rt.at && (Date.now()-rt.at)<cool) return;
    if(rt.sig===sig && res.hits.some(function(h){ return !!h.art; })) return;
    AR.rt[rule.id]={sig:sig, at:Date.now()};
    rule.fired=(rule.fired||0)+1; rule.last=Date.now();
    fired.push(rule);
    arDispatch(rule, res);
  });
  if(fired.length){ arStore(); arRenderList(); arRenderLog(); }
  arSummary();
  return fired;
}
/* coalesced tick — called from the price poll and the news cycle, runs on the
   next frame-ish slot so a slow rule can never delay a render */
function arTick(){
  if(AR.pending) return;
  AR.pending=setTimeout(function(){
    AR.pending=null;
    try{ arEvaluate(); }catch(e){ console.error('alertTick:', e); }
  }, 400);
}

/* ── builder UI: one row per condition, fields per kind ───────────────── */
function arBlankCond(){ return {kind:'price', sym:(orderedAssets()[0]||'BTC'), op:'gt', value:''}; }
function arFields(c){
  if(c.kind==='price'||c.kind==='change'){
    const syms=orderedAssets();
    return '<select class="ar-sym" aria-label="دارایی">'+syms.map(function(s){
        return '<option value="'+esc(s)+'"'+(c.sym===s?' selected':'')+'>'+esc(s)+'</option>'; }).join('')+'</select>'
      +'<select class="ar-op" aria-label="عملگر">'+Object.keys(AR_OPS).filter(function(k){ return k!=='contains'; }).map(function(k){
        return '<option value="'+k+'"'+(c.op===k?' selected':'')+'>'+AR_OP_SYM[k]+' '+AR_OPS[k]+'</option>'; }).join('')+'</select>'
      +'<input class="ar-val" type="text" inputmode="decimal" style="direction:ltr;text-align:left" placeholder="'
        +(c.kind==='change'?'-3':'100')+'" value="'+esc(String(c.value==null?'':c.value))+'" aria-label="مقدار">'
      +(c.kind==='change'?'<span class="ar-unit">درصد</span>':'<span class="ar-unit">دلار/واحد</span>');
  }
  if(c.kind==='event'){
    return '<select class="ar-impact" aria-label="سطح اهمیت">'+Object.keys(AR_IMPACTS).map(function(k){
      return '<option value="'+k+'"'+((c.impact||'all')===k?' selected':'')+'>'+AR_IMPACTS[k]+'</option>'; }).join('')+'</select>'
      +'<span class="ar-unit">رقم منتشرشده در تقویم</span>';
  }
  /* every value that reaches esc() is stringified first: esc() is the page's
     `.replace()`-based escaper, and a bare number would throw in it */
  return '<input class="ar-terms" type="text" placeholder="Hormuz, Emergency" style="direction:ltr;text-align:left" value="'
      +esc((c.terms||[]).join(', '))+'" aria-label="کلیدواژه‌ها">'
    +'<span class="ar-unit">اعتبار ≥</span>'
    +'<input class="ar-cred" type="text" inputmode="numeric" style="width:74px;direction:ltr;text-align:left" value="'
      +esc(String(c.minCred!=null?Math.round(c.minCred*100):85))+'" aria-label="حداقل اعتبار درصد"><span class="ar-unit">٪</span>'
    +'<input class="ar-within" type="text" inputmode="numeric" style="width:74px;direction:ltr;text-align:left" value="'
      +esc(String(c.within!=null?c.within:240))+'" aria-label="پنجرهٔ زمانی دقیقه"><span class="ar-unit">دقیقهٔ اخیر</span>';
}
function arRenderConds(list){
  const box=document.getElementById('arConds'); if(!box) return;
  const conds=(list&&list.length)?list:[arBlankCond()];
  box.innerHTML=conds.map(function(c,i){
    return '<div class="ar-cond" data-i="'+i+'">'
      +'<span class="ar-idx">'+toFa(i+1)+'</span>'
      +'<select class="ar-kind" aria-label="نوع شرط">'+Object.keys(AR_KINDS).map(function(k){
        return '<option value="'+k+'"'+(c.kind===k?' selected':'')+'>'+AR_KINDS[k]+'</option>'; }).join('')+'</select>'
      +'<span class="ar-fields">'+arFields(c)+'</span>'
      +'<button type="button" class="ar-del" aria-label="حذف شرط">'+ic('trash')+'</button>'
    +'</div>';
  }).join('');
}
function arReadConds(){
  const rows=[].slice.call(document.querySelectorAll('#arConds .ar-cond'));
  return rows.map(function(row){
    const val=function(sel){ const el=row.querySelector(sel); return el?el.value:''; };
    const kind=val('.ar-kind');
    if(kind==='price'||kind==='change') return {kind:kind, sym:val('.ar-sym'), op:val('.ar-op'), value:val('.ar-val').trim()};
    if(kind==='event') return {kind:kind, impact:val('.ar-impact')};
    return {kind:'news', terms:val('.ar-terms').split(',').map(function(s){ return s.trim(); }).filter(Boolean),
            minCred:(parseFloat(val('.ar-cred'))||0)/100, within:parseFloat(val('.ar-within'))||0};
  });
}
function arReadForm(){
  const num=function(id,d){ const v=parseFloat((document.getElementById(id)||{}).value); return isNaN(v)?d:v; };
  return {
    id:AR.edit||arNewId(),
    name:(document.getElementById('arName').value||'').trim(),
    enabled:true,
    logic:document.getElementById('arLogic').value,
    cooldown:num('arCooldown',30),
    when:arReadConds(),
    actions:{toast:document.getElementById('arActToast').checked,
             tone:document.getElementById('arActTone').checked,
             tg:document.getElementById('arActTg').checked,
             bale:document.getElementById('arActBale')?document.getElementById('arActBale').checked:false,
             push:document.getElementById('arActPush').checked},
    template:(document.getElementById('arTemplate').value||'').trim()||AR_TPL_DEFAULT,
    created:Date.now(), fired:0, last:0
  };
}
function arHint(msg, bad){
  const h=document.getElementById('arHint'); if(!h) return;
  h.textContent=msg||'';
  h.classList.toggle('is-bad', !!bad);
  h.classList.toggle('is-ok', !!msg && !bad);
}
function arLogicHint(){
  const l=document.getElementById('arLogic');
  const h=document.getElementById('arLogicHint');
  if(h) h.textContent=l&&l.value==='or'?'با OR: برقرار شدن یک شرط برای اجرای قانون کافی است.':'با AND: همهٔ شرطها باید هم‌زمان برقرار شوند.';
}
function arAddCond(){
  const list=arReadConds(); list.push(arBlankCond()); arRenderConds(list);
}
function arClearForm(){
  AR.edit=null;
  document.getElementById('arName').value='';
  document.getElementById('arLogic').value='and';
  document.getElementById('arCooldown').value='30';
  document.getElementById('arActToast').checked=true;
  document.getElementById('arActTone').checked=false;
  document.getElementById('arActTg').checked=false;
  if(document.getElementById('arActBale')) document.getElementById('arActBale').checked=false;
  document.getElementById('arActPush').checked=false;
  document.getElementById('arTemplate').value=AR_TPL_DEFAULT;
  document.getElementById('arSaveBtn').innerHTML=ic('save')+' ذخیرهٔ قانون';
  arRenderConds([arBlankCond()]); arLogicHint();
}
function arSave(){
  const rule=arReadForm();
  if(arValidate(rule)) return;
  if(AR.edit){
    const i=AR.rules.map(function(r){ return r.id; }).indexOf(AR.edit);
    if(i>=0){
      const old=AR.rules[i];
      rule.id=old.id; rule.created=old.created||rule.created;
      rule.fired=old.fired||0; rule.last=old.last||0; rule.enabled=old.enabled!==false;
      AR.rules[i]=rule;
    } else AR.rules.unshift(rule);
  } else AR.rules.unshift(rule);
  delete AR.rt[rule.id];
  if(rule.actions&&rule.actions.push) arAskNotify();   /* a user gesture may ask once */
  arStore(); arArmTone(); arClearForm(); arRenderList(); arSummary();
  arHint('قانون «'+(rule.name||'')+'» ذخیره شد ✓');
  toast('قانون هشدار ذخیره شد ✓');
}
function arEditRule(id){
  const rule=AR.rules.filter(function(r){ return r.id===id; })[0];
  if(!rule) return;
  AR.edit=id;
  document.getElementById('arName').value=rule.name||'';
  document.getElementById('arLogic').value=rule.logic||'and';
  document.getElementById('arCooldown').value=rule.cooldown!=null?rule.cooldown:30;
  const a=rule.actions||{};
  document.getElementById('arActToast').checked=!!a.toast;
  document.getElementById('arActTone').checked=!!a.tone;
  document.getElementById('arActTg').checked=!!a.tg;
  if(document.getElementById('arActBale')) document.getElementById('arActBale').checked=!!a.bale;
  document.getElementById('arActPush').checked=!!a.push;
  document.getElementById('arTemplate').value=rule.template||AR_TPL_DEFAULT;
  document.getElementById('arSaveBtn').innerHTML=ic('check')+' به‌روزرسانی قانون';
  arRenderConds((rule.when||[]).length?rule.when:[arBlankCond()]);
  arLogicHint();
  const panel=document.getElementById('arPanel');
  if(panel&&panel.scrollIntoView) panel.scrollIntoView({block:'start', behavior:'smooth'});
}
function arToggle(id, on){
  const rule=AR.rules.filter(function(r){ return r.id===id; })[0];
  if(!rule) return;
  rule.enabled=!!on; arStore(); arRenderList(); arSummary();
  toast(on?'قانون فعال شد':'قانون غیرفعال شد');
}
function arDelete(id){
  const rule=AR.rules.filter(function(r){ return r.id===id; })[0];
  if(!rule) return;
  AR.rules=AR.rules.filter(function(r){ return r.id!==id; });
  delete AR.rt[id];
  if(AR.edit===id) arClearForm();
  arStore(); arRenderList(); arSummary();
  toast('قانون حذف شد');
}
function arTestNow(){
  const rule=arReadForm();
  if(arValidate(rule)) return;
  const ctx=arBuildCtx(); AR.ctx=ctx;
  const lines=(rule.when||[]).map(function(c){
    const r=arCondOk(c, ctx);
    return arCondText(c)+' → '+(r===null?'داده در دسترس نیست':(r?'برقرار':'برقرار نیست'));
  });
  const res=arRuleEval(rule, ctx);
  lines.push(res.ok?('نتیجه: قانون برقرار است ('+toFa(res.hits.length)+' شرط)') : 'نتیجه: برقرار نیست');
  if(res.ok) arNotify('اجرای آزمایشی: '+(rule.name||''), res.hits.map(function(h){ return h.label+' — '+arFmtVal(h); }).join(' · '), 'warn');
  arHint(lines.join('\n'));
}
function arRenderList(){
  const box=document.getElementById('arList'); if(!box) return;
  if(!AR.rules.length){
    box.innerHTML='<div class="empty">هنوز قانونی ساخته نشده — با فرم بالا یکی بساز؛ مثلاً «نفت بالای ۱۰۰» یا «تیتر شامل Hormuz با اعتبار بالای ۸۵٪».</div>';
    return;
  }
  box.innerHTML=AR.rules.map(function(r){
    const a=r.actions||{};
    const acts=[a.toast?'توست':null, a.tone?'آهنگ':null, a.tg?'تلگرام':null, a.push?'نوتیفیکیشن':null].filter(Boolean).join(' · ')||'—';
    return '<div class="ar-item'+(r.enabled===false?' is-off':'')+'" data-id="'+esc(r.id)+'">'
      +'<div class="ar-item-hd">'
        +'<label class="switch ar-sw"><input type="checkbox" data-ar-toggle aria-label="فعال/غیرفعال"'
          +(r.enabled===false?'':' checked')+'><span class="slider"></span></label>'
        +'<b>'+esc(r.name||'هشدار')+'</b>'
        +'<span class="ar-tag">'+(r.logic==='or'?'OR':'AND')+' · '+toFa((r.when||[]).length)+' شرط</span>'
        +'<span class="ar-meta">'+toFa(r.fired||0)+' اجرا'
          +(r.last?(' · آخرین '+esc(tzClock(Math.floor(r.last/1000)))):'')+' · هر '+toFa(r.cooldown!=null?r.cooldown:30)+' دقیقه</span>'
        +'<span class="ar-item-btns">'
          +'<button type="button" class="btn ghost sm" data-ar-edit>'+ic('pen')+' ویرایش</button>'
          +'<button type="button" class="btn ghost sm" data-ar-del>'+ic('trash')+' حذف</button></span>'
      +'</div>'
      +'<div class="ar-item-body">'+esc((r.when||[]).map(arCondText).join(r.logic==='or'?' — یا — ':' و '))+'</div>'
      +'<div class="ar-item-acts"><span>اقدام: '+esc(acts)+'</span>'
        +(a.tg?'<span class="ar-tpl">قالب: '+esc((r.template||'').slice(0,60))+'</span>':'')+'</div>'
    +'</div>';
  }).join('');
}
function arRenderLog(){
  const box=document.getElementById('arLog'); if(!box) return;
  if(!AR.log.length){ box.innerHTML='<div class="empty">هنوز قانونی اجرا نشده است.</div>'; return; }
  box.innerHTML=AR.log.slice(0,20).map(function(e){
    const d=new Date(e.ts);
    return '<div class="ar-lrow"><span class="ar-lt">'+esc(tzClock(Math.floor(e.ts/1000)))+'</span>'
      +'<span class="ar-ld">'+esc(String(d.getFullYear())+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'))+'</span>'
      +'<b>'+esc(e.name||'')+'</b>'
      +'<span class="ar-lb">'+esc(e.body||'')+'</span></div>';
  }).join('');
}
function arSummary(){
  const el=document.getElementById('arSummary'); if(!el) return;
  const on=AR.rules.filter(function(r){ return r.enabled!==false; }).length;
  el.textContent=toFa(AR.rules.length)+' قانون ('+toFa(on)+' فعال) · '+toFa(AR.log.length)+' اجرا'
    +(AR.lastRun?(' · آخرین ارزیابی '+esc(tzClock(Math.floor(AR.lastRun/1000)))):'');
}
function arInitUI(){
  const panel=document.getElementById('arPanel');
  if(!panel) return;
  if(!AR.loaded){ AR.loaded=1; arLoad(); }
  const conds=document.getElementById('arConds');
  if(!AR.wired){
    AR.wired=1;
    conds.addEventListener('change', function(ev){
      const k=ev.target.closest('.ar-kind');
      if(!k) return;
      const row=ev.target.closest('.ar-cond');
      const list=arReadConds();
      /* fields differ per kind, so that row restarts from a blank one */
      list[+row.dataset.i]=Object.assign(arBlankCond(), {kind:k.value});
      arRenderConds(list);
    });
    conds.addEventListener('click', function(ev){
      const d=ev.target.closest('.ar-del');
      if(!d) return;
      const list=arReadConds();
      list.splice(+d.closest('.ar-cond').dataset.i, 1);
      arRenderConds(list.length?list:[]);
    });
    const list=document.getElementById('arList');
    list.addEventListener('click', function(ev){
      const item=ev.target.closest('.ar-item');
      if(!item) return;
      if(ev.target.closest('[data-ar-edit]')) arEditRule(item.dataset.id);
      else if(ev.target.closest('[data-ar-del]')) arDelete(item.dataset.id);
    });
    list.addEventListener('change', function(ev){
      const t=ev.target.closest('[data-ar-toggle]');
      if(!t) return;
      arToggle(t.closest('.ar-item').dataset.id, t.checked);
    });
    document.getElementById('arLogic').addEventListener('change', arLogicHint);
    arArmTone();
  }
  if(!conds.querySelector('.ar-cond')) arRenderConds([]);
  if(!document.getElementById('arTemplate').value) document.getElementById('arTemplate').value=AR_TPL_DEFAULT;
  arLogicHint(); arRenderList(); arRenderLog(); arSummary();
  window.__arDebug={AR:AR, condOk:arCondOk, ruleEval:arRuleEval, evaluate:arEvaluate, ctx:arBuildCtx};
}

function initAlerts(){
  const tg=(DATA&&DATA.config&&DATA.config.telegram)||{};
  const tk=document.getElementById('tgToken'), tc=document.getElementById('tgChat');
  if(tg.token && (!tk.value || tk.value.length < 5)) tk.value=tg.token;
  if(tg.chat && !tc.value) tc.value=tg.chat;
  document.getElementById('tgEnabled').checked = tg.enabled!==false;
  document.getElementById('tgMinCred').value = tg.min_credibility!=null?tg.min_credibility:0.70;
  document.getElementById('tgMaxItems').value = tg.max_items||10;
  document.getElementById('tgMaxAge').value = tg.max_age_hours||24;
  document.getElementById('tgAssets').value = (tg.asset_filter||[]).join(', ');
  document.getElementById('tgQuiet').checked = tg.quiet_hours!==false;
  document.getElementById('tgLink').checked = tg.include_link!==false;
  document.getElementById('tgLinkLine').checked = !!tg.link_on_own_line;
  document.getElementById('tgSummary').checked = tg.include_summary!==false;
  document.getElementById('tgHashtags').checked = tg.hashtags!==false;
  document.getElementById('tgEmoji').checked = tg.emoji!==false;
  document.getElementById('tgStars').checked = tg.show_stars!==false;
  document.getElementById('tgSilent').checked = !!tg.silent;
  document.getElementById('tgPin').checked = !!tg.pin;
  document.getElementById('tgLang').value = tg.language||'fa';
  document.getElementById('tgTemplate').value = tg.template||TG_TPL_DEFAULT;
  initBale();
  arInitUI();                    /* the smart-alert builder lives in this view */
}

function toggleTokenVisibility(){
  const tk = document.getElementById('tgToken');
  if(!tk) return;
  tk.type = tk.type === 'password' ? 'text' : 'password';
}

async function detectTelegramChat(){
  const token = document.getElementById('tgToken').value.trim();
  const btn = document.getElementById('btnDetectChat');
  const box = document.getElementById('detectedChatsBox');
  if(!token){
    toast('ابتدا توکن ربات تلگرام را وارد کنید');
    return;
  }
  if(btn) btn.textContent = '⏳ در حال بررسی...';
  try {
    const r = await fetch('/api/telegram/get-chat-id', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({token})
    });
    const d = await r.json();
    if(!d.ok){
      toast('✗ خطا: ' + (d.error || 'ارتباط برقرار نشد'));
      if(box){
        box.style.display = 'block';
        box.innerHTML = `<div style="background:rgba(235,87,87,0.12);padding:10px 14px;border-radius:8px;border:1px solid var(--dn,#eb5757);color:var(--dn,#eb5757);font-size:0.85rem">✗ ${d.error || 'خطا در بررسی توکن'}</div>`;
      }
      return;
    }
    if(d.chats && d.chats.length > 0){
      const latest = d.chats[d.chats.length - 1];
      document.getElementById('tgChat').value = latest.id;
      toast(`✓ چت شناسایی شد: ${latest.title} (${latest.id})`);
      if(box){
        box.style.display = 'block';
        let html = '<div style="background:var(--bg2,#1c2128);padding:10px 14px;border-radius:8px;border:1px solid var(--border,#30363d);font-size:0.85rem">';
        html += `<div style="color:var(--up,#2ecc71);margin-bottom:8px">✓ ربات @${d.bot_username || ''} متصل است. چت‌های شناسایی‌شده:</div>`;
        d.chats.forEach(c => {
          html += `<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.06)">
            <span><b>${c.title}</b> <span style="opacity:0.7">(${c.type})</span> <code style="direction:ltr;display:inline-block">${c.id}</code></span>
            <button class="btn sm" type="button" onclick="document.getElementById('tgChat').value='${c.id}';toast('شناسه چت انتخاب شد');">انتخاب</button>
          </div>`;
        });
        html += '</div>';
        box.innerHTML = html;
      }
    } else {
      toast('ربات متصل است اما پیامی دریافت نکرده است');
      if(box){
        box.style.display = 'block';
        box.innerHTML = `<div style="background:rgba(243,156,18,0.12);padding:10px 14px;border-radius:8px;border:1px solid var(--warn,#f39c12);color:var(--warn,#f39c12);font-size:0.85rem">
          ⚠️ ${d.hint || 'پیامی در ربات یافت نشد.'}
        </div>`;
      }
    }
  } catch(e) {
    toast('خطای اتصال به سرور: ' + e);
  } finally {
    if(btn) btn.textContent = '🔍 تشخیص خودکار چت';
  }
}

async function saveTelegram(){
  const p=tgPayload();
  if(!p.telegram.token||!p.telegram.chat){ toast('توکن و شناسهٔ چت را وارد کنید'); return; }
  const r=await postSettings(p);
  if(r&&r.ok){
    toast('همه تنظیمات تلگرام ذخیره شد ✓');
    if(r.config && r.config.telegram && DATA && DATA.config){
      DATA.config.telegram = r.config.telegram;
    }
  } else {
    toast('خطا در ذخیره تنظیمات');
  }
}

async function testTelegram(){
  const token=document.getElementById('tgToken').value.trim(), chat=document.getElementById('tgChat').value.trim();
  if(!token||!chat){ toast('توکن و شناسهٔ چت را وارد کنید'); return; }
  toast('در حال ارسال پیام تست به تلگرام...');
  const r=await fetch('/api/telegram/test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,chat})});
  const d=await r.json();
  if(d.ok){
    toast('✓ پیام تست با موفقیت ارسال شد — تلگرام خود را چک کنید');
  } else {
    toast('✗ ارسال نشد: ' + (d.error || 'خطای نامشخص'));
  }
}

async function sendNowTelegram(){
  toast('در حال ارسال خلاصه خبرها به تلگرام...');
  const r=await fetch('/api/telegram/send-now',{method:'POST'});
  const d=await r.json();
  if(d.ok){
    toast(`✓ خلاصه ارسال شد (${toFa(d.sent||0)} خبر)`);
  } else {
    toast('✗ ارسال نشد: ' + (d.error || 'خطای نامشخص'));
  }
}

async function previewTelegram(){
  /* server renders with saved config but never sends */
  await saveTelegram();
  const r=await fetch('/api/telegram/preview',{method:'POST'});
  const d=await r.json();
  const box=document.getElementById('tgPreview');
  box.style.display='block';
  box.textContent = d.ok ? d.text.replace(/<[^>]+>/g,'') : ('خطا: '+(d.error||''));
}

/* ═══════════ Bale Messenger Settings ═══════════ */
const BALE_TPL_DEFAULT='🏅 {index}. {title}\n{summary_fa}\n📰 {source} · ⭐ {cred}% {stars} · {assets}\n🕒 {time_fa}\n{link_line}';

function switchMessengerTab(type){
  const tgPanel = document.getElementById('panel-messenger-tg');
  const balePanel = document.getElementById('panel-messenger-bale');
  const tgBtn = document.getElementById('subtab-btn-tg');
  const baleBtn = document.getElementById('subtab-btn-bale');
  if(type === 'bale'){
    if(tgPanel) tgPanel.style.display = 'none';
    if(balePanel) balePanel.style.display = 'block';
    if(tgBtn){ tgBtn.classList.remove('btn'); tgBtn.classList.add('btn', 'ghost'); }
    if(baleBtn){ baleBtn.classList.remove('ghost'); }
  } else {
    if(tgPanel) tgPanel.style.display = 'block';
    if(balePanel) balePanel.style.display = 'none';
    if(tgBtn){ tgBtn.classList.remove('ghost'); }
    if(baleBtn){ baleBtn.classList.remove('btn'); baleBtn.classList.add('btn', 'ghost'); }
  }
}

function balePayload(){
  return {bale:{
    token: document.getElementById('baleToken').value.trim(),
    chat: document.getElementById('baleChat').value.trim(),
    enabled: document.getElementById('baleEnabled').checked,
    min_credibility: parseFloat(document.getElementById('baleMinCred').value)||0.70,
    max_items: parseInt(document.getElementById('baleMaxItems').value)||10,
    max_age_hours: parseFloat(document.getElementById('baleMaxAge').value)||24,
    asset_filter: document.getElementById('baleAssets').value.split(',').map(x=>x.trim().toUpperCase()).filter(Boolean),
    quiet_hours: document.getElementById('baleQuiet').checked,
    include_link: document.getElementById('baleLink').checked,
    include_summary: document.getElementById('baleSummary').checked,
    hashtags: document.getElementById('baleHashtags').checked,
    emoji: document.getElementById('baleEmoji').checked,
    show_stars: document.getElementById('baleStars').checked,
    silent: document.getElementById('baleSilent').checked,
    language: document.getElementById('baleLang').value,
    template: document.getElementById('baleTemplate').value.trim()
  }};
}

function initBale(){
  const bale=(DATA&&DATA.config&&DATA.config.bale)||{};
  const tk=document.getElementById('baleToken'), tc=document.getElementById('baleChat');
  if(tk && bale.token && (!tk.value || tk.value.length < 5)) tk.value = bale.token;
  if(tc && bale.chat && !tc.value) tc.value = bale.chat;
  const be = document.getElementById('baleEnabled');
  if(be) be.checked = bale.enabled!==false;
  const bmc = document.getElementById('baleMinCred');
  if(bmc) bmc.value = bale.min_credibility!=null?bale.min_credibility:0.70;
  const bmi = document.getElementById('baleMaxItems');
  if(bmi) bmi.value = bale.max_items||10;
  const bma = document.getElementById('baleMaxAge');
  if(bma) bma.value = bale.max_age_hours||24;
  const bas = document.getElementById('baleAssets');
  if(bas) bas.value = (bale.asset_filter||[]).join(', ');
  const bq = document.getElementById('baleQuiet');
  if(bq) bq.checked = bale.quiet_hours!==false;
  const bl = document.getElementById('baleLink');
  if(bl) bl.checked = bale.include_link!==false;
  const bs = document.getElementById('baleSummary');
  if(bs) bs.checked = bale.include_summary!==false;
  const bh = document.getElementById('baleHashtags');
  if(bh) bh.checked = bale.hashtags!==false;
  const bem = document.getElementById('baleEmoji');
  if(bem) bem.checked = bale.emoji!==false;
  const bst = document.getElementById('baleStars');
  if(bst) bst.checked = bale.show_stars!==false;
  const bsl = document.getElementById('baleSilent');
  if(bsl) bsl.checked = !!bale.silent;
  const bla = document.getElementById('baleLang');
  if(bla) bla.value = bale.language||'fa';
  const bt = document.getElementById('baleTemplate');
  if(bt) bt.value = bale.template||BALE_TPL_DEFAULT;
}

function toggleBaleTokenVisibility(){
  const tk = document.getElementById('baleToken');
  if(!tk) return;
  tk.type = tk.type === 'password' ? 'text' : 'password';
}

async function detectBaleChat(){
  const token = document.getElementById('baleToken').value.trim();
  const btn = document.getElementById('btnDetectBaleChat');
  const box = document.getElementById('detectedBaleChatsBox');
  if(!token){
    toast('ابتدا توکن ربات بله را وارد کنید');
    return;
  }
  if(btn) btn.textContent = '⏳ در حال بررسی...';
  try {
    const r = await fetch('/api/bale/get-chat-id', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({token})
    });
    const d = await r.json();
    if(!d.ok){
      toast('✗ خطا: ' + (d.error || 'ارتباط برقرار نشد'));
      if(box){
        box.style.display = 'block';
        box.innerHTML = `<div style="background:rgba(235,87,87,0.12);padding:10px 14px;border-radius:8px;border:1px solid var(--dn,#eb5757);color:var(--dn,#eb5757);font-size:0.85rem">✗ ${d.error || 'خطا در بررسی توکن بله'}</div>`;
      }
      return;
    }
    if(d.chats && d.chats.length > 0){
      const latest = d.chats[d.chats.length - 1];
      document.getElementById('baleChat').value = latest.id;
      toast(`✓ چت بله شناسایی شد: ${latest.title} (${latest.id})`);
      if(box){
        box.style.display = 'block';
        let html = '<div style="background:var(--bg2,#1c2128);padding:10px 14px;border-radius:8px;border:1px solid var(--border,#30363d);font-size:0.85rem">';
        html += `<div style="color:var(--up,#2ecc71);margin-bottom:8px">✓ ربات @${d.bot_username || ''} در بله متصل است. چت‌های شناسایی‌شده:</div>`;
        d.chats.forEach(c => {
          html += `<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.06)">
            <span><b>${c.title}</b> <span style="opacity:0.7">(${c.type})</span> <code style="direction:ltr;display:inline-block">${c.id}</code></span>
            <button class="btn sm" type="button" onclick="document.getElementById('baleChat').value='${c.id}';toast('شناسه چت بله انتخاب شد');">انتخاب</button>
          </div>`;
        });
        html += '</div>';
        box.innerHTML = html;
      }
    } else {
      toast('ربات بله متصل است اما پیامی دریافت نکرده است');
      if(box){
        box.style.display = 'block';
        box.innerHTML = `<div style="background:rgba(243,156,18,0.12);padding:10px 14px;border-radius:8px;border:1px solid var(--warn,#f39c12);color:var(--warn,#f39c12);font-size:0.85rem">
          ⚠️ ${d.hint || 'پیامی در ربات بله یافت نشد.'}
        </div>`;
      }
    }
  } catch(e) {
    toast('خطای اتصال به سرور: ' + e);
  } finally {
    if(btn) btn.textContent = '🔍 تشخیص خودکار چت';
  }
}

async function saveBale(){
  const p=balePayload();
  if(!p.bale.token||!p.bale.chat){ toast('توکن و شناسهٔ چت بله را وارد کنید'); return; }
  const r=await postSettings(p);
  if(r&&r.ok){
    toast('همه تنظیمات پیام‌رسان بله ذخیره شد ✓');
    if(r.config && r.config.bale && DATA && DATA.config){
      DATA.config.bale = r.config.bale;
    }
  } else {
    toast('خطا در ذخیره تنظیمات بله');
  }
}

async function testBale(){
  const token=document.getElementById('baleToken').value.trim(), chat=document.getElementById('baleChat').value.trim();
  if(!token||!chat){ toast('توکن و شناسهٔ چت بله را وارد کنید'); return; }
  toast('در حال ارسال پیام تست به پیام‌رسان بله...');
  const r=await fetch('/api/bale/test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,chat})});
  const d=await r.json();
  if(d.ok){
    toast('✓ پیام تست با موفقیت به بله ارسال شد — اپلیکیشن بله را چک کنید');
  } else {
    toast('✗ ارسال نشد: ' + (d.error || 'خطای نامشخص'));
  }
}

async function sendNowBale(){
  toast('در حال ارسال خلاصه خبرها به بله...');
  const r=await fetch('/api/bale/send-now',{method:'POST'});
  const d=await r.json();
  if(d.ok){
    toast(`✓ خلاصه ارسال شد (${toFa(d.sent||0)} خبر)`);
  } else {
    toast('✗ ارسال نشد: ' + (d.error || 'خطای نامشخص'));
  }
}

async function previewBale(){
  await saveBale();
  const r=await fetch('/api/bale/preview',{method:'POST'});
  const d=await r.json();
  const box=document.getElementById('balePreview');
  if(box){
    box.style.display='block';
    box.textContent = d.ok ? d.text : ('خطا: '+(d.error||''));
  }
}

loadData();
pollLive();
dl2Skeleton(6);
setTimeout(function(){ dl2MarkSeen(); }, 15000);

/* ═══════════════════════════════════════════════════════════════════════════
   STREAM MANAGER — one connection, three channels, no polling while it works
   ═══════════════════════════════════════════════════════════════════════════
   Replaces the hand-rolled `connectSSE()` that stood here, and the timers it
   leaned on: prices every 15s, the feed every 60s, a 120s safety net, and every
   one of those refreshes re-rendered a whole component (the ticker rebuilt its
   markup on each tick, the feed replaced #newsGrid — taking the reader's scroll
   position with it).

     transport   WebSocket → SSE → HTTP polling, in that order. A WebSocket is
                 used when the server advertises one (/api/stream/info); this
                 deployment pushes over SSE, which needs no upgrade and no
                 dependency, and the client is written so pointing a proxy at a
                 ws endpoint is the only change required to move to it.
     contract    one socket, three channels routed by event name:
                   prices   → tick frames, applied as micro-updates
                   news     → newly ingested articles, prepended
                   calendar → a release that just landed, flashed in place
     backoff     1s · 2s · 5s · 10s · 20s · 30s … capped at 30s, with jitter so
                 N tabs started together do not reconnect in lockstep. Polling
                 is only started while no transport is alive, and stopped again
                 the moment one connects.
     DOM         one requestAnimationFrame per batch. Only the `.p` / `.c` nodes
                 whose value actually moved are written and flashed: an
                 unchanged symbol costs zero layout work.
     feed        new headlines are inserted above the list and the scroll offset
                 is corrected by exactly the height that was added.
   ═══════════════════════════════════════════════════════════════════════════ */
const SM_BACKOFF=[1000,2000,5000,10000,20000,30000];
const SM_CHANNELS=['prices','news','calendar'];
/* server event name → channel. The server emits `init`, `update` and `prices`
   today (see app.py `_sse_broadcast`) and `calendar` for releases; the extra
   spellings are accepted so a new server event cannot silently vanish. */
const SM_WIRE={prices:'prices', tick:'prices', quote:'prices',
               update:'news', news:'news', init:'news',
               calendar:'calendar', release:'calendar', econ:'calendar'};
const SM_POLL={prices:15000, data:120000, calendar:300000};

/* 1s, 2s, 5s, 10s, 20s, 30s, 30s… with up to 25% jitter */
function smBackoff(attempt){
  const i=Math.max(0, Math.min(SM_BACKOFF.length-1, (parseInt(attempt,10)||1)-1));
  const base=SM_BACKOFF[i];
  return base + Math.floor(Math.random()*Math.min(500, Math.round(base/4)));
}
function smRouteEvent(name){
  return SM_WIRE[String(name==null?'':name).toLowerCase()]||null;
}
/* What actually changed since the previous frame — the whole reason the DOM
   update can be cheap: symbols that did not move produce no entries at all. */
function smPriceDiff(prev, next, fields){
  const keys=fields||['price','change_24h'], out=[];
  const prevMap=prev||{}, nextMap=next||{};
  Object.keys(nextMap).forEach(function(sym){
    const a=prevMap[sym]||{}, b=nextMap[sym]||{}, moved=[];
    keys.forEach(function(f){
      if(b[f]==null) return;
      if(a[f]==null||Number(a[f])!==Number(b[f])) moved.push(f);
    });
    if(!moved.length) return;
    out.push({sym:sym, price:b.price, change:b.change_24h, moved:moved,
              dir:(a.change_24h==null||b.change_24h==null)?0:(b.change_24h>a.change_24h?1:(b.change_24h<a.change_24h?-1:0)),
              dirPrice:(a.price==null||b.price==null)?0:(b.price>a.price?1:(b.price<a.price?-1:0))});
  });
  return out;
}
/* Newest-first merge that neither duplicates nor reorders: the stream and a
   /api/data refresh can both deliver the same story. */
function smMergeNews(existing, incoming, limit){
  const seen={}, merged=[];
  (incoming||[]).forEach(function(a){ if(a&&a.id&&!seen[a.id]){ seen[a.id]=1; merged.push(a); } });
  const fresh=merged.slice();
  (existing||[]).forEach(function(a){ if(a&&a.id&&!seen[a.id]){ seen[a.id]=1; merged.push(a); } });
  merged.sort(function(x,y){ return (y.published_ts||0)-(x.published_ts||0); });
  return {list:(limit?merged.slice(0,limit):merged), fresh:fresh};
}
/* Scroll anchoring, by reference point rather than by height.

   The obvious version (add the height the list grew by) is wrong here: the feed
   is a multi-column grid, so inserting one card repacks the columns and the
   total height can even shrink. What must stay fixed is the element the reader
   is looking at, so the anchor is that element's viewport position: whatever it
   moved down by is exactly what scrollTop has to move down by. */
function smAnchorScroll(prevTop, prevAnchorTop, nextAnchorTop){
  const shift=(Number(nextAnchorTop)||0)-(Number(prevAnchorTop)||0);
  return Math.max(0, (Number(prevTop)||0) + shift);
}
/* Is the feed narrowed right now? A new card prepended into a filtered list can
   be a card that does not belong there, so in that case the renderer is used
   instead of the incremental path (rare, and it keeps the two honest). */
function smFeedFiltered(){
  try{
    const q=(document.getElementById('q').value||'').trim();
    const src=document.getElementById('srcSel').value, kind=document.getElementById('kindSel').value;
    const minC=+document.getElementById('credSlider').value/100;
    return !!(q||(src&&src!=='all')||(kind&&kind!=='all')||minC>0||
              UI.topic!=='all'||UI.asset!=='all'||UI.onlyBookmarked);
  }catch(e){ return true; }
}
function smChangeText(chg){ return (chg>=0?'▲':'▼')+Math.abs(Number(chg)).toFixed(2)+'%'; }
/* The feed scrolls inside `main.app-main`, not the document — anchoring against
   document.scrollingElement silently does nothing (the page itself does not
   scroll at all in this shell), which is how a prepend ends up throwing the
   reader to a different story. Walk up to whatever actually scrolls. */
/* The card the reader is actually looking at, not the first card in the list:
   in a multi-column grid the first card stays in the first row when something
   is inserted before it (it only slides sideways), while the cards below it
   move down a whole row. Anchoring on the topmost *visible* card is therefore
   the only choice that reflects what the eye is following. */
function smPickAnchor(grid, scroller){
  if(!grid||!scroller) return null;
  const top=scroller.getBoundingClientRect().top;
  const kids=grid.children;
  for(let i=0;i<kids.length;i++){
    const r=kids[i].getBoundingClientRect();
    if(r.bottom>top+1) return kids[i];
  }
  return null;
}
function smScroller(from){
  let n=from||document.getElementById('newsGrid');
  while(n&&n!==document.body){
    let cs=null;
    try{ cs=getComputedStyle(n); }catch(e){ cs=null; }
    if(cs&&(cs.overflowY==='auto'||cs.overflowY==='scroll')&&n.scrollHeight>n.clientHeight) return n;
    n=n.parentElement;
  }
  return document.scrollingElement||document.documentElement;
}

/* ── DOM micro-updates ──────────────────────────────────────────────────────
   The price index is built from the markup, not from the data: any element that
   carries `data-sym` (ticker chips, asset table rows) and holds a `.p` and/or
   `.c` child becomes a hit target. That keeps this layer independent of the
   renderers — a new component gets live ticks the moment it declares its symbol. */
let SM_INDEX={}, SM_INDEX_SIZE=0;
function smIndexPrices(root){
  const idx={}, nodes=(root||document).querySelectorAll('[data-sym]');
  for(let i=0;i<nodes.length;i++){
    const sym=nodes[i].getAttribute('data-sym');
    if(!sym) continue;
    const p=nodes[i].querySelector('.p'), c=nodes[i].querySelector('.c');
    if(!p&&!c) continue;
    const slot=idx[sym]||(idx[sym]={p:[], c:[]});
    if(p) slot.p.push(p);
    if(c) slot.c.push(c);
  }
  SM_INDEX=idx;
  SM_INDEX_SIZE=nodes.length;
  return idx;
}
function smPaintPrices(diff){
  if(!diff||!diff.length) return 0;
  if(!SM_INDEX_SIZE) smIndexPrices(document);
  let touched=0;
  diff.forEach(function(t){
    const slot=SM_INDEX[t.sym];
    if(!slot) return;
    slot.p.forEach(function(el){
      const txt=fmtPrice(t.price);
      if(el.textContent===txt) return;
      el.textContent=txt; touched++;
      if(t.dirPrice) flash(el, t.dirPrice);
    });
    slot.c.forEach(function(el){
      if(t.change==null) return;
      const txt=smChangeText(t.change);
      if(el.textContent===txt) return;
      el.textContent=txt; touched++;
      const host=el.parentElement;
      if(host){ host.classList.remove('up','dn'); host.classList.add(t.change>=0?'up':'dn'); }
      if(t.dir) flash(el, t.dir);
    });
  });
  return touched;
}
function smPrependNews(list){
  const grid=document.getElementById('newsGrid');
  const vs=VS.feed;
  if(!grid||!list||!list.length) return 0;
  const seen={};
  /* the identity of what is already on screen comes from the window's own
     item list when it is virtualised — the DOM only holds a few rows, so
     reading ids out of it would re-admit a story that is merely scrolled off */
  if(vs) vs.items.forEach(function(a){ if(a&&a.id) seen[a.id]=1; });
  else [].forEach.call(grid.children, function(n){ const id=n.getAttribute('data-id'); if(id) seen[id]=1; });
  const fresh=list.filter(function(a){ return a&&a.id&&!seen[a.id]; });
  if(!fresh.length) return 0;
  /* windowed path (see below): the head of the list grows and the rows are re-placed from
     the computed offsets, so the reader's position is corrected by arithmetic
     rather than by a DOM probe — which is exact even when the inserted cards
     change the height of the very row the reader is looking at */
  if(vs){ vs.prepend(fresh); return fresh.length; }
  const scroller=smScroller(grid);
  const wasEmpty=!grid.children.length;
  const anchor=smPickAnchor(grid, scroller);                 /* the story at the top of the view */
  const anchorTop=anchor?anchor.getBoundingClientRect().top:0;
  grid.insertAdjacentHTML('afterbegin', fresh.map(cardHTML).join(''));
  const added=Array.prototype.slice.call(grid.children, 0, fresh.length);
  added.forEach(function(el){ el.classList.add('card-enter'); });
  /* only correct the scroll when the reader has scrolled: at the top of the
     list the new cards should simply be there */
  if(anchor&&!wasEmpty&&scroller.scrollTop>0){
    const next=smAnchorScroll(scroller.scrollTop, anchorTop, anchor.getBoundingClientRect().top);
    if(next!==scroller.scrollTop) scroller.scrollTop=next;
  }
  setTimeout(function(){ added.forEach(function(el){ el.classList.remove('card-enter'); }); }, 1000);
  return fresh.length;
}
function smFlashEvent(item){
  if(!item) return false;
  const q=function(s){ return String(s==null?'':s).replace(/"/g,'\\"'); };
  /* the calendar board renders rows as .cal-tr (dashboard's own markup); the
     epoch second is the fallback selector when the keys differ */
  /* the server's key first, the epoch second as the fallback: a release frame
     has to land on its own row without the client rebuilding the calendar */
  let row=item.key?document.querySelector('.cal-tr[data-key="'+q(item.key)+'"]'):null;
  if(!row&&item.ts!=null) row=document.querySelector('.cal-tr[data-ts="'+q(item.ts)+'"]');
  if(!row) return false;
  /* the board's own vocabulary (pending/released), plus a transient marker for
     the one row that changed while the reader was watching */
  row.classList.remove('pending');
  row.classList.add('released','just-released');
  flash(row, (item.better==null?0:item.better)>=0?1:-1);
  setTimeout(function(){ row.classList.remove('just-released'); }, 10000);
  const cell=row.querySelector('.c-num.c-act');
  if(cell&&item.actual_fmt&&cell.textContent!==String(item.actual_fmt)){
    cell.textContent=String(item.actual_fmt);
    cell.classList.remove('sched');
    flash(cell,1);
  }
  return true;
}

/* ── the manager ───────────────────────────────────────────────────────── */
class StreamManager{
  constructor(opts){
    opts=opts||{};
    this.handlers={};
    SM_CHANNELS.forEach((c)=>{ this.handlers[c]=[]; });
    this.info=opts.info||null;      /* /api/stream/info, asked once per connect */
    this.state='idle';              /* idle | connecting | live | reconnecting | polling | stopped */
    this.transport=null;            /* 'ws' | 'sse' | 'poll' */
    this.attempt=0;
    this.socket=null; this.es=null;
    this.timers={};
    this.queue={prices:null, news:[], calendar:[]};
    this.raf=null;
    this.prevPrices={};
    this.announced={};
    this.lastTick=0;
    this.counters={prices:0, news:0, calendar:0, reconnects:0, polls:0, dom:0};
  }
  /* Any channel may be subscribed to, not only the three data ones: `status`
     is emitted here too, and a lazy map means a new channel cannot be silently
     dropped by a missing initialiser (that bug cost a status pill that never
     painted while every other handler worked). */
  on(channel, fn){
    if(!fn) return this;
    if(!this.handlers[channel]) this.handlers[channel]=[];
    this.handlers[channel].push(fn);
    return this;
  }
  emit(channel, payload){
    (this.handlers[channel]||[]).forEach(function(fn){
      try{ fn(payload); }catch(e){ console.error('stream handler '+channel+':', e); }
    });
  }
  /* one probe per connect: the client must not guess a transport */
  probe(){
    return fetch('/api/stream/info',{cache:'no-store'})
      .then(function(r){ return r.ok?r.json():null; })
      .catch(function(){ return null; });
  }
  start(){
    if(this.state==='live'||this.state==='connecting') return this;
    /* the maquette is a single demo file opened from a disk with a stubbed
       fetch: it has no server to stream from, so it says so instead of
       retrying a socket that cannot exist */
    if(window.__MAQUETTE__){ this.state='demo'; smPaintStatus({state:'demo'}); return this; }
    this.state='connecting';
    const self=this;
    const go=function(){
      const info=self.info||{};
      const wantWs=(info.ws||window.__SM_FORCE_WS)&&typeof WebSocket==='function'&&!window.__SM_NO_WS;
      if(wantWs) self.openWs(info.ws||((location.protocol==='https:'?'wss://':'ws://')+location.host+'/api/ws'));
      else self.openSse(info.sse||'/api/stream');
    };
    if(this.info) go();
    else this.probe().then(function(info){ self.info=info; go(); });
    return this;
  }
  stop(){
    this.state='stopped';
    /* the fallback pollers are clock slots now, not browser timers: leaving
       them behind would keep polling a transport that is already closed */
    Object.keys(this.timers).forEach((k)=>{ Clock.off(this.timers[k]); });
    this.timers={};
    try{ if(this.socket) this.socket.close(); }catch(e){}
    try{ if(this.es) this.es.close(); }catch(e){}
    this.socket=null; this.es=null;
    return this;
  }
  alive(transport){
    this.transport=transport;
    this.state='live';
    this.attempt=0;
    this.stopPolling();
    /* a pending reconnect must not fire once the stream is back, or a healthy
       terminal reconnects on top of itself and the counters lie */
    if(this.timers.reconnect){ clearTimeout(this.timers.reconnect); delete this.timers.reconnect; }
    this.emit('status', {state:'live', transport:transport, attempt:0});
  }
  fail(transport){
    this.counters.reconnects++;
    try{ if(this.socket) this.socket.close(); }catch(e){}
    try{ if(this.es) this.es.close(); }catch(e){}
    this.socket=null; this.es=null;
    /* a ws that this server cannot serve is not a failure of the terminal: the
       same push model is available one line down, so step down immediately
       instead of waiting out the backoff for a transport that will never work */
    if(transport==='ws'&&!this.triedSse){ this.triedSse=true; this.openSse((this.info&&this.info.sse)||'/api/stream'); return; }
    this.startPolling();
    const delay=smBackoff(this.attempt+1);
    this.attempt++;
    this.emit('status', {state:'reconnecting', transport:this.transport, retryIn:delay, attempt:this.attempt});
    const self=this;
    clearTimeout(this.timers.reconnect);
    this.timers.reconnect=setTimeout(function(){ self.start(); }, delay);
  }
  openWs(url){
    const self=this;
    let sock;
    try{ sock=new WebSocket(url); }catch(e){ this.fail('ws'); return; }
    this.transport='ws'; this.socket=sock;
    sock.onopen=function(){ self.triedSse=false; self.alive('ws'); };
    sock.onmessage=function(ev){ self.ingest(ev.data); };
    sock.onerror=function(){ try{ sock.close(); }catch(e){} };
    sock.onclose=function(){ if(self.state!=='stopped') self.fail('ws'); };
  }
  openSse(url){
    if(typeof EventSource!=='function'){ this.startPolling(); return; }
    const self=this;
    this.transport='sse';
    const es=new EventSource(url);
    this.es=es;
    es.onopen=function(){ self.alive('sse'); };
    es.onmessage=function(ev){ self.ingest(ev.data, 'message'); };
    Object.keys(SM_WIRE).forEach(function(name){
      es.addEventListener(name, function(ev){ self.ingest(ev.data, name); });
    });
    es.onerror=function(){ if(self.state!=='stopped') self.fail('sse'); };
  }
  /* Accepts either a wire frame ({event, data}) or a bare SSE payload, and
     either an already-parsed object or JSON text. */
  ingest(raw, eventName){
    let frame=raw, name=eventName;
    /* tolerate either order — (payload, event) is what an SSE listener passes,
       (event, payload) is what a hand-built frame looks like */
    if(typeof frame==='string'&&name&&typeof name==='object'){ const t=frame; frame=name; name=t; }
    if(typeof frame==='string'){
      try{ frame=JSON.parse(frame); }catch(e){ return; }
      if(frame&&typeof frame==='object'&&(frame.event||frame.channel)){
        name=frame.event||frame.channel;
        frame=frame.data||frame.payload||frame;
      }
    }
    if(frame&&typeof frame==='object'&&frame.type&&!name) name=frame.type;
    const channel=smRouteEvent(name)||(frame&&smRouteEvent(frame.event))||null;
    if(!channel) return null;
    this.lastTick=Date.now();
    this.counters[channel]++;
    if(channel==='prices'){ this.queue.prices=frame; this.schedule(); }
    else if(channel==='news'){ this.queueNews(frame); }
    else { this.queue.calendar.push(frame); this.schedule(); }
    return channel;
  }
  queueNews(frame){
    if(!frame) return;
    const list=frame.articles||frame.items||(frame.id?[frame]:[]);
    const fresh=[];
    const self=this;
    list.forEach(function(a){ if(a&&a.id&&!self.announced[a.id]){ self.announced[a.id]=1; fresh.push(a); } });
    if(!fresh.length) return;
    this.queue.news=this.queue.news.concat(fresh);
    this.schedule();
  }
  schedule(){
    if(this.raf) return;
    const self=this;
    const run=function(){ self.raf=null; self.flush(); };
    this.raf=(typeof requestAnimationFrame==='function')?requestAnimationFrame(run):setTimeout(run, 16);
  }
  flush(){
    if(this.queue.prices){
      const next=this.queue.prices;
      const diff=smPriceDiff(this.prevPrices, next);
      this.prevPrices=next;
      if(diff.length){
        this.counters.dom+=smPaintPrices(diff);
        this.emit('prices', {prices:next, diff:diff});
      }
    }
    if(this.queue.news.length){
      const fresh=this.queue.news.slice();
      this.queue.news=[];
      const added=smPrependNews(fresh);
      this.emit('news', {fresh:fresh, prepended:added});
    }
    if(this.queue.calendar.length){
      const items=this.queue.calendar.slice();
      this.queue.calendar=[];
      const self=this;
      items.forEach(function(item){ self.emit('calendar', item); });
    }
  }
  /* Polling is a fallback, never a parallel track: it starts only when no
     transport is alive and is cleared the moment one connects. */
  startPolling(){
    if(this.state==='polling') return;
    this.state='polling';
    this.emit('status', {state:'polling', transport:'poll', attempt:this.attempt});
    const self=this;
    const rates=(this.info&&this.info.poll_seconds)||SM_POLL;
    if(!this.timers.prices&&typeof pollLive==='function'){
      this.timers.prices=Clock.every((rates.prices||SM_POLL.prices)*1000, function(){ self.counters.polls++; pollLive(); }, {label:'stream-poll-prices'});
    }
    if(!this.timers.data&&typeof loadData==='function'){
      this.timers.data=Clock.every((rates.data||120)*1000, function(){ self.counters.polls++; loadData(); }, {label:'stream-poll-data'});
    }
    if(!this.timers.calendar&&typeof loadCalendar==='function'){
      this.timers.calendar=Clock.every((rates.calendar||300)*1000, function(){
        self.counters.polls++;
        if(typeof UI!=='undefined'&&UI.view==='calendar') loadCalendar();
      }, {label:'stream-poll-calendar'});
    }
  }
  stopPolling(){
    ['prices','data','calendar'].forEach((k)=>{ if(this.timers[k]){ Clock.off(this.timers[k]); delete this.timers[k]; } });
  }
  stats(){
    return {state:this.state, transport:this.transport, attempt:this.attempt,
            age:this.lastTick?Math.round((Date.now()-this.lastTick)/1000):null,
            counters:Object.assign({}, this.counters)};
  }
}

/* ── wiring ─────────────────────────────────────────────────────────────── */
function smPaintStatus(st){
  const item=document.getElementById('smItem'), dot=document.getElementById('smDot'), txt=document.getElementById('smTxt');
  if(!item) return;
  const label=st.state==='live'?(st.transport==='ws'?'WebSocket':'SSE live')
            : st.state==='polling'?'Polling fallback'
            : st.state==='reconnecting'?('Reconnect in '+Math.round((st.retryIn||0)/1000)+'s')
            : st.state==='demo'?'Demo (offline)'
            : st.state;
  item.dataset.mode=st.state==='live'?'online':(st.state==='polling'||st.state==='demo'?'warn':'offline');
  if(txt) txt.textContent=label;
  if(dot) dot.className='pwa-dot '+(st.state==='live'?'is-on':(st.state==='polling'?'is-idle':'is-off'));
  item.title='کانال‌های زنده: قیمت، خبر، تقویم — '+(st.transport||'—')+
             (st.attempt?(' · تلاش '+toFa(st.attempt)):'')+' · پوش‌ها: '+toFa((Stream.counters&&Stream.counters.prices)||0);
}
const Stream=new StreamManager();
Stream.on('prices', function(p){
  LIVE=p.prices||LIVE;
  if(typeof paintLive==='function') paintLive();   /* an open report head */
  if(typeof paintFng==='function') paintFng();
  if(typeof arTick==='function') arTick();         /* alert rules see the tick */
  /* the pill counts frames; refresh its tooltip without repainting the label */
  const item=document.getElementById('smItem');
  if(item&&Stream.transport) item.title='کانال‌های زنده: قیمت، خبر، تقویم — '+Stream.transport+
    ' · فریم‌های قیمت: '+toFa(Stream.counters.prices)+' · به‌روزرسانی DOM: '+toFa(Stream.counters.dom);
});
Stream.on('news', function(p){
  const fresh=p.fresh||[];
  if(!fresh.length) return;
  if(!DATA) DATA={};
  const merged=smMergeNews(DATA.articles||[], fresh);
  DATA.articles=merged.list;
  if(typeof smFeedFiltered==='function'&&smFeedFiltered()){
    /* a filter is on: the incremental path would insert a card the filter
       excludes, so the renderer does it (correct beats cheap) */
    if(typeof renderFeed==='function') renderFeed();
  }
  const cnt=document.getElementById('feedCount');
  if(cnt) cnt.textContent=toFa(DATA.articles.length)+' خبر';
  const empty=document.getElementById('feedEmpty');
  if(empty&&DATA.articles.length) empty.style.display='none';
  if(typeof renderChips==='function') renderChips();
  if(typeof toast==='function'&&p.prepended) toast('خبر جدید — '+toFa(p.prepended)+' مورد');
});
Stream.on('calendar', function(item){
  const flashed=smFlashEvent(item);
  /* the released value has to survive the next render of the board */
  try{
    if(typeof ECON!=='undefined'&&ECON&&ECON.calendar&&ECON.calendar.events){
      [ECON.calendar, ECON.calendar_next].forEach(function(src){
        ((src&&src.events)||[]).forEach(function(e){
          const ek=(e.ts||0)+'_'+String(e.title||'').replace(/[^a-zA-Z0-9]/g,'').slice(0,20);
          if((item.key&&ek===item.key)||(e.ts===item.ts&&e.title===item.title)){
            e.actual=item.actual; e.actual_fmt=item.actual_fmt||e.actual_fmt; e.past=true; e.released=true;
          }
        });
      });
    }
  }catch(e){}
  if(typeof toast==='function'){
    toast((item.country?('['+item.country+'] '):'')+(item.title||'')+' — '+(item.actual_fmt||item.actual||'')+
          (flashed?'':' (رویداد در نمای تقویم نیست)'), item.impact==='High'?'warn':'info');
  }
  if(typeof arTick==='function') arTick();
});
Stream.on('status', smPaintStatus);
Stream.start();
window.Stream=Stream;
window.SM=Stream;
</script>

<!-- ══ REDESIGN 2026-09-26 · TradingView chart engine + report helpers ══════
     The widget mount, the fullscreen mode, the citation rows and the section
     jumps — one readable layer, loaded after the app script so it owns these
     globals. Nothing here touches the data pipeline. -->
<script>
/* ── the official TradingView Advanced Chart widget (free, key-less) ─────── */
const TV_SYMBOL={
  BTC:'BINANCE:BTCUSDT', ETH:'BINANCE:ETHUSDT', BNB:'BINANCE:BNBUSDT',
  SOL:'BINANCE:SOLUSDT', XRP:'BINANCE:XRPUSDT', ADA:'BINANCE:ADAUSDT',
  DOGE:'BINANCE:DOGEUSDT', LINK:'BINANCE:LINKUSDT',
  XAU:'OANDA:XAUUSD', XAG:'OANDA:XAGUSD', WTI:'TVC:USOIL',
  DXY:'TVC:DXY', SPX:'FOREXCOM:SPXUSD', VIX:'TVC:VIX'
};
const TV_INTERVAL={'5':'5','60':'60','4h':'240','1d':'D'};
function tvSymbolFor(sym){
  const s=String(sym||'').toUpperCase();
  if(TV_SYMBOL[s]) return TV_SYMBOL[s];
  const m=((DATA&&DATA.assets_meta&&DATA.assets_meta[s])||{});
  const y=String(m.yahoo||'').toUpperCase().trim();
  if(!y) return s;
  if(m.is_crypto||/-USD$/.test(y)) return 'BINANCE:'+y.replace(/-USD.*$/,'')+'USDT';
  return y;                            /* stocks and futures keep their ticker */
}
let TV_STAMP='';                       /* sym|tf|size the mounted widget serves */
let TV_FALLBACK_TIMER=null;
let TV_PING=null;                      /* the clock slot that watches for the iframe */
/* ── leaving a view must actually release it ─────────────────────────────
   The TradingView embed builds an iframe, a websocket to its own backend and a
   layout listener inside that frame; the fallback chart above builds a canvas
   and its own resize observer. Switching tabs used to leave both alive — a
   widget nobody can see, and the report tab paid for it on every visit. */
function tvTeardown(){
  if(TV_PING){ Clock.off(TV_PING); TV_PING=null; }
  if(TV_MOUNT_RETRY){ clearTimeout(TV_MOUNT_RETRY); TV_MOUNT_RETRY=null; }
  if(TV_FALLBACK_TIMER){ clearTimeout(TV_FALLBACK_TIMER); TV_FALLBACK_TIMER=null; }
  TV_STAMP='';
  const host=document.getElementById('tvholder');
  if(host) host.innerHTML='';
  const tag=document.getElementById('tvLiveTag');
  if(tag) tag.innerHTML='';
  const fail=document.getElementById('tvfail');
  if(fail) fail.style.display='none';
  if(document.body.classList.contains('tv-full')){
    document.body.classList.remove('tv-full');
    const box=document.getElementById('chartBox');
    if(box) box.classList.remove('tvfull');
    const b=document.getElementById('tvFullBtn');
    if(b){ b.classList.remove('on'); b.innerHTML='⛶ بزرگ‌نمایی'; }
  }
}
/* What leaving a view releases, and what it deliberately keeps.

   The TradingView embed goes: it is an iframe with its own connection to its
   own backend, it is the single most expensive thing this page can hold, and
   showView() re-mounts it from scratch on the way back in.

   The windowed grids keep their rows: those rows are a few dozen nodes, and
   they *are* the reader's scroll position. */
function teardownView(prev){
  if(prev==='reports') tvTeardown();
}
/* the page may be closed from any view, including the one holding the embed */
if(typeof window!=='undefined'&&window.addEventListener)
  window.addEventListener('pagehide', function(){ try{ tvTeardown(); }catch(e){} });
function mountTVChart(force){
  const host=document.getElementById('tvholder'), rep=window.__rep;
  if(!host||!rep) return;
  /* The widget measures its container once, at mount. Doing that while the
     reports tab is still hidden sizes the iframe to nothing and it never
     re-measures — which is why the chart used to come back tiny. Wait for the
     tab instead of mounting blind. Do NOT test offsetParent here: inside the
     fullscreen panel the ancestor is position:fixed and offsetParent is null
     for every element in the subtree, which would block exactly the case we
     just resized for. A real box is what we need. */
  const hr = host.getBoundingClientRect();
  if(!(hr.width > 4 && hr.height > 4)){
    if(TV_MOUNT_RETRY) clearTimeout(TV_MOUNT_RETRY);
    TV_MOUNT_RETRY=setTimeout(()=>mountTVChart(true),200);
    return;
  }
  if(TV_MOUNT_RETRY){ clearTimeout(TV_MOUNT_RETRY); TV_MOUNT_RETRY=null; }
  const sym=rep.symbol||'';
  const stamp=sym+'|'+TVW.tf+'|'+(document.body.classList.contains('tv-full')?'full':'inline');
  if(!force&&TV_STAMP===stamp&&host.querySelector('iframe')) return;
  TV_STAMP=stamp;
  const fail=document.getElementById('tvfail'); if(fail) fail.style.display='none';
  host.innerHTML='<div class="tradingview-widget-container" style="block-size:100%">'
    +'<div class="tradingview-widget-container__widget" style="block-size:100%"></div></div>';
  const box=host.querySelector('.tradingview-widget-container__widget');
  const conf={
    autosize:true, symbol:tvSymbolFor(sym), interval:TV_INTERVAL[TVW.tf]||'60',
    timezone:'Asia/Tehran', theme:'dark', style:'1', locale:'en',
    /* the widget ships a cool blue-black; the app is midnight navy with an
       electric-blue accent, and the hole it used to punch in the palette was
       the loudest thing on the report tab. Same depth, same hairline colour. */
    backgroundColor:'rgba(12,17,28,1)', gridColor:'rgba(160,180,210,0.07)',
    fontColor:'#AFB9C8',
    hide_side_toolbar:false, allow_symbol_change:true, withdateranges:true,
    save_image:true, hide_volume:false, support_host:'https://www.tradingview.com'
  };
  const sc=document.createElement('script');
  sc.type='text/javascript'; sc.async=true;
  sc.src='https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
  sc.innerHTML=JSON.stringify(conf);
  sc.onerror=()=>showTvFail();                      /* blocked / offline */
  box.appendChild(sc);
  /* the live pill lights up only once the widget has really mounted */
  let tries=0;
  const ping=Clock.every(500, ()=>{
    if(TV_PING!==ping) return;                 /* a newer mount owns the slot */
    const tag=document.getElementById('tvLiveTag');
    if(host.querySelector('iframe')){
      Clock.off(ping); TV_PING=null;
      if(tag) tag.innerHTML='<span class="live-dot"></span>لایو';
      return;
    }
    if(++tries>26){ Clock.off(ping); TV_PING=null; }
  }, {label:'tv-ping'});
  TV_PING=ping;
  if(TV_FALLBACK_TIMER) clearTimeout(TV_FALLBACK_TIMER);
  TV_FALLBACK_TIMER=setTimeout(()=>{
    if(TV_STAMP!==stamp) return;
    if(!host.querySelector('iframe')) showTvFail();
  }, 15000);
}
/* the widget could not mount: blocked, offline, or simply slow. Say exactly
   that, and point at the chart on TradingView — there is no second chart in
   the app to quietly substitute. */
function showTvFail(msg){
  const fail=document.getElementById('tvfail');
  if(!fail) return;
  fail.style.display='block';
  const sym=(window.__rep&&window.__rep.symbol)||'';
  const url='https://www.tradingview.com/chart/?symbol='+encodeURIComponent(tvSymbolFor(sym));
  fail.innerHTML=(msg||'نمودار تریدینگ‌ویو بارگذاری نشد (اینترنت یا تاخیر ویجت).')+
    ` <a class="mlink" href="${url}" target="_blank" rel="noopener">باز کردن در تریدینگ‌ویو</a>`;
}
/* «⛶ بزرگ‌نمایی»: the panel leaves the grid and fills the viewport */
function toggleTvFull(){
  const box=document.getElementById('chartBox'); if(!box) return;
  const on=box.classList.toggle('tvfull');
  document.body.classList.toggle('tv-full', on);
  const b=document.getElementById('tvFullBtn');
  if(b){ b.innerHTML=on?'🗗 بستن تمام‌صفحه':'⛶ بزرگ‌نمایی'; b.classList.toggle('on', on); }
  if(on&&window.__rep) mountTVChart(true);
  setTimeout(()=>{ try{ window.dispatchEvent(new Event('resize')); }catch(e){} }, 80);
}
function exitTvFull(){
  const box=document.getElementById('chartBox');
  if(box&&box.classList.contains('tvfull')) toggleTvFull();
}
/* ── report helpers ───────────────────────────────────────────────────────── */
/* one citation row: number, Persian title, English original, source, date,
   time and credibility. The row itself opens the article. */
function citeHTML(it, fa){
  const link=it.link||'';
  const inner=`<span class="idx">${toFa(it.index_fa||it.index||'')}</span>
    <span class="ct-body">
      <span class="ct-t">${esc(it.title_fa||it.title_en||'')}</span>
      ${it.title_fa?`<span class="ct-en">${esc(it.title_en||'')}</span>`:''}
      <span class="ct-meta">
        <span class="ct-src">${esc(it.source||'')}</span>
        ${it.date_fa?`<span>${ic('calendar')} ${esc(it.date_fa)}</span>`:''}
        ${it.time_fa?`<span>${ic('clock')} ${esc(it.time_fa)}</span>`:''}
        ${it.credibility_fa?`<span class="ct-cred">${ic('check')} ${esc(it.credibility_fa)}</span>`:''}
      </span>
      ${(!fa&&it.why_en)?`<span class="why" dir="ltr">${esc(it.why_en)}</span>`:''}
    </span>`;
  return link
    ? `<a class="cite" href="${attr(safeUrl(link))}" target="_blank" rel="noopener">${inner}<span class="ct-go">↗</span></a>`
    : `<div class="cite">${inner}<span></span></div>`;
}
/* the sources button: one click opens the list for that section */
function toggleCites(btn){
  const box=btn.closest('.cites'); if(!box) return;
  const open=box.classList.toggle('open');
  btn.setAttribute('aria-expanded', open?'true':'false');
  const a=btn.querySelector('.cb-a');
  if(a) a.textContent=open?'بستن منابع':'نمایش منابع';
}
/* ══ FILTER MODEL 3 — the shared toolbar ═══════════════════════════════════
   Every view now shows ONE line: the filter button with a live count of what
   is switched on, those filters as removable chips, and the result count.
   The sheet that drops out of the button holds every control. Nothing here
   changes what a filter *does* — the same selects and chip containers drive
   the same renderers, they are just not in the reader's face until asked. */
function tbCloseAll(except){
  document.querySelectorAll('.fsheet.open').forEach(s=>{ if(s!==except) s.classList.remove('open'); });
  document.querySelectorAll('.tb-btn[aria-expanded="true"]').forEach(b=>{
    const s=b.getAttribute('aria-controls')&&document.getElementById(b.getAttribute('aria-controls'));
    if(!s||s!==except) b.setAttribute('aria-expanded','false');
  });
}
function tbToggle(id){
  const sheet=document.getElementById(id); if(!sheet) return;
  const open=!sheet.classList.contains('open');
  tbCloseAll(open?sheet:null);
  sheet.classList.toggle('open', open);
  const bar=sheet.closest('.tb');
  const btn=bar?bar.querySelector('.tb-btn'):null;
  if(btn) btn.setAttribute('aria-expanded', open?'true':'false');
  if(open){
    /* the sheet must fit the room left *below its button*, not a fixed slice of
       the viewport — otherwise the footer (and “clear all”) sits off-screen on
       short windows. */
    if(bar){
      try{
        const r=bar.getBoundingClientRect();
        const room=Math.max(240, Math.min(window.innerHeight-r.bottom-18, Math.round(window.innerHeight*0.72)));
        sheet.style.maxBlockSize=room+'px';
      }catch(e){}
    }
    const f=sheet.querySelector('input[type=text],input:not([type])');
    if(f){ try{ f.focus({preventScroll:true}); }catch(e){} }
  }
}
function tbClose(id){ const s=document.getElementById(id); if(s) s.classList.remove('open'); }
/* Clicking outside or pressing Esc puts the page back to its quiet state.
   The hit is remembered in the CAPTURE phase on purpose: a click inside the
   sheet can delete the very node it landed on (setAssetFilter re-renders the
   chip grid), so by the time the event bubbles to the document the target is
   detached and closest('.tb') is null — which used to close the sheet on every
   single filter toggle. Detached targets are ignored for the same reason. */
let TB_HIT = false;
document.addEventListener('click', e=>{
  const t=e.target;
  TB_HIT = !!(t && t.closest && t.closest('.tb'));
}, true);
document.addEventListener('click', e=>{
  const t=e.target;
  if(TB_HIT || (t && t.isConnected === false)) return;
  tbCloseAll(null);
});
document.addEventListener('keydown', e=>{ if(e.key==='Escape') tbCloseAll(null); });
/* a resize re-flows the page under an open sheet; put it away rather than leave
   it pointing at a button that has moved */
window.addEventListener('resize', ()=>tbCloseAll(null));
function tbChipHTML(label, act){
  return `<button class="tb-chip" title="حذف این فیلتر" onclick="${act}">${label}<span class="x">✕</span></button>`;
}
/* items = [[label, onclick], …]; assetChip is an optional non-removable chip */
function tbPaint(badgeId, liveId, btnId, items, assetChip, lang){
  /* the calendar's toolbar reads in English, the rest of the app in Persian */
  const en = lang === 'en';
  const badge=document.getElementById(badgeId), live=document.getElementById(liveId), btn=document.getElementById(btnId);
  if(badge){ const n=en?String(items.length):toFa(items.length); badge.textContent=n; badge.setAttribute('data-n', String(items.length)); }
  if(btn) btn.classList.toggle('on', items.length>0);
  if(!live) return;
  let h = assetChip || '';
  h += items.slice(0,4).map(it=>tbChipHTML(it[0], it[1])).join('');
  if(items.length>4) h += `<span class="tb-chip more">+${en?String(items.length-4):toFa(items.length-4)} ${en?'more filters':'فیلتر دیگر'}</span>`;
  live.innerHTML = h;
}
function valOf(id){ const el=document.getElementById(id); return el?el.value:''; }
function txtOf(sel){
  const el=document.querySelector(sel); if(!el) return '';
  const o=el.options?el.options[el.selectedIndex]:null;
  return String((o&&o.textContent)||el.value||'').trim();
}
function faAssetName(sym){
  const m=((typeof DATA!=='undefined'&&DATA&&DATA.assets_meta)||{})[sym]||{};
  const v=m.fa;
  return (v&&!isAsciiName(v))?v:(ASSET_FA_FALLBACK[sym]||v||sym);
}
/* topics arrive from the feed in English; the map above carries the Persian
   name for every one the scraper emits */
function faTopic(t){ return FA_TOPIC[t]||t||''; }
function setSel(id,v){ const el=document.getElementById(id); if(el){ el.value=v; renderFeed(); } }
function setCred(v){
  const s=document.getElementById('credSlider'), cv=document.getElementById('credVal');
  if(s) s.value=v;
  if(cv) cv.textContent=toFa(v)+'٪';
  renderFeed();
}
function setQ(v){ const q=document.getElementById('q'); if(q) q.value=v; renderFeed(); }
function renderFeedToolbar(){
  const items=[];
  if(UI.onlyBookmarked) items.push([ic('star')+' نشان‌شده‌ها', "UI.onlyBookmarked=false;renderChips();renderFeed()"]);
  if(UI.asset&&UI.asset!=='all') items.push([assetIc(UI.asset)+' '+faAssetName(UI.asset), "setAssetFilter('"+UI.asset+"')"]);
  if(UI.topic&&UI.topic!=='all') items.push([topicIc(UI.topic)+' '+(FA_TOPIC[UI.topic]||UI.topic), "setTopicFilter('"+UI.topic+"')"]);
  const kind=valOf('kindSel');
  if(kind&&kind!=='all') items.push([ic('book')+' '+(((typeof DATA!=='undefined'&&DATA&&DATA.kind_labels)||{})[kind]||kind), "setSel('kindSel','all')"]);
  const src=valOf('srcSel');
  if(src&&src!=='all') items.push([ic('bank')+' '+esc(src), "setSel('srcSel','all')"]);
  const cred=parseInt(valOf('credSlider')||'0',10)||0;
  if(cred>0) items.push([ic('star')+' اعتبار ≥ '+toFa(cred)+'٪', 'setCred(0)']);
  const sort=valOf('sortSel');
  if(sort&&sort!=='new') items.push(['⇅ '+esc(txtOf('#sortSel')), "setSel('sortSel','new')"]);
  const q=document.getElementById('q');
  if(q&&q.value.trim()) items.push([ic('search')+' «'+esc(q.value.trim().slice(0,16))+'»', "setQ('')"]);
  tbPaint('feedBadge','feedLive','feedBtn',items);
}
function renderIdeasToolbar(){
  const sym=ideasSym();
  const items=[];
  const kind=UI.ideasKind||'all';
  if(kind!=='all') items.push([ic('grid')+' '+esc(txtOf('#ideasKindChips')), "setIdeasKind('all')"]);
  const tf=UI.ideasTf||'all';
  /* the timeframe list is built from the ideas that actually loaded, so the
     select can legitimately have no matching option yet — name the value itself */
  if(tf!=='all') items.push([ic('clock')+' '+esc(txtOf('#ideasTfChips')||tfLabel(tf)), "setIdeasTf('all')"]);
  const srt=UI.ideasSort||'popular';
  if(srt!=='popular') items.push(['⇅ '+esc(txtOf('#ideasSortChips')), "setIdeasSort('popular')"]);
  tbPaint('ideasBadge','ideasLive','ideasBtn',items);
  const cnt=document.getElementById('ideasCount'), c=IDEAS_CACHE[sym];
  if(cnt) cnt.textContent = c ? (c.err ? '—' : (toFa((c.items||[]).length)+' ایده')) : 'در حال خواندن…';
}
function renderEtfToolbar(){
  const nm=document.getElementById('etfBtnName');
  if(nm){ const g=UI.etfGroup||'all'; nm.textContent = g==='all' ? 'همه' : (ETF_GROUP_FA[g]||g); }
  const btn=document.getElementById('etfBtn'); if(btn) btn.classList.toggle('on', (UI.etfGroup||'all')!=='all');
}
/* the calendar keeps all six controls, but only the ones you changed show on
   the line — including the timezone, which is easy to forget you moved */
function renderCalToolbar(){
  const items=[];
  const imp=valOf('calImpact');
  if(imp&&imp!=='all') items.push([ic('target')+' '+esc(txtOf('#calImpact')), "setSelCal('calImpact','all')"]);
  const ccys=[...(CAL.ccys||[])];
  if(ccys.length) items.push([ic('swap')+' '+ccys.map(esc).join(', '), "clearCalCcy();renderCalendar()"]);
  const srt=valOf('calSort');
  if(srt&&srt!=='time') items.push(['⇅ '+esc(txtOf('#calSort')), "setSelCal('calSort','time')"]);
  const tz=valOf('calTz');
  if(tz&&tz!=='Asia/Tehran') items.push([ic('clock')+' '+esc(txtOf('#calTz')), "setSelCal('calTz','Asia/Tehran')"]);
  const q=document.getElementById('calQ');
  if(q&&q.value.trim()) items.push([ic('search')+' «'+esc(q.value.trim().slice(0,16))+'»', "setCalQ('')"]);
  const hp=document.getElementById('calHidePast');
  if(hp&&hp.checked) items.push([ic('eye-off')+' released hidden', 'setCalHidePast(false)']);
  tbPaint('calBadge','calLive','calBtn',items,null,'en');
  /* the result count on the far side of the line — the feed and the ideas tab
     both carry one, the calendar's slot was painted empty */
  const cnt=document.getElementById('calFiltersCount');
  if(cnt){
    const n=(window.__calDayCount||0);
    cnt.innerHTML='<b>'+n+'</b> '+(n===1?'event':'events');
  }
}
function setSelCal(id,v){ const el=document.getElementById(id); if(el){ el.value=v; renderCalendar(); } }
function toggleCalCcy(inp){
  if(!CAL.ccys) CAL.ccys=new Set();
  if(inp.checked) CAL.ccys.add(inp.value); else CAL.ccys.delete(inp.value);
  const lab=inp.closest('.ccy'); if(lab) lab.classList.toggle('on', inp.checked);
  renderCalendar();
}
function clearCalCcy(){
  CAL.ccys=new Set();
  document.querySelectorAll('#calCurChips input[type=checkbox]').forEach(function(i){
    i.checked=false; const l=i.closest('.ccy'); if(l) l.classList.remove('on');
  });
}
function setCalQ(v){ const q=document.getElementById('calQ'); if(q) q.value=v; renderCalendar(); }
function setCalHidePast(v){ const hp=document.getElementById('calHidePast'); if(hp) hp.checked=!!v; renderCalendar(); }
function resetCalFilters(){
  const set=(id,v)=>{ const el=document.getElementById(id); if(el) el.value=v; };
  set('calImpact','all'); set('calSort','time'); set('calTz','Asia/Tehran');
  clearCalCcy();
  const q=document.getElementById('calQ'); if(q) q.value='';
  const hp=document.getElementById('calHidePast'); if(hp) hp.checked=false;
  renderCalendar();
  if(typeof toast==='function') toast('Calendar filters cleared');
}
/* ── filter bar helpers ───────────────────────────────────────────────────── */
function syncFeedReset(){
  const btn=document.getElementById('feedReset'); if(!btn) return;
  const val=id=>{ const el=document.getElementById(id); return el?el.value:''; };
  const q=document.getElementById('q');
  const on=(UI.asset&&UI.asset!=='all')||(UI.topic&&UI.topic!=='all')||UI.onlyBookmarked
    ||val('srcSel')!=='all'||val('kindSel')!=='all'||val('sortSel')!=='new'
    ||(+val('credSlider')||0)>0||!!(q&&q.value.trim());
  btn.hidden=!on;
  if(typeof renderFeedToolbar==='function') renderFeedToolbar();   /* FILTER MODEL 3 toolbar */
}
function resetFeedFilters(){
  UI.asset='all'; UI.topic='all'; UI.onlyBookmarked=false;
  const q=document.getElementById('q'); if(q) q.value='';
  const set=(id,v)=>{ const el=document.getElementById(id); if(el) el.value=v; };
  set('sortSel','new'); set('kindSel','all'); set('srcSel','all'); set('credSlider',0);
  const cv=document.getElementById('credVal'); if(cv) cv.textContent='۰٪';
  renderChips(); renderFeed();
  toast('فیلترها پاک شد');
}
/* jump inside the report pane without moving the whole page */
function jumpRepSec(id){
  const doc=document.getElementById('repDoc'), el=document.getElementById(id);
  if(!doc||!el) return;
  const top=doc.scrollTop+(el.getBoundingClientRect().top-doc.getBoundingClientRect().top)-10;
  try{ doc.scrollTo({top:top, behavior:'smooth'}); }catch(e){ doc.scrollTop=top; }
}
</script>

<script>
/* ══ COMMAND PALETTE — Ctrl/Cmd+K ══════════════════════════════════════════
   One field over the whole product: every view, every covered asset (jumping
   straight to its report) and the handful of actions worth a shortcut. ↑ ↓
   move, Enter runs, Esc closes, a click outside closes. */
(function(){
  const VIEWS=[
    ['feed','جریان زندهٔ اخبار','news'],
    ['reports','تحلیل و گزارش‌ها','chart'],
    ['channel','کانال طلا و سکه','coins'],
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

  window.cmdkOpen=open; window.cmdkClose=close;
  const field=document.getElementById('cmdkQ');
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
</script>
<script>
/* ═══════════════════════════════════════════════════════════════════════════
   MOHMD NEWS — ON-CHAIN WHALE TRACKER CONTROLLER
   ═══════════════════════════════════════════════════════════════════════════ */

/* Audio reader removed per specification */


/* ── 2 · ON-CHAIN WHALE LIQUIDITY TRACKER ── */
class WhaleTracker {
  constructor() {
    this.filterAsset = 'ALL';
    this.filterFlow = 'ALL';
    this.txs = this.initSeedData();
    this.loadLive();
  }

  /* real on-chain BTC moves from the mempool (/api/whales/live) prepended to
     the seed rows; a failed fetch just leaves the seed board as it is */
  async loadLive() {
    try {
      const r = await fetch('/api/whales/live');
      const j = await r.json();
      if (!j || j.ok === false || !(j.whales || []).length) return;
      const now = Date.now();
      const live = j.whales.map((w, i) => ({
        id: w.id || ('live-' + i),
        ts: now - i * 30000,
        asset: w.asset || 'BTC',
        amount: w.amount || 0,
        usd: w.usd || 0,
        from: 'Unknown (on-chain)',
        to: 'Mempool — در انتظار تأیید',
        type: 'mempool',
        tag: w.tag || 'میم‌پول',
        hash: w.hash || '',
      }));
      this.txs = live.concat(this.txs.filter(t => t.type !== 'mempool'));
      this.render();
    } catch (e) { /* seed stays */ }
  }

  initSeedData() {
    const now = Date.now();
    return [
      { id: 'wtx-1', ts: now - 3 * 60000, asset: 'BTC', amount: 3450, usd: 228500000, from: 'Binance (Hot Wallet)', to: 'Cold Storage (0x1f9...c4)', type: 'outflow', tag: '🚨 Ultra Large', hash: '0x7e8...b12' },
      { id: 'wtx-2', ts: now - 9 * 60000, asset: 'USDT', amount: 150000000, usd: 150000000, from: 'Tether Treasury', to: 'Binance', type: 'mint', tag: '🚨 Ultra Large', hash: '0x4a1...99f' },
      { id: 'wtx-3', ts: now - 16 * 60000, asset: 'ETH', amount: 38200, usd: 134800000, from: 'Unknown Whale (0x8b3...de)', to: 'Lido Staking Contract', type: 'outflow', tag: '🚨 Ultra Large', hash: '0x99c...32a' },
      { id: 'wtx-4', ts: now - 24 * 60000, asset: 'BTC', amount: 1200, usd: 79440000, from: 'Kraken', to: 'Institutional Custody (Fidelity)', type: 'outflow', tag: 'انباشت نهادی', hash: '0x12c...4df' },
      { id: 'wtx-5', ts: now - 35 * 60000, asset: 'BTC', amount: 890, usd: 58910000, from: 'Unknown Whale (0x334...a1)', to: 'Coinbase Pro', type: 'inflow', tag: 'فشار فروش', hash: '0xbb2...5e8' },
      { id: 'wtx-6', ts: now - 48 * 60000, asset: 'SOL', amount: 350000, usd: 52500000, from: 'Solana Foundation', to: 'Unknown Staking Validator', type: 'outflow', tag: 'انباشت / استیکینگ', hash: '5xY9...p1q' },
      { id: 'wtx-7', ts: now - 62 * 60000, asset: 'USDC', amount: 85000000, usd: 85000000, from: 'Circle Reserve', to: 'Coinbase Prime', type: 'mint', tag: 'تزریق نقدینگی', hash: '0x6e2...18b' },
      { id: 'wtx-8', ts: now - 80 * 60000, asset: 'ETH', amount: 22000, usd: 77660000, from: 'Bitfinex', to: 'Arbitrum Bridge', type: 'outflow', tag: 'انتقال به L2', hash: '0x22f...81c' },
      { id: 'wtx-9', ts: now - 105 * 60000, asset: 'BTC', amount: 650, usd: 43030000, from: 'Foundry USA Pool', to: 'Binance Deposit', type: 'inflow', tag: 'فشار فروش ماینر', hash: '0x33a...ff2' },
      { id: 'wtx-10', ts: now - 122 * 60000, asset: 'USDT', amount: 70000000, usd: 70000000, from: 'Tether Treasury', to: 'OKX', type: 'mint', tag: 'تزریق نقدینگی', hash: '0x55d...01e' },
      { id: 'wtx-11', ts: now - 150 * 60000, asset: 'SOL', amount: 180000, usd: 27000000, from: 'Binance', to: 'Whale Vault (0x77a...99)', type: 'outflow', tag: 'انباشت', hash: '4uK8...88j' },
      { id: 'wtx-12', ts: now - 175 * 60000, asset: 'ETH', amount: 15400, usd: 54360000, from: 'OKX', to: 'Unknown Wallet (0xcc1...44)', type: 'outflow', tag: 'انباشت', hash: '0xaa7...04b' },
      { id: 'wtx-13', ts: now - 210 * 60000, asset: 'BTC', amount: 520, usd: 34420000, from: 'Unknown Whale', to: 'Bybit', type: 'inflow', tag: 'ورود به صرافی', hash: '0x00f...e2a' },
      { id: 'wtx-14', ts: now - 250 * 60000, asset: 'USDC', amount: 65000000, usd: 65000000, from: 'Circle Treasury', to: 'Kraken', type: 'mint', tag: 'تزریق نقدینگی', hash: '0x44c...91b' },
      { id: 'wtx-15', ts: now - 290 * 60000, asset: 'BTC', amount: 1850, usd: 122470000, from: 'Coinbase Custody', to: 'BlackRock iShares (IBIT)', type: 'outflow', tag: '🚨 Ultra Large', hash: '0x99a...67c' }
    ];
  }

  setFilter(type, val) {
    if (type === 'asset') this.filterAsset = val;
    if (type === 'flow') this.filterFlow = val;

    const tb = document.getElementById('whaleTB');
    if (tb) {
      if (type === 'asset') {
        tb.querySelectorAll('[data-asset]').forEach(b => {
          b.classList.toggle('active', b.getAttribute('data-asset') === val);
        });
      }
      if (type === 'flow') {
        tb.querySelectorAll('[data-flow]').forEach(b => {
          b.classList.toggle('active', b.getAttribute('data-flow') === val);
        });
      }
    }
    this.render();
  }

  generateTick() {
    const assets = ['BTC', 'ETH', 'SOL', 'USDT', 'USDC'];
    const asset = assets[Math.floor(Math.random() * assets.length)];
    const isStable = (asset === 'USDT' || asset === 'USDC');
    const flowTypes = isStable ? ['mint', 'outflow'] : ['outflow', 'inflow', 'outflow'];
    const type = flowTypes[Math.floor(Math.random() * flowTypes.length)];

    let usd, amount;
    if (asset === 'BTC') {
      amount = Math.round(300 + Math.random() * 2500);
      usd = amount * 66500;
    } else if (asset === 'ETH') {
      amount = Math.round(5000 + Math.random() * 35000);
      usd = amount * 3500;
    } else if (asset === 'SOL') {
      amount = Math.round(80000 + Math.random() * 400000);
      usd = amount * 150;
    } else {
      usd = Math.round((20 + Math.random() * 120) * 1000000);
      amount = usd;
    }

    const exch = ['Binance', 'Coinbase Prime', 'Kraken', 'OKX', 'Bybit'][Math.floor(Math.random() * 5)];
    let from, to, tag;
    if (type === 'outflow') {
      from = exch;
      to = 'کیف پول ناشناس (0x' + Math.random().toString(16).substr(2, 6) + '...)';
      tag = 'انباشت نهادی';
    } else if (type === 'inflow') {
      from = 'نهنگ ناشناس (0x' + Math.random().toString(16).substr(2, 6) + '...)';
      to = exch;
      tag = 'فشار فروش';
    } else {
      from = (asset === 'USDT' ? 'Tether Treasury' : 'Circle Reserve');
      to = exch;
      tag = 'تزریق نقدینگی';
    }

    if (usd >= 100000000) {
      tag = '🚨 Ultra Large';
    }

    const newTx = {
      id: 'wtx-' + Date.now(),
      ts: Date.now(),
      asset,
      amount,
      usd,
      from,
      to,
      type,
      tag,
      hash: '0x' + Math.random().toString(16).substr(2, 8) + '...'
    };

    this.txs.unshift(newTx);
    if (this.txs.length > 60) this.txs.pop();

    this.render();
  }

  render() {
    const list = this.txs.filter(tx => {
      if (this.filterAsset !== 'ALL') {
        if (this.filterAsset === 'STABLE') {
          if (tx.asset !== 'USDT' && tx.asset !== 'USDC') return false;
        } else if (tx.asset !== this.filterAsset) {
          return false;
        }
      }
      if (this.filterFlow !== 'ALL' && tx.type !== this.filterFlow) return false;
      return true;
    });

    if (!this.txs || !this.txs.length) {
      this.txs = this.initSeedData();
    }

    // Calculate 24h Netflows
    let btcNet = 0, ethNet = 0, stableMint = 0;
    this.txs.forEach(tx => {
      if (tx.asset === 'BTC') {
        if (tx.type === 'outflow') btcNet -= tx.usd;
        else if (tx.type === 'inflow') btcNet += tx.usd;
      } else if (tx.asset === 'ETH') {
        if (tx.type === 'outflow') ethNet -= tx.usd;
        else if (tx.type === 'inflow') ethNet += tx.usd;
      } else if (tx.asset === 'USDT' || tx.asset === 'USDC') {
        if (tx.type === 'mint') stableMint += tx.usd;
      }
    });

    const btcEl = document.getElementById('wkpiBtc');
    if (btcEl) {
      const btcM = (Math.abs(btcNet) / 1e6).toFixed(1);
      btcEl.textContent = (btcNet < 0 ? `-$${btcM}M (خروج / انباشت صرافی)` : `+$${btcM}M (ورود به صرافی)`);
      btcEl.className = 'whale-kpi-val ' + (btcNet <= 0 ? 'pos' : 'neg');
    }
    const ethEl = document.getElementById('wkpiEth');
    if (ethEl) {
      const ethM = (Math.abs(ethNet) / 1e6).toFixed(1);
      ethEl.textContent = (ethNet < 0 ? `-$${ethM}M (خروج / استیکینگ)` : `+$${ethM}M (ورود به صرافی)`);
      ethEl.className = 'whale-kpi-val ' + (ethNet <= 0 ? 'pos' : 'neg');
    }
    const stEl = document.getElementById('wkpiStable');
    if (stEl) {
      const stM = (stableMint / 1e6).toFixed(1);
      stEl.textContent = `+$${stM}M (مینت خالص)`;
    }

    // Update counts
    const cntEl = document.getElementById('whaleCount');
    if (cntEl) {
      cntEl.textContent = 'نمایش ' + (typeof toFa === 'function' ? toFa(list.length) : list.length) +
        ' از ' + (typeof toFa === 'function' ? toFa(this.txs.length) : this.txs.length) + ' جابه‌جایی سنگین';
    }
    const sideCnt = document.getElementById('cntWhales');
    if (sideCnt) {
      sideCnt.textContent = (typeof toFa === 'function' ? toFa(this.txs.length) : this.txs.length);
      sideCnt.style.display = 'inline-block';
    }

    // Render Table Body
    const tbody = document.getElementById('whaleTableBody');
    if (tbody) {
      if (!list.length) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--ink-4)">تراکنشی با این فیلتر یافت نشد.</td></tr>';
      } else {
        tbody.innerHTML = list.map(tx => {
          const agoMin = Math.max(1, Math.round((Date.now() - tx.ts) / 60000));
          const timeStr = typeof toFa === 'function' ? (toFa(agoMin) + ' دقیقه پیش') : (agoMin + 'm ago');
          const usdStr = '$' + (tx.usd >= 1e9 ? (tx.usd / 1e9).toFixed(2) + 'B' : (tx.usd / 1e6).toFixed(1) + 'M');
          const amtStr = (typeof toFa === 'function' ? toFa(tx.amount.toLocaleString()) : tx.amount.toLocaleString()) + ' ' + tx.asset;

          let tagCls = 'wtag-accum';
          if (tx.tag.includes('Ultra')) tagCls = 'wtag-ultra';
          else if (tx.type === 'inflow') tagCls = 'wtag-inflow';
          else if (tx.type === 'mint') tagCls = 'wtag-mint';

          return `<tr>
            <td style="color:var(--ink-3);font-size:var(--t-xs);white-space:nowrap">${timeStr}</td>
            <td><strong style="color:var(--cu-txt);font-weight:700">${tx.asset}</strong></td>
            <td><span class="wtag-flow" style="color:var(--ink-1);font-weight:700">${usdStr}</span></td>
            <td style="font-variant-numeric:tabular-nums;color:var(--ink-2)">${amtStr}</td>
            <td style="direction:ltr;text-align:start;font-size:var(--t-xs);color:var(--ink-2)">
              <span style="color:var(--ink-1)">${tx.from}</span>
              <span style="color:var(--cu);margin:0 4px">➔</span>
              <span style="color:var(--ink-1)">${tx.to}</span>
            </td>
            <td><span class="wtag ${tagCls}">${tx.tag}</span></td>
            <td><code style="font-size:10px;color:var(--ink-4);direction:ltr;display:inline-block">${tx.hash}</code></td>
          </tr>`;
        }).join('');
      }
    }

  }
}

// Instantiate singletons and hook into window
window.whaleTracker = new WhaleTracker();

// Clock tick for whale tracking (every 35 seconds)
if (typeof Clock !== 'undefined' && Clock.every) {
  Clock.every(35000, () => {
    if (window.whaleTracker) window.whaleTracker.generateTick();
  }, { label: 'whale-tick-35s' });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    if (window.whaleTracker) window.whaleTracker.render();
  });
} else {
  if (window.whaleTracker) window.whaleTracker.render();
}
</script>
<script>
/* ═══════════════════════════════════════════════════════════════════════════
   PWA BRIDGE — the page half of the offline-first layer
   ═══════════════════════════════════════════════════════════════════════════
   The dashboard keeps its state in memory (DATA / ECON) and, until now, only
   localStorage — 5 MB, synchronous, and on this profile already carrying the
   bookmarks of a year of terminals. This block moves the cache to IndexedDB
   (`MohmdNewsDB`, see web/storage_engine.js) and does four things:

     1. captures every JSON answer the page receives (articles, reports,
        calendar, article bodies) into the database, cloned off the response so
        the render path is never blocked or slowed;
     2. serves a feed and an article body back from the cache when the network
        is gone — the swap happens inside the existing renderers, so nothing
        downstream had to change;
     3. mirrors the starred list into a `bookmarks` store with full snapshots,
        and restores it when localStorage is empty;
     4. answers the feed search box from the full-text index when the live
        filter finds nothing — 2 000 cached articles are searched by posting
        list, not by walking the DOM.

   Everything here is additive: if IndexedDB, the worker or the engine is
   missing, the dashboard behaves exactly as it did before and the telemetry
   capsule simply says so.
   ═══════════════════════════════════════════════════════════════════════════ */
(function(){
'use strict';

/* the maquette is a self-contained demo file: it must not register a worker or
   write into a database that would then leak into the next design review */
if(window.__MAQUETTE__){
  /* say so in the same capsule rather than leaving a dash hanging there */
  const item=document.getElementById('pwaItem'), txt=document.getElementById('pwaTxt'), dot=document.getElementById('pwaDot');
  if(txt) txt.textContent='Cache off (demo)';
  if(item){ item.setAttribute('data-mode','warn'); item.title='ماکت تک‌فایل: بدون سرور، بدون حافظهٔ آفلاین'; }
  if(dot) dot.className='pwa-dot is-idle';
  return;
}

const PWA_LABEL={boot:'Starting…', online:'Online (Synced)', syncing:'Syncing…',
                 offline:'Offline (Cache Mode)', error:'Storage Off'};
const PWA_STATE={mode:'boot', counts:null, sw:null, pruned:false, last:null};
const CACHE_PATHS=[['/api/data','data'],['/api/report/','report'],
                   ['/api/econ','econ'],['/api/article/','article']];

let SE_ENGINE=null, SE_OPEN=null, SEARCH_TOKEN=0;

function el(id){ return document.getElementById(id); }
function fa(n){ try{ return toFa(n); }catch(e){ return String(n); } }
function supported(){ return typeof indexedDB!=='undefined' && typeof window.StorageEngine==='function'; }

/* one engine per page; open() is idempotent, and a failure is remembered as
   "no cache" rather than retried on every call */
function engine(){
  if(SE_ENGINE) return SE_ENGINE;
  if(!supported()) return null;
  try{ SE_ENGINE=new StorageEngine(); }catch(e){ SE_ENGINE=null; }
  return SE_ENGINE;
}
function ready(){
  const eng=engine();
  if(!eng) return Promise.resolve(null);
  if(!SE_OPEN) SE_OPEN=eng.open().then(function(){ return eng; }).catch(function(e){
    console.warn('MohmdNewsDB unavailable:', e); return null;
  });
  return SE_OPEN;
}

/* ── status indicator ──────────────────────────────────────────────────── */
function status(mode, note){
  PWA_STATE.mode=mode;
  const item=el('pwaItem'), txt=el('pwaTxt'), dot=el('pwaDot');
  if(txt) txt.textContent=PWA_LABEL[mode]||mode;
  if(item){ item.setAttribute('data-mode', mode); item.title=tooltip(note); }
  if(dot) dot.className='pwa-dot '+(mode==='online'?'is-on':(mode==='offline'?'is-off':'is-idle'));
}
function tooltip(note){
  if(note) return note;
  const c=PWA_STATE.counts;
  const head = PWA_STATE.mode==='offline' ? 'حالت آفلاین: فید، گزارش‌ها و تقویم از حافظهٔ محلی خوانده می‌شوند'
            : PWA_STATE.mode==='error'  ? 'ذخیره‌سازی آفلاین در این مرورگر فعال نشد (فید کار می‌کند)'
            : 'همگام با سرور · ذخیره‌سازی آفلاین فعال';
  if(!c) return head;
  return head+' · '+fa(c.articles)+' خبر، '+fa(c.reports)+' گزارش، '+fa(c.calendar)+' رویداد، '
         +fa(c.terms)+' ترم نمایه‌سازی';
}
function refreshCounts(eng){
  const e=eng||engine();
  if(!e) return;
  e.stats().then(function(s){
    PWA_STATE.counts=s;
    const item=el('pwaItem'); if(item) item.title=tooltip();
  }).catch(function(){});
}

/* ── capture every JSON answer into the database ───────────────────────── */
function kindOf(url){
  if(typeof url!=='string' || url.charAt(0)!=='/') return null;
  for(let i=0;i<CACHE_PATHS.length;i++)
    if(url.indexOf(CACHE_PATHS[i][0])===0) return CACHE_PATHS[i][1];
  return null;
}
/* `/api/report/BTC?lang=fa` → "BTC", `/api/article/ab12` → "ab12". The index
   here was the bug that made every report land under the literal key
   "report" — invisible in the UI, which is exactly why it needed the browser
   check rather than a unit test. */
function pathArg(url){ return String(url).split('?')[0].split('/')[3] || ''; }
/* the calendar endpoint returns a WEEK OBJECT ({events, source, range}), not a
   list — concat'ing it directly threw and the cache silently stayed empty */
function calEvents(cal){
  if(!cal) return [];
  if(Array.isArray(cal)) return cal;
  return Array.isArray(cal.events)?cal.events:[];
}
function capture(kind, url, res){
  /* off the critical path on purpose: the caller already has its response */
  Promise.resolve().then(function(){
    return ready().then(function(eng){
      if(!eng || !res) return null;
      return res.json().then(function(json){ return {eng:eng, json:json}; });
    });
  }).then(function(ctx){
    if(!ctx) return null;
    const eng=ctx.eng, json=ctx.json;
    if(kind==='data'){
      const list=(json.articles||[]).concat(json.archive||[]);
      if(!list.length) return null;
      return eng.putArticles(list).then(function(){
        /* the small payload fields are stored so an offline boot gets the same
           toolbar, chips and asset names as a live one. Market prices are
           deliberately NOT kept here: stale quotes dressed as live ones are
           worse than no quotes — the worker's own /api/data cache covers the
           "show me the last snapshot" case, under the cache-mode indicator. */
        return eng.putMeta('data_meta', {
          ts: Date.now(),
          kind_labels: json.kind_labels || {}, kind_counts: json.kind_counts || {},
          topic_counts: json.topic_counts || {}, asset_counts: json.asset_counts || {},
          topics_meta: json.topics_meta || {}, assets_meta: json.assets_meta || {},
          config: json.config || null, rules: json.rules || null, stats: json.stats || null,
          server_time_fa: json.server_time_fa || '', interval_fa: json.interval_fa || ''
        });
      }).then(function(){
        /* bounded cache, one prune per page load — the retention window and the
           profile cap both live in the engine */
        if(PWA_STATE.pruned) return null;
        PWA_STATE.pruned=true;
        return eng.prune();
      }).then(function(){ refreshCounts(eng); });
    }
    if(kind==='report') return eng.putReport(pathArg(url), json).then(function(){ refreshCounts(eng); });
    if(kind==='econ'){
      const ev=calEvents(json.calendar).concat(calEvents(json.calendar_next));
      return Promise.resolve(ev.length?eng.putCalendar(ev):null)
        .then(function(){ return eng.putMeta('econ', {ts:Date.now(), data:json}); })
        .then(function(){ refreshCounts(eng); });
    }
    if(kind==='article') return eng.putMeta('body:'+pathArg(url), {ts:Date.now(), data:json});
    return null;
  }).catch(function(e){ /* a cache write may never break a request */ });
}

/* Wraps the global fetch. Installed while the document is still parsing, so the
   very first /api/data of the session is already captured. */
function wireFetch(){
  if(window.__pwaFetchWired || typeof window.fetch!=='function') return;
  window.__pwaFetchWired=true;
  const orig=window.fetch.bind(window);
  window.fetch=function(input, init){
    const url=(typeof input==='string')?input:((input&&input.url)||'');
    const method=String((init&&init.method)||(input&&input.method)||'GET').toUpperCase();
    const kind=kindOf(url);
    return orig(input, init).then(function(res){
      /* a worker-served answer is a cache answer: `X-MOHMD-Cache: hit` is set
         by sw.js, and treating it as a fresh sync would be the one lie this
         indicator must not tell */
      let mark='', fromCache=false;
      try{
        mark=res&&res.headers?String(res.headers.get('X-MOHMD-Cache')||''):'';
        fromCache=mark==='hit';
      }catch(e){}
      if(kind && method==='GET' && mark==='miss'){
        /* a worker that answered "I have nothing" is a failed request as far as
           the cache layer is concerned — but if it ever returns a response
           instead of failing, serve the local copy now */
        return fallback(kind, url).then(function(res2){ return res2||res; });
      }
      if(kind || url.indexOf('/api/')===0){
        PWA_STATE.last={ts:Date.now(), ok:!!(res&&res.ok)&&!fromCache, cache:fromCache, url:url};
        /* the payload request is remembered separately: by the time loadData()
           resolves, renderAll() has fired its own requests and the single
           "last request" slot would belong to one of those instead — which is
           how the offline boot ended up re-rendering instead of just saying
           that the data it already has is old */
        if(kind==='data') PWA_STATE.lastData=PWA_STATE.last;
      }
      if(fromCache) status('offline');
      if(kind && method==='GET' && res && res.ok){
        try{ capture(kind, url, res.clone()); }catch(e){}
      }
      return res;
    }, function(err){
      PWA_STATE.last={ts:Date.now(), ok:false, url:url};
      if(kind) return fallback(kind, url).then(function(res){ if(res) return res; throw err; });
      throw err;
    });
  };
}

/* Serve a request the network could not: the worker covers the whole-payload
   case, this covers the exact shapes the UI asks for by symbol / by id. */
function jres(data){
  return new Response(JSON.stringify(data), {status:200,
    headers:{'Content-Type':'application/json','X-MOHMD-Cache':'hit'}});
}
function fallback(kind, url){
  return ready().then(function(eng){
    if(!eng) return null;
    if(kind==='report') return eng.getReport(pathArg(url)).then(function(d){ return d?jres(d):null; });
    if(kind==='econ') return eng.getMeta('econ').then(function(m){
      if(m&&m.data) return jres(m.data);
      /* without the snapshot, rebuild the shape the renderer expects: it reads
         ECON.calendar.events, not a bare list */
      return eng.getCalendar().then(function(ev){
        return (ev&&ev.length)?jres({calendar:{events:ev, source:'local cache'}, offline:true}):null;
      });
    });
    if(kind==='article'){
      return eng.getMeta('body:'+pathArg(url)).then(function(m){ return (m&&m.data)?jres(m.data):null; });
    }
    return null;                       /* /api/data is rebuilt by hydrate() */
  }).then(function(res){ if(res) status('offline'); return res; })
    .catch(function(){ return null; });
}

/* ── offline boot: rebuild the feed from the cache ─────────────────────── */
function hydrate(){
  return ready().then(function(eng){
    if(!eng) return false;
    return Promise.all([eng.getArticles({limit:400}), eng.getMeta('data_meta')]).then(function(pair){
      const rows=pair[0], meta=pair[1];
      if(!rows.length) return false;
      if(!DATA) DATA={};
      DATA.articles=rows;
      DATA.archive=DATA.archive||[];
      DATA.offline=true;
      if(meta){
        /* the live payload's small fields, as captured with the last sync */
        DATA.kind_labels=DATA.kind_labels||meta.kind_labels||{};
        DATA.kind_counts=meta.kind_counts||{};
        DATA.topic_counts=meta.topic_counts||{};
        DATA.asset_counts=meta.asset_counts||{};
        DATA.topics_meta=DATA.topics_meta||meta.topics_meta||{};
        DATA.assets_meta=meta.assets_meta||{};
        DATA.config=DATA.config||meta.config;
        DATA.rules=meta.rules||null;
        DATA.stats=DATA.stats||meta.stats||null;
      }
      try{ if(typeof initMeta==='function') initMeta(); }catch(e){}
      if(DATA.stats) DATA.stats.cycle_running=false;
      /* renderAll() expects the whole payload (market, sources, macro…); the
         offline path re-runs only what the feed itself needs. Without this the
         source select stayed empty — and an empty select means its value is
         "", which the feed filter reads as "show only articles with no
         source": a silently blank feed (found in the browser, not in a test). */
      try{
        if(typeof renderSrcSel==='function') renderSrcSel();
        if(typeof renderKindSel==='function') renderKindSel();
        renderFeed();
      }catch(e){ console.warn('offline feed render:', e); }
      try{ toast('حالت آفلاین — فید از حافظهٔ محلی ('+fa(rows.length)+' خبر)'); }catch(e){}
      refreshCounts(eng);
      return true;
    });
  }).catch(function(){ return false; });
}

/* ── the search box falls back to the full-text index ──────────────────────
   The live filter only ever sees the current window. When it comes up empty
   and the query is a real word, the index is consulted instead: 2 000 cached
   articles ranked by posting lists, not by re-scanning the rendered cards. */
function cacheSearch(q){
  return ready().then(function(eng){
    if(!eng) return null;
    const token=++SEARCH_TOKEN;
    return eng.search(q, {limit:60}).then(function(res){
      if(!res || token!==SEARCH_TOKEN) return null;
      const box=el('q');
      if(!box || (box.value||'').trim()!==q) return null;   /* query moved on */
      const grid=el('newsGrid');
      /* "the live filter found nothing" is read from the feed itself, not from
         an empty child list: a virtualised grid always has its spacer and its
         layer in it, and asking the DOM whether it is empty would have made
         this fallback fire on a perfectly good feed */
      const blank=el('feedEmpty');
      const feedEmpty=(blank&&blank.style.display!=='none')||
                      (VS.feed?VS.feed.items.length===0:false);
      if(!grid || !feedEmpty || !res.articles.length) return null;
      vsGrid('feed','newsGrid',VS_OPTS_FEED, res.articles, res.articles.map(cardHTML).join(''));
      const cnt=el('feedCount');
      if(cnt) cnt.textContent=fa(res.articles.length)+' خبر · از حافظهٔ محلی ('+fa(res.took)+'ms)';
      const empty=el('feedEmpty');
      if(empty){ empty.style.display='block';
        empty.textContent='در فید زنده نبود — این نتایج از نمایهٔ محلی ('+fa(PWA_STATE.counts?PWA_STATE.counts.articles:0)+' خبر) خوانده شد'; }
      return res;
    });
  }).catch(function(){ return null; });
}

/* ── alert notifications through the worker when it is available ──────────
   A notification raised by the page dies with the tab; one raised by the
   registration survives a focus change, shows the icon, and is tappable. */
function wirePush(){
  if(window.__pwaPushWired || typeof window.arPush!=='function') return;
  window.__pwaPushWired=true;
  const orig=window.arPush;
  window.arPush=function(name, body){
    try{
      const reg=PWA_STATE.sw;
      if(reg && reg.showNotification && typeof Notification!=='undefined' && Notification.permission==='granted'){
        reg.showNotification(String(name||'MOHMD NEWS'), {body:String(body||''), tag:'mohmd-alert',
          lang:'fa', dir:'rtl', icon:'/icons/icon-192.png', badge:'/icons/icon-192.png', data:{url:'/'}});
        return true;
      }
    }catch(e){ /* fall through to the in-page path */ }
    return orig.apply(this, arguments);
  };
}

/* ── bookmarks: snapshots in the database, ids in localStorage ─────────── */
function mirrorBookmarks(){
  return ready().then(function(eng){
    if(!eng) return null;
    return eng.syncBookmarks(getBookmarks(), getBmarkMeta());
  }).catch(function(){ return null; });
}
function restoreBookmarks(){
  return ready().then(function(eng){
    if(!eng) return null;
    if(getBookmarks().length) return mirrorBookmarks();
    return eng.listBookmarks().then(function(rows){
      if(!rows.length) return null;
      const ids=[], meta={};
      rows.forEach(function(r){ ids.push(r.id); meta[r.id]=r; });
      try{ localStorage.setItem(BM_KEY, JSON.stringify(ids)); }catch(e){}
      try{ localStorage.setItem(BM_META_KEY, JSON.stringify(meta)); }catch(e){}
      try{ renderChips(); renderFeed(); renderBookmarks(); }catch(e){}
      return ids.length;
    });
  }).catch(function(){ return null; });
}

/* ── service worker ────────────────────────────────────────────────────── */
function registerWorker(){
  if(!('serviceWorker' in navigator)) return;
  if(location.protocol!=='http:' && location.protocol!=='https:') return;
  navigator.serviceWorker.register('/sw.js', {scope:'/'}).then(function(reg){
    PWA_STATE.sw=reg;
    const take=function(){
      if(reg.waiting && navigator.serviceWorker.controller){
        reg.waiting.postMessage({type:'SKIP_WAITING'});
        try{ toast('نسخهٔ جدید داشبورد فعال شد'); }catch(e){}
      }
    };
    take();
    if(reg.addEventListener) reg.addEventListener('updatefound', take);
    try{ navigator.serviceWorker.addEventListener('controllerchange', take); }catch(e){}
  }).catch(function(e){ console.warn('service worker:', e); });
  navigator.serviceWorker.addEventListener('message', function(ev){
    const d=ev.data||{};
    if(d.type==='SW_OFFLINE_TICK'){ status('offline'); markStaleCycle(); }
    if(d.type==='PONG'){
      /* the worker answers whether it has been serving from its caches; a
         response that arrived before this listener existed is covered here */
      if(d.lastCacheHit){ status('offline'); markStaleCycle(); }
      if(d.failures&&d.failures.length) console.warn('shell precache failures:', d.failures);
    }
    if(d.type==='SW_SHELL_PRIMED'){
      if(d.failures&&d.failures.length) console.warn('shell precache failures:', d.failures);
      else console.info('offline shell rebuilt (worker '+d.version+')');
    }
    if(d.type==='SW_SHELL_OK') console.info('offline shell present (worker '+d.version+')');
  });
}

/* ── boot ──────────────────────────────────────────────────────────────── */
function wireApp(){
  if(typeof window.loadData==='function' && !window.__pwaLoadWired){
    window.__pwaLoadWired=true;
    const orig=window.loadData;
    window.loadData=function(){
      return Promise.resolve(orig.apply(this, arguments)).then(function(r){
        const last=PWA_STATE.lastData||PWA_STATE.last;
        if(last && last.ok===false && !last.cache){
          return hydrate().then(function(hit){
            /* the feed is now local: say that where the cycle status lives */
            const ct2=el('cycleTxt'); if(ct2&&hit) ct2.textContent='حالت آفلاین — فید از حافظهٔ محلی';
            const cd2=el('cycleDot'); if(cd2&&hit) cd2.className='dot err';
            status(hit?'offline':'error', hit?null:'اتصال به سرور نیست و حافظهٔ محلی هم خالی است');
            return r;
          });
        }
        if(last && last.cache){
          /* the payload is real but old: say so where the cycle status is
             shown, or the cached "cycle running" text reads as live */
          const ct=el('cycleTxt');
          if(ct) ct.textContent='حالت آفلاین — داده ذخیرهشدهٔ آخر';
          const cd=el('cycleDot');
          if(cd){ cd.className='dot err'; cd.title='اتصال به سرور نیست — این داده ذخیره‌شدهٔ آخرین همگام‌سازی است'; }
          status('offline');
        } else {
          status(navigator.onLine?'online':'offline');
        }
        return r;
      });
    };
  }
  if(typeof window.toggleBookmark==='function' && !window.__pwaBmWired){
    window.__pwaBmWired=true;
    const orig=window.toggleBookmark;
    window.toggleBookmark=function(){ const r=orig.apply(this, arguments); mirrorBookmarks(); return r; };
    if(typeof window.clearBookmarks==='function'){
      const oc=window.clearBookmarks;
      window.clearBookmarks=function(){ const r=oc.apply(this, arguments); mirrorBookmarks(); return r; };
    }
  }
  if(typeof window.renderFeed==='function' && !window.__pwaFeedWired){
    window.__pwaFeedWired=true;
    const orig=window.renderFeed;
    window.renderFeed=function(){
      const r=orig.apply(this, arguments);
      try{
        const box=el('q');
        const q=box?String(box.value||'').trim():'';
        const grid=el('newsGrid');
        if(q.length>=2 && grid && !grid.children.length) cacheSearch(q);
      }catch(e){}
      return r;
    };
  }
  wirePush();
}

/* If the offline shell is missing (evicted, or cleared by another worker on
   this origin) the worker is asked to rebuild it while the server is up — the
   page is the only party that knows whether it is online. */
function ensureShell(){
  if(!('serviceWorker' in navigator) || !('caches' in window)) return;
  /* the worker owns the cache name — the page only asks it to check */
  const ask=function(w){ if(w&&w.postMessage) w.postMessage({type:'ENSURE_SHELL'}); };
  ask(navigator.serviceWorker.controller);
  if(navigator.serviceWorker.ready){
    navigator.serviceWorker.ready.then(function(reg){ ask(reg.active); }).catch(function(){});
  }
}

/* "the numbers on screen are real but old" — said where the cycle status is,
   because a cached payload still carries the last live cycle line */
function markStaleCycle(txt){
  try{
    const t=el('cycleTxt');
    if(t) t.textContent=txt||'حالت آفلاین — داده ذخیره‌شدهٔ آخر';
    const d=el('cycleDot');
    if(d){ d.className='dot err'; d.title='اتصال به سرور نیست — این دادهٔ آخرین همگام‌سازی است'; }
  }catch(e){}
}
function pingWorker(){
  const ctrl=navigator.serviceWorker&&navigator.serviceWorker.controller;
  if(ctrl&&ctrl.postMessage) ctrl.postMessage({type:'PING'});
}

function boot(){
  if(!supported()){ status('error', 'این مرورگر IndexedDB ندارد — فید بدون حافظهٔ آفلاین کار می‌کند');
    const item=el('pwaItem'); if(item) item.setAttribute('data-off','1'); return; }
  ensureShell();
  ready().then(function(eng){
    if(!eng){ status('error'); return; }
    status(navigator.onLine?'online':'offline');
    restoreBookmarks();
    refreshCounts(eng);
  });
  registerWorker();
  pingWorker();
  try{ if(navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(function(){}); }catch(e){}
  window.addEventListener('online', function(){ status('syncing'); });
  window.addEventListener('offline', function(){ status('offline'); });
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', wireApp);
  else wireApp();
}

/* fetch capture is installed synchronously (the first poll may already be in
   flight); everything that patches the dashboard's own functions waits for the
   script blocks above to have defined them */
wireFetch();
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', boot);
else boot();

/* a small read-only surface for the console, the tests and future views */
window.MohmdCache={
  engine:engine, open:ready, status:function(){ return PWA_STATE; },
  search:function(q, opts){ return ready().then(function(e){ return e?e.search(q, opts||{}):null; }); },
  stats:function(){ return ready().then(function(e){ return e?e.stats():null; }); },
  articles:function(opts){ return ready().then(function(e){ return e?e.getArticles(opts||{}):[]; }); },
  report:function(sym){ return ready().then(function(e){ return e?e.getReport(sym):null; }); },
  calendar:function(opts){ return ready().then(function(e){ return e?e.getCalendar(opts||{}):[]; }); },
  bookmarks:function(){ return ready().then(function(e){ return e?e.listBookmarks():[]; }); },
  prune:function(opts){ return ready().then(function(e){ return e?e.prune(opts||{}):0; }); },
  clear:function(store){ return ready().then(function(e){ return e?e.clear(store):[]; }); }
};
})();

/* Service worker: registerWorker() above is the only registration. A second
   one for '/static/sw.js' used to live here — that path is now a tombstone that
   unregisters itself, and registering it again on every load was pure noise. */
</script>

<script>



/* ═══════════════════════════════════════════════════════════════════════════
   FREEBUFF EXPANSION SUITE CONTROLLERS
   1. FreebuffWatchlist (واچ‌لیست اختصاصی دارایی‌ها)
   2. FreebuffBookmarks (پشتیبان‌گیری و بازیابی نشان‌شده‌ها)
   3. FreebuffOffline (مدیریت اتصال و وضعیت آفلاین)
   ═══════════════════════════════════════════════════════════════════════════ */


// ── 2. Watchlist Manager ───────────────────────────────────────────────────
const FreebuffWatchlist = (function(){
  const STORAGE_KEY = 'freebuff_watchlist';
  const DEFAULT_SYMS = ['BTC', 'ETH', 'SOL', 'XAU', 'WTI', 'EUR', 'DXY'];

  function get(){
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : DEFAULT_SYMS;
    } catch(e){
      return DEFAULT_SYMS;
    }
  }

  function set(list){
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
      if(typeof renderChips==='function') renderChips();
      if(typeof renderFeed==='function') renderFeed();
    } catch(e){}
  }

  function toggle(sym){
    let cur = get();
    if(cur.includes(sym)){
      cur = cur.filter(s => s !== sym);
    } else {
      cur.push(sym);
    }
    set(cur);
    renderGrid();
  }

  function selectAll(val){
    if(val && typeof orderedAssets==='function'){
      set(orderedAssets());
    } else {
      set([]);
    }
    renderGrid();
  }

  function openModal(){
    renderGrid();
    const ov = document.getElementById('watchlistOverlay');
    if(ov) ov.classList.add('open');
  }

  function renderGrid(){
    const grid = document.getElementById('watchlistGrid');
    if(!grid || typeof orderedAssets!=='function') return;
    const cur = get();
    const assets = orderedAssets();
    grid.innerHTML = assets.map(s => {
      const active = cur.includes(s);
      const name = typeof faAssetName==='function' ? faAssetName(s) : s;
      return `<div class="watchlist-card ${active?'active':''}" onclick="FreebuffWatchlist.toggle('${s}')">
        <span>${typeof assetIc==='function'?assetIc(s):'🪙'} <b>${esc(name)}</b></span>
        <span>${active ? '✅' : '⚪'}</span>
      </div>`;
    }).join('');
  }

  return { get, set, toggle, selectAll, openModal, renderGrid };
})();
window.FreebuffWatchlist = FreebuffWatchlist;

// ── 3. Bookmarks JSON Export/Import ─────────────────────────────────────────
const FreebuffBookmarks = (function(){
  function exportJSON(){
    const bmarks = (typeof getBookmarks==='function' ? getBookmarks() : []);
    const meta = (typeof getBmarkMeta==='function' ? getBmarkMeta() : {});
    const payload = { version: 1, exported_at: new Date().toISOString(), bookmarks: bmarks, metadata: meta };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'freebuff_bookmarks_' + new Date().toISOString().slice(0,10) + '.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    if(typeof toast==='function') toast('فایل پشتیبان نشان‌شده‌ها دانلود شد (' + toFa(bmarks.length) + ' خبر)');
  }

  function importJSON(ev){
    const file = ev.target.files && ev.target.files[0];
    if(!file) return;
    const reader = new FileReader();
    reader.onload = function(e){
      try {
        const data = JSON.parse(e.target.result);
        if(!data || !Array.isArray(data.bookmarks)) throw new Error('فایل نامعتبر است');
        const curBmarks = (typeof getBookmarks==='function' ? getBookmarks() : []);
        const curMeta = (typeof getBmarkMeta==='function' ? getBmarkMeta() : {});
        const mergedBmarks = Array.from(new Set([...curBmarks, ...data.bookmarks]));
        const mergedMeta = Object.assign({}, curMeta, data.metadata || {});
        localStorage.setItem('mohmd_bmarks', JSON.stringify(mergedBmarks));
        localStorage.setItem('mohmd_bmarks_meta', JSON.stringify(mergedMeta));
        if(typeof renderBookmarks==='function') renderBookmarks();
        if(typeof renderChips==='function') renderChips();
        if(typeof toast==='function') toast('بازیابی موفق: ' + toFa(mergedBmarks.length) + ' خبر نشان‌شده در مرورگر بارگذاری شد');
      } catch(err){
        if(typeof toast==='function') toast('خطا در خواندن فایل: ' + err.message);
      }
    };
    reader.readAsText(file);
    ev.target.value = '';
  }

  return { exportJSON, importJSON };
})();
window.FreebuffBookmarks = FreebuffBookmarks;

// ── 5. Offline Status & Sync Listener ───────────────────────────────────────
window.addEventListener('offline', function(){
  const pwaTxt = document.getElementById('pwaTxt');
  const pwaItem = document.getElementById('pwaItem');
  if(pwaTxt) pwaTxt.textContent = 'آفلاین (حافظه محلی)';
  if(pwaItem) pwaItem.classList.add('offline-pill-active');
  if(typeof toast==='function') toast('📡 ارتباط اینترنت قطع شد — داشبورد در حالت آفلاین کار می‌کند');
});

window.addEventListener('online', function(){
  const pwaTxt = document.getElementById('pwaTxt');
  const pwaItem = document.getElementById('pwaItem');
  if(pwaTxt) pwaTxt.textContent = 'همگام‌شده';
  if(pwaItem) pwaItem.classList.remove('offline-pill-active');
  if(typeof toast==='function') toast('🟢 اتصال اینترنت برقرار شد — دریافت اطلاعات تازه...');
  if(typeof loadData==='function') loadData();
});

</script>
</body>
</html>
"""
