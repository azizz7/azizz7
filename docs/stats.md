# Profile stats: setup and maintenance

The Activity and Languages cards in the README are generated daily by
[.github/workflows/update-stats.yml](../.github/workflows/update-stats.yml),
which runs [scripts/update_stats.py](../scripts/update_stats.py). The images are
published to the `stats` branch, so `main` stays free of bot commits.

## What the numbers mean

All figures cover repositories owned by `azizz7` (public and private), last 12 months.

| Card row | Source |
|---|---|
| Commits | Commits authored by me on each repo's default branch |
| Pull requests merged of opened | PRs I opened in my own repos, and how many were merged |
| Active repositories | Own repos pushed to in the last 12 months |
| Contributions, all repos | GitHub's own total. Shown only if private contributions are enabled on the profile; otherwise hidden, because it would silently omit private work |
| Languages | GitHub's language detection, by code size, in repos pushed to in the last 12 months. HTML, CSS, notebooks and Makefiles are excluded |

Not included: work in repositories owned by other accounts or organisations
(for example an employer's private repos). A read-only token owned by this
account cannot read them. With private contributions enabled, GitHub counts
that work in its own total.

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
