# TikTok Scraper Documentation

## Overview

The TikTok scraper (`tiktok.py`) is a production-ready implementation for extracting metadata from TikTok profiles using yt-dlp. It prioritizes performance by downloading only metadata (no video files) while collecting comprehensive engagement metrics.

## Features

- **Metadata-only scraping** - No video downloads for maximum speed
- **Anti-bot measures** - User-agent rotation, retry logic, rate limiting
- **Comprehensive metrics** - Views, likes, comments, shares, engagement rates
- **Robust error handling** - Network errors, timeouts, anti-bot detection
- **Production-ready** - Logging, cleanup, checkpointing

## Requirements

- Python 3.8+
- yt-dlp >= 2024.0.0 (included in requirements.txt)

```bash
pip install yt-dlp>=2024.0.0
```

## Usage

### Basic Usage

```python
from scrapers.tiktok import TikTokScraper

# Initialize scraper
scraper = TikTokScraper(
    output_dir="output",  # Where to save data
    max_posts=25          # Number of posts to scrape
)

# Scrape a profile
result = scraper.scrape(
    url="https://www.tiktok.com/@username",
    grantee_name="Influencer Name"
)

# Check results
if result['success']:
    print(f"Scraped {result['posts_downloaded']} posts")
    print(f"Total likes: {result['engagement_metrics']['total_likes']:,}")
    print(f"Engagement rate: {result['engagement_metrics']['avg_engagement_rate']}%")
else:
    print(f"Errors: {result['errors']}")
```

### URL Formats Supported

The scraper handles multiple TikTok URL formats:

```python
# All of these work:
"https://www.tiktok.com/@username"
"https://tiktok.com/@username"
"tiktok.com/@username"
"https://www.tiktok.com/username"
"tiktok.com/username"
```

### Extract Username Only

```python
username = scraper.extract_username("https://www.tiktok.com/@thehobokengirl")
# Returns: "thehobokengirl"
```

## Return Value

The `scrape()` method returns a dictionary with the following structure:

```python
{
    "success": bool,              # Whether scraping succeeded
    "posts_downloaded": int,       # Number of posts scraped
    "errors": list,                # List of error messages (if any)
    "engagement_metrics": {
        "followers_count": None,   # Not available via yt-dlp
        "total_views": int,        # Sum of all post views
        "total_likes": int,        # Sum of all post likes
        "total_comments": int,     # Sum of all post comments
        "total_shares": int,       # Sum of all post shares
        "avg_engagement_rate": float,  # (likes+comments+shares)/views * 100
        "posts_analyzed": int      # Number of posts used in calculation
    }
}
```

## Output Files

### Directory Structure

```
output/
└── {grantee_name}/
    └── tiktok/
        ├── metadata.json       # Consolidated metadata for all posts
        └── temp/               # Temporary .info.json files (auto-deleted)
```

### metadata.json Format

```json
[
  {
    "post_id": "7507004545118113054",
    "title": "Post title text",
    "description": "Post description/caption",
    "date": "20241215",
    "timestamp": 1734285600,
    "views": 125000,
    "likes": 5430,
    "comments": 234,
    "shares": 89,
    "duration": 45.2,
    "username": "username",
    "display_name": "Display Name",
    "url": "https://www.tiktok.com/@username/video/7507004545118113054",
    "thumbnail": "https://..."
  }
]
```

## Anti-Bot Measures

The scraper implements several anti-bot techniques:

### 1. User-Agent Rotation
Randomly selects from multiple browser user agents:
- Chrome (Windows/Mac/Linux)
- Firefox
- Safari

### 2. Rate Limiting
- 1 second delay between requests
- Configurable via `--sleep-requests` flag
- Additional delays on retry attempts

### 3. Retry Logic
- 3 automatic retries on network errors
- Exponential backoff (5s, 10s, 15s)
- Graceful handling of anti-bot detection

### 4. API Endpoint Selection
Uses TikTok's specific API hostname:
```python
--extractor-args tiktok:api_hostname=api22-normal-c-useast2a.tiktokv.com
```

## Error Handling

### Common Errors and Solutions

#### 1. Anti-bot Detection (403, Captcha, Blocked)
```
Error: "TikTok is blocking requests. Possible anti-bot measures detected."
```
**Solutions:**
- Wait 15-30 minutes before retrying
- Use a VPN or residential proxy
- Try during off-peak hours
- Reduce max_posts to lower request volume

#### 2. Network Errors
```
Error: "network error", "connection timeout"
```
**Solutions:**
- Check internet connection
- Automatic retry will attempt 3 times
- Increase timeout if needed

#### 3. No Videos Found
```
Warning: "No videos found for profile"
```
**Solutions:**
- Verify username is correct
- Check if profile is public
- Account may be new with no posts

