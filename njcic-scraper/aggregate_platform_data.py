#!/usr/bin/env python3
"""
Aggregate platform-level post data to root level for all grantee JSON files.

This script reads existing grantee JSON files and aggregates:
1. top_posts from all platforms into root-level top_posts
2. time_series from all platforms into root-level time_series
3. Calculates overall_frequency from combined data

This fixes the issue where individual grantee pages show "No detailed post data available"
because the root-level arrays are empty despite platform-level data existing.

Author: Claude
Date: 2026-01-13
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict


# Base paths
SCRIPT_DIR = Path(__file__).parent
GRANTEES_DIR = SCRIPT_DIR.parent / "dashboard" / "data" / "grantees"


def detect_platform_from_url(url: str) -> str:
    """Detect the platform from a post URL."""
    if not url:
        return "unknown"
    url_lower = url.lower()
    if "tiktok.com" in url_lower:
        return "tiktok"
    elif "instagram.com" in url_lower:
        return "instagram"
    elif "facebook.com" in url_lower:
        return "facebook"
    elif "twitter.com" in url_lower or "x.com" in url_lower:
        return "twitter"
    elif "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    elif "linkedin.com" in url_lower:
        return "linkedin"
    elif "bsky.app" in url_lower:
        return "bluesky"
    elif "threads.net" in url_lower:
        return "threads"
    return "unknown"


def get_post_engagement(post: Dict[str, Any]) -> int:
    """Extract total engagement from a post."""
    engagement = post.get("engagement", {})
    if isinstance(engagement, dict):
        return engagement.get("total", 0)
    elif isinstance(engagement, (int, float)):
        return int(engagement)
    return 0


def aggregate_top_posts(platforms: Dict[str, Any], max_posts: int = 9) -> List[Dict[str, Any]]:
    """Aggregate top posts from all platforms, sorted by engagement."""
    all_posts = []

    for platform_name, platform_data in platforms.items():
        if not isinstance(platform_data, dict):
            continue

        top_posts = platform_data.get("top_posts", [])
        if not isinstance(top_posts, list):
            continue

        for post in top_posts:
            if not isinstance(post, dict):
                continue
            # Ensure platform is tagged on the post
            post_copy = post.copy()
            if "platform" not in post_copy:
                # Try to detect from URL or use the platform name
                url = post_copy.get("url", "")
                detected = detect_platform_from_url(url)
                post_copy["platform"] = detected if detected != "unknown" else platform_name
            all_posts.append(post_copy)

    # Sort by engagement (descending) and take top posts
    all_posts.sort(key=lambda p: get_post_engagement(p), reverse=True)
    return all_posts[:max_posts]


def aggregate_time_series(platforms: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Aggregate time series data from all platforms."""
    # Group by date and sum posts/engagement
    date_data = defaultdict(lambda: {"posts": 0, "engagement": 0})

    for platform_name, platform_data in platforms.items():
        if not isinstance(platform_data, dict):
            continue

        time_series = platform_data.get("time_series", [])
        if not isinstance(time_series, list):
            continue

        for entry in time_series:
            if not isinstance(entry, dict):
                continue
            date = entry.get("date")
            if not date:
                continue
            date_data[date]["posts"] += entry.get("posts", 0)
            date_data[date]["engagement"] += entry.get("engagement", 0)

    # Convert to list and sort by date
    result = [
        {"date": date, "posts": data["posts"], "engagement": data["engagement"]}
        for date, data in date_data.items()
        if data["posts"] > 0  # Only include dates with actual posts
    ]
    result.sort(key=lambda x: x["date"])
    return result


