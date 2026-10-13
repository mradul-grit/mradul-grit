"""Static hero banner. Regenerate with `python -m scripts.profile_cards.build --static`.

The typing effect is pure CSS inside the SVG (clip-path width animated with
steps()), so it works through GitHub's image proxy without any JavaScript.
"""

from __future__ import annotations

from .theme import BG, BORDER, CYAN, FAINT, GRID, MONO, MUTED, SANS, TEXT, VIOLET, BLUE, esc

PHASE = 5.0  # seconds each phrase stays on screen

# Two layouts: the wide banner, and a taller compact one served to narrow screens
# through <picture media="(max-width: ...)"> so text stays legible on phones.
LAYOUTS = {
    "wide": dict(w=1200, h=340, x=72, prompt=(92, 15), name=(160, 62), role=(192, 20), typing=(228, 24), rule=270,
                 net=(1010, 170, 1.0)),
    "compact": dict(w=640, h=380, x=40, prompt=(70, 14), name=(132, 46), role=(162, 17), typing=(200, 15), rule=232,
                    net=(500, 296, 0.55)),
}


def _typing(phrases: list[str], x: int, y: int, size: int) -> tuple[str, str]:
    char_w = size * 0.61  # monospace advance; padded below so wider fallbacks still fit
    total = PHASE * len(phrases)
    css, groups = [], []
    for i, phrase in enumerate(phrases):
        width = int(len(phrase) * char_w) + 16
        start = i * PHASE / total * 100
        typed = (i * PHASE + 1.6) / total * 100
        hold = (i * PHASE + PHASE - 0.6) / total * 100
        end = (i + 1) * PHASE / total * 100
        if i == 0:
            caret_start = "0% { transform: translateX(0); opacity: 1; } "
        else:  # hidden until its phrase starts, so only one caret is ever visible
            caret_start = (f"0%, {start - 0.01:.2f}% {{ transform: translateX(0); opacity: 0; }} "
                           f"{start:.2f}% {{ transform: translateX(0); opacity: 1; }} ")
        steps = max(len(phrase), 1)
        css.append(
            f"@keyframes type{i} {{ 0%, {start:.2f}% {{ width: 0; }} {typed:.2f}% {{ width: {width}px; }} "
            f"{hold:.2f}% {{ width: {width}px; }} {end:.2f}%, 100% {{ width: 0; }} }}\n"
            f"@keyframes caret{i} {{ {caret_start}"
            f"{typed:.2f}% {{ transform: translateX({width - 12}px); }} {hold:.2f}% {{ transform: translateX({width - 12}px); opacity: 1; }} "
            f"{end:.2f}% {{ transform: translateX(0); opacity: 0; }} 100% {{ opacity: 0; }} }}\n"
            f"#clip{i} rect {{ animation: type{i} {total}s steps({steps}, end) infinite; }}\n"
            f"#caret{i} {{ animation: caret{i} {total}s steps({steps}, end) infinite, blink 1s step-end infinite; }}\n"
        )
        groups.append(
            f'<clipPath id="clip{i}"><rect x="{x}" y="{y - size}" width="0" height="{size + 10}"/></clipPath>'
            f'<text x="{x}" y="{y}" clip-path="url(#clip{i})" font-family="{MONO}" font-size="{size}" fill="{TEXT}">{esc(phrase)}</text>'
            f'<g id="caret{i}"><rect x="{x + 2}" y="{y - size + 3}" width="{max(6, size // 2 - 1)}" height="{size}" fill="{CYAN}" opacity="0.85"/></g>'
        )
    css.append("@keyframes blink { 50% { fill-opacity: 0; } }\n")
    # Static fallback: with reduced motion only the first phrase is shown, fully typed.
    first = int(len(phrases[0]) * char_w) + 16
    css.append(
        "@media (prefers-reduced-motion: reduce) { "
        + " ".join(f"#clip{i} rect, #caret{i} {{ animation: none; }}" for i in range(len(phrases)))
        + f" #clip0 rect {{ width: {first}px; }}"
        + " ".join(f" #caret{i} {{ opacity: 0; }}" for i in range(len(phrases)))
        + " }\n"
    )
    return "".join(css), "".join(groups)


