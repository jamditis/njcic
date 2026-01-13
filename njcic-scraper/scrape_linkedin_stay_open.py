#!/usr/bin/env python
"""
LinkedIn scraper - STAYS OPEN until you signal to close.
Signal file 1: READY_TO_SCRAPE - starts scraping
Signal file 2: CLOSE_BROWSER - closes browser
"""

import sys
import os
import json
import asyncio
import re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

try:
    from playwright.async_api import async_playwright
    from playwright_stealth.stealth import Stealth
except ImportError:
    print("Playwright not installed!")
    sys.exit(1)

LINKEDIN_URL = "https://www.linkedin.com/company/center-for-cooperative-media/"
GRANTEE_NAME = "Center_for_Cooperative_Media"
MAX_POSTS = 50
SIGNAL_FILE = Path("output/READY_TO_SCRAPE")
CLOSE_FILE = Path("output/CLOSE_BROWSER")


async def scrape_linkedin_stay_open():
    """Browser stays open until you create CLOSE_BROWSER file."""

    print("="*60)
    print("LINKEDIN SCRAPER - BROWSER STAYS OPEN")
    print("="*60)
    print()
    print("WORKFLOW:")
    print("1. Log in when browser opens")
    print("2. Navigate to where you want to scrape")
    print("3. Create signal: touch output/READY_TO_SCRAPE")
    print("4. Scraping happens")
    print("5. Browser STAYS OPEN for you to explore")
    print("6. When done: touch output/CLOSE_BROWSER")
    print()

    # Clean up any existing signal files
    if SIGNAL_FILE.exists():
        SIGNAL_FILE.unlink()
    if CLOSE_FILE.exists():
        CLOSE_FILE.unlink()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )

        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
        )

        page = await context.new_page()

        stealth = Stealth()
        await stealth.apply_stealth_async(page)

        print(">>> Opening LinkedIn login page...")
        await page.goto('https://www.linkedin.com/login', wait_until='domcontentloaded')

        print()
        print("="*60)
        print(">>> WAITING FOR: output/READY_TO_SCRAPE")
        print(">>> Log in, navigate to posts, then create the file")
        print("="*60)

        check_count = 0
        while not SIGNAL_FILE.exists():
            await asyncio.sleep(2)
            check_count += 1
            if check_count % 15 == 0:
                print(f"    Still waiting... ({check_count * 2}s)")

        print(">>> Signal received! Starting scrape...")
        SIGNAL_FILE.unlink()

        # Save cookies
        cookies = await context.cookies()
        cookies_file = Path("output/.cookies/linkedin_cookies.json")
        cookies_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cookies_file, 'w') as f:
            json.dump(cookies, f, indent=2)

        # Get current URL (user may have navigated somewhere)
        current_url = page.url
        print(f">>> Current URL: {current_url}")

        # Get company info from current page
        followers_count = 0
        company_name = ""

        try:
            page_text = await page.inner_text('body')

            name_el = await page.query_selector('h1')
            if name_el:
                company_name = (await name_el.inner_text()).strip()
                print(f"Company: {company_name}")

            for pattern in [r'([\d,]+)\s*followers', r'Followers[:\s]*([\d,]+)']:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    followers_count = int(match.group(1).replace(',', ''))
                    break
            print(f"Followers: {followers_count:,}")
        except Exception as e:
            print(f"Error getting info: {e}")

        # Scroll and collect posts from CURRENT VIEW
        print(">>> Scrolling to load posts from current view...")
        posts = []
        seen_ids = set()
        scroll_attempts = 0
        max_scrolls = 100
        no_new_posts_count = 0

        while len(posts) < MAX_POSTS and scroll_attempts < max_scrolls:
            prev_count = len(posts)

            # Click any "Show more" buttons
            try:
                for btn in await page.query_selector_all('button:has-text("Show more"), button:has-text("Load more")'):
                    try:
                        await btn.click()
                        await page.wait_for_timeout(1500)
                    except:
                        pass
            except:
                pass

            # Find posts
            post_elements = await page.query_selector_all(
                '[data-urn*="activity"], .feed-shared-update-v2, .occludable-update, .org-update-card'
            )

            for post_el in post_elements:
                try:
                    urn = await post_el.get_attribute('data-urn')
                    post_id = ""
                    if urn:
                        id_match = re.search(r'activity[:\-](\d+)', urn)
                        if id_match:
                            post_id = id_match.group(1)

                    if not post_id:
                        content = await post_el.inner_text()
                        if len(content) < 20:
                            continue
                        post_id = str(hash(content[:100]))

                    if post_id in seen_ids:
                        continue
                    seen_ids.add(post_id)

                    text = ""
                    for sel in ['.feed-shared-text', '.break-words', '.update-components-text']:
                        text_el = await post_el.query_selector(sel)
                        if text_el:
                            text = await text_el.inner_text()
                            if text:
                                break

                    likes = 0
                    reactions_el = await post_el.query_selector('.social-details-social-counts__reactions-count')
                    if reactions_el:
                        try:
                            likes = int((await reactions_el.inner_text()).replace(',', ''))
                        except:
                            pass

                    comments = 0
                    comments_el = await post_el.query_selector('.social-details-social-counts__comments')
                    if comments_el:
                        try:
                            match = re.search(r'(\d+)', await comments_el.inner_text())
                            if match:
                                comments = int(match.group(1))
                        except:
                            pass

                    posts.append({
                        'post_id': post_id,
                        'text': text[:500] if text else "",
                        'likes': likes,
                        'comments': comments,
                        'total_engagement': likes + comments,
                        'platform': 'linkedin'
                    })
                    print(f"  Post {len(posts)}: {text[:50]}... | Likes: {likes}")

                except:
                    continue

            if len(posts) == prev_count:
                no_new_posts_count += 1
                if no_new_posts_count >= 15:
                    print(f"  No new posts after {no_new_posts_count} scrolls")
                    break
            else:
                no_new_posts_count = 0

            await page.evaluate('window.scrollBy(0, 1500)')
            await page.wait_for_timeout(2000)
            scroll_attempts += 1

            if scroll_attempts % 10 == 0:
                print(f"  Scrolled {scroll_attempts}x, found {len(posts)} posts...")

        print(f"\n>>> Collected {len(posts)} posts")

        # Save data
        output_dir = Path("output") / GRANTEE_NAME / "linkedin" / "center-for-cooperative-media"
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_dir / "posts_final.json", 'w', encoding='utf-8') as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)

        total_likes = sum(p.get('likes', 0) for p in posts)
        total_comments = sum(p.get('comments', 0) for p in posts)

        metadata = {
            'url': current_url,
            'company_name': company_name,
            'scraped_at': datetime.now().isoformat(),
            'posts_downloaded': len(posts),
            'engagement_metrics': {
                'followers_count': followers_count,
                'total_likes': total_likes,
                'total_comments': total_comments,
                'avg_likes': round(total_likes / len(posts), 2) if posts else 0,
            },
            'platform': 'linkedin'
        }

        with open(output_dir / "metadata_final.json", 'w') as f:
            json.dump(metadata, f, indent=2)

        await page.screenshot(path=str(output_dir / "screenshot_final.png"))

        print("\n" + "="*60)
        print("SCRAPING DONE - BROWSER STAYS OPEN")
        print("="*60)
        print(f"Posts: {len(posts)} | Likes: {total_likes}")
        print()
        print(">>> Browser will stay open indefinitely")
        print(">>> Create output/CLOSE_BROWSER when you want to close")
        print("="*60)

        # Wait for close signal
        while not CLOSE_FILE.exists():
            await asyncio.sleep(2)

        print(">>> Close signal received, shutting down...")
        CLOSE_FILE.unlink()
        await browser.close()

        return {'success': len(posts) > 0, 'posts_downloaded': len(posts)}


if __name__ == "__main__":
    result = asyncio.run(scrape_linkedin_stay_open())
    print(f"\nFinal: {result}")
