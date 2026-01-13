#!/usr/bin/env python
"""
Facebook batch scraper - scrapes ALL grantees in one session.
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
MAX_POSTS = 30


def get_facebook_grantees():
    """Load all grantees with Facebook accounts."""
    grantees = []

    for json_file in GRANTEES_DIR.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            fb_url = data.get('social', {}).get('facebook')
            if fb_url:
                # Extract page name/id from URL
                match = re.search(r'facebook\.com/([^/?]+)', fb_url)
                if match:
                    page_id = match.group(1).rstrip('/')
                    if page_id not in ['profile.php', 'pages', 'groups']:
                        grantees.append({
                            'name': data.get('name', json_file.stem),
                            'slug': data.get('slug', json_file.stem),
                            'page_id': page_id,
                            'url': fb_url
                        })
        except Exception as e:
            print(f"Warning: Could not load {json_file}: {e}")

    return sorted(grantees, key=lambda x: x['name'])


async def scrape_facebook_profile(page, grantee, grantee_num, total):
    """Scrape a single Facebook page."""
    print(f"\n[{grantee_num}/{total}] {grantee['name']} ({grantee['page_id']})")
    print("-" * 50, flush=True)

    url = f"https://www.facebook.com/{grantee['page_id']}"

    try:
        await page.goto(url, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)

        # Check if page exists
        page_text = await page.inner_text('body')
        if "This page isn't available" in page_text or "This content isn't available" in page_text:
            print(f"  SKIP: Page not available")
            return None

        # Try to get follower/like counts from page
        followers = 0
        likes = 0

        # Look for follower count patterns
        follower_match = re.search(r'([\d,\.]+[KMB]?)\s*(?:followers|people follow)', page_text, re.IGNORECASE)
        if follower_match:
            num_str = follower_match.group(1).replace(',', '')
            if 'K' in num_str:
                followers = int(float(num_str.replace('K', '')) * 1000)
            elif 'M' in num_str:
                followers = int(float(num_str.replace('M', '')) * 1000000)
            else:
                try:
                    followers = int(num_str)
                except:
                    pass

        likes_match = re.search(r'([\d,\.]+[KMB]?)\s*(?:likes|people like)', page_text, re.IGNORECASE)
        if likes_match:
            num_str = likes_match.group(1).replace(',', '')
            if 'K' in num_str:
                likes = int(float(num_str.replace('K', '')) * 1000)
            elif 'M' in num_str:
                likes = int(float(num_str.replace('M', '')) * 1000000)
            else:
                try:
                    likes = int(num_str)
                except:
                    pass

        print(f"  Followers: {followers:,} | Likes: {likes:,}")

        # Scroll to load posts
        posts = []
        seen_urls = set()
        scroll_attempts = 0
        no_new_count = 0

        while len(posts) < MAX_POSTS and scroll_attempts < 15:
            prev_count = len(posts)

            # Find post links - Facebook uses various patterns
            post_links = await page.query_selector_all('a[href*="/posts/"], a[href*="/photos/"], a[href*="/videos/"]')

            for link in post_links:
                try:
                    href = await link.get_attribute('href')
                    if not href:
                        continue

                    # Clean URL
                    if '?' in href:
                        href = href.split('?')[0]

                    if href in seen_urls:
                        continue
                    seen_urls.add(href)

                    # Extract post ID
                    post_id_match = re.search(r'/(?:posts|photos|videos)/([^/]+)', href)
                    if not post_id_match:
                        continue

                    post_id = post_id_match.group(1)

                    posts.append({
                        'post_id': post_id,
                        'url': href if href.startswith('http') else f"https://www.facebook.com{href}",
                        'platform': 'facebook'
                    })

                except Exception:
                    continue

            if len(posts) == prev_count:
                no_new_count += 1
                if no_new_count >= 3:
                    break
            else:
                no_new_count = 0

            await page.evaluate('window.scrollBy(0, 1500)')
            await page.wait_for_timeout(2000)
            scroll_attempts += 1

        print(f"  Found {len(posts)} posts")

        if not posts:
            # Still save metadata even with no posts
            grantee_safe = re.sub(r'[^\w\-]', '_', grantee['name'].replace(' ', '_'))
            output_dir = OUTPUT_DIR / grantee_safe / "facebook" / grantee['page_id']
            output_dir.mkdir(parents=True, exist_ok=True)

            metadata = {
                'url': grantee['url'],
                'page_id': grantee['page_id'],
                'grantee_name': grantee['name'],
                'scraped_at': datetime.now().isoformat(),
                'posts_downloaded': 0,
                'engagement_metrics': {
                    'followers_count': followers,
                    'likes_count': likes,
                },
                'platform': 'facebook',
                'method': 'batch_scrape'
            }

            with open(output_dir / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)

            return metadata

        # Save data
        grantee_safe = re.sub(r'[^\w\-]', '_', grantee['name'].replace(' ', '_'))
        output_dir = OUTPUT_DIR / grantee_safe / "facebook" / grantee['page_id']
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_dir / "posts.json", 'w', encoding='utf-8') as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)

        metadata = {
            'url': grantee['url'],
            'page_id': grantee['page_id'],
            'grantee_name': grantee['name'],
            'scraped_at': datetime.now().isoformat(),
            'posts_downloaded': len(posts),
            'engagement_metrics': {
                'followers_count': followers,
                'likes_count': likes,
            },
            'platform': 'facebook',
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
    print("FACEBOOK BATCH SCRAPER")
    print("=" * 60)

    grantees = get_facebook_grantees()
    print(f"\nFound {len(grantees)} grantees with Facebook pages")

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

        # Go to Facebook login
        print("\n>>> Opening Facebook login...")
        await page.goto('https://www.facebook.com/login', wait_until='domcontentloaded')

        print()
        print("=" * 60)
        print("LOG IN TO FACEBOOK")
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
        with open(cookies_dir / "facebook_cookies.json", 'w') as f:
            json.dump(cookies, f, indent=2)

        # Check which grantees already have data (to skip)
        already_done = set()
        for grantee in grantees:
            grantee_safe = re.sub(r'[^\w\-]', '_', grantee['name'].replace(' ', '_'))
            metadata_file = OUTPUT_DIR / grantee_safe / "facebook" / grantee['page_id'] / "metadata.json"
            if metadata_file.exists():
                already_done.add(grantee['page_id'])

        if already_done:
            print(f"\n>>> Skipping {len(already_done)} already-scraped grantees")

        # Scrape all grantees
        results = []
        success = 0
        failed = 0
        skipped = 0

        for i, grantee in enumerate(grantees, 1):
            # Skip if already done
            if grantee['page_id'] in already_done:
                print(f"\n[{i}/{len(grantees)}] {grantee['name']} - ALREADY DONE, skipping")
                skipped += 1
                continue

            # Check for close signal
            if CLOSE_FILE.exists():
                print("\n>>> Close signal received, stopping...")
                CLOSE_FILE.unlink()
                break

            result = await scrape_facebook_profile(page, grantee, i, len(grantees))

            if result:
                results.append({
                    'grantee': grantee['name'],
                    'page_id': grantee['page_id'],
                    'posts': result['posts_downloaded'],
                    'followers': result['engagement_metrics']['followers_count'],
                    'status': 'success'
                })
                success += 1
            elif result is None:
                results.append({
                    'grantee': grantee['name'],
                    'page_id': grantee['page_id'],
                    'status': 'skipped'
                })
                skipped += 1
            else:
                results.append({
                    'grantee': grantee['name'],
                    'page_id': grantee['page_id'],
                    'status': 'failed'
                })
                failed += 1

            # Pause between grantees
            await page.wait_for_timeout(2500)

        # Save summary
        summary = {
            'scraped_at': datetime.now().isoformat(),
            'total_grantees': len(grantees),
            'success': success,
            'failed': failed,
            'skipped': skipped,
            'results': results
        }

        with open(OUTPUT_DIR / "facebook_batch_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)

        print("\n" + "=" * 60)
        print("FACEBOOK BATCH COMPLETE")
        print("=" * 60)
        print(f"Success: {success}")
        print(f"Skipped: {skipped}")
        print(f"Failed: {failed}")
        print(f"Summary saved to: output/facebook_batch_summary.json")

        print("\n>>> Browser stays open. Create output/CLOSE_BROWSER to close.")

        while not CLOSE_FILE.exists():
            await asyncio.sleep(2)

        CLOSE_FILE.unlink()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
