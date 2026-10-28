# Profile stats: setup and maintenance

The Activity and Languages cards in the README are generated daily by
[.github/workflows/update-stats.yml](../.github/workflows/update-stats.yml),
which runs [scripts/update_stats.py](../scripts/update_stats.py). The images are
published to the `stats` branch, so `main` stays free of bot commits.

## What the numbers mean

The first three rows cover repositories owned by `azizz7` (public and private), last 12 months.

| Card row | Source |
|---|---|
| Commits | Commits authored by me on each repo's default branch |
| Pull requests | PRs I opened in my own repos, and how many of those were merged |
| Active repositories | Own repos pushed to in the last 12 months |
| Contributions | GitHub's own total across all repositories, including private ones the token cannot read (for example an employer's) |
| of which private | GitHub's anonymous count of private contributions |
| Languages | GitHub's language detection, by code size, in repos pushed to in the last 12 months. HTML, CSS, notebooks and Makefiles are excluded |

The last two Activity rows only appear when private contributions are enabled
on the profile; otherwise they are hidden, because GitHub would silently omit
private work and the number would mislead.

Not included: issues, and per-repository breakdowns for repositories owned by
other accounts or organisations. A read-only token owned by this account cannot
read them. With private contributions enabled, GitHub still counts that work
in the all-repositories total, with no names or details.

## Profile views counter

The "Profile views" badge in the README comes from komarev.com's
[github-profile-views-counter](https://github.com/antonkomarev/github-profile-views-counter).
It counts page loads (hits) made through GitHub's image proxy, not unique
people, and it cannot see visitor IPs or usernames. If the service is down the
badge shows its alt text and the rest of the page is unaffected. There is
nothing to configure or renew. To reset the count, use the reset page linked
from that project's README.

## One-time setup

1. **Private contributions.** On the profile page, open *Contribution settings*
   and turn on *Private contributions*. This shows anonymous counts only.
2. **Create a read-only token.** GitHub, *Settings, Developer settings,
   Personal access tokens, Fine-grained tokens, Generate new token*.
   - Resource owner: `azizz7`
   - Repository access: *All repositories*
   - Repository permissions, all *Read-only*: *Contents*, *Pull requests*
     (*Metadata* is added automatically)
   - Expiration: 1 year
3. **Store it.** In this repo: *Settings, Secrets and variables, Actions,
   New repository secret*. Name it `STATS_TOKEN`.
4. **First run.** *Actions, Update stats, Run workflow*. The images appear
   on the `stats` branch and in the README.

## Maintenance and failures

- Renew the token before it expires and update the `STATS_TOKEN` secret.
  Expiry shows up as a failed run.
- On any API error, rate limit exhaustion or malformed data the script exits
  non-zero and publishes nothing. The last good images stay in the README and
  GitHub's failed-run notification reaches the repo owner.
- Each image shows its update date, so a stale card is visible.
- The workflow runs only on schedule and manual trigger, never on pull
  requests, so the secret is never exposed to forks.
- Run locally for a quick check: `STATS_TOKEN=$(gh auth token) python3 scripts/update_stats.py --out /tmp/stats`
