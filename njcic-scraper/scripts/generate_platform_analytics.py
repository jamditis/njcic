#!/usr/bin/env python3
"""
Generate platform-analytics.json from scraped metadata files.

This script creates detailed per-platform analytics for the dashboard
platforms page, including top grantees and content type breakdowns.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

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
    except Exception:
        return {}

def slugify(name: str) -> str:
    """Convert a name to a URL-friendly slug."""
    import re
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')

def get_post_count(metadata: Dict) -> int:
    """Extract post count from metadata with various field names."""
    posts = metadata.get("posts_downloaded", 0) or 0
    if posts == 0:
        posts = metadata.get("total_videos_scraped", 0) or 0
    if posts == 0:
        posts = metadata.get("posts_count", 0) or 0
    if posts == 0 and isinstance(metadata.get("posts"), list):
        posts = len(metadata.get("posts", []))
    if posts == 0 and isinstance(metadata.get("videos"), list):
        posts = len(metadata.get("videos", []))
    return posts

def analyze_content_types(metadata: Dict, platform: str) -> Dict[str, Dict]:
    """Analyze content types from posts."""
    content_types = {}
    posts = metadata.get("posts", []) or metadata.get("videos", []) or []

    if not posts:
        # Default content type based on platform
        if platform in ["tiktok", "youtube"]:
            return {"video": {"count": get_post_count(metadata), "engagement": 0, "percentage": 100.0}}
        return {}

    for post in posts:
        post_type = "other"
        if platform == "instagram":
            typename = post.get("typename", "")
            if "Video" in typename or post.get("is_video"):
                post_type = "video"
            elif "Sidecar" in typename:
                post_type = "carousel"
            else:
                post_type = "image"
        elif platform == "bluesky":
            if post.get("has_video"):
                post_type = "video"
            elif post.get("has_images"):
                post_type = "image"
            elif post.get("is_quote"):
                post_type = "quote"
            elif post.get("has_link") or post.get("embed_type") == "link":
                post_type = "link"
            else:
                post_type = "text"
        elif platform in ["tiktok", "youtube"]:
            post_type = "video"
        elif platform == "twitter":
            post_type = "tweet"
        elif platform == "facebook":
            post_type = "post"

        if post_type not in content_types:
            content_types[post_type] = {"count": 0, "engagement": 0}
        content_types[post_type]["count"] += 1

        # Sum engagement
        engagement = (post.get("likes", 0) or 0) + (post.get("comments", 0) or 0)
        engagement += post.get("views", 0) or 0
        engagement += post.get("shares", 0) or post.get("retweets", 0) or post.get("reposts", 0) or 0
        content_types[post_type]["engagement"] += engagement

    # Calculate percentages
    total = sum(ct["count"] for ct in content_types.values())
    for ct in content_types.values():
        ct["percentage"] = round((ct["count"] / total * 100) if total > 0 else 0, 1)

    return content_types

def aggregate_platform_data(output_dir: Path) -> Dict[str, Dict]:
    """Aggregate data for each platform."""
    platforms = {}

    for platform in PLATFORM_COLORS.keys():
        platforms[platform] = {
            "color": PLATFORM_COLORS[platform],
            "grantees": 0,
            "total_posts": 0,
            "total_engagement": 0,
            "total_followers": 0,
            "grantee_data": [],  # Temporary for top grantees calculation
            "content_types": {},
        }

    # Walk through grantee directories
    for grantee_dir in output_dir.iterdir():
        if not grantee_dir.is_dir() or grantee_dir.name.startswith('.'):
            continue
        if grantee_dir.name == 'linkedin':
            continue

        grantee_name = grantee_dir.name.replace('_', ' ').strip()

        for platform in PLATFORM_COLORS.keys():
            platform_dir = grantee_dir / platform
            if not platform_dir.is_dir():
                continue

            # Find metadata.json
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

            posts = get_post_count(metadata)
            metrics = metadata.get("engagement_metrics", {})

            # Calculate engagement
            engagement = 0
            followers = 0

            if platform == "twitter":
                engagement = (metrics.get("total_likes", 0) or 0) + (metrics.get("total_retweets", 0) or 0)
                followers = metrics.get("followers_count", 0) or 0
            elif platform == "youtube":
                engagement = (metrics.get("total_views", 0) or 0) + (metrics.get("total_likes", 0) or 0)
                followers = metrics.get("subscribers_count", 0) or metrics.get("subscriber_count", 0) or 0
            elif platform == "facebook":
                engagement = (metrics.get("total_likes", 0) or 0) + (metrics.get("total_comments", 0) or 0)
                followers = metrics.get("followers_count", 0) or metrics.get("page_likes", 0) or 0
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
            elif platform == "linkedin":
                engagement = (metrics.get("total_likes", 0) or 0) + (metrics.get("total_comments", 0) or 0)
                followers = metrics.get("followers_count", 0) or 0

            if posts > 0 or followers > 0:
                platforms[platform]["grantees"] += 1
                platforms[platform]["total_posts"] += posts
                platforms[platform]["total_engagement"] += engagement
                platforms[platform]["total_followers"] += followers
                platforms[platform]["grantee_data"].append({
                    "name": grantee_name,
                    "slug": slugify(grantee_name),
                    "posts": posts,
                    "engagement": engagement,
                })

                # Aggregate content types
                ct = analyze_content_types(metadata, platform)
                for ctype, data in ct.items():
                    if ctype not in platforms[platform]["content_types"]:
                        platforms[platform]["content_types"][ctype] = {"count": 0, "engagement": 0}
                    platforms[platform]["content_types"][ctype]["count"] += data["count"]
                    platforms[platform]["content_types"][ctype]["engagement"] += data["engagement"]

    return platforms

def generate_platform_analytics(output_dir: Path) -> Dict[str, Any]:
    """Generate the complete platform analytics JSON."""
    platforms_raw = aggregate_platform_data(output_dir)

    platforms = {}
    comparison_engagement = []
    comparison_posts = []

    for platform, data in platforms_raw.items():
        if data["grantees"] == 0:
            continue

        # Calculate averages
        avg_engagement = round(data["total_engagement"] / data["total_posts"], 2) if data["total_posts"] > 0 else 0
        avg_posts = round(data["total_posts"] / data["grantees"], 1) if data["grantees"] > 0 else 0

        # Get top 10 grantees by engagement
        top_grantees = sorted(data["grantee_data"], key=lambda x: x["engagement"], reverse=True)[:10]

        # Calculate content type percentages
        content_types = {}
        total_content = sum(ct["count"] for ct in data["content_types"].values())
        for ctype, ct_data in data["content_types"].items():
            content_types[ctype] = {
                "count": ct_data["count"],
                "engagement": ct_data["engagement"],
                "percentage": round((ct_data["count"] / total_content * 100) if total_content > 0 else 0, 1)
            }

        platforms[platform] = {
            "color": data["color"],
            "grantees": data["grantees"],
            "total_posts": data["total_posts"],
            "total_engagement": data["total_engagement"],
            "total_followers": data["total_followers"],
            "avg_engagement_per_post": avg_engagement,
            "avg_posts_per_grantee": avg_posts,
            "content_types": content_types if content_types else {"post": {"count": data["total_posts"], "engagement": data["total_engagement"], "percentage": 100.0}},
            "top_grantees": top_grantees,
        }

        comparison_engagement.append({"platform": platform, "engagement": data["total_engagement"]})
        comparison_posts.append({"platform": platform, "posts": data["total_posts"]})

    # Sort comparisons
    comparison_engagement.sort(key=lambda x: x["engagement"], reverse=True)
    comparison_posts.sort(key=lambda x: x["posts"], reverse=True)

    return {
        "platforms": platforms,
        "comparison": {
            "by_engagement": comparison_engagement,
            "by_posts": comparison_posts,
        },
        "generated_at": datetime.now().isoformat(),
    }

def main():
    script_dir = Path(__file__).resolve().parent
    base_dir = script_dir.parent
    output_dir = base_dir / "output"
    project_dir = base_dir.parent

    print(f"Generating platform analytics from: {output_dir}")

    analytics = generate_platform_analytics(output_dir)

    print(f"\nPlatforms with data:")
    for platform, data in analytics["platforms"].items():
        print(f"  {platform}: {data['grantees']} grantees, {data['total_posts']} posts, {data['total_engagement']:,} engagement")

    # Save to output locations
    output_paths = [
        base_dir / "output" / "platform-analytics.json",
        project_dir / "dashboard" / "data" / "platform-analytics.json",
    ]

    for path in output_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(analytics, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to: {path}")

if __name__ == "__main__":
    main()
