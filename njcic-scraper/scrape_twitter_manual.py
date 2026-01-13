#!/usr/bin/env python
"""
Twitter scraper with MANUAL LOGIN SUPPORT.
Opens a browser, waits for you to complete login, then scrapes.
"""

import sys
import os
import json
import asyncio
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

TWITTER_URL = "https://twitter.com/centercoopmedia"
GRANTEE_NAME = "Center_for_Cooperative_Media"
MAX_POSTS = 50


async def scrape_twitter_manual():
    """Open Twitter, let user login, then scrape."""

    print("="*60)
    print("TWITTER MANUAL LOGIN SCRAPER")
    print("="*60)
    print()

    async with async_playwright() as p:
        # Launch VISIBLE browser
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

        # Apply stealth
        stealth = Stealth()
        await stealth.apply_stealth_async(page)

        # Go to Twitter login
        print(">>> Opening Twitter login page...")
        print(">>> Please complete the login process in the browser window.")
        print()
        await page.goto('https://x.com/i/flow/login', wait_until='domcontentloaded')

        # WAIT FOR USER
        print("="*60)
        input(">>> PRESS ENTER AFTER YOU'VE LOGGED IN SUCCESSFULLY... ")
        print("="*60)
        print()

        # Save cookies for future use
        cookies = await context.cookies()
        cookies_file = Path("output/.cookies/twitter_cookies.json")
        cookies_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cookies_file, 'w') as f:
            json.dump(cookies, f, indent=2)
        print(f"Saved {len(cookies)} cookies for future use")

        # Now navigate to the profile
        print(f">>> Navigating to profile: {TWITTER_URL}")
        await page.goto(f"https://x.com/centercoopmedia", wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)

        # Get follower count
        followers_count = 0
        try:
            followers_elements = await page.query_selector_all('[data-testid="UserDescription"]')
            page_text = await page.inner_text('body')
            import re
            follower_match = re.search(r'([\d,]+)\s*Followers?', page_text)
            if follower_match:
                followers_count = int(follower_match.group(1).replace(',', ''))
                print(f"Followers: {followers_count:,}")
        except Exception as e:
            print(f"Could not get follower count: {e}")

        # Scroll and collect tweets
        print(">>> Scrolling to load tweets...")
        tweets = []
        seen_ids = set()
        scroll_attempts = 0
        max_scrolls = 30

        while len(tweets) < MAX_POSTS and scroll_attempts < max_scrolls:
            # Extract tweets
            tweet_elements = await page.query_selector_all('article[data-testid="tweet"]')

            for tweet_el in tweet_elements:
                try:
                    # Get tweet text
                    text_el = await tweet_el.query_selector('[data-testid="tweetText"]')
                    text = await text_el.inner_text() if text_el else ""

                    # Get link/ID
                    link_el = await tweet_el.query_selector('a[href*="/status/"]')
                    tweet_url = ""
                    tweet_id = ""
                    if link_el:
                        tweet_url = await link_el.get_attribute('href')
                        if '/status/' in tweet_url:
                            tweet_id = tweet_url.split('/status/')[-1].split('/')[0].split('?')[0]

                    if tweet_id and tweet_id not in seen_ids:
                        seen_ids.add(tweet_id)

                        # Get metrics
                        likes = 0
                        retweets = 0
                        replies = 0
                        views = 0

                        # Try to get metrics from aria-labels
                        buttons = await tweet_el.query_selector_all('[role="button"]')
                        for btn in buttons:
                            label = await btn.get_attribute('aria-label') or ""
                            label_lower = label.lower()

                            if 'like' in label_lower:
                                match = re.search(r'(\d+)', label)
                                if match:
                                    likes = int(match.group(1))
                            elif 'repost' in label_lower or 'retweet' in label_lower:
                                match = re.search(r'(\d+)', label)
                                if match:
                                    retweets = int(match.group(1))
                            elif 'repl' in label_lower:
                                match = re.search(r'(\d+)', label)
                                if match:
                                    replies = int(match.group(1))

                        # Try to get view count
                        analytics = await tweet_el.query_selector('[data-testid="analytics"]')
                        if analytics:
                            analytics_text = await analytics.inner_text()
                            view_match = re.search(r'([\d,.KMB]+)', analytics_text)
                            if view_match:
                                view_str = view_match.group(1).replace(',', '')
                                if 'K' in view_str:
                                    views = int(float(view_str.replace('K', '')) * 1000)
                                elif 'M' in view_str:
                                    views = int(float(view_str.replace('M', '')) * 1000000)
                                else:
                                    views = int(float(view_str))

                        tweet_data = {
                            'post_id': tweet_id,
                            'text': text[:500],
                            'url': f"https://x.com/centercoopmedia/status/{tweet_id}",
                            'likes': likes,
                            'retweets': retweets,
                            'replies': replies,
                            'views': views,
                            'total_engagement': likes + retweets + replies,
                            'platform': 'twitter'
                        }
                        tweets.append(tweet_data)
                        print(f"  Tweet {len(tweets)}: {text[:50]}... | Likes: {likes}")

                except Exception as e:
                    continue

            # Scroll down
            await page.evaluate('window.scrollBy(0, 1000)')
            await page.wait_for_timeout(1500)
            scroll_attempts += 1

            if len(tweets) >= MAX_POSTS:
                break

        print(f"\n>>> Collected {len(tweets)} tweets")

        # Save data
        output_dir = Path("output") / GRANTEE_NAME / "twitter" / "centercoopmedia"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save posts
        posts_file = output_dir / "posts.json"
        with open(posts_file, 'w', encoding='utf-8') as f:
            json.dump(tweets, f, indent=2, ensure_ascii=False)
        print(f"Saved posts to: {posts_file}")

        # Calculate metrics
        total_likes = sum(t['likes'] for t in tweets)
        total_retweets = sum(t['retweets'] for t in tweets)
        total_replies = sum(t['replies'] for t in tweets)
        total_views = sum(t['views'] for t in tweets)

        # Save metadata
        metadata = {
            'url': TWITTER_URL,
            'username': 'centercoopmedia',
            'grantee_name': GRANTEE_NAME,
            'scraped_at': datetime.now().isoformat(),
            'posts_downloaded': len(tweets),
            'engagement_metrics': {
                'followers_count': followers_count,
                'total_likes': total_likes,
                'total_retweets': total_retweets,
                'total_replies': total_replies,
                'total_views': total_views,
                'avg_likes': round(total_likes / len(tweets), 2) if tweets else 0,
                'avg_engagement': round((total_likes + total_retweets + total_replies) / len(tweets), 2) if tweets else 0,
                'posts_analyzed': len(tweets)
            },
            'authenticated': True,
            'platform': 'twitter'
        }

        metadata_file = output_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"Saved metadata to: {metadata_file}")

        # Take screenshot
        screenshot_file = output_dir / "screenshot.png"
        await page.screenshot(path=str(screenshot_file))
        print(f"Saved screenshot to: {screenshot_file}")

        print("\n" + "="*60)
        print("TWITTER SCRAPING COMPLETE")
        print("="*60)
        print(f"Posts collected: {len(tweets)}")
        print(f"Followers: {followers_count:,}")
        print(f"Total likes: {total_likes:,}")
        print(f"Total retweets: {total_retweets:,}")
        print(f"Total views: {total_views:,}")

        input("\n>>> Press ENTER to close browser...")
        await browser.close()

        return {
            'success': len(tweets) > 0,
            'posts_downloaded': len(tweets),
            'engagement_metrics': metadata['engagement_metrics']
        }


if __name__ == "__main__":
    result = asyncio.run(scrape_twitter_manual())
    print(f"\nResult: {result}")
