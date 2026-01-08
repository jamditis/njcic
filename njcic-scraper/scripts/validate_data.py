#!/usr/bin/env python3
"""
Data Validation Script for NJCIC Social Media Scraper

This script validates the quality of scraped social media data by:
1. Loading scraping_report.json from the output directory
2. Checking for missing required fields
3. Flagging posts with zero engagement metrics
4. Detecting duplicate post IDs
5. Validating timestamps are within reasonable range
6. Checking for empty/null URLs

Usage:
    python validate_data.py                    # Run validation
    python validate_data.py --save             # Save report to output/data_quality_report.json
    python validate_data.py --verbose          # Show detailed output
    python validate_data.py --posts-dir        # Also scan individual post files
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Script location - use relative paths based on this
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
OUTPUT_DIR = BASE_DIR / "output"
SCRAPING_REPORT_PATH = OUTPUT_DIR / "scraping_report.json"
DATA_QUALITY_REPORT_PATH = OUTPUT_DIR / "data_quality_report.json"

# Required fields for post validation
REQUIRED_POST_FIELDS = [
    "post_id",
    "text",
    "timestamp",
    "author",
    "platform",
    "url"
]

# Engagement metrics to check
ENGAGEMENT_METRICS = [
    "likes",
    "comments",
    "shares",
    "views",
    "reactions"
]

# Timestamp validation range (posts should be within this range)
MIN_VALID_DATE = datetime(2000, 1, 1)
MAX_VALID_DATE = datetime.now() + timedelta(days=1)  # Allow 1 day buffer for timezone issues


class DataValidator:
    """Validates scraped social media data quality."""

    def __init__(self, verbose: bool = False, scan_posts: bool = False):
        """
        Initialize the validator.

        Args:
            verbose: Whether to print detailed output
            scan_posts: Whether to scan individual post files in output directories
        """
        self.verbose = verbose
        self.scan_posts = scan_posts
        self.issues: List[Dict[str, Any]] = []
        self.stats = {
            "total_posts_analyzed": 0,
            "posts_with_issues": 0,
            "duplicate_post_ids": 0,
            "missing_fields": defaultdict(int),
            "zero_engagement_posts": 0,
            "invalid_timestamps": 0,
            "empty_urls": 0,
        }

    def log(self, message: str, level: str = "INFO") -> None:
        """Print message if verbose mode is enabled."""
        if self.verbose or level in ("ERROR", "WARNING"):
            prefix = {"INFO": "[INFO]", "WARNING": "[WARN]", "ERROR": "[ERR]"}.get(level, "[INFO]")
            print(f"{prefix} {message}")

    def load_scraping_report(self) -> Optional[Dict[str, Any]]:
        """
        Load the scraping report from the output directory.

        Returns:
            Report dictionary or None if file doesn't exist
        """
        if not SCRAPING_REPORT_PATH.exists():
            self.log(f"Scraping report not found: {SCRAPING_REPORT_PATH}", "ERROR")
            return None

        try:
            with open(SCRAPING_REPORT_PATH, 'r', encoding='utf-8') as f:
                report = json.load(f)
            self.log(f"Loaded scraping report from {SCRAPING_REPORT_PATH}")
            return report
        except json.JSONDecodeError as e:
            self.log(f"Failed to parse scraping report: {e}", "ERROR")
            return None

    def collect_posts_from_output(self) -> List[Dict[str, Any]]:
        """
        Collect all posts from individual post files in output directories.

        Returns:
            List of all posts found
        """
        all_posts = []

        if not OUTPUT_DIR.exists():
            self.log(f"Output directory not found: {OUTPUT_DIR}", "WARNING")
            return all_posts

        # Walk through output directory structure
        for grantee_dir in OUTPUT_DIR.iterdir():
            if not grantee_dir.is_dir() or grantee_dir.name.startswith('.'):
                continue

            for platform_dir in grantee_dir.iterdir():
                if not platform_dir.is_dir():
                    continue

                posts_file = platform_dir / "posts.json"
                if posts_file.exists():
                    try:
                        with open(posts_file, 'r', encoding='utf-8') as f:
                            posts = json.load(f)
                            if isinstance(posts, list):
                                for post in posts:
                                    post['_source_file'] = str(posts_file)
                                    post['_grantee'] = grantee_dir.name
                                all_posts.extend(posts)
                                self.log(f"Loaded {len(posts)} posts from {posts_file}")
                    except (json.JSONDecodeError, Exception) as e:
                        self.log(f"Failed to load {posts_file}: {e}", "WARNING")

        return all_posts

    def validate_required_fields(self, post: Dict[str, Any], context: str = "") -> List[str]:
        """
        Check for missing required fields in a post.

        Args:
            post: Post dictionary to validate
            context: Context string for error reporting

        Returns:
            List of missing field names
        """
        missing = []
        for field in REQUIRED_POST_FIELDS:
            if field not in post or post[field] is None or post[field] == "":
                missing.append(field)
                self.stats["missing_fields"][field] += 1

        return missing

    def check_zero_engagement(self, post: Dict[str, Any]) -> bool:
        """
        Check if a post has zero engagement across all metrics.

        Args:
            post: Post dictionary to check

        Returns:
            True if all engagement metrics are zero/missing
        """
        total_engagement = 0
        for metric in ENGAGEMENT_METRICS:
            value = post.get(metric, 0)
            if isinstance(value, (int, float)):
                total_engagement += value

        return total_engagement == 0

    def validate_timestamp(self, timestamp: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate that a timestamp is within a reasonable range.

        Args:
            timestamp: Timestamp value to validate (string or int)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if timestamp is None:
            return False, "Timestamp is null"

        try:
            # Handle different timestamp formats
            if isinstance(timestamp, (int, float)):
                # Unix timestamp
                dt = datetime.fromtimestamp(timestamp)
            elif isinstance(timestamp, str):
                # Try ISO format first
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except ValueError:
                    # Try other common formats
                    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"]:
                        try:
                            dt = datetime.strptime(timestamp, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        return False, f"Could not parse timestamp format: {timestamp}"
            else:
                return False, f"Invalid timestamp type: {type(timestamp)}"

            # Check if within valid range
            if dt < MIN_VALID_DATE:
                return False, f"Timestamp too old: {dt}"
            if dt > MAX_VALID_DATE:
                return False, f"Timestamp in the future: {dt}"

            return True, None

        except (ValueError, OSError) as e:
            return False, f"Invalid timestamp: {e}"

    def check_duplicate_post_ids(self, posts: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Find duplicate post IDs across all posts.

        Args:
            posts: List of post dictionaries

        Returns:
            Dictionary mapping duplicate post_ids to list of sources
        """
        post_id_sources = defaultdict(list)

        for post in posts:
            post_id = post.get("post_id")
            if post_id:
                source = post.get("_source_file", "unknown")
                post_id_sources[str(post_id)].append(source)

        # Filter to only duplicates
        duplicates = {
            post_id: sources
            for post_id, sources in post_id_sources.items()
            if len(sources) > 1
        }

        return duplicates

    def validate_posts(self, posts: List[Dict[str, Any]]) -> None:
        """
        Validate a list of posts and record issues.

        Args:
            posts: List of post dictionaries to validate
        """
        self.stats["total_posts_analyzed"] = len(posts)

        # Check for duplicate post IDs
        duplicates = self.check_duplicate_post_ids(posts)
        self.stats["duplicate_post_ids"] = len(duplicates)

        for post_id, sources in duplicates.items():
            self.issues.append({
                "type": "duplicate_post_id",
                "post_id": post_id,
                "occurrences": len(sources),
                "sources": sources[:5],  # Limit to first 5 sources
                "severity": "warning"
            })

        # Validate each post
        for i, post in enumerate(posts):
            post_context = f"Post {i+1}"
            post_id = post.get("post_id", "unknown")
            has_issue = False

            # Check required fields
            missing_fields = self.validate_required_fields(post, post_context)
            if missing_fields:
                has_issue = True
                self.issues.append({
                    "type": "missing_required_fields",
                    "post_id": post_id,
                    "missing_fields": missing_fields,
                    "platform": post.get("platform", "unknown"),
                    "severity": "error"
                })

            # Check zero engagement
            if self.check_zero_engagement(post):
                self.stats["zero_engagement_posts"] += 1
                # Only flag as issue if it's a notable pattern
                # Individual posts may legitimately have zero engagement

            # Validate timestamp
            timestamp = post.get("timestamp")
            is_valid, error_msg = self.validate_timestamp(timestamp)
            if not is_valid:
                has_issue = True
                self.stats["invalid_timestamps"] += 1
                self.issues.append({
                    "type": "invalid_timestamp",
                    "post_id": post_id,
                    "timestamp": str(timestamp),
                    "error": error_msg,
                    "platform": post.get("platform", "unknown"),
                    "severity": "warning"
                })

            # Check for empty URL
            url = post.get("url")
            if url is None or url == "" or url == "null":
                has_issue = True
                self.stats["empty_urls"] += 1
                self.issues.append({
                    "type": "empty_url",
                    "post_id": post_id,
                    "platform": post.get("platform", "unknown"),
                    "severity": "warning"
                })

            if has_issue:
                self.stats["posts_with_issues"] += 1

    def analyze_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the scraping report for quality metrics.

        Args:
            report: Scraping report dictionary

        Returns:
            Analysis results dictionary
        """
        analysis = {
            "total_grantees": 0,
            "successful_scrapes": 0,
            "failed_scrapes": 0,
            "platforms_coverage": {},
            "grantees_with_no_data": [],
        }

        # Analyze grantee results
        grantee_results = report.get("grantee_results", [])
        analysis["total_grantees"] = len(grantee_results)

        platform_stats = defaultdict(lambda: {"has_data": 0, "no_data": 0, "total_posts": 0})

        for grantee in grantee_results:
            grantee_name = grantee.get("name", "Unknown")
            summary = grantee.get("summary", {})
            platforms = grantee.get("platforms", {})

            total_posts = summary.get("total_posts", 0)
            if total_posts > 0:
                analysis["successful_scrapes"] += 1
            else:
                analysis["failed_scrapes"] += 1
                analysis["grantees_with_no_data"].append(grantee_name)

            # Track platform coverage
            for platform, data in platforms.items():
                posts_downloaded = data.get("posts_downloaded", 0)
                if posts_downloaded > 0:
                    platform_stats[platform]["has_data"] += 1
                    platform_stats[platform]["total_posts"] += posts_downloaded
                else:
                    platform_stats[platform]["no_data"] += 1

        # Convert platform stats
        for platform, stats in platform_stats.items():
            total = stats["has_data"] + stats["no_data"]
            analysis["platforms_coverage"][platform] = {
                "grantees_with_data": stats["has_data"],
                "grantees_without_data": stats["no_data"],
                "coverage_rate": f"{(stats['has_data'] / total * 100) if total > 0 else 0:.1f}%",
                "total_posts": stats["total_posts"]
            }

        return analysis

    def generate_quality_report(self, report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a comprehensive data quality report.

        Args:
            report: Original scraping report (or None)

        Returns:
            Quality report dictionary
        """
        quality_report = {
            "generated_at": datetime.now().isoformat(),
            "source_report": str(SCRAPING_REPORT_PATH),
            "validation_summary": {},
            "data_quality_issues": [],
            "summary_statistics": {},
            "platforms_coverage": {},
            "recommendations": []
        }

        # Analyze scraping report if available
        if report:
            analysis = self.analyze_report(report)
            quality_report["validation_summary"] = {
                "total_grantees": analysis["total_grantees"],
                "successful_scrapes": analysis["successful_scrapes"],
                "failed_scrapes": analysis["failed_scrapes"],
                "grantees_with_no_data": analysis["grantees_with_no_data"][:20]  # Limit list
            }
            quality_report["platforms_coverage"] = analysis["platforms_coverage"]

        # If scanning posts, collect and validate them
        if self.scan_posts:
            posts = self.collect_posts_from_output()
            if posts:
                self.validate_posts(posts)

        # Add post validation stats
        quality_report["summary_statistics"] = {
            "total_posts_analyzed": self.stats["total_posts_analyzed"],
            "posts_with_issues": self.stats["posts_with_issues"],
            "issue_rate": f"{(self.stats['posts_with_issues'] / self.stats['total_posts_analyzed'] * 100) if self.stats['total_posts_analyzed'] > 0 else 0:.1f}%",
            "duplicate_post_ids": self.stats["duplicate_post_ids"],
            "zero_engagement_posts": self.stats["zero_engagement_posts"],
            "invalid_timestamps": self.stats["invalid_timestamps"],
            "empty_urls": self.stats["empty_urls"],
            "missing_fields_breakdown": dict(self.stats["missing_fields"])
        }

        # Add issues (limited to prevent huge reports)
        quality_report["data_quality_issues"] = self.issues[:100]
        if len(self.issues) > 100:
            quality_report["data_quality_issues_truncated"] = True
            quality_report["total_issues_found"] = len(self.issues)

        # Generate recommendations
        quality_report["recommendations"] = self.generate_recommendations()

        return quality_report

    def generate_recommendations(self) -> List[str]:
        """
        Generate actionable recommendations based on findings.

        Returns:
            List of recommendation strings
        """
        recommendations = []

        if self.stats["duplicate_post_ids"] > 0:
            recommendations.append(
                f"Found {self.stats['duplicate_post_ids']} duplicate post IDs. "
                "Consider implementing deduplication logic in the scrapers."
            )

        if self.stats["missing_fields"]["post_id"] > 0:
            recommendations.append(
                f"Missing post_id in {self.stats['missing_fields']['post_id']} posts. "
                "This field is critical for data integrity."
            )

        if self.stats["missing_fields"]["timestamp"] > 0:
            recommendations.append(
                f"Missing timestamps in {self.stats['missing_fields']['timestamp']} posts. "
                "Timestamps are important for temporal analysis."
            )

        if self.stats["invalid_timestamps"] > 0:
            recommendations.append(
                f"Found {self.stats['invalid_timestamps']} invalid timestamps. "
                "Review timestamp parsing logic in platform scrapers."
            )

        if self.stats["empty_urls"] > 0:
            recommendations.append(
                f"Found {self.stats['empty_urls']} posts with empty/null URLs. "
                "Post URLs are essential for verification and reference."
            )

        zero_engagement_rate = (
            self.stats["zero_engagement_posts"] / self.stats["total_posts_analyzed"] * 100
            if self.stats["total_posts_analyzed"] > 0 else 0
        )
        if zero_engagement_rate > 50:
            recommendations.append(
                f"{zero_engagement_rate:.1f}% of posts have zero engagement. "
                "This may indicate scraping issues or very new posts."
            )

        if not recommendations:
            recommendations.append("No significant data quality issues detected.")

        return recommendations

    def print_summary(self, quality_report: Dict[str, Any]) -> None:
        """
        Print a human-readable summary to console.

        Args:
            quality_report: The generated quality report
        """
        print("\n" + "=" * 70)
        print("DATA QUALITY VALIDATION REPORT")
        print("=" * 70)
        print(f"Generated: {quality_report['generated_at']}")
        print(f"Source: {quality_report['source_report']}")
        print()

        # Validation Summary
        summary = quality_report.get("validation_summary", {})
        if summary:
            print("SCRAPING SUMMARY")
            print("-" * 40)
            print(f"  Total Grantees:     {summary.get('total_grantees', 'N/A')}")
            print(f"  Successful Scrapes: {summary.get('successful_scrapes', 'N/A')}")
            print(f"  Failed Scrapes:     {summary.get('failed_scrapes', 'N/A')}")
            print()

        # Platform Coverage
        platforms = quality_report.get("platforms_coverage", {})
        if platforms:
            print("PLATFORM COVERAGE")
            print("-" * 40)
            for platform, stats in sorted(platforms.items()):
                print(f"  {platform.capitalize():12} - "
                      f"Coverage: {stats['coverage_rate']:>6}, "
                      f"Posts: {stats['total_posts']:>5}, "
                      f"Grantees: {stats['grantees_with_data']}/{stats['grantees_with_data'] + stats['grantees_without_data']}")
            print()

        # Post Validation Stats
        stats = quality_report.get("summary_statistics", {})
        if stats.get("total_posts_analyzed", 0) > 0:
            print("POST VALIDATION STATISTICS")
            print("-" * 40)
            print(f"  Posts Analyzed:       {stats.get('total_posts_analyzed', 0)}")
            print(f"  Posts with Issues:    {stats.get('posts_with_issues', 0)} ({stats.get('issue_rate', '0%')})")
            print(f"  Duplicate Post IDs:   {stats.get('duplicate_post_ids', 0)}")
            print(f"  Zero Engagement:      {stats.get('zero_engagement_posts', 0)}")
            print(f"  Invalid Timestamps:   {stats.get('invalid_timestamps', 0)}")
            print(f"  Empty URLs:           {stats.get('empty_urls', 0)}")

            missing = stats.get("missing_fields_breakdown", {})
            if missing:
                print("\n  Missing Fields:")
                for field, count in sorted(missing.items(), key=lambda x: -x[1]):
                    print(f"    - {field}: {count}")
            print()

        # Issues (limited display)
        issues = quality_report.get("data_quality_issues", [])
        if issues:
            print("SAMPLE ISSUES (first 10)")
            print("-" * 40)
            for issue in issues[:10]:
                issue_type = issue.get("type", "unknown")
                severity = issue.get("severity", "info").upper()
                post_id = issue.get("post_id", "N/A")

                if issue_type == "missing_required_fields":
                    print(f"  [{severity}] Post {post_id}: Missing fields: {', '.join(issue.get('missing_fields', []))}")
                elif issue_type == "duplicate_post_id":
                    print(f"  [{severity}] Duplicate post_id: {post_id} ({issue.get('occurrences', 0)} occurrences)")
                elif issue_type == "invalid_timestamp":
                    print(f"  [{severity}] Post {post_id}: {issue.get('error', 'Invalid timestamp')}")
                elif issue_type == "empty_url":
                    print(f"  [{severity}] Post {post_id}: Empty or null URL")
                else:
                    print(f"  [{severity}] {issue_type}: {post_id}")

            if len(issues) > 10:
                print(f"  ... and {len(issues) - 10} more issues")
            print()

        # Recommendations
        recommendations = quality_report.get("recommendations", [])
        if recommendations:
            print("RECOMMENDATIONS")
            print("-" * 40)
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
            print()

        print("=" * 70)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate NJCIC social media scraper data quality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Run validation with report only
  %(prog)s --save             # Save report to output/data_quality_report.json
  %(prog)s --verbose          # Show detailed output
  %(prog)s --posts-dir        # Also scan individual post files
        """
    )

    parser.add_argument(
        '--save',
        action='store_true',
        help='Save quality report to output/data_quality_report.json'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output during validation'
    )

    parser.add_argument(
        '--posts-dir',
        action='store_true',
        help='Scan and validate individual post files in output directories'
    )

    parser.add_argument(
        '--report-path',
        type=str,
        metavar='PATH',
        help=f'Path to scraping_report.json (default: {SCRAPING_REPORT_PATH})'
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()

    # Override report path if specified
    global SCRAPING_REPORT_PATH
    if args.report_path:
        SCRAPING_REPORT_PATH = Path(args.report_path)

    # Initialize validator
    validator = DataValidator(
        verbose=args.verbose,
        scan_posts=args.posts_dir
    )

    # Load scraping report
    report = validator.load_scraping_report()

    if report is None and not args.posts_dir:
        print(f"Error: No scraping report found at {SCRAPING_REPORT_PATH}")
        print("Run the scraper first or use --posts-dir to validate existing post files.")
        sys.exit(1)

    # Generate quality report
    quality_report = validator.generate_quality_report(report)

    # Print summary to console
    validator.print_summary(quality_report)

    # Save report if requested
    if args.save:
        DATA_QUALITY_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DATA_QUALITY_REPORT_PATH, 'w', encoding='utf-8') as f:
            json.dump(quality_report, f, indent=2, ensure_ascii=False)
        print(f"Quality report saved to: {DATA_QUALITY_REPORT_PATH}")

    # Exit with error code if significant issues found
    if quality_report.get("summary_statistics", {}).get("posts_with_issues", 0) > 0:
        sys.exit(0)  # Issues found but validation completed
    else:
        sys.exit(0)  # Success


if __name__ == '__main__':
    main()
