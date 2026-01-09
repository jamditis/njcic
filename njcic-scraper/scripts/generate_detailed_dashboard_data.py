#!/usr/bin/env python3
"""
Generate detailed dashboard data for NJCIC grantees.

This script reads all scraped data and generates comprehensive analytics including:
- Total posts, engagement, followers per platform
- Engagement rates
- Top performing posts
- Post frequency (posts per day/week)
- Platform breakdown with percentages
- Time series data
- Content type breakdown

Output files:
- dashboard-data.json - Main dashboard summary
- grantees/*.json - Individual grantee detailed data
- rankings.json - Grantee rankings by various metrics
- platform-analytics.json - Deep platform analysis
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
OUTPUT_DIR = BASE_DIR / "output"
DASHBOARD_DIR = BASE_DIR.parent / "dashboard" / "data"
GRANTEES_DIR = DASHBOARD_DIR / "grantees"

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


# =============================================================================
# Helper Functions
# =============================================================================

def slugify(name: str) -> str:
    """
    Convert a grantee name to a URL-friendly slug.

    Args:
        name: The grantee name to slugify

    Returns:
        A lowercase, hyphenated slug
    """
    # Convert to lowercase
    slug = name.lower()
    # Replace underscores and spaces with hyphens
    slug = re.sub(r'[_\s]+', '-', slug)
    # Remove special characters except hyphens
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    return slug


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to integer, handling None and invalid values."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float, handling None and invalid values."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def calculate_engagement_rate(engagement: int, posts: int) -> float:
    """
    Calculate engagement rate as engagement per post.

    Args:
        engagement: Total engagement count
        posts: Total number of posts

    Returns:
        Engagement rate (engagement / posts), or 0 if no posts
    """
    if posts <= 0:
        return 0.0
    return round(engagement / posts, 2)


def parse_post_date(post: Dict) -> Optional[datetime]:
    """
    Extract and parse the date from a post.

    Handles various date formats:
    - ISO format timestamps
    - YYYYMMDD format (TikTok)
    - Unix timestamps

    Args:
        post: The post dictionary

    Returns:
        datetime object or None if parsing fails
    """
    # Try various date fields
    date_fields = ['timestamp', 'formatted_date', 'date', 'created_at', 'published_at']

    for field in date_fields:
        value = post.get(field)
        if value is None:
            continue

        # Unix timestamp (numeric)
        if isinstance(value, (int, float)) and value > 1000000000:
            try:
                return datetime.fromtimestamp(value)
            except (ValueError, OSError):
                continue

        # ISO format string
        if isinstance(value, str):
            # Try ISO format
            try:
                # Handle various ISO formats
                if 'T' in value:
                    return datetime.fromisoformat(value.replace('Z', '+00:00').split('+')[0])
            except ValueError:
                pass

            # Try YYYYMMDD format (TikTok uses this)
            try:
                if len(value) == 8 and value.isdigit():
                    return datetime.strptime(value, '%Y%m%d')
            except ValueError:
                pass

            # Try common date formats
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y']:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue

    return None


def get_post_engagement(post: Dict) -> Dict[str, int]:
    """
    Extract engagement metrics from a post.

    Args:
        post: The post dictionary

    Returns:
        Dictionary with likes, comments, shares, views, and total
    """
    # Use max(0, ...) to handle negative values from rate-limited Instagram scrapes
    # where instaloader returns -1 when it can't fetch like counts
    likes = max(0, safe_int(post.get('likes') or post.get('like_count') or post.get('likeCount')))
    comments = max(0, safe_int(post.get('comments') or post.get('comment_count') or post.get('commentCount') or post.get('replies')))
    shares = max(0, safe_int(post.get('shares') or post.get('share_count') or post.get('shareCount') or
                      post.get('reposts') or post.get('repost_count')))
    views = max(0, safe_int(post.get('views') or post.get('view_count') or post.get('viewCount') or
                     post.get('play_count') or post.get('playCount')))

    # For Bluesky, also check total_engagement field
    if 'total_engagement' in post:
        total = max(0, safe_int(post.get('total_engagement')))
    else:
        total = likes + comments + shares

    return {
        'likes': likes,
        'comments': comments,
        'shares': shares,
        'views': views,
        'total': total
    }


def identify_top_posts(posts: List[Dict], limit: int = 5) -> List[Dict]:
    """
    Identify the top performing posts by engagement.

    Args:
        posts: List of post dictionaries
        limit: Maximum number of top posts to return

    Returns:
        List of top posts with essential info
    """
    # Filter out invalid posts
    valid_posts = []
    for post in posts:
        if not post:
            continue
        # Skip posts that appear to be profile data (TikTok metadata entries)
        if post.get('post_id', '').startswith('MS4wLjA'):
            continue
        if not post.get('date') and not post.get('timestamp') and not post.get('formatted_date'):
            # Might be invalid entry
            if safe_int(post.get('likes')) == 0 and safe_int(post.get('views')) == 0:
                continue
        valid_posts.append(post)

    # Sort by engagement
    def get_sort_key(p):
        eng = get_post_engagement(p)
        # Prioritize total engagement, then views
        return (eng['total'], eng['views'])

    sorted_posts = sorted(valid_posts, key=get_sort_key, reverse=True)

    top = []
    for post in sorted_posts[:limit]:
        engagement = get_post_engagement(post)
        date = parse_post_date(post)

        top.append({
            'id': post.get('post_id') or post.get('id'),
            'url': post.get('url'),
            'text': (post.get('text') or post.get('title') or post.get('description') or '')[:200],
            'date': date.isoformat() if date else None,
            'engagement': engagement,
            'thumbnail': post.get('thumbnail')
        })

    return top


def calculate_post_frequency(posts: List[Dict]) -> Dict:
    """
    Calculate posting frequency metrics.

    Args:
        posts: List of post dictionaries

    Returns:
        Dictionary with frequency metrics
    """
    dates = []
    for post in posts:
        date = parse_post_date(post)
        if date:
            dates.append(date)

    if not dates:
        return {
            'posts_per_day': 0,
            'posts_per_week': 0,
            'date_range_days': 0,
            'first_post': None,
            'last_post': None
        }

    dates.sort()
    first_date = dates[0]
    last_date = dates[-1]
    date_range = (last_date - first_date).days or 1

    posts_per_day = round(len(dates) / date_range, 2) if date_range > 0 else 0
    posts_per_week = round(posts_per_day * 7, 2)

    return {
        'posts_per_day': posts_per_day,
        'posts_per_week': posts_per_week,
        'date_range_days': date_range,
        'first_post': first_date.isoformat(),
        'last_post': last_date.isoformat()
    }


def create_time_series(posts: List[Dict], granularity: str = 'week') -> List[Dict]:
    """
    Create time series data for posts over time.

    Args:
        posts: List of post dictionaries
        granularity: 'day' or 'week'

    Returns:
        List of time series data points
    """
    date_counts = defaultdict(lambda: {'posts': 0, 'engagement': 0})

    for post in posts:
        date = parse_post_date(post)
        if not date:
            continue

        if granularity == 'week':
            # Start of week (Monday)
            key = (date - timedelta(days=date.weekday())).strftime('%Y-%m-%d')
        else:
            key = date.strftime('%Y-%m-%d')

        date_counts[key]['posts'] += 1
        date_counts[key]['engagement'] += get_post_engagement(post)['total']

    # Convert to sorted list
    result = [
        {'date': date, **data}
        for date, data in sorted(date_counts.items())
    ]

    return result


def get_content_type(post: Dict, platform: str) -> str:
    """
    Determine the content type of a post.

    Args:
        post: The post dictionary
        platform: The platform name

    Returns:
        Content type string
    """
    if platform == 'bluesky':
        embed_type = post.get('embed_type') or ''
        if 'image' in embed_type:
            return 'image'
        elif 'external' in embed_type:
            return 'link'
        elif 'record' in embed_type:
            return 'quote'
        elif 'video' in embed_type:
            return 'video'
        elif post.get('has_media'):
            return 'media'
        return 'text'

    elif platform == 'tiktok':
        return 'video'

    elif platform == 'youtube':
        return 'video'

    elif platform == 'instagram':
        if post.get('is_video'):
            return 'video'
        elif post.get('carousel_media_count', 0) > 1:
            return 'carousel'
        return 'image'

    return 'unknown'


def analyze_content_types(posts: List[Dict], platform: str) -> Dict[str, Dict]:
    """
    Analyze content type breakdown.

    Args:
        posts: List of post dictionaries
        platform: The platform name

    Returns:
        Dictionary mapping content types to counts and engagement
    """
    content_types = defaultdict(lambda: {'count': 0, 'engagement': 0})

    for post in posts:
        content_type = get_content_type(post, platform)
        content_types[content_type]['count'] += 1
        content_types[content_type]['engagement'] += get_post_engagement(post)['total']

    # Calculate percentages
    total_posts = sum(ct['count'] for ct in content_types.values())
    for ct in content_types.values():
        ct['percentage'] = round(ct['count'] / total_posts * 100, 1) if total_posts > 0 else 0

    return dict(content_types)


# =============================================================================
# Data Loading Functions
# =============================================================================

def read_json(path: Path) -> Any:
    """Read JSON file safely."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not read {path}: {e}")
        return None


