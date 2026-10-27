"""Design tokens and small SVG helpers shared by every generated card.

All cards are self-contained dark panels (their own background), so they read
the same on GitHub's light and dark themes. Only system fonts are used: an SVG
loaded through <img> cannot fetch web fonts.
"""

from __future__ import annotations

import base64
from datetime import datetime
from functools import lru_cache
from html import escape
from pathlib import Path

# Palette: one primary accent (cyan), one secondary (violet), one quiet support
# (blue). Everything else is neutral so the accents stay meaningful.
BG = "#0B0F17"
PANEL = "#0F1522"
PANEL_HI = "#141B2B"
BORDER = "#1F2A3C"
GRID = "#151D2C"
TEXT = "#E6EDF3"
MUTED = "#8B98A9"
FAINT = "#77849A"  # 4.8:1 on PANEL, the floor for small text
CYAN = "#22D3EE"
VIOLET = "#A78BFA"
BLUE = "#60A5FA"
LOCKED = "#2A3446"

# Tier colors for achievements. Muted metals, not saturated gold/silver clip art.
TIERS = {
    "bronze": "#C08457",
    "silver": "#B8C4D6",
    "gold": "#E8C268",
}

# Type: Chakra Petch (angular, technical) for display and figures, IBM Plex Sans
# for reading text, IBM Plex Mono only for the hero's terminal lines. The fonts
# are subset to Latin and embedded in each SVG, because an SVG loaded through
# <img> cannot fetch web fonts. Licenses: assets/fonts/OFL.txt.
DISPLAY = "'Chakra Petch','Segoe UI',Helvetica,Arial,sans-serif"
SANS = "'IBM Plex Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"
FONTS = {  # family -> weights shipped in assets/fonts
    "Chakra Petch": (600, 700),
    "IBM Plex Sans": (400, 600),
    "IBM Plex Mono": (400,),
}

# Layout (px). Everything sits on an 8px grid; PAD is the card's inner margin.
PAD = 24
RADIUS = 12
CARD_W = 400
WIDE_W = 804

# Contribution heatmap ramp, from empty to most active.
HEAT = ["#141B2B", "#0E3A4A", "#106379", "#1597AE", "#22D3EE"]


def esc(value: object) -> str:
    return escape(str(value), quote=True)


@lru_cache(maxsize=None)
def _face(family: str, weight: int) -> str:
    path = FONT_DIR / f"{family.lower().replace(' ', '-')}-{weight}.woff2"
    data = base64.b64encode(path.read_bytes()).decode()
    return f"@font-face {{ font-family: '{family}'; font-weight: {weight}; src: url(data:font/woff2;base64,{data}) format('woff2'); }}"


def font_faces(svg_body: str) -> str:
    """@font-face rules for the families this SVG actually uses."""
    used = {"IBM Plex Sans", "Chakra Petch"}  # body text and card headings
    if "IBM Plex Mono" in svg_body or 'class="m ' in svg_body or 'class="m"' in svg_body:
        used.add("IBM Plex Mono")
    bold = 'font-weight="700"' in svg_body
    return "\n".join(_face(f, w) for f in sorted(used) for w in FONTS[f] if w != 700 or bold)


def style_block(body: str = "") -> str:
    return f"""<style>
  {font_faces(body)}
  .t {{ font-family: {SANS}; fill: {TEXT}; }}
  .m {{ font-family: {MONO}; }}
  .head {{ font-family: {DISPLAY}; font-size: 16px; font-weight: 600; fill: {TEXT}; letter-spacing: 0.2px; }}
  .muted {{ fill: {MUTED}; }}
  .faint {{ fill: {FAINT}; }}
  .tn {{ font-variant-numeric: tabular-nums; }}
  .num {{ font-family: {DISPLAY}; font-weight: 600; fill: {TEXT}; font-variant-numeric: tabular-nums; }}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>"""


def short_date(iso_day: str) -> str:
    """2026-10-13 -> 13 Oct 2026"""
    d = datetime.strptime(iso_day[:10], "%Y-%m-%d")
    return f"{d.day} {d.strftime('%b %Y')}"


def stamp_text(generated_at: str) -> str:
    """'2026-10-13 15:09 UTC' -> 'Updated 13 Oct 2026, 15:09 UTC'"""
    try:
        return f"Updated {short_date(generated_at[:10])}, {generated_at[11:]}"
    except ValueError:
        return f"Updated {generated_at}"


def card(width: int, height: int, body: str, title: str, label: str, desc: str, stamp: str | None = None) -> str:
    """Wrap card content in the shared frame: panel, hairline border, header row."""
    footer = ""
    if stamp:
        footer = (
            f'<text x="{width - PAD}" y="{height - 14}" text-anchor="end" class="t faint" '
            f'font-size="11.5">{esc(stamp)}</text>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{esc(title)}</title>
<desc id="desc">{esc(desc)}</desc>
{style_block(body + footer)}
<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="{RADIUS}" fill="{PANEL}" stroke="{BORDER}"/>
<text x="{PAD}" y="{PAD + 12}" class="head">{esc(label)}</text>
{body}
{footer}
</svg>
"""


def bar(x: float, y: float, w: float, h: float, frac: float, grad_id: str = "bar") -> str:
    frac = max(0.0, min(1.0, frac))
    fill_w = max(h, w * frac) if frac > 0 else 0
    out = [
        f'<defs><linearGradient id="{grad_id}" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{CYAN}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient></defs>',
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}" fill="{PANEL_HI}" stroke="{BORDER}"/>',
    ]
    if fill_w:
        out.append(f'<rect x="{x}" y="{y}" width="{fill_w:.1f}" height="{h}" rx="{h / 2}" fill="url(#{grad_id})"/>')
    return "".join(out)


def fmt_int(n: int | None) -> str:
    if n is None:
        return "n/a"
    if n >= 10_000:
        return f"{n / 1000:.1f}k"
    return f"{n:,}"
