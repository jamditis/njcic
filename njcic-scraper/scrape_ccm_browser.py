#!/usr/bin/env python
"""
Scrape Center for Cooperative Media social media accounts using browser automation.
Uses Playwright with stealth mode for Instagram, Facebook, and LinkedIn.
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# CCM Social Media URLs
CCM_ACCOUNTS = {
    "instagram": "https://www.instagram.com/centerforcooperativemedia/",
    "facebook": "https://www.facebook.com/centerforcooperativemedia",
    "linkedin": "https://www.linkedin.com/company/center-for-cooperative-media/",
}

GRANTEE_NAME = "Center_for_Cooperative_Media"
MAX_POSTS = 50


def scrape_instagram():
    """Scrape Instagram using Playwright."""
    print("\n" + "="*60)
    print("SCRAPING INSTAGRAM")
    print("="*60)

    try:
        from scrapers.instagram_playwright import InstagramPlaywrightScraper

        scraper = InstagramPlaywrightScraper(
            output_dir=Path("output"),
            headless=True,
            max_retries=3
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
            print(f"  Total engagement: {em.get('total_engagement', 'N/A')}")

        return result

    except Exception as e:
        print(f"Instagram error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e), "posts_downloaded": 0}


def scrape_facebook():
    """Scrape Facebook using Playwright."""
    print("\n" + "="*60)
    print("SCRAPING FACEBOOK")
    print("="*60)

    try:
        from scrapers.facebook import FacebookScraper

        scraper = FacebookScraper(
            output_dir=Path("output"),
            headless=True,
            max_retries=3
        )

        result = scraper.scrape(
            CCM_ACCOUNTS["facebook"],
            GRANTEE_NAME,
            max_posts=MAX_POSTS
        )

        print(f"Facebook: {result.get('posts_downloaded', 0)} posts scraped")
        if result.get('engagement_metrics'):
            em = result['engagement_metrics']
            print(f"  Followers: {em.get('followers_count', 'N/A')}")

        return result

    except Exception as e:
        print(f"Facebook error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e), "posts_downloaded": 0}


def scrape_linkedin():
    """Scrape LinkedIn using Playwright."""
    print("\n" + "="*60)
    print("SCRAPING LINKEDIN")
    print("="*60)

    try:
        from scrapers.linkedin import LinkedInScraper

        scraper = LinkedInScraper(
            output_dir="output",
            headless=True
        )

        result = scraper.scrape(
            CCM_ACCOUNTS["linkedin"],
            GRANTEE_NAME,
            max_posts=MAX_POSTS
        )

        print(f"LinkedIn: {result.get('posts_downloaded', 0)} posts scraped")
        if result.get('engagement_metrics'):
            em = result['engagement_metrics']
            print(f"  Followers: {em.get('followers_count', 'N/A')}")

        return result

    except Exception as e:
        print(f"LinkedIn error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e), "posts_downloaded": 0}


def main():
    results = {}
    output_dir = Path("output") / GRANTEE_NAME
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run browser-based scrapers sequentially
    results["instagram"] = scrape_instagram()
    results["facebook"] = scrape_facebook()
    results["linkedin"] = scrape_linkedin()

    # Summary
    print("\n" + "="*60)
    print("BROWSER SCRAPING SUMMARY")
    print("="*60)

    for platform, result in results.items():
        posts = result.get('posts_downloaded', 0)
        success = result.get('success', False)
        print(f"{platform.upper():12} | {'SUCCESS' if success else 'FAILED':8} | {posts:3} posts")

    # Save summary
    summary_path = output_dir / "browser_scrape_summary.json"
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
