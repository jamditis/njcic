#!/usr/bin/env python
"""
Scrape Center for Cooperative Media social media accounts.
Collects the last 50 posts from each platform.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.bluesky import BlueSkyScraper
from scrapers.twitter import TwitterScraper
from scrapers.youtube import YouTubeScraper
from scrapers.tiktok import TikTokScraper

# CCM Social Media URLs
CCM_ACCOUNTS = {
    "bluesky": "https://bsky.app/profile/centercoopmedia.bsky.social",
    "twitter": "https://twitter.com/centercoopmedia",
    "youtube": "https://www.youtube.com/@CenterCoopMedia",
    "tiktok": "https://www.tiktok.com/@centercooperativemedia",
}

GRANTEE_NAME = "Center_for_Cooperative_Media"
MAX_POSTS = 50


def main():
    results = {}
    output_dir = Path("output") / GRANTEE_NAME
    output_dir.mkdir(parents=True, exist_ok=True)

    # Bluesky - uses public API, should work without auth
    print("\n" + "="*60)
    print("SCRAPING BLUESKY")
    print("="*60)
    try:
        scraper = BlueSkyScraper(output_dir=Path("output"))
        result = scraper.scrape(
            CCM_ACCOUNTS["bluesky"],
            GRANTEE_NAME,
            max_posts=MAX_POSTS
        )
        results["bluesky"] = result
        print(f"Bluesky: {result['posts_downloaded']} posts scraped")
        if result.get('engagement_metrics'):
            em = result['engagement_metrics']
            print(f"  Followers: {em.get('followers_count', 'N/A')}")
            print(f"  Total engagement: {em.get('total_engagement', 'N/A')}")
    except Exception as e:
        print(f"Bluesky error: {e}")
        results["bluesky"] = {"success": False, "error": str(e)}

    # Twitter - requires API keys
    print("\n" + "="*60)
    print("SCRAPING TWITTER/X")
    print("="*60)
    try:
        scraper = TwitterScraper(output_dir=Path("output"))
        result = scraper.scrape(
            CCM_ACCOUNTS["twitter"],
            GRANTEE_NAME,
            max_posts=MAX_POSTS
        )
        results["twitter"] = result
        print(f"Twitter: {result['posts_downloaded']} posts scraped")
    except Exception as e:
        print(f"Twitter error: {e}")
        results["twitter"] = {"success": False, "error": str(e)}

    # YouTube - uses yt-dlp
    print("\n" + "="*60)
    print("SCRAPING YOUTUBE")
    print("="*60)
    try:
        scraper = YouTubeScraper(output_dir=Path("output"))
        result = scraper.scrape(
            CCM_ACCOUNTS["youtube"],
            GRANTEE_NAME,
            max_posts=MAX_POSTS
        )
        results["youtube"] = result
        print(f"YouTube: {result['posts_downloaded']} videos scraped")
    except Exception as e:
        print(f"YouTube error: {e}")
        results["youtube"] = {"success": False, "error": str(e)}

    # TikTok - uses yt-dlp
    print("\n" + "="*60)
    print("SCRAPING TIKTOK")
    print("="*60)
    try:
        scraper = TikTokScraper(output_dir=Path("output"))
        result = scraper.scrape(
            CCM_ACCOUNTS["tiktok"],
            GRANTEE_NAME,
            max_posts=MAX_POSTS
        )
        results["tiktok"] = result
        print(f"TikTok: {result['posts_downloaded']} videos scraped")
    except Exception as e:
        print(f"TikTok error: {e}")
        results["tiktok"] = {"success": False, "error": str(e)}

    # Summary
    print("\n" + "="*60)
    print("SCRAPING SUMMARY")
    print("="*60)

    summary = {
        "grantee": GRANTEE_NAME,
        "timestamp": datetime.now().isoformat(),
        "platforms": {}
    }

    for platform, result in results.items():
        posts = result.get('posts_downloaded', 0)
        success = result.get('success', False)
        print(f"{platform.upper():12} | {'SUCCESS' if success else 'FAILED':8} | {posts:3} posts")
        summary["platforms"][platform] = {
            "success": success,
            "posts_downloaded": posts,
            "engagement_metrics": result.get('engagement_metrics', {})
        }

    # Save summary
    summary_path = output_dir / "scrape_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved to: {summary_path}")

    return results


if __name__ == "__main__":
    main()
