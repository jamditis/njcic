#!/usr/bin/env python
"""
Universal grantee social media scraper.
Scrapes any platform for any grantee using manual login workflow.

Usage:
    python scrape_grantee.py --platform twitter --grantee "NJ Spotlight" --url "https://twitter.com/njspotlight"
    python scrape_grantee.py --platform instagram --grantee "TAPinto" --url "https://instagram.com/tapinto"
"""

import sys
import os
import json
import asyncio
import re
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

try:
    from playwright.async_api import async_playwright
    from playwright_stealth.stealth import Stealth
except ImportError:
    print("ERROR: Playwright not installed!")
    print("Run: pip install playwright playwright-stealth")
    sys.exit(1)

SIGNAL_FILE = Path("output/READY_TO_SCRAPE")
CLOSE_FILE = Path("output/CLOSE_BROWSER")
MAX_POSTS = 50


def sanitize_name(name: str) -> str:
    """Convert grantee name to filesystem-safe format."""
    return re.sub(r'[^\w\-]', '_', name.replace(' ', '_'))


def extract_username(url: str, platform: str) -> str:
    """Extract username from social media URL."""
    patterns = {
        'twitter': r'twitter\.com/([^/?\s]+)',
        'instagram': r'instagram\.com/([^/?\s]+)',
        'facebook': r'facebook\.com/([^/?\s]+)',
        'tiktok': r'tiktok\.com/@([^/?\s]+)',
        'linkedin': r'linkedin\.com/company/([^/?\s]+)',
        'youtube': r'youtube\.com/(@?[^/?\s]+)',
        'bluesky': r'bsky\.app/profile/([^/?\s]+)',
    }
    pattern = patterns.get(platform, r'/([^/?\s]+)/?$')
    match = re.search(pattern, url)
    return match.group(1) if match else 'unknown'


PLATFORM_CONFIGS = {
    'twitter': {
        'login_url': 'https://twitter.com/login',
        'name': 'Twitter/X',
    },
    'instagram': {
        'login_url': 'https://www.instagram.com/accounts/login/',
        'name': 'Instagram',
    },
    'facebook': {
        'login_url': 'https://www.facebook.com/login',
        'name': 'Facebook',
    },
    'tiktok': {
        'login_url': 'https://www.tiktok.com/login',
        'name': 'TikTok',
    },
    'linkedin': {
        'login_url': 'https://www.linkedin.com/login',
        'name': 'LinkedIn',
    },
    'youtube': {
        'login_url': None,  # YouTube doesn't require login for public data
        'name': 'YouTube',
    },
    'bluesky': {
        'login_url': None,  # Bluesky has public API
        'name': 'Bluesky',
    },
}


async def scrape_twitter(page, url: str) -> tuple[list, dict]:
    """Scrape Twitter posts."""
    await page.goto(url, wait_until='domcontentloaded')
    await page.wait_for_timeout(3000)

    # Get follower count
    followers = 0
    try:
        page_text = await page.inner_text('body')
        match = re.search(r'([\d,]+)\s*Followers', page_text)
        if match:
            followers = int(match.group(1).replace(',', ''))
    except:
        pass

    posts = []
    seen_ids = set()
    scroll_attempts = 0

    while len(posts) < MAX_POSTS and scroll_attempts < 50:
        tweets = await page.query_selector_all('article[data-testid="tweet"]')

        for tweet in tweets:
            try:
                # Get tweet link for ID
                link = await tweet.query_selector('a[href*="/status/"]')
                if not link:
                    continue
                href = await link.get_attribute('href')
                tweet_id = re.search(r'/status/(\d+)', href)
                if not tweet_id:
                    continue
                tweet_id = tweet_id.group(1)

                if tweet_id in seen_ids:
                    continue
                seen_ids.add(tweet_id)

                # Get text
                text_el = await tweet.query_selector('[data-testid="tweetText"]')
                text = await text_el.inner_text() if text_el else ""

                # Get metrics from aria-labels
                likes = retweets = replies = 0
                for label_text in ['like', 'retweet', 'reply']:
                    el = await tweet.query_selector(f'[data-testid="{label_text}"] [aria-label]')
                    if el:
                        aria = await el.get_attribute('aria-label')
                        if aria:
                            num_match = re.search(r'(\d+)', aria)
                            if num_match:
                                val = int(num_match.group(1))
                                if 'like' in label_text:
                                    likes = val
                                elif 'retweet' in label_text:
                                    retweets = val
                                elif 'reply' in label_text:
                                    replies = val

                posts.append({
                    'post_id': tweet_id,
                    'text': text[:500],
                    'likes': likes,
                    'retweets': retweets,
                    'replies': replies,
                    'total_engagement': likes + retweets + replies,
                    'platform': 'twitter'
                })
                print(f"  Tweet {len(posts)}: {text[:40]}... | L:{likes} RT:{retweets}")

            except:
                continue

        await page.evaluate('window.scrollBy(0, 1500)')
        await page.wait_for_timeout(2000)
        scroll_attempts += 1

    metadata = {
        'followers_count': followers,
        'total_likes': sum(p['likes'] for p in posts),
        'total_retweets': sum(p['retweets'] for p in posts),
        'total_replies': sum(p['replies'] for p in posts),
    }

    return posts, metadata


