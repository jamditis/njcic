# Instagram manual login scraper

Batch scrape Instagram profiles for all NJCIC grantees using manual authentication.

## Quick start

```bash
cd njcic-scraper
./venv/Scripts/python.exe scrape_instagram_batch.py
```

1. Browser opens to Instagram login
2. Log in (handle 2FA if needed)
3. Signal ready: `touch output/READY_TO_SCRAPE`
4. Wait for completion (55 accounts, ~2-3 min each)
5. Close browser: `touch output/CLOSE_BROWSER`

## What it collects

- Follower/following counts
- Post URLs and shortcodes
- Likes and comments (for first 10 posts per account)
- Caption previews from alt text

## Notes

- Instagram is aggressive with rate limiting - script uses longer delays
- Engagement data may show 0s if Instagram's page structure changed
- Post URLs are always collected even if metrics fail
- Accounts with 0 posts are skipped

## Resume capability

If interrupted, restart the script - it automatically skips accounts that have `metadata.json` files.
