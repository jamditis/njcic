#!/usr/bin/env python
"""
Scrape Center for Cooperative Media with FULL authentication.
Uses visible browser windows for manual intervention when needed.
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# Verify credentials are loaded
print("="*60)
print("CHECKING CREDENTIALS")
print("="*60)
print(f"TWITTER_USERNAME: {os.getenv('TWITTER_USERNAME')}")
print(f"TWITTER_PASSWORD: {'*' * len(os.getenv('TWITTER_PASSWORD', '')) if os.getenv('TWITTER_PASSWORD') else 'NOT SET'}")
print(f"INSTAGRAM_USERNAME: {os.getenv('INSTAGRAM_USERNAME')}")
print(f"INSTAGRAM_PASSWORD: {'*' * len(os.getenv('INSTAGRAM_PASSWORD', '')) if os.getenv('INSTAGRAM_PASSWORD') else 'NOT SET'}")
print(f"TIKTOK_USERNAME: {os.getenv('TIKTOK_USERNAME')}")
print()

# CCM Social Media URLs
CCM_ACCOUNTS = {
    "instagram": "https://www.instagram.com/centerforcooperativemedia/",
    "twitter": "https://twitter.com/centercoopmedia",
    "tiktok": "https://www.tiktok.com/@centercooperativemedia",
}

GRANTEE_NAME = "Center_for_Cooperative_Media"
MAX_POSTS = 50


def scrape_instagram_with_instaloader():
    """Scrape Instagram using Instaloader with login."""
    print("\n" + "="*60)
    print("SCRAPING INSTAGRAM (Instaloader with Login)")
    print("="*60)

    try:
        from scrapers.instagram import InstagramScraper

        session_file = Path("output/.sessions/instagram_session")
        session_file.parent.mkdir(parents=True, exist_ok=True)

        scraper = InstagramScraper(
            output_dir="output",
            session_file=str(session_file)
        )

        result = scraper.scrape(
            CCM_ACCOUNTS["instagram"],
            GRANTEE_NAME,
            max_posts=MAX_POSTS
        )

        print(f"Instagram: {result.get('posts_downloaded', 0)} posts scraped")
        if result.get('engagement_metrics'):
            em = result['engagement_metrics']
            print(f"  Followers: {em.get('followers_count', 'N/A')}")
            print(f"  Total likes: {em.get('total_likes', 'N/A')}")
            print(f"  Total comments: {em.get('total_comments', 'N/A')}")

        return result

    except Exception as e:
        print(f"Instagram error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e), "posts_downloaded": 0}


def scrape_twitter_visible():
    """Scrape Twitter with VISIBLE browser for manual auth if needed."""
    print("\n" + "="*60)
    print("SCRAPING TWITTER (Visible Browser)")
    print("="*60)
    print(">>> A browser window will open. Please complete any security challenges if prompted.")
    print()

    try:
        from scrapers.twitter import TwitterScraper

        scraper = TwitterScraper(
            output_dir="output",
            max_posts=MAX_POSTS,
            headless=False  # VISIBLE BROWSER
        )

        result = scraper.scrape(
            CCM_ACCOUNTS["twitter"],
            GRANTEE_NAME,
            max_posts=MAX_POSTS
        )

        print(f"Twitter: {result.get('posts_downloaded', 0)} posts scraped")
        if result.get('engagement_metrics'):
            em = result['engagement_metrics']
            print(f"  Followers: {em.get('followers_count', 'N/A')}")
            print(f"  Total likes: {em.get('total_likes', 'N/A')}")

        return result

    except Exception as e:
        print(f"Twitter error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e), "posts_downloaded": 0}


def scrape_tiktok_with_proxy():
    """Scrape TikTok with retry and alternative methods."""
    print("\n" + "="*60)
    print("SCRAPING TIKTOK")
    print("="*60)

    try:
        from scrapers.tiktok import TikTokScraper

        scraper = TikTokScraper(output_dir=Path("output"))

        result = scraper.scrape(
            CCM_ACCOUNTS["tiktok"],
            GRANTEE_NAME,
            max_posts=MAX_POSTS
        )

        print(f"TikTok: {result.get('posts_downloaded', 0)} posts scraped")
        return result

    except Exception as e:
        print(f"TikTok error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e), "posts_downloaded": 0}


def main():
    results = {}
    output_dir = Path("output") / GRANTEE_NAME
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run scrapers sequentially for manual intervention
    results["twitter"] = scrape_twitter_visible()
    results["instagram"] = scrape_instagram_with_instaloader()
    results["tiktok"] = scrape_tiktok_with_proxy()

    # Summary
    print("\n" + "="*60)
    print("AUTHENTICATED SCRAPING SUMMARY")
    print("="*60)

    for platform, result in results.items():
        posts = result.get('posts_downloaded', 0)
        success = result.get('success', False)
        print(f"{platform.upper():12} | {'SUCCESS' if success else 'FAILED':8} | {posts:3} posts")

    # Save summary
    summary_path = output_dir / "authenticated_scrape_summary.json"
    summary = {
        "grantee": GRANTEE_NAME,
        "timestamp": datetime.now().isoformat(),
        "platforms": {
            platform: {
                "success": result.get('success', False),
                "posts_downloaded": result.get('posts_downloaded', 0),
                "engagement_metrics": result.get('engagement_metrics', {})
            }
            for platform, result in results.items()
        }
    }

    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved to: {summary_path}")

    return results


if __name__ == "__main__":
    main()
