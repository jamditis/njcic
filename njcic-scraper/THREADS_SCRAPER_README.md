# Threads Scraper Documentation

Production-ready Threads scraper using Playwright for browser automation.

## Overview

The Threads scraper (`scrapers/threads.py`) is designed to scrape posts from Threads profiles. Since Threads doesn't currently have a public API, this implementation uses browser automation via Playwright to extract post data.

## Features

- **Browser Automation**: Uses Playwright to navigate and scrape Threads profiles
- **Graceful Fallbacks**: Handles anti-bot measures and rate limiting
- **Engagement Metrics**: Extracts comprehensive engagement data
- **Configurable**: Headless/non-headless mode, custom timeouts
- **Production-Ready**: Comprehensive error handling and logging

## Installation

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Playwright browsers

After installing the playwright package, you need to install the browser binaries:

```bash
playwright install chromium
```

This downloads the Chromium browser that Playwright will use for automation.

## Usage

### Basic example

```python
from pathlib import Path
from scrapers.threads import ThreadsScraper

# Initialize scraper
scraper = ThreadsScraper(
    output_dir="output",
    headless=True,  # Run browser in headless mode
    timeout=30000   # Page load timeout in milliseconds
)

# Scrape a profile
result = scraper.scrape(
    url="https://www.threads.net/@zuck",
    grantee_name="Mark Zuckerberg"
)

# Check results
if result['success']:
    print(f"Downloaded {result['posts_downloaded']} posts")
    print(f"Engagement metrics: {result['engagement_metrics']}")
else:
    print(f"Errors: {result['errors']}")
```

### Using the test script

A test script is provided for easy testing:

```bash
# Test username extraction only
python test_threads_scraper.py

# Test full scraping
python test_threads_scraper.py "https://www.threads.net/@zuck" "Mark Zuckerberg"
```

## URL format support

The scraper handles the following URL formats:

- `https://www.threads.net/@username`
- `https://threads.net/@username`
- `threads.net/@username`
- `https://www.threads.net/username`
- `threads.net/username`

## Output structure

```
output/
└── [Grantee_Name]/
    └── threads/
        └── [username]/
            └── metadata.json
```

### metadata.json structure

```json
{
  "username": "zuck",
  "profile_url": "https://www.threads.net/@zuck",
  "posts_count": 25,
  "posts": [
    {
      "index": 0,
      "text": "Post content here...",
      "timestamp": "2024-01-15T10:30:00Z",
      "likes": 1523,
      "replies": 45,
      "reposts": 12,
      "url": "https://www.threads.net/@zuck/post/ABC123",
      "raw_html_length": 5432
    }
    // ... more posts
  ],
  "engagement_metrics": {
    "followers_count": 5234567,
    "total_likes": 38456,
    "total_replies": 1234,
    "total_reposts": 567,
    "avg_engagement_rate": 0.75
  },
  "scraped_at": "2024-01-15T12:00:00.000000",
  "platform": "threads"
}
```

## Return value

The `scrape()` method returns a dictionary with:

```python
{
    'success': bool,              # Whether scraping succeeded
    'posts_downloaded': int,      # Number of posts scraped (max 25)
    'errors': List[str],          # List of error messages
    'engagement_metrics': {
        'followers_count': int,           # Number of followers
        'total_likes': int,               # Sum of likes across all posts
        'total_replies': int,             # Sum of replies across all posts
        'total_reposts': int,             # Sum of reposts across all posts
        'avg_engagement_rate': float      # Average engagement rate (%)
    }
}
```

## Configuration options

### ThreadsScraper Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `output_dir` | str | `"output"` | Base directory for storing scraped data |
| `headless` | bool | `True` | Run browser in headless mode |
| `timeout` | int | `30000` | Page load timeout in milliseconds |

### Post limit

The scraper is configured to download up to **25 posts** per profile (as per requirements). This is hard-coded in the `ThreadsScraper` class.

## Implementation details

### How it works

1. **URL Validation**: Extracts username from Threads URL
2. **Browser Launch**: Launches Chromium browser via Playwright
3. **Navigation**: Navigates to the profile page
4. **Content Loading**: Scrolls page to trigger lazy loading of posts
5. **Data Extraction**: Extracts post content and engagement metrics using JavaScript
6. **Metadata Saving**: Saves all data to `metadata.json`

### Engagement metrics calculation

- **Followers Count**: Extracted from profile page (supports K/M/B notation)
- **Total Likes/Replies/Reposts**: Sum across all scraped posts
- **Avg Engagement Rate**: `(total_engagement / followers) * 100`

### Anti-bot handling

The scraper implements several strategies to avoid detection:

- Realistic user agent strings
- Realistic viewport sizes (1920x1080)
- Progressive scrolling with delays
- Timeout handling for slow pages
- Graceful degradation on errors

## Known limitations

### 1. Browser automation required

Threads has no public API, so browser automation is necessary. This means:

