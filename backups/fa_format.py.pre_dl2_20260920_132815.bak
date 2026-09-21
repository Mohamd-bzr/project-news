#!/usr/bin/env python3
"""
Persian formatting helpers
==========================
Everything the dashboard needs to speak Persian properly:

  • Persian numerals                  ۱ ۲ ۳ …
  • Jalali (شمسی) date conversion     so news timestamps read ۲۴ شهریور ۱۴۰۵
  • Tehran-local clock times          Asia/Tehran = UTC+03:30 (no DST since 2022)
  • relative age ("۳ ساعت پیش")

Pure stdlib, no dependencies, no locale requirements.
"""

from datetime import datetime, timedelta, timezone

IRAN_TZ = timezone(timedelta(hours=3, minutes=30))

_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
_JALALI_MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                  "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
_WEEKDAYS = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]


def fa_digits(text) -> str:
    """0123456789 -> ۰۱۲۳۴۵۶۷۸۹"""
    if text is None:
        return ""
    return str(text).translate(_FA_DIGITS)


def gregorian_to_jalali(gy: int, gm: int, gd: int):
    """Standard Gregorian -> Jalali (Solar Hijri) conversion."""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = (355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100)
            + ((gy2 + 399) // 400) + gd + g_d_m[gm - 1])
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


def to_tehran(ts_or_dt):
    """Accept epoch seconds, a datetime, or an ISO-8601 string."""
    if ts_or_dt is None:
        return None
    if isinstance(ts_or_dt, bool):
        return None
    if isinstance(ts_or_dt, (int, float)):
        dt = datetime.fromtimestamp(ts_or_dt, timezone.utc)
    elif isinstance(ts_or_dt, datetime):
        dt = ts_or_dt if ts_or_dt.tzinfo else ts_or_dt.replace(tzinfo=timezone.utc)
    elif isinstance(ts_or_dt, str):
        try:
            dt = datetime.fromisoformat(ts_or_dt.replace("Z", "+00:00"))
        except ValueError:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    else:
        return None
    return dt.astimezone(IRAN_TZ)


def fa_date(ts_or_dt) -> str:
    """`۲۴ شهریور ۱۴۰۵`"""
    dt = to_tehran(ts_or_dt)
    if not dt:
        return ""
    jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
    return f"{fa_digits(jd)} {_JALALI_MONTHS[jm - 1]} {fa_digits(jy)}"


def fa_time(ts_or_dt) -> str:
    """`۱۳:۴۵`"""
    dt = to_tehran(ts_or_dt)
    if not dt:
        return ""
    return fa_digits(dt.strftime("%H:%M"))


def fa_datetime(ts_or_dt, with_weekday: bool = False) -> str:
    """`۲۴ شهریور ۱۴۰۵، ساعت ۱۳:۴۵` (+ optional weekday)"""
    dt = to_tehran(ts_or_dt)
    if not dt:
        return ""
    wd = _WEEKDAYS[dt.weekday()]
    base = f"{fa_date(dt)}، ساعت {fa_time(dt)}"
    return f"{wd} {base}" if with_weekday else base


def fa_ago(hours) -> str:
    """`۳ ساعت پیش` / `۲۵ دقیقه پیش` / `۱ دقیقه پیش` — no "همین حالا" */"""
    if hours is None:
        return ""
    minutes = float(hours) * 60
    if minutes < 1:
        return "۱ دقیقه پیش"
    if minutes < 60:
        return f"{fa_digits(int(minutes))} دقیقه پیش"
    if hours < 24:
        return f"{fa_digits(int(round(hours)))} ساعت پیش"
    days = int(hours // 24)
    return f"{fa_digits(days)} روز پیش"


def fa_datetime_str(iso_str: str) -> str:
    """`2026-09-15T10:00:00+00:00` -> Persian datetime."""
    if not iso_str:
        return ""
    try:
        return fa_datetime(datetime.fromisoformat(iso_str))
    except Exception:
        return ""


if __name__ == "__main__":
    # sanity check against a known conversion: 2026-09-15 -> 1405-06-24
    print(gregorian_to_jalali(2026, 9, 15))
    print(gregorian_to_jalali(2024, 3, 20))   # 1403-01-01
    print(fa_datetime(datetime(2026, 9, 15, 10, 5, tzinfo=timezone.utc)))
    print(fa_ago(3.4), "|", fa_ago(0.3), "|", fa_ago(30))
