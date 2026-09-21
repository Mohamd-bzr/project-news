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
<title>MOHMD NEWS — Market Intelligence</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800;900&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

:root {
  /* 2026 Deep Obsidian Institutional Surfaces */
  --bg: #07090E;
  --surface: #0E121A;
  --surface-2: #141A26;
  --surface-3: #1A2232;
  --surface-glass: rgba(14, 18, 26, 0.85);
  --surface-glass-hi: rgba(20, 26, 38, 0.92);
  --card: #0F141F;
  --card-hover: #161D2C;
  --sidebar-bg: #0A0D14;
  --topbar-bg: rgba(9, 12, 18, 0.88);

  /* Signature Warm Copper Metallic Palette */
  --copper: #C69A6B;
  --copper-hi: #DDB98C;
  --copper-deep: #8C6A44;
  --copper-txt: #E3C9A6;
  --copper-bg: rgba(198, 154, 107, 0.12);
  --copper-line: rgba(198, 154, 107, 0.32);
  --copper-glow: rgba(198, 154, 107, 0.28);

  /* Financial Market Indicators */
  --green: #10B981;
  --green-bg: rgba(16, 185, 129, 0.12);
  --green-line: rgba(16, 185, 129, 0.32);
  --red: #F43F5E;
  --red-bg: rgba(244, 63, 94, 0.12);
  --red-line: rgba(244, 63, 94, 0.32);
  --cyan: #38BDF8;
  --purple: #A855F7;
  --gold: var(--copper-hi);
  --amber: var(--copper-hi);
  --slate: #94A3B8;

  /* Typography */
  --text: #F8FAFC;
  --body: #CBD5E1;
  --muted: #94A3B8;
  --faint: #64748B;

  /* Geometry & Shadows */
  --border: rgba(255, 255, 255, 0.08);
  --border-focus: var(--copper);
  --line: rgba(255, 255, 255, 0.06);
  --line-soft: rgba(255, 255, 255, 0.03);
  --radius-sm: 8px;
  --radius: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --radius-pill: 9999px;
  --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3);
  --shadow-md: 0 8px 24px -4px rgba(0, 0, 0, 0.5);
  --shadow-lg: 0 16px 40px -8px rgba(0, 0, 0, 0.65);
  --shadow-glow: 0 0 25px var(--copper-glow);

  /* Layout dimensions */
  --topbar-height: 60px;
  --sidebar-width: 250px;

  /* ── 2026 CINEMATIC REFRESH TOKENS ── */
  --e-reveal: cubic-bezier(.16, 1, .3, 1);   /* long graceful settle */
  --e-soft:   cubic-bezier(.25, .8, .3, 1);  /* supporting motion */
  --stage-base: #06080C;
  --glass:      rgba(255, 255, 255, .045);
  --glass-hi:   rgba(255, 255, 255, .08);
  --glass-line: rgba(255, 255, 255, .085);
  --glass-blur: saturate(140%) blur(18px);
  --sheen:      linear-gradient(180deg, rgba(255, 255, 255, .05), rgba(255, 255, 255, .016));
  --inset-hi:   inset 0 1px 0 rgba(255, 255, 255, .07);

  /* refined ink + surfaces (overrides the values above) */
  --bg:         #06080C;
  --body:       #C8D2DE;
  --muted:      #9AA6B4;
  --faint:      #64707E;
  --topbar-height: 64px;
  --radius:     12px;
  --radius-lg:  18px;
  --radius-xl:  22px;
}

* { margin: 0; padding: 0; box-sizing: border-box; }
html, body {
  height: 100%;
  width: 100%;
  background: var(--bg);
  color: var(--text);
  font-family: 'Vazirmatn', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  overflow: hidden;
  -webkit-font-smoothing: antialiased;
}

/* Scrollbars */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.14); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--copper); }

/* Typography */
h1, h2, h3, h4, h5 { letter-spacing: -0.015em; font-weight: 800; color: var(--text); }
a { color: var(--copper); text-decoration: none; transition: color 0.15s; }
a:hover { color: var(--copper-hi); }
button, input, select, textarea { font-family: inherit; font-size: inherit; }

/* ── UNIVERSAL DARK FORM CONTROLS (NO DEFAULT BROWSER WHITE SELECTS) ── */
select, input[type="text"], input[type="password"], textarea {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 600;
  padding: 8px 12px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
}
select {
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%23C69A6B' viewBox='0 0 16 16'%3E%3Cpath d='M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: left 10px center;
  padding-left: 28px;
}
select:focus, input[type="text"]:focus, input[type="password"]:focus, textarea:focus {
  border-color: var(--copper);
  background: var(--surface-3);
  box-shadow: 0 0 0 3px rgba(198, 154, 107, 0.2);
}
select option {
  background: #0E121A;
  color: #F8FAFC;
  padding: 10px;
}

/* ── APP SHELL ARCHITECTURE ── */
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: var(--bg);
}

/* ── TOPBAR ── */
.app-topbar {
  height: var(--topbar-height);
  background: var(--topbar-bg);
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  gap: 16px;
  z-index: 100;
  flex-shrink: 0;
}
.brand-group {
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand-badge {
  width: 38px;
  height: 38px;
  border-radius: var(--radius);
  background: linear-gradient(135deg, #DDB98C 0%, #8C6A44 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 19px;
  box-shadow: 0 4px 16px var(--copper-glow);
  border: 1px solid rgba(255,255,255,0.2);
  flex-shrink: 0;
}
.brand-title-wrap {
  display: flex;
  flex-direction: column;
}
.brand-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.brand-title-row h1 {
  font-size: 16px;
  font-weight: 900;
  letter-spacing: -0.02em;
  background: linear-gradient(180deg, #FFFFFF 0%, #CBD5E1 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.brand-desc {
  font-size: 11px;
  color: var(--muted);
  font-weight: 500;
}

/* Pulse Live Pill */
.live-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  border-radius: var(--radius-pill);
  background: var(--green-bg);
  border: 1px solid var(--green-line);
  font-size: 10px;
  font-weight: 800;
  color: var(--green);
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 8px var(--green);
}
.dot.busy { background: var(--copper-hi); box-shadow: 0 0 8px var(--copper-hi); animation: pulse 1s infinite; }
.dot.err { background: var(--red); box-shadow: 0 0 8px var(--red); }
@keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.35; transform: scale(0.85); } }

/* Telemetry capsule */
.topbar-telemetry {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 6px 14px;
  border-radius: var(--radius-pill);
  font-size: 11.5px;
  color: var(--muted);
  box-shadow: var(--shadow-sm);
}
.telem-item {
  display: flex;
  align-items: center;
  gap: 5px;
}
.telem-item b {
  color: var(--text);
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.telem-divider {
  width: 1px;
  height: 12px;
  background: var(--border);
}

/* Topbar Actions */
.topbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.menu-toggle-btn {
  display: none;
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text);
  width: 38px;
  height: 38px;
  border-radius: var(--radius);
  cursor: pointer;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

/* ── APP BODY CONTAINER (Sidebar on RIGHT, Main on LEFT in RTL) ── */
.app-body {
  display: flex;
  flex-direction: row;
  flex: 1;
  height: calc(100vh - var(--topbar-height));
  width: 100vw;
  overflow: hidden;
  position: relative;
}

/* ── RIGHT NAVIGATION SIDEBAR (RTL: inline-end border is left side) ── */
.app-sidebar {
  width: var(--sidebar-width);
  background: var(--sidebar-bg);
  border-inline-end: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  height: 100%;
  overflow-y: auto;
  padding: 16px 12px 24px;
  gap: 4px;
  z-index: 90;
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.sidebar-section-label {
  font-size: 10.5px;
  font-weight: 800;
  color: var(--faint);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 12px 10px 4px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: var(--radius);
  color: var(--body);
  font-size: 13px;
  font-weight: 600;
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  text-align: right;
  width: 100%;
  transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
}
.nav-item:hover {
  background: var(--surface-2);
  color: var(--text);
  border-color: var(--border);
}
.nav-item.active {
  background: var(--copper-bg);
  color: var(--copper-txt);
  border-color: var(--copper-line);
  font-weight: 800;
  box-shadow: 0 0 16px rgba(198, 154, 107, 0.15);
}
.nav-item.active::before {
  content: "";
  position: absolute;
  inset-inline-start: 4px;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 2px;
  background: var(--copper);
}
.nav-icon {
  font-size: 16px;
  width: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.nav-text {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.nav-badge, .nav-item .cnt {
  font-size: 10.5px;
  font-weight: 800;
  background: var(--surface-3);
  border: 1px solid var(--border);
  color: var(--muted);
  padding: 1px 7px;
  border-radius: var(--radius-pill);
  font-variant-numeric: tabular-nums;
  margin-inline-start: auto;
}
.nav-item.active .cnt {
  background: rgba(198, 154, 107, 0.25);
  color: var(--copper-hi);
  border-color: var(--copper-line);
}
.sidebar-footer {
  margin-top: auto;
  padding-top: 14px;
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.sidebar-backdrop {
  display: none;
}

/* ── MAIN CONTENT AREA ── */
.app-main {
  flex: 1;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  background: var(--bg);
}

/* ── ASSETS TICKER STRIP ── */
.assets {
  display: flex;
  gap: 10px;
  padding: 12px 24px;
  background: #090C12;
  border-bottom: 1px solid var(--border);
  overflow-x: auto;
  flex-shrink: 0;
  scroll-behavior: smooth;
}
.acard {
  min-width: 190px;
  max-width: 220px;
  flex: 1 0 190px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 11px 13px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
  box-shadow: var(--shadow-sm);
}
.acard:hover {
  background: var(--card-hover);
  border-color: var(--copper);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md), 0 0 12px var(--copper-glow);
}
.acard .sym {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  font-weight: 800;
}
.acard .sym .ic { font-size: 15px; }
.acard .sym .tk { color: var(--faint); font-weight: 600; font-size: 11px; direction: ltr; margin-inline-start: auto; }
.acard .prc {
  font-size: 17.5px;
  font-weight: 900;
  margin-top: 5px;
  direction: ltr;
  text-align: right;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}
.acard .prc.flash-up { color: var(--green); text-shadow: 0 0 10px rgba(16, 185, 129, 0.4); }
.acard .prc.flash-dn { color: var(--red); text-shadow: 0 0 10px rgba(244, 63, 94, 0.4); }
.acard .chg {
  font-size: 11.5px;
  font-weight: 800;
  direction: ltr;
  text-align: right;
  margin-top: 2px;
  font-variant-numeric: tabular-nums;
}
.acard .up { color: var(--green); }
.acard .dn { color: var(--red); }
.acard svg { margin-top: 6px; width: 100%; height: 26px; display: block; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3)); }
.acard .nm { font-size: 10.5px; color: var(--muted); margin-top: 4px; font-weight: 500; }
.acard .custom { position: absolute; top: 6px; left: 8px; font-size: 9px; color: var(--purple); font-weight: 700; }
.acard .live-dot { display: inline-block; width: 5px; height: 5px; border-radius: 50%; background: var(--green); margin-left: 4px; animation: pulse 2s infinite; }

/* ── VIEW SECTIONS CONTAINER ── */
.view-container {
  flex: 1;
  padding: 24px;
}
.view { display: none; }
.view.active { display: block; animation: viewIn 0.22s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes viewIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

/* ── BUTTONS ── */
.btn {
  background: linear-gradient(135deg, #C69A6B 0%, #8C6A44 100%);
  color: #120D08;
  border: none;
  padding: 8px 18px;
  border-radius: var(--radius);
  font-size: 12.5px;
  font-weight: 800;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.18s ease;
  box-shadow: 0 2px 10px rgba(198, 154, 107, 0.3);
}
.btn:hover {
  filter: brightness(1.12);
  transform: translateY(-1px);
  box-shadow: 0 4px 18px rgba(198, 154, 107, 0.45);
}
.btn:active { transform: translateY(0); }
.btn:disabled { opacity: 0.45; cursor: wait; transform: none; box-shadow: none; }
.btn.ghost {
  background: var(--surface-2);
  color: var(--text);
  border: 1px solid var(--border);
  box-shadow: none;
}
.btn.ghost:hover {
  border-color: var(--copper);
  color: var(--copper-hi);
  background: var(--surface-3);
}
.btn.on { background: linear-gradient(135deg, #DDB98C, #C69A6B); color: #120D08; }
.btn.sm { padding: 5px 12px; font-size: 11.5px; border-radius: var(--radius-sm); }
.iconbtn {
  width: 36px;
  height: 36px;
  border-radius: var(--radius);
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: all 0.15s ease;
}
.iconbtn:hover { border-color: var(--copper); color: var(--copper-hi); background: var(--surface-3); }
.iconbtn.on { border-color: var(--copper); color: var(--copper-txt); background: var(--copper-bg); }

/* ── COMMAND SEARCH & CONTROL CONSOLE ── */
.feed-header-toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}
.search-box-wrap {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
}
.search-glass-icon {
  position: absolute;
  right: 14px;
  font-size: 14px;
  color: var(--muted);
  pointer-events: none;
}
.search-box-wrap input[type=text] {
  width: 100%;
  padding: 12px 42px 12px 120px;
  border-radius: var(--radius);
  background: var(--surface);
  border: 1px solid var(--border);
  font-size: 13.5px;
  color: var(--text);
  transition: all 0.2s ease;
  box-shadow: var(--shadow-sm);
}
.search-box-wrap input[type=text]:focus {
  border-color: var(--copper);
  background: var(--surface-2);
  box-shadow: 0 0 0 3px rgba(198, 154, 107, 0.18);
  outline: none;
}
.search-kbd-hint {
  position: absolute;
  left: 14px;
  font-size: 10px;
  color: var(--faint);
  background: var(--surface-2);
  border: 1px solid var(--border);
  padding: 3px 8px;
  border-radius: 6px;
  pointer-events: none;
}
.feed-meta-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 11px 18px;
  border-radius: var(--radius);
  font-size: 12.5px;
  color: var(--muted);
  box-shadow: var(--shadow-sm);
  white-space: nowrap;
}
.feed-meta-badge .badge-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--green); }
.feed-meta-badge b { color: var(--copper-txt); font-weight: 900; font-size: 13.5px; font-variant-numeric: tabular-nums; }

/* Control Console Panel */
.feed-control-console {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 12px 18px;
  margin-bottom: 12px;
  box-shadow: var(--shadow-sm);
}
.console-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.console-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
  white-space: nowrap;
}
.console-item select {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  outline: none;
}
.console-slider-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 220px;
  flex: 1;
  max-width: 320px;
  margin-inline-start: auto;
  background: var(--surface-2);
  border: 1px solid var(--border);
  padding: 6px 12px;
  border-radius: var(--radius-sm);
}
.slider-info { display: flex; justify-content: space-between; align-items: center; }
.cred-pill {
  font-size: 11px;
  font-weight: 900;
  color: var(--copper-txt);
  background: var(--copper-bg);
  border: 1px solid var(--copper-line);
  padding: 1px 7px;
  border-radius: 6px;
  font-variant-numeric: tabular-nums;
}
.console-slider-item input[type=range] {
  width: 100%;
  height: 5px;
  -webkit-appearance: none;
  appearance: none;
  background: linear-gradient(90deg, rgba(198, 154, 107, 0.25), var(--copper));
  border-radius: 3px;
  outline: none;
}
.console-slider-item input[type=range]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--copper-hi);
  border: 2px solid #000;
  cursor: pointer;
  box-shadow: 0 0 8px var(--copper);
}

/* Category & Asset Dual Chips Console */
.chips-console {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 12px 16px;
  box-shadow: var(--shadow-sm);
}
.chips-lane {
  display: flex;
  align-items: center;
  gap: 10px;
}
.lane-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 800;
  color: var(--copper-txt);
  min-width: 78px;
  flex-shrink: 0;
  background: var(--copper-bg);
  border: 1px solid var(--copper-line);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
}
.lane-chips {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
  align-items: center;
}
.chip {
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--muted);
  padding: 5px 12px;
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  display: inline-flex;
  gap: 5px;
  align-items: center;
}
.chip:hover { border-color: var(--copper); color: var(--text); background: var(--surface-3); }
.chip.on {
  background: var(--copper-bg);
  border-color: var(--copper);
  color: var(--copper-hi);
  font-weight: 800;
  box-shadow: 0 0 12px rgba(198, 154, 107, 0.15);
}
.chip .n { font-size: 10.5px; opacity: 0.85; font-variant-numeric: tabular-nums; }

