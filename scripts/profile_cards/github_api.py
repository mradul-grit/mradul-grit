"""Fetch profile data from the GitHub GraphQL API and normalize it.

Standard library only. Authenticates with the token in $GITHUB_TOKEN (the
workflow passes the built-in Actions token, or the optional PROFILE_STATS_TOKEN
secret). The token is only ever sent in the Authorization header and is never
written to output or logs.

Privacy: private repositories are dropped here, whatever the token can see, so
no private repository name can reach a generated card.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone

API = "https://api.github.com/graphql"

PROFILE_QUERY = """
query($login: String!) {
  user(login: $login) {
    login
    name
    createdAt
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes {
        name description url stargazerCount forkCount pushedAt createdAt isArchived
        primaryLanguage { name color }
        languages(first: 12, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

YEAR_FRAGMENT = """
  y{idx}: contributionsCollection(from: "{start}", to: "{end}") {{
    totalCommitContributions
    totalIssueContributions
    totalPullRequestContributions
    totalPullRequestReviewContributions
    restrictedContributionsCount
    contributionCalendar {{ weeks {{ contributionDays {{ date contributionCount }} }} }}
    pullRequestContributionsByRepository(maxRepositories: 100) {{
      repository {{ nameWithOwner isPrivate owner {{ login }} }}
      contributions {{ totalCount }}
    }}
  }}
"""

RECENT_FRAGMENT = """
  recent: contributionsCollection(from: "{start}", to: "{end}") {{
    commitContributionsByRepository(maxRepositories: 10) {{
      repository {{ name nameWithOwner url isPrivate owner {{ login }} primaryLanguage {{ name color }} }}
      contributions {{ totalCount }}
    }}
  }}
"""


class FetchError(RuntimeError):
    pass


def _post(query: str, variables: dict, token: str, attempts: int = 3) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode()
    last = None
    for attempt in range(attempts):
        req = urllib.request.Request(
            API,
            data=body,
            headers={
                "Authorization": f"bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "profile-cards",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.load(resp)
        except urllib.error.HTTPError as err:
            last = f"HTTP {err.code}"
            # 502/503 and secondary rate limits are worth a retry; auth errors are not.
            if err.code in (401, 403) and "rate limit" not in err.read().decode(errors="ignore").lower():
                raise FetchError(f"GitHub API refused the request ({last}); check the token") from None
        except (urllib.error.URLError, TimeoutError) as err:
            last = type(err).__name__
        else:
            if payload.get("errors"):
                messages = "; ".join(e.get("message", "?") for e in payload["errors"])
                raise FetchError(f"GraphQL error: {messages}")
            return payload["data"]
        time.sleep(2 ** (attempt + 1))
    raise FetchError(f"GitHub API unreachable after {attempts} attempts ({last})")


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_profile(login: str, token: str, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    base = _post(PROFILE_QUERY, {"login": login}, token)["user"]
    if base is None:
        raise FetchError(f"user {login!r} not found")

    # contributionsCollection spans at most one year, so ask for each year since signup.
    created = datetime.fromisoformat(base["createdAt"].replace("Z", "+00:00"))
    fragments, start, idx = [], created, 0
    while start < now:
        end = min(start + timedelta(days=365) - timedelta(seconds=1), now)
        fragments.append(YEAR_FRAGMENT.format(idx=idx, start=_iso(start), end=_iso(end)))
        start, idx = end + timedelta(seconds=1), idx + 1
    fragments.append(RECENT_FRAGMENT.format(start=_iso(now - timedelta(days=30)), end=_iso(now)))
    query = "query($login: String!) { user(login: $login) {" + "".join(fragments) + "} }"
    years = _post(query, {"login": login}, token)["user"]
    return normalize(base, years, login, now)


def normalize(base: dict, years: dict, login: str, now: datetime) -> dict:
    repos = []
    lang_bytes: dict[str, int] = defaultdict(int)
    lang_color: dict[str, str] = {}
    for r in base["repositories"]["nodes"]:
        langs = {}
        for edge in r["languages"]["edges"]:
            name = edge["node"]["name"]
            langs[name] = edge["size"]
            lang_bytes[name] += edge["size"]
            lang_color[name] = edge["node"]["color"] or "#8B98A9"
        repos.append(
            {
                "name": r["name"],
                "description": r["description"] or "",
                "url": r["url"],
                "stars": r["stargazerCount"],
                "forks": r["forkCount"],
                "pushed_at": r["pushedAt"],
                "created_at": r["createdAt"],
                "archived": r["isArchived"],
                "language": (r["primaryLanguage"] or {}).get("name"),
                "language_color": (r["primaryLanguage"] or {}).get("color"),
                "languages": langs,
            }
        )

    calendar: dict[str, int] = {}
    totals = defaultdict(int)
    external: set[str] = set()
    for key, coll in years.items():
        if not key.startswith("y"):
            continue
        totals["commits"] += coll["totalCommitContributions"]
        totals["issues"] += coll["totalIssueContributions"]
        totals["pull_requests"] += coll["totalPullRequestContributions"]
        totals["reviews"] += coll["totalPullRequestReviewContributions"]
        totals["private_contributions"] += coll["restrictedContributionsCount"]
        for week in coll["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                calendar[day["date"]] = max(calendar.get(day["date"], 0), day["contributionCount"])
        for item in coll["pullRequestContributionsByRepository"]:
            repo = item["repository"]
            if not repo["isPrivate"] and repo["owner"]["login"].lower() != login.lower():
                external.add(repo["nameWithOwner"])
    totals["external_repos"] = len(external)

    recent = []
    for item in years.get("recent", {}).get("commitContributionsByRepository", []):
        repo = item["repository"]
        if repo["isPrivate"]:
            continue
        recent.append(
            {
                # Short name only: the card column is narrow, and owner/name gets truncated mid-word.
                "name": repo["name"],
                "url": repo["url"],
                "commits": item["contributions"]["totalCount"],
                "language": (repo["primaryLanguage"] or {}).get("name"),
                "language_color": (repo["primaryLanguage"] or {}).get("color"),
            }
        )

    total_bytes = sum(lang_bytes.values()) or 1
    return {
        "source": "github-graphql",
        "login": base["login"],
        "name": base["name"] or base["login"],
        "created_at": base["createdAt"],
        "generated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
        "repos": repos,
        "calendar": [{"date": d, "count": c} for d, c in sorted(calendar.items())],
        "totals": dict(totals),
        "recent": recent,
        "language_share": {k: v / total_bytes for k, v in sorted(lang_bytes.items(), key=lambda kv: -kv[1])},
        "language_colors": lang_color,
    }


def token_from_env() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or None