async def scrape_instagram(page, url: str) -> tuple[list, dict]:
    """Scrape Instagram posts."""
    await page.goto(url, wait_until='domcontentloaded')
    await page.wait_for_timeout(3000)

    followers = 0
    try:
        content = await page.content()
        match = re.search(r'"edge_followed_by":\s*\{\s*"count":\s*(\d+)', content)
        if match:
            followers = int(match.group(1))
    except:
        pass

    # Collect post shortcodes
    posts = []
    seen_ids = set()
    scroll_attempts = 0

    while len(posts) < MAX_POSTS and scroll_attempts < 50:
        links = await page.query_selector_all('a[href*="/p/"]')

        for link in links:
            try:
                href = await link.get_attribute('href')
                match = re.search(r'/p/([^/]+)/', href)
                if not match:
                    continue
                shortcode = match.group(1)

                if shortcode in seen_ids:
                    continue
                seen_ids.add(shortcode)

                img = await link.query_selector('img')
                alt = await img.get_attribute('alt') if img else ""

                posts.append({
                    'post_id': shortcode,
                    'shortcode': shortcode,
                    'url': f"https://www.instagram.com/p/{shortcode}/",
                    'caption_preview': alt[:200] if alt else "",
                    'platform': 'instagram'
                })
                print(f"  Post {len(posts)}: {shortcode}")

            except:
                continue

        await page.evaluate('window.scrollBy(0, 1000)')
        await page.wait_for_timeout(1500)
        scroll_attempts += 1

    # Fetch detailed engagement for each post
    print(">>> Fetching engagement for each post...")
    for i, post in enumerate(posts[:MAX_POSTS]):
        try:
            await page.goto(post['url'], wait_until='domcontentloaded')
            await page.wait_for_timeout(1500)
            content = await page.content()

            likes = 0
            likes_match = re.search(r'"edge_media_preview_like":\s*\{\s*"count":\s*(\d+)', content)
            if likes_match:
                likes = int(likes_match.group(1))

            comments = 0
            comments_match = re.search(r'"edge_media_to_parent_comment":\s*\{\s*"count":\s*(\d+)', content)
            if comments_match:
                comments = int(comments_match.group(1))

            post['likes'] = likes
            post['comments'] = comments
            post['total_engagement'] = likes + comments
            print(f"    {i+1}/{len(posts)}: L:{likes} C:{comments}")
        except:
            post['likes'] = 0
            post['comments'] = 0
            post['total_engagement'] = 0

    metadata = {
        'followers_count': followers,
        'total_likes': sum(p.get('likes', 0) for p in posts),
        'total_comments': sum(p.get('comments', 0) for p in posts),
    }

    return posts, metadata


async def scrape_facebook(page, url: str) -> tuple[list, dict]:
    """Scrape Facebook posts (public only)."""
    await page.goto(url, wait_until='domcontentloaded')
    await page.wait_for_timeout(3000)

    followers = 0
    try:
        page_text = await page.inner_text('body')
        match = re.search(r'([\d,]+)\s*(?:followers|likes)', page_text, re.IGNORECASE)
        if match:
            followers = int(match.group(1).replace(',', ''))
    except:
        pass

    posts = []
    seen_ids = set()
    scroll_attempts = 0

    while len(posts) < MAX_POSTS and scroll_attempts < 30:
        post_links = await page.query_selector_all('a[href*="/posts/"], a[href*="/photo"], a[href*="story_fbid"]')

        for link in post_links:
            try:
                href = await link.get_attribute('href')
                post_id = str(hash(href))

                if post_id in seen_ids:
                    continue
                seen_ids.add(post_id)

                parent = await link.evaluate_handle('el => el.closest("[data-ad-preview], [role=article]")')
                text = ""
                if parent:
                    try:
                        text = await parent.inner_text()
                        text = text[:500]
                    except:
                        pass

                posts.append({
                    'post_id': post_id,
                    'url': href,
                    'text': text,
                    'platform': 'facebook'
                })
                print(f"  Post {len(posts)}: {text[:40]}...")

            except:
                continue

        await page.evaluate('window.scrollBy(0, 1500)')
        await page.wait_for_timeout(2000)
        scroll_attempts += 1

    metadata = {
        'followers_count': followers,
        'posts_collected': len(posts),
    }

    return posts, metadata


