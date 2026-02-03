#!/usr/bin/env python3
"""
NJCIC Internal Social Media Scraper

This script scrapes social media metrics for NJCIC's own organizational accounts
(not grantee accounts). It runs weekly to provide internal staff with a snapshot
of the consortium's social media performance.

Usage:
    python scrape_internal.py                    # Run full scrape
    python scrape_internal.py --platforms twitter,instagram  # Specific platforms only
    python scrape_internal.py --output-dir /custom/path      # Custom output directory
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import config

# Import all scrapers
from scrapers.twitter import TwitterScraper
from scrapers.bluesky import BlueSkyScraper
from scrapers.instagram_playwright import InstagramPlaywrightScraper
from scrapers.facebook import FacebookScraper
from scrapers.linkedin import LinkedInScraper
from scrapers.tiktok import TikTokScraper
from scrapers.youtube import YouTubeScraper
from scrapers.threads import ThreadsScraper

# Constants
BASE_DIR = Path(__file__).resolve().parent
INTERNAL_ACCOUNTS_PATH = BASE_DIR / "data" / "njcic-internal-accounts.json"
INTERNAL_OUTPUT_DIR = BASE_DIR / "output" / "njcic-internal"
INTERNAL_DASHBOARD_DATA_PATH = BASE_DIR / "output" / "njcic-internal-metrics.json"

# Platform to scraper class mapping
PLATFORM_SCRAPERS = {
    'twitter': TwitterScraper,
    'bluesky': BlueSkyScraper,
    'instagram': InstagramPlaywrightScraper,
    'facebook': FacebookScraper,
    'linkedin': LinkedInScraper,
    'tiktok': TikTokScraper,
    'youtube': YouTubeScraper,
    'threads': ThreadsScraper,
}


class InternalMetricsScraper:
    """Scraper for NJCIC's own organizational social media accounts."""

    def __init__(
        self,
        platforms: Optional[List[str]] = None,
        output_dir: Optional[Path] = None,
        max_posts: int = 50
    ):
        """
        Initialize the internal metrics scraper.

        Args:
            platforms: List of platform names to scrape (None = all enabled platforms)
            output_dir: Custom output directory
            max_posts: Maximum posts to scrape per platform
        """
        self.output_dir = output_dir or INTERNAL_OUTPUT_DIR
        self.max_posts = max_posts

        # Load internal accounts configuration
        self.config = self._load_config()

        # Filter to only enabled platforms
        self.platforms = self._get_enabled_platforms(platforms)

        # Initialize logging
        self.logger = self._setup_logging()

        # Statistics tracking (must be initialized before scrapers)
        self.stats = {
            'start_time': None,
            'end_time': None,
            'platforms': {},
            'errors': []
        }

        # Initialize scrapers
        self.scrapers: Dict[str, Any] = {}
        self._initialize_scrapers()

    def _load_config(self) -> Dict[str, Any]:
        """Load internal accounts configuration."""
        if not INTERNAL_ACCOUNTS_PATH.exists():
            raise FileNotFoundError(
                f"Internal accounts configuration not found: {INTERNAL_ACCOUNTS_PATH}"
            )

        with open(INTERNAL_ACCOUNTS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _get_enabled_platforms(self, requested_platforms: Optional[List[str]] = None) -> List[str]:
        """Get list of enabled platforms from config."""
        social_accounts = self.config.get('social_accounts', {})
        enabled = [
            platform
            for platform, data in social_accounts.items()
            if data.get('enabled', False) and data.get('url')
        ]

        if requested_platforms:
            # Filter to only requested platforms that are also enabled
            return [p for p in requested_platforms if p in enabled]

        return enabled

    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger('InternalMetricsScraper')
        logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)

        # File handler
        config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(config.LOGS_DIR / 'internal_scraper.log')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(config.LOG_FORMAT)
        file_handler.setFormatter(file_formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

    def _initialize_scrapers(self) -> None:
        """Initialize all platform scrapers."""
        self.logger.info(f"Initializing scrapers for platforms: {', '.join(self.platforms)}")

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        for platform in self.platforms:
            if platform not in PLATFORM_SCRAPERS:
                self.logger.warning(f"Unknown platform: {platform}, skipping")
                continue

            try:
                scraper_class = PLATFORM_SCRAPERS[platform]

                # Initialize with platform-specific parameters
                if platform == 'twitter':
                    self.scrapers[platform] = scraper_class(
                        output_dir=self.output_dir,
                        max_posts=self.max_posts
                    )
                elif platform in ['facebook', 'linkedin']:
                    self.scrapers[platform] = scraper_class(
                        output_dir=self.output_dir,
                        headless=True
                    )
                elif platform == 'threads':
                    self.scrapers[platform] = scraper_class(
                        output_dir=str(self.output_dir),
                        headless=True,
                        timeout=30000
                    )
                elif platform == 'instagram':
                    self.scrapers[platform] = scraper_class(
                        output_dir=self.output_dir,
                        headless=True
                    )
                else:
                    self.scrapers[platform] = scraper_class(
                        output_dir=self.output_dir
                    )

                self.logger.info(f"Initialized {platform} scraper")

                # Initialize stats for this platform
                self.stats['platforms'][platform] = {
                    'success': False,
                    'posts': 0,
                    'followers': 0,
                    'engagement': 0,
                    'error': None
                }

            except Exception as e:
                self.logger.error(f"Failed to initialize {platform} scraper: {e}")
                self.stats['errors'].append({
                    'type': 'scraper_init',
                    'platform': platform,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })

    def _scrape_platform(self, platform: str, url: str) -> Dict[str, Any]:
        """
        Scrape a single platform.

        Args:
            platform: Platform name
            url: Social media URL

        Returns:
            Scraping result dictionary
        """
        org_name = self.config.get('organization', {}).get('name', 'NJCIC')

        if platform not in self.scrapers:
            return {
                'success': False,
                'error': f'Scraper not initialized for {platform}',
                'posts_downloaded': 0
            }

        scraper = self.scrapers[platform]

        try:
            self.logger.info(f"Scraping {platform} for {org_name}: {url}")
            result = scraper.scrape(
                url=url,
                grantee_name=org_name,
                max_posts=self.max_posts
            )
            return result

        except Exception as e:
            self.logger.error(f"Error scraping {platform}: {e}")
            return {
                'success': False,
                'error': str(e),
                'posts_downloaded': 0
            }

    def scrape_all_platforms(self) -> Dict[str, Any]:
        """
        Scrape all enabled platforms.

        Returns:
            Combined results dictionary
        """
        social_accounts = self.config.get('social_accounts', {})
        org_info = self.config.get('organization', {})

        results = {
            'organization': org_info,
            'scraped_at': datetime.now().isoformat(),
            'platforms': {},
            'summary': {
                'total_posts': 0,
                'total_followers': 0,
                'total_engagement': 0,
                'platforms_scraped': 0,
                'platforms_failed': 0
            }
        }

        for platform in self.platforms:
            account_data = social_accounts.get(platform, {})
            url = account_data.get('url')

            if not url:
                self.logger.warning(f"No URL configured for {platform}, skipping")
                continue

            # Scrape the platform
            result = self._scrape_platform(platform, url)

            # Process result
            platform_result = {
                'url': url,
                'username': account_data.get('username'),
                'success': result.get('success', False),
                'posts': result.get('posts_downloaded', 0),
                'followers': result.get('followers', 0),
                'engagement_metrics': result.get('engagement_metrics', {}),
                'error': result.get('error')
            }

            # Calculate total engagement
            metrics = result.get('engagement_metrics', {})
            total_engagement = sum(
                metrics.get(metric, 0)
                for metric in config.ENGAGEMENT_METRICS
            )
            platform_result['total_engagement'] = total_engagement

            # Update summary
            if result.get('success'):
                results['summary']['total_posts'] += platform_result['posts']
                results['summary']['total_followers'] += platform_result['followers']
                results['summary']['total_engagement'] += total_engagement
                results['summary']['platforms_scraped'] += 1

                # Update stats
                self.stats['platforms'][platform] = {
                    'success': True,
                    'posts': platform_result['posts'],
                    'followers': platform_result['followers'],
                    'engagement': total_engagement,
                    'error': None
                }
            else:
                results['summary']['platforms_failed'] += 1
                self.stats['platforms'][platform] = {
                    'success': False,
                    'posts': 0,
                    'followers': 0,
                    'engagement': 0,
                    'error': result.get('error')
                }
                self.stats['errors'].append({
                    'type': 'scraping',
                    'platform': platform,
                    'url': url,
                    'error': result.get('error', 'Unknown error'),
                    'timestamp': datetime.now().isoformat()
                })

            results['platforms'][platform] = platform_result

        return results

    def generate_dashboard_data(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate dashboard-ready data from scraping results.

        Args:
            results: Scraping results

        Returns:
            Dashboard data dictionary
        """
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()

        dashboard_data = {
            'organization': results['organization'],
            'lastUpdated': datetime.now().isoformat(),
            'scrapingDuration': f"{int(duration)}s",
            'summary': {
                'totalPosts': results['summary']['total_posts'],
                'totalFollowers': results['summary']['total_followers'],
                'totalEngagement': results['summary']['total_engagement'],
                'platformsTracked': results['summary']['platforms_scraped'],
                'engagementRate': round(
                    results['summary']['total_engagement'] / max(results['summary']['total_posts'], 1),
                    2
                )
            },
            'platforms': {},
            'weeklySnapshot': {
                'weekOf': datetime.now().strftime('%Y-%m-%d'),
                'dayOfWeek': 'Monday'
            },
            'history': []  # Can be extended to track historical data
        }

        # Platform colors for visualization
        platform_colors = {
            'twitter': '#1DA1F2',
            'instagram': '#E1306C',
            'facebook': '#1877F2',
            'linkedin': '#0A66C2',
            'youtube': '#FF0000',
            'tiktok': '#000000',
            'bluesky': '#0085FF',
            'threads': '#000000'
        }

        for platform, data in results['platforms'].items():
            dashboard_data['platforms'][platform] = {
                'url': data['url'],
                'username': data['username'],
                'posts': data['posts'],
                'followers': data['followers'],
                'engagement': data['total_engagement'],
                'engagementRate': round(
                    data['total_engagement'] / max(data['posts'], 1),
                    2
                ),
                'metrics': data['engagement_metrics'],
                'color': platform_colors.get(platform, '#666666'),
                'success': data['success']
            }

        return dashboard_data

    def save_results(self, dashboard_data: Dict[str, Any]) -> None:
        """
        Save dashboard data to file.

        Args:
            dashboard_data: Dashboard-ready data
        """
        INTERNAL_DASHBOARD_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(INTERNAL_DASHBOARD_DATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(dashboard_data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Dashboard data saved to: {INTERNAL_DASHBOARD_DATA_PATH}")

    def run(self) -> Dict[str, Any]:
        """
        Run the complete scraping process.

        Returns:
            Dashboard data dictionary
        """
        self.stats['start_time'] = datetime.now()

        self.logger.info("=" * 70)
        self.logger.info("NJCIC Internal Social Media Scraper - Starting")
        self.logger.info("=" * 70)
        self.logger.info(f"Organization: {self.config.get('organization', {}).get('name')}")
        self.logger.info(f"Platforms: {', '.join(self.platforms)}")
        self.logger.info(f"Max posts per platform: {self.max_posts}")
        self.logger.info("")

        # Scrape all platforms
        results = self.scrape_all_platforms()

        self.stats['end_time'] = datetime.now()

        # Generate dashboard data
        dashboard_data = self.generate_dashboard_data(results)

        # Save results
        self.save_results(dashboard_data)

        # Print summary
        self._print_summary(dashboard_data)

        return dashboard_data

    def _print_summary(self, dashboard_data: Dict[str, Any]) -> None:
        """Print execution summary to console."""
        self.logger.info("")
        self.logger.info("=" * 70)
        self.logger.info("SCRAPING COMPLETE")
        self.logger.info("=" * 70)
        self.logger.info(f"Duration: {dashboard_data['scrapingDuration']}")
        self.logger.info(f"Total posts: {dashboard_data['summary']['totalPosts']}")
        self.logger.info(f"Total followers: {dashboard_data['summary']['totalFollowers']:,}")
        self.logger.info(f"Total engagement: {dashboard_data['summary']['totalEngagement']:,}")
        self.logger.info("")
        self.logger.info("Platform breakdown:")

        for platform, data in dashboard_data['platforms'].items():
            status = "OK" if data['success'] else "FAILED"
            self.logger.info(
                f"  {platform.capitalize():12} [{status:6}] - "
                f"Posts: {data['posts']:3}, "
                f"Followers: {data['followers']:,}, "
                f"Engagement: {data['engagement']:,}"
            )

        self.logger.info("")
        self.logger.info(f"Dashboard data saved to: {INTERNAL_DASHBOARD_DATA_PATH}")
        self.logger.info("=" * 70)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="NJCIC Internal Social Media Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Run full scrape
  %(prog)s --platforms twitter,instagram      # Specific platforms only
  %(prog)s --max-posts 100                    # More posts per platform
        """
    )

    parser.add_argument(
        '--platforms',
        type=str,
        metavar='LIST',
        help='Comma-separated list of platforms to scrape (default: all enabled)'
    )

    parser.add_argument(
        '--max-posts',
        type=int,
        default=50,
        metavar='N',
        help='Maximum posts to scrape per platform (default: 50)'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        metavar='PATH',
        help='Custom output directory'
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()

    # Parse platforms
    platforms = None
    if args.platforms:
        platforms = [p.strip().lower() for p in args.platforms.split(',')]

    # Parse output directory
    output_dir = Path(args.output_dir) if args.output_dir else None

    # Initialize and run scraper
    try:
        scraper = InternalMetricsScraper(
            platforms=platforms,
            output_dir=output_dir,
            max_posts=args.max_posts
        )

        scraper.run()
        print("\nInternal metrics scraping completed successfully!")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
