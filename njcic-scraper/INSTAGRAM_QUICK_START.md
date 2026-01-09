# Instagram scraper quick start

## Installation

```bash
pip install instaloader>=4.10.0
```

## Basic usage

```python
from scrapers.instagram import InstagramScraper

# Create scraper
scraper = InstagramScraper()

# Scrape a profile
result = scraper.scrape(
    "https://instagram.com/username",
    "Grantee Name"
)

# Check results
if result['success']:
    print(f"Downloaded {result['posts_downloaded']} posts")
    print(f"Engagement: {result['engagement_metrics']['avg_engagement_rate']}%")
else:
    print(f"Errors: {result['errors']}")
```

## With authentication

```python
import os

# Set credentials
os.environ['INSTAGRAM_USERNAME'] = 'your_username'
os.environ['INSTAGRAM_PASSWORD'] = 'your_password'

# Scrape with full access
scraper = InstagramScraper()
result = scraper.scrape(url, grantee_name)
```

## Output location

```
output/
└── {grantee_name}/
    └── instagram/
        └── {username}/
            └── metadata.json
```

## Key features

- Downloads metadata for last 25 posts (no media files)
- Handles private profiles gracefully
- Calculates engagement metrics automatically
- Supports session persistence
- Production-ready error handling

## Test it

```bash
python test_instagram.py
```

All 10 tests should pass!
