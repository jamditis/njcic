"""
Example usage of the Threads scraper.

This script demonstrates how to use the ThreadsScraper to scrape
Threads profiles and collect engagement metrics.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path to import scrapers
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.threads import ThreadsScraper


def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def scrape_single_profile():
    """Example: Scrape a single Threads profile."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Scraping a single Threads profile")
    print("="*70 + "\n")

    # Initialize scraper
    scraper = ThreadsScraper(
        output_dir="output",
        headless=True,
        timeout=30000
    )

    # Scrape profile
    url = "https://www.threads.net/@zuck"
    grantee_name = "Mark Zuckerberg"

    print(f"Scraping: {url}")
    print(f"Grantee: {grantee_name}\n")

    result = scraper.scrape(url, grantee_name)

    # Display results
    if result['success']:
        print(f"✓ Success!")
        print(f"  Posts downloaded: {result['posts_downloaded']}")

        metrics = result['engagement_metrics']
        print(f"\n  Engagement Metrics:")
        print(f"    Followers: {metrics['followers_count']:,}")
        print(f"    Total likes: {metrics['total_likes']:,}")
        print(f"    Total replies: {metrics['total_replies']:,}")
        print(f"    Total reposts: {metrics['total_reposts']:,}")
        print(f"    Avg engagement rate: {metrics['avg_engagement_rate']:.2f}%")
    else:
        print(f"✗ Failed")
        print(f"  Errors: {', '.join(result['errors'])}")


def scrape_multiple_profiles():
    """Example: Scrape multiple Threads profiles."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Scraping multiple Threads profiles")
    print("="*70 + "\n")

    # List of profiles to scrape
    profiles = [
        ("https://www.threads.net/@zuck", "Mark Zuckerberg"),
        ("https://www.threads.net/@mosseri", "Adam Mosseri"),
    ]

    # Initialize scraper
    scraper = ThreadsScraper(
        output_dir="output",
        headless=True,
        timeout=30000
    )

    # Scrape all profiles
    results = []
    for i, (url, grantee_name) in enumerate(profiles, 1):
        print(f"[{i}/{len(profiles)}] Scraping {grantee_name}...")

        result = scraper.scrape(url, grantee_name)
        results.append({
            'grantee': grantee_name,
            'result': result
        })

        if result['success']:
            print(f"  ✓ {result['posts_downloaded']} posts downloaded\n")
        else:
            print(f"  ✗ Failed: {', '.join(result['errors'])}\n")

        # Rate limiting - wait between requests
        if i < len(profiles):
            import time
            print("  Waiting 5 seconds before next profile...\n")
            time.sleep(5)

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    successful = sum(1 for r in results if r['result']['success'])
    total_posts = sum(r['result']['posts_downloaded'] for r in results)

    print(f"Profiles scraped: {successful}/{len(profiles)}")
    print(f"Total posts: {total_posts}")

    # Detailed results
    print("\nDetailed Results:")
    for r in results:
        status = "✓" if r['result']['success'] else "✗"
        posts = r['result']['posts_downloaded']
        print(f"  {status} {r['grantee']:30} {posts:3} posts")


def scrape_with_error_handling():
    """Example: Scrape with comprehensive error handling."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Scraping with error handling and retries")
    print("="*70 + "\n")

    import time

    url = "https://www.threads.net/@zuck"
    grantee_name = "Mark Zuckerberg"
    max_retries = 3

    scraper = ThreadsScraper(
        output_dir="output",
        headless=True,
        timeout=30000
    )

    for attempt in range(1, max_retries + 1):
        print(f"Attempt {attempt}/{max_retries}...")

        result = scraper.scrape(url, grantee_name)

        if result['success']:
            print(f"✓ Success on attempt {attempt}")
            print(f"  Posts: {result['posts_downloaded']}")

            # Save engagement summary
            metrics = result['engagement_metrics']
            summary = {
                'grantee': grantee_name,
                'url': url,
                'posts': result['posts_downloaded'],
                'followers': metrics['followers_count'],
                'total_engagement': (
                    metrics['total_likes'] +
                    metrics['total_replies'] +
                    metrics['total_reposts']
                ),
                'avg_engagement_rate': metrics['avg_engagement_rate']
            }

            print(f"\n  Summary: {summary}")
            break

        else:
            print(f"✗ Failed on attempt {attempt}")
            print(f"  Errors: {result['errors']}")

            if attempt < max_retries:
                wait_time = 10 * attempt  # Exponential backoff
                print(f"  Retrying in {wait_time} seconds...\n")
                time.sleep(wait_time)
            else:
                print(f"  Max retries reached. Giving up.")


def check_url_formats():
    """Example: Test different URL formats."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Testing URL format support")
    print("="*70 + "\n")

    scraper = ThreadsScraper()

    test_urls = [
        "https://www.threads.net/@zuck",
        "https://threads.net/@zuck",
        "threads.net/@zuck",
        "https://www.threads.net/zuck",
        "threads.net/zuck",
        "www.threads.net/@someuser",
    ]

    print("Extracting usernames from various URL formats:\n")
    for url in test_urls:
        username = scraper.extract_username(url)
        print(f"  {url:40} -> @{username}")


def main():
    """Main entry point."""
    setup_logging()

    print("\n" + "="*70)
    print("THREADS SCRAPER - USAGE EXAMPLES")
    print("="*70)

    # Run examples
    examples = [
        ("URL Format Testing", check_url_formats),
        # Uncomment to run scraping examples (requires Playwright)
        # ("Single Profile", scrape_single_profile),
        # ("Multiple Profiles", scrape_multiple_profiles),
        # ("Error Handling", scrape_with_error_handling),
    ]

    for name, func in examples:
        try:
            func()
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
            break
        except Exception as e:
            print(f"\n✗ Error in example '{name}': {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*70)
    print("Examples complete!")
    print("="*70 + "\n")

    print("NOTE: Scraping examples are commented out by default.")
    print("To run them, you need to:")
    print("  1. Install Playwright: pip install playwright")
    print("  2. Install browsers: playwright install chromium")
    print("  3. Uncomment the examples in the code")
    print()


if __name__ == "__main__":
    main()
