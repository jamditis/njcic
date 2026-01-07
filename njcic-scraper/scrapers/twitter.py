"""
Twitter/X scraper implementation using gallery-dl.
"""

import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from .base import BaseScraper


class TwitterScraper(BaseScraper):
    """Scraper for Twitter/X platform using gallery-dl."""

    platform_name = "twitter"

    # List of Nitter instances as fallback (though gallery-dl is preferred)
    NITTER_INSTANCES = [
        "nitter.net",
        "nitter.poast.org",
        "nitter.privacydev.net",
    ]

    def __init__(self, output_dir: str = "output", max_posts: int = 25):
        """
        Initialize Twitter scraper.

        Args:
            output_dir: Base directory for storing scraped data
            max_posts: Maximum number of posts to scrape (default: 25)
        """
        super().__init__(output_dir)
        self.max_posts = max_posts
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Check if required tools (gallery-dl) are installed."""
        try:
            result = subprocess.run(
                ["gallery-dl", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                self.logger.warning(
                    "gallery-dl not found. Install with: pip install gallery-dl"
                )
        except (subprocess.SubprocessError, FileNotFoundError):
            self.logger.warning(
                "gallery-dl not found. Install with: pip install gallery-dl"
            )

    def extract_username(self, url: str) -> Optional[str]:
        """
        Extract username from Twitter/X URL.

        Handles:
        - twitter.com/username
        - x.com/username
        - twitter.com/username/status/...
        - x.com/username/status/...

        Args:
            url: Twitter/X URL

        Returns:
            Extracted username or None if invalid
        """
        try:
            # Parse the URL
            parsed = urlparse(url)

            # Check if domain is twitter.com or x.com
            domain = parsed.netloc.lower()
            if not any(d in domain for d in ['twitter.com', 'x.com']):
                self.logger.error(f"Invalid Twitter/X URL: {url}")
                return None

            # Extract path and get username
            path = parsed.path.strip('/')
            if not path:
                return None

            # Split path and get first component (username)
            parts = path.split('/')
            username = parts[0]

            # Remove @ if present
            username = username.lstrip('@')

            # Validate username format (alphanumeric and underscore)
            if not re.match(r'^[A-Za-z0-9_]{1,15}$', username):
                self.logger.error(f"Invalid username format: {username}")
                return None

            return username

        except Exception as e:
            self.logger.error(f"Error extracting username from {url}: {e}")
            return None

    def _scrape_with_gallery_dl(
        self,
        username: str,
        output_dir: Path
    ) -> Dict[str, Any]:
        """
        Scrape Twitter profile using gallery-dl.

        Args:
            username: Twitter username
            output_dir: Directory to save content

        Returns:
            Dictionary with scraping results
        """
        errors = []
        posts_data = []

        try:
            # Create gallery-dl config for this scrape
            config = {
                "extractor": {
                    "twitter": {
                        "user": {
                            "username": username
                        },
                        "retweets": False,
                        "replies": False,
                        "text-tweets": True,
                        "videos": True,
                    }
                },
                "output": {
                    "mode": "terminal",
                    "progress": False
                }
            }

            # Save temporary config
            config_path = output_dir / "gallery-dl-config.json"
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            # Construct gallery-dl command
            twitter_url = f"https://twitter.com/{username}"

            # Use gallery-dl to fetch metadata
            cmd = [
                "gallery-dl",
                "--config", str(config_path),
                "--write-metadata",
                "--no-download",  # Just get metadata first
                "--range", f"1-{self.max_posts}",
                "-D", str(output_dir),
                twitter_url
            ]

            self.logger.info(f"Running gallery-dl for @{username}")
            self.logger.debug(f"Command: {' '.join(cmd)}")

            # Execute gallery-dl
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                error_msg = f"gallery-dl failed: {result.stderr}"
                self.logger.error(error_msg)
                errors.append(error_msg)
                return {
                    "success": False,
                    "posts_downloaded": 0,
                    "errors": errors,
                    "posts_data": []
                }

            # Parse metadata files
            posts_data = self._parse_metadata_files(output_dir)

            # Clean up config
            config_path.unlink(missing_ok=True)

            return {
                "success": len(posts_data) > 0,
                "posts_downloaded": len(posts_data),
                "errors": errors,
                "posts_data": posts_data
            }

        except subprocess.TimeoutExpired:
            error_msg = "gallery-dl timed out after 5 minutes"
            self.logger.error(error_msg)
            errors.append(error_msg)
            return {
                "success": False,
                "posts_downloaded": 0,
                "errors": errors,
                "posts_data": []
            }

        except Exception as e:
            error_msg = f"Error during gallery-dl scraping: {str(e)}"
            self.logger.error(error_msg)
            errors.append(error_msg)
            return {
                "success": False,
                "posts_downloaded": 0,
                "errors": errors,
                "posts_data": []
            }

    def _parse_metadata_files(self, output_dir: Path) -> List[Dict[str, Any]]:
        """
        Parse gallery-dl metadata JSON files.

        Args:
            output_dir: Directory containing metadata files

        Returns:
            List of parsed post data
        """
        posts_data = []

        # Find all .json files (gallery-dl metadata)
        json_files = list(output_dir.glob("*.json"))

        # Exclude our own metadata.json and config
        json_files = [
            f for f in json_files
            if f.name not in ["metadata.json", "gallery-dl-config.json"]
        ]

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Extract relevant fields
                post_info = {
                    "tweet_id": data.get("tweet_id", ""),
                    "text": data.get("content", ""),
                    "date": data.get("date", ""),
                    "likes": data.get("favorite_count", 0),
                    "retweets": data.get("retweet_count", 0),
                    "replies": data.get("reply_count", 0),
                    "views": data.get("view_count", 0),
                    "author": data.get("author", {}).get("name", ""),
                    "username": data.get("author", {}).get("nick", ""),
                }

                posts_data.append(post_info)

            except Exception as e:
                self.logger.warning(f"Error parsing {json_file}: {e}")

        return posts_data

    def _calculate_engagement_metrics(
        self,
        posts_data: List[Dict[str, Any]],
        username: str
    ) -> Dict[str, Any]:
        """
        Calculate engagement metrics from posts data.

        Args:
            posts_data: List of post data dictionaries
            username: Twitter username

        Returns:
            Dictionary of engagement metrics
        """
        if not posts_data:
            return {
                "username": username,
                "followers_count": None,
                "total_likes": 0,
                "total_retweets": 0,
                "total_replies": 0,
                "total_views": 0,
                "avg_likes": 0.0,
                "avg_retweets": 0.0,
                "avg_replies": 0.0,
                "avg_views": 0.0,
                "avg_engagement_rate": 0.0,
                "posts_analyzed": 0
            }

        total_likes = sum(post.get("likes", 0) for post in posts_data)
        total_retweets = sum(post.get("retweets", 0) for post in posts_data)
        total_replies = sum(post.get("replies", 0) for post in posts_data)
        total_views = sum(post.get("views", 0) for post in posts_data)

        num_posts = len(posts_data)

        # Calculate averages
        avg_likes = total_likes / num_posts if num_posts > 0 else 0
        avg_retweets = total_retweets / num_posts if num_posts > 0 else 0
        avg_replies = total_replies / num_posts if num_posts > 0 else 0
        avg_views = total_views / num_posts if num_posts > 0 else 0

        # Calculate average engagement rate
        # Engagement rate = (likes + retweets + replies) / views
        total_engagements = total_likes + total_retweets + total_replies
        avg_engagement_rate = (
            (total_engagements / total_views * 100)
            if total_views > 0 else 0.0
        )

        return {
            "username": username,
            "followers_count": None,  # Not available without API access
            "total_likes": total_likes,
            "total_retweets": total_retweets,
            "total_replies": total_replies,
            "total_views": total_views,
            "avg_likes": round(avg_likes, 2),
            "avg_retweets": round(avg_retweets, 2),
            "avg_replies": round(avg_replies, 2),
            "avg_views": round(avg_views, 2),
            "avg_engagement_rate": round(avg_engagement_rate, 2),
            "posts_analyzed": num_posts
        }

    def scrape(self, url: str, grantee_name: str) -> Dict[str, Any]:
        """
        Scrape Twitter/X profile.

        Args:
            url: Twitter/X profile URL
            grantee_name: Name of the grantee

        Returns:
            Dictionary containing:
                - success (bool): Whether scraping was successful
                - posts_downloaded (int): Number of posts downloaded
                - errors (List[str]): List of errors encountered
                - engagement_metrics (Dict): Engagement metrics
        """
        errors = []

        try:
            # Extract username
            username = self.extract_username(url)
            if not username:
                return {
                    "success": False,
                    "posts_downloaded": 0,
                    "errors": ["Failed to extract username from URL"],
                    "engagement_metrics": {}
                }

            self.logger.info(f"Scraping Twitter profile: @{username}")

            # Create output directory
            output_dir = self._create_output_directory(grantee_name, username)
            self.logger.info(f"Output directory: {output_dir}")

            # Scrape with gallery-dl
            scrape_result = self._scrape_with_gallery_dl(username, output_dir)

            if not scrape_result["success"]:
                errors.extend(scrape_result["errors"])
                return {
                    "success": False,
                    "posts_downloaded": 0,
                    "errors": errors,
                    "engagement_metrics": {}
                }

            posts_data = scrape_result["posts_data"]
            errors.extend(scrape_result["errors"])

            # Calculate engagement metrics
            engagement_metrics = self._calculate_engagement_metrics(
                posts_data,
                username
            )

            # Save metadata
            metadata = {
                "url": url,
                "username": username,
                "grantee_name": grantee_name,
                "posts_downloaded": len(posts_data),
                "engagement_metrics": engagement_metrics,
                "posts": posts_data,
                "errors": errors
            }

            self._save_metadata(output_dir, metadata)

            return {
                "success": True,
                "posts_downloaded": len(posts_data),
                "errors": errors,
                "engagement_metrics": engagement_metrics
            }

        except Exception as e:
            error_msg = f"Unexpected error during scraping: {str(e)}"
            self.logger.error(error_msg)
            errors.append(error_msg)

            return {
                "success": False,
                "posts_downloaded": 0,
                "errors": errors,
                "engagement_metrics": {}
            }


# Example usage
if __name__ == "__main__":
    import sys
    import logging

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Test the scraper
    if len(sys.argv) < 3:
        print("Usage: python twitter.py <twitter_url> <grantee_name>")
        sys.exit(1)

    twitter_url = sys.argv[1]
    grantee_name = sys.argv[2]

    scraper = TwitterScraper(output_dir="output", max_posts=25)
    result = scraper.scrape(twitter_url, grantee_name)

    print("\n=== Scraping Results ===")
    print(f"Success: {result['success']}")
    print(f"Posts Downloaded: {result['posts_downloaded']}")
    print(f"Errors: {result['errors']}")
    print(f"\nEngagement Metrics:")
    for key, value in result.get('engagement_metrics', {}).items():
        print(f"  {key}: {value}")
