#!/usr/bin/env python3
"""
Example script to test Facebook scraper.

Usage:
    python scripts/test_facebook.py <facebook_url> <grantee_name>

Example:
    python scripts/test_facebook.py https://facebook.com/example "Example Org"
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.facebook import FacebookScraper


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/test_facebook.py <facebook_url> <grantee_name>")
        print("\nExamples:")
        print("  python scripts/test_facebook.py https://facebook.com/example 'Example Org'")
        print("  python scripts/test_facebook.py https://facebook.com/pages/name/123456 'Example Org'")
        print("  python scripts/test_facebook.py https://facebook.com/groups/example 'Example Org'")
        sys.exit(1)

    url = sys.argv[1]
    grantee_name = sys.argv[2]

    print(f"\n{'='*60}")
    print("Facebook Scraper Test")
    print(f"{'='*60}")
    print(f"URL: {url}")
    print(f"Grantee: {grantee_name}")
    print(f"{'='*60}\n")

    # Create scraper
    scraper = FacebookScraper(output_dir="output", headless=True)

    # Test username extraction
    username = scraper.extract_username(url)
    print(f"Extracted username: {username}\n")

    if not username:
        print("ERROR: Could not extract username from URL")
        sys.exit(1)

    # Run scraper
    print("Starting scrape...\n")
    result = scraper.scrape(url, grantee_name)

    # Display results
    print(f"\n{'='*60}")
    print("Scraping Results")
    print(f"{'='*60}")
    print(f"Success: {result['success']}")
    print(f"Posts Downloaded: {result['posts_downloaded']}")
    
    if result['errors']:
        print(f"\nErrors:")
        for error in result['errors']:
            print(f"  - {error}")
    
    print(f"\nEngagement Metrics:")
    metrics = result['engagement_metrics']
    print(f"  Followers: {metrics.get('followers_count', 'N/A')}")
    print(f"  Total Reactions: {metrics.get('total_reactions', 0)}")
    print(f"  Total Comments: {metrics.get('total_comments', 0)}")
    print(f"  Total Shares: {metrics.get('total_shares', 0)}")
    print(f"  Avg Engagement Rate: {metrics.get('avg_engagement_rate', 0)}%")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
