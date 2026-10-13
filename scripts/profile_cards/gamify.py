"""Developer progression: XP, levels, achievement tiers, milestones and quests.

Every number here is derived from the normalized GitHub data produced by
github_api.fetch_profile(). Nothing is entered by hand except quests, which are
labelled as self-set goals wherever they are shown. docs/XP_RULES.md documents
these rules; keep the two in sync (tests/test_gamify.py checks the table).

These levels and achievements are this profile's own system. They are not
GitHub achievements and are never presented as such.
"""

from __future__ import annotations

import math

# --- XP rules --------------------------------------------------------------

DAILY_CAP = 12  # contributions per day that earn XP; stops one bulk-commit day from dominating
XP_RULES = {
    "contribution": 3,  # per contribution on the calendar, up to DAILY_CAP per day
    "active_day": 5,  # per day with at least one contribution
    "pull_request": 20,  # per pull request opened
    "review": 15,  # per pull request review
    "issue": 8,  # per issue opened
    "public_repo": 40,  # per public, non-fork repository you own
    "star": 10,  # per star on those repositories
    "external_repo": 30,  # per repository owned by someone else that you opened a PR to
}

# --- Levels ----------------------------------------------------------------
# XP needed to reach level L is 50 * L * (L - 1): 0, 100, 300, 600, 1000, ...

RANKS = [(1, "Initiate"), (3, "Builder"), (6, "Shipper"), (10, "Maintainer"), (15, "Veteran")]


def level_threshold(level: int) -> int:
    return 50 * level * (level - 1)


def level_for(xp: int) -> int:
    # Largest L with 50 L (L-1) <= xp.
    level = int((1 + math.sqrt(1 + 0.08 * xp)) / 2)
    while level_threshold(level + 1) <= xp:
        level += 1
    while level > 1 and level_threshold(level) > xp:
        level -= 1
    return max(level, 1)


def rank_for(level: int) -> str:
    name = RANKS[0][1]
    for start, label in RANKS:
        if level >= start:
            name = label
    return name


# --- Achievements ----------------------------------------------------------
# (key, title, metric, (bronze, silver, gold), what the metric counts)

ACHIEVEMENTS = [
    ("commits", "Committed", "commits", (50, 250, 1000), "commits"),
    ("streak", "Consistent", "longest_streak", (7, 30, 100), "day streak"),
    ("active", "Regular", "active_days", (30, 100, 250), "active days"),
    ("repos", "Portfolio", "public_repos", (3, 10, 25), "public repos"),
    ("polyglot", "Polyglot", "languages", (3, 5, 8), "languages"),
    ("prs", "Collaborator", "pull_requests", (5, 25, 100), "pull requests"),
    ("reviews", "Reviewer", "reviews", (5, 25, 100), "reviews"),
    ("oss", "Contributor", "external_repos", (1, 3, 10), "external repos"),
]
TIER_NAMES = ("bronze", "silver", "gold")


def _streaks(days: list[dict]) -> tuple[int, int, tuple[str, str] | None]:
    """Return (current, longest, longest_range) over a date-sorted calendar."""
    longest = run = 0
    best: tuple[str, str] | None = None
    run_start = None
    for d in days:
        if d["count"] > 0:
            run += 1
            run_start = run_start or d["date"]
            if run > longest:
                longest, best = run, (run_start, d["date"])
        else:
            run, run_start = 0, None
    # Current streak: today may still be empty, so it does not break the streak.
    current = 0
    for i, d in enumerate(reversed(days)):
        if d["count"] > 0:
            current += 1
        elif i == 0:
            continue
        else:
            break
    return current, longest, best


def metrics(data: dict) -> dict:
    days = sorted(data.get("calendar", []), key=lambda d: d["date"])
    totals = data.get("totals", {})
    current, longest, best = _streaks(days)
    langs = data.get("language_share", {})
    return {
        "contributions": sum(d["count"] for d in days),
        "active_days": sum(1 for d in days if d["count"] > 0),
        "current_streak": current,
        "longest_streak": longest,
        "longest_range": best,
        "commits": totals.get("commits"),
        "pull_requests": totals.get("pull_requests"),
        "reviews": totals.get("reviews"),
        "issues": totals.get("issues"),
        "public_repos": len(data.get("repos", [])),
        "stars": sum(r.get("stars", 0) for r in data.get("repos", [])),
        "languages": sum(1 for share in langs.values() if share >= 0.02),
        "external_repos": totals.get("external_repos"),
    }


