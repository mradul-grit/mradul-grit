"""Tests for the card generator. Run: python -m unittest discover -s tests -t . -v

The data below is synthetic test input, built only to exercise the code paths.
It is never published.
"""

from __future__ import annotations

import json
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from scripts.profile_cards import build, cards, gamify, github_api, hero, leetcode, stack

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "profile.config.json").read_text(encoding="utf-8"))


def sample_data(active: dict[str, int] | None = None) -> dict:
    end = date(2026, 10, 12)
    active = active or {"2026-10-10": 3, "2026-10-11": 15, "2026-10-12": 2, "2026-06-01": 1}
    calendar = [
        {"date": (end - timedelta(days=i)).isoformat(), "count": active.get((end - timedelta(days=i)).isoformat(), 0)}
        for i in range(400)
    ][::-1]
    repos = [
        {"name": n, "description": "d", "url": f"https://github.com/x/{n}", "stars": s, "forks": 0,
         "pushed_at": "2026-10-12T00:00:00Z", "created_at": c, "archived": False,
         "language": "Python", "language_color": "#3572A5", "languages": {"Python": 10}}
        for n, s, c in [("NetSentinel-AI", 2, "2026-06-14T00:00:00Z"), ("SIH-2026", 0, "2026-09-06T00:00:00Z"),
                        ("structor_ai", 0, "2026-10-01T00:00:00Z"), ("snakegame", 0, "2026-10-12T00:00:00Z")]
    ]
    return {
        "login": "mradul-grit", "name": "Test", "created_at": "2024-10-15T17:43:22Z",
        "generated_at": "2026-10-12 04:17 UTC", "repos": repos, "calendar": calendar,
        "totals": {"commits": 21, "pull_requests": 3, "reviews": 1, "issues": 2, "external_repos": 1},
        "recent": [{"name": "structor_ai", "url": "u", "commits": 9, "language": "TypeScript", "language_color": "#3178c6"}],
        "language_share": {"Python": 0.6, "TypeScript": 0.35, "Java": 0.05},
        "language_colors": {"Python": "#3572A5", "TypeScript": "#3178c6", "Java": "#b07219"},
    }


def assert_svg(test: unittest.TestCase, svg: str) -> ET.Element:
    root = ET.fromstring(svg)  # raises on malformed XML
    test.assertTrue(root.tag.endswith("svg"))
    test.assertIn("<title", svg)
    test.assertIn("<desc", svg)
    test.assertNotIn("None", re.sub(r"<desc.*?</desc>", "", svg, flags=re.S))
    return root


class GamifyTests(unittest.TestCase):
    def test_level_thresholds(self):
        self.assertEqual([gamify.level_threshold(l) for l in range(1, 6)], [0, 100, 300, 600, 1000])
        for xp, lvl in [(0, 1), (99, 1), (100, 2), (299, 2), (300, 3), (999, 4), (1000, 5), (10**6, 141)]:
            self.assertEqual(gamify.level_for(xp), lvl, xp)

    def test_daily_cap_and_breakdown(self):
        data = sample_data()
        prog = gamify.progression(data, [])
        rows = dict((k, (n, xp)) for k, n, xp in prog["xp_rows"])
        self.assertEqual(rows["contribution"][0], 3 + 12 + 2 + 1)  # the 15-contribution day is capped at 12
        self.assertEqual(rows["active_day"][0], 4)
        self.assertEqual(rows["star"][0], 2)
        self.assertEqual(prog["xp"], sum(xp for _, _, xp in prog["xp_rows"]))

    def test_streaks(self):
        m = gamify.metrics(sample_data())
        self.assertEqual(m["current_streak"], 3)
        self.assertEqual(m["longest_streak"], 3)
        # An empty today does not break the current streak.
        m = gamify.metrics(sample_data({"2026-10-10": 1, "2026-10-11": 1}))
        self.assertEqual(m["current_streak"], 2)

    def test_unknown_metrics_earn_nothing(self):
        data = sample_data()
        data["totals"] = {"commits": None, "pull_requests": None, "reviews": None, "issues": None, "external_repos": None}
        prog = gamify.progression(data, [{"title": "q", "metric": "pull_requests", "target": 5}])
        collab = next(a for a in prog["achievements"] if a["key"] == "prs")
        self.assertIsNone(collab["tier"])
        self.assertFalse(prog["quests"][0]["done"])

    def test_tiers(self):
        m = {"commits": 300, "longest_streak": 0}
        got = {a["key"]: a["tier"] for a in gamify.achievements(m)}
        self.assertEqual(got["commits"], "silver")
        self.assertIsNone(got["streak"])

    def test_docs_match_rules(self):
        doc = (ROOT / "docs" / "XP_RULES.md").read_text(encoding="utf-8")
        for rule, xp in gamify.XP_RULES.items():
            self.assertRegex(doc, rf"`{rule}`\s*\|\s*{xp}\s*\|", rule)
        for _, title, _, (b, s, g), _ in gamify.ACHIEVEMENTS:
            self.assertRegex(doc, rf"{title}\s*\|.*\|\s*{b:,}\s*\|\s*{s:,}\s*\|\s*{g:,}\s*\|", title)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(f"max {gamify.DAILY_CAP} per day", readme)


