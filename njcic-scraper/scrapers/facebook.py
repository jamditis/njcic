"""
Facebook scraper using Playwright for browser automation.
Handles various Facebook URL formats and extracts posts with engagement metrics.
"""

import asyncio
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, unquote

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from .base import BaseScraper


class FacebookScraper(BaseScraper):
    """
    Facebook scraper implementation using Playwright.

    Note: Facebook is highly protective of scraping. This implementation uses
    best-effort strategies with graceful degradation for reliability.
    """

    platform_name = "facebook"

    def __init__(self, output_dir: Optional[Path] = None, headless: bool = True):
        """
        Initialize Facebook scraper.

        Args:
            output_dir: Directory to save scraped data (Path object or None for default)
            headless: Whether to run browser in headless mode
        """
        super().__init__(output_dir)
        self.headless = headless

        if not PLAYWRIGHT_AVAILABLE:
            self.logger.error(
                "Playwright not installed. Install with: pip install playwright && playwright install"
            )

    def extract_username(self, url: str) -> Optional[str]:
        """
        Extract username/identifier from Facebook URL.

        Handles formats:
        - facebook.com/pagename
        - facebook.com/pages/name/id
        - facebook.com/groups/groupname
        - fb.com/pagename
        - m.facebook.com/pagename
        - www.facebook.com/pagename

        Args:
            url: Facebook URL

        Returns:
            Username/identifier or None if invalid
        """
        try:
            # Clean and normalize URL
            url = url.strip()
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            parsed = urlparse(url)

            # Validate domain
            domain = parsed.netloc.lower()
            if not any(d in domain for d in ['facebook.com', 'fb.com']):
                self.logger.warning(f"Invalid Facebook domain: {domain}")
                return None

            # Extract path
            path = parsed.path.strip('/')
            if not path:
                return None

            # Remove query parameters and fragments
            path = path.split('?')[0].split('#')[0]

            # Handle different URL patterns
            parts = path.split('/')

            # Pattern: facebook.com/pages/name/id
            if len(parts) >= 3 and parts[0] == 'pages':
                # Use the page ID (last part) as identifier
                return parts[-1]

            # Pattern: facebook.com/groups/groupname
            if len(parts) >= 2 and parts[0] == 'groups':
                return f"group_{parts[1]}"

            # Pattern: facebook.com/profile.php?id=123
            if parts[0] == 'profile.php':
                # Try to extract ID from query string
                if 'id=' in url:
                    match = re.search(r'id=(\d+)', url)
                    if match:
                        return f"profile_{match.group(1)}"
                return None

            # Pattern: facebook.com/pagename or fb.com/pagename
            # Take the first part of the path as username
            username = parts[0]

            # Decode URL encoding
            username = unquote(username)

            # Validate username (basic check)
            if username and len(username) > 0 and username not in ['home', 'watch', 'marketplace', 'gaming']:
                return username

            return None

        except Exception as e:
            self.logger.error(f"Error extracting username from {url}: {e}")
            return None

    def _create_output_directory(self, grantee_name: str, username: str) -> Path:
        """
        Create and return Facebook-specific output directory.

        Creates structure: output/facebook/{grantee_name}/{username}

        Args:
            grantee_name: Name of the grantee
            username: Facebook username/page identifier

        Returns:
            Path object for the output directory
        """
        # Get base output path from parent class
        base_path = self.get_output_path(grantee_name)

        # Add username subdirectory
        username_path = base_path / username
        username_path.mkdir(exist_ok=True, parents=True)

        return username_path

    def scrape(self, url: str, grantee_name: str, max_posts: int = 25) -> Dict[str, Any]:
        """
        Scrape Facebook page/profile for posts and engagement metrics.

        Args:
            url: Facebook URL to scrape
            grantee_name: Name of the grantee
            max_posts: Maximum posts to scrape

        Returns:
            Dictionary with:
                - success (bool): Whether scraping succeeded
                - posts_downloaded (int): Number of posts downloaded
                - errors (List[str]): Error messages
                - engagement_metrics (Dict): Engagement statistics
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {
                'success': False,
                'posts_downloaded': 0,
                'errors': ['Playwright not installed'],
                'engagement_metrics': {}
            }

        # Extract username
        username = self.extract_username(url)
        if not username:
            return {
                'success': False,
                'posts_downloaded': 0,
                'errors': ['Could not extract username from URL'],
                'engagement_metrics': {}
            }

        self.logger.info(f"Starting Facebook scrape for {username}")

        # Run async scraping
        try:
            result = asyncio.run(self._scrape_async(url, username, grantee_name))
            return result
        except Exception as e:
            self.logger.error(f"Fatal error during scrape: {e}", exc_info=True)
            return {
                'success': False,
                'posts_downloaded': 0,
                'errors': [f'Fatal error: {str(e)}'],
                'engagement_metrics': {}
            }

    async def _scrape_async(self, url: str, username: str, grantee_name: str) -> Dict[str, Any]:
        """
        Async scraping implementation using Playwright.

        Args:
            url: Facebook URL
            username: Extracted username
            grantee_name: Grantee name

        Returns:
            Scraping results dictionary
        """
        errors = []
        posts = []
        engagement_metrics = {
            'followers_count': None,
            'total_reactions': 0,
            'total_comments': 0,
            'total_shares': 0,
            'avg_engagement_rate': 0.0
        }

        async with async_playwright() as p:
            try:
                # Launch browser
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox'
                    ]
                )

                # Create context with realistic settings
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='en-US',
                    timezone_id='America/New_York'
                )

                page = await context.new_page()

                # Navigate to page
                self.logger.info(f"Navigating to {url}")
                try:
                    await page.goto(url, wait_until='networkidle', timeout=30000)
                except PlaywrightTimeout:
                    self.logger.warning("Page load timeout, continuing anyway")
                    await page.wait_for_timeout(2000)

                # Wait for content to load
                await page.wait_for_timeout(3000)

                # Try to extract follower count
                followers_count = await self._extract_followers(page)
                if followers_count:
                    engagement_metrics['followers_count'] = followers_count
                    self.logger.info(f"Found {followers_count} followers/likes")

                # Scroll to load posts
                self.logger.info("Scrolling to load posts...")
                await self._scroll_page(page, max_scrolls=5)

                # Extract posts
                self.logger.info("Extracting posts...")
                posts = await self._extract_posts(page, max_posts=25)

                # Calculate engagement metrics
                if posts:
                    total_reactions = sum(p.get('reactions', 0) for p in posts)
                    total_comments = sum(p.get('comments', 0) for p in posts)
                    total_shares = sum(p.get('shares', 0) for p in posts)

                    engagement_metrics['total_reactions'] = total_reactions
                    engagement_metrics['total_comments'] = total_comments
                    engagement_metrics['total_shares'] = total_shares

                    # Calculate average engagement rate
                    total_engagement = total_reactions + total_comments + total_shares
                    if followers_count and followers_count > 0:
                        avg_engagement = (total_engagement / len(posts)) / followers_count * 100
                        engagement_metrics['avg_engagement_rate'] = round(avg_engagement, 2)

                    self.logger.info(f"Extracted {len(posts)} posts with {total_engagement} total engagements")

                # Save data
                output_dir = self._create_output_directory(grantee_name, username)

                # Save metadata
                metadata = {
                    'url': url,
                    'username': username,
                    'grantee_name': grantee_name,
                    'posts_count': len(posts),
                    'engagement_metrics': engagement_metrics,
                    'scraped_at': datetime.now().isoformat()
                }
                self.save_metadata(output_dir, metadata)

                # Save posts
                if posts:
                    posts_file = output_dir / "posts.json"
                    import json
                    with open(posts_file, 'w', encoding='utf-8') as f:
                        json.dump(posts, f, indent=2, ensure_ascii=False)
                    self.logger.info(f"Saved posts to {posts_file}")

                await browser.close()

                return {
                    'success': True,
                    'posts_downloaded': len(posts),
                    'errors': errors,
                    'engagement_metrics': engagement_metrics
                }

            except Exception as e:
                self.logger.error(f"Error during scraping: {e}", exc_info=True)
                errors.append(str(e))

                try:
                    await browser.close()
                except:
                    pass

                return {
                    'success': False,
                    'posts_downloaded': len(posts),
                    'errors': errors,
                    'engagement_metrics': engagement_metrics
                }

    async def _extract_followers(self, page) -> Optional[int]:
        """
        Extract follower/likes count from page.

        Args:
            page: Playwright page object

        Returns:
            Follower count or None
        """
        try:
            # Look for common follower count patterns
            selectors = [
                'text=/\\d+[KkMm]? followers?/i',
                'text=/\\d+[KkMm]? likes/i',
                'text=/\\d+[KkMm]? people like this/i',
                '[aria-label*="follower"]',
                '[aria-label*="like"]'
            ]

            for selector in selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=3000)
                    if element:
                        text = await element.inner_text()
                        # Extract number from text
                        match = re.search(r'([\d,]+)\s*([KkMm])?', text)
                        if match:
                            number = match.group(1).replace(',', '')
                            multiplier = match.group(2)

                            count = int(number)
                            if multiplier:
                                if multiplier.lower() == 'k':
                                    count *= 1000
                                elif multiplier.lower() == 'm':
                                    count *= 1000000

                            return count
                except:
                    continue

            return None

        except Exception as e:
            self.logger.debug(f"Could not extract follower count: {e}")
            return None

    async def _scroll_page(self, page, max_scrolls: int = 5, scroll_delay: float = 2.0):
        """
        Scroll page to load dynamic content.

        Args:
            page: Playwright page object
            max_scrolls: Maximum number of scrolls
            scroll_delay: Delay between scrolls in seconds
        """
        for i in range(max_scrolls):
            try:
                # Scroll to bottom
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')

                # Wait for content to load
                await page.wait_for_timeout(int(scroll_delay * 1000))

                self.logger.debug(f"Scroll {i+1}/{max_scrolls} completed")

            except Exception as e:
                self.logger.debug(f"Error during scroll {i+1}: {e}")
                break

    async def _extract_posts(self, page, max_posts: int = 25) -> List[Dict[str, Any]]:
        """
        Extract posts from page.

        Args:
            page: Playwright page object
            max_posts: Maximum number of posts to extract

        Returns:
            List of post dictionaries
        """
        posts = []

        try:
            # Common selectors for Facebook posts
            # Note: Facebook frequently changes their DOM structure, so we try multiple selectors
            post_selectors = [
                '[role="article"]',
                '[data-ad-preview="message"]',
                'div[data-pagelet*="FeedUnit"]',
                '.userContentWrapper'
            ]

            post_elements = []
            for selector in post_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        post_elements = elements
                        self.logger.debug(f"Found {len(elements)} posts using selector: {selector}")
                        break
                except:
                    continue

            if not post_elements:
                self.logger.warning("Could not find any posts on the page")
                return posts

            # Limit to max_posts
            post_elements = post_elements[:max_posts]

            # Extract data from each post
            for idx, element in enumerate(post_elements):
                try:
                    post_data = await self._extract_post_data(element, idx)
                    if post_data:
                        posts.append(post_data)

                    if len(posts) >= max_posts:
                        break

                except Exception as e:
                    self.logger.debug(f"Error extracting post {idx}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error extracting posts: {e}")

        return posts

    async def _extract_post_data(self, element, index: int) -> Optional[Dict[str, Any]]:
        """
        Extract data from a single post element.

        Args:
            element: Playwright element for the post
            index: Post index

        Returns:
            Post data dictionary or None
        """
        try:
            post_data = {
                'id': f'post_{index}',
                'text': '',
                'date': None,
                'reactions': 0,
                'comments': 0,
                'shares': 0,
                'url': None
            }

            # Extract post text
            try:
                # Try multiple selectors for post content
                text_selectors = [
                    '[data-ad-preview="message"]',
                    '[data-ad-comet-preview="message"]',
                    '.userContent',
                    'div[dir="auto"]'
                ]

                for selector in text_selectors:
                    text_elem = await element.query_selector(selector)
                    if text_elem:
                        text = await text_elem.inner_text()
                        if text and len(text.strip()) > 0:
                            post_data['text'] = text.strip()
                            break

                # If still no text, get all text content (may include extra info)
                if not post_data['text']:
                    text = await element.inner_text()
                    # Take first 500 chars to avoid getting too much extra content
                    post_data['text'] = text[:500].strip()

            except Exception as e:
                self.logger.debug(f"Could not extract post text: {e}")

            # Extract date/timestamp
            try:
                time_selectors = [
                    'abbr',
                    'a[href*="/posts/"]',
                    'a[href*="/permalink/"]',
                    'span[id^="jsc"]'
                ]

                for selector in time_selectors:
                    time_elem = await element.query_selector(selector)
                    if time_elem:
                        # Try to get timestamp from various attributes
                        for attr in ['data-utime', 'data-timestamp', 'title']:
                            timestamp = await time_elem.get_attribute(attr)
                            if timestamp:
                                try:
                                    # Try to parse as unix timestamp
                                    if timestamp.isdigit():
                                        dt = datetime.fromtimestamp(int(timestamp))
                                        post_data['date'] = dt.isoformat()
                                        break
                                except:
                                    pass

                        # If still no date, try to get text content
                        if not post_data['date']:
                            time_text = await time_elem.inner_text()
                            if time_text:
                                post_data['date'] = time_text.strip()
                                break

            except Exception as e:
                self.logger.debug(f"Could not extract post date: {e}")

            # Extract engagement metrics
            try:
                # Get all text from element to find engagement numbers
                full_text = await element.inner_text()

                # Look for reactions (likes, love, etc.)
                reaction_patterns = [
                    r'(\d+)\s+reactions?',
                    r'(\d+)\s+likes?',
                    r'(\d[\d,]*)\s+(?:others?|people)\s+(?:reacted|like)',
                ]

                for pattern in reaction_patterns:
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        post_data['reactions'] = int(match.group(1).replace(',', ''))
                        break

                # Look for comments
                comment_patterns = [
                    r'(\d[\d,]*)\s+comments?',
                    r'(\d[\d,]*)\s+comment',
                ]

                for pattern in comment_patterns:
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        post_data['comments'] = int(match.group(1).replace(',', ''))
                        break

                # Look for shares
                share_patterns = [
                    r'(\d[\d,]*)\s+shares?',
                    r'(\d[\d,]*)\s+share',
                ]

                for pattern in share_patterns:
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        post_data['shares'] = int(match.group(1).replace(',', ''))
                        break

            except Exception as e:
                self.logger.debug(f"Could not extract engagement metrics: {e}")

            # Try to extract post URL
            try:
                link_elem = await element.query_selector('a[href*="/posts/"], a[href*="/permalink/"]')
                if link_elem:
                    href = await link_elem.get_attribute('href')
                    if href:
                        # Make absolute URL
                        if href.startswith('/'):
                            href = 'https://www.facebook.com' + href
                        post_data['url'] = href
            except Exception as e:
                self.logger.debug(f"Could not extract post URL: {e}")

            # Only return post if we extracted at least some content
            if post_data['text'] or post_data['reactions'] > 0 or post_data['comments'] > 0:
                return post_data

            return None

        except Exception as e:
            self.logger.debug(f"Error extracting post data: {e}")
            return None
