#!/usr/bin/env python3
"""
Integrate scraped social media data into grantee JSON files and regenerate dashboard-data.json.

This script reads scraped metadata from the output/ directory and updates:
1. Individual grantee JSON files in ../dashboard/data/grantees/
2. The aggregated dashboard-data.json file

Author: Joe Amditis
Date: 2026-01-13
"""

import json
import os
import re
import glob
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from collections import defaultdict


# Platform colors for dashboard
PLATFORM_COLORS = {
    "twitter": "#1DA1F2",
    "youtube": "#FF0000",
    "instagram": "#E1306C",
    "facebook": "#1877F2",
    "linkedin": "#0A66C2",
    "tiktok": "#000000",
    "bluesky": "#0085FF",
    "threads": "#000000"
}

# Base paths
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"
GRANTEES_DIR = SCRIPT_DIR.parent / "dashboard" / "data" / "grantees"
DASHBOARD_DATA_PATH = SCRIPT_DIR.parent / "dashboard" / "data" / "dashboard-data.json"


def sanitize_grantee_name(name: str) -> str:
    """Convert grantee folder name to a slug for matching."""
    # Remove underscores and replace with spaces
    name = name.replace("_", " ").strip()
    # Handle special characters
    name = re.sub(r'\s+', ' ', name)
    return name


def normalize_unicode(text: str) -> str:
    """Normalize unicode characters to their closest ASCII equivalent."""
    # Normalize to NFD form (decomposed)
    normalized = unicodedata.normalize('NFD', text)
    # Remove diacritics (combining characters)
    ascii_text = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return ascii_text


def folder_to_slug(folder_name: str) -> str:
    """Convert a folder name to a slug matching grantee JSON filenames."""
    # Replace underscores with spaces
    name = folder_name.replace("_", " ")
    # Convert to lowercase
    name = name.lower()
    # Normalize unicode characters (e.g., ó -> o)
    name = normalize_unicode(name)
    # Remove special characters but keep letters, numbers, spaces, hyphens
    name = re.sub(r'[^a-z0-9\s-]', '', name)
    # Replace spaces with hyphens
    name = re.sub(r'\s+', '-', name.strip())
    # Remove multiple consecutive hyphens
    name = re.sub(r'-+', '-', name)
    return name


def find_grantee_json(folder_name: str) -> Optional[Path]:
    """Find the matching grantee JSON file for a scraped data folder."""
    slug = folder_to_slug(folder_name)

    # Try exact match first
    json_path = GRANTEES_DIR / f"{slug}.json"
    if json_path.exists():
        return json_path

    # Try variations
    # Remove common suffixes/variations
    variations = [
        slug,
        slug.replace("inc", "").strip("-"),
        slug.replace("--", "-"),
    ]

    for var in variations:
        json_path = GRANTEES_DIR / f"{var}.json"
        if json_path.exists():
            return json_path

    # Try fuzzy matching by listing all grantee files
    grantee_files = list(GRANTEES_DIR.glob("*.json"))

    # Score-based matching for better fuzzy matching
    best_match = None
    best_score = 0

    for gf in grantee_files:
        gf_slug = gf.stem
        # Normalize the grantee file slug for comparison
        gf_slug_normalized = normalize_unicode(gf_slug)

        # Check if the folder slug is contained in or contains the file slug
        if slug in gf_slug or gf_slug in slug:
            return gf
        # Also check normalized versions
        if slug in gf_slug_normalized or gf_slug_normalized in slug:
            return gf

        # Calculate similarity score based on shared characters/substrings
        # This handles cases where special characters were stripped differently
        slug_parts = set(slug.split('-'))
        gf_parts = set(gf_slug.split('-'))
        common_parts = slug_parts & gf_parts
        score = len(common_parts) / max(len(slug_parts), len(gf_parts))

        if score > best_score and score > 0.5:  # At least 50% match
            best_score = score
            best_match = gf

    return best_match


