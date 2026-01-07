"""
Test script to verify base scraper infrastructure is working correctly.
"""

from scrapers.base import BaseScraper
from typing import Optional, Dict, Any
import config


class TestScraper(BaseScraper):
    """Test implementation of BaseScraper for verification."""

    platform_name = "test_platform"

    def extract_username(self, url: str) -> Optional[str]:
        """Extract username from URL."""
        # Simple test implementation
        if "test.com/" in url:
            return url.split("test.com/")[-1].split("/")[0]
        return None

    def scrape(
        self,
        url: str,
        grantee_name: str,
        max_posts: Optional[int] = None
    ) -> Dict[str, Any]:
        """Scrape posts from URL."""
        max_posts = max_posts or config.MAX_POSTS_PER_ACCOUNT

        # Get output directory
        output_path = self.get_output_path(grantee_name)

        # Create test posts
        posts = [
            {
                "post_id": f"test_{i}",
                "text": f"Test post {i}",
                "timestamp": "2026-01-07T12:00:00",
                "author": "test_user",
                "platform": self.platform_name,
                "url": f"{url}/post/{i}",
                "likes": i * 10,
                "comments": i * 2,
                "shares": i,
                "views": i * 100,
                "reactions": i * 5
            }
            for i in range(1, min(6, max_posts + 1))  # Create 5 test posts
        ]

        # Save posts
        self.save_posts(posts, output_path)

        # Calculate engagement
        engagement = self.calculate_engagement_metrics(posts)

        # Create metadata
        metadata = {
            "url": url,
            "grantee_name": grantee_name,
            "username": self.extract_username(url),
            "posts_scraped": len(posts),
            "max_posts_requested": max_posts
        }

        # Save metadata
        self.save_metadata(output_path, metadata)

        return {
            "success": True,
            "posts_downloaded": len(posts),
            "errors": [],
            "engagement_metrics": engagement,
            "output_path": str(output_path)
        }


def test_configuration():
    """Test configuration settings."""
    print("Testing Configuration...")
    print(f"✓ BASE_DIR: {config.BASE_DIR}")
    print(f"✓ OUTPUT_DIR: {config.OUTPUT_DIR}")
    print(f"✓ DATA_DIR: {config.DATA_DIR}")
    print(f"✓ LOGS_DIR: {config.LOGS_DIR}")
    print(f"✓ MAX_POSTS_PER_ACCOUNT: {config.MAX_POSTS_PER_ACCOUNT}")
    print(f"✓ REQUEST_DELAY: {config.REQUEST_DELAY}s")
    print(f"✓ SUPPORTED_PLATFORMS: {', '.join(config.SUPPORTED_PLATFORMS)}")
    print()


def test_base_scraper():
    """Test base scraper functionality."""
    print("Testing BaseScraper...")

    # Initialize test scraper
    scraper = TestScraper()
    print(f"✓ Initialized: {scraper}")

    # Test scraping
    result = scraper.scrape(
        url="https://test.com/example_org",
        grantee_name="Test Organization"
    )

    print(f"✓ Scrape completed successfully")
    print(f"  - Posts downloaded: {result['posts_downloaded']}")
    print(f"  - Output path: {result['output_path']}")
    print(f"  - Engagement metrics:")
    for metric, value in result['engagement_metrics'].items():
        print(f"    - {metric}: {value}")
    print()


def test_validation():
    """Test post validation."""
    print("Testing Post Validation...")

    scraper = TestScraper()

    # Valid post
    valid_post = {
        "post_id": "123",
        "text": "Test",
        "timestamp": "2026-01-07T12:00:00",
        "author": "user",
        "platform": "test",
        "url": "https://test.com"
    }

    # Invalid post (missing required field)
    invalid_post = {
        "post_id": "123",
        "text": "Test"
        # Missing other required fields
    }

    assert scraper.validate_post(valid_post), "Valid post should pass validation"
    print("✓ Valid post passed validation")

    assert not scraper.validate_post(invalid_post), "Invalid post should fail validation"
    print("✓ Invalid post failed validation (as expected)")
    print()


def main():
    """Run all tests."""
    print("=" * 60)
    print("NJCIC Base Scraper Infrastructure Test")
    print("=" * 60)
    print()

    try:
        test_configuration()
        test_base_scraper()
        test_validation()

        print("=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        print()
        print("Base infrastructure is ready. Next steps:")
        print("1. Implement platform-specific scrapers")
        print("2. Set up .env file with API credentials")
        print("3. Test with real social media accounts")

    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise


if __name__ == "__main__":
    main()
