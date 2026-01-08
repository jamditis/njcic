"""
Example usage of BlueSky scraper.

This script demonstrates how to scrape BlueSky profiles using the BlueSky scraper.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.bluesky import BlueSkyScraper
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def main():
    """Example usage of BlueSky scraper."""

    # Initialize scraper
    scraper = BlueSkyScraper()

    # Example 1: Scrape the official BlueSky account
    print("Example 1: Scraping BlueSky official account")
    print("-" * 60)

    result = scraper.scrape(
        url="https://bsky.app/profile/bsky.app",
        grantee_name="bluesky_official",
        max_posts=10  # Fetch only 10 posts for this example
    )

    print(f"Success: {result['success']}")
    print(f"Posts downloaded: {result['posts_downloaded']}")
    print(f"Output path: {result['output_path']}")

    # Display engagement metrics
    print("\nEngagement Metrics:")
    metrics = result['engagement_metrics']
    print(f"  Followers: {metrics.get('followers_count', 0)}")
    print(f"  Total likes: {metrics.get('total_likes', 0)}")
    print(f"  Total reposts: {metrics.get('total_reposts', 0)}")
    print(f"  Total replies: {metrics.get('total_replies', 0)}")
    print(f"  Avg engagement rate: {metrics.get('avg_engagement_rate', 0):.2f}%")

    # Display any errors
    if result['errors']:
        print(f"\nErrors encountered: {len(result['errors'])}")
        for error in result['errors'][:3]:  # Show first 3 errors
            print(f"  - {error}")

    print("\n" + "=" * 60 + "\n")

    # Example 2: Using just a handle instead of full URL
    print("Example 2: Using a handle directly")
    print("-" * 60)

    result2 = scraper.scrape(
        url="bsky.app",  # Just the handle
        grantee_name="bluesky_direct_handle",
        max_posts=5
    )

    print(f"Success: {result2['success']}")
    print(f"Posts downloaded: {result2['posts_downloaded']}")

    print("\n" + "=" * 60)
    print("Examples completed!")


if __name__ == "__main__":
    main()
