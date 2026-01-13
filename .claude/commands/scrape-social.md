# Social media manual login scraper

This skill scrapes social media posts using Playwright with a manual login workflow. Supports Instagram, TikTok, LinkedIn, and Twitter.

## Pattern overview

All manual login scrapers follow the same pattern:

1. **Launch browser** - Playwright opens visible browser (headless=False)
2. **Apply stealth** - playwright-stealth hides automation markers
3. **Wait for login** - Script polls for signal file
4. **User logs in** - Manual login handles 2FA, captchas, etc.
5. **Signal completion** - User creates signal file
6. **Scrape content** - Script navigates and extracts data
7. **Save results** - JSON files with posts and metadata

## Signal file

All scrapers wait for: `output/READY_TO_SCRAPE`

Create it after logging in:
```bash
touch njcic-scraper/output/READY_TO_SCRAPE
```

The script deletes the file when it detects it, so you can reuse the same signal for multiple scrapers run sequentially.

## Available scrapers

### Instagram
```bash
python scrape_instagram_manual.py
```
- Collects posts from profile grid
- Visits each post for engagement metrics
- Saves: posts, likes, comments, captions

### TikTok
```bash
python scrape_tiktok_manual.py
```
- Collects videos from profile
- Visits each video for engagement
- Saves: videos, views, likes, comments, shares

### LinkedIn
```bash
python scrape_linkedin_manual.py
python scrape_linkedin_improved.py  # More aggressive scrolling
```
- Scrapes company page posts
- Gets reactions, comments
- Saves: posts, likes, comments, followers

### Twitter
```bash
python scrape_twitter_file_signal.py
```
- Scrolls timeline for tweets
- Extracts engagement via aria-labels
- Saves: tweets, likes, retweets, replies

## Quick start

1. Activate virtual environment:
```bash
cd njcic-scraper
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
```

2. Run desired scraper:
```bash
python scrape_instagram_manual.py
```

3. Log in manually in the browser

4. Signal completion:
```bash
touch output/READY_TO_SCRAPE
```

5. Wait for scraping to complete

## Customizing for different accounts

Each scraper has constants at the top to modify:

```python
INSTAGRAM_URL = "https://www.instagram.com/TARGET_USERNAME/"
GRANTEE_NAME = "Organization_Name"
MAX_POSTS = 50
```

## Output structure

```
output/
  {GRANTEE_NAME}/
    instagram/
      {username}/
        posts_manual.json
        metadata_manual.json
        screenshot_manual.png
    twitter/
      {username}/
        posts.json
        metadata.json
    tiktok/
      posts_manual.json
      metadata_manual.json
    linkedin/
      center-for-cooperative-media/
        posts_manual.json
        metadata_manual.json
  .cookies/
    instagram_cookies.json
    twitter_cookies.json
    tiktok_cookies.json
    linkedin_cookies.json
```

## Tips

### Reusing cookies

Cookies are saved after each successful login. Future scrapers could load these to skip login, but most platforms detect cookie reuse across sessions.

### Rate limiting

Add delays between requests to avoid rate limits:
```python
await page.wait_for_timeout(2000)  # 2 second delay
```

### Scrolling more content

Increase scroll attempts for more posts:
```python
max_scrolls = 100  # Default is usually 30-50
```

### Keeping browser open

Increase final delay before browser closes:
```python
await asyncio.sleep(60)  # Keep open 60 seconds
```

## Creating new scrapers

Use this template:

```python
#!/usr/bin/env python
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth.stealth import Stealth

SIGNAL_FILE = Path("output/READY_TO_SCRAPE")

async def scrape_platform():
    if SIGNAL_FILE.exists():
        SIGNAL_FILE.unlink()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        stealth = Stealth()
        await stealth.apply_stealth_async(page)

        await page.goto('https://platform.com/login')

        print("Waiting for signal file...")
        while not SIGNAL_FILE.exists():
            await asyncio.sleep(2)
        SIGNAL_FILE.unlink()
        print("Signal received!")

        # Your scraping logic here

        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_platform())
```

## Related commands

- `/scrape-instagram` - Instagram-specific instructions
- Full scraper files in `njcic-scraper/` directory
