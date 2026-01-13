#!/usr/bin/env python
"""
LinkedIn scraper with MANUAL LOGIN.
Opens browser, waits for signal file after login, then scrapes posts.
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


async def scrape_linkedin_manual():
    """Open LinkedIn, let user login, then scrape."""

    print("="*60)
    print("LINKEDIN MANUAL LOGIN SCRAPER")
    print("="*60)
    print()
    print("INSTRUCTIONS:")
    print("1. Browser opens to LinkedIn login")
    print("2. Complete login")
    print("3. Create signal file to continue:")
    print(f"   echo > output\\READY_TO_SCRAPE")
    print()

    if SIGNAL_FILE.exists():
        SIGNAL_FILE.unlink()

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
        print(f">>> Waiting for signal file: {SIGNAL_FILE}")
        print(">>> Complete login, then create the file to continue")
        print("="*60)

        check_count = 0
        while not SIGNAL_FILE.exists():
            await asyncio.sleep(2)
            check_count += 1
            if check_count % 10 == 0:
                print(f"    Still waiting... ({check_count * 2}s elapsed)")

        print(">>> Signal received! Continuing...")
        SIGNAL_FILE.unlink()

        # Save cookies
        cookies = await context.cookies()
        cookies_file = Path("output/.cookies/linkedin_cookies.json")
        cookies_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cookies_file, 'w') as f:
            json.dump(cookies, f, indent=2)
        print(f"Saved {len(cookies)} cookies")

        # Navigate to company page
        print(f">>> Navigating to company page: {LINKEDIN_URL}")
        await page.goto(LINKEDIN_URL, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)

        # Get company info
        followers_count = 0
        company_name = ""
        employee_count = ""
        industry = ""
        description = ""

        try:
            page_text = await page.inner_text('body')

            # Get company name
            name_el = await page.query_selector('h1')
            if name_el:
                company_name = await name_el.inner_text()
                company_name = company_name.strip()
                print(f"Company: {company_name}")

            # Get follower count
            follower_patterns = [
                r'([\d,]+)\s*followers',
                r'Followers[:\s]*([\d,]+)',
            ]
            for pattern in follower_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    followers_count = int(match.group(1).replace(',', ''))
                    break

            print(f"Followers: {followers_count:,}")

            # Get employee count
            employee_match = re.search(r'([\d,]+(?:-[\d,]+)?)\s*employees', page_text, re.IGNORECASE)
            if employee_match:
                employee_count = employee_match.group(1)
                print(f"Employees: {employee_count}")

        except Exception as e:
            print(f"Error getting company info: {e}")

        # Navigate to posts
        posts_url = LINKEDIN_URL.rstrip('/') + '/posts/'
        print(f">>> Navigating to posts: {posts_url}")
        await page.goto(posts_url, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)

        # Scroll and collect posts
        print(">>> Scrolling to load posts...")
        posts = []
        seen_ids = set()
        scroll_attempts = 0
        max_scrolls = 30

        while len(posts) < MAX_POSTS and scroll_attempts < max_scrolls:
            # Find post containers
            post_elements = await page.query_selector_all('[data-urn*="activity"], .feed-shared-update-v2, .occludable-update')

            for post_el in post_elements:
                try:
                    # Try to get post URN/ID
                    urn = await post_el.get_attribute('data-urn')
                    if not urn:
                        # Try to find it in child elements
                        urn_el = await post_el.query_selector('[data-urn]')
                        if urn_el:
                            urn = await urn_el.get_attribute('data-urn')

                    post_id = ""
                    if urn:
                        # Extract activity ID from URN
                        id_match = re.search(r'activity:(\d+)', urn)
                        if id_match:
                            post_id = id_match.group(1)

                    if not post_id:
                        # Generate a hash from content as fallback
                        content = await post_el.inner_text()
                        post_id = str(hash(content[:100]))

                    if post_id in seen_ids:
                        continue

                    seen_ids.add(post_id)

                    # Get post text
                    text = ""
                    text_el = await post_el.query_selector('.feed-shared-text, .break-words, .feed-shared-update-v2__description')
                    if text_el:
                        text = await text_el.inner_text()

                    # Get reactions/likes
                    likes = 0
                    reactions_el = await post_el.query_selector('.social-details-social-counts__reactions-count, [data-test-id="social-actions__reaction-count"]')
                    if reactions_el:
                        reactions_text = await reactions_el.inner_text()
                        reactions_text = reactions_text.replace(',', '').strip()
                        try:
                            likes = int(reactions_text)
                        except:
                            pass

                    # Get comments count
                    comments = 0
                    comments_el = await post_el.query_selector('.social-details-social-counts__comments, [aria-label*="comment"]')
                    if comments_el:
                        comments_text = await comments_el.inner_text()
                        comment_match = re.search(r'(\d+)', comments_text)
                        if comment_match:
                            comments = int(comment_match.group(1))

                    post_data = {
                        'post_id': post_id,
                        'text': text[:500] if text else "",
                        'likes': likes,
                        'comments': comments,
                        'total_engagement': likes + comments,
                        'platform': 'linkedin'
                    }
                    posts.append(post_data)
                    print(f"  Post {len(posts)}: {text[:40]}... | Likes: {likes}, Comments: {comments}")

                except Exception as e:
                    continue

            # Scroll down
            await page.evaluate('window.scrollBy(0, 1000)')
            await page.wait_for_timeout(2000)
            scroll_attempts += 1

            if len(posts) >= MAX_POSTS:
                break

        print(f"\n>>> Collected {len(posts)} posts")

        # Save data
        output_dir = Path("output") / GRANTEE_NAME / "linkedin" / "center-for-cooperative-media"
        output_dir.mkdir(parents=True, exist_ok=True)

        posts_file = output_dir / "posts_manual.json"
        with open(posts_file, 'w', encoding='utf-8') as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)
        print(f"Saved posts to: {posts_file}")

        # Calculate metrics
        total_likes = sum(p.get('likes', 0) for p in posts)
        total_comments = sum(p.get('comments', 0) for p in posts)

        metadata = {
            'url': LINKEDIN_URL,
            'company_name': company_name,
            'grantee_name': GRANTEE_NAME,
            'scraped_at': datetime.now().isoformat(),
            'posts_downloaded': len(posts),
            'engagement_metrics': {
                'followers_count': followers_count,
                'employee_count': employee_count,
                'total_likes': total_likes,
                'total_comments': total_comments,
                'avg_likes': round(total_likes / len(posts), 2) if posts else 0,
                'avg_comments': round(total_comments / len(posts), 2) if posts else 0,
                'posts_analyzed': len(posts)
            },
            'authenticated': True,
            'platform': 'linkedin',
            'method': 'manual_login'
        }

        metadata_file = output_dir / "metadata_manual.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"Saved metadata to: {metadata_file}")

        await page.screenshot(path=str(output_dir / "screenshot_manual.png"))

        print("\n" + "="*60)
        print("LINKEDIN SCRAPING COMPLETE")
        print("="*60)
        print(f"Posts collected: {len(posts)}")
        print(f"Company: {company_name}")
        print(f"Followers: {followers_count:,}")
        print(f"Total likes: {total_likes:,}")
        print(f"Total comments: {total_comments:,}")

        print("\n>>> Browser will close in 10 seconds...")
        await asyncio.sleep(10)
        await browser.close()

        return {
            'success': len(posts) > 0,
            'posts_downloaded': len(posts),
            'engagement_metrics': metadata['engagement_metrics']
        }


if __name__ == "__main__":
    result = asyncio.run(scrape_linkedin_manual())
    print(f"\nFinal result: {result}")
