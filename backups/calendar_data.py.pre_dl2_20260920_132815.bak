#!/usr/bin/env python3
"""
Market Context — economic calendar, Fear & Greed, ETF flows, macro index quotes
===============================================================================
All free and key-less:
  - ForexFactory weekly calendar (nfs.faireconomy.media)   -> /api/econ
  - Fear & Greed index          (alternative.me)          -> /api/econ
  - Spot BTC ETF flows          (Farside HTML tables)     -> /api/econ
  - DXY / S&P500 / VIX / WTI    (Yahoo v8 chart API)      -> /api/econ
Every source fails independently and degrades to {"error": ...} — never raises.
"""

import re
import time
import json
from datetime import datetime, timezone

import requests

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/128.0.0.0 Safari/537.36"),
}

CACHE = {"ts": 0.0, "data": None}
TTL = 900.0  # 15 minutes


# ---------------------------------------------------------------------------
# Market sessions (market24hclock-style, computed locally — no API needed)
# ---------------------------------------------------------------------------
SESSIONS = [
    # key, label(EN), icon, open-hour-UTC, close-hour-UTC, weekdays-open (Mon=0)
    {"key": "sydney", "label": "Sydney", "icon": "🇦🇺", "open": 21, "close": 6, "days": {6, 0, 1, 2, 3, 4}},
    {"key": "tokyo",  "label": "Tokyo",  "icon": "🇯🇵", "open": 0,  "close": 9, "days": {0, 1, 2, 3, 4}},
    {"key": "london", "label": "London", "icon": "🇬🇧", "open": 7,  "close": 16, "days": {0, 1, 2, 3, 4}},
    {"key": "newyork","label": "New York","icon": "🇺🇸", "open": 12, "close": 21, "days": {0, 1, 2, 3, 4}},
]


def market_sessions():
    """Which exchanges are open right now + minutes to next open/close.
    Static weekly schedule in UTC (winter hours — close enough for a glance).
    """
    from datetime import datetime
    now = datetime.now(timezone.utc)
    out = []
    for s in SESSIONS:
        o, c = s["open"], s["close"]
        wrap = c <= o
        is_open = (s["days"].__contains__(now.weekday()) and
                   ((o <= now.hour < c) if not wrap else (now.hour >= o or now.hour < c)))
        # minutes to next boundary (open if closed, close if open)
        nowm = now.hour * 60 + now.minute
        boundary = (c if is_open else o) * 60
        if wrap and is_open and now.hour < c:
            mins = boundary - nowm
        elif boundary > nowm:
            mins = boundary - nowm
        else:
            mins = 1440 - nowm + boundary
        out.append({"key": s["key"], "label": s["label"], "icon": s["icon"],
                    "open": is_open, "mins_to_change": mins,
                    "hours": f"{o:02d}:00-{c:02d}:00 UTC"})
    return out

IMPACT_FA = {"High": "بالا", "Medium": "متوسط", "Low": "کم", "Holiday": "تعطیلی"}
COUNTRY_FLAG = {
    "USD": "\U0001F1FA\U0001F1F8", "EUR": "\U0001F1EA\U0001F1FA",
    "GBP": "\U0001F1EC\U0001F1E7", "JPY": "\U0001F1EF\U0001F1F5",
    "CNY": "\U0001F1E8\U0001F1F3", "CAD": "\U0001F1E8\U0001F1E6",
    "AUD": "\U0001F1E6\U0001F1FA", "NZD": "\U0001F1F3\U0001F1FF",
    "CHF": "\U0001F1E8\U0001F1ED", "All": "\U0001F30D",
}
FNG_FA = {"Extreme Fear": "ترس شدید", "Fear": "ترس", "Neutral": "خنثی",
          "Greed": "طمع", "Extreme Greed": "طمع شدید"}

MACRO_QUOTES = [  # (sym, yahoo_symbol, fa_name, icon)
    ("DXY", "DX-Y.NYB", "دلار (DXY)", "\U0001F4B5"),
    ("SPX", "^GSPC",    "اس‌اند‌پی ۵۰۰", "\U0001F3DB"),
    ("VIX", "^VIX",     "شاخص ترس VIX", "\U0001F630"),
    ("WTI", "CL=F",     "نفت وست تگزاس", "\U0001F6E2"),
]