class CardTests(unittest.TestCase):
    def test_all_cards_render_valid_svg(self):
        with tempfile.TemporaryDirectory() as tmp:
            failed = build.render_all(sample_data(), CONFIG, Path(tmp))
            self.assertEqual(failed, [])
            names = {p.name for p in Path(tmp).glob("*.svg")}
            for f in CONFIG["featured"]:
                self.assertIn(f"repo-{f['repo'].lower()}.svg", names)
            for p in Path(tmp).glob("*.svg"):
                assert_svg(self, p.read_text(encoding="utf-8"))

    def test_static_assets(self):
        for layout in ("wide", "compact"):
            assert_svg(self, hero.render(CONFIG["name"], CONFIG["login"], CONFIG["role"], CONFIG["typing"], layout))
        for compact in (False, True):
            assert_svg(self, stack.render(CONFIG["stack"], compact))

    def test_committed_assets_are_current(self):
        for layout, fname in (("wide", "hero.svg"), ("compact", "hero-compact.svg")):
            expected = hero.render(CONFIG["name"], CONFIG["login"], CONFIG["role"], CONFIG["typing"], layout)
            self.assertEqual((ROOT / "assets" / fname).read_text(encoding="utf-8"), expected, f"run build --static ({fname})")

    def test_empty_data(self):
        data = sample_data({})
        data["recent"], data["language_share"] = [], {}
        prog = gamify.progression(data, [])
        for fn in (cards.overview, cards.languages, cards.activity, cards.level, cards.achievements, cards.milestones, cards.quests):
            assert_svg(self, fn(data, prog))

    def test_missing_repo_card(self):
        svg = cards.repo(sample_data(), "does-not-exist", None, [])
        self.assertIn("Data unavailable", svg)

    def test_escaping(self):
        data = sample_data()
        data["repos"][0]["description"] = '<script>alert("x")</script> & co'
        svg = cards.repo(data, "NetSentinel-AI", None, ["<b>"])
        assert_svg(self, svg)
        self.assertNotIn("<script>", svg)


class FallbackTests(unittest.TestCase):
    def test_keeps_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as prev, tempfile.TemporaryDirectory() as out:
            Path(prev, "overview.svg").write_text("<svg>old</svg>")
            Path(prev, "snake.svg").write_text("<svg>snake</svg>")
            build.fallback(Path(out), Path(prev), CONFIG, "test")
            self.assertEqual(Path(out, "overview.svg").read_text(), "<svg>old</svg>")
            self.assertFalse(Path(out, "snake.svg").exists())  # the snake job owns that file

    def test_placeholders_without_previous(self):
        with tempfile.TemporaryDirectory() as out:
            build.fallback(Path(out), None, CONFIG, "test")
            for p in Path(out).glob("*.svg"):
                self.assertIn("Data unavailable", p.read_text())
            self.assertTrue(Path(out, "activity-compact.svg").exists())

    def test_main_without_token_never_fails(self):
        with tempfile.TemporaryDirectory() as out:
            import os
            saved = os.environ.pop("GITHUB_TOKEN", None)
            try:
                self.assertEqual(build.main(["--out", out]), 0)
            finally:
                if saved:
                    os.environ["GITHUB_TOKEN"] = saved
            self.assertTrue(Path(out, "overview.svg").exists())