def load_metadata_files(platform_dir: Path) -> List[Dict[str, Any]]:
    """Load all metadata files from a platform directory, preferring manual scraped data."""
    metadata_list = []

    # Check for metadata directly in platform dir (some scrapers put it here)
    direct_metadata = platform_dir / "metadata.json"
    if direct_metadata.exists():
        try:
            with open(direct_metadata, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['_source_file'] = str(direct_metadata)
                metadata_list.append(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"  Warning: Could not load {direct_metadata}: {e}")

    # Check for metadata_manual.json (preferred)
    manual_metadata = platform_dir / "metadata_manual.json"
    if manual_metadata.exists():
        try:
            with open(manual_metadata, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['_source_file'] = str(manual_metadata)
                data['_is_manual'] = True
                metadata_list.append(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"  Warning: Could not load {manual_metadata}: {e}")

    # Check subdirectories (handle structure)
    for subdir in platform_dir.iterdir():
        if subdir.is_dir() and not subdir.name.startswith('.'):
            # Try metadata.json in subdirectory
            sub_metadata = subdir / "metadata.json"
            if sub_metadata.exists():
                try:
                    with open(sub_metadata, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        data['_source_file'] = str(sub_metadata)
                        metadata_list.append(data)
                except (json.JSONDecodeError, IOError) as e:
                    print(f"  Warning: Could not load {sub_metadata}: {e}")

            # Try metadata_manual.json in subdirectory (preferred)
            sub_manual = subdir / "metadata_manual.json"
            if sub_manual.exists():
                try:
                    with open(sub_manual, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        data['_source_file'] = str(sub_manual)
                        data['_is_manual'] = True
                        metadata_list.append(data)
                except (json.JSONDecodeError, IOError) as e:
                    print(f"  Warning: Could not load {sub_manual}: {e}")

    return metadata_list


def extract_platform_metrics(metadata_list: List[Dict[str, Any]], platform: str) -> Dict[str, Any]:
    """Extract aggregated metrics from metadata files for a platform."""
    if not metadata_list:
        return {}

    # Prefer manual metadata if available
    manual_data = [m for m in metadata_list if m.get('_is_manual')]
    data_to_use = manual_data if manual_data else metadata_list

    # Use the most recent data
    best_data = data_to_use[-1]  # Assume last is most recent

    metrics = best_data.get('engagement_metrics', {})

    result = {
        'followers': 0,
        'posts': 0,
        'engagement': 0,
        'views': 0,
        'engagement_rate': 0.0,
    }

    # Extract followers
    followers_keys = ['followers_count', 'followersCount', 'subscriber_count']
    for key in followers_keys:
        if key in metrics and metrics[key]:
            result['followers'] = int(metrics[key])
            break

    # Also check top-level for followers
    if result['followers'] == 0:
        if 'profile' in best_data:
            profile = best_data['profile']
            if 'followersCount' in profile:
                result['followers'] = int(profile['followersCount'])

    # Extract posts count
    posts_keys = ['posts_analyzed', 'posts_count', 'posts_found', 'posts_downloaded']
    for key in posts_keys:
        if key in metrics and metrics[key]:
            result['posts'] = int(metrics[key])
            break
    if result['posts'] == 0 and 'posts_count' in best_data:
        result['posts'] = int(best_data['posts_count'])
    if result['posts'] == 0 and 'posts_downloaded' in best_data:
        result['posts'] = int(best_data['posts_downloaded'])
    if result['posts'] == 0 and 'videos_downloaded' in best_data:
        result['posts'] = int(best_data['videos_downloaded'])

    # Extract engagement based on platform
    total_engagement = 0

    if platform == 'instagram':
        total_engagement = metrics.get('total_likes', 0) + metrics.get('total_comments', 0)
    elif platform == 'facebook':
        total_engagement = (metrics.get('total_reactions', 0) +
                          metrics.get('total_comments', 0) +
                          metrics.get('total_shares', 0))
    elif platform == 'twitter':
        total_engagement = (metrics.get('total_likes', 0) +
                          metrics.get('total_retweets', 0) +
                          metrics.get('total_replies', 0))
    elif platform == 'tiktok':
        total_engagement = (metrics.get('total_likes', 0) +
                          metrics.get('total_video_likes', 0) +
                          metrics.get('total_comments', 0) +
                          metrics.get('total_shares', 0))
        result['views'] = metrics.get('total_views', 0)
    elif platform == 'youtube':
        total_engagement = metrics.get('total_likes', 0)
        result['views'] = metrics.get('total_views', 0)
    elif platform == 'bluesky':
        total_engagement = (metrics.get('total_likes', 0) +
                          metrics.get('total_reposts', 0) +
                          metrics.get('total_replies', 0))
    elif platform == 'linkedin':
        total_engagement = metrics.get('posts_found', 0)  # LinkedIn is restricted

    result['engagement'] = int(total_engagement)

    # Extract engagement rate
    rate_keys = ['avg_engagement_rate', 'engagement_rate']
    for key in rate_keys:
        if key in metrics and metrics[key]:
            result['engagement_rate'] = float(metrics[key])
            break

    # Add scraped_at timestamp
    if 'scraped_at' in best_data:
        result['scraped_at'] = best_data['scraped_at']

    return result


def update_grantee_json(grantee_path: Path, platform_data: Dict[str, Dict[str, Any]]) -> bool:
    """Update a grantee JSON file with new platform metrics."""
    try:
        with open(grantee_path, 'r', encoding='utf-8') as f:
            grantee = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"  Error reading {grantee_path}: {e}")
        return False

    # Initialize platforms dict if not present
    if 'platforms' not in grantee:
        grantee['platforms'] = {}

    # Update each platform
    total_followers = 0
    total_posts = 0
    total_engagement = 0
    platforms_active = 0

    for platform, metrics in platform_data.items():
        if not metrics:
            continue

        # Update platform data
        if platform not in grantee['platforms']:
            grantee['platforms'][platform] = {}

        plat_data = grantee['platforms'][platform]

        # Update metrics
        if metrics.get('followers', 0) > 0:
            plat_data['followers'] = metrics['followers']
        if metrics.get('posts', 0) > 0:
            plat_data['posts'] = metrics['posts']
        if metrics.get('engagement', 0) > 0:
            plat_data['engagement'] = metrics['engagement']
        if metrics.get('views', 0) > 0:
            plat_data['views'] = metrics['views']
        if metrics.get('engagement_rate', 0) > 0:
            plat_data['engagement_rate'] = metrics['engagement_rate']
        if metrics.get('scraped_at'):
            plat_data['last_scraped'] = metrics['scraped_at']

        # Accumulate totals
        total_followers += plat_data.get('followers', 0)
        total_posts += plat_data.get('posts', 0)
        total_engagement += plat_data.get('engagement', 0)

        if plat_data.get('posts', 0) > 0 or plat_data.get('followers', 0) > 0:
            platforms_active += 1

    # Update summary
    if 'summary' not in grantee:
        grantee['summary'] = {}

    grantee['summary']['total_followers'] = total_followers
    grantee['summary']['total_posts'] = total_posts
    grantee['summary']['total_engagement'] = total_engagement
    grantee['summary']['platforms_active'] = platforms_active

    # Calculate engagement rate
    if total_followers > 0 and total_posts > 0:
        grantee['summary']['engagement_rate'] = round(
            (total_engagement / total_posts) if total_posts > 0 else 0, 2
        )

    grantee['summary']['last_updated'] = datetime.now().isoformat()

    # Update platform breakdown
    if 'platform_breakdown' not in grantee:
        grantee['platform_breakdown'] = {}

    for platform, metrics in platform_data.items():
        if not metrics or metrics.get('posts', 0) == 0:
            continue

        posts = metrics.get('posts', 0)
        engagement = metrics.get('engagement', 0)

        grantee['platform_breakdown'][platform] = {
            'posts': posts,
            'posts_pct': round((posts / total_posts * 100) if total_posts > 0 else 0, 1),
            'engagement': engagement,
            'engagement_pct': round((engagement / total_engagement * 100) if total_engagement > 0 else 0, 1)
        }

    # Write updated grantee JSON
    try:
        with open(grantee_path, 'w', encoding='utf-8') as f:
            json.dump(grantee, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"  Error writing {grantee_path}: {e}")
        return False


def regenerate_dashboard_data() -> bool:
    """Regenerate dashboard-data.json from all grantee JSON files."""
    print("\nRegenerating dashboard-data.json...")

    # Initialize aggregated data
    summary = {
        'totalGrantees': 0,
        'totalPosts': 0,
        'totalEngagement': 0,
        'totalFollowers': 0,
        'platformsTracked': 0,
        'avgEngagementRate': 0.0,
        'lastUpdated': datetime.now().isoformat(),
        'scrapingDuration': 'aggregated'
    }

    platforms = defaultdict(lambda: {
        'posts': 0,
        'engagement': 0,
        'followers': 0,
        'grantees': 0,
        'avgEngagement': 0.0
    })

    top_grantees = []
    all_platforms_seen = set()

    # Process each grantee JSON
    grantee_files = list(GRANTEES_DIR.glob("*.json"))

    for gf in grantee_files:
        try:
            with open(gf, 'r', encoding='utf-8') as f:
                grantee = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"  Warning: Could not read {gf}: {e}")
            continue

        summary['totalGrantees'] += 1

        # Get grantee summary
        grantee_summary = grantee.get('summary', {})
        grantee_posts = grantee_summary.get('total_posts', 0)
        grantee_engagement = grantee_summary.get('total_engagement', 0)
        grantee_followers = grantee_summary.get('total_followers', 0)

        summary['totalPosts'] += grantee_posts
        summary['totalEngagement'] += grantee_engagement
        summary['totalFollowers'] += grantee_followers

        # Track platforms
        grantee_platforms = grantee.get('platforms', {})
        platforms_scraped = 0
        top_platform = None
        top_platform_engagement = 0

        for platform, plat_data in grantee_platforms.items():
            all_platforms_seen.add(platform)

            plat_posts = plat_data.get('posts', 0)
            plat_engagement = plat_data.get('engagement', 0)
            plat_followers = plat_data.get('followers', 0)

            if plat_posts > 0 or plat_followers > 0:
                platforms_scraped += 1
                platforms[platform]['posts'] += plat_posts
                platforms[platform]['engagement'] += plat_engagement
                platforms[platform]['followers'] += plat_followers
                platforms[platform]['grantees'] += 1

                if plat_engagement > top_platform_engagement:
                    top_platform_engagement = plat_engagement
                    top_platform = platform

        # Add to top grantees list
        if grantee_posts > 0 or grantee_followers > 0:
            engagement_rate = round(
                (grantee_engagement / grantee_posts) if grantee_posts > 0 else 0, 2
            )

            grantee_entry = {
                'name': grantee.get('name', gf.stem),
                'slug': grantee.get('slug', gf.stem),
                'posts': grantee_posts,
                'engagement': grantee_engagement,
                'followers': grantee_followers,
                'engagementRate': engagement_rate,
                'topPlatform': top_platform or 'facebook',
                'platformsScraped': platforms_scraped
            }

            # Add logo if available
            if grantee.get('logo'):
                grantee_entry['logo'] = grantee['logo']

            top_grantees.append(grantee_entry)

    # Calculate platform averages
    for platform, plat_data in platforms.items():
        if plat_data['posts'] > 0:
            plat_data['avgEngagement'] = round(
                plat_data['engagement'] / plat_data['posts'], 2
            )

    # Sort top grantees by engagement (descending)
    top_grantees.sort(key=lambda x: x['engagement'], reverse=True)

    # Calculate overall average engagement rate
    if summary['totalPosts'] > 0:
        summary['avgEngagementRate'] = round(
            summary['totalEngagement'] / summary['totalPosts'], 2
        )

    summary['platformsTracked'] = len(all_platforms_seen)

    # Build engagement by platform list (sorted by engagement)
    engagement_by_platform = []
    for platform in sorted(platforms.keys(), key=lambda p: platforms[p]['engagement'], reverse=True):
        engagement_by_platform.append({
            'platform': platform,
            'engagement': platforms[platform]['engagement'],
            'posts': platforms[platform]['posts'],
            'color': PLATFORM_COLORS.get(platform, '#888888')
        })

    # Build final dashboard data
    dashboard_data = {
        'summary': summary,
        'platforms': dict(platforms),
        'topGrantees': top_grantees,
        'engagementByPlatform': engagement_by_platform,
        'metadata': {
            'generatedAt': datetime.now().isoformat(),
            'platformColors': PLATFORM_COLORS,
            'version': '2.0.0'
        }
    }

    # Write dashboard data
    try:
        with open(DASHBOARD_DATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(dashboard_data, f, indent=2, ensure_ascii=False)
        print(f"  Dashboard data written to {DASHBOARD_DATA_PATH}")
        print(f"  Total grantees: {summary['totalGrantees']}")
        print(f"  Total posts: {summary['totalPosts']}")
        print(f"  Total engagement: {summary['totalEngagement']}")
        print(f"  Total followers: {summary['totalFollowers']}")
        return True
    except IOError as e:
        print(f"  Error writing dashboard data: {e}")
        return False


def main():
    """Main function to integrate scraped data."""
    print("=" * 60)
    print("NJCIC Scraped Data Integration")
    print("=" * 60)
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print(f"Grantees directory: {GRANTEES_DIR}")
    print(f"Dashboard data: {DASHBOARD_DATA_PATH}")

    # Verify directories exist
    if not OUTPUT_DIR.exists():
        print(f"\nError: Output directory does not exist: {OUTPUT_DIR}")
        return 1

    if not GRANTEES_DIR.exists():
        print(f"\nError: Grantees directory does not exist: {GRANTEES_DIR}")
        return 1

    # Get all grantee folders in output
    grantee_folders = [
        d for d in OUTPUT_DIR.iterdir()
        if d.is_dir() and not d.name.startswith('.') and not d.name.startswith('tmp')
    ]

    print(f"\nFound {len(grantee_folders)} grantee folders to process")

    # Statistics
    stats = {
        'processed': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0,
        'platforms_found': defaultdict(int)
    }

    # Process each grantee folder
    for grantee_folder in sorted(grantee_folders):
        print(f"\n--- Processing: {grantee_folder.name} ---")

        # Find matching grantee JSON
        grantee_json = find_grantee_json(grantee_folder.name)

        if not grantee_json:
            print(f"  Warning: No matching grantee JSON found for {grantee_folder.name}")
            stats['skipped'] += 1
            continue

        print(f"  Matched to: {grantee_json.name}")

        # Find platform directories
        platform_dirs = [
            d for d in grantee_folder.iterdir()
            if d.is_dir() and not d.name.startswith('.') and not d.name.startswith('tmp')
        ]

        if not platform_dirs:
            print(f"  No platform directories found")
            stats['skipped'] += 1
            continue

        # Collect platform data
        platform_data = {}

        for platform_dir in platform_dirs:
            platform = platform_dir.name.lower()
            print(f"  Reading {platform} data...")

            # Load metadata files
            metadata_list = load_metadata_files(platform_dir)

            if not metadata_list:
                print(f"    No metadata found for {platform}")
                continue

            # Extract metrics
            metrics = extract_platform_metrics(metadata_list, platform)

            if metrics:
                platform_data[platform] = metrics
                stats['platforms_found'][platform] += 1
                print(f"    Followers: {metrics.get('followers', 0)}, Posts: {metrics.get('posts', 0)}, Engagement: {metrics.get('engagement', 0)}")

        # Update grantee JSON
        if platform_data:
            if update_grantee_json(grantee_json, platform_data):
                print(f"  Updated {grantee_json.name}")
                stats['updated'] += 1
            else:
                print(f"  Failed to update {grantee_json.name}")
                stats['errors'] += 1
        else:
            print(f"  No platform data to update")
            stats['skipped'] += 1

        stats['processed'] += 1

    # Regenerate dashboard data
    if not regenerate_dashboard_data():
        stats['errors'] += 1

    # Print summary
    print("\n" + "=" * 60)
    print("INTEGRATION COMPLETE")
    print("=" * 60)
    print(f"\nProcessed: {stats['processed']} grantees")
    print(f"Updated: {stats['updated']} grantee files")
    print(f"Skipped: {stats['skipped']} (no match or no data)")
    print(f"Errors: {stats['errors']}")
    print("\nPlatforms found:")
    for platform, count in sorted(stats['platforms_found'].items()):
        print(f"  {platform}: {count} grantees")

    return 0 if stats['errors'] == 0 else 1


if __name__ == "__main__":
    exit(main())
