# Progression rules

The level, XP, achievements and milestones on this profile are my own system. They are **not GitHub achievements** and are not affiliated with GitHub. Everything is computed by [`scripts/profile_cards/gamify.py`](../scripts/profile_cards/gamify.py) from GitHub API data on each workflow run. No number is entered by hand. A unit test checks that the tables below match the code.

## Data used

All counts are lifetime, from account creation (October 2024) to the run date, as reported by the GitHub GraphQL API (`contributionsCollection`, one request per year, plus the public repository list).

* Private-repository activity counts only if *Include private contributions on my profile* is turned on in GitHub settings. GitHub then reports it as anonymous daily counts. Private repository names never appear on any card.
* When a value is unavailable, it earns 0 XP and the card shows `n/a`. Missing values are never estimated.

## XP

| Rule | XP | Counts |
| :--- | ---: | :--- |
| `contribution` | 3 | per contribution on the contribution calendar, **max 12 per day** |
| `active_day` | 5 | per day with at least one contribution |
| `pull_request` | 20 | per pull request opened |
| `review` | 15 | per pull request review |
| `issue` | 8 | per issue opened |
| `public_repo` | 40 | per public, non-fork repository I own |
| `star` | 10 | per star on those repositories |
| `external_repo` | 30 | per public repository owned by someone else that I opened a pull request to |

The daily cap means a single bulk-commit day can't outweigh steady work. Pull requests, reviews and issues already count on the calendar, so they get a bonus on top because they take more effort than a commit.

## Levels

Reaching level *L* takes `50 × L × (L − 1)` total XP:

| Level | 1 | 2 | 3 | 4 | 5 | 6 | 8 | 10 | 15 |
| :--- | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| XP | 0 | 100 | 300 | 600 | 1,000 | 1,500 | 2,800 | 4,500 | 10,500 |

Ranks: Initiate (1–2), Builder (3–5), Shipper (6–9), Maintainer (10–14), Veteran (15+).

## Achievements

Each achievement has three tiers. A tier is earned when the metric reaches its threshold.

| Achievement | Metric | Bronze | Silver | Gold |
| :--- | :--- | ---: | ---: | ---: |
| Committed | commits | 50 | 250 | 1,000 |
| Consistent | longest daily streak | 7 | 30 | 100 |
| Regular | days with a contribution | 30 | 100 | 250 |
| Portfolio | public, non-fork repositories | 3 | 10 | 25 |
| Polyglot | languages with ≥ 2 % of public code by bytes | 3 | 5 | 8 |
| Collaborator | pull requests opened | 5 | 25 | 100 |
| Reviewer | pull request reviews | 5 | 25 | 100 |
| Contributor | external repositories with my pull requests | 1 | 3 | 10 |

## Milestones

These are dated directly from the data: the first public repository, the 1st, 100th, 250th, 500th, 1,000th (and so on) contribution, the busiest day, and the longest streak. The card shows the latest five.

## Quests

Quests are goals I set for myself in [`profile.config.json`](../profile.config.json). They are labelled *self-set* on the card, they never count as achievements, and they earn no XP. A quest with a `metric` tracks its progress automatically from the same data. A quest without one is ticked by hand with `"done": true`.
