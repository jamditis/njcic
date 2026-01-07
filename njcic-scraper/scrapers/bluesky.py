"""
BlueSky scraper using the AT Protocol public API.
"""
import re
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from scrapers.base import BaseScraper
import config


class BlueSkyScraper(BaseScraper):
    """Scraper for BlueSky social media platform using AT Protocol."""

    platform_name = "bluesky"

    # Public API endpoints
    API_BASE = "https://public.api.bsky.app/xrpc"
    FEED_ENDPOINT = f"{API_BASE}/app.bsky.feed.getAuthorFeed"
    PROFILE_ENDPOINT = f"{API_BASE}/app.bsky.actor.getProfile"

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize BlueSky scraper.

        Args:
            output_dir: Directory to save scraped data
        """
        super().__init__(output_dir)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.USER_AGENT,
            'Accept': 'application/json'
        })

    def extract_username(self, url: str) -> Optional[str]:
        """
        Extract username/handle from BlueSky URL.

        Supports formats:
        - https://bsky.app/profile/username.bsky.social
        - https://bsky.app/profile/custom.domain
        - Direct handles: username.bsky.social

        Args:
            url: BlueSky profile URL or handle

        Returns:
            Username/handle (e.g., 'username.bsky.social') or None if invalid
        """
        try:
            # If it's already a handle (contains a dot but no protocol)
            if '.' in url and '://' not in url:
                return url.strip()

            # Parse URL
            parsed = urlparse(url)
            path = parsed.path

            # Match /profile/handle pattern
            match = re.match(r'^/profile/([^/]+)/?$', path)
            if match:
                handle = match.group(1)
                return handle

            self.logger.error(f"Could not extract handle from URL path: {path}")
            return None

        except Exception as e:
            self.logger.error(f"Invalid BlueSky URL format: {url}. Error: {str(e)}")
            return None

    def _fetch_profile(self, handle: str) -> Optional[Dict[str, Any]]:
        """
        Fetch user profile information.

        Args:
            handle: BlueSky handle

        Returns:
            Profile data or None if failed
        """
        try:
            self.rate_limit()
            params = {'actor': handle}
            response = self.session.get(
                self.PROFILE_ENDPOINT,
                params=params,
                timeout=config.TIMEOUT
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch profile for {handle}: {str(e)}")
            return None

    def _fetch_posts(self, handle: str, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Fetch posts from user's feed.

        Args:
            handle: BlueSky handle
            limit: Maximum number of posts to fetch

        Returns:
            List of post data dictionaries
        """
        posts = []
        cursor = None
        fetched = 0

        try:
            while fetched < limit:
                self.rate_limit()

                params = {
                    'actor': handle,
                    'limit': min(100, limit - fetched)  # API max is 100 per request
                }
                if cursor:
                    params['cursor'] = cursor

                response = self.session.get(
                    self.FEED_ENDPOINT,
                    params=params,
                    timeout=config.TIMEOUT
                )
                response.raise_for_status()
                data = response.json()

                feed_items = data.get('feed', [])
                if not feed_items:
                    break

                posts.extend(feed_items)
                fetched += len(feed_items)

                # Check if there's more data
                cursor = data.get('cursor')
                if not cursor or fetched >= limit:
                    break

            # Limit to requested number
            return posts[:limit]

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch posts for {handle}: {str(e)}")
            return posts

    def _extract_post_data(self, feed_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant data from a feed item.

        Args:
            feed_item: Raw feed item from API

        Returns:
            Processed post data
        """
        post = feed_item.get('post', {})
        record = post.get('record', {})
        author = post.get('author', {})

        # Extract engagement metrics
        likes = post.get('likeCount', 0)
        reposts = post.get('repostCount', 0)
        replies = post.get('replyCount', 0)

        # Extract post content
        text = record.get('text', '')
        created_at = record.get('createdAt', '')

        # Parse created_at to more readable format
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            formatted_date = dt.strftime('%Y-%m-%d %H:%M:%S')
            timestamp = created_at
        except (ValueError, AttributeError):
            formatted_date = created_at
            timestamp = created_at

        # Extract media/embed info if present
        embed = record.get('embed')
        has_media = embed is not None
        embed_type = embed.get('$type') if embed else None

        # Get post URI and create web URL
        uri = post.get('uri', '')
        # Extract post ID from URI (format: at://did:plc:xxx/app.bsky.feed.post/postid)
        post_id = uri.split('/')[-1] if uri else ''
        handle = author.get('handle', '')
        post_url = f"https://bsky.app/profile/{handle}/post/{post_id}" if handle and post_id else ''

        return {
            'post_id': post_id,
            'text': text,
            'timestamp': timestamp,
            'author': author.get('handle', ''),
            'platform': self.platform_name,
            'url': post_url,
            'formatted_date': formatted_date,
            'likes': likes,
            'shares': reposts,  # Map to standard 'shares' field
            'comments': replies,  # Map to standard 'comments' field
            'reposts': reposts,  # Keep original for BlueSky-specific data
            'replies': replies,  # Keep original for BlueSky-specific data
            'total_engagement': likes + reposts + replies,
            'has_media': has_media,
            'embed_type': embed_type,
            'author_info': {
                'did': author.get('did', ''),
                'handle': author.get('handle', ''),
                'display_name': author.get('displayName', ''),
                'avatar': author.get('avatar', '')
            },
            'uri': uri,
            'cid': post.get('cid', '')
        }

    def _calculate_engagement_metrics(
        self,
        posts: List[Dict[str, Any]],
        profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate aggregate engagement metrics.

        Args:
            posts: List of processed post data
            profile: User profile data

        Returns:
            Dictionary of engagement metrics
        """
        if not posts:
            return {
                'followers_count': profile.get('followersCount', 0) if profile else 0,
                'total_likes': 0,
                'total_reposts': 0,
                'total_replies': 0,
                'avg_engagement_rate': 0.0,
                'posts_analyzed': 0
            }

        total_likes = sum(post.get('likes', 0) for post in posts)
        total_reposts = sum(post.get('reposts', 0) for post in posts)
        total_replies = sum(post.get('replies', 0) for post in posts)
        total_engagement = total_likes + total_reposts + total_replies
        posts_count = len(posts)

        followers = profile.get('followersCount', 0) if profile else 0

        # Calculate engagement rate
        # Engagement rate = (total engagement / (posts * followers)) * 100
        # If followers is 0, use total engagement per post as proxy
        if followers > 0 and posts_count > 0:
            avg_engagement_rate = (total_engagement / (posts_count * followers)) * 100
        else:
            avg_engagement_rate = total_engagement / posts_count if posts_count > 0 else 0

        return {
            'followers_count': followers,
            'following_count': profile.get('followsCount', 0) if profile else 0,
            'posts_count': profile.get('postsCount', 0) if profile else 0,
            'total_likes': total_likes,
            'total_reposts': total_reposts,
            'total_replies': total_replies,
            'total_engagement': total_engagement,
            'avg_engagement_rate': round(avg_engagement_rate, 4),
            'avg_likes_per_post': round(total_likes / posts_count, 2) if posts_count > 0 else 0,
            'avg_reposts_per_post': round(total_reposts / posts_count, 2) if posts_count > 0 else 0,
            'avg_replies_per_post': round(total_replies / posts_count, 2) if posts_count > 0 else 0,
            'avg_total_engagement_per_post': round(total_engagement / posts_count, 2) if posts_count > 0 else 0,
            'posts_analyzed': posts_count
        }

    def scrape(
        self,
        url: str,
        grantee_name: str,
        max_posts: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Scrape BlueSky profile data.

        Args:
            url: BlueSky profile URL or handle
            grantee_name: Name of the grantee
            max_posts: Maximum number of posts to scrape (defaults to config.MAX_POSTS_PER_ACCOUNT)

        Returns:
            Dictionary with:
                - success: bool
                - posts_downloaded: int
                - errors: list
                - engagement_metrics: dict
                - output_path: str
        """
        errors = []
        posts_data = []
        profile_data = None

        # Use config default if max_posts not specified
        limit = max_posts or config.MAX_POSTS_PER_ACCOUNT

        try:
            # Extract handle from URL
            self.logger.info(f"Extracting handle from URL: {url}")
            handle = self.extract_username(url)
            if not handle:
                error_msg = f"Failed to extract handle from URL: {url}"
                errors.append({'error': error_msg, 'timestamp': datetime.now().isoformat()})
                return {
                    'success': False,
                    'posts_downloaded': 0,
                    'errors': errors,
                    'engagement_metrics': {},
                    'output_path': ''
                }

            self.logger.info(f"Extracted handle: {handle}")

            # Fetch profile
            self.logger.info(f"Fetching profile for: {handle}")
            profile_data = self._fetch_profile(handle)
            if not profile_data:
                errors.append({
                    'error': f"Failed to fetch profile for {handle}",
                    'timestamp': datetime.now().isoformat()
                })

            # Fetch posts
            self.logger.info(f"Fetching posts for: {handle}")
            raw_posts = self._fetch_posts(handle, limit=limit)
            self.logger.info(f"Fetched {len(raw_posts)} posts")

            # Process posts
            for feed_item in raw_posts:
                try:
                    post_data = self._extract_post_data(feed_item)

                    # Validate post if validation is enabled
                    if self.validate_post(post_data):
                        posts_data.append(post_data)
                    else:
                        errors.append({
                            'error': 'Post failed validation',
                            'post_id': post_data.get('post_id', 'unknown'),
                            'timestamp': datetime.now().isoformat()
                        })

                except Exception as e:
                    error_msg = f"Error processing post: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append({
                        'error': error_msg,
                        'timestamp': datetime.now().isoformat()
                    })

            # Calculate engagement metrics
            engagement_metrics = self._calculate_engagement_metrics(posts_data, profile_data)

            # Get output path
            output_path = self.get_output_path(grantee_name)

            # Save posts
            if posts_data:
                self.save_posts(posts_data, output_path)

            # Prepare metadata
            metadata = {
                'grantee_name': grantee_name,
                'profile_url': url,
                'handle': handle,
                'profile': profile_data,
                'engagement_metrics': engagement_metrics,
                'posts_count': len(posts_data),
                'errors_count': len(errors)
            }

            # Save metadata
            self.save_metadata(output_path, metadata)

            # Save errors if any
            if errors:
                self.save_errors(errors, output_path)

            self.logger.info(
                f"Scraping completed for {handle}: "
                f"{len(posts_data)} posts, {len(errors)} errors"
            )

            return {
                'success': len(posts_data) > 0 or profile_data is not None,
                'posts_downloaded': len(posts_data),
                'errors': errors,
                'engagement_metrics': engagement_metrics,
                'output_path': str(output_path)
            }

        except Exception as e:
            error_msg = f"Unexpected error during scraping: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            errors.append({
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            })

            # Try to save what we have
            if posts_data or profile_data:
                try:
                    output_path = self.get_output_path(grantee_name)
                    if posts_data:
                        self.save_posts(posts_data, output_path)
                    if errors:
                        self.save_errors(errors, output_path)
                except Exception as save_error:
                    self.logger.error(f"Failed to save data after error: {save_error}")

            return {
                'success': False,
                'posts_downloaded': len(posts_data),
                'errors': errors,
                'engagement_metrics': self._calculate_engagement_metrics(posts_data, profile_data),
                'output_path': str(output_path) if 'output_path' in locals() else ''
            }
