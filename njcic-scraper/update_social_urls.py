#!/usr/bin/env python
"""
Update grantee JSON files with newly found social media URLs.
Also normalizes Twitter URLs to x.com format.
"""

import json
from pathlib import Path

GRANTEES_DIR = Path(__file__).parent.parent / "dashboard" / "data" / "grantees"

# New URLs found through web searches
NEW_URLS = {
    "radio-rouj-ble": {
        "twitter": "https://x.com/RadioRouje"
    },
    "stories-of-atlantic-city": {
        "instagram": "https://www.instagram.com/stories_of_ac/"
    },
    "morristown-green": {
        "youtube": "https://www.youtube.com/user/MorristownGreen",
        "linkedin": "https://www.linkedin.com/company/morristown-green"
    },
    "paterson-alliance": {
        "twitter": "https://x.com/VibrantPaterson"
    },
    "beyond-expectations": {
        "facebook": "https://www.facebook.com/beyondexpfanpage"
    },
    "asbury-park-media-collective": {
        "instagram": "https://www.instagram.com/asburyparkreporter/",
        "linkedin": "https://www.linkedin.com/company/asburyparkreporter"
    },
    "camden-fireworks": {
        "facebook": "https://www.facebook.com/CamdenFireWorksArt/"
    },
    "new-labor": {
        "linkedin": "https://www.linkedin.com/company/new-labor"
    },
    "mercerme": {
        "linkedin": "https://www.linkedin.com/company/mercerme"
    },
    "newark-news-and-story-collaborative": {
        "linkedin": "https://www.linkedin.com/company/newark-stories"
    },
    "trenton-journal": {
        "facebook": "https://www.facebook.com/trentonjournal"
    },
    "front-runner-new-jersey": {
        "linkedin": "https://www.linkedin.com/company/frontrunnernewjersey"
    },
    "south-jersey-climate-news-project": {
        "twitter": "https://x.com/sjclimatenews",
        "facebook": "https://www.facebook.com/sj.climatenews"
    }
}


def normalize_twitter_url(url):
    """Convert twitter.com URLs to x.com"""
    if url and "twitter.com" in url:
        return url.replace("twitter.com", "x.com")
    return url


def update_grantee(filepath, new_urls=None):
    """Update a single grantee file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    slug = filepath.stem
    modified = False

    # Initialize social dict if missing
    if 'social' not in data:
        data['social'] = {}

    # Add new URLs if provided
    if new_urls:
        for platform, url in new_urls.items():
            if not data['social'].get(platform):
                data['social'][platform] = url
                print(f"  + Added {platform}: {url}")
                modified = True

    # Normalize Twitter URLs to x.com
    if data['social'].get('twitter'):
        old_url = data['social']['twitter']
        new_url = normalize_twitter_url(old_url)
        if old_url != new_url:
            data['social']['twitter'] = new_url
            print(f"  ~ Normalized Twitter: {old_url} -> {new_url}")
            modified = True

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    return modified


def main():
    print("="*60)
    print("UPDATING GRANTEE SOCIAL MEDIA URLs")
    print("="*60)

    updated = 0

    for filepath in sorted(GRANTEES_DIR.glob("*.json")):
        slug = filepath.stem
        new_urls = NEW_URLS.get(slug)

        print(f"\n{slug}:")

        if update_grantee(filepath, new_urls):
            updated += 1
        else:
            print("  (no changes)")

    print("\n" + "="*60)
    print(f"Updated {updated} grantee files")
    print("="*60)


if __name__ == "__main__":
    main()
