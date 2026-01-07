# LinkedIn Scraper - Quick Start Guide

## Installation

```bash
# Install Playwright
pip install playwright

# Install Chromium browser
playwright install chromium
```

## Quick Example

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

## Key Features

✓ Company pages (`/company/name`)
✓ Personal profiles (`/in/username`)
✓ Automatic username extraction
✓ Graceful error handling
✓ Screenshot capture
✓ JSON metadata export

## Expected Metrics

**Company Pages:**
- `followers_count` - Number of followers (if public)
- `employee_count` - Employee range (e.g., "50-100")
- `posts_found` - Number of visible posts

**Personal Profiles:**
- `followers_count` - Number of followers (often restricted)
- `connections_count` - Connections (often restricted)
- `posts_found` - Number of visible posts

## Important Limitations

⚠️ **LinkedIn heavily restricts scraping**

- Many pages require login
- Rate limiting after multiple requests
- Limited public data available
- Terms of Service prohibit automation
- Best effort only - expect failures

## When It Works Best

- Public company pages
- Profiles with public visibility settings
- Single requests (not bulk scraping)
- Viewing basic metrics only

## When It Fails

- Profiles behind authentication wall
- After too many requests (rate limiting)
- Private profiles
- Detailed engagement metrics
- Post content extraction

## Output Location

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

## Legal Notice

This scraper is for **educational/research purposes only**.
LinkedIn's Terms of Service prohibit automated scraping.
Consider using LinkedIn's official API for production use.

## Run Example

```bash
cd /home/user/njcic/njcic-scraper
python3 examples/linkedin_example.py
```

## More Information

See `README_LINKEDIN.md` for full documentation.
