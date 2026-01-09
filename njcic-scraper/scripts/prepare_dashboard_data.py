#!/usr/bin/env python3
"""
NJCIC Dashboard Data Transformer

This script transforms scraping_report.json into a dashboard-ready format
for legislators and stakeholders. It creates summary statistics and
platform-specific engagement data suitable for visualization.

Usage:
    python prepare_dashboard_data.py                    # Use default paths
    python prepare_dashboard_data.py --input report.json --output data.json

Output is saved to:
    - njcic-scraper/output/dashboard-data.json
    - dashboard/data/dashboard-data.json (if dashboard folder exists)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


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


def load_scraping_report(report_path: Path) -> Dict[str, Any]:
    """
    Load the scraping report JSON file.

    Args:
        report_path: Path to scraping_report.json

    Returns:
        Parsed JSON data as dictionary

    Raises:
        FileNotFoundError: If report file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    if not report_path.exists():
        raise FileNotFoundError(f"Scraping report not found: {report_path}")

    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_platform_stats(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate platform-level statistics from the report.

    Args:
        report: The full scraping report

    Returns:
        Dictionary with platform stats including posts, engagement, and grantee counts
    """
    platform_stats = report.get("platform_stats", {})
    grantee_results = report.get("grantee_results", [])

    platforms = {}

    for platform, stats in platform_stats.items():
        # Count grantees with successful scrapes for this platform
        grantees_with_data = sum(
            1
            for grantee in grantee_results
            if grantee.get("platforms", {}).get(platform, {}).get("success", False)
        )

        platforms[platform] = {
            "posts": stats.get("total_posts_collected", 0),
            "engagement": stats.get("total_engagement", 0),
            "grantees": grantees_with_data,
            "attempted": stats.get("attempted", 0),
            "successful": stats.get("successful", 0),
            "successRate": stats.get("success_rate", "0%"),
        }

    return platforms


def calculate_top_grantees(
    report: Dict[str, Any], limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Identify top grantees by engagement.

    Args:
        report: The full scraping report
        limit: Maximum number of top grantees to return

    Returns:
        List of top grantees sorted by total engagement
    """
    grantee_results = report.get("grantee_results", [])
    top_grantees = []

    for grantee in grantee_results:
        name = grantee.get("name", "Unknown")
        summary = grantee.get("summary", {})
        platforms_data = grantee.get("platforms", {})

        total_posts = summary.get("total_posts", 0)
        total_engagement = summary.get("total_engagement", 0)

        # Find the top platform by engagement
        # Use -inf so platforms with negative engagement (from scraper errors) still get selected
        top_platform = None
        top_platform_engagement = float("-inf")

        for platform, data in platforms_data.items():
            if data.get("success", False):
                metrics = data.get("engagement_metrics", {})
                platform_engagement = sum(metrics.values())
                if platform_engagement > top_platform_engagement:
                    top_platform_engagement = platform_engagement
                    top_platform = platform

        top_grantees.append(
            {
                "name": name,
                "posts": total_posts,
                "engagement": total_engagement,
                "topPlatform": top_platform or "N/A",
                "platformsScraped": summary.get("platforms_scraped", 0),
            }
        )

    # Sort by engagement (descending) and limit
    top_grantees.sort(key=lambda x: x["engagement"], reverse=True)
    return top_grantees[:limit]


def create_engagement_by_platform(
    platform_stats: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Create engagement data with colors for chart visualization.

    Args:
        platform_stats: Dictionary of platform statistics

    Returns:
        List of platform engagement data with colors
    """
    engagement_data = []

    for platform, stats in platform_stats.items():
        engagement_data.append(
            {
                "platform": platform,
                "engagement": stats.get("engagement", 0),
                "posts": stats.get("posts", 0),
                "color": PLATFORM_COLORS.get(platform, "#808080"),
            }
        )

    # Sort by engagement (descending)
    engagement_data.sort(key=lambda x: x["engagement"], reverse=True)
    return engagement_data


def transform_to_dashboard_data(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform the scraping report into dashboard-ready format.

    Args:
        report: The full scraping report

    Returns:
        Dashboard-formatted data dictionary
    """
    grantee_results = report.get("grantee_results", [])
    platform_stats = calculate_platform_stats(report)

    # Calculate summary statistics
    total_posts = sum(stats.get("posts", 0) for stats in platform_stats.values())
    total_engagement = sum(
        stats.get("engagement", 0) for stats in platform_stats.values()
    )
    platforms_tracked = len([p for p in platform_stats.values() if p.get("posts", 0) > 0])

    dashboard_data = {
        "summary": {
            "totalGrantees": len(grantee_results),
            "totalPosts": total_posts,
            "totalEngagement": total_engagement,
            "platformsTracked": platforms_tracked,
            "lastUpdated": datetime.now().isoformat(),
            "scrapingDuration": report.get("metadata", {}).get(
                "duration_formatted", "N/A"
            ),
        },
        "platforms": platform_stats,
        "topGrantees": calculate_top_grantees(report, limit=10),
        "engagementByPlatform": create_engagement_by_platform(platform_stats),
        "metadata": {
            "generatedAt": datetime.now().isoformat(),
            "sourceReport": report.get("metadata", {}).get("generated_at", "Unknown"),
            "platformColors": PLATFORM_COLORS,
        },
    }

    return dashboard_data


def save_dashboard_data(
    data: Dict[str, Any], output_paths: List[Path]
) -> List[Path]:
    """
    Save dashboard data to specified output paths.

    Args:
        data: Dashboard data dictionary
        output_paths: List of paths to save to

    Returns:
        List of paths where data was successfully saved
    """
    saved_paths = []

    for output_path in output_paths:
        try:
            # Create parent directories if they don't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            saved_paths.append(output_path)
            print(f"Saved dashboard data to: {output_path}")

        except Exception as e:
            print(f"Warning: Could not save to {output_path}: {e}")

    return saved_paths


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Transform NJCIC scraping report into dashboard-ready format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--input",
        "-i",
        type=str,
        metavar="PATH",
        help="Path to scraping_report.json (default: ../output/scraping_report.json)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        metavar="PATH",
        help="Additional output path for dashboard-data.json",
    )

    parser.add_argument(
        "--top-grantees",
        type=int,
        default=10,
        metavar="N",
        help="Number of top grantees to include (default: 10)",
    )

    parser.add_argument(
        "--pretty",
        action="store_true",
        default=True,
        help="Pretty-print JSON output (default: True)",
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()

    # Determine base directory (relative to this script)
    script_dir = Path(__file__).resolve().parent
    base_dir = script_dir.parent  # njcic-scraper directory
    project_dir = base_dir.parent  # njcic directory

    # Determine input path
    if args.input:
        input_path = Path(args.input)
    else:
        input_path = base_dir / "output" / "scraping_report.json"

    # Determine output paths
    output_paths = [
        base_dir / "output" / "dashboard-data.json",
    ]

    # Add dashboard/data path if dashboard folder exists
    dashboard_data_dir = project_dir / "dashboard" / "data"
    if dashboard_data_dir.exists() or (project_dir / "dashboard").exists():
        output_paths.append(dashboard_data_dir / "dashboard-data.json")

    # Add custom output path if specified
    if args.output:
        output_paths.append(Path(args.output))

    # Load the scraping report
    print(f"Loading scraping report from: {input_path}")
    try:
        report = load_scraping_report(input_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nMake sure you have run the scraper first to generate scraping_report.json")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in scraping report: {e}")
        sys.exit(1)

    # Transform to dashboard format
    print("Transforming data to dashboard format...")
    dashboard_data = transform_to_dashboard_data(report)

    # Print summary
    summary = dashboard_data["summary"]
    print(f"\nDashboard Data Summary:")
    print(f"  Total Grantees: {summary['totalGrantees']}")
    print(f"  Total Posts: {summary['totalPosts']}")
    print(f"  Total Engagement: {summary['totalEngagement']:,}")
    print(f"  Platforms Tracked: {summary['platformsTracked']}")

    # Save to output paths
    print(f"\nSaving dashboard data...")
    saved = save_dashboard_data(dashboard_data, output_paths)

    if saved:
        print(f"\nSuccessfully saved to {len(saved)} location(s)")
    else:
        print("\nWarning: No files were saved!")
        sys.exit(1)


if __name__ == "__main__":
    main()
