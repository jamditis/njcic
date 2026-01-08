# Instagram Scraper Documentation

## Overview

Production-ready Instagram scraper built using the instaloader library. Scrapes post metadata without downloading media files for optimal speed and storage efficiency.

## File Location

**Main scraper:** `/home/user/njcic/njcic-scraper/scrapers/instagram.py`

## Features

### Core Functionality

1. **Inherits from BaseScraper** - Follows the established scraper architecture
2. **Platform name:** `instagram`
3. **Metadata-only scraping** - Downloads last 25 posts without media files for speed
4. **Session management** - Loads existing sessions or logs in with credentials
5. **Graceful error handling** - Handles private profiles, rate limits, and API errors
6. **Comprehensive metrics** - Calculates engagement rates and social metrics

### URL Handling

The `extract_username()` method handles multiple URL formats:
- `instagram.com/username`
- `instagram.com/username/`
- `https://www.instagram.com/username`
- `https://www.instagram.com/username/`
- Just a username: `username`

Automatically filters out non-profile URLs (posts, reels, stories, explore pages).

### Data Extraction

For each post, the scraper extracts:
- Caption
- Date/timestamp
- Likes count
- Comments count
- Is video flag
- Video views (if applicable)
- Location (if available)
- Tagged users
- Hashtags
- Post URL

### Engagement Metrics

The scraper calculates and returns:
- `followers_count` - Number of followers
- `following_count` - Number of accounts followed
- `total_likes` - Sum of likes across all scraped posts
- `total_comments` - Sum of comments across all scraped posts
- `total_video_views` - Sum of video views (videos only)
- `avg_engagement_rate` - Average engagement rate as percentage

**Engagement rate formula:** `((likes + comments) / followers) * 100`

### Private Profile Handling

When encountering a private profile that the authenticated user doesn't follow:
- Returns success=True (no error state)
- Sets posts_downloaded=0
- Includes a descriptive warning in errors list
- Saves metadata with private profile note
- Includes basic profile metrics (follower/following counts if available)

## Installation

1. Install required dependencies:
```bash
pip install instaloader>=4.10.0
```

2. (Optional) Set up Instagram credentials for full functionality:
```bash
export INSTAGRAM_USERNAME="your_username"
export INSTAGRAM_PASSWORD="your_password"
```

## Usage

### Basic Usage

```python
from scrapers.instagram import InstagramScraper

# Initialize scraper
scraper = InstagramScraper(output_dir="output")

# Scrape a profile
result = scraper.scrape(
    url="https://www.instagram.com/natgeo/",
    grantee_name="National Geographic"
)

# Check results
print(f"Success: {result['success']}")
print(f"Posts downloaded: {result['posts_downloaded']}")
print(f"Engagement rate: {result['engagement_metrics']['avg_engagement_rate']}%")
```

### With Session File

```python
scraper = InstagramScraper(
    output_dir="output",
    session_file="data/instagram_session"
)

result = scraper.scrape(url, grantee_name)
```

### Using the Example Script

```bash
# Simple usage (public profiles only)
python example_instagram.py --url https://instagram.com/username

# With credentials
export INSTAGRAM_USERNAME="your_username"
export INSTAGRAM_PASSWORD="your_password"
python example_instagram.py --url https://instagram.com/username --grantee-name "Organization Name"

# With session file
python example_instagram.py --url https://instagram.com/username --session-file data/instagram_session

# With debug logging
python example_instagram.py --url https://instagram.com/username --debug
```

## Return Structure

The `scrape()` method returns a dictionary with:

```python
{
    'success': bool,              # Whether scraping was successful
    'posts_downloaded': int,      # Number of posts downloaded
    'errors': List[str],          # List of error messages
    'engagement_metrics': {
        'followers_count': int,
        'following_count': int,
        'total_likes': int,
        'total_comments': int,
        'total_video_views': int,
        'avg_engagement_rate': float
    }
}
```

## Output Structure

Scraped data is saved to:
```
output/
└── {grantee_name}/
    └── instagram/
        └── {username}/
            └── metadata.json
```

### Metadata JSON Format

```json
{
  "username": "natgeo",
  "url": "https://www.instagram.com/natgeo/",
  "grantee_name": "National Geographic",
  "profile": {
    "full_name": "National Geographic",
    "biography": "...",
    "external_url": "https://www.nationalgeographic.com",
    "is_verified": true,
    "is_private": false,
    "mediacount": 28453
  },
  "posts": [
    {
      "shortcode": "ABC123",
      "url": "https://www.instagram.com/p/ABC123/",
      "caption": "Caption text...",
      "date": "2024-01-15T12:30:45",
      "likes": 125000,
      "comments": 3400,
      "is_video": false,
      "video_views": null,
      "typename": "GraphImage",
      "location": null,
      "tagged_users": [],
      "hashtags": ["nature", "photography"]
    }
  ],
  "engagement_metrics": {
    "followers_count": 284000000,
    "following_count": 148,
    "total_likes": 3125000,
    "total_comments": 85000,
    "total_video_views": 500000,
    "avg_engagement_rate": 1.13,
    "posts_analyzed": 25
  },
  "errors": [],
  "scraped_at": "2026-01-07T22:00:00",
  "platform": "instagram"
}
```

## Testing

Run the comprehensive test suite:

```bash
python test_instagram.py
```

Tests cover:
- BaseScraper inheritance
- Platform name configuration
- Username extraction (11 test cases)
- Instaloader configuration
- Engagement metrics calculation
- Post metadata extraction
- Return structure validation
- Private profile handling
- Output directory creation

## Configuration

### Environment Variables

- `INSTAGRAM_USERNAME` - Instagram username for authentication
- `INSTAGRAM_PASSWORD` - Instagram password for authentication

### Instaloader Settings

The scraper is configured with these optimizations:
- `download_pictures=False` - Skip image downloads
- `download_videos=False` - Skip video downloads
- `download_video_thumbnails=False` - Skip thumbnail downloads
- `download_geotags=False` - Skip geolocation data
- `download_comments=False` - Skip comment threads
- `save_metadata=False` - Skip instaloader's metadata files
- `quiet=True` - Minimize console output

## Error Handling

The scraper handles:
- Invalid URLs (returns error immediately)
- Non-existent profiles (returns error with message)
- Private profiles (returns success with note)
- Rate limiting (retries with exponential backoff)
- Network errors (returns error with details)
- Authentication failures (logs warning, continues with limited access)

## Limitations

1. **Rate Limiting:** Instagram enforces rate limits. Use authenticated sessions for higher limits.
2. **Private Profiles:** Cannot access posts from private profiles unless authenticated and following.
3. **Post Limit:** Configured to download metadata for the last 25 posts only (configurable).
4. **API Changes:** Instagram may change their API, requiring instaloader updates.

## Technical Details

- **Lines of code:** 454
- **Dependencies:** instaloader, pathlib, json, os, re, datetime, typing
- **Python version:** 3.7+
- **License:** Follows project license

## Support

For issues or questions:
1. Check instaloader documentation: https://instaloader.github.io/
2. Verify Instagram credentials and rate limits
3. Review error messages in the returned errors list
4. Check metadata.json for detailed scraping results
