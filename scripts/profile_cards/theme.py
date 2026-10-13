"""Design tokens and small SVG helpers shared by every generated card.

All cards are self-contained dark panels (their own background), so they read
the same on GitHub's light and dark themes. Only system fonts are used: an SVG
loaded through <img> cannot fetch web fonts.
"""

from __future__ import annotations

from html import escape

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

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'JetBrains Mono',Menlo,Consolas,'Liberation Mono',monospace"

# Layout (px). Everything sits on an 8px grid; PAD is the card's inner margin.
PAD = 24
RADIUS = 12
CARD_W = 400
WIDE_W = 804

# Contribution heatmap ramp, from empty to most active.
HEAT = ["#141B2B", "#0E3A4A", "#106379", "#1597AE", "#22D3EE"]


def esc(value: object) -> str:
    return escape(str(value), quote=True)


def style_block() -> str:
    return f"""<style>
  .t {{ font-family: {SANS}; fill: {TEXT}; }}
  .m {{ font-family: {MONO}; }}
  .label {{ font-family: {MONO}; font-size: 11px; letter-spacing: 1.6px; fill: {MUTED}; }}
  .title {{ font-family: {SANS}; font-size: 15px; font-weight: 600; fill: {TEXT}; }}
  .muted {{ fill: {MUTED}; }}
  .faint {{ fill: {FAINT}; }}
  .num {{ font-family: {SANS}; font-weight: 650; fill: {TEXT}; }}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>"""


def card(width: int, height: int, body: str, title: str, label: str, desc: str, stamp: str | None = None) -> str:
    """Wrap card content in the shared frame: panel, hairline border, header row."""
    footer = ""
    if stamp:
        footer = (
            f'<text x="{width - PAD}" y="{height - 14}" text-anchor="end" class="m faint" '
            f'font-size="10">{esc(stamp)}</text>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{esc(title)}</title>
<desc id="desc">{esc(desc)}</desc>
{style_block()}
<defs>
  <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{CYAN}" stop-opacity="0.9"/>
    <stop offset="0.55" stop-color="{VIOLET}" stop-opacity="0.6"/>
    <stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/>
  </linearGradient>
</defs>
<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="{RADIUS}" fill="{PANEL}" stroke="{BORDER}"/>
<rect x="{PAD}" y="0.5" width="{min(140, width - 2 * PAD)}" height="1.5" fill="url(#edge)"/>
<text x="{PAD}" y="{PAD + 10}" class="label">{esc(label.upper())}</text>
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
