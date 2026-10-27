"""Hero banner: name, role, typing line, and the Blender-rendered contribution skyline.

The workflow renders the skyline (scripts/render3d/skyline.py) and calls
`build --hero` to embed it here as a data URI: an SVG loaded through <img>
cannot fetch other files. Without a skyline the hero still renders, just
without the 3D image.

The typing effect is pure CSS inside the SVG (clip-path width animated with
steps()), so it works through GitHub's image proxy without any JavaScript.
"""

from __future__ import annotations

import base64

from .theme import BG, BORDER, CYAN, DISPLAY, FAINT, GRID, MONO, MUTED, SANS, TEXT, VIOLET, esc, style_block

PHASE = 5.0  # seconds each phrase stays on screen

# Two layouts: the wide banner, and a taller compact one served to narrow screens
# through <picture media="(max-width: ...)"> so text stays legible on phones.
LAYOUTS = {
    # sky = (x, y, width) of the skyline image; its aspect ratio is fixed by the render (1400x640).
    "wide": dict(w=1200, h=400, x=64, prompt=(100, 15), name=(176, 66), role=(212, 20), typing=(256, 19), rule=300,
                 caption=(64, 352, "start", 13), sky=(540, 0, 700)),
    "compact": dict(w=640, h=560, x=36, prompt=(64, 14), name=(128, 48), role=(160, 17), typing=(196, 14), rule=226,
                    caption=(36, 538, "start", 12), sky=(0, 232, 640)),
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


def render(name: str, login: str, role: str, phrases: list[str], layout: str = "wide",
           skyline: bytes | None = None, caption: str | None = None) -> str:
    L = LAYOUTS[layout]
    W, H, x = L["w"], L["h"], L["x"]
    ty, tsize = L["typing"]
    type_css, type_svg = _typing(phrases, x + int(tsize * 1.1), ty, tsize)
    grid = "".join(f'<line x1="{gx}" y1="0" x2="{gx}" y2="{H}"/>' for gx in range(0, W + 1, 40))
    grid += "".join(f'<line x1="0" y1="{gy}" x2="{W}" y2="{gy}"/>' for gy in range(0, H + 1, 40))
    art = ""
    if skyline:
        sx, sy, sw = L["sky"]
        sh = sw * 640 / 1400
        data = base64.b64encode(skyline).decode()
        art = f'<image x="{sx}" y="{sy}" width="{sw}" height="{sh:.0f}" href="data:image/webp;base64,{data}" mask="url(#skymask)"/>'
    cap = ""
    if skyline and caption:
        cx, cy, anchor, csize = L["caption"]
        cap = f'<text x="{cx}" y="{cy}" text-anchor="{anchor}" font-family="{SANS}" font-size="{csize}" fill="{FAINT}">{esc(caption)}</text>'
    # Wide: the text column sits left, so the image fades in from the left.
    # Compact: the image sits under the text, so it fades in from the top.
    fade = ('x1="0" y1="0" x2="1" y2="0"><stop offset="0.5" stop-color="#000"/><stop offset="0.7" stop-color="#fff"/>'
            if layout == "wide" else
            'x1="0" y1="0" x2="0" y2="1"><stop offset="0.36" stop-color="#000"/><stop offset="0.56" stop-color="#fff"/>')
    body = f"""<g clip-path="url(#frame)">
  <rect width="{W}" height="{H}" fill="{BG}"/>
  <g stroke="{GRID}" stroke-width="1" opacity="0.6">{grid}</g>
  {art}
</g>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="none" stroke="{BORDER}"/>
<text x="{x}" y="{L["prompt"][0]}" font-family="{MONO}" font-size="{L["prompt"][1]}" fill="{MUTED}"><tspan fill="{CYAN}">~/</tspan>{esc(login)} <tspan fill="{FAINT}">$</tspan> whoami</text>
<text x="{x - 3}" y="{L["name"][0]}" font-family="{DISPLAY}" font-size="{L["name"][1]}" font-weight="700" fill="{TEXT}">{esc(name)}</text>
<text x="{x}" y="{L["role"][0]}" font-family="{SANS}" font-size="{L["role"][1]}" fill="{MUTED}">{esc(role)}</text>
<text x="{x}" y="{ty}" font-family="{MONO}" font-size="{tsize}" fill="{VIOLET}">›</text>
{type_svg}
<rect x="{x}" y="{L["rule"]}" width="48" height="3" fill="{CYAN}"/>
{cap}"""
    sky_desc = f" {caption}" if skyline and caption else ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">
<title id="title">{esc(name)}</title>
<desc id="desc">{esc(name)}, {esc(role)}. {esc(' / '.join(phrases))}.{esc(sky_desc)}</desc>
{style_block(body + 'class="m "')}
<style>
{type_css}
</style>
<defs>
  <linearGradient id="skyfade" {fade}</linearGradient>
  <mask id="skymask"><rect width="{W}" height="{H}" fill="url(#skyfade)"/></mask>
  <clipPath id="frame"><rect width="{W}" height="{H}" rx="16"/></clipPath>
</defs>
{body}
</svg>
"""