class NormalizeTests(unittest.TestCase):
    def test_private_repos_never_leak(self):
        base = {"login": "mradul-grit", "name": None, "createdAt": "2025-01-01T00:00:00Z", "repositories": {"nodes": []}}
        day = {"date": "2025-06-01", "contributionCount": 4}
        years = {
            "y0": {
                "totalCommitContributions": 4, "totalIssueContributions": 0, "totalPullRequestContributions": 2,
                "totalPullRequestReviewContributions": 0, "restrictedContributionsCount": 7,
                "contributionCalendar": {"weeks": [{"contributionDays": [day]}]},
                "pullRequestContributionsByRepository": [
                    {"repository": {"nameWithOwner": "other/public", "isPrivate": False, "owner": {"login": "other"}}, "contributions": {"totalCount": 1}},
                    {"repository": {"nameWithOwner": "other/secret", "isPrivate": True, "owner": {"login": "other"}}, "contributions": {"totalCount": 1}},
                    {"repository": {"nameWithOwner": "mradul-grit/own", "isPrivate": False, "owner": {"login": "mradul-grit"}}, "contributions": {"totalCount": 1}},
                ],
            },
            "recent": {"commitContributionsByRepository": [
                {"repository": {"name": "secret-app", "nameWithOwner": "mradul-grit/secret-app", "url": "u", "isPrivate": True,
                                "owner": {"login": "mradul-grit"}, "primaryLanguage": None}, "contributions": {"totalCount": 5}},
                {"repository": {"name": "pub", "nameWithOwner": "mradul-grit/pub", "url": "u", "isPrivate": False,
                                "owner": {"login": "mradul-grit"}, "primaryLanguage": None}, "contributions": {"totalCount": 2}},
            ]},
        }
        data = github_api.normalize(base, years, "mradul-grit", datetime(2025, 7, 1, tzinfo=timezone.utc))
        dumped = json.dumps(data)
        self.assertNotIn("secret", dumped)
        self.assertEqual(data["totals"]["external_repos"], 1)
        self.assertEqual([r["name"] for r in data["recent"]], ["pub"])
        self.assertEqual(data["name"], "mradul-grit")


class FetchTests(unittest.TestCase):
    def test_one_collection_per_year(self):
        calls = []

        def fake_post(query, variables, token, attempts=3):
            calls.append(query)
            if len(calls) == 1:
                return {"user": {"login": "mradul-grit", "name": "M", "createdAt": "2024-10-15T17:43:22Z", "repositories": {"nodes": []}}}
            empty = {"totalCommitContributions": 0, "totalIssueContributions": 0, "totalPullRequestContributions": 0,
                     "totalPullRequestReviewContributions": 0, "restrictedContributionsCount": 0,
                     "contributionCalendar": {"weeks": []}, "pullRequestContributionsByRepository": []}
            return {"user": {"y0": empty, "y1": empty, "recent": {"commitContributionsByRepository": []}}}

        original = github_api._post
        github_api._post = fake_post
        try:
            data = github_api.fetch_profile("mradul-grit", "t", now=datetime(2026, 10, 12, tzinfo=timezone.utc))
        finally:
            github_api._post = original
        self.assertIn("y1: contributionsCollection", calls[1])
        self.assertNotIn("y2:", calls[1])
        self.assertEqual(data["generated_at"], "2026-10-12 00:00 UTC")


class LeetCodeTests(unittest.TestCase):
    PAYLOAD = {"data": {
        "allQuestionsCount": [{"difficulty": d, "count": c} for d, c in [("All", 3000), ("Easy", 800), ("Medium", 1600), ("Hard", 600)]],
        "matchedUser": {"username": "someone", "profile": {"ranking": 123456},
                        "submitStatsGlobal": {"acSubmissionNum": [{"difficulty": d, "count": c} for d, c in [("All", 60), ("Easy", 40), ("Medium", 18), ("Hard", 2)]]}},
    }}

    def test_parse_and_render(self):
        stats = leetcode.parse(self.PAYLOAD)
        self.assertEqual(stats["solved"]["All"], 60)
        assert_svg(self, leetcode.render(stats))

    def test_unknown_user(self):
        with self.assertRaises(ValueError):
            leetcode.parse({"data": {"matchedUser": None}})

    def test_skipped_without_username(self):
        with tempfile.TemporaryDirectory() as out:
            self.assertEqual(leetcode.build({"username": ""}, Path(out), None), 0)
            self.assertEqual(list(Path(out).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
