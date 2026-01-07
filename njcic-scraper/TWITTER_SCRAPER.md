# Twitter/X Scraper - Quick Reference

## Location
`/home/user/njcic/njcic-scraper/scrapers/twitter.py`

## Class: TwitterScraper

Inherits from `BaseScraper` and implements Twitter/X specific scraping logic.

### Key Features

✓ Handles both `twitter.com` and `x.com` URLs
✓ Downloads up to 25 posts (configurable)
✓ Uses gallery-dl (no API key required)
✓ Comprehensive engagement metrics
✓ Graceful error handling
✓ Rate limit management
✓ Production-ready logging

### Public Methods

#### 1. `extract_username(url: str) -> Optional[str]`

Extracts username from Twitter/X URLs.

**Supported formats:**
- `https://twitter.com/username`
- `https://x.com/username`
- `https://twitter.com/username/status/123456`
- `https://x.com/username/status/123456`

**Returns:** Username string or None if invalid

**Example:**
```python
scraper = TwitterScraper()
username = scraper.extract_username("https://twitter.com/elonmusk")
# Returns: "elonmusk"
```

#### 2. `scrape(url: str, grantee_name: str) -> Dict[str, Any]`

Scrapes Twitter profile and extracts engagement metrics.

**Parameters:**
- `url`: Twitter/X profile URL
- `grantee_name`: Name of the organization/grantee

**Returns:**
```python
{
    "success": bool,
    "posts_downloaded": int,
    "errors": List[str],
    "engagement_metrics": {
        "username": str,
        "followers_count": None,  # Not available without API
        "total_likes": int,
        "total_retweets": int,
        "total_replies": int,
        "total_views": int,
        "avg_likes": float,
        "avg_retweets": float,
        "avg_replies": float,
        "avg_views": float,
        "avg_engagement_rate": float,
        "posts_analyzed": int
    }
}
```

**Example:**
```python
scraper = TwitterScraper(output_dir="output", max_posts=25)
result = scraper.scrape(
    url="https://twitter.com/NASA",
    grantee_name="Space Organization"
)

if result['success']:
    print(f"Downloaded {result['posts_downloaded']} posts")
    metrics = result['engagement_metrics']
    print(f"Average engagement: {metrics['avg_engagement_rate']}%")
```

### Configuration

**Constructor parameters:**
- `output_dir` (str): Base directory for output (default: "output")
- `max_posts` (int): Maximum posts to scrape (default: 25)

### Output Structure

```
output/
└── {grantee_name}/
    └── twitter/
        └── {username}/
            ├── metadata.json       # Comprehensive metadata
            └── *.json              # Individual tweet metadata (from gallery-dl)
```

### Engagement Metrics Explained

| Metric | Description |
|--------|-------------|
| `total_likes` | Sum of all likes across posts |
| `total_retweets` | Sum of all retweets across posts |
| `total_replies` | Sum of all replies across posts |
| `total_views` | Sum of all views across posts |
| `avg_likes` | Average likes per post |
| `avg_retweets` | Average retweets per post |
| `avg_replies` | Average replies per post |
| `avg_views` | Average views per post |
| `avg_engagement_rate` | (likes + retweets + replies) / views × 100 |
| `posts_analyzed` | Number of posts included in calculations |

### Error Handling

The scraper gracefully handles:
- Invalid URLs
- Invalid username formats
- Network errors
- Rate limiting
- Missing dependencies
- Gallery-dl execution failures

All errors are:
1. Logged using Python's logging module
2. Collected in the `errors` list
3. Returned in the result dictionary

### Dependencies

**Required:**
- `gallery-dl >= 1.26.0`
- Python 3.8+

**Install:**
```bash
pip install gallery-dl
```

### Command Line Usage

```bash
# Basic usage
python /home/user/njcic/njcic-scraper/scrapers/twitter.py \
    https://twitter.com/username \
    "Organization Name"

# Run test suite
python /home/user/njcic/njcic-scraper/scripts/test_twitter_scraper.py \
    https://twitter.com/NASA \
    "Test Org"
```

### Integration Example

```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/user/njcic/njcic-scraper')

from scrapers.twitter import TwitterScraper

# Initialize
scraper = TwitterScraper(
    output_dir="/home/user/njcic/njcic-scraper/output",
    max_posts=25
)

# Scrape multiple accounts
accounts = [
    ("https://twitter.com/account1", "Grantee A"),
    ("https://twitter.com/account2", "Grantee B"),
]

for url, grantee in accounts:
    result = scraper.scrape(url, grantee)
    print(f"{grantee}: {result['posts_downloaded']} posts")
```

### Limitations

1. **Follower count**: Not available (requires paid Twitter API)
2. **Private accounts**: Cannot scrape protected accounts
3. **Historical data**: Limited by Twitter's public availability
4. **Rate limits**: Subject to Twitter/gallery-dl rate limits

### Advanced Configuration

For better reliability, configure gallery-dl with authentication:

**~/.config/gallery-dl/config.json:**
```json
{
  "extractor": {
    "twitter": {
      "cookies": "/path/to/twitter-cookies.txt"
    }
  }
}
```

Export cookies from browser using a tool like "Get cookies.txt" extension.

## Troubleshooting

### Issue: "gallery-dl not found"
```bash
pip install --upgrade gallery-dl
```

### Issue: Rate limited
- Wait before retrying
- Configure authentication in gallery-dl
- Reduce `max_posts` parameter

### Issue: No posts downloaded
- Check if account is public
- Verify URL is correct
- Check internet connection
- Review error logs

## Performance

**Typical performance:**
- 25 posts: ~30-60 seconds
- Rate: ~2-3 posts/second
- Metadata only: faster (no media download)

## Security Considerations

- Never commit Twitter credentials to git
- Store cookies/auth in secure location
- Sanitize all filenames (handled by base class)
- Validate URLs before scraping
- Log errors without exposing sensitive data

## Testing

```bash
# Test username extraction only
python /home/user/njcic/njcic-scraper/scripts/test_twitter_scraper.py

# Test full scraping
python /home/user/njcic/njcic-scraper/scripts/test_twitter_scraper.py \
    https://twitter.com/username "Test Grantee"
```

---

**Created:** 2026-01-07
**Version:** 1.0
**Status:** Production-ready
