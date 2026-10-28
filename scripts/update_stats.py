#!/usr/bin/env python3
"""Build the profile activity tiles from the GitHub GraphQL API.

Standard library only. Reads STATS_TOKEN (a read-only token) and writes one SVG
tile per metric to --out: tile-contributions.svg, tile-commits.svg,
tile-prs.svg and tile-repos.svg.

Scope of every number, last 12 months:
  commits, pull requests, active repos  repositories owned by LOGIN, public and private
  contributions                         GitHub's own count across all repositories,
                                        including private work the token cannot read

Anything that cannot be read is left out, never shown as 0. On any API error or
malformed data the script exits non-zero and writes nothing, so the previously
published tiles stay in place.
"""
import argparse
import datetime as dt
import html
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com/graphql"
LOGIN = os.environ.get("STATS_LOGIN", "azizz7")
WINDOW_DAYS = 365

REPOS_QUERY = """
query($login: String!, $id: ID!, $since: GitTimestamp!, $cursor: String) {
  user(login: $login) {
    repositories(first: 50, after: $cursor, ownerAffiliations: OWNER, isFork: false) {
      pageInfo { hasNextPage endCursor }
      nodes {
        pushedAt
        defaultBranchRef { target { ... on Commit {
          history(author: {id: $id}, since: $since) { totalCount }
        } } }
      }
    }
  }
}
"""

PRS_QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    pullRequests(first: 100, after: $cursor, orderBy: {field: CREATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes { createdAt merged repository { owner { login } } }
    }
  }
}
"""

USER_QUERY = """
query($login: String!) {
  user(login: $login) {
    id
    contributionsCollection {
      hasAnyRestrictedContributions
      restrictedContributionsCount
      contributionCalendar { totalContributions }
    }
  }
}
"""


class StatsError(Exception):
    pass


def graphql(token, query, variables, attempts=4):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-stats-updater",
        },
    )
    last = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.load(resp)
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            # 401/404 will not fix themselves; 403 may be a rate limit, 5xx is transient.
            if e.code in (401, 404):
                raise StatsError(f"{last}: token rejected or user not found") from e
            retry_after = e.headers.get("Retry-After")
            delay = int(retry_after) if retry_after and retry_after.isdigit() else 2 ** (attempt + 1)
        except (urllib.error.URLError, TimeoutError) as e:
            last = str(e)
            delay = 2 ** (attempt + 1)
        else:
            if payload.get("errors"):
                msgs = "; ".join(err.get("message", "?") for err in payload["errors"])
                if "rate limit" in msgs.lower() and attempt < attempts - 1:
                    last, delay = msgs, 2 ** (attempt + 2)
                else:
                    raise StatsError(f"GraphQL errors: {msgs}")
            else:
                data = payload.get("data")
                if not data or not data.get("user"):
                    raise StatsError("GraphQL returned no user data")
                return data["user"]
        if attempt < attempts - 1:
            print(f"retrying after {last} in {delay}s", file=sys.stderr)
            time.sleep(delay)
    raise StatsError(f"giving up after {attempts} attempts: {last}")


def paginate(token, query, variables, connection):
    cursor, nodes = None, []
    while True:
        user = graphql(token, query, {**variables, "cursor": cursor})
        conn = user[connection]
        nodes.extend(conn["nodes"])
        if not conn["pageInfo"]["hasNextPage"]:
            return nodes
        cursor = conn["pageInfo"]["endCursor"]


def collect(token, now):
    since = (now - dt.timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    user = graphql(token, USER_QUERY, {"login": LOGIN})
    calendar = user["contributionsCollection"]

    repos = paginate(token, REPOS_QUERY, {"login": LOGIN, "id": user["id"], "since": since}, "repositories")
    prs = paginate(token, PRS_QUERY, {"login": LOGIN}, "pullRequests")

    commits = active = 0
    for repo in repos:
        if repo["pushedAt"] and repo["pushedAt"] >= since:
            active += 1
        target = (repo["defaultBranchRef"] or {}).get("target") or {}
        commits += (target.get("history") or {}).get("totalCount", 0)

    own = [p for p in prs if p["repository"]["owner"]["login"].lower() == LOGIN.lower() and p["createdAt"] >= since]
    shared = calendar["hasAnyRestrictedContributions"]
    return {
        "commits": commits,
        "prs_opened": len(own),
        "prs_merged": sum(1 for p in own if p["merged"]),
        "active_repos": active,
        # GitHub's own totals only mean something when private contributions are
        # shared on the profile; otherwise they silently omit private work, so
        # they are hidden rather than shown as a misleadingly small number.
        "contributions": calendar["contributionCalendar"]["totalContributions"] if shared else None,
        "private_contributions": calendar["restrictedContributionsCount"] if shared else None,
    }


def validate(stats):
    for key in ("commits", "prs_opened", "prs_merged", "active_repos"):
        if not isinstance(stats[key], int) or stats[key] < 0:
            raise StatsError(f"bad value for {key}: {stats[key]!r}")
    if stats["prs_merged"] > stats["prs_opened"]:
        raise StatsError("merged PRs exceed opened PRs")


FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
WIDTH, HEIGHT = 156, 108


def tile(label, value, sub):
    text = f"{label}: {value}, {sub}"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{html.escape(text, quote=True)}">
  <title>{html.escape(text)}</title>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#10162a"/><stop offset="1" stop-color="#0a0e19"/></linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#f59e0b"/><stop offset="1" stop-color="#60a5fa"/></linearGradient>
    <clipPath id="r"><rect width="{WIDTH}" height="{HEIGHT}" rx="12"/></clipPath>
  </defs>
  <g clip-path="url(#r)">
    <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#bg)"/>
    <rect x="18" width="28" height="3" fill="url(#accent)"/>
  </g>
  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="11.5" fill="none" stroke="#252d45"/>
  <g font-family="{FONT}">
    <text x="18" y="56" font-size="34" font-weight="700" fill="#f5f7fb">{html.escape(value)}</text>
    <text x="18" y="76" font-size="10.5" font-weight="600" letter-spacing="1.3" fill="#7aa7ff">{html.escape(label)}</text>
    <text x="18" y="93" font-size="10.5" fill="#7f8aa3">{html.escape(sub)}</text>
  </g>
</svg>
"""


def tiles(stats):
    out = {}
    if stats["contributions"] is not None:
        out["tile-contributions.svg"] = tile("CONTRIBUTIONS", f"{stats['contributions']:,}", f"incl. {stats['private_contributions']:,} private")
    out["tile-commits.svg"] = tile("COMMITS", f"{stats['commits']:,}", "my repos · 12 months")
    out["tile-prs.svg"] = tile("PULL REQUESTS", f"{stats['prs_opened']:,}", f"{stats['prs_merged']:,} merged · my repos")
    out["tile-repos.svg"] = tile("ACTIVE REPOS", f"{stats['active_repos']:,}", "pushed in 12 months")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="dist")
    args = parser.parse_args()

    token = os.environ.get("STATS_TOKEN")
    if not token:
        sys.exit("STATS_TOKEN is not set")

    try:
        stats = collect(token, dt.datetime.now(dt.timezone.utc))
        validate(stats)
    except (StatsError, KeyError, TypeError) as e:
        sys.exit(f"stats update failed, keeping previous tiles: {e}")

    os.makedirs(args.out, exist_ok=True)
    for name, svg in tiles(stats).items():
        with open(os.path.join(args.out, name), "w", encoding="utf-8") as f:
            f.write(svg)
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
