# Scrape grantee social media

Use this skill when you need to scrape social media data for NJCIC grantees. This provides a complete workflow for collecting engagement metrics across all platforms.

## Prerequisites

```bash
cd njcic-scraper
# Activate venv if needed
./venv/Scripts/activate  # Windows
source venv/bin/activate  # Linux/Mac
```

## Full scraping workflow

### 1. Automated scrapers (no login required)

```bash
# Bluesky - uses public AT Protocol API
./venv/Scripts/python.exe scrape_bluesky_batch.py

# YouTube - uses yt-dlp
./venv/Scripts/python.exe scrape_youtube_batch.py
```

### 2. Manual login scrapers

Run each platform scraper, login when browser opens, then signal:

```bash
# Twitter
./venv/Scripts/python.exe scrape_twitter_batch.py
# Login, then: touch output/READY_TO_SCRAPE
# When done: touch output/CLOSE_BROWSER

# Instagram
./venv/Scripts/python.exe scrape_instagram_batch.py
# Login, then: touch output/READY_TO_SCRAPE
# When done: touch output/CLOSE_BROWSER

# Facebook
./venv/Scripts/python.exe scrape_facebook_batch.py
# Login, then: touch output/READY_TO_SCRAPE
# When done: touch output/CLOSE_BROWSER

# LinkedIn
./venv/Scripts/python.exe scrape_linkedin_batch.py
# Login, then: touch output/READY_TO_SCRAPE
# When done: touch output/CLOSE_BROWSER

# TikTok (login optional)
./venv/Scripts/python.exe scrape_tiktok_batch.py
# Signal: touch output/READY_TO_SCRAPE
# When done: touch output/CLOSE_BROWSER
```

### 3. Integrate scraped data

```bash
./venv/Scripts/python.exe integrate_scraped_data.py
```

This updates:
- Individual grantee JSON files in `dashboard/data/grantees/`
- Aggregated `dashboard/data/dashboard-data.json`

## Handling stuck scrapers

If a scraper appears stuck:
1. Check if it's still processing (output may be buffered)
2. Create close signal: `touch output/CLOSE_BROWSER`
3. Restart - it will skip already-completed accounts

## Typical results

| Platform | Success rate |
|----------|--------------|
| Bluesky | 100% |
| YouTube | ~65% (some 404s) |
| Twitter | ~80% (some inactive accounts) |
| Instagram | ~90% (some private/no posts) |
| Facebook | ~80% (some unavailable pages) |
| LinkedIn | ~95% |
| TikTok | ~100% |
