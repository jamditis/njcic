#!/usr/bin/env python3
"""
Aggregate all platform metadata into a combined dashboard data file.

This script walks through all grantee output folders and aggregates
data from all platforms (twitter, youtube, facebook, linkedin, threads,
instagram, tiktok, bluesky) into a single dashboard-data.json file.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Platform colors for chart visualization
PLATFORM_COLORS = {
    "twitter": "#1DA1F2",
    "youtube": "#FF0000",
    "instagram": "#E1306C",
    "facebook": "#1877F2",
    "linkedin": "#0A66C2",
    "tiktok": "#000000",
    "bluesky": "#0085FF",
    "threads": "#000000",
}

def load_metadata(metadata_path: Path) -> Dict[str, Any]:
    """Load a metadata.json file."""
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  Warning: Could not load {metadata_path}: {e}")
        return {}

def slugify(name: str) -> str:
    """Convert a name to a URL-friendly slug."""
    import re
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')

def normalize_grantee_name(folder_name: str) -> str:
    """Convert folder name to displayable grantee name."""
    name = folder_name.replace('_', ' ')
    # Handle special cases
    name = name.replace('  ', ' @ ')  # For names with @ symbols
    name = name.replace(' s ', "'s ")  # For possessives
    return name.strip()

def aggregate_platform_data(output_dir: Path) -> Tuple[Dict[str, Any], Dict[str, Dict[str, int]]]:
    """
    Walk through all grantee folders and aggregate platform data.
    """
    grantees = {}
    platform_stats = {
        "twitter": {"posts": 0, "engagement": 0, "followers": 0, "grantees": 0},
        "youtube": {"posts": 0, "engagement": 0, "followers": 0, "grantees": 0},
        "facebook": {"posts": 0, "engagement": 0, "followers": 0, "grantees": 0},
        "linkedin": {"posts": 0, "engagement": 0, "followers": 0, "grantees": 0},
        "threads": {"posts": 0, "engagement": 0, "followers": 0, "grantees": 0},
        "instagram": {"posts": 0, "engagement": 0, "followers": 0, "grantees": 0},
        "tiktok": {"posts": 0, "engagement": 0, "followers": 0, "grantees": 0},
        "bluesky": {"posts": 0, "engagement": 0, "followers": 0, "grantees": 0},
    }

    # Walk through grantee directories
    for grantee_dir in output_dir.iterdir():
        if not grantee_dir.is_dir() or grantee_dir.name.startswith('.'):
            continue

        # Skip special directories that aren't grantee folders
        if grantee_dir.name in ['linkedin']:
            continue

        grantee_name = normalize_grantee_name(grantee_dir.name)
        grantee_slug = slugify(grantee_name)

        grantee_data = {
            "name": grantee_name,
            "slug": grantee_slug,
            "posts": 0,
            "engagement": 0,
            "followers": 0,
            "platforms": {},
            "platformsScraped": 0,
        }

        # Check each platform folder
        for platform in platform_stats.keys():
            platform_dir = grantee_dir / platform
            if not platform_dir.is_dir():
                continue

            # Find metadata.json (could be directly in platform dir or in a username subdir)
            metadata_path = None
            if (platform_dir / "metadata.json").exists():
                metadata_path = platform_dir / "metadata.json"
            else:
                for subdir in platform_dir.iterdir():
                    if subdir.is_dir() and (subdir / "metadata.json").exists():
                        metadata_path = subdir / "metadata.json"
                        break

            if not metadata_path:
                continue

            metadata = load_metadata(metadata_path)
            if not metadata:
                continue

            # Handle different field names for posts across platforms
            posts = metadata.get("posts_downloaded", 0) or 0
            if posts == 0:
                posts = metadata.get("total_videos_scraped", 0) or 0  # YouTube
            if posts == 0:
                posts = metadata.get("posts_scraped", 0) or 0  # Alternative field name
            if posts == 0:
                posts = metadata.get("posts_count", 0) or 0  # TikTok
            if posts == 0 and isinstance(metadata.get("posts"), list):
                posts = len(metadata.get("posts", []))  # Instagram/TikTok stores posts as array
            if posts == 0 and isinstance(metadata.get("videos"), list):
                posts = len(metadata.get("videos", []))  # Some YouTube stores videos as array

            metrics = metadata.get("engagement_metrics", {})

            # Calculate engagement based on platform
            engagement = 0
            followers = 0

            if platform == "twitter":
                engagement = (metrics.get("total_likes", 0) or 0) + (metrics.get("total_retweets", 0) or 0)
                followers = metrics.get("followers_count", 0) or 0
            elif platform == "youtube":
                engagement = (metrics.get("total_views", 0) or 0) + (metrics.get("total_likes", 0) or 0)
                followers = metrics.get("subscribers_count", 0) or metrics.get("subscriber_count", 0) or 0
            elif platform == "facebook":
                engagement = (metrics.get("total_likes", 0) or 0) + (metrics.get("total_comments", 0) or 0) + (metrics.get("total_shares", 0) or 0)
                followers = metrics.get("followers_count", 0) or metrics.get("page_likes", 0) or 0
            elif platform == "linkedin":
                engagement = (metrics.get("total_likes", 0) or 0) + (metrics.get("total_comments", 0) or 0)
                followers = metrics.get("followers_count", 0) or 0
            elif platform == "instagram":
                engagement = (metrics.get("total_likes", 0) or 0) + (metrics.get("total_comments", 0) or 0)
                followers = metrics.get("followers_count", 0) or 0
            elif platform == "tiktok":
                engagement = (metrics.get("total_likes", 0) or 0) + (metrics.get("total_views", 0) or 0)
                followers = metrics.get("followers_count", 0) or 0
            elif platform == "bluesky":
                engagement = (metrics.get("total_likes", 0) or 0) + (metrics.get("total_reposts", 0) or 0)
                followers = metrics.get("followers_count", 0) or 0
            elif platform == "threads":
                engagement = (metrics.get("total_likes", 0) or 0) + (metrics.get("total_replies", 0) or 0)
                followers = metrics.get("followers_count", 0) or 0

            # Only count if we have actual data (posts or followers)
            if posts > 0 or followers > 0:
                grantee_data["platforms"][platform] = {
                    "posts": posts,
                    "engagement": engagement,
                    "followers": followers,
                }
                grantee_data["posts"] += posts
                grantee_data["engagement"] += engagement
                grantee_data["followers"] += followers
                grantee_data["platformsScraped"] += 1

                platform_stats[platform]["posts"] += posts
                platform_stats[platform]["engagement"] += engagement
                platform_stats[platform]["followers"] += followers
                platform_stats[platform]["grantees"] += 1

        # Only include grantees with data
        if grantee_data["platformsScraped"] > 0:
            grantees[grantee_name] = grantee_data

    return grantees, platform_stats

def create_dashboard_data(grantees: Dict, platform_stats: Dict) -> Dict[str, Any]:
    """Create the dashboard data structure."""

    # Calculate totals
    total_posts = sum(g["posts"] for g in grantees.values())
    total_engagement = sum(g["engagement"] for g in grantees.values())
    total_followers = sum(g["followers"] for g in grantees.values())
    platforms_with_data = sum(1 for p in platform_stats.values() if p["posts"] > 0 or p["grantees"] > 0)

    # Calculate average engagement rate
    avg_engagement_rate = 0
    if total_posts > 0:
        avg_engagement_rate = round(total_engagement / total_posts, 2)

    # Create top grantees list sorted by engagement
    top_grantees = []
    for name, data in grantees.items():
        top_platform = None
        top_platform_engagement = 0
        top_platform_posts = 0

        # First pass: find platform with highest engagement
        for platform, pdata in data.get("platforms", {}).items():
            if pdata.get("engagement", 0) > top_platform_engagement:
                top_platform_engagement = pdata["engagement"]
                top_platform = platform

        # Fallback: if no engagement, use platform with most posts
        if top_platform is None:
            for platform, pdata in data.get("platforms", {}).items():
                if pdata.get("posts", 0) > top_platform_posts:
                    top_platform_posts = pdata["posts"]
                    top_platform = platform

        engagement_rate = 0
        if data["posts"] > 0:
            engagement_rate = round(data["engagement"] / data["posts"], 2)

        top_grantees.append({
            "name": name,
            "slug": data["slug"],
            "posts": data["posts"],
            "engagement": data["engagement"],
            "followers": data["followers"],
            "engagementRate": engagement_rate,
            "topPlatform": top_platform or "N/A",
            "platformsScraped": data["platformsScraped"],
        })

    # Sort by engagement descending
    top_grantees.sort(key=lambda x: x["engagement"], reverse=True)

    # Create platforms dict with average engagement
    platforms = {}
    for platform, stats in platform_stats.items():
        if stats["posts"] > 0 or stats["grantees"] > 0:
            avg_eng = round(stats["engagement"] / stats["posts"], 2) if stats["posts"] > 0 else 0
            platforms[platform] = {
                "posts": stats["posts"],
                "engagement": stats["engagement"],
                "followers": stats["followers"],
                "grantees": stats["grantees"],
                "avgEngagement": avg_eng,
            }

    # Create engagement by platform for charts
    engagement_by_platform = []
    for platform, stats in platform_stats.items():
        if stats["posts"] > 0 or stats["engagement"] > 0:
            engagement_by_platform.append({
                "platform": platform,
                "engagement": stats["engagement"],
                "posts": stats["posts"],
                "color": PLATFORM_COLORS.get(platform, "#808080"),
            })
    engagement_by_platform.sort(key=lambda x: x["engagement"], reverse=True)

    return {
        "summary": {
            "totalGrantees": len(grantees),
            "totalPosts": total_posts,
            "totalEngagement": total_engagement,
            "totalFollowers": total_followers,
            "platformsTracked": platforms_with_data,
            "avgEngagementRate": avg_engagement_rate,
            "lastUpdated": datetime.now().isoformat(),
            "scrapingDuration": "aggregated",
        },
        "platforms": platforms,
        "topGrantees": top_grantees[:15],  # Top 15 grantees
        "engagementByPlatform": engagement_by_platform,
        "metadata": {
            "generatedAt": datetime.now().isoformat(),
            "platformColors": PLATFORM_COLORS,
            "version": "2.0.0",
        },
    }

def main():
    # Determine paths
    script_dir = Path(__file__).resolve().parent
    base_dir = script_dir.parent  # njcic-scraper directory
    output_dir = base_dir / "output"
    project_dir = base_dir.parent  # njcic directory

    print(f"Aggregating platform data from: {output_dir}")

    # Aggregate data
    grantees, platform_stats = aggregate_platform_data(output_dir)

    print(f"\nFound {len(grantees)} grantees with data")
    print("\nPlatform stats:")
    for platform, stats in platform_stats.items():
        if stats["posts"] > 0 or stats["grantees"] > 0:
            print(f"  {platform}: {stats['grantees']} grantees, {stats['posts']} posts, {stats['engagement']:,} engagement")

    # Create dashboard data
    dashboard_data = create_dashboard_data(grantees, platform_stats)

    # Save to output locations
    output_paths = [
        base_dir / "output" / "dashboard-data.json",
        project_dir / "dashboard" / "data" / "dashboard-data.json",
    ]

    for path in output_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dashboard_data, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to: {path}")

    # Print summary
    summary = dashboard_data["summary"]
    print(f"\n=== Dashboard Summary ===")
    print(f"Total grantees: {summary['totalGrantees']}")
    print(f"Total posts: {summary['totalPosts']}")
    print(f"Total engagement: {summary['totalEngagement']:,}")
    print(f"Total followers: {summary['totalFollowers']:,}")
    print(f"Platforms tracked: {summary['platformsTracked']}")

if __name__ == "__main__":
    main()