/* ── 2026 NEWS GRID & CARDS ── */
.ngrid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}
.ncard {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: var(--shadow-sm);
}
.ncard:hover {
  border-color: var(--copper-line);
  background: var(--card-hover);
  transform: translateY(-3px);
  box-shadow: var(--shadow-md), 0 0 16px rgba(198, 154, 107, 0.2);
}
.ncard .thumb {
  width: 100%;
  height: 160px;
  display: block;
  background: var(--surface-2);
  position: relative;
  overflow: hidden;
}
.ncard .thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.3s ease;
}
.ncard:hover .thumb img { transform: scale(1.03); }
.ncard .thumb::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(0,0,0,0) 40%, rgba(7, 9, 14, 0.88) 100%);
  pointer-events: none;
}
.ncard .thumb .cred-chip {
  position: absolute;
  bottom: 10px;
  inset-inline-start: 10px;
  z-index: 2;
}
.cred {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  direction: ltr;
  font-weight: 800;
  border-radius: var(--radius-sm);
  padding: 2px 7px;
  font-size: 10.5px;
  font-variant-numeric: tabular-nums;
}
.cred.hi { background: var(--green-bg); color: var(--green); border: 1px solid var(--green-line); }
.cred.mid { background: var(--copper-bg); color: var(--copper-hi); border: 1px solid var(--copper-line); }
.cred.low { background: var(--red-bg); color: var(--red); border: 1px solid var(--red-line); }
.ncard .noimg {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  opacity: 0.3;
  background: var(--surface-2);
}
.ncard .body {
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}
.ncard .row1 { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
.badge {
  font-size: 10px;
  font-weight: 800;
  padding: 2px 8px;
  border-radius: var(--radius-pill);
}
.b-topic { background: rgba(56, 189, 248, 0.12); color: var(--cyan); border: 1px solid rgba(56, 189, 248, 0.28); }
.b-asset { background: var(--copper-bg); color: var(--copper-txt); border: 1px solid var(--copper-line); }
.b-kind { background: rgba(168, 85, 247, 0.12); color: #C084FC; border: 1px solid rgba(168, 85, 247, 0.25); }

.ncard .ttl {
  font-size: 14.5px;
  font-weight: 800;
  line-height: 1.75;
  color: var(--text);
}
.ncard .ttl-en {
  font-size: 10.5px;
  color: var(--muted);
  direction: ltr;
  text-align: left;
  line-height: 1.5;
  opacity: 0.85;
}
.ncard .summ {
  font-size: 12px;
  color: var(--body);
  line-height: 1.8;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.ncard .row2 {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid var(--line);
  font-size: 11px;
  color: var(--muted);
  flex-wrap: wrap;
}
.src { color: var(--copper); font-weight: 800; }
.ncard .dt { font-weight: 500; font-variant-numeric: tabular-nums; }
.star-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  color: var(--muted);
  padding: 0 4px;
  margin-inline-start: auto;
  transition: all 0.2s ease;
}
.star-btn:hover, .star-btn.on { color: var(--gold); transform: scale(1.2); }
.blurb-btn {
  margin-top: 4px;
  align-self: flex-start;
  min-height: 28px;
  padding: 4px 12px;
  font-size: 11px;
}

/* ── MODALS & OVERLAYS ── */
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(3, 5, 8, 0.8);
  z-index: 400;
  display: none;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}
.overlay.open { display: flex; animation: overlayIn 0.2s ease; }
@keyframes overlayIn { from { opacity: 0; } to { opacity: 1; } }
.modal {
  background: var(--surface);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-xl);
  width: 95%;
  max-width: 840px;
  max-height: 90vh;
  overflow-y: auto;
  padding: 26px 28px;
  position: relative;
  box-shadow: var(--shadow-lg), 0 0 30px var(--copper-glow);
}
.mclose {
  position: absolute;
  top: 16px;
  left: 16px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 50%;
  width: 32px;
  height: 32px;
  color: var(--muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  transition: all 0.15s;
}
.mclose:hover { background: var(--red); color: #fff; border-color: var(--red); }
.modal h2 { font-size: 18px; margin: 12px 0 6px; line-height: 1.8; }
.modal .h2en { font-size: 12px; color: var(--muted); direction: ltr; text-align: left; margin-bottom: 12px; }
.modal .mmeta { display: flex; gap: 14px; flex-wrap: wrap; font-size: 11.5px; color: var(--muted); margin-bottom: 14px; align-items: center; }
.modal .flags { background: rgba(244, 63, 94, 0.12); border: 1px solid var(--red-line); color: var(--red); border-radius: var(--radius-sm); padding: 8px 12px; font-size: 11.5px; margin-bottom: 12px; }
.msec { margin-top: 16px; padding: 14px; background: var(--surface-2); border-radius: var(--radius); border: 1px solid var(--border); }
.msec h4 { font-size: 13px; color: var(--copper); margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
.msec p { font-size: 13px; line-height: 2.1; color: var(--body); }
.msec p.en { direction: ltr; text-align: left; }
.msec p.fa { direction: rtl; text-align: right; }
.msec .scroll { max-height: 240px; overflow-y: auto; padding-right: 4px; }
.mlink { display: inline-flex; align-items: center; gap: 6px; font-weight: 800; font-size: 12.5px; color: var(--copper-hi); margin-top: 14px; }

/* ── PANELS & COMMON STYLES ── */
.panelbox {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 22px;
  margin-bottom: 18px;
  box-shadow: var(--shadow-sm);
}
.panelbox h3 { font-size: 15px; margin-bottom: 14px; color: var(--copper); }
.panelbox .hint { font-size: 11.5px; color: var(--muted); line-height: 2; }
.empty { color: var(--muted); text-align: center; padding: 48px 20px; font-size: 13px; font-weight: 600; }
.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--border);
  border-top-color: var(--copper);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  margin: 36px auto;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Toast */
.toast {
  position: fixed;
  bottom: 24px;
  left: 24px;
  background: var(--surface-3);
  border: 1px solid var(--copper-line);
  color: var(--copper-txt);
  padding: 10px 18px;
  border-radius: var(--radius);
  font-size: 12.5px;
  font-weight: 700;
  box-shadow: var(--shadow-md);
  z-index: 500;
  display: none;
}

/* ── REPORTS & CHARTS ── */
.rep-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.rep-layout { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.75fr); gap: 18px; align-items: start; }
@media(max-width: 1080px){ .rep-layout { grid-template-columns: 1fr; } }
.rep-doc {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  line-height: 2.1;
  box-shadow: var(--shadow-sm);
}
.rep-actions { display: flex; gap: 8px; margin-bottom: 14px; }
.rep-doc h2 { color: var(--copper-hi); font-size: 19px; margin-bottom: 4px; }
.rep-doc .meta { font-size: 11.5px; color: var(--muted); margin-bottom: 16px; display: flex; gap: 14px; flex-wrap: wrap; }
.rep-doc h3 { font-size: 15px; color: var(--cyan); margin: 22px 0 10px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
.rep-doc p { font-size: 13.5px; margin-bottom: 12px; white-space: pre-wrap; color: var(--body); }
.rep-doc p.en { text-align: left; direction: ltr; }
.rep-doc p.fa { text-align: right; direction: rtl; }

.chartbox {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 16px;
  position: sticky;
  top: 10px;
  box-shadow: var(--shadow-sm);
}
.chartbox h3 { font-size: 14px; color: var(--copper); margin-bottom: 6px; }
.chartbox .csub { font-size: 10.5px; color: var(--muted); margin-bottom: 10px; }
.mode-row { display: flex; gap: 6px; align-items: center; margin-bottom: 10px; flex-wrap: wrap; }
.mode-row .mlabel { font-size: 11px; color: var(--muted); }
.mode-row .tg, .toggles .tg {
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--muted);
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  cursor: pointer;
}
.mode-row .tg.on, .toggles .tg.on { background: var(--copper-bg); border-color: var(--copper); color: var(--copper-txt); font-weight: 800; }
.chart-live { font-size: 10.5px; color: var(--green); margin-inline-start: auto; }
.chart-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.chart-head .p { font-size: 20px; font-weight: 900; direction: ltr; font-variant-numeric: tabular-nums; }
.chart-head .p.flash-up { color: var(--green); } .chart-head .p.flash-dn { color: var(--red); }
.chart-head .c { font-size: 12.5px; font-weight: 800; direction: ltr; font-variant-numeric: tabular-nums; }
.chart-head .c.up { color: var(--green); } .chart-head .c.dn { color: var(--red); }
.tvwrap { position: relative; height: 380px; border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; background: #000; }
.pane { width: 100%; display: block; border-bottom: 1px solid var(--line); }
.legend { display: flex; gap: 10px; font-size: 10px; color: var(--muted); margin-top: 8px; flex-wrap: wrap; }
.legend i { display: inline-block; width: 10px; height: 3px; border-radius: 2px; vertical-align: middle; margin-inline-end: 4px; }
.chart-notes { font-size: 11px; color: var(--muted); line-height: 1.9; margin-top: 10px; border-top: 1px solid var(--line); padding-top: 8px; }
.chart-notes ul { padding-inline-start: 18px; margin-top: 4px; }

/* Citations in reports */
.cites { background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius); margin: 6px 0 14px; overflow: hidden; }
.cites-toggle { display: flex; align-items: center; gap: 8px; width: 100%; background: none; border: none; color: var(--copper); font-size: 11.5px; font-weight: 800; padding: 9px 12px; cursor: pointer; text-align: right; }
.cites-toggle:hover { background: var(--copper-bg); }
.cites-toggle .arrow { transition: transform 0.18s; font-size: 9px; display: inline-block; }
.cites.open .cites-toggle .arrow { transform: rotate(90deg); }
.cites-body { display: none; padding: 2px 12px 10px; }
.cites.open .cites-body { display: block; }
.cite { display: flex; gap: 9px; padding: 8px 0; border-bottom: 1px dashed var(--border); align-items: flex-start; }
.cite:last-child { border-bottom: none; }
.cite .idx { background: var(--copper-bg); color: var(--copper-txt); border: 1px solid var(--copper-line); font-size: 10px; font-weight: 900; min-width: 20px; height: 20px; border-radius: 6px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.cite .body { flex: 1; min-width: 0; }
.cite .t { font-size: 12px; line-height: 1.7; font-weight: 700; }
.cite .t-en { font-size: 10px; color: var(--muted); direction: ltr; text-align: left; }
.cite .meta2 { font-size: 10px; color: var(--muted); margin-top: 4px; display: flex; gap: 8px; flex-wrap: wrap; }

/* ── ECONOMIC CALENDAR ── */
.cal-grid { display: grid; grid-template-columns: minmax(0, 1.7fr) minmax(280px, 0.75fr); gap: 16px; align-items: start; }
@media(max-width: 1000px){ .cal-grid { grid-template-columns: 1fr; } }
.cal-countdown {
  background: linear-gradient(135deg, rgba(198, 154, 107, 0.15) 0%, rgba(140, 106, 68, 0.08) 100%);
  border: 1px solid var(--copper-line);
  border-radius: var(--radius);
  padding: 12px 18px;
  font-size: 13.5px;
  color: var(--copper-txt);
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: var(--shadow-sm);
  margin-bottom: 14px;
}
.cal-countdown b { font-size: 15.5px; font-variant-numeric: tabular-nums; }
.cal-released {
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid var(--green-line);
  color: var(--green);
  border-radius: var(--radius);
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Dedicated Calendar Control Console */
.cal-control-panel {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 14px 16px;
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: var(--shadow-sm);
}
.cal-tabs-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.cal-segmented-control {
  display: inline-flex;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 4px;
  gap: 4px;
}
.cal-seg-btn {
  background: transparent;
  border: none;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  padding: 7px 16px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.18s ease;
}
.cal-seg-btn:hover {
  color: var(--text);
  background: rgba(255, 255, 255, 0.05);
}
.cal-seg-btn.on {
  background: linear-gradient(135deg, #C69A6B 0%, #8C6A44 100%);
  color: #120D08;
  font-weight: 800;
  box-shadow: 0 2px 8px rgba(198, 154, 107, 0.35);
}
.cal-filters-row {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}
.cal-filter-group {
  display: flex;
  align-items: center;
  gap: 6px;
}
.cal-label {
  font-size: 11.5px;
  font-weight: 700;
  color: var(--muted);
  white-space: nowrap;
}
.cal-filter-group select {
  min-width: 140px;
  background-color: var(--surface);
}
.cal-hide-past-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--body);
  cursor: pointer;
  margin-inline-start: auto;
  user-select: none;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  transition: background 0.15s;
}
.cal-hide-past-toggle:hover {
  background: var(--surface);
}
.cal-hide-past-toggle input[type="checkbox"] {
  accent-color: var(--copper);
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.calday { border: 1px solid var(--border); border-radius: var(--radius); margin-bottom: 12px; overflow: hidden; background: var(--surface); }
.calday-h { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: var(--surface-2); border-bottom: 1px solid var(--border); font-size: 13px; }
.calrow { display: flex; gap: 10px; align-items: center; padding: 9px 12px; border-bottom: 1px solid var(--line-soft); font-size: 12px; flex-wrap: wrap; }
.calrow:last-child { border-bottom: none; }
.calrow.past { opacity: 0.5; }
.calrow.released { background: rgba(16, 185, 129, 0.04); }
.ev-actual { display: inline-flex; align-items: center; gap: 4px; font-size: 10px; font-weight: 800; padding: 2px 7px; border-radius: 6px; background: var(--green-bg); color: var(--green); border: 1px solid var(--green-line); }
.ev-check { color: var(--green); }
.cal-fcst, .cal-prev { font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 6px; font-variant-numeric: tabular-nums; }
.cal-fcst { background: var(--green-bg); color: var(--green); }
.cal-prev { background: rgba(148, 163, 184, 0.12); color: var(--slate); }
.badge-hi { background: rgba(244, 63, 94, 0.15); border-color: var(--red); color: #FDA4AF; }
.badge-md { background: rgba(245, 158, 11, 0.15); border-color: var(--copper-line); color: var(--copper-txt); }
.badge-lo { background: rgba(148, 163, 184, 0.08); border-color: var(--line); color: var(--muted); }
.session { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-bottom: 1px solid var(--line-soft); font-size: 11.5px; }
.session .dot { width: 7px; height: 7px; border-radius: 50%; }
.session.on .dot { background: var(--green); box-shadow: 0 0 6px var(--green); }
.session.off .dot { background: var(--faint); }
.session .state { font-size: 10px; font-weight: 800; }
.session.on .state { color: var(--green); } .session.off .state { color: var(--muted); }
.session .eta { font-size: 10px; color: var(--muted); margin-inline-start: auto; }

/* ── FEAR & GREED ── */
.fngchip { display: flex; align-items: center; gap: 8px; background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius); padding: 8px 14px; font-size: 12px; font-variant-numeric: tabular-nums; }
.fngchip b { font-size: 15px; font-weight: 900; }
.fngsyms { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; margin-top: 6px; }
.fngsym { background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius); padding: 12px; display: flex; flex-direction: column; gap: 5px; }
.fngsym .fs-head { display: flex; align-items: center; gap: 6px; font-size: 12.5px; font-weight: 800; }
.fngsym .fs-score { font-size: 24px; font-weight: 900; line-height: 1.1; }
.fngsym .fs-bar { height: 5px; border-radius: 3px; background: rgba(255,255,255,0.08); overflow: hidden; margin-top: 4px; }
.fngsym .fs-bar i { display: block; height: 100%; border-radius: 3px; }

/* ── ETF & IDEAS ── */
.etftab { width: 100%; border-collapse: collapse; font-size: 12px; }
.etftab td { padding: 6px 10px; border-bottom: 1px solid var(--line-soft); }
.etfgrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; margin-top: 8px; }
.etfcard { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 12px; }
.etfcard .tk { font-weight: 900; font-size: 13.5px; direction: ltr; }
.etfcard .prc { font-size: 16px; font-weight: 900; direction: ltr; text-align: right; }
.etfcard .chg { font-size: 11px; font-weight: 800; direction: ltr; text-align: right; }
.etfcard .chg.up { color: var(--green); } .etfcard .chg.dn { color: var(--red); }
.idea { display: flex; flex-direction: column; gap: 3px; padding: 8px 10px; border-bottom: 1px solid var(--line-soft); text-decoration: none; color: var(--body); }
.idea .dir { font-size: 10px; font-weight: 800; }
.idea .dir.up { color: var(--green); } .idea .dir.dn { color: var(--red); }
.idea .ttl { font-size: 12px; font-weight: 700; line-height: 1.5; }
.idea .meta { font-size: 10px; color: var(--muted); direction: ltr; text-align: right; }

/* ── SETTINGS, SOURCES & ASSETS FORMS ── */
.setrow { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 12px 0; border-bottom: 1px solid var(--border); flex-wrap: wrap; }
.setrow .lbl { font-size: 13px; font-weight: 700; }
.setrow .hint { font-size: 11px; color: var(--muted); margin-top: 2px; }
.switch { position: relative; width: 38px; height: 22px; flex-shrink: 0; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; inset: 0; background: var(--border); border-radius: 20px; cursor: pointer; transition: 0.2s; }
.slider:before { content: ""; position: absolute; width: 16px; height: 16px; border-radius: 50%; background: var(--faint); top: 3px; right: 3px; transition: 0.2s; }
.switch input:checked + .slider { background: var(--copper-line); }
.switch input:checked + .slider:before { transform: translateX(-16px); background: var(--copper); }
.formgrid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; align-items: end; }
.formgrid label { font-size: 11px; color: var(--muted); display: block; margin-bottom: 4px; font-weight: 600; }
.formgrid input, .formgrid select { width: 100%; direction: ltr; text-align: left; }
.asset-toggles { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
table.asset-table { width: 100%; border-collapse: collapse; font-size: 12px; }
table.asset-table th, table.asset-table td { padding: 9px 8px; border-bottom: 1px solid var(--border); text-align: right; }
table.asset-table th { color: var(--muted); font-weight: 700; font-size: 11px; }
table.asset-table td.ltr { direction: ltr; text-align: left; color: var(--muted); font-variant-numeric: tabular-nums; }
.kindgroup { margin-bottom: 12px; border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
.kindgroup .kh { padding: 9px 14px; background: var(--surface-2); font-size: 12px; font-weight: 800; display: flex; justify-content: space-between; cursor: pointer; }
.kindgroup .kb { padding: 0 14px; }
.srcrow { display: flex; align-items: center; gap: 10px; padding: 9px 2px; border-bottom: 1px solid var(--border); font-size: 12px; flex-wrap: wrap; }
.srcrow:last-child { border-bottom: none; }
.srcrow .nm { font-weight: 700; min-width: 130px; }
.srcrow .url { color: var(--muted); font-size: 10.5px; flex: 1; direction: ltr; text-align: left; }
.trust { font-size: 10px; font-weight: 800; padding: 2px 7px; border-radius: 6px; background: var(--copper-bg); color: var(--copper-txt); direction: ltr; }
.ok { color: var(--green); font-weight: 800; } .bad { color: var(--red); font-weight: 800; }
.monrow { border: 1px solid var(--border); border-radius: var(--radius); padding: 11px 14px; margin-bottom: 8px; background: var(--surface); font-size: 12px; }
.tg-toggles { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 8px 14px; }
.tgopt { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--body); cursor: pointer; padding: 6px 10px; border-radius: var(--radius-sm); }
.tgopt:hover { background: var(--surface-2); }
.tgopt input { accent-color: var(--copper); width: 15px; height: 15px; }

/* ── RESPONSIVE ADAPTATIONS (MOBILE & TABLET) ── */
@media (max-width: 1024px) {
  .topbar-telemetry { display: none; }
}
@media (max-width: 860px) {
  .menu-toggle-btn { display: flex; }
  .app-sidebar {
    position: fixed;
    right: 0;
    top: var(--topbar-height);
    bottom: 0;
    z-index: 200;
    transform: translateX(100%);
    box-shadow: -8px 0 24px rgba(0, 0, 0, 0.7);
  }
  .app-sidebar.open {
    transform: translateX(0);
  }
  .sidebar-backdrop {
    position: fixed;
    inset: 0;
    top: var(--topbar-height);
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(4px);
    z-index: 150;
    display: none;
  }
  .sidebar-backdrop.open {
    display: block;
  }
  .view-container {
    padding: 16px;
  }
  .ngrid {
    grid-template-columns: 1fr;
  }
}

/* ═══════════════════════════════════════════════════════════════════════
   2026 CINEMATIC REFRESH
   Ambient stage + frosted glass surfaces + editorial hierarchy + staged
   entrance. Idea borrowed from the Sellix hero: a single proportional
   unit, quiet hairlines, one confident accent, and a stage that is lit
   before the cast walks on.
   This whole layer is additive — delete this block to revert to the
   previous skin without touching anything else.
   ═══════════════════════════════════════════════════════════════════════ */

/* ── AMBIENT STAGE ─────────────────────────────────────────────────────
   A lit backdrop rather than a flat fill: two soft glows, a drifting dot
   matrix and a vignette. Fixed, non-interactive, never animated away. */
.stage {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
  background:
    radial-gradient(1100px 720px at 84% -12%, rgba(198, 154, 107, .14), transparent 62%),
    radial-gradient(880px 680px at 4% 114%, rgba(56, 189, 248, .075), transparent 64%),
    radial-gradient(760px 560px at 46% 44%, rgba(168, 85, 247, .055), transparent 72%),
    var(--stage-base);
}
.stage::before {
  content: "";
  position: absolute;
  inset: -25%;
  background-image: radial-gradient(rgba(255, 255, 255, .06) 1px, transparent 1.4px);
  background-size: 28px 28px;
  -webkit-mask-image: radial-gradient(circle at 50% 42%, #000 0%, transparent 76%);
  mask-image: radial-gradient(circle at 50% 42%, #000 0%, transparent 76%);
  animation: stageDrift 72s linear infinite;
}
.stage::after {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(125% 95% at 50% 26%, transparent 38%, rgba(0, 0, 0, .62) 100%);
}
@keyframes stageDrift { from { transform: translate3d(0, 0, 0); } to { transform: translate3d(28px, 28px, 0); } }

/* the shell floats above the stage and goes translucent so it shows through */
.app-shell { position: relative; z-index: 1; background: transparent; }
.app-main  { background: transparent; }

/* ── EDITORIAL TYPE ────────────────────────────────────────────────────
   Latin glyphs resolve to Plus Jakarta Sans; Persian falls through to
   Vazirmatn (PJS carries no Arabic script), so both scripts keep their
   own voice in one stack. */
body, button, input, select, textarea {
  font-family: 'Plus Jakarta Sans', 'Vazirmatn', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  text-rendering: geometricPrecision;
}
h1, h2, h3, h4, h5 { letter-spacing: -.022em; }
h1 { font-weight: 800; }
h2 { font-weight: 700; }
.brand-title-row h1 { font-size: 17px; letter-spacing: -.035em; white-space: nowrap; }
.panelbox h3, .chartbox h3 { letter-spacing: -.015em; font-weight: 700; }

/* ── TOPBAR ──────────────────────────────────────────────────────────── */
.app-topbar {
  position: relative;
  background: rgba(8, 10, 15, .62);
  -webkit-backdrop-filter: var(--glass-blur);
  backdrop-filter: var(--glass-blur);
  border-bottom: 1px solid var(--glass-line);
  padding: 0 24px;
}
.app-topbar::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(198, 154, 107, .42) 50%, transparent);
  pointer-events: none;
}
.brand-group { gap: 13px; }
.brand-badge {
  width: 40px;
  height: 40px;
  border-radius: 13px;
  background: linear-gradient(160deg, #E9CBA3 0%, #A67C4F 55%, #8C6A44 100%);
  box-shadow: 0 10px 26px -10px rgba(198, 154, 107, .85), inset 0 1px 0 rgba(255, 255, 255, .5);
  border: 1px solid rgba(255, 255, 255, .18);
}
.brand-desc { font-size: 10.5px; letter-spacing: .01em; }
.live-pill { padding: 3px 9px; letter-spacing: .04em; backdrop-filter: blur(6px); }
.topbar-telemetry {
  background: var(--glass);
  border: 1px solid var(--glass-line);
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
  box-shadow: var(--inset-hi);
  padding: 7px 16px;
}
.telem-item b { letter-spacing: -.01em; }

/* ── BUTTONS — one confident accent, one quiet ghost ─────────────────── */
.btn {
  border-radius: var(--radius-pill);
  padding: 9px 20px;
  background: linear-gradient(180deg, #E3C39A 0%, #C69A6B 100%);
  color: #17110A;
  letter-spacing: -.008em;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .38), 0 8px 20px -10px rgba(198, 154, 107, .8);
  transition: transform .18s var(--e-soft), box-shadow .18s var(--e-soft), background .18s ease;
}
.btn:hover {
  filter: none;
  background: linear-gradient(180deg, #EFD2AC 0%, #D3A97C 100%);
  transform: translateY(-1px);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .45), 0 12px 26px -10px rgba(198, 154, 107, .95);
}
.btn.on { background: linear-gradient(180deg, #F2D6B1 0%, #D9B084 100%); }
.btn.ghost {
  background: var(--glass);
  border: 1px solid var(--glass-line);
  color: #E7EBF0;
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  box-shadow: var(--inset-hi);
}
.btn.ghost:hover {
  background: var(--glass-hi);
  border-color: rgba(255, 255, 255, .2);
  color: #fff;
}
.btn.sm { border-radius: var(--radius-pill); padding: 6px 14px; }
.iconbtn { border-radius: var(--radius-pill); background: var(--glass); border: 1px solid var(--glass-line); }

/* arrow glyph used on primary calls to action */
.arw { width: 14px; height: 11px; flex: 0 0 auto; display: block; }

/* ── SIDEBAR — frosted rail, hairline separation ─────────────────────── */
.app-sidebar {
  background: linear-gradient(180deg, rgba(10, 13, 19, .70), rgba(7, 9, 14, .88));
  -webkit-backdrop-filter: var(--glass-blur);
  backdrop-filter: var(--glass-blur);
  border-inline-end: 1px solid var(--glass-line);
  padding: 18px 12px 22px;
}
.sidebar-section-label {
  font-size: 9.5px;
  letter-spacing: .14em;
  color: var(--faint);
  padding: 14px 12px 6px;
}
.nav-item {
  border-radius: 13px;
  padding: 10px 13px;
  letter-spacing: -.008em;
  transition: background .18s var(--e-soft), color .18s ease, box-shadow .18s ease, transform .18s var(--e-soft);
}
.nav-item:hover { transform: translateX(-2px); }
.nav-item.active {
  background: linear-gradient(90deg, rgba(198, 154, 107, .18), rgba(198, 154, 107, .04));
  box-shadow: inset 0 0 0 1px rgba(198, 154, 107, .30), 0 10px 26px -14px rgba(198, 154, 107, .9);
}
.nav-item.active::before { inset-inline-start: 5px; width: 2.5px; box-shadow: 0 0 10px var(--copper); }
.nav-icon { font-size: 15px; filter: saturate(.92); }
.sidebar-footer { border-top: 1px solid var(--glass-line); }

/* ── ASSET TICKER ────────────────────────────────────────────────────── */
.assets {
  background: linear-gradient(180deg, rgba(9, 12, 18, .78), rgba(9, 12, 18, .42));
  -webkit-backdrop-filter: blur(14px);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--glass-line);
  padding: 13px 24px;
  gap: 11px;
}
.acard {
  background: var(--sheen);
  border: 1px solid var(--glass-line);
  border-radius: 15px;
  box-shadow: var(--inset-hi), 0 10px 24px -18px rgba(0, 0, 0, .9);
  transition: transform .22s var(--e-reveal), border-color .22s ease, box-shadow .22s var(--e-reveal), background .22s ease;
}
.acard::before {
  content: "";
  position: absolute;
  inset-inline: 14px;
  top: 0;
  height: 2px;
  border-radius: 2px;
  background: linear-gradient(90deg, transparent, rgba(198, 154, 107, .55), transparent);
  opacity: .7;
}
.acard:hover {
  background: linear-gradient(180deg, rgba(255, 255, 255, .075), rgba(255, 255, 255, .028));
  border-color: rgba(198, 154, 107, .55);
  transform: translateY(-3px);
  box-shadow: var(--inset-hi), 0 18px 34px -18px rgba(0, 0, 0, .95), 0 0 22px -8px rgba(198, 154, 107, .55);
}
.acard .prc { font-size: 19px; font-weight: 800; letter-spacing: -.03em; }
.acard .sym { letter-spacing: -.01em; }
.acard svg { filter: drop-shadow(0 3px 6px rgba(0, 0, 0, .45)); }

/* ── GLASS SURFACES — one material for every panel ───────────────────── */
.panelbox, .rep-doc, .chartbox, .calday, .cal-control-panel, .chips-console,
.feed-control-console, .monrow, .kindgroup, .msec, .etfcard, .fngsym,
.feed-meta-badge, .cites {
  background: var(--sheen);
  border: 1px solid var(--glass-line);
  box-shadow: var(--inset-hi), 0 14px 34px -26px rgba(0, 0, 0, .95);
}
.feed-control-console, .chips-console, .cal-control-panel, .feed-meta-badge {
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
}
.panelbox { padding: 24px; }
.panelbox h3 { display: flex; align-items: center; gap: 8px; }
.rep-doc p { color: #CBD5E1; line-height: 2.05; }
.msec p { color: #C6D1DD; }

/* ── NEWS CARDS ──────────────────────────────────────────────────────── */
.ncard {
  background: var(--sheen);
  border: 1px solid var(--glass-line);
  border-radius: var(--radius-lg);
  box-shadow: var(--inset-hi), 0 16px 36px -28px rgba(0, 0, 0, .95);
  transition: transform .26s var(--e-reveal), border-color .26s ease, box-shadow .26s var(--e-reveal), background .26s ease;
}
.ncard:hover {
  background: linear-gradient(180deg, rgba(255, 255, 255, .075), rgba(255, 255, 255, .026));
  border-color: rgba(198, 154, 107, .42);
  transform: translateY(-4px);
  box-shadow: var(--inset-hi), 0 26px 52px -26px rgba(0, 0, 0, .98), 0 0 26px -12px rgba(198, 154, 107, .55);
}
.ncard .thumb::after { background: linear-gradient(180deg, rgba(6, 8, 12, 0) 38%, rgba(6, 8, 12, .92) 100%); }
.ncard .thumb img { transition: transform .5s var(--e-reveal); }
.ncard:hover .thumb img { transform: scale(1.045); }
.ncard .ttl { font-size: 15px; line-height: 1.7; letter-spacing: -.012em; }
.ncard .body { padding: 15px 17px; gap: 9px; }
.ncard .row2 { border-top: 1px solid var(--glass-line); }

/* ── SEARCH + CONSOLE CONTROLS ───────────────────────────────────────── */
.search-box-wrap input[type=text] {
  background: var(--glass);
  border: 1px solid var(--glass-line);
  border-radius: 14px;
  padding: 13px 44px 13px 130px;
  box-shadow: var(--inset-hi);
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
}
.search-box-wrap input[type=text]:focus {
  background: rgba(255, 255, 255, .07);
  border-color: rgba(198, 154, 107, .65);
  box-shadow: 0 0 0 4px rgba(198, 154, 107, .14), var(--inset-hi);
}
.console-item select, .cal-filter-group select, select, input[type=text], input[type=password], textarea {
  border-radius: 10px;
}
.chip { border-radius: var(--radius-pill); padding: 6px 13px; }
.chip.on { box-shadow: 0 0 16px -4px rgba(198, 154, 107, .55), inset 0 1px 0 rgba(255, 255, 255, .06); }

/* ── MODALS — deeper glass over a blurred stage ──────────────────────── */
.overlay { background: rgba(3, 5, 8, .72); -webkit-backdrop-filter: blur(16px) saturate(120%); backdrop-filter: blur(16px) saturate(120%); }
.modal {
  background: linear-gradient(180deg, rgba(20, 26, 38, .94), rgba(12, 16, 24, .96));
  border: 1px solid rgba(255, 255, 255, .1);
  border-radius: var(--radius-xl);
  box-shadow: var(--inset-hi), 0 40px 90px -30px rgba(0, 0, 0, 1), 0 0 46px -20px rgba(198, 154, 107, .6);
}

/* ── SCROLLBARS — quieter ────────────────────────────────────────────── */
html { scrollbar-width: thin; scrollbar-color: rgba(255, 255, 255, .16) transparent; }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, .12);
  border: 3px solid transparent;
  background-clip: padding-box;
  border-radius: 99px;
}
::-webkit-scrollbar-thumb:hover { background: rgba(198, 154, 107, .6); background-clip: padding-box; }

/* ── STAGED ENTRANCE ───────────────────────────────────────────────────
   Armed synchronously in <head> so there is never a flash of unanimated
   content. The apparatus removes itself when the last tween ends. */
html.anim .app-topbar,
html.anim .app-sidebar,
html.anim .assets,
html.anim .view-container { opacity: 0; }
html.anim .app-topbar, html.anim .assets, html.anim .view-container { will-change: transform, opacity; }

@keyframes shellDown { from { opacity: 0; transform: translateY(-12px); } to { opacity: 1; transform: none; } }
@keyframes shellUp   { from { opacity: 0; transform: translateY(16px); }  to { opacity: 1; transform: none; } }
@keyframes shellFade { from { opacity: 0; } to { opacity: 1; } }
@keyframes shellSide { from { opacity: 0; transform: translateX(22px); } to { opacity: 1; transform: none; } }

html.anim.go .app-topbar     { animation: shellDown .72s var(--e-soft)   .04s both; }
html.anim.go .app-sidebar    { animation: shellFade .70s var(--e-soft)   .12s both; }
html.anim.go .assets         { animation: shellUp   .78s var(--e-reveal) .22s both; }
html.anim.go .view-container { animation: shellUp   .92s var(--e-reveal) .32s both; }
@media (min-width: 861px) {
  html.anim.go .app-sidebar { animation-name: shellSide; }
}
@media (prefers-reduced-motion: reduce) {
  html.anim .app-topbar, html.anim .app-sidebar, html.anim .assets, html.anim .view-container { opacity: 1; }
  html.anim.go .app-topbar, html.anim.go .app-sidebar, html.anim.go .assets, html.anim.go .view-container { animation: none; }
  .stage::before { animation: none; }
}

/* ── ARCHIVE — same card language as the front page, grouped by day ─── */
.archgrid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
  padding: 14px;
}
.archday .calday-h { background: linear-gradient(180deg, rgba(255, 255, 255, .05), rgba(255, 255, 255, .018)); }
@media (max-width: 860px) { .archgrid { grid-template-columns: 1fr; padding: 10px; } }

/* ── RELATED NEWS (article modal) ───────────────────────────────────────
   One row per story, hairline separated, title carries the ink and the
   outlet carries the copper — so the eye reads story → source, not a
   run-on sentence. */
.rel { padding: 6px 0 2px; }
.rel .relrow {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding: 11px 2px;
  text-decoration: none;
  border-bottom: 1px solid var(--glass-line);
  transition: background .16s ease, padding .16s ease;
}
.rel .relrow:last-child { border-bottom: none; }
.rel .relrow:hover { background: rgba(255, 255, 255, .045); padding-inline: 10px; border-radius: 10px; }
.rel .reltitle { flex: 1; min-width: 0; font-size: 12.5px; font-weight: 700; line-height: 1.75; color: #FFFFFF; }
.rel .relsrc {
  flex: 0 0 auto;
  font-size: 10.5px;
  font-weight: 800;
  color: var(--copper-hi);
  direction: ltr;
  white-space: nowrap;
}
.rel .relgo { flex: 0 0 auto; color: var(--faint); font-size: 11px; }

/* ── CONTROL SURFACES — lifted off pure black so they read as clickable ──
   Every interactive control was sitting on #141A26 with a 0.08 hairline, which
   reads as black-on-black on the stage. Just enough lift to be seen, never
   the white pill treatment (that stays reserved for the primary action). */
.chip { background: rgba(255, 255, 255, .07); border-color: rgba(255, 255, 255, .13); color: #C6D0DC; }
.chip:hover { background: rgba(255, 255, 255, .11); border-color: rgba(198, 154, 107, .6); }
.chip.on {
  background: rgba(198, 154, 107, .22);
  border-color: var(--copper);
  color: var(--copper-hi);
  box-shadow: 0 0 0 1px rgba(198, 154, 107, .35), 0 0 18px -6px rgba(198, 154, 107, .85);
}
.chip:active { transform: translateY(1px); }

select, input[type="text"], input[type="password"], textarea {
  background: rgba(255, 255, 255, .06);
  border-color: rgba(255, 255, 255, .13);
}
select option { background: #141A26; }
.console-item select, .cal-filter-group select { background-color: rgba(255, 255, 255, .06); }

.btn.ghost { background: rgba(255, 255, 255, .075); border-color: rgba(255, 255, 255, .15); color: #E7EBF0; }
.btn.ghost:hover { background: rgba(255, 255, 255, .12); border-color: rgba(255, 255, 255, .26); color: #fff; }

.iconbtn, .menu-toggle-btn { background: rgba(255, 255, 255, .07); border-color: rgba(255, 255, 255, .13); }
.iconbtn:hover { background: rgba(255, 255, 255, .13); }

.cal-seg-btn { background: rgba(255, 255, 255, .05); }
.cal-seg-btn:not(.on):hover { background: rgba(255, 255, 255, .1); }

.mode-row .tg, .toggles .tg { background: rgba(255, 255, 255, .07); border-color: rgba(255, 255, 255, .13); }
.mode-row .tg.on, .toggles .tg.on { background: rgba(198, 154, 107, .22); border-color: var(--copper); color: var(--copper-txt); }

.cites-toggle { background: rgba(255, 255, 255, .05); }

/* credibility slider — give the track body so it is visible on a dark stage */
.console-slider-item input[type=range] { height: 6px; }
.console-slider-item input[type=range]::-webkit-slider-thumb {
  border-color: #0A0D13;
  box-shadow: 0 0 0 2px rgba(198, 154, 107, .4), 0 0 10px var(--copper);
}
::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, .18); }

/* active-sort readout next to the news count */
.sort-hint {
  font-size: 10.5px;
  font-weight: 700;
  color: var(--copper-hi);
  border-inline-start: 1px solid var(--glass-line);
  padding-inline-start: 9px;
  margin-inline-start: 2px;
  white-space: nowrap;
}

/* ── CALENDAR: single-day navigation ─────────────────────────────────── */
.cal-daynav { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.cal-weeknav { margin-inline-start: auto; }
.cal-daynow {
  font-size: 12.5px;
  font-weight: 800;
  color: var(--text);
  background: rgba(255, 255, 255, .06);
  border: 1px solid var(--glass-line);
  border-radius: var(--radius-pill);
  padding: 7px 15px;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  min-width: 170px;
  text-align: center;
}
.cal-daynow.is-today { border-color: var(--copper-line); color: var(--copper-hi); background: var(--copper-bg); }
@media (max-width: 760px) { .cal-weeknav { margin-inline-start: 0; } .cal-daynow { min-width: 0; } }

/* ── EVENT COUNTDOWN — its own box, fixed cells, never reflows ──────────
   This had no styling at all: the digits changed width on every tick and
   the whole cell jumped at each minute rollover. Fixed-width cells +
   tabular figures mean nothing moves, and the day cell is always present
   so the day rollover cannot resize the box either. */
.cal-timer {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: stretch;
  gap: 4px;
  padding: 3px 5px;
  border-radius: 11px;
  background: rgba(0, 0, 0, .34);
  border: 1px solid var(--glass-line);
}
.cal-timer .sg {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
  width: 34px;
  padding: 2px 0;
  border-radius: 8px;
  background: rgba(255, 255, 255, .055);
  border: 1px solid rgba(255, 255, 255, .07);
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1;
}
.cal-timer .sg b {
  font-family: 'Plus Jakarta Sans', 'Vazirmatn', ui-monospace, monospace;
  font-size: 12.5px;
  font-weight: 800;
  line-height: 1.05;
  letter-spacing: -.02em;
  color: var(--text);
}
.cal-timer .sg small {
  font-size: 7.5px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--muted);
}
@media (max-width: 760px) {
  .cal-timer .sg { width: 29px; }
  .cal-timer .sg b { font-size: 11px; }
}

/* top countdown bar — tabular figures so it stops jittering every tick */
.cal-countdown { font-variant-numeric: tabular-nums; min-height: 44px; }

/* the asset / topic lane labels are filter-clearing buttons now */
button.lane-tag { appearance: none; font-family: inherit; cursor: pointer; transition: background .15s ease, border-color .15s ease, color .15s ease; }
button.lane-tag:hover { background: rgba(198, 154, 107, .2); border-color: var(--copper); color: var(--copper-hi); }
button.lane-tag:active { transform: translateY(1px); }

/* ETF group chip on the live quote cards */
.etfcard .grp {
  display: inline-block;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: .06em;
  text-transform: uppercase;
  color: var(--copper-hi);
  background: var(--copper-bg);
  border: 1px solid var(--copper-line);
  border-radius: var(--radius-pill);
  padding: 1px 7px;
  margin-bottom: 3px;
}

:is(button, a, input, select, [tabindex]):focus-visible {
  outline: 2px solid var(--copper-hi);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}

/* ═══════════════════════════════════════════════════════════════════════════
   DL2 — DESIGN LANGUAGE 2.0 · phase 1  (tokens · type · a11y · states)
   Added by Cline. Purely additive: no rule above is modified or removed.
   Revert: restore backups\snapshot_dl2_20260920_132815.zip   (or the single
   file backups\dashboard_html.py.pre_dl2_20260920_132815.bak)
   ═══════════════════════════════════════════════════════════════════════════ */
:root{
  /* — ink ramp: every text step ≥ 4.5:1 on --bg AND on --card ---------- */
  --ink-1:#F5F8FC;  --ink-2:#C9D3E0;  --ink-3:#A2ADBC;  --ink-4:#7C8797;
  /* contrast repair: --faint (3.97:1) and --copper-deep (4.07:1) were
     carrying text; they now resolve to accessible steps, and the deep
     copper is reserved for hairlines/icons only. */
  --faint:#7C8797;  --muted:#A2ADBC;  --copper-deep:#9A7748;  --copper-txt:#EDD6B4;

  /* — 9-step type scale (replaces 24 ad-hoc sizes) --------------------- */
  --t-meta:12px; --t-label:12.5px; --t-body:13.5px; --t-body-lg:15px;
  --t-h4:17px;   --t-h3:20px;      --t-h2:24px;     --t-h1:32px; --t-display:40px;
  --lh-fa:1.8;   --lh-tight:1.35;

  /* — spacing (4px grid) · radius · motion ---------------------------- */
  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:20px; --s6:24px; --s7:32px; --s8:40px;
  --r1:10px; --r2:14px;
  --state-hover:rgba(255,255,255,.07);
  --state-active:rgba(198,154,107,.16);
  --dur-fast:120ms; --dur:220ms; --dur-slow:400ms; --ease-out:cubic-bezier(.16,1,.3,1);
  --measure:68ch;
  --shadow-1:0 1px 2px rgba(0,0,0,.35);
  --shadow-2:0 8px 24px -8px rgba(0,0,0,.55);
  --shadow-3:0 20px 48px -12px rgba(0,0,0,.7);
}

/* ── base readable body: Persian needs more leading + optical size ────── */
body{ color:var(--ink-2); line-height:var(--lh-fa); }
html, body{ font-size:15px; }
p, li{ line-height:var(--lh-fa); text-wrap:pretty; }
:is(h1,h2,h3,h4,h5){ line-height:var(--lh-tight); letter-spacing:-.01em; text-wrap:balance; }
.ltr, .num{ direction:ltr; unicode-bidi:isolate; font-variant-numeric:tabular-nums; }
::selection{ background:rgba(198,154,107,.32); color:#fff; }

/* ── readability floor: nothing under 12px, hints + meta get real air ── */
.panelbox .hint, .hint{ font-size:var(--t-label); line-height:1.95; color:var(--ink-3); }
.chip .n{ font-size:12px; opacity:.9; }
.badge{ font-size:12px; }
.ncard .ttl{ font-size:15.5px; line-height:1.75; letter-spacing:0; }
.ncard .summ{
  font-size:var(--t-body); line-height:1.85; color:var(--ink-3);
  display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;
}
.ncard .row2, .ncard .dt, .ncard .src, .ncard .ttl-en{ font-size:12.5px; }
.ncard .ttl-en{ color:var(--ink-4); line-height:1.6; }
.setrow .hint, .setrow .lbl + .hint{ font-size:var(--t-label); line-height:1.9; }

/* ── reading experience of the report (this tab is the product) ──────── */
.rep-doc p{ max-inline-size:var(--measure); line-height:1.9; font-size:15px; }
.rep-doc p + p{ margin-top:14px; }
.rep-doc h3, .rep-doc h4{ margin-top:26px; }
.panel-sub{ font-size:var(--t-label); font-weight:400; color:var(--ink-3); }

/* ── unified interaction states (was: 5 different opacities) ─────────── */
button, a, select, input, [role="button"]{ transition:background var(--dur-fast) var(--ease-out), color var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out); }
.btn{ border-radius:var(--r1); }
.btn:not(.ghost):hover{ background:var(--copper-hi); color:#12101A; }
.btn.ghost:hover{ background:var(--state-hover); border-color:var(--copper-line); color:var(--ink-1); }
.btn:active{ transform:translateY(1px); }
button:disabled{ opacity:.5; cursor:not-allowed; }
.chip:hover{ background:var(--state-hover); }
.chip.on{ background:var(--state-active); border-color:var(--copper); color:var(--ink-1); }
.ncard{ box-shadow:var(--shadow-1); border-radius:var(--r2); }
.ncard:hover{ box-shadow:var(--shadow-2); border-color:rgba(198,154,107,.34); }
.panelbox, .chartbox, .rep-doc{ border-radius:var(--r2); box-shadow:var(--shadow-1); }

/* ── keyboard: one visible focus ring for every control ──────────────── */
:is(button, a[href], input, select, textarea, [tabindex], [role="tab"]):focus-visible{
  outline:2px solid var(--copper-hi);
  outline-offset:2px;
  border-radius:var(--r1);
  box-shadow:0 0 0 4px rgba(198,154,107,.22);
}
/* sticky chrome must never hide the focused element (WCAG 2.2 SC 2.4.11) */
:root{ scroll-padding-block-start:96px; }

/* ── translucent surfaces need an opaque fallback ────────────────────── */
@media (prefers-reduced-transparency: reduce){
  :is(.app-topbar, .topbar-bg, .chips-console, .cal-control-panel, .live-pill, .modal){
    background:var(--surface-2) !important; backdrop-filter:none !important;
  }
}
@media (prefers-reduced-motion: reduce){
  .flash-up, .flash-dn, .skeleton, .newdot{ animation:none !important; }
}

/* ══ NEW COMPONENT PRIMITIVES — inert until markup uses them (phase 2) ══ */
/* nav rail groups */
.rail-group{ display:flex; flex-direction:column; gap:2px; margin-block-end:14px; }
.rail-group-label{
  font-size:11.5px; font-weight:700; letter-spacing:.04em; color:var(--copper-deep);
  padding-inline:12px; margin-block-end:6px; text-transform:uppercase;
}
.tab[aria-selected="true"]{ background:var(--state-active); }

/* lead story row above the feed */
.lead-row{ display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:var(--s4); margin-block-end:var(--s5); }
.lead-card{ position:relative; border-radius:var(--r2); overflow:hidden; border:1px solid var(--border); background:var(--card); min-block-size:190px; }
.lead-card .lead-ttl{ font-size:var(--t-h3); line-height:1.55; font-weight:800; }
.lead-card .body{ padding:var(--s5); display:flex; flex-direction:column; gap:var(--s2); }

/* sticky filter bar */
.sticky-filterbar{ position:sticky; inset-block-start:64px; z-index:30; backdrop-filter:var(--glass-blur); background:var(--surface-glass); border-block-end:1px solid var(--border); }

/* credibility as a rail instead of a numeric chip */
.cred-rail{ position:absolute; inset-inline-end:0; inset-block:0; inline-size:3px; background:var(--copper-deep); }
.cred-rail.hi{ background:var(--green); } .cred-rail.lo{ background:var(--red); }

/* freshness + loading */
.newdot{ inline-size:7px; block-size:7px; border-radius:50%; background:var(--copper); box-shadow:0 0 0 0 var(--copper-glow); animation:pulse 2.4s var(--ease-out) infinite; }
@keyframes pulse{ 0%{ box-shadow:0 0 0 0 rgba(198,154,107,.45);} 70%{ box-shadow:0 0 0 9px rgba(198,154,107,0);} 100%{ box-shadow:0 0 0 0 rgba(198,154,107,0);} }
.skeleton{ background:linear-gradient(100deg, var(--surface-2) 30%, var(--surface-3) 50%, var(--surface-2) 70%); background-size:220% 100%; animation:shimmer 1.4s linear infinite; border-radius:var(--r1); }
@keyframes shimmer{ from{ background-position:180% 0; } to{ background-position:-40% 0; } }

/* language segmented control (EN | فا) */
.langseg{ display:inline-flex; border:1px solid var(--border); border-radius:var(--radius-pill); overflow:hidden; }
.langseg button{ padding:5px 14px; font-size:var(--t-label); background:transparent; border:0; color:var(--ink-3); }
.langseg button.on{ background:var(--state-active); color:var(--ink-1); }

/* two-line citation list (replaces the crowded sources box) */
.src-two-line{ display:flex; flex-direction:column; gap:6px; }
.src-two-line .row{ display:flex; align-items:baseline; gap:8px; font-size:12.5px; line-height:1.9; }
.src-two-line .src-name{ color:var(--copper-txt); font-weight:600; }
.src-two-line .src-meta{ color:var(--ink-4); font-variant-numeric:tabular-nums; }

/* touch targets: comfortable without breaking compact rows */
.btn, .chip, .cal-seg-btn, .nav-item{ min-block-size:34px; }
@media (pointer:coarse){ .btn, .chip, .mclose, .star-btn{ min-block-size:44px; min-inline-size:44px; } }

/* mobile: horizontal sticky tab bar instead of the long rail */
@media (max-width:760px){
  .app-sidebar{ border-radius:0; }
  .rail-group-label{ display:none; }
  .ncard .summ{ -webkit-line-clamp:2; }
  .rep-doc p{ font-size:14.5px; line-height:1.85; }
}
/* ══ end DL2 phase 1 ══ */

/* ── DL2 phase 2 · price ticker · lead stories · feed density ───────────── */
.dl2-ticker{
  position:relative; z-index:25; display:flex; gap:20px; align-items:center;
  block-size:34px; padding-inline:20px; overflow-x:auto; overflow-y:hidden; white-space:nowrap;
  background:linear-gradient(90deg, rgba(198,154,107,.10), rgba(198,154,107,.02) 45%, rgba(198,154,107,.10));
  border-block-end:1px solid var(--hairline);
  scrollbar-width:none;
}
.dl2-ticker::-webkit-scrollbar{ height:0; }
.dl2-ticker .tk{ display:inline-flex; align-items:center; gap:7px; font-size:12.5px; font-variant-numeric:tabular-nums; }
.dl2-ticker .tk .s{ color:var(--copper-txt); font-weight:700; letter-spacing:.02em; }
.dl2-ticker .tk .p{ color:var(--ink-1); font-weight:900; }
.dl2-ticker .tk .c{ font-weight:700; }
.dl2-ticker .tk.up .c{ color:var(--green); }
.dl2-ticker .tk.dn .c{ color:var(--red); }
.dl2-ticker .tk .st{ color:var(--copper-deep); font-size:11px; }
.dl2-ticker .sep{ color:var(--copper-deep); }

/* sticky filter console (was scrolling away with the feed) */
.chips-console{
  position:sticky; inset-block-start:0; z-index:30;
  background:var(--surface-glass); backdrop-filter:var(--glass-blur);
  border-block-end:1px solid var(--border);
}
/* lead stories sit above the grid without adding a second title row */
.lead-row + .ngrid{ margin-block-start:var(--s1); }
.lead-card{ cursor:pointer; }
.lead-card:hover{ border-color:rgba(198,154,107,.36); box-shadow:var(--shadow-2); }
.lead-card .lead-rail{ position:absolute; inset-inline-end:0; inset-block:0; inline-size:3px;
  background:linear-gradient(180deg, var(--copper-hi), var(--copper-deep)); }
.lead-card .row1{ display:flex; gap:6px; flex-wrap:wrap; }
.lead-card .summ{ color:var(--ink-3); font-size:var(--t-body); line-height:1.85; }
.lead-card .row2{ display:flex; gap:10px; align-items:center; margin-block-start:auto;
  padding-block-start:10px; border-block-start:1px solid var(--glass-line); font-size:12.5px; color:var(--ink-4); }

/* feed density */
.ncard .blurb-btn{ display:none; }          /* action lives in the article modal */
.ncard .row1 .badge{ font-size:11.5px; }
.ncard .badge.more{ border-style:dashed; color:var(--ink-4); }

/* ── DL2 phase 3 · report reading surface + chart panel (CSS only) ──────── */
.rep-layout{ align-items:start; gap:var(--s5); }
/* the chart/analysis column follows the reader instead of scrolling away */
.rep-layout > .chartbox, .rep-layout > .pane, .rep-layout > aside, .rep-doc ~ .chartbox{
  position:sticky; inset-block-start:78px;
}
@media (max-width:1080px){
  .rep-layout > *{ position:static; }
}
.rep-doc{
  padding:var(--s6) var(--s7);
  background:linear-gradient(180deg, rgba(255,255,255,.022), transparent 240px), var(--card);
}
.rep-doc h3{
  font-size:var(--t-h3); color:var(--copper-txt);
  border-block-end:1px solid var(--hairline); padding-block-end:8px; margin-block-start:var(--s7);
}
.rep-doc h4{ font-size:var(--t-h4); color:var(--ink-1); }
.rep-doc :is(strong,b){ color:var(--ink-1); font-weight:600; }

/* sources per section: a calm, scannable two-line list inside a disclosure */
.rep-doc .cites{
  margin-block-start:var(--s4); border:1px solid var(--border); border-radius:var(--r1);
  background:rgba(255,255,255,.02); overflow:hidden;
}
.rep-doc .cites-toggle{
  inline-size:100%; display:flex; align-items:center; gap:8px; padding:10px 14px;
  font-size:12.5px; color:var(--copper-txt); background:transparent; border:0;
  cursor:pointer; text-align:start;
}
.rep-doc .cites-toggle:hover{ background:var(--state-hover); }
.rep-doc .cites-body{ padding:2px 14px 12px; }
.rep-doc .cite{
  display:block; padding-block:9px; border-block-start:1px dashed var(--line);
  font-size:12.5px; line-height:1.95; color:var(--ink-3);
}
.rep-doc .cite:first-child{ border-block-start:0; }
.rep-doc .cite a{ color:var(--copper-txt); }

/* chart panel: tighter chrome, legible footer notes */
.chartbox{ padding:var(--s4) var(--s5); }
.chart-head{
  display:flex; align-items:center; gap:10px; flex-wrap:wrap;
  border-block-end:1px solid var(--border); padding-block-end:10px; margin-block-end:10px;
}
.chart-head h3{ font-size:var(--t-h4); margin:0; }
.chart-live{
  font-size:12px; padding:3px 10px; border:1px solid var(--green-line);
  border-radius:var(--radius-pill); background:var(--green-bg); color:var(--green);
  font-variant-numeric:tabular-nums;
}
.chart-notes{ font-size:12.5px; line-height:1.95; color:var(--ink-3); }
.rep-actions{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; }

/* printing a report should give paper, not chrome */
@media print{
  .app-sidebar, .app-topbar, .dl2-ticker, .chips-console, .rep-grid, .overlay{ display:none !important; }
  .rep-doc p{ max-inline-size:none; }
  .rep-doc{ box-shadow:none; border:0; }
}

/* ── DL2 phase 4 · nav rail · calendar · ETF/F&G · tables · settings ───── */

/* nav rail: consistent rhythm, active indicator, calmer icons */
.nav-item{ position:relative; border-radius:var(--r1); }
.nav-item .nav-icon{ inline-size:24px; text-align:center; font-size:15px; line-height:1; }
.nav-item .nav-text{ font-size:var(--t-body); }
.nav-item[aria-selected="true"]::before{
  content:""; position:absolute; inset-inline-start:0; inset-block:9px;
  inline-size:3px; border-radius:3px;
  background:linear-gradient(180deg, var(--copper-hi), var(--copper-deep));
}
.nav-item .cnt{ font-size:11.5px; font-variant-numeric:tabular-nums; }
.sidebar-section-label{ font-size:11.5px; letter-spacing:.05em; color:var(--copper-deep); }

/* calendar: readable time column + countdown that does not dance */
.cal-grid{ gap:var(--s4); align-items:start; }
#calCountdown{ font-size:var(--t-h3); font-variant-numeric:tabular-nums; letter-spacing:-.01em; }
.cal-timer, .sg{ font-variant-numeric:tabular-nums; }
.calday{ border-radius:var(--r2); }
.cal-tabs-row, .cal-filters-row{ gap:var(--s3); flex-wrap:wrap; }
.cal-label{ font-size:12px; color:var(--ink-4); }
#calSummary, #archSummary, #bmarkSummary{ font-size:12px; color:var(--ink-4); }
#sessionsBox{ font-size:12.5px; line-height:1.95; }
#calReleased{ font-size:12.5px; }

/* ETF / F&G: quote tiles become KPI cards, gauge gets breathing room */
#etfLive2.etfgrid, .etfgrid{
  display:grid; grid-template-columns:repeat(auto-fill, minmax(148px, 1fr)); gap:10px;
}
.etfgrid > *{ border:1px solid var(--border); border-radius:var(--r1); padding:10px 12px; background:rgba(255,255,255,.02); }
#fngPage{ padding-block:var(--s4); }
#fngPage .fng-val, #fngPage b{ font-variant-numeric:tabular-nums; }
#etfBox2{ font-size:12.5px; }

/* tables & grids: same gutter everywhere, no crammed rows */
#archGrid.grid, #archGrid, #bmarkGrid, #repChips, .rep-grid{ gap:var(--s4); }
table{ border-collapse:separate; border-spacing:0; }
th{ font-size:12px; color:var(--ink-4); text-transform:none; }
td{ font-size:12.5px; }
td, th{ padding-block:9px; border-block-end:1px solid var(--line); }
tbody tr:hover{ background:rgba(255,255,255,.025); }
.spark, .spark svg{ display:block; }

/* forms: comfortable controls, one focus language */
select, input[type="text"], input[type="password"], input[type="number"], textarea{
  min-block-size:36px; border-radius:var(--r1);
  background:rgba(255,255,255,.04); border:1px solid var(--border); color:var(--ink-1);
  padding-inline:10px;
}
select:hover, input[type="text"]:hover{ border-color:var(--border-strong); }
.switch .slider{ border-radius:var(--radius-pill); }
.switch input:focus-visible + .slider{ box-shadow:0 0 0 4px rgba(198,154,107,.22); }

/* settings: label + control on one line, description under the label */
.setrow{
  display:grid; grid-template-columns:minmax(0,1fr) auto; gap:var(--s4);
  align-items:center; padding-block:14px; border-block-end:1px solid var(--line);
}
.setrow .lbl{ font-size:var(--t-body-lg); font-weight:600; color:var(--ink-1); }
.setrow select[style]{ width:auto !important; min-inline-size:150px; }
.asset-toggles{ display:flex; flex-wrap:wrap; gap:6px; }

/* empty states + hints share one voice */
.empty{ font-size:13px; line-height:1.95; color:var(--ink-3); }

/* ── DL2 phase 5b · image layout stability + mobile rail ──────────────── */
.ncard .thumb{ aspect-ratio:16/9; }
.ncard .thumb img{ inline-size:100%; block-size:100%; object-fit:cover; }
.lead-card .thumb{ aspect-ratio:21/9; }
.lead-card .body{ min-block-size:0; }
@media (max-width:760px){
  .app-sidebar{ max-block-size:70vh; overflow-y:auto; }
  .dl2-ticker{ block-size:32px; gap:14px; }
  .ncard .thumb{ aspect-ratio:2/1; }
}
@media (prefers-reduced-motion: reduce){
  .ncard .thumb img, .ncard:hover .thumb img{ transform:none; transition:none; }
/* ── DL2 step 1 · skeleton cards + freshness markers ─────────────────────── */
.skcard{ block-size:200px; border:1px solid var(--border); border-radius:var(--r2); }
.ncard .ttl .newdot{ margin-inline-end:6px; }
.ncard .ttl .newdot.newdot-inline{
  display:inline-block; vertical-align:middle; margin-block-end:2px;
}
#feedNewBadge{
  display:inline-flex; align-items:center; gap:6px; margin-inline-start:8px;
  font-size:12px; color:var(--copper-txt);
}
@media (prefers-reduced-motion: reduce){
  #feedNewBadge .newdot{ animation:none; }
}
/* ── DL2 step 4 · CSS duplication map (measured, not guessed) ─────────────
   This stylesheet defines 83 selectors in more than one place. Worst offenders
   measured on 2026-09-20: `.btn.ghost:hover` ×4; `.chip.on` ×4; and ×3 each for
   `.nav-item`, `.btn`, `.btn.ghost`, `.chip`, `.chip:hover`, `.ncard`,
   `.ncard:hover`, `.ncard .thumb img`, `.ncard .ttl`, `.rep-doc p`,
   `.sidebar-section-label`.
   Cascade rule: the LAST block wins on conflicting properties, earlier blocks
   still contribute theirs — which is why an edit in the wrong copy silently
   does nothing. Until the physical merge lands, ALWAYS edit the last
   occurrence of a selector, and prefer adding to the DL2 layers below.
   ───────────────────────────────────────────────────────────────────────── */


}

/* ── DL2 phase 5 · rail groups · collapsed rail · mobile · view motion ─── */
.rail-group + .rail-group{
  margin-block-start:6px; padding-block-start:10px; border-block-start:1px solid var(--line);
}
.dl2-rail-toggle{
  margin-block-start:auto; align-self:flex-start;
  inline-size:34px; block-size:34px; display:grid; place-items:center;
  border:1px solid var(--border); border-radius:var(--r1); background:transparent;
  color:var(--copper); font-size:15px; cursor:pointer;
}
.dl2-rail-toggle:hover{ background:var(--state-hover); border-color:var(--copper-line); color:var(--ink-1); }

/* collapsed rail: icon-only 64px, labels out of the way */
body.dl2-rail-collapsed .app-sidebar{ inline-size:64px; padding-inline:8px; }
body.dl2-rail-collapsed .app-sidebar .nav-text,
body.dl2-rail-collapsed .app-sidebar .cnt,
body.dl2-rail-collapsed .app-sidebar .rail-group-label,
body.dl2-rail-collapsed .app-sidebar > .sidebar-section-label{ display:none; }
body.dl2-rail-collapsed .app-sidebar .nav-item{ justify-content:center; padding-inline:0; }
body.dl2-rail-collapsed .app-sidebar .nav-icon{ inline-size:auto; }
body.dl2-rail-collapsed .app-sidebar .rail-group + .rail-group{ margin-block-start:2px; padding-block-start:6px; }

/* view switch: one quiet motion, never a jump */
.view.active{ animation:dl2Fade var(--dur) var(--ease-out) both; }
@keyframes dl2Fade{ from{ opacity:0; transform:translateY(6px); } to{ opacity:1; transform:none; } }

/* mobile: bigger targets, rail never eats the screen */
@media (max-width:760px){
  .app-sidebar{ padding-block-end:14px; }
  .nav-item{ min-block-size:44px; }
  .dl2-rail-toggle{ display:none; }
}
@media (prefers-reduced-motion: reduce){
  .view.active{ animation:none; }
}

</style>
<script>
/* Entrance arm — runs synchronously so there is no flash of unanimated
   content. Reduced motion skips it entirely and the finished design paints. */
try {
  if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.documentElement.classList.add('anim');
  }
} catch (e) {
  document.documentElement.classList.add('anim');
}
</script>
</head>
<body>

<!-- ══ AMBIENT STAGE (lit backdrop, never animated away) ══ -->
<div class="stage" aria-hidden="true"></div>

<div class="app-shell">

  <!-- ══ INSTITUTIONAL TOPBAR ══ -->
  <header class="app-topbar">
    <div class="brand-group">
      <button class="menu-toggle-btn" id="btnMenu" onclick="toggleSidebar()" aria-label="منوی ناوبری">
        ☰
      </button>
      <div class="brand-badge">⚡</div>
      <div class="brand-title-wrap">
        <div class="brand-title-row">
          <h1>MOHMD NEWS</h1>
          <span class="live-pill">
            <span class="dot" id="cycleDot"></span>
            <span id="cycleTxt">LIVE</span>
          </span>
        </div>
        <div class="brand-desc">Market Intelligence Command Center</div>
      </div>
    </div>

    <!-- Telemetry capsule -->
    <div class="topbar-telemetry" id="cyclePill">
      <div class="telem-item" title="بازه زمانی نگهداری اخبار">
        <span>پنجره:</span><b id="ruleAge">24</b><span>h</span>
      </div>
      <div class="telem-divider"></div>
      <div class="telem-item">
        <span>پایش بعدی:</span><b id="nextIn">—</b>
      </div>
      <div class="telem-divider"></div>
      <div class="telem-item">
        <span>آخرین همگام‌سازی:</span><b id="lastUpd">—</b>
      </div>
    </div>

    <div class="topbar-actions">
      <button class="btn" id="refreshBtn" onclick="doRefresh()">
        <span>⟳</span> بروزرسانی
      </button>
    </div>
  </header>
  <div class="dl2-ticker" id="tickerBar" role="status" aria-live="off" aria-label="قیمت لحظه‌ای دارایی‌ها"></div>

  <!-- ══ APP BODY CONTAINER (Sidebar on RIGHT, Main on LEFT in RTL) ══ -->
  <div class="app-body">

    <!-- ══ RIGHT NAVIGATION SIDEBAR (First flex item = Far Right in RTL) ══ -->
    <aside class="app-sidebar" id="appSidebar" role="tablist" aria-label="ناوبری داشبورد" aria-orientation="vertical">
      <div class="sidebar-section-label">مانیتورینگ بازار</div>
      <button class="tab nav-item active" role="tab" aria-selected="true" data-view="feed" onclick="showView('feed')">
        <span class="nav-icon">📰</span>
        <span class="nav-text">جریان زنده اخبار</span>
        <span class="cnt" id="cntFeed">۰</span>
      </button>
      <button class="tab nav-item" role="tab" aria-selected="false" data-view="reports" onclick="showView('reports')">
        <span class="nav-icon">📊</span>
        <span class="nav-text">تحلیل و گزارش‌ها</span>
      </button>
      <button class="tab nav-item" role="tab" aria-selected="false" data-view="calendar" onclick="showView('calendar')">
        <span class="nav-icon">📅</span>
        <span class="nav-text">تقویم اقتصادی</span>
        <span class="cnt" id="cntEvents" style="display:none">۰</span>
      </button>
      <button class="tab nav-item" role="tab" aria-selected="false" data-view="fng" onclick="showView('fng')">
        <span class="nav-icon">😱</span>
        <span class="nav-text">شاخص ترس و طمع</span>
      </button>
      <button class="tab nav-item" role="tab" aria-selected="false" data-view="etf" onclick="showView('etf')">
        <span class="nav-icon">🏛</span>
        <span class="nav-text">جریان‌های ETF</span>
      </button>
      <button class="tab nav-item" role="tab" aria-selected="false" data-view="archive" onclick="showView('archive')">
        <span class="nav-icon">🗄</span>
        <span class="nav-text">آرشیو هوشمند</span>
        <span class="cnt" id="cntArchive" style="display:none">۰</span>
      </button>

      <button class="tab nav-item" role="tab" aria-selected="false" data-view="bookmarks" onclick="showView('bookmarks')">
        <span class="nav-icon">⭐</span>
        <span class="nav-text">نشان‌شده‌ها</span>
        <span class="cnt" id="cntBmarks" style="display:none">۰</span>
      </button>

      <div class="sidebar-section-label">سیستم و سلامت</div>
      <button class="tab nav-item" role="tab" aria-selected="false" data-view="monitor" onclick="showView('monitor')">
        <span class="nav-icon">🩺</span>
        <span class="nav-text">سلامت منابع</span>
        <span class="cnt" id="cntBroken" style="display:none">۰</span>
      </button>
      <button class="tab nav-item" role="tab" aria-selected="false" data-view="alerts" onclick="showView('alerts')">
        <span class="nav-icon">📨</span>
        <span class="nav-text">پیام‌رسان تلگرام</span>
      </button>

      <div class="sidebar-footer">
        <div class="sidebar-section-label">مدیریت و پیکربندی</div>
        <button class="tab nav-item" id="ibSettings" role="tab" aria-selected="false" data-view="settings" onclick="showView('settings')">
          <span class="nav-icon">⚙️</span>
          <span class="nav-text">تنظیمات داشبورد</span>
        </button>
        <button class="tab nav-item" id="ibSources" role="tab" aria-selected="false" data-view="sources" onclick="showView('sources')">
          <span class="nav-icon">📡</span>
          <span class="nav-text">مدیریت منابع خبری</span>
          <span class="cnt" id="cntSrc">۰</span>
        </button>
        <button class="tab nav-item" id="ibAssets" role="tab" aria-selected="false" data-view="assets" onclick="showView('assets')">
          <span class="nav-icon">💹</span>
          <span class="nav-text">مدیریت دارایی‌ها</span>
        </button>
      </div>
    </aside>

    <!-- ══ MAIN SCROLLABLE CONTENT (Second flex item = Left of Sidebar in RTL) ══ -->
    <main class="app-main">

      <!-- Assets Ticker Strip -->
      <div class="assets" id="assetsStrip"></div>

      <!-- Views Container -->
      <div class="view-container">

        <!-- ══ 1. FEED VIEW ══ -->
        <section class="view active" id="view-feed">
          <!-- Level 1: Command Search Bar -->
          <div class="feed-header-toolbar">
            <div class="search-box-wrap">
              <span class="search-glass-icon">🔍</span>
              <label class="visually-hidden" for="q" style="position:absolute;width:1px;height:1px;overflow:hidden">جستجو</label>
              <input type="text" id="q" placeholder="جستجوی پیشرفته در تیترها، خلاصه‌ها و منابع خبری..." oninput="renderFeed()">
              <span class="search-kbd-hint">ESC پاکسازی</span>
            </div>
            <div class="feed-meta-badge">
              <span class="badge-dot"></span>
              <span>تعداد خبر:</span>
              <b id="feedCount" role="status">—</b>
            </div>
          </div>

          <!-- Level 2: Control Console -->
          <div class="feed-control-console">
            <div class="console-item">
              <span class="console-label">ترتیب:</span>
              <select id="sortSel" onchange="renderFeed()" aria-label="ترتیب نمایش">
                <option value="new" selected>🕒 جدیدترین اخبار (پیش‌فرض)</option>
                <option value="cred">⭐ بیشترین اعتبار نهادی</option>
                <option value="src">🏛 بر اساس نام منبع</option>
              </select>
            </div>
            <div class="console-item">
              <span class="console-label">دسته:</span>
              <select id="kindSel" onchange="renderFeed()" aria-label="دسته منبع"></select>
            </div>
            <div class="console-item">
              <span class="console-label">منبع:</span>
              <select id="srcSel" onchange="renderFeed()" aria-label="منبع خبری"></select>
            </div>
            <div class="console-slider-item">
              <div class="slider-info">
                <span class="console-label">حداقل اعتبار:</span>
                <span class="cred-pill" id="credVal">0%</span>
              </div>
              <input type="range" id="credSlider" min="0" max="90" step="5" value="0" aria-label="حداقل اعتبار"
                     oninput="document.getElementById('credVal').textContent=this.value+'%';renderFeed()">
            </div>
          </div>

          <!-- Level 3: Dual Category & Asset Filter Lanes -->
          <div class="chips-console">
            <div class="chips-lane">
              <button class="lane-tag" onclick="UI.asset='all';UI.onlyBookmarked=false;renderChips();renderFeed()" title="نمایش همه دارایی‌ها (پاک کردن فیلتر)" aria-label="نمایش همه دارایی‌ها"><span>🪙</span> دارایی‌ها</button>
              <div class="lane-chips" id="assetChips"></div>
            </div>
            <div class="chips-lane">
              <button class="lane-tag" onclick="UI.topic='all';UI.onlyBookmarked=false;renderChips();renderFeed()" title="نمایش همه موضوعات (پاک کردن فیلتر)" aria-label="نمایش همه موضوعات"><span>🏷️</span> موضوعات</button>
              <div class="lane-chips" id="topicChips"></div>
            </div>
          </div>

          <div class="lead-row" id="leadRow"></div>
          <div class="ngrid" id="newsGrid"></div>
          <div class="empty" id="feedEmpty" style="display:none">خبری با این فیلترها یافت نشد.</div>
        </section>

        <!-- ══ 2. REPORTS VIEW ══ -->
        <section class="view" id="view-reports">
          <div class="rep-grid" id="repChips"></div>
          <div id="repBox"><div class="empty">یکی از دارایی‌ها را انتخاب کنید تا گزارش تحلیلی و نمودار آن ساخته شود.</div></div>
        </section>

        <!-- ══ 3. CALENDAR VIEW (REDESIGNED INSTITUTIONAL TOOLBAR & FILTERS) ══ -->
        <section class="view" id="view-calendar">
          <div class="cal-grid">
            <div class="panelbox calcol">
              <h3>📅 Economic Calendar <span id="calSummary" style="font-size:11px;color:var(--muted);direction:ltr">…</span></h3>
              <div class="cal-countdown" id="calCountdown" role="status" aria-live="polite">—</div>
              <div id="calReleased" class="cal-released" style="display:none"></div>

              <!-- High-end Dark Calendar Control Panel -->
              <div class="cal-control-panel">
                <!-- Row 1: Week Selector Tabs -->
                <div class="cal-tabs-row">
                  <!-- primary control: one day at a time -->
                  <div class="cal-daynav">
                    <button class="btn ghost sm" id="calDayPrev" onclick="shiftCalDay(-1)" aria-label="Previous day">‹ Prev day</button>
                    <span class="cal-daynow" id="calDayNow" role="status">—</span>
                    <button class="btn ghost sm" id="calDayNext" onclick="shiftCalDay(1)" aria-label="Next day">Next day ›</button>
                    <button class="cal-seg-btn btn sm ghost" id="calBtnToday" onclick="gotoCalToday()">Today</button>
                  </div>
                  <!-- week-level jumps, parked on the far left -->
                  <div class="cal-segmented-control cal-weeknav">
                    <button class="cal-seg-btn btn sm ghost" id="calBtnPrevW" onclick="shiftCalDay(-7)">‹ Prev week</button>
                    <button class="cal-seg-btn btn sm ghost" id="calBtnNextW" onclick="shiftCalDay(7)">Next week ›</button>
                  </div>
                </div>

                <!-- Row 2: Filters (Impact, Country, Sort, Hide Past) -->
                <div class="cal-filters-row">
                  <div class="cal-filter-group">
                    <label class="cal-label">Impact</label>
                    <select id="calImpact" onchange="renderCalendar()" aria-label="Minimum impact">
                      <option value="all">All impact levels</option>
                      <option value="High">🔴 High impact only</option>
                      <option value="Medium">🟡 Medium &amp; above</option>
                      <option value="Low">⚪ Low &amp; above</option>
                    </select>
                  </div>

                  <div class="cal-filter-group">
                    <label class="cal-label">Currency</label>
                    <select id="calCountry" onchange="renderCalendar()" aria-label="Currency"></select>
                  </div>

                  <div class="cal-filter-group">
                    <label class="cal-label">Order</label>
                    <select id="calSort" onchange="renderCalendar()" aria-label="Sort order">
                      <option value="ff">🕒 Chronological</option>
                      <option value="impact">⭐ Impact, then time</option>
                      <option value="time">⏱ Newest first</option>
                    </select>
                  </div>

                  <label class="cal-hide-past-toggle">
                    <input type="checkbox" id="calHidePast" onchange="renderCalendar()">
                    <span>Hide past events</span>
                  </label>
                </div>
              </div>

              <div id="calDays"></div>
            </div>

            <div class="calside">
              <div class="panelbox">
                <h3>🕐 Market Sessions</h3>
                <div id="sessionsBox" class="hint">…</div>
              </div>
            </div>
          </div>
        </section>

        <!-- ══ 4. FEAR & GREED VIEW ══ -->
        <section class="view" id="view-fng">
          <div class="panelbox">
            <h3>😱 Fear &amp; Greed Index <span class="hint">— شاخص ترس و طمع بازار کریپتو · منبع: alternative.me</span></h3>
            <div id="fngPage" class="fng-page">…</div>
          </div>
        </section>

        <!-- ══ 5. ETF FLOWS VIEW ══ -->
        <section class="view" id="view-etf">
          <div class="cal-grid">
            <div class="panelbox">
              <h3>🏛 Spot Bitcoin ETF Flows <span style="font-weight:400;font-size:10px;color:var(--muted)">$M daily · Farside</span></h3>
              <div id="etfBox2" class="hint">…</div>
            </div>
            <div class="calside">
              <div class="panelbox">
                <h3>📈 Live ETF Quotes <span style="font-weight:400;font-size:10px;color:var(--muted)">Yahoo · ۶۰s</span></h3>
                <div id="etfLive2" class="etfgrid"><span class="fs-spin">…</span></div>
              </div>
              <div class="panelbox" style="margin-top:12px">
                <h3>💡 TradingView Ideas</h3>
                <div id="ideasBox" class="hint">…</div>
              </div>
            </div>
          </div>
        </section>

        <!-- ══ 6. ARCHIVE VIEW ══ -->
        <section class="view" id="view-archive">
          <div class="panelbox">
            <h3>🗄 Archive <span id="archSummary" style="font-size:11px;color:var(--muted)">…</span></h3>
            <div id="archGrid" class="grid"></div>
            <div class="empty" id="archEmpty" style="display:none">آرشیو خالی است — با گذر زمان خبرهای قدیمی‌تر از پنجرهٔ فعال اینجا می‌آیند.</div>
          </div>
        </section>

        <!-- ══ 6b. BOOKMARKS VIEW ══ -->
        <section class="view" id="view-bookmarks">
          <div class="panelbox">
            <h3>⭐ Bookmarks <span id="bmarkSummary" style="font-size:11px;color:var(--muted)">…</span>
              <button class="btn ghost sm" style="margin-inline-start:auto" onclick="clearBookmarks()">Clear all</button></h3>
            <div id="bmarkGrid" class="ngrid"></div>
            <div class="empty" id="bmarkEmpty" style="display:none">No bookmarks yet — tap ☆ on any news card to save it here.</div>
          </div>
        </section>

        <!-- ══ 7. SOURCE MONITOR VIEW ══ -->
        <section class="view" id="view-monitor">
          <div class="panelbox">
            <h3>🩺 Source Health — <span id="monSummary" style="font-size:12px;color:var(--muted)">…</span>
              <button class="btn" id="recoverBtn" style="margin-inline-start:auto" onclick="recoverAll()">🔧 Recover all broken feeds</button></h3>
            <div class="hint" style="font-size:11px;color:var(--muted);margin-bottom:12px;line-height:2">
              این پنل وضعیت اتصال به تمامی فیدهای خبری و تلاش‌های بازیابی خودکار را به زبان فارسی نمایش می‌دهد.
            </div>
            <div id="monList"></div>
          </div>
        </section>

        <!-- ══ 8. TELEGRAM DIGEST VIEW ══ -->
        <section class="view" id="view-alerts">
          <div class="panelbox">
            <h3>📨 Telegram Digest <span class="hint">— خلاصه خودکار معتبرترین خبرها بعد از هر چرخه</span>
              <button class="btn sm" style="margin-inline-start:auto" onclick="sendNowTelegram()">🚀 ارسال خلاصه الآن</button></h3>
            <div class="formgrid">
              <div style="grid-column:1/-1"><label>Bot token (از BotFather)</label>
                <input type="password" id="tgToken" placeholder="123456:ABC-DEF..." style="direction:ltr;text-align:left"></div>
              <div><label>Chat ID</label>
                <input type="text" id="tgChat" placeholder="-1001234..." style="direction:ltr;text-align:left"></div>
              <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end">
                <button class="btn" onclick="saveTelegram()">ذخیره همه تنظیمات</button>
                <button class="btn ghost" onclick="testTelegram()">ارسال پیام تست</button>
              </div>
            </div>
            <h4 style="margin:16px 0 6px">⚙️ تنظیمات ارسال</h4>
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
            <h4 style="margin:16px 0 6px">🎛 رفتار پیام</h4>
            <div class="tg-toggles">
              <label class="tgopt"><input type="checkbox" id="tgQuiet" checked><span>🌙 سکوت شبانه (۲۳ تا ۸ صبح ارسال نشود)</span></label>
              <label class="tgopt"><input type="checkbox" id="tgLink" checked><span>🔗 تیتر به‌صورت هایپرلینک به خبر</span></label>
              <label class="tgopt"><input type="checkbox" id="tgLinkLine"><span>➕ لینک در خط جدا هم بیاید</span></label>
              <label class="tgopt" checked><input type="checkbox" id="tgSummary" checked><span>📄 خلاصه فارسی خبر در پیام</span></label>
              <label class="tgopt"><input type="checkbox" id="tgHashtags" checked><span>#️⃣ هشتگ دارایی‌ها (#BTC #ETH)</span></label>
              <label class="tgopt"><input type="checkbox" id="tgEmoji" checked><span>🔔 ایموجی شروع هر خبر</span></label>
              <label class="tgopt"><input type="checkbox" id="tgStars" checked><span>⭐ ستاره اعتبار (تا ۵ ستاره)</span></label>
              <label class="tgopt"><input type="checkbox" id="tgSilent"><span>🔕 ارسال بی‌صدا (نوتیف نزند)</span></label>
              <label class="tgopt"><input type="checkbox" id="tgPin"><span>📌 پیام بعد از ارسال پین شود</span></label>
            </div>
            <h4 style="margin:16px 0 6px">🧩 قالب پیام</h4>
            <div style="font-size:11px;color:var(--muted);margin-bottom:6px;line-height:2">
              متغیرها: <code class="ltr">{index} {title} {summary_fa} {source} {cred} {stars} {assets} {tags} {time_fa} {link_line}</code>
              — قالب خالی = پیش‌فرض
            </div>
            <textarea id="tgTemplate" rows="5" style="width:100%;direction:ltr;text-align:left;font-family:ui-monospace,monospace;font-size:11.5px;background:var(--surface-2);border:1px solid var(--border);border-radius:10px;color:var(--text);padding:10px"></textarea>
            <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">
              <button class="btn" onclick="saveTelegram()">ذخیره همه تنظیمات</button>
              <button class="btn ghost" onclick="previewTelegram()">👁 پیش‌نمایش پیام</button>
            </div>
            <div id="tgPreview" style="display:none;margin-top:10px;background:var(--surface-2);border:1px solid var(--border);border-radius:10px;padding:12px;font-size:12px;line-height:2;white-space:pre-wrap"></div>
            <div class="hint" style="font-size:11px;margin-top:10px">بعد از هر چرخه، جمع‌بندی معتبرترین خبرها خودکار به همین چت فرستاده می‌شود.</div>
          </div>
        </section>

        <!-- ══ 9. ASSETS MANAGEMENT VIEW ══ -->
        <section class="view" id="view-assets">
          <div class="panelbox">
            <h3>➕ افزودن دارایی دلخواه <span class="hint">— هر دارایی: کریپتو، سهام، فلز، شاخص</span></h3>
            <div class="formgrid">
              <div><label>نماد (لاتین)</label><input type="text" id="naSym" placeholder="LINK"></div>
              <div><label>نام فارسی</label><input type="text" id="naFa" placeholder="چین‌لینک"></div>
              <div><label>نام انگلیسی</label><input type="text" id="naName" placeholder="Chainlink"></div>
              <div><label>نماد Yahoo (تاریخچه قیمت)</label><input type="text" id="naYahoo" placeholder="LINK-USD"></div>
              <div><label>شناسه CoinGecko (اختیاری)</label><input type="text" id="naCg" placeholder="chainlink"></div>
              <div><label>کلیدواژه‌های خبری (با کاما)</label><input type="text" id="naKw" placeholder="chainlink, LINK"></div>
              <div><button class="btn" onclick="addAsset()">افزودن دارایی</button></div>
            </div>
            <div style="font-size:11px;color:var(--muted);margin-top:10px;line-height:2.1">
              نماد Yahoo تاریخچه قیمت و نمودار را می‌سازد (مثلاً LINK-USD، GC=F، AAPL).
            </div>
          </div>
          <div class="panelbox">
            <h3>💹 دارایی‌های تحت پوشش</h3>
            <div id="assetTableBox"></div>
          </div>
        </section>

        <!-- ══ 10. SOURCES MANAGEMENT VIEW ══ -->
        <section class="view" id="view-sources">
          <div class="panelbox">
            <h3>📡 منابع فعال — <span id="srcCount"></span></h3>
            <div id="srcList"></div>
          </div>
          <div class="panelbox">
            <h3>➕ افزودن منبع RSS جدید</h3>
            <div style="display:flex;gap:8px;flex-wrap:wrap">
              <input type="text" id="newSrcName" placeholder="نام منبع (مثلاً: Wired)" style="flex:1;min-width:150px">
              <input type="text" id="newSrcUrl" placeholder="https://example.com/rss" style="flex:2;min-width:220px;direction:ltr;text-align:left">
              <button class="btn" onclick="addSource()">افزودن</button>
            </div>
          </div>
        </section>

        <!-- ══ 11. DASHBOARD SETTINGS VIEW ══ -->
        <section class="view" id="view-settings">
          <div class="panelbox">
            <h3>⚙️ تنظیمات داشبورد</h3>
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
            <div style="margin-top:18px;display:flex;gap:8px;flex-wrap:wrap">
              <button class="btn" onclick="saveSettings()">💾 ذخیره تنظیمات</button>
              <button class="btn ghost" onclick="doRefresh()">اعمال و بروزرسانی الآن</button>
            </div>
            <div style="font-size:11px;color:var(--muted);margin-top:14px;line-height:2">
              حداکثر سن خبر: <b id="setAgeInfo">۲۴</b> ساعت
            </div>
          </div>
        </section>

      </div><!-- /view-container -->
    </main>

    <div class="sidebar-backdrop" id="sidebarBackdrop" onclick="toggleSidebar()"></div>

  </div><!-- /app-body -->
</div><!-- /app-shell -->

<!-- Article Modal -->
<div class="overlay" id="artOverlay" onclick="if(event.target===this)closeModal('artOverlay')">
  <div class="modal">
    <button class="mclose" onclick="closeModal('artOverlay')">✕</button>
    <div id="artBody"><div class="spinner"></div></div>
  </div>
</div>

<!-- Blurb Modal -->
<div class="overlay" id="blurbOverlay" onclick="if(event.target===this)closeModal('blurbOverlay')">
  <div class="modal" style="max-width:620px">
    <button class="mclose" onclick="closeModal('blurbOverlay')">✕</button>
    <div id="blurbBody"><div class="spinner"></div></div>
  </div>
</div>

<div class="toast" id="toast" role="status" aria-live="polite"></div>

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
    ['artOverlay', 'blurbOverlay'].forEach(id => closeModal(id));
  }
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    const q = document.getElementById('q');
    if (q) { showView('feed'); q.focus(); }
  }
});

