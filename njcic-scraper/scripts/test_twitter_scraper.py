#!/usr/bin/env python3
"""
Test script for Twitter scraper.
Demonstrates usage and validates implementation.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path to import scrapers
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.twitter import TwitterScraper


def test_username_extraction():
    """Test username extraction from various URL formats."""
    print("=" * 60)
    print("Testing Username Extraction")
    print("=" * 60)
    
    scraper = TwitterScraper()
    
    test_cases = [
        ("https://twitter.com/elonmusk", "elonmusk"),
        ("https://x.com/elonmusk", "elonmusk"),
        ("https://twitter.com/NASA/status/123456", "NASA"),
        ("https://x.com/OpenAI/status/789", "OpenAI"),
        ("https://twitter.com/@username", "username"),
        ("https://example.com/user", None),  # Invalid domain
        ("https://twitter.com/", None),  # No username
    ]
    
    for url, expected in test_cases:
        result = scraper.extract_username(url)
        status = "✓" if result == expected else "✗"
        print(f"{status} {url}")
        print(f"  Expected: {expected}, Got: {result}")
        print()
    
    print()


def test_scraping(url: str, grantee_name: str):
    """Test actual scraping (requires internet connection)."""
    print("=" * 60)
    print("Testing Twitter Scraping")
    print("=" * 60)
    print(f"URL: {url}")
    print(f"Grantee: {grantee_name}")
    print()
    
    # Initialize scraper
    scraper = TwitterScraper(
        output_dir="/home/user/njcic/njcic-scraper/output",
        max_posts=5  # Limit to 5 posts for testing
    )
    
    # Scrape
    result = scraper.scrape(url, grantee_name)
    
    # Display results
    print("\n" + "=" * 60)
    print("Results")
    print("=" * 60)
    print(f"Success: {result['success']}")
    print(f"Posts Downloaded: {result['posts_downloaded']}")
    print(f"Errors: {len(result['errors'])}")
    
    if result['errors']:
        print("\nErrors:")
        for error in result['errors']:
            print(f"  - {error}")
    
    print("\nEngagement Metrics:")
    metrics = result.get('engagement_metrics', {})
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    
    return result


def main():
    """Main test function."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\nTwitter/X Scraper Test Suite")
    print("=" * 60)
    print()
    
    # Test username extraction
    test_username_extraction()
    
    # Test actual scraping if URL provided
    if len(sys.argv) >= 2:
        url = sys.argv[1]
        grantee_name = sys.argv[2] if len(sys.argv) >= 3 else "Test Organization"
        
        try:
            test_scraping(url, grantee_name)
        except Exception as e:
            print(f"\nError during scraping test: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("To test actual scraping, provide a Twitter URL:")
        print("  python test_twitter_scraper.py https://twitter.com/username \"Grantee Name\"")
        print()
    
    print("\nTest suite completed!")


if __name__ == "__main__":
    main()