async def scrape_tiktok(page, url: str) -> tuple[list, dict]:
    """Scrape TikTok videos."""
    await page.goto(url, wait_until='domcontentloaded')
    await page.wait_for_timeout(5000)

    followers = 0
    likes = 0
    try:
        page_text = await page.inner_text('body')

        match = re.search(r'(\d+(?:\.\d+)?[KMB]?)\s*Followers', page_text, re.IGNORECASE)
        if match:
            val = match.group(1).replace(',', '')
            if 'K' in val.upper():
                followers = int(float(val.upper().replace('K', '')) * 1000)
            elif 'M' in val.upper():
                followers = int(float(val.upper().replace('M', '')) * 1000000)
            else:
                followers = int(float(val))

        match = re.search(r'(\d+(?:\.\d+)?[KMB]?)\s*Likes', page_text, re.IGNORECASE)
        if match:
            val = match.group(1).replace(',', '')
            if 'K' in val.upper():
                likes = int(float(val.upper().replace('K', '')) * 1000)
            elif 'M' in val.upper():
                likes = int(float(val.upper().replace('M', '')) * 1000000)
            else:
                likes = int(float(val))
    except:
        pass

    print(f"  Profile: {followers} followers, {likes} likes")

    videos = []
    seen_ids = set()
    scroll_attempts = 0

    while len(videos) < MAX_POSTS and scroll_attempts < 50:
        links = await page.query_selector_all('a[href*="/video/"]')

        for link in links:
            try:
                href = await link.get_attribute('href')
                match = re.search(r'/video/(\d+)', href)
                if not match:
                    continue
                video_id = match.group(1)

                if video_id in seen_ids:
                    continue
                seen_ids.add(video_id)

                videos.append({
                    'post_id': video_id,
                    'video_id': video_id,
                    'url': href if href.startswith('http') else f"https://www.tiktok.com{href}",
                    'platform': 'tiktok'
                })
                print(f"  Video {len(videos)}: {video_id}")

            except:
                continue

        await page.evaluate('window.scrollBy(0, 1000)')
        await page.wait_for_timeout(1500)
        scroll_attempts += 1

    metadata = {
        'followers_count': followers,
        'profile_likes': likes,
        'videos_collected': len(videos),
    }

    return videos, metadata


async def scrape_linkedin(page, url: str) -> tuple[list, dict]:
    """Scrape LinkedIn company posts."""
    # Navigate to posts page
    posts_url = url.rstrip('/') + '/posts/' if '/posts' not in url else url
    await page.goto(posts_url, wait_until='domcontentloaded')
    await page.wait_for_timeout(3000)

    followers = 0
    company_name = ""
    try:
        page_text = await page.inner_text('body')

        name_el = await page.query_selector('h1')
        if name_el:
            company_name = (await name_el.inner_text()).strip()

        match = re.search(r'([\d,]+)\s*followers', page_text, re.IGNORECASE)
        if match:
            followers = int(match.group(1).replace(',', ''))
    except:
        pass

    print(f"  Company: {company_name}, Followers: {followers}")

    posts = []
    seen_ids = set()
    scroll_attempts = 0
    no_new = 0

    while len(posts) < MAX_POSTS and scroll_attempts < 100:
        prev_count = len(posts)

        elements = await page.query_selector_all('[data-urn*="activity"], .feed-shared-update-v2, .occludable-update')

        for el in elements:
            try:
                urn = await el.get_attribute('data-urn')
                post_id = ""
                if urn:
                    match = re.search(r'activity[:\-](\d+)', urn)
                    if match:
                        post_id = match.group(1)

                if not post_id:
                    text = await el.inner_text()
                    if len(text) < 20:
                        continue
                    post_id = str(hash(text[:100]))

                if post_id in seen_ids:
                    continue
                seen_ids.add(post_id)

                text = ""
                for sel in ['.feed-shared-text', '.break-words']:
                    text_el = await el.query_selector(sel)
                    if text_el:
                        text = await text_el.inner_text()
                        break

                likes = 0
                likes_el = await el.query_selector('.social-details-social-counts__reactions-count')
                if likes_el:
                    try:
                        likes = int((await likes_el.inner_text()).replace(',', ''))
                    except:
                        pass

                posts.append({
                    'post_id': post_id,
                    'text': text[:500],
                    'likes': likes,
                    'platform': 'linkedin'
                })
                print(f"  Post {len(posts)}: {text[:40]}... | L:{likes}")

            except:
                continue

        if len(posts) == prev_count:
            no_new += 1
            if no_new >= 15:
                break
        else:
            no_new = 0

        await page.evaluate('window.scrollBy(0, 1500)')
        await page.wait_for_timeout(2000)
        scroll_attempts += 1

    metadata = {
        'company_name': company_name,
        'followers_count': followers,
        'total_likes': sum(p.get('likes', 0) for p in posts),
    }

    return posts, metadata