let DATA = null;
let UI = {topic:'all', asset:'all', kind:'all', view:'feed', repSym:null, repLang:'en', repSections:null, onlyBookmarked:false};
let CHART = {show:true, bb:true, ema:true, levels:true};
let TVW = {sym:null, tf:'60'};    /* نمودار لایو: دارایی و تایم‌فریم فعال */
let CAND = {sym:null, tf:null, data:null, at:0};            /* کش کندل‌های لایو */
let LIVE = {};            /* sym -> {price, change_24h, src} from /api/live */

const FA_TOPIC = {regulation:'Regulation',institutional:'Institutional',etf:'ETF',macro:'Macro',security:'Security',analysis:'Analysis',defi:'DeFi',market:'Market',tech:'Tech',general:'General'};
const FA_ASSET = {}, ASSET_ICONS = {};

/* Chart palette — mirrors the :root tokens above (SVG presentation attributes
   must use concrete colours, var() only works in style=""). */
const C = {
  price:'#C69A6B', priceTxt:'#E3C9A6',
  ema20:'#9FB4CC', ema50:'#DDB98C', ema200:'#8C6A44',
  band:'rgba(159,180,204,.10)', bandLine:'rgba(159,180,204,.30)',
  grid:'#232D39', axis:'#6B7684',
  sup:'#A3C4B4', res:'#C97C6B',
  rsi:'#DDB98C',
  up:'rgba(163,196,180,.55)', down:'rgba(201,124,107,.55)',
  vol:'rgba(159,180,204,.35)',
  cup:'#A3C4B4', cdn:'#C97C6B'    /* کندل صعودی/نزولی لایو */
};