def _fetch(url, **kw):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, **kw)
        if r.status_code == 200:
            return r
    except Exception:
        pass
    return None


def _calendar_next_page():
    """Next week via the ForexFactory weekly page itself
    (the faireconomy JSON mirror has no nextweek file).
    Parses calendar__row table rows incl. impact icon classes."""
    from bs4 import BeautifulSoup
    try:
        r = requests.get("https://www.forexfactory.com/calendar?week=next",
                         headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                                  "Accept": "text/html"}, timeout=15)
        if r.status_code != 200:
            return {"error": "unavailable"}
        soup = BeautifulSoup(r.text, "html.parser")
        MON = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
               "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
        IMP = {"red": "High", "ora": "Medium", "gra": "Low", "hol": "Holiday"}
        out, cur_day = [], None
        now = datetime.now(timezone.utc)
        for tr in soup.select("tr.calendar__row"):
            cls = tr.get("class") or []
            if "calendar__row--day-breaker" in cls:
                td = tr.select_one("td")
                txt = td.get_text(strip=True) if td else ""      # e.g. 'SunSep 20' (no space!)
                try:
                    m = re.search(r"([A-Za-z]{3})\s*(\d{1,2})", txt)
                    if m:
                        cur_day = datetime(now.year, MON[m.group(1)], int(m.group(2)))
                        if cur_day.month < now.month - 1:        # year wrap (Dec -> Jan)
                            cur_day = cur_day.replace(year=now.year + 1)
                        cur_day = cur_day.date()
                except Exception:
                    cur_day = None
                continue
            if "calendar__row--subheader" in cls or "calendar__row--spacer" in cls:
                continue
            title_el = tr.select_one(".calendar__event-title")
            if not title_el:
                continue
            imp_span = tr.select_one("td.calendar__impact span")
            imp = "Low"
            if imp_span:
                icls = " ".join(imp_span.get("class") or [])
                for k, v in IMP.items():
                    if f"impact-{k}" in icls:
                        imp = v
                        break
            t_el = tr.select_one(".calendar__time")
            time_txt = t_el.get_text(strip=True) if t_el else ""
            ts, iso = 0, ""
            try:
                if cur_day and time_txt and ":" in time_txt and "Day" not in time_txt:
                    hm = time_txt.replace("am", "").replace("pm", "").strip()
                    hh, mm = map(int, hm.split(":"))
                    if "pm" in time_txt and hh != 12:
                        hh += 12
                    if "am" in time_txt and hh == 12:
                        hh = 0
                    dt = datetime(now.year, cur_day.month, cur_day.day, hh, mm, tzinfo=timezone.utc)
                    ts, iso = int(dt.timestamp()), dt.isoformat()
                elif cur_day:
                    dt = datetime(cur_day.year, cur_day.month, cur_day.day, tzinfo=timezone.utc)
                    ts, iso = int(dt.timestamp()), dt.isoformat()
            except Exception:
                pass
            cur_el = tr.select_one(".calendar__currency")
            country = cur_el.get_text(strip=True) if cur_el else ""
            def cell(sel):
                el = tr.select_one(sel)
                return el.get_text(strip=True) if el else ""
            out.append({
                "title": title_el.get_text(strip=True),
                "country": country,
                "flag": COUNTRY_FLAG.get(country, "\U0001F30D"),
                "impact": imp,
                "impact_fa": IMPACT_FA.get(imp, imp),
                "forecast": cell(".calendar__forecast") or "—",
                "previous": cell(".calendar__previous") or "—",
                "actual": cell(".calendar__actual"),
                "ts": ts,
                "iso": iso,
                "day": cur_day.isoformat() if cur_day else "",
                "time_str": (datetime.fromtimestamp(ts, timezone.utc).strftime("%H:%M") if ts else ""),
                "past": (dt < now) if (ts and (dt := datetime.fromtimestamp(ts, timezone.utc))) else False,
            })
        out.sort(key=lambda x: x["ts"])
        return {"events": out, "source": "forexfactory.com (page)"}
    except Exception as e:
        return {"error": str(e)}


