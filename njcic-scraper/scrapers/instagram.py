"""
Instagram scraper using instaloader library.
Scrapes post metadata without downloading media files for speed.
"""

import json
import os
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

import instaloader

from .base import BaseScraper

# Rate limiting constants - conservative to avoid 401/403 blocks
MIN_DELAY_BETWEEN_REQUESTS = 30  # seconds between profiles
MAX_DELAY_BETWEEN_REQUESTS = 60  # seconds between profiles
DELAY_AFTER_LOGIN = 10  # seconds
DELAY_BETWEEN_POSTS = 1.0  # seconds between posts


class InstagramScraper(BaseScraper):
    """Scraper for Instagram profiles using instaloader."""

    platform_name = "instagram"

    def __init__(self, output_dir: str = "output", session_file: Optional[str] = None):
        """
        Initialize Instagram scraper.

        Args:
            output_dir: Base directory for storing scraped data
            session_file: Optional path to instaloader session file
        """
        super().__init__(Path(output_dir) if output_dir else None)
        self.session_file = session_file
        self.loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            post_metadata_txt_pattern='',
            quiet=True
        )

    def extract_username(self, url: str) -> Optional[str]:
        """
        Extract username from Instagram URL.

        Handles formats:
        - instagram.com/username
        - instagram.com/username/
        - https://www.instagram.com/username
        - https://www.instagram.com/username/

        Args:
            url: Instagram URL

        Returns:
            Extracted username or None if invalid
        """
        # Remove protocol and www if present
        url = url.lower().strip()

        # Return None for empty strings
        if not url:
            return None

        url = re.sub(r'^https?://', '', url)
        url = re.sub(r'^www\.', '', url)

        # Match instagram.com/username pattern
        pattern = r'^instagram\.com/([a-zA-Z0-9._]+)/?.*$'
        match = re.match(pattern, url)

        if match:
            username = match.group(1)
            # Filter out known non-username paths
            if username not in ['p', 'reel', 'reels', 'tv', 'stories', 'explore']:
                return username

        # If URL is just a username without domain
        if '/' not in url and '.' not in url and url:
            return url

        return None

    def _load_session(self) -> bool:
        """
        Load Instagram session from file if available.

        Returns:
            True if session loaded successfully, False otherwise
        """
        if not self.session_file or not os.path.exists(self.session_file):
            return False

        try:
            self.loader.load_session_from_file(
                username=self._get_session_username(),
                filename=self.session_file
            )
            self.logger.info("Session loaded successfully")
            return True
        except Exception as e:
            self.logger.warning(f"Failed to load session: {e}")
            return False

    def _get_session_username(self) -> str:
        """
        Get username from session file.

        Returns:
            Username stored in session file
        """
        if self.session_file and os.path.exists(self.session_file):
            # Session filename format: session-{username}
            basename = os.path.basename(self.session_file)
            if basename.startswith('session-'):
                return basename.replace('session-', '')
        return os.getenv('INSTAGRAM_USERNAME', 'user')

    def _get_output_directory(self, grantee_name: str, username: str) -> Path:
        """
        Create and return Instagram-specific output directory.

        Creates structure: output/{grantee_name}/instagram/{username}

        Args:
            grantee_name: Name of the grantee
            username: Instagram username

        Returns:
            Path object for the output directory
        """
        # Get base output path from parent class
        base_path = self.get_output_path(grantee_name)

        # Add username subdirectory
        username_path = base_path / username
        username_path.mkdir(exist_ok=True, parents=True)

        return username_path

    def _login_if_needed(self) -> bool:
        """
        Log in to Instagram using credentials from environment variables.

        Returns:
            True if login successful or already logged in, False otherwise
        """
        # Check if already logged in
        if self.loader.context.is_logged_in:
            self.logger.info("Already logged in")
            return True

        # Try to load existing session first
        if self._load_session():
            return True

        # Attempt login with credentials from environment
        username = os.getenv('INSTAGRAM_USERNAME')
        password = os.getenv('INSTAGRAM_PASSWORD')

        if not username or not password:
            self.logger.warning(
                "No Instagram credentials found in environment variables. "
                "Some features may be limited."
            )
            return False

        try:
            self.loader.login(username, password)
            self.logger.info(f"Successfully logged in as {username}")

            # Rate limit: delay after login
            time.sleep(DELAY_AFTER_LOGIN)

            # Save session for future use
            if self.session_file:
                session_dir = os.path.dirname(self.session_file)
                if session_dir:
                    os.makedirs(session_dir, exist_ok=True)
                self.loader.save_session_to_file(self.session_file)
                self.logger.info(f"Session saved to {self.session_file}")

            return True
        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    def _extract_post_metadata(self, post) -> Dict[str, Any]:
        """
        Extract metadata from an Instagram post.

        Args:
            post: Instaloader Post object

        Returns:
            Dictionary with post metadata
        """
        metadata = {
            'shortcode': post.shortcode,
            'url': f"https://www.instagram.com/p/{post.shortcode}/",
            'caption': post.caption if post.caption else '',
            'date': post.date_utc.isoformat() if post.date_utc else None,
            'likes': post.likes,
            'comments': post.comments,
            'is_video': post.is_video,
            'video_views': post.video_view_count if post.is_video else None,
            'typename': post.typename,
        }

        # Add optional fields if available
        try:
            metadata['location'] = post.location.name if post.location else None
        except:
            metadata['location'] = None

        try:
            metadata['tagged_users'] = [user.username for user in post.tagged_users]
        except:
            metadata['tagged_users'] = []

        try:
            metadata['hashtags'] = list(post.caption_hashtags)
        except:
            metadata['hashtags'] = []

        return metadata

    def _calculate_engagement_metrics(
        self,
        posts: List[Dict[str, Any]],
        profile
    ) -> Dict[str, Any]:
        """
        Calculate engagement metrics from posts and profile.

        Args:
            posts: List of post metadata dictionaries
            profile: Instaloader Profile object

        Returns:
            Dictionary with engagement metrics
        """
        total_likes = sum(post.get('likes', 0) for post in posts)
        total_comments = sum(post.get('comments', 0) for post in posts)
        total_video_views = sum(
            post.get('video_views', 0) or 0
            for post in posts
            if post.get('is_video')
        )

        followers = profile.followers if hasattr(profile, 'followers') else 0
        following = profile.followees if hasattr(profile, 'followees') else 0

        # Calculate average engagement rate
        # Engagement rate = (likes + comments) / followers * 100
        avg_engagement_rate = 0.0
        if followers > 0 and posts:
            total_engagement = total_likes + total_comments
            avg_engagement = total_engagement / len(posts)
            avg_engagement_rate = (avg_engagement / followers) * 100

        metrics = {
            'followers_count': followers,
            'following_count': following,
            'total_likes': total_likes,
            'total_comments': total_comments,
            'total_video_views': total_video_views,
            'avg_engagement_rate': round(avg_engagement_rate, 2),
            'posts_analyzed': len(posts),
        }

        return metrics

    def scrape(self, url: str, grantee_name: str, max_posts: int = 25) -> Dict[str, Any]:
        """
        Scrape Instagram profile posts.

        Downloads metadata for the specified number of posts without downloading media files.

        Args:
            url: Instagram profile URL
            grantee_name: Name of the grantee
            max_posts: Maximum number of posts to scrape (default: 25)

        Returns:
            Dictionary containing:
                - success (bool): Whether scraping was successful
                - posts_downloaded (int): Number of posts downloaded
                - errors (List[str]): List of errors encountered
                - engagement_metrics (Dict): Engagement metrics
        """
        errors = []
        posts_downloaded = 0
        posts_metadata = []

        # Extract username from URL
        username = self.extract_username(url)
        if not username:
            error_msg = f"Could not extract username from URL: {url}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'posts_downloaded': 0,
                'errors': [error_msg],
                'engagement_metrics': {}
            }

        self.logger.info(f"Starting scrape for Instagram user: {username}")

        # Create output directory
        output_dir = self._get_output_directory(grantee_name, username)

        try:
            # Attempt login
            self._login_if_needed()

            # Rate limit: random delay before loading profile
            delay = random.uniform(MIN_DELAY_BETWEEN_REQUESTS, MAX_DELAY_BETWEEN_REQUESTS)
            self.logger.debug(f"Rate limit: waiting {delay:.1f}s before loading profile")
            time.sleep(delay)

            # Load profile
            try:
                profile = instaloader.Profile.from_username(
                    self.loader.context,
                    username
                )
            except instaloader.exceptions.ProfileNotExistsException:
                error_msg = f"Profile does not exist: {username}"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'posts_downloaded': 0,
                    'errors': [error_msg],
                    'engagement_metrics': {}
                }
            except Exception as e:
                error_msg = f"Failed to load profile: {str(e)}"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'posts_downloaded': 0,
                    'errors': [error_msg],
                    'engagement_metrics': {}
                }

            # Check if profile is private
            if profile.is_private and not profile.followed_by_viewer:
                warning_msg = (
                    f"Profile {username} is private and you don't follow them. "
                    "Skipping scrape."
                )
                self.logger.warning(warning_msg)

                # Save metadata with note about private profile
                metadata = {
                    'username': username,
                    'url': url,
                    'grantee_name': grantee_name,
                    'is_private': True,
                    'note': 'Profile is private and inaccessible',
                    'posts': [],
                    'engagement_metrics': {
                        'followers_count': profile.followers if hasattr(profile, 'followers') else 0,
                        'following_count': profile.followees if hasattr(profile, 'followees') else 0,
                        'total_likes': 0,
                        'total_comments': 0,
                        'total_video_views': 0,
                        'avg_engagement_rate': 0.0,
                        'posts_analyzed': 0,
                    }
                }
                self.save_metadata(output_dir, metadata)

                return {
                    'success': True,
                    'posts_downloaded': 0,
                    'errors': [warning_msg],
                    'engagement_metrics': metadata['engagement_metrics']
                }

            # Scrape posts (limit to max_posts)
            self.logger.info(f"Downloading metadata for last {max_posts} posts from {username}")
            post_count = 0

            try:
                for post in profile.get_posts():
                    if post_count >= max_posts:
                        break

                    try:
                        post_metadata = self._extract_post_metadata(post)
                        posts_metadata.append(post_metadata)
                        post_count += 1
                        self.logger.info(
                            f"Extracted metadata for post {post_count}/{max_posts}: "
                            f"{post.shortcode}"
                        )

                        # Rate limit: small delay between posts
                        time.sleep(DELAY_BETWEEN_POSTS)
                    except Exception as e:
                        error_msg = f"Error extracting post {post.shortcode}: {str(e)}"
                        self.logger.error(error_msg)
                        errors.append(error_msg)

                posts_downloaded = post_count

            except Exception as e:
                error_msg = f"Error iterating posts: {str(e)}"
                self.logger.error(error_msg)
                errors.append(error_msg)

            # Calculate engagement metrics
            engagement_metrics = self._calculate_engagement_metrics(
                posts_metadata,
                profile
            )

            # Save metadata
            metadata = {
                'username': username,
                'url': url,
                'grantee_name': grantee_name,
                'profile': {
                    'full_name': profile.full_name if hasattr(profile, 'full_name') else '',
                    'biography': profile.biography if hasattr(profile, 'biography') else '',
                    'external_url': profile.external_url if hasattr(profile, 'external_url') else '',
                    'is_verified': profile.is_verified if hasattr(profile, 'is_verified') else False,
                    'is_private': profile.is_private,
                    'mediacount': profile.mediacount if hasattr(profile, 'mediacount') else 0,
                },
                'posts': posts_metadata,
                'engagement_metrics': engagement_metrics,
                'errors': errors,
            }

            self.save_metadata(output_dir, metadata)

            success = posts_downloaded > 0 or len(errors) == 0
            self.logger.info(
                f"Scrape completed. Posts downloaded: {posts_downloaded}, "
                f"Errors: {len(errors)}"
            )

            return {
                'success': success,
                'posts_downloaded': posts_downloaded,
                'errors': errors,
                'engagement_metrics': engagement_metrics
            }

        except Exception as e:
            error_msg = f"Unexpected error during scrape: {str(e)}"
            self.logger.error(error_msg)
            errors.append(error_msg)

            return {
                'success': False,
                'posts_downloaded': posts_downloaded,
                'errors': errors,
                'engagement_metrics': {}
            }
