# Social media scrapers

Production-ready scrapers for various social media platforms.

## Overview

This package provides a consistent interface for scraping social media content across multiple platforms. Each scraper inherits from `BaseScraper` and implements platform-specific logic.

## Installation

Install required dependencies:

```bash
pip install -r ../requirements.txt
```

## Twitter/X Scraper

### Features

- Scrapes up to 25 recent posts from a Twitter/X profile
- Extracts comprehensive engagement metrics
- Handles both `twitter.com` and `x.com` URLs
- Uses gallery-dl for reliable scraping (no API key required)
- Graceful error handling and rate limit management

### Usage

#### As a module

```python
from scrapers.twitter import TwitterScraper

# Initialize scraper
scraper = TwitterScraper(output_dir="output", max_posts=25)

# Scrape a profile
result = scraper.scrape(
    url="https://twitter.com/username",
    grantee_name="Organization Name"
)

# Check results
if result['success']:
    print(f"Downloaded {result['posts_downloaded']} posts")
    print(f"Engagement metrics: {result['engagement_metrics']}")
else:
    print(f"Errors: {result['errors']}")
```

#### Command line

```bash
cd /home/user/njcic/njcic-scraper/scrapers
python twitter.py https://twitter.com/username "Organization Name"
```

### Data structure

#### Output directory structure

```
output/
└── {grantee_name}/
    └── twitter/
        └── {username}/
            ├── metadata.json
            └── {tweet_id}.json (one per tweet)
```

#### Metadata format

```json
{
  "url": "https://twitter.com/username",
  "username": "username",
  "grantee_name": "Organization Name",
  "posts_downloaded": 25,
  "scraped_at": "2026-01-07T12:00:00",
  "platform": "twitter",
  "engagement_metrics": {
    "username": "username",
    "followers_count": null,
    "total_likes": 15000,
    "total_retweets": 3000,
    "total_replies": 500,
    "total_views": 100000,
    "avg_likes": 600.0,
    "avg_retweets": 120.0,
    "avg_replies": 20.0,
    "avg_views": 4000.0,
    "avg_engagement_rate": 18.5,
    "posts_analyzed": 25
  },
  "posts": [
    {
      "tweet_id": "1234567890",
      "text": "Tweet content...",
      "date": "2026-01-07",
      "likes": 500,
      "retweets": 100,
      "replies": 20,
      "views": 5000,
      "author": "Display Name",
      "username": "username"
    }
  ],
  "errors": []
}
```

#### Return value

The `scrape()` method returns a dictionary with:

```python
{
    "success": bool,              # Whether scraping was successful
    "posts_downloaded": int,      # Number of posts downloaded
    "errors": List[str],          # List of error messages
    "engagement_metrics": {
        "username": str,
        "followers_count": int|None,     # Not available without API
        "total_likes": int,
        "total_retweets": int,
        "total_replies": int,
        "total_views": int,
        "avg_likes": float,
        "avg_retweets": float,
        "avg_replies": float,
        "avg_views": float,
        "avg_engagement_rate": float,    # (likes+retweets+replies)/views * 100
        "posts_analyzed": int
    }
}
```

### Error handling

The scraper handles various error conditions:

- Invalid URLs (non-Twitter/X domains)
- Invalid username formats
- gallery-dl execution failures
- Rate limiting (via timeout and retry logic)
- Missing dependencies
- Network errors

Errors are collected in the `errors` list and logged for debugging.

### Rate limiting

- Uses a 5-minute timeout for gallery-dl operations
- Downloads only metadata by default (can be configured)
- Respects Twitter's rate limits through gallery-dl's built-in handling

### Requirements

- `gallery-dl >= 1.26.0` - Primary scraping tool
- `requests >= 2.31.0` - HTTP library
- Python 3.8+

### Limitations

1. **Follower Count**: Not available without Twitter API access (requires paid tier)
2. **Private Accounts**: Cannot scrape protected/private accounts
3. **Rate Limits**: Subject to Twitter's rate limiting policies
4. **Authentication**: Some content may require authentication (can be configured in gallery-dl)

### Configuration

To scrape with authentication (for better rate limits):

1. Create `~/.config/gallery-dl/config.json`:

```json
{
  "extractor": {
    "twitter": {
      "username": "your_twitter_username",
      "password": "your_twitter_password"
    }
  }
}
```

2. Or use cookies authentication (recommended):

```json
{
  "extractor": {
    "twitter": {
      "cookies": "/path/to/cookies.txt"
    }
  }
}
```

## Base scraper

All platform scrapers inherit from `BaseScraper`, which provides:

- Logger setup
- Output directory management
- Filename sanitization
- Metadata saving
- Abstract methods for `extract_username()` and `scrape()`

### Creating a new scraper

```python
from scrapers.base import BaseScraper

class MyPlatformScraper(BaseScraper):
    platform_name = "myplatform"
    
    def extract_username(self, url: str) -> Optional[str]:
        # Extract username from URL
        pass
    
    def scrape(self, url: str, grantee_name: str) -> Dict[str, Any]:
        # Implement scraping logic
        pass
```

## Troubleshooting

### gallery-dl not found

```bash
pip install gallery-dl
```

### Permission errors

Ensure the output directory is writable:

```bash
chmod 755 /home/user/njcic/njcic-scraper/output
```

### Twitter authentication required

Some profiles may require authentication. Configure gallery-dl with your Twitter credentials or cookies.

## License

Part of the NJCIC grant tracking system.
