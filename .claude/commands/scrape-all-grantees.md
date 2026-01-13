# Scrape all grantees

Batch scraping workflow for collecting social media data from all NJCIC grantees.

## Overview

There are 60+ grantees with varying social media presence. This skill covers how to systematically scrape them all using the manual login workflow.

## Quick reference

```bash
cd njcic-scraper
venv\Scripts\activate

# See platform coverage
python batch_scrape.py --summary

# List all grantees
python batch_scrape.py --list

# Generate commands for a platform
python batch_scrape.py --commands twitter

# Export all URLs to CSV
python batch_scrape.py --export grantees_social.csv
```

## Recommended workflow

### 1. Check platform coverage

```bash
python batch_scrape.py --summary
```

Shows how many grantees have accounts on each platform.

### 2. Pick a platform to scrape

Start with platforms that don't require login (easier):
- **Bluesky** - Public API, no login needed
- **YouTube** - Public API via yt-dlp

Then do login-required platforms:
- **Twitter** - Manual login, good engagement data
- **Instagram** - Manual login, visits each post
- **LinkedIn** - Manual login, limited to public posts (no admin access)
- **TikTok** - Manual login, handles captchas
- **Facebook** - Manual login, limited public data

### 3. Generate scraping commands

```bash
python batch_scrape.py --commands twitter > twitter_commands.txt
```

This outputs commands like:
```bash
# NJ Spotlight News
python scrape_grantee.py -p twitter -g "NJ Spotlight News" -u "https://twitter.com/NJSpotlightNews"

# TAPinto
python scrape_grantee.py -p twitter -g "TAPinto" -u "https://twitter.com/tapinto"
```

### 4. Run scrapers one at a time

For each grantee:

1. Run the command
2. Log in when browser opens
3. Signal: `touch output/READY_TO_SCRAPE`
4. Wait for scraping
5. Signal to close: `touch output/CLOSE_BROWSER`
6. Move to next grantee

### 5. Use same login session (efficiency tip)

Once logged into a platform, you can scrape multiple grantees without re-logging in:

1. After scraping first grantee, don't close browser
2. Manually navigate to next grantee's profile
3. Create `READY_TO_SCRAPE` signal
4. Script will scrape from current page
5. Repeat for remaining grantees

## Admin vs public access

### CCM (you have admin access)
- Can use admin URL: `linkedin.com/company/{id}/admin/page-posts/published/`
- See all historical posts
- Full engagement metrics

### Other grantees (public access only)
- Limited to public feed view
- May see fewer posts (recent only)
- Some engagement data hidden
- LinkedIn company pages: typically 5-15 posts visible

## Data storage

All scraped data goes to:
```
njcic-scraper/output/
  {Grantee_Name}/
    twitter/
      {username}/
        posts.json
        metadata.json
    instagram/
      {username}/
        posts.json
        metadata.json
    ...
```

## Platform-specific notes

### Twitter/X
- Full engagement via aria-labels (likes, retweets, replies)
- May require waiting for rate limits
- Security challenges possible - handle manually

### Instagram
- Collects post shortcodes first, then visits each
- Engagement extraction may fail on new page layouts
- 2FA required for most accounts

### LinkedIn
- Without admin access: ~5-15 posts visible
- Navigate to `/posts/` URL manually for best results
- Follower count usually available

### TikTok
- Captchas common - handle manually
- Video IDs collected, engagement varies
- Profile likes/followers usually visible

### Facebook
- Most limited public data
- Many pages restrict non-followers
- May only get 10-20 posts

### YouTube
- Use yt-dlp instead of browser scraper
- Public API, no login needed
- Full video metadata available

### Bluesky
- Public AT Protocol API
- No login needed
- Full engagement data

## Tracking progress

Create a simple tracking spreadsheet:

| Grantee | Twitter | Instagram | LinkedIn | TikTok | YouTube | Bluesky |
|---------|---------|-----------|----------|--------|---------|---------|
| NJ Spotlight | Done | Done | Pending | Done | Done | Done |
| TAPinto | Done | Pending | N/A | N/A | Done | N/A |
| ... | ... | ... | ... | ... | ... | ... |

## Troubleshooting

### Account doesn't exist
- Skip and note in tracking
- Some grantees don't have all platforms

### Account is private
- Can't scrape without following
- Note as "private" in tracking

### Rate limited
- Wait and retry later
- Consider spreading across days

### Login blocked
- Clear cookies, try new session
- Use different browser profile

## Related skills

- `/scrape-grantee` - Single grantee scraping
- `/scrape-social` - Manual login workflow details

## Files

- `njcic-scraper/scrape_grantee.py` - Main parameterized scraper
- `njcic-scraper/batch_scrape.py` - Batch utilities
- `dashboard/data/grantees/*.json` - Grantee data with social URLs