def load_platform_data(platform_dir: Path) -> Tuple[List[Dict], Optional[Dict]]:
    """
    Load posts and metadata from a platform directory.

    Args:
        platform_dir: Path to the platform directory

    Returns:
        Tuple of (posts list, metadata dict)
    """
    posts = []
    metadata = None

    # Check for posts.json directly in platform dir
    posts_file = platform_dir / "posts.json"
    if posts_file.exists():
        data = read_json(posts_file)
        if isinstance(data, list):
            posts.extend(data)
        elif isinstance(data, dict) and 'posts' in data:
            posts.extend(data.get('posts', []))
            metadata = data.get('engagement_metrics') or data

    # Check for tweets.json (Twitter stores tweets here)
    tweets_file = platform_dir / "tweets.json"
    if tweets_file.exists():
        tweets_data = read_json(tweets_file)
        if isinstance(tweets_data, list) and not posts:
            posts.extend(tweets_data)

    # Check for metadata.json (Instagram stores posts here, YouTube stores videos)
    metadata_file = platform_dir / "metadata.json"
    if metadata_file.exists():
        meta_data = read_json(metadata_file)
        if meta_data:
            metadata = meta_data
            # Instagram stores posts inside metadata.json
            if 'posts' in meta_data and not posts:
                posts.extend(meta_data.get('posts', []))
            # YouTube stores videos inside metadata.json
            if 'videos' in meta_data and not posts:
                posts.extend(meta_data.get('videos', []))

    # Also check subdirectories (YouTube uses channel_id subdirs)
    for subdir in platform_dir.iterdir():
        if subdir.is_dir():
            sub_posts, sub_meta = load_platform_data(subdir)
            posts.extend(sub_posts)
            if sub_meta and not metadata:
                metadata = sub_meta

    return posts, metadata


