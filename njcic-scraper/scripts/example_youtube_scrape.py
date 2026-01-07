#!/usr/bin/env python3
"""
Example script demonstrating how to use the YouTube scraper.
"""
import sys
import logging
from pathlib import Path

# Add parent directory to path to import scrapers
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers import YouTubeScraper


def main():
    """Run example YouTube scrape."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize scraper
    scraper = YouTubeScraper(output_dir="output")

    # Example YouTube channels
    test_urls = [
        "https://www.youtube.com/@mkbhd",  # @handle format
        "https://www.youtube.com/c/Veritasium",  # /c/channel format
        "https://www.youtube.com/user/CGPGrey",  # /user/username format
    ]

    # Scrape each channel
    for url in test_urls:
        print(f"\n{'='*80}")
        print(f"Scraping: {url}")
        print('='*80)

        try:
            # Extract username
            username = scraper.extract_username(url)
            print(f"Channel identifier: {username}")

            # Scrape channel
            result = scraper.scrape(url, grantee_name="Example_Grantee")

            # Print results
            print(f"\nResults:")
            print(f"  Success: {result['success']}")
            print(f"  Posts Downloaded: {result['posts_downloaded']}")
            print(f"  Errors: {result['errors']}")
            print(f"\nEngagement Metrics:")
            for key, value in result['engagement_metrics'].items():
                print(f"  {key}: {value}")

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
