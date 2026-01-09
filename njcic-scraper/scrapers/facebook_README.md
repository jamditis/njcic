# Facebook Scraper

Production-ready Facebook scraper using Playwright for browser automation. Handles various Facebook URL formats and extracts posts with comprehensive engagement metrics.

## Features

- **Multiple URL Format Support**:
  - `facebook.com/pagename`
  - `facebook.com/pages/name/id`
  - `facebook.com/groups/groupname`
  - `fb.com/pagename`
  - `m.facebook.com/pagename`
  - Profile URLs with IDs

- **Data Extraction**:
  - Post text content
  - Publication dates
  - Reactions/likes
  - Comments count
  - Shares count
  - Post URLs

- **Engagement Metrics**:
  - Followers/page likes count
  - Total reactions across posts
  - Total comments
  - Total shares
  - Average engagement rate

- **Production Features**:
  - Graceful degradation
  - Comprehensive error handling
  - Stealth browser settings
  - Configurable headless mode
  - Structured output (JSON)

## Installation

Ensure Playwright is installed:

```bash
pip install playwright
playwright install chromium
```

## Usage

### Basic usage

```python
from scrapers.facebook import FacebookScraper

# Initialize scraper
scraper = FacebookScraper(output_dir="output", headless=True)

# Scrape a Facebook page
result = scraper.scrape(
    url="https://facebook.com/example",
    grantee_name="Example Organization"
)

# Check results
if result['success']:
    print(f"Downloaded {result['posts_downloaded']} posts")
    print(f"Engagement metrics: {result['engagement_metrics']}")
else:
    print(f"Errors: {result['errors']}")
```

### Command line

```bash
# Test scraper
python scripts/test_facebook.py https://facebook.com/example "Example Org"

# With different URL formats
python scripts/test_facebook.py https://facebook.com/pages/name/123456 "Example Org"
python scripts/test_facebook.py https://facebook.com/groups/example "Example Org"
```

### Extract username only

```python
scraper = FacebookScraper()

username = scraper.extract_username("https://facebook.com/example")
print(username)  # "example"

username = scraper.extract_username("https://facebook.com/pages/name/123456")
print(username)  # "123456"

username = scraper.extract_username("https://facebook.com/groups/example")
print(username)  # "group_example"
```

## Output structure

The scraper creates the following directory structure:

```
output/
└── {grantee_name}/
    └── facebook/
        └── {username}/
            ├── metadata.json
            └── posts.json
```

### metadata.json

```json
{
  "url": "https://facebook.com/example",
  "username": "example",
  "grantee_name": "Example Organization",
  "posts_count": 25,
  "engagement_metrics": {
    "followers_count": 10000,
    "total_reactions": 500,
    "total_comments": 150,
    "total_shares": 50,
    "avg_engagement_rate": 0.28
  },
  "scraped_at": "2026-01-07T12:00:00",
  "platform": "facebook"
}
```

### posts.json

```json
[
  {
    "id": "post_0",
    "text": "Post content here...",
    "date": "2026-01-07T10:00:00",
    "reactions": 50,
    "comments": 10,
    "shares": 5,
    "url": "https://www.facebook.com/example/posts/123456"
  },
  ...
]
```

## API reference

### FacebookScraper

```python
class FacebookScraper(BaseScraper):
    def __init__(self, output_dir: str = "output", headless: bool = True)
```

**Parameters**:
- `output_dir` (str): Directory to save scraped data. Default: "output"
- `headless` (bool): Run browser in headless mode. Default: True

**Methods**:

#### extract_username(url: str) -> Optional[str]

Extract username/identifier from Facebook URL.

**Parameters**:
- `url` (str): Facebook URL

**Returns**:
- `str`: Username/identifier
- `None`: If URL is invalid

**Examples**:
```python
scraper.extract_username("https://facebook.com/example")  # "example"
scraper.extract_username("https://fb.com/example")  # "example"
scraper.extract_username("https://facebook.com/pages/name/123")  # "123"
scraper.extract_username("https://facebook.com/groups/example")  # "group_example"
```

#### scrape(url: str, grantee_name: str) -> Dict[str, Any]

Scrape Facebook page/profile for posts and engagement metrics.

**Parameters**:
- `url` (str): Facebook URL to scrape
- `grantee_name` (str): Name of the grantee for organizing data

**Returns**:
Dictionary with:
- `success` (bool): Whether scraping succeeded
- `posts_downloaded` (int): Number of posts downloaded (max 25)
- `errors` (List[str]): List of error messages
- `engagement_metrics` (Dict): Engagement statistics
  - `followers_count` (int|None): Page followers/likes
  - `total_reactions` (int): Total reactions across posts
  - `total_comments` (int): Total comments across posts
  - `total_shares` (int): Total shares across posts
  - `avg_engagement_rate` (float): Average engagement rate as percentage

**Example**:
```python
result = scraper.scrape(
    "https://facebook.com/example",
    "Example Organization"
)

if result['success']:
    print(f"Posts: {result['posts_downloaded']}")
    print(f"Followers: {result['engagement_metrics']['followers_count']}")
    print(f"Engagement Rate: {result['engagement_metrics']['avg_engagement_rate']}%")
```

## Important notes

### Facebook's anti-scraping measures

Facebook actively prevents scraping through:
- CAPTCHAs
- Rate limiting
- Login requirements
- Dynamic DOM changes

This scraper uses best-effort strategies:
- Stealth browser settings
- Realistic user agent
- Graceful degradation
- Multiple selector fallbacks

### Limitations

1. **Login Wall**: Some pages require login. The scraper works best on public pages.
2. **Rate Limiting**: Facebook may block IPs with excessive requests.
3. **Dynamic Content**: Facebook's DOM changes frequently; selectors may need updates.
4. **CAPTCHA**: Manual intervention may be required if CAPTCHA appears.
5. **Post Limit**: Extracts up to 25 posts to avoid excessive scraping time.

### Best practices

1. **Respect Rate Limits**: Don't scrape too frequently
2. **Use Delays**: Add delays between requests
3. **Public Pages Only**: Focus on public, non-login-required pages
4. **Error Handling**: Always check `result['success']` and `result['errors']`
5. **Monitor Changes**: Facebook updates its site regularly

### Graceful degradation

The scraper is designed to:
- Continue even if some elements aren't found
- Return partial data if extraction fails
- Log warnings instead of crashing
- Use multiple fallback selectors

## Troubleshooting

### "Playwright not installed" error

```bash
pip install playwright
playwright install chromium
```

### "Could not extract username from URL"

- Check URL format
- Ensure URL is a valid Facebook URL
- Try different URL format (e.g., use page ID instead of name)

### Zero posts extracted

- Page may require login
- Facebook may be blocking the scraper
- Try with `headless=False` to see what's happening
- Check if page is public

### Low engagement metrics

- Some pages don't show public engagement counts
- Facebook may hide metrics from scrapers
- This is expected behavior for privacy-protected pages

## Example: Batch scraping

```python
from scrapers.facebook import FacebookScraper
import time

# List of URLs to scrape
urls = [
    "https://facebook.com/example1",
    "https://facebook.com/example2",
    "https://facebook.com/example3",
]

scraper = FacebookScraper(output_dir="output", headless=True)

for url in urls:
    print(f"Scraping {url}...")
    
    result = scraper.scrape(url, "My Grantee")
    
    if result['success']:
        print(f"  ✓ {result['posts_downloaded']} posts")
    else:
        print(f"  ✗ Errors: {result['errors']}")
    
    # Delay to avoid rate limiting
    time.sleep(10)
```

## License

Part of NJCIC scraper suite.
