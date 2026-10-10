#!/usr/bin/env python3
"""
Generate the PWA icons from the dashboard's own brand mark.

The manifest needs real PNG files, and this project has no image dependency
(no Pillow in requirements.txt) — so the icons are drawn here with a
signed-distance rasteriser and written with zlib, which is all a PNG is.

The artwork is the same polyline as the inline `<symbol id="i-mark">` in
web/fragments/30_body_head.html, in its 24×24 viewBox, stroked in copper on
graphite. Keeping the geometry in one place means the launcher icon and the
topbar mark cannot drift apart.

Usage:  python tools/make_icons.py [--check]
"""
from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "icons"

# ── brand ────────────────────────────────────────────────────────────────────
# Stroke #4C8DFF (--cu) on the midnight-navy panel colour, plus the same token
# used as a hairline border so the icon reads as engraved rather than pasted on.
CU = (108, 151, 220)
BG_TOP = (3, 5, 12)
BG_BOT = (12, 17, 28)
HAIRLINE = (160, 180, 210)

# i-mark polyline in the 24-unit viewBox of the inline SVG
MARK = [(3.0, 13.5), (7.0, 13.5), (9.5, 6.0), (14.0, 17.0), (17.0, 10.0), (21.0, 10.0)]
DOT = (20.0, 5.5, 1.6)
MARK_W = 1.7                # matches the .ic stroke width in the stylesheet


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else (hi if v > hi else v)


def _sd_segment(px, py, ax, ay, bx, by):
    """Distance from (px,py) to segment ab."""
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    L = vx * vx + vy * vy
    t = 0.0 if L == 0 else _clamp((wx * vx + wy * vy) / L)
    dx, dy = wx - t * vx, wy - t * vy
    return (dx * dx + dy * dy) ** 0.5


def _sd_round_rect(px, py, cx, cy, hw, hh, r):
    """Distance to a rounded rectangle (negative inside)."""
    qx = abs(px - cx) - (hw - r)
    qy = abs(py - cy) - (hh - r)
    outside = (max(qx, 0.0) ** 2 + max(qy, 0.0) ** 2) ** 0.5
    return outside + min(max(qx, qy), 0.0) - r


def _over(dst, src, a):
    """Alpha-composite `src` over `dst` tuple, returning a new tuple."""
    return tuple(int(round(dst[i] * (1 - a) + src[i] * a)) for i in range(3))


def render(size: int, maskable: bool = False) -> bytes:
    """Return RGBA bytes for one icon.

    `maskable` draws a full-bleed square (no rounded corners, mark pulled into
    the 60 % safe zone) because launchers crop maskable icons to their own
    shape and would otherwise shave the outline off.
    """
    scale = size / 24.0
    mark_scale = scale * (0.66 if maskable else 0.78)
    # centre the mark: its own bounds are x 3…21, y 6…17
    cx, cy = 12.0 * scale, 11.6 * scale
    off_x = size / 2.0 - cx
    off_y = size / 2.0 - cy
    half = size / 2.0
    radius = 0.0 if maskable else size * 0.22
    border = max(1.0, size * 0.006)

    # bounding boxes so the per-pixel loop only runs where ink can appear
    pts = [(x * mark_scale + off_x, y * mark_scale + off_y) for x, y in MARK]
    mx0 = min(p[0] for p in pts) - mark_scale * 1.6
    mx1 = max(p[0] for p in pts) + mark_scale * 1.6
    my0 = min(p[1] for p in pts) - mark_scale * 1.6
    my1 = max(p[1] for p in pts) + mark_scale * 1.6
    dx, dy = DOT[0] * mark_scale + off_x, DOT[1] * mark_scale + off_y
    dr = DOT[2] * mark_scale
    mx0, mx1 = min(mx0, dx - dr - 1), max(mx1, dx + dr + 1)
    my0, my1 = min(my0, dy - dr - 1), max(my1, dy + dr + 1)

    w = MARK_W * mark_scale / 2.0          # half stroke width
    rows = []
    for y in range(size):
        row = bytearray()
        py = y + 0.5
        for x in range(size):
            px = x + 0.5
            # ── plate ──
            d_rect = _sd_round_rect(px, py, half, half, half, half, radius) if radius else \
                -min(px, py, size - px, size - py)
            a_plate = _clamp(0.5 - d_rect)
            if a_plate <= 0.0:
                row += b"\x00\x00\x00\x00"
                continue
            shade = _clamp(py / max(1, size))
            base = tuple(int(round(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * shade)) for i in range(3))
            col = _over((0, 0, 0), base, 1.0)
            # top-lit wash, so the plate is not a flat swatch
            col = _over(col, (255, 255, 255), 0.030 * (1.0 - shade))

            # ── engraved hairline ──
            if radius:
                a_line = _clamp(0.5 - abs(d_rect + border) + border / 2) * 0.34
                if a_line > 0:
                    col = _over(col, HAIRLINE, a_line)

            # ── copper mark ──
            if mx0 <= px <= mx1 and my0 <= py <= my1:
                d = min(_sd_segment(px, py, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
                        for i in range(len(pts) - 1))
                d = min(d, ((px - dx) ** 2 + (py - dy) ** 2) ** 0.5 - dr)
                a_ink = _clamp(0.5 + w - d)
                if a_ink > 0:
                    # the mark is slightly brighter at the top: a light source,
                    # not a sticker
                    tone = 1.0 - 0.12 * (py / max(1, size))
                    ink = tuple(int(round(c * tone)) for c in CU)
                    col = _over(col, ink, a_ink)

            row += bytes((col[0], col[1], col[2], int(round(a_plate * 255))))
        rows.append(bytes(row))
    return _png(size, size, rows)


def _png(width: int, height: int, rows: list[bytes]) -> bytes:
    raw = b"".join(b"\x00" + r for r in rows)          # filter 0 per scanline

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)   # 8-bit RGBA
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
            chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


