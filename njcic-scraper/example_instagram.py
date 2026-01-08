"""
Example script demonstrating how to use the Instagram scraper.

Usage:
    # Without credentials (limited functionality)
    python example_instagram.py

    # With credentials (set environment variables first)
    export INSTAGRAM_USERNAME="your_username"
    export INSTAGRAM_PASSWORD="your_password"
    python example_instagram.py

    # With session file
    python example_instagram.py --session-file data/instagram_session
"""

import argparse
import logging
import os
from pathlib import Path

from scrapers.instagram import InstagramScraper


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Scrape Instagram profiles')
    parser.add_argument(
        '--url',
        default='https://www.instagram.com/natgeo/',
        help='Instagram profile URL to scrape'
    )
    parser.add_argument(
        '--grantee-name',
        default='Example Grantee',
        help='Name of the grantee'
    )
    parser.add_argument(
        '--output-dir',
        default='output',
        help='Output directory for scraped data'
    )
    parser.add_argument(
        '--session-file',
        help='Path to Instagram session file'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create scraper instance
    scraper = InstagramScraper(
        output_dir=args.output_dir,
        session_file=args.session_file
    )

    # Test username extraction
    username = scraper.extract_username(args.url)
    print(f"\nExtracted username: {username}")

    # Perform scrape
    print(f"\nScraping {args.url}...")
    print("-" * 60)

    result = scraper.scrape(args.url, args.grantee_name)

    # Display results
    print("\nResults:")
    print("-" * 60)
    print(f"Success: {result['success']}")
    print(f"Posts downloaded: {result['posts_downloaded']}")
    print(f"Errors: {len(result['errors'])}")

    if result['errors']:
        print("\nErrors encountered:")
        for error in result['errors']:
            print(f"  - {error}")

    if result['engagement_metrics']:
        print("\nEngagement Metrics:")
        metrics = result['engagement_metrics']
        print(f"  Followers: {metrics.get('followers_count', 0):,}")
        print(f"  Following: {metrics.get('following_count', 0):,}")
        print(f"  Total likes: {metrics.get('total_likes', 0):,}")
        print(f"  Total comments: {metrics.get('total_comments', 0):,}")
        print(f"  Average engagement rate: {metrics.get('avg_engagement_rate', 0):.2f}%")

        if metrics.get('total_video_views'):
            print(f"  Total video views: {metrics.get('total_video_views', 0):,}")

    # Show output location
    if username:
        output_path = scraper._create_output_directory(args.grantee_name, username)
        print(f"\nMetadata saved to: {output_path}/metadata.json")


if __name__ == '__main__':
    main()
