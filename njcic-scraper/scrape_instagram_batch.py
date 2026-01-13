#!/usr/bin/env python
"""
Instagram batch scraper - scrapes ALL grantees in one session.
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


def get_instagram_grantees():
    """Load all grantees with Instagram accounts."""
    grantees = []

    for json_file in GRANTEES_DIR.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            ig_url = data.get('social', {}).get('instagram')
            if ig_url:
                # Extract username from URL
                match = re.search(r'instagram\.com/([^/?]+)', ig_url)
                if match:
                    username = match.group(1).rstrip('/')
                    if username not in ['p', 'reel', 'stories']:  # Skip if it's a post URL
                        grantees.append({
                            'name': data.get('name', json_file.stem),
                            'slug': data.get('slug', json_file.stem),
                            'username': username,
                            'url': ig_url
                        })
        except Exception as e:
            print(f"Warning: Could not load {json_file}: {e}")

    return sorted(grantees, key=lambda x: x['name'])


async def scrape_instagram_profile(page, grantee, grantee_num, total):
    """Scrape a single Instagram profile."""
    print(f"\n[{grantee_num}/{total}] {grantee['name']} (@{grantee['username']})")
    print("-" * 50, flush=True)

    url = f"https://www.instagram.com/{grantee['username']}/"

    try:
        await page.goto(url, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)

        # Check if account exists
        page_text = await page.inner_text('body')
        if "Sorry, this page isn't available" in page_text:
            print(f"  SKIP: Page not available")
            return None

        # Get profile stats from page content
        content = await page.content()
        followers = 0
        following = 0
        posts_count = 0

        # Try JSON data extraction
        follower_match = re.search(r'"edge_followed_by":\s*\{\s*"count":\s*(\d+)', content)
        if follower_match:
            followers = int(follower_match.group(1))

        following_match = re.search(r'"edge_follow":\s*\{\s*"count":\s*(\d+)', content)
        if following_match:
            following = int(following_match.group(1))

        posts_match = re.search(r'"edge_owner_to_timeline_media":\s*\{\s*"count":\s*(\d+)', content)
        if posts_match:
            posts_count = int(posts_match.group(1))

        print(f"  Followers: {followers:,} | Posts: {posts_count}")

        # Collect post shortcodes by scrolling
        posts = []
        seen_ids = set()
        scroll_attempts = 0
        no_new_count = 0

        while len(posts) < MAX_POSTS and scroll_attempts < 20:
            prev_count = len(posts)

            # Find post links
            post_links = await page.query_selector_all('a[href*="/p/"]')

            for link in post_links:
                try:
                    href = await link.get_attribute('href')
                    if not href or '/p/' not in href:
                        continue

                    shortcode_match = re.search(r'/p/([^/]+)/', href)
                    if not shortcode_match:
                        continue

                    shortcode = shortcode_match.group(1)
                    if shortcode in seen_ids:
                        continue
                    seen_ids.add(shortcode)

                    # Get image alt text
                    img = await link.query_selector('img')
                    alt_text = ""
                    if img:
                        alt_text = await img.get_attribute('alt') or ""

                    posts.append({
                        'post_id': shortcode,
                        'shortcode': shortcode,
                        'url': f"https://www.instagram.com/p/{shortcode}/",
                        'caption_preview': alt_text[:200],
                        'platform': 'instagram'
                    })

                except Exception:
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

        if not posts:
            return None

        # Fetch engagement for first few posts (Instagram is aggressive with rate limits)
        max_detail = min(10, len(posts))
        print(f"  Fetching engagement for {max_detail} posts...")

        for i, post in enumerate(posts[:max_detail]):
            try:
                await page.goto(post['url'], wait_until='domcontentloaded')
                await page.wait_for_timeout(2000)

                post_content = await page.content()

                # Extract likes
                likes = 0
                likes_match = re.search(r'"edge_media_preview_like":\s*\{\s*"count":\s*(\d+)', post_content)
                if likes_match:
                    likes = int(likes_match.group(1))

                # Extract comments
                comments = 0
                comments_match = re.search(r'"edge_media_to_parent_comment":\s*\{\s*"count":\s*(\d+)', post_content)
                if comments_match:
                    comments = int(comments_match.group(1))

                post['likes'] = likes
                post['comments'] = comments
                post['total_engagement'] = likes + comments

            except Exception:
                post['likes'] = 0
                post['comments'] = 0
                post['total_engagement'] = 0

        # Calculate totals
        total_likes = sum(p.get('likes', 0) for p in posts)
        total_comments = sum(p.get('comments', 0) for p in posts)

        print(f"  Engagement: {total_likes} likes, {total_comments} comments")

        # Save data
        grantee_safe = re.sub(r'[^\w\-]', '_', grantee['name'].replace(' ', '_'))
        output_dir = OUTPUT_DIR / grantee_safe / "instagram" / grantee['username']
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_dir / "posts.json", 'w', encoding='utf-8') as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)

        metadata = {
            'url': grantee['url'],
            'username': grantee['username'],
            'grantee_name': grantee['name'],
            'scraped_at': datetime.now().isoformat(),
            'posts_downloaded': len(posts),
            'engagement_metrics': {
                'followers_count': followers,
                'following_count': following,
                'posts_count': posts_count,
                'total_likes': total_likes,
                'total_comments': total_comments,
                'avg_engagement': round((total_likes + total_comments) / max_detail, 2) if max_detail > 0 else 0
            },
            'platform': 'instagram',
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
    print("INSTAGRAM BATCH SCRAPER")
    print("=" * 60)

    grantees = get_instagram_grantees()
    print(f"\nFound {len(grantees)} grantees with Instagram accounts")

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

        # Go to Instagram login
        print("\n>>> Opening Instagram login...")
        await page.goto('https://www.instagram.com/accounts/login/', wait_until='domcontentloaded')

        print()
        print("=" * 60)
        print("LOG IN TO INSTAGRAM")
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
        with open(cookies_dir / "instagram_cookies.json", 'w') as f:
            json.dump(cookies, f, indent=2)

        # Check which grantees already have data (to skip)
        already_done = set()
        for grantee in grantees:
            grantee_safe = re.sub(r'[^\w\-]', '_', grantee['name'].replace(' ', '_'))
            metadata_file = OUTPUT_DIR / grantee_safe / "instagram" / grantee['username'] / "metadata.json"
            if metadata_file.exists():
                already_done.add(grantee['username'])

        if already_done:
            print(f"\n>>> Skipping {len(already_done)} already-scraped grantees")

        # Scrape all grantees
        results = []
        success = 0
        failed = 0
        skipped = 0

        for i, grantee in enumerate(grantees, 1):
            # Skip if already done
            if grantee['username'] in already_done:
                print(f"\n[{i}/{len(grantees)}] {grantee['name']} - ALREADY DONE, skipping")
                skipped += 1
                continue

            # Check for close signal
            if CLOSE_FILE.exists():
                print("\n>>> Close signal received, stopping...")
                CLOSE_FILE.unlink()
                break

            result = await scrape_instagram_profile(page, grantee, i, len(grantees))

            if result:
                results.append({
                    'grantee': grantee['name'],
                    'username': grantee['username'],
                    'posts': result['posts_downloaded'],
                    'followers': result['engagement_metrics']['followers_count'],
                    'status': 'success'
                })
                success += 1
            elif result is None:
                results.append({
                    'grantee': grantee['name'],
                    'username': grantee['username'],
                    'status': 'skipped'
                })
                skipped += 1
            else:
                results.append({
                    'grantee': grantee['name'],
                    'username': grantee['username'],
                    'status': 'failed'
                })
                failed += 1

            # Longer pause between grantees (Instagram is stricter)
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

        with open(OUTPUT_DIR / "instagram_batch_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)

        print("\n" + "=" * 60)
        print("INSTAGRAM BATCH COMPLETE")
        print("=" * 60)
        print(f"Success: {success}")
        print(f"Skipped: {skipped}")
        print(f"Failed: {failed}")
        print(f"Summary saved to: output/instagram_batch_summary.json")

        print("\n>>> Browser stays open. Create output/CLOSE_BROWSER to close.")

        while not CLOSE_FILE.exists():
            await asyncio.sleep(2)

        CLOSE_FILE.unlink()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
