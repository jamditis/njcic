"""
Threads scraper using Playwright for browser automation.

Threads doesn't have a public API yet, so we use browser automation
to scrape posts. This implementation includes graceful fallbacks for
anti-bot measures and rate limiting.

Supports authentication via INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD
environment variables (Threads uses Instagram/Meta login).
"""
from __future__ import annotations

import os
import re
import json
import asyncio
import logging
import random
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None
    PlaywrightTimeout = Exception

try:
    from playwright_stealth.stealth import Stealth
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False
    Stealth = None

from dotenv import load_dotenv
from .base import BaseScraper

# Load environment variables
load_dotenv()


class ThreadsScraper(BaseScraper):
    """Scraper for Threads posts using Playwright browser automation."""

    platform_name = "threads"

    def __init__(self, output_dir: str = "output", headless: bool = True, timeout: int = 30000):
        """
        Initialize Threads scraper.

        Args:
            output_dir: Base directory for storing scraped data
            headless: Whether to run browser in headless mode
            timeout: Page load timeout in milliseconds
        """
        super().__init__(Path(output_dir) if isinstance(output_dir, str) else output_dir)
        self.headless = headless
        self.timeout = timeout
        self.max_posts = 25  # Threads specific limit as per requirements
        self.username = os.getenv('INSTAGRAM_USERNAME')
        self.password = os.getenv('INSTAGRAM_PASSWORD')
        self._logged_in = False

        # Cookie persistence for session reuse
        self.cookies_file = Path(output_dir) / ".threads_cookies.json"

        # Retry configuration
        self.max_retries = 3
        self.retry_delay_base = 2  # Base delay in seconds for exponential backoff

        if not PLAYWRIGHT_AVAILABLE:
            self.logger.warning(
                "Playwright not installed. Install with: pip install playwright && playwright install"
            )

        if not STEALTH_AVAILABLE:
            self.logger.warning(
                "playwright-stealth not installed. Install with: pip install playwright-stealth for better anti-detection"
            )

    async def _random_delay(self, min_sec: float = 0.5, max_sec: float = 2.0):
        """
        Add random delay to simulate human behavior.

        Args:
            min_sec: Minimum delay in seconds
            max_sec: Maximum delay in seconds
        """
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)

    async def _human_type(self, element, text: str):
        """
        Type text with human-like delays between keystrokes.

        Args:
            element: Playwright element to type into
            text: Text to type
        """
        for char in text:
            await element.type(char, delay=random.uniform(50, 150))
            # Occasionally pause longer (simulating thinking)
            if random.random() < 0.1:
                await self._random_delay(0.2, 0.5)

    async def _save_cookies(self, context):
        """
        Save browser cookies for session reuse.

        Args:
            context: Playwright browser context
        """
        try:
            cookies = await context.cookies()
            self.cookies_file.parent.mkdir(exist_ok=True, parents=True)
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f)
            self.logger.info(f"Cookies saved to {self.cookies_file}")
        except Exception as e:
            self.logger.warning(f"Failed to save cookies: {e}")

    async def _load_cookies(self, context):
        """
        Load saved cookies into browser context.

        Args:
            context: Playwright browser context

        Returns:
            True if cookies were loaded successfully, False otherwise
        """
        try:
            if self.cookies_file.exists():
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                await context.add_cookies(cookies)
                self.logger.info("Loaded saved cookies")
                return True
        except Exception as e:
            self.logger.warning(f"Failed to load cookies: {e}")
        return False

    async def _get_random_user_agent(self) -> str:
        """
        Get a random realistic user agent.

        Returns:
            User agent string
        """
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        return random.choice(user_agents)

    async def _get_random_viewport(self) -> Dict[str, int]:
        """
        Get a random viewport size.

        Returns:
            Dictionary with width and height
        """
        viewports = [
            {'width': 1920, 'height': 1080},
            {'width': 1366, 'height': 768},
            {'width': 1536, 'height': 864},
            {'width': 1440, 'height': 900},
            {'width': 1280, 'height': 720},
        ]
        return random.choice(viewports)

    async def _retry_with_backoff(self, func, *args, **kwargs):
        """
        Retry a function with exponential backoff.

        Args:
            func: Async function to retry
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func if successful

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay_base ** (attempt + 1)
                    jitter = random.uniform(0, delay * 0.3)
                    total_delay = delay + jitter
                    self.logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                        f"Retrying in {total_delay:.1f}s..."
                    )
                    await asyncio.sleep(total_delay)
                else:
                    self.logger.error(f"All {self.max_retries} attempts failed")

        raise last_exception

    async def _login(self, page) -> bool:
        """
        Log in to Threads using Instagram credentials.

        Threads uses Meta/Instagram login, so we authenticate via Instagram.

        Args:
            page: Playwright page object

        Returns:
            True if login successful, False otherwise
        """
        if not self.username or not self.password:
            self.logger.warning("Instagram credentials not found in environment variables")
            return False

        try:
            self.logger.info("Attempting Threads login via Instagram...")

            # Navigate to Threads login page
            await page.goto('https://www.threads.net/login', timeout=self.timeout)
            await self._random_delay(2, 4)

            # Look for "Log in with Instagram" button or direct login form
            # Threads may show different login flows
            try:
                # Try multiple selectors for the Instagram login button
                ig_login_selectors = [
                    'text="Log in with Instagram"',
                    'button:has-text("Log in with Instagram")',
                    'a:has-text("Log in with Instagram")',
                    '[role="button"]:has-text("Instagram")'
                ]

                ig_login_btn = None
                for selector in ig_login_selectors:
                    ig_login_btn = await page.query_selector(selector)
                    if ig_login_btn:
                        self.logger.info(f"Found Instagram login button with selector: {selector}")
                        break

                if ig_login_btn:
                    await ig_login_btn.click()
                    await self._random_delay(2, 4)
            except Exception as e:
                self.logger.warning(f"Could not find Instagram login button: {e}")

            # Try to find login form with multiple fallback selectors
            username_input = None
            password_input = None

            username_selectors = [
                'input[name="username"]',
                'input[aria-label*="username" i]',
                'input[placeholder*="username" i]',
                'input[type="text"]',
                'input[autocomplete="username"]'
            ]

            password_selectors = [
                'input[name="password"]',
                'input[aria-label*="password" i]',
                'input[type="password"]',
                'input[autocomplete="current-password"]'
            ]

            # Try to find username field
            for selector in username_selectors:
                username_input = await page.query_selector(selector)
                if username_input:
                    self.logger.debug(f"Found username input with selector: {selector}")
                    break

            # Try to find password field
            for selector in password_selectors:
                password_input = await page.query_selector(selector)
                if password_input:
                    self.logger.debug(f"Found password input with selector: {selector}")
                    break

            # If still not found, try clicking "Log in" link first
            if not username_input or not password_input:
                try:
                    login_link_selectors = [
                        'text="Log in"',
                        'a:has-text("Log in")',
                        'button:has-text("Log in")'
                    ]

                    for selector in login_link_selectors:
                        login_link = await page.query_selector(selector)
                        if login_link:
                            await login_link.click()
                            await self._random_delay(1, 2)
                            break

                    # Try finding inputs again
                    for selector in username_selectors:
                        username_input = await page.query_selector(selector)
                        if username_input:
                            break

                    for selector in password_selectors:
                        password_input = await page.query_selector(selector)
                        if password_input:
                            break
                except Exception as e:
                    self.logger.warning(f"Error clicking login link: {e}")

            if not username_input or not password_input:
                self.logger.error("Could not find login form fields after trying all selectors")
                return False

            # Fill credentials with human-like typing
            self.logger.info("Filling login credentials...")
            await username_input.click()
            await self._random_delay(0.3, 0.7)
            await self._human_type(username_input, self.username)
            await self._random_delay(0.5, 1.0)

            await password_input.click()
            await self._random_delay(0.3, 0.7)
            await self._human_type(password_input, self.password)
            await self._random_delay(0.5, 1.0)

            # Submit form with multiple fallback methods
            submit_btn = None
            submit_selectors = [
                'button[type="submit"]',
                'button:has-text("Log in")',
                'button:has-text("Continue")',
                'input[type="submit"]',
                '[role="button"]:has-text("Log in")'
            ]

            for selector in submit_selectors:
                submit_btn = await page.query_selector(selector)
                if submit_btn:
                    self.logger.debug(f"Found submit button with selector: {selector}")
                    break

            if submit_btn:
                await submit_btn.click()
            else:
                # Fallback to pressing Enter
                self.logger.warning("Could not find submit button, pressing Enter")
                await page.keyboard.press('Enter')

            # Wait for navigation with realistic delay
            await self._random_delay(3, 6)

            # Check if login was successful
            current_url = page.url
            self.logger.info(f"Post-login URL: {current_url}")

            # Check for various success indicators
            if ('threads.net' in current_url or 'threads.com' in current_url) and 'login' not in current_url.lower():
                self.logger.info("Threads login successful")
                self._logged_in = True
                return True

            # Check for security challenge
            if 'challenge' in current_url.lower() or 'checkpoint' in current_url.lower():
                self.logger.warning("Security challenge detected - manual intervention may be required")
                return False

            # Check for two-factor authentication
            if '2fa' in current_url.lower() or 'two_factor' in current_url.lower():
                self.logger.warning("Two-factor authentication required - manual intervention needed")
                return False

            # Check for error messages
            page_text = await page.evaluate('document.body.textContent')
            error_keywords = ['incorrect', 'wrong', 'invalid', 'error', 'try again']
            if any(keyword in page_text.lower() for keyword in error_keywords):
                self.logger.error("Login failed - credentials may be incorrect")
                return False

            self.logger.warning(f"Login status unclear, current URL: {current_url}")
            return False

        except PlaywrightTimeout as e:
            self.logger.error(f"Timeout during login: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error during login: {e}")
            return False

    def extract_username(self, url: str) -> Optional[str]:
        """
        Extract username from Threads URL.

        Handles patterns:
        - threads.net/@username
        - threads.net/username
        - www.threads.net/@username
        - www.threads.net/username

        Args:
            url: Threads profile URL

        Returns:
            Extracted username (without @) or None if invalid
        """
        if not url or not isinstance(url, str):
            return None

        # Clean up the URL
        url = url.strip()

        # Patterns for Threads URLs (handles both .net and .com)
        patterns = [
            r'threads\.(?:net|com)/@([^/?&#]+)',  # threads.net/@username or threads.com/@username
            r'threads\.(?:net|com)/([^/@?&#]+)',  # threads.net/username or threads.com/username
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                username = match.group(1).strip()
                # Filter out non-username paths
                if username and username not in ['explore', 'settings', 'activity', 'search']:
                    return username

        return None

    def _create_output_directory(self, grantee_name: str, username: str) -> Path:
        """
        Create and return Threads-specific output directory.

        Creates structure: output/threads/{grantee_name}/{username}

        Args:
            grantee_name: Name of the grantee
            username: Threads username

        Returns:
            Path object for the output directory
        """
        # Get base output path from parent class
        base_path = self.get_output_path(grantee_name)

        # Add username subdirectory
        username_path = base_path / username
        username_path.mkdir(exist_ok=True, parents=True)

        return username_path

    async def _wait_for_page_load(self, page, selector: str = 'article', max_wait: int = 10):
        """
        Wait for page to load with progressive timeout.

        Args:
            page: Playwright page object
            selector: CSS selector to wait for
            max_wait: Maximum wait time in seconds
        """
        try:
            await page.wait_for_selector(selector, timeout=max_wait * 1000)
        except PlaywrightTimeout:
            self.logger.warning(f"Timeout waiting for selector: {selector}")

    async def _scroll_to_load_posts(self, page, target_posts: int = 25, max_scrolls: int = 10):
        """
        Scroll page to trigger lazy loading of posts with realistic human-like behavior.

        Args:
            page: Playwright page object
            target_posts: Target number of posts to load
            max_scrolls: Maximum scroll attempts

        Returns:
            Number of posts loaded
        """
        previous_height = 0
        scrolls = 0
        no_change_count = 0

        while scrolls < max_scrolls:
            # Realistic scroll behavior: scroll in chunks, not always to bottom
            scroll_type = random.choice(['full', 'partial', 'partial', 'slow'])

            if scroll_type == 'full':
                # Scroll to bottom in one go
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            elif scroll_type == 'partial':
                # Scroll down by a partial amount (60-90% of viewport)
                scroll_amount = random.randint(60, 90)
                await page.evaluate(f'window.scrollBy(0, window.innerHeight * {scroll_amount / 100})')
            else:  # slow
                # Simulate slow scroll with multiple small steps
                steps = random.randint(3, 6)
                scroll_per_step = await page.evaluate('Math.floor(window.innerHeight / arguments[0])', steps)
                for _ in range(steps):
                    await page.evaluate(f'window.scrollBy(0, {scroll_per_step})')
                    await self._random_delay(0.1, 0.3)

            # Random delay after scrolling (simulating reading)
            await self._random_delay(1.5, 4.0)

            # Occasionally scroll up a bit (like a human re-reading)
            if random.random() < 0.2:
                await page.evaluate('window.scrollBy(0, -window.innerHeight * 0.3)')
                await self._random_delay(0.5, 1.0)

            # Check current height
            current_height = await page.evaluate('document.body.scrollHeight')

            # Count visible articles (posts) with error handling
            try:
                post_count = await page.evaluate('document.querySelectorAll("article").length')
            except Exception as e:
                self.logger.warning(f"Error counting posts: {e}")
                post_count = 0

            self.logger.info(f"Loaded {post_count} posts (scroll {scrolls + 1}/{max_scrolls})")

            # Break if we have enough posts
            if post_count >= target_posts:
                self.logger.info(f"Reached target of {target_posts} posts")
                break

            # Track if page stopped growing
            if current_height == previous_height:
                no_change_count += 1
                if no_change_count >= 3:
                    self.logger.info("Page stopped growing, ending scroll")
                    break
            else:
                no_change_count = 0

            previous_height = current_height
            scrolls += 1

        return post_count

    async def _extract_post_data(self, page) -> List[Dict[str, Any]]:
        """
        Extract post data from the loaded page with robust fallback selectors.

        Args:
            page: Playwright page object

        Returns:
            List of post dictionaries with metadata
        """
        posts = []

        try:
            # Extract posts using JavaScript in the browser context
            posts_data = await page.evaluate('''() => {
                const articles = document.querySelectorAll('article');
                const posts = [];

                articles.forEach((article, index) => {
                    try {
                        // Extract post text with multiple fallback strategies
                        let postText = '';

                        // Strategy 1: Look for text in [dir="auto"] elements
                        const dirAutoElements = article.querySelectorAll('[dir="auto"]');
                        dirAutoElements.forEach(el => {
                            const text = el.textContent?.trim();
                            // Skip if it's just engagement text (likes, replies, etc.)
                            if (text && !text.match(/^\\d+\\s+(like|repl|repost|quote)/i)) {
                                if (text.length > postText.length) {
                                    postText = text;
                                }
                            }
                        });

                        // Strategy 2: Look for specific content divs
                        if (!postText) {
                            const contentSelectors = [
                                '[data-testid="post-text"]',
                                '.post-text',
                                '[role="article"] > div > div',
                                'span[dir="auto"]'
                            ];

                            for (const selector of contentSelectors) {
                                const el = article.querySelector(selector);
                                if (el?.textContent?.trim()) {
                                    postText = el.textContent.trim();
                                    break;
                                }
                            }
                        }

                        // Strategy 3: Get all text and filter
                        if (!postText) {
                            const allText = article.textContent || '';
                            const lines = allText.split('\\n').filter(line => {
                                const trimmed = line.trim();
                                return trimmed.length > 10 &&
                                       !trimmed.match(/^\\d+\\s+(like|repl|repost|quote|hour|min|day)/i);
                            });
                            if (lines.length > 0) {
                                postText = lines[0].trim();
                            }
                        }

                        // Extract timestamp with multiple fallback selectors
                        let timestamp = new Date().toISOString();
                        const timeSelectors = [
                            'time[datetime]',
                            'time',
                            '[data-testid="timestamp"]',
                            'a[href*="/post/"] time'
                        ];

                        for (const selector of timeSelectors) {
                            const timeElement = article.querySelector(selector);
                            if (timeElement) {
                                timestamp = timeElement.getAttribute('datetime') ||
                                           timeElement.textContent ||
                                           timestamp;
                                break;
                            }
                        }

                        // Extract engagement metrics with improved regex
                        const allText = article.textContent || '';

                        // Try to find likes (matches "X likes", "1 like", "123K likes")
                        const likesMatch = allText.match(/([\\d,\\.]+[KMB]?)\\s+likes?/i);
                        let likes = 0;
                        if (likesMatch) {
                            const likeText = likesMatch[1].replace(/,/g, '');
                            if (likeText.includes('K')) {
                                likes = Math.floor(parseFloat(likeText) * 1000);
                            } else if (likeText.includes('M')) {
                                likes = Math.floor(parseFloat(likeText) * 1000000);
                            } else {
                                likes = parseInt(likeText) || 0;
                            }
                        }

                        // Try to find replies (matches "X replies", "1 reply")
                        const repliesMatch = allText.match(/([\\d,\\.]+[KMB]?)\\s+repl(?:y|ies)/i);
                        let replies = 0;
                        if (repliesMatch) {
                            const replyText = repliesMatch[1].replace(/,/g, '');
                            if (replyText.includes('K')) {
                                replies = Math.floor(parseFloat(replyText) * 1000);
                            } else if (replyText.includes('M')) {
                                replies = Math.floor(parseFloat(replyText) * 1000000);
                            } else {
                                replies = parseInt(replyText) || 0;
                            }
                        }

                        // Try to find reposts/quotes
                        const repostsMatch = allText.match(/([\\d,\\.]+[KMB]?)\\s+(?:repost|quote)s?/i);
                        let reposts = 0;
                        if (repostsMatch) {
                            const repostText = repostsMatch[1].replace(/,/g, '');
                            if (repostText.includes('K')) {
                                reposts = Math.floor(parseFloat(repostText) * 1000);
                            } else if (repostText.includes('M')) {
                                reposts = Math.floor(parseFloat(repostText) * 1000000);
                            } else {
                                reposts = parseInt(repostText) || 0;
                            }
                        }

                        // Get post URL with fallback selectors
                        let postUrl = '';
                        const linkSelectors = [
                            'a[href*="/post/"]',
                            'a[role="link"][href*="/post/"]',
                            '[data-testid="post-link"]'
                        ];

                        for (const selector of linkSelectors) {
                            const linkElement = article.querySelector(selector);
                            if (linkElement?.href) {
                                postUrl = linkElement.href;
                                break;
                            }
                        }

                        posts.push({
                            index: index,
                            text: postText || '[No text content]',
                            timestamp: timestamp,
                            likes: likes,
                            replies: replies,
                            reposts: reposts,
                            url: postUrl,
                            raw_html_length: article.innerHTML?.length || 0
                        });
                    } catch (err) {
                        console.error('Error extracting post:', err);
                        // Add placeholder for failed extraction
                        posts.push({
                            index: index,
                            text: '[Extraction failed]',
                            timestamp: new Date().toISOString(),
                            likes: 0,
                            replies: 0,
                            reposts: 0,
                            url: '',
                            raw_html_length: 0,
                            error: err.message
                        });
                    }
                });

                return posts;
            }''')

            posts = posts_data if posts_data else []
            self.logger.info(f"Successfully extracted {len(posts)} posts")

        except Exception as e:
            self.logger.error(f"Error extracting post data: {e}")

        return posts

    async def _extract_follower_count(self, page) -> int:
        """
        Extract follower count from profile page.

        Args:
            page: Playwright page object

        Returns:
            Follower count (0 if not found)
        """
        try:
            # Threads shows followers in the format "X followers"
            followers_text = await page.evaluate('''() => {
                const text = document.body.textContent || '';
                const match = text.match(/([\\d,\\.]+[KMB]?)\\s+followers/i);
                return match ? match[1] : '0';
            }''')

            # Convert text like "1.2K" to number
            followers_text = followers_text.replace(',', '')

            if 'K' in followers_text.upper():
                return int(float(followers_text.upper().replace('K', '')) * 1000)
            elif 'M' in followers_text.upper():
                return int(float(followers_text.upper().replace('M', '')) * 1000000)
            elif 'B' in followers_text.upper():
                return int(float(followers_text.upper().replace('B', '')) * 1000000000)
            else:
                return int(followers_text) if followers_text.isdigit() else 0

        except Exception as e:
            self.logger.warning(f"Could not extract follower count: {e}")
            return 0

    async def _scrape_async(self, url: str, username: str, output_dir: Path) -> Dict[str, Any]:
        """
        Async method to scrape Threads profile.

        Args:
            url: Threads profile URL
            username: Extracted username
            output_dir: Output directory for saving data

        Returns:
            Scraping result dictionary
        """
        result = {
            'success': False,
            'posts_downloaded': 0,
            'errors': [],
            'engagement_metrics': {
                'followers_count': 0,
                'total_likes': 0,
                'total_replies': 0,
                'total_reposts': 0,
                'avg_engagement_rate': 0.0
            }
        }

        async with async_playwright() as p:
            browser = None
            try:
                # Launch browser with additional anti-detection args
                self.logger.info(f"Launching browser (headless={self.headless})...")
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process'
                    ]
                )

                # Create context with random user agent and viewport
                user_agent = await self._get_random_user_agent()
                viewport = await self._get_random_viewport()

                self.logger.info(f"Using viewport: {viewport['width']}x{viewport['height']}")

                context = await browser.new_context(
                    user_agent=user_agent,
                    viewport=viewport,
                    locale='en-US',
                    timezone_id='America/New_York',
                    permissions=['geolocation'],
                    extra_http_headers={
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1'
                    }
                )

                # Try to load saved cookies
                cookies_loaded = await self._load_cookies(context)
                if cookies_loaded:
                    self.logger.info("Using saved session cookies")

                page = await context.new_page()

                # Apply stealth mode if available
                if STEALTH_AVAILABLE:
                    try:
                        stealth = Stealth()
                        await stealth.apply_stealth_async(page)
                        self.logger.info("Applied playwright-stealth for anti-detection")
                    except Exception as e:
                        self.logger.warning(f"Could not apply stealth mode: {e}")

                # Attempt login if credentials are available and no cookies loaded
                if self.username and self.password and not cookies_loaded:
                    if not await self._login(page):
                        self.logger.warning("Login failed, continuing without authentication")
                    else:
                        # Save cookies after successful login
                        await self._save_cookies(context)
                        await self._random_delay(1, 3)  # Brief pause after login

                # Construct profile URL
                profile_url = f"https://www.threads.net/@{username}" if not url.startswith('http') else url

                self.logger.info(f"Navigating to {profile_url}...")

                try:
                    await page.goto(profile_url, timeout=self.timeout, wait_until='domcontentloaded')
                except PlaywrightTimeout:
                    result['errors'].append(f"Timeout loading profile page: {profile_url}")
                    return result

                # Add realistic delay after page load
                await self._random_delay(1, 2)

                # Wait for content to load
                await self._wait_for_page_load(page)

                # Check for rate limiting or blocking
                page_text = await page.evaluate('document.body.textContent')
                if any(keyword in page_text.lower() for keyword in ['rate limit', 'try again later', 'blocked', 'suspicious activity']):
                    error_msg = "Rate limit or anti-bot detection triggered"
                    self.logger.error(error_msg)
                    result['errors'].append(error_msg)
                    return result

                # Check if profile exists (look for error messages)
                page_text = await page.evaluate('document.body.textContent')
                if 'not found' in page_text.lower() or 'doesn\'t exist' in page_text.lower():
                    result['errors'].append(f"Profile @{username} not found")
                    return result

                # Extract follower count
                followers = await self._extract_follower_count(page)
                result['engagement_metrics']['followers_count'] = followers
                self.logger.info(f"Followers: {followers:,}")

                # Scroll to load posts
                self.logger.info(f"Scrolling to load up to {self.max_posts} posts...")
                posts_loaded = await self._scroll_to_load_posts(page, self.max_posts)

                if posts_loaded == 0:
                    result['errors'].append("No posts found on profile")
                    return result

                # Extract post data
                self.logger.info(f"Extracting data from {posts_loaded} posts...")
                posts = await self._extract_post_data(page)

                # Limit to max_posts
                posts = posts[:self.max_posts]

                if not posts:
                    result['errors'].append("Failed to extract post data")
                    return result

                # Calculate engagement metrics
                total_likes = sum(p.get('likes', 0) for p in posts)
                total_replies = sum(p.get('replies', 0) for p in posts)
                total_reposts = sum(p.get('reposts', 0) for p in posts)

                total_engagement = total_likes + total_replies + total_reposts
                avg_engagement_rate = (total_engagement / followers * 100) if followers > 0 else 0.0

                result['engagement_metrics'].update({
                    'total_likes': total_likes,
                    'total_replies': total_replies,
                    'total_reposts': total_reposts,
                    'avg_engagement_rate': round(avg_engagement_rate, 2)
                })

                # Save metadata
                metadata = {
                    'username': username,
                    'profile_url': profile_url,
                    'posts_count': len(posts),
                    'posts': posts,
                    'engagement_metrics': result['engagement_metrics'],
                    'scraped_at': datetime.now().isoformat()
                }

                self.save_metadata(output_dir, metadata)

                result['success'] = True
                result['posts_downloaded'] = len(posts)

                self.logger.info(f"Successfully scraped {len(posts)} posts from @{username}")
                self.logger.info(f"Engagement: {total_likes:,} likes, {total_replies:,} replies, {total_reposts:,} reposts")

            except Exception as e:
                error_msg = f"Error during scraping: {str(e)}"
                self.logger.exception(error_msg)
                result['errors'].append(error_msg)

            finally:
                if browser:
                    await browser.close()

        return result

    def scrape(self, url: str, grantee_name: str, max_posts: int = 25) -> Dict[str, Any]:
        """
        Scrape Threads profile content.

        Args:
            url: Threads profile URL
            grantee_name: Name of the grantee
            max_posts: Maximum posts to scrape

        Returns:
            Dictionary containing:
                - success (bool): Whether scraping was successful
                - posts_downloaded (int): Number of posts downloaded
                - errors (List[str]): List of errors encountered
                - engagement_metrics (Dict): Engagement metrics including:
                    - followers_count: Number of followers
                    - total_likes: Sum of likes across all posts
                    - total_replies: Sum of replies across all posts
                    - total_reposts: Sum of reposts across all posts
                    - avg_engagement_rate: Average engagement rate (%)
        """
        result = {
            'success': False,
            'posts_downloaded': 0,
            'errors': [],
            'engagement_metrics': {
                'followers_count': 0,
                'total_likes': 0,
                'total_replies': 0,
                'total_reposts': 0,
                'avg_engagement_rate': 0.0
            }
        }

        # Extract username
        username = self.extract_username(url)
        if not username:
            result['errors'].append(f"Could not extract username from URL: {url}")
            self.logger.error(result['errors'][-1])
            return result

        self.logger.info(f"Scraping Threads profile: @{username}")

        # Create output directory
        output_dir = self._create_output_directory(grantee_name, username)
        self.logger.info(f"Output directory: {output_dir}")

        # Run async scraper
        try:
            # Check if playwright is installed
            try:
                import playwright
            except ImportError:
                result['errors'].append(
                    "Playwright not installed. Install with: pip install playwright && playwright install chromium"
                )
                self.logger.error(result['errors'][-1])
                return result

            # Run async scraping
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._scrape_async(url, username, output_dir))
            finally:
                loop.close()

        except Exception as e:
            error_msg = f"Fatal error scraping Threads: {str(e)}"
            self.logger.exception(error_msg)
            result['errors'].append(error_msg)

        return result
