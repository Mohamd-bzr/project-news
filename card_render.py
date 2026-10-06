"""card_render.py — Persian news card PNG, rendered server-side.

The studio produces the text; this produces the *picture* a Telegram channel
actually posts. One size: 1080×1350 (the studio's own export format), drawn in
the dashboard's DL6 midnight palette so the card reads as the product, and the
headline set in Vazirmatn — the same letterforms the page uses.

The Persian-on-image problem and its standard fix:
  * shaping — Arabic letters must CONNECT (بـ‌ـا), which no raw Unicode
    string does for a rasterizer: `arabic_reshaper` substitutes the
    presentation forms;
  * direction — the shaped run must then be reversed for left-to-right
    rasterizers: `python-bidi`.
Both are optional deps; without them (or without the font file) the renderer
raises CardUnavailable and the endpoint answers 503 — never a broken image.

Everything is drawn from the article's own fields: title, summary, source,
Jalali time, the numbers already extracted by the pipeline. Nothing invented.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont

_ROOT = Path(__file__).resolve().parent
_FONT_DIR = _ROOT / "assets" / "fonts"
_FONT_REG = _FONT_DIR / "Vazirmatn-Regular.ttf"
_FONT_BOLD = _FONT_DIR / "Vazirmatn-Bold.ttf"

W, H = 1080, 1350

# DL6 midnight tokens (kept literal — SVG-style var() does not exist here)
BG = (12, 17, 28)          # --bg
PANEL = (18, 24, 38)       # --panel
RULE = (56, 72, 100)       # hairline
ACCENT = (108, 151, 220)   # --cu matte blue
INK1 = (241, 244, 249)
INK2 = (210, 217, 227)
INK4 = (141, 153, 171)
UP = (46, 189, 119)
DN = (238, 106, 88)


class CardUnavailable(Exception):
    """Raised when the fonts or the shaping stack are missing — the endpoint
    answers 503 with a note instead of a broken image."""


def _require_stack():
    if not (_FONT_REG.exists() and _FONT_BOLD.exists()):
        raise CardUnavailable("فونت وزیرمتن روی دیسک نیست (assets/fonts/)")
    try:
        import arabic_reshaper  # noqa: F401
        from bidi.algorithm import get_display  # noqa: F401
    except ImportError as e:
        raise CardUnavailable(f"reshaper/bidi نصب نیست: {e}")


def _shape(text: str) -> str:
    """Connect + direction-fix one Persian/Arabic run for a rasterizer."""
    import arabic_reshaper
    from bidi.algorithm import get_display
    return get_display(arabic_reshaper.reshape(str(text or "")))


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(_FONT_BOLD if bold else _FONT_REG), size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
          max_width: int, max_lines: int) -> List[str]:
    """Greedy wrap on words; the last line takes an ellipsis when truncated."""
    words = str(text or "").split()
    lines: List[str] = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(_shape(trial), font=font) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines - 1:
                break
    if cur:
        lines.append(cur)
    if len(lines) == max_lines and words and " ".join(lines) != " ".join(words):
        last = lines[-1]
        while last and draw.textlength(_shape(last + "…"), font=font) > max_width:
            last = last.rsplit(" ", 1)[0]
        lines[-1] = (last + " …").strip()
    return lines


_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa_num(v: Any) -> str:
    return str(v).translate(_FA_DIGITS)


def render_news_card(article: Dict[str, Any]) -> bytes:
    """PNG bytes for one story — 1080×1350, DL6 midnight, Vazirmatn.

    Two layers: the text block is drawn on a full-size overlay first (its
    height is known only after wrapping), then composited onto the background
    shifted down by a third of the leftover room — so a short story reads
    centred instead of floating at the top of a tall empty card. Frame, rail
    and footer are painted last and never move.
    """
    _require_stack()
    title = str(article.get("title_fa") or article.get("title") or "").strip()
    if not title:
        raise CardUnavailable("خبر بدون تیتر")
    summary = str(article.get("summary_fa") or article.get("summary") or "").strip()
    source = str(article.get("source_name") or article.get("source") or "").strip()
    dt_fa = str(article.get("datetime_fa") or article.get("date_fa") or "").strip()
    nums = [n for n in (article.get("numbers") or [])][:5]

    # ── layer 1: the content block, at its natural height ──
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    margin = 72
    inner_w = W - margin * 2
    y = 0          # overlay-local top

    head = _shape(" — ".join(x for x in (source, dt_fa) if x))
    d.text((W - margin, y), head, font=_font(30), fill=INK4 + (255,), anchor="ra")
    y += 66
    d.line([margin, y, W - margin, y], fill=RULE + (255,), width=1)
    y += 44

    h_font = _font(62, bold=True)
    for line in _wrap(d, title, h_font, inner_w, 4):
        d.text((W - margin, y), _shape(line), font=h_font, fill=INK1 + (255,), anchor="ra")
        y += 88
    y += 26

    if summary:
        s_font = _font(36)
        d.line([W - margin, y, W - margin - 120, y], fill=ACCENT + (255,), width=3)
        y += 34
        for line in _wrap(d, summary, s_font, inner_w, 5):
            d.text((W - margin, y), _shape(line), font=s_font, fill=INK2 + (255,), anchor="ra")
            y += 62
        y += 20

    if nums:
        d.line([margin, y, W - margin, y], fill=RULE + (255,), width=1)
        y += 34
        n_font = _font(40, bold=True)
        x = W - margin
        for n in nums:
            t = _shape(_fa_num(n))
            tw = d.textlength(t, font=n_font)
            if x - tw < margin:
                break
            d.text((x, y), t, font=n_font, fill=ACCENT + (255,), anchor="ra")
            x -= tw + 34
        y += 78

    content_h = y
    if content_h > H - 320:
        content_h = H - 320       # extreme case: keep the footer clear

    # ── layer 2: compose — shift content down by a third of the slack ──
    top = 96 + min(220, max(0, (H - 96 - 250 - content_h)) // 3)
    img = Image.new("RGB", (W, H), BG)
    img.paste(overlay, (0, top), overlay)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([24, 24, W - 24, H - 24], radius=18, outline=RULE, width=2)
    d.rounded_rectangle([24, 24, 34, H - 24], radius=5, fill=ACCENT)
    d.line([margin, top - 26, W - margin, top - 26], fill=RULE, width=1)

    # footer brand — always at the bottom rail
    f_font = _font(34, bold=True)
    d.text((W - margin, H - 138), _shape("MOHMD NEWS · ترمینال هوش بازار"),
           font=f_font, fill=ACCENT, anchor="ra")
    d.text((margin, H - 130), _shape(_fa_num("۱۴۰۵")), font=_font(26), fill=INK4, anchor="la")

    import io as _io
    buf = _io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


if __name__ == "__main__":
    demo = {
        "title_fa": "سقف تاریخی جدید طلا؛ اونس با جهش ۳.۲ درصدی به ۴۱۶۰ دلار رسید",
        "summary_fa": "قیمت طلا برای اولین بار رکورد تاریخی زد؛ بازار تهران و دلار آزاد هم واکنش نشان دادند. سرمایه‌گذاران منتظر آمار تورم هستند.",
        "source_name": "Bloomberg", "datetime_fa": "۲۶ مهر ۱۴۰۵ · ۱۷:۳۵",
        "numbers": ["۴۱۶۰ دلار", "۳.۲٪", "۲۶ میلیون تومان"],
    }
    png = render_news_card(demo)
    out = _ROOT / "logs" / "card_demo.png"
    out.write_bytes(png)
    print(f"rendered {len(png)} bytes -> {out}")
