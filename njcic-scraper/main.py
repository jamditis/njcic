#!/usr/bin/env python3
"""
NJCIC Social Media Scraper - Main Orchestrator

This script orchestrates the scraping of social media platforms for NJCIC grantees.
It loads grantee data, initializes all platform scrapers, processes each grantee,
and generates comprehensive reports.

Usage:
    python main.py                              # Run full scrape
    python main.py --test                       # Test with first grantee only
    python main.py --start 10 --end 20          # Process grantees 10-20
    python main.py --platforms twitter,facebook # Only scrape specific platforms
    python main.py --extract-urls               # Extract URLs before scraping
    python main.py --skip-existing              # Skip grantees with existing data
"""

import argparse
import asyncio
import csv
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

import config
from tqdm import tqdm

# Import all scrapers
from scrapers.twitter import TwitterScraper
from scrapers.bluesky import BlueSkyScraper
from scrapers.instagram import InstagramScraper
from scrapers.facebook import FacebookScraper
from scrapers.linkedin import LinkedInScraper
from scrapers.tiktok import TikTokScraper
from scrapers.youtube import YouTubeScraper
from scrapers.threads import ThreadsScraper


# Constants
GRANTEES_DATA_PATH = Path("/home/user/njcic/njcic-scraper/data/grantees_with_social.json")
SCRAPING_REPORT_PATH = Path("/home/user/njcic/njcic-scraper/output/scraping_report.json")
ENGAGEMENT_SUMMARY_PATH = Path("/home/user/njcic/njcic-scraper/output/engagement_summary.csv")

# Platform to scraper class mapping
PLATFORM_SCRAPERS = {
    'twitter': TwitterScraper,
    'bluesky': BlueSkyScraper,
    'instagram': InstagramScraper,
    'facebook': FacebookScraper,
    'linkedin': LinkedInScraper,
    'tiktok': TikTokScraper,
    'youtube': YouTubeScraper,
    'threads': ThreadsScraper,
}


