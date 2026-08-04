# Bugbot review guidelines (CFB Ranking System)

Focus on real bugs and security issues. Skip style, formatting, and nitpicks.

## Always flag

- Broken API contracts between Flask backend and SvelteKit frontend
- Missing or wrong handling of CFBD API failures / empty data
- Cache key collisions or stale ranking data served to users
- Secrets or API keys committed to the repo
- CORS misconfiguration that exposes credentials broadly in production paths

## Usually skip

- MD5 used for cache keys or config fingerprints (intentional, non-cryptographic)
- `/tmp/cfb-cache` fallback when `CACHE_DIR` is unset
- Pre-existing ESLint/style issues unless this PR introduces new ones
- Dependency version bumps that only touch lockfiles or requirements pins

## Dependency PRs

Grouped Dependabot PRs are auto-merged when CI passes. Review only if the diff touches application logic, not just version pins.
