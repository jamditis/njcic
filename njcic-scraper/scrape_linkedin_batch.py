#!/usr/bin/env python
"""
LinkedIn batch scraper - scrapes ALL grantees in one session.
Login once, then script cycles through all grantees automatically.
"""

import sys
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

GRANTEES_DIR = Path(__file__).parent.parent / "dashboard" / "data" / "grantees"
OUTPUT_DIR = Path(__file__).parent / "output"
SIGNAL_FILE = Path("output/READY_TO_SCRAPE")
CLOSE_FILE = Path("output/CLOSE_BROWSER")
MAX_POSTS = 20


def get_linkedin_grantees():
    """Load all grantees with LinkedIn accounts."""
    grantees = []

    for json_file in GRANTEES_DIR.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            li_url = data.get('social', {}).get('linkedin')
            if li_url:
                # Extract company/profile name from URL
                match = re.search(r'linkedin\.com/(?:company|in)/([^/?]+)', li_url)
                if match:
                    handle = match.group(1).rstrip('/')
                    url_type = 'company' if '/company/' in li_url else 'in'
                    grantees.append({
                        'name': data.get('name', json_file.stem),
                        'slug': data.get('slug', json_file.stem),
                        'handle': handle,
                        'url_type': url_type,
                        'url': li_url
                    })
        except Exception as e:
            print(f"Warning: Could not load {json_file}: {e}")

    return sorted(grantees, key=lambda x: x['name'])


async def scrape_linkedin_profile(page, grantee, grantee_num, total):
    """Scrape a single LinkedIn company/profile page."""
    print(f"\n[{grantee_num}/{total}] {grantee['name']} ({grantee['handle']})")
    print("-" * 50, flush=True)

    url = f"https://www.linkedin.com/{grantee['url_type']}/{grantee['handle']}/"

    try:
        await page.goto(url, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)

        # Check if page exists
        page_text = await page.inner_text('body')
        if "Page not found" in page_text or "This page doesn" in page_text:
            print(f"  SKIP: Page not found")
            return None

        # Try to get follower count
        followers = 0

        # Look for follower patterns
        follower_match = re.search(r'([\d,\.]+)\s*followers', page_text, re.IGNORECASE)
        if follower_match:
            num_str = follower_match.group(1).replace(',', '')
            try:
                followers = int(num_str)
            except:
                pass

        print(f"  Followers: {followers:,}")

        # For company pages, try to get posts
        posts = []

        if grantee['url_type'] == 'company':
            # Navigate to posts section
            posts_url = f"https://www.linkedin.com/company/{grantee['handle']}/posts/"
            await page.goto(posts_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)

            # Scroll to load posts
            seen_ids = set()
            scroll_attempts = 0
            no_new_count = 0

            while len(posts) < MAX_POSTS and scroll_attempts < 10:
                prev_count = len(posts)

                # Find post containers
                post_elements = await page.query_selector_all('[data-urn*="activity"]')

                for post_el in post_elements:
                    try:
                        urn = await post_el.get_attribute('data-urn')
                        if not urn or urn in seen_ids:
                            continue
                        seen_ids.add(urn)

                        # Extract activity ID
                        activity_match = re.search(r'activity:(\d+)', urn)
                        if activity_match:
                            activity_id = activity_match.group(1)
                            posts.append({
                                'post_id': activity_id,
                                'urn': urn,
                                'url': f"https://www.linkedin.com/feed/update/{urn}/",
                                'platform': 'linkedin'
                            })
                    except:
                        continue

                if len(posts) == prev_count:
                    no_new_count += 1
                    if no_new_count >= 3:
                        break
                else:
                    no_new_count = 0

                await page.evaluate('window.scrollBy(0, 1000)')
                await page.wait_for_timeout(1500)
                scroll_attempts += 1

        print(f"  Found {len(posts)} posts")

        # Save data
        grantee_safe = re.sub(r'[^\w\-]', '_', grantee['name'].replace(' ', '_'))
        output_dir = OUTPUT_DIR / grantee_safe / "linkedin" / grantee['handle']
        output_dir.mkdir(parents=True, exist_ok=True)

        if posts:
            with open(output_dir / "posts.json", 'w', encoding='utf-8') as f:
                json.dump(posts, f, indent=2, ensure_ascii=False)

        metadata = {
            'url': grantee['url'],
            'handle': grantee['handle'],
            'url_type': grantee['url_type'],
            'grantee_name': grantee['name'],
            'scraped_at': datetime.now().isoformat(),
            'posts_downloaded': len(posts),
            'engagement_metrics': {
                'followers_count': followers,
            },
            'platform': 'linkedin',
            'method': 'batch_scrape'
        }

        with open(output_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)

        return metadata

    except Exception as e:
        print(f"  ERROR: {e}")
        return None


