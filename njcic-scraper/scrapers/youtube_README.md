# YouTube Scraper

## Overview
Production-ready YouTube channel scraper using yt-dlp. Extracts video metadata without downloading video files.

## Features
- Scrapes last 25 videos from any YouTube channel
- Supports multiple URL formats (@handle, /c/, /channel/, /user/)
- Extracts comprehensive metadata and engagement metrics
- No video downloads (metadata only)
- Robust error handling with detailed logging
- Rate limiting built-in

## Requirements
- yt-dlp (installed via pip)
- Python 3.8+

## Usage

```python
from scrapers import YouTubeScraper

# Initialize scraper
scraper = YouTubeScraper()

# Scrape a channel
result = scraper.scrape(
    url="https://www.youtube.com/@mkbhd",
    grantee_name="Tech Reviews Org",
    max_posts=25  # Optional, defaults to config.MAX_POSTS_PER_ACCOUNT
)

# Check results
if result['success']:
    print(f"Downloaded {result['posts_downloaded']} videos")
    print(f"Engagement metrics: {result['engagement_metrics']}")
else:
    print(f"Errors: {result['errors']}")
```

## Supported URL Formats

1. **@handle format**: `https://www.youtube.com/@mkbhd`
2. **Channel name**: `https://www.youtube.com/c/Veritasium`
3. **Channel ID**: `https://www.youtube.com/channel/UCBJycsmduvYEL83R_U4JriQ`
4. **User format**: `https://www.youtube.com/user/CGPGrey`

## Extracted Metadata

For each video:
- `video_id`: YouTube video ID
- `title`: Video title
- `description`: Full video description
- `upload_date`: Upload date (YYYYMMDD format)
- `views`: View count
- `likes`: Like count
- `comments`: Comment count
- `duration`: Video duration in seconds
- `url`: Full video URL

## Engagement Metrics

- `subscribers_count`: Channel subscriber count (if available)
- `total_views`: Sum of views across all scraped videos
- `total_likes`: Sum of likes across all scraped videos
- `total_comments`: Sum of comments across all scraped videos
- `avg_views_per_video`: Average views per video
- `avg_engagement_rate`: Average engagement rate ((likes + comments) / views * 100)

## Output Structure

```
output/
  └── {grantee_name}/
      └── youtube/
          └── {channel_identifier}/
              └── metadata.json
```

## Error Handling

The scraper implements robust error handling:
- Invalid URLs return empty results with error messages
- Failed video fetches are logged but don't stop the scrape
- Partial results are saved even if some videos fail
- All errors are logged to both console and log file

## Rate Limiting

Built-in rate limiting respects YouTube's guidelines:
- Configurable delay between requests (default: 2 seconds)
- Prevents API throttling
- Configurable via `config.REQUEST_DELAY`

## Testing

Run the URL extraction test:
```bash
python scripts/test_youtube_url_extraction.py
```

Run an example scrape:
```bash
python scripts/example_youtube_scrape.py
```
