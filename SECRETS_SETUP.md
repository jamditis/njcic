# Repository secrets setup

This guide explains how to configure GitHub repository secrets for the NJCIC social media scrapers. **No developer API accounts are required** — all scrapers use Playwright browser automation to collect public data. You only need regular account credentials for platforms that restrict anonymous access.

## Platforms and what they need

| Platform | Credentials required | Secrets to set |
|----------|---------------------|----------------|
| **Facebook** | None | — |
| **Threads** | None (uses Instagram login if available) | — |
| **Twitter/X** | Optional (improves access) | `TWITTER_USERNAME`, `TWITTER_PASSWORD` |
| **Instagram** | Recommended | `INSTAGRAM_USERNAME`, `INSTAGRAM_PASSWORD` |
| **LinkedIn** | Recommended | `LINKEDIN_EMAIL`, `LINKEDIN_PASSWORD` |

## Secrets to configure

### Required (recommended for reliable scraping)

| Secret | Value | Notes |
|--------|-------|-------|
| `INSTAGRAM_USERNAME` | Your Instagram username | Also used by Threads (Meta login). Consider a dedicated account. |
| `INSTAGRAM_PASSWORD` | Your Instagram password | |
| `LINKEDIN_EMAIL` | Your LinkedIn email | Consider a dedicated account. |
| `LINKEDIN_PASSWORD` | Your LinkedIn password | |

### Optional (improve Twitter/X data access)

| Secret | Value | Notes |
|--------|-------|-------|
| `TWITTER_USERNAME` | Your Twitter/X username | Regular account — **not** a developer API key. |
| `TWITTER_PASSWORD` | Your Twitter/X password | The scraper works without this via public page scraping. |

### Optional (notifications)

| Secret | Value | Notes |
|--------|-------|-------|
| `SLACK_WEBHOOK` | Slack incoming webhook URL | For failure notifications. Not required. |

## How to add secrets

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret from the tables above with the exact name and your value
5. Repeat for each secret

## What you do NOT need

The previous setup referenced several developer API credentials that are **no longer required**:

- ~~`TWITTER_BEARER_TOKEN`~~ — not needed (Playwright browser scraping replaces the API)
- ~~`TWITTER_API_KEY` / `TWITTER_API_SECRET`~~ — not needed
- ~~`TWITTER_ACCESS_TOKEN` / `TWITTER_ACCESS_TOKEN_SECRET`~~ — not needed
- ~~`FACEBOOK_ACCESS_TOKEN`~~ — not needed (Playwright scrapes public pages)
- ~~`FACEBOOK_APP_ID` / `FACEBOOK_APP_SECRET`~~ — not needed
- ~~`YOUTUBE_API_KEY`~~ — not needed (YouTube not in active platform list)
- ~~`BLUESKY_HANDLE` / `BLUESKY_APP_PASSWORD`~~ — not needed (BlueSky not in active platform list)

## Schedule

Both workflows run weekly on Mondays:

- **Internal metrics** (NJCIC accounts): 6:00 AM ET
- **Grantee dashboard** (all grantees): 7:00 AM ET

You can also trigger either workflow manually from the Actions tab.