SCRAPERS = {
    'twitter': scrape_twitter,
    'instagram': scrape_instagram,
    'facebook': scrape_facebook,
    'tiktok': scrape_tiktok,
    'linkedin': scrape_linkedin,
}


async def run_scraper(platform: str, grantee: str, url: str):
    """Main scraper orchestrator."""

    config = PLATFORM_CONFIGS.get(platform)
    if not config:
        print(f"ERROR: Unknown platform '{platform}'")
        print(f"Supported: {', '.join(PLATFORM_CONFIGS.keys())}")
        return

    scraper_func = SCRAPERS.get(platform)
    if not scraper_func:
        print(f"ERROR: No scraper implemented for '{platform}'")
        return

    grantee_safe = sanitize_name(grantee)
    username = extract_username(url, platform)

    print("=" * 60)
    print(f"SCRAPING {config['name'].upper()} FOR: {grantee}")
    print("=" * 60)
    print(f"URL: {url}")
    print(f"Username: {username}")
    print()

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

        # Handle login if needed
        if config['login_url']:
            print(f">>> Opening {config['name']} login page...")
            await page.goto(config['login_url'], wait_until='domcontentloaded')

            print()
            print("=" * 60)
            print("MANUAL LOGIN REQUIRED")
            print("1. Log in to your account")
            print("2. Navigate to the target profile if needed")
            print("3. Create signal file: touch output/READY_TO_SCRAPE")
            print("=" * 60)

            while not SIGNAL_FILE.exists():
                await asyncio.sleep(2)

            print(">>> Signal received!")
            SIGNAL_FILE.unlink()

            # Save cookies
            cookies = await context.cookies()
            cookies_dir = Path("output/.cookies")
            cookies_dir.mkdir(parents=True, exist_ok=True)
            with open(cookies_dir / f"{platform}_cookies.json", 'w') as f:
                json.dump(cookies, f, indent=2)

        # Run the scraper
        print(f">>> Scraping {config['name']}...")
        posts, metrics = await scraper_func(page, url)

        print(f"\n>>> Collected {len(posts)} posts")

        # Save results
        output_dir = Path("output") / grantee_safe / platform / username
        output_dir.mkdir(parents=True, exist_ok=True)

        posts_file = output_dir / "posts.json"
        with open(posts_file, 'w', encoding='utf-8') as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)

        metadata = {
            'url': url,
            'username': username,
            'grantee_name': grantee,
            'scraped_at': datetime.now().isoformat(),
            'posts_downloaded': len(posts),
            'engagement_metrics': metrics,
            'platform': platform,
        }

        with open(output_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)

        await page.screenshot(path=str(output_dir / "screenshot.png"))

        print("\n" + "=" * 60)
        print(f"{config['name'].upper()} SCRAPING COMPLETE")
        print("=" * 60)
        print(f"Posts: {len(posts)}")
        print(f"Output: {output_dir}")
        print()
        print(">>> Browser stays open. Create output/CLOSE_BROWSER to close.")

        while not CLOSE_FILE.exists():
            await asyncio.sleep(2)

        CLOSE_FILE.unlink()
        print(">>> Closing browser...")
        await browser.close()

        return {
            'success': len(posts) > 0,
            'posts_downloaded': len(posts),
            'output_dir': str(output_dir),
            'metrics': metrics,
        }


def main():
    parser = argparse.ArgumentParser(
        description='Scrape social media for NJCIC grantees',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python scrape_grantee.py --platform twitter --grantee "NJ Spotlight" --url "https://twitter.com/njspotlight"
    python scrape_grantee.py --platform instagram --grantee "TAPinto" --url "https://instagram.com/tapintonewjersey"
    python scrape_grantee.py --platform linkedin --grantee "WHYY" --url "https://linkedin.com/company/whyy"

Supported platforms: twitter, instagram, facebook, tiktok, linkedin
        '''
    )

    parser.add_argument('--platform', '-p', required=True,
                        choices=['twitter', 'instagram', 'facebook', 'tiktok', 'linkedin'],
                        help='Social media platform to scrape')
    parser.add_argument('--grantee', '-g', required=True,
                        help='Grantee organization name')
    parser.add_argument('--url', '-u', required=True,
                        help='Profile/page URL to scrape')

    args = parser.parse_args()

    result = asyncio.run(run_scraper(args.platform, args.grantee, args.url))
    print(f"\nResult: {result}")


if __name__ == "__main__":
    main()
