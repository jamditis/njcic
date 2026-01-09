"""
TikTok scraper using yt-dlp for metadata extraction.

This scraper downloads metadata only (no videos) for performance,
extracting engagement metrics and post information from TikTok profiles.
"""
import re
import json
import subprocess
import time
import random
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

from scrapers.base import BaseScraper
import config


class TikTokScraper(BaseScraper):
    """Scraper for TikTok metadata using yt-dlp."""

    platform_name = "tiktok"

    # Expanded anti-bot user agents to rotate (15+ diverse agents)
    USER_AGENTS = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        # Chrome on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Chrome on Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        # Firefox on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
        # Safari on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    ]

    # TikTok API endpoints to try (configurable via environment)
    API_ENDPOINTS = [
        "api22-normal-c-useast2a.tiktokv.com",
        "api16-normal-c-useast1a.tiktokv.com",
        "api19-normal-c-useast1a.tiktokv.com",
        "api22-normal-c-useast1a.tiktokv.com",
    ]

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize TikTok scraper.

        Args:
            output_dir: Directory to save scraped data (Path object or None for config default)
        """
        super().__init__(output_dir)

        # Load proxy configuration from environment
        self.proxy = os.getenv("TIKTOK_PROXY") or os.getenv("HTTP_PROXY")
        if self.proxy:
            self.logger.info(f"Using proxy: {self.proxy}")

        # Load API endpoint from environment or use default
        custom_endpoint = os.getenv("TIKTOK_API_ENDPOINT")
        if custom_endpoint:
            self.api_endpoint = custom_endpoint
            self.logger.info(f"Using custom TikTok API endpoint: {custom_endpoint}")
        else:
            self.api_endpoint = random.choice(self.API_ENDPOINTS)
            self.logger.debug(f"Using default TikTok API endpoint: {self.api_endpoint}")

    def extract_username(self, url: str) -> Optional[str]:
        """
        Extract TikTok username from URL.

        Handles formats:
        - https://www.tiktok.com/@username
        - https://tiktok.com/@username
        - https://www.tiktok.com/username
        - tiktok.com/username

        Args:
            url: TikTok profile URL

        Returns:
            Username string or None if extraction fails
        """
        if not url:
            return None

        # Remove protocol and www
        url = url.strip()

        # Pattern 1: tiktok.com/@username (most common)
        match = re.search(r'tiktok\.com/@([a-zA-Z0-9_.]+)', url)
        if match:
            return match.group(1)

        # Pattern 2: tiktok.com/username (without @)
        match = re.search(r'tiktok\.com/([a-zA-Z0-9_.]+)(?:/|\?|$)', url)
        if match:
            username = match.group(1)
            # Exclude common non-username paths
            if username not in ['trending', 'foryou', 'following', 'live', 'search', 'tag', 'music', 'video']:
                return username

        self.logger.warning(f"Could not extract username from URL: {url}")
        return None

    def scrape(self, url: str, grantee_name: str, max_posts: Optional[int] = None) -> Dict[str, Any]:
        """
        Scrape TikTok metadata using yt-dlp (no video downloads).

        Args:
            url: TikTok profile URL
            grantee_name: Name of the grantee/influencer
            max_posts: Maximum number of posts to scrape (defaults to config value)

        Returns:
            Dictionary containing:
                - success: bool - Whether scraping succeeded
                - posts_downloaded: int - Number of posts scraped
                - errors: list - List of error messages
                - engagement_metrics: dict - Aggregated engagement data
                - output_path: str - Path where data was saved
        """
        # Use provided max_posts or fall back to config default
        max_posts = max_posts or config.MAX_POSTS_PER_ACCOUNT
        result = {
            "success": False,
            "posts_downloaded": 0,
            "errors": [],
            "engagement_metrics": {
                "followers_count": None,
                "total_views": 0,
                "total_likes": 0,
                "total_comments": 0,
                "total_shares": 0,
                "avg_engagement_rate": 0.0,
            },
            "output_path": ""
        }

        # Extract username
        username = self.extract_username(url)
        if not username:
            result["errors"].append(f"Failed to extract username from URL: {url}")
            return result

        # Ensure username has @ prefix for TikTok URL
        if not username.startswith('@'):
            profile_url = f"https://www.tiktok.com/@{username}"
        else:
            profile_url = f"https://www.tiktok.com/{username}"
            username = username.lstrip('@')

        self.logger.info(f"Scraping TikTok profile: @{username} for {grantee_name}")

        # Create output directory using base class method
        output_path = self.get_output_path(grantee_name)
        result["output_path"] = str(output_path)

        # Temporary directory for info.json files
        temp_dir = output_path / "temp"
        temp_dir.mkdir(exist_ok=True)

        try:
            # Run yt-dlp to extract metadata only (no video download)
            posts_data = self._run_ytdlp(profile_url, temp_dir, username, max_posts)

            if not posts_data:
                result["errors"].append("No posts found or unable to extract metadata")
                return result

            # Process posts and calculate metrics
            result["posts_downloaded"] = len(posts_data)
            result["engagement_metrics"] = self._calculate_engagement_metrics(posts_data)

            # Save posts using base class method
            self.save_posts(posts_data, output_path, "posts.json")

            # Save engagement metrics
            self.save_metadata(output_path, {
                "posts": posts_data,
                "engagement_metrics": result["engagement_metrics"],
                "username": username,
                "url": profile_url,
                "posts_count": len(posts_data)
            })

            result["success"] = True
            self.logger.info(
                f"Successfully scraped {result['posts_downloaded']} posts from @{username}. "
                f"Engagement: {result['engagement_metrics']['total_likes']:,} likes, "
                f"{result['engagement_metrics']['total_views']:,} views"
            )

        except subprocess.TimeoutExpired:
            result["errors"].append("yt-dlp process timed out (>10 minutes)")
            self.logger.error(f"Timeout scraping @{username}")

        except FileNotFoundError:
            result["errors"].append(
                "yt-dlp not found. Install with: pip install yt-dlp"
            )
            self.logger.error("yt-dlp is not installed")

        except Exception as e:
            result["errors"].append(f"Unexpected error: {str(e)}")
            self.logger.exception(f"Error scraping @{username}")

        finally:
            # Cleanup temp directory
            self._cleanup_temp_dir(temp_dir)

        return result

    def _run_ytdlp(self, profile_url: str, temp_dir: Path, username: str, max_posts: int) -> List[Dict[str, Any]]:
        """
        Execute yt-dlp to extract metadata with improved retry logic.

        Args:
            profile_url: TikTok profile URL
            temp_dir: Temporary directory for info.json files
            username: TikTok username
            max_posts: Maximum number of posts to scrape

        Returns:
            List of post metadata dictionaries

        Raises:
            subprocess.TimeoutExpired: If process exceeds timeout
            FileNotFoundError: If yt-dlp is not installed
        """
        output_template = str(temp_dir / "%(id)s.%(ext)s")

        # Build yt-dlp command with anti-bot measures
        cmd = [
            "yt-dlp",
            "--write-info-json",      # Save metadata to .info.json
            "--skip-download",         # Don't download videos (metadata only)
            "--no-warnings",           # Suppress warnings for cleaner output
            "--playlist-end", str(max_posts),  # Limit to max_posts
            "--extractor-args", f"tiktok:api_hostname={self.api_endpoint}",  # Use configured API endpoint
            "--sleep-requests", "1",   # Sleep 1 second between requests (rate limiting)
            "--retries", "5",          # Retry failed requests 5 times
            "--fragment-retries", "5", # Retry failed fragments 5 times
            "-o", output_template,     # Output template
        ]

        # Try to use browser impersonation for better anti-bot evasion
        # Requires curl-cffi package (pip install curl-cffi)
        impersonate_target = os.getenv("TIKTOK_IMPERSONATE", "chrome")
        try:
            # Check if impersonation is available by testing if curl_cffi is installed
            import importlib.util
            if importlib.util.find_spec("curl_cffi") is not None:
                cmd.extend(["--impersonate", impersonate_target])
                self.logger.info(f"Using browser impersonation: {impersonate_target}")
            else:
                # Fallback to user agent rotation without impersonation
                cmd.extend(["--user-agent", self._get_user_agent()])
                self.logger.debug("Browser impersonation not available (curl_cffi not installed), using user agent rotation")
        except Exception as e:
            # Fallback to user agent rotation
            cmd.extend(["--user-agent", self._get_user_agent()])
            self.logger.debug(f"Could not enable impersonation: {e}")

        # Add proxy if configured and disable cert verification for proxied requests
        if self.proxy:
            cmd.extend(["--proxy", self.proxy])
            # Disable SSL verification when using proxy (common for corporate/container proxies)
            cmd.append("--no-check-certificates")
            self.logger.debug(f"Using proxy with SSL verification disabled: {self.proxy}")

        # Check if TIKTOK_IGNORE_SSL env var is set (useful for testing environments)
        if os.getenv("TIKTOK_IGNORE_SSL", "").lower() in ("1", "true", "yes"):
            cmd.append("--no-check-certificates")
            self.logger.debug("SSL certificate verification disabled via TIKTOK_IGNORE_SSL")

        cmd.append(profile_url)

        self.logger.debug(f"Running yt-dlp command: {' '.join(cmd)}")

        # Execute yt-dlp with exponential backoff + jitter
        max_retries = 4
        base_delay = 3  # Base delay in seconds

        for attempt in range(max_retries):
            try:
                # Rotate API endpoint on retry attempts
                if attempt > 0:
                    new_endpoint = random.choice(self.API_ENDPOINTS)
                    cmd = [arg.replace(f"tiktok:api_hostname={self.api_endpoint}",
                                     f"tiktok:api_hostname={new_endpoint}")
                          if "tiktok:api_hostname" in arg else arg for arg in cmd]
                    self.logger.debug(f"Rotating API endpoint to: {new_endpoint}")

                process = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 minute timeout
                    check=False,
                )

                # Check for common errors
                if process.returncode != 0:
                    stderr = process.stderr.lower()
                    stdout = process.stdout.lower()

                    self.logger.debug(f"yt-dlp stderr: {process.stderr}")
                    self.logger.debug(f"yt-dlp stdout: {process.stdout}")

                    # Enhanced anti-bot detection patterns
                    anti_bot_keywords = [
                        'captcha', 'blocked', '403', 'forbidden', 'too many requests',
                        'rate limit', 'access denied', 'not available', 'restricted',
                        'verification', 'challenge', 'suspicious activity', '429'
                    ]

                    if any(keyword in stderr or keyword in stdout for keyword in anti_bot_keywords):
                        if attempt < max_retries - 1:
                            # Exponential backoff with jitter
                            wait_time = base_delay * (2 ** attempt) + random.uniform(0, 2)
                            self.logger.warning(
                                f"Anti-bot detection triggered. Retrying in {wait_time:.1f}s... "
                                f"(Attempt {attempt + 1}/{max_retries})"
                            )
                            time.sleep(wait_time)
                            continue
                        else:
                            raise Exception(
                                "TikTok is blocking requests after multiple attempts. "
                                "Anti-bot measures detected. Try again later, use a different "
                                "network/VPN, or set TIKTOK_PROXY environment variable."
                            )

                    # Network errors - retry with backoff
                    network_keywords = [
                        'network', 'connection', 'timeout', 'unable to download',
                        'timed out', 'could not connect', 'connection refused'
                    ]

                    if any(keyword in stderr or keyword in stdout for keyword in network_keywords):
                        if attempt < max_retries - 1:
                            wait_time = base_delay * (attempt + 1) + random.uniform(0, 1)
                            self.logger.warning(
                                f"Network error detected. Retrying in {wait_time:.1f}s... "
                                f"(Attempt {attempt + 1}/{max_retries})"
                            )
                            time.sleep(wait_time)
                            continue

                    # Check for private account or embedding disabled
                    private_keywords = ['private', 'embedding disabled', 'unable to extract secondary user id']
                    if any(keyword in stderr or keyword in stdout for keyword in private_keywords):
                        self.logger.warning(
                            f"TikTok account appears to be private or has embedding disabled: {profile_url}. "
                            f"This account cannot be scraped via yt-dlp. Try using official TikTok API if available."
                        )
                        return []

                    # Check for no content (account exists but no videos)
                    no_content_keywords = ['no videos found', 'no entries', 'playlist is empty']
                    if any(keyword in stderr or keyword in stdout for keyword in no_content_keywords):
                        self.logger.warning(
                            f"No videos found for profile: {profile_url}. "
                            f"Account may have no videos or username may be invalid."
                        )
                        return []

                # Parse .info.json files
                posts_data = self._parse_info_json_files(temp_dir)

                if posts_data:
                    self.logger.info(f"Successfully extracted {len(posts_data)} posts")
                    return posts_data
                elif attempt < max_retries - 1:
                    # No data but no error - might be transient issue
                    wait_time = base_delay + random.uniform(0, 1)
                    self.logger.warning(
                        f"No data extracted but no error. Retrying in {wait_time:.1f}s... "
                        f"(Attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    return []

            except subprocess.TimeoutExpired:
                if attempt < max_retries - 1:
                    wait_time = base_delay * (attempt + 1)
                    self.logger.warning(
                        f"Process timeout after 10 minutes. Retrying... "
                        f"(Attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    raise

        return []

    def _parse_info_json_files(self, temp_dir: Path) -> List[Dict[str, Any]]:
        """
        Parse all .info.json files from temp directory.

        Args:
            temp_dir: Directory containing .info.json files

        Returns:
            List of post metadata dictionaries
        """
        posts_data = []
        info_files = list(temp_dir.glob("*.info.json"))

        self.logger.debug(f"Found {len(info_files)} info.json files")

        for info_file in info_files:
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)

                # Extract relevant fields
                post_data = {
                    "post_id": info.get("id"),
                    "title": info.get("title") or info.get("fulltitle") or "",
                    "description": info.get("description") or "",
                    "date": info.get("upload_date"),  # Format: YYYYMMDD
                    "timestamp": info.get("timestamp"),
                    "views": info.get("view_count", 0) or 0,
                    "likes": info.get("like_count", 0) or 0,
                    "comments": info.get("comment_count", 0) or 0,
                    "shares": info.get("repost_count", 0) or 0,  # TikTok calls it repost_count
                    "duration": info.get("duration"),
                    "username": info.get("uploader_id") or info.get("creator"),
                    "display_name": info.get("uploader") or info.get("channel"),
                    "url": info.get("webpage_url"),
                    "thumbnail": info.get("thumbnail"),
                }

                posts_data.append(post_data)

            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse {info_file}: {e}")
            except Exception as e:
                self.logger.warning(f"Error processing {info_file}: {e}")

        # Sort by timestamp (newest first) if available
        posts_data.sort(key=lambda x: x.get("timestamp", 0) or 0, reverse=True)

        return posts_data

    def _calculate_engagement_metrics(self, posts_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate aggregated engagement metrics from posts.

        Args:
            posts_data: List of post metadata dictionaries

        Returns:
            Dictionary with engagement metrics
        """
        if not posts_data:
            return {
                "followers_count": None,
                "total_views": 0,
                "total_likes": 0,
                "total_comments": 0,
                "total_shares": 0,
                "avg_engagement_rate": 0.0,
            }

        total_views = sum(post.get("views", 0) for post in posts_data)
        total_likes = sum(post.get("likes", 0) for post in posts_data)
        total_comments = sum(post.get("comments", 0) for post in posts_data)
        total_shares = sum(post.get("shares", 0) for post in posts_data)

        # Calculate average engagement rate
        # Engagement rate = (likes + comments + shares) / views
        total_engagements = total_likes + total_comments + total_shares
        avg_engagement_rate = (total_engagements / total_views * 100) if total_views > 0 else 0.0

        # Note: TikTok API via yt-dlp doesn't provide follower count in video metadata
        # This would require separate API call or scraping the profile page
        followers_count = None  # Would need TikTok API or profile scraping

        return {
            "followers_count": followers_count,
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "avg_engagement_rate": round(avg_engagement_rate, 2),
            "posts_analyzed": len(posts_data),
        }

    def _get_user_agent(self) -> str:
        """
        Get a rotating user agent for anti-bot evasion.

        Returns:
            User agent string from expanded pool
        """
        return random.choice(self.USER_AGENTS)

    def _cleanup_temp_dir(self, temp_dir: Path) -> None:
        """
        Clean up temporary directory and its contents.

        Args:
            temp_dir: Temporary directory to clean up
        """
        try:
            if temp_dir.exists():
                for file in temp_dir.iterdir():
                    file.unlink()
                temp_dir.rmdir()
                self.logger.debug(f"Cleaned up temp directory: {temp_dir}")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup temp directory: {e}")