/* importance order for the top strip and every asset list */
const ASSET_ORDER = ['BTC','ETH','BNB','SOL','XRP','ADA','DOGE','LINK','XAU','XAG','WTI','DXY','SPX','VIX'];
const IMPORTANCE = {};
ASSET_ORDER.forEach((s,i)=>IMPORTANCE[s]=i);
function importance(sym){ return IMPORTANCE[sym]!=null ? IMPORTANCE[sym] : 900+String(sym).length; }
function orderedAssets(){
  if(!DATA) return [];
  const custom=Object.keys(DATA.assets_meta||{}).filter(s=>DATA.assets_meta[s].custom&&DATA.config.assets.includes(s));
  return (DATA.config.assets||[]).slice().sort((a,b)=>importance(a)-importance(b))
    .concat(custom.filter(s=>!DATA.config.assets.includes(s)));
}

function initMeta(){
  if(!DATA) return;
  for(const [k,v] of Object.entries(DATA.assets_meta||{})){ FA_ASSET[k]=v.fa; ASSET_ICONS[k]=v.icon; }
}
function toFa(n){ return String(n==null?'':n).replace(/\d/g,d=>'۰۱۲۳۴۵۶۷۸۹'[d]); }
function esc(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function num(v,nd){ return Number(v).toLocaleString('en-US',{minimumFractionDigits:nd||0,maximumFractionDigits:nd||0}); }
function fmtPrice(v){ if(v==null) return '—';
  if(v>=1000) return '$'+num(v,0);
  if(v>=10) return '$'+num(v,2); if(v>=1) return '$'+num(v,3); return '$'+num(v,4); }
function fmtIran(iso){ if(!iso) return '—'; try{ return toFa(new Date(iso).toLocaleTimeString('fa-IR',{hour:'2-digit',minute:'2-digit'})); }catch(e){ return '—'; } }
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
  UI.view=v;
  document.querySelectorAll('.tab').forEach(t=>{t.classList.toggle('active',t.dataset.view===v); t.setAttribute('aria-selected', t.dataset.view===v?'true':'false');});
  document.querySelectorAll('.view').forEach(s=>s.classList.toggle('active',s.id==='view-'+v));
  ['ibSettings','ibSources','ibAssets'].forEach(id=>{
    const b=document.getElementById(id);
    if(b) b.classList.toggle('on', b.id==='ibSettings'&&v==='settings' || b.id==='ibSources'&&v==='sources' || b.id==='ibAssets'&&v==='assets');
  });
  if(v==='reports'&&DATA&&!skipPick){
    const ordered=orderedAssets().filter(s=>true);
    if(!UI.repSym||!ordered.includes(UI.repSym)) UI.repSym=ordered[0];
    pickReport(UI.repSym, true);   // pickReport calls showView(..., skipPick)
  }
  if(v==='assets') renderAssetTable();
  if(v==='monitor') loadMonitor();
  if(v==='calendar'){ if(ECON) renderCalendar(); else loadCalendar(); }
  if(v==='alerts') initAlerts();
  if(UI.view==='archive'){ renderArchive(); return; }
  if(UI.view==='bookmarks'){ renderBookmarks(); return; }
  if(v==='fng') renderFngPage();
  if(v==='etf'){ renderEtfTab(); if(ECON) renderEtfFlows(document.getElementById('etfBox2')); renderEtfLive('etfLive2'); loadIdeas(); }
}
function gotoView(v){ showView(v); }

