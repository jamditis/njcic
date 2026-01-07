"""
Test script for BlueSky scraper.
"""
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.bluesky import BlueSkyScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def test_extract_username():
    """Test username extraction from various URL formats."""
    scraper = BlueSkyScraper()

    test_cases = [
        ("https://bsky.app/profile/username.bsky.social", "username.bsky.social"),
        ("https://bsky.app/profile/custom.domain", "custom.domain"),
        ("username.bsky.social", "username.bsky.social"),
        ("https://bsky.app/profile/test.bsky.social/", "test.bsky.social"),
    ]

    print("Testing username extraction:")
    for url, expected in test_cases:
        try:
            result = scraper.extract_username(url)
            status = "✓" if result == expected else "✗"
            print(f"  {status} {url} -> {result}")
        except Exception as e:
            print(f"  ✗ {url} -> Error: {e}")
    print()


def test_scrape(handle: str = None):
    """
    Test scraping a BlueSky profile.

    Args:
        handle: BlueSky handle to test (default: use a popular account)
    """
    from pathlib import Path
    scraper = BlueSkyScraper(output_dir=Path("output"))

    # Use a well-known account for testing if none provided
    test_url = handle or "https://bsky.app/profile/bsky.app"

    print(f"Testing scrape for: {test_url}")
    result = scraper.scrape(test_url, grantee_name="test_grantee")

    print("\nResults:")
    print(f"  Success: {result['success']}")
    print(f"  Posts downloaded: {result['posts_downloaded']}")
    print(f"  Errors: {len(result.get('errors', []))}")
    if result.get('errors'):
        for i, error in enumerate(result['errors'][:5]):  # Show max 5 errors
            print(f"    - {error}")
        if len(result['errors']) > 5:
            print(f"    ... and {len(result['errors']) - 5} more errors")

    print("\nEngagement metrics:")
    metrics = result.get('engagement_metrics', {})
    for key, value in metrics.items():
        print(f"  {key}: {value}")

    if result.get('output_path'):
        print(f"\nOutput saved to: {result['output_path']}")
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("BlueSky Scraper Test")
    print("=" * 60)
    print()

    # Test username extraction
    test_extract_username()

    # Test scraping (uncomment to run actual API test)
    # test_scrape()

    print("Tests completed!")
