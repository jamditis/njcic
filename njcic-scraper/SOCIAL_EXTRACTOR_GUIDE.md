# Social Media URL Extractor - User Guide

## Overview

The `extract_social_urls.py` script automatically extracts social media links from NJCIC grantee websites and outputs a structured JSON file with the results.

## Quick Start

### 1. Install Dependencies

```bash
cd /home/user/njcic/njcic-scraper
pip install -r requirements.txt
```

### 2. Run the Extractor

```bash
python3 scripts/extract_social_urls.py
```

The script will:
- Read grantee data from `/home/user/njcic/repos/njcic-grantees-map/data/grantees.json`
- Fetch each grantee's website
- Extract social media URLs
- Save results to `/home/user/njcic/njcic-scraper/data/grantees_with_social.json`
- Display progress and statistics

## Features

### Supported Platforms

✓ Facebook  
✓ Twitter/X  
✓ Instagram  
✓ LinkedIn  
✓ YouTube  
✓ TikTok  
✓ Threads  
✓ BlueSky  

### Extraction Strategy

The script uses a multi-layered approach to find social media links:

1. **Meta Tags** (highest priority)
   - Open Graph tags (`og:url`, `fb:page_id`)
   - Twitter cards (`twitter:site`, `twitter:creator`)
   - Instagram tags

2. **Header/Footer Links** (high priority)
   - Links within `<header>`, `<footer>`, `<nav>` elements
   - Elements with class/id containing "social", "footer", "header"

3. **All Page Links** (medium priority)
   - All `<a href>` tags on the page

4. **Text Content** (fallback)
   - Plain text URLs in page content

### Smart URL Normalization

- Adds `https://` protocol if missing
- Normalizes platform-specific URLs:
  - `x.com` → `twitter.com`
  - `fb.com` → `facebook.com`
  - `m.facebook.com` → `www.facebook.com`
- Removes unnecessary URL parameters
- Removes trailing slashes

### Error Handling

- **HTTP Errors**: Retries failed requests up to 2 times
- **Timeouts**: 10-second timeout per request with retry
- **Parsing Errors**: Continues processing other grantees
- **Missing Websites**: Skips gracefully and logs warning
- **Rate Limiting**: 0.5-second delay between requests

## Output Format

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
        "linkedin": "https://linkedin.com/company/example",
        "youtube": "https://youtube.com/@example",
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
      "linkedin": 28,
      "youtube": 15,
      "tiktok": 8,
      "threads": 3,
      "bluesky": 2
    }
  }
}
```

## Configuration Options

Edit the constants at the top of `extract_social_urls.py`:

```python
REQUEST_TIMEOUT = 10     # HTTP request timeout (seconds)
REQUEST_DELAY = 0.5      # Delay between requests (seconds)
MAX_RETRIES = 2          # Number of retry attempts
USER_AGENT = "..."       # Browser user agent string
```

## Example Output

```
======================================================================
NJCIC Social Media URL Extractor
======================================================================

Loading grantee data from: /home/user/njcic/repos/njcic-grantees-map/data/grantees.json
✓ Loaded 75 grantees

Processing 72 grantees with websites...
Extracting social links: 100%|███████████████████| 72/72 [01:23<00:00,  1.15s/it]

======================================================================
Extraction Complete!
======================================================================
Total grantees processed: 72

Social media links found:
  Facebook       45 ( 62.5%)
  Twitter        38 ( 52.8%)
  Instagram      32 ( 44.4%)
  Linkedin       28 ( 38.9%)
  Youtube        15 ( 20.8%)
  Tiktok          8 ( 11.1%)
  Threads         3 (  4.2%)
  Bluesky         2 (  2.8%)

Saving results to: /home/user/njcic/njcic-scraper/data/grantees_with_social.json
✓ Results saved successfully!
```

## Testing

Test the extractor with sample HTML:

```bash
python3 scripts/test_extractor.py
```

This will run the extractor on a sample HTML page to verify it's working correctly.

## Troubleshooting

### Script fails to fetch websites

**Problem**: Some websites may block automated requests

**Solution**: 
- The script already uses a realistic browser User-Agent
- Increase `REQUEST_TIMEOUT` if sites are slow to respond
- Check if the website is actually accessible in a browser

### Missing social media links

**Problem**: Script doesn't find links that exist on the page

**Solution**:
- Check if the links use non-standard URL formats
- Add additional regex patterns to `PATTERNS` dict
- Check if links are loaded via JavaScript (script only analyzes static HTML)

### "ModuleNotFoundError"

**Problem**: Required Python packages not installed

**Solution**:
```bash
pip install -r requirements.txt
```

### Extraction is too slow

**Problem**: Processing takes a long time

**Solution**:
- Decrease `REQUEST_TIMEOUT` (faster but may miss slow sites)
- Decrease `REQUEST_DELAY` (faster but less respectful)
- Process a subset of grantees by modifying the input data

## Performance

- **Average time per website**: 1-2 seconds
- **Total time for 75 grantees**: ~2-3 minutes
- **Success rate**: ~95% (assuming websites are accessible)

## Use Cases

1. **Social Media Audit**: Identify which grantees have social media presence
2. **Contact Information**: Collect alternative contact channels
3. **Outreach Campaigns**: Plan social media engagement strategies
4. **Data Analysis**: Analyze social media adoption by region/focus area
5. **Report Generation**: Include social media links in grantee directories

## Next Steps

After running the extractor, you can:

1. Import the JSON into spreadsheet software for analysis
2. Use the data to populate a grantee directory website
3. Track social media engagement metrics for each platform
4. Identify grantees that need help with digital presence
5. Create social media lists/groups for better communication

## Technical Details

**Language**: Python 3.7+  
**Dependencies**: requests, beautifulsoup4, tqdm  
**Input Format**: JSON (from Airtable sync)  
**Output Format**: JSON with metadata  
**HTTP Method**: GET with browser headers  
**Parsing**: BeautifulSoup4 HTML parser  

## Support

For issues or questions:
- Check the main README.md
- Review the inline code documentation
- Test with `test_extractor.py` to isolate issues