# =============================================================================
# Analytics Generation
# =============================================================================

def generate_grantee_analytics(grantee_dir: Path) -> Optional[Dict]:
    """
    Generate detailed analytics for a single grantee.

    Args:
        grantee_dir: Path to the grantee's output directory

    Returns:
        Dictionary with detailed analytics
    """
    grantee_name = grantee_dir.name.replace('_', ' ')
    slug = slugify(grantee_dir.name)

    platforms_data = {}
    all_posts = []
    total_engagement = 0
    total_posts = 0
    total_followers = 0

    # Process each platform
    for platform in ['bluesky', 'tiktok', 'youtube', 'twitter', 'instagram', 'facebook', 'linkedin', 'threads']:
        platform_dir = grantee_dir / platform
        if not platform_dir.exists():
            continue

        posts, metadata = load_platform_data(platform_dir)

        # Get follower count from metadata if available
        followers = 0
        if metadata:
            followers = safe_int(
                metadata.get('followers_count') or
                metadata.get('followersCount') or
                (metadata.get('profile', {}) or {}).get('followersCount') or
                (metadata.get('engagement_metrics', {}) or {}).get('followers_count') or
                (metadata.get('data', {}) or {}).get('followers_count')
            )

        # Skip if no posts AND no followers (need at least one data point)
        if not posts and not followers:
            continue

        # Calculate platform metrics
        platform_posts = len([p for p in posts if p])
        platform_engagement = sum(get_post_engagement(p)['total'] for p in posts if p)
        platform_views = sum(get_post_engagement(p)['views'] for p in posts if p)

        platforms_data[platform] = {
            'posts': platform_posts,
            'engagement': platform_engagement,
            'views': platform_views,
            'followers': followers,
            'engagement_rate': calculate_engagement_rate(platform_engagement, platform_posts),
            'top_posts': identify_top_posts(posts, limit=3),
            'frequency': calculate_post_frequency(posts),
            'time_series': create_time_series(posts, 'week'),
            'content_types': analyze_content_types(posts, platform)
        }

        all_posts.extend(posts)
        total_posts += platform_posts
        total_engagement += platform_engagement
        total_followers += followers

    if total_posts == 0:
        return None

    # Calculate platform breakdown with percentages
    platform_breakdown = {}
    for platform, data in platforms_data.items():
        platform_breakdown[platform] = {
            'posts': data['posts'],
            'posts_pct': round(data['posts'] / total_posts * 100, 1) if total_posts > 0 else 0,
            'engagement': data['engagement'],
            'engagement_pct': round(data['engagement'] / total_engagement * 100, 1) if total_engagement > 0 else 0
        }

    return {
        'name': grantee_name,
        'slug': slug,
        'summary': {
            'total_posts': total_posts,
            'total_engagement': total_engagement,
            'total_followers': total_followers,
            'platforms_active': len(platforms_data),
            'engagement_rate': calculate_engagement_rate(total_engagement, total_posts),
            'last_updated': datetime.now().isoformat()
        },
        'platform_breakdown': platform_breakdown,
        'platforms': platforms_data,
        'top_posts': identify_top_posts(all_posts, limit=5),
        'overall_frequency': calculate_post_frequency(all_posts),
        'time_series': create_time_series(all_posts, 'week')
    }


