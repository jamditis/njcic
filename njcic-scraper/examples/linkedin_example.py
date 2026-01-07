"""
Example usage of LinkedIn scraper.

This demonstrates how to use the LinkedInScraper class to scrape
LinkedIn company pages and personal profiles.
"""
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.linkedin import LinkedInScraper


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def main():
    """Run LinkedIn scraper examples."""

    # Initialize scraper
    scraper = LinkedInScraper(
        output_dir="output",
        headless=True  # Set to False to see browser
    )

    # Example 1: Scrape a company page
    print("\n" + "="*60)
    print("Example 1: Scraping company page")
    print("="*60)

    company_url = "https://www.linkedin.com/company/microsoft"
    grantee_name = "Microsoft"

    try:
        # Extract username
        username = scraper.extract_username(company_url)
        print(f"Extracted username: {username}")

        # Scrape the page
        result = scraper.scrape(company_url, grantee_name)

        print(f"\nResults:")
        print(f"  Success: {result['success']}")
        print(f"  Posts found: {result['posts_downloaded']}")
        print(f"  Errors: {result['errors']}")
        print(f"  Engagement metrics:")
        for key, value in result['engagement_metrics'].items():
            print(f"    {key}: {value}")

    except Exception as e:
        print(f"Error: {e}")


    # Example 2: Scrape a personal profile
    print("\n" + "="*60)
    print("Example 2: Scraping personal profile")
    print("="*60)

    profile_url = "https://www.linkedin.com/in/williamhgates"
    grantee_name = "Bill Gates"

    try:
        # Extract username
        username = scraper.extract_username(profile_url)
        print(f"Extracted username: {username}")

        # Scrape the page
        result = scraper.scrape(profile_url, grantee_name)

        print(f"\nResults:")
        print(f"  Success: {result['success']}")
        print(f"  Posts found: {result['posts_downloaded']}")
        print(f"  Errors: {result['errors']}")
        print(f"  Engagement metrics:")
        for key, value in result['engagement_metrics'].items():
            print(f"    {key}: {value}")

    except Exception as e:
        print(f"Error: {e}")


    # Example 3: Test URL parsing
    print("\n" + "="*60)
    print("Example 3: URL parsing examples")
    print("="*60)

    test_urls = [
        "https://www.linkedin.com/company/google",
        "https://linkedin.com/company/apple/",
        "https://www.linkedin.com/in/sundar-pichai",
        "https://linkedin.com/in/satya-nadella/",
        "https://www.linkedin.com/company/tesla?trk=public_profile",
    ]

    for url in test_urls:
        try:
            username = scraper.extract_username(url)
            page_type = "company" if "/company/" in url else "profile"
            print(f"  {url}")
            print(f"    → username: {username}, type: {page_type}")
        except Exception as e:
            print(f"  {url}")
            print(f"    → Error: {e}")

    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60)


if __name__ == "__main__":
    main()
