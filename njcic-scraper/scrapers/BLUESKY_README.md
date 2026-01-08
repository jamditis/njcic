# BlueSky Scraper

Production-ready scraper for BlueSky social media platform using the AT Protocol public API.

## Overview

The BlueSky scraper (`bluesky.py`) is a fully-functional implementation that:
- Uses the public BlueSky AT Protocol API (no authentication required)
- Inherits from `BaseScraper` for consistent interface
- Downloads up to 25 posts per account (configurable)
- Extracts comprehensive engagement metrics
- Saves data in JSON format with proper error handling

## Features

### Core Functionality
- **Platform**: BlueSky (platform_name: "bluesky")
- **API**: Public AT Protocol API at `https://public.api.bsky.app/xrpc`
- **Authentication**: None required (public API)
- **Rate Limiting**: Built-in via BaseScraper

### URL Formats Supported
The scraper handles multiple URL formats:
- Full profile URLs: `https://bsky.app/profile/username.bsky.social`
- Custom domains: `https://bsky.app/profile/custom.domain`
- Direct handles: `username.bsky.social`

### Data Extracted

#### Per Post:
- Post ID and URI
- Text content
- Timestamp (ISO format + formatted)
- Author information (handle, DID, display name, avatar)
- Engagement metrics:
  - Likes
  - Reposts (mapped to 'shares')
  - Replies (mapped to 'comments')
- Media presence (embed type)
- Post URL for web viewing

#### Aggregate Metrics:
- `followers_count`: Number of followers
- `following_count`: Number of accounts followed
- `posts_count`: Total posts on profile
- `total_likes`: Sum of all likes
- `total_reposts`: Sum of all reposts
- `total_replies`: Sum of all replies
- `total_engagement`: Combined engagement count
- `avg_engagement_rate`: Engagement rate as percentage
- `avg_likes_per_post`: Average likes per post
- `avg_reposts_per_post`: Average reposts per post
- `avg_replies_per_post`: Average replies per post
- `avg_total_engagement_per_post`: Average total engagement
- `posts_analyzed`: Number of posts included in metrics

## Usage

### Basic Example

```python
from scrapers.bluesky import BlueSkyScraper

# Initialize scraper
scraper = BlueSkyScraper()

# Scrape a profile
result = scraper.scrape(
    url="https://bsky.app/profile/bsky.app",
    grantee_name="my_grantee",
    max_posts=25  # Optional, defaults to config.MAX_POSTS_PER_ACCOUNT
)

# Check results
print(f"Success: {result['success']}")
print(f"Posts downloaded: {result['posts_downloaded']}")
print(f"Engagement metrics: {result['engagement_metrics']}")
```

### Return Value

The `scrape()` method returns a dictionary with:
```python
{
    'success': bool,              # Whether scraping succeeded
    'posts_downloaded': int,       # Number of posts downloaded
    'errors': List[Dict],          # List of errors encountered
    'engagement_metrics': Dict,    # Calculated metrics
    'output_path': str            # Path where data was saved
}
```

### Output Files

Data is saved to: `output/{grantee_name}/bluesky/`

Files created:
- `posts.json`: All scraped posts
- `metadata.json`: Profile info, metrics, and scraping metadata
- `errors.json`: Error log (if any errors occurred)

## API Endpoints Used

1. **Profile Endpoint**: `app.bsky.actor.getProfile`
   - Fetches user profile information
   - Returns: followers, following, posts count, bio, etc.

2. **Feed Endpoint**: `app.bsky.feed.getAuthorFeed`
   - Fetches user's posts
   - Supports pagination via cursor
   - Max 100 posts per request

## Implementation Details

### Class: `BlueSkyScraper(BaseScraper)`

**Methods:**

- `__init__(output_dir: Optional[Path] = None)`
  - Initializes scraper with custom output directory
  - Sets up requests session with proper headers

- `extract_username(url: str) -> Optional[str]`
  - Extracts BlueSky handle from various URL formats
  - Returns handle or None if invalid

- `scrape(url: str, grantee_name: str, max_posts: Optional[int] = None) -> Dict`
  - Main scraping method
  - Fetches profile and posts
  - Calculates metrics
  - Saves all data

**Private Methods:**

- `_fetch_profile(handle: str) -> Optional[Dict]`
  - Fetches user profile from API

- `_fetch_posts(handle: str, limit: int) -> List[Dict]`
  - Fetches posts with pagination support

- `_extract_post_data(feed_item: Dict) -> Dict`
  - Extracts and normalizes post data

- `_calculate_engagement_metrics(posts: List, profile: Optional[Dict]) -> Dict`
  - Calculates aggregate engagement metrics

## Error Handling

- All API errors are logged and included in errors list
- Partial data is saved even if errors occur
- Individual post processing errors don't stop scraping
- Network timeouts handled gracefully (30s default)

## Testing

Run the test suite:
```bash
cd /home/user/njcic/njcic-scraper
python3 test_bluesky.py
```

See example usage:
```bash
python3 examples/bluesky_example.py
```

## Configuration

Default settings from `config.py`:
- `MAX_POSTS_PER_ACCOUNT`: 25
- `REQUEST_DELAY`: 2 seconds
- `TIMEOUT`: 30 seconds
- `USER_AGENT`: Standard Chrome user agent

## Dependencies

- `requests`: HTTP client
- `python-dotenv`: Environment variables (via config)
- Standard library: `re`, `datetime`, `pathlib`, `typing`, `urllib`

## Notes

- No authentication required - uses public API only
- Rate limiting handled automatically via BaseScraper
- All data is UTF-8 encoded JSON
- Posts are validated against required fields from config
- Suitable for production use with proper error handling