def generate_rankings(all_grantees: List[Dict]) -> Dict:
    """
    Generate rankings by various metrics.

    Args:
        all_grantees: List of grantee analytics dictionaries

    Returns:
        Dictionary with various rankings
    """
    # Filter out None values and grantees with no data
    valid_grantees = [g for g in all_grantees if g and g['summary']['total_posts'] > 0]

    def create_ranking(sorted_grantees, metric_key):
        return [
            {
                'rank': i + 1,
                'name': g['name'],
                'slug': g['slug'],
                'value': g['summary'].get(metric_key, 0)
            }
            for i, g in enumerate(sorted_grantees)
        ]

    return {
        'by_engagement': create_ranking(
            sorted(valid_grantees, key=lambda x: x['summary']['total_engagement'], reverse=True),
            'total_engagement'
        ),
        'by_posts': create_ranking(
            sorted(valid_grantees, key=lambda x: x['summary']['total_posts'], reverse=True),
            'total_posts'
        ),
        'by_engagement_rate': create_ranking(
            sorted(valid_grantees, key=lambda x: x['summary']['engagement_rate'], reverse=True),
            'engagement_rate'
        ),
        'by_followers': create_ranking(
            sorted(valid_grantees, key=lambda x: x['summary']['total_followers'], reverse=True),
            'total_followers'
        ),
        'by_platforms': create_ranking(
            sorted(valid_grantees, key=lambda x: x['summary']['platforms_active'], reverse=True),
            'platforms_active'
        ),
        'generated_at': datetime.now().isoformat()
    }


