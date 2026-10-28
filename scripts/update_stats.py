#!/usr/bin/env python3
"""Build the profile activity and language cards from the GitHub GraphQL API.

Standard library only. Reads STATS_TOKEN (a read-only token) and writes four
SVGs to --out: activity-{dark,light}.svg and languages-{dark,light}.svg.

Scope of every number: repositories owned by LOGIN, public and private, in the
last 12 months. Anything that cannot be read is left out, never shown as 0.
On any API error or malformed data the script exits non-zero and writes
nothing, so the previously published images stay in place.
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
# Markup and notebooks are not "code written", and one large generated file
# would otherwise dominate the language share.
EXCLUDED_LANGUAGES = {"HTML", "CSS", "SCSS", "Jupyter Notebook", "Makefile"}
MAX_LANGUAGES = 5
MIN_LANGUAGE_SHARE = 1.0  # percent; hides noise such as a 0.0% Dockerfile

REPOS_QUERY = """
query($login: String!, $id: ID!, $since: GitTimestamp!, $cursor: String) {
  user(login: $login) {
    repositories(first: 50, after: $cursor, ownerAffiliations: OWNER, isFork: false) {
      pageInfo { hasNextPage endCursor }
      nodes {
        pushedAt
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
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

THEMES = {
    "dark": dict(bg="#0d1117", border="#30363d", text="#e6edf3", muted="#8b949e", accent="#58a6ff", track="#21262d"),
    "light": dict(bg="#ffffff", border="#d0d7de", text="#1f2328", muted="#656d76", accent="#0969da", track="#eaeef2"),
}


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
    user_id = user["id"]
    calendar = user["contributionsCollection"]

    repos = paginate(token, REPOS_QUERY, {"login": LOGIN, "id": user_id, "since": since}, "repositories")
    prs = paginate(token, PRS_QUERY, {"login": LOGIN}, "pullRequests")

    commits = 0
    active = 0
    languages = {}
    for repo in repos:
        if repo["pushedAt"] and repo["pushedAt"] >= since:
            active += 1
            for edge in repo["languages"]["edges"]:
                name = edge["node"]["name"]
                if name in EXCLUDED_LANGUAGES:
                    continue
                size, color = languages.get(name, (0, edge["node"]["color"]))
                languages[name] = (size + edge["size"], color)
        target = (repo["defaultBranchRef"] or {}).get("target") or {}
        commits += (target.get("history") or {}).get("totalCount", 0)

    own = [p for p in prs if p["repository"]["owner"]["login"].lower() == LOGIN.lower() and p["createdAt"] >= since]
    stats = {
        "commits": commits,
        "prs_opened": len(own),
        "prs_merged": sum(1 for p in own if p["merged"]),
        "active_repos": active,
        # GitHub's own totals across every repository, including private ones
        # the token cannot read (for example an employer's). They only mean
        # something when private contributions are shared on the profile;
        # otherwise GitHub silently omits private work, so they are hidden.
        "contributions": (
            calendar["contributionCalendar"]["totalContributions"]
            if calendar["hasAnyRestrictedContributions"]
            else None
        ),
        "private_contributions": (
            calendar["restrictedContributionsCount"]
            if calendar["hasAnyRestrictedContributions"]
            else None
        ),
    }
    total = sum(size for size, _ in languages.values())
    ranked = sorted(languages.items(), key=lambda kv: -kv[1][0])
    langs = [
        (n, 100 * s / total, c or "#8b949e")
        for n, (s, c) in ranked[:MAX_LANGUAGES]
        if total and 100 * s / total >= MIN_LANGUAGE_SHARE
    ]
    return stats, langs


def validate(stats, langs):
    for key in ("commits", "prs_opened", "prs_merged", "active_repos"):
        if not isinstance(stats[key], int) or stats[key] < 0:
            raise StatsError(f"bad value for {key}: {stats[key]!r}")
    if stats["prs_merged"] > stats["prs_opened"]:
        raise StatsError("merged PRs exceed opened PRs")
    if not langs:
        raise StatsError("no language data")


def esc(text):
    return html.escape(str(text), quote=True)


FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
WIDTH, HEIGHT = 400, 270


def frame(theme, title, subtitle, body, updated):
    c = THEMES[theme]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{esc(title)}: {esc(subtitle)}">
  <title>{esc(title)}</title>
  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="10" fill="{c['bg']}" stroke="{c['border']}"/>
  <g font-family="{FONT}">
    <text x="24" y="38" font-size="18" font-weight="600" fill="{c['accent']}">{esc(title)}</text>
    <text x="24" y="58" font-size="12" fill="{c['muted']}">{esc(subtitle)}</text>
{body}
    <text x="24" y="{HEIGHT - 16}" font-size="11" fill="{c['muted']}">Updated {esc(updated)}</text>
  </g>
</svg>
"""


def activity_svg(theme, stats, updated):
    c = THEMES[theme]
    own = [
        ("Commits", f"{stats['commits']:,}"),
        ("Pull requests", f"{stats['prs_opened']:,} opened · {stats['prs_merged']:,} merged"),
        ("Active repositories", f"{stats['active_repos']:,}"),
    ]
    everywhere = []
    if stats["contributions"] is not None:
        everywhere = [
            ("Contributions", f"{stats['contributions']:,}"),
            ("of which private", f"{stats['private_contributions']:,}"),
        ]
    out = []

    def row(label, value, y):
        out.append(f'    <text x="24" y="{y}" font-size="14" fill="{c["muted"]}">{esc(label)}</text>')
        out.append(f'    <text x="{WIDTH - 24}" y="{y}" font-size="14" font-weight="600" text-anchor="end" fill="{c["text"]}">{esc(value)}</text>')

    for i, (label, value) in enumerate(own):
        row(label, value, 90 + i * 26)
    if everywhere:
        out.append(f'    <line x1="24" y1="158" x2="{WIDTH - 24}" y2="158" stroke="{c["border"]}"/>')
        out.append(f'    <text x="24" y="176" font-size="11" fill="{c["muted"]}">All repositories, GitHub\'s own count</text>')
        for i, (label, value) in enumerate(everywhere):
            row(label, value, 200 + i * 26)
    return frame(theme, "Activity", "Last 12 months · repositories I own", "\n".join(out), updated)


def languages_svg(theme, langs, updated):
    c = THEMES[theme]
    bar_x, bar_w, bar_y = 24, WIDTH - 48, 78
    parts = [f'    <clipPath id="bar"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="8" rx="4"/></clipPath>',
             f'    <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="8" rx="4" fill="{c["track"]}"/>',
             '    <g clip-path="url(#bar)">']
    x = float(bar_x)
    total = sum(p for _, p, _ in langs)
    for name, pct, color in langs:
        w = bar_w * pct / total
        parts.append(f'      <rect x="{x:.2f}" y="{bar_y}" width="{w:.2f}" height="8" fill="{esc(color)}"/>')
        x += w
    parts.append("    </g>")
    for i, (name, pct, color) in enumerate(langs):
        col, row = i % 2, i // 2
        lx, ly = 24 + col * 180, 114 + row * 26
        parts.append(f'    <circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{esc(color)}"/>')
        parts.append(f'    <text x="{lx + 18}" y="{ly}" font-size="13" fill="{c["text"]}">{esc(name)} <tspan fill="{c["muted"]}">{pct:.1f}%</tspan></text>')
    return frame(theme, "Languages", "Share of code by size, repos I pushed to this year", "\n".join(parts), updated)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="dist")
    args = parser.parse_args()

    token = os.environ.get("STATS_TOKEN")
    if not token:
        sys.exit("STATS_TOKEN is not set")

    now = dt.datetime.now(dt.timezone.utc)
    try:
        stats, langs = collect(token, now)
        validate(stats, langs)
    except (StatsError, KeyError, TypeError) as e:
        sys.exit(f"stats update failed, keeping previous images: {e}")

    updated = now.strftime("%Y-%m-%d")
    os.makedirs(args.out, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(args.out, f"activity-{theme}.svg"), "w", encoding="utf-8") as f:
            f.write(activity_svg(theme, stats, updated))
        with open(os.path.join(args.out, f"languages-{theme}.svg"), "w", encoding="utf-8") as f:
            f.write(languages_svg(theme, langs, updated))
    print(json.dumps({"stats": stats, "languages": [(n, round(p, 1)) for n, p, _ in langs]}))


if __name__ == "__main__":
    main()