- Slower than API-based scraping
- Requires browser binaries (Chromium)
- More resource-intensive
- More fragile to UI changes

### 2. Rate limiting

Threads may implement rate limiting or bot detection:

- **Mitigation**: Add delays between requests
- **Mitigation**: Use residential IPs if needed
- **Mitigation**: Reduce concurrent scraping

### 3. Dynamic content

Threads uses heavy JavaScript and lazy loading:

- **Mitigation**: Scrolling mechanism to trigger content loading
- **Mitigation**: Progressive waiting for selectors
- **Limitation**: Some posts may not load on slow connections

### 4. UI changes

Threads UI is subject to change:

- **Mitigation**: Flexible selectors (e.g., `article` tags, `time` elements)
- **Limitation**: Major UI overhauls may break scraping
- **Recommendation**: Regular testing and updates

### 5. Authentication

This scraper works for **public profiles only**:

- No authentication implemented
- Private profiles cannot be scraped
- Login-only features not accessible

### 6. Accuracy of engagement metrics

Engagement numbers are extracted from displayed text:

- **Pattern matching** for "X likes", "Y replies", etc.
- May miss metrics if Threads changes formatting
- Numbers may be approximations (e.g., "1.2K")

## Troubleshooting

### Playwright not found

```
Error: Playwright not installed
```

**Solution**:
```bash
pip install playwright
playwright install chromium
```

### Profile not found

```
Error: Profile @username not found
```

**Possible causes**:
- Username is incorrect
- Profile doesn't exist
- Profile is private or deleted
- Threads is blocking the request

### Timeout errors

```
Error: Timeout loading profile page
```

**Solutions**:
- Increase timeout: `ThreadsScraper(timeout=60000)`
- Check internet connection
- Check if Threads is accessible in your region

### No posts found

```
Error: No posts found on profile
```

**Possible causes**:
- Profile has no public posts
- JavaScript didn't load properly
- Page structure changed

**Solutions**:
- Try with `headless=False` to see what's happening
- Check if profile actually has posts
- Update scraper if Threads UI changed

### Rate limiting

```
Error: Connection error / 429 Too Many Requests
```

**Solutions**:
- Add delays between scraping multiple profiles
- Use VPN or residential proxy
- Reduce scraping frequency

## Development

### Running tests

```bash
# Test username extraction
python test_threads_scraper.py

# Test scraping (non-headless mode to watch)
python -c "
from scrapers.threads import ThreadsScraper
scraper = ThreadsScraper(headless=False)
result = scraper.scrape('https://www.threads.net/@zuck', 'Test')
print(result)
"
```

### Debugging

To see what the browser is doing, run in non-headless mode:

```python
scraper = ThreadsScraper(headless=False, timeout=60000)
result = scraper.scrape(url, grantee_name)
```

This will open a visible browser window so you can see the scraping process.

### Customization

To modify the scraper:

1. **Change post limit**: Modify `self.max_posts` in `__init__`
2. **Add more metrics**: Extend `_extract_post_data()` method
3. **Change selectors**: Update JavaScript in `_extract_post_data()`
4. **Add authentication**: Implement login in `_scrape_async()`

## Best practices

1. **Respect Rate Limits**: Add delays between scraping multiple profiles
2. **Monitor Errors**: Check `result['errors']` for issues
3. **Test Regularly**: Threads UI may change, requiring updates
4. **Use Headless Mode**: In production, always use `headless=True`
5. **Handle Failures**: Implement retry logic for transient errors
6. **Cache Results**: Store metadata to avoid re-scraping

## Integration example

```python
import logging
from pathlib import Path
from scrapers.threads import ThreadsScraper

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize scraper
scraper = ThreadsScraper(
    output_dir="output",
    headless=True,
    timeout=30000
)

# List of profiles to scrape
profiles = [
    ("https://www.threads.net/@zuck", "Mark Zuckerberg"),
    ("https://www.threads.net/@mosseri", "Adam Mosseri"),
]

# Scrape all profiles
results = []
for url, grantee_name in profiles:
    logger.info(f"Scraping {grantee_name}...")

    result = scraper.scrape(url, grantee_name)
    results.append(result)

    if result['success']:
        logger.info(f"✓ {grantee_name}: {result['posts_downloaded']} posts")
    else:
        logger.error(f"✗ {grantee_name}: {result['errors']}")

    # Rate limiting
    import time
    time.sleep(5)

# Summary
total_posts = sum(r['posts_downloaded'] for r in results)
successful = sum(1 for r in results if r['success'])

logger.info(f"\nSummary:")
logger.info(f"  Profiles scraped: {successful}/{len(profiles)}")
logger.info(f"  Total posts: {total_posts}")
```

## License

This scraper is provided as-is for research and educational purposes. Always respect Threads' Terms of Service and robots.txt when scraping.

## Support

For issues or questions:

1. Check this documentation
2. Review the test script (`test_threads_scraper.py`)
3. Run in non-headless mode to debug
4. Check Playwright documentation: https://playwright.dev/python/
