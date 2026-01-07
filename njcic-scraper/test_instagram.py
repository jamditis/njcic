"""
Test suite for Instagram scraper.
Verifies all required functionality without making actual API calls.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from scrapers.instagram import InstagramScraper


def test_inheritance():
    """Test that InstagramScraper inherits from BaseScraper."""
    from scrapers.base import BaseScraper
    scraper = InstagramScraper()
    assert isinstance(scraper, BaseScraper)
    print("✓ InstagramScraper properly inherits from BaseScraper")


def test_platform_name():
    """Test that platform_name is set correctly."""
    scraper = InstagramScraper()
    assert scraper.platform_name == "instagram"
    print("✓ platform_name is 'instagram'")


def test_username_extraction():
    """Test username extraction from various URL formats."""
    scraper = InstagramScraper()

    test_cases = [
        ("instagram.com/natgeo", "natgeo"),
        ("instagram.com/natgeo/", "natgeo"),
        ("https://www.instagram.com/natgeo", "natgeo"),
        ("https://www.instagram.com/natgeo/", "natgeo"),
        ("https://instagram.com/some_user.name_123/", "some_user.name_123"),
        ("natgeo", "natgeo"),
        ("instagram.com/p/ABC123/", None),  # Post URL, should not extract
        ("instagram.com/reel/ABC123/", None),  # Reel URL
        ("instagram.com/explore/", None),  # Explore page
        ("", None),  # Empty string
        ("https://twitter.com/user", None),  # Wrong platform
    ]

    for url, expected in test_cases:
        result = scraper.extract_username(url)
        assert result == expected, f"Failed for {url}: expected {expected}, got {result}"

    print("✓ Username extraction works for all test cases")


def test_instaloader_configuration():
    """Test that instaloader is configured correctly for metadata-only scraping."""
    scraper = InstagramScraper()

    # Verify instaloader settings
    assert scraper.loader.download_pictures == False
    assert scraper.loader.download_videos == False
    assert scraper.loader.download_video_thumbnails == False
    assert scraper.loader.download_geotags == False
    assert scraper.loader.download_comments == False
    assert scraper.loader.save_metadata == False

    print("✓ Instaloader configured for metadata-only scraping")


def test_engagement_metrics_calculation():
    """Test engagement metrics calculation."""
    scraper = InstagramScraper()

    # Create mock posts
    mock_posts = [
        {'likes': 100, 'comments': 10, 'is_video': False},
        {'likes': 200, 'comments': 20, 'is_video': True, 'video_views': 1000},
        {'likes': 150, 'comments': 15, 'is_video': False},
    ]

    # Create mock profile
    mock_profile = Mock()
    mock_profile.followers = 10000
    mock_profile.followees = 500

    metrics = scraper._calculate_engagement_metrics(mock_posts, mock_profile)

    # Verify calculations
    assert metrics['followers_count'] == 10000
    assert metrics['following_count'] == 500
    assert metrics['total_likes'] == 450  # 100 + 200 + 150
    assert metrics['total_comments'] == 45  # 10 + 20 + 15
    assert metrics['total_video_views'] == 1000
    assert metrics['posts_analyzed'] == 3

    # Verify engagement rate calculation
    # avg_engagement = (450 + 45) / 3 = 165
    # rate = (165 / 10000) * 100 = 1.65%
    expected_rate = 1.65
    assert abs(metrics['avg_engagement_rate'] - expected_rate) < 0.01

    print("✓ Engagement metrics calculation is correct")


def test_post_metadata_extraction():
    """Test post metadata extraction."""
    scraper = InstagramScraper()

    # Create mock post
    mock_post = Mock()
    mock_post.shortcode = 'ABC123'
    mock_post.caption = 'Test caption #hashtag'
    mock_post.date_utc = None
    mock_post.likes = 100
    mock_post.comments = 10
    mock_post.is_video = True
    mock_post.video_view_count = 500
    mock_post.typename = 'GraphVideo'
    mock_post.location = None
    mock_post.tagged_users = []
    mock_post.caption_hashtags = ['hashtag']

    metadata = scraper._extract_post_metadata(mock_post)

    # Verify extracted metadata
    assert metadata['shortcode'] == 'ABC123'
    assert metadata['url'] == 'https://www.instagram.com/p/ABC123/'
    assert metadata['caption'] == 'Test caption #hashtag'
    assert metadata['likes'] == 100
    assert metadata['comments'] == 10
    assert metadata['is_video'] == True
    assert metadata['video_views'] == 500
    assert metadata['typename'] == 'GraphVideo'
    assert metadata['hashtags'] == ['hashtag']

    print("✓ Post metadata extraction works correctly")


def test_scrape_return_structure():
    """Test that scrape returns the correct structure."""
    scraper = InstagramScraper()

    # Test with invalid URL (should return error structure)
    result = scraper.scrape('invalid_url', 'Test Grantee')

    # Verify return structure
    assert 'success' in result
    assert 'posts_downloaded' in result
    assert 'errors' in result
    assert 'engagement_metrics' in result

    assert isinstance(result['success'], bool)
    assert isinstance(result['posts_downloaded'], int)
    assert isinstance(result['errors'], list)
    assert isinstance(result['engagement_metrics'], dict)

    print("✓ scrape() returns correct structure")


def test_private_profile_handling():
    """Test that private profiles are handled gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        scraper = InstagramScraper(output_dir=tmpdir)

        # Mock the profile loading and check for private profile
        with patch('instaloader.Profile.from_username') as mock_profile:
            # Create a mock private profile
            profile = Mock()
            profile.is_private = True
            profile.followed_by_viewer = False
            profile.followers = 1000
            profile.followees = 500
            mock_profile.return_value = profile

            result = scraper.scrape('https://instagram.com/privateuser/', 'Test Grantee')

            # Verify that it handled private profile gracefully
            assert result['success'] == True  # Should still be successful
            assert result['posts_downloaded'] == 0
            assert len(result['errors']) > 0
            assert 'private' in result['errors'][0].lower()

            # Check that metadata was saved
            metadata_path = Path(tmpdir) / 'Test_Grantee' / 'instagram' / 'privateuser' / 'metadata.json'
            assert metadata_path.exists()

            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                assert metadata['is_private'] == True
                assert 'note' in metadata

    print("✓ Private profiles are handled gracefully")


