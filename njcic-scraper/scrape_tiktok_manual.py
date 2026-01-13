#!/usr/bin/env python
"""
TikTok scraper with MANUAL LOGIN.
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

TIKTOK_URL = "https://www.tiktok.com/@centercooperativemedia"
GRANTEE_NAME = "Center_for_Cooperative_Media"
MAX_POSTS = 50
SIGNAL_FILE = Path("output/READY_TO_SCRAPE")


async def scrape_tiktok_manual():
    """Open TikTok, let user login, then scrape."""

    print("="*60)
    print("TIKTOK MANUAL LOGIN SCRAPER")
    print("="*60)
    print()
    print("INSTRUCTIONS:")
    print("1. Browser opens to TikTok login")
    print("2. Complete login (handle captcha if needed)")
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

        print(">>> Opening TikTok login page...")
        await page.goto('https://www.tiktok.com/login', wait_until='domcontentloaded')

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
        cookies_file = Path("output/.cookies/tiktok_cookies.json")
        cookies_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cookies_file, 'w') as f:
            json.dump(cookies, f, indent=2)
        print(f"Saved {len(cookies)} cookies")

        # Navigate to profile
        print(f">>> Navigating to profile: {TIKTOK_URL}")
        await page.goto(TIKTOK_URL, wait_until='domcontentloaded')
        await page.wait_for_timeout(5000)

        # Get profile stats
        followers_count = 0
        following_count = 0
        likes_count = 0

        try:
            # Look for stats on page
            stats_elements = await page.query_selector_all('[data-e2e="followers-count"], [data-e2e="following-count"], [data-e2e="likes-count"]')

            # Try different selectors
            page_text = await page.inner_text('body')

            # Parse follower count
            follower_patterns = [
                r'(\d+(?:\.\d+)?[KMB]?)\s*Followers',
                r'Followers[:\s]*(\d+(?:\.\d+)?[KMB]?)',
            ]
            for pattern in follower_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    val = match.group(1)
                    val = val.replace(',', '')
                    if 'K' in val.upper():
                        followers_count = int(float(val.upper().replace('K', '')) * 1000)
                    elif 'M' in val.upper():
                        followers_count = int(float(val.upper().replace('M', '')) * 1000000)
                    else:
                        followers_count = int(float(val))
                    break

            # Parse following count
            following_patterns = [
                r'(\d+(?:\.\d+)?[KMB]?)\s*Following',
                r'Following[:\s]*(\d+(?:\.\d+)?[KMB]?)',
            ]
            for pattern in following_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    val = match.group(1)
                    val = val.replace(',', '')
                    if 'K' in val.upper():
                        following_count = int(float(val.upper().replace('K', '')) * 1000)
                    elif 'M' in val.upper():
                        following_count = int(float(val.upper().replace('M', '')) * 1000000)
                    else:
                        following_count = int(float(val))
                    break

            # Parse likes count
            likes_patterns = [
                r'(\d+(?:\.\d+)?[KMB]?)\s*Likes',
                r'Likes[:\s]*(\d+(?:\.\d+)?[KMB]?)',
            ]
            for pattern in likes_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    val = match.group(1)
                    val = val.replace(',', '')
                    if 'K' in val.upper():
                        likes_count = int(float(val.upper().replace('K', '')) * 1000)
                    elif 'M' in val.upper():
                        likes_count = int(float(val.upper().replace('M', '')) * 1000000)
                    else:
                        likes_count = int(float(val))
                    break

            print(f"Profile stats - Followers: {followers_count}, Following: {following_count}, Likes: {likes_count}")

        except Exception as e:
            print(f"Could not get profile stats: {e}")

        # Scroll and collect videos
        print(">>> Scrolling to load videos...")
        videos = []
        seen_ids = set()
        scroll_attempts = 0
        max_scrolls = 50

        while len(videos) < MAX_POSTS and scroll_attempts < max_scrolls:
            # Find video links
            video_links = await page.query_selector_all('a[href*="/video/"]')

            for link in video_links:
                try:
                    href = await link.get_attribute('href')
                    if not href or '/video/' not in href:
                        continue

                    # Extract video ID
                    video_match = re.search(r'/video/(\d+)', href)
                    if not video_match:
                        continue

                    video_id = video_match.group(1)
                    if video_id in seen_ids:
                        continue

                    seen_ids.add(video_id)

                    video_data = {
                        'post_id': video_id,
                        'video_id': video_id,
                        'url': f"https://www.tiktok.com/@centercooperativemedia/video/{video_id}",
                        'platform': 'tiktok'
                    }
                    videos.append(video_data)
                    print(f"  Video {len(videos)}: {video_id}")

                except Exception as e:
                    continue

            # Scroll down
            await page.evaluate('window.scrollBy(0, 1000)')
            await page.wait_for_timeout(1500)
            scroll_attempts += 1

            if len(videos) >= MAX_POSTS:
                break

        print(f"\n>>> Collected {len(videos)} videos")

        # Fetch detailed data for each video
        print(">>> Fetching detailed engagement data for each video...")
        detailed_videos = []

        for i, video in enumerate(videos[:MAX_POSTS]):
            try:
                print(f"  Fetching details for video {i+1}/{min(len(videos), MAX_POSTS)}...")
                await page.goto(video['url'], wait_until='domcontentloaded')
                await page.wait_for_timeout(2000)

                page_text = await page.inner_text('body')

                # Try to extract likes
                likes = 0
                likes_match = re.search(r'(\d+(?:\.\d+)?[KMB]?)\s*(?:likes?|Likes?)', page_text)
                if likes_match:
                    val = likes_match.group(1).replace(',', '')
                    if 'K' in val.upper():
                        likes = int(float(val.upper().replace('K', '')) * 1000)
                    elif 'M' in val.upper():
                        likes = int(float(val.upper().replace('M', '')) * 1000000)
                    else:
                        try:
                            likes = int(float(val))
                        except:
                            pass

                # Try to extract comments
                comments = 0
                comments_match = re.search(r'(\d+(?:\.\d+)?[KMB]?)\s*(?:comments?|Comments?)', page_text)
                if comments_match:
                    val = comments_match.group(1).replace(',', '')
                    if 'K' in val.upper():
                        comments = int(float(val.upper().replace('K', '')) * 1000)
                    elif 'M' in val.upper():
                        comments = int(float(val.upper().replace('M', '')) * 1000000)
                    else:
                        try:
                            comments = int(float(val))
                        except:
                            pass

                # Try to extract shares
                shares = 0
                shares_match = re.search(r'(\d+(?:\.\d+)?[KMB]?)\s*(?:shares?|Shares?)', page_text)
                if shares_match:
                    val = shares_match.group(1).replace(',', '')
                    if 'K' in val.upper():
                        shares = int(float(val.upper().replace('K', '')) * 1000)
                    elif 'M' in val.upper():
                        shares = int(float(val.upper().replace('M', '')) * 1000000)
                    else:
                        try:
                            shares = int(float(val))
                        except:
                            pass

                # Try to extract views
                views = 0
                views_match = re.search(r'(\d+(?:\.\d+)?[KMB]?)\s*(?:views?|Views?|plays?|Plays?)', page_text)
                if views_match:
                    val = views_match.group(1).replace(',', '')
                    if 'K' in val.upper():
                        views = int(float(val.upper().replace('K', '')) * 1000)
                    elif 'M' in val.upper():
                        views = int(float(val.upper().replace('M', '')) * 1000000)
                    else:
                        try:
                            views = int(float(val))
                        except:
                            pass

                detailed_video = {
                    **video,
                    'likes': likes,
                    'comments': comments,
                    'shares': shares,
                    'views': views,
                    'total_engagement': likes + comments + shares
                }
                detailed_videos.append(detailed_video)
                print(f"    Views: {views}, Likes: {likes}, Comments: {comments}, Shares: {shares}")

            except Exception as e:
                print(f"    Error fetching details: {e}")
                detailed_videos.append(video)

        # Save data
        output_dir = Path("output") / GRANTEE_NAME / "tiktok"
        output_dir.mkdir(parents=True, exist_ok=True)

        posts_file = output_dir / "posts_manual.json"
        with open(posts_file, 'w', encoding='utf-8') as f:
            json.dump(detailed_videos, f, indent=2, ensure_ascii=False)
        print(f"\nSaved videos to: {posts_file}")

        # Calculate metrics
        total_likes = sum(v.get('likes', 0) for v in detailed_videos)
        total_comments = sum(v.get('comments', 0) for v in detailed_videos)
        total_shares = sum(v.get('shares', 0) for v in detailed_videos)
        total_views = sum(v.get('views', 0) for v in detailed_videos)

        metadata = {
            'url': TIKTOK_URL,
            'username': 'centercooperativemedia',
            'grantee_name': GRANTEE_NAME,
            'scraped_at': datetime.now().isoformat(),
            'posts_downloaded': len(detailed_videos),
            'engagement_metrics': {
                'followers_count': followers_count,
                'following_count': following_count,
                'profile_likes': likes_count,
                'total_video_likes': total_likes,
                'total_comments': total_comments,
                'total_shares': total_shares,
                'total_views': total_views,
                'avg_views': round(total_views / len(detailed_videos), 2) if detailed_videos else 0,
                'avg_likes': round(total_likes / len(detailed_videos), 2) if detailed_videos else 0,
                'posts_analyzed': len(detailed_videos)
            },
            'authenticated': True,
            'platform': 'tiktok',
            'method': 'manual_login'
        }

        metadata_file = output_dir / "metadata_manual.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"Saved metadata to: {metadata_file}")

        await page.screenshot(path=str(output_dir / "screenshot_manual.png"))

        print("\n" + "="*60)
        print("TIKTOK SCRAPING COMPLETE")
        print("="*60)
        print(f"Videos collected: {len(detailed_videos)}")
        print(f"Followers: {followers_count:,}")
        print(f"Total views: {total_views:,}")
        print(f"Total likes: {total_likes:,}")
        print(f"Total comments: {total_comments:,}")
        print(f"Total shares: {total_shares:,}")

        print("\n>>> Browser will close in 10 seconds...")
        await asyncio.sleep(10)
        await browser.close()

        return {
            'success': len(detailed_videos) > 0,
            'posts_downloaded': len(detailed_videos),
            'engagement_metrics': metadata['engagement_metrics']
        }


if __name__ == "__main__":
    result = asyncio.run(scrape_tiktok_manual())
    print(f"\nFinal result: {result}")
