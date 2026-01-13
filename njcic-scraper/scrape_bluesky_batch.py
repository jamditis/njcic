#!/usr/bin/env python
"""
Automated Bluesky scraper for all NJCIC grantees.
Uses public AT Protocol API - no login required.
"""

import sys
import json
import time
import re
import requests
from pathlib import Path
from datetime import datetime

# Load grantee data
GRANTEES_DIR = Path(__file__).parent.parent / "dashboard" / "data" / "grantees"
OUTPUT_DIR = Path(__file__).parent / "output"
MAX_POSTS = 50


def get_bluesky_grantees():
    """Load all grantees with Bluesky accounts."""
    grantees = []

    for json_file in GRANTEES_DIR.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            bluesky_url = data.get('social', {}).get('bluesky')
            if bluesky_url:
                # Extract handle from URL
                match = re.search(r'bsky\.app/profile/([^/\s]+)', bluesky_url)
                if match:
                    handle = match.group(1)
                    grantees.append({
                        'name': data.get('name', json_file.stem),
                        'slug': data.get('slug', json_file.stem),
                        'handle': handle,
                        'url': bluesky_url
                    })
        except Exception as e:
            print(f"Warning: Could not load {json_file}: {e}")

    return grantees


def resolve_handle(handle):
    """Resolve a Bluesky handle to DID."""
    try:
        resp = requests.get(
            f"https://bsky.social/xrpc/com.atproto.identity.resolveHandle",
            params={"handle": handle},
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json().get('did')
    except:
        pass
    return None


def get_profile(actor):
    """Get profile info for an actor (handle or DID)."""
    try:
        resp = requests.get(
            "https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile",
            params={"actor": actor},
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None


def get_author_feed(actor, limit=50, cursor=None):
    """Get posts from an author's feed."""
    try:
        params = {"actor": actor, "limit": min(limit, 100)}
        if cursor:
            params["cursor"] = cursor

        resp = requests.get(
            "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed",
            params=params,
            timeout=30
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"    Error fetching feed: {e}")
    return None


def scrape_grantee(grantee):
    """Scrape a single grantee's Bluesky."""
    print(f"\n{'='*60}")
    print(f"Scraping: {grantee['name']}")
    print(f"Handle: {grantee['handle']}")
    print(f"{'='*60}")

    # Get profile
    profile = get_profile(grantee['handle'])
    if not profile:
        print(f"  ERROR: Could not fetch profile")
        return None

    followers = profile.get('followersCount', 0)
    following = profile.get('followsCount', 0)
    posts_count = profile.get('postsCount', 0)
    display_name = profile.get('displayName', grantee['handle'])

    print(f"  Profile: {display_name}")
    print(f"  Followers: {followers:,} | Following: {following:,} | Posts: {posts_count:,}")

    # Get posts
    posts = []
    cursor = None

    while len(posts) < MAX_POSTS:
        feed_data = get_author_feed(grantee['handle'], limit=50, cursor=cursor)
        if not feed_data:
            break

        feed = feed_data.get('feed', [])
        if not feed:
            break

        for item in feed:
            post = item.get('post', {})
            record = post.get('record', {})

            # Extract post data
            uri = post.get('uri', '')
            cid = post.get('cid', '')

            # Get post ID from URI (at://did:plc:xxx/app.bsky.feed.post/yyy)
            post_id = uri.split('/')[-1] if uri else ''

            text = record.get('text', '')
            created_at = record.get('createdAt', '')

            # Engagement
            likes = post.get('likeCount', 0)
            reposts = post.get('repostCount', 0)
            replies = post.get('replyCount', 0)
            quotes = post.get('quoteCount', 0)

            # Determine content type
            embed = post.get('embed', {}) or record.get('embed', {})
            embed_type = embed.get('$type', '') if embed else ''

            if 'image' in embed_type:
                content_type = 'image'
            elif 'video' in embed_type:
                content_type = 'video'
            elif 'external' in embed_type:
                content_type = 'link'
            elif 'record' in embed_type:
                content_type = 'quote'
            else:
                content_type = 'text'

            post_data = {
                'post_id': post_id,
                'uri': uri,
                'cid': cid,
                'url': f"https://bsky.app/profile/{grantee['handle']}/post/{post_id}",
                'text': text[:500],
                'created_at': created_at,
                'likes': likes,
                'reposts': reposts,
                'replies': replies,
                'quotes': quotes,
                'total_engagement': likes + reposts + replies + quotes,
                'content_type': content_type,
                'platform': 'bluesky'
            }
            posts.append(post_data)

            if len(posts) >= MAX_POSTS:
                break

        cursor = feed_data.get('cursor')
        if not cursor:
            break

        time.sleep(0.5)  # Rate limiting

    print(f"  Collected {len(posts)} posts")

    # Calculate totals
    total_likes = sum(p['likes'] for p in posts)
    total_reposts = sum(p['reposts'] for p in posts)
    total_replies = sum(p['replies'] for p in posts)

    print(f"  Total engagement: {total_likes + total_reposts + total_replies:,}")

    # Save data
    grantee_safe = re.sub(r'[^\w\-]', '_', grantee['name'].replace(' ', '_'))
    output_dir = OUTPUT_DIR / grantee_safe / "bluesky" / grantee['handle']
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "posts.json", 'w', encoding='utf-8') as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

    metadata = {
        'url': grantee['url'],
        'handle': grantee['handle'],
        'display_name': display_name,
        'grantee_name': grantee['name'],
        'scraped_at': datetime.now().isoformat(),
        'posts_downloaded': len(posts),
        'engagement_metrics': {
            'followers_count': followers,
            'following_count': following,
            'posts_count': posts_count,
            'total_likes': total_likes,
            'total_reposts': total_reposts,
            'total_replies': total_replies,
            'avg_engagement': round((total_likes + total_reposts + total_replies) / len(posts), 2) if posts else 0
        },
        'platform': 'bluesky',
        'method': 'api'
    }

    with open(output_dir / "metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)

    return metadata


def main():
    print("="*60)
    print("BLUESKY BATCH SCRAPER")
    print("="*60)

    grantees = get_bluesky_grantees()
    print(f"\nFound {len(grantees)} grantees with Bluesky accounts\n")

    results = []
    success = 0
    failed = 0

    for i, grantee in enumerate(grantees, 1):
        print(f"\n[{i}/{len(grantees)}]", end="")

        try:
            result = scrape_grantee(grantee)
            if result:
                results.append({
                    'grantee': grantee['name'],
                    'handle': grantee['handle'],
                    'posts': result['posts_downloaded'],
                    'followers': result['engagement_metrics']['followers_count'],
                    'status': 'success'
                })
                success += 1
            else:
                results.append({
                    'grantee': grantee['name'],
                    'handle': grantee['handle'],
                    'status': 'failed'
                })
                failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                'grantee': grantee['name'],
                'handle': grantee['handle'],
                'status': 'error',
                'error': str(e)
            })
            failed += 1

        time.sleep(1)  # Rate limiting between grantees

    # Save summary
    summary = {
        'scraped_at': datetime.now().isoformat(),
        'total_grantees': len(grantees),
        'success': success,
        'failed': failed,
        'results': results
    }

    with open(OUTPUT_DIR / "bluesky_batch_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)

    print("\n" + "="*60)
    print("BLUESKY BATCH COMPLETE")
    print("="*60)
    print(f"Success: {success}/{len(grantees)}")
    print(f"Failed: {failed}/{len(grantees)}")
    print(f"Summary saved to: output/bluesky_batch_summary.json")


if __name__ == "__main__":
    main()