def test_required_engagement_metrics():
    """Test that all required engagement metrics are present."""
    scraper = InstagramScraper()

    mock_posts = [{'likes': 100, 'comments': 10, 'is_video': False}]
    mock_profile = Mock()
    mock_profile.followers = 1000
    mock_profile.followees = 100

    metrics = scraper._calculate_engagement_metrics(mock_posts, mock_profile)

    # Verify all required metrics are present
    required_metrics = [
        'followers_count',
        'following_count',
        'total_likes',
        'total_comments',
        'avg_engagement_rate'
    ]

    for metric in required_metrics:
        assert metric in metrics, f"Missing required metric: {metric}"

    print("✓ All required engagement metrics are present")


def test_output_directory_creation():
    """Test that output directories are created correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        scraper = InstagramScraper(output_dir=tmpdir)

        # Test directory creation
        output_path = scraper._get_output_directory('Test Grantee', 'testuser')

        # Verify path structure
        assert output_path.exists()
        assert output_path.is_dir()
        assert 'Test_Grantee' in str(output_path)
        assert 'instagram' in str(output_path)
        assert 'testuser' in str(output_path)

    print("✓ Output directories are created correctly")


def main():
    """Run all tests."""
    print("Running Instagram Scraper Tests")
    print("=" * 60)

    try:
        test_inheritance()
        test_platform_name()
        test_username_extraction()
        test_instaloader_configuration()
        test_engagement_metrics_calculation()
        test_post_metadata_extraction()
        test_scrape_return_structure()
        test_private_profile_handling()
        test_required_engagement_metrics()
        test_output_directory_creation()

        print("=" * 60)
        print("All tests passed! ✓")
        return 0

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
