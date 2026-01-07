"""
YouTube scraper using yt-dlp.
"""
import subprocess
import json
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from .base import BaseScraper
import config


class YouTubeScraper(BaseScraper):
    """Scraper for YouTube channels using yt-dlp."""

    platform_name = "youtube"

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize YouTube scraper.

        Args:
            output_dir: Directory to save scraped data. If None, uses config.OUTPUT_DIR
        """
        super().__init__(output_dir)

    def extract_username(self, url: str) -> Optional[str]:
        """
        Extract channel identifier from YouTube URL.

        Handles:
        - youtube.com/@handle
        - youtube.com/c/channelname
        - youtube.com/channel/CHANNELID
        - youtube.com/user/username

        Args:
            url: YouTube URL

        Returns:
            Channel identifier (handle, channel name, channel ID, or username)
            Returns None if URL format is not recognized
        """
        try:
            # Remove protocol and www if present
            url = url.replace('https://', '').replace('http://', '').replace('www.', '')

            # Parse the URL
            parsed = urlparse(f'https://{url}')
            path = parsed.path.rstrip('/')

            # Handle @handle format
            if '/@' in path:
                match = re.search(r'/@([^/]+)', path)
                if match:
                    return f"@{match.group(1)}"

            # Handle /c/channelname format
            if '/c/' in path:
                match = re.search(r'/c/([^/]+)', path)
                if match:
                    return match.group(1)

            # Handle /channel/CHANNELID format
            if '/channel/' in path:
                match = re.search(r'/channel/([^/]+)', path)
                if match:
                    return match.group(1)

            # Handle /user/username format
            if '/user/' in path:
                match = re.search(r'/user/([^/]+)', path)
                if match:
                    return match.group(1)

            # If no pattern matched, log error and return None
            self.logger.error(f"Could not extract channel identifier from URL: {url}")
            return None

        except Exception as e:
            self.logger.error(f"Error extracting username from URL {url}: {e}")
            return None

    def _run_ytdlp(self, url: str, max_videos: int = 25) -> List[Dict[str, Any]]:
        """
        Run yt-dlp to extract video metadata.

        Args:
            url: YouTube channel URL
            max_videos: Maximum number of videos to fetch

        Returns:
            List of video metadata dictionaries

        Raises:
            RuntimeError: If yt-dlp command fails
        """
        try:
            # Construct yt-dlp command
            cmd = [
                'yt-dlp',
                '--flat-playlist',
                '--dump-json',
                '--playlist-end', str(max_videos),
                '--no-warnings',
                '--quiet',
                url
            ]

            self.logger.info(f"Running yt-dlp command: {' '.join(cmd)}")

            # Run command and capture output
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                error_msg = result.stderr or "Unknown error"
                raise RuntimeError(f"yt-dlp command failed: {error_msg}")

            # Parse JSON lines
            videos = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        videos.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Failed to parse JSON line: {e}")
                        continue

            return videos

        except subprocess.TimeoutExpired:
            raise RuntimeError("yt-dlp command timed out after 5 minutes")
        except FileNotFoundError:
            raise RuntimeError("yt-dlp not found. Please install it: pip install yt-dlp")
        except Exception as e:
            self.logger.error(f"Error running yt-dlp: {e}")
            raise

    def _get_detailed_video_info(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get detailed information for specific videos.

        Args:
            video_ids: List of video IDs

        Returns:
            List of detailed video metadata
        """
        detailed_videos = []

        for video_id in video_ids:
            try:
                self.rate_limit()  # Respect rate limiting

                video_url = f"https://www.youtube.com/watch?v={video_id}"
                cmd = [
                    'yt-dlp',
                    '--dump-json',
                    '--no-warnings',
                    '--quiet',
                    video_url
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=config.TIMEOUT
                )

                if result.returncode == 0 and result.stdout:
                    video_data = json.loads(result.stdout)
                    detailed_videos.append(video_data)
                else:
                    self.logger.warning(f"Failed to get details for video {video_id}")

            except Exception as e:
                self.logger.error(f"Error getting video details for {video_id}: {e}")
                if not config.SKIP_ON_ERROR:
                    raise
                continue

        return detailed_videos

    def _extract_video_metadata(self, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract relevant metadata from video data.

        Args:
            videos: Raw video data from yt-dlp

        Returns:
            List of cleaned video metadata
        """
        extracted_videos = []

        for video in videos:
            try:
                metadata = {
                    'video_id': video.get('id'),
                    'title': video.get('title'),
                    'description': video.get('description', ''),
                    'upload_date': video.get('upload_date'),
                    'views': video.get('view_count', 0),
                    'likes': video.get('like_count', 0),
                    'comments': video.get('comment_count', 0),
                    'duration': video.get('duration'),
                    'url': video.get('webpage_url') or f"https://www.youtube.com/watch?v={video.get('id')}",
                }
                extracted_videos.append(metadata)
            except Exception as e:
                self.logger.warning(f"Error extracting metadata for video: {e}")
                if not config.SKIP_ON_ERROR:
                    raise
                continue

        return extracted_videos

    def _calculate_engagement_metrics(
        self,
        videos: List[Dict[str, Any]],
        channel_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate engagement metrics from video data.

        Args:
            videos: List of video metadata
            channel_info: Optional channel information

        Returns:
            Dictionary of engagement metrics
        """
        if not videos:
            return {
                'subscribers_count': None,
                'total_views': 0,
                'total_likes': 0,
                'total_comments': 0,
                'avg_views_per_video': 0,
                'avg_engagement_rate': 0,
            }

        total_views = sum(v.get('views', 0) for v in videos)
        total_likes = sum(v.get('likes', 0) for v in videos)
        total_comments = sum(v.get('comments', 0) for v in videos)
        num_videos = len(videos)

        avg_views = total_views / num_videos if num_videos > 0 else 0

        # Calculate engagement rate (likes + comments) / views
        # Only for videos with views > 0
        engagement_rates = []
        for video in videos:
            views = video.get('views', 0)
            if views > 0:
                likes = video.get('likes', 0)
                comments = video.get('comments', 0)
                engagement_rate = ((likes + comments) / views) * 100
                engagement_rates.append(engagement_rate)

        avg_engagement_rate = (
            sum(engagement_rates) / len(engagement_rates)
            if engagement_rates else 0
        )

        # Extract subscriber count from channel info if available
        subscribers_count = None
        if channel_info:
            subscribers_count = channel_info.get('channel_follower_count') or \
                               channel_info.get('subscriber_count')

        return {
            'subscribers_count': subscribers_count,
            'total_views': total_views,
            'total_likes': total_likes,
            'total_comments': total_comments,
            'avg_views_per_video': round(avg_views, 2),
            'avg_engagement_rate': round(avg_engagement_rate, 4),
        }

    def scrape(
        self,
        url: str,
        grantee_name: str,
        max_posts: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Scrape YouTube channel data.

        Args:
            url: YouTube channel URL
            grantee_name: Name of the grantee
            max_posts: Maximum number of videos to scrape (defaults to 25)

        Returns:
            Dictionary with:
                - success: bool
                - posts_downloaded: int
                - errors: list of error dictionaries
                - engagement_metrics: dict with engagement statistics
                - output_path: str (path to output directory)
        """
        errors = []
        videos_metadata = []
        engagement_metrics = {}
        max_videos = max_posts or config.MAX_POSTS_PER_ACCOUNT

        try:
            # Extract channel identifier
            channel_id = self.extract_username(url)
            if not channel_id:
                error_msg = f"Could not extract channel identifier from URL: {url}"
                self.logger.error(error_msg)
                errors.append({'error': error_msg, 'url': url})
                return {
                    'success': False,
                    'posts_downloaded': 0,
                    'errors': errors,
                    'engagement_metrics': self._calculate_engagement_metrics([]),
                    'output_path': ''
                }

            self.logger.info(f"Scraping YouTube channel: {channel_id}")

            # Get output path
            output_path = self.get_output_path(grantee_name)
            channel_output_path = output_path / channel_id.replace('@', '').replace('/', '_')
            channel_output_path.mkdir(exist_ok=True, parents=True)

            # Get initial playlist data (flat format for speed)
            flat_videos = self._run_ytdlp(url, max_videos=max_videos)

            if not flat_videos:
                self.logger.warning("No videos found in channel")
                error_msg = "No videos found in channel"
                errors.append({'error': error_msg, 'channel_id': channel_id})

                # Still save metadata even if no videos
                metadata = {
                    'channel_id': channel_id,
                    'channel_url': url,
                    'grantee_name': grantee_name,
                    'total_videos_scraped': 0,
                    'engagement_metrics': self._calculate_engagement_metrics([]),
                    'videos': [],
                    'errors': errors
                }
                self.save_metadata(channel_output_path, metadata)

                return {
                    'success': False,
                    'posts_downloaded': 0,
                    'errors': errors,
                    'engagement_metrics': self._calculate_engagement_metrics([]),
                    'output_path': str(channel_output_path)
                }

            # Extract video IDs
            video_ids = [v.get('id') for v in flat_videos if v.get('id')]
            self.logger.info(f"Found {len(video_ids)} videos, fetching detailed metadata...")

            # Get detailed information for each video
            detailed_videos = self._get_detailed_video_info(video_ids)

            if not detailed_videos:
                error_msg = "Failed to get detailed video information"
                self.logger.error(error_msg)
                errors.append({'error': error_msg, 'channel_id': channel_id})

                # Still save metadata
                metadata = {
                    'channel_id': channel_id,
                    'channel_url': url,
                    'grantee_name': grantee_name,
                    'total_videos_scraped': 0,
                    'engagement_metrics': self._calculate_engagement_metrics([]),
                    'videos': [],
                    'errors': errors
                }
                self.save_metadata(channel_output_path, metadata)

                return {
                    'success': False,
                    'posts_downloaded': 0,
                    'errors': errors,
                    'engagement_metrics': self._calculate_engagement_metrics([]),
                    'output_path': str(channel_output_path)
                }

            # Extract metadata
            videos_metadata = self._extract_video_metadata(detailed_videos)

            # Calculate engagement metrics
            # Use first video's channel info for subscriber count
            channel_info = detailed_videos[0] if detailed_videos else None
            engagement_metrics = self._calculate_engagement_metrics(
                videos_metadata,
                channel_info
            )

            # Prepare and save metadata
            metadata = {
                'channel_id': channel_id,
                'channel_url': url,
                'grantee_name': grantee_name,
                'total_videos_scraped': len(videos_metadata),
                'engagement_metrics': engagement_metrics,
                'videos': videos_metadata,
            }

            self.save_metadata(channel_output_path, metadata)

            # Also save errors if any
            if errors:
                self.save_errors(errors, channel_output_path)

            self.logger.info(
                f"Successfully scraped {len(videos_metadata)} videos from {channel_id}"
            )

            return {
                'success': True,
                'posts_downloaded': len(videos_metadata),
                'errors': errors,
                'engagement_metrics': engagement_metrics,
                'output_path': str(channel_output_path)
            }

        except Exception as e:
            error_msg = f"Error scraping YouTube channel: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            errors.append({'error': error_msg, 'exception': str(e)})

            # Try to save whatever we have
            try:
                if 'channel_output_path' in locals():
                    metadata = {
                        'channel_id': channel_id if 'channel_id' in locals() else 'unknown',
                        'channel_url': url,
                        'grantee_name': grantee_name,
                        'total_videos_scraped': len(videos_metadata),
                        'engagement_metrics': engagement_metrics or self._calculate_engagement_metrics([]),
                        'videos': videos_metadata,
                        'errors': errors
                    }
                    self.save_metadata(channel_output_path, metadata)
                    self.save_errors(errors, channel_output_path)
            except Exception as save_error:
                self.logger.error(f"Failed to save error metadata: {save_error}")

            return {
                'success': False,
                'posts_downloaded': len(videos_metadata),
                'errors': errors,
                'engagement_metrics': engagement_metrics or self._calculate_engagement_metrics([]),
                'output_path': str(channel_output_path) if 'channel_output_path' in locals() else ''
            }
