# Instagram manual login scraper

This skill scrapes Instagram posts for a specified profile using Playwright with manual login authentication.

## Overview

Instagram requires authentication to view most content. This skill uses a manual login approach where:
1. A browser opens to Instagram's login page
2. The user logs in manually (handling 2FA if needed)
3. A signal file triggers the scraper to continue
4. The scraper collects posts and engagement data

## Prerequisites

- Python 3.11+ with virtual environment
- Playwright installed with chromium browser
- playwright-stealth package

```bash
cd njcic-scraper
python -m venv venv
venv\Scripts\activate  # Windows
pip install playwright playwright-stealth python-dotenv
playwright install chromium
```

## Usage

### Step 1: Update target profile

Edit the scraper file to set the target Instagram URL:
```python
INSTAGRAM_URL = "https://www.instagram.com/TARGET_USERNAME/"
GRANTEE_NAME = "Organization_Name"
```

### Step 2: Run the scraper

```bash
cd njcic-scraper
venv\Scripts\activate
python scrape_instagram_manual.py
```

### Step 3: Complete login

1. Browser opens to Instagram login page
2. Enter username and password
3. Complete 2FA if prompted
4. Navigate around to ensure you're fully logged in

### Step 4: Signal completion

Create the signal file to tell the scraper to continue:

**Windows:**
```bash
touch njcic-scraper/output/READY_TO_SCRAPE
```

**PowerShell:**
```powershell
New-Item -Path "njcic-scraper\output\READY_TO_SCRAPE" -ItemType File
```

### Step 5: Wait for scraping

The scraper will:
1. Save cookies for potential reuse
2. Navigate to the target profile
3. Scroll to load posts
4. Visit each post to get detailed engagement metrics
5. Save results to JSON files

## Output files

All output goes to: `output/{GRANTEE_NAME}/instagram/{username}/`

- `posts_manual.json` - Array of post data with engagement
- `metadata_manual.json` - Scrape metadata and aggregated metrics
- `screenshot_manual.png` - Final screenshot

## Post data structure

```json
{
  "post_id": "shortcode",
  "shortcode": "ABC123xyz",
  "url": "https://www.instagram.com/p/ABC123xyz/",
  "caption_preview": "First 200 chars of caption...",
  "likes": 42,
  "comments": 5,
  "caption": "Full caption text",
  "timestamp": "2025-01-10T14:30:00",
  "total_engagement": 47,
  "platform": "instagram"
}
```

## Troubleshooting

### Engagement metrics showing 0

Instagram frequently changes their page structure. The regex patterns for extracting likes/comments may need updating. Check the page source for current patterns.

### Browser closes too quickly

The browser stays open for 10 seconds after completion. Increase the sleep time in the script if needed:
```python
await asyncio.sleep(30)  # Increase from 10
```

### Rate limiting

Instagram may rate-limit if scraping too fast. The script has built-in delays but you may need to increase them:
```python
await page.wait_for_timeout(3000)  # Increase from 1500
```

### 2FA issues

Complete 2FA manually in the browser before creating the signal file. The script waits indefinitely for the signal.

## Cookies

Cookies are saved to `output/.cookies/instagram_cookies.json` for potential reuse. To use existing cookies:

```python
# Load cookies before navigating
cookies_file = Path("output/.cookies/instagram_cookies.json")
if cookies_file.exists():
    with open(cookies_file, 'r') as f:
        cookies = json.load(f)
    await context.add_cookies(cookies)
```

## Related files

- `njcic-scraper/scrape_instagram_manual.py` - Main scraper script
- `njcic-scraper/output/.cookies/instagram_cookies.json` - Saved auth cookies
