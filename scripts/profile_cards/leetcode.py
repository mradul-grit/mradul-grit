"""Optional LeetCode card.

LeetCode has no official public API. This uses the same public GraphQL endpoint
the leetcode.com profile page uses, which needs no login. Because it is
unofficial it can change without notice, so a failed fetch keeps the previous
card (or shows "Data unavailable") and never fails the workflow.
"""

from __future__ import annotations

import json
import shutil
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import cards
from .theme import CARD_W, PAD, PANEL_HI, card, esc, fmt_int

ENDPOINT = "https://leetcode.com/graphql"
QUERY = """
query($u: String!) {
  allQuestionsCount { difficulty count }
  matchedUser(username: $u) {
    username
    profile { ranking }
    submitStatsGlobal { acSubmissionNum { difficulty count } }
  }
}
"""
COLORS = {"Easy": "#2DD4BF", "Medium": "#FBBF24", "Hard": "#F87171"}


def fetch(username: str) -> dict:
    body = json.dumps({"query": QUERY, "variables": {"u": username}}).encode()
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={"Content-Type": "application/json", "Referer": "https://leetcode.com", "User-Agent": "profile-cards"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return parse(json.load(resp))


def parse(payload: dict) -> dict:
    data = payload.get("data") or {}
    user = data.get("matchedUser")
    if not user:
        raise ValueError("LeetCode user not found")
    solved = {row["difficulty"]: row["count"] for row in user["submitStatsGlobal"]["acSubmissionNum"]}
    totals = {row["difficulty"]: row["count"] for row in data.get("allQuestionsCount", [])}
    return {
        "username": user["username"],
        "ranking": (user.get("profile") or {}).get("ranking"),
        "solved": solved,
        "totals": totals,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def render(stats: dict) -> str:
    solved, totals = stats["solved"], stats["totals"]
    body = [
        f'<text x="{PAD}" y="84" class="num" font-size="30">{fmt_int(solved.get("All"))}</text>',
        f'<text x="{PAD}" y="104" class="t muted" font-size="12">solved of {fmt_int(totals.get("All"))}</text>',
    ]
    if stats.get("ranking"):
        body.append(f'<text x="{PAD}" y="124" class="m faint" font-size="11">rank {fmt_int(stats["ranking"])}</text>')
    x0, w = PAD + 130, CARD_W - 2 * PAD - 130
    for i, level in enumerate(("Easy", "Medium", "Hard")):
        y = 66 + i * 38
        have, of = solved.get(level, 0), totals.get(level) or 1
        body.append(f'<text x="{x0}" y="{y}" class="t" font-size="12.5">{level}</text>')
        body.append(f'<text x="{x0 + w}" y="{y}" text-anchor="end" class="m muted" font-size="11">{have}/{of}</text>')
        body.append(f'<rect x="{x0}" y="{y + 8}" width="{w}" height="5" rx="2.5" fill="{PANEL_HI}"/>')
        body.append(f'<rect x="{x0}" y="{y + 8}" width="{max(w * have / of, 2):.1f}" height="5" rx="2.5" fill="{COLORS[level]}"/>')
    body.append(f'<text x="{CARD_W - PAD}" y="{PAD + 10}" text-anchor="end" class="m faint" font-size="10">@{esc(stats["username"])}</text>')
    desc = f"LeetCode: {solved.get('All')} problems solved (easy {solved.get('Easy')}, medium {solved.get('Medium')}, hard {solved.get('Hard')})."
    return card(CARD_W, cards.ROW_H, "".join(body), "LeetCode", "LeetCode", desc, f"daily snapshot · {stats['generated_at']}")


def build(config: dict, out: Path, previous: Path | None) -> int:
    username = (config or {}).get("username", "").strip()
    if not username:
        print("LeetCode username not set; skipping.")
        return 0
    try:
        svg = render(fetch(username))
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError) as err:
        prev = previous / "leetcode.svg" if previous else None
        if prev and prev.exists():
            shutil.copy2(prev, out / "leetcode.svg")
            print(f"::warning::LeetCode unavailable ({err}); kept the previous card.", file=sys.stderr)
        else:
            (out / "leetcode.svg").write_text(
                cards.unavailable("LeetCode", "LeetCode", "LeetCode stats could not be fetched."), encoding="utf-8"
            )
            print(f"::warning::LeetCode unavailable ({err}); wrote a placeholder.", file=sys.stderr)
        return 0
    (out / "leetcode.svg").write_text(svg, encoding="utf-8")
    print("wrote leetcode.svg")
    return 0