async function loadData(){
  try{
    const r = await fetch('/api/data'); DATA = await r.json();
    initMeta(); renderAll();
  }catch(e){ document.getElementById('cycleTxt').textContent='خطای اتصال به سرور'; }
}
/* poll /api/data every 60s so newly-cycled news appears without reload */
setInterval(()=>{ if(!DATA||!DATA.stats||!DATA.stats.cycle_running) loadData(); }, 60000);
/* ── DL2 phase 2: live price ticker under the topbar ─────────────────── */
function renderTicker(){
  const bar=document.getElementById('tickerBar');
  if(!bar||!DATA) return;
  const out=[];
  (typeof orderedAssets==='function'?orderedAssets():[]).forEach(sym=>{
    const m=(DATA.market||{})[sym]||{};
    const lv=(typeof liveOf==='function')?liveOf(sym):null;
    const price=(lv&&lv.price!=null)?lv.price:m.price;
    if(price==null) return;
    const chg=(lv&&lv.change_24h!=null)?lv.change_24h:m.change_24h;
    const cls=chg==null?'':(chg>=0?'up':'dn');
    const arrow=chg==null?'':(chg>=0?'▲':'▼');
    out.push(`<span class="tk ${cls}"><span class="s">${esc(sym)}</span>`+
      `<span class="p">${fmtPrice(price)}</span>`+
      (chg==null?'':`<span class="c">${arrow}${toFa(Math.abs(chg).toFixed(2))}%</span>`)+
      (m.stale?'<span class="st">کهنه</span>':'')+`</span>`);
  });
  bar.innerHTML=out.join('<span class="sep">·</span>');
}
/* ── DL2 phase 2: three highest-credibility stories above the grid ───── */
function renderLead(){
  const box=document.getElementById('leadRow');
  if(!box||!DATA) return;
  const pool=(DATA.articles||[]).filter(a=>(a.credibility||0)>=0.6);
  const top=pool.slice().sort((a,b)=>((b.credibility||0)-(a.credibility||0))||((b.published_ts||0)-(a.published_ts||0))).slice(0,3);
  if(!top.length){ box.innerHTML=''; return; }
  box.innerHTML=top.map(a=>`<article class="lead-card" role="button" tabindex="0"
      aria-label="${esc(a.title_fa||a.title)}" onclick="openArticle('${a.id}')"
      onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();openArticle('${a.id}')}">
      <div class="lead-rail"></div>
      <div class="body">
        <div class="row1">${(a.assets||[]).slice(0,2).map(s=>`<span class="badge b-asset">${ASSET_ICONS[s]||''}${FA_ASSET[s]||s}</span>`).join('')}
          <span class="badge b-topic">${a.topic_icon||''} ${FA_TOPIC[a.topic]||''}</span></div>
        <div class="lead-ttl">${esc(a.title_fa||a.title)}</div>
        <div class="summ">${esc((a.summary_fa||a.summary||'').slice(0,190))}</div>
        <div class="row2"><span class="src">${esc(a.source)}</span><span class="dt">${esc(a.datetime_fa||'')}</span></div>
      </div></article>`).join('');
}
function renderAll(){
  window.__MACRO=DATA.macro||[];
  renderAssets(); renderChips(); renderSrcSel(); renderKindSel(); renderFeed();
  renderTicker(); renderLead(); dl2AfterFeed();
  renderSources(); renderSettings(); renderStats(); renderAssetTable(); renderArchive(); renderBookmarks();
  paintFng();
  if(UI.view==='monitor') loadMonitor();
  if(UI.view==='calendar'&&ECON) renderCalendar();
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
  g.innerHTML=items.map(cardHTML).join('');
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
  g.innerHTML=days.map(day=>{
    const items=byDay[day];
    return `<div class="calday archday">
      <div class="calday-h"><span class="calday-title">🗓 ${esc(day)}</span>
        <span class="calday-meta">${toFa(items.length)} خبر آرشیوشده</span></div>
      <div class="archgrid">${items.map(cardHTML).join('')}</div>
    </div>`;
  }).join('');
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
  catch(e){ b.disabled=false; toast('Recovery could not start'); return; }
  toast('Deep recovery started — 60+ ways per broken feed');
  clearInterval(recTimer);
  recTimer=setInterval(async ()=>{
    try{
      const r=await fetch('/api/recover/status'); const j=await r.json();
      if(!j.running){
        clearInterval(recTimer); b.disabled=false;
        b.textContent='🔧 Recover all broken feeds';
        if(j.total) toast(`Recovery finished — ${j.fixed}/${j.total} feeds back online · ${j.attempts} ways tried`);
        loadMonitor();
        return;
      }
      b.textContent=`🔧 Recovering… feed ${j.done||0}/${j.total||0} · ${(j.attempts||0)} ways tried · ${j.fixed||0} fixed`;
      if((j.attempts||0)%6===0) loadMonitor();      /* refresh rows live */
    }catch(e){}
  },2000);
  setTimeout(loadMonitor, 4000);
}
function renderMonitor(){
  if(!MON) return;
  document.getElementById('monSummary').textContent=`${toFa(MON.ok)} of ${toFa(MON.total)} feeds healthy · ${toFa(MON.broken)} down`;
  const nb=document.getElementById('cntBroken');
  if(MON.broken>0){ nb.style.display='inline-block'; nb.textContent=MON.broken; nb.style.background='var(--red)'; nb.style.color='#fff'; }
  else nb.style.display='none';
  const rows=[...MON.rows].sort((a,b)=>(a.ok-b.ok)||(b.count-a.count));
  let html='';
  for(const r of rows){
    if(r.ok&&!r.recovered) continue;                 /* healthy & untouched: skip in monitor */
    const st=r.ok?(r.recovered?'<span style="color:var(--green)">✓ recovered</span>':'<span style="color:var(--green)">✓ OK</span>')
                 :'<span style="color:var(--red)">✗ down</span>';
    const reason=r.ok?'':`<div style="color:var(--copper-txt);margin-top:3px">⚠ Cause: ${esc(r.reason_fa||r.detail||'unknown')}</div>`;
    const rec=(r.recovery||[]);
    const shown=rec.slice(0,8);
    const path=rec.length?`<div style="color:var(--muted);font-size:10.5px;margin-top:2px">Recovery: ${rec.length} way${rec.length>1?'s':''} tried — ${shown.map(esc).join(' → ')}${rec.length>8?` … (+${rec.length-8} more)`:''}${r.mirror?' (mirror)':''}${r.ok?' · last hit: '+esc(shown[shown.length-1]||''):''}</div>`:'';
    const hist=(r.hist&&r.hist.length)?`<div style="display:flex;align-items:center;gap:6px;margin-top:3px;color:var(--faint);font-size:10.5px">Last 30 cycles: ${histSvg(r.hist)}</div>`:'';
    html+=`<div class="monrow">
      <div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap">
        <span><b>${esc(r.name)}</b> <span style="color:var(--faint);font-size:10px">${esc(r.kind_fa||'')}</span></span>
        <span style="font-size:11px">${st}${r.count?` · ${r.count} news`:''}${r.checked_fa?` · at ${esc(r.checked_fa)}`:''}</span>
      </div>
      ${reason}${path}${hist}
    </div>`;
  }
  document.getElementById('monList').innerHTML=html||'<div class="empty">همه منابع سالم‌اند 🎉</div>';
}
function renderStats(){
  const s=DATA.stats;
  document.getElementById('lastUpd').textContent = fmtIran(s.last_update);
  const d=document.getElementById('cycleDot'), t=document.getElementById('cycleTxt');
  d.className='dot'+(s.cycle_running?' busy':(s.last_error?' err':''));
  t.textContent = s.cycle_running?'Fetching & translating…':(s.cycles_run? ('Cycle '+s.cycles_run+' done · every '+(DATA.config.interval/60)+' min'):'starting…');
  document.getElementById('cntFeed').textContent = toFa(DATA.articles.length);
  document.getElementById('cntSrc').textContent = toFa(DATA.sources.filter(x=>x.enabled).length);
  document.getElementById('ruleAge').textContent = DATA.rules.max_age_hours;
  document.getElementById('setAgeInfo').textContent = toFa(DATA.rules.max_age_hours);
  const rb=document.getElementById('refreshBtn'); rb.disabled=!!s.cycle_running;
  rb.textContent = s.cycle_running?'⏳ Updating…':'⟳ Refresh now';
  const cs = s.cycle_stats||{};
  if(cs.total!=null) document.getElementById('cycleTxt').title =
     `Valid news: ${cs.total} | rejected: ${cs.rejected} (older than ${cs.max_age_hours}h: ${cs.stale_rejected}) | feeds OK: ${cs.feeds_ok}/${cs.feeds_total}`;
}
setInterval(()=>{
  if(!DATA) return;
  const nx=DATA.stats.next_cycle_ts;
  if(!nx){ document.getElementById('nextIn').textContent='—'; return; }
  let s=Math.max(0,Math.round(nx-Date.now()/1000));
  document.getElementById('nextIn').textContent=s/60|0+'m '+(s%60)+'s';
},1000);

/* ── live prices (free APIs, polled every 15s) ── */
async function pollLive(){
  try{
    const r=await fetch('/api/live'); const d=await r.json();
    if(d.ok&&d.prices){ LIVE=d.prices; if(d.fng&&d.fng.now!=null) window.__FNG=d.fng; paintLive(); paintFng(); }
  }catch(e){}
}
function liveOf(sym){ return LIVE[sym]||null; }
function paintLive(){
  renderAssets();                       /* strip re-renders with live prices */
  if(UI.view==='reports'&&window.__rep){ updateChartLive(); updateCandlesLive(); }
}
/* green/red flash on a price element whose value moved */
function flash(el, dir){ if(!el||!dir) return; el.classList.remove('flash-up','flash-dn'); void el.offsetWidth;
  el.classList.add(dir>0?'flash-up':'flash-dn'); }
setInterval(pollLive, 15000);

/* ── assets strip ── */
function renderAssets(){
  const strip=document.getElementById('assetsStrip');
  const m=DATA.market, counts=DATA.asset_counts||{};
  let html='', prev=window.__prevLive||{};
  for(const sym of orderedAssets()){
    const meta=DATA.assets_meta[sym]||{}; if(!meta||!DATA.config.assets.includes(sym)) continue;
    const d=m[sym]||{};
    const lv=liveOf(sym);
    const price = lv?lv.price:(d.price!=null?d.price:null);
    const chg   = lv&&lv.change_24h!=null?lv.change_24h:d.change_24h;
    const cls = chg==null?'':(chg>=0?'up':'dn');
    let flash='';
    if(lv&&prev[sym]!=null&&lv.price!==prev[sym]) flash = lv.price>prev[sym]?' flash-up':' flash-dn';
    const footer = toFa(counts[sym]||0)+' خبر';
    html+=`<div class="acard" onclick="pickReport('${sym}')" title="گزارش تحلیلی ${esc(meta.fa)}">
      <div class="sym"><span class="ic">${meta.icon||''}</span>${esc(meta.fa)} <span class="tk">${sym}</span></div>
      <div class="prc${flash}" data-sym="${sym}">${fmtPrice(price)}</div>
      <div class="chg ${cls}">${chg==null?'':(chg>=0?'▲ +':'▼ ')+num(chg,2)+'%'}</div>
      ${sparkSVG(d.spark)}
      <div class="nm">${footer}${d.stale?' · stale':''}</div>
    </div>`;
  }
  /* macro assets are now full registry members with reports — only render a
     plain chip for macro feeds that are NOT tracked assets (no duplicate card) */
  for(const mq of (window.__MACRO||[])){
    if(DATA.config.assets.includes(mq.sym)||orderedAssets().includes(mq.sym)) continue;
    const mcls=mq.change==null?'':(mq.change>=0?'up':'dn');
    html+=`<div class="acard macro" title="${esc(mq.fa||mq.sym)}">
      <div class="sym"><span class="ic">${mq.icon||''}</span>${esc(mq.sym)}</div>
      <div class="prc">${mq.price!=null?num(mq.price,mq.price>=1000?0:2):'—'}</div>
      <div class="chg ${mcls}">${mq.change==null?'':(mq.change>=0?'▲ +':'▼ ')+num(mq.change,2)+'%'}</div>
      <div class="nm">${esc(mq.fa||'')}</div>
    </div>`;
  }
  strip.innerHTML=html||'<div class="empty">دارایی‌ای فعال نیست — از تب «دارایی‌ها» اضافه کنید.</div>';
  window.__prevLive={}; for(const sym of orderedAssets()){ const lv=liveOf(sym); if(lv) window.__prevLive[sym]=lv.price; }
}
function histSvg(arr){
  if(!arr||!arr.length) return '';
  const W=arr.length*4;
  return `<svg class="histsvg" viewBox="0 0 ${W} 20" preserveAspectRatio="none" role="img" aria-label="health history">`+
    arr.map((v,i)=>`<rect x="${i*4}" y="${v?4:12}" width="3" height="${v?12:4}" fill="${v?'var(--green)':'var(--red)'}"/>`).join('')+`</svg>`;
}
function sparkSVG(arr){
  if(!arr||arr.length<2) return `<svg viewBox="0 0 100 26" preserveAspectRatio="none"><line x1="0" y1="13" x2="100" y2="13" stroke="var(--border)" stroke-width="1"/></svg>`;
  const mn=Math.min(...arr), mx=Math.max(...arr), rg=(mx-mn)||1;
  const pts=arr.map((v,i)=>`${(i/(arr.length-1)*100).toFixed(1)},${(24-(v-mn)/rg*22+1).toFixed(1)}`).join(' ');
  const col=arr[arr.length-1]>=arr[0]?'var(--green)':'var(--red)';
  return `<svg viewBox="0 0 100 26" preserveAspectRatio="none"><polyline points="${pts}" fill="none" stroke="${col}" stroke-width="1.6"/></svg>`;
}

/* ── chips ── */
function renderChips(){
  const tc=DATA.topic_counts||{};
  const bmarks=getBookmarks();
  let th=`<button class="chip ${UI.topic==='all'&&!UI.onlyBookmarked?'on':''}" aria-pressed="${UI.topic==='all'&&!UI.onlyBookmarked}" onclick="UI.onlyBookmarked=false;UI.topic='all';renderChips();renderFeed()">همه موضوعات <span class="n">${toFa(DATA.articles.length)}</span></button>`;
  if(bmarks.length){
    th+=`<button class="chip ${UI.onlyBookmarked?'on':''}" onclick="UI.onlyBookmarked=!UI.onlyBookmarked;renderChips();renderFeed()">⭐ نشان‌شده‌ها <span class="n">${toFa(bmarks.length)}</span></button>`;
  }
  for(const t of Object.keys(DATA.topics_meta)){
    const n=tc[t]||0; if(!n) continue;
    const meta=DATA.topics_meta[t];
    const tact=UI.topic===t&&!UI.onlyBookmarked;
    th+=`<button class="chip ${tact?'on':''}" aria-pressed="${tact}" onclick="setTopicFilter('${t}')">${meta.icon} ${FA_TOPIC[t]||meta.fa} <span class="n">${toFa(n)}</span></button>`;
  }
  document.getElementById('topicChips').innerHTML=th;

  const ac=DATA.asset_counts||{};
  let ah=`<button class="chip ${UI.asset==='all'?'on':''}" aria-pressed="${UI.asset==='all'}" onclick="UI.asset='all';UI.onlyBookmarked=false;renderChips();renderFeed()">همه دارایی‌ها</button>`;
  for(const sym of orderedAssets()){
    if(!DATA.config.assets.includes(sym)) continue;
    const meta=DATA.assets_meta[sym]||{};
    const aact=UI.asset===sym;
    ah+=`<button class="chip ${aact?'on':''}" aria-pressed="${aact}" onclick="setAssetFilter('${sym}')">${meta.icon||''} ${esc(meta.fa||sym)} <span class="n">${toFa(ac[sym]||0)}</span></button>`;
  }
  document.getElementById('assetChips').innerHTML=ah;
}
/* asset & topic chips are toggles: clicking the active one clears the filter */
function setAssetFilter(sym){ UI.asset = (UI.asset===sym) ? 'all' : sym; UI.onlyBookmarked=false; renderChips(); renderFeed(); }
function setTopicFilter(t){ UI.topic = (UI.topic===t) ? 'all' : t; UI.onlyBookmarked=false; renderChips(); renderFeed(); }
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
  const q=(document.getElementById('q').value||'').toLowerCase();
  const src=document.getElementById('srcSel').value;
  const kind=document.getElementById('kindSel').value;
  const minC=+document.getElementById('credSlider').value/100;
  const sort=document.getElementById('sortSel').value;
  let list=DATA.articles.filter(a=>{
    if(UI.onlyBookmarked && !isBookmarked(a.id)) return false;
    if(UI.topic!=='all'&&a.topic!==UI.topic) return false;
    if(UI.asset!=='all'&&!(a.assets||[]).includes(UI.asset)) return false;
    if(src!=='all'&&a.source!==src) return false;
    if(kind!=='all'&&a.source_kind!==kind) return false;
    if(a.credibility<minC) return false;
    if(q&&!((a.title+' '+(a.title_fa||'')+' '+(a.summary_fa||'')+' '+(a.summary||'')+' '+a.source).toLowerCase().includes(q))) return false;
    return true;
  });
  /* tolerate a millisecond epoch from any single upstream feed — one bad ts would
     otherwise sort to the very top of "newest" forever */
  const tsOf=a=>{ const t=a.published_ts||0; return t>1e12?Math.floor(t/1000):t; };
  if(sort==='new') list.sort((a,b)=>tsOf(b)-tsOf(a)||String(a.source).localeCompare(String(b.source)));
  else if(sort==='cred') list.sort((a,b)=>b.credibility-a.credibility||tsOf(b)-tsOf(a));
  else if(sort==='src') list.sort((a,b)=>a.source.localeCompare(b.source)||tsOf(b)-tsOf(a));
  document.getElementById('feedEmpty').style.display=list.length?'none':'block';
  document.getElementById('newsGrid').innerHTML=list.slice(0,400).map(cardHTML).join('');
  document.getElementById('feedCount').textContent = toFa(list.length)+' خبر';
}
/* ── DL2 step 3: one language policy for the chrome ──────────────────────
   The dashboard spoke Persian everywhere except a handful of English panel
   titles and calendar buttons. This rewrites ONLY chrome text (headings,
   buttons, labels, options, hints) — never news content — by editing text
   nodes in place, so no element, handler or attribute is ever re-created. */
