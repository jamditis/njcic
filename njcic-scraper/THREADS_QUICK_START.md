# Threads scraper - quick start guide

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## Basic usage

```python
from scrapers.threads import ThreadsScraper

# Initialize
scraper = ThreadsScraper(output_dir="output", headless=True)

# Scrape a profile
result = scraper.scrape(
    url="https://www.threads.net/@username",
    grantee_name="Grantee Name"
)

# Check results
if result['success']:
    print(f"Posts: {result['posts_downloaded']}")
    print(f"Metrics: {result['engagement_metrics']}")
```

## What gets scraped

For each profile:
- **Up to 25 posts** (most recent)
- **Post data**: text, timestamp, URL
- **Engagement**: likes, replies, reposts per post
- **Profile metrics**: follower count
- **Aggregate metrics**: totals and engagement rate

## Output format

```
output/
└── [Grantee_Name]/
    └── threads/
        └── [username]/
            └── metadata.json
```

## Return value

```python
{
    'success': True,
    'posts_downloaded': 25,
    'errors': [],
    'engagement_metrics': {
        'followers_count': 1234567,
        'total_likes': 12345,
        'total_replies': 678,
        'total_reposts': 234,
        'avg_engagement_rate': 1.05  # percentage
    }
}
```

## URL formats supported

- `https://www.threads.net/@username`
- `https://threads.net/@username`
- `threads.net/@username`
- `threads.net/username`

## Configuration options

```python
ThreadsScraper(
    output_dir="output",   # Output directory
    headless=True,         # Run browser invisibly
    timeout=30000          # Page timeout (ms)
)
```

## Testing

```bash
# Test username extraction
python test_threads_scraper.py

# Test full scraping
python test_threads_scraper.py "https://www.threads.net/@zuck" "Test User"

# Run examples
python examples/threads_example.py
```

## Common issues

### Playwright not installed
```bash
pip install playwright
playwright install chromium
```

### Timeout errors
- Increase timeout: `ThreadsScraper(timeout=60000)`
- Check internet connection
- Try non-headless: `ThreadsScraper(headless=False)`

### No posts found
- Profile may be private
- Profile may have no posts
- Threads UI may have changed

### Rate limiting
- Add delays between profiles (5-10 seconds)
- Reduce concurrent scraping
- Consider using proxies

## Best practices

1. **Rate Limiting**: Add 5-10 second delays between profiles
2. **Error Handling**: Check `result['errors']` and implement retries
3. **Headless Mode**: Use `headless=True` in production
4. **Logging**: Enable logging to debug issues
5. **Testing**: Test with `headless=False` to see browser behavior

## Integration example

```python
import time
from scrapers.threads import ThreadsScraper

profiles = [
    ("https://www.threads.net/@user1", "User 1"),
    ("https://www.threads.net/@user2", "User 2"),
]

scraper = ThreadsScraper()

for url, name in profiles:
    result = scraper.scrape(url, name)

    if result['success']:
        print(f"✓ {name}: {result['posts_downloaded']} posts")
    else:
        print(f"✗ {name}: {result['errors']}")

    time.sleep(5)  # Rate limiting
```

## Documentation

- Full documentation: `THREADS_SCRAPER_README.md`
- Examples: `examples/threads_example.py`
- Test script: `test_threads_scraper.py`

## Requirements

- Python 3.9+
- Playwright 1.40+
- Chromium browser (installed via Playwright)
- See `requirements.txt` for full list

## Notes

- **No API**: Threads has no public API, so browser automation is required
- **Public only**: Works for public profiles only
- **UI dependent**: May break if Threads changes their UI
- **Rate limits**: Respect Threads' rate limiting
- **25 post limit**: Hard-coded to scrape up to 25 posts per profile
