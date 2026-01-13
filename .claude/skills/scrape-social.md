# Social media manual login scraper

Use this skill to batch scrape social media platforms that require authentication. This covers Instagram, Twitter/X, Facebook, LinkedIn, and TikTok.

## Overview

These scrapers use Playwright with stealth mode and a signal-file workflow:
1. Browser opens to login page
2. User logs in manually (handles 2FA, CAPTCHAs)
3. User creates signal file: `touch output/READY_TO_SCRAPE`
4. Script cycles through all grantees automatically
5. Skips already-scraped accounts (resume capability)
6. User creates close file when done: `touch output/CLOSE_BROWSER`

## Available batch scrapers

Located in `njcic-scraper/`:

| Script | Platform | Grantees |
|--------|----------|----------|
| `scrape_twitter_batch.py` | Twitter/X | 48 |
| `scrape_instagram_batch.py` | Instagram | 55 |
| `scrape_facebook_batch.py` | Facebook | 52 |
| `scrape_linkedin_batch.py` | LinkedIn | 30 |
| `scrape_tiktok_batch.py` | TikTok | 14 |

## Usage

```bash
cd njcic-scraper
./venv/Scripts/python.exe scrape_twitter_batch.py
# Login manually in browser
touch output/READY_TO_SCRAPE
# Wait for completion
touch output/CLOSE_BROWSER
```

## Key features

- **Resume capability**: Checks for existing metadata.json files and skips completed accounts
- **Stealth mode**: Uses playwright-stealth to avoid bot detection
- **Signal file workflow**: No manual intervention needed after login
- **Structured output**: Saves to `output/{Grantee_Name}/{platform}/{handle}/`

## Output structure

```
output/
├── {Grantee_Name}/
│   └── {platform}/
│       └── {handle}/
│           ├── posts.json
│           └── metadata.json
├── {platform}_batch_summary.json
└── .cookies/
    └── {platform}_cookies.json
```

## Data integration

After scraping, run `integrate_scraped_data.py` to update dashboard grantee files.
