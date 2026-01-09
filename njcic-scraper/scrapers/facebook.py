"""
Facebook scraper using Playwright for browser automation.
Handles various Facebook URL formats and extracts posts with engagement metrics.

Enhanced with anti-detection measures and robust error handling.
"""

import asyncio
import json
import random
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

    def __init__(self, output_dir: Optional[Path] = None, headless: bool = True, max_retries: int = 3):
        """
        Initialize Facebook scraper.

        Args:
            output_dir: Directory to save scraped data (Path object or None for default)
            headless: Whether to run browser in headless mode
            max_retries: Maximum number of retry attempts on failure
        """
        super().__init__(output_dir)
        self.headless = headless
        self.max_retries = max_retries
        self.cookies_file = Path("output/facebook_cookies.json")

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

    async def _random_delay(self, min_ms: int = 500, max_ms: int = 2000):
        """Add random delay to simulate human behavior."""
        delay = random.randint(min_ms, max_ms)
        await asyncio.sleep(delay / 1000)

    async def _human_like_mouse_movement(self, page):
        """Simulate human-like mouse movements."""
        try:
            # Move mouse to random positions
            for _ in range(random.randint(2, 4)):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                await page.mouse.move(x, y)
                await self._random_delay(100, 300)
        except Exception as e:
            self.logger.debug(f"Mouse movement error: {e}")

    async def _save_cookies(self, context):
        """Save cookies for session persistence."""
        try:
            cookies = await context.cookies()
            self.cookies_file.parent.mkdir(exist_ok=True, parents=True)
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f)
            self.logger.debug(f"Saved {len(cookies)} cookies")
        except Exception as e:
            self.logger.debug(f"Could not save cookies: {e}")

    async def _load_cookies(self, context):
        """Load cookies for session persistence."""
        try:
            if self.cookies_file.exists():
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                await context.add_cookies(cookies)
                self.logger.debug(f"Loaded {len(cookies)} cookies")
                return True
        except Exception as e:
            self.logger.debug(f"Could not load cookies: {e}")
        return False

    async def _detect_blocks(self, page) -> bool:
        """
        Detect if the page is blocked by Facebook.

        Returns:
            True if blocked, False otherwise
        """
        try:
            content = await page.content()
            text = await page.evaluate('() => document.body.innerText')

            # Check for common block indicators
            block_indicators = [
                'checkpoint',
                'captcha',
                'verify your identity',
                'confirm your identity',
                'unusual activity',
                'temporarily blocked',
                'security check',
                'try again later'
            ]

            text_lower = text.lower()
            for indicator in block_indicators:
                if indicator in text_lower:
                    self.logger.warning(f"Detected block indicator: {indicator}")
                    return True

            # Check for redirect to login
            current_url = page.url
            if 'login' in current_url or 'checkpoint' in current_url:
                self.logger.warning(f"Redirected to login/checkpoint: {current_url}")
                return True

        except Exception as e:
            self.logger.debug(f"Error detecting blocks: {e}")

        return False

    async def _handle_login_wall(self, page) -> bool:
        """
        Try to handle login wall without authentication.

        Returns:
            True if handled successfully, False otherwise
        """
        try:
            # Look for "Not Now" or "Close" buttons
            close_selectors = [
                'button[aria-label*="Close"]',
                'button[aria-label*="Not Now"]',
                'button:has-text("Not Now")',
                'button:has-text("Close")',
                '[role="button"]:has-text("Not Now")',
                'div[aria-label*="Close"]'
            ]

            for selector in close_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=2000)
                    if element:
                        await element.click()
                        self.logger.info("Closed login wall")
                        await self._random_delay(1000, 2000)
                        return True
                except:
                    continue

        except Exception as e:
            self.logger.debug(f"Could not handle login wall: {e}")

        return False

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

        # Run async scraping with retry logic
        last_error = None
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    # Exponential backoff
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    self.logger.info(f"Retry attempt {attempt + 1}/{self.max_retries} after {wait_time:.1f}s")
                    time.sleep(wait_time)

                result = asyncio.run(self._scrape_async(url, username, grantee_name, max_posts))

                # If successful or partially successful, return result
                if result['success'] or result['posts_downloaded'] > 0:
                    return result

                last_error = result.get('errors', ['Unknown error'])

            except Exception as e:
                last_error = [f'Fatal error: {str(e)}']
                self.logger.error(f"Error during scrape attempt {attempt + 1}: {e}", exc_info=True)

        # All retries failed
        self.logger.error(f"All {self.max_retries} retry attempts failed")
        return {
            'success': False,
            'posts_downloaded': 0,
            'errors': last_error if last_error else ['All retry attempts failed'],
            'engagement_metrics': {}
        }

    async def _scrape_async(self, url: str, username: str, grantee_name: str, max_posts: int = 25) -> Dict[str, Any]:
        """
        Async scraping implementation using Playwright.

        Args:
            url: Facebook URL
            username: Extracted username
            grantee_name: Grantee name
            max_posts: Maximum posts to scrape

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
                # Launch browser with enhanced stealth settings
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--disable-site-isolation-trials'
                    ]
                )

                # Randomize user agent slightly to avoid fingerprinting
                user_agents = [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
                ]

                # Create context with realistic settings
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=random.choice(user_agents),
                    locale='en-US',
                    timezone_id='America/New_York',
                    permissions=['geolocation']
                )

                # Load cookies if available
                await self._load_cookies(context)

                page = await context.new_page()

                # Add stealth JavaScript to hide automation
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });
                    window.chrome = {
                        runtime: {}
                    };
                """)

                # Navigate to page
                self.logger.info(f"Navigating to {url}")
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    await self._random_delay(2000, 4000)
                except PlaywrightTimeout:
                    self.logger.warning("Page load timeout, continuing anyway")
                    await self._random_delay(1000, 2000)

                # Simulate human-like mouse movement
                await self._human_like_mouse_movement(page)

                # Check for blocks or captcha
                if await self._detect_blocks(page):
                    errors.append("Page appears to be blocked or requires verification")
                    await self._save_cookies(context)
                    await browser.close()
                    return {
                        'success': False,
                        'posts_downloaded': 0,
                        'errors': errors,
                        'engagement_metrics': engagement_metrics
                    }

                # Try to handle login wall
                await self._handle_login_wall(page)
                await self._random_delay(1000, 2000)

                # Try to extract follower count
                followers_count = await self._extract_followers(page)
                if followers_count:
                    engagement_metrics['followers_count'] = followers_count
                    self.logger.info(f"Found {followers_count} followers/likes")

                # Scroll to load posts with human-like behavior
                self.logger.info("Scrolling to load posts...")
                await self._scroll_page_realistic(page, max_scrolls=5)

                # Extract posts
                self.logger.info("Extracting posts...")
                posts = await self._extract_posts(page, max_posts=max_posts)

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
                    with open(posts_file, 'w', encoding='utf-8') as f:
                        json.dump(posts, f, indent=2, ensure_ascii=False)
                    self.logger.info(f"Saved posts to {posts_file}")

                # Save cookies for future use
                await self._save_cookies(context)

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
        Extract follower/likes count from page with multiple fallback strategies.

        Args:
            page: Playwright page object

        Returns:
            Follower count or None
        """
        try:
            # Strategy 1: Look for text patterns in the page
            page_text = await page.evaluate('() => document.body.innerText')

            # Common patterns for follower/like counts
            patterns = [
                r'([\d,]+(?:\.\d+)?)\s*([KkMm])?\s+followers?',
                r'([\d,]+(?:\.\d+)?)\s*([KkMm])?\s+people follow this',
                r'([\d,]+(?:\.\d+)?)\s*([KkMm])?\s+likes?',
                r'([\d,]+(?:\.\d+)?)\s*([KkMm])?\s+people like this',
                r'Followers\s+([\d,]+(?:\.\d+)?)\s*([KkMm])?',
                r'Likes\s+([\d,]+(?:\.\d+)?)\s*([KkMm])?',
            ]

            for pattern in patterns:
                matches = re.finditer(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    try:
                        number_str = match.group(1).replace(',', '')
                        multiplier = match.group(2) if len(match.groups()) > 1 else None

                        # Handle decimal numbers (e.g., "1.2K")
                        count = float(number_str)

                        if multiplier:
                            if multiplier.lower() == 'k':
                                count *= 1000
                            elif multiplier.lower() == 'm':
                                count *= 1000000

                        return int(count)
                    except (ValueError, AttributeError):
                        continue

            # Strategy 2: Look for specific selectors
            selectors = [
                '[aria-label*="follower"]',
                '[aria-label*="like"]',
                'a[href*="followers"]',
                'a[href*="likes"]'
            ]

            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        text = await element.inner_text()
                        # Try to extract number
                        match = re.search(r'([\d,]+(?:\.\d+)?)\s*([KkMm])?', text)
                        if match:
                            number_str = match.group(1).replace(',', '')
                            multiplier = match.group(2)

                            count = float(number_str)
                            if multiplier:
                                if multiplier.lower() == 'k':
                                    count *= 1000
                                elif multiplier.lower() == 'm':
                                    count *= 1000000

                            return int(count)
                except:
                    continue

            return None

        except Exception as e:
            self.logger.debug(f"Could not extract follower count: {e}")
            return None

    async def _scroll_page(self, page, max_scrolls: int = 5, scroll_delay: float = 2.0):
        """
        Scroll page to load dynamic content (simple version).

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

    async def _scroll_page_realistic(self, page, max_scrolls: int = 5):
        """
        Scroll page with human-like behavior to load dynamic content.

        Args:
            page: Playwright page object
            max_scrolls: Maximum number of scrolls
        """
        for i in range(max_scrolls):
            try:
                # Get current scroll position
                prev_height = await page.evaluate('document.body.scrollHeight')

                # Scroll in multiple smaller increments (more human-like)
                scroll_distance = random.randint(400, 800)
                for _ in range(3):
                    await page.evaluate(f'window.scrollBy(0, {scroll_distance})')
                    await self._random_delay(200, 500)

                # Random chance to scroll back up a bit (like reading)
                if random.random() < 0.3:
                    await page.evaluate(f'window.scrollBy(0, -{random.randint(100, 300)})')
                    await self._random_delay(300, 600)

                # Wait for new content to load with random delay
                await self._random_delay(1500, 3000)

                # Check if new content loaded
                new_height = await page.evaluate('document.body.scrollHeight')
                if new_height == prev_height:
                    self.logger.debug(f"No new content after scroll {i+1}, stopping")
                    break

                self.logger.debug(f"Scroll {i+1}/{max_scrolls} completed")

            except Exception as e:
                self.logger.debug(f"Error during scroll {i+1}: {e}")
                break

    async def _extract_posts(self, page, max_posts: int = 25) -> List[Dict[str, Any]]:
        """
        Extract posts from page with multiple fallback strategies.

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
                'div[data-pagelet*="ProfileTimeline"]',
                '.userContentWrapper',
                'div.story_body_container',
                '[data-testid="story-subtitle"]'
            ]

            post_elements = []
            used_selector = None
            for selector in post_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        # Filter out empty or invalid elements
                        valid_elements = []
                        for elem in elements:
                            try:
                                # Check if element has meaningful content
                                text = await elem.inner_text()
                                if text and len(text.strip()) > 10:
                                    valid_elements.append(elem)
                            except:
                                continue

                        if valid_elements:
                            post_elements = valid_elements
                            used_selector = selector
                            self.logger.debug(f"Found {len(valid_elements)} valid posts using selector: {selector}")
                            break
                except Exception as e:
                    self.logger.debug(f"Error with selector {selector}: {e}")
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

            self.logger.info(f"Successfully extracted {len(posts)} posts")

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

            # Extract engagement metrics with multiple strategies
            try:
                # Get all text from element to find engagement numbers
                full_text = await element.inner_text()

                # Strategy 1: Look for reactions (likes, love, etc.)
                reaction_patterns = [
                    r'(\d[\d,]*)\s+reactions?',
                    r'(\d[\d,]*)\s+likes?',
                    r'(\d[\d,]*)\s+(?:others?|people)\s+(?:reacted|like)',
                    r'(\d[\d,]*)\s+All\s+reactions?',
                    r'Like:\s*(\d[\d,]*)',
                    r'(\d[\d,]*)\s+(?:👍|❤|😆|😮|😢|😡)',  # Emoji reactions
                ]

                for pattern in reaction_patterns:
                    matches = re.finditer(pattern, full_text, re.IGNORECASE)
                    for match in matches:
                        try:
                            count = int(match.group(1).replace(',', ''))
                            # Only update if we found a larger number (more specific)
                            if count > post_data['reactions']:
                                post_data['reactions'] = count
                        except (ValueError, IndexError):
                            continue

                # Strategy 2: Look for comments
                comment_patterns = [
                    r'(\d[\d,]*)\s+comments?',
                    r'(\d[\d,]*)\s+comment\s',
                    r'Comment:\s*(\d[\d,]*)',
                    r'View\s+(\d[\d,]*)\s+comments?',
                    r'See\s+all\s+(\d[\d,]*)\s+comments?',
                ]

                for pattern in comment_patterns:
                    matches = re.finditer(pattern, full_text, re.IGNORECASE)
                    for match in matches:
                        try:
                            count = int(match.group(1).replace(',', ''))
                            if count > post_data['comments']:
                                post_data['comments'] = count
                        except (ValueError, IndexError):
                            continue

                # Strategy 3: Look for shares
                share_patterns = [
                    r'(\d[\d,]*)\s+shares?',
                    r'(\d[\d,]*)\s+share\s',
                    r'Share:\s*(\d[\d,]*)',
                    r'Shared\s+(\d[\d,]*)\s+times?',
                ]

                for pattern in share_patterns:
                    matches = re.finditer(pattern, full_text, re.IGNORECASE)
                    for match in matches:
                        try:
                            count = int(match.group(1).replace(',', ''))
                            if count > post_data['shares']:
                                post_data['shares'] = count
                        except (ValueError, IndexError):
                            continue

                # Strategy 4: Look for engagement in aria-labels and specific elements
                try:
                    engagement_elements = await element.query_selector_all('[aria-label*="reaction"], [aria-label*="comment"], [aria-label*="share"]')
                    for eng_elem in engagement_elements:
                        aria_label = await eng_elem.get_attribute('aria-label')
                        if aria_label:
                            # Extract numbers from aria-label
                            numbers = re.findall(r'(\d[\d,]*)', aria_label)
                            for num_str in numbers:
                                try:
                                    count = int(num_str.replace(',', ''))
                                    # Heuristic: assign based on aria-label content
                                    aria_lower = aria_label.lower()
                                    if 'reaction' in aria_lower or 'like' in aria_lower:
                                        if count > post_data['reactions']:
                                            post_data['reactions'] = count
                                    elif 'comment' in aria_lower:
                                        if count > post_data['comments']:
                                            post_data['comments'] = count
                                    elif 'share' in aria_lower:
                                        if count > post_data['shares']:
                                            post_data['shares'] = count
                                except (ValueError, AttributeError):
                                    continue
                except Exception as e:
                    self.logger.debug(f"Could not extract from aria-labels: {e}")

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
