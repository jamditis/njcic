#!/usr/bin/env python
"""
Twitter batch scraper - scrapes ALL grantees in one session.
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
MAX_POSTS = 50


def get_twitter_grantees():
    """Load all grantees with Twitter accounts."""
    grantees = []

    for json_file in GRANTEES_DIR.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            twitter_url = data.get('social', {}).get('twitter')
            if twitter_url:
                # Extract handle from URL
                match = re.search(r'(?:twitter\.com|x\.com)/([^/?\s]+)', twitter_url)
                if match:
                    handle = match.group(1)
                    grantees.append({
                        'name': data.get('name', json_file.stem),
                        'slug': data.get('slug', json_file.stem),
                        'handle': handle,
                        'url': twitter_url
                    })
        except Exception as e:
            print(f"Warning: Could not load {json_file}: {e}")

    return sorted(grantees, key=lambda x: x['name'])


async def scrape_twitter_profile(page, grantee, grantee_num, total):
    """Scrape a single Twitter profile."""
    print(f"\n[{grantee_num}/{total}] {grantee['name']} (@{grantee['handle']})")

    url = f"https://x.com/{grantee['handle']}"

    try:
        await page.goto(url, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)

        # Check if account exists
        page_text = await page.inner_text('body')
        if "This account doesn't exist" in page_text or "Account suspended" in page_text:
            print(f"  SKIP: Account doesn't exist or is suspended")
            return None

        # Get follower count
        followers = 0
        try:
            followers_match = re.search(r'([\d,]+)\s*Followers', page_text)
            if followers_match:
                followers = int(followers_match.group(1).replace(',', ''))
        except:
            pass

        print(f"  Followers: {followers:,}")

        # Scroll and collect tweets
        posts = []
        seen_ids = set()
        scroll_attempts = 0
        no_new_count = 0

        while len(posts) < MAX_POSTS and scroll_attempts < 30:
            prev_count = len(posts)

            tweets = await page.query_selector_all('article[data-testid="tweet"]')

            for tweet in tweets:
                try:
                    # Get tweet link for ID
                    link = await tweet.query_selector('a[href*="/status/"]')
                    if not link:
                        continue
                    href = await link.get_attribute('href')
                    tweet_id_match = re.search(r'/status/(\d+)', href)
                    if not tweet_id_match:
                        continue
                    tweet_id = tweet_id_match.group(1)

                    if tweet_id in seen_ids:
                        continue
                    seen_ids.add(tweet_id)

                    # Get text
                    text_el = await tweet.query_selector('[data-testid="tweetText"]')
                    text = await text_el.inner_text() if text_el else ""

                    # Get metrics from aria-labels
                    likes = retweets = replies = views = 0

                    # Likes
                    like_el = await tweet.query_selector('[data-testid="like"] [aria-label]')
                    if like_el:
                        aria = await like_el.get_attribute('aria-label')
                        if aria:
                            num = re.search(r'(\d+)', aria.replace(',', ''))
                            if num:
                                likes = int(num.group(1))

                    # Retweets
                    rt_el = await tweet.query_selector('[data-testid="retweet"] [aria-label]')
                    if rt_el:
                        aria = await rt_el.get_attribute('aria-label')
                        if aria:
                            num = re.search(r'(\d+)', aria.replace(',', ''))
                            if num:
                                retweets = int(num.group(1))

                    # Replies
                    reply_el = await tweet.query_selector('[data-testid="reply"] [aria-label]')
                    if reply_el:
                        aria = await reply_el.get_attribute('aria-label')
                        if aria:
                            num = re.search(r'(\d+)', aria.replace(',', ''))
                            if num:
                                replies = int(num.group(1))

                    posts.append({
                        'post_id': tweet_id,
                        'url': f"https://x.com/{grantee['handle']}/status/{tweet_id}",
                        'text': text[:500],
                        'likes': likes,
                        'retweets': retweets,
                        'replies': replies,
                        'total_engagement': likes + retweets + replies,
                        'platform': 'twitter'
                    })

                except Exception as e:
                    continue

            if len(posts) == prev_count:
                no_new_count += 1
                if no_new_count >= 5:
                    break
            else:
                no_new_count = 0

            await page.evaluate('window.scrollBy(0, 1500)')
            await page.wait_for_timeout(1500)
            scroll_attempts += 1

        print(f"  Posts: {len(posts)}")

        if not posts:
            return None

        # Calculate totals
        total_likes = sum(p['likes'] for p in posts)
        total_rts = sum(p['retweets'] for p in posts)
        total_replies = sum(p['replies'] for p in posts)

        print(f"  Engagement: {total_likes} likes, {total_rts} RTs, {total_replies} replies")

        # Save data
        grantee_safe = re.sub(r'[^\w\-]', '_', grantee['name'].replace(' ', '_'))
        output_dir = OUTPUT_DIR / grantee_safe / "twitter" / grantee['handle']
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_dir / "posts.json", 'w', encoding='utf-8') as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)

        metadata = {
            'url': grantee['url'],
            'handle': grantee['handle'],
            'grantee_name': grantee['name'],
            'scraped_at': datetime.now().isoformat(),
            'posts_downloaded': len(posts),
            'engagement_metrics': {
                'followers_count': followers,
                'total_likes': total_likes,
                'total_retweets': total_rts,
                'total_replies': total_replies,
                'avg_engagement': round((total_likes + total_rts + total_replies) / len(posts), 2) if posts else 0
            },
            'platform': 'twitter',
            'method': 'batch_scrape'
        }

        with open(output_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)

        return metadata

    except Exception as e:
        print(f"  ERROR: {e}")
        return None


async def main():
    print("="*60)
    print("TWITTER BATCH SCRAPER")
    print("="*60)

    grantees = get_twitter_grantees()
    print(f"\nFound {len(grantees)} grantees with Twitter accounts")

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

        # Go to Twitter login
        print("\n>>> Opening Twitter login...")
        await page.goto('https://x.com/login', wait_until='domcontentloaded')

        print()
        print("="*60)
        print("LOG IN TO TWITTER")
        print("Then create signal file: touch output/READY_TO_SCRAPE")
        print("="*60)

        # Wait for login signal
        while not SIGNAL_FILE.exists():
            await asyncio.sleep(2)

        print("\n>>> Signal received! Starting batch scrape...")
        SIGNAL_FILE.unlink()

        # Save cookies
        cookies = await context.cookies()
        cookies_dir = OUTPUT_DIR / ".cookies"
        cookies_dir.mkdir(parents=True, exist_ok=True)
        with open(cookies_dir / "twitter_cookies.json", 'w') as f:
            json.dump(cookies, f, indent=2)

        # Check which grantees already have data (to skip)
        already_done = set()
        for grantee in grantees:
            grantee_safe = re.sub(r'[^\w\-]', '_', grantee['name'].replace(' ', '_'))
            metadata_file = OUTPUT_DIR / grantee_safe / "twitter" / grantee['handle'] / "metadata.json"
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

            result = await scrape_twitter_profile(page, grantee, i, len(grantees))

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

            # Brief pause between grantees
            await page.wait_for_timeout(2000)

        # Save summary
        summary = {
            'scraped_at': datetime.now().isoformat(),
            'total_grantees': len(grantees),
            'success': success,
            'failed': failed,
            'skipped': skipped,
            'results': results
        }

        with open(OUTPUT_DIR / "twitter_batch_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)

        print("\n" + "="*60)
        print("TWITTER BATCH COMPLETE")
        print("="*60)
        print(f"Success: {success}")
        print(f"Skipped: {skipped}")
        print(f"Failed: {failed}")
        print(f"Summary saved to: output/twitter_batch_summary.json")

        print("\n>>> Browser stays open. Create output/CLOSE_BROWSER to close.")

        while not CLOSE_FILE.exists():
            await asyncio.sleep(2)

        CLOSE_FILE.unlink()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
