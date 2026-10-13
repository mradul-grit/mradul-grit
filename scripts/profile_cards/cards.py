"""SVG card renderers. Each takes normalized data and returns an SVG string."""

from __future__ import annotations

import math
import textwrap
from datetime import date, timedelta

from .theme import (
    BG, BORDER, CARD_W, CYAN, FAINT, HEAT, LOCKED, MUTED, PAD, PANEL_HI,
    TEXT, TIERS, VIOLET, WIDE_W, bar, card, esc, fmt_int,
)

ROW_H = 210  # every half-width card in a row shares this height


def _stamp(data: dict) -> str:
    return f"daily snapshot · {data['generated_at']}"


def _hexagon(cx: float, cy: float, r: float) -> str:
    pts = [(cx + r * math.cos(math.radians(60 * i - 90)), cy + r * math.sin(math.radians(60 * i - 90))) for i in range(6)]
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)


# --- Overview ----------------------------------------------------------------

def overview(data: dict, prog: dict) -> str:
    m = prog["metrics"]
    cells = [
        ("contributions", m["contributions"]),
        ("commits", m["commits"]),
        ("pull requests", m["pull_requests"]),
        ("active days", m["active_days"]),
        ("current streak", m["current_streak"]),
        ("longest streak", m["longest_streak"]),
    ]
    body = []
    col_w = (CARD_W - 2 * PAD) / 3
    for i, (label, value) in enumerate(cells):
        x = PAD + (i % 3) * col_w
        y = 84 + (i // 3) * 64
        suffix = "d" if "streak" in label and value is not None else ""
        body.append(f'<text x="{x}" y="{y}" class="num" font-size="26">{esc(fmt_int(value))}<tspan font-size="15" fill="{MUTED}">{suffix}</tspan></text>')
        body.append(f'<text x="{x}" y="{y + 20}" class="t muted" font-size="12">{esc(label)}</text>')
    since = data["created_at"][:4]
    body.append(f'<text x="{CARD_W - PAD}" y="{PAD + 10}" text-anchor="end" class="m faint" font-size="10">since {since}</text>')
    desc = ", ".join(f"{label}: {fmt_int(v)}" for label, v in cells)
    return card(CARD_W, ROW_H, "".join(body), "GitHub overview", "Overview", desc, _stamp(data))


# --- Languages ---------------------------------------------------------------

def languages(data: dict, prog: dict, exclude: list[str] | None = None, top: int = 6) -> str:
    exclude = set(exclude or [])
    shares = {k: v for k, v in data.get("language_share", {}).items() if k not in exclude}
    total = sum(shares.values()) or 1
    items = sorted(((k, v / total) for k, v in shares.items()), key=lambda kv: -kv[1])
    shown = [kv for kv in items[:top] if kv[1] >= 0.01]
    other = 1 - sum(v for _, v in shown)
    if other >= 0.005:
        shown.append(("Other", other))
    colors = dict(data.get("language_colors", {}), Other=FAINT)

    body = []
    x, w, y = PAD, CARD_W - 2 * PAD, 54
    body.append(f'<clipPath id="lbar"><rect x="{x}" y="{y}" width="{w}" height="10" rx="5"/></clipPath><g clip-path="url(#lbar)">')
    cursor = x
    for name, share in shown:
        seg = w * share
        body.append(f'<rect x="{cursor:.1f}" y="{y}" width="{seg + 0.5:.1f}" height="10" fill="{colors.get(name, MUTED)}"/>')
        cursor += seg
    body.append("</g>")
    for i, (name, share) in enumerate(shown):
        col, row = i % 2, i // 2
        lx = PAD + col * (w / 2)
        ly = 98 + row * 28
        body.append(f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{colors.get(name, MUTED)}"/>')
        body.append(f'<text x="{lx + 18}" y="{ly}" class="t" font-size="13">{esc(name)}</text>')
        body.append(f'<text x="{lx + w / 2 - 16}" y="{ly}" text-anchor="end" class="m muted" font-size="12">{share * 100:.1f}%</text>')
    if not shown:
        body.append(f'<text x="{PAD}" y="110" class="t muted" font-size="13">No public code to measure yet.</text>')
    body.append(f'<text x="{CARD_W - PAD}" y="{PAD + 10}" text-anchor="end" class="m faint" font-size="10">by bytes · public repos</text>')
    desc = "Language share by bytes across public repositories: " + ", ".join(f"{n} {s * 100:.1f}%" for n, s in shown)
    return card(CARD_W, ROW_H, "".join(body), "Languages", "Languages", desc, _stamp(data))


# --- Activity (wide) ---------------------------------------------------------

def activity(data: dict, prog: dict, compact: bool = False) -> str:
    """Wide: 52-week heatmap plus last-30-days repos. Compact (phones): 26 weeks, heatmap only."""
    weeks = 26 if compact else 52
    width = CARD_W if compact else WIDE_W
    days = {d["date"]: d["count"] for d in data.get("calendar", [])}
    end = date.fromisoformat(max(days)) if days else date.today()
    start = end - timedelta(days=(end.weekday() + 1) % 7 + weeks * 7)  # weeks start on Sunday
    peak = max([c for d, c in days.items() if d >= start.isoformat()] or [0])
    cell, gap = (10, 2) if compact else (9, 2)
    gx, gy = PAD, 66
    body = []
    year_total = 0
    d, col = start, 0
    last_month = None
    while d <= end:
        row = (d.weekday() + 1) % 7
        if row == 0 and d != start:
            col += 1
        count = days.get(d.isoformat(), 0)
        year_total += count
        level = 0 if count == 0 else min(4, 1 + int(3 * count / max(peak, 1)))
        body.append(f'<rect x="{gx + col * (cell + gap)}" y="{gy + row * (cell + gap)}" width="{cell}" height="{cell}" rx="2" fill="{HEAT[level]}"/>')
        if row == 0 and d.month != last_month and d.day <= 7:
            body.append(f'<text x="{gx + col * (cell + gap)}" y="{gy - 8}" class="m faint" font-size="10">{d.strftime("%b")}</text>')
            last_month = d.month
        d += timedelta(days=1)
    grid_right = gx + (col + 1) * (cell + gap)
    ly = gy + 7 * (cell + gap) + 12
    if not compact:  # legend, right-aligned under the grid
        lx = grid_right - 5 * (cell + gap) - 30
        body.append(f'<text x="{lx - 6}" y="{ly + 8}" text-anchor="end" class="m faint" font-size="10">less</text>')
        for i, c in enumerate(HEAT):
            body.append(f'<rect x="{lx + i * (cell + gap)}" y="{ly}" width="{cell}" height="{cell}" rx="2" fill="{c}"/>')
        body.append(f'<text x="{lx + 5 * (cell + gap) + 4}" y="{ly + 8}" class="m faint" font-size="10">more</text>')
    m = prog["metrics"]
    span = "6 months" if compact else "year"
    body.append(f'<text x="{gx}" y="{ly + 8}" class="t muted" font-size="12"><tspan class="num" font-size="13" fill="{TEXT}">{fmt_int(year_total)}</tspan> in the last {span} · longest streak <tspan fill="{TEXT}">{m["longest_streak"]}d</tspan></text>')
    if compact:
        desc = f"{year_total} contributions in the last 6 months. Longest streak {m['longest_streak']} days."
        return card(width, ROW_H, "".join(body), "Contribution activity", "Contributions · 6 months", desc, _stamp(data))

    # Right column: where the last 30 days of public commits went.
    rx = grid_right + 32
    body.append(f'<line x1="{rx - 16}" y1="50" x2="{rx - 16}" y2="{ROW_H - 40}" stroke="{BORDER}"/>')
    body.append(f'<text x="{rx}" y="{PAD + 10}" class="label">LAST 30 DAYS</text>')
    recent = data.get("recent", [])[:4]
    if not recent:
        body.append(f'<text x="{rx}" y="74" class="t muted" font-size="12">No public commits</text>')
    top = max([r["commits"] for r in recent] or [1])
    for i, r in enumerate(recent):
        y = 66 + i * 30
        name = r["name"] if len(r["name"]) <= 17 else r["name"][:16] + "…"
        body.append(f'<text x="{rx}" y="{y}" class="t" font-size="13">{esc(name)}</text>')
        body.append(f'<text x="{WIDE_W - PAD}" y="{y}" text-anchor="end" class="m muted" font-size="11">{r["commits"]}</text>')
        bw = (WIDE_W - PAD - rx) * r["commits"] / top
        body.append(f'<rect x="{rx}" y="{y + 7}" width="{WIDE_W - PAD - rx}" height="3" rx="1.5" fill="{PANEL_HI}"/>')
        body.append(f'<rect x="{rx}" y="{y + 7}" width="{max(bw, 3):.1f}" height="3" rx="1.5" fill="{r.get("language_color") or CYAN}"/>')
    desc = f"{year_total} contributions in the last year. Longest streak {m['longest_streak']} days. Recent public commits: " + ", ".join(
        f"{r['name']} {r['commits']}" for r in recent
    )
    return card(WIDE_W, ROW_H, "".join(body), "Contribution activity", "Contributions · last 12 months", desc, _stamp(data))


# --- Level -------------------------------------------------------------------

def level(data: dict, prog: dict) -> str:
    cx, cy, r = PAD + 52, 112, 46
    frac = prog["level_frac"]
    circ = 2 * math.pi * (r + 9)
    body = [
        f'<defs><linearGradient id="ring" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{CYAN}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient></defs>',
        f'<circle cx="{cx}" cy="{cy}" r="{r + 9}" fill="none" stroke="{PANEL_HI}" stroke-width="4"/>',
        f'<circle cx="{cx}" cy="{cy}" r="{r + 9}" fill="none" stroke="url(#ring)" stroke-width="4" stroke-linecap="round" '
        f'stroke-dasharray="{circ * frac:.1f} {circ:.1f}" transform="rotate(-90 {cx} {cy})"/>',
        f'<polygon points="{_hexagon(cx, cy, r)}" fill="{BG}" stroke="{BORDER}" stroke-width="1.5"/>',
        f'<polygon points="{_hexagon(cx, cy, r - 8)}" fill="none" stroke="{CYAN}" stroke-opacity="0.35"/>',
        f'<text x="{cx}" y="{cy - 6}" text-anchor="middle" class="label" font-size="10">LEVEL</text>',
        f'<text x="{cx}" y="{cy + 22}" text-anchor="middle" class="num" font-size="30">{prog["level"]}</text>',
    ]
    tx = cx + r + 34
    w = CARD_W - PAD - tx
    to_next = prog["level_next"] - prog["xp"]
    body += [
        f'<text x="{tx}" y="78" class="t" font-size="20" font-weight="650">{esc(prog["rank"])}</text>',
        f'<text x="{tx}" y="100" class="m muted" font-size="12"><tspan fill="{CYAN}">{prog["xp"]:,}</tspan> XP total</text>',
        bar(tx, 116, w, 8, frac, "xpbar"),
        f'<text x="{tx}" y="142" class="m faint" font-size="11">{to_next:,} XP to level {prog["level"] + 1}</text>',
    ]
    rows = sorted(prog["xp_rows"], key=lambda r: -r[2])
    total = prog["xp"] or 1
    names = {"contribution": "contributions", "active_day": "active days", "public_repo": "repos", "pull_request": "PRs",
             "review": "reviews", "issue": "issues", "star": "stars", "external_repo": "external repos"}
    k, _, top_xp = rows[0]
    src = f"most XP from {names[k]} ({top_xp * 100 / total:.0f}%)" if top_xp else "no XP yet"
    body.append(f'<text x="{tx}" y="166" class="t muted" font-size="11">{esc(src)}</text>')
    desc = f"Level {prog['level']} {prog['rank']}, {prog['xp']} XP, {to_next} XP to the next level. XP comes from public GitHub activity using documented rules."
    return card(CARD_W, ROW_H, "".join(body), "Developer level", "Progression", desc, "profile system · not a GitHub feature")


# --- Achievements ------------------------------------------------------------

def achievements(data: dict, prog: dict) -> str:
    items = prog["achievements"]
    body = []
    cols, cw, ch = 4, (CARD_W - 2 * PAD) / 4, 74
    earned = sum(1 for a in items if a["tier"])
    body.append(f'<text x="{CARD_W - PAD}" y="{PAD + 10}" text-anchor="end" class="m faint" font-size="10">{earned}/{len(items)} earned</text>')
    for i, a in enumerate(items):
        x = PAD + (i % cols) * cw + cw / 2
        y = 72 + (i // cols) * ch
        color = TIERS[a["tier"]] if a["tier"] else LOCKED
        opacity = "1" if a["tier"] else "0.9"
        body.append(f'<polygon points="{_hexagon(x, y, 15)}" fill="{BG}" stroke="{color}" stroke-width="1.6" opacity="{opacity}"/>')
        pips = {"bronze": 1, "silver": 2, "gold": 3}.get(a["tier"] or "", 0)
        for p in range(3):
            body.append(f'<circle cx="{x - 6 + p * 6}" cy="{y}" r="1.8" fill="{color if p < pips else LOCKED}"/>')
        title_cls = "t" if a["tier"] else "t faint"
        body.append(f'<text x="{x}" y="{y + 30}" text-anchor="middle" class="{title_cls}" font-size="11.5" font-weight="600">{esc(a["title"])}</text>')
        if a["value"] is None:
            sub = "no data"
        elif a["next"] is None:
            sub = "gold · maxed"
        else:
            sub = f"{fmt_int(a['value'])}/{fmt_int(a['next'])}"
        body.append(f'<text x="{x}" y="{y + 44}" text-anchor="middle" class="m faint" font-size="10">{esc(sub)}</text>')
    desc = "Achievements computed from GitHub data: " + "; ".join(
        f"{a['title']} {a['tier'] or 'locked'} ({a['value']} {a['unit']})" for a in items
    )
    return card(CARD_W, ROW_H, "".join(body), "Achievements", "Achievements", desc)


# --- Milestones --------------------------------------------------------------

def milestones(data: dict, prog: dict) -> str:
    items = prog["milestones"][-5:]
    body = []
    x = PAD + 6
    if items:
        body.append(f'<line x1="{x}" y1="58" x2="{x}" y2="{58 + (len(items) - 1) * 26}" stroke="{BORDER}" stroke-width="1.5"/>')
    for i, (when, text) in enumerate(items):
        y = 58 + i * 26
        color = CYAN if i == len(items) - 1 else VIOLET
        body.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{BG}" stroke="{color}" stroke-width="1.6"/>')
        body.append(f'<text x="{x + 16}" y="{y + 4}" class="m muted" font-size="11">{esc(when)}</text>')
        body.append(f'<text x="{x + 104}" y="{y + 4}" class="t" font-size="12.5">{esc(text)}</text>')
    if not items:
        body.append(f'<text x="{PAD}" y="80" class="t muted" font-size="13">Milestones appear as activity is recorded.</text>')
    desc = "Milestones: " + "; ".join(f"{w} {t}" for w, t in items)
    return card(CARD_W, ROW_H, "".join(body), "Milestones", "Milestones", desc, _stamp(data))


# --- Quests ------------------------------------------------------------------

def quests(data: dict, prog: dict) -> str:
    items = prog["quests"][:4]
    body = [f'<text x="{CARD_W - PAD}" y="{PAD + 10}" text-anchor="end" class="m faint" font-size="10">self-set</text>']
    w = CARD_W - 2 * PAD
    for i, q in enumerate(items):
        y = 64 + i * 34
        mark = "✓" if q["done"] else "○"
        color = CYAN if q["done"] else FAINT
        body.append(f'<text x="{PAD}" y="{y}" class="m" font-size="12" fill="{color}">{mark}</text>')
        body.append(f'<text x="{PAD + 18}" y="{y}" class="t" font-size="12.5">{esc(q["title"])}</text>')
        if q["auto"]:
            frac = 0 if q["value"] is None else q["value"] / q["target"]
            shown = "no data" if q["value"] is None else f"{fmt_int(q['value'])}/{fmt_int(q['target'])}"
            body.append(f'<text x="{PAD + w}" y="{y}" text-anchor="end" class="m muted" font-size="11">{shown}</text>')
            body.append(bar(PAD + 18, y + 8, w - 18, 4, frac, f"q{i}"))
    if not items:
        body.append(f'<text x="{PAD}" y="80" class="t muted" font-size="13">No goals set.</text>')
    desc = "Self-set goals, not achievements: " + "; ".join(
        f"{q['title']} ({'done' if q['done'] else 'in progress'})" for q in items
    )
    return card(CARD_W, ROW_H, "".join(body), "Quests", "Quests · goals", desc, "goals, not achievements")


# --- Repository card ---------------------------------------------------------

def repo(data: dict, name: str, tagline: str | None, stack: list[str]) -> str:
    r = next((x for x in data.get("repos", []) if x["name"].lower() == name.lower()), None)
    if r is None:
        return unavailable(f"Repository {name}", "Repository", "This repository is private or was renamed.", CARD_W, 140)
    text = tagline or r["description"] or "No description yet."
    lines = textwrap.wrap(text, 54)[:2]
    body = [f'<text x="{PAD}" y="{PAD + 34}" class="t" font-size="17" font-weight="650">{esc(r["name"])}</text>']
    for i, line in enumerate(lines):
        body.append(f'<text x="{PAD}" y="{PAD + 58 + i * 18}" class="t muted" font-size="12.5">{esc(line)}</text>')
    y = 140 - 22
    x = PAD
    if r["language"]:
        body.append(f'<circle cx="{x + 5}" cy="{y - 4}" r="5" fill="{r["language_color"] or MUTED}"/>')
        body.append(f'<text x="{x + 15}" y="{y}" class="t muted" font-size="11.5">{esc(r["language"])}</text>')
        x += 24 + 7 * len(r["language"])
    for s in stack[:3]:
        body.append(f'<text x="{x}" y="{y}" class="m faint" font-size="11">{esc(s)}</text>')
        x += 14 + 6.8 * len(s)
    if r["stars"]:
        body.append(f'<text x="{CARD_W - PAD}" y="{y}" text-anchor="end" class="m muted" font-size="11">★ {r["stars"]}</text>')
    body.append(f'<text x="{CARD_W - PAD}" y="{PAD + 10}" text-anchor="end" class="m faint" font-size="10">updated {r["pushed_at"][:10]}</text>')
    desc = f"{r['name']}: {text} Language: {r['language']}."
    return card(CARD_W, 140, "".join(body), r["name"], "Repository", desc)


# --- Fallback ----------------------------------------------------------------

def unavailable(title: str, label: str, reason: str, width: int = CARD_W, height: int = ROW_H) -> str:
    body = (
        f'<text x="{PAD}" y="{height / 2 + 2}" class="t" font-size="14">Data unavailable</text>'
        f'<text x="{PAD}" y="{height / 2 + 22}" class="t muted" font-size="12">{esc(reason)}</text>'
    )
    return card(width, height, body, title, label, f"{title}: data unavailable. {reason}")