def _network(cx: int, cy: int, scale: float = 1.0) -> str:
    """Quiet node graph on the right: the visual motif for 'systems that talk to each other'."""
    nodes = [(0, 0), (-110, -70), (-140, 40), (-40, 105), (95, 70), (120, -50), (20, -115), (-200, -10)]
    edges = [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (1, 6), (1, 7), (2, 7), (3, 4), (4, 5), (5, 6), (2, 3)]
    out = []
    for a, b in edges:
        (x1, y1), (x2, y2) = nodes[a], nodes[b]
        out.append(f'<line x1="{cx + x1}" y1="{cy + y1}" x2="{cx + x2}" y2="{cy + y2}" stroke="{BORDER}" stroke-width="1.2"/>')
    # A few edges carry a travelling pulse.
    for i, (a, b) in enumerate([(7, 1), (1, 0), (2, 0), (0, 4), (0, 5)]):
        (x1, y1), (x2, y2) = nodes[a], nodes[b]
        color = CYAN if i % 2 == 0 else VIOLET
        out.append(
            f'<line x1="{cx + x1}" y1="{cy + y1}" x2="{cx + x2}" y2="{cy + y2}" stroke="{color}" stroke-width="1.6" '
            f'stroke-linecap="round" stroke-dasharray="10 400" class="pulse" style="animation-delay:{i * 0.9:.1f}s"/>'
        )
    for i, (x, y) in enumerate(nodes):
        r = 9 if i == 0 else 4.5
        color = CYAN if i in (0, 4, 7) else (VIOLET if i in (1, 5) else BLUE)
        glow = ' filter="url(#glow)"' if i == 0 else ""
        out.append(f'<circle cx="{cx + x}" cy="{cy + y}" r="{r}" fill="{BG}" stroke="{color}" stroke-width="1.6"{glow}/>')
    out.append(f'<circle cx="{cx}" cy="{cy}" r="3" fill="{CYAN}"/>')
    return f'<g transform="translate({cx} {cy}) scale({scale}) translate({-cx} {-cy})">' + "".join(out) + "</g>"


def render(name: str, login: str, role: str, phrases: list[str], layout: str = "wide") -> str:
    L = LAYOUTS[layout]
    W, H, x = L["w"], L["h"], L["x"]
    ty, tsize = L["typing"]
    type_css, type_svg = _typing(phrases, x + int(tsize * 1.1), ty, tsize)
    grid = "".join(f'<line x1="{gx}" y1="0" x2="{gx}" y2="{H}"/>' for gx in range(0, W + 1, 40))
    grid += "".join(f'<line x1="0" y1="{gy}" x2="{W}" y2="{gy}"/>' for gy in range(0, H + 1, 40))
    halo_cx = L["net"][0] / W
    halo_cy = L["net"][1] / H
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">
<title id="title">{esc(name)}</title>
<desc id="desc">{esc(name)}, {esc(role)}. {esc(' / '.join(phrases))}.</desc>
<style>
{type_css}
@keyframes pulse {{ from {{ stroke-dashoffset: 410; }} to {{ stroke-dashoffset: 0; }} }}
.pulse {{ animation: pulse 4.5s linear infinite; }}
@media (prefers-reduced-motion: reduce) {{ .pulse {{ animation: none; opacity: 0; }} }}
</style>
<defs>
  <radialGradient id="halo" cx="{halo_cx:.2f}" cy="{halo_cy:.2f}" r="0.5">
    <stop offset="0" stop-color="{CYAN}" stop-opacity="0.16"/>
    <stop offset="0.5" stop-color="{VIOLET}" stop-opacity="0.06"/>
    <stop offset="1" stop-color="{BG}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="fade" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{BG}" stop-opacity="1"/>
    <stop offset="0.45" stop-color="{BG}" stop-opacity="0.7"/>
    <stop offset="1" stop-color="{BG}" stop-opacity="0.2"/>
  </linearGradient>
  <linearGradient id="rule" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{CYAN}"/><stop offset="0.5" stop-color="{VIOLET}"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/>
  </linearGradient>
  <filter id="glow" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <clipPath id="frame"><rect width="{W}" height="{H}" rx="16"/></clipPath>
</defs>
<g clip-path="url(#frame)">
  <rect width="{W}" height="{H}" fill="{BG}"/>
  <g stroke="{GRID}" stroke-width="1">{grid}</g>
  <rect width="{W}" height="{H}" fill="url(#fade)"/>
  <rect width="{W}" height="{H}" fill="url(#halo)"/>
  {_network(*L["net"])}
  <rect x="0" y="0" width="{W}" height="2" fill="url(#rule)"/>
</g>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="none" stroke="{BORDER}"/>
<text x="{x}" y="{L["prompt"][0]}" font-family="{MONO}" font-size="{L["prompt"][1]}" fill="{MUTED}" letter-spacing="0.5"><tspan fill="{CYAN}">~/</tspan>{esc(login)} <tspan fill="{FAINT}">$</tspan> whoami</text>
<text x="{x - 2}" y="{L["name"][0]}" font-family="{SANS}" font-size="{L["name"][1]}" font-weight="700" fill="{TEXT}" letter-spacing="{-L["name"][1] / 40:.1f}">{esc(name)}</text>
<text x="{x}" y="{L["role"][0]}" font-family="{SANS}" font-size="{L["role"][1]}" fill="{MUTED}">{esc(role)}</text>
<text x="{x}" y="{ty}" font-family="{MONO}" font-size="{tsize}" fill="{VIOLET}">›</text>
{type_svg}
<rect x="{x}" y="{L["rule"]}" width="56" height="2" fill="{CYAN}"/>
</svg>
"""
