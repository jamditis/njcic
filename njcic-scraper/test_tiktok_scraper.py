"""
Test script for TikTok scraper.

Usage:
    python test_tiktok_scraper.py
"""
import logging
import sys
from pathlib import Path

# Add scrapers directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.tiktok import TikTokScraper


def setup_logging():
    """Configure logging for the test script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('tiktok_scraper_test.log')
        ]
    )


def main():
    """Test the TikTok scraper."""
    setup_logging()
    logger = logging.getLogger(__name__)

    # Test URLs
    test_cases = [
        {
            "url": "https://www.tiktok.com/@thehobokengirl",
            "grantee_name": "Hoboken Girl",
        },
        {
            "url": "https://www.tiktok.com/@thegardenstatepodcast",
            "grantee_name": "Garden State Podcast",
        },
        {
            "url": "tiktok.com/@njhooprecruit",
            "grantee_name": "NJ Hoop Recruit",
        },
    ]

    # Initialize scraper
    scraper = TikTokScraper(output_dir="output", max_posts=25)

    logger.info("=" * 80)
    logger.info("TikTok Scraper Test")
    logger.info("=" * 80)

    # Test each URL
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\nTest {i}/{len(test_cases)}: {test_case['grantee_name']}")
        logger.info(f"URL: {test_case['url']}")
        logger.info("-" * 80)

        # Test username extraction
        username = scraper.extract_username(test_case['url'])
        logger.info(f"✓ Extracted username: @{username}")

        # Test scraping
        result = scraper.scrape(test_case['url'], test_case['grantee_name'])

        # Display results
        logger.info(f"\nResults:")
        logger.info(f"  Success: {result['success']}")
        logger.info(f"  Posts downloaded: {result['posts_downloaded']}")

        if result['errors']:
            logger.error(f"  Errors: {result['errors']}")

        metrics = result['engagement_metrics']
        logger.info(f"\nEngagement Metrics:")
        logger.info(f"  Followers: {metrics['followers_count'] or 'N/A'}")
        logger.info(f"  Total views: {metrics['total_views']:,}")
        logger.info(f"  Total likes: {metrics['total_likes']:,}")
        logger.info(f"  Total comments: {metrics['total_comments']:,}")
        logger.info(f"  Total shares: {metrics['total_shares']:,}")
        logger.info(f"  Avg engagement rate: {metrics['avg_engagement_rate']}%")

        logger.info("=" * 80)


if __name__ == "__main__":
    main()
