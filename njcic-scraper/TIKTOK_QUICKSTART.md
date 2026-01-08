# TikTok Scraper - Quick Start Guide

## Overview
Production-ready TikTok scraper that extracts metadata only (no video downloads) for maximum performance.

## Files Created
- `/home/user/njcic/njcic-scraper/scrapers/tiktok.py` - Main scraper implementation
- `/home/user/njcic/njcic-scraper/scrapers/README_TIKTOK.md` - Comprehensive documentation
- `/home/user/njcic/njcic-scraper/test_tiktok_scraper.py` - Test script
- `/home/user/njcic/njcic-scraper/scrapers/__init__.py` - Updated to register TikTokScraper

## Installation

Ensure yt-dlp is installed (already in requirements.txt):
```bash
pip install yt-dlp>=2024.0.0
```

## Basic Usage

```python
from scrapers.tiktok import TikTokScraper

# Initialize scraper (uses config.OUTPUT_DIR and config.MAX_POSTS_PER_ACCOUNT = 25)
scraper = TikTokScraper()

# Scrape a profile
result = scraper.scrape(
    url="https://www.tiktok.com/@thehobokengirl",
    grantee_name="Hoboken Girl"
)

# Check results
print(f"Success: {result['success']}")
print(f"Posts: {result['posts_downloaded']}")
print(f"Likes: {result['engagement_metrics']['total_likes']:,}")
print(f"Views: {result['engagement_metrics']['total_views']:,}")
print(f"Engagement Rate: {result['engagement_metrics']['avg_engagement_rate']}%")
```

## Key Features

### 1. Metadata-Only Mode (Fast)
- Uses `--skip-download` flag
- ~2-5 seconds per post
- 25 posts in ~1-2 minutes
- No video storage needed

### 2. Anti-Bot Measures
- User-agent rotation (4 different browsers)
- Rate limiting (1s delay between requests)
- Automatic retry with exponential backoff (3 attempts)
- Specific TikTok API endpoint configuration

### 3. Comprehensive Metrics
```python
engagement_metrics = {
    "followers_count": None,  # Not available via yt-dlp
    "total_views": 125430,
    "total_likes": 5234,
    "total_comments": 234,
    "total_shares": 89,
    "avg_engagement_rate": 4.42,  # (likes+comments+shares)/views * 100
    "posts_analyzed": 25
}
```

### 4. Extracted Post Data
Each post includes:
- post_id, title, description
- date, timestamp
- views, likes, comments, shares
- duration, username, display_name
- url, thumbnail

## URL Formats Supported

All of these work:
```python
"https://www.tiktok.com/@username"
"https://tiktok.com/@username"
"tiktok.com/@username"
"https://www.tiktok.com/username"
```

## Output Structure

```
output/
└── {grantee_name}/
    └── tiktok/
        ├── posts.json          # Individual post data
        └── metadata.json       # Consolidated metadata + engagement metrics
```

## Configuration

Default configuration from `config.py`:
- `MAX_POSTS_PER_ACCOUNT`: 25
- `REQUEST_DELAY`: 2 seconds
- `TIMEOUT`: 30 seconds
- `MAX_RETRIES`: 3

Override max_posts per scrape:
```python
result = scraper.scrape(url, grantee_name, max_posts=50)
```

## Error Handling

The scraper handles:
- Anti-bot detection (403, captcha, blocked) → Auto-retry with delays
- Network errors → 3 automatic retries
- Invalid URLs → Clear error messages
- No videos found → Warning logged
- Missing yt-dlp → Installation instructions

## Testing

Run the test script:
```bash
cd /home/user/njcic/njcic-scraper
python test_tiktok_scraper.py
```

This tests:
- Username extraction
- 3 sample TikTok profiles
- Engagement metrics calculation
- Error handling

## Quick Test

```python
from scrapers.tiktok import TikTokScraper

scraper = TikTokScraper()

# Test username extraction
print(scraper.extract_username("https://www.tiktok.com/@thehobokengirl"))
# Output: thehobokengirl

# Test import
print(f"Platform: {scraper.platform_name}")
# Output: Platform: tiktok
```

## Performance

**Speed:**
- Metadata only: ~1-2 minutes for 25 posts
- vs. Full videos: ~15-25 minutes for 25 posts

**Resources:**
- Memory: ~50-100 MB
- Disk: ~50-100 KB per post (metadata only)
- Network: ~50-100 KB per post

## Production Considerations

1. **Rate Limiting**: TikTok limits ~100-200 requests/hour
2. **Batch Processing**: Add 5-10s delays between profiles
3. **Anti-Bot Detection**: May need VPN during peak hours
4. **Error Handling**: Some profiles may be unavailable (handled gracefully)
5. **Logging**: All activity logged to `logs/scraper.log`

## Common Issues

### "TikTok is blocking requests"
- Wait 15-30 minutes
- Use VPN/proxy
- Try during off-peak hours
- Reduce max_posts

### "yt-dlp not found"
```bash
pip install yt-dlp>=2024.0.0
```

### "No videos found"
- Verify username is correct
- Check if profile is public
- Account may have no posts

## API Reference

### `TikTokScraper(output_dir=None)`
Initialize scraper with optional output directory (defaults to config.OUTPUT_DIR).

### `extract_username(url: str) -> Optional[str]`
Extract username from TikTok URL.

### `scrape(url: str, grantee_name: str, max_posts: Optional[int] = None) -> Dict`
Scrape TikTok profile metadata.

**Returns:**
```python
{
    "success": bool,
    "posts_downloaded": int,
    "errors": List[str],
    "engagement_metrics": Dict[str, Any],
    "output_path": str
}
```

## Full Documentation

See `/home/user/njcic/njcic-scraper/scrapers/README_TIKTOK.md` for:
- Detailed API reference
- Advanced configuration
- Troubleshooting guide
- Best practices
- Example scripts

## Support

For issues:
1. Check error logs: `logs/scraper.log`
2. Review `/home/user/njcic/njcic-scraper/scrapers/README_TIKTOK.md`
3. Test with yt-dlp directly: `yt-dlp --version`
4. Check yt-dlp GitHub for known issues