(function(){
  try{
    var MAP={
      'Economic Calendar':'تقویم اقتصادی',
      'Market Sessions':'سشن‌های بازار',
      'Fear & Greed Index':'شاخص ترس و طمع',
      'Spot Bitcoin ETF Flows':'جریان‌های ETF بیت‌کوین',
      'Live ETF Quotes':'نرخ زنده‌ی ETF',
      'TradingView Ideas':'ایده‌های تریدینگ‌ویو',
      'Clear all':'پاک‌کردن همه',
      'Archive':'آرشیو هوشمند',
      'Bookmarks':'نشان‌شده‌ها',
      'Hide past events':'پنهان‌کردن رویدادهای گذشته',
      'Impact, then time':'ابتدا اهمیت، سپس زمان',
      'All impact levels':'همه‌ی سطوح اهمیت',
      'High impact only':'فقط اهمیت بالا',
      'Medium & above':'متوسط و بالاتر',
      'Low & above':'کم و بالاتر',
      'Chronological':'به ترتیب زمان',
      'Newest first':'جدیدترین ابتدا',
      'Prev day':'روز قبل',
      'Next day':'روز بعد',
      'Prev week':'هفته قبل',
      'Next week':'هفته بعد',
      'Today':'امروز',
      'Currency':'ارز',
      'Impact':'اهمیت',
      'Order':'ترتیب'
    };
    var KEYS=Object.keys(MAP).sort(function(a,b){ return b.length-a.length; });
    var SEL='h1,h2,h3,h4,button,label,option,th,.hint,.panel-sub,.nav-text';
    var w=document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
    var nodes=[], n;
    while((n=w.nextNode())) nodes.push(n);
    nodes.forEach(function(node){
      var el=node.parentElement;
      if(!el || !el.closest || !el.closest(SEL)) return;
      var v=node.nodeValue, changed=false;
      KEYS.forEach(function(k){
        if(v.indexOf(k)>=0){ v=v.split(k).join(MAP[k]); changed=true; }
      });
      if(changed) node.nodeValue=v;
    });
  }catch(e){ /* cosmetic pass only — never block the dashboard */ }
})();

/* ── DL2 step 4: retire the repeated inline typography hack ──────────────
   ‎115 inline styles remain in the markup and 18 of them repeat the same
   "font-size:10–11px; color:var(--muted)" subtitle hack (9 variants). They are
   folded into the .panel-sub class so every subtitle shares one style and
   nothing sits below the 12px readability floor. Layout-bearing inline styles
   (width/height/margin/display/direction) are deliberately left untouched. */
(function(){
  try{
    var els=document.querySelectorAll('[style*="font-size"]');
    var retired=0;
    els.forEach(function(el){
      var st=el.getAttribute('style')||'';
      if(st.indexOf('--muted')<0 && st.indexOf('--faint')<0) return;
      if(/width|height|top|left|right|bottom|display|margin|direction|text-align/.test(st)) return;
      el.classList.add('panel-sub');
      el.removeAttribute('style');
      retired++;
    });
    window.__dl2_retired_inline=retired;
  }catch(e){}
})();

function credBadge(c){
  const pct=Math.round(c*100), cls=pct>=75?'hi':(pct>=55?'mid':'low');
  return `<span class="cred ${cls}" title="امتیاز اعتبار محتوایی: ${toFa(pct)}٪"><span class="bar"><i style="width:${pct}%"></i></span><span>${pct}%</span></span>`;
}
function credChip(c){
  const pct=Math.round(c*100), cls=pct>=75?'hi':(pct>=55?'mid':'low');
  return `<span class="cred ${cls} cred-chip" title="امتیاز اعتبار محتوایی: ${toFa(pct)}٪">${toFa(pct)}٪</span>`;
}
function cardHTML(a){
  const _as=(a.assets||[]);
  const chips=_as.slice(0,2).map(s=>`<span class="badge b-asset">${ASSET_ICONS[s]||''}${FA_ASSET[s]||s}</span>`).join('')
    + (_as.length>2?`<span class="badge more">+${toFa(_as.length-2)}</span>`:'');
  const tp=a.topic_fa?`<span class="badge b-topic">${a.topic_icon||''} ${FA_TOPIC[a.topic]||a.topic_fa}</span>`:'';
  const kd=(DATA.kind_labels||{})[a.source_kind]?`<span class="badge b-kind">${DATA.kind_labels[a.source_kind]}</span>`:'';
  const faTitle = a.title_fa || a.title;
  const enTitle = a.title_fa ? `<div class="ttl-en">${esc(a.title)}</div>` : '';
  const summ = a.summary_fa || a.summary || '';
  const img = a.image
    ? `<img src="${esc(a.image)}" alt="" loading="lazy" referrerpolicy="no-referrer" data-orig="${esc(a.image)}" onerror="if(!this.dataset.tried){this.dataset.tried='1';this.src='/api/proxy-image?url='+encodeURIComponent(this.dataset.orig);}else{this.replaceWith(Object.assign(document.createElement('div'),{className:'noimg',textContent:'📰'}))}">`
    : '';
  const thumb = `<div class="thumb">${img || '<div class="noimg">📰</div>'}${credChip(a.credibility)}</div>`;
  const bmarked = isBookmarked(a.id);
  const starBtn = `<button class="star-btn ${bmarked?'on':''}" onclick="toggleBookmark('${a.id}', event)" title="${bmarked?'حذف از نشان‌شده‌ها':'نشان کردن این خبر'}" aria-label="نشان کردن">${bmarked?'★':'☆'}</button>`;
  return `<div class="ncard" role="button" tabindex="0" aria-label="${esc(faTitle)} — ${esc(a.source)}" onclick="openArticle('${a.id}')" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();openArticle('${a.id}')}">
    ${thumb}
    <div class="body">
      <div class="row1">${tp}${kd}${chips}</div>
      <div class="ttl">${isNew(a)?'<span class="newdot newdot-inline" title="خبر تازه"></span>':''}${esc(faTitle)}</div>
      ${summ?`<div class="summ">${esc(summ)}</div>`:''}
      <div class="row2">
        <span class="src">${esc(a.source)}</span>
        <span class="dt" title="${esc(a.published_str||'')}">${esc(a.datetime_fa||'')}</span>
        ${starBtn}
      </div>
      <button class="btn ghost sm blurb-btn" onclick="event.stopPropagation();openBlurb('${a.id}')" aria-label="توضیحات خبر">📋 توضیحات خبر</button>
    </div>
  </div>`;
}