#### 4. yt-dlp Not Found
```
Error: "yt-dlp not found. Install with: pip install yt-dlp"
```
**Solution:**
```bash
pip install yt-dlp>=2024.0.0
```

## Configuration Options

### Constructor Parameters

```python
TikTokScraper(
    output_dir: str = "output",  # Output directory
    max_posts: int = 25          # Max posts to scrape per profile
)
```

### yt-dlp Command Options

Current configuration (in `_run_ytdlp` method):

```python
cmd = [
    "yt-dlp",
    "--write-info-json",      # Save metadata
    "--skip-download",        # No video download
    "--no-warnings",          # Clean output
    "--playlist-end", "25",   # Limit posts
    "--user-agent", "...",    # Rotating user agent
    "--sleep-requests", "1",  # Rate limiting
    "--retries", "3",         # Retry logic
    "--extractor-args", "tiktok:api_hostname=...",
    "-o", output_template,
    profile_url
]
```

To modify:
- Increase `--playlist-end` for more posts
- Increase `--sleep-requests` for slower requests
- Add `--proxy` for proxy support

## Performance Considerations

### Speed Optimization

**Metadata-only mode** (current implementation):
- No video downloads
- ~2-5 seconds per post
- 25 posts in ~1-2 minutes

**vs. Full video downloads**:
- Downloads videos
- ~30-60 seconds per post
- 25 posts in ~15-25 minutes

### Resource Usage

- **Memory**: ~50-100 MB
- **Disk**: ~50-100 KB per post (metadata only)
- **Network**: ~50-100 KB per post

## Limitations

### 1. Follower Count Not Available
yt-dlp doesn't extract follower count from video metadata. To get follower count:
- Use TikTok API (requires API key)
- Scrape profile page (requires additional tools)
- Use third-party analytics services

### 2. Rate Limiting
TikTok enforces rate limits:
- ~100-200 requests per hour
- May be stricter without authentication
- Use delays between batch scraping

### 3. Regional Restrictions
Some content may be region-locked:
- Use VPN if needed
- May vary by account location

### 4. Private Accounts
Cannot scrape private accounts:
- Profile must be public
- No authentication support in yt-dlp

## Testing

Run the included test script:

```bash
python test_tiktok_scraper.py
```

This will test:
- Username extraction
- Scraping 3 sample profiles
- Engagement metrics calculation
- Error handling

## Troubleshooting

### Enable Debug Logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Check yt-dlp Version

```bash
yt-dlp --version
```

Should be >= 2024.0.0

### Test yt-dlp Directly

```bash
yt-dlp --write-info-json --skip-download --playlist-end 1 https://www.tiktok.com/@username
```

### Common Issues

1. **Import errors**: Make sure you're in the correct directory
2. **Permission errors**: Check output directory permissions
3. **Encoding errors**: Ensure UTF-8 encoding in environment

## Best Practices

1. **Respect rate limits** - Don't scrape too aggressively
2. **Monitor errors** - Check error logs regularly
3. **Use batch processing** - Process multiple profiles with delays
4. **Handle failures gracefully** - Some profiles may be unavailable
5. **Clean up regularly** - Remove old temp files
6. **Update yt-dlp** - Keep yt-dlp updated for latest fixes

## Examples

### Batch Scraping Multiple Profiles

```python
import time
from scrapers.tiktok import TikTokScraper

profiles = [
    ("https://www.tiktok.com/@thehobokengirl", "Hoboken Girl"),
    ("https://www.tiktok.com/@thegardenstatepodcast", "Garden State"),
    ("https://www.tiktok.com/@njhooprecruit", "NJ Hoop Recruit"),
]

scraper = TikTokScraper(output_dir="output", max_posts=25)

for url, name in profiles:
    print(f"Scraping {name}...")
    result = scraper.scrape(url, name)

    if result['success']:
        print(f"✓ Success: {result['posts_downloaded']} posts")
    else:
        print(f"✗ Failed: {result['errors']}")

    # Delay between profiles to avoid rate limiting
    time.sleep(5)
```

### Extract Engagement Metrics

```python
result = scraper.scrape(url, grantee_name)

if result['success']:
    metrics = result['engagement_metrics']

    # Calculate average views per post
    avg_views = metrics['total_views'] / metrics['posts_analyzed']

    # Calculate average likes per post
    avg_likes = metrics['total_likes'] / metrics['posts_analyzed']

    print(f"Average views: {avg_views:,.0f}")
    print(f"Average likes: {avg_likes:,.0f}")
    print(f"Engagement rate: {metrics['avg_engagement_rate']}%")
```

## Support

For issues or questions:
1. Check the error messages in the logs
2. Review the troubleshooting section
3. Test with yt-dlp directly to isolate issues
4. Check yt-dlp GitHub issues for known problems

## License

This scraper is part of the NJCIC social media scraper project.
