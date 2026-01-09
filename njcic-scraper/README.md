# NJCIC grantee social media scraper

Production-ready infrastructure for extracting social media URLs and scraping content from NJCIC grantee organizations across multiple platforms.

## Project overview

This project contains two main components:

1. **Social URL Extraction** - Extracts social media links from grantee websites
2. **Base Scraper Infrastructure** - Framework for scraping content from social media platforms

## Installation

```bash
# Navigate to the project directory
cd /home/user/njcic/njcic-scraper

# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables for API access
cp .env.example .env
# Edit .env and add your API keys and credentials

# Install Playwright browsers (if using browser automation)
playwright install
```

## Project structure

```
njcic-scraper/
├── config.py                      # Central configuration and settings
├── requirements.txt               # Python dependencies
├── .env.example                   # Example environment variables
├── .gitignore                     # Git ignore rules
├── README.md                      # This file
├── scrapers/
│   ├── __init__.py               # Package initialization
│   └── base.py                   # Abstract base scraper class
├── scripts/
│   └── extract_social_urls.py   # Social media URL extractor
├── output/                       # Scraped data (auto-created)
├── data/                         # Input data and references (auto-created)
└── logs/                         # Application logs (auto-created)
```

## Base scraper infrastructure

### Features

- **Multi-platform support**: Facebook, Instagram, Twitter/X, YouTube, TikTok, LinkedIn
- **Rate limiting**: Respects platform guidelines with configurable delays
- **Robust error handling**: Continues scraping even when individual posts fail
- **Engagement metrics**: Tracks likes, comments, shares, views, and reactions
- **Structured output**: Organized by grantee and platform
- **Comprehensive logging**: File and console logging with configurable levels
- **Data validation**: Ensures all posts contain required fields
- **Metadata tracking**: Saves scraping metadata for audit trails

### Key configuration settings

- **MAX_POSTS_PER_ACCOUNT**: 25 (as requested)
- **REQUEST_DELAY**: 2 seconds between requests
- **TIMEOUT**: 30 seconds for requests
- **MAX_RETRIES**: 3 retry attempts for failed requests

### Creating a platform-specific scraper

All platform scrapers inherit from `BaseScraper`:

```python
from scrapers.base import BaseScraper
import config

class FacebookScraper(BaseScraper):
    platform_name = "facebook"

    def extract_username(self, url: str) -> Optional[str]:
        # Extract username from Facebook URL
        pass

    def scrape(self, url: str, grantee_name: str, max_posts: Optional[int] = None) -> Dict[str, Any]:
        max_posts = max_posts or config.MAX_POSTS_PER_ACCOUNT
        output_path = self.get_output_path(grantee_name)

        posts = []
        errors = []

        # Scrape with rate limiting
        for post in self._fetch_posts(url, max_posts):
            self.rate_limit()
            posts.append(post)

        # Save results
        self.save_posts(posts, output_path)
        engagement = self.calculate_engagement_metrics(posts)

        metadata = {
            "url": url,
            "grantee_name": grantee_name,
            "posts_scraped": len(posts),
            "engagement_metrics": engagement
        }
        self.save_metadata(output_path, metadata)

        return {
            "success": True,
            "posts_downloaded": len(posts),
            "errors": errors,
            "engagement_metrics": engagement,
            "output_path": str(output_path)
        }
```

### Base scraper methods

**Required (Abstract):**
- `extract_username(url)` - Extract username from platform URL
- `scrape(url, grantee_name, max_posts)` - Scrape posts and return results

**Provided (Inherited):**
- `get_output_path(grantee_name)` - Create platform-specific output directory
- `save_metadata(output_path, metadata)` - Save metadata to JSON
- `save_posts(posts, output_path)` - Save posts to JSON
- `save_errors(errors, output_path)` - Save errors to JSON
- `rate_limit()` - Implement rate limiting
- `calculate_engagement_metrics(posts)` - Calculate engagement statistics
- `validate_post(post)` - Validate post has required fields

### Output structure

```
output/
└── Example_Organization/
    ├── facebook/
    │   ├── posts.json           # Scraped posts
    │   ├── metadata.json        # Scraping metadata
    │   └── errors.json          # Error log (if any)
    ├── instagram/
    └── twitter/
```

## Scripts

### extract_social_urls.py

Extracts social media links from grantee websites.