/* ── article modal ── */
async function openArticle(id, fa){
  const ov=document.getElementById('artOverlay'); ov.classList.add('open');
  const b=document.getElementById('artBody');
  /* paint what we already have instantly, then swap in the full text —
     an uncached article runs the deep-extraction ladder server-side and can
     take ~15s, so a bare spinner reads as "nothing happened" */
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
        ${quick.summary_fa||quick.summary?`<div class="msec"><h4>📄 خلاصه</h4><p class="fa">${esc(quick.summary_fa||quick.summary)}</p></div>`:''}
        <div class="msec"><h4>📝 متن کامل خبر</h4>
          <div style="display:flex;align-items:center;gap:10px;color:var(--muted);font-size:12.5px;padding:6px 0">
            <span class="spinner"></span><span>در حال استخراج متن کامل… ممکن است چند ثانیه طول بکشد</span>
          </div></div>`;
    } else {
      b.innerHTML='<div class="spinner"></div>';
    }
  }catch(e){ b.innerHTML='<div class="spinner"></div>'; }
  try{
    const d=await (await fetch('/api/article/'+id+(fa?'?fa=1':''))).json();
    const flags=(d.flags||[]).length?`<div class="flags">⚠️ پرچم‌های اعتبارسنجی: ${d.flags.map(esc).join(' · ')}</div>`:'';
    const rel=(d.related||[]).map(x=>`<a class="relrow" href="javascript:void(0)" onclick="openArticle('${x.id}');event.stopPropagation()"><span class="reltitle">${esc(x.title)}</span><span class="relsrc">${esc(x.source)}</span><span class="relgo">↗</span></a>`).join('');
    const assets=(d.assets||[]).map(s=>`<span class="badge b-asset">${esc(FA_ASSET[s]||s)}</span>`).join(' ');
    const c=d.content||{};
    const paras = (c.paragraphs||[]);
    const searchUrl='https://www.google.com/search?q='+encodeURIComponent('"'+d.title+'" '+d.source);
    const bodyHtml = paras.length
      ? paras.map(p=>`<p class="en">${esc(p)}</p>`).join('')
      : `<p style="color:var(--muted)">متن کامل به‌صورت خودکار قابل استخراج نبود (این خبر از جستجوی گوگل‌نیوز آمده و لینک آن ریدایرکت رمزنگاری‌شده است، یا سایت مرجع ربات را بلاک/پی‌وال کرده). از دکمه پایین متن اصلی را باز کن.</p>
         <a class="mlink" style="margin-top:8px" href="${searchUrl}" target="_blank" rel="noopener">🔍 جستجوی متن کامل این خبر</a>`;
    const faHtml = d.content_fa && d.content_fa.length
      ? d.content_fa.slice(0,60).map(p=>`<p class="fa">${esc(p)}</p>`).join('')
      : '';
    b.innerHTML=`
      <div class="row1" style="display:flex;gap:6px;flex-wrap:wrap">
        <span class="badge b-topic">${d.topic_icon||''} ${esc(FA_TOPIC[d.topic]||'')}</span>${assets}
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
      ${(d.summary_full_fa||d.summary_full)?`<div class="msec"><h4>📄 خلاصه (فارسی)</h4><p class="fa">${esc(d.summary_full_fa||'')}</p>
        ${!d.summary_full_fa&&d.summary_full?`<p class="en" style="font-size:12px;color:var(--muted)">${esc(d.summary_full)}</p>`:''}
        <h4 style="margin-top:10px">📄 Original summary</h4><p class="en" style="font-size:12px;color:var(--muted)">${esc(d.summary_full||'—')}</p></div>`:''}
      <div class="msec">
        <h4><span>📝 متن کامل خبر (انگلیسی)</span>
          <span style="font-size:10.5px;color:var(--muted)">${toFa(c.word_count||0)} کلمه · ${toFa(paras.length)} پاراگراف${c.partial?' · ناقص/پی‌وال':''}</span></h4>
        <div class="scroll">${bodyHtml}</div>
        ${(c.word_count<60)&&paras.length?`<div style="font-size:11px;color:var(--amber);margin-top:8px">⚠️ متن استخراج‌شده کوتاه است (احتمالاً پی‌وال یا بارگذاری جاوااسکریپتی). لینک اصلی را باز کنید.</div>`:''}
        ${!faHtml?`<button class="btn ghost sm" style="margin-top:10px" onclick="openArticle('${id}',1)">🇮🇷 ترجمه فارسی متن کامل</button>`:''}
      </div>
      ${faHtml?`<div class="msec"><h4>🇮🇷 ترجمه فارسی متن کامل</h4><div class="scroll">${faHtml}</div></div>`:''}
      <a class="mlink" href="${esc((c&&c.resolved_url)||d.link)}" target="_blank" rel="noopener">🔗 مشاهده در ${esc(d.source)}</a>
      ${rel?`<div class="msec rel" style="margin-top:12px"><h4>🧩 اخبار مرتبط <span style="font-size:10.5px;color:var(--muted);font-weight:400">${toFa((d.related||[]).length)} خبر هم‌موضوع</span></h4>${rel}</div>`:''}`;
  }catch(e){ b.innerHTML='<div class="empty">خطا در دریافت خبر</div>'; }
}
function closeModal(id){ document.getElementById(id).classList.remove('open'); }

/* ── reports ── */
function renderRepChips(){
  document.getElementById('repChips').innerHTML=orderedAssets().map(s=>{
    const m=DATA.assets_meta[s]||{};
    return `<button class="chip ${UI.repSym===s?'on':''}" onclick="pickReport('${s}')">${m.icon||''} ${esc(m.fa||s)}</button>`;
  }).join('');
}
function pickReport(sym, keepLang){
  UI.repSym=sym; if(!keepLang) UI.repLang='en';
  showView('reports', true);   // skipPick: never call back into pickReport
  renderRepChips();
  const box=document.getElementById('repBox');
  box.innerHTML='<div class="spinner"></div>';
  const url='/api/report/'+sym+(UI.repLang==='fa'?'?lang=fa':'');
  fetch(url).then(r=>r.json()).then(rep=>{
    if(rep.error){ box.innerHTML=`<div class="empty">خطا در تولید گزارش: ${esc(rep.error)}</div>`; return; }
    UI.repSections=rep.sections;
    const fa = UI.repLang==='fa';
    let html=`<div class="rep-layout">
      <div class="rep-doc">
        <div class="rep-actions">
          <button class="btn ghost sm" onclick="copyReport()" title="فقط متن تحلیل کپی می‌شود">📋 کپی متن</button>
          <button class="btn ${fa?'on':'ghost'} sm" onclick="toggleLang('${sym}','fa')">🇮🇷 ترجمه فارسی</button>
          <button class="btn ${fa?'ghost':'on'} sm" onclick="toggleLang('${sym}','en')">🇬🇧 English</button>
        </div>`;
    for(const [kind,val] of rep.sections){
      if(kind==='meta'){
        html+=`<h2>${esc(fa?(val.title_fa||val.title):val.title)}</h2>
          <div class="meta"><span>🕒 ${esc(fa?(val.asof_fa||val.asof):val.asof)}</span>
          <span>💰 ${fmtPrice(val.price)}</span>
          <span>${val.change_24h!=null?((val.change_24h>=0?'▲ ':'▼ ')+num(val.change_24h,2)+'% در ۲۴ ساعت'):''}</span>
          <span>📰 ${toFa(val.news_used||0)} خبر استنادشده از ${toFa((val.sources_used||[]).length)} منبع</span></div>`;
      }
      else if(kind==='h') html+=`<h3>${esc(fa?val.fa:val.en)}</h3>`;
      else if(kind==='p'){
        const t = fa ? (val.fa || val.en) : val.en;
        html+=`<p class="${fa?'fa':'en'}">${mdLite(t)}</p>`;
        if(fa && !val.fa) html+=`<p class="fa" style="color:var(--amber);font-size:11px">ترجمه این بخش در دسترس نبود؛ متن انگلیسی نمایش داده شد.</p>`;
      }
      else if(kind==='cites'){
        const items=val.items||[];
        if(!items.length) continue;
        /* collapsible sources — closed by default, one click opens the list */
        html+=`<div class="cites" id="cites-${rep.symbol}-${window.__citesN=(window.__citesN||0)+1}">`
              +`<button class="cites-toggle" onclick="this.parentElement.classList.toggle('open')" aria-expanded="false">`
              +`<span class="arrow">▶</span> 🔖 منابع این بخش (${toFa(items.length)} خبر) — برای نمایش کلیک کنید</button>`
              +`<div class="cites-body">`; 
        for(const it of items){
          html+=`<div class="cite">
            <span class="idx">${toFa(it.index_fa||it.index||'')}</span>
            <div class="body">
              <div class="t">${esc(it.title_fa||it.title_en)}</div>
              ${it.title_fa?`<div class="t-en">${esc(it.title_en)}</div>`:''}
              ${it.why_en&&!fa?`<div class="why">${esc(it.why_en)}</div>`:''}
              <div class="meta2">
                <span>📰 منبع: <b>${esc(it.source)}</b></span>
                <span>🗓 تاریخ: <b>${esc(it.date_fa||'—')}</b></span>
                <span>🕐 ساعت: <b>${esc(it.time_fa||'—')}</b></span>
                <span>✅ اعتبار: <b>${esc(it.credibility_fa||'')}</b></span>
                <a href="${esc(it.link)}" target="_blank" rel="noopener">مشاهده خبر ↗</a>
              </div>
            </div></div>`;
        }
        html+=`</div></div>`;   /* /cites-body /cites */
      }
    }
    html+=`</div><div id="chartCol"></div></div>`;
    box.innerHTML=html;
    window.__rep = rep;
    document.getElementById('chartCol').innerHTML=renderChartPanel(rep.chart);
    afterChartRender();
  }).catch(()=>box.innerHTML='<div class="empty">خطا در دریافت گزارش</div>');
}
/* mount chart for the current UI.chartMode (live candles or analytic SVG) */
function afterChartRender(){
  const rep=window.__rep; if(!rep) return;
  const sym=rep.symbol;
  if(UI.chartMode==='analytic'){ redrawChart(); return; }
  if(sym!==TVW.sym){ TVW.sym=sym; CAND.data=null; }
  loadCandles(sym, TVW.tf);
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

/* ── chart panel (the box beside the report text) ── */
function renderChartPanel(c){
  if(!c||c.empty) return `<div class="chartbox"><h3>📈 نمودار</h3><div class="empty">داده قیمت برای این دارایی در دسترس نیست.</div></div>`;
  const mode=(UI.chartMode==='analytic')?'analytic':'live';
  return `<div class="chartbox">
    <h3>📈 نمودار ${esc(c.icon||'')} ${esc(c.fa||c.sym)}
      <span style="font-size:10.5px;color:var(--muted);font-weight:400">${esc(c.sym)}</span></h3>
    <div class="csub" id="chartSub">${mode==='live'?'نمودار لایو بازار — کندل واقعی (منبع رایگان Yahoo Finance)':'همان داده‌ای که متن تحلیل از آن ساخته شده — '+toFa(c.n)+' کندل روزانه'}</div>
    <div class="mode-row">
      <span class="mlabel">نمودار:</span>
      <button class="tg ${mode==='live'?'on':''}" id="mLive" onclick="tvTimeframe('60')">🔴 لایو</button>
      <button class="tg ${mode==='live'&&TVW.tf==='5'?'on':''}" onclick="tvTimeframe('5')">۵ دقیقه</button>
      <button class="tg ${mode==='live'&&TVW.tf==='60'?'on':''}" onclick="tvTimeframe('60')">۱ ساعته</button>
      <button class="tg ${mode==='live'&&TVW.tf==='4h'?'on':''}" onclick="tvTimeframe('4h')">۴ ساعته</button>
      <button class="tg ${mode==='live'&&TVW.tf==='1d'?'on':''}" onclick="tvTimeframe('1d')">روزانه</button>
      <button class="tg ${mode==='analytic'?'on':''}" id="mAn" onclick="tvTimeframe('analytic')">📊 تحلیلی</button>
      <span class="chart-live" id="tvLiveTag" style="${mode==='live'?'':'display:none'}">⏳ …</span>
    </div>
    <div class="chart-head" style="${mode==='live'?'display:none':''}">
      <span class="p" id="chartLivePrice">${fmtPrice(c.price)}</span>
      <span style="display:flex;flex-direction:column;align-items:flex-end;gap:2px">
        <span class="c ${c.change_24h>=0?'up':'dn'}" id="chartLiveChg">${c.change_24h==null?'':((c.change_24h>=0?'▲ +':'▼ ')+num(c.change_24h,2)+'%')}</span>
        <span class="chart-live" id="chartLiveTag">⏳ منتظر قیمت لحظه‌ای…</span>
      </span>
    </div>
    <div class="toggles" style="${mode==='live'?'display:none':''}">
      <button class="tg ${CHART.bb?'on':''}" onclick="CHART.bb=!CHART.bb;redrawChart()">باند بولینگر</button>
      <button class="tg ${CHART.ema?'on':''}" onclick="CHART.ema=!CHART.ema;redrawChart()">میانگین‌ها</button>
      <button class="tg ${CHART.levels?'on':''}" onclick="CHART.levels=!CHART.levels;redrawChart()">حمایت/مقاومت</button>
      <button class="tg ${CHART.show?'on':''}" onclick="CHART.show=!CHART.show;redrawChart()">RSI/MACD</button>
    </div>
    <div id="tvwrap" class="tvwrap" style="${mode==='live'?'':'display:none'}">
      <div id="tvholder"></div>
      <div id="tvfail" class="empty" style="display:none">کندل لایو برای این دارایی در دسترس نیست — «📊 تحلیلی» را انتخاب کن</div>
    </div>
    <div id="panes" style="${mode==='live'?'display:none':''}"></div>
    <div class="legend" style="${mode==='live'?'display:none':''}">
      <span><i style="background:var(--copper)"></i>قیمت</span>
      <span><i style="background:var(--slate)"></i>EMA20</span>
      <span><i style="background:var(--copper-hi)"></i>EMA50</span>
      <span><i style="background:var(--copper-deep)"></i>EMA200</span>
      <span><i style="background:rgba(159,180,204,.35)"></i>حجم</span>
    </div>
    <div class="chart-notes" id="chartNotes" style="${mode==='live'?'display:none':''}"></div>
  </div>`;
}
/* ── live candlestick engine — candles from /api/candles (Yahoo v8, free, key-less) ── */
async function loadCandles(sym, tf){
  const holder=document.getElementById('tvholder'), fail=document.getElementById('tvfail'), tag=document.getElementById('tvLiveTag');
  if(!holder) return;
  if(CAND.sym!==sym||CAND.tf!==tf||!CAND.data)
    holder.innerHTML='<div class="empty" style="padding:34px;text-align:center">⏳ در حال دریافت کندل‌ها…</div>';
  if(fail) fail.style.display='none';
  try{
    const r=await fetch('/api/candles/'+encodeURIComponent(sym)+'?tf='+encodeURIComponent(tf));
    const d=await r.json();
    if(d.ok&&d.t&&d.t.length){
      CAND={sym:sym, tf:tf, data:d, at:Date.now()};
      if(UI.chartMode!=='analytic') drawCandles();
      if(tag) tag.innerHTML='<span class="live-dot"></span>لایو — '+toFa(fmtIran(new Date().toISOString()));
    }else if(CAND.sym===sym&&CAND.tf===tf){
      holder.innerHTML='';
      if(fail) fail.style.display='block';
    }
  }catch(e){
    if(CAND.sym===sym&&CAND.tf===tf&&fail) fail.style.display='block';
  }
}
function drawCandles(){
  const holder=document.getElementById('tvholder'); if(!holder||!CAND.data) return;
  holder.innerHTML=candlesSVG(CAND.data);
}
function faStampCandle(ts){
  const dte=new Date(ts*1000);
  if(TVW.tf==='1d'||TVW.tf==='D') return faDateFromIso(dte.toISOString().slice(0,10));
  const t=dte.toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'});
  return toFa(t)+' — '+faDateFromIso(dte.toISOString().slice(0,10));
}
/* TradingView-style candlestick chart in pure SVG — theme-coloured, no external deps */
function candlesSVG(d){
  const T=d.t, O=d.o, H=d.h, L=d.l, Cc=d.c, V=d.v||[];
  const n=T.length; if(!n) return '';
  const W=520, PADL=56, PADR=12, x0=PADL, x1=W-PADR;
  const inner=x1-x0, slot=inner/n, bw=Math.max(1.4, Math.min(14, slot*0.62));
  const H1=300, y0=16, y1=H1-24;
  const hv=Math.max(...H.filter(v=>v!=null)), lv=Math.min(...L.filter(v=>v!=null));
  const pad=(hv-lv)*0.05||1; const mn=lv-pad, mx=hv+pad;
  const Y=mkY(y0,y1,mn,mx);
  const X=i=>x0+slot*(i+0.5);
  let html='';
  for(let g=0;g<=4;g++){
    const v=mn+(mx-mn)*g/4, y=Y(v);
    html+=`<line x1="${x0}" y1="${y.toFixed(1)}" x2="${x1}" y2="${y.toFixed(1)}" stroke="${C.grid}"/>`+
          `<text x="${x0-7}" y="${(y+3.5).toFixed(1)}" fill="${C.axis}" font-size="9" text-anchor="end">${num(v,mx>=1000?0:2)}</text>`;
  }
  const vb=Math.max(1,Math.floor(n/6));
  for(let i=0;i<n;i+=vb){
    html+=`<text x="${X(i).toFixed(1)}" y="${H1-8}" fill="${C.axis}" font-size="8.5" text-anchor="middle">${faStampCandle(T[i])}</text>`;
  }
  for(let i=0;i<n;i++){
    if(O[i]==null||Cc[i]==null||H[i]==null||L[i]==null) continue;
    const up=Cc[i]>=O[i], col=up?C.cup:C.cdn, x=X(i);
    const yH=Y(H[i]), yL=Y(L[i]), yO=Y(O[i]), yC=Y(Cc[i]);
    html+=`<line x1="${x.toFixed(1)}" y1="${yH.toFixed(1)}" x2="${x.toFixed(1)}" y2="${yL.toFixed(1)}" stroke="${col}" stroke-width="1"/>`;
    const top=Math.min(yO,yC), hgt=Math.max(1.2, Math.abs(yC-yO));
    html+=`<rect x="${(x-bw/2).toFixed(1)}" y="${top.toFixed(1)}" width="${bw.toFixed(1)}" height="${hgt.toFixed(1)}" fill="${col}"/>`;
  }
  if(V.some(v=>v!=null&&v>0)){
    const vmax=Math.max(...V.filter(v=>v!=null),1), vh=34, vy1=H1-26;
    for(let i=0;i<n;i++){
      const v=V[i]; if(v==null) continue;
      const up=Cc[i]!=null&&O[i]!=null&&Cc[i]>=O[i];
      const h=(v/vmax)*vh;
      html+=`<rect x="${(X(i)-bw/2).toFixed(1)}" y="${(vy1-h).toFixed(1)}" width="${bw.toFixed(1)}" height="${h.toFixed(1)}" fill="${up?'rgba(163,196,180,.25)':'rgba(201,124,107,.25)'}"/>`;
    }
  }
  const last=Cc[n-1];
  if(last!=null) html+=`<circle cx="${X(n-1).toFixed(1)}" cy="${Y(last).toFixed(1)}" r="3" fill="${C.priceTxt}"/>`;
  const tfLabel={'5':'کندل ۵ دقیقه','60':'کندل ۱ ساعته','4h':'کندل ۴ ساعته','1d':'کندل روزانه'}[d.tf]||'';
  const head=`<div class="tvhead"><span class="p">${fmtPrice(last)}</span>`+
    `<span class="chg ${Cc[n-1]>=O[n-1]?'up':'dn'}">${Cc[n-1]>=O[n-1]?'▲':'▼'} ${d.icon||''} ${esc(d.fa||d.sym)}</span>`+
    `<span style="font-size:10px;color:var(--muted)">${tfLabel} · ${toFa(n)} کندل · بروزرسانی خودکار هر دقیقه</span></div>`;
  return head+`<svg class="pane tvpane" viewBox="0 0 ${W} ${H1}" preserveAspectRatio="none">${html}</svg>`;
}
function tvTimeframe(tf){
  UI.chartMode=(tf==='analytic')?'analytic':'live';
  if(UI.chartMode==='live') TVW.tf=tf;
  const rep=window.__rep;
  if(rep){ document.getElementById('chartCol').innerHTML=renderChartPanel(rep.chart); afterChartRender(); }
  else if(UI.chartMode==='live') afterChartRender();
}
/* DL2: duplicate redrawChart() removed — the live-price-aware definition lower
   in this file wins in JS anyway, so the shadowed one was dead code. */

/* merge the live quote into the chart head + last point of the price line */
function updateChartLive(){
  const rep=window.__rep; if(!rep||!rep.chart) return;
  if(UI.chartMode!=='analytic') return;   /* حالت لایو: قیمت را خود کندل‌ها نشان می‌دهند */
  const sym=rep.symbol, lv=liveOf(sym);
  const p=document.getElementById('chartLivePrice'), chg=document.getElementById('chartLiveChg'), tag=document.getElementById('chartLiveTag');
  if(!p) return;
  if(lv&&lv.price!=null){
    const prev=+p.dataset.v||rep.chart.price;
    p.textContent=fmtPrice(lv.price);
    flash(p, lv.price-prev);
    p.dataset.v=lv.price;
    if(chg&&lv.change_24h!=null){ chg.textContent=(lv.change_24h>=0?'▲ +':'▼ ')+num(lv.change_24h,2)+'%'; chg.className='c '+(lv.change_24h>=0?'up':'dn'); }
    if(tag) tag.innerHTML='<span class="live-dot"></span>لایو — '+toFa(fmtIran(new Date().toISOString()));
    redrawChart(lv.price);
  } else if(tag){ tag.textContent='قیمت لحظه‌ای برای این دارایی در دسترس نیست'; }
}
/* tiny SVG helpers — every pane maps values through its own y() function */
function pathMap(vals,X,Y,from,to){
  let d='', open=false;
  const start=from||0, end=(to==null?vals.length:to);
  for(let i=start;i<end;i++){
    const v=vals?vals[i]:null;
    if(v==null||isNaN(v)){ open=false; continue; }
    const x=X(i), y=Y(v);
    d+=(open?'L':'M')+x.toFixed(1)+' '+y.toFixed(1)+' '; open=true;
  }
  return d;
}
function mkY(y0,y1,mn,mx){ return v=>y1-(y1-y0)*((v-mn)/((mx-mn)||1)); }
function lastValid(vals){ for(let i=(vals?vals.length:0)-1;i>=0;i--){ if(vals[i]!=null&&!isNaN(vals[i])) return {v:vals[i],i:i}; } return null; }

function panesSVG(c, livePrice){
  const W=520, PADL=56, PADR=12, x0=PADL, x1=W-PADR;
  const closes=(c.closes||[]).slice();
  if(livePrice!=null){ if(closes.length) closes[closes.length-1]=livePrice; else closes.push(livePrice); }
  const n=closes.length || 1;
  const XI=i=>x0+(x1-x0)*(n<2?0:i/(n-1));
  const bw=Math.max(1.2,(x1-x0)/n-0.8);
  let html='';

  const band=[...(CHART.bb?(c.bb_up||[]).concat(c.bb_low||[]):[]),
              ...(CHART.ema?(c.ema200||[]).filter(v=>v!=null):[]),
              ...closes];
  const valid=band.filter(v=>v!=null&&!isNaN(v));
  let mn=Math.min(...(valid.length?valid:[0])), mx=Math.max(...(valid.length?valid:[1]));
  const pad=(mx-mn)*0.06||1; mn-=pad; mx+=pad;
  const H=252, y0=14, y1=H-22;
  const Y=mkY(y0,y1,mn,mx);

  // Bollinger envelope
  if(CHART.bb && c.bb_up && c.bb_low){
    const up=[], lo=[];
    for(let i=0;i<c.bb_up.length;i++){
      if(c.bb_up[i]!=null&&c.bb_low[i]!=null){ up.push(XI(i).toFixed(1)+' '+Y(c.bb_up[i]).toFixed(1)); lo.push(XI(i).toFixed(1)+' '+Y(c.bb_low[i]).toFixed(1)); }
    }
    if(up.length) html+=`<polygon points="${up.concat(lo.reverse()).join(' ')}" fill="${C.band}" stroke="${C.bandLine}" stroke-width="1"/>`;
  }
  // grey gridlines + price axis
  for(let g=0;g<=4;g++){
    const v=mn+(mx-mn)*g/4, y=Y(v);
    html+=`<line x1="${x0}" y1="${y.toFixed(1)}" x2="${x1}" y2="${y.toFixed(1)}" stroke="${C.grid}"/>
           <text x="${x0-7}" y="${(y+3.5).toFixed(1)}" fill="${C.axis}" font-size="9" text-anchor="end">${num(v,mx>=1000?0:2)}</text>`;
  }
  // support / resistance
  if(CHART.levels){
    for(const [nm,v,col] of [['حمایت',c.support,C.sup],['مقاومت',c.resistance,C.res]]){
      if(v==null) continue;
      const y=Y(v);
      html+=`<line x1="${x0}" y1="${y.toFixed(1)}" x2="${x1}" y2="${y.toFixed(1)}" stroke="${col}" stroke-dasharray="5 4" opacity=".8"/>
             <text x="${x1-4}" y="${(y-4).toFixed(1)}" fill="${col}" font-size="9" text-anchor="end">${nm}</text>`;
    }
  }
  // EMAs
  if(CHART.ema){
    for(const [key,col] of [['ema20',C.ema20],['ema50',C.ema50],['ema200',C.ema200]]){
      const s=c[key]; if(!s||!s.some(v=>v!=null)) continue;
      html+=`<path d="${pathMap(s,XI,Y)}" fill="none" stroke="${col}" stroke-width="1.5"/>`;
    }
  }
  // price + marker
  html+=`<path d="${pathMap(closes,XI,Y)}" fill="none" stroke="${C.price}" stroke-width="2"/>`;
  const lp=lastValid(closes);
  if(lp) html+=`<circle cx="${XI(lp.i).toFixed(1)}" cy="${Y(lp.v).toFixed(1)}" r="3.2" fill="${C.priceTxt}"/>`;
  // date axis
  if(c.dates&&c.dates.length){
    html+=`<text x="${x0}" y="${H-5}" fill="${C.axis}" font-size="9.5">${faDateFromIso(c.dates[0])}</text>
           <text x="${x1}" y="${H-5}" fill="${C.axis}" font-size="9.5" text-anchor="end">${faDateFromIso(c.dates[c.dates.length-1])}</text>`;
  }
  let out=`<svg class="pane" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${html}</svg>`;

  if(CHART.show){
    // RSI pane
    const RH=82, ry0=12, ry1=RH-16;
    const Yr=mkY(ry0,ry1,0,100);
    let r='';
    for(const lvl of [70,30]){
      const y=Yr(lvl);
      r+=`<line x1="${x0}" y1="${y.toFixed(1)}" x2="${x1}" y2="${y.toFixed(1)}" stroke="${lvl===70?C.res:C.sup}" stroke-dasharray="4 4" opacity=".55"/>
          <text x="${x0-7}" y="${(y+3.5).toFixed(1)}" fill="${C.axis}" font-size="9" text-anchor="end">${lvl}</text>`;
    }
    r+=`<path d="${pathMap(c.rsi,XI,Yr)}" fill="none" stroke="${C.rsi}" stroke-width="1.6"/>`;
    const rl=lastValid(c.rsi);
    if(rl) r+=`<text x="${(XI(rl.i)-6).toFixed(1)}" y="${(Yr(rl.v)+3).toFixed(1)}" fill="${C.rsi}" font-size="9.5" text-anchor="end">RSI ${num(rl.v,1)}</text>`;
    out+=`<svg class="pane" viewBox="0 0 ${W} ${RH}" preserveAspectRatio="none">${r}</svg>`;

    // MACD pane
    const MH=86, my0=12, my1=MH-14;
    const hh=(c.macd_hist||[]).filter(v=>v!=null&&!isNaN(v));
    const mmax=Math.max(1e-9,...[...(c.macd||[]),...(c.macd_signal||[]),...hh].filter(v=>v!=null).map(v=>Math.abs(v)));
    const Ym=mkY(my0,my1,-mmax,mmax);
    const zero=Ym(0);
    let m=''; // histogram bars first
    (c.macd_hist||[]).forEach((v,i)=>{
      if(v==null||isNaN(v)) return;
      const y=Ym(v);
      m+=`<rect x="${(XI(i)-bw/2).toFixed(1)}" y="${Math.min(zero,y).toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(0.6,Math.abs(y-zero)).toFixed(1)}" fill="${v>=0?C.up:C.down}"/>`;
    });
    m+=`<line x1="${x0}" y1="${zero.toFixed(1)}" x2="${x1}" y2="${zero.toFixed(1)}" stroke="${C.grid}"/>`;
    m+=`<path d="${pathMap(c.macd_signal,XI,Ym)}" fill="none" stroke="${C.ema50}" stroke-width="1.3"/>`;
    m+=`<path d="${pathMap(c.macd,XI,Ym)}" fill="none" stroke="${C.ema20}" stroke-width="1.5"/>`;
    out+=`<svg class="pane" viewBox="0 0 ${W} ${MH}" preserveAspectRatio="none">${m}
      <text x="${x0-7}" y="${(zero+3.5).toFixed(1)}" fill="${C.axis}" font-size="9" text-anchor="end">MACD</text></svg>`;

    // volume pane
    const VH=58;
    const vols=c.volumes||[], vmax=Math.max(...vols.filter(v=>v!=null),1);
    let vv='';
    vols.forEach((v,i)=>{
      if(v==null) return;
      const h=(v/vmax)*(VH-14);
      vv+=`<rect x="${(XI(i)-bw/2).toFixed(1)}" y="${(VH-6-h).toFixed(1)}" width="${bw.toFixed(1)}" height="${h.toFixed(1)}" fill="${C.vol}"/>`;
    });
    out+=`<svg class="pane" viewBox="0 0 ${W} ${VH}" preserveAspectRatio="none">${vv}
      <text x="${x0-7}" y="${VH-10}" fill="${C.axis}" font-size="9" text-anchor="end">حجم</text></svg>`;
  }
  return out;
}
function redrawChartWithLive(){ if(UI.chartMode!=='analytic') return; if(window.__rep&&window.__rep.chart){ const lv=liveOf(window.__rep.symbol); document.getElementById('panes').innerHTML=panesSVG(window.__rep.chart, lv?lv.price:null); document.getElementById('chartNotes').innerHTML=notesHTML(window.__rep.chart); } }
/* live mode: refresh candles every 60s and pin the last close to the live quote */
function updateCandlesLive(){
  if(UI.chartMode!=='analytic'&&window.__rep){
    const sym=window.__rep.symbol;
    if(sym!==TVW.sym){ TVW.sym=sym; CAND.data=null; }
    if(!CAND.loading) loadCandles(sym, TVW.tf);
    if(CAND.data&&CAND.sym===sym){
      const lv=liveOf(sym);
      if(lv&&lv.price!=null){ CAND.data.c[CAND.data.c.length-1]=lv.price;
        CAND.data.h[CAND.data.h.length-1]=Math.max(CAND.data.h[CAND.data.h.length-1],lv.price);
        CAND.data.l[CAND.data.l.length-1]=Math.min(CAND.data.l[CAND.data.l.length-1],lv.price); }
      drawCandles();
      const tag=document.getElementById('tvLiveTag');
      if(tag&&lv) tag.innerHTML='<span class="live-dot"></span>لایو — '+toFa(fmtIran(new Date().toISOString()));
    }
  }
}
function redrawChart(){ redrawChartWithLive(); }
function notesHTML(c){
  const closes=(c.closes||[]).filter(v=>v!=null);
  const last=c.price!=null?c.price:(closes.length?closes[closes.length-1]:null);
  const e20=c.ema20&&c.ema20.filter(v=>v!=null), e50=c.ema50&&c.ema50.filter(v=>v!=null), e200=c.ema200&&c.ema200.filter(v=>v!=null);
  const L=a=>a&&a.length?a[a.length-1]:null;
  const rsi=L(c.rsi&&c.rsi.filter(v=>v!=null));
  const hist=L(c.macd_hist&&c.macd_hist.filter(v=>v!=null));
  let trend='نامشخص';
  if(last!=null&&L(e50)!=null){
    if(last>L(e50)&&(L(e200)==null||last>L(e200))) trend='صعودی/سازنده (بالای میانگین‌ها)';
    else if(last<L(e50)&&L(e200)!=null&&last<L(e200)) trend='نزولی/تدافعی (زیر میانگین‌ها)';
    else trend='خنثی و در محدوده (میانگین‌ها درهم‌تنیده)';
  }
  let rsiTxt='—';
  if(rsi!=null) rsiTxt = rsi>=70?'اشباع خرید':(rsi<=30?'اشباع فروش':'خنثی')+' ('+num(rsi,1)+')';
  const macdTxt = hist==null?'—':(hist>0?'مومنتوم مثبت (بالای خط سیگنال)':'مومنتوم منفی (زیر خط سیگنال)');
  const bbw = (c.bb_up&&c.bb_low&&c.bb_up.length&&c.bb_low.length)
    ? ((c.bb_up[c.bb_up.length-1]-c.bb_low[c.bb_low.length-1])/last*100) : null;
  const atrP = (c.atr14&&last)?(c.atr14/last*100):null;
  return `<b>این نمودارها همان داده‌ای هستند که متن تحلیل بالا از آن نوشته شده:</b>
    <ul>
      <li>ساختار روند: <b>${trend}</b></li>
      <li>RSI(14): <b>${rsiTxt}</b> · MACD: <b>${macdTxt}</b></li>
      <li>محدوده حمایت: <b>${c.support!=null?num(c.support,c.support>=1000?0:2):'—'}</b> · مقاومت: <b>${c.resistance!=null?num(c.resistance,c.resistance>=1000?0:2):'—'}</b></li>
      <li>پهنای باند بولینگر: <b>${bbw!=null?toFa(num(bbw,1))+'٪':'—'}</b> از میانه · نوسان روزانه (ATR): <b>${atrP!=null?toFa(num(atrP,1))+'٪':'—'}</b></li>
      <li>نقطه آخر خط قیمت، قیمت لحظه‌ای لایو است (هر ۱۵ ثانیه از API رایگان بروز می‌شود).</li>
      <li>خطوط آبی روشن/تیره: میانگین‌های متحرک ۲۰/۵۰ روز — مرزهای اصلی تغییر روند.</li>
      <li>خطوط سبز و قرمز نقطه‌چین: نزدیک‌ترین حمایت و مقاومت ۶۰ روز گذشته.</li>
    </ul>`;
}
/* ── sources ── */
function renderSources(){
  const list=DATA.sources;
  document.getElementById('srcCount').textContent=toFa(list.filter(s=>s.enabled).length)+' فعال از '+toFa(list.length);
  const groups={};
  for(const s of list){ (groups[s.kind_fa]=groups[s.kind_fa]||[]).push(s); }
  let html='';
  for(const [kind,items] of Object.entries(groups)){
    const on=items.filter(x=>x.enabled).length;
    html+=`<div class="kindgroup">
      <div class="kh"><span>${esc(kind)}</span><span style="font-size:11px;color:var(--muted)">${toFa(on)}/${toFa(items.length)} فعال</span></div>
      <div class="kb">${items.map(s=>`
        <div class="srcrow">
          <label class="switch"><input type="checkbox" ${s.enabled?'checked':''} onchange="toggleSrc('${s.key}',this.checked)"><span class="slider"></span></label>
          <span class="nm">${esc(s.name)}</span>
          <span class="trust">اعتماد ${toFa(Math.round(s.trust*100))}٪</span>
          <span class="url" title="${esc(s.url)}">${esc(s.url)}</span>
          <span style="font-size:10.5px" class="${s.last_ok===false?'bad':'ok'}">${s.last_count==null?'—':(s.last_ok?('✓ '+toFa(s.last_count)+' خبر'):'✗ قطع')}</span>
          ${s.type==='custom'?`<button class="btn ghost sm" onclick="removeSrc('${s.key}')">حذف</button>`:''}
        </div>`).join('')}</div></div>`;
  }
  document.getElementById('srcList').innerHTML=html;
}
async function toggleSrc(key,on){
  await postSettings({source_updates:{[key]:on}});
  toast('منبع بروزرسانی شد — در چرخه بعدی اعمال می‌شود');
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
    rows+=`<tr>
      <td>${m.icon||''} ${esc(m.fa)}</td>
      <td>${esc(m.name||'')}</td>
      <td class="ltr">${esc(m.yahoo||'—')}</td>
      <td class="ltr">${esc(m.coingecko||'—')}</td>
      <td class="ltr">${fmtPrice(price)}${lv?' <span class="live-dot"></span>':''}${m.custom&&d.price==null&&!lv?' <span style="color:var(--copper-hi);font-size:10px" title="نماد Yahoo برای این دارایی داده نداد — آن را اصلاح کن (مثلاً LINK-USD)">⚠</span>':''}</td>
      <td class="ltr">${toFa(DATA.asset_counts[sym]||0)}</td>
      <td>${m.custom?`<button class="btn ghost sm" onclick="removeAsset('${sym}')">حذف</button>`:'<span style="font-size:10px;color:var(--muted)">پیش‌فرض</span>'}</td>
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
  toast('دارایی حذف شد'); loadData();
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
    return `<button class="chip ${on?'on':''}" data-sym="${s}" onclick="this.classList.toggle('on')">${m.icon||''} ${esc(m.fa)}</button>`;
  }).join('');
}
async function saveSettings(){
  const assets=[...document.querySelectorAll('#assetToggles .chip.on')].map(b=>b.dataset.sym);
  if(!assets.length){ toast('حداقل یک دارایی انتخاب کنید'); return; }
  await postSettings({interval:+document.getElementById('setInterval').value,
                      report_max_age_hours:+document.getElementById('setAge').value,
                      assets, auto_reports:document.getElementById('setAutoRep').checked});
  toast('تنظیمات ذخیره شد ✓'); loadData();
}
async function postSettings(payload){
  const r=await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  return r.json();
}

/* ── refresh / toast ── */
async function doRefresh(){
  const rb=document.getElementById('refreshBtn'); rb.disabled=true; rb.textContent='⏳ ارسال درخواست…';
  try{ await fetch('/api/refresh',{method:'POST'}); toast('چرخه بروزرسانی شروع شد'); }
  finally{ setTimeout(()=>{rb.disabled=false;rb.textContent='⟳ بروزرسانی فوری';},1500); }
}
function toast(msg){
  const t=document.getElementById('toast'); t.textContent=msg; t.style.display='block';
  clearTimeout(t._h); t._h=setTimeout(()=>t.style.display='none',2600);
}
document.addEventListener('keydown',e=>{ if(e.key==='Escape'){ closeModal('artOverlay'); closeModal('blurbOverlay'); } });
document.getElementById('ibSources').onclick=()=>showView('sources');
document.getElementById('ibAssets').onclick=()=>showView('assets');

