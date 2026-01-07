"""
Test script for Threads scraper.

Usage:
    python test_threads_scraper.py <threads_url> [grantee_name]

Example:
    python test_threads_scraper.py "https://www.threads.net/@zuck" "Mark Zuckerberg"
"""

import sys
import logging
from pathlib import Path
from scrapers.threads import ThreadsScraper


def setup_logging():
    """Configure logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_extract_username():
    """Test username extraction from various URL formats."""
    scraper = ThreadsScraper()

    test_urls = [
        ("https://www.threads.net/@zuck", "zuck"),
        ("https://threads.net/@elonmusk", "elonmusk"),
        ("threads.net/@testuser", "testuser"),
        ("https://www.threads.net/someuser", "someuser"),
        ("threads.net/anotheruser", "anotheruser"),
        ("https://www.threads.net/explore", None),  # Should return None
        ("not_a_url", None),  # Should return None
    ]

    print("\n" + "="*60)
    print("Testing username extraction:")
    print("="*60)

    for url, expected in test_urls:
        result = scraper.extract_username(url)
        status = "✓" if result == expected else "✗"
        print(f"{status} {url:45} -> {result} (expected: {expected})")

    print()


def test_scraping(url: str, grantee_name: str = "Test Grantee"):
    """
    Test scraping a Threads profile.

    Args:
        url: Threads profile URL
        grantee_name: Name of the grantee
    """
    # Create output directory
    output_dir = Path("output_test")
    output_dir.mkdir(exist_ok=True)

    # Initialize scraper
    scraper = ThreadsScraper(
        output_dir=str(output_dir),
        headless=True,  # Set to False to see browser
        timeout=30000
    )

    print("\n" + "="*60)
    print(f"Testing Threads scraper with: {url}")
    print(f"Grantee: {grantee_name}")
    print("="*60 + "\n")

    # Scrape the profile
    result = scraper.scrape(url, grantee_name)

    # Print results
    print("\n" + "="*60)
    print("SCRAPING RESULTS")
    print("="*60)
    print(f"Success: {result['success']}")
    print(f"Posts downloaded: {result['posts_downloaded']}")

    if result['errors']:
        print(f"\nErrors ({len(result['errors'])}):")
        for error in result['errors']:
            print(f"  - {error}")

    if result.get('engagement_metrics'):
        metrics = result['engagement_metrics']
        print(f"\nEngagement Metrics:")
        print(f"  Followers: {metrics['followers_count']:,}")
        print(f"  Total likes: {metrics['total_likes']:,}")
        print(f"  Total replies: {metrics['total_replies']:,}")
        print(f"  Total reposts: {metrics['total_reposts']:,}")
        print(f"  Avg engagement rate: {metrics['avg_engagement_rate']:.2f}%")

    print("="*60 + "\n")

    return result


def main():
    """Main entry point."""
    setup_logging()

    # Always test username extraction
    test_extract_username()

    # If URL provided, test scraping
    if len(sys.argv) < 2:
        print("\nTo test scraping, provide a URL:")
        print(f"  python {sys.argv[0]} <threads_url> [grantee_name]")
        print("\nExample:")
        print(f"  python {sys.argv[0]} 'https://www.threads.net/@zuck' 'Mark Zuckerberg'")
        return

    url = sys.argv[1]
    grantee_name = sys.argv[2] if len(sys.argv) > 2 else "Test Grantee"

    # Check for playwright installation
    try:
        import playwright
        print("✓ Playwright is installed")
    except ImportError:
        print("✗ Playwright is not installed!")
        print("\nInstall with:")
        print("  pip install playwright")
        print("  playwright install chromium")
        return

    # Run scraping test
    test_scraping(url, grantee_name)


if __name__ == "__main__":
    main()
