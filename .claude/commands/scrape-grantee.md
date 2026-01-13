# Scrape grantee social media

Scrape social media posts for any NJCIC grantee across multiple platforms using a manual login workflow.

## Quick start

```bash
cd njcic-scraper
venv\Scripts\activate

# Scrape a specific platform
python scrape_grantee.py --platform twitter --grantee "NJ Spotlight" --url "https://twitter.com/njspotlight"
```

## Supported platforms

| Platform | Login required | Notes |
|----------|---------------|-------|
| Twitter/X | Yes | Full engagement metrics via aria-labels |
| Instagram | Yes | Visits each post for likes/comments |
| Facebook | Yes | Limited to public posts |
| TikTok | Yes | Profile + video collection |
| LinkedIn | Yes | Company page posts (public view only for non-admin) |
| YouTube | No | Use yt-dlp or API instead |
| Bluesky | No | Use public AT Protocol API instead |

## Workflow

1. **Run the scraper** with platform, grantee name, and URL
2. **Browser opens** to login page
3. **Log in manually** (handle 2FA, captchas)
4. **Signal to start**: `touch output/READY_TO_SCRAPE`
5. **Scraper runs** - collects posts by scrolling
6. **Browser stays open** for inspection
7. **Signal to close**: `touch output/CLOSE_BROWSER`

## Command-line arguments

```
--platform, -p    Platform to scrape (required)
                  Options: twitter, instagram, facebook, tiktok, linkedin

--grantee, -g     Organization name (required)
                  Used for output directory naming

--url, -u         Profile/page URL to scrape (required)
```

## Examples

### Twitter
```bash
python scrape_grantee.py -p twitter -g "NJ Spotlight News" -u "https://twitter.com/njspotlight"
```

### Instagram
```bash
python scrape_grantee.py -p instagram -g "TAPinto" -u "https://instagram.com/tapintonewjersey"
```

### LinkedIn (public view)
```bash
python scrape_grantee.py -p linkedin -g "WHYY" -u "https://linkedin.com/company/whyy"
```

### TikTok
```bash
python scrape_grantee.py -p tiktok -g "NJ Advance Media" -u "https://tiktok.com/@njadvancemedia"
```

## Output structure

```
output/
  {Grantee_Name}/
    {platform}/
      {username}/
        posts.json      # Array of post data
        metadata.json   # Scrape metadata + metrics
        screenshot.png  # Final page screenshot
  .cookies/
    {platform}_cookies.json  # Saved auth cookies
```

## Post data fields

### Twitter
- post_id, text, likes, retweets, replies, total_engagement

### Instagram
- post_id, shortcode, url, caption_preview, likes, comments, total_engagement

### Facebook
- post_id, url, text

### TikTok
- post_id, video_id, url

### LinkedIn
- post_id, text, likes

## Engagement metrics (metadata.json)

Each platform's metadata includes aggregated engagement:
- `followers_count` - Profile followers
- `total_likes` - Sum of likes across posts
- Platform-specific metrics (retweets, comments, shares, etc.)

## Admin vs public access

**CCM (admin access):**
- Navigate to admin URL: `linkedin.com/company/{id}/admin/page-posts/published/`
- Can see all historical posts
- More engagement data available

**Other grantees (public access):**
- Limited to public posts feed
- Some engagement metrics may be hidden
- Fewer posts visible (typically recent posts only)

## Batch processing multiple grantees

Create a CSV with grantee info and loop through:

```bash
# grantees.csv format:
# grantee_name,platform,url

while IFS=, read -r grantee platform url; do
    python scrape_grantee.py -p "$platform" -g "$grantee" -u "$url"
done < grantees.csv
```

## Troubleshooting

### Rate limiting
Add delays between requests. Edit scraper to increase `wait_for_timeout` values.

### Login issues
Clear cookies and try fresh login. Some platforms detect automation even with stealth mode.

### Missing engagement data
Platform may hide metrics for non-logged-in or non-admin users. Logged-in scraping helps.

### Browser closes unexpectedly
Check for errors in console. Increase timeout values if needed.

## Related skills

- `/scrape-social` - General manual login scraping documentation
- `/scrape-instagram` - Instagram-specific instructions

## See also

- `njcic-scraper/scrape_grantee.py` - Main parameterized scraper
- `njcic-scraper/output/` - All scraped data
- `dashboard/data/grantees.json` - Grantee social media URLs