/* ═══════════ economic calendar & market context (/api/econ) ═══════════ */
let ECON=null, ECON_AT=0;
async function loadCalendar(){
  try{
    const r=await fetch('/api/econ'); const d=await r.json();
    ECON=d; ECON_AT=Date.now(); window.__MACRO=d.macro||[]; renderAssets(); renderCalendar();
  }catch(e){ renderCalendar(); }
}
const FA_DAY={'Saturday':'شنبه','Sunday':'یکشنبه','Monday':'دوشنبه','Tuesday':'سه‌شنبه','Wednesday':'چهارشنبه','Thursday':'پنجشنبه','Friday':'جمعه'};
const FA_MONTH={'Farvardin':'فروردین','Ordibehesht':'اردیبهشت','Khordad':'خرداد','Tir':'تیر','Mordad':'مرداد','Shahrivar':'شهریور','Mehr':'مهر','Aban':'آبان','Azar':'آذر','Dey':'دی','Bahman':'بهمن','Esfand':'اسفند'};
function isoOf(d){ return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'); }
function todayIso(){ return isoOf(new Date()); }
function shiftCalDay(n){
  const base = window.__calDay ? new Date(window.__calDay+'T12:00:00') : new Date();
  base.setDate(base.getDate()+n);
  window.__calDay = isoOf(base);
  renderCalendar();
}
function gotoCalToday(){ window.__calDay = todayIso(); renderCalendar(); }
function jumpToNextEventDay(){
  const days=[...new Set((window.__calPool||[]).map(e=>e.day))].sort();
  if(!days.length) return;
  const cur=window.__calDay||todayIso();
  window.__calDay = days.find(d=>d>=cur) || days[days.length-1];
  renderCalendar();
}
function faDayBox(isoDay){
  /* English day header: "Thursday, Sep 26" — the calendar is English-only */
  try{
    const d=new Date(isoDay+'T12:00:00');
    return esc(d.toLocaleDateString('en-US',{weekday:'long',month:'short',day:'numeric'}));
  }catch(e){ return esc(isoDay); }
}
function perDayCountdown(e){
  /* live segmented countdown — boxed digits, one segment per unit */
  let s=Math.max(0,Math.round(e.ts-Date.now()/1000));
  const d=Math.floor(s/86400); s%=86400; const h=Math.floor(s/3600); s%=3600; const m=Math.floor(s/60); s%=60;
  const two=n=>String(n).padStart(2,'0');
  const seg=(v,l)=>`<span class="sg"><b>${v}</b><small>${l}</small></span>`;
  /* all four cells always present — the box can never change width mid-countdown */
  return seg(d,'d')+seg(two(h),'h')+seg(two(m),'m')+seg(two(s),'s');
}
function renderCalendar(){
  const box=document.getElementById('calDays'), cd=document.getElementById('calCountdown');
  if(!ECON){ box.innerHTML='<div class="empty">Loading calendar…</div>'; return; }
  window.__ECON_FA=ECON.fng_fa||{};
  if(ECON.fng&&ECON.fng.now!=null) window.__FNG=ECON.fng;
  /* pool this week + next week (deduped) so one day can be walked in both directions */
  const pool=[], seen={};
  for(const src of [ECON.calendar||{}, ECON.calendar_next||{}]){
    for(const e of (src.events||[])){
      const k=[e.day,e.time_str,e.title,e.country||''].join('|');
      if(seen[k]) continue; seen[k]=1; pool.push(e);
    }
  }
  pool.sort((a,b)=>a.ts-b.ts);
  window.__calPool = pool;
  const selDay = window.__calDay || todayIso();
  window.__calDay = selDay;
  const dayEl=document.getElementById('calDayNow');
  if(dayEl){ dayEl.innerHTML=faDayBox(selDay); dayEl.classList.toggle('is-today', selDay===todayIso()); }
  const todayBtn=document.getElementById('calBtnToday');
  if(todayBtn) todayBtn.classList.toggle('on', selDay===todayIso());
  const evsAll=pool;
  const hi=evsAll.filter(e=>!e.past&&e.impact==='High');
  const nb=document.getElementById('cntEvents');
  if(hi.length){ nb.style.display='inline-block'; nb.textContent=toFa(hi.length); }
  else nb.style.display='none';
  /* countdown tick — next High-impact event (+ released strip once it drops) */
  const rel=document.getElementById('calReleased');
  clearInterval(window.__calTick);
  const tick=()=>{
    if(!hi.length){ cd.innerHTML='No high-impact events left in this window'; rel.style.display='none'; return; }
    let s=Math.round(hi[0].ts-Date.now()/1000);
    if(s<=0){   /* event just came out — mark released instead of showing a stuck timer */
      rel.style.display='flex';
      rel.innerHTML=`<span class="ev-check">✔</span> Released: <b>${esc(hi[0].title)}</b> ${hi[0].flag||''} <span class="ltr" style="font-weight:400">${esc(hi[0].time_str||'')}</span>`;
      const nx=evsAll.find(e=>!e.past&&e.impact==='High'&&e.ts>hi[0].ts);
      cd.innerHTML=nx?('Released — next high impact: '+esc(nx.title)+' '+(nx.flag||'')):'No high-impact events left in this window';
      return;
    }
    rel.style.display='none';
    const d=Math.floor(s/86400); s%=86400; const h=Math.floor(s/3600); s%=3600; const m=Math.floor(s/60);
    cd.innerHTML=`<b>${d}</b>d <b>${h}</b>h <b>${m}</b>m until ${esc(hi[0].title)} ${hi[0].flag||''}`;
  };
  tick(); window.__calTick=setInterval(tick,30000);
  const sum=document.getElementById('calSummary');
  if(sum) sum.textContent=`${evsAll.length} events · ${hi.length} high-impact upcoming`;
  /* ETF flows moved to their own tab — calendar keeps sessions only */
  renderEtfFlows(document.getElementById('etfBox2'));
  renderEtfLive('etfLive2');
  renderSessions();
  /* ---- events: filter → sort → group per day ---- */
  /* ---- events: filter → sort → group per day ---- */
  const impSel=document.getElementById('calImpact'), cSel=document.getElementById('calCountry'),
        sSel=document.getElementById('calSort'), hp=document.getElementById('calHidePast');
  if(cSel&&!cSel.options.length){
    const countries=[...new Set(evsAll.map(e=>e.country).filter(Boolean))];
    cSel.innerHTML='<option value="all">All currencies</option>'+countries.map(c=>`<option value="${esc(c)}">${c}</option>`).join('');
  }
  let evs=[...evsAll];
  const imp=impSel?impSel.value:'all';
  if(imp==='High') evs=evs.filter(e=>e.impact==='High');
  else if(imp==='Medium') evs=evs.filter(e=>e.impact==='High'||e.impact==='Medium');
  else if(imp==='Low') evs=evs.filter(e=>e.impact==='High'||e.impact==='Medium'||e.impact==='Low');
  const ctry=cSel?cSel.value:'all';
  if(ctry!=='all') evs=evs.filter(e=>e.country===ctry);
  /* one day at a time — that is the whole point of the day navigator */
  evs=evs.filter(e=>e.day===selDay);
  if(hp&&hp.checked) evs=evs.filter(e=>!e.past);
  const srt=sSel?sSel.value:'ff';
  const impRank={High:0,Medium:1,Low:2,Holiday:3};
  if(srt==='impact') evs.sort((a,b)=>(impRank[a.impact]??9)-(impRank[b.impact]??9)||a.ts-b.ts);
  else if(srt==='time') evs.sort((a,b)=>b.ts-a.ts);  /* newest releases first */
  else evs.sort((a,b)=>a.ts-b.ts);                   /* FF: strict chronological, like the site */
  /* a single day box */
  const list=evs;
  const hiDay=list.filter(e=>e.impact==='High').length;
  const rows=list.map(e=>{
      const released=!!(e.actual||e.past);   /* feed rarely fills actual — time passed = released */
      const bd=e.impact==='High'?'badge-hi':(e.impact==='Medium'?'badge-md':'badge-lo');
      const il=e.impact==='High'?'🔴':(e.impact==='Medium'?'🟡':'⚪');
      const tickEl=!e.past?`<span class="cal-timer" data-ts="${e.ts}" role="timer"></span>`:'';
      const apart=released?`<span class="ev-actual"><span class="ev-check">✔</span> Released${e.actual?`: <b class="num">${esc(e.actual)}</b>`:''}</span>`:'';
      const fpart=(e.forecast&&e.forecast!=='—')
        ?`<span class="cal-fcst" title="Analyst forecast">FCST <b class="ltr">${esc(e.forecast)}</b></span>`:'';
      const ppart=(e.previous&&e.previous!=='—')
        ?`<span class="cal-prev" title="Previous print">PREV <b class="ltr">${esc(e.previous)}</b></span>`:'';
      return `<div class="calrow ${released?'released':(e.past?'past':'')}">
        <span class="ltr" style="min-width:52px;font-weight:700;color:var(--body)">${esc(e.time_str||'')}</span>
        <span title="${esc(e.country)}">${e.flag}</span>
        <span style="flex:1;min-width:140px" class="ev-title">${esc(e.title)}</span>
        <span class="badge ${bd}">${il} ${e.impact}</span>
        ${tickEl}${fpart}${ppart}${apart}
      </div>`;
    }).join('');
  clearInterval(window.__dayTick);
  box.innerHTML=rows
    ? `<div class="calday">
      <div class="calday-h">
        <span class="calday-title">🗓 ${faDayBox(selDay)}</span>
        <span class="calday-meta" style="direction:ltr">${list.length} events${hiDay?` · <span style="color:var(--red)">${hiDay} high</span>`:''}</span>
      </div>
      ${rows}
    </div>`
    : ((window.__calPool||[]).length
        ? `<div class="empty">No events scheduled on ${faDayBox(selDay)}.<br>
             <button class="btn ghost sm" style="margin-top:14px" onclick="jumpToNextEventDay()">Jump to the next day with events →</button></div>`
        : '<div class="empty">No calendar data for this day — the feed covers this week and next.</div>');
  /* per-event ticking clocks — painted immediately (an empty box for the first
     second looked like the timer had been cut off), then once a second */
  const paintTimers=()=>{
    document.querySelectorAll('.cal-timer').forEach(el=>{
      const ts=+el.dataset.ts; if(!ts) return;
      if(ts<=Date.now()/1000){   /* time reached — swap the ticking clock for a released chip */
        el.outerHTML='<span class="ev-actual"><span class="ev-check">✔</span> Released</span>';
        return;
      }
      el.innerHTML=perDayCountdown({ts});
    });
  };
  clearInterval(window.__dayTick);
  paintTimers();
  window.__dayTick=setInterval(paintTimers,1000);
}
/* ── ETF flows table into any target box (calendar kept minimal; flows live in ETF tab) ── */
function renderEtfFlows(eb){
  if(!eb||!ECON) return;
  const etf=ECON.etf||{};
  if(etf.rows&&etf.rows.length){
    eb.innerHTML='<table class="etftab">'+etf.rows.map(r=>{
      const pos=r.total_musd>=0;
      return `<tr><td>${esc(r.date)}</td><td>${pos?'⬆ +':'⬇ −'}${num(Math.abs(r.total_musd),1)}<span style="color:var(--muted)"> $M</span></td>
        <td style="width:45%">${flowBar(r.total_musd)}</td></tr>`;
    }).join('')+'</table>';
  } else eb.innerHTML='<span style="color:var(--muted)">ETF flow data temporarily unavailable.</span>';
}
function renderEtfTab(){ renderEtfFlows(document.getElementById('etfBox2')); renderEtfLive('etfLive2'); }
/* ── market sessions ── */
function renderSessions(){
  const box=document.getElementById('sessionsBox'); if(!box||!ECON) return;
  const ss=ECON.sessions||[];
  if(!ss.length){ box.innerHTML='<span style="color:var(--muted)">Sessions temporarily unavailable.</span>'; return; }
  box.innerHTML=ss.map(s=>{
    const st=s.open?'OPEN':'CLOSED';
    const h=Math.floor(s.mins_to_change/60), m=s.mins_to_change%60;
    const to=s.open?`closes in ${toFa(h)}h ${toFa(String(m).padStart(2,'0'))}m`:`opens in ${toFa(h)}h ${toFa(String(m).padStart(2,'0'))}m`;
    return `<div class="session ${s.open?'on':'off'}">
      <span class="ic">${s.icon}</span>
      <span class="lbl">${esc(s.label)}</span>
      <span class="dot" title="${st}"></span>
      <span class="state">${st}</span>
      <span class="eta">${to}</span>
    </div>`;
  }).join('')
  +`<div class="hint" style="margin-top:8px;font-size:10px">Weekly schedule, UTC — live clock updates every minute.</div>`;
  if(window.__sessTick) clearInterval(window.__sessTick);
  window.__sessTick=setInterval(()=>{ if(UI.view==='calendar'&&ECON) renderSessions(); },60000);
}
/* ── TradingView ideas list (ETF tab sidebar) ── */
async function loadIdeas(){
  const box=document.getElementById('ideasBox'); if(!box) return;
  try{
    const d=await (await fetch('/api/ideas?sym=BTC')).json();
    if(!d.ok||!d.items.length){ box.innerHTML='<span style="color:var(--muted)">Ideas temporarily unavailable.</span>'; return; }
    box.innerHTML=d.items.map(x=>`
      <a class="idea" href="${esc(x.link)}" target="_blank" rel="noopener">
        <span class="dir ${x.symbol_dir==='Long'?'up':x.symbol_dir==='Short'?'dn':''}">${x.symbol_dir?(x.symbol_dir==='Long'?'▲ Long':'▼ Short'):'•'}</span>
        <span class="ttl">${esc(x.title)}</span>
        <span class="meta">${x.hot?'🔥 ':''}❤ ${toFa(x.likes)} · 👁 ${toFa(x.views)} · ${esc(x.user)}</span>
      </a>`).join('');
  }catch(e){ box.innerHTML='<span style="color:var(--muted)">Ideas temporarily unavailable.</span>'; }
}
/* ── live ETF quote cards (Yahoo, 60s cache server-side) ── */
function renderEtfLive(targetId){
  const box=document.getElementById(targetId||'etfLive'); if(!box) return;
  const q=window.__ETFQ||{};
  const syms=Object.keys(q);
  if(!syms.length){ box.innerHTML='<span style="color:var(--muted)">کوت لایو ETF موقتاً در دسترس نیست.</span>'; return; }
  box.innerHTML=syms.map(s=>{
    const x=q[s], ch=x.change_pct==null?null:x.change_pct;
    const cls=ch==null?'':(ch>=0?'up':'dn');
    return `<div class="etfcard">${x.group?`<span class="grp">${esc(x.group)}</span>`:''}<div class="tk">${s}</div><div class="nm">${esc(x.name||'')}</div>
      <div class="prc">${x.price!=null?'$'+num(x.price,2):'—'}</div>
      <div class="chg ${cls}">${ch==null?'':(ch>=0?'▲ +':'▼ ')+num(ch,2)+'%'}</div>
      ${x.market_state?`<div class="ms">market: ${esc(x.market_state)}</div>`:''}</div>`;
  }).join('');
}
async function pollEtf(){
  try{ const d=await (await fetch('/api/etf')).json();
    if(d.ok&&d.quotes&&Object.keys(d.quotes).length){ window.__ETFQ=d.quotes; renderEtfLive('etfLive'); renderEtfLive('etfLive2'); }
  }catch(e){}
}
pollEtf(); setInterval(pollEtf, 60000);
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

function fngGauge(v){
  /* 0=fear(green) … 100=greed(red) — semicircle arc, 270° sweep */
  const a0=135, a1=405, ang=a0+(a1-a0)*v/100, rad=ang*Math.PI/180;
  const x=30+25*Math.cos(rad), y=30+25*Math.sin(rad);
  const large=(ang-a0)>180?1:0;
  const col=v>=75?'var(--red)':v>=55?'var(--copper)':v>=45?'var(--muted)':'var(--green)';
  const dash=`<circle cx="30" cy="30" r="25" fill="none" stroke="${col}" stroke-width="7"
    stroke-dasharray="${(169.6*v/100).toFixed(1)} 169.6" transform="rotate(135 30 30)" stroke-linecap="round"/>`;
  const cls=v>=75?'var(--red)':v>=55?'var(--copper-hi)':v>=45?'var(--muted)':'var(--green)';
  const falab=(window.__ECON_FA&&window.__ECON_FA[(window.__FNG||{}).label])||'';
  return [dash,cls,falab||({ 'Extreme Fear':'ترس شدید','Fear':'ترس','Neutral':'خنثی','Greed':'طمع','Extreme Greed':'طمع شدید' }[(window.__FNG||{}).label]||'')];
}
function flowBar(v){
  const mx=800, w=Math.min(100,Math.abs(v)/mx*100)/2;
  const pos=v>=0;
  return `<svg viewBox="0 0 100 10" preserveAspectRatio="none" style="width:100%;height:10px;display:block">
    <line x1="50" y1="0" x2="50" y2="10" stroke="var(--line)" stroke-width="1"/>
    <rect x="${pos?50:50-w}" y="1.5" width="${w}" height="7" fill="${pos?'var(--green)':'var(--red)'}"/></svg>`;
}
function paintFng(){ if(UI.view==='fng') renderFngPage(); else if(UI.view==='calendar'&&ECON) renderCalendar(); }
function fngInner(f){
  const [dash,cls,falab]=fngGauge(f.now);
  const bars=(f.history||[]).map((x,i)=>{
    const h=Math.max(4,Math.round(x.v/100*46));
    const c=x.v>=75?'var(--red)':x.v>=55?'var(--copper-hi)':x.v>=45?'var(--muted)':'var(--sage)';
    return `<rect x="${i*16}" y="${50-h}" width="11" height="${h}" rx="2.5" fill="${c}" opacity=".9"><title>${toFa(x.v)}</title></rect>`;
  }).join('');
  return `<div style="display:flex;align-items:center;gap:14px">
      <svg class="fngdial" viewBox="0 0 60 60" role="img" aria-label="Fear & Greed ${f.now}" style="width:74px;height:74px">
        <circle cx="30" cy="30" r="25" fill="none" stroke="var(--line)" stroke-width="7"/>
        ${dash}</svg>
      <div><div style="font-weight:800;font-size:22px;color:${cls}">${toFa(f.now)}<span style="font-size:11px;color:var(--muted)"> / ۱۰۰</span></div>
      <div style="font-size:12px;color:var(--body);font-weight:600">${falab}</div>
      <div style="font-size:10.5px;color:var(--muted)">۸ روز گذشته ↓</div></div>
    </div>
    <svg viewBox="0 0 ${(f.history||[]).length*16} 50" style="width:100%;height:50px;margin-top:8px">${bars}</svg>`;
}
function renderFngPage(){
  const box=document.getElementById('fngPage'); if(!box) return;
  if(!ECON){ box.innerHTML='<div class="empty">در حال دریافت داده…</div>'; return; }
  const f=ECON.fng||{};
  if(f.now==null){ box.innerHTML='<div class="empty">داده ترس و طمع موقتاً در دسترس نیست.</div>'; return; }
  const h=f.history||[];
  const y=h.length>1?h[h.length-2].v:null, wk=h.length?h[0].v:null;
  const chip=(lbl,v)=>v==null?'':`<div class="fngchip"><span>${lbl}</span><b style="color:${v>=75?'var(--red)':v>=55?'var(--copper-hi)':v>=45?'var(--body)':'var(--sage)'}">${toFa(v)}</b></div>`;
  /* per-asset sentiment cards — one live score per selected asset */
  const syms=orderedAssets();
  const cards=syms.map(sym=>{
    const meta=DATA.assets_meta[sym]||{};
    return `<div class="fngsym" id="fngsym-${sym}" data-sym="${sym}">
      <div class="fs-head"><span class="ic">${meta.icon||''}</span><b>${esc(meta.fa||sym)}</b> <span class="tk">${sym}</span></div>
      <div class="fs-body"><span class="fs-spin">…</span></div>
    </div>`;
  }).join('');
  box.innerHTML=`<div>${fngInner(f)}
    <div style="display:flex;gap:10px;margin-top:12px;flex-wrap:wrap">
      ${chip('دیروز',y)}${chip('یک هفته قبل',wk)}
    </div>
    <h4 style="margin:18px 0 10px;font-size:13px;color:var(--copper-txt)">🎯 سنتیمنت هر دارایی (۲۴ ساعت گذشته، خبرهای همین داشبورد)</h4>
    <div class="fngsyms">${cards}</div>
    <div class="hint" style="font-size:11px;margin-top:14px;line-height:2.1">
      مقیاس: ۰ ترس شدید · ۲۵ ترس · ۵۰ خنثی · ۷۵ طمع · ۱۰۰ طمع شدید.
      اعداد بالا یعنی اشباع خرید و اعداد پایین یعنی ریسک‌گریزی — این شاخص زمینهٔ احساسات بازار را نشان می‌دهد، سیگنال معامله نیست.
    </div></div>`;
  for(const sym of syms) loadFngSym(sym);
}
async function loadFngSym(sym){
  try{
    const d=await (await fetch('/api/fng/'+sym)).json();
    if(!d.ok) return;
    const box=document.getElementById('fngsym-'+sym); if(!box) return;
    const v=d.now||50, cls=v>=75?'var(--red)':v>=55?'var(--copper-hi)':v>=45?'var(--body)':'var(--sage)';
    const fal=({'Extreme Fear':'ترس شدید','Fear':'ترس','Neutral':'خنثی','Greed':'طمع','Extreme Greed':'طمع شدید'})[d.label]||d.label;
    box.querySelector('.fs-body').innerHTML=
      `<div class="fs-score" style="color:${cls}">${toFa(v)}</div>
       <div class="fs-lab" style="color:${cls}">${fal}</div>
       <div class="fs-bar" role="progressbar" aria-valuenow="${v}" aria-valuemin="0" aria-valuemax="100"><i style="width:${v}%;background:${cls}"></i></div>
       <div class="fs-count">${toFa(d.count||0)} خبر ۲۴س</div>`;
  }catch(e){}
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
      <div class="msec" style="border-inline-start:3px solid var(--copper)">
        <h4 style="margin-bottom:6px">💡 این خبر چیست؟</h4>
        <p style="font-size:13.5px;line-height:2.15;margin:0">${esc(d.blurb_fa||'توضیحی برای این خبر ساخته نشد — خلاصه را در مودال اصلی ببینید.')}</p>
      </div>
      <button class="btn sm" style="margin-top:4px" onclick="closeModal('blurbOverlay');openArticle('${id}')">📄 متن کامل خبر</button>`;
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
function initAlerts(){
  const tg=(DATA&&DATA.config&&DATA.config.telegram)||{};
  const tk=document.getElementById('tgToken'), tc=document.getElementById('tgChat');
  if(tg.token) tk.value=tg.token;
  if(tg.chat) tc.value=tg.chat;
  document.getElementById('tgEnabled').checked = tg.enabled!==false;
  document.getElementById('tgMinCred').value = tg.min_credibility!=null?tg.min_credibility:0.75;
  document.getElementById('tgMaxItems').value = tg.max_items||10;
  document.getElementById('tgMaxAge').value = tg.max_age_hours||6;
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
}
async function saveTelegram(){
  const p=tgPayload();
  if(!p.telegram.token||!p.telegram.chat){ toast('توکن و Chat ID را وارد کنید'); return; }
  const r=await postSettings(p);
  if(r&&r.ok){ toast('همه تنظیمات تلگرام ذخیره شد ✓'); }
}
async function testTelegram(){
  const token=document.getElementById('tgToken').value.trim(), chat=document.getElementById('tgChat').value.trim();
  if(!token||!chat){ toast('توکن و Chat ID را وارد کنید'); return; }
  const r=await fetch('/api/telegram/test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,chat})});
  const d=await r.json(); toast(d.ok?'✓ پیام تست رفت — تلگرام را چک کن':'✗ ارسال نشد: '+(d.error||'')); 
}
async function sendNowTelegram(){
  const r=await fetch('/api/telegram/send-now',{method:'POST'});
  const d=await r.json();
  toast(d.ok?`✓ خلاصه ارسال شد (${toFa(d.sent||0)} خبر)`:'✗ ارسال نشد: '+(d.error||''));
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

loadData();
pollLive();
dl2Skeleton(6);
setTimeout(function(){ dl2MarkSeen(); }, 15000);
/* DL2: duplicate poll removed — the guarded 60s interval defined above is the
   single source of truth for /api/data refresh (this one doubled the traffic). */

/* ── DL2 phase 5: group the nav rail into clusters + collapsible rail ─────
   Runs on the existing DOM (no markup change). Wrapped in try/catch so any
   failure leaves the original rail exactly as it was. */
(function(){
  try{
    const rail=document.getElementById('appSidebar');
    if(!rail) return;
    const GROUPS=[
      ['جریان بازار',['feed','calendar','fng']],
      ['تحلیل',['reports','etf']],
      ['آرشیو',['archive','bookmarks']],
      ['سیستم',['sources','monitor','assets','settings','alerts']]
    ];
    const items=[...rail.querySelectorAll('.nav-item')];
    if(items.length){
      const picked=new Set();
      const groups=[];
      GROUPS.forEach(([label,views])=>{
        const g=document.createElement('div'); g.className='rail-group';
        const l=document.createElement('div'); l.className='rail-group-label'; l.textContent=label;
        const owned=items.filter(it=>views.includes(it.dataset.view));
        if(!owned.length) return;
        g.appendChild(l);
        owned.forEach(it=>{ g.appendChild(it); picked.add(it); });
        groups.push(g);
      });
      const leftover=items.filter(it=>!picked.has(it));
      if(leftover.length){
        const g=document.createElement('div'); g.className='rail-group';
        leftover.forEach(it=>g.appendChild(it));
        groups.push(g);
      }
      const frag=document.createDocumentFragment();
      groups.forEach(g=>frag.appendChild(g));
      rail.appendChild(frag);                       // moves nodes, handlers survive
      const head=rail.querySelector('.sidebar-section-label');
      if(head) head.style.display='none';
    }
    const btn=document.createElement('button');
    btn.type='button'; btn.className='dl2-rail-toggle';
    btn.setAttribute('aria-label','جمع و باز کردن نوار کناری');
    btn.setAttribute('aria-expanded','true');
    btn.textContent='⇤';
    let saved=null; try{ saved=localStorage.getItem('dl2_rail'); }catch(e){}
    if(saved==='1'){ document.body.classList.add('dl2-rail-collapsed'); btn.textContent='⇥'; btn.setAttribute('aria-expanded','false'); }
    btn.addEventListener('click',()=>{
      const on=document.body.classList.toggle('dl2-rail-collapsed');
      btn.textContent=on?'⇥':'⇤';
      btn.setAttribute('aria-expanded',on?'false':'true');
      try{ localStorage.setItem('dl2_rail',on?'1':'0'); }catch(e){}
    });
    rail.appendChild(btn);
  }catch(e){ /* fail-safe: original rail untouched */ }
})();

/* ══ STAGED ENTRANCE ══
   The stage is already lit; the cast walks on in order — topbar, nav rail,
   ticker, content — then the whole apparatus detaches so the design rests
   completely still. Reduced motion never gets here. */
(function () {
  var d = document.documentElement;
  var started = false, boot_t = null, safety = null;

  function clean() {
    if (boot_t) { clearTimeout(boot_t); boot_t = null; }
    if (safety) { clearTimeout(safety); safety = null; }
    document.removeEventListener('animationend', onEnd, true);
    d.classList.remove('anim');
    d.classList.remove('go');
  }

  function onEnd(e) {
    /* the content pane is last on the timeline */
    if (e.animationName === 'shellUp' && e.target && e.target.classList &&
        e.target.classList.contains('view-container')) clean();
  }

  function start() {
    if (started || !d.classList.contains('anim')) return;
    started = true;
    if (boot_t) { clearTimeout(boot_t); boot_t = null; }
    document.addEventListener('animationend', onEnd, true);
    safety = setTimeout(clean, 2600);
    d.classList.add('go');
  }

  function boot() {
    /* ceiling: never hold the page hostage to a slow font fetch */
    boot_t = setTimeout(start, 900);
    if (document.fonts && document.fonts.ready && document.fonts.ready.then) {
      document.fonts.ready.then(start, start);
    } else {
      start();
    }
  }

  if (!d.classList.contains('anim')) return;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
</script>
</body>
</html>
"""