def generate_platform_analytics(all_grantees: List[Dict]) -> Dict:
    """
    Generate deep platform analysis across all grantees.

    Args:
        all_grantees: List of grantee analytics dictionaries

    Returns:
        Dictionary with platform-level analytics
    """
    valid_grantees = [g for g in all_grantees if g]

    platform_data = defaultdict(lambda: {
        'grantees': 0,
        'total_posts': 0,
        'total_engagement': 0,
        'total_followers': 0,
        'content_types': defaultdict(lambda: {'count': 0, 'engagement': 0}),
        'top_grantees': []
    })

    # Aggregate data per platform
    for grantee in valid_grantees:
        for platform, data in grantee.get('platforms', {}).items():
            pd = platform_data[platform]
            pd['grantees'] += 1
            pd['total_posts'] += data['posts']
            pd['total_engagement'] += data['engagement']
            pd['total_followers'] += data.get('followers', 0)

            # Aggregate content types
            for ct, ct_data in data.get('content_types', {}).items():
                pd['content_types'][ct]['count'] += ct_data['count']
                pd['content_types'][ct]['engagement'] += ct_data['engagement']

            # Track for top grantees list
            pd['top_grantees'].append({
                'name': grantee['name'],
                'slug': grantee['slug'],
                'posts': data['posts'],
                'engagement': data['engagement']
            })

    # Process each platform
    result = {}
    for platform, data in platform_data.items():
        # Sort top grantees by engagement
        data['top_grantees'] = sorted(
            data['top_grantees'],
            key=lambda x: x['engagement'],
            reverse=True
        )[:10]

        # Calculate content type percentages
        total_ct_posts = sum(ct['count'] for ct in data['content_types'].values())
        content_types = {}
        for ct, ct_data in data['content_types'].items():
            content_types[ct] = {
                **ct_data,
                'percentage': round(ct_data['count'] / total_ct_posts * 100, 1) if total_ct_posts > 0 else 0
            }

        result[platform] = {
            'color': PLATFORM_COLORS.get(platform, '#6B7280'),
            'grantees': data['grantees'],
            'total_posts': data['total_posts'],
            'total_engagement': data['total_engagement'],
            'total_followers': data['total_followers'],
            'avg_engagement_per_post': calculate_engagement_rate(data['total_engagement'], data['total_posts']),
            'avg_posts_per_grantee': round(data['total_posts'] / data['grantees'], 1) if data['grantees'] > 0 else 0,
            'content_types': content_types,
            'top_grantees': data['top_grantees']
        }

    return {
        'platforms': result,
        'comparison': {
            'by_engagement': sorted(
                [{'platform': p, 'engagement': d['total_engagement']} for p, d in result.items()],
                key=lambda x: x['engagement'],
                reverse=True
            ),
            'by_posts': sorted(
                [{'platform': p, 'posts': d['total_posts']} for p, d in result.items()],
                key=lambda x: x['posts'],
                reverse=True
            )
        },
        'generated_at': datetime.now().isoformat()
    }


def generate_dashboard_summary(all_grantees: List[Dict], platform_analytics: Dict) -> Dict:
    """
    Generate the main dashboard summary.

    Args:
        all_grantees: List of grantee analytics dictionaries
        platform_analytics: Platform analytics dictionary

    Returns:
        Dashboard summary dictionary
    """
    valid_grantees = [g for g in all_grantees if g and g['summary']['total_posts'] > 0]

    total_posts = sum(g['summary']['total_posts'] for g in valid_grantees)
    total_engagement = sum(g['summary']['total_engagement'] for g in valid_grantees)
    total_followers = sum(g['summary']['total_followers'] for g in valid_grantees)

    # Build grantees list (all grantees, sorted by engagement)
    top_grantees = sorted(valid_grantees, key=lambda x: x['summary']['total_engagement'], reverse=True)

    # Find top platform for each grantee
    def get_top_platform(grantee):
        platforms = grantee.get('platforms', {})
        if not platforms:
            return 'N/A'
        # First try to find platform with highest engagement
        top_by_engagement = max(platforms.keys(), key=lambda p: platforms[p].get('engagement', 0))
        if platforms[top_by_engagement].get('engagement', 0) > 0:
            return top_by_engagement
        # Fallback: platform with most posts
        return max(platforms.keys(), key=lambda p: platforms[p].get('posts', 0))

    return {
        'summary': {
            'totalGrantees': len(valid_grantees),
            'totalPosts': total_posts,
            'totalEngagement': total_engagement,
            'totalFollowers': total_followers,
            'platformsTracked': len(platform_analytics.get('platforms', {})),
            'avgEngagementRate': calculate_engagement_rate(total_engagement, total_posts),
            'lastUpdated': datetime.now().isoformat(),
            'scrapingDuration': 'aggregated'
        },
        'platforms': {
            platform: {
                'posts': data['total_posts'],
                'engagement': data['total_engagement'],
                'followers': data['total_followers'],
                'grantees': data['grantees'],
                'avgEngagement': data['avg_engagement_per_post']
            }
            for platform, data in platform_analytics.get('platforms', {}).items()
        },
        'topGrantees': [
            {
                'name': g['name'],
                'slug': g['slug'],
                'posts': g['summary']['total_posts'],
                'engagement': g['summary']['total_engagement'],
                'followers': g['summary']['total_followers'],
                'engagementRate': g['summary']['engagement_rate'],
                'topPlatform': get_top_platform(g),
                'platformsScraped': g['summary']['platforms_active']
            }
            for g in top_grantees
        ],
        'engagementByPlatform': [
            {
                'platform': platform,
                'engagement': data['total_engagement'],
                'posts': data['total_posts'],
                'color': data['color']
            }
            for platform, data in sorted(
                platform_analytics.get('platforms', {}).items(),
                key=lambda x: x[1]['total_engagement'],
                reverse=True
            )
        ],
        'metadata': {
            'generatedAt': datetime.now().isoformat(),
            'platformColors': PLATFORM_COLORS,
            'version': '2.0.0'
        }
    }