**Features:**
- Fetches HTML from each grantee website
- Searches multiple locations: meta tags, headers, footers, links, and text content
- Supports 8 platforms: Facebook, Twitter/X, Instagram, LinkedIn, YouTube, TikTok, Threads, BlueSky
- Handles errors gracefully with retry logic
- Shows progress bar with tqdm
- Outputs structured JSON with statistics

**Usage:**

```bash
# Install dependencies
pip install -r requirements.txt

# Run the scraper
python scripts/extract_social_urls.py
```

**Input:** `/home/user/njcic/repos/njcic-grantees-map/data/grantees.json`

**Output:** `/home/user/njcic/njcic-scraper/data/grantees_with_social.json`

**Output Format:**

```json
{
  "grantees": [
    {
      "name": "Organization Name",
      "website": "https://example.org",
      "social": {
        "facebook": "https://www.facebook.com/example",
        "twitter": "https://twitter.com/example",
        "instagram": "https://instagram.com/example",
        "linkedin": null,
        "youtube": null,
        "tiktok": null,
        "threads": null,
        "bluesky": null
      }
    }
  ],
  "metadata": {
    "total_grantees": 75,
    "extraction_date": "2026-01-07",
    "source_file": "/home/user/njcic/repos/njcic-grantees-map/data/grantees.json",
    "statistics": {
      "facebook": 45,
      "twitter": 38,
      "instagram": 32,
      ...
    }
  }
}
```

**Configuration:**

Edit the constants at the top of the script to customize:
- `REQUEST_TIMEOUT`: HTTP request timeout (default: 10 seconds)
- `REQUEST_DELAY`: Delay between requests (default: 0.5 seconds)
- `MAX_RETRIES`: Number of retry attempts (default: 2)
- `USER_AGENT`: Browser user agent string

**How It Works:**

1. Loads grantee data from JSON file
2. For each grantee with a website:
   - Fetches the website HTML
   - Searches for social media links in:
     - Meta tags (Open Graph, Twitter cards)
     - Header and footer sections
     - All links on the page
     - Text content (fallback)
   - Normalizes URLs to consistent format
3. Outputs JSON with social media links for each grantee
4. Displays statistics on extraction success

**Error Handling:**

- Failed HTTP requests are retried up to MAX_RETRIES times
- Timeouts are handled gracefully
- HTML parsing errors don't stop the entire process
- Progress and errors are shown in real-time

## Dependencies

All dependencies are listed in `requirements.txt`:

**Core scraping:**
- yt-dlp (video downloading)
- instaloader (Instagram)
- playwright (browser automation)
- requests, aiohttp (HTTP)
- beautifulsoup4 (HTML parsing)

**Data handling:**
- pandas (data manipulation)
- pydantic (validation)

**Social media APIs:**
- tweepy (Twitter/X)
- facebook-sdk (Facebook)

**Utilities:**
- tqdm (progress bars)
- python-dotenv (environment variables)
- coloredlogs (enhanced logging)

## Notes

- The script respects websites with a 0.5-second delay between requests
- URLs are normalized for consistency (e.g., x.com → twitter.com)
- Links found in header/footer sections are prioritized
- The script can handle various URL formats and edge cases

## Future enhancements

**Scraper Infrastructure:**
- Implement platform-specific scrapers (Facebook, Instagram, Twitter, etc.)
- Create main orchestration script to scrape all grantees
- Add CSV export functionality
- Implement media downloading (images, videos)
- Add data analysis and reporting dashboard

**URL Extraction:**
- Add email extraction from websites
- Extract contact forms
- Analyze website accessibility
- Check for broken links
- Extract organization logos

## Environment variables

Copy `.env.example` to `.env` and configure your API credentials:

- **Twitter/X**: API key, secret, bearer token
- **Facebook**: Access token, app ID, app secret
- **Instagram**: Username and password (use dedicated account)
- **YouTube**: API key
- **LinkedIn**: Email and password (use dedicated account)
- **TikTok**: Client key and secret (optional)

**IMPORTANT**: Never commit your `.env` file to version control!

## Logging

Logs are written to:
- **File**: `logs/scraper.log`
- **Console**: Real-time output

Configure log level in `.env`:
```
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Support

For issues or questions, refer to the project documentation or contact the development team.

## License

Internal use only - NJCIC project.
