#!/usr/bin/env python3
"""
Regenerate dashboard-data.json from individual grantee JSON files.
This reads all files in dashboard/data/grantees/ and builds a complete dashboard-data.json.
"""

import json
from pathlib import Path
from datetime import datetime

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
DASHBOARD_DIR = SCRIPT_DIR.parent
GRANTEES_DIR = DASHBOARD_DIR / "data" / "grantees"
OUTPUT_PATH = DASHBOARD_DIR / "data" / "dashboard-data.json"

# Platform colors
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


def load_grantee_data():
    """Load all grantee JSON files."""
    grantees = []
    platform_totals = {}

    for json_file in sorted(GRANTEES_DIR.glob("*.json")):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Get summary data
            summary = data.get('summary', {})
            name = data.get('name', json_file.stem.replace('-', ' ').title())
            slug = data.get('slug', json_file.stem)

            total_posts = summary.get('total_posts', 0)
            total_engagement = summary.get('total_engagement', 0)
            total_followers = summary.get('total_followers', 0)

            # Get platform breakdown
            platforms = data.get('platforms', {})
            top_platform = None
            top_engagement = 0
            platforms_scraped = 0

            top_posts = 0
            for platform, pdata in platforms.items():
                posts = pdata.get('posts', 0)
                engagement = pdata.get('engagement', 0)
                followers = pdata.get('followers', 0)

                if posts > 0:
                    platforms_scraped += 1

                    # Update platform totals
                    if platform not in platform_totals:
                        platform_totals[platform] = {'posts': 0, 'engagement': 0, 'followers': 0, 'grantees': 0}
                    platform_totals[platform]['posts'] += posts
                    platform_totals[platform]['engagement'] += engagement
                    platform_totals[platform]['followers'] += followers
                    platform_totals[platform]['grantees'] += 1

                    # Track top platform for this grantee (by engagement)
                    if engagement > top_engagement:
                        top_engagement = engagement
                        top_platform = platform

                    # Track platform with most posts as fallback
                    if posts > top_posts:
                        top_posts = posts
                        top_platform_by_posts = platform

            # Use platform with most posts if no engagement found
            if top_platform is None and top_posts > 0:
                top_platform = top_platform_by_posts

            if total_posts > 0:
                engagement_rate = round(total_engagement / total_posts, 2) if total_posts > 0 else 0
                grantee_entry = {
                    'name': name,
                    'slug': slug,
                    'posts': total_posts,
                    'engagement': total_engagement,
                    'followers': total_followers,
                    'engagementRate': engagement_rate,
                    'topPlatform': top_platform or 'N/A',
                    'platformsScraped': platforms_scraped
                }
                # Include logo URL if available
                if data.get('logo'):
                    grantee_entry['logo'] = data['logo']
                grantees.append(grantee_entry)

        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load {json_file}: {e}")

    return grantees, platform_totals


def build_dashboard_data(grantees, platform_totals):
    """Build the dashboard data structure."""
    # Sort all grantees by engagement (include ALL)
    sorted_grantees = sorted(grantees, key=lambda x: x['engagement'], reverse=True)

    # Calculate totals
    total_posts = sum(g['posts'] for g in grantees)
    total_engagement = sum(g['engagement'] for g in grantees)
    total_followers = sum(g['followers'] for g in grantees)

    # Build platform stats
    platforms = {}
    engagement_by_platform = []

    for platform, data in platform_totals.items():
        avg_engagement = round(data['engagement'] / data['posts'], 2) if data['posts'] > 0 else 0
        platforms[platform] = {
            'posts': data['posts'],
            'engagement': data['engagement'],
            'followers': data['followers'],
            'grantees': data['grantees'],
            'avgEngagement': avg_engagement
        }
        engagement_by_platform.append({
            'platform': platform,
            'engagement': data['engagement'],
            'posts': data['posts'],
            'color': PLATFORM_COLORS.get(platform, '#6B7280')
        })

    engagement_by_platform.sort(key=lambda x: x['engagement'], reverse=True)

    avg_engagement_rate = round(total_engagement / total_posts, 2) if total_posts > 0 else 0

    return {
        'summary': {
            'totalGrantees': len(grantees),
            'totalPosts': total_posts,
            'totalEngagement': total_engagement,
            'totalFollowers': total_followers,
            'platformsTracked': len([p for p in platform_totals.values() if p['posts'] > 0]),
            'avgEngagementRate': avg_engagement_rate,
            'lastUpdated': datetime.now().isoformat(),
            'scrapingDuration': 'aggregated'
        },
        'platforms': platforms,
        'topGrantees': sorted_grantees,  # ALL grantees, sorted by engagement
        'engagementByPlatform': engagement_by_platform,
        'metadata': {
            'generatedAt': datetime.now().isoformat(),
            'platformColors': PLATFORM_COLORS,
            'version': '2.0.0'
        }
    }


def main():
    print(f"Loading grantee data from: {GRANTEES_DIR}")
    grantees, platform_totals = load_grantee_data()

    print(f"\nFound {len(grantees)} grantees with social media data")
    print(f"Platforms: {', '.join(sorted(platform_totals.keys()))}")

    dashboard_data = build_dashboard_data(grantees, platform_totals)

    print(f"\nDashboard Summary:")
    summary = dashboard_data['summary']
    print(f"  Total Grantees: {summary['totalGrantees']}")
    print(f"  Total Posts: {summary['totalPosts']}")
    print(f"  Total Engagement: {summary['totalEngagement']:,}")
    print(f"  Platforms Tracked: {summary['platformsTracked']}")

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, indent=2)

    print(f"\nSaved to: {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
