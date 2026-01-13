"""
Instagram scraper using Playwright for browser automation.
No login required - scrapes public profile data only.
"""

import asyncio
import json
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from .base import BaseScraper


class InstagramPlaywrightScraper(BaseScraper):
    """
    Instagram scraper implementation using Playwright.
    Scrapes public profiles without requiring login credentials.
    """

    platform_name = "instagram"

    def __init__(self, output_dir: Optional[Path] = None, headless: bool = True, max_retries: int = 3):
        """
        Initialize Instagram Playwright scraper.

        Args:
            output_dir: Directory to save scraped data
            headless: Whether to run browser in headless mode
            max_retries: Maximum number of retry attempts on failure
        """
        super().__init__(output_dir)
        self.headless = headless
        self.max_retries = max_retries
        self.cookies_file = Path("output/instagram_cookies.json")

        if not PLAYWRIGHT_AVAILABLE:
            self.logger.error(
                "Playwright not installed. Install with: pip install playwright && playwright install"
            )

    def extract_username(self, url: str) -> Optional[str]:
        """
        Extract username from Instagram URL.

        Handles formats:
        - instagram.com/username
        - instagram.com/username/
        - https://www.instagram.com/username

        Args:
            url: Instagram URL

        Returns:
            Extracted username or None if invalid
        """
        url = url.lower().strip()
        if not url:
            return None

        url = re.sub(r'^https?://', '', url)
        url = re.sub(r'^www\.', '', url)

        pattern = r'^instagram\.com/([a-zA-Z0-9._]+)/?.*$'
        match = re.match(pattern, url)

        if match:
            username = match.group(1)
            if username not in ['p', 'reel', 'reels', 'tv', 'stories', 'explore']:
                return username

        if '/' not in url and '.' not in url and url:
            return url

        return None

    def _create_output_directory(self, grantee_name: str, username: str) -> Path:
        """Create and return Instagram-specific output directory."""
        base_path = self.get_output_path(grantee_name)
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

    async def _handle_login_wall(self, page) -> bool:
        """Try to dismiss login popup without authenticating."""
        try:
            # First try pressing Escape multiple times
            for _ in range(3):
                try:
                    await page.keyboard.press('Escape')
                    await self._random_delay(300, 500)
                except:
                    pass

            # Try clicking outside the modal
            try:
                await page.mouse.click(10, 10)
                await self._random_delay(300, 500)
            except:
                pass

            close_selectors = [
                'svg[aria-label="Close"]',
                'button[aria-label*="Close"]',
                '[role="button"][aria-label*="Close"]',
                'button:has-text("Not Now")',
                '[role="button"]:has-text("Not Now")',
                'div[role="dialog"] button',
            ]

            for selector in close_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=1500)
                    if element:
                        await element.click()
                        self.logger.info(f"Closed login popup using: {selector}")
                        await self._random_delay(500, 1000)
                        return True
                except:
                    continue

            # Try clicking somewhere to dismiss overlay
            try:
                await page.evaluate('document.querySelector("div[role=\\"dialog\\"]")?.remove()')
                self.logger.info("Removed dialog via JavaScript")
            except:
                pass

        except Exception as e:
            self.logger.debug(f"Could not handle login wall: {e}")

        return False

    def scrape(self, url: str, grantee_name: str, max_posts: int = 25) -> Dict[str, Any]:
        """
        Scrape Instagram profile for posts and engagement metrics.

        Args:
            url: Instagram URL to scrape
            grantee_name: Name of the grantee
            max_posts: Maximum posts to scrape

        Returns:
            Dictionary with scraping results
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {
                'success': False,
                'posts_downloaded': 0,
                'errors': ['Playwright not installed'],
                'engagement_metrics': {}
            }

        username = self.extract_username(url)
        if not username:
            return {
                'success': False,
                'posts_downloaded': 0,
                'errors': ['Could not extract username from URL'],
                'engagement_metrics': {}
            }

        self.logger.info(f"Starting Instagram Playwright scrape for @{username}")

        last_error = None
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    self.logger.info(f"Retry attempt {attempt + 1}/{self.max_retries} after {wait_time:.1f}s")
                    time.sleep(wait_time)

                result = asyncio.run(self._scrape_async(url, username, grantee_name, max_posts))

                if result['success'] or result['posts_downloaded'] > 0:
                    return result

                last_error = result.get('errors', ['Unknown error'])

            except Exception as e:
                last_error = [f'Fatal error: {str(e)}']
                self.logger.error(f"Error during scrape attempt {attempt + 1}: {e}", exc_info=True)

        self.logger.error(f"All {self.max_retries} retry attempts failed")
        return {
            'success': False,
            'posts_downloaded': 0,
            'errors': last_error if last_error else ['All retry attempts failed'],
            'engagement_metrics': {}
        }

    async def _scrape_async(self, url: str, username: str, grantee_name: str, max_posts: int = 25) -> Dict[str, Any]:
        """Async scraping implementation using Playwright."""
        errors = []
        posts = []
        engagement_metrics = {
            'followers_count': 0,
            'following_count': 0,
            'posts_count': 0,
            'total_likes': 0,
            'total_comments': 0,
            'avg_engagement_rate': 0.0
        }

        async with async_playwright() as p:
            try:
                # Launch browser with stealth settings
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process',
                    ]
                )

                user_agents = [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                ]

                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=random.choice(user_agents),
                    locale='en-US',
                    timezone_id='America/New_York',
                )

                await self._load_cookies(context)

                page = await context.new_page()

                # Add stealth JavaScript
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                    window.chrome = { runtime: {} };
                """)

                # Navigate to profile
                profile_url = f"https://www.instagram.com/{username}/"
                self.logger.info(f"Navigating to {profile_url}")

                try:
                    await page.goto(profile_url, wait_until='domcontentloaded', timeout=30000)
                    await self._random_delay(2000, 4000)
                except PlaywrightTimeout:
                    self.logger.warning("Page load timeout, continuing anyway")
                    await self._random_delay(1000, 2000)

                await self._human_like_mouse_movement(page)

                # Handle login popup
                await self._handle_login_wall(page)
                await self._random_delay(1000, 2000)

                # Check if profile exists / is accessible
                page_content = await page.content()
                if "Sorry, this page isn't available" in page_content:
                    errors.append(f"Profile @{username} does not exist or is not available")
                    await browser.close()
                    return {
                        'success': False,
                        'posts_downloaded': 0,
                        'errors': errors,
                        'engagement_metrics': engagement_metrics
                    }

                # Check for private profile
                if "This account is private" in page_content or "This Account is Private" in page_content:
                    self.logger.warning(f"Profile @{username} is private")
                    # Still try to get follower count
                    followers = await self._extract_profile_stats(page)
                    engagement_metrics.update(followers)

                    output_dir = self._create_output_directory(grantee_name, username)
                    metadata = {
                        'username': username,
                        'url': url,
                        'grantee_name': grantee_name,
                        'is_private': True,
                        'posts': [],
                        'engagement_metrics': engagement_metrics,
                        'scraped_at': datetime.now().isoformat()
                    }
                    self.save_metadata(output_dir, metadata)

                    return {
                        'success': True,
                        'posts_downloaded': 0,
                        'errors': ['Profile is private'],
                        'engagement_metrics': engagement_metrics
                    }

                # Extract profile stats (followers, following, posts count)
                profile_stats = await self._extract_profile_stats(page)
                engagement_metrics.update(profile_stats)
                self.logger.info(f"Profile stats: {profile_stats}")

                # Note: Instagram blocks post extraction without login
                # We can only get profile stats (followers, following, posts count)
                # Individual posts require authentication
                posts = []

                # Log the limitation
                if profile_stats.get('posts_count', 0) > 0:
                    self.logger.info(
                        f"Profile has {profile_stats['posts_count']} posts but Instagram requires login to view them. "
                        f"Only profile stats collected."
                    )

                # Calculate engagement metrics
                if posts:
                    total_likes = sum(p.get('likes', 0) for p in posts)
                    total_comments = sum(p.get('comments', 0) for p in posts)

                    engagement_metrics['total_likes'] = total_likes
                    engagement_metrics['total_comments'] = total_comments
                    engagement_metrics['posts_analyzed'] = len(posts)

                    followers = engagement_metrics.get('followers_count', 0)
                    if followers and followers > 0:
                        total_engagement = total_likes + total_comments
                        avg_engagement = (total_engagement / len(posts)) / followers * 100
                        engagement_metrics['avg_engagement_rate'] = round(avg_engagement, 2)

                    self.logger.info(f"Extracted {len(posts)} posts with {total_likes + total_comments} total engagements")

                # Save data
                output_dir = self._create_output_directory(grantee_name, username)

                metadata = {
                    'username': username,
                    'url': url,
                    'grantee_name': grantee_name,
                    'is_private': False,
                    'posts': posts,
                    'engagement_metrics': engagement_metrics,
                    'scraped_at': datetime.now().isoformat()
                }
                self.save_metadata(output_dir, metadata)

                await self._save_cookies(context)
                await browser.close()

                self.logger.info(f"Successfully scraped @{username}: {len(posts)} posts")

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

    async def _extract_profile_stats(self, page) -> Dict[str, int]:
        """Extract followers, following, and posts count from profile."""
        stats = {
            'followers_count': 0,
            'following_count': 0,
            'posts_count': 0
        }

        try:
            # Try to get stats from meta tags first (most reliable)
            try:
                meta_desc = await page.query_selector('meta[name="description"]')
                if meta_desc:
                    content = await meta_desc.get_attribute('content')
                    if content:
                        # Pattern: "1.2M Followers, 500 Following, 1,234 Posts"
                        followers_match = re.search(r'([\d,.]+[KkMm]?)\s*Followers', content)
                        following_match = re.search(r'([\d,.]+[KkMm]?)\s*Following', content)
                        posts_match = re.search(r'([\d,.]+[KkMm]?)\s*Posts', content)

                        if followers_match:
                            stats['followers_count'] = self._parse_count(followers_match.group(1))
                        if following_match:
                            stats['following_count'] = self._parse_count(following_match.group(1))
                        if posts_match:
                            stats['posts_count'] = self._parse_count(posts_match.group(1))

                        if stats['followers_count'] > 0:
                            return stats
            except Exception as e:
                self.logger.debug(f"Could not extract from meta: {e}")

            # Fallback: Try to find stats in page text
            page_text = await page.evaluate('() => document.body.innerText')

            # Look for patterns like "1,234 followers"
            patterns = [
                (r'([\d,]+(?:\.\d+)?)\s*([KkMm])?\s*followers?', 'followers_count'),
                (r'([\d,]+(?:\.\d+)?)\s*([KkMm])?\s*following', 'following_count'),
                (r'([\d,]+(?:\.\d+)?)\s*([KkMm])?\s*posts?', 'posts_count'),
            ]

            for pattern, key in patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    stats[key] = self._parse_count(match.group(1), match.group(2) if len(match.groups()) > 1 else None)

        except Exception as e:
            self.logger.debug(f"Error extracting profile stats: {e}")

        return stats

    def _parse_count(self, number_str: str, multiplier: str = None) -> int:
        """Parse a count string like '1.2K' or '1,234' into an integer."""
        try:
            # Remove commas
            number_str = number_str.replace(',', '')

            # Check for K/M suffix in the string itself
            if number_str.lower().endswith('k'):
                return int(float(number_str[:-1]) * 1000)
            elif number_str.lower().endswith('m'):
                return int(float(number_str[:-1]) * 1000000)

            count = float(number_str)

            if multiplier:
                if multiplier.lower() == 'k':
                    count *= 1000
                elif multiplier.lower() == 'm':
                    count *= 1000000

            return int(count)
        except (ValueError, AttributeError):
            return 0

    async def _scroll_page(self, page, max_scrolls: int = 5):
        """Scroll page with human-like behavior to load more posts."""
        for i in range(max_scrolls):
            try:
                prev_height = await page.evaluate('document.body.scrollHeight')

                # Scroll in smaller increments
                scroll_distance = random.randint(400, 800)
                for _ in range(3):
                    await page.evaluate(f'window.scrollBy(0, {scroll_distance})')
                    await self._random_delay(200, 500)

                # Random chance to scroll back up
                if random.random() < 0.3:
                    await page.evaluate(f'window.scrollBy(0, -{random.randint(100, 300)})')
                    await self._random_delay(300, 600)

                await self._random_delay(1500, 3000)

                new_height = await page.evaluate('document.body.scrollHeight')
                if new_height == prev_height:
                    self.logger.debug(f"No new content after scroll {i+1}, stopping")
                    break

                self.logger.debug(f"Scroll {i+1}/{max_scrolls} completed")

            except Exception as e:
                self.logger.debug(f"Error during scroll {i+1}: {e}")
                break

    async def _extract_posts_no_scroll(self, page, max_posts: int = 25) -> List[Dict[str, Any]]:
        """Extract posts from the profile page without scrolling - just from initial HTML."""
        posts = []

        try:
            # Get the page HTML immediately
            html = await page.content()

            # Look for post links in HTML using regex
            pattern = r'href="(/p/[A-Za-z0-9_-]+/)"'
            matches = re.findall(pattern, html)

            post_links = []
            for match in matches:
                url = 'https://www.instagram.com' + match
                if url not in post_links:
                    post_links.append(url)

            if post_links:
                self.logger.info(f"Found {len(post_links)} posts from initial HTML")

                # Limit to max_posts
                post_links = post_links[:max_posts]

                # For each post, create basic entry (without visiting each post page)
                for idx, link in enumerate(post_links):
                    shortcode = link.split('/p/')[-1].rstrip('/')
                    posts.append({
                        'id': f'post_{idx}',
                        'url': link,
                        'shortcode': shortcode,
                        'caption': '',
                        'likes': 0,
                        'comments': 0,
                        'date': None,
                        'is_video': False
                    })

                self.logger.info(f"Extracted {len(posts)} post links (basic data)")

        except Exception as e:
            self.logger.debug(f"Error extracting posts from HTML: {e}")

        return posts

    async def _extract_posts(self, page, max_posts: int = 25) -> List[Dict[str, Any]]:
        """Extract posts from the profile page."""
        posts = []

        try:
            # Wait for main content to load
            await self._random_delay(2000, 3000)

            # Try to remove any blocking overlays first
            try:
                await page.evaluate('''
                    // Remove login modals and overlays
                    document.querySelectorAll('div[role="dialog"]').forEach(el => el.remove());
                    document.querySelectorAll('div[role="presentation"]').forEach(el => el.remove());
                ''')
            except:
                pass

            # Instagram post grid selectors - try multiple approaches
            post_selectors = [
                'main article a[href*="/p/"]',
                'main a[href*="/p/"]',
                'article a[href*="/p/"]',
                'a[href*="/p/"]',
                'main article a[href*="/reel/"]',
                'a[href*="/reel/"]',
            ]

            post_links = []
            for selector in post_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        for elem in elements:
                            href = await elem.get_attribute('href')
                            if href and ('/p/' in href or '/reel/' in href):
                                # Normalize URL
                                if not href.startswith('http'):
                                    href = 'https://www.instagram.com' + href
                                if href not in post_links:
                                    post_links.append(href)
                        if post_links:
                            self.logger.info(f"Found {len(post_links)} posts using selector: {selector}")
                            break
                except Exception as e:
                    self.logger.debug(f"Error with selector {selector}: {e}")
                    continue

            # If no posts found via selectors, try extracting from page HTML
            if not post_links:
                try:
                    html = await page.content()
                    # Look for post links in HTML
                    import re
                    pattern = r'href="(/p/[A-Za-z0-9_-]+/)"'
                    matches = re.findall(pattern, html)
                    for match in matches:
                        url = 'https://www.instagram.com' + match
                        if url not in post_links:
                            post_links.append(url)
                    if post_links:
                        self.logger.info(f"Found {len(post_links)} posts from HTML parsing")
                except Exception as e:
                    self.logger.debug(f"HTML parsing failed: {e}")

            if not post_links:
                self.logger.warning("Could not find any posts on the page")
                # Take a debug screenshot
                try:
                    screenshot_path = self.output_dir / "debug_no_posts.png" if self.output_dir else Path("output/debug_no_posts.png")
                    screenshot_path.parent.mkdir(exist_ok=True, parents=True)
                    await page.screenshot(path=str(screenshot_path))
                    self.logger.info(f"Debug screenshot saved to {screenshot_path}")
                except:
                    pass
                return posts

            # Limit to max_posts
            post_links = list(dict.fromkeys(post_links))[:max_posts]  # Remove duplicates and limit
            self.logger.info(f"Processing {len(post_links)} unique post links...")

            # Extract data from each post by visiting it
            for idx, link in enumerate(post_links):
                try:
                    post_data = await self._extract_post_data(page, link, idx)
                    if post_data:
                        posts.append(post_data)
                        self.logger.debug(f"Extracted post {idx + 1}/{len(post_links)}: {post_data.get('likes', 0)} likes")

                    # Small delay between post extractions
                    await self._random_delay(800, 1500)

                except Exception as e:
                    self.logger.debug(f"Error extracting post {idx}: {e}")
                    continue

            self.logger.info(f"Successfully extracted {len(posts)} posts")

        except Exception as e:
            self.logger.error(f"Error extracting posts: {e}")

        return posts

    async def _extract_post_data(self, page, link: str, index: int) -> Optional[Dict[str, Any]]:
        """Extract data from a single post by visiting it."""
        try:
            # Make absolute URL
            if link.startswith('/'):
                link = 'https://www.instagram.com' + link

            # Navigate to post
            await page.goto(link, wait_until='domcontentloaded', timeout=15000)
            await self._random_delay(1000, 2000)

            # Handle login popup if it appears
            await self._handle_login_wall(page)

            post_data = {
                'id': f'post_{index}',
                'url': link,
                'shortcode': link.split('/p/')[-1].split('/')[0] if '/p/' in link else link.split('/reel/')[-1].split('/')[0],
                'caption': '',
                'likes': 0,
                'comments': 0,
                'date': None,
                'is_video': '/reel/' in link
            }

            page_text = await page.evaluate('() => document.body.innerText')

            # Extract likes
            like_patterns = [
                r'([\d,]+)\s+likes?',
                r'Liked by.*?and\s+([\d,]+)\s+others?',
                r'([\d,]+)\s+views?',  # For videos
            ]

            for pattern in like_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    post_data['likes'] = self._parse_count(match.group(1))
                    break

            # Extract comments count
            comment_patterns = [
                r'View all\s+([\d,]+)\s+comments?',
                r'([\d,]+)\s+comments?',
            ]

            for pattern in comment_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    post_data['comments'] = self._parse_count(match.group(1))
                    break

            # Extract caption
            try:
                # Try meta description first
                meta_desc = await page.query_selector('meta[property="og:description"]')
                if meta_desc:
                    content = await meta_desc.get_attribute('content')
                    if content:
                        # Remove "X likes, X comments - " prefix
                        caption = re.sub(r'^[\d,]+\s+likes?,\s+[\d,]+\s+comments?\s+-\s+', '', content)
                        post_data['caption'] = caption[:500]  # Limit length
            except:
                pass

            # Extract date
            try:
                time_elem = await page.query_selector('time')
                if time_elem:
                    datetime_attr = await time_elem.get_attribute('datetime')
                    if datetime_attr:
                        post_data['date'] = datetime_attr
            except:
                pass

            # Go back to profile
            await page.go_back()
            await self._random_delay(500, 1000)

            return post_data

        except Exception as e:
            self.logger.debug(f"Error extracting post data from {link}: {e}")
            # Try to go back to profile
            try:
                await page.go_back()
            except:
                pass
            return None