class ScraperOrchestrator:
    """Main orchestrator for coordinating all social media scrapers."""

    def __init__(
        self,
        platforms: Optional[List[str]] = None,
        skip_existing: bool = False,
        max_posts: int = 25
    ):
        """
        Initialize the scraper orchestrator.

        Args:
            platforms: List of platform names to scrape (None = all platforms)
            skip_existing: Whether to skip grantees that already have data
            max_posts: Maximum posts to scrape per platform
        """
        self.platforms = platforms or list(PLATFORM_SCRAPERS.keys())
        self.skip_existing = skip_existing
        self.max_posts = max_posts

        # Initialize logging
        self.logger = self._setup_logging()

        # Statistics tracking (must be before _initialize_scrapers)
        self.stats = {
            'start_time': None,
            'end_time': None,
            'grantees_processed': 0,
            'grantees_skipped': 0,
            'grantees_failed': 0,
            'platforms': {},
            'errors': []
        }

        # Initialize scrapers
        self.scrapers: Dict[str, Any] = {}
        self._initialize_scrapers()

    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger('ScraperOrchestrator')
        logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)

        # File handler
        file_handler = logging.FileHandler(config.LOGS_DIR / 'orchestrator.log')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(config.LOG_FORMAT)
        file_handler.setFormatter(file_formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

    def _initialize_scrapers(self) -> None:
        """Initialize all platform scrapers."""
        self.logger.info(f"Initializing scrapers for platforms: {', '.join(self.platforms)}")

        for platform in self.platforms:
            if platform not in PLATFORM_SCRAPERS:
                self.logger.warning(f"Unknown platform: {platform}, skipping")
                continue

            try:
                scraper_class = PLATFORM_SCRAPERS[platform]

                # Initialize with platform-specific parameters
                if platform == 'twitter':
                    self.scrapers[platform] = scraper_class(
                        output_dir=config.OUTPUT_DIR,
                        max_posts=self.max_posts
                    )
                elif platform in ['facebook', 'linkedin']:
                    self.scrapers[platform] = scraper_class(
                        output_dir=config.OUTPUT_DIR,
                        headless=True
                    )
                elif platform == 'threads':
                    self.scrapers[platform] = scraper_class(
                        output_dir=str(config.OUTPUT_DIR),
                        headless=True,
                        timeout=30000
                    )
                elif platform == 'instagram':
                    self.scrapers[platform] = scraper_class(
                        output_dir=str(config.OUTPUT_DIR),
                        session_file=None
                    )
                else:
                    self.scrapers[platform] = scraper_class(
                        output_dir=config.OUTPUT_DIR
                    )

                self.logger.info(f"✓ Initialized {platform} scraper")

                # Initialize stats for this platform
                self.stats['platforms'][platform] = {
                    'attempted': 0,
                    'successful': 0,
                    'failed': 0,
                    'skipped': 0,
                    'total_posts': 0,
                    'total_engagement': 0
                }

            except Exception as e:
                self.logger.error(f"Failed to initialize {platform} scraper: {e}")
                self.stats['errors'].append({
                    'type': 'scraper_init',
                    'platform': platform,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })

    def _should_skip_grantee(self, grantee: Dict[str, Any]) -> bool:
        """
        Check if a grantee should be skipped.

        Args:
            grantee: Grantee dictionary

        Returns:
            True if should skip, False otherwise
        """
        if not self.skip_existing:
            return False

        # Check if grantee has existing data for any platform
        grantee_name = grantee.get('name', 'Unknown')
        safe_name = self._sanitize_name(grantee_name)

        for platform in self.platforms:
            output_path = config.OUTPUT_DIR / safe_name / platform
            metadata_file = output_path / "metadata.json"

            if metadata_file.exists():
                self.logger.debug(f"Skipping {grantee_name} - existing data found")
                return True

        return False

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """
        Sanitize grantee name for filesystem.

        Args:
            name: Original name

        Returns:
            Sanitized name safe for filesystem
        """
        return "".join(
            c if c.isalnum() or c in (' ', '-', '_') else '_'
            for c in name
        ).strip().replace(' ', '_')

    def _scrape_platform(
        self,
        platform: str,
        url: str,
        grantee_name: str
    ) -> Dict[str, Any]:
        """
        Scrape a single platform for a grantee.

        Args:
            platform: Platform name
            url: Social media URL
            grantee_name: Grantee name

        Returns:
            Scraping result dictionary
        """
        if platform not in self.scrapers:
            return {
                'success': False,
                'error': f'Scraper not initialized for {platform}',
                'posts_downloaded': 0
            }

        scraper = self.scrapers[platform]

        try:
            self.logger.debug(f"Scraping {platform} for {grantee_name}: {url}")
            result = scraper.scrape(
                url=url,
                grantee_name=grantee_name,
                max_posts=self.max_posts
            )

            return result

        except Exception as e:
            self.logger.error(f"Error scraping {platform} for {grantee_name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'posts_downloaded': 0
            }

    def process_grantee(self, grantee: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single grantee across all platforms.

        Args:
            grantee: Grantee dictionary with social media URLs

        Returns:
            Results dictionary for this grantee
        """
        grantee_name = grantee.get('name', 'Unknown')
        social = grantee.get('social', {})

        results = {
            'name': grantee_name,
            'website': grantee.get('website'),
            'platforms': {},
            'summary': {
                'total_posts': 0,
                'total_followers': 0,
                'total_engagement': 0,
                'platforms_scraped': 0,
                'platforms_failed': 0
            }
        }

        # Process each platform
        for platform in self.platforms:
            url = social.get(platform)

            if not url:
                self.stats['platforms'][platform]['skipped'] += 1
                continue

            self.stats['platforms'][platform]['attempted'] += 1

            # Scrape the platform
            result = self._scrape_platform(platform, url, grantee_name)

            # Update statistics
            if result.get('success'):
                self.stats['platforms'][platform]['successful'] += 1
                self.stats['platforms'][platform]['total_posts'] += result.get('posts_downloaded', 0)

                # Calculate engagement
                metrics = result.get('engagement_metrics', {})
                engagement = sum(
                    metrics.get(metric, 0)
                    for metric in config.ENGAGEMENT_METRICS
                )
                self.stats['platforms'][platform]['total_engagement'] += engagement

                results['summary']['total_posts'] += result.get('posts_downloaded', 0)
                results['summary']['total_engagement'] += engagement
                results['summary']['platforms_scraped'] += 1

            else:
                self.stats['platforms'][platform]['failed'] += 1
                results['summary']['platforms_failed'] += 1

                # Log error
                self.stats['errors'].append({
                    'type': 'scraping',
                    'grantee': grantee_name,
                    'platform': platform,
                    'url': url,
                    'error': result.get('error', 'Unknown error'),
                    'timestamp': datetime.now().isoformat()
                })

            # Store result
            results['platforms'][platform] = {
                'url': url,
                'success': result.get('success', False),
                'posts_downloaded': result.get('posts_downloaded', 0),
                'engagement_metrics': result.get('engagement_metrics', {}),
                'output_path': result.get('output_path', ''),
                'error': result.get('error')
            }

        return results

    def process_all_grantees(
        self,
        grantees: List[Dict[str, Any]],
        start_idx: int = 0,
        end_idx: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Process all grantees in the specified range.

        Args:
            grantees: List of grantee dictionaries
            start_idx: Starting index
            end_idx: Ending index (None = all)

        Returns:
            List of results for all processed grantees
        """
        # Determine range
        end_idx = end_idx or len(grantees)
        grantees_to_process = grantees[start_idx:end_idx]

        self.logger.info(f"Processing {len(grantees_to_process)} grantees (indices {start_idx}-{end_idx})")

        results = []

        # Process with progress bar
        with tqdm(total=len(grantees_to_process), desc="Processing grantees") as pbar:
            for grantee in grantees_to_process:
                grantee_name = grantee.get('name', 'Unknown')
                pbar.set_description(f"Processing: {grantee_name[:40]}")

                # Check if should skip
                if self._should_skip_grantee(grantee):
                    self.stats['grantees_skipped'] += 1
                    pbar.update(1)
                    continue

                # Process grantee
                try:
                    result = self.process_grantee(grantee)
                    results.append(result)
                    self.stats['grantees_processed'] += 1

                except Exception as e:
                    self.logger.error(f"Failed to process {grantee_name}: {e}")
                    self.stats['grantees_failed'] += 1
                    self.stats['errors'].append({
                        'type': 'grantee_processing',
                        'grantee': grantee_name,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })

                pbar.update(1)

        return results

    def generate_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate comprehensive scraping report.

        Args:
            results: List of grantee results

        Returns:
            Report dictionary
        """
        self.logger.info("Generating comprehensive report...")

        # Calculate duration
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()

        report = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'duration_seconds': duration,
                'duration_formatted': f"{int(duration // 3600)}h {int((duration % 3600) // 60)}m {int(duration % 60)}s",
                'platforms_enabled': self.platforms,
                'max_posts_per_account': self.max_posts
            },
            'summary': {
                'total_grantees_attempted': len(results),
                'grantees_processed': self.stats['grantees_processed'],
                'grantees_skipped': self.stats['grantees_skipped'],
                'grantees_failed': self.stats['grantees_failed'],
                'total_errors': len(self.stats['errors'])
            },
            'platform_stats': {},
            'grantee_results': results,
            'errors': self.stats['errors']
        }

        # Add platform statistics
        for platform, stats in self.stats['platforms'].items():
            report['platform_stats'][platform] = {
                'attempted': stats['attempted'],
                'successful': stats['successful'],
                'failed': stats['failed'],
                'skipped': stats['skipped'],
                'success_rate': f"{(stats['successful'] / stats['attempted'] * 100) if stats['attempted'] > 0 else 0:.1f}%",
                'total_posts_collected': stats['total_posts'],
                'total_engagement': stats['total_engagement']
            }

        # Save to file
        SCRAPING_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SCRAPING_REPORT_PATH, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Report saved to: {SCRAPING_REPORT_PATH}")

        return report

    def generate_csv_summary(self, results: List[Dict[str, Any]]) -> None:
        """
        Generate CSV summary of engagement metrics.

        Args:
            results: List of grantee results
        """
        self.logger.info("Generating CSV engagement summary...")

        # Prepare CSV data
        csv_rows = []

        for result in results:
            row = {
                'Grantee Name': result['name'],
                'Website': result.get('website', ''),
                'Total Posts': result['summary']['total_posts'],
                'Total Engagement': result['summary']['total_engagement'],
                'Platforms Scraped': result['summary']['platforms_scraped'],
                'Platforms Failed': result['summary']['platforms_failed']
            }

            # Add per-platform metrics
            for platform in self.platforms:
                platform_data = result['platforms'].get(platform, {})

                # Posts
                row[f'{platform.capitalize()} Posts'] = platform_data.get('posts_downloaded', 0)

                # Engagement
                metrics = platform_data.get('engagement_metrics', {})
                engagement = sum(metrics.get(m, 0) for m in config.ENGAGEMENT_METRICS)
                row[f'{platform.capitalize()} Engagement'] = engagement

                # URL
                row[f'{platform.capitalize()} URL'] = platform_data.get('url', '')

            csv_rows.append(row)

        # Write CSV
        if csv_rows:
            ENGAGEMENT_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)

            with open(ENGAGEMENT_SUMMARY_PATH, 'w', newline='', encoding='utf-8') as f:
                # Get all field names from first row
                fieldnames = list(csv_rows[0].keys())

                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_rows)

            self.logger.info(f"CSV summary saved to: {ENGAGEMENT_SUMMARY_PATH}")

    def run(
        self,
        grantees: List[Dict[str, Any]],
        start_idx: int = 0,
        end_idx: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run the complete scraping orchestration.

        Args:
            grantees: List of grantee dictionaries
            start_idx: Starting index
            end_idx: Ending index (None = all)

        Returns:
            Final report dictionary
        """
        self.stats['start_time'] = datetime.now()

        self.logger.info("=" * 70)
        self.logger.info("NJCIC Social Media Scraper - Starting")
        self.logger.info("=" * 70)
        self.logger.info(f"Platforms: {', '.join(self.platforms)}")
        self.logger.info(f"Max posts per account: {self.max_posts}")
        self.logger.info(f"Skip existing: {self.skip_existing}")
        self.logger.info("")

        # Process all grantees
        results = self.process_all_grantees(grantees, start_idx, end_idx)

        self.stats['end_time'] = datetime.now()

        # Generate reports
        report = self.generate_report(results)
        self.generate_csv_summary(results)

        # Print summary
        self._print_summary(report)

        return report

    def _print_summary(self, report: Dict[str, Any]) -> None:
        """Print execution summary to console."""
        self.logger.info("")
        self.logger.info("=" * 70)
        self.logger.info("SCRAPING COMPLETE")
        self.logger.info("=" * 70)
        self.logger.info(f"Duration: {report['metadata']['duration_formatted']}")
        self.logger.info(f"Grantees processed: {report['summary']['grantees_processed']}")
        self.logger.info(f"Grantees skipped: {report['summary']['grantees_skipped']}")
        self.logger.info(f"Grantees failed: {report['summary']['grantees_failed']}")
        self.logger.info("")
        self.logger.info("Platform Statistics:")

        for platform, stats in report['platform_stats'].items():
            self.logger.info(f"  {platform.capitalize():12} - Success: {stats['successful']:3}/{stats['attempted']:3} "
                           f"({stats['success_rate']:>5}), Posts: {stats['total_posts_collected']:4}, "
                           f"Engagement: {stats['total_engagement']:,}")

        self.logger.info("")
        self.logger.info(f"Reports saved:")
        self.logger.info(f"  JSON: {SCRAPING_REPORT_PATH}")
        self.logger.info(f"  CSV:  {ENGAGEMENT_SUMMARY_PATH}")
        self.logger.info("=" * 70)


def load_grantee_data() -> List[Dict[str, Any]]:
    """
    Load grantee data from JSON file.

    Returns:
        List of grantee dictionaries

    Raises:
        FileNotFoundError: If data file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    if not GRANTEES_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Grantee data file not found: {GRANTEES_DATA_PATH}\n"
            f"Run with --extract-urls to generate it first."
        )

    with open(GRANTEES_DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data.get('grantees', [])


def extract_urls() -> None:
    """Run URL extraction script."""
    import subprocess

    extraction_script = Path("/home/user/njcic/njcic-scraper/scripts/extract_social_urls.py")

    if not extraction_script.exists():
        print(f"Error: URL extraction script not found: {extraction_script}")
        sys.exit(1)

    print("Running URL extraction...")
    result = subprocess.run(
        [sys.executable, str(extraction_script)],
        cwd=extraction_script.parent
    )

    if result.returncode != 0:
        print("URL extraction failed!")
        sys.exit(1)

    print("URL extraction completed successfully!")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="NJCIC Social Media Scraper - Main Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Run full scrape
  %(prog)s --test                       # Test with first grantee only
  %(prog)s --start 10 --end 20          # Process grantees 10-20
  %(prog)s --platforms twitter,facebook # Only scrape Twitter and Facebook
  %(prog)s --extract-urls               # Extract URLs before scraping
  %(prog)s --skip-existing              # Skip grantees with existing data
        """
    )

    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode: only process the first grantee'
    )

    parser.add_argument(
        '--start',
        type=int,
        default=0,
        metavar='N',
        help='Start from grantee index N (default: 0)'
    )

    parser.add_argument(
        '--end',
        type=int,
        metavar='N',
        help='End at grantee index N (default: all)'
    )

    parser.add_argument(
        '--platforms',
        type=str,
        metavar='LIST',
        help='Comma-separated list of platforms to scrape (default: all)'
    )

    parser.add_argument(
        '--extract-urls',
        action='store_true',
        help='Run URL extraction before scraping'
    )

    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip grantees that already have scraped data'
    )

    parser.add_argument(
        '--max-posts',
        type=int,
        default=25,
        metavar='N',
        help='Maximum posts to scrape per account (default: 25)'
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()

    # Extract URLs if requested
    if args.extract_urls:
        extract_urls()

    # Load grantee data
    try:
        grantees = load_grantee_data()
        print(f"Loaded {len(grantees)} grantees from {GRANTEES_DATA_PATH}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        sys.exit(1)

    # Parse platforms
    platforms = None
    if args.platforms:
        platforms = [p.strip().lower() for p in args.platforms.split(',')]
        # Validate platforms
        invalid = [p for p in platforms if p not in PLATFORM_SCRAPERS]
        if invalid:
            print(f"Error: Invalid platforms: {', '.join(invalid)}")
            print(f"Valid platforms: {', '.join(PLATFORM_SCRAPERS.keys())}")
            sys.exit(1)

    # Determine range
    start_idx = args.start
    end_idx = args.end

    if args.test:
        print("TEST MODE: Processing only the first grantee")
        start_idx = 0
        end_idx = 1

    # Validate range
    if start_idx < 0 or start_idx >= len(grantees):
        print(f"Error: Start index {start_idx} out of range (0-{len(grantees)-1})")
        sys.exit(1)

    if end_idx is not None and (end_idx <= start_idx or end_idx > len(grantees)):
        print(f"Error: End index {end_idx} out of range ({start_idx+1}-{len(grantees)})")
        sys.exit(1)

    # Initialize orchestrator
    orchestrator = ScraperOrchestrator(
        platforms=platforms,
        skip_existing=args.skip_existing,
        max_posts=args.max_posts
    )

    # Run scraping
    try:
        orchestrator.run(grantees, start_idx, end_idx)
        print("\nScraping completed successfully!")

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
