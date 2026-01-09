#!/usr/bin/env python3
"""
Aggregate data from all scraped platforms into a single dashboard-ready JSON file.
Reads individual grantee data files and combines them.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
OUTPUT_DIR = BASE_DIR / "output"
DASHBOARD_DATA_PATH = BASE_DIR.parent / "dashboard" / "data" / "dashboard-data.json"

# Platform colors for dashboard
PLATFORM_COLORS = {
    'twitter': '#1DA1F2',
    'youtube': '#FF0000',
    'instagram': '#E1306C',
    'facebook': '#1877F2',
    'linkedin': '#0A66C2',
    'tiktok': '#000000',
    'bluesky': '#0085FF',
    'threads': '#000000'
}


def scan_grantee_data():
    """Scan all grantee directories and collect data."""
    grantees = []
    platform_totals = defaultdict(lambda: {'posts': 0, 'engagement': 0, 'grantees': 0})

    # Find all grantee directories (exclude non-directories)
    for item in OUTPUT_DIR.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            grantee_data = process_grantee_dir(item)
            if grantee_data['total_posts'] > 0:
                grantees.append(grantee_data)

                # Update platform totals
                for platform, data in grantee_data['platforms'].items():
                    platform_totals[platform]['posts'] += data['posts']
                    platform_totals[platform]['engagement'] += data['engagement']
                    if data['posts'] > 0:
                        platform_totals[platform]['grantees'] += 1

    return grantees, dict(platform_totals)


def process_grantee_dir(grantee_dir):
    """Process a single grantee directory."""
    grantee_name = grantee_dir.name.replace('_', ' ')
    result = {
        'name': grantee_name,
        'platforms': {},
        'total_posts': 0,
        'total_engagement': 0
    }

    # Check each platform subdirectory
    for platform in ['bluesky', 'tiktok', 'youtube', 'twitter', 'instagram', 'facebook', 'linkedin', 'threads']:
        platform_dir = grantee_dir / platform
        if platform_dir.exists():
            data = process_platform_dir(platform_dir)
            if data['posts'] > 0:
                result['platforms'][platform] = data
                result['total_posts'] += data['posts']
                result['total_engagement'] += data['engagement']

    return result


def process_platform_dir(platform_dir):
    """Process a platform directory for a grantee."""
    posts = 0
    engagement = 0

    # Look for posts.json directly in platform dir
    posts_file = platform_dir / "posts.json"
    if posts_file.exists():
        data = read_json(posts_file)
        if isinstance(data, list):
            posts = len(data)
            engagement = sum_engagement(data)

    # Also check subdirectories (YouTube uses channel_id subdirs)
    for subdir in platform_dir.iterdir():
        if subdir.is_dir():
            sub_posts = subdir / "posts.json"
            if sub_posts.exists():
                data = read_json(sub_posts)
                if isinstance(data, list):
                    posts += len(data)
                    engagement += sum_engagement(data)

    return {'posts': posts, 'engagement': engagement}


def sum_engagement(posts):
    """Calculate total engagement from posts."""
    total = 0
    for post in posts:
        # Different platforms use different field names
        likes = post.get('likes') or post.get('like_count') or post.get('likeCount') or 0
        comments = post.get('comments') or post.get('comment_count') or post.get('commentCount') or 0
        shares = post.get('shares') or post.get('share_count') or post.get('shareCount') or post.get('repost_count') or post.get('repostCount') or 0
        views = post.get('views') or post.get('view_count') or post.get('viewCount') or post.get('play_count') or post.get('playCount') or 0

        # Handle None values
        likes = likes if isinstance(likes, (int, float)) else 0
        comments = comments if isinstance(comments, (int, float)) else 0
        shares = shares if isinstance(shares, (int, float)) else 0
        views = views if isinstance(views, (int, float)) else 0

        # Engagement = likes + comments + shares (views counted separately)
        total += int(likes) + int(comments) + int(shares)

    return total


def read_json(path):
    """Read JSON file safely."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def build_dashboard_data(grantees, platform_totals):
    """Build dashboard-ready JSON structure."""
    # Sort grantees by engagement - include ALL grantees, not just top 12
    top_grantees = sorted(grantees, key=lambda x: x['total_engagement'], reverse=True)

    # Build platform data
    platforms = {}
    engagement_by_platform = []

    for platform, data in platform_totals.items():
        platforms[platform] = {
            'posts': data['posts'],
            'engagement': data['engagement'],
            'grantees': data['grantees']
        }
        engagement_by_platform.append({
            'platform': platform,
            'engagement': data['engagement'],
            'posts': data['posts'],
            'color': PLATFORM_COLORS.get(platform, '#6B7280')
        })

    # Sort by engagement
    engagement_by_platform.sort(key=lambda x: x['engagement'], reverse=True)

    # Calculate totals
    total_posts = sum(g['total_posts'] for g in grantees)
    total_engagement = sum(g['total_engagement'] for g in grantees)
    unique_grantees = len([g for g in grantees if g['total_posts'] > 0])

    return {
        'summary': {
            'totalGrantees': unique_grantees,
            'totalPosts': total_posts,
            'totalEngagement': total_engagement,
            'platformsTracked': len([p for p, d in platform_totals.items() if d['posts'] > 0]),
            'lastUpdated': datetime.now().isoformat(),
            'scrapingDuration': 'aggregated'
        },
        'platforms': platforms,
        'topGrantees': [
            {
                'name': g['name'],
                'posts': g['total_posts'],
                'engagement': g['total_engagement'],
                'topPlatform': max(g['platforms'].keys(), key=lambda p: g['platforms'][p]['engagement']) if g['platforms'] else 'N/A',
                'platformsScraped': len(g['platforms'])
            }
            for g in top_grantees
        ],
        'engagementByPlatform': engagement_by_platform,
        'metadata': {
            'generatedAt': datetime.now().isoformat(),
            'platformColors': PLATFORM_COLORS
        }
    }


def main():
    print("Scanning grantee data directories...")
    grantees, platform_totals = scan_grantee_data()

    print(f"\nFound data for {len(grantees)} grantees across {len(platform_totals)} platforms")
    for platform, data in platform_totals.items():
        print(f"  {platform.capitalize():12}: {data['posts']:4} posts, {data['engagement']:8} engagement, {data['grantees']:2} grantees")

    print("\nBuilding dashboard data...")
    dashboard_data = build_dashboard_data(grantees, platform_totals)

    print("\nDashboard Summary:")
    print(f"  Total Grantees with data: {dashboard_data['summary']['totalGrantees']}")
    print(f"  Total Posts: {dashboard_data['summary']['totalPosts']}")
    print(f"  Total Engagement: {dashboard_data['summary']['totalEngagement']}")
    print(f"  Platforms: {dashboard_data['summary']['platformsTracked']}")

    # Save to both locations
    output_paths = [
        OUTPUT_DIR / "dashboard-data.json",
        DASHBOARD_DATA_PATH
    ]

    for path in output_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(dashboard_data, f, indent=2)
        print(f"\nSaved: {path}")

    print("\nDone!")


if __name__ == '__main__':
    main()
