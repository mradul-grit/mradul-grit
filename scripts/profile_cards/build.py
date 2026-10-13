"""Generate every profile card.

    python -m scripts.profile_cards.build --out dist                 # fetch with $GITHUB_TOKEN
    python -m scripts.profile_cards.build --out dist --data d.json   # render from saved data
    python -m scripts.profile_cards.build --static                    # rewrite assets/hero*.svg

Failure policy: if the API cannot be reached, the previous run's cards (passed
with --previous) are kept unchanged, so the profile shows the last good snapshot
with its original date. If there is no previous run, each card says
"Data unavailable" instead of showing invented numbers. A single card that
fails to render never blocks the others.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import traceback
from pathlib import Path

from . import cards, gamify, hero, leetcode, stack
from .github_api import FetchError, fetch_profile, token_from_env

ROOT = Path(__file__).resolve().parents[2]


def log(level: str, msg: str) -> None:
    # GitHub Actions annotations; harmless plain text elsewhere.
    print(f"::{level}::{msg}" if level in ("warning", "error", "notice") else msg, file=sys.stderr)


def write(out: Path, name: str, svg: str) -> None:
    (out / name).write_text(svg, encoding="utf-8")


def render_all(data: dict, config: dict, out: Path) -> list[str]:
    prog = gamify.progression(data, config.get("quests", []))
    jobs = {
        "overview.svg": lambda: cards.overview(data, prog),
        "languages.svg": lambda: cards.languages(data, prog, config.get("language_exclude")),
        "activity.svg": lambda: cards.activity(data, prog),
        "activity-compact.svg": lambda: cards.activity(data, prog, compact=True),
        "level.svg": lambda: cards.level(data, prog),
        "achievements.svg": lambda: cards.achievements(data, prog),
        "milestones.svg": lambda: cards.milestones(data, prog),
        "quests.svg": lambda: cards.quests(data, prog),
    }
    for f in config.get("featured", []):
        jobs[f"repo-{f['repo'].lower()}.svg"] = (
            lambda f=f: cards.repo(data, f["repo"], f.get("tagline"), f.get("stack", []))
        )
    failed = []
    for name, job in jobs.items():
        try:
            write(out, name, job())
        except Exception:  # one broken card must not take the rest down
            traceback.print_exc()
            failed.append(name)
            write(out, name, cards.unavailable(name, "Unavailable", "This card failed to render on the last run."))
    summary = {
        "generated_at": data["generated_at"],
        "level": prog["level"],
        "xp": prog["xp"],
        "xp_rows": prog["xp_rows"],
        "achievements": [{k: a[k] for k in ("key", "tier", "value")} for a in prog["achievements"]],
        "failed_cards": failed,
    }
    (out / "progression.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return failed


def fallback(out: Path, previous: Path | None, config: dict, reason: str) -> None:
    if previous and any(previous.glob("*.svg")):
        for f in previous.glob("*.svg"):
            if not f.name.startswith(("snake", "leetcode")):  # those have their own jobs
                shutil.copy2(f, out / f.name)
        log("warning", f"GitHub data unavailable ({reason}); kept the previous snapshot.")
        return
    log("warning", f"GitHub data unavailable ({reason}) and no previous snapshot; writing placeholders.")
    names = ["overview", "languages", "level", "achievements", "milestones", "quests"]
    for n in names:
        write(out, f"{n}.svg", cards.unavailable(n.title(), n.title(), "The scheduled refresh could not reach GitHub."))
    write(out, "activity.svg", cards.unavailable("Activity", "Activity", "The scheduled refresh could not reach GitHub.", cards.WIDE_W))
    write(out, "activity-compact.svg", cards.unavailable("Activity", "Activity", "The scheduled refresh could not reach GitHub."))
    for f in config.get("featured", []):
        write(out, f"repo-{f['repo'].lower()}.svg", cards.unavailable(f["repo"], "Repository", "Details unavailable right now.", cards.CARD_W, 140))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", type=Path, default=ROOT / "profile.config.json")
    p.add_argument("--out", type=Path, default=ROOT / "dist")
    p.add_argument("--previous", type=Path, help="directory holding the last published cards")
    p.add_argument("--data", type=Path, help="render from a saved data file instead of the API")
    p.add_argument("--dump-data", type=Path, help="also save the normalized data here")
    p.add_argument("--static", action="store_true", help="regenerate the static assets (hero, stack) and exit")
    p.add_argument("--leetcode", action="store_true", help="only build the LeetCode card")
    args = p.parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))

    if args.static:
        for layout, fname in (("wide", "hero.svg"), ("compact", "hero-compact.svg")):
            svg = hero.render(config["name"], config["login"], config["role"], config["typing"], layout)
            (ROOT / "assets" / fname).write_text(svg, encoding="utf-8")
            print(f"wrote assets/{fname}")
        for compact, fname in ((False, "stack.svg"), (True, "stack-compact.svg")):
            (ROOT / "assets" / fname).write_text(stack.render(config["stack"], compact), encoding="utf-8")
            print(f"wrote assets/{fname}")
        return 0

    args.out.mkdir(parents=True, exist_ok=True)

    if args.leetcode:
        return leetcode.build(config.get("leetcode", {}), args.out, args.previous)

    try:
        if args.data:
            data = json.loads(args.data.read_text(encoding="utf-8"))
        else:
            token = token_from_env()
            if not token:
                raise FetchError("GITHUB_TOKEN is not set")
            data = fetch_profile(config["login"], token)
    except (FetchError, OSError, ValueError) as err:
        fallback(args.out, args.previous, config, str(err))
        return 0

    if args.dump_data:
        args.dump_data.write_text(json.dumps(data, indent=1), encoding="utf-8")
    failed = render_all(data, config, args.out)
    if failed:
        log("warning", f"cards that fell back to placeholders: {', '.join(failed)}")
    print(f"wrote {len(list(args.out.glob('*.svg')))} cards to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
