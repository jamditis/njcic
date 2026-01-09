# LinkedIn scraper documentation

## Overview

The LinkedIn scraper (`linkedin.py`) is a best-effort implementation for collecting publicly available information from LinkedIn company pages and personal profiles.

**Important**: LinkedIn has very strict anti-scraping measures. This scraper has limited functionality and may not always succeed.

## Features

- Inherits from `BaseScraper` base class
- Supports both company pages and personal profiles
- Uses Playwright for browser automation
- Implements graceful fallback on errors
- Saves metadata and screenshots
- Realistic browser behavior to minimize detection

## Limitations

Due to LinkedIn's anti-scraping policies:

1. **Authentication Wall**: Many profiles require login to view
2. **Rate Limiting**: LinkedIn may block requests after multiple attempts
3. **Limited Data**: Only publicly visible information can be accessed
4. **Dynamic Content**: Some metrics may not load without authentication
5. **Geographic Restrictions**: Content availability varies by region

## Installation

### Prerequisites

```bash
# Install Playwright
pip install playwright

# Install browser drivers
playwright install chromium
```

## Usage

### Basic example

```python
from scrapers.linkedin import LinkedInScraper

# Initialize scraper
scraper = LinkedInScraper(
    output_dir="output",
    headless=True
)

# Scrape a company page
result = scraper.scrape(
    url="https://www.linkedin.com/company/microsoft",
    grantee_name="Microsoft"
)

print(f"Success: {result['success']}")
print(f"Metrics: {result['engagement_metrics']}")
```

### URL formats supported

**Company Pages:**
- `https://www.linkedin.com/company/companyname`
- `https://linkedin.com/company/companyname/`
- `https://www.linkedin.com/company/companyname?trk=...`

**Personal Profiles:**
- `https://www.linkedin.com/in/username`
- `https://linkedin.com/in/username/`
- `https://www.linkedin.com/in/username?trk=...`

### Extract username

```python
# Extract company name
username = scraper.extract_username("https://linkedin.com/company/google")
# Returns: "google"

# Extract profile username
username = scraper.extract_username("https://linkedin.com/in/williamhgates")
# Returns: "williamhgates"
```

## Return value

The `scrape()` method returns a dictionary with:

```python
{
    'success': bool,              # True if at least some data was extracted
    'posts_downloaded': int,      # Number of posts found (usually 0)
    'errors': list,              # List of error messages
    'engagement_metrics': {      # Metrics extracted
        # For company pages:
        'followers_count': str,  # Number of followers
        'employee_count': str,   # Employee count range
        'posts_found': int,      # Number of posts visible

        # For personal profiles:
        'followers_count': str,     # Number of followers
        'connections_count': str,   # Number of connections
        'posts_found': int,         # Number of posts visible
    }
}
```

## Engagement metrics

### Company pages

- `followers_count`: Number of company followers
- `employee_count`: Employee count (often a range like "10,001+")
- `posts_found`: Number of visible posts/updates

### Personal profiles

- `followers_count`: Number of profile followers
- `connections_count`: Number of connections (often restricted)
- `posts_found`: Number of visible posts

## Output files

For each scraped page, the following files are created:

```
output/
└── linkedin/
    └── {grantee_name}/
        └── {username}/
            ├── metadata.json    # All extracted data
            └── screenshot.png   # Screenshot of the page
```

### metadata.json Structure

```json
{
  "platform": "linkedin",
  "grantee_name": "Example Org",
  "username": "example-company",
  "url": "https://linkedin.com/company/example-company",
  "page_type": "company",
  "scraped_at": "2026-01-07T12:00:00",
  "data": {
    "company_name": "Example Company",
    "followers_count": "12345",
    "employee_count": "50-100",
    "posts_found": 0,
    "description": "Company description...",
    "industry": null,
    "website": null
  },
  "engagement_metrics": {
    "followers_count": "12345",
    "employee_count": "50-100",
    "posts_found": 0
  },
  "success": true,
  "errors": [],
  "notes": [
    "LinkedIn heavily restricts scraping",
    "Only public information was accessed",
    "Some metrics may be unavailable without authentication"
  ]
}
```

## Error handling

The scraper handles various error conditions:

1. **Invalid URL Format**: Raises `ValueError` with descriptive message
2. **Page Not Found**: Returns error in `errors` list
3. **Authentication Required**: Returns error but continues extraction
4. **Rate Limiting**: Returns error message
5. **Network Timeout**: Returns timeout error

All errors are logged and returned in the `errors` list.

## Best practices

1. **Rate Limiting**: Don't scrape too frequently (wait hours/days between requests)
2. **Respect robots.txt**: LinkedIn's robots.txt disallows most scraping
3. **Use Responsibly**: Only scrape public information you need
4. **Handle Failures**: Expect failures and implement retry logic with exponential backoff
5. **Consider Alternatives**: LinkedIn API (requires partnership) or manual data collection

## Debugging

To see the browser in action:

```python
scraper = LinkedInScraper(headless=False)
```

Check the screenshot saved in the output directory to see what the scraper saw.

## Troubleshooting

### "Playwright is not installed"
```bash
pip install playwright
playwright install chromium
```

### "LinkedIn requires authentication"
- This is expected for most profiles
- Try different URLs or consider using LinkedIn API
- Some company pages may be publicly accessible

### "Rate limited by LinkedIn"
- Wait several hours before trying again
- Use different IP address (VPN)
- Reduce scraping frequency

### "Could not extract username"
- Verify URL format matches supported patterns
- Check for typos in URL
- Ensure URL is a valid LinkedIn page

## Legal and ethical considerations

⚠️ **Important**:

- LinkedIn's Terms of Service prohibit automated scraping
- This scraper is for educational/research purposes only
- Consider using LinkedIn's official API for production use
- Respect privacy and data protection laws (GDPR, CCPA, etc.)
- Only collect publicly available information
- Do not use scraped data for spam or harassment

## Alternative approaches

1. **LinkedIn API**: Official API (requires partnership)
2. **Manual Collection**: Copy data manually
3. **LinkedIn Sales Navigator**: Paid tool with export features
4. **Browser Extensions**: Some browser extensions can export LinkedIn data
5. **Third-party Services**: Companies like ZoomInfo, Apollo.io provide LinkedIn data

## Support

For issues or questions:
1. Check the logs for detailed error messages
2. Review the screenshot to see what the scraper saw
3. Verify LinkedIn hasn't changed their page structure
4. Consider rate limiting or authentication issues

## Updates

LinkedIn frequently updates their website structure. This scraper may need updates:
- Check for changes to CSS selectors
- Monitor for new anti-scraping measures
- Update user agent strings
- Adjust timeout values