def xp_breakdown(data: dict, m: dict) -> list[tuple[str, int, int]]:
    """Rows of (rule, count, xp). Unknown counts (None) earn nothing rather than a guess."""
    days = data.get("calendar", [])
    capped = sum(min(d["count"], DAILY_CAP) for d in days)
    rows = [
        ("contribution", capped, capped * XP_RULES["contribution"]),
        ("active_day", m["active_days"], m["active_days"] * XP_RULES["active_day"]),
    ]
    for rule, key in [
        ("pull_request", "pull_requests"),
        ("review", "reviews"),
        ("issue", "issues"),
        ("public_repo", "public_repos"),
        ("star", "stars"),
        ("external_repo", "external_repos"),
    ]:
        n = m.get(key) or 0
        rows.append((rule, n, n * XP_RULES[rule]))
    return rows


def achievements(m: dict) -> list[dict]:
    out = []
    for key, title, metric, thresholds, unit in ACHIEVEMENTS:
        value = m.get(metric)
        tier = None
        if value is not None:
            for name, need in zip(TIER_NAMES, thresholds):
                if value >= need:
                    tier = name
        nxt = None
        if value is not None:
            nxt = next((need for need in thresholds if value < need), None)
        out.append(
            {
                "key": key,
                "title": title,
                "value": value,
                "tier": tier,
                "next": nxt,
                "unit": unit,
                "thresholds": thresholds,
            }
        )
    return out


def milestones(data: dict, m: dict) -> list[tuple[str, str]]:
    """(date, text) pairs, oldest first. Only events that the data actually dates."""
    days = sorted(data.get("calendar", []), key=lambda d: d["date"])
    out: list[tuple[str, str]] = []
    repos = sorted(data.get("repos", []), key=lambda r: r["created_at"])
    if repos:
        out.append((repos[0]["created_at"][:10], f"First public repo: {repos[0]['name']}"))
    running = 0
    marks = [1, 100, 250, 500, 1000, 2500, 5000]
    for d in days:
        before = running
        running += d["count"]
        for mark in marks:
            if before < mark <= running:
                text = "First contribution on record" if mark == 1 else f"{mark:,}th contribution"
                out.append((d["date"], text))
    if days:
        peak = max(days, key=lambda d: d["count"])
        if peak["count"] > 0:
            out.append((peak["date"], f"Busiest day: {peak['count']} contributions"))
    if m.get("longest_range") and m["longest_streak"] >= 3:
        start, end = m["longest_range"]
        out.append((end, f"Longest streak: {m['longest_streak']} days"))
    return sorted(out)


def quests(config_quests: list[dict], m: dict) -> list[dict]:
    """Self-set goals from profile.config.json. Metric-bound quests track progress automatically."""
    out = []
    for q in config_quests:
        if "metric" in q:
            value = m.get(q["metric"])
            target = q["target"]
            out.append(
                {
                    "title": q["title"],
                    "value": value,
                    "target": target,
                    "done": value is not None and value >= target,
                    "auto": True,
                }
            )
        else:
            out.append({"title": q["title"], "value": None, "target": None, "done": bool(q.get("done")), "auto": False})
    return out


def progression(data: dict, config_quests: list[dict]) -> dict:
    m = metrics(data)
    rows = xp_breakdown(data, m)
    xp = sum(r[2] for r in rows)
    level = level_for(xp)
    lo, hi = level_threshold(level), level_threshold(level + 1)
    return {
        "metrics": m,
        "xp_rows": rows,
        "xp": xp,
        "level": level,
        "rank": rank_for(level),
        "level_floor": lo,
        "level_next": hi,
        "level_frac": (xp - lo) / (hi - lo),
        "achievements": achievements(m),
        "milestones": milestones(data, m),
        "quests": quests(config_quests, m),
    }