async def main():
    print("=" * 60)
    print("LINKEDIN BATCH SCRAPER")
    print("=" * 60)

    grantees = get_linkedin_grantees()
    print(f"\nFound {len(grantees)} grantees with LinkedIn accounts")

    # Clean signal files
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

        # Go to LinkedIn login
        print("\n>>> Opening LinkedIn login...")
        await page.goto('https://www.linkedin.com/login', wait_until='domcontentloaded')

        print()
        print("=" * 60)
        print("LOG IN TO LINKEDIN")
        print("Then create signal file: touch output/READY_TO_SCRAPE")
        print("=" * 60)

        # Wait for login signal
        while not SIGNAL_FILE.exists():
            await asyncio.sleep(2)

        print("\n>>> Signal received! Starting batch scrape...")
        SIGNAL_FILE.unlink()

        # Save cookies
        cookies = await context.cookies()
        cookies_dir = OUTPUT_DIR / ".cookies"
        cookies_dir.mkdir(parents=True, exist_ok=True)
        with open(cookies_dir / "linkedin_cookies.json", 'w') as f:
            json.dump(cookies, f, indent=2)

        # Check which grantees already have data (to skip)
        already_done = set()
        for grantee in grantees:
            grantee_safe = re.sub(r'[^\w\-]', '_', grantee['name'].replace(' ', '_'))
            metadata_file = OUTPUT_DIR / grantee_safe / "linkedin" / grantee['handle'] / "metadata.json"
            if metadata_file.exists():
                already_done.add(grantee['handle'])

        if already_done:
            print(f"\n>>> Skipping {len(already_done)} already-scraped grantees")

        # Scrape all grantees
        results = []
        success = 0
        failed = 0
        skipped = 0

        for i, grantee in enumerate(grantees, 1):
            # Skip if already done
            if grantee['handle'] in already_done:
                print(f"\n[{i}/{len(grantees)}] {grantee['name']} - ALREADY DONE, skipping")
                skipped += 1
                continue

            # Check for close signal
            if CLOSE_FILE.exists():
                print("\n>>> Close signal received, stopping...")
                CLOSE_FILE.unlink()
                break

            result = await scrape_linkedin_profile(page, grantee, i, len(grantees))

            if result:
                results.append({
                    'grantee': grantee['name'],
                    'handle': grantee['handle'],
                    'posts': result['posts_downloaded'],
                    'followers': result['engagement_metrics']['followers_count'],
                    'status': 'success'
                })
                success += 1
            elif result is None:
                results.append({
                    'grantee': grantee['name'],
                    'handle': grantee['handle'],
                    'status': 'skipped'
                })
                skipped += 1
            else:
                results.append({
                    'grantee': grantee['name'],
                    'handle': grantee['handle'],
                    'status': 'failed'
                })
                failed += 1

            # Longer pause for LinkedIn (they're strict about automation)
            await page.wait_for_timeout(3000)

        # Save summary
        summary = {
            'scraped_at': datetime.now().isoformat(),
            'total_grantees': len(grantees),
            'success': success,
            'failed': failed,
            'skipped': skipped,
            'results': results
        }

        with open(OUTPUT_DIR / "linkedin_batch_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)

        print("\n" + "=" * 60)
        print("LINKEDIN BATCH COMPLETE")
        print("=" * 60)
        print(f"Success: {success}")
        print(f"Skipped: {skipped}")
        print(f"Failed: {failed}")
        print(f"Summary saved to: output/linkedin_batch_summary.json")

        print("\n>>> Browser stays open. Create output/CLOSE_BROWSER to close.")

        while not CLOSE_FILE.exists():
            await asyncio.sleep(2)

        CLOSE_FILE.unlink()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
