# LinkedIn scraper - Quick start guide

## Installation

```bash
# Install Playwright
pip install playwright

# Install Chromium browser
playwright install chromium
```

## Quick example

```python
from scrapers.linkedin import LinkedInScraper

# Initialize
scraper = LinkedInScraper(output_dir="output", headless=True)

# Scrape a company
result = scraper.scrape(
    url="https://www.linkedin.com/company/microsoft",
    grantee_name="Microsoft Corp"
)

# Check results
if result['success']:
    print(f"Followers: {result['engagement_metrics']['followers_count']}")
    print(f"Employees: {result['engagement_metrics']['employee_count']}")
else:
    print(f"Errors: {result['errors']}")
```

## Key features

✓ Company pages (`/company/name`)
✓ Personal profiles (`/in/username`)
✓ Automatic username extraction
✓ Graceful error handling
✓ Screenshot capture
✓ JSON metadata export

## Expected metrics

**Company Pages:**
- `followers_count` - Number of followers (if public)
- `employee_count` - Employee range (e.g., "50-100")
- `posts_found` - Number of visible posts

**Personal Profiles:**
- `followers_count` - Number of followers (often restricted)
- `connections_count` - Connections (often restricted)
- `posts_found` - Number of visible posts

## Important limitations

⚠️ **LinkedIn heavily restricts scraping**

- Many pages require login
- Rate limiting after multiple requests
- Limited public data available
- Terms of Service prohibit automation
- Best effort only - expect failures

## When it works best

- Public company pages
- Profiles with public visibility settings
- Single requests (not bulk scraping)
- Viewing basic metrics only

## When it fails

- Profiles behind authentication wall
- After too many requests (rate limiting)
- Private profiles
- Detailed engagement metrics
- Post content extraction

## Output location

```
output/linkedin/{grantee_name}/{username}/
├── metadata.json    # All extracted data
└── screenshot.png   # Visual reference
```

## Troubleshooting

**Problem**: "LinkedIn requires authentication"
**Solution**: This is expected. LinkedIn blocks most unauthenticated access.

**Problem**: "Rate limited by LinkedIn"
**Solution**: Wait several hours before trying again.

**Problem**: "Could not extract username"
**Solution**: Check URL format matches: `linkedin.com/company/name` or `linkedin.com/in/username`

## Legal notice

This scraper is for **educational/research purposes only**.
LinkedIn's Terms of Service prohibit automated scraping.
Consider using LinkedIn's official API for production use.

## Run example

```bash
cd /home/user/njcic/njcic-scraper
python3 examples/linkedin_example.py
```

## More information

See `README_LINKEDIN.md` for full documentation.
