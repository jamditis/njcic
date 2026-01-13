#!/usr/bin/env python
"""
Instagram scraper with MANUAL LOGIN.
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

INSTAGRAM_URL = "https://www.instagram.com/centerforcooperativemedia/"
GRANTEE_NAME = "Center_for_Cooperative_Media"
MAX_POSTS = 50
SIGNAL_FILE = Path("output/READY_TO_SCRAPE")


async def scrape_instagram_manual():
    """Open Instagram, let user login, then scrape."""

    print("="*60)
    print("INSTAGRAM MANUAL LOGIN SCRAPER")
    print("="*60)
    print()
    print("INSTRUCTIONS:")
    print("1. Browser opens to Instagram login")
    print("2. Complete login (handle 2FA if needed)")
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

        print(">>> Opening Instagram login page...")
        await page.goto('https://www.instagram.com/accounts/login/', wait_until='domcontentloaded')

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
        cookies_file = Path("output/.cookies/instagram_cookies.json")
        cookies_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cookies_file, 'w') as f:
            json.dump(cookies, f, indent=2)
        print(f"Saved {len(cookies)} cookies")

        # Navigate to profile
        print(f">>> Navigating to profile: {INSTAGRAM_URL}")
        await page.goto(INSTAGRAM_URL, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)

        # Get profile stats
        followers_count = 0
        following_count = 0
        posts_count = 0

        try:
            # Try to get follower count from meta or page
            page_content = await page.content()

            # Look for follower count in various places
            follower_match = re.search(r'"edge_followed_by":\s*\{\s*"count":\s*(\d+)', page_content)
            if follower_match:
                followers_count = int(follower_match.group(1))

            following_match = re.search(r'"edge_follow":\s*\{\s*"count":\s*(\d+)', page_content)
            if following_match:
                following_count = int(following_match.group(1))

            posts_match = re.search(r'"edge_owner_to_timeline_media":\s*\{\s*"count":\s*(\d+)', page_content)
            if posts_match:
                posts_count = int(posts_match.group(1))

            # Fallback: try to get from visible elements
            if followers_count == 0:
                stats = await page.query_selector_all('span._ac2a')
                if len(stats) >= 3:
                    for stat in stats:
                        text = await stat.inner_text()
                        title = await stat.get_attribute('title')
                        if title:
                            text = title
                        # Parse numbers like "1,129" or "1.2K"
                        text = text.replace(',', '')
                        if 'K' in text:
                            num = float(text.replace('K', '')) * 1000
                        elif 'M' in text:
                            num = float(text.replace('M', '')) * 1000000
                        else:
                            try:
                                num = int(text)
                            except:
                                continue

            print(f"Profile stats - Followers: {followers_count}, Following: {following_count}, Posts: {posts_count}")

        except Exception as e:
            print(f"Could not get profile stats: {e}")

        # Scroll and collect posts
        print(">>> Scrolling to load posts...")
        posts = []
        seen_ids = set()
        scroll_attempts = 0
        max_scrolls = 50

        while len(posts) < MAX_POSTS and scroll_attempts < max_scrolls:
            # Find post links
            post_links = await page.query_selector_all('a[href*="/p/"]')

            for link in post_links:
                try:
                    href = await link.get_attribute('href')
                    if not href or '/p/' not in href:
                        continue

                    # Extract shortcode
                    shortcode_match = re.search(r'/p/([^/]+)/', href)
                    if not shortcode_match:
                        continue

                    shortcode = shortcode_match.group(1)
                    if shortcode in seen_ids:
                        continue

                    seen_ids.add(shortcode)

                    # Get image element for potential alt text
                    img = await link.query_selector('img')
                    alt_text = ""
                    if img:
                        alt_text = await img.get_attribute('alt') or ""

                    post_data = {
                        'post_id': shortcode,
                        'shortcode': shortcode,
                        'url': f"https://www.instagram.com/p/{shortcode}/",
                        'caption_preview': alt_text[:200] if alt_text else "",
                        'platform': 'instagram'
                    }
                    posts.append(post_data)
                    print(f"  Post {len(posts)}: {shortcode} - {alt_text[:40]}...")

                except Exception as e:
                    continue

            # Scroll down
            await page.evaluate('window.scrollBy(0, 1000)')
            await page.wait_for_timeout(1500)
            scroll_attempts += 1

            if len(posts) >= MAX_POSTS:
                break

        print(f"\n>>> Collected {len(posts)} posts")

        # Now fetch detailed data for each post
        print(">>> Fetching detailed engagement data for each post...")
        detailed_posts = []

        for i, post in enumerate(posts[:MAX_POSTS]):
            try:
                print(f"  Fetching details for post {i+1}/{min(len(posts), MAX_POSTS)}...")
                await page.goto(post['url'], wait_until='domcontentloaded')
                await page.wait_for_timeout(1500)

                # Get page content for parsing
                content = await page.content()

                # Try to extract likes
                likes = 0
                likes_match = re.search(r'"edge_media_preview_like":\s*\{\s*"count":\s*(\d+)', content)
                if likes_match:
                    likes = int(likes_match.group(1))
                else:
                    # Try visible element
                    likes_el = await page.query_selector('section span span')
                    if likes_el:
                        likes_text = await likes_el.inner_text()
                        likes_text = likes_text.replace(',', '').replace(' likes', '').replace(' like', '')
                        try:
                            likes = int(likes_text)
                        except:
                            pass

                # Try to extract comments count
                comments = 0
                comments_match = re.search(r'"edge_media_to_parent_comment":\s*\{\s*"count":\s*(\d+)', content)
                if comments_match:
                    comments = int(comments_match.group(1))

                # Try to get caption
                caption = ""
                caption_match = re.search(r'"edge_media_to_caption":\s*\{\s*"edges":\s*\[\s*\{\s*"node":\s*\{\s*"text":\s*"([^"]*)"', content)
                if caption_match:
                    caption = caption_match.group(1)

                # Try to get timestamp
                timestamp = ""
                time_match = re.search(r'"taken_at_timestamp":\s*(\d+)', content)
                if time_match:
                    ts = int(time_match.group(1))
                    timestamp = datetime.fromtimestamp(ts).isoformat()

                detailed_post = {
                    **post,
                    'likes': likes,
                    'comments': comments,
                    'caption': caption[:500] if caption else post.get('caption_preview', ''),
                    'timestamp': timestamp,
                    'total_engagement': likes + comments
                }
                detailed_posts.append(detailed_post)
                print(f"    Likes: {likes}, Comments: {comments}")

            except Exception as e:
                print(f"    Error fetching details: {e}")
                detailed_posts.append(post)

        # Save data
        output_dir = Path("output") / GRANTEE_NAME / "instagram" / "centerforcooperativemedia"
        output_dir.mkdir(parents=True, exist_ok=True)

        posts_file = output_dir / "posts_manual.json"
        with open(posts_file, 'w', encoding='utf-8') as f:
            json.dump(detailed_posts, f, indent=2, ensure_ascii=False)
        print(f"\nSaved posts to: {posts_file}")

        # Calculate metrics
        total_likes = sum(p.get('likes', 0) for p in detailed_posts)
        total_comments = sum(p.get('comments', 0) for p in detailed_posts)

        metadata = {
            'url': INSTAGRAM_URL,
            'username': 'centerforcooperativemedia',
            'grantee_name': GRANTEE_NAME,
            'scraped_at': datetime.now().isoformat(),
            'posts_downloaded': len(detailed_posts),
            'engagement_metrics': {
                'followers_count': followers_count,
                'following_count': following_count,
                'posts_count': posts_count,
                'total_likes': total_likes,
                'total_comments': total_comments,
                'avg_likes': round(total_likes / len(detailed_posts), 2) if detailed_posts else 0,
                'avg_comments': round(total_comments / len(detailed_posts), 2) if detailed_posts else 0,
                'posts_analyzed': len(detailed_posts)
            },
            'authenticated': True,
            'platform': 'instagram',
            'method': 'manual_login'
        }

        metadata_file = output_dir / "metadata_manual.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"Saved metadata to: {metadata_file}")

        await page.screenshot(path=str(output_dir / "screenshot_manual.png"))

        print("\n" + "="*60)
        print("INSTAGRAM SCRAPING COMPLETE")
        print("="*60)
        print(f"Posts collected: {len(detailed_posts)}")
        print(f"Followers: {followers_count:,}")
        print(f"Total likes: {total_likes:,}")
        print(f"Total comments: {total_comments:,}")

        print("\n>>> Browser will close in 10 seconds...")
        await asyncio.sleep(10)
        await browser.close()

        return {
            'success': len(detailed_posts) > 0,
            'posts_downloaded': len(detailed_posts),
            'engagement_metrics': metadata['engagement_metrics']
        }


if __name__ == "__main__":
    result = asyncio.run(scrape_instagram_manual())
    print(f"\nFinal result: {result}")
