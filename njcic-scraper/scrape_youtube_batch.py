#!/usr/bin/env python
"""
Automated YouTube scraper for all NJCIC grantees.
Uses yt-dlp to fetch channel/video data - no login required.
"""

import sys
import json
import time
import re
import subprocess
from pathlib import Path
from datetime import datetime

GRANTEES_DIR = Path(__file__).parent.parent / "dashboard" / "data" / "grantees"
OUTPUT_DIR = Path(__file__).parent / "output"
MAX_VIDEOS = 50


def get_youtube_grantees():
    """Load all grantees with YouTube accounts."""
    grantees = []

    for json_file in GRANTEES_DIR.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            youtube_url = data.get('social', {}).get('youtube')
            if youtube_url:
                grantees.append({
                    'name': data.get('name', json_file.stem),
                    'slug': data.get('slug', json_file.stem),
                    'url': youtube_url
                })
        except Exception as e:
            print(f"Warning: Could not load {json_file}: {e}")

    return grantees


YTDLP_PATH = "yt-dlp"  # Will be set by main()

def scrape_youtube_channel(grantee):
    """Scrape a YouTube channel using yt-dlp."""
    global YTDLP_PATH
    print(f"\n{'='*60}")
    print(f"Scraping: {grantee['name']}")
    print(f"URL: {grantee['url']}")
    print(f"{'='*60}")

    # Normalize URL to get videos tab
    url = grantee['url'].rstrip('/')
    if '/videos' not in url:
        url = url + '/videos'

    try:
        # Use yt-dlp to get channel info and video list
        cmd = [
            YTDLP_PATH,
            '--dump-json',
            '--flat-playlist',
            '--playlist-end', str(MAX_VIDEOS),
            '--no-warnings',
            url
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            print(f"  ERROR: yt-dlp failed: {result.stderr[:200]}")
            return None

        # Parse JSON lines output
        videos = []
        channel_info = {}

        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                data = json.loads(line)

                # Extract video info
                video = {
                    'video_id': data.get('id', ''),
                    'title': data.get('title', ''),
                    'url': data.get('url', '') or f"https://www.youtube.com/watch?v={data.get('id', '')}",
                    'duration': data.get('duration', 0),
                    'view_count': data.get('view_count', 0),
                    'like_count': data.get('like_count', 0),
                    'upload_date': data.get('upload_date', ''),
                    'platform': 'youtube'
                }

                # Calculate engagement
                video['total_engagement'] = (video['like_count'] or 0)

                videos.append(video)

                # Try to get channel info from first video
                if not channel_info and data.get('channel'):
                    channel_info = {
                        'channel_name': data.get('channel', ''),
                        'channel_id': data.get('channel_id', ''),
                        'channel_url': data.get('channel_url', ''),
                        'subscriber_count': data.get('channel_follower_count', 0)
                    }

            except json.JSONDecodeError:
                continue

        print(f"  Found {len(videos)} videos")

        if not videos:
            return None

        # Get more detailed info for first few videos
        total_views = sum(v.get('view_count', 0) or 0 for v in videos)
        total_likes = sum(v.get('like_count', 0) or 0 for v in videos)

        print(f"  Total views: {total_views:,}")
        print(f"  Total likes: {total_likes:,}")

        # Save data
        grantee_safe = re.sub(r'[^\w\-]', '_', grantee['name'].replace(' ', '_'))
        output_dir = OUTPUT_DIR / grantee_safe / "youtube"
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_dir / "videos.json", 'w', encoding='utf-8') as f:
            json.dump(videos, f, indent=2, ensure_ascii=False)

        metadata = {
            'url': grantee['url'],
            'grantee_name': grantee['name'],
            'scraped_at': datetime.now().isoformat(),
            'videos_downloaded': len(videos),
            'channel_info': channel_info,
            'engagement_metrics': {
                'subscriber_count': channel_info.get('subscriber_count', 0),
                'total_views': total_views,
                'total_likes': total_likes,
                'avg_views': round(total_views / len(videos), 2) if videos else 0,
                'avg_likes': round(total_likes / len(videos), 2) if videos else 0
            },
            'platform': 'youtube',
            'method': 'yt-dlp'
        }

        with open(output_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)

        return metadata

    except subprocess.TimeoutExpired:
        print(f"  ERROR: Timeout fetching channel")
        return None
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def main():
    print("="*60)
    print("YOUTUBE BATCH SCRAPER")
    print("="*60)

    # Check if yt-dlp is installed - use venv path on Windows
    ytdlp_path = Path(__file__).parent / "venv" / "Scripts" / "yt-dlp.exe"
    if not ytdlp_path.exists():
        ytdlp_path = "yt-dlp"  # Fall back to PATH
    else:
        ytdlp_path = str(ytdlp_path)

    try:
        result = subprocess.run([ytdlp_path, '--version'], capture_output=True, text=True)
        print(f"Using yt-dlp version: {result.stdout.strip()}")
    except FileNotFoundError:
        print("ERROR: yt-dlp not installed!")
        print("Install with: pip install yt-dlp")
        sys.exit(1)

    # Store for use in scrape function
    global YTDLP_PATH
    YTDLP_PATH = ytdlp_path

    grantees = get_youtube_grantees()
    print(f"\nFound {len(grantees)} grantees with YouTube accounts\n")

    results = []
    success = 0
    failed = 0

    for i, grantee in enumerate(grantees, 1):
        print(f"\n[{i}/{len(grantees)}]", end="")

        try:
            result = scrape_youtube_channel(grantee)
            if result:
                results.append({
                    'grantee': grantee['name'],
                    'url': grantee['url'],
                    'videos': result['videos_downloaded'],
                    'views': result['engagement_metrics']['total_views'],
                    'status': 'success'
                })
                success += 1
            else:
                results.append({
                    'grantee': grantee['name'],
                    'url': grantee['url'],
                    'status': 'failed'
                })
                failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                'grantee': grantee['name'],
                'url': grantee['url'],
                'status': 'error',
                'error': str(e)
            })
            failed += 1

        time.sleep(2)  # Rate limiting between channels

    # Save summary
    summary = {
        'scraped_at': datetime.now().isoformat(),
        'total_grantees': len(grantees),
        'success': success,
        'failed': failed,
        'results': results
    }

    with open(OUTPUT_DIR / "youtube_batch_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)

    print("\n" + "="*60)
    print("YOUTUBE BATCH COMPLETE")
    print("="*60)
    print(f"Success: {success}/{len(grantees)}")
    print(f"Failed: {failed}/{len(grantees)}")
    print(f"Summary saved to: output/youtube_batch_summary.json")


if __name__ == "__main__":
    main()
