# Setup and maintenance

## One-time setup

1. **Create the profile repository.** On GitHub, create a **public** repository named exactly `mradul-grit` under the `mradul-grit` account. GitHub shows its README on the profile page.
2. **Push these files** to its `main` branch. The workflow asks for exactly the permissions it needs, so the repository's default Actions permissions can stay read-only.
3. **Run the workflow once.** Go to *Actions → Profile cards → Run workflow*. The first run creates the `output` branch that the README images point to. Until it finishes, those images appear broken. The stack card lives on `main`, so it shows right away. The hero banner is built by the workflow too, so it also waits for the first run.
4. Optional: **Turn on private contribution counts.** Go to *GitHub profile → Contribution settings → Include private contributions on my profile*. The calendar, streaks and XP then include private work as anonymous counts. Private repository names are never shown.

### Optional secrets

| Secret | Needed? | What it does |
| :--- | :--- | :--- |
| `PROFILE_STATS_TOKEN` | No | A fine-grained or classic personal access token with **read-only** `read:user` access. Use it only if the built-in token is ever refused for user queries. Without it, the built-in `GITHUB_TOKEN` is used. |

The workflow needs no other credentials. Tokens are passed only through environment variables and are never written to cards, data files or logs (GitHub masks secrets in logs, and the publish step also masks the auth header it builds).

### LeetCode (optional)

Set `"leetcode": { "username": "<your handle>" }` in `profile.config.json`, push, and uncomment the LeetCode block in `README.md`.

## Editing the profile

| To change | Edit | Then |
| :--- | :--- | :--- |
| Name, role, typing lines | `profile.config.json` | push; the workflow rebuilds the hero |
| Stack | `profile.config.json` | `python -m scripts.profile_cards.build --static` and commit `assets/stack*.svg` |
| Featured repositories | `featured` in `profile.config.json` and the matching `<a><img>` lines in `README.md` | push; the workflow rebuilds the cards |
| Quests (self-set goals) | `quests` in `profile.config.json` | push |
| XP rules | `scripts/profile_cards/gamify.py` **and** `docs/XP_RULES.md` | `python -m unittest discover -s tests -t .` (fails if the two disagree) |

To preview locally: `GITHUB_TOKEN=<token> python -m scripts.profile_cards.build --out dist --dump-data dist/data.json`, then open the SVGs in `dist/`. Python 3.10+ only, with no dependencies.

## What updates when

Nothing on this profile updates second by second. GitHub serves README images as static files, and a README cannot run JavaScript.

| Element | Data source | Updates | If the source fails | Rate limits |
| :--- | :--- | :--- | :--- | :--- |
| Hero text | `profile.config.json` | Daily, with the cards. The typing animation is CSS that plays in the browser; it is not data. | Can't fail: it needs no external data | none |
| 3D contribution skyline in the hero (rendered with Blender) | The same GitHub contribution data, last 26 weeks | **Weekly** (Mondays 04:17 UTC), plus on manual and push runs, or whenever none exists yet. Rendering takes several minutes and downloads about 400 MB, so it isn't repeated daily. | The previous render is reused; if there never was one, the hero shows without the image | none (uses data from the cards job) |
| Stack card | `profile.config.json` | Only when you rebuild it with `--static` and commit | Can't fail: committed to `main` | none |
| Featured repository cards | GitHub GraphQL API (description, language, stars, last push) | **Daily** at 04:17 UTC, on manual runs, and on pushes that change the config or scripts | The last good card is kept with its original date; a missing or private repository shows "Data unavailable" | GraphQL: 1,000 points/hour for `GITHUB_TOKEN`. A run uses 2 queries. |
| Overview, languages, contribution heatmap, last 30 days | GitHub GraphQL API (`contributionsCollection`) | Daily, same schedule | The previous snapshot is kept; on the first run, "Data unavailable" | same as above |
| Level, XP, achievements, milestones, quests | Computed from the same API data by `gamify.py` | Daily, same schedule | Same as above; unknown values earn 0 XP and show `n/a` | none (no extra calls) |
| Contribution snake | [Platane/snk](https://github.com/Platane/snk) v3.5.0 (reads the contribution calendar with `GITHUB_TOKEN`) | Daily, same schedule | The previous snake is carried over; the other cards still publish | 1 GraphQL query per run |
| LeetCode card (off by default) | LeetCode's public GraphQL endpoint. It is **unofficial**: LeetCode has no public API. | Daily, once enabled | The previous card is kept, or "Data unavailable"; the workflow never fails because of it | 1 request per day |
| Snapshot dates on cards | Workflow run time | Every run | n/a | n/a |

**Caching and freshness.** Images on `raw.githubusercontent.com` are cached for about 5 minutes, and GitHub's image proxy may cache them for longer. So a card can lag a run by a few minutes. Every data card prints its snapshot time, so a stale card is easy to spot.

## How the workflow is put together

`.github/workflows/profile.yml` has four jobs:

| Job | Permissions | What it does |
| :--- | :--- | :--- |
| `cards` | `contents: read` | Runs the unit tests, builds the GitHub cards and the optional LeetCode card. The last published snapshot is used as a fallback. |
| `skyline` | `contents: read` | Renders the 3D skyline with Blender's Python module (`bpy`, pinned in `scripts/render3d/requirements.txt`) and builds the hero. A failed render never blocks the other cards. |
| `snake` | `contents: read` | Generates `snake.svg` and `snake-dark.svg` and checks they are valid SVG files |
| `publish` | `contents: write` | Combines the outputs, carries over the previous snake, skyline and hero if this run couldn't rebuild them, and force-pushes one commit to the `output` branch |

Notes:

* `output` always holds exactly one commit, so generated files never build up history, and `main` only changes when you edit it.
* Bot commits are made by `github-actions[bot]`. They don't appear on your contribution graph and don't inflate any statistic.
* Every third-party action is pinned to a full commit SHA, with its version in a comment. To update one, change both.
* Workflow runs never overlap (`concurrency: profile-cards`).
* **GitHub disables scheduled workflows** in a public repository after 60 days with no repository activity. If the cards stop updating, re-enable the workflow under *Actions*, or push any change to `main`.

## Why there is no GitHub Pages dashboard

Everything here works as static images, so a separate site isn't needed. If you later want data that loads when a visitor opens the page (for example, a real-time view or interactive charts), that would need a GitHub Pages site. The README can only link to it, because a README cannot run scripts.

## Design notes

* **Type.** Chakra Petch (headings and figures), IBM Plex Sans (text) and IBM Plex Mono (the hero's terminal lines), all under the SIL Open Font License. The fonts are subset to Latin and embedded in each SVG, because an image loaded through a README cannot fetch web fonts. They live in `assets/fonts/` with their license texts.
* **Color.** Dark neutral panels with one cyan accent and one violet accent. Small text keeps at least 4.5:1 contrast on the panels.
* **Skyline.** `scripts/render3d/skyline.py` builds one tower per day from the contribution calendar, with height on a square-root scale, and renders it with Cycles on the CPU. To preview locally: `pip install bpy==5.2.3`, then `python scripts/render3d/skyline.py --data data.json --out skyline.webp`.