TARGETS = [
    ("icon-192.png", 192, False),
    ("icon-512.png", 512, False),
    ("icon-maskable-512.png", 512, True),
]


def _png_pixels(png: bytes) -> tuple[int, int, bytes]:
    """Decode OUR own icon PNGs (filter-0 rows, 8-bit RGBA) back to raw rows.

    Comparing decoded pixels instead of the file bytes: the container is
    zlib-compressed by whichever CPython built the interpreter, and different
    builds/platforms ship different zlib versions — byte-identical output is
    impossible across environments even when the image is identical.
    """
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, dims = 8, b"", None
    while pos < len(png):
        (length,) = struct.unpack(">I", png[pos:pos + 4])
        tag = png[pos + 4:pos + 8]
        data = png[pos + 8:pos + 8 + length]
        if tag == b"IHDR":
            w, h = struct.unpack(">II", data[:8])
            dims = (w, h)
            assert data[12] == 0, "non-filter-0 icon — decode path invalid"
        elif tag == b"IDAT":
            idat += data
        pos += 12 + length
        if tag == b"IEND":
            break
    return dims[0], dims[1], zlib.decompress(idat)


def main() -> int:
    check = "--check" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    stale = 0
    for name, size, maskable in TARGETS:
        blob = render(size, maskable)
        path = OUT / name
        if check:
            have = path.read_bytes() if path.is_file() else b""
            ok, note = False, ""
            if not have:
                note = "missing"
            else:
                try:
                    hw, hh, hpix = _png_pixels(have)
                    rw, rh, rpix = _png_pixels(blob)
                    if (hw, hh) != (rw, rh):
                        note = f"size {hw}x{hh} != {rw}x{rh}"
                    else:
                        # tiny byte drift is libm rounding noise on a
                        # different platform's float math; real staleness
                        # (mark/colour/size changes) moves orders of
                        # magnitude more
                        diff = sum(a != b for a, b in zip(hpix, rpix))
                        drift = diff / max(1, len(rpix))
                        ok = drift <= 0.001
                        note = f"pixel drift {drift*100:.4f}%"
                except Exception as e:
                    note = f"undecodable: {e}"
            stale += 0 if ok else 1
            print(f"  [{'ok' if ok else 'STALE'}] {name} "
                  f"({len(have)/1024:.1f} KB on disk, {len(blob)/1024:.1f} KB rendered"
                  + (f" — {note}" if note else "") + ")")
            continue
        path.write_bytes(blob)
        print(f"wrote web/icons/{name}  {size}×{size}  {len(blob)/1024:.1f} KB")
    if check and stale:
        print("icons are out of date — run: python tools/make_icons.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