# =============================================================================
# Main Execution
# =============================================================================

def main():
    """Main execution function."""
    print("=" * 60)
    print("NJCIC Detailed Dashboard Data Generator")
    print("=" * 60)

    # Ensure output directories exist
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    GRANTEES_DIR.mkdir(parents=True, exist_ok=True)

    # Collect all grantee analytics
    print("\nScanning grantee directories...")
    all_grantees = []

    for item in sorted(OUTPUT_DIR.iterdir()):
        if item.is_dir() and not item.name.startswith('.'):
            print(f"  Processing: {item.name}")
            grantee_data = generate_grantee_analytics(item)
            if grantee_data:
                all_grantees.append(grantee_data)

                # Save individual grantee file
                grantee_file = GRANTEES_DIR / f"{grantee_data['slug']}.json"
                with open(grantee_file, 'w', encoding='utf-8') as f:
                    json.dump(grantee_data, f, indent=2)
                print(f"    -> Saved: {grantee_file.name}")

    print(f"\nProcessed {len(all_grantees)} grantees with data")

    # Generate rankings
    print("\nGenerating rankings...")
    rankings = generate_rankings(all_grantees)
    rankings_file = DASHBOARD_DIR / "rankings.json"
    with open(rankings_file, 'w', encoding='utf-8') as f:
        json.dump(rankings, f, indent=2)
    print(f"  Saved: {rankings_file}")

    # Generate platform analytics
    print("\nGenerating platform analytics...")
    platform_analytics = generate_platform_analytics(all_grantees)
    platform_file = DASHBOARD_DIR / "platform-analytics.json"
    with open(platform_file, 'w', encoding='utf-8') as f:
        json.dump(platform_analytics, f, indent=2)
    print(f"  Saved: {platform_file}")

    # Generate main dashboard summary
    print("\nGenerating dashboard summary...")
    dashboard_data = generate_dashboard_summary(all_grantees, platform_analytics)
    dashboard_file = DASHBOARD_DIR / "dashboard-data.json"
    with open(dashboard_file, 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, indent=2)
    print(f"  Saved: {dashboard_file}")

    # Also save to scraper output directory
    output_dashboard_file = OUTPUT_DIR / "dashboard-data.json"
    with open(output_dashboard_file, 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, indent=2)
    print(f"  Saved: {output_dashboard_file}")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total Grantees: {dashboard_data['summary']['totalGrantees']}")
    print(f"  Total Posts: {dashboard_data['summary']['totalPosts']}")
    print(f"  Total Engagement: {dashboard_data['summary']['totalEngagement']:,}")
    print(f"  Total Followers: {dashboard_data['summary']['totalFollowers']:,}")
    print(f"  Platforms Tracked: {dashboard_data['summary']['platformsTracked']}")
    print(f"  Avg Engagement Rate: {dashboard_data['summary']['avgEngagementRate']}")

    print("\nPlatform Breakdown:")
    for item in dashboard_data['engagementByPlatform']:
        print(f"  {item['platform'].capitalize():12}: {item['posts']:4} posts, {item['engagement']:,} engagement")

    print("\nTop 5 Grantees by Engagement:")
    for i, g in enumerate(dashboard_data['topGrantees'][:5], 1):
        print(f"  {i}. {g['name']}: {g['engagement']:,} engagement, {g['posts']} posts")

    print("\n" + "=" * 60)
    print("Output files generated:")
    print(f"  - {dashboard_file}")
    print(f"  - {rankings_file}")
    print(f"  - {platform_file}")
    print(f"  - {GRANTEES_DIR}/*.json ({len(all_grantees)} files)")
    print("=" * 60)
    print("\nDone!")


if __name__ == '__main__':
    main()