def calculate_overall_frequency(platforms: Dict[str, Any], time_series: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate overall posting frequency from all platforms."""
    all_dates = []
    total_posts = 0

    # Collect all post dates from platform frequency data
    for platform_name, platform_data in platforms.items():
        if not isinstance(platform_data, dict):
            continue

        frequency = platform_data.get("frequency", {})
        if isinstance(frequency, dict):
            first_post = frequency.get("first_post")
            last_post = frequency.get("last_post")
            if first_post:
                all_dates.append(first_post)
            if last_post:
                all_dates.append(last_post)

        # Also get posts count
        total_posts += platform_data.get("posts", 0)

    # Also check time_series for date range
    for entry in time_series:
        date = entry.get("date")
        if date:
            all_dates.append(date)

    if not all_dates:
        return {
            "posts_per_day": 0,
            "posts_per_week": 0,
            "date_range_days": 0,
            "first_post": None,
            "last_post": None
        }

    # Parse and sort dates
    parsed_dates = []
    for d in all_dates:
        try:
            if isinstance(d, str):
                # Handle various date formats
                if "T" in d:
                    parsed = datetime.fromisoformat(d.replace("Z", "+00:00"))
                else:
                    parsed = datetime.strptime(d, "%Y-%m-%d")
                parsed_dates.append(parsed)
        except (ValueError, TypeError):
            continue

    if not parsed_dates:
        return {
            "posts_per_day": 0,
            "posts_per_week": 0,
            "date_range_days": 0,
            "first_post": None,
            "last_post": None
        }

    parsed_dates.sort()
    first_post = parsed_dates[0]
    last_post = parsed_dates[-1]
    date_range_days = (last_post - first_post).days or 1

    posts_per_day = round(total_posts / date_range_days, 2) if date_range_days > 0 else 0
    posts_per_week = round(posts_per_day * 7, 2)

    return {
        "posts_per_day": posts_per_day,
        "posts_per_week": posts_per_week,
        "date_range_days": date_range_days,
        "first_post": first_post.isoformat(),
        "last_post": last_post.isoformat()
    }


def process_grantee_file(grantee_path: Path) -> bool:
    """Process a single grantee JSON file to aggregate platform data."""
    try:
        with open(grantee_path, 'r', encoding='utf-8') as f:
            grantee = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"  Error reading {grantee_path}: {e}")
        return False

    platforms = grantee.get("platforms", {})
    if not platforms:
        print(f"  No platforms data found")
        return False

    # Check if there's any platform-level post data to aggregate
    has_platform_posts = False
    has_platform_time_series = False

    for platform_data in platforms.values():
        if isinstance(platform_data, dict):
            if platform_data.get("top_posts"):
                has_platform_posts = True
            if platform_data.get("time_series"):
                has_platform_time_series = True

    # Aggregate top_posts
    top_posts = aggregate_top_posts(platforms)

    # Aggregate time_series
    time_series = aggregate_time_series(platforms)

    # Calculate overall frequency
    overall_frequency = calculate_overall_frequency(platforms, time_series)

    # Check if we actually aggregated anything new
    existing_top_posts = grantee.get("top_posts", [])
    existing_time_series = grantee.get("time_series", [])

    changes_made = False

    # Update root-level data
    if top_posts and (not existing_top_posts or len(top_posts) > len(existing_top_posts)):
        grantee["top_posts"] = top_posts
        changes_made = True
        print(f"  Aggregated {len(top_posts)} top posts")

    if time_series and (not existing_time_series or len(time_series) > len(existing_time_series)):
        grantee["time_series"] = time_series
        changes_made = True
        print(f"  Aggregated {len(time_series)} time series entries")

    if overall_frequency.get("date_range_days", 0) > 0:
        existing_freq = grantee.get("overall_frequency", {})
        if not existing_freq.get("date_range_days"):
            grantee["overall_frequency"] = overall_frequency
            changes_made = True
            print(f"  Updated overall frequency")

    if not changes_made:
        if not has_platform_posts and not has_platform_time_series:
            print(f"  No platform-level post data to aggregate")
        else:
            print(f"  No new data to aggregate (root data already present)")
        return False

    # Write updated grantee JSON
    try:
        with open(grantee_path, 'w', encoding='utf-8') as f:
            json.dump(grantee, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"  Error writing {grantee_path}: {e}")
        return False


def main():
    """Main function to aggregate platform data for all grantees."""
    print("=" * 60)
    print("NJCIC Platform Data Aggregation")
    print("=" * 60)
    print(f"\nGrantees directory: {GRANTEES_DIR}")

    if not GRANTEES_DIR.exists():
        print(f"\nError: Grantees directory does not exist: {GRANTEES_DIR}")
        return 1

    # Get all grantee JSON files
    grantee_files = list(GRANTEES_DIR.glob("*.json"))
    print(f"\nFound {len(grantee_files)} grantee files to process")

    # Statistics
    stats = {
        "processed": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0
    }

    # Process each grantee file
    for grantee_path in sorted(grantee_files):
        print(f"\n--- Processing: {grantee_path.stem} ---")
        stats["processed"] += 1

        try:
            if process_grantee_file(grantee_path):
                stats["updated"] += 1
            else:
                stats["skipped"] += 1
        except Exception as e:
            print(f"  Error processing {grantee_path}: {e}")
            stats["errors"] += 1

    # Print summary
    print("\n" + "=" * 60)
    print("AGGREGATION COMPLETE")
    print("=" * 60)
    print(f"\nProcessed: {stats['processed']} grantee files")
    print(f"Updated: {stats['updated']} files with aggregated data")
    print(f"Skipped: {stats['skipped']} (no new data to aggregate)")
    print(f"Errors: {stats['errors']}")

    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    exit(main())