def _calendar(week_offset: int = 0):
    if week_offset > 0:
        return _calendar_next_page()
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    r = _fetch(url)
    if not r:
        return {"error": "unavailable"}
    try:
        items = r.json()
    except Exception:
        return {"error": "bad_json"}
    out = []
    now = datetime.now(timezone.utc)
    for it in items:
        try:
            dt = datetime.fromisoformat(it["date"])
            ts = int(dt.timestamp())
            # Iran-local calendar day + clock time so the UI can box events per day
            local_day = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            out.append({
                "title": it.get("title", ""),
                "country": it.get("country", ""),
                "flag": COUNTRY_FLAG.get(it.get("country", ""), "\U0001F30D"),
                "impact": it.get("impact", "Low"),
                "impact_fa": IMPACT_FA.get(it.get("impact", "Low"), it.get("impact", "")),
                "forecast": it.get("forecast") or "—",
                "previous": it.get("previous") or "—",
                "actual": (str(it.get("actual")).strip() if it.get("actual") not in (None, "", "—") else ""),
                "ts": ts,
                "iso": dt.isoformat(),
                "day": local_day,
                "time_str": dt.strftime("%H:%M"),
                "past": dt < now,
            })
        except Exception:
            continue
    out.sort(key=lambda x: x["ts"])
    return {"events": out}


def _fng():
    r = _fetch("https://api.alternative.me/fng/?limit=8")
    if not r:
        return {"error": "unavailable"}
    try:
        d = r.json()["data"]
        return {"now": int(d[0]["value"]),
                "label": d[0]["value_classification"],
                "label_fa": FNG_FA.get(d[0]["value_classification"], ""),
                "history": [{"v": int(x["value"]), "ts": int(x["timestamp"])}
                            for x in reversed(d)]}
    except Exception:
        return {"error": "bad_json"}


def _etf_num(s):
    """Farside writes negatives in accounting style: (201.9) == -201.9"""
    s = (s or "").replace(",", "").strip()
    if s in ("", "-"):
        return None
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    try:
        v = float(s)
        return -v if neg else v
    except ValueError:
        return None


def _etf_flows():
    """Farside spot-BTC ETF daily net-flow table (latest rows)."""
    r = _fetch("https://farside.co.uk/btc/")
    if not r:
        return {"error": "unavailable"}
    try:
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", r.text, re.S)
        out = []
        for row in rows:
            cells = [re.sub(r"<[^>]+>", "", c).strip()
                     for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
            if len(cells) >= 12 and re.match(r"\d{1,2} \w{3} \d{4}", cells[0]):
                total = _etf_num(cells[-1])
                if total is not None:
                    out.append({"date": cells[0], "total_musd": total})
        return {"rows": out[-10:]}
    except Exception:
        return {"error": "parse"}


def _macro_quotes():
    out = []
    for sym, yh, fa, icon in MACRO_QUOTES:
        r = _fetch("https://query1.finance.yahoo.com/v8/finance/chart/" + yh,
                   params={"range": "2d", "interval": "1d"})
        price = chg = None
        if r:
            try:
                meta = r.json()["chart"]["result"][0]["meta"]
                price = meta.get("regularMarketPrice")
                chg = meta.get("regularMarketChangePercent")
            except Exception:
                pass
        out.append({"sym": sym, "fa": fa, "icon": icon, "price": price,
                    "change": round(chg, 2) if chg is not None else None})
    return out


def market_context():
    """Cached bundle for /api/econ — this week + next week calendars."""
    now = time.time()
    if CACHE["data"] is not None and now - CACHE["ts"] < TTL:
        return CACHE["data"]
    data = {
        "calendar": _calendar(),
        "calendar_next": _calendar(week_offset=1),
        "fng": _fng(),
        "etf": _etf_flows(),
        "macro": _macro_quotes(),
        "sessions": market_sessions(),
        "fng_fa": FNG_FA,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    CACHE["ts"] = now
    CACHE["data"] = data
    return data


if __name__ == "__main__":
    d = market_context()
    cal = d.get("calendar", {})
    ev = cal.get("events", [])
    print("calendar:", ("ERR " + str(cal.get("error"))) if "error" in cal else f"{len(ev)} events")
    for e in [x for x in ev if not x["past"] and x["impact"] == "High"][:3]:
        print("  ", e["flag"], e["title"], "|", e["impact_fa"])
    print("fng:", d["fng"])
    print("etf:", d["etf"])
    print("macro:", [(m["sym"], m["price"], m["change"]) for m in d["macro"]])
